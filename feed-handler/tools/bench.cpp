// itch_bench: per-layer replay cost of an ITCH 5.0 BinaryFILE, measured on a memory-mapped,
// pre-faulted file so disk and page faults are excluded.
//
//   itch_bench [--runs N] <file>
//
// Layers, each timed separately over the whole file:
//   framing   walk the 2-byte length prefixes only
//   dispatch  framing + message-type dispatch to an empty handler
//   replay    framing + dispatch + full L3 book maintenance (BookBuilder)
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <limits>
#include <memory>
#include <string>
#include <string_view>
#include <vector>

#if defined(__APPLE__)
#include <pthread/qos.h>
#endif

#include "itch/replay.hpp"
#include "cli.hpp"

namespace {

struct EmptyHandler {
    std::uint64_t seen = 0;
    void on_other(itch::Header) { ++seen; }
};

template <class Run>
std::vector<double> time_runs(int runs, Run&& run) {
    std::vector<double> seconds;
    for (int i = 0; i < runs; ++i) {
        const auto start = std::chrono::steady_clock::now();
        run();
        seconds.push_back(
            std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count());
    }
    std::sort(seconds.begin(), seconds.end());
    return seconds;
}

void report(const char* layer, const std::vector<double>& s, std::uint64_t messages) {
    const double median = s[s.size() / 2];
    const auto rate = [&](double sec) { return static_cast<double>(messages) / sec / 1e6; };
    std::printf("%-9s %7.1f M msg/s (%.1f-%.1f)  %6.1f ns/msg\n", layer, rate(median),
                rate(s.back()), rate(s.front()), median * 1e9 / static_cast<double>(messages));
}

}  // namespace

int main(int argc, char** argv) {
#if defined(__APPLE__)
    pthread_set_qos_class_self_np(QOS_CLASS_USER_INTERACTIVE, 0);
#endif
    unsigned int runs = 5;
    std::string path;
    try {
        bool positional = false;
        for (int i = 1; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (!positional && arg == "--") {
                positional = true;
            } else if (!positional && arg == "--runs") {
                if (++i == argc) {
                    throw std::invalid_argument("--runs: missing value");
                }
                runs = itch::tools::number<unsigned int>(arg, argv[i]);
                if (runs > static_cast<unsigned int>(std::numeric_limits<int>::max())) {
                    throw std::invalid_argument("--runs: integer out of range");
                }
            } else if (!positional && arg.starts_with('-')) {
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
        std::fprintf(stderr, "itch_bench: %s\nusage: itch_bench [--runs N] <file>\n", e.what());
        return 2;
    }

    try {
        itch::MappedFile file(path);
        file.prefault();
        const itch::Bytes bytes = file.bytes();

        std::uint64_t messages = 0;
        bool ended = false;
        EmptyHandler validation;
        const std::size_t used = itch::walk_frames(bytes, [&](itch::Bytes m) {
            if (ended) {
                throw std::runtime_error("record after BinaryFILE end marker");
            }
            if (m.empty()) {
                ended = true;
                return;
            }
            ++messages;
            const auto result = itch::dispatch(m, validation);
            if (result == itch::Dispatch::UnknownType || result == itch::Dispatch::BadLength) {
                throw std::runtime_error("unknown message type or incorrect message length");
            }
        });
        if (used != bytes.size()) {
            throw std::runtime_error("truncated input frame");
        }
        if (messages == 0) {
            throw std::runtime_error("input contains no ITCH messages");
        }
        std::printf("%s: %zu bytes, %llu messages, %u runs per layer (median, range)\n\n",
                    path.c_str(), bytes.size(), static_cast<unsigned long long>(messages), runs);

        std::uint64_t sink = 0;
        report("framing", time_runs(static_cast<int>(runs), [&] {
                   itch::walk_frames(bytes, [&](itch::Bytes m) {
                       if (!m.empty()) {
                           sink += m[0];
                       }
                   });
               }),
               messages);

        report("dispatch", time_runs(static_cast<int>(runs), [&] {
                   EmptyHandler h;
                   itch::walk_frames(bytes, [&](itch::Bytes m) { itch::dispatch(m, h); });
                   sink += h.seen;
               }),
               messages);

        std::uint64_t hash = 0;
        std::size_t peak = 0;
        std::vector<double> replay_seconds;
        for (unsigned int i = 0; i < runs; ++i) {
            // Construction writes/pre-faults the pools before the clock starts. Hashing,
            // validation and destruction also stay outside the replay interval.
            auto builder = std::make_unique<itch::BookBuilder>();
            const auto start = std::chrono::steady_clock::now();
            itch::walk_frames(bytes, [&](itch::Bytes m) { itch::dispatch(m, *builder); });
            replay_seconds.push_back(
                std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count());
            const auto& a = builder->book().anomalies();
            const auto& invalid = builder->invalid_messages();
            if (a.unknown_ref || a.duplicate_ref || a.share_underflow || a.capacity ||
                invalid.invalid_side || invalid.locate_mismatch) {
                throw std::runtime_error("book anomalies: refusing to benchmark an invalid replay");
            }
            const std::uint64_t current_hash = builder->book_hash();
            if (i != 0 && current_hash != hash) {
                throw std::runtime_error("book hash changed between replay runs");
            }
            hash = current_hash;
            peak = builder->book().peak_orders();
        }
        std::sort(replay_seconds.begin(), replay_seconds.end());
        report("replay", replay_seconds, messages);
        std::printf("\npeak orders %zu, book hash %016llx (sink %llu)\n", peak,
                    static_cast<unsigned long long>(hash), static_cast<unsigned long long>(sink));
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_bench: %s\n", e.what());
        return 1;
    }
    return 0;
}
