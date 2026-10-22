#pragma once

#include <cstddef>
#include <functional>
#include <list>
#include <map>
#include <optional>
#include <unordered_map>
#include <vector>

#include "me/types.hpp"

namespace me {

// v1: correct and readable, not fast. Price-time priority (FIFO within a level).
// See README.md "Roadmap" for the optimisations that replace each container.
class OrderBook {
public:
    // Trades are appended to `trades`; the caller owns and reuses the buffer so the
    // hot path does not allocate once the vector has grown.
    ExecutionReport add_limit(OrderId id, Side side, Price price, Quantity qty,
                              std::vector<Trade>& trades);

    // Market orders never rest: whatever cannot be filled is cancelled (IOC semantics).
    ExecutionReport add_market(OrderId id, Side side, Quantity qty, std::vector<Trade>& trades);

    bool cancel(OrderId id);

    [[nodiscard]] std::optional<Price> best_bid() const;
    [[nodiscard]] std::optional<Price> best_ask() const;
    [[nodiscard]] Quantity volume_at(Side side, Price price) const;
    [[nodiscard]] std::size_t level_count(Side side) const;
    [[nodiscard]] std::size_t order_count() const { return index_.size(); }

private:
    struct RestingOrder {
        OrderId id;
        Quantity remaining;
    };
    using Level = std::list<RestingOrder>;

    // Both maps iterate best price first.
    std::map<Price, Level, std::greater<>> bids_;
    std::map<Price, Level, std::less<>> asks_;

    struct Locator {
        Side side;
        Price price;
        Level::iterator it;
    };
    std::unordered_map<OrderId, Locator> index_;  // O(1) cancel

    template <class Levels, class Crosses>
    Quantity match(Levels& levels, Side aggressor, OrderId id, Quantity qty, Crosses crosses,
                   std::vector<Trade>& trades);

    void rest(OrderId id, Side side, Price price, Quantity qty);
};

}  // namespace me
