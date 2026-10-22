#include "me/order_book.hpp"

#include <algorithm>
#include <iterator>

namespace me {

namespace {

Trade make_trade(Side aggressor, OrderId aggressor_id, OrderId resting_id, Price price,
                 Quantity qty) {
    if (aggressor == Side::Buy) {
        return Trade{aggressor_id, resting_id, price, qty, aggressor};
    }
    return Trade{resting_id, aggressor_id, price, qty, aggressor};
}

template <class Levels>
Quantity level_volume(const Levels& levels, Price price) {
    auto it = levels.find(price);
    if (it == levels.end()) {
        return 0;
    }
    Quantity total = 0;
    for (const auto& order : it->second) {
        total += order.remaining;
    }
    return total;
}

}  // namespace

template <class Levels, class Crosses>
Quantity OrderBook::match(Levels& levels, Side aggressor, OrderId id, Quantity qty,
                          Crosses crosses, std::vector<Trade>& trades) {
    Quantity filled = 0;
    while (filled < qty && !levels.empty()) {
        auto level_it = levels.begin();
        if (!crosses(level_it->first)) {
            break;
        }
        Level& level = level_it->second;
        while (filled < qty && !level.empty()) {
            RestingOrder& resting = level.front();
            const Quantity fill = std::min(qty - filled, resting.remaining);
            trades.push_back(make_trade(aggressor, id, resting.id, level_it->first, fill));
            resting.remaining -= fill;
            filled += fill;
            if (resting.remaining == 0) {
                index_.erase(resting.id);
                level.pop_front();
            }
        }
        if (level.empty()) {
            levels.erase(level_it);
        }
    }
    return filled;
}

void OrderBook::rest(OrderId id, Side side, Price price, Quantity qty) {
    Level& level = side == Side::Buy ? bids_[price] : asks_[price];
    level.push_back(RestingOrder{id, qty});
    index_.emplace(id, Locator{side, price, std::prev(level.end())});
}

ExecutionReport OrderBook::add_limit(OrderId id, Side side, Price price, Quantity qty,
                                     std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
        return report;
    }
    if (price <= 0) {
        report.reject = RejectReason::InvalidPrice;
        return report;
    }
    if (index_.contains(id)) {
        report.reject = RejectReason::DuplicateId;
        return report;
    }
    return execute_limit(id, side, price, qty, trades);
}

ExecutionReport OrderBook::execute_limit(OrderId id, Side side, Price price, Quantity qty,
                                         std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (side == Side::Buy) {
        report.filled = match(asks_, side, id, qty, [price](Price p) { return p <= price; }, trades);
    } else {
        report.filled = match(bids_, side, id, qty, [price](Price p) { return p >= price; }, trades);
    }

    report.resting = qty - report.filled;
    if (report.resting > 0) {
        rest(id, side, price, report.resting);
    }
    return report;
}

ExecutionReport OrderBook::add_market(OrderId id, Side side, Quantity qty,
                                      std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
        return report;
    }
    if (index_.contains(id)) {
        report.reject = RejectReason::DuplicateId;
        return report;
    }

    const auto any_price = [](Price) { return true; };
    report.filled = side == Side::Buy ? match(asks_, side, id, qty, any_price, trades)
                                      : match(bids_, side, id, qty, any_price, trades);
    report.cancelled = qty - report.filled;
    return report;
}

void OrderBook::remove(OrderIndex::iterator found) {
    const Locator loc = found->second;
    index_.erase(found);
    with_levels(loc.side, [&loc](auto& levels) {
        auto level_it = levels.find(loc.price);
        level_it->second.erase(loc.it);
        if (level_it->second.empty()) {
            levels.erase(level_it);
        }
    });
}

bool OrderBook::cancel(OrderId id) {
    auto found = index_.find(id);
    if (found == index_.end()) {
        return false;
    }
    remove(found);
    return true;
}

ExecutionReport OrderBook::modify(OrderId id, Price new_price, Quantity new_qty,
                                  std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (new_qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
        return report;
    }
    if (new_price <= 0) {
        report.reject = RejectReason::InvalidPrice;
        return report;
    }
    auto found = index_.find(id);
    if (found == index_.end()) {
        report.reject = RejectReason::UnknownOrder;
        return report;
    }

    // All validation happens above, so nothing below can leave a half-applied modify.
    const Locator& loc = found->second;
    if (new_price == loc.price) {
        RestingOrder& order = *loc.it;
        if (new_qty > order.remaining) {
            // Increasing size forfeits time priority. splice relinks the node at the back
            // of the same list: no allocation, and loc.it stays valid.
            with_levels(loc.side, [&loc](auto& levels) {
                Level& level = levels.find(loc.price)->second;
                level.splice(level.end(), level, loc.it);
            });
        }
        order.remaining = new_qty;
        report.resting = new_qty;
        return report;
    }

    // A new price is a new commitment: leave the queue and re-enter through matching,
    // because the order may now cross the spread.
    const Side side = loc.side;
    remove(found);
    return execute_limit(id, side, new_price, new_qty, trades);
}

std::optional<Price> OrderBook::best_bid() const {
    if (bids_.empty()) {
        return std::nullopt;
    }
    return bids_.begin()->first;
}

std::optional<Price> OrderBook::best_ask() const {
    if (asks_.empty()) {
        return std::nullopt;
    }
    return asks_.begin()->first;
}

Quantity OrderBook::volume_at(Side side, Price price) const {
    return side == Side::Buy ? level_volume(bids_, price) : level_volume(asks_, price);
}

std::size_t OrderBook::level_count(Side side) const {
    return side == Side::Buy ? bids_.size() : asks_.size();
}

}  // namespace me
