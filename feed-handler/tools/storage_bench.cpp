// One fresh-process replay for comparing reconstruction storage/search policies.
// Timing mode excludes construction, mmap/prefault, input preflight, final hashes and
// teardown from replay_seconds. Memory mode streams without mapping the input; its
// elapsed replay includes I/O/validation and is deliberately not a replay benchmark.
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>

#include <cerrno>
#include <fcntl.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <unistd.h>

#include "itch/replay.hpp"
#include "cli.hpp"

namespace {

using Clock = std::chrono::steady_clock;

double seconds_since(Clock::time_point start) {
    const double seconds = std::chrono::duration<double>(Clock::now() - start).count();
    if (!std::isfinite(seconds) || seconds < 0) {
        throw std::runtime_error("invalid monotonic-clock duration");
    }
    return seconds;
}

std::uint64_t peak_rss_bytes() {
    rusage usage{};
    if (::getrusage(RUSAGE_SELF, &usage) != 0) {
        throw std::system_error(errno, std::generic_category(), "cannot read process peak RSS");
    }
    if (usage.ru_maxrss < 0) throw std::runtime_error("negative process peak RSS");
    const auto value = static_cast<std::uint64_t>(usage.ru_maxrss);
#if defined(__APPLE__)
    return value;  // macOS reports bytes.
#elif defined(__linux__)
    if (value > std::numeric_limits<std::uint64_t>::max() / 1024) {
        throw std::overflow_error("process peak RSS conversion overflow");
    }
    return value * 1024;  // Linux reports KiB.
#else
    throw std::runtime_error("process peak RSS units are unsupported on this platform");
#endif
}

class Input {
public:
    explicit Input(const std::string& path) {
        // Nonblocking open lets a FIFO/device be rejected by fstat instead of
        // waiting for a writer before we can enforce the regular-file contract.
        const int fd = ::open(path.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) throw std::system_error(errno, std::generic_category(), "cannot open input");
        struct stat info{};
        if (::fstat(fd, &info) != 0) {
            const int error = errno;
            ::close(fd);
            throw std::system_error(error, std::generic_category(), "cannot stat input");
        }
        if (!S_ISREG(info.st_mode)) {
            ::close(fd);
            throw std::invalid_argument("input must be a regular BinaryFILE file");
        }
        file_ = ::fdopen(fd, "rb");
        if (!file_) {
            const int error = errno;
            ::close(fd);
            throw std::system_error(error, std::generic_category(), "cannot open input stream");
        }
    }
    ~Input() { if (file_) std::fclose(file_); }
    Input(const Input&) = delete;
    Input& operator=(const Input&) = delete;
    std::FILE* get() const { return file_; }
    void close() {
        std::FILE* file = file_;
        file_ = nullptr;
        if (std::fclose(file) != 0) {
            throw std::system_error(errno ? errno : EIO, std::generic_category(), "cannot close input");
        }
    }
private:
    std::FILE* file_ = nullptr;
};

// Timing preflight owns all wire/lifecycle counters so the measured callback can
// consist solely of dispatch. Memory mode uses the same checks while streaming.
struct WireStats {
    std::uint64_t messages = 0;
    std::uint64_t records = 0;
    std::uint64_t consumed_bytes = 0;
    std::uint64_t end_records = 0;
    std::uint64_t after_end = 0;
    std::uint64_t unknown_type = 0;
    std::uint64_t bad_length = 0;
    bool end_of_messages = false;

    void observe(itch::Bytes message) {
        if (end_records != 0 || (!message.empty() && end_of_messages)) ++after_end;
        ++records;
        consumed_bytes += message.size() + 2;
        if (message.empty()) {
            ++end_records;
            return;
        }
        ++messages;
        const auto expected = itch::kMessageLength[message[0]];
        if (expected == 0) ++unknown_type;
        else if (message.size() != expected) ++bad_length;
        else if (message[0] == 'S' && itch::SystemEvent{message.data()}.event() == 'C') {
            end_of_messages = true;
        }
    }

    [[nodiscard]] bool clean(std::uint64_t input_bytes) const {
        return messages != 0 && consumed_bytes == input_bytes && unknown_type == 0 &&
            bad_length == 0 && after_end == 0;
    }
};

}  // namespace

