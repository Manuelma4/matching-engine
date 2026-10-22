#include "workloads.hpp"

#include <algorithm>
#include <utility>

#include "rng.hpp"

namespace bench {

namespace {

using me::OrderId;
using me::Price;
using me::Quantity;
using me::Side;

constexpr Price kMidLow = 2'000;
constexpr Price kMidHigh = 60'000;

Price clamp_mid(Price mid) { return std::clamp(mid, kMidLow, kMidHigh); }

Side random_side(Rng& rng) { return rng.percent(50) ? Side::Buy : Side::Sell; }

Quantity random_qty(Rng& rng, std::int64_t lo, std::int64_t hi) {
    return static_cast<Quantity>(rng.between(lo, hi));
}

// Records every limit order so modifies and cancels can target earlier ones. Some
// targets will already be filled or cancelled, as in real flow.
class Flow {
public:
    struct LimitRef {
        OrderId id;
        Side side;
        Price price;
    };

    Flow(std::uint64_t seed, std::size_t n) : rng_(seed) {
        ops_.reserve(n);
        limits_.reserve(n);
    }

    Rng& rng() { return rng_; }
    [[nodiscard]] std::size_t size() const { return ops_.size(); }
    [[nodiscard]] bool has_limits() const { return !limits_.empty(); }
    std::vector<Op> take() { return std::move(ops_); }

    void limit(Side side, Price price, Quantity qty) {
        ops_.push_back({OpType::Limit, side, next_id_, price, qty});
        limits_.push_back({next_id_, side, price});
        ++next_id_;
    }

    void market(Side side, Quantity qty) {
        ops_.push_back({OpType::Market, side, next_id_++, 0, qty});
    }

    // Picks one of the `window` most recent limit orders (0 = any of them).
    LimitRef& pick(std::size_t window = 0) {
        const std::size_t n = limits_.size();
        const std::size_t span = window == 0 || window > n ? n : window;
        return limits_[n - 1 - rng_.below(span)];
    }

    void modify(LimitRef& target, Price price, Quantity qty) {
        target.price = price;
        ops_.push_back({OpType::Modify, target.side, target.id, price, qty});
    }

