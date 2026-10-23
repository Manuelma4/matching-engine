#include "itch/journal.hpp"

#include <algorithm>
#include <array>
#include <string_view>

namespace itch {
namespace {

// Reflected CRC-32/ISO-HDLC, the zlib.crc32 convention (not authentication).
constexpr auto kCrcTable = [] {
    std::array<std::uint32_t, 256> table{};
    for (std::uint32_t i = 0; i < table.size(); ++i) {
        std::uint32_t value = i;
        for (int bit = 0; bit < 8; ++bit) {
            value = (value >> 1) ^ ((value & 1) ? 0xEDB88320u : 0u);
        }
        table[i] = value;
    }
    return table;
}();

std::uint32_t crc32(Bytes bytes, std::uint32_t previous = 0) {
    std::uint32_t value = previous ^ 0xFFFFFFFFu;
    for (unsigned char byte : bytes) value = kCrcTable[(value ^ byte) & 0xFF] ^ (value >> 8);
    return value ^ 0xFFFFFFFFu;
}

bool tag(Bytes bytes, std::size_t offset, std::string_view expected) {
    return offset <= bytes.size() && expected.size() <= bytes.size() - offset &&
        std::memcmp(bytes.data() + offset, expected.data(), expected.size()) == 0;
}

bool zeros(Bytes bytes) {
    return std::all_of(bytes.begin(), bytes.end(), [](unsigned char c) { return c == 0; });
}

void require(bool condition, const char* error) {
    if (!condition) throw std::runtime_error(error);
}

}  // namespace

JournalInfo inspect_journal(Bytes bytes) {
    require(bytes.size() >= kJournalHeaderBytes + kJournalFooterBytes,
            "truncated journal header/footer");
    require(tag(bytes, 0, std::string_view("ITCHJNL\0", 8)), "invalid journal magic");
    require(load_be16(bytes.data() + 8) == 1 &&
            load_be16(bytes.data() + 10) == kJournalHeaderBytes &&
            load_be32(bytes.data() + 12) == kJournalBlockBytes &&
            load_be32(bytes.data() + 16) == 1 && zeros(bytes.subspan(20, 12)),
            "unsupported journal version, flags or reserved fields");
    JournalInfo info;
    std::size_t offset = kJournalHeaderBytes;
    std::uint32_t prefix_crc = crc32(bytes.first(kJournalHeaderBytes));
    bool short_block = false;
    while (tag(bytes, offset, "DATA")) {
        require(bytes.size() - offset >= kJournalBlockHeaderBytes, "truncated journal block header");
        const auto header = bytes.subspan(offset, kJournalBlockHeaderBytes);
        const auto size = static_cast<std::size_t>(load_be32(header.data() + 4));
        require(size != 0 && size <= kJournalBlockBytes && !short_block,
                "invalid journal block size or non-canonical packing");
        require(load_be64(header.data() + 8) == info.source_bytes &&
                load_be32(header.data() + 20) == 0, "invalid journal block offset/reserved field");
        offset += kJournalBlockHeaderBytes;
        require(size <= bytes.size() - offset, "truncated journal block payload");
        const auto payload = bytes.subspan(offset, size);
        require(crc32(payload) == load_be32(header.data() + 16), "journal block CRC mismatch");
        prefix_crc = crc32(header, prefix_crc);
        prefix_crc = crc32(payload, prefix_crc);
        info.source_bytes += size;
        ++info.blocks;
        short_block = size != kJournalBlockBytes;
        offset += size;
    }
    require(bytes.size() - offset == kJournalFooterBytes &&
            tag(bytes, offset, std::string_view("ITCHEND\0", 8)),
            "missing journal footer or trailing bytes");
    const auto footer = bytes.subspan(offset, kJournalFooterBytes);
    require(info.blocks != 0 && load_be64(footer.data() + 8) == info.source_bytes &&
            load_be64(footer.data() + 16) == info.blocks, "journal footer counts mismatch");
    require(load_be32(footer.data() + 56) == prefix_crc, "journal prefix CRC mismatch");
    require(load_be32(footer.data() + 60) == 0 && load_be32(footer.data() + 68) == 0,
            "unsupported journal footer reserved fields");
    require(load_be32(footer.data() + 64) == crc32(footer.first(64)), "journal footer CRC mismatch");
    std::copy_n(footer.data() + 24, info.source_sha256.size(), info.source_sha256.begin());
    return info;
}

}  // namespace itch
