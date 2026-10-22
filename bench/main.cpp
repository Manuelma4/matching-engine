// me_bench: replays deterministic workloads through each book variant.
//
//   me_bench [--book NAME|all] [--regime NAME|all] [--seed N] [--ops N]
//            [--max-orders N] [--csv]
//
// Each (book, regime) pair runs three passes, each on a fresh book:
//   1. verification: hashes the full event stream (reports, trades, cancel results),
//      which must be identical for every variant;
//   2. throughput: one timer around the whole replay, no per-operation timing;
//   3. latency: steady_clock around each operation, percentiles per operation type.
// Always build in Release.
#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#if defined(__APPLE__)
#include <pthread/qos.h>
#endif

#include "me/book.hpp"
#include "me/book_v1.hpp"
#include "workloads.hpp"

using namespace bench;
using Clock = std::chrono::steady_clock;

namespace {

struct Percentiles {
    std::size_t count = 0;
    std::int64_t p50 = 0, p90 = 0, p99 = 0, p999 = 0, max = 0;
};

struct Result {
    std::uint64_t hash = 0;
    std::size_t peak_orders = 0;
    std::size_t final_orders = 0;
    double mops = 0;
    std::array<Percentiles, kOpTypes + 1> latency{};  // index kOpTypes = all operations
};

// FNV-1a over 64-bit words.
class EventHash {
public:
    void add(std::uint64_t word) {
        for (int i = 0; i < 8; ++i) {
            h_ ^= (word >> (8 * i)) & 0xFF;
            h_ *= 0x100000001B3ull;
        }
    }
    [[nodiscard]] std::uint64_t value() const { return h_; }

private:
    std::uint64_t h_ = 0xCBF29CE484222325ull;
};

template <class Book>
me::ExecutionReport apply(Book& book, const Op& op, std::vector<me::Trade>& trades) {
    switch (op.type) {
        case OpType::Limit:
            return book.add_limit(op.id, op.side, op.price, op.qty, trades);
        case OpType::Market:
            return book.add_market(op.id, op.side, op.qty, trades);
        case OpType::Modify:
            return book.modify(op.id, op.price, op.qty, trades);
        case OpType::Cancel:
            break;
    }
    me::ExecutionReport report{op.id};
    report.cancelled = book.cancel(op.id) ? 1 : 0;
    return report;
}

Percentiles summarise(std::vector<std::int64_t>& samples) {
    Percentiles p;
    p.count = samples.size();
    if (samples.empty()) {
        return p;
    }
    std::sort(samples.begin(), samples.end());
    const auto at = [&](double q) {
        return samples[static_cast<std::size_t>(q * static_cast<double>(samples.size() - 1))];
    };
    p.p50 = at(0.50);
    p.p90 = at(0.90);
    p.p99 = at(0.99);
    p.p999 = at(0.999);
    p.max = samples.back();
    return p;
}

template <class Book>
Result measure(const std::vector<Op>& ops, const me::BookConfig& cfg) {
    Result result;
    std::vector<me::Trade> trades;
    trades.reserve(1 << 16);

    {
        auto book = std::make_unique<Book>(cfg);
        EventHash hash;
        for (const Op& op : ops) {
            trades.clear();
            const me::ExecutionReport r = apply(*book, op, trades);
            hash.add(r.id);
            hash.add(r.filled);
            hash.add(r.resting);
            hash.add(r.cancelled);
            hash.add(static_cast<std::uint64_t>(r.reject));
            for (const me::Trade& t : trades) {
                hash.add(t.buy_id);
                hash.add(t.sell_id);
                hash.add(static_cast<std::uint64_t>(t.price));
                hash.add(t.qty);
                hash.add(static_cast<std::uint64_t>(t.aggressor));
            }
            result.peak_orders = std::max(result.peak_orders, book->order_count());
        }
        result.hash = hash.value();
        result.final_orders = book->order_count();
    }

    {
        auto book = std::make_unique<Book>(cfg);
        const auto start = Clock::now();
        for (const Op& op : ops) {
            trades.clear();
            apply(*book, op, trades);
        }
        const double seconds = std::chrono::duration<double>(Clock::now() - start).count();
        result.mops = static_cast<double>(ops.size()) / seconds / 1e6;
    }

    {
        auto book = std::make_unique<Book>(cfg);
        std::vector<std::int64_t> all;
        all.reserve(ops.size());
        std::array<std::vector<std::int64_t>, kOpTypes> by_type;
        for (const Op& op : ops) {
            trades.clear();
            const auto t0 = Clock::now();
            apply(*book, op, trades);
            const auto t1 = Clock::now();
            const auto ns = std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count();
            all.push_back(ns);
            by_type[static_cast<std::size_t>(op.type)].push_back(ns);
        }
        for (std::size_t t = 0; t < kOpTypes; ++t) {
            result.latency[t] = summarise(by_type[t]);
        }
        result.latency[kOpTypes] = summarise(all);
    }
    return result;
}

// Distribution of two back-to-back clock reads: the floor under every latency number.
Percentiles timer_floor(std::size_t n) {
    std::vector<std::int64_t> samples;
    samples.reserve(n);
    for (std::size_t i = 0; i < n; ++i) {
        const auto t0 = Clock::now();
        const auto t1 = Clock::now();
        samples.push_back(std::chrono::duration_cast<std::chrono::nanoseconds>(t1 - t0).count());
    }
    return summarise(samples);
}

struct Variant {
    const char* name;
    Result (*run)(const std::vector<Op>&, const me::BookConfig&);
};

constexpr std::array kVariants{
    Variant{"v1", &measure<me::BookV1>},
    Variant{"map", &measure<me::BookMap>},
    Variant{"map-oa", &measure<me::BookMapOA>},
    Variant{"vec", &measure<me::BookVec>},
    Variant{"ladder", &measure<me::BookLadder>},
};

struct Options {
    std::string book = "all";
    std::string regime = "all";
    std::uint64_t seed = 42;
    std::size_t ops = 1'000'000;
    std::uint32_t max_orders = me::BookConfig{}.max_orders;
    bool csv = false;
};

[[noreturn]] void usage() {
    std::fprintf(stderr,
                 "usage: me_bench [--book NAME|all] [--regime NAME|all] [--seed N] [--ops N] "
                 "[--max-orders N] [--csv]\n  books:");
    for (const Variant& v : kVariants) {
        std::fprintf(stderr, " %s", v.name);
    }
    std::fprintf(stderr, "\n  regimes:");
    for (Regime r : kRegimes) {
        std::fprintf(stderr, " %s", regime_name(r));
    }
    std::fprintf(stderr, "\n");
    std::exit(2);
}

Options parse(int argc, char** argv) {
    Options o;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg = argv[i];
        const auto value = [&]() -> const char* {
            if (i + 1 >= argc) {
                usage();
            }
            return argv[++i];
        };
        if (arg == "--book") {
            o.book = value();
        } else if (arg == "--regime") {
            o.regime = value();
        } else if (arg == "--seed") {
            o.seed = std::strtoull(value(), nullptr, 10);
        } else if (arg == "--ops") {
            o.ops = std::strtoull(value(), nullptr, 10);
        } else if (arg == "--max-orders") {
            const char* text = value();
            char* end = nullptr;
            const unsigned long long n = std::strtoull(text, &end, 10);
            if (end == text || *end != '\0' || n == 0 || n > 0xFFFF'FFFEull) {
                usage();
            }
            o.max_orders = static_cast<std::uint32_t>(n);
        } else if (arg == "--csv") {
            o.csv = true;
        } else {
            usage();
        }
    }
    return o;
}

