#pragma once

#include <algorithm>
#include <cstddef>
#include <optional>
#include <utility>
#include <vector>

#include "me/index.hpp"
#include "me/levels.hpp"
#include "me/store.hpp"

namespace me {

// Matching on top of a Store: price-time priority, trades at the resting price, IOC
// market orders and exchange-style modify. Same interface and behaviour as BookV1; the
// variants below differ only in their containers. After construction nothing allocates
// except the caller's trade buffer, and only the std::map / std::unordered_map variants
// allocate per level or per order.
template <class S>
class Book {
public:
    explicit Book(const BookConfig& cfg = {}) : store_(cfg) {}

    ExecutionReport add_limit(OrderId id, Side side, Price price, Quantity qty,
                              std::vector<Trade>& trades);
    ExecutionReport add_market(OrderId id, Side side, Quantity qty, std::vector<Trade>& trades);
    bool cancel(OrderId id);
    ExecutionReport modify(OrderId id, Price new_price, Quantity new_qty,
                           std::vector<Trade>& trades);

    [[nodiscard]] std::optional<Price> best_bid() const { return store_.best_price(Side::Buy); }
    [[nodiscard]] std::optional<Price> best_ask() const { return store_.best_price(Side::Sell); }
    [[nodiscard]] Quantity volume_at(Side side, Price price) const {
        return store_.volume_at(side, price);
    }
    [[nodiscard]] std::size_t level_count(Side side) const { return store_.level_count(side); }
    [[nodiscard]] std::size_t order_count() const { return store_.order_count(); }

    template <class F>
    void for_each_order(Side side, Price price, F&& f) const {
        store_.for_each_order(side, price, std::forward<F>(f));
    }

private:
    template <bool HasLimit>
    Quantity match(Side aggressor, OrderId id, Quantity qty, Price limit,
                   std::vector<Trade>& trades);

    S store_;
};

template <class S>
template <bool HasLimit>
Quantity Book<S>::match(Side aggressor, OrderId id, Quantity qty, Price limit,
                        std::vector<Trade>& trades) {
    const Side passive = opposite(aggressor);
    Quantity filled = 0;
    while (filled < qty) {
        const Slot s = store_.front(passive);
        if (s == kNil) {
            break;
        }
        const Price price = store_.price_of(s);
        if constexpr (HasLimit) {
            if (aggressor == Side::Buy ? price > limit : price < limit) {
                break;
            }
        }
        const Order& resting = store_.order(s);
        const Quantity fill = std::min(qty - filled, resting.qty);
        trades.push_back(aggressor == Side::Buy
                             ? Trade{id, resting.id, price, fill, aggressor}
                             : Trade{resting.id, id, price, fill, aggressor});
        filled += fill;
        if (fill == resting.qty) {
            store_.erase(s);
        } else {
            store_.set_qty(s, resting.qty - fill);
        }
    }
    return filled;
}

template <class S>
ExecutionReport Book<S>::add_limit(OrderId id, Side side, Price price, Quantity qty,
                                   std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
    } else if (price <= 0) {
        report.reject = RejectReason::InvalidPrice;
    } else if (!store_.config().in_band(price)) {
        report.reject = RejectReason::PriceOutOfBand;
    } else if (id == 0) {
        report.reject = RejectReason::InvalidId;
    } else if (store_.find(id) != kNil) {
        report.reject = RejectReason::DuplicateId;
    } else if (store_.full()) {
        report.reject = RejectReason::CapacityExceeded;
    }
    if (!report.accepted()) {
        return report;
    }

    report.filled = match<true>(side, id, qty, price, trades);
    report.resting = qty - report.filled;
    if (report.resting > 0) {
        store_.insert(id, side, price, report.resting);
    }
    return report;
}

template <class S>
ExecutionReport Book<S>::add_market(OrderId id, Side side, Quantity qty,
                                    std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
    } else if (id == 0) {
        report.reject = RejectReason::InvalidId;
    } else if (store_.find(id) != kNil) {
        report.reject = RejectReason::DuplicateId;
    }
    if (!report.accepted()) {
        return report;
    }

    report.filled = match<false>(side, id, qty, 0, trades);
    report.cancelled = qty - report.filled;
    return report;
}

template <class S>
bool Book<S>::cancel(OrderId id) {
    const Slot s = store_.find(id);
    if (s == kNil) {
        return false;
    }
    store_.erase(s);
    return true;
}

template <class S>
ExecutionReport Book<S>::modify(OrderId id, Price new_price, Quantity new_qty,
                                std::vector<Trade>& trades) {
    ExecutionReport report{id};
    if (new_qty == 0) {
        report.reject = RejectReason::InvalidQuantity;
    } else if (new_price <= 0) {
        report.reject = RejectReason::InvalidPrice;
    } else if (!store_.config().in_band(new_price)) {
        report.reject = RejectReason::PriceOutOfBand;
    }
    if (!report.accepted()) {
        return report;
    }
    const Slot s = store_.find(id);
    if (s == kNil) {
        report.reject = RejectReason::UnknownOrder;
        return report;
    }

    if (new_price == store_.price_of(s)) {
        // A decrease keeps time priority; an increase goes to the back of the level.
        if (new_qty > store_.order(s).qty) {
            store_.move_to_tail(s);
        }
        store_.set_qty(s, new_qty);
        report.resting = new_qty;
        return report;
    }

    // A new price re-enters through matching. The order keeps its slot and index entry
    // while it is out of the queue, so nothing is freed or allocated on this path. If the
    // caller's trade buffer fails to grow mid-match, the order is dropped as a cancel
    // (as BookV1 does) rather than left indexed but outside every queue.
    const Side side = store_.order(s).side;
    store_.unlink(s);
    try {
        report.filled = match<true>(side, id, new_qty, new_price, trades);
        report.resting = new_qty - report.filled;
        if (report.resting > 0) {
            store_.order(s).qty = report.resting;
            store_.link(s, new_price);
            return report;
        }
    } catch (...) {
        store_.discard(s);
        throw;
    }
    store_.discard(s);
    return report;
}

// Variants, each adding one change to the previous one (see docs/journal.md).
using BookMap = Book<Store<MapLevels, StdIndex>>;         // order pool + intrusive FIFO
using BookMapOA = Book<Store<MapLevels, OpenAddrIndex>>;  // + open-addressing index
using BookVec = Book<Store<VecLevels, OpenAddrIndex>>;    // + sorted level vector
using BookLadder = Book<Store<LadderLevels, OpenAddrIndex>>;  // + price ladder and bitmap

// The default book: the variant that holds up across every benchmark regime.
using OrderBook = BookLadder;

extern template class Book<Store<MapLevels, StdIndex>>;
extern template class Book<Store<MapLevels, OpenAddrIndex>>;
extern template class Book<Store<VecLevels, OpenAddrIndex>>;
extern template class Book<Store<LadderLevels, OpenAddrIndex>>;

}  // namespace me
