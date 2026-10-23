// Strict displayed-history projection. This exports external observations, not fills.
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <limits>
#include <set>
#include <stdexcept>
#include <string>
#include <string_view>
#include <system_error>
#include <utility>

#include <fcntl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#include "itch/queue_window.hpp"
#include "cli.hpp"

namespace {

namespace queue = itch::queue;

struct Arguments {
    queue::WindowConfig window;
    itch::L3Book::Config book;
    std::string input, output, provenance;
};

Arguments arguments(int argc, char** argv) {
    Arguments result;
    std::set<std::string_view> seen;
    bool positional = false;
    for (int i = 1; i < argc; ++i) {
        const std::string_view arg = argv[i];
        if (!positional && arg == "--") { positional = true; continue; }
        if (!positional && arg.starts_with('-')) {
            if (arg != "--symbol" && arg != "--side" && arg != "--price4" &&
                arg != "--start-ns" && arg != "--end-ns" && arg != "--out" &&
                arg != "--provenance" && arg != "--max-orders")
                throw std::invalid_argument("unknown option: " + std::string(arg));
            if (!seen.insert(arg).second)
                throw std::invalid_argument("duplicate option: " + std::string(arg));
            if (++i == argc) throw std::invalid_argument(std::string(arg) + ": missing value");
            const std::string_view value = argv[i];
            if (arg == "--symbol") result.window.symbol = value;
            else if (arg == "--side") {
                if (value == "buy") result.window.side = queue::Side::Buy;
                else if (value == "sell") result.window.side = queue::Side::Sell;
                else throw std::invalid_argument("--side: expected buy or sell");
            } else if (arg == "--out") result.output = value;
            else if (arg == "--provenance") result.provenance = value;
            else if (arg == "--price4") {
                result.window.price4 = itch::tools::number<std::uint32_t>(arg, value);
                if (result.window.price4 > queue::kValueLimit)
                    throw std::invalid_argument("--price4: value exceeds one-billion model bound");
            } else if (arg == "--start-ns") {
                result.window.start_ns = itch::tools::number<queue::Time>(arg, value, true);
            } else if (arg == "--end-ns") {
                result.window.end_ns = itch::tools::number<queue::Time>(arg, value, true);
            } else {
                result.book.max_orders = itch::tools::number<std::uint32_t>(arg, value);
                result.book.max_levels = std::min(result.book.max_levels, result.book.max_orders);
            }
        } else {
            if (!result.input.empty()) throw std::invalid_argument("expected one raw input path");
            result.input = arg;
        }
    }
    for (std::string_view required : {"--symbol", "--side", "--price4", "--start-ns",
                                      "--end-ns", "--out", "--provenance"}) {
        if (!seen.contains(required))
            throw std::invalid_argument("required option missing: " + std::string(required));
    }
    if (result.window.symbol.empty() || result.window.symbol.size() > 8)
        throw std::invalid_argument("--symbol: expected one to eight ticker characters");
    for (char character : result.window.symbol) {
        const auto c = static_cast<unsigned char>(character);
        if (!((c >= 'A' && c <= 'Z') || (c >= '0' && c <= '9') ||
              c == '.' || c == '-' || c == '^' || c == '/'))
            throw std::invalid_argument("--symbol: expected uppercase letters, digits or .-^/");
    }
    if (result.window.start_ns >= result.window.end_ns)
        throw std::invalid_argument("window requires start-ns < end-ns");
    if (result.input.empty() || result.input == "-" || result.output.empty() ||
        result.output == "-" || result.provenance.empty() || result.provenance == "-")
        throw std::invalid_argument("regular input and two fresh output paths are required");
    if (result.output == result.provenance)
        throw std::invalid_argument("normalised and provenance paths must be distinct");
    return result;
}

bool same_identity(const struct stat& a, const struct stat& b) {
    const bool common = a.st_dev == b.st_dev && a.st_ino == b.st_ino && a.st_size == b.st_size;
#if defined(__APPLE__)
    return common && a.st_mtimespec.tv_sec == b.st_mtimespec.tv_sec &&
        a.st_mtimespec.tv_nsec == b.st_mtimespec.tv_nsec &&
        a.st_ctimespec.tv_sec == b.st_ctimespec.tv_sec &&
        a.st_ctimespec.tv_nsec == b.st_ctimespec.tv_nsec;
#else
    return common && a.st_mtim.tv_sec == b.st_mtim.tv_sec && a.st_mtim.tv_nsec == b.st_mtim.tv_nsec &&
        a.st_ctim.tv_sec == b.st_ctim.tv_sec && a.st_ctim.tv_nsec == b.st_ctim.tv_nsec;
#endif
}

// Map the same checked descriptor: no second path-based open can select other bytes.
class Input {
public:
    explicit Input(std::string path) : path_(std::move(path)) {
        fd_ = ::open(path_.c_str(), O_RDONLY | O_NONBLOCK | O_CLOEXEC);
        if (fd_ < 0) throw std::system_error(errno, std::generic_category(), "cannot open raw input");
        if (::fstat(fd_, &identity_) != 0) {
            const int error = errno; ::close(fd_);
            throw std::system_error(error, std::generic_category(), "cannot stat raw input");
        }
        if (!S_ISREG(identity_.st_mode) || identity_.st_size <= 0 ||
            static_cast<std::uintmax_t>(identity_.st_size) >
                static_cast<std::uintmax_t>(std::numeric_limits<std::ptrdiff_t>::max())) {
            ::close(fd_);
            throw std::invalid_argument("raw input must be a nonempty regular file fitting the address space");
        }
        size_ = static_cast<std::size_t>(identity_.st_size);
        void* mapped = ::mmap(nullptr, size_, PROT_READ, MAP_PRIVATE, fd_, 0);
        if (mapped == MAP_FAILED) {
            const int error = errno; ::close(fd_);
            throw std::system_error(error, std::generic_category(), "cannot map raw input");
        }
        data_ = static_cast<const unsigned char*>(mapped);
        try { unchanged(); }
        catch (...) { ::munmap(const_cast<unsigned char*>(data_), size_); ::close(fd_); throw; }
    }
    ~Input() { ::munmap(const_cast<unsigned char*>(data_), size_); ::close(fd_); }
    Input(const Input&) = delete;
    Input& operator=(const Input&) = delete;
    itch::Bytes bytes() const { return {data_, size_}; }
    void unchanged() const {
        struct stat current{}, named{};
        if (::fstat(fd_, &current) != 0 || ::stat(path_.c_str(), &named) != 0 ||
            !same_identity(identity_, current) || !same_identity(identity_, named))
            throw std::runtime_error("raw input identity changed during projection or output");
    }
private:
    std::string path_;
    int fd_ = -1;
    struct stat identity_{};
    const unsigned char* data_ = nullptr;
    std::size_t size_ = 0;
};

// A failed pair creation/write removes only the new files still owned by this run.
class Output {
public:
    explicit Output(std::string path) : path_(std::move(path)), file_(std::fopen(path_.c_str(), "wx")) {
        if (!file_) throw std::system_error(errno, std::generic_category(), "cannot create fresh output");
        if (::fstat(::fileno(file_), &identity_) != 0) {
            const int error = errno; std::fclose(file_); file_ = nullptr;
            throw std::system_error(error, std::generic_category(), "cannot stat fresh output");
        }
    }
    ~Output() {
        if (file_) std::fclose(file_);
        if (!keep_) {
            struct stat current{};
            if (::lstat(path_.c_str(), &current) == 0 && S_ISREG(current.st_mode) &&
                current.st_dev == identity_.st_dev && current.st_ino == identity_.st_ino)
                (void)::unlink(path_.c_str());
        }
    }
    Output(const Output&) = delete;
    Output& operator=(const Output&) = delete;
    std::FILE* get() const { return file_; }
    void close() {
        auto* file = file_; file_ = nullptr;
        const bool failed = std::ferror(file) != 0;
        if (std::fclose(file) != 0 || failed)
            throw std::system_error(errno ? errno : EIO, std::generic_category(), "cannot finish output file");
    }
    void keep() { keep_ = true; }
private:
    std::string path_;
    std::FILE* file_;
    struct stat identity_{};
    bool keep_ = false;
};

void normalised(std::FILE* file, const queue::WindowResult& result) {
    if (std::fprintf(file, "timestamp_ns,kind,quantity,opposite_price4\n") < 0)
        throw std::runtime_error("cannot write normalised header");
    for (const auto& e : result.events) {
        const auto kind = queue::name(e.kind);
        if (std::fprintf(file, "%llu,%.*s,%u,%u\n", static_cast<unsigned long long>(e.timestamp_ns),
                         static_cast<int>(kind.size()), kind.data(), e.quantity, e.opposite_price4) < 0)
            throw std::runtime_error("cannot write normalised row");
    }
}

void provenance(std::FILE* file, const queue::WindowResult& result) {
    if (std::fprintf(file, "sequence,frame_offset,timestamp_ns,body_bytes,type,reason,reference,"
                     "new_reference,match,before_quantity,before_opposite_price4,before_opposite_quantity,"
                     "after_quantity,after_opposite_price4,after_opposite_quantity,normalised_row\n") < 0)
        throw std::runtime_error("cannot write provenance header");
    for (const auto& row : result.observations) {
        const auto reason = queue::name(row.reason);
        const auto& p = row.source;
        if (std::fprintf(file, "%llu,%llu,%llu,%u,%c,%.*s,%llu,%llu,%llu,%u,%u,%u,%u,%u,%u,%u\n",
            static_cast<unsigned long long>(p.sequence), static_cast<unsigned long long>(p.frame_offset),
            static_cast<unsigned long long>(p.timestamp_ns), static_cast<unsigned>(p.body_bytes), p.type,
            static_cast<int>(reason.size()), reason.data(), static_cast<unsigned long long>(row.reference),
            static_cast<unsigned long long>(row.new_reference), static_cast<unsigned long long>(row.match),
            row.before_quantity, row.before_opposite_price4, row.before_opposite_quantity, row.after_quantity,
            row.after_opposite_price4, row.after_opposite_quantity, row.normalised_row) < 0)
            throw std::runtime_error("cannot write provenance row");
    }
}

void json_string(std::string_view value) {
    std::putchar('"');
    for (char character : value) {
        const auto c = static_cast<unsigned char>(character);
        if (c == '"' || c == '\\') { std::putchar('\\'); std::putchar(c); }
        else if (c < 32 || c >= 127) std::printf("\\u%04x", static_cast<unsigned>(c));
        else std::putchar(c);
    }
    std::putchar('"');
}

void point(const queue::SourcePoint& p) {
    std::printf("{\"sequence\": %llu, \"frame_offset\": %llu, \"timestamp_ns\": %llu, "
                "\"body_bytes\": %u, \"type\": ", static_cast<unsigned long long>(p.sequence),
                static_cast<unsigned long long>(p.frame_offset),
                static_cast<unsigned long long>(p.timestamp_ns), static_cast<unsigned>(p.body_bytes));
    json_string(std::string_view(&p.type, 1)); std::putchar('}');
}

void counts(const std::array<std::uint64_t, 256>& values) {
    std::putchar('{');
    bool first = true;
    for (std::size_t i = 0; i < values.size(); ++i) {
        if (values[i] == 0) continue;
        if (!first) std::printf(", ");
        first = false;
        const char type = static_cast<char>(i);
        json_string(std::string_view(&type, 1));
        std::printf(": %llu", static_cast<unsigned long long>(values[i]));
    }
    std::putchar('}');
}

void report(const Arguments& args, const queue::WindowResult& result) {
    std::printf("{\n  \"schema_version\": 1,\n  \"model\": \"strict_displayed_window_v1\",\n  \"symbol\": ");
    json_string(result.config.symbol);
    const auto side = queue::name(result.config.side);
    std::printf(",\n  \"side\": \"%.*s\",\n  \"price4\": %u", static_cast<int>(side.size()),
                side.data(), result.config.price4);
    const auto number = [](const char* name, std::uint64_t value) {
        std::printf(",\n  \"%s\": %llu", name, static_cast<unsigned long long>(value));
    };
    number("start_ns", result.config.start_ns); number("end_ns", result.config.end_ns);
    number("max_orders", args.book.max_orders); number("max_levels", args.book.max_levels);
    number("locate", result.locate); number("source_messages", result.source_messages);
    number("source_end_records", result.source_end_records); number("source_bytes", result.source_bytes);
    number("reconciled_messages", result.reconciled_messages);
    number("displayed_executed_shares", result.displayed_executed_shares);
    number("final_quantity", result.final_quantity); number("final_opposite_price4", result.final_opposite_price4);
    number("final_opposite_quantity", result.final_opposite_quantity);
    number("normalised_rows", result.events.size()); number("provenance_rows", result.observations.size());
    std::printf(",\n  \"source_type_counts\": "); counts(result.source_type_counts);
    std::printf(",\n  \"window_type_counts\": "); counts(result.window_type_counts);
    std::printf(",\n  \"eligibility\": {\n    \"directory\": "); point(result.eligibility.directory);
    std::printf(",\n    \"trading_action\": "); point(result.eligibility.trading_action);
    std::printf(",\n    \"market_hours\": "); point(result.eligibility.market_hours);
    std::printf(",\n    \"opening_cross\": "); point(result.eligibility.opening_cross);
    std::printf(",\n    \"operational\": ");
    if (result.eligibility.operational) point(*result.eligibility.operational);
    else std::printf("null");
    std::printf(",\n    \"operational_action\": ");
    json_string(std::string_view(&result.eligibility.operational_action, 1));
    std::printf(",\n    \"retail_interest\": ");
    json_string(std::string_view(&result.eligibility.retail_interest, 1));
    std::printf("\n  },\n  \"source_identity_stable\": true,\n  \"passed\": true\n}\n");
    if (std::fflush(stdout) != 0 || std::ferror(stdout))
        throw std::runtime_error("cannot finish window summary");
}

} // namespace

int main(int argc, char** argv) {
    try {
        const auto args = arguments(argc, argv);
        Input input(args.input);
        queue::WindowProjector projector(args.window, args.book);
        std::uint64_t offset = 0;
        const auto used = itch::walk_frames(input.bytes(), [&](itch::Bytes message) {
            projector.consume(message, offset);
            offset += message.size() + 2;
        });
        if (used != input.bytes().size()) throw std::invalid_argument("raw input has a trailing partial frame");
        const auto result = projector.finish(input.bytes().size());
        input.unchanged();
        Output output(args.output);
        Output origins(args.provenance);
        normalised(output.get(), result);
        provenance(origins.get(), result);
        output.close(); origins.close();
        input.unchanged();
        output.keep(); origins.keep();
        report(args, result);
        return 0;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_queue_window: %s\nusage: itch_queue_window --symbol TICKER "
                     "--side buy|sell --price4 N --start-ns N --end-ns N --out FRESH.csv "
                     "--provenance FRESH.csv [--max-orders N] RAW.itch\n", e.what());
        return 1;
    }
}