void print_row(const char* name, const Percentiles& p) {
    std::printf("  %-7s %8zu %6lld %6lld %6lld %7lld %9lld\n", name, p.count,
                static_cast<long long>(p.p50), static_cast<long long>(p.p90),
                static_cast<long long>(p.p99), static_cast<long long>(p.p999),
                static_cast<long long>(p.max));
}

void print_csv_row(const Options& o, const char* book, const char* regime, const Result& r,
                   const char* op, const Percentiles& p) {
    std::printf("%s,%s,%llu,%zu,%016llx,%zu,%.3f,%s,%zu,%lld,%lld,%lld,%lld,%lld,%u\n", book,
                regime, static_cast<unsigned long long>(o.seed), o.ops,
                static_cast<unsigned long long>(r.hash), r.peak_orders, r.mops, op, p.count,
                static_cast<long long>(p.p50), static_cast<long long>(p.p90),
                static_cast<long long>(p.p99), static_cast<long long>(p.p999),
                static_cast<long long>(p.max), o.max_orders);
}

}  // namespace

int main(int argc, char** argv) {
#if defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    const Options o = parse(argc, argv);
    me::BookConfig cfg{};
    cfg.max_orders = o.max_orders;

    std::vector<const Variant*> variants;
    for (const Variant& v : kVariants) {
        if (o.book == "all" || o.book == v.name) {
            variants.push_back(&v);
        }
    }
    std::vector<Regime> regimes;
    for (Regime r : kRegimes) {
        if (o.regime == "all" || o.regime == regime_name(r)) {
            regimes.push_back(r);
        }
    }
    if (variants.empty() || regimes.empty()) {
        usage();
    }

    if (!o.csv) {
        const Percentiles floor = timer_floor(1'000'000);
        std::printf("timer floor (two back-to-back steady_clock reads), ns: p50=%lld p99=%lld\n",
                    static_cast<long long>(floor.p50), static_cast<long long>(floor.p99));
    }

    for (Regime regime : regimes) {
        const std::vector<Op> ops = generate(regime, o.seed, o.ops);
        for (const Variant* v : variants) {
            const Result r = v->run(ops, cfg);
            if (o.csv) {
                for (std::size_t t = 0; t < kOpTypes; ++t) {
                    print_csv_row(o, v->name, regime_name(regime), r, kOpNames[t], r.latency[t]);
                }
                print_csv_row(o, v->name, regime_name(regime), r, "all", r.latency[kOpTypes]);
                continue;
            }
            std::printf("\n[%s] %s: %.2f M ops/s, orders peak %zu / final %zu, hash %016llx\n",
                        regime_name(regime), v->name, r.mops, r.peak_orders, r.final_orders,
                        static_cast<unsigned long long>(r.hash));
            std::printf("  %-7s %8s %6s %6s %6s %7s %9s\n", "op", "count", "p50", "p90", "p99",
                        "p99.9", "max");
            print_row("all", r.latency[kOpTypes]);
            for (std::size_t t = 0; t < kOpTypes; ++t) {
                print_row(kOpNames[t], r.latency[t]);
            }
        }
    }
    return 0;
}
