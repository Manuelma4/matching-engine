// Captures real U windows from a Nasdaq ITCH 5.0 BinaryFILE and runs the identified
// observer on them.
//
//   itch_identified_capture INPUT INPUT_SHA256 REQUESTS_CSV DELAY_NS
//                           CHECKPOINTS_CSV SNAPSHOTS_CSV SUMMARY_JSON
//
// REQUESTS_CSV: request_id,symbol,from_ns,min_run,max_facts[,need] (ids 1, 2, ... in
// order; need is `any`, `queued_same_price` or `queued_same_price_overtaken`, and `any`
// when the column is absent). For each request the tool takes the first maximal run,
// starting at or after from_ns, of the symbol's own messages that are all U, of length
// >= min_run (at most max_facts of it). With queued_same_price, the taken U must include
// one that keeps its price and whose old order had a displayed order ahead of it; with
// queued_same_price_overtaken, that old order must also have had a displayed order
// behind it. A run without such a U is skipped whole.
// The seed is the symbol's complete displayed book after the global message just
// before the first U. The SHA-256 is declared by the caller and never verified here.
//
// Outputs: post-message checkpoints for every captured state, the states themselves as
// state_id,side,price4,fifo_rank,reference,shares rows, and a JSON summary with facts
// and one delayed observation per request. The file is read once, front to back.
#include "itch/framing.hpp"
#include "itch/identified_observer.hpp"
#include "itch/messages.hpp"
#include "itch/replay.hpp"

#include <algorithm>
#include <charconv>
#include <filesystem>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace {

namespace id = itch::identified;
using U64 = std::uint64_t;

enum class Need { Any, QueuedSamePrice, QueuedSamePriceOvertaken };

const char* need_name(Need n) {
    return n == Need::QueuedSamePrice ? "queued_same_price" : "queued_same_price_overtaken";
}

struct Request {
    U64 id{};
    std::string symbol;
    U64 from_ns{};
    U64 min_run{};
    U64 max_facts{};
    Need need = Need::Any;

    std::optional<itch::Locate> locate;
    bool in_run = false;
    bool qualifies = false;  // the run so far holds a queued same-price U
    bool skipping = false;   // inside the rest of a run that was taken and rejected
    bool done = false;
    id::SourceCut seed_cut;
    std::vector<id::Order> seed;
    std::vector<id::Occurrence> run;
};

void need(bool ok, const char* why) {
    if (!ok) throw std::runtime_error(why);
}

U64 number(std::string_view s) {
    U64 v = 0;
    const auto r = std::from_chars(s.data(), s.data() + s.size(), v);
    need(!s.empty() && r.ec == std::errc{} && r.ptr == s.data() + s.size() && (s == "0" || s[0] != '0'),
         "invalid unsigned integer in requests");
    return v;
}

std::vector<std::string> split(const std::string& line) {
    std::vector<std::string> f;
    std::stringstream ss(line);
    for (std::string x; std::getline(ss, x, ',');) f.push_back(x);
    return f;
}

std::vector<Request> read_requests(const std::string& path) {
    std::ifstream in(path);
    need(static_cast<bool>(in), "cannot open requests");
    std::string line;
    need(static_cast<bool>(std::getline(in, line)), "requests header");
    const bool with_need = line == "request_id,symbol,from_ns,min_run,max_facts,need";
    need(with_need || line == "request_id,symbol,from_ns,min_run,max_facts", "requests header");
    std::vector<Request> out;
    while (std::getline(in, line)) {
        const auto f = split(line);
        need(f.size() == (with_need ? 6u : 5u) && !f[1].empty() && f[1].size() <= 8, "invalid request line");
        Request r;
        r.id = number(f[0]);
        r.symbol = f[1];
        r.from_ns = number(f[2]);
        r.min_run = number(f[3]);
        r.max_facts = number(f[4]);
        if (with_need) {
            if (f[5] == "queued_same_price") {
                r.need = Need::QueuedSamePrice;
            } else if (f[5] == "queued_same_price_overtaken") {
                r.need = Need::QueuedSamePriceOvertaken;
            } else {
                need(f[5] == "any", "need must be any, queued_same_price or queued_same_price_overtaken");
            }
        }
        need(r.id == out.size() + 1, "request ids must be 1, 2, ...");
        need(r.min_run >= 1 && r.min_run <= r.max_facts && r.max_facts <= id::kHardMaxFacts, "invalid run bounds");
        out.push_back(std::move(r));
    }
    need(!out.empty() && out.size() <= 64, "1..64 requests");
    return out;
}

