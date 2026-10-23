#pragma once

#include <array>
#include <cstdint>
#include <memory>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

#include "itch/book.hpp"
#include "itch/framing.hpp"
#include "itch/queue_sim.hpp"

namespace itch::queue {

struct WindowConfig {
    std::string symbol;
    Side side{Side::Buy};
    std::uint32_t price4{};
    Time start_ns{}; // seed after the entire <= start timestamp group
    Time end_ns{};   // include the entire end timestamp group
};

struct SourcePoint {
    std::uint64_t sequence{}; // one-based non-empty BinaryFILE message
    std::uint64_t frame_offset{}; // absolute offset of the two-byte length prefix
    Time timestamp_ns{};
    std::uint16_t body_bytes{};
    char type{};
    bool operator==(const SourcePoint&) const = default;
};

enum class ProjectionReason {
    SeedBoundary, DisplayedAdd, DisplayedCancel, DisplayedExecution,
    OppositeQuote, NonDisplayedPrint, UnrelatedBrokenTrade, NoRepresentedChange
};

struct WindowObservation {
    SourcePoint source;
    ProjectionReason reason{};
    Ref reference{};
    Ref new_reference{};
    std::uint64_t match{};
    std::uint32_t before_quantity{};
    std::uint32_t before_opposite_price4{};
    std::uint32_t before_opposite_quantity{};
    std::uint32_t after_quantity{};
    std::uint32_t after_opposite_price4{};
    std::uint32_t after_opposite_quantity{};
    std::uint32_t normalised_row{}; // one-based output row; zero means no emission
};

struct SeedEligibility {
    SourcePoint directory;
    SourcePoint trading_action;
    SourcePoint market_hours;
    SourcePoint opening_cross;
    std::optional<SourcePoint> operational;
    char operational_action{'?'}; // absent means no announcement observed
    char retail_interest{'?'};
};

struct WindowResult {
    WindowConfig config;
    Locate locate{};
    std::uint64_t source_messages{};
    std::uint64_t source_end_records{};
    std::uint64_t source_bytes{};
    std::uint64_t reconciled_messages{};
    std::uint64_t displayed_executed_shares{};
    std::uint32_t final_quantity{};
    std::uint32_t final_opposite_price4{};
    std::uint32_t final_opposite_quantity{};
    SeedEligibility eligibility;
    std::array<std::uint64_t, 256> source_type_counts{};
    std::array<std::uint64_t, 256> window_type_counts{};
    std::vector<MarketEvent> events;
    // Seed plus every selected-symbol message in (start, end], including exclusions.
    std::vector<WindowObservation> observations;
};

std::string_view name(ProjectionReason value);

// Strict whole-source validation followed by a bounded visible-event projection.
// Requires O/S/Q/M/E/C in order, a full clean/empty source lifecycle, monotone raw
// timestamps and contiguous framing. Rejects unsupported windows rather than changing
// their meaning. E rows describe displayed executions, not parent aggressor demand.
class WindowProjector {
public:
    explicit WindowProjector(WindowConfig config, const L3Book::Config& book_config = {});
    ~WindowProjector();
    WindowProjector(const WindowProjector&) = delete;
    WindowProjector& operator=(const WindowProjector&) = delete;
    void consume(Bytes message, std::uint64_t frame_offset);
    WindowResult finish(std::uint64_t input_bytes);

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

} // namespace itch::queue
