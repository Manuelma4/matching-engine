// Replay an observed-wire journal, or its raw BinaryFILE source, through the same
// reconstruction core. Checkpoints are post-message, in source order, never sorted.
#include <algorithm>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <memory>
#include <string>
#include <string_view>
#include <system_error>

#include "itch/journal.hpp"
#include "itch/replay.hpp"
#include "cli.hpp"
#include "source.hpp"

namespace {

class Output {
public:
    explicit Output(const std::string& path) : file_(std::fopen(path.c_str(), "wx")) {
        if (!file_) throw std::system_error(errno, std::generic_category(), "cannot create " + path);
    }
    ~Output() { if (file_) std::fclose(file_); }
    Output(const Output&) = delete;
    Output& operator=(const Output&) = delete;
    std::FILE* get() const { return file_; }
    void close() {
        auto* file = file_;
        file_ = nullptr;
        const bool failed = std::ferror(file) != 0;
        if (std::fclose(file) != 0 || failed) {
            throw std::system_error(errno ? errno : EIO, std::generic_category(),
                                    "cannot finish checkpoint output");
        }
    }
private:
    std::FILE* file_;
};

std::string hex(const std::array<unsigned char, 32>& digest) {
    constexpr char alphabet[] = "0123456789abcdef";
    std::string result;
    for (unsigned char c : digest) {
        result += alphabet[c >> 4];
        result += alphabet[c & 15];
    }
    return result;
}

}  // namespace

