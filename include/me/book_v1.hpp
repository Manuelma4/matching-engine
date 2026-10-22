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

// The first version, kept unchanged as the behavioural reference: std::map price levels,
// std::list FIFO queues and std::unordered_map lookup. Every optimised variant must
// produce exactly the same event stream (see docs/BENCHMARKS.md, output hashes).
class BookV1 {
public:
    explicit BookV1(const BookConfig& cfg = {}) : cfg_(cfg) {}

    // Trades are appended to `trades`; the caller owns and reuses the buffer so the
    // hot path does not allocate once the vector has grown.
    ExecutionReport add_limit(OrderId id, Side side, Price price, Quantity qty,
                              std::vector<Trade>& trades);

    // Market orders never rest: whatever cannot be filled is cancelled (IOC semantics).
    ExecutionReport add_market(OrderId id, Side side, Quantity qty, std::vector<Trade>& trades);

    bool cancel(OrderId id);

    // `new_qty` is the new open quantity. A decrease at the same price keeps queue
    // priority; an increase moves the order to the back of its level; a price change
    // re-enters the order through matching and may trade. Rejects leave the book unchanged.
    // The report's filled + resting + cancelled equals new_qty.
    ExecutionReport modify(OrderId id, Price new_price, Quantity new_qty,
                           std::vector<Trade>& trades);

    [[nodiscard]] std::optional<Price> best_bid() const;
    [[nodiscard]] std::optional<Price> best_ask() const;
    [[nodiscard]] Quantity volume_at(Side side, Price price) const;
    [[nodiscard]] std::size_t level_count(Side side) const;
    [[nodiscard]] std::size_t order_count() const { return index_.size(); }

    // Visits the orders resting at one price in priority order: f(OrderId, Quantity).
    template <class F>
    void for_each_order(Side side, Price price, F&& f) const {
        const auto visit = [&](const auto& levels) {
            auto it = levels.find(price);
            if (it == levels.end()) {
                return;
            }
            for (const auto& order : it->second) {
                f(order.id, order.remaining);
            }
        };
        side == Side::Buy ? visit(bids_) : visit(asks_);
    }

private:
    struct RestingOrder {
        OrderId id;
        Quantity remaining;
    };
    using Level = std::list<RestingOrder>;

    BookConfig cfg_;

    // Both maps iterate best price first.
    std::map<Price, Level, std::greater<>> bids_;
    std::map<Price, Level, std::less<>> asks_;

    struct Locator {
        Side side;
        Price price;
        Level::iterator it;
    };
    using OrderIndex = std::unordered_map<OrderId, Locator>;
    OrderIndex index_;  // O(1) cancel and modify

    template <class F>
    decltype(auto) with_levels(Side side, F&& f) {
        return side == Side::Buy ? f(bids_) : f(asks_);
    }

    template <class Levels, class Crosses>
    Quantity match(Levels& levels, Side aggressor, OrderId id, Quantity qty, Crosses crosses,
                   std::vector<Trade>& trades);

    // Matches a validated limit order and rests the remainder.
    ExecutionReport execute_limit(OrderId id, Side side, Price price, Quantity qty,
                                  std::vector<Trade>& trades);
    void rest(OrderId id, Side side, Price price, Quantity qty);
    void remove(OrderIndex::iterator found);
};

}  // namespace me
