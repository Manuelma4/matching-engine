// Bounded synthetic queue-model CLI. This consumes normalised, fixed-level traces,
// never raw ITCH, and writes an auditable hypothetical run without a fill-accuracy claim.
#include <array>
#include <cerrno>
#include <charconv>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>
#include <vector>

#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

#include "itch/queue_sim.hpp"
#include "cli.hpp"

namespace {

namespace queue = itch::queue;

struct Arguments {
    queue::Config config;
    std::string input;
    std::string audit;
};

std::uint32_t bounded_value(std::string_view option, std::string_view value, bool zero = false) {
    const auto parsed = itch::tools::number<std::uint32_t>(option, value, zero);
    if (parsed > queue::kValueLimit) {
        throw std::invalid_argument(std::string(option) + ": value exceeds one-billion model bound");
    }
    return parsed;
}

std::int32_t fee(std::string_view value) {
    std::int32_t parsed{};
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (value.empty() || error != std::errc{} || end != value.data() + value.size() ||
        parsed < -static_cast<std::int32_t>(queue::kValueLimit) ||
        parsed > static_cast<std::int32_t>(queue::kValueLimit)) {
        throw std::invalid_argument("--fee4: expected signed integer with magnitude at most one billion");
    }
    return parsed;
}

Arguments arguments(int argc, char** argv) {
    Arguments result;
    std::set<std::string_view> seen;
    bool positional = false;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg = argv[i];
        if (!positional && arg == "--") {
            positional = true;
            continue;
        }
        if (!positional && arg.starts_with('-')) {
            if (arg != "--side" && arg != "--price4" && arg != "--quantity" &&
                arg != "--decision-ns" && arg != "--horizon-ns" && arg != "--feed-delay-ns" &&
                arg != "--order-delay-ns" && arg != "--response-delay-ns" &&
                arg != "--cancel-model" && arg != "--cancel-ns" && arg != "--fee4" &&
                arg != "--audit") {
                throw std::invalid_argument("unknown option: " + std::string(arg));
            }
            if (!seen.insert(arg).second) {
                throw std::invalid_argument("duplicate option: " + std::string(arg));
            }
            if (++i == argc) throw std::invalid_argument(std::string(arg) + ": missing value");
            const std::string_view value = argv[i];
            if (arg == "--side") {
                if (value == "buy") result.config.side = queue::Side::Buy;
                else if (value == "sell") result.config.side = queue::Side::Sell;
                else throw std::invalid_argument("--side: expected buy or sell");
            } else if (arg == "--cancel-model") {
                if (value == "optimistic") result.config.cancel_model = queue::CancelModel::Optimistic;
                else if (value == "conservative") result.config.cancel_model = queue::CancelModel::Conservative;
                else throw std::invalid_argument("--cancel-model: expected optimistic or conservative");
            } else if (arg == "--audit") {
                result.audit = value;
            } else if (arg == "--price4") result.config.price4 = bounded_value(arg, value);
            else if (arg == "--quantity") result.config.quantity = bounded_value(arg, value);
            else if (arg == "--fee4") result.config.fee4 = fee(value);
            else {
                const auto time = itch::tools::number<queue::Time>(arg, value, true);
                if (arg == "--decision-ns") result.config.decision_ns = time;
                else if (arg == "--horizon-ns") result.config.horizon_ns = time;
                else if (arg == "--feed-delay-ns") result.config.feed_delay_ns = time;
                else if (arg == "--order-delay-ns") result.config.order_delay_ns = time;
                else if (arg == "--response-delay-ns") result.config.response_delay_ns = time;
                else result.config.cancel_ns = time;
            }
        } else {
            if (!result.input.empty()) throw std::invalid_argument("expected one trace input path");
            result.input = arg;
        }
    }
    for (std::string_view required : {"--side", "--price4", "--quantity", "--decision-ns",
            "--horizon-ns", "--feed-delay-ns", "--order-delay-ns", "--response-delay-ns",
            "--cancel-model", "--audit"}) {
        if (!seen.contains(required)) {
            throw std::invalid_argument("required option missing: " + std::string(required));
        }
    }
    if (result.input.empty() || result.input == "-" || result.audit.empty() || result.audit == "-") {
        throw std::invalid_argument("regular trace input and fresh audit file paths are required");
    }
    return result;
}

