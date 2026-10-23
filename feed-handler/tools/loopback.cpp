// itch_loopback: the matching engine publishes an ITCH 5.0 feed and this library rebuilds
// it. Each benchmark regime of the engine becomes one stock. After every engine operation
// the encoded messages are decoded into an L3 replica, and the replica's best bid and ask
// (price, size, order count) must equal the engine's; at the end the full books must match
// order by order. With --out the feed is written as a BinaryFILE for itch_replay.
//
//   itch_loopback [--ops N] [--seed N] [--out day.itch]
//
// Mapping from engine events to ITCH messages:
//   trade against a resting order  E (order executed) on the resting order
//   limit order rests              A (add order) with a new reference
//   cancel                         D (order delete)
//   modify, smaller size           X (order cancel) for the difference
//   modify, larger size            U (order replace): new reference, back of the queue
//   modify, new price, no trade    U
//   modify, new price, trades      D, then E for each trade, then A for any remainder
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <unordered_map>
#include <vector>

#include "itch/encode.hpp"
#include "itch/replay.hpp"
#include "me/book.hpp"
#include "workloads.hpp"

namespace {

using itch::BookSide;
using itch::Locate;
using itch::Price4;
using itch::Ref;
using itch::Shares;

constexpr std::uint64_t kMarketOpen = 34'200'000'000'000ull;  // 09:30:00 in ns since midnight

Price4 to_price4(me::Price ticks) { return static_cast<Price4>(ticks * 100); }  // $0.01 tick
me::Price to_ticks(Price4 price) { return static_cast<me::Price>(price / 100); }
BookSide to_side(me::Side side) { return side == me::Side::Buy ? BookSide::Bid : BookSide::Ask; }
me::Side to_side(BookSide side) { return side == BookSide::Bid ? me::Side::Buy : me::Side::Sell; }

struct Published {
    Ref ref;
    BookSide side;
    Price4 price;
    Shares shares;
};

struct Venue {
    Locate locate;
    std::string symbol;
    std::unique_ptr<me::OrderBook> book;
    std::vector<bench::Op> ops;
    std::unordered_map<me::OrderId, Published> resting;  // engine id -> order on the feed
};

class Publisher {
public:
    explicit Publisher(itch::Writer& out) : out_(out) {}