int main(int argc, char** argv) {
    std::string path, checkpoints_path;
    bool raw = false, allow_partial = false;
    std::uint64_t checkpoint_every = 10'000'000;
    itch::L3Book::Config cfg;
    try {
        bool positional = false;
        for (int i = 1; i < argc; ++i) {
            const std::string_view arg = argv[i];
            if (!positional && arg == "--") positional = true;
            else if (!positional && arg == "--raw") raw = true;
            else if (!positional && arg == "--allow-partial") allow_partial = true;
            else if (!positional && (arg == "--checkpoint-every" || arg == "--max-orders" ||
                                     arg == "--checkpoints")) {
                if (++i == argc) throw std::invalid_argument(std::string(arg) + ": missing value");
                if (arg == "--checkpoints") checkpoints_path = argv[i];
                else if (arg == "--checkpoint-every") {
                    checkpoint_every = itch::tools::number<std::uint64_t>(arg, argv[i]);
                } else {
                    cfg.max_orders = itch::tools::number<std::uint32_t>(arg, argv[i]);
                    cfg.max_levels = std::min(cfg.max_levels, cfg.max_orders);
                }
            } else if (!positional && arg != "-" && arg.starts_with('-')) {
                throw std::invalid_argument("unknown option: " + std::string(arg));
            } else if (path.empty()) path = arg;
            else throw std::invalid_argument("expected one input path");
        }
        if (path.empty() || checkpoints_path.empty() || (!raw && path == "-")) {
            throw std::invalid_argument("input and fresh checkpoints path required; journal input must be a file");
        }
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_journal_replay: %s\nusage: itch_journal_replay [--raw] "
                     "[--allow-partial] [--checkpoint-every N] [--max-orders N] "
                     "--checkpoints fresh.csv INPUT\n", e.what());
        return 2;
    }

    try {
        Output output(checkpoints_path);
        if (std::fprintf(output.get(), "sequence,source_offset,timestamp_ns,live_orders,book_hash,state_hash\n") < 0) {
            throw std::runtime_error("cannot write checkpoint header");
        }
        auto builder = std::make_unique<itch::BookBuilder>(cfg);
        std::uint64_t messages = 0, records = 0, offset = 0, message_offset = 0, timestamp = 0,
            unknown = 0, bad_length = 0, end_records = 0, after_end = 0,
            checkpoints = 0, last_checkpoint = 0;
        const auto checkpoint = [&] {
            if (std::fprintf(output.get(), "%llu,%llu,%llu,%zu,%016llx,%016llx\n",
                static_cast<unsigned long long>(messages), static_cast<unsigned long long>(message_offset),
                static_cast<unsigned long long>(timestamp), builder->book().order_count(),
                static_cast<unsigned long long>(builder->book_hash()),
                static_cast<unsigned long long>(builder->state_hash())) < 0) {
                throw std::runtime_error("cannot write checkpoint");
            }
            ++checkpoints;
            last_checkpoint = messages;
        };
        const auto on_message = [&](itch::Bytes message) {
            if (end_records != 0 || (!message.empty() && builder->stats().end_of_messages)) ++after_end;
            ++records;
            offset += message.size() + 2;
            if (!message.empty()) {
                ++messages;
                message_offset = offset;
                timestamp = message.size() >= 11 ? itch::Header{message.data()}.timestamp() : 0;
            }
            switch (itch::dispatch(message, *builder)) {
                case itch::Dispatch::UnknownType: ++unknown; break;
                case itch::Dispatch::BadLength: ++bad_length; break;
                case itch::Dispatch::EndOfSession: ++end_records; break;
                default: break;
            }
            if (!message.empty() && messages % checkpoint_every == 0) checkpoint();
        };
        itch::JournalInfo journal;
        std::uint64_t source_bytes = 0;
        if (raw) {
            const auto input = itch::tools::walk_input(path, on_message);
            source_bytes = input.bytes;
        } else {
            itch::MappedFile input(path);
            journal = itch::walk_journal(input.bytes(), on_message);
            source_bytes = journal.source_bytes;
        }
        if (messages != 0 && last_checkpoint != messages) checkpoint();
        output.close();
        const auto& book = builder->book();
        const auto& a = book.anomalies();
        const auto& invalid = builder->invalid_messages();
        const auto& s = builder->stats();
        const bool clean = messages != 0 && source_bytes == offset && a.unknown_ref == 0 &&
            a.duplicate_ref == 0 && a.share_underflow == 0 && a.capacity == 0 &&
            invalid.invalid_side == 0 && invalid.locate_mismatch == 0 && unknown == 0 &&
            bad_length == 0 && after_end == 0;
        const bool passed = clean && (allow_partial || (s.end_of_messages && book.order_count() == 0));
        const std::string digest = raw ? "null" : '"' + hex(journal.source_sha256) + '"';
        std::printf("{\n  \"schema_version\": 1,\n  \"fingerprint_version\": 1,\n"
                    "  \"reference_index\": \"%.*s\",\n"
                    "  \"level_search\": \"%.*s\",\n"
                    "  \"format\": \"%s\",\n  \"source_sha256\": %s,\n"
                    "  \"source_identity_verified\": false,\n  \"journal_blocks\": %llu",
                    static_cast<int>(itch::kReferenceIndexName.size()), itch::kReferenceIndexName.data(),
                    static_cast<int>(itch::kLevelSearchName.size()), itch::kLevelSearchName.data(),
                    raw ? "raw" : "journal_v1", digest.c_str(),
                    static_cast<unsigned long long>(journal.blocks));
        const auto field = [](const char* name, std::uint64_t value) {
            std::printf(",\n  \"%s\": %llu", name, static_cast<unsigned long long>(value));
        };
        field("max_orders", cfg.max_orders); field("max_levels", cfg.max_levels);
        field("messages", messages); field("records", records); field("input_bytes", source_bytes);
        field("consumed_bytes", offset); field("checkpoint_every", checkpoint_every);
        field("checkpoints", checkpoints); field("final_orders", book.order_count());
        field("peak_orders", book.peak_orders()); field("adds", s.adds);
        field("executions", s.executions); field("executed_shares", s.executed_shares);
        field("non_printable_shares", s.non_printable_shares); field("trade_shares", s.trade_shares);
        field("cross_shares", s.cross_shares); field("broken_trades", s.broken_trades);
        field("unknown_ref", a.unknown_ref); field("duplicate_ref", a.duplicate_ref);
        field("share_underflow", a.share_underflow); field("capacity", a.capacity);
        field("invalid_side", invalid.invalid_side); field("locate_mismatch", invalid.locate_mismatch);
        field("unknown_type", unknown); field("bad_length", bad_length);
        field("end_records", end_records); field("after_end", after_end);
        field("trailing_bytes", source_bytes - offset);
        std::printf(",\n  \"book_hash\": \"%016llx\",\n  \"state_hash\": \"%016llx\",\n"
                    "  \"end_of_messages\": %s,\n  \"allow_partial\": %s,\n  \"passed\": %s\n}\n",
                    static_cast<unsigned long long>(builder->book_hash()),
                    static_cast<unsigned long long>(builder->state_hash()),
                    s.end_of_messages ? "true" : "false", allow_partial ? "true" : "false",
                    passed ? "true" : "false");
        if (std::fflush(stdout) != 0 || std::ferror(stdout)) throw std::runtime_error("cannot finish summary output");
        return passed ? 0 : 1;
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_journal_replay: %s\n", e.what());
        return 1;
    }
}
