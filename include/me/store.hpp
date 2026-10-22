#pragma once

#include <cstddef>
#include <optional>
#include <utility>

#include "me/core.hpp"

namespace me {

// Owns the resting orders: the order pool, the price-level container and the id index.
// It knows nothing about matching, so a market-data replica can reuse it as is.
//
// Levels: find(side, price), find_or_create(side, price), release(side, slot),
//         best(side), level(side, slot), count(side)
// Index:  find(id), insert(id, slot), erase(id)
template <class Levels, class Index>
class Store {
public:
    explicit Store(const BookConfig& cfg)
        : cfg_(cfg), orders_(cfg.max_orders), levels_(cfg), index_(cfg.max_orders) {}

    [[nodiscard]] const BookConfig& config() const { return cfg_; }
    [[nodiscard]] bool full() const { return orders_.full(); }
    [[nodiscard]] std::size_t order_count() const { return orders_.live(); }
    [[nodiscard]] std::size_t level_count(Side side) const { return levels_.count(side); }

    [[nodiscard]] Slot find(OrderId id) const { return index_.find(id); }
    Order& order(Slot s) { return orders_[s]; }
    [[nodiscard]] const Order& order(Slot s) const { return orders_[s]; }

    [[nodiscard]] Price price_of(Slot s) const {
        const Order& o = orders_[s];
        return levels_.level(o.side, o.level).price;
    }

    // The order first in time priority at the best price, or kNil.
    [[nodiscard]] Slot front(Side side) const {
        const Slot l = levels_.best(side);
        return l == kNil ? kNil : levels_.level(side, l).head;
    }

    [[nodiscard]] std::optional<Price> best_price(Side side) const {
        const Slot l = levels_.best(side);
        if (l == kNil) {
            return std::nullopt;
        }
        return levels_.level(side, l).price;
    }

    [[nodiscard]] Quantity volume_at(Side side, Price price) const {
        const Slot l = find_level(side, price);
        return l == kNil ? 0 : levels_.level(side, l).total;
    }

    // Visits the orders resting at one price in priority order: f(OrderId, Quantity).
    template <class F>
    void for_each_order(Side side, Price price, F&& f) const {
        const Slot l = find_level(side, price);
        if (l == kNil) {
            return;
        }
        for (Slot s = levels_.level(side, l).head; s != kNil; s = orders_[s].next) {
            f(orders_[s].id, orders_[s].qty);
        }
    }

    // Adds a new order at the back of its level. The caller has checked capacity, the
    // price band and that the id is not already resting.
    Slot insert(OrderId id, Side side, Price price, Quantity qty) {
        const Slot s = orders_.acquire();
        Order& o = orders_[s];
        o.id = id;
        o.qty = qty;
        o.side = side;
        link(s, price);
        index_.insert(id, s);
        return s;
    }

    // Appends an unlinked order at the back of the level for `price`.
    void link(Slot s, Price price) {
        Order& o = orders_[s];
        const Slot l = levels_.find_or_create(o.side, price);
        Level& level = levels_.level(o.side, l);
        o.level = l;
        o.prev = level.tail;
        o.next = kNil;
        if (level.tail == kNil) {
            level.head = s;
        } else {
            orders_[level.tail].next = s;
        }
        level.tail = s;
        level.total += o.qty;
        ++level.count;
    }

    // Takes an order out of its level's FIFO, keeping its slot and index entry. The level
    // is released once its last order leaves.
    void unlink(Slot s) {
        Order& o = orders_[s];
        Level& level = levels_.level(o.side, o.level);
        if (o.prev == kNil) {
            level.head = o.next;
        } else {
            orders_[o.prev].next = o.next;
        }
        if (o.next == kNil) {
            level.tail = o.prev;
        } else {
            orders_[o.next].prev = o.prev;
        }
        level.total -= o.qty;
        if (--level.count == 0) {
            levels_.release(o.side, o.level);
        }
    }

    // Frees an order that is no longer linked into a level.
    void discard(Slot s) {
        index_.erase(orders_[s].id);
        orders_.release(s);
    }

    void erase(Slot s) {
        unlink(s);
        discard(s);
    }

    void set_qty(Slot s, Quantity qty) {
        Order& o = orders_[s];
        Level& level = levels_.level(o.side, o.level);
        level.total = level.total - o.qty + qty;
        o.qty = qty;
    }

    // Moves an order to the back of its own level (loses time priority).
    void move_to_tail(Slot s) {
        Order& o = orders_[s];
        Level& level = levels_.level(o.side, o.level);
        if (level.tail == s) {
            return;
        }
        // Not the tail, so o.next is a real order and the level keeps others.
        if (o.prev == kNil) {
            level.head = o.next;
        } else {
            orders_[o.prev].next = o.next;
        }
        orders_[o.next].prev = o.prev;
        o.prev = level.tail;
        o.next = kNil;
        orders_[level.tail].next = s;
        level.tail = s;
    }

private:
    [[nodiscard]] Slot find_level(Side side, Price price) const {
        return cfg_.in_band(price) ? levels_.find(side, price) : kNil;
    }

    BookConfig cfg_;
    OrderPool orders_;
    Levels levels_;
    Index index_;
};

}  // namespace me