    void publish(Venue& v, const bench::Op& op, std::uint64_t ts, std::vector<me::Trade>& trades) {
        // The pre-operation state of a modified order decides which messages describe it.
        std::optional<Published> before;
        if (op.type == bench::OpType::Modify) {
            if (auto it = v.resting.find(op.id); it != v.resting.end()) {
                before = it->second;
            }
        }

        trades.clear();
        me::ExecutionReport report{op.id};
        bool cancelled = false;
        switch (op.type) {
            case bench::OpType::Limit:
                report = v.book->add_limit(op.id, op.side, op.price, op.qty, trades);
                break;
            case bench::OpType::Market:
                report = v.book->add_market(op.id, op.side, op.qty, trades);
                break;
            case bench::OpType::Modify:
                report = v.book->modify(op.id, op.price, op.qty, trades);
                break;
            case bench::OpType::Cancel:
                cancelled = v.book->cancel(op.id);
                break;
        }

        if (op.type == bench::OpType::Cancel) {
            if (cancelled) {
                out_.remove(v.locate, ts, v.resting.at(op.id).ref);
                v.resting.erase(op.id);
            }
            return;
        }
        if (!report.accepted()) {
            return;
        }

        const bool repriced =
            op.type == bench::OpType::Modify && before && before->price != to_price4(op.price);
        if (op.type == bench::OpType::Modify && !repriced) {
            Published& p = v.resting.at(op.id);
            const auto qty = static_cast<Shares>(op.qty);
            if (qty < p.shares) {
                out_.cancel(v.locate, ts, p.ref, p.shares - qty);
            } else if (qty > p.shares) {
                const Ref ref = next_ref_++;
                out_.replace(v.locate, ts, p.ref, ref, qty, p.price);
                p.ref = ref;
            }
            p.shares = qty;
            return;
        }
        if (repriced && trades.empty()) {
            Published& p = v.resting.at(op.id);
            const Ref ref = next_ref_++;
            out_.replace(v.locate, ts, p.ref, ref, static_cast<Shares>(report.resting),
                         to_price4(op.price));
            p = Published{ref, p.side, to_price4(op.price), static_cast<Shares>(report.resting)};
            return;
        }
        if (repriced) {
            out_.remove(v.locate, ts, before->ref);
            v.resting.erase(op.id);
        }
        for (const me::Trade& t : trades) {
            const me::OrderId passive = t.aggressor == me::Side::Buy ? t.sell_id : t.buy_id;
            Published& p = v.resting.at(passive);
            out_.executed(v.locate, ts, p.ref, static_cast<Shares>(t.qty), next_match_++);
            p.shares -= static_cast<Shares>(t.qty);
            if (p.shares == 0) {
                v.resting.erase(passive);
            }
        }
        if (report.resting > 0) {
            const Ref ref = next_ref_++;
            const Published p{ref, to_side(op.side), to_price4(op.price),
                              static_cast<Shares>(report.resting)};
            out_.add(v.locate, ts, ref, p.side, p.shares, v.symbol, p.price);
            v.resting[op.id] = p;
        }
    }

private:
    itch::Writer& out_;
    Ref next_ref_ = 1;
    std::uint64_t next_match_ = 1;
};

// Best price, total size and order count at the touch.
std::optional<itch::Quote> engine_touch(const me::OrderBook& book, me::Side side) {
    const auto price = side == me::Side::Buy ? book.best_bid() : book.best_ask();
    if (!price) {
        return std::nullopt;
    }
    std::uint32_t orders = 0;
    book.for_each_order(side, *price, [&](me::OrderId, me::Quantity) { ++orders; });
    return itch::Quote{to_price4(*price), book.volume_at(side, *price), orders};
}

// Compares every resting order of one stock, in priority order.
bool books_match(const Venue& v, const itch::L3Book& replica) {
    for (BookSide side : {BookSide::Bid, BookSide::Ask}) {
        if (replica.level_count(v.locate, side) != v.book->level_count(to_side(side))) {
            return false;
        }
        std::vector<std::pair<Ref, Shares>> expected;
        std::vector<std::pair<Ref, Shares>> actual;
        Price4 last = 0;
        bool first = true;
        replica.visit(v.locate, side, [&](Price4 price, Ref ref, Shares shares) {
            actual.emplace_back(ref, shares);
            if (first || price != last) {
                v.book->for_each_order(to_side(side), to_ticks(price), [&](me::OrderId id, me::Quantity q) {
                    expected.emplace_back(v.resting.at(id).ref, static_cast<Shares>(q));
                });
                last = price;
                first = false;
            }
        });
        if (expected != actual) {
            return false;
        }
    }
    return true;
}

}  // namespace

