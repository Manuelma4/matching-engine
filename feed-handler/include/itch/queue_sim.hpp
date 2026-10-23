#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string_view>
#include <vector>

namespace itch::queue {

// A deliberately bounded, synthetic, single-level shadow model. These events are
// observations of external liquidity; our hypothetical order never edits them.
using Time = std::uint64_t;
constexpr std::uint32_t kValueLimit = 1'000'000'000;
constexpr std::size_t kMaxMarketEvents = 100'000;
enum class Side { Buy, Sell };
enum class CancelModel { Optimistic, Conservative };
enum class MarketKind { Seed, Add, Cancel, Trade, Quote };
enum class OrderState { Idle, Pending, Live, Filled, Cancelled, Rejected };

struct MarketEvent {
    Time timestamp_ns{};
    MarketKind kind{};
    std::uint32_t quantity{};
    std::uint32_t opposite_price4{}; // zero means no displayed opposite quote
};

struct Config {
    Side side{Side::Buy};
    CancelModel cancel_model{CancelModel::Conservative};
    std::uint32_t price4{};
    std::uint32_t quantity{};
    std::int32_t fee4{}; // signed Price(4) per filled share; negative is a rebate
    Time decision_ns{};
    std::optional<Time> cancel_ns;
    Time horizon_ns{};
    Time feed_delay_ns{};
    Time order_delay_ns{};
    Time response_delay_ns{};
};

struct Account {
    std::uint32_t filled{};
    std::int64_t position{};
    std::int64_t cash4{};
    std::int64_t fees4{};
    bool operator==(const Account&) const = default;
};

struct TraceRow {
    Time time_ns{};
    Time origin_ns{};
    unsigned phase{};
    std::uint64_t serial{};
    std::string_view event;
    std::size_t source_index{}; // one-based market row, or zero for strategy actions
    std::uint32_t event_quantity{};
    std::uint32_t external_quantity{};
    std::uint32_t opposite_price4{};
    std::uint32_t ahead{};
    std::uint32_t remaining{};
    OrderState exchange_state{OrderState::Idle};
    Account exchange;
    bool observed{};
    Time observed_timestamp_ns{};
    std::uint32_t observed_quantity{};
    std::uint32_t observed_opposite_price4{};
    std::uint32_t known_remaining{};
    OrderState local_state{OrderState::Idle};
    Account local;
};

struct Result {
    std::vector<TraceRow> trace;
    Account exchange;
    Account local;
    OrderState exchange_state{OrderState::Idle};
    OrderState local_state{OrderState::Idle};
    std::uint32_t remaining{};
    std::uint32_t known_remaining{};
    std::uint32_t ahead{};
    std::size_t pending_events{};
    bool submitted{};
    bool cancel_requested{};
    // Twice Price(4) money, using only the final delivered external BBO. This is
    // a mark, not realised P&L or an executable liquidation value.
    std::optional<std::int64_t> local_marked_equity_twice4;
};

std::string_view name(Side value);
std::string_view name(CancelModel value);
std::string_view name(MarketKind value);
std::string_view name(OrderState value);

// Throws std::invalid_argument on an invalid trace/configuration and
// std::overflow_error on a clock addition overflow. No partial result is returned.
// Equal-time phases: market, feed, decisions, arrivals, responses. Every generated
// zero-delay child has a later phase than its parent; no response triggers a decision.
Result simulate(std::span<const MarketEvent> events, const Config& config);

} // namespace itch::queue
