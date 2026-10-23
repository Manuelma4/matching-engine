#include "itch/book.hpp"

#include <algorithm>

namespace itch {

namespace {

using me::kNil;
using me::Slot;

#if defined(ITCH_BINARY_LEVEL_SEARCH) && ITCH_BINARY_LEVEL_SEARCH
template <class Entries>
std::size_t binary_position(const Entries& entries, BookSide side, Price4 price) {
    return static_cast<std::size_t>(
        std::lower_bound(entries.begin(), entries.end(), price,
                         [side](const auto& entry, Price4 target) {
                             return side == BookSide::Bid ? entry.price < target
                                                         : entry.price > target;
                         }) - entries.begin());
}
#else
// True if `a` is a better price than `b` for orders on `side`.
bool better(BookSide side, Price4 a, Price4 b) { return side == BookSide::Bid ? a > b : a < b; }
#endif

}  // namespace

L3Book::L3Book(const Config& cfg)
    : orders_(cfg.max_orders),
      levels_(cfg.max_levels),
      index_(cfg.max_orders),
      books_(kLocates) {}

Slot L3Book::find_level(Locate locate, BookSide side, Price4 price) const {
    const SideLevels& v = sides(locate, side);
#if defined(ITCH_BINARY_LEVEL_SEARCH) && ITCH_BINARY_LEVEL_SEARCH
    const std::size_t pos = binary_position(v, side, price);
    return pos < v.size() && v[pos].price == price ? v[pos].level : kNil;
#else
    for (auto it = v.rbegin(); it != v.rend(); ++it) {
        if (it->price == price) {
            return it->level;
        }
        if (better(side, price, it->price)) {
            break;  // walked past where `price` would be
        }
    }
    return kNil;
#endif
}

Slot L3Book::find_or_create_level(Locate locate, BookSide side, Price4 price) {
    SideLevels& v = sides(locate, side);
#if defined(ITCH_BINARY_LEVEL_SEARCH) && ITCH_BINARY_LEVEL_SEARCH
    const std::size_t pos = binary_position(v, side, price);
    if (pos < v.size() && v[pos].price == price) {
        return v[pos].level;
    }
#else
    std::size_t pos = v.size();
    while (pos > 0) {
        const LevelEntry& e = v[pos - 1];
        if (e.price == price) {
            return e.level;
        }
        if (better(side, price, e.price)) {
            break;
        }
        --pos;
    }
#endif
    if (levels_.full()) {
        return kNil;
    }
    // Allocate the vector entry before taking a pool slot. If insertion throws, neither
    // storage structure has changed and a later add can still use the full pool.
    const auto entry =
        v.insert(v.begin() + static_cast<std::ptrdiff_t>(pos), LevelEntry{price, kNil});
    const Slot l = levels_.acquire();
    levels_[l] = me::Level{price, 0, kNil, kNil, 0};
    entry->level = l;
    return l;
}

void L3Book::release_level(Locate locate, BookSide side, Price4 price) {
    SideLevels& v = sides(locate, side);
#if defined(ITCH_BINARY_LEVEL_SEARCH) && ITCH_BINARY_LEVEL_SEARCH
    const std::size_t pos = binary_position(v, side, price);
    if (pos < v.size() && v[pos].price == price) {
        levels_.release(v[pos].level);
        v.erase(v.begin() + static_cast<std::ptrdiff_t>(pos));
    }
#else
    for (std::size_t i = v.size(); i-- > 0;) {
        if (v[i].price == price) {
            levels_.release(v[i].level);
            v.erase(v.begin() + static_cast<std::ptrdiff_t>(i));
            return;
        }
    }
#endif
}

void L3Book::link(Slot s) {
    BookOrder& o = orders_[s];
    me::Level& l = levels_[o.level];
    o.prev = l.tail;
    o.next = kNil;
    if (l.tail == kNil) {
        l.head = s;
    } else {
        orders_[l.tail].next = s;
    }
    l.tail = s;
    l.total += o.shares;
    ++l.count;
}

void L3Book::unlink(Slot s) {
    BookOrder& o = orders_[s];
    me::Level& l = levels_[o.level];
    if (o.prev == kNil) {
        l.head = o.next;
    } else {
        orders_[o.prev].next = o.next;
    }
    if (o.next == kNil) {
        l.tail = o.prev;
    } else {
        orders_[o.next].prev = o.prev;
    }
    l.total -= o.shares;
    if (--l.count == 0) {
        release_level(o.locate, o.side, o.price);
    }
}

bool L3Book::add(Locate locate, Ref ref, BookSide side, Shares shares, Price4 price) {
    if (ref == 0) {
        ++anomalies_.unknown_ref;  // 0 marks an empty index entry and never appears in ITCH
        return false;
    }
    if (index_.find(ref) != kNil) {
        ++anomalies_.duplicate_ref;
        return false;
    }
    if (orders_.full()) {
        ++anomalies_.capacity;
        return false;
    }
    const Slot s = orders_.acquire();
    Slot l = kNil;
    bool indexed = false;
    try {
        // The standard index allocates a node here. Nothing has been linked yet;
        // either index or level-vector allocation can fail without leaving an order.
        index_.insert(ref, s);
        indexed = true;
        l = find_or_create_level(locate, side, price);
    } catch (...) {
        if (indexed) index_.erase(ref);
        orders_.release(s);
        throw;
    }
    if (l == kNil) {
        index_.erase(ref);
        orders_.release(s);
        ++anomalies_.capacity;
        return false;
    }
    orders_[s] = BookOrder{ref, shares, price, l, kNil, kNil, locate, side};
    link(s);
    peak_orders_ = std::max<std::size_t>(peak_orders_, orders_.live());
    return true;
}

void L3Book::reduce(Slot s, Shares shares) {
    BookOrder& o = orders_[s];
    if (shares < o.shares) {
        o.shares -= shares;
        levels_[o.level].total -= shares;
        return;
    }
    if (shares > o.shares) {
        ++anomalies_.share_underflow;
    }
    unlink(s);
    index_.erase(o.ref);
    orders_.release(s);
}

bool L3Book::execute(Ref ref, Shares shares) {
    const Slot s = index_.find(ref);
    if (s == kNil) {
        ++anomalies_.unknown_ref;
        return false;
    }
    reduce(s, shares);
    return true;
}

bool L3Book::cancel(Ref ref, Shares shares) { return execute(ref, shares); }

bool L3Book::remove(Ref ref) {
    const Slot s = index_.find(ref);
    if (s == kNil) {
        ++anomalies_.unknown_ref;
        return false;
    }
    unlink(s);
    index_.erase(ref);
    orders_.release(s);
    return true;
}

bool L3Book::replace(Ref old_ref, Ref new_ref, Shares shares, Price4 price) {
    const Slot s = index_.find(old_ref);
    if (s == kNil) {
        ++anomalies_.unknown_ref;
        return false;
    }
    if (new_ref == 0) {
        ++anomalies_.unknown_ref;
        return false;
    }
    if (new_ref != old_ref && index_.find(new_ref) != kNil) {
        ++anomalies_.duplicate_ref;
        return false;
    }
    const Locate locate = orders_[s].locate;
    const BookSide side = orders_[s].side;
    bool reserved_level = false;
    if (find_level(locate, side, price) == kNil) {
        if (levels_.full()) {
            if (levels_[orders_[s].level].count != 1) {
                ++anomalies_.capacity;
                return false;
            }
            // Removing this order frees its level. Its vector keeps its allocation,
            // so inserting the replacement afterwards cannot allocate or fail.
        } else {
            // Reserve the destination before changing the old order: vector allocation
            // can throw, and a failed replacement must preserve the old FIFO position.
            find_or_create_level(locate, side, price);
            reserved_level = true;
        }
    }
    if constexpr (kUsesStdReferenceIndex) {
        if (new_ref != old_ref) {
            try {
                // Keep the old mapping/FIFO until all throwing work has succeeded.
                // Only the standard index needs this extra transient mapping. A flat
                // table sized for one order must retain an empty probe sentinel.
                index_.insert(new_ref, s);
            } catch (...) {
                if (reserved_level) release_level(locate, side, price);
                throw;
            }
        }
    }
    // The order slot is reused (as with the previous remove/add implementation).
    // Any missing destination is already reserved, or removing the single old order
    // frees a level and leaves sufficient vector capacity for its replacement.
    unlink(s);
    if (new_ref != old_ref) {
        index_.erase(old_ref);
        if constexpr (!kUsesStdReferenceIndex) index_.insert(new_ref, s);
    }
    const Slot destination = find_or_create_level(locate, side, price);
    orders_[s] = BookOrder{new_ref, shares, price, destination, kNil, kNil, locate, side};
    link(s);
    return true;
}

const BookOrder* L3Book::find(Ref ref) const {
    const Slot s = index_.find(ref);
    return s == kNil ? nullptr : &orders_[s];
}

std::optional<Quote> L3Book::best(Locate locate, BookSide side) const {
    const SideLevels& v = sides(locate, side);
    if (v.empty()) {
        return std::nullopt;
    }
    const me::Level& l = levels_[v.back().level];
    return Quote{v.back().price, l.total, l.count};
}

std::size_t L3Book::level_count(Locate locate, BookSide side) const {
    return sides(locate, side).size();
}

}  // namespace itch