int main(int argc, char** argv) {
    std::size_t ops_per_venue = 1'000'000;
    std::uint64_t seed = 42;
    std::string out_path;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg = argv[i];
        if (arg == "--ops" && i + 1 < argc) {
            ops_per_venue = std::strtoull(argv[++i], nullptr, 10);
        } else if (arg == "--seed" && i + 1 < argc) {
            seed = std::strtoull(argv[++i], nullptr, 10);
        } else if (arg == "--out" && i + 1 < argc) {
            out_path = argv[++i];
        } else {
            std::fprintf(stderr, "usage: itch_loopback [--ops N] [--seed N] [--out file]\n");
            return 2;
        }
    }

    const me::BookConfig engine_cfg{1u << 19, 1, 16};
    const char* symbols[] = {"FMID", "RWLK", "DEEP", "FLSH", "MMKR"};
    std::vector<Venue> venues;
    for (std::size_t i = 0; i < bench::kRegimes.size(); ++i) {
        venues.push_back(Venue{static_cast<Locate>(i + 1), symbols[i],
                               std::make_unique<me::OrderBook>(engine_cfg),
                               bench::generate(bench::kRegimes[i], seed, ops_per_venue), {}});
    }

    itch::Writer writer;
    std::uint64_t ts = kMarketOpen - 1'000'000'000;
    writer.system_event(ts, 'O');
    for (const Venue& v : venues) {
        writer.stock_directory(v.locate, ts, v.symbol);
    }
    writer.system_event(ts, 'S');
    writer.system_event(kMarketOpen, 'Q');

    auto replica = std::make_unique<itch::BookBuilder>(itch::L3Book::Config{1u << 21, 1u << 20});
    std::size_t fed = 0;
    const auto feed_new_bytes = [&] {
        const auto& bytes = writer.bytes();
        fed += itch::walk_frames(itch::Bytes(bytes.data() + fed, bytes.size() - fed),
                                 [&](itch::Bytes m) { itch::dispatch(m, *replica); });
    };
    feed_new_bytes();

    Publisher publisher(writer);
    std::vector<me::Trade> trades;
    trades.reserve(1 << 16);
    std::uint64_t checks = 0;
    const auto start = std::chrono::steady_clock::now();
    for (std::size_t i = 0; i < ops_per_venue; ++i) {
        for (Venue& v : venues) {
            ts += 1'000;
            publisher.publish(v, v.ops[i], ts, trades);
            feed_new_bytes();
            for (me::Side side : {me::Side::Buy, me::Side::Sell}) {
                ++checks;
                const auto engine = engine_touch(*v.book, side);
                const auto feed = replica->book().best(v.locate, to_side(side));
                if (engine != feed) {
                    std::fprintf(stderr,
                                 "MISMATCH %s op %zu side %s: engine %u/%llu/%u feed %u/%llu/%u\n",
                                 v.symbol.c_str(), i, side == me::Side::Buy ? "bid" : "ask",
                                 engine ? engine->price : 0,
                                 static_cast<unsigned long long>(engine ? engine->shares : 0),
                                 engine ? engine->orders : 0, feed ? feed->price : 0,
                                 static_cast<unsigned long long>(feed ? feed->shares : 0),
                                 feed ? feed->orders : 0);
                    return 1;
                }
            }
        }
    }
    writer.system_event(ts + 1'000, 'M');
    writer.system_event(ts + 2'000, 'E');
    writer.system_event(ts + 3'000, 'C');
    writer.end_of_session();
    feed_new_bytes();
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

    bool full_match = true;
    for (const Venue& v : venues) {
        const bool ok = books_match(v, replica->book());
        std::printf("%-5s %8zu resting orders, %4zu bid / %4zu ask levels: %s\n", v.symbol.c_str(),
                    v.book->order_count(), v.book->level_count(me::Side::Buy),
                    v.book->level_count(me::Side::Sell), ok ? "identical" : "DIFFERENT");
        full_match = full_match && ok;
    }
    const itch::Anomalies& a = replica->book().anomalies();
    const bool clean = a.unknown_ref == 0 && a.duplicate_ref == 0 && a.share_underflow == 0 &&
                       a.capacity == 0;
    std::printf("\nengine operations  %zu (%zu per stock, seed %llu)\n",
                ops_per_venue * venues.size(), ops_per_venue,
                static_cast<unsigned long long>(seed));
    std::printf("feed               %zu bytes, %.2f s to publish and rebuild\n",
                writer.bytes().size(), seconds);
    std::printf("touch comparisons  %llu, all equal\n", static_cast<unsigned long long>(checks));
    std::printf("full books         %s\n", full_match ? "identical" : "DIFFERENT");
    std::printf("replica anomalies  %s\n", clean ? "none" : "PRESENT");
    std::printf("book hash          %016llx\n",
                static_cast<unsigned long long>(replica->book_hash()));

    if (!out_path.empty()) {
        std::FILE* f = std::fopen(out_path.c_str(), "wb");
        if (f == nullptr ||
            std::fwrite(writer.bytes().data(), 1, writer.bytes().size(), f) != writer.bytes().size()) {
            std::fprintf(stderr, "itch_loopback: cannot write %s\n", out_path.c_str());
            return 1;
        }
        std::fclose(f);
        std::printf("written            %s\n", out_path.c_str());
    }
    return full_match && clean ? 0 : 1;
}