std::string trim(std::string_view s) {
    while (!s.empty() && s.back() == ' ') s.remove_suffix(1);
    return std::string(s);
}

std::vector<id::Order> capture(const itch::L3Book& book, itch::Locate locate) {
    std::vector<id::Order> rows;
    for (const itch::BookSide side : {itch::BookSide::Bid, itch::BookSide::Ask}) {
        book.visit(locate, side, [&](itch::Price4 price, itch::Ref ref, itch::Shares shares) {
            rows.push_back(id::Order{ref, side, price, shares, id::Attribution::Unknown});
        });
    }
    return rows;
}

std::string cut_json(const id::SourceCut& c) {
    std::ostringstream o;
    o << "{\"sequence\":" << c.sequence << ",\"frame_offset\":" << c.frame_offset
      << ",\"frame_end_offset\":" << c.frame_end_offset << ",\"timestamp_ns\":" << c.timestamp_ns
      << ",\"body_bytes\":" << c.body_bytes << ",\"type\":\"" << c.type << "\"}";
    return o.str();
}

std::string order_json(const id::Order& o) {
    std::ostringstream s;
    s << "{\"reference\":" << o.reference << ",\"side\":\"" << (o.side == itch::BookSide::Bid ? 'B' : 'S')
      << "\",\"price4\":" << o.price4 << ",\"shares\":" << o.shares << '}';
    return s.str();
}

// True when U keeps the old order's price and that order is not first in its queue
// (and, for the overtaken variant, not last either). Called on the book before the U.
bool queued_same_price(const itch::L3Book& book, const itch::OrderReplace& u, Need n) {
    const itch::BookOrder* old = book.find(u.old_ref());
    if (old == nullptr || old->price != u.price()) return false;
    bool ahead = false, found = false, behind = false;
    book.for_each_order(old->locate, old->side, old->price, [&](itch::Ref ref, itch::Shares) {
        if (found) behind = true;
        if (ref == old->ref) found = true;
        if (!found) ahead = true;
    });
    return found && ahead && (n != Need::QueuedSamePriceOvertaken || behind);
}

// A finished run becomes the request's capture; a short or unqualified one is discarded.
// A rejected run cut at max_facts is skipped up to the next non-U message.
void close_run(Request& r, bool cut_at_max) {
    if (r.in_run && r.run.size() >= r.min_run && (r.need == Need::Any || r.qualifies)) {
        r.done = true;
    } else {
        r.run.clear();
        r.seed.clear();
        r.skipping = cut_at_max;
    }
    r.in_run = false;
    r.qualifies = false;
}

struct Captured {
    const Request* request;
    id::History history;
    id::Observation observation;
    id::ObservationConfig config;
};

