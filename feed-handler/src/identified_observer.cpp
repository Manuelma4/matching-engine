#include "itch/identified_observer.hpp"

#include <algorithm>
#include <limits>
#include <stdexcept>
#include <unordered_set>
#include <utility>

#include "itch/endian.hpp"
#include "itch/messages.hpp"

namespace itch::identified {

namespace {

[[noreturn]] void invalid(const char* what) { throw std::invalid_argument(what); }
[[noreturn]] void too_long(const char* what) { throw std::length_error(what); }

bool is_lower_hex_sha256(std::string_view s) {
    return s.size() == 64 && std::all_of(s.begin(), s.end(), [](char c) {
               return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
           });
}

void check_limits(const Limits& l) {
    if (l.max_orders < 1 || l.max_orders > kHardMaxOrders) invalid("max_orders out of range");
    if (l.max_facts > kHardMaxFacts) invalid("max_facts out of range");
    if (l.max_captured_rows > kHardMaxCapturedRows) invalid("max_captured_rows out of range");
    if (l.max_probes < 1 || l.max_probes > kHardMaxProbes) invalid("max_probes out of range");
}

void check_identity(const SourceIdentity& id) {
    if (id.input_bytes == 0) invalid("declared input is empty");
    if (!is_lower_hex_sha256(id.input_sha256)) invalid("input SHA-256 is not 64 lower-case hex");
    if (id.evidence_sha256 && !is_lower_hex_sha256(*id.evidence_sha256)) {
        invalid("evidence SHA-256 is not 64 lower-case hex");
    }
}

// One cut on its own: a known type of the stated length, inside the declared input.
void check_cut(const SourceCut& c, std::uint64_t input_bytes) {
    if (c.sequence == 0) invalid("source sequence must be positive");
    const std::uint8_t expected = kMessageLength[static_cast<unsigned char>(c.type)];
    if (expected == 0 || c.body_bytes != expected) invalid("source type/length mismatch");
    if (c.timestamp_ns > kMaxWireTimestamp) invalid("source timestamp exceeds 48 bits");
    if (c.frame_offset > input_bytes || input_bytes - c.frame_offset < 2u + c.body_bytes ||
        c.frame_end_offset != c.frame_offset + 2u + c.body_bytes) {
        invalid("source span inconsistent with the declared input");
    }
}

// Seed then occurrences: increasing sequences, ordered spans that never overlap.
void check_sources(const Input& in) {
    std::vector<SourceCut> actual;
    actual.reserve(in.occurrences.size() + 1);
    actual.push_back(in.seed.source);
    for (const Occurrence& o : in.occurrences) actual.push_back(o.source);

    for (std::size_t i = 0; i < actual.size(); ++i) {
        check_cut(actual[i], in.source_identity.input_bytes);
        if (i > 0) {
            const SourceCut& prev = actual[i - 1];
            if (actual[i].sequence <= prev.sequence) invalid("source sequences not increasing");
            if (actual[i].frame_offset < prev.frame_end_offset) invalid("source spans overlap");
            if (actual[i].timestamp_ns < prev.timestamp_ns) invalid("source timestamps decrease");
        }
        if (i > 0 && actual[i].type != 'U') invalid("occurrence is not a U message");
    }
    if (actual != in.expected_sources) invalid("sources differ from the expected list");
}

void check_order_values(const Order& o) {
    if (o.reference == 0) invalid("zero order reference");
    if (o.shares == 0) invalid("zero shares");
    if (o.price4 == 0 || o.price4 > kMaxPrice4) invalid("price out of range");
    if (o.side != BookSide::Bid && o.side != BookSide::Ask) invalid("invalid side");
    if (o.attribution != Attribution::Unknown) invalid("seed attribution must be unknown");
}

// Bids before asks, best price first. Equal prices keep the caller's FIFO order.
void check_seed(const Seed& s) {
    if (s.symbol.empty() || s.symbol.size() > 8 ||
        !std::all_of(s.symbol.begin(), s.symbol.end(), [](char c) { return c > ' ' && c < 127; })) {
        invalid("symbol must be 1..8 printable characters");
    }
    for (std::size_t i = 0; i < s.orders.size(); ++i) {
        const Order& o = s.orders[i];
        check_order_values(o);
        if (i == 0) continue;
        const Order& p = s.orders[i - 1];
        if (p.side == BookSide::Ask && o.side == BookSide::Bid) invalid("seed bid after an ask");
        if (p.side == o.side) {
            const bool worse_or_equal = o.side == BookSide::Bid ? o.price4 <= p.price4
                                                                 : o.price4 >= p.price4;
            if (!worse_or_equal) invalid("seed prices not ordered best first");
        }
    }
}

void check_clock(const Input& in) {
    if (in.seed.effective_ns < in.seed.source.timestamp_ns) {
        invalid("effective seed time precedes its source cut");
    }
    if (!in.occurrences.empty() && in.seed.effective_ns > in.occurrences.front().source.timestamp_ns) {
        invalid("effective seed time is after the first fact");
    }
}

// Strict U framing. Field values are read only after the frame is admitted.
OrderReplace check_frame(const Occurrence& o, Locate locate) {
    const unsigned char* f = o.frame.data();
    if (load_be16(f) != kMessageLength['U'] || f[2] != 'U') invalid("frame is not a framed U");
    const OrderReplace u{f + 2};
    if (u.locate() != locate) invalid("frame locate differs from the selected stock");
    if (u.tracking() != o.tracking_number) invalid("frame tracking number differs");
    if (u.timestamp() != o.source.timestamp_ns) invalid("frame timestamp differs from its cut");
    return u;
}

// The exchange's own displayed book is never locked or crossed; such a state means the
// input is not a consistent view of it.
void check_uncrossed(const L3Book& book, Locate locate) {
    const std::optional<Quote> bid = book.best(locate, BookSide::Bid);
    const std::optional<Quote> ask = book.best(locate, BookSide::Ask);
    if (bid && ask && bid->price >= ask->price) invalid("displayed book is locked or crossed");
}

std::vector<Order> capture(const L3Book& book, Locate locate) {
    std::vector<Order> rows;
    rows.reserve(book.order_count());
    for (const BookSide side : {BookSide::Bid, BookSide::Ask}) {
        book.visit(locate, side, [&](Price4 price, Ref ref, Shares shares) {
            rows.push_back(Order{ref, side, price, shares, Attribution::Unknown});
        });
    }
    return rows;
}

}  // namespace

History::History(History&& other) noexcept
    : admitted_(std::exchange(other.admitted_, false)),
      identity_(std::move(other.identity_)),
      symbol_(std::move(other.symbol_)),
      locate_(other.locate_),
      limits_(other.limits_),
      facts_(std::move(other.facts_)),
      snapshots_(std::move(other.snapshots_)),
      captured_rows_(std::exchange(other.captured_rows_, 0)) {}

History& History::operator=(History&& other) noexcept {
    if (this != &other) {
        admitted_ = std::exchange(other.admitted_, false);
        identity_ = std::move(other.identity_);
        symbol_ = std::move(other.symbol_);
        locate_ = other.locate_;
        limits_ = other.limits_;
        facts_ = std::move(other.facts_);
        snapshots_ = std::move(other.snapshots_);
        captured_rows_ = std::exchange(other.captured_rows_, 0);
    }
    return *this;
}

History build_history(const Input& in) {
    const Limits& lim = in.limits;
    check_limits(lim);
    check_identity(in.source_identity);
    if (in.seed.orders.size() > lim.max_orders) too_long("seed exceeds max_orders");
    if (in.occurrences.size() > lim.max_facts) too_long("occurrences exceed max_facts");
    if (in.seed.orders.size() > lim.max_captured_rows) too_long("seed exceeds max_captured_rows");
    check_sources(in);
    check_seed(in.seed);
    check_clock(in);

    const Locate locate = in.seed.locate;
    // One level per order at most, so the level pool can never refuse a replacement.
    L3Book book(L3Book::Config{lim.max_orders, lim.max_orders});
    // Every reference seen in this window; not evidence of day-wide uniqueness.
    std::unordered_set<Ref> seen;
    seen.reserve(in.seed.orders.size() + in.occurrences.size());
    for (const Order& o : in.seed.orders) {
        if (!seen.insert(o.reference).second) invalid("duplicate seed reference");
        if (!book.add(locate, o.reference, o.side, o.shares, o.price4)) {
            invalid("seed order rejected by the book");
        }
    }
    check_uncrossed(book, locate);

    History h;
    h.identity_ = in.source_identity;
    h.symbol_ = in.seed.symbol;
    h.locate_ = locate;
    h.limits_ = lim;
    h.facts_.reserve(in.occurrences.size());
    h.snapshots_.reserve(in.occurrences.size() + 1);
    h.snapshots_.push_back(Snapshot{std::nullopt, in.seed.source, in.seed.effective_ns, capture(book, locate)});
    h.captured_rows_ = h.snapshots_.back().orders.size();

    for (std::size_t i = 0; i < in.occurrences.size(); ++i) {
        const Occurrence& occ = in.occurrences[i];
        const OrderReplace u = check_frame(occ, locate);
        const Ref old_ref = u.old_ref();
        const Ref new_ref = u.new_ref();

        // Copy the old order now: its slot is reused by the replacement.
        const BookOrder* found = book.find(old_ref);
        if (found == nullptr || found->locate != locate) invalid("old reference is not live");
        const Order before{found->ref, found->side, found->price, found->shares, Attribution::Unknown};
        const Order after{new_ref, before.side, u.price(), u.shares(), Attribution::Unknown};
        check_order_values(after);
        if (new_ref == old_ref) invalid("replacement keeps the same reference");
        if (seen.contains(new_ref)) invalid("new reference already seen in this window");

        std::uint32_t rank = 0;
        std::uint64_t ahead = 0;
        bool reached = false;
        book.for_each_order(locate, before.side, before.price4, [&](Ref ref, Shares shares) {
            if (reached) return;
            ++rank;
            if (ref == old_ref) {
                reached = true;
            } else {
                ahead += shares;
            }
        });
        if (!reached) invalid("old order missing from its level");

        if (!book.replace(old_ref, new_ref, after.shares, after.price4)) {
            invalid("replacement rejected by the book");
        }
        seen.insert(new_ref);
        check_uncrossed(book, locate);

        std::vector<Order> rows = capture(book, locate);
        if (h.captured_rows_ + rows.size() > lim.max_captured_rows) {
            too_long("snapshots exceed max_captured_rows");
        }
        h.captured_rows_ += rows.size();
        h.facts_.push_back(Fact{occ.source, u.locate(), u.tracking(), occ.frame, before, after, rank, ahead});
        h.snapshots_.push_back(Snapshot{i, occ.source, occ.source.timestamp_ns, std::move(rows)});
    }
    h.admitted_ = true;
    return h;
}

Observation observe(const History& history, const ObservationConfig& cfg) {
    if (!history.admitted()) invalid("history is not admitted");
    if (cfg.probes.size() > history.limits().max_probes) too_long("probes exceed max_probes");
    for (std::size_t i = 0; i < cfg.probes.size(); ++i) {
        if (cfg.probes[i] > cfg.horizon_ns) invalid("probe beyond the horizon");
        if (i > 0 && cfg.probes[i] < cfg.probes[i - 1]) invalid("probes decrease");
    }

    const std::span<const Snapshot> snaps = history.snapshots();
    Observation out;
    out.delivery_ns.reserve(snaps.size());
    for (const Snapshot& s : snaps) {
        if (s.origin_ns > cfg.horizon_ns) invalid("source time beyond the horizon");
    }
    for (const Snapshot& s : snaps) {
        if (s.origin_ns > std::numeric_limits<Time>::max() - cfg.delay_ns) {
            throw std::overflow_error("delivery time overflows");
        }
        out.delivery_ns.push_back(s.origin_ns + cfg.delay_ns);
    }

    // Origins never decrease and the delay is fixed, so deliveries keep source order:
    // a probe sees the last snapshot delivered at or before it.
    out.snapshot_at.reserve(cfg.probes.size());
    std::size_t delivered = 0;
    for (const Time probe : cfg.probes) {
        while (delivered < out.delivery_ns.size() && out.delivery_ns[delivered] <= probe) ++delivered;
        out.snapshot_at.push_back(delivered == 0 ? std::nullopt : std::optional<std::size_t>(delivered - 1));
    }
    for (std::size_t i = 0; i < out.delivery_ns.size(); ++i) {
        if (out.delivery_ns[i] > cfg.horizon_ns) out.pending.push_back(i);
    }
    return out;
}

}  // namespace itch::identified
