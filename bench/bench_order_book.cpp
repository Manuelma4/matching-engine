// Latency benchmark: replays a deterministic stream of add/cancel/market orders and
// reports per-operation latency percentiles. Always build in Release.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <random>
#include <vector>

#include "me/order_book.hpp"

using namespace me;
using Clock = std::chrono::steady_clock;

namespace {

enum class OpType : std::uint8_t { Limit, Market, Cancel };

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
    std::uniform_int_distribution<int> side(0, 1);
    std::uniform_int_distribution<Price> offset(0, 50);
    std::uniform_int_distribution<Quantity> qty(1, 100);
    constexpr Price mid = 10'000;

    std::vector<Op> ops;
    ops.reserve(n);
    OrderId next_id = 1;
    for (std::size_t i = 0; i < n; ++i) {
        const int k = kind(rng);
        const Side s = side(rng) == 0 ? Side::Buy : Side::Sell;
        if (k < 60 || next_id == 1) {
            // Buys mostly below mid, sells mostly above, with some overlap so trades happen.
            const Price p = s == Side::Buy ? mid + 5 - offset(rng) : mid - 5 + offset(rng);
            ops.push_back({OpType::Limit, s, next_id++, p, qty(rng)});
        } else if (k < 70) {
            ops.push_back({OpType::Market, s, next_id++, 0, qty(rng)});
        } else {
            // Target a random earlier id; it may already be filled, like in real flow.
            std::uniform_int_distribution<OrderId> target(1, next_id - 1);
            ops.push_back({OpType::Cancel, s, target(rng), 0, 0});
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
    // part of what you see here; see README exercise on cycle counters.
    {
        OrderBook book;
        std::vector<std::int64_t> latencies;
        latencies.reserve(n);
        for (const auto& op : ops) {
            trades.clear();
            const auto t0 = Clock::now();
            apply(book, op, trades);
            const auto t1 = Clock::now();
            latencies.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count());
        }
        std::sort(latencies.begin(), latencies.end());
        std::printf("latency ns : p50=%lld p90=%lld p99=%lld p99.9=%lld max=%lld\n",
                    static_cast<long long>(percentile(latencies, 0.50)),
                    static_cast<long long>(percentile(latencies, 0.90)),
                    static_cast<long long>(percentile(latencies, 0.99)),
                    static_cast<long long>(percentile(latencies, 0.999)),
                    static_cast<long long>(latencies.back()));
    }
    return 0;
}
