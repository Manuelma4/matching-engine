#pragma once

#include <cstdint>

namespace me {

using OrderId = std::uint64_t;
// Prices are integer ticks, never floating point: 101.25 with a 0.01 tick is 10125.
using Price = std::int64_t;
using Quantity = std::uint64_t;

enum class Side : std::uint8_t { Buy, Sell };

struct Trade {
    OrderId buy_id;
    OrderId sell_id;
    Price price;  // always the resting order's price
    Quantity qty;
    Side aggressor;
};

enum class RejectReason : std::uint8_t {
    None,
    InvalidQuantity,
    InvalidPrice,
    DuplicateId,
    UnknownOrder,
};

// filled + resting + cancelled == the quantity sent with the request
// (qty for add_limit / add_market, new_qty for modify).
struct ExecutionReport {
    OrderId id;
    Quantity filled = 0;
    Quantity resting = 0;
    Quantity cancelled = 0;
    RejectReason reject = RejectReason::None;

    [[nodiscard]] bool accepted() const { return reject == RejectReason::None; }
};

}  // namespace me
