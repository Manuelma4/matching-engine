// itch_snapshots: complete-feed validation plus one-symbol periodic BBO export.
// Raw BinaryFILE input is mapped; '-' reads a decompressed stream. Output files must
// be fresh. Prices are exact integer Price(4), quantities aggregate displayed shares.
#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <limits>
#include <memory>
#include <string>
#include <string_view>
#include <system_error>

#include "itch/replay.hpp"
#include "itch/snapshots.hpp"
#include "cli.hpp"
#include "source.hpp"

namespace {

class Output {
public:
    explicit Output(const std::string& path) : file_(std::fopen(path.c_str(), "wx")) {
        if (!file_) {
            throw std::system_error(errno, std::generic_category(), "cannot create " + path);
        }
    }
    ~Output() { if (file_) std::fclose(file_); }
    Output(const Output&) = delete;
    Output& operator=(const Output&) = delete;
    std::FILE* get() const { return file_; }
    void close() {
        std::FILE* file = file_;
        file_ = nullptr;
        const bool failed = std::ferror(file) != 0;
        if (std::fclose(file) != 0 || failed) {
            throw std::system_error(errno ? errno : EIO, std::generic_category(),
                                    "cannot finish output file");
        }
    }
private:
    std::FILE* file_;
};

void json_string(std::FILE* file, const std::string& value) {
    std::fputc('"', file);
    for (char c : value) {
        if (c == '"' || c == '\\') std::fputc('\\', file);
        std::fputc(c, file);
    }
    std::fputc('"', file);
}

}  // namespace

