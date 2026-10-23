// itch_replay: rebuilds every stock's full-depth (L3) book from an ITCH 5.0 BinaryFILE and
// reports throughput, book lifecycle checks and the most traded stocks.
//
//   itch_replay [--allow-partial] [--top N] [--max-orders N] <file | ->
//
// Wall time includes input handling and page faults; use itch_bench for warm replay cost.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#include "itch/replay.hpp"
#include "cli.hpp"
#include "source.hpp"

int main(int argc, char** argv) {
    std::size_t top = 10;
    itch::L3Book::Config cfg;
    std::string path;
    bool allow_partial = false;
    try {
        bool positional = false;
        for (int i = 1; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (!positional && arg == "--") {
                positional = true;
            } else if (!positional && arg == "--allow-partial") {
                allow_partial = true;
            } else if (!positional && (arg == "--top" || arg == "--max-orders")) {
                if (++i == argc) {
                    throw std::invalid_argument(std::string(arg) + ": missing value");
                }
                if (arg == "--top") {
                    top = itch::tools::number<std::size_t>(arg, argv[i], true);
                } else {
                    cfg.max_orders = itch::tools::number<std::uint32_t>(arg, argv[i]);
                    cfg.max_levels = std::min(itch::L3Book::Config{}.max_levels, cfg.max_orders);
                }
            } else if (!positional && arg != "-" && arg.starts_with('-')) {
                throw std::invalid_argument("unknown option: " + std::string(arg));
            } else if (path.empty()) {
                path = arg;
            } else {
                throw std::invalid_argument("expected one input path");
            }
        }
        if (path.empty()) {
            throw std::invalid_argument("missing input path");
        }
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_replay: %s\nusage: itch_replay [--allow-partial] [--top N] "
                             "[--max-orders N] <file | ->\n", e.what());
        return 2;
    }

    std::unique_ptr<itch::BookBuilder> builder;
    std::uint64_t messages = 0;
    std::uint64_t unknown = 0;
    std::uint64_t bad_length = 0;
    std::uint64_t end_records = 0;
    std::uint64_t after_end = 0;
    std::chrono::steady_clock::time_point start;
    itch::tools::WalkResult r;
    try {
        builder = std::make_unique<itch::BookBuilder>(cfg);
        start = std::chrono::steady_clock::now();
        r = itch::tools::walk_input(
            path,
            [&](itch::Bytes m) {
                if (end_records != 0 || (!m.empty() && builder->stats().end_of_messages)) {
                    ++after_end;
                }
                ++messages;
                switch (itch::dispatch(m, *builder)) {
                    case itch::Dispatch::UnknownType:
                        ++unknown;
                        break;
                    case itch::Dispatch::BadLength:
                        ++bad_length;
                        break;
                    case itch::Dispatch::EndOfSession:
                        ++end_records;
                        --messages;  // the zero-length record is not a message
                        break;
                    default:
                        break;
                }
            });
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_replay: %s\n", e.what());
        return 1;
    }
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

    const itch::L3Book& book = builder->book();
    const itch::DayStats& s = builder->stats();
    const itch::Anomalies& a = book.anomalies();
    const auto& invalid = builder->invalid_messages();
    std::printf("messages        %llu in %.3f s (%.1f M msg/s, %.1f ns/msg)\n",
                static_cast<unsigned long long>(messages), seconds,
                static_cast<double>(messages) / seconds / 1e6,
                seconds * 1e9 / static_cast<double>(std::max<std::uint64_t>(messages, 1)));
    std::printf("adds            %llu\n", static_cast<unsigned long long>(s.adds));
    std::printf("executions      %llu (%llu printable shares, %llu non-printable)\n",
                static_cast<unsigned long long>(s.executions),
                static_cast<unsigned long long>(s.executed_shares),
                static_cast<unsigned long long>(s.non_printable_shares));
    std::printf("other volume    %llu shares non-displayed (P), %llu crossed (Q), %llu broken\n",
                static_cast<unsigned long long>(s.trade_shares),
                static_cast<unsigned long long>(s.cross_shares),
                static_cast<unsigned long long>(s.broken_trades));
    std::printf("peak orders     %zu\n", book.peak_orders());
    std::printf("live at end     %zu orders\n", book.order_count());
    std::printf("end of messages %s\n", s.end_of_messages ? "seen" : "missing");
    std::printf("anomalies       %llu unknown ref, %llu duplicate ref, %llu share underflow, "
                "%llu capacity, %llu unknown type, %llu wrong length, "
                "%llu invalid side, %llu locate mismatch\n",
                static_cast<unsigned long long>(a.unknown_ref),
                static_cast<unsigned long long>(a.duplicate_ref),
                static_cast<unsigned long long>(a.share_underflow),
                static_cast<unsigned long long>(a.capacity),
                static_cast<unsigned long long>(unknown),
                static_cast<unsigned long long>(bad_length),
                static_cast<unsigned long long>(invalid.invalid_side),
                static_cast<unsigned long long>(invalid.locate_mismatch));
    std::printf("trailing        %zu bytes outside complete frames\n", r.bytes - r.consumed);
    std::printf("after end       %llu records after session end\n",
                static_cast<unsigned long long>(after_end));
    std::printf("book hash       %016llx\n", static_cast<unsigned long long>(builder->book_hash()));

    if (top > 0) {
        std::vector<itch::Locate> locates;
        for (std::uint32_t l = 1; l <= builder->max_locate(); ++l) {
            if (builder->volume(static_cast<itch::Locate>(l)) > 0) {
                locates.push_back(static_cast<itch::Locate>(l));
            }
        }
        std::sort(locates.begin(), locates.end(), [&](itch::Locate x, itch::Locate y) {
            return builder->volume(x) > builder->volume(y);
        });
        locates.resize(std::min(top, locates.size()));
        std::printf("\n%-8s %-8s %16s\n", "locate", "symbol", "volume");
        for (itch::Locate l : locates) {
            std::printf("%-8u %-8.*s %16llu\n", l,
                        static_cast<int>(builder->symbol(l).size()), builder->symbol(l).data(),
                        static_cast<unsigned long long>(builder->volume(l)));
        }
    }
    const bool clean = a.unknown_ref == 0 && a.duplicate_ref == 0 && a.share_underflow == 0 &&
                       a.capacity == 0 && unknown == 0 && bad_length == 0 && after_end == 0 &&
                       invalid.invalid_side == 0 && invalid.locate_mismatch == 0 &&
                       r.bytes == r.consumed && messages != 0;
    const bool complete = s.end_of_messages && book.order_count() == 0;
    const bool valid = clean && (allow_partial || complete);
    std::printf("validation      %s (%s)\n", valid ? "passed" : "FAILED",
                allow_partial ? "partial input allowed" : "complete day required");
    return valid ? 0 : 1;
}
