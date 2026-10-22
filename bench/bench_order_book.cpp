// Latency benchmark: replays a deterministic stream of limit, market, modify and cancel
// operations and reports throughput plus latency percentiles per operation type.
// Always build in Release.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

#include "me/order_book.hpp"

using namespace me;
using Clock = std::chrono::steady_clock;

namespace {

enum class OpType : std::uint8_t { Limit, Market, Modify, Cancel };
constexpr std::array<const char*, 4> op_names{"limit", "market", "modify", "cancel"};

struct Op {
    OpType type;
    Side side;
    OrderId id;
    Price price;
    Quantity qty;
};

std::vector<Op> generate(std::size_t n, std::uint64_t seed) {
    std::mt19937_64 rng(seed);
    std::uniform_int_distribution<int> kind(0, 99);
    std::uniform_int_distribution<int> coin(0, 1);
    std::uniform_int_distribution<Price> offset(0, 50);
    std::uniform_int_distribution<Quantity> qty(1, 100);
    constexpr Price mid = 10'000;

    // Buys mostly below mid, sells mostly above, with some overlap so trades happen.
    const auto limit_price = [&](Side s) {
        return s == Side::Buy ? mid + 5 - offset(rng) : mid - 5 + offset(rng);
    };

    // Every limit order generated so far, with the last price sent for it. Modifies and
    // cancels target these; some will already be filled or cancelled, as in real flow.
    struct LimitRef {
        OrderId id;
        Side side;
        Price price;
    };
    std::vector<LimitRef> limits;
    limits.reserve(n);

    std::vector<Op> ops;
    ops.reserve(n);
    OrderId next_id = 1;
    for (std::size_t i = 0; i < n; ++i) {
        const int k = kind(rng);
        const Side s = coin(rng) == 0 ? Side::Buy : Side::Sell;
        if (k < 55 || limits.empty()) {
            const Price p = limit_price(s);
            ops.push_back({OpType::Limit, s, next_id, p, qty(rng)});
            limits.push_back({next_id, s, p});
            ++next_id;
        } else if (k < 65) {
            ops.push_back({OpType::Market, s, next_id++, 0, qty(rng)});
        } else {
            std::uniform_int_distribution<std::size_t> pick(0, limits.size() - 1);
            LimitRef& target = limits[pick(rng)];
            if (k < 75) {
                // Half the modifies keep the price and only change size, so the in-place
                // and splice paths are exercised as much as the price-change path.
                if (coin(rng) == 0) {
                    target.price = limit_price(target.side);
                }
                ops.push_back({OpType::Modify, target.side, target.id, target.price, qty(rng)});
            } else {
                ops.push_back({OpType::Cancel, target.side, target.id, 0, 0});
            }
        }
    }
    return ops;
}

void apply(OrderBook& book, const Op& op, std::vector<Trade>& trades) {
    switch (op.type) {
        case OpType::Limit:
            book.add_limit(op.id, op.side, op.price, op.qty, trades);
            break;
        case OpType::Market:
            book.add_market(op.id, op.side, op.qty, trades);
            break;
        case OpType::Modify:
            book.modify(op.id, op.price, op.qty, trades);
            break;
        case OpType::Cancel:
            book.cancel(op.id);
            break;
    }
}

std::int64_t percentile(const std::vector<std::int64_t>& sorted, double p) {
    const auto idx = static_cast<std::size_t>(p * static_cast<double>(sorted.size() - 1));
    return sorted[idx];
}

}  // namespace

int main() {
    constexpr std::size_t n = 1'000'000;
    const auto ops = generate(n, 42);
    std::vector<Trade> trades;
    trades.reserve(1024);

    // Pass 1: throughput, no per-op timing overhead.
    {
        OrderBook book;
        const auto start = Clock::now();
        for (const auto& op : ops) {
            trades.clear();
            apply(book, op, trades);
        }
        const auto elapsed = std::chrono::duration<double>(Clock::now() - start).count();
        std::printf("throughput : %.2f M ops/s (%zu ops in %.3f s)\n",
                    static_cast<double>(n) / elapsed / 1e6, n, elapsed);
        std::printf("final book : %zu orders, %zu bid levels, %zu ask levels\n",
                    book.order_count(), book.level_count(Side::Buy),
                    book.level_count(Side::Sell));
    }

    // Pass 2: per-op latency. steady_clock::now() itself costs ~20-40 ns, which is
    // included in these numbers (cycle-counter timing is on the roadmap).
    {
        OrderBook book;
        std::vector<std::int64_t> all;
        all.reserve(n);
        std::array<std::vector<std::int64_t>, op_names.size()> by_type;
        for (const auto& op : ops) {
            trades.clear();
            const auto t0 = Clock::now();
            apply(book, op, trades);
            const auto t1 = Clock::now();
            const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
            all.push_back(ns);
            by_type[static_cast<std::size_t>(op.type)].push_back(ns);
        }

        const auto print_row = [](const char* name, std::vector<std::int64_t>& v) {
            std::sort(v.begin(), v.end());
            std::printf("  %-7s %8zu %6lld %6lld %6lld %7lld\n", name, v.size(),
                        static_cast<long long>(percentile(v, 0.50)),
                        static_cast<long long>(percentile(v, 0.90)),
                        static_cast<long long>(percentile(v, 0.99)),
                        static_cast<long long>(percentile(v, 0.999)));
        };
        std::printf("latency ns:\n  %-7s %8s %6s %6s %6s %7s\n", "op", "count", "p50", "p90",
                    "p99", "p99.9");
        print_row("all", all);
        for (std::size_t t = 0; t < by_type.size(); ++t) {
            print_row(op_names[t], by_type[t]);
        }
        std::printf("  max %lld ns (OS noise; not tracked)\n", static_cast<long long>(all.back()));
    }
    return 0;
}
