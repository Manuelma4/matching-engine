#pragma once

#include <algorithm>
#include <bit>
#include <cstddef>
#include <functional>
#include <map>
#include <stdexcept>
#include <vector>

#include "me/core.hpp"

namespace me {

// Live levels per side never exceed live orders (a level is released as soon as its last
// order leaves, and a re-priced order leaves its old level before joining a new one), so
// the pools need no more than min(prices in the band, max_orders) entries.
inline std::uint32_t max_levels_per_side(const BookConfig& cfg) {
    return static_cast<std::uint32_t>(
        std::min<std::uint64_t>(std::uint64_t{1} << cfg.band_log2, cfg.max_orders));
}

// Price-level containers. Each maps (side, price) to a Level slot and tracks the best
// level per side; they differ only in how a price is found.
//
//   MapLevels  std::map from price to level slot, O(log n): the textbook baseline.
//   VecLevels  per-side vector of level slots sorted with the best price at the back,
//              searched linearly from the touch, where nearly all activity happens.
//   LadderLevels  direct index into the price band, plus a three-level bitmap that finds
//              the next best price in O(1) when the best level empties.

class MapLevels {
public:
    explicit MapLevels(const BookConfig& cfg)
        : bid_pool_(max_levels_per_side(cfg)), ask_pool_(max_levels_per_side(cfg)) {}

    [[nodiscard]] Slot find(Side side, Price price) const {
        return side == Side::Buy ? lookup(bids_, price) : lookup(asks_, price);
    }

    Slot find_or_create(Side side, Price price) {
        return side == Side::Buy ? emplace(bids_, bid_pool_, price)
                                 : emplace(asks_, ask_pool_, price);
    }

    void release(Side side, Slot l) {
        if (side == Side::Buy) {
            bids_.erase(bid_pool_[l].price);
            bid_pool_.release(l);
        } else {
            asks_.erase(ask_pool_[l].price);
            ask_pool_.release(l);
        }
    }

    [[nodiscard]] Slot best(Side side) const {
        if (side == Side::Buy) {
            return bids_.empty() ? kNil : bids_.begin()->second;
        }
        return asks_.empty() ? kNil : asks_.begin()->second;
    }

    Level& level(Side side, Slot l) { return side == Side::Buy ? bid_pool_[l] : ask_pool_[l]; }
    [[nodiscard]] const Level& level(Side side, Slot l) const {
        return side == Side::Buy ? bid_pool_[l] : ask_pool_[l];
    }

    [[nodiscard]] std::size_t count(Side side) const {
        return side == Side::Buy ? bids_.size() : asks_.size();
    }

private:
    template <class Map>
    static Slot lookup(const Map& map, Price price) {
        auto it = map.find(price);
        return it == map.end() ? kNil : it->second;
    }

    template <class Map>
    static Slot emplace(Map& map, LevelPool& pool, Price price) {
        auto [it, inserted] = map.try_emplace(price, kNil);
        if (inserted) {
            it->second = pool.acquire();
            pool[it->second] = Level{price, 0, kNil, kNil, 0};
        }
        return it->second;
    }

    std::map<Price, Slot, std::greater<>> bids_;  // best first
    std::map<Price, Slot, std::less<>> asks_;
    LevelPool bid_pool_;
    LevelPool ask_pool_;
};

// Bids ascending and asks descending, so the best price is always back(). Each entry
// carries its price, so the search from the touch reads contiguous memory instead of
// following a slot per step. Finding, inserting or erasing a level costs O(distance from
// the touch): cheap near the top of the book, linear deep in it. Capacity is reserved up
// front, so the vectors never reallocate.
class VecLevels {
public:
    explicit VecLevels(const BookConfig& cfg)
        : sides_{SideLevels(max_levels_per_side(cfg)), SideLevels(max_levels_per_side(cfg))} {}

    [[nodiscard]] Slot find(Side side, Price price) const {
        const auto& order = sides_[index(side)].order;
        for (auto it = order.rbegin(); it != order.rend(); ++it) {
            if (it->price == price) {
                return it->level;
            }
            if (better(side, price, it->price)) {
                break;  // walked past where `price` would be
            }
        }
        return kNil;
    }

    Slot find_or_create(Side side, Price price) {
        SideLevels& sl = sides_[index(side)];
        // pos ends at the first entry that is not better than `price`, scanning from the
        // touch; everything at or after pos is better and stays behind the new level.
        std::size_t pos = sl.order.size();
        while (pos > 0) {
            const Entry& e = sl.order[pos - 1];
            if (e.price == price) {
                return e.level;
            }
            if (better(side, price, e.price)) {
                break;
            }
            --pos;
        }
        const Slot l = sl.pool.acquire();
        sl.pool[l] = Level{price, 0, kNil, kNil, 0};
        sl.order.insert(sl.order.begin() + static_cast<std::ptrdiff_t>(pos), Entry{price, l});
        return l;
    }

    void release(Side side, Slot l) {
        SideLevels& sl = sides_[index(side)];
        for (std::size_t i = sl.order.size(); i-- > 0;) {
            if (sl.order[i].level == l) {
                sl.order.erase(sl.order.begin() + static_cast<std::ptrdiff_t>(i));
                break;
            }
        }
        sl.pool.release(l);
    }

    [[nodiscard]] Slot best(Side side) const {
        const auto& order = sides_[index(side)].order;
        return order.empty() ? kNil : order.back().level;
    }

    Level& level(Side side, Slot l) { return sides_[index(side)].pool[l]; }
    [[nodiscard]] const Level& level(Side side, Slot l) const {
        return sides_[index(side)].pool[l];
    }

