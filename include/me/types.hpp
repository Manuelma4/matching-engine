#pragma once

#include <cstdint>
#include <stdexcept>

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

    // The distance is computed unsigned: exact once price >= band_low, and free of the
    // signed overflow a negative band_low would otherwise cause.
    [[nodiscard]] constexpr bool in_band(Price price) const {
        return price >= band_low &&
               static_cast<std::uint64_t>(price) - static_cast<std::uint64_t>(band_low) <
                   (std::uint64_t{1} << band_log2);
    }
};

// Throws std::invalid_argument unless 1 <= max_orders <= 2^32 - 2 (slot 2^32 - 1 is the
// null slot) and band_log2 <= 62.
inline const BookConfig& validate(const BookConfig& cfg) {
    if (cfg.max_orders == 0 || cfg.max_orders == 0xFFFF'FFFFu) {
        throw std::invalid_argument("BookConfig: max_orders must be in [1, 2^32 - 2]");
    }
    if (cfg.band_log2 > 62) {
        throw std::invalid_argument("BookConfig: band_log2 must be at most 62");
    }
    return cfg;
}

}  // namespace me
