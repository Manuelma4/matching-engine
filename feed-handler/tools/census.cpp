// itch_census: counts the messages of an ITCH 5.0 BinaryFILE by type and checks framing.
//
//   itch_census 12302019.NASDAQ_ITCH50
//   gzip -dc 12302019.NASDAQ_ITCH50.gz | itch_census -
//
// The byte identity sum(count * (length + 2)) == file size holds for a well-formed file
// (plus 2 bytes when the optional zero-length end-of-session record is present).
#include <array>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <exception>
#include <string>

#include "itch/messages.hpp"
#include "source.hpp"

namespace {

const char* message_name(unsigned char type) {
    switch (type) {
        case 'S': return "system event";
        case 'R': return "stock directory";
        case 'H': return "trading action";
        case 'Y': return "Reg SHO restriction";
        case 'L': return "market participant position";
        case 'V': return "MWCB decline level";
        case 'W': return "MWCB status";
        case 'K': return "IPO quoting period";
        case 'J': return "LULD auction collar";
        case 'h': return "operational halt";
        case 'A': return "add order";
        case 'F': return "add order (MPID)";
        case 'E': return "order executed";
        case 'C': return "order executed with price";
        case 'X': return "order cancel";
        case 'D': return "order delete";
        case 'U': return "order replace";
        case 'P': return "trade (non-cross)";
        case 'Q': return "cross trade";
        case 'B': return "broken trade";
        case 'I': return "net order imbalance";
        case 'N': return "retail price improvement";
        case 'O': return "DLCR price discovery";
        default: return "unknown";
    }
}

}  // namespace

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: itch_census <file | ->\n");
        return 2;
    }
    std::array<std::uint64_t, 256> count{};
    std::uint64_t bad_length = 0;
    std::uint64_t messages = 0;
    std::uint64_t end_records = 0;
    std::uint64_t after_end = 0;

    const auto start = std::chrono::steady_clock::now();
    itch::tools::WalkResult r;
    try {
        r = itch::tools::walk_input(argv[1], [&](itch::Bytes m) {
            if (end_records != 0) {
                ++after_end;
            }
            if (m.empty()) {
                ++end_records;  // zero-length record: end of session
                return;
            }
            ++messages;
            ++count[m[0]];
            const std::uint8_t expected = itch::kMessageLength[m[0]];
            if (expected != 0 && expected != m.size()) {
                ++bad_length;
            }
        });
    } catch (const std::exception& e) {
        std::fprintf(stderr, "itch_census: %s\n", e.what());
        return 1;
    }
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();

    std::printf("%-4s %-28s %14s %16s\n", "type", "message", "count", "bytes");
    std::uint64_t framed = 0;
    std::uint64_t unknown = 0;
    for (std::size_t t = 0; t < count.size(); ++t) {
        if (count[t] == 0) {
            continue;
        }
        const std::uint8_t len = itch::kMessageLength[t];
        if (len == 0) {
            unknown += count[t];
        }
        const std::uint64_t bytes = count[t] * (len + 2u);
        framed += bytes;
        std::printf("%-4c %-28s %14llu %16llu\n", static_cast<int>(t),
                    message_name(static_cast<unsigned char>(t)),
                    static_cast<unsigned long long>(count[t]),
                    static_cast<unsigned long long>(bytes));
    }
    std::printf("\nmessages     %llu\n", static_cast<unsigned long long>(messages));
    std::printf("file bytes   %zu\n", r.bytes);
    std::printf("identity     sum(count * (length + 2)) + end record = %llu  %s\n",
                static_cast<unsigned long long>(framed + 2 * end_records),
                framed + 2 * end_records == r.bytes && unknown == 0 ? "== file size" : "!= file size");
    std::printf("trailing     %zu bytes outside complete frames\n", r.bytes - r.consumed);
    std::printf("end record   %s\n", end_records > 0 ? "present" : "absent (allowed)");
    std::printf("after end    %llu records after session end\n",
                static_cast<unsigned long long>(after_end));
    std::printf("anomalies    %llu unknown type, %llu wrong length\n",
                static_cast<unsigned long long>(unknown),
                static_cast<unsigned long long>(bad_length));
    std::printf("elapsed      %.3f s (%.1f M msg/s)\n", seconds,
                static_cast<double>(messages) / seconds / 1e6);
    return messages != 0 && framed + 2 * end_records == r.bytes && r.bytes == r.consumed &&
                   unknown == 0 && bad_length == 0 && after_end == 0 ? 0 : 1;
}