bool same_identity(const struct stat& before, const struct stat& after) {
    const bool common = before.st_dev == after.st_dev && before.st_ino == after.st_ino &&
        before.st_size == after.st_size;
#if defined(__APPLE__)
    return common && before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec &&
        before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec &&
        before.st_ctimespec.tv_sec == after.st_ctimespec.tv_sec &&
        before.st_ctimespec.tv_nsec == after.st_ctimespec.tv_nsec;
#else
    return common && before.st_mtim.tv_sec == after.st_mtim.tv_sec &&
        before.st_mtim.tv_nsec == after.st_mtim.tv_nsec &&
        before.st_ctim.tv_sec == after.st_ctim.tv_sec && before.st_ctim.tv_nsec == after.st_ctim.tv_nsec;
#endif
}

class Input {
public:
    explicit Input(std::string path) : path_(std::move(path)) {
        const int fd = ::open(path_.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd < 0) throw std::system_error(errno, std::generic_category(), "cannot open trace input");
        if (::fstat(fd, &original_) != 0) {
            const int error = errno;
            ::close(fd);
            throw std::system_error(error, std::generic_category(), "cannot stat trace input");
        }
        if (!S_ISREG(original_.st_mode) || original_.st_size < 0) {
            ::close(fd);
            throw std::invalid_argument("trace input must be a regular file");
        }
        file_ = ::fdopen(fd, "rb");
        if (!file_) {
            const int error = errno;
            ::close(fd);
            throw std::system_error(error, std::generic_category(), "cannot open trace stream");
        }
    }
    ~Input() { if (file_) std::fclose(file_); }
    Input(const Input&) = delete;
    Input& operator=(const Input&) = delete;
    bool line(std::string& value) {
        value.clear();
        for (;;) {
            const int c = std::fgetc(file_);
            if (c == EOF) {
                if (std::ferror(file_)) {
                    throw std::system_error(errno ? errno : EIO, std::generic_category(),
                                            "cannot read trace stream");
                }
                if (value.empty()) return false;
                break;
            }
            ++read_bytes_;
            if (c == '\n') break;
            if (value.size() == 128) throw std::invalid_argument("trace line exceeds 128 bytes");
            value.push_back(static_cast<char>(c));
        }
        if (!value.empty() && value.back() == '\r') value.pop_back();
        return true;
    }
    void unchanged() const {
        struct stat current{}, named{};
        if (::fstat(::fileno(file_), &current) != 0 || ::stat(path_.c_str(), &named) != 0 ||
            !same_identity(original_, current) || !same_identity(original_, named) ||
            read_bytes_ != static_cast<std::uint64_t>(original_.st_size)) {
            throw std::runtime_error("trace input identity changed during reading or simulation");
        }
    }
    std::uint64_t bytes() const { return read_bytes_; }
private:
    std::string path_;
    std::FILE* file_ = nullptr;
    struct stat original_{};
    std::uint64_t read_bytes_ = 0;
};

