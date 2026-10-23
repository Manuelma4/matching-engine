#pragma once

#include <cstdint>
#include <limits>
#include <optional>
#include <stdexcept>
#include <string>
#include <string_view>
#include <utility>

#include "itch/messages.hpp"

namespace itch {

struct BboSnapshot {
    std::uint64_t timestamp;
    std::optional<Quote> ask;
    std::optional<Quote> bid;
};

// Periodic, pre-message snapshots under the pinned itchbook comparison convention.
// Feed every *validated* message here before dispatching it to the complete-feed
// BookBuilder. Only the selected symbol's modelled messages and global S messages
// advance this clock. There is deliberately no EOF flush: a future state is not
// inferred from the end of a byte stream.
class BboSampler {
public:
    explicit BboSampler(std::string symbol, std::uint64_t interval_ns)
        : symbol_(std::move(symbol)), interval_ns_(interval_ns) {
        if (symbol_.empty() || symbol_.size() > 8 || interval_ns == 0) {
            throw std::invalid_argument("snapshot symbol/interval is invalid");
        }
    }

    template <class Emit>
    void before_message(Bytes message, const L3Book& book, Emit&& emit) {
        // This guard also makes this public helper safe against accidental malformed
        // calls, although the exporter counts/rejects those messages separately.
        if (message.empty() || kMessageLength[message[0]] == 0 ||
            message.size() != kMessageLength[message[0]]) {
            return;
        }
        const Header header{message.data()};
        if (header.type() == 'R') {
            std::string_view stock = StockDirectory{message.data()}.stock();
            while (!stock.empty() && stock.back() == ' ') {
                stock.remove_suffix(1);
            }
            if (stock == symbol_) {
                locate_ = header.locate();
            }
        }
        if (!modelled(header.type()) ||
            (header.type() != 'S' && (!locate_ || header.locate() != *locate_))) {
            return;
        }

        const std::uint64_t timestamp = header.timestamp();
        if (timestamp < last_accepted_timestamp_ns_) {
            ++clock_regressions_;
        }
        last_accepted_timestamp_ns_ = timestamp;
        if (next_snapshot_ns_ == 0 && timestamp > 0) {
            first_accepted_timestamp_ns_ = timestamp;
            // ITCH timestamps occupy 48 bits; an interval above that range simply
            // schedules a boundary beyond all messages in the file.
            next_snapshot_ns_ = (timestamp / interval_ns_) * interval_ns_;
            advance_grid();
        }
        while (next_snapshot_ns_ != 0 && next_snapshot_ns_ <= timestamp) {
            const BboSnapshot snapshot{
                next_snapshot_ns_,
                locate_ ? book.best(*locate_, BookSide::Ask) : std::nullopt,
                locate_ ? book.best(*locate_, BookSide::Bid) : std::nullopt};
            emit(snapshot);
            if (snapshots_written_ == 0) {
                first_snapshot_ns_ = next_snapshot_ns_;
            }
            last_snapshot_ns_ = next_snapshot_ns_;
            ++snapshots_written_;
            advance_grid();
        }
    }

    [[nodiscard]] std::optional<Locate> locate() const { return locate_; }
    [[nodiscard]] std::uint64_t interval_ns() const { return interval_ns_; }
    [[nodiscard]] std::uint64_t snapshots_written() const { return snapshots_written_; }
    [[nodiscard]] std::uint64_t first_snapshot_ns() const { return first_snapshot_ns_; }
    [[nodiscard]] std::uint64_t last_snapshot_ns() const { return last_snapshot_ns_; }
    [[nodiscard]] std::uint64_t next_snapshot_ns() const { return next_snapshot_ns_; }
    [[nodiscard]] std::uint64_t first_accepted_timestamp_ns() const {
        return first_accepted_timestamp_ns_;
    }
    [[nodiscard]] std::uint64_t last_accepted_timestamp_ns() const {
        return last_accepted_timestamp_ns_;
    }
    [[nodiscard]] std::uint64_t clock_regressions() const { return clock_regressions_; }

private:
    static bool modelled(char type) {
        switch (type) {
            case 'S': case 'R': case 'A': case 'F': case 'E': case 'C':
            case 'X': case 'D': case 'U': case 'P': case 'Q': case 'H':
                return true;
            default:
                return false;
        }
    }

    void advance_grid() {
        if (interval_ns_ > std::numeric_limits<std::uint64_t>::max() - next_snapshot_ns_) {
            throw std::overflow_error("snapshot grid overflow");
        }
        next_snapshot_ns_ += interval_ns_;
    }

    std::string symbol_;
    std::uint64_t interval_ns_;
    std::optional<Locate> locate_;
    std::uint64_t snapshots_written_ = 0;
    std::uint64_t first_snapshot_ns_ = 0;
    std::uint64_t last_snapshot_ns_ = 0;
    std::uint64_t first_accepted_timestamp_ns_ = 0;
    std::uint64_t last_accepted_timestamp_ns_ = 0;
    std::uint64_t next_snapshot_ns_ = 0;
    std::uint64_t clock_regressions_ = 0;
};

}  // namespace itch
