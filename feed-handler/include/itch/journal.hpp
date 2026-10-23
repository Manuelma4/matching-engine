#pragma once

#include <array>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <vector>

#include "itch/framing.hpp"

namespace itch {

inline constexpr std::size_t kJournalHeaderBytes = 32;
inline constexpr std::size_t kJournalBlockHeaderBytes = 24;
inline constexpr std::size_t kJournalFooterBytes = 72;
inline constexpr std::size_t kJournalBlockBytes = 1u << 20;

struct JournalInfo {
    std::uint64_t source_bytes = 0;
    std::uint64_t blocks = 0;
    std::array<unsigned char, 32> source_sha256{};
};

// Validate the complete version-1 container before exposing any messages. CRC-32
// detects accidental corruption; SHA-256 identity is independently recomputed by
// bench/journal.py verify. A stored digest alone is not an identity check.
[[nodiscard]] JournalInfo inspect_journal(Bytes bytes);

// Recover the original BinaryFILE stream in source order, carrying incomplete frames
// across journal blocks. The callback sees precisely the original wire payloads,
// including ignored metadata and the optional empty end record. A trailing partial
// frame throws. Application-level errors are the handler's responsibility.
template <class OnMessage>
JournalInfo walk_journal(Bytes bytes, OnMessage&& on_message) {
    const JournalInfo info = inspect_journal(bytes);
    std::vector<unsigned char> buffer(kJournalBlockBytes + 65'536);
    std::size_t carried = 0;
    std::size_t offset = kJournalHeaderBytes;
    for (std::uint64_t block = 0; block < info.blocks; ++block) {
        const auto size = static_cast<std::size_t>(load_be32(bytes.data() + offset + 4));
        const auto* payload = bytes.data() + offset + kJournalBlockHeaderBytes;
        std::memcpy(buffer.data() + carried, payload, size);
        const std::size_t filled = carried + size;
        const std::size_t used = walk_frames(Bytes(buffer.data(), filled), on_message);
        carried = filled - used;
        if (carried != 0) std::memmove(buffer.data(), buffer.data() + used, carried);
        offset += kJournalBlockHeaderBytes + size;
    }
    if (carried != 0) throw std::runtime_error("journal contains a truncated BinaryFILE frame");
    return info;
}

}  // namespace itch