std::vector<queue::MarketEvent> read_events(Input& input) {
    std::string line;
    if (!input.line(line) || line != "timestamp_ns,kind,quantity,opposite_price4") {
        throw std::invalid_argument("trace header must exactly match timestamp_ns,kind,quantity,opposite_price4");
    }
    std::vector<queue::MarketEvent> events;
    while (input.line(line)) {
        if (events.size() == queue::kMaxMarketEvents) {
            throw std::invalid_argument("trace exceeds 100000 market rows");
        }
        std::array<std::string_view, 4> fields;
        const std::string_view row = line;
        std::size_t start = 0;
        for (std::size_t i = 0; i < fields.size(); ++i) {
            const auto comma = row.find(',', start);
            if ((i != fields.size() - 1 && comma == std::string_view::npos) ||
                (i == fields.size() - 1 && comma != std::string_view::npos)) {
                throw std::invalid_argument("trace row must have exactly four columns");
            }
            const auto end = comma == std::string_view::npos ? row.size() : comma;
            fields[i] = row.substr(start, end - start);
            start = end + 1;
        }
        queue::MarketEvent event;
        event.timestamp_ns = itch::tools::number<queue::Time>("timestamp_ns", fields[0], true);
        if (fields[1] == "seed") event.kind = queue::MarketKind::Seed;
        else if (fields[1] == "add") event.kind = queue::MarketKind::Add;
        else if (fields[1] == "cancel") event.kind = queue::MarketKind::Cancel;
        else if (fields[1] == "trade") event.kind = queue::MarketKind::Trade;
        else if (fields[1] == "quote") event.kind = queue::MarketKind::Quote;
        else throw std::invalid_argument("trace kind must be seed, add, cancel, trade or quote");
        event.quantity = bounded_value("quantity", fields[2], true);
        event.opposite_price4 = bounded_value("opposite_price4", fields[3], true);
        events.push_back(event);
    }
    input.unchanged();
    return events;
}

class Audit {
public:
    explicit Audit(const std::string& path) : file_(std::fopen(path.c_str(), "wx")) {
        if (!file_) throw std::system_error(errno, std::generic_category(), "cannot create fresh audit file");
    }
    ~Audit() { if (file_) std::fclose(file_); }
    Audit(const Audit&) = delete;
    Audit& operator=(const Audit&) = delete;
    void write(const std::vector<queue::TraceRow>& trace) {
        if (std::fprintf(file_, "time_ns,origin_ns,phase,serial,event,source_index,event_quantity,"
                     "external_quantity,opposite_price4,ahead,remaining,"
                     "exchange_state,exchange_filled,exchange_position,exchange_cash4,exchange_fees4,observed,"
                     "observed_timestamp_ns,observed_quantity,observed_opposite_price4,known_remaining,"
                     "local_state,local_filled,local_position,local_cash4,local_fees4\n") < 0) {
            throw std::runtime_error("cannot write audit header");
        }
        for (const auto& row : trace) {
            const auto exchange_name = queue::name(row.exchange_state);
            const auto local_name = queue::name(row.local_state);
            if (std::fprintf(file_, "%llu,%llu,%u,%llu,%.*s,%zu,%u,%u,%u,%u,%u,%.*s,%u,%lld,%lld,%lld,%u,%llu,%u,%u,%u,"
                             "%.*s,%u,%lld,%lld,%lld\n",
                    static_cast<unsigned long long>(row.time_ns),
                    static_cast<unsigned long long>(row.origin_ns), row.phase,
                    static_cast<unsigned long long>(row.serial),
                    static_cast<int>(row.event.size()), row.event.data(), row.source_index,
                    row.event_quantity, row.external_quantity, row.opposite_price4, row.ahead, row.remaining,
                    static_cast<int>(exchange_name.size()), exchange_name.data(), row.exchange.filled,
                    static_cast<long long>(row.exchange.position), static_cast<long long>(row.exchange.cash4),
                    static_cast<long long>(row.exchange.fees4), row.observed ? 1u : 0u,
                    static_cast<unsigned long long>(row.observed_timestamp_ns),
                    row.observed_quantity, row.observed_opposite_price4, row.known_remaining,
                    static_cast<int>(local_name.size()), local_name.data(), row.local.filled,
                    static_cast<long long>(row.local.position), static_cast<long long>(row.local.cash4),
                    static_cast<long long>(row.local.fees4)) < 0) {
                throw std::runtime_error("cannot write audit row");
            }
        }
    }
    void close() {
        auto* file = file_;
        file_ = nullptr;
        const bool failed = std::ferror(file) != 0;
        if (std::fclose(file) != 0 || failed) {
            throw std::system_error(errno ? errno : EIO, std::generic_category(), "cannot finish audit file");
        }
    }
private:
    std::FILE* file_;
};

