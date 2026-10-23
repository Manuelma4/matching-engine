#pragma once

#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "itch/book.hpp"
#include "itch/messages.hpp"

namespace itch {

struct DayStats {
    std::uint64_t adds = 0;
    std::uint64_t executions = 0;          // E and C
    std::uint64_t executed_shares = 0;     // printable E and C
    std::uint64_t non_printable_shares = 0;
    std::uint64_t trade_shares = 0;        // P: non-displayed liquidity
    std::uint64_t cross_shares = 0;        // Q
    std::uint64_t broken_trades = 0;
    bool end_of_messages = false;          // system event 'C' seen
};

// Wire fields can be inconsistent even when the message type and length are valid.
// Rejected messages do not change the book or its statistics.
struct DecodeAnomalies {
    std::uint64_t invalid_side = 0;
    std::uint64_t locate_mismatch = 0;
};

// Applies the order messages of a feed to an L3Book and keeps day statistics. Plug it into
// itch::dispatch. Locates are assigned by the stock directory ('R') messages.
class BookBuilder {
public:
    explicit BookBuilder(const L3Book::Config& cfg = {});

    void on_directory(StockDirectory m);
    void on_add(AddOrder m);
    void on_execute(OrderExecuted m);
    void on_execute_with_price(OrderExecutedWithPrice m);
    void on_cancel(OrderCancel m);
    void on_delete(OrderDelete m);
    void on_replace(OrderReplace m);
    void on_trade(Trade m);
    void on_cross(CrossTrade m);
    void on_broken(BrokenTrade m);
    void on_system(SystemEvent m);

    [[nodiscard]] const L3Book& book() const { return book_; }
    [[nodiscard]] const DayStats& stats() const { return stats_; }
    [[nodiscard]] const DecodeAnomalies& invalid_messages() const { return invalid_messages_; }
    [[nodiscard]] std::string_view symbol(Locate locate) const;
    // Printable executed shares (E, C, P and Q) per stock.
    [[nodiscard]] std::uint64_t volume(Locate locate) const { return volume_[locate]; }
    [[nodiscard]] Locate max_locate() const { return max_locate_; }

    // FNV-1a over every resting order of every stock, in priority order: two replays that
    // end with byte-identical books have the same hash.
    [[nodiscard]] std::uint64_t book_hash() const;

    // Version-1 deterministic checkpoint fingerprint: ordered L3 state, all directory
    // mappings and volumes, lifecycle/decode counters and peak/live order totals.
    // This is a non-cryptographic regression fingerprint, not a proof of equality.
    [[nodiscard]] std::uint64_t state_hash() const;

private:
    [[nodiscard]] bool matches_locate(Locate locate, Ref ref);

    L3Book book_;
    DayStats stats_;
    DecodeAnomalies invalid_messages_;
    std::vector<std::string> symbols_;
    std::vector<std::uint64_t> volume_;
    Locate max_locate_ = 0;
};

}  // namespace itch
