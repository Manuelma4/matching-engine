// Direct C++ API example: a fictional four-order book, two U messages encoded with the
// project's own writer, the identified history they produce and what a strategy could
// know at each probe under two delivery horizons. Reads no file.
#include "itch/encode.hpp"
#include "itch/identified_observer.hpp"

#include <algorithm>
#include <iostream>
#include <stdexcept>
#include <string_view>

namespace {

namespace id = itch::identified;
using itch::BookSide;

constexpr itch::Locate kLocate = 7;

// One U record with its 2-byte length prefix. The writer leaves tracking at zero.
id::Occurrence replace(id::SourceCut cut, itch::Ref old_ref, itch::Ref new_ref,
                       itch::Shares shares, itch::Price4 price) {
    itch::Writer w;
    w.replace(kLocate, cut.timestamp_ns, old_ref, new_ref, shares, price);
    id::Occurrence o{cut, 0, {}};
    std::copy_n(w.bytes().begin(), id::kFrameBytes, o.frame.begin());
    return o;
}

id::Input example() {
    const id::SourceCut seed{10, 400, 414, 7, 12, 'S'};
    const id::SourceCut u1{11, 414, 451, 12, 35, 'U'};
    const id::SourceCut u2{13, 492, 529, 12, 35, 'U'};
    return id::Input{
        .source_identity = {1000, std::string(64, 'a'), std::nullopt},
        .seed = {"TEST", kLocate, seed, 10,
                 {{1, BookSide::Bid, 10000, 10},
                  {11, BookSide::Ask, 10010, 30},
                  {12, BookSide::Ask, 10010, 40},
                  {13, BookSide::Ask, 10020, 25}}},
        .occurrences = {replace(u1, 11, 21, 60, 10010), replace(u2, 21, 22, 35, 10020)},
        .expected_sources = {seed, u1, u2},
        .limits = {16, 4, 64, 8},  // narrow: the book reserves max_orders slots
    };
}

void print_order(const id::Order& o) {
    std::cout << (o.side == BookSide::Bid ? 'B' : 'S') << o.reference << '@' << o.price4
              << '/' << o.shares;
}

void print_history(const id::History& h) {
    std::cout << "verification=" << h.verification() << '\n';
    for (const id::Fact& f : h.facts()) {
        std::cout << "fact seq=" << f.source.sequence << " t=" << f.source.timestamp_ns << " ";
        print_order(f.before_order);
        std::cout << " -> ";
        print_order(f.after_order);
        std::cout << " rank_before=" << f.fifo_rank_before
                  << " shares_ahead_before=" << f.visible_shares_ahead_before << '\n';
    }
    for (std::size_t i = 0; i < h.snapshots().size(); ++i) {
        const id::Snapshot& s = h.snapshots()[i];
        std::cout << "snapshot " << i << " origin=" << s.origin_ns << ":";
        for (const id::Order& o : s.orders) {
            std::cout << ' ';
            print_order(o);
        }
        std::cout << '\n';
    }
}

void print_observation(const id::History& h, id::ObservationConfig cfg) {
    const id::Observation o = id::observe(h, cfg);
    std::cout << "delay=" << cfg.delay_ns << " horizon=" << cfg.horizon_ns << ':';
    for (std::size_t i = 0; i < cfg.probes.size(); ++i) {
        std::cout << " t" << cfg.probes[i] << '=';
        if (o.snapshot_at[i]) {
            std::cout << *o.snapshot_at[i];
        } else {
            std::cout << "none";
        }
    }
    std::cout << " pending=" << o.pending.size() << '\n';
}

}  // namespace

int main() {
    const id::History history = id::build_history(example());
    print_history(history);
    print_observation(history, {5, 17, {10, 14, 15, 16, 17}});
    print_observation(history, {5, 16, {10, 14, 15, 16}});

    // Reusing the reference retired by the first replacement is refused as a whole.
    id::Input reuse = example();
    reuse.occurrences[1] = replace(reuse.occurrences[1].source, 21, 11, 35, 10020);
    try {
        (void)id::build_history(reuse);
        std::cout << "reuse: admitted\n";
    } catch (const std::invalid_argument& e) {
        std::cout << "reuse: refused (" << e.what() << ")\n";
    }
    return 0;
}
