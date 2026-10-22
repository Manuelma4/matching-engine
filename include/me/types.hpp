#pragma once

#include <cstdint>

namespace me {

using OrderId = std::uint64_t;
// Prices are integer ticks, never floating point: 101.25 with a 0.01 tick is 10125.
using Price = std::int64_t;
using Quantity = std::uint64_t;

enum class Side : std::uint8_t { Buy, Sell };

[[nodiscard]] constexpr Side opposite(Side side) {
    return side == Side::Buy ? Side::Sell : Side::Buy;
}

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
    InvalidId,         // order id 0 is reserved
    PriceOutOfBand,    // outside [band_low, band_low + 2^band_log2)
    CapacityExceeded,  // the preallocated order pool is full
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

// Every book variant is sized once from this and never allocates on the hot path.
// The price band acts as an engine price collar: limit orders and modifies outside it
// are rejected. It bounds the price ladder and keeps all variants semantically equal.
struct BookConfig {
    std::uint32_t max_orders = 1u << 20;
    Price band_low = 1;
    std::uint8_t band_log2 = 16;

    [[nodiscard]] constexpr bool in_band(Price price) const {
        return price >= band_low && price - band_low < (Price{1} << band_log2);
    }
};

}  // namespace me