void account(std::string_view field, const queue::Account& value) {
    std::printf("  \"%.*s\": {\"filled\": %u, \"position\": %lld, \"cash4\": %lld, \"fees4\": %lld},\n",
                static_cast<int>(field.size()), field.data(), value.filled,
                static_cast<long long>(value.position), static_cast<long long>(value.cash4),
                static_cast<long long>(value.fees4));
}

void report(const Arguments& args, const queue::Result& result, std::size_t events, std::uint64_t bytes) {
    const auto side = queue::name(args.config.side);
    const auto cancellation = queue::name(args.config.cancel_model);
    std::printf("{\n  \"schema_version\": 1,\n  \"model\": \"synthetic_shadow_single_level_v1\",\n"
                "  \"side\": \"%.*s\",\n  \"cancel_model\": \"%.*s\",\n"
                "  \"price4\": %u,\n  \"quantity\": %u,\n  \"fee4\": %d,\n",
                static_cast<int>(side.size()), side.data(), static_cast<int>(cancellation.size()),
                cancellation.data(), args.config.price4, args.config.quantity, args.config.fee4);
    const auto number = [](const char* field, std::uint64_t value) {
        std::printf("  \"%s\": %llu,\n", field, static_cast<unsigned long long>(value));
    };
    number("decision_ns", args.config.decision_ns); number("horizon_ns", args.config.horizon_ns);
    number("feed_delay_ns", args.config.feed_delay_ns); number("order_delay_ns", args.config.order_delay_ns);
    number("response_delay_ns", args.config.response_delay_ns);
    if (args.config.cancel_ns) number("cancel_ns", *args.config.cancel_ns);
    else std::printf("  \"cancel_ns\": null,\n");
    number("market_events", events); number("input_bytes", bytes); number("audit_rows", result.trace.size());
    number("remaining", result.remaining); number("known_remaining", result.known_remaining);
    number("ahead", result.ahead); number("pending_events", result.pending_events);
    account("exchange", result.exchange); account("local", result.local);
    const auto exchange_state = queue::name(result.exchange_state);
    const auto local_state = queue::name(result.local_state);
    std::printf("  \"exchange_state\": \"%.*s\",\n  \"local_state\": \"%.*s\",\n"
                "  \"submitted\": %s,\n  \"cancel_requested\": %s,\n",
                static_cast<int>(exchange_state.size()), exchange_state.data(),
                static_cast<int>(local_state.size()), local_state.data(),
                result.submitted ? "true" : "false", result.cancel_requested ? "true" : "false");
    if (result.local_marked_equity_twice4) {
        std::printf("  \"local_marked_equity_twice4\": %lld,\n",
                    static_cast<long long>(*result.local_marked_equity_twice4));
    } else std::printf("  \"local_marked_equity_twice4\": null,\n");
    std::printf("  \"source_identity_stable\": true,\n  \"passed\": true\n}\n");
    if (std::fflush(stdout) != 0 || std::ferror(stdout)) {
        throw std::runtime_error("cannot finish queue simulation summary");
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const auto args = arguments(argc, argv);
        Input input(args.input);
        const auto events = read_events(input);
        const auto result = queue::simulate(events, args.config);
        input.unchanged();
        Audit audit(args.audit);
        audit.write(result.trace);
        audit.close();
        input.unchanged();
        report(args, result, events.size(), input.bytes());
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_queue_sim: %s\nusage: itch_queue_sim --side buy|sell --price4 N "
                     "--quantity N --decision-ns N --horizon-ns N --feed-delay-ns N --order-delay-ns N "
                     "--response-delay-ns N --cancel-model optimistic|conservative [--cancel-ns N] "
                     "[--fee4 SIGNED] --audit FRESH.csv TRACE.csv\n", e.what());
        return 1;
    }
}