int main(int argc, char** argv) {
    itch::L3Book::Config config;
    std::string path;
    bool memory = false;
    try {
        bool positional = false;
        for (int i = 1; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (!positional && arg == "--") positional = true;
            else if (!positional && arg == "--memory") memory = true;
            else if (!positional && (arg == "--max-orders" || arg == "--max-levels")) {
                if (++i == argc) throw std::invalid_argument(std::string(arg) + ": missing value");
                const auto value = itch::tools::number<std::uint32_t>(arg, argv[i]);
                if (arg == "--max-orders") config.max_orders = value;
                else config.max_levels = value;
            } else if (!positional && arg.starts_with('-')) {
                throw std::invalid_argument("unknown option: " + std::string(arg));
            } else if (path.empty()) path = arg;
            else throw std::invalid_argument("expected one input path");
        }
        if (path.empty() || path == "-") {
            throw std::invalid_argument("one regular-file input path is required; stdin is unsupported");
        }
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_storage_bench: %s\nusage: itch_storage_bench [--memory] "
                     "[--max-orders N] [--max-levels N] INPUT\n", e.what());
        return 2;
    }

    try {
        Input input(path);
        const auto baseline_peak_rss = peak_rss_bytes();
        const auto construction_start = Clock::now();
        auto builder = std::make_unique<itch::BookBuilder>(config);
        const double construction_seconds = seconds_since(construction_start);
        const auto post_construct_peak_rss = peak_rss_bytes();
        std::unique_ptr<itch::MappedFile> mapped;
        WireStats wire;
        std::uint64_t input_bytes = 0;
        double replay_seconds = 0;
        bool replay_performed = false;
        if (memory) {
            const auto replay_start = Clock::now();
            const auto leftover = itch::walk_stream(input.get(), [&](itch::Bytes message) {
                wire.observe(message);
                itch::dispatch(message, *builder);
            });
            replay_seconds = seconds_since(replay_start);
            input_bytes = wire.consumed_bytes + leftover;
            replay_performed = true;
        } else {
            // Mapping and touching the complete input happen only after construction
            // RSS has been sampled, and entirely outside the replay interval.
            mapped = std::make_unique<itch::MappedFile>(path);
            mapped->prefault();
            const auto bytes = mapped->bytes();
            input_bytes = bytes.size();
            itch::walk_frames(bytes, [&](itch::Bytes message) { wire.observe(message); });
            if (wire.clean(input_bytes)) {
                const auto replay_start = Clock::now();
                const auto consumed = itch::walk_frames(bytes, [&](itch::Bytes message) {
                    itch::dispatch(message, *builder);
                });
                replay_seconds = seconds_since(replay_start);
                if (consumed != bytes.size()) throw std::runtime_error("timed input framing changed");
                replay_performed = true;
            }
        }
        const auto process_peak_rss = peak_rss_bytes();
        input.close();
        const bool preflight_passed = wire.clean(input_bytes);

        // Fingerprints and summary extraction are intentionally outside replay_seconds.
        const auto& book = builder->book();
        const auto anomalies = book.anomalies();
        const auto invalid = builder->invalid_messages();
        const auto stats = builder->stats();
        const auto peak_orders = book.peak_orders();
        const auto final_orders = book.order_count();
        const auto book_hash = builder->book_hash();
        const auto state_hash = builder->state_hash();
        const bool passed = preflight_passed && replay_performed && stats.end_of_messages &&
            final_orders == 0 && anomalies.unknown_ref == 0 && anomalies.duplicate_ref == 0 &&
            anomalies.share_underflow == 0 && anomalies.capacity == 0 &&
            invalid.invalid_side == 0 && invalid.locate_mismatch == 0;
        const auto teardown_start = Clock::now();
        builder.reset();
        const double teardown_seconds = seconds_since(teardown_start);

        std::printf("{\n  \"schema_version\": 1,\n  \"fingerprint_version\": 1,\n"
                    "  \"reference_index\": \"%.*s\",\n  \"level_search\": \"%.*s\",\n"
                    "  \"mode\": \"%s\",\n"
                    "  \"construction_seconds\": %.17g,\n  \"replay_seconds\": %.17g,\n"
                    "  \"teardown_seconds\": %.17g",
                    static_cast<int>(itch::kReferenceIndexName.size()), itch::kReferenceIndexName.data(),
                    static_cast<int>(itch::kLevelSearchName.size()), itch::kLevelSearchName.data(),
                    memory ? "memory" : "timing", construction_seconds, replay_seconds, teardown_seconds);
        const auto field = [](const char* name, std::uint64_t value) {
            std::printf(",\n  \"%s\": %llu", name, static_cast<unsigned long long>(value));
        };
        field("max_orders", config.max_orders); field("max_levels", config.max_levels);
        field("baseline_peak_rss_bytes", baseline_peak_rss);
        field("post_construct_peak_rss_bytes", post_construct_peak_rss);
        field("process_peak_rss_bytes", process_peak_rss);
        field("input_bytes", input_bytes); field("consumed_bytes", wire.consumed_bytes);
        field("messages", wire.messages); field("records", wire.records);
        field("end_records", wire.end_records); field("after_end", wire.after_end);
        field("unknown_type", wire.unknown_type); field("bad_length", wire.bad_length);
        field("trailing_bytes", input_bytes - wire.consumed_bytes);
        field("unknown_ref", anomalies.unknown_ref); field("duplicate_ref", anomalies.duplicate_ref);
        field("share_underflow", anomalies.share_underflow); field("capacity", anomalies.capacity);
        field("invalid_side", invalid.invalid_side); field("locate_mismatch", invalid.locate_mismatch);
        field("peak_orders", peak_orders); field("final_orders", final_orders);
        field("adds", stats.adds); field("executions", stats.executions);
        field("executed_shares", stats.executed_shares);
        field("non_printable_shares", stats.non_printable_shares);
        field("trade_shares", stats.trade_shares); field("cross_shares", stats.cross_shares);
        field("broken_trades", stats.broken_trades);
        std::printf(",\n  \"rss_scope\": \"%s\",\n  \"timing_scope\": \"%s\",\n"
                    "  \"book_hash\": \"%016llx\",\n  \"state_hash\": \"%016llx\",\n"
                    "  \"end_of_messages\": %s,\n  \"preflight_passed\": %s,\n"
                    "  \"replay_performed\": %s,\n  \"passed\": %s\n}\n",
                    memory ? "whole process including book, allocator and streaming buffer; excludes mapped input; not index-only"
                           : "whole process including prefaulted mapped input; not index-only",
                    memory ? "stream I/O, wire validation, framing and dispatch; not a replay benchmark"
                           : "framing and BookBuilder dispatch only; excludes construction, mmap/prefault, wire preflight, hashing and teardown",
                    static_cast<unsigned long long>(book_hash), static_cast<unsigned long long>(state_hash),
                    stats.end_of_messages ? "true" : "false", preflight_passed ? "true" : "false",
                    replay_performed ? "true" : "false", passed ? "true" : "false");
        if (std::fflush(stdout) != 0 || std::ferror(stdout)) {
            throw std::runtime_error("cannot finish storage benchmark summary");
        }
        return passed ? 0 : 1;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_storage_bench: %s\n", e.what());
        return 1;
    }
}
