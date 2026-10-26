#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

#include "itch/book.hpp"

namespace itch::identified {

// A deliberately narrow observer of one selected stock: a seed inventory followed by
// U (order replace) messages only. It records what each replacement did to the
// identified book and when that knowledge could have reached a strategy. It reads no
// file, owns no feed, matches nothing and models no own order or fill.
//
// Every snapshot and fact owns plain values. Nothing returned points into the book's
// slab, whose slots are reused by later replacements.
using Time = std::uint64_t;

inline constexpr Price4 kMaxPrice4 = 2'000'000'000;
inline constexpr Time kMaxWireTimestamp = (Time{1} << 48) - 1;
inline constexpr std::size_t kFrameBytes = 37;  // 2-byte BinaryFILE prefix + 35-byte U
// Hard bounds sized for one real stock's full displayed book over a short U window.
// Callers narrow them; every bound is enforced before or while memory is committed.
inline constexpr std::uint32_t kHardMaxOrders = std::uint32_t{1} << 20;
inline constexpr std::uint32_t kHardMaxFacts = 256;
inline constexpr std::uint32_t kHardMaxCapturedRows = std::uint32_t{1} << 24;
inline constexpr std::uint32_t kHardMaxProbes = std::uint32_t{1} << 16;

// The module never reads the input bytes, so it cannot authenticate them. This fixed
// declaration is part of every admitted history; it is not a caller-supplied flag.
inline constexpr std::string_view kVerification = "unverified_by_module";

// Position of one framed message in the declared input: the record occupies
// [frame_offset, frame_end_offset), including its 2-byte length prefix.
struct SourceCut {
    std::uint64_t sequence{};  // one-based global message number
    std::uint64_t frame_offset{};
    std::uint64_t frame_end_offset{};
    Time timestamp_ns{};
    std::uint16_t body_bytes{};
    char type{};

    friend bool operator==(const SourceCut&, const SourceCut&) = default;
};

// Declared identity of the input the cuts refer to. Metadata only (see kVerification).
struct SourceIdentity {
    std::uint64_t input_bytes{};
    std::string input_sha256;                    // 64 lower-case hex digits
    std::optional<std::string> evidence_sha256;  // same format when present
};

// Seed orders carry no participant identity, and replacements inherit it.
enum class Attribution : std::uint8_t { Unknown };

struct Order {
    Ref reference{};
    BookSide side{};
    Price4 price4{};
    Shares shares{};
    Attribution attribution{Attribution::Unknown};

    friend bool operator==(const Order&, const Order&) = default;
};

// Complete displayed inventory of the selected stock as of `effective_ns`: bids then
// asks, best price first, time priority within a price.
struct Seed {
    std::string symbol;  // 1..8 printable characters; not checked against a directory
    Locate locate{};
    SourceCut source;    // the message after which the inventory holds
    Time effective_ns{};
    std::vector<Order> orders;
};

struct Occurrence {
    SourceCut source;
    std::uint16_t tracking_number{};
    std::array<unsigned char, kFrameBytes> frame{};
};

// Caller limits; each may only narrow the hard bound above it, and must be positive
// except max_facts and max_captured_rows. Captured rows count the order rows of the
// seed and of every post-replacement snapshot.
struct Limits {
    std::uint32_t max_orders = kHardMaxOrders;
    std::uint32_t max_facts = kHardMaxFacts;
    std::uint32_t max_captured_rows = kHardMaxCapturedRows;
    std::uint32_t max_probes = kHardMaxProbes;
};

struct Input {
    SourceIdentity source_identity;
    Seed seed;
    std::vector<Occurrence> occurrences;
    std::vector<SourceCut> expected_sources;  // must equal seed cut + occurrence cuts
    Limits limits;
};

// What one replacement did. Rank is one-based within the old price level and, with the
// visible shares ahead, describes the order immediately before the message.
struct Fact {
    SourceCut source;
    Locate source_locate{};
    std::uint16_t tracking_number{};
    std::array<unsigned char, kFrameBytes> frame{};
    Order before_order;
    Order after_order;
    std::uint32_t fifo_rank_before{};
    std::uint64_t visible_shares_ahead_before{};
};

// Complete inventory after the seed (event_index empty) or after fact event_index.
struct Snapshot {
    std::optional<std::size_t> event_index;
    SourceCut source;
    Time origin_ns{};  // effective seed time, or the fact's source timestamp
    std::vector<Order> orders;
};

// Retrospective record of every snapshot. A strategy's information at a given time is
// only what observe() delivers; reading later snapshots directly would leak the future.
class History {
public:
    History(const History&) = default;
    History& operator=(const History&) = default;
    // A moved-from history is no longer admitted and observe() refuses it.
    History(History&& other) noexcept;
    History& operator=(History&& other) noexcept;
    ~History() = default;

    [[nodiscard]] bool admitted() const { return admitted_; }
    [[nodiscard]] std::string_view verification() const { return kVerification; }
    [[nodiscard]] const SourceIdentity& source_identity() const { return identity_; }
    [[nodiscard]] std::string_view symbol() const { return symbol_; }
    [[nodiscard]] Locate locate() const { return locate_; }
    [[nodiscard]] const Limits& limits() const { return limits_; }
    [[nodiscard]] std::span<const Fact> facts() const { return facts_; }
    [[nodiscard]] std::span<const Snapshot> snapshots() const { return snapshots_; }
    [[nodiscard]] std::size_t captured_rows() const { return captured_rows_; }

private:
    History() = default;
    friend History build_history(const Input& input);

    bool admitted_ = false;
    SourceIdentity identity_;
    std::string symbol_;
    Locate locate_{};
    Limits limits_;
    std::vector<Fact> facts_;
    std::vector<Snapshot> snapshots_;
    std::size_t captured_rows_ = 0;
};

// Validates the whole input and applies every replacement to a private L3Book.
// Throws std::invalid_argument for malformed or inconsistent input, std::length_error
// when a limit is exceeded; allocation failures propagate. Nothing partial is returned.
[[nodiscard]] History build_history(const Input& input);

// Knowledge of each snapshot arrives `delay_ns` after its origin. Probes must be
// nondecreasing and within the inclusive horizon. A delivery at the same time as a probe
// is visible to it; deliveries after the horizon stay pending and are never flushed.
struct ObservationConfig {
    Time delay_ns{};
    Time horizon_ns{};
    std::vector<Time> probes;
};

struct Observation {
    std::vector<Time> delivery_ns;                         // one per snapshot
    std::vector<std::optional<std::size_t>> snapshot_at;   // one per probe; empty: none yet
    std::vector<std::size_t> pending;                      // delivered after the horizon
};

// Throws std::invalid_argument (bad probes, origin after the horizon, history not
// admitted), std::length_error (too many probes) or std::overflow_error (a delivery time
// does not fit in 64 bits, checked for every snapshot, pending or not).
[[nodiscard]] Observation observe(const History& history, const ObservationConfig& config);

}  // namespace itch::identified
