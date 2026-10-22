#pragma once

#include <unordered_map>

#include "me/core.hpp"

namespace me {

// Order-id lookup: find(id), insert(id, slot), erase(id).
//
//   StdIndex  std::unordered_map: one heap node per resting order.

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

}  // namespace me