int run(int argc, char** argv) {
    need(argc == 8,
         "usage: itch_identified_capture INPUT INPUT_SHA256 REQUESTS_CSV DELAY_NS "
         "CHECKPOINTS_CSV SNAPSHOTS_CSV SUMMARY_JSON");
    const std::string input_path = argv[1];
    const std::string sha = argv[2];
    std::vector<Request> requests = read_requests(argv[3]);
    const U64 delay = number(argv[4]);

    const U64 input_bytes = std::filesystem::file_size(input_path);
    std::unique_ptr<std::FILE, int (*)(std::FILE*)> file(std::fopen(input_path.c_str(), "rb"), &std::fclose);
    need(file != nullptr, "cannot open input");

    // Full-day capacities, as for the existing replay tools.
    auto builder = std::make_unique<itch::BookBuilder>(itch::L3Book::Config{1u << 22, 1u << 21});
    U64 sequence = 0, offset = 0, previous_ts = 0;
    id::SourceCut previous{};
    bool all_done = false;
    std::size_t open = requests.size();
    U64 bad_frames = 0;

    struct Stop {};
    try {
        itch::walk_stream(file.get(), [&](itch::Bytes body) {
            if (body.empty()) throw Stop{};  // end-of-session record
            const unsigned char* p = body.data();
            const std::uint8_t expected = itch::kMessageLength[p[0]];
            if (expected == 0 || body.size() != expected) {
                ++bad_frames;
                throw std::runtime_error("unknown type or wrong message length");
            }
            const itch::Header h{p};
            need(sequence == 0 || h.timestamp() >= previous_ts, "timestamp regression");
            const id::SourceCut cut{++sequence, offset, offset + 2 + body.size(), h.timestamp(),
                                    static_cast<std::uint16_t>(body.size()), h.type()};

            if (h.type() == 'R') {
                const std::string symbol = trim(itch::StockDirectory{p}.stock());
                for (Request& r : requests) {
                    if (r.symbol == symbol) {
                        need(!r.locate || *r.locate == h.locate(), "directory remaps a requested symbol");
                        r.locate = h.locate();
                    }
                }
            }
            for (Request& r : requests) {
                if (r.done || !r.locate || h.locate() != *r.locate || h.type() == 'S') continue;
                if (h.type() == 'U' && h.timestamp() >= r.from_ns) {
                    if (r.skipping) continue;
                    if (!r.in_run) {
                        r.in_run = true;
                        r.seed_cut = previous;
                        r.seed = capture(builder->book(), *r.locate);
                    }
                    id::Occurrence o{cut, h.tracking(), {}};
                    itch::store_be16(o.frame.data(), static_cast<std::uint16_t>(body.size()));
                    std::copy(body.begin(), body.end(), o.frame.begin() + 2);
                    r.run.push_back(o);
                    if (r.need != Need::Any && queued_same_price(builder->book(), itch::OrderReplace{p}, r.need)) {
                        r.qualifies = true;
                    }
                    if (r.run.size() == r.max_facts) close_run(r, true);
                } else {
                    r.skipping = false;
                    if (r.in_run) close_run(r, false);
                }
                if (r.done) --open;
            }
            itch::dispatch(body, *builder);
            offset = cut.frame_end_offset;
            previous_ts = h.timestamp();
            previous = cut;
            if (open == 0) {
                all_done = true;
                throw Stop{};
            }
        });
    } catch (const Stop&) {
    }
    // A run still open at the end of the input closes there.
    for (Request& r : requests) {
        if (!r.done && r.in_run) {
            close_run(r, false);
            if (r.done) --open;
        }
    }

    const itch::Anomalies& an = builder->book().anomalies();
    const itch::DecodeAnomalies& dec = builder->invalid_messages();
    const U64 anomalies = an.unknown_ref + an.duplicate_ref + an.share_underflow + an.capacity +
                          dec.invalid_side + dec.locate_mismatch;
    builder.reset();  // release the full-day book before building histories

    std::vector<Captured> captured;
    for (const Request& r : requests) {
        if (!r.done) continue;
        id::Input in;
        in.source_identity = {input_bytes, sha, std::nullopt};
        in.seed = {r.symbol, *r.locate, r.seed_cut, r.seed_cut.timestamp_ns, r.seed};
        in.occurrences = r.run;
        in.expected_sources.push_back(r.seed_cut);
        for (const auto& o : r.run) in.expected_sources.push_back(o.source);
        const auto orders = static_cast<std::uint32_t>(std::max<std::size_t>(r.seed.size(), 1));
        const auto facts = static_cast<std::uint32_t>(r.run.size());
        in.limits = {orders, facts, static_cast<std::uint32_t>(r.seed.size() * (r.run.size() + 1)),
                     2 * (facts + 1)};
        id::History h = id::build_history(in);

        id::ObservationConfig cfg{delay, 0, {}};
        for (const id::Snapshot& s : h.snapshots()) {
            need(s.origin_ns <= std::numeric_limits<U64>::max() - delay, "delay overflows");
            cfg.probes.push_back(s.origin_ns);
            cfg.probes.push_back(s.origin_ns + delay);
        }
        std::sort(cfg.probes.begin(), cfg.probes.end());
        cfg.horizon_ns = cfg.probes.back();
        id::Observation o = id::observe(h, cfg);
        captured.push_back({&r, std::move(h), std::move(o), std::move(cfg)});
    }

    // Global post-message checkpoints, in source order, numbered 1, 2, ...
    struct Row {
        U64 sequence;
        const Captured* c;
        std::size_t snapshot;
    };
    std::vector<Row> order;
    for (const Captured& c : captured) {
        for (std::size_t i = 0; i < c.history.snapshots().size(); ++i) {
            order.push_back({c.history.snapshots()[i].source.sequence, &c, i});
        }
    }
    std::stable_sort(order.begin(), order.end(), [](const Row& a, const Row& b) { return a.sequence < b.sequence; });

    std::ofstream checkpoints(argv[5]), snapshots(argv[6]), summary(argv[7]);
    need(checkpoints && snapshots && summary, "cannot open outputs");
    checkpoints << "state_id,symbol,locate,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type\n";
    snapshots << "state_id,side,price4,fifo_rank,reference,shares\n";
    std::map<std::pair<const Captured*, std::size_t>, std::size_t> state_ids;
    for (std::size_t k = 0; k < order.size(); ++k) {
        const Row& row = order[k];
        const id::Snapshot& s = row.c->history.snapshots()[row.snapshot];
        const std::size_t state_id = k + 1;
        state_ids[{row.c, row.snapshot}] = state_id;
        const id::SourceCut& p = s.source;
        checkpoints << state_id << ',' << row.c->request->symbol << ',' << row.c->history.locate() << ','
                    << p.sequence << ',' << p.frame_offset << ',' << p.frame_end_offset << ','
                    << p.timestamp_ns << ',' << p.body_bytes << ',' << p.type << '\n';
        U64 rank = 0;
        const id::Order* prev = nullptr;
        for (const id::Order& o : s.orders) {
            rank = (prev && prev->side == o.side && prev->price4 == o.price4) ? rank + 1 : 1;
            prev = &o;
            snapshots << state_id << ',' << (o.side == itch::BookSide::Bid ? 'B' : 'S') << ',' << o.price4 << ','
                      << rank << ',' << o.reference << ',' << o.shares << '\n';
        }
    }

    summary << "{\"schema_version\":1,\"input_bytes\":" << input_bytes << ",\"declared_input_sha256\":\"" << sha
            << "\",\"scanned_messages\":" << sequence << ",\"consumed_prefix_bytes\":" << offset
            << ",\"stopped_after_all_requests\":" << (all_done ? "true" : "false")
            << ",\"book_anomalies\":" << anomalies << ",\"bad_frames\":" << bad_frames
            << ",\"delay_ns\":" << delay << ",\"requests\":[";
    for (std::size_t i = 0; i < requests.size(); ++i) {
        const Request& r = requests[i];
        if (i) summary << ',';
        summary << "{\"request_id\":" << r.id << ",\"symbol\":\"" << r.symbol << "\",\"from_ns\":" << r.from_ns
                << ",\"min_run\":" << r.min_run << ",\"max_facts\":" << r.max_facts;
        if (r.need != Need::Any) summary << ",\"need\":\"" << need_name(r.need) << '"';
        const auto c = std::find_if(captured.begin(), captured.end(), [&](const Captured& x) { return x.request == &r; });
        if (c == captured.end()) {
            summary << ",\"captured\":null}";
            continue;
        }
        const id::History& h = c->history;
        summary << ",\"locate\":" << h.locate() << ",\"verification\":\"" << h.verification()
                << "\",\"seed_orders\":" << h.snapshots().front().orders.size()
                << ",\"captured_rows\":" << h.captured_rows() << ",\"states\":[";
        for (std::size_t s = 0; s < h.snapshots().size(); ++s) {
            const id::Snapshot& snap = h.snapshots()[s];
            if (s) summary << ',';
            summary << "{\"state_id\":" << state_ids.at({&*c, s}) << ",\"event_index\":"
                    << (snap.event_index ? std::to_string(*snap.event_index) : "null")
                    << ",\"origin_ns\":" << snap.origin_ns << ",\"orders\":" << snap.orders.size()
                    << ",\"source\":" << cut_json(snap.source) << '}';
        }
        summary << "],\"facts\":[";
        for (std::size_t f = 0; f < h.facts().size(); ++f) {
            const id::Fact& x = h.facts()[f];
            if (f) summary << ',';
            summary << "{\"source\":" << cut_json(x.source) << ",\"tracking_number\":" << x.tracking_number
                    << ",\"before_order\":" << order_json(x.before_order)
                    << ",\"after_order\":" << order_json(x.after_order)
                    << ",\"fifo_rank_before\":" << x.fifo_rank_before
                    << ",\"visible_shares_ahead_before\":" << x.visible_shares_ahead_before << '}';
        }
        summary << "],\"observation\":{\"horizon_ns\":" << c->config.horizon_ns << ",\"probes\":[";
        for (std::size_t k = 0; k < c->config.probes.size(); ++k) {
            if (k) summary << ',';
            const auto& at = c->observation.snapshot_at[k];
            summary << "{\"t\":" << c->config.probes[k] << ",\"snapshot\":" << (at ? std::to_string(*at) : "null") << '}';
        }
        summary << "],\"pending\":" << c->observation.pending.size() << "}}";
    }
    summary << "]}\n";
    need(static_cast<bool>(checkpoints) && static_cast<bool>(snapshots) && static_cast<bool>(summary), "write failed");
    return anomalies == 0 ? 0 : 3;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        return run(argc, argv);
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_identified_capture: %s\n", e.what());
        return 1;
    }
}