    [[nodiscard]] std::size_t count(Side side) const { return sides_[index(side)].order.size(); }

private:
    struct Entry {
        Price price;
        Slot level;
    };
    struct SideLevels {
        explicit SideLevels(std::uint32_t capacity) : pool(capacity) { order.reserve(capacity); }
        std::vector<Entry> order;  // best at the back
        LevelPool pool;
    };

    static constexpr std::size_t index(Side side) { return side == Side::Buy ? 0 : 1; }
    // True if `a` is a better price than `b` for orders on `side`.
    static constexpr bool better(Side side, Price a, Price b) {
        return side == Side::Buy ? a > b : a < b;
    }

    SideLevels sides_[2];
};

// One bit per price, summarised twice with a fan-out of 64: a set bit in l1 means "this l0
// word is non-zero", a set bit in l2 means "this l1 word is non-zero". The lowest or
// highest set bit is three count-zeros away (rbit/clz on arm64), however many empty ticks
// separate the levels. Supports up to 2^18 prices.
class LevelBitmap {
public:
    static constexpr std::uint8_t kMaxLog2 = 18;

    explicit LevelBitmap(std::uint8_t log2)
        : l0_(std::max<std::size_t>(1, (std::size_t{1} << log2) >> 6)),
          l1_(std::max<std::size_t>(1, (std::size_t{1} << log2) >> 12)) {}

    [[nodiscard]] bool test(Slot i) const { return (l0_[i >> 6] & bit(i)) != 0; }

    void set(Slot i) {
        l0_[i >> 6] |= bit(i);
        l1_[i >> 12] |= bit(i >> 6);
        l2_ |= bit(i >> 12);
    }

    void clear(Slot i) {
        if ((l0_[i >> 6] &= ~bit(i)) != 0) {
            return;
        }
        if ((l1_[i >> 12] &= ~bit(i >> 6)) != 0) {
            return;
        }
        l2_ &= ~bit(i >> 12);
    }

    [[nodiscard]] Slot lowest() const {
        if (l2_ == 0) {
            return kNil;
        }
        const Slot a = static_cast<Slot>(std::countr_zero(l2_));
        const Slot b = (a << 6) | static_cast<Slot>(std::countr_zero(l1_[a]));
        return (b << 6) | static_cast<Slot>(std::countr_zero(l0_[b]));
    }

    [[nodiscard]] Slot highest() const {
        if (l2_ == 0) {
            return kNil;
        }
        const Slot a = static_cast<Slot>(63 - std::countl_zero(l2_));
        const Slot b = (a << 6) | static_cast<Slot>(63 - std::countl_zero(l1_[a]));
        return (b << 6) | static_cast<Slot>(63 - std::countl_zero(l0_[b]));
    }

private:
    static constexpr std::uint64_t bit(Slot i) { return std::uint64_t{1} << (i & 63); }

    std::vector<std::uint64_t> l0_;
    std::vector<std::uint64_t> l1_;
    std::uint64_t l2_ = 0;
};

// A Level for every price in the band, indexed by (price - band_low), so finding or
// creating a level is a single array access. The best level per side is cached; when it
// empties, the bitmap gives the next one in O(1), which avoids the walk over empty ticks
// that sinks a plain array book in a fast market. 2^16 prices cost 2 MB per side.
class LadderLevels {
public:
    explicit LadderLevels(const BookConfig& cfg)
        : base_(cfg.band_low),
          sides_{SideLadder(checked(cfg.band_log2)), SideLadder(cfg.band_log2)} {}

    [[nodiscard]] Slot find(Side side, Price price) const {
        const Slot i = offset(price);
        return sides_[index(side)].bits.test(i) ? i : kNil;
    }

    Slot find_or_create(Side side, Price price) {
        SideLadder& sl = sides_[index(side)];
        const Slot i = offset(price);
        if (!sl.bits.test(i)) {
            sl.bits.set(i);
            sl.levels[i] = Level{price, 0, kNil, kNil, 0};
            ++sl.count;
            if (sl.best == kNil || (side == Side::Buy ? i > sl.best : i < sl.best)) {
                sl.best = i;
            }
        }
        return i;
    }

    void release(Side side, Slot i) {
        SideLadder& sl = sides_[index(side)];
        sl.bits.clear(i);
        --sl.count;
        if (i == sl.best) {
            // The emptied level was the extreme one, so the new best is the bitmap's
            // highest bid or lowest ask.
            sl.best = side == Side::Buy ? sl.bits.highest() : sl.bits.lowest();
        }
    }

    [[nodiscard]] Slot best(Side side) const { return sides_[index(side)].best; }

    Level& level(Side side, Slot i) { return sides_[index(side)].levels[i]; }
    [[nodiscard]] const Level& level(Side side, Slot i) const {
        return sides_[index(side)].levels[i];
    }

    [[nodiscard]] std::size_t count(Side side) const { return sides_[index(side)].count; }

private:
    struct SideLadder {
        explicit SideLadder(std::uint8_t band_log2)
            : levels(std::size_t{1} << band_log2), bits(band_log2) {}
        std::vector<Level> levels;
        LevelBitmap bits;
        Slot best = kNil;
        std::size_t count = 0;
    };

    static std::uint8_t checked(std::uint8_t band_log2) {
        if (band_log2 > LevelBitmap::kMaxLog2) {
            throw std::invalid_argument("LadderLevels: band_log2 must be at most 18");
        }
        return band_log2;
    }
    static constexpr std::size_t index(Side side) { return side == Side::Buy ? 0 : 1; }
    // The Store only passes prices inside the band; the unsigned distance cannot overflow.
    [[nodiscard]] Slot offset(Price price) const {
        return static_cast<Slot>(static_cast<std::uint64_t>(price) -
                                 static_cast<std::uint64_t>(base_));
    }

    Price base_;
    SideLadder sides_[2];
};

}  // namespace me