int main(int argc, char** argv) {
    std::string path, symbol, csv_path, summary_path;
    std::uint64_t interval_ns = 1'000'000'000;
    itch::L3Book::Config cfg;
    try {
        bool positional = false;
        for (int i = 1; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (!positional && arg == "--") {
                positional = true;
            } else if (!positional && arg == "--strict") {
                // Complete-day validation is always required; retained for explicit scripts.
            } else if (!positional && (arg == "--symbol" || arg == "--interval-ms" ||
                       arg == "--out" || arg == "--output" || arg == "--summary" ||
                       arg == "--max-orders" || arg == "--input")) {
                if (++i == argc) throw std::invalid_argument(std::string(arg) + ": missing value");
                if (arg == "--symbol") symbol = argv[i];
                else if (arg == "--out" || arg == "--output") csv_path = argv[i];
                else if (arg == "--summary") summary_path = argv[i];
                else if (arg == "--input") {
                    if (!path.empty()) throw std::invalid_argument("input specified more than once");
                    path = argv[i];
                } else if (arg == "--max-orders") {
                    cfg.max_orders = itch::tools::number<std::uint32_t>(arg, argv[i]);
                    cfg.max_levels = std::min(cfg.max_levels, cfg.max_orders);
                } else {
                    const auto milliseconds = itch::tools::number<std::uint64_t>(arg, argv[i]);
                    if (milliseconds > std::numeric_limits<std::uint64_t>::max() / 1'000'000) {
                        throw std::invalid_argument("--interval-ms: nanosecond conversion overflows");
                    }
                    interval_ns = milliseconds * 1'000'000;
                }
            } else if (!positional && arg != "-" && arg.starts_with('-')) {
                throw std::invalid_argument("unknown option: " + std::string(arg));
            } else {
                if (!path.empty()) throw std::invalid_argument("input specified more than once");
                path = arg;
            }
        }
        if (path.empty() || symbol.empty() || symbol.size() > 8 || csv_path.empty() ||
            summary_path.empty() || csv_path == summary_path) {
            throw std::invalid_argument("input, 1–8 character symbol and two distinct output paths required");
        }
        for (char character : symbol) {
            const auto c = static_cast<unsigned char>(character);
            if (c <= 32 || c >= 127) throw std::invalid_argument("symbol must use visible ASCII characters");
        }
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_snapshots: %s\nusage: itch_snapshots --symbol SYMBOL "
                     "[--interval-ms 1000] --out fresh.csv --summary fresh.json "
                     "[--max-orders N] [--strict] <file | ->\n", e.what());
        return 2;
    }

    try {
        Output csv(csv_path);
        Output summary(summary_path);
        if (std::fprintf(csv.get(), "ts,ask_px_1,ask_sz_1,bid_px_1,bid_sz_1\n") < 0) {
            throw std::runtime_error("cannot write snapshot header");
        }
        auto builder = std::make_unique<itch::BookBuilder>(cfg);
        itch::BboSampler sampler(symbol, interval_ns);
        std::uint64_t messages = 0, unknown_type = 0, bad_length = 0, after_end = 0,
                      end_records = 0;
        const auto input = itch::tools::walk_input(path, [&](itch::Bytes message) {
            if (end_records != 0 || (!message.empty() && builder->stats().end_of_messages)) {
                ++after_end;
            }
            if (!message.empty()) {
                ++messages;
                sampler.before_message(message, builder->book(), [&](const itch::BboSnapshot& s) {
                    const auto ask_price = s.ask ? static_cast<long long>(s.ask->price) : 9'999'999'999LL;
                    const auto bid_price = s.bid ? static_cast<long long>(s.bid->price) : -9'999'999'999LL;
                    if (std::fprintf(csv.get(), "%llu,%lld,%llu,%lld,%llu\n",
                                     static_cast<unsigned long long>(s.timestamp), ask_price,
                                     static_cast<unsigned long long>(s.ask ? s.ask->shares : 0),
                                     bid_price,
                                     static_cast<unsigned long long>(s.bid ? s.bid->shares : 0)) < 0) {
                        throw std::runtime_error("cannot write snapshot row");
                    }
                });
            }
            switch (itch::dispatch(message, *builder)) {
                case itch::Dispatch::UnknownType: ++unknown_type; break;
                case itch::Dispatch::BadLength: ++bad_length; break;
                case itch::Dispatch::EndOfSession: ++end_records; break;
                default: break;
            }
        });
        // A successful return includes fclose verification; buffered write failures
        // must not produce a success summary.
        csv.close();
        const auto& book = builder->book();
        const auto& a = book.anomalies();
        const auto& invalid = builder->invalid_messages();
        const auto trailing = input.bytes - input.consumed;
        const std::uint64_t anomalies = a.unknown_ref + a.duplicate_ref + a.share_underflow +
            a.capacity + invalid.invalid_side + invalid.locate_mismatch + unknown_type +
            bad_length + after_end + sampler.clock_regressions();
        const bool passed = messages != 0 && trailing == 0 && anomalies == 0 &&
            builder->stats().end_of_messages && book.order_count() == 0 &&
            sampler.locate().has_value() && sampler.snapshots_written() != 0;
        std::fprintf(summary.get(), "{\n  \"schema_version\": 1,\n  \"symbol\": ");
        json_string(summary.get(), symbol);
        const auto field = [&](const char* name, std::uint64_t value) {
            std::fprintf(summary.get(), ",\n  \"%s\": %llu", name,
                         static_cast<unsigned long long>(value));
        };
        field("interval_ns", interval_ns);
        field("messages", messages);
        field("input_bytes", input.bytes);
        field("snapshots_written", sampler.snapshots_written());
        field("first_snapshot_ns", sampler.first_snapshot_ns());
        field("last_snapshot_ns", sampler.last_snapshot_ns());
        field("next_snapshot_ns", sampler.next_snapshot_ns());
        field("first_accepted_timestamp_ns", sampler.first_accepted_timestamp_ns());
        field("last_accepted_timestamp_ns", sampler.last_accepted_timestamp_ns());
        field("locate", sampler.locate().value_or(0));
        field("final_orders", book.order_count());
        field("peak_orders", book.peak_orders());
        field("unknown_ref", a.unknown_ref);
        field("duplicate_ref", a.duplicate_ref);
        field("share_underflow", a.share_underflow);
        field("capacity", a.capacity);
        field("invalid_side", invalid.invalid_side);
        field("locate_mismatch", invalid.locate_mismatch);
        field("unknown_type", unknown_type);
        field("bad_length", bad_length);
        field("after_end", after_end);
        field("end_records", end_records);
        field("trailing_bytes", trailing);
        field("anomalies", anomalies);
        field("clock_regressions", sampler.clock_regressions());
        std::fprintf(summary.get(), ",\n  \"end_of_messages\": %s,\n  \"passed\": %s,\n"
                     "  \"strict_passed\": %s\n}\n",
                     builder->stats().end_of_messages ? "true" : "false",
                     passed ? "true" : "false", passed ? "true" : "false");
        summary.close();
        if (!passed) {
            std::fprintf(stderr, "itch_snapshots: validation failed (full clean day, known symbol "
                         "and non-empty snapshots required); inspect summary\n");
        }
        return passed ? 0 : 1;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_snapshots: %s\n", e.what());
        return 1;
    }
}
