#pragma once

#include <cstddef>
#include <functional>
#include <map>
#include <vector>

#include "me/core.hpp"

namespace me {

// Price-level containers. Each maps (side, price) to a Level slot and tracks the best
// level per side; they differ only in how a price is found.
//
//   MapLevels  std::map from price to level slot, O(log n): the textbook baseline.
//   VecLevels  per-side vector of level slots sorted with the best price at the back,
//              searched linearly from the touch, where nearly all activity happens.

class MapLevels {
public:
    explicit MapLevels(const BookConfig& cfg)
        : bid_pool_(levels_per_side(cfg)), ask_pool_(levels_per_side(cfg)) {}

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
    // At most one level per price in the band.
    static std::uint32_t levels_per_side(const BookConfig& cfg) {
        return std::uint32_t{1} << cfg.band_log2;
    }

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

// Bids ascending and asks descending, so the best price is always back(). Finding,
// inserting or erasing a level costs O(distance from the touch): cheap near the top of
// the book, linear deep in it. Capacity is reserved for every price in the band, so the
// vectors never reallocate.
class VecLevels {
public:
    explicit VecLevels(const BookConfig& cfg)
        : sides_{SideLevels(cfg.band_log2), SideLevels(cfg.band_log2)} {}

    [[nodiscard]] Slot find(Side side, Price price) const {
        const SideLevels& sl = sides_[index(side)];
        for (auto it = sl.order.rbegin(); it != sl.order.rend(); ++it) {
            const Price p = sl.pool[*it].price;
            if (p == price) {
                return *it;
            }
            if (better(side, price, p)) {
                break;  // walked past where `price` would be
            }
        }
        return kNil;
    }

    Slot find_or_create(Side side, Price price) {
        SideLevels& sl = sides_[index(side)];
        // pos ends at the first element that is not better than `price`, scanning from the
        // touch; everything at or after pos is better and stays behind the new level.
        std::size_t pos = sl.order.size();
        while (pos > 0) {
            const Slot l = sl.order[pos - 1];
            const Price p = sl.pool[l].price;
            if (p == price) {
                return l;
            }
            if (better(side, price, p)) {
                break;
            }
            --pos;
        }
        const Slot l = sl.pool.acquire();
        sl.pool[l] = Level{price, 0, kNil, kNil, 0};
        sl.order.insert(sl.order.begin() + static_cast<std::ptrdiff_t>(pos), l);
        return l;
    }

    void release(Side side, Slot l) {
        SideLevels& sl = sides_[index(side)];
        for (std::size_t i = sl.order.size(); i-- > 0;) {
            if (sl.order[i] == l) {
                sl.order.erase(sl.order.begin() + static_cast<std::ptrdiff_t>(i));
                break;
            }
        }
        sl.pool.release(l);
    }

    [[nodiscard]] Slot best(Side side) const {
        const SideLevels& sl = sides_[index(side)];
        return sl.order.empty() ? kNil : sl.order.back();
    }

    Level& level(Side side, Slot l) { return sides_[index(side)].pool[l]; }
    [[nodiscard]] const Level& level(Side side, Slot l) const {
        return sides_[index(side)].pool[l];
    }

    [[nodiscard]] std::size_t count(Side side) const { return sides_[index(side)].order.size(); }

private:
    struct SideLevels {
        explicit SideLevels(std::uint8_t band_log2) : pool(std::uint32_t{1} << band_log2) {
            order.reserve(std::size_t{1} << band_log2);
        }
        std::vector<Slot> order;  // best at the back
        LevelPool pool;
    };

    static constexpr std::size_t index(Side side) { return side == Side::Buy ? 0 : 1; }
    // True if `a` is a better price than `b` for orders on `side`.
    static constexpr bool better(Side side, Price a, Price b) {
        return side == Side::Buy ? a > b : a < b;
    }

    SideLevels sides_[2];
};

}  // namespace me