    void cancel(const LimitRef& target) {
        ops_.push_back({OpType::Cancel, target.side, target.id, 0, 0});
    }

private:
    Rng rng_;
    std::vector<Op> ops_;
    std::vector<LimitRef> limits_;
    OrderId next_id_ = 1;
};

// Buys at or below mid + 5 and sells at or above mid - 5, so the two sides overlap a
// little and orders trade on arrival.
Price overlapping_quote(Rng& rng, Side side, Price mid, Price depth) {
    return side == Side::Buy ? mid + 5 - rng.between(0, depth) : mid - 5 + rng.between(0, depth);
}

// 55% limit, 10% market, 10% modify (half keep the price), 25% cancel.
void mixed_step(Flow& flow, Price mid) {
    Rng& rng = flow.rng();
    const std::uint64_t k = rng.below(100);
    const Side side = random_side(rng);
    if (k < 55 || !flow.has_limits()) {
        flow.limit(side, overlapping_quote(rng, side, mid, 50), random_qty(rng, 1, 100));
    } else if (k < 65) {
        flow.market(side, random_qty(rng, 1, 100));
    } else if (k < 75) {
        auto& target = flow.pick();
        const Price price =
            rng.percent(50) ? target.price : overlapping_quote(rng, target.side, mid, 50);
        flow.modify(target, price, random_qty(rng, 1, 100));
    } else {
        flow.cancel(flow.pick());
    }
}

Price random_walk(Rng& rng, Price mid, std::uint64_t move_percent) {
    if (rng.percent(move_percent)) {
        mid += rng.percent(50) ? 1 : -1;
    }
    return clamp_mid(mid);
}

void fixed_mid(Flow& flow, std::size_t n) {
    while (flow.size() < n) {
        mixed_step(flow, 10'000);
    }
}

void random_walk_regime(Flow& flow, std::size_t n) {
    Price mid = 10'000;
    while (flow.size() < n) {
        mid = random_walk(flow.rng(), mid, 20);
        mixed_step(flow, mid);
    }
}

void deep_book(Flow& flow, std::size_t n) {
    constexpr Price mid = 10'000;
    constexpr Price depth = 1'000;
    Rng& rng = flow.rng();

    // Build phase: `per_level` orders on each of 1,000 levels per side, never crossing.
    const std::size_t per_level = std::max<std::size_t>(1, n / 10'000);
    for (std::size_t i = 0; i < per_level && flow.size() < n; ++i) {
        for (Price k = 1; k <= depth && flow.size() + 1 < n; ++k) {
            flow.limit(Side::Buy, mid - k, random_qty(rng, 1, 100));
            flow.limit(Side::Sell, mid + k, random_qty(rng, 1, 100));
        }
    }

    // Steady phase: passive adds and re-prices anywhere in the depth, cancels, and market
    // orders large enough to take out a level or more.
    const auto passive = [&](Side side) {
        const Price k = rng.between(1, depth);
        return side == Side::Buy ? mid - k : mid + k;
    };
    while (flow.size() < n) {
        const std::uint64_t k = rng.below(100);
        const Side side = random_side(rng);
        if (k < 40 || !flow.has_limits()) {
            flow.limit(side, passive(side), random_qty(rng, 1, 100));
        } else if (k < 45) {
            flow.market(side, random_qty(rng, 200, 5'000));
        } else if (k < 60) {
            auto& target = flow.pick();
            const Price price = rng.percent(50) ? target.price : passive(target.side);
            flow.modify(target, price, random_qty(rng, 1, 100));
        } else {
            flow.cancel(flow.pick());
        }
    }
}

void flash_crash(Flow& flow, std::size_t n) {
    constexpr std::size_t period = 200'000;
    constexpr std::size_t crash_start = 100'000;
    constexpr std::size_t crash_len = 2'000;  // the mid falls 3,000 ticks, then recovers
    Rng& rng = flow.rng();
    Price mid = 30'000;
    while (flow.size() < n) {
        const std::size_t phase = flow.size() % period;
        const bool crashing = phase >= crash_start && phase < crash_start + crash_len;
        const bool recovering =
            phase >= crash_start + crash_len && phase < crash_start + 2 * crash_len;
        if (crashing || recovering) {
            const Price step = phase % 2 == 0 ? 2 : 1;
            mid = clamp_mid(crashing ? mid - step : mid + step);
            if (rng.percent(50)) {
                flow.market(crashing ? Side::Sell : Side::Buy, random_qty(rng, 100, 1'000));
                continue;
            }
        } else {
            mid = random_walk(rng, mid, 20);
        }
        mixed_step(flow, mid);
    }
}

void cancel_heavy(Flow& flow, std::size_t n) {
    Rng& rng = flow.rng();
    Price mid = 10'000;
    // Quotes sit at the touch or up to 5 ticks behind it, with a spread of at least 1.
    const auto quote = [&](Side side) {
        const Price k = rng.between(0, 5);
        return side == Side::Buy ? mid - k : mid + 1 + k;
    };
    while (flow.size() < n) {
        mid = random_walk(rng, mid, 5);
        const std::uint64_t k = rng.below(100);
        const Side side = random_side(rng);
        if (k < 30 || !flow.has_limits()) {
            flow.limit(side, quote(side), random_qty(rng, 1, 100));
        } else if (k < 35) {
            flow.market(side, random_qty(rng, 1, 200));
        } else if (k < 40) {
            auto& target = flow.pick(2'000);
            flow.modify(target, rng.percent(80) ? target.price : quote(target.side),
                        random_qty(rng, 1, 100));
        } else {
            flow.cancel(flow.pick(2'000));
        }
    }
}

}  // namespace

const char* regime_name(Regime regime) {
    switch (regime) {
        case Regime::FixedMid:
            return "fixed-mid";
        case Regime::RandomWalk:
            return "random-walk";
        case Regime::DeepBook:
            return "deep-book";
        case Regime::FlashCrash:
            return "flash-crash";
        case Regime::CancelHeavy:
            return "cancel-heavy";
    }
    return "?";
}

std::optional<Regime> parse_regime(std::string_view name) {
    for (Regime regime : kRegimes) {
        if (name == regime_name(regime)) {
            return regime;
        }
    }
    return std::nullopt;
}

std::vector<Op> generate(Regime regime, std::uint64_t seed, std::size_t n) {
    Flow flow(seed, n);
    switch (regime) {
        case Regime::FixedMid:
            fixed_mid(flow, n);
            break;
        case Regime::RandomWalk:
            random_walk_regime(flow, n);
            break;
        case Regime::DeepBook:
            deep_book(flow, n);
            break;
        case Regime::FlashCrash:
            flash_crash(flow, n);
            break;
        case Regime::CancelHeavy:
            cancel_heavy(flow, n);
            break;
    }
    return flow.take();
}

}  // namespace bench
