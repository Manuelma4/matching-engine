#include "itch/queue_sim.hpp"

#include <algorithm>
#include <limits>
#include <queue>
#include <stdexcept>
#include <tuple>

namespace itch::queue {
namespace {

Time later(Time time, Time delay) {
    if (delay > std::numeric_limits<Time>::max() - time)
        throw std::overflow_error("simulator clock addition overflow");
    return time + delay;
}

bool passive(const Config& c, std::uint32_t opposite) {
    return opposite != 0 && (c.side == Side::Buy ? c.price4 < opposite : c.price4 > opposite);
}

void validate(std::span<const MarketEvent> events, const Config& c) {
    if ((c.side != Side::Buy && c.side != Side::Sell) ||
        (c.cancel_model != CancelModel::Optimistic && c.cancel_model != CancelModel::Conservative))
        throw std::invalid_argument("invalid simulator enum");
    if (c.price4 == 0 || c.price4 > kValueLimit || c.quantity == 0 || c.quantity > kValueLimit ||
        c.fee4 < -static_cast<std::int32_t>(kValueLimit) ||
        c.fee4 > static_cast<std::int32_t>(kValueLimit))
        throw std::invalid_argument("price, quantity or fee outside bounded simulator range");
    if (c.decision_ns > c.horizon_ns ||
        (c.cancel_ns && (*c.cancel_ns < c.decision_ns || *c.cancel_ns > c.horizon_ns)))
        throw std::invalid_argument("decision/cancel times outside ordered simulation horizon");
    if (events.empty() || events.size() > kMaxMarketEvents || events.front().kind != MarketKind::Seed)
        throw std::invalid_argument("trace needs one initial seed and at most 100000 market rows");
    // Check all possible derived clocks, including responses that would remain
    // pending at the horizon, before running any event.
    (void)later(later(c.decision_ns, c.order_delay_ns), c.response_delay_ns);
    if (c.cancel_ns) (void)later(later(*c.cancel_ns, c.order_delay_ns), c.response_delay_ns);
    std::uint32_t visible = 0;
    std::uint32_t opposite = 0;
    Time previous = 0;
    for (std::size_t i = 0; i < events.size(); ++i) {
        const auto& e = events[i];
        if (e.timestamp_ns > c.horizon_ns || (i != 0 && e.timestamp_ns < previous))
            throw std::invalid_argument("market times must be non-decreasing and within horizon");
        previous = e.timestamp_ns;
        (void)later(e.timestamp_ns, c.feed_delay_ns);
        (void)later(e.timestamp_ns, c.response_delay_ns);
        if (e.quantity > kValueLimit || e.opposite_price4 > kValueLimit)
            throw std::invalid_argument("market value outside bounded simulator range");
        switch (e.kind) {
        case MarketKind::Seed:
            if (i != 0) throw std::invalid_argument("seed may appear only as the first market row");
            visible = e.quantity;
            opposite = e.opposite_price4;
            break;
        case MarketKind::Add:
            if (e.quantity == 0 || e.opposite_price4 != 0 || e.quantity > kValueLimit - visible)
                throw std::invalid_argument("invalid add quantity or unused price field");
            visible += e.quantity;
            break;
        case MarketKind::Cancel:
        case MarketKind::Trade:
            if (e.quantity == 0 || e.opposite_price4 != 0 || e.quantity > visible)
                throw std::invalid_argument("reduction exceeds external quantity or has unused price");
            visible -= e.quantity;
            break;
        case MarketKind::Quote:
            if (e.quantity != 0) throw std::invalid_argument("quote must have zero quantity");
            opposite = e.opposite_price4;
            break;
        default:
            throw std::invalid_argument("invalid market event kind");
        }
        if (visible != 0 && opposite != 0 && !passive(c, opposite))
            throw std::invalid_argument("external fixed level crosses its opposite quote");
    }
}

enum class Kind {
    Market, Feed, Decision, CancelDecision, Arrival, CancelArrival,
    Accept, Reject, Fill, Cancelled, CancelReject
};

struct Scheduled {
    Time time{};
    unsigned phase{};
    std::uint64_t serial{};
    Kind kind{};
    std::size_t source{};
    Time origin{};
    std::uint32_t quantity{};
    std::uint32_t visible{};
    std::uint32_t opposite{};
};

struct After {
    bool operator()(const Scheduled& a, const Scheduled& b) const {
        return std::tie(a.time, a.phase, a.serial) > std::tie(b.time, b.phase, b.serial);
    }
};

std::string_view market_name(MarketKind value, bool feed) {
    switch (value) {
    case MarketKind::Seed: return feed ? "feed_seed" : "market_seed";
    case MarketKind::Add: return feed ? "feed_add" : "market_add";
    case MarketKind::Cancel: return feed ? "feed_cancel" : "market_cancel";
    case MarketKind::Trade: return feed ? "feed_trade" : "market_trade";
    case MarketKind::Quote: return feed ? "feed_quote" : "market_quote";
    }
    throw std::logic_error("unreachable market kind");
}

void fill_account(Account& account, std::uint32_t quantity, const Config& c) {
    const std::int64_t sign = c.side == Side::Buy ? 1 : -1;
    const std::int64_t amount = quantity;
    // Bounds and one-order cumulative-fill conservation in simulate keep every
    // product and sum within int64, including twice-money midpoint marks.
    account.filled += quantity;
    account.position += sign * amount;
    account.fees4 += static_cast<std::int64_t>(c.fee4) * amount;
    account.cash4 += (-sign * static_cast<std::int64_t>(c.price4) - c.fee4) * amount;
}

} // namespace

std::string_view name(Side value) {
    switch (value) { case Side::Buy: return "buy"; case Side::Sell: return "sell"; }
    throw std::invalid_argument("invalid side");
}
std::string_view name(CancelModel value) {
    switch (value) { case CancelModel::Optimistic: return "optimistic";
                    case CancelModel::Conservative: return "conservative"; }
    throw std::invalid_argument("invalid cancellation model");
}
std::string_view name(MarketKind value) {
    switch (value) {
    case MarketKind::Seed: return "seed";
    case MarketKind::Add: return "add";
    case MarketKind::Cancel: return "cancel";
    case MarketKind::Trade: return "trade";
    case MarketKind::Quote: return "quote";
    }
    throw std::invalid_argument("invalid market event kind");
}
std::string_view name(OrderState value) {
    switch (value) {
    case OrderState::Idle: return "idle";
    case OrderState::Pending: return "pending";
    case OrderState::Live: return "live";
    case OrderState::Filled: return "filled";
    case OrderState::Cancelled: return "cancelled";
    case OrderState::Rejected: return "rejected";
    }
    throw std::invalid_argument("invalid order state");
}

Result simulate(std::span<const MarketEvent> events, const Config& c) {
    validate(events, c);
    std::priority_queue<Scheduled, std::vector<Scheduled>, After> pending;
    std::uint64_t serial = 0;
    auto schedule = [&](Time time, unsigned phase, Kind kind, std::size_t source,
                        Time origin, std::uint32_t quantity = 0,
                        std::uint32_t visible = 0, std::uint32_t opposite = 0) {
        pending.push({time, phase, serial++, kind, source, origin, quantity, visible, opposite});
    };
    for (std::size_t i = 0; i < events.size(); ++i)
        schedule(events[i].timestamp_ns, 1, Kind::Market, i + 1, events[i].timestamp_ns, events[i].quantity);
    schedule(c.decision_ns, 3, Kind::Decision, 0, c.decision_ns, c.quantity);
    if (c.cancel_ns) schedule(*c.cancel_ns, 3, Kind::CancelDecision, 0, *c.cancel_ns);

    Result result;
    result.trace.reserve(3 * events.size() + 8);
    std::uint32_t visible = 0, opposite = 0;
    std::uint32_t observed_visible = 0, observed_opposite = 0;
    bool observed = false;
    Time observed_time = 0;
    auto response = [&](const Scheduled& parent, Kind kind, std::uint32_t quantity = 0) {
        schedule(later(parent.time, c.response_delay_ns), 5, kind,
                 parent.source, parent.time, quantity);
    };
    while (!pending.empty() && pending.top().time <= c.horizon_ns) {
        const Scheduled e = pending.top();
        pending.pop();
        std::string_view label;
        switch (e.kind) {
        case Kind::Market: {
            const auto& market = events[e.source - 1];
            label = market_name(market.kind, false);
            switch (market.kind) {
            case MarketKind::Seed:
                visible = market.quantity;
                opposite = market.opposite_price4;
                break;
            case MarketKind::Add:
                visible += market.quantity; // all later external arrivals are behind us
                break;
            case MarketKind::Cancel:
                if (result.exchange_state == OrderState::Live) {
                    const auto reduction = c.cancel_model == CancelModel::Optimistic
                        ? std::min(result.ahead, market.quantity)
                        : market.quantity - std::min(market.quantity, visible - result.ahead);
                    result.ahead -= reduction;
                }
                visible -= market.quantity;
                break;
            case MarketKind::Trade:
                if (result.exchange_state == OrderState::Live) {
                    const auto passed = market.quantity - std::min(market.quantity, result.ahead);
                    const auto fill = std::min(result.remaining, passed);
                    result.ahead -= std::min(result.ahead, market.quantity);
                    if (fill != 0) {
                        result.remaining -= fill;
                        fill_account(result.exchange, fill, c);
                        if (result.remaining == 0) {
                            result.exchange_state = OrderState::Filled;
                            result.ahead = 0;
                        }
                        response(e, Kind::Fill, fill);
                    }
                }
                // Historical displayed flow is depleted exactly once. The shadow
                // fill does not remove another fill shares from external history.
                visible -= market.quantity;
                break;
            case MarketKind::Quote:
                opposite = market.opposite_price4;
                break;
            }
            schedule(later(e.time, c.feed_delay_ns), 2, Kind::Feed, e.source,
                     e.time, market.quantity, visible, opposite);
            break;
        }
        case Kind::Feed:
            label = market_name(events[e.source - 1].kind, true);
            observed = true;
            observed_time = e.origin;
            observed_visible = e.visible;
            observed_opposite = e.opposite;
            break;
        case Kind::Decision:
            if (!observed || observed_visible == 0 || !passive(c, observed_opposite)) {
                label = "decision_skip";
            } else {
                label = "submit";
                result.submitted = true;
                result.local_state = OrderState::Pending;
                result.known_remaining = c.quantity;
                schedule(later(e.time, c.order_delay_ns), 4, Kind::Arrival, 0, e.time, c.quantity);
            }
            break;
        case Kind::CancelDecision:
            if (result.local_state != OrderState::Live || result.known_remaining == 0) {
                label = "cancel_skip";
            } else {
                label = "cancel_request";
                result.cancel_requested = true;
                schedule(later(e.time, c.order_delay_ns), 4, Kind::CancelArrival, 0, e.time);
            }
            break;
        case Kind::Arrival:
            if (!passive(c, opposite)) {
                label = "arrival_reject";
                result.exchange_state = OrderState::Rejected;
                response(e, Kind::Reject);
            } else {
                label = "arrival_accept";
                result.exchange_state = OrderState::Live;
                result.remaining = c.quantity;
                result.ahead = visible;
                response(e, Kind::Accept, c.quantity);
            }
            break;
        case Kind::CancelArrival:
            if (result.exchange_state == OrderState::Live) {
                label = "arrival_cancel";
                response(e, Kind::Cancelled, result.remaining);
                result.remaining = 0;
                result.ahead = 0;
                result.exchange_state = OrderState::Cancelled;
            } else {
                label = "arrival_cancel_reject";
                response(e, Kind::CancelReject);
            }
            break;
        case Kind::Accept:
            label = "response_accept";
            result.local_state = OrderState::Live;
            break;
        case Kind::Reject:
            label = "response_reject";
            result.local_state = OrderState::Rejected;
            result.known_remaining = 0;
            break;
        case Kind::Fill:
            label = "response_fill";
            result.known_remaining -= e.quantity;
            fill_account(result.local, e.quantity, c);
            if (result.known_remaining == 0) result.local_state = OrderState::Filled;
            break;
        case Kind::Cancelled:
            label = "response_cancel";
            result.known_remaining = 0;
            result.local_state = OrderState::Cancelled;
            break;
        case Kind::CancelReject:
            label = "response_cancel_reject";
            break;
        }
        result.trace.push_back({e.time, e.origin, e.phase, e.serial, label, e.source, e.quantity,
            visible, opposite, result.ahead, result.remaining, result.exchange_state, result.exchange,
            observed, observed_time, observed_visible, observed_opposite,
            result.known_remaining, result.local_state, result.local});
    }
    result.pending_events = pending.size();
    if (observed && observed_visible != 0 && passive(c, observed_opposite))
        result.local_marked_equity_twice4 = 2 * result.local.cash4 + result.local.position *
            (static_cast<std::int64_t>(c.price4) + observed_opposite);
    return result;
}

} // namespace itch::queue
