#pragma once

#include <cstdint>
#include <vector>

#include "me/types.hpp"

namespace me {

// Orders and levels are addressed by 32-bit slots into preallocated arrays rather than by
// pointers: half the size, and never invalidated because nothing is reallocated.
using Slot = std::uint32_t;
inline constexpr Slot kNil = 0xFFFF'FFFFu;

// A resting order, linked into the FIFO of its level. The price lives in the level, which
// keeps the node at 32 bytes: four per 128-byte cache line on Apple Silicon.
struct Order {
    OrderId id;
    Quantity qty;
    Slot level;
    Slot prev;
    Slot next;
    Side side;
};
static_assert(sizeof(Order) == 32);

// One price level: the ends of its FIFO plus running totals, so volume_at is O(1).
struct Level {
    Price price;
    Quantity total;
    Slot head;
    Slot tail;
    std::uint32_t count;
};
static_assert(sizeof(Level) == 32);

// Fixed-capacity slab with a free list threaded through the `Link` member. Freed slots
// are reused LIFO, so the most recently freed (cache-hot) slot is handed out first.
// Construction writes every element, which also pre-faults the pages.
template <class T, Slot T::*Link>
class Slab {
public:
    explicit Slab(std::uint32_t capacity) : items_(capacity) {
        for (Slot s = 0; s < capacity; ++s) {
            items_[s].*Link = s + 1 < capacity ? s + 1 : kNil;
        }
        free_ = capacity > 0 ? 0 : kNil;
    }

    [[nodiscard]] bool full() const { return free_ == kNil; }
    [[nodiscard]] std::uint32_t live() const { return live_; }

    Slot acquire() {
        const Slot s = free_;
        free_ = items_[s].*Link;
        ++live_;
        return s;
    }

    void release(Slot s) {
        items_[s].*Link = free_;
        free_ = s;
        --live_;
    }

    T& operator[](Slot s) { return items_[s]; }
    const T& operator[](Slot s) const { return items_[s]; }

private:
    std::vector<T> items_;
    Slot free_ = kNil;
    std::uint32_t live_ = 0;
};

using OrderPool = Slab<Order, &Order::next>;
using LevelPool = Slab<Level, &Level::head>;

}  // namespace me
