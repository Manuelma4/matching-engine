#pragma once

#include <algorithm>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <unordered_map>
#include <vector>

#include "me/core.hpp"

namespace me {

// Order-id lookup: find(id), insert(id, slot), erase(id).
//
//   StdIndex       std::unordered_map: one heap node per resting order.
//   OpenAddrIndex  flat power-of-two table with linear probing, no per-order allocation.

class StdIndex {
public:
    explicit StdIndex(std::uint32_t max_orders) { map_.reserve(max_orders); }

    [[nodiscard]] Slot find(OrderId id) const {
        auto it = map_.find(id);
        return it == map_.end() ? kNil : it->second;
    }
    void insert(OrderId id, Slot s) { map_.emplace(id, s); }
    void erase(OrderId id) { map_.erase(id); }

private:
    std::unordered_map<OrderId, Slot> map_;
};

// 16-byte entries in a table of at least 2 * max_orders. The order pool bounds the live
// entries, so the load factor never exceeds 0.5 and the table never rehashes. Deletion
// shifts later entries of the probe run back into the hole instead of leaving tombstones,
// so cancel-heavy flow does not slowly degrade lookups. Key 0 marks an empty entry, which
// is why order id 0 is reserved.
class OpenAddrIndex {
public:
    explicit OpenAddrIndex(std::uint32_t max_orders)
        : mask_(std::bit_ceil(std::uint64_t{2} * std::max<std::uint32_t>(max_orders, 1)) - 1),
          table_(static_cast<std::size_t>(mask_ + 1)) {}

    [[nodiscard]] Slot find(OrderId id) const {
        for (std::uint64_t i = home(id);; i = next(i)) {
            const Entry& e = table_[i];
            if (e.key == kEmpty) {
                return kNil;
            }
            if (e.key == id) {
                return e.slot;
            }
        }
    }

    // `id` must not be present.
    void insert(OrderId id, Slot s) {
        std::uint64_t i = home(id);
        while (table_[i].key != kEmpty) {
            i = next(i);
        }
        table_[i] = Entry{id, s};
    }

    // `id` must be present.
    void erase(OrderId id) {
        std::uint64_t hole = home(id);
        while (table_[hole].key != id) {
            hole = next(hole);
        }
        // Backward-shift deletion: an entry further along the run moves into the hole if
        // the hole lies between its home bucket and its current position.
        for (std::uint64_t i = next(hole); table_[i].key != kEmpty; i = next(i)) {
            const std::uint64_t from_home = (i - home(table_[i].key)) & mask_;
            const std::uint64_t from_hole = (i - hole) & mask_;
            if (from_home >= from_hole) {
                table_[hole] = table_[i];
                hole = i;
            }
        }
        table_[hole] = Entry{};
    }

private:
    struct Entry {
        OrderId key = kEmpty;
        Slot slot = kNil;
    };
    static constexpr OrderId kEmpty = 0;

    // MurmurHash3 fmix64: spreads sequential ids across the table.
    [[nodiscard]] std::uint64_t home(OrderId id) const {
        std::uint64_t k = id;
        k ^= k >> 33;
        k *= 0xFF51AFD7ED558CCDull;
        k ^= k >> 33;
        k *= 0xC4CEB9FE1A85EC53ull;
        k ^= k >> 33;
        return k & mask_;
    }
    [[nodiscard]] std::uint64_t next(std::uint64_t i) const { return (i + 1) & mask_; }

    std::uint64_t mask_;
    std::vector<Entry> table_;
};

}  // namespace me
