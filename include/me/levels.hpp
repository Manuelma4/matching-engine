#pragma once

#include <cstddef>
#include <functional>
#include <map>

#include "me/core.hpp"

namespace me {

// Price-level containers. Each maps (side, price) to a Level slot and tracks the best
// level per side; they differ only in how a price is found.
//
//   MapLevels  std::map from price to level slot, O(log n): the textbook baseline.

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

}  // namespace me
