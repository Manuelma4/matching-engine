#pragma once

#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <span>
#include <stdexcept>
#include <string>
#include <system_error>
#include <vector>

#include "itch/endian.hpp"

namespace itch {

using Bytes = std::span<const unsigned char>;

// Nasdaq BinaryFILE framing, as used by the emi.nasdaq.com sample files: every message is
// preceded by its length as a 2-byte big-endian integer. A zero-length record marks the end
// of the session and is passed on as an empty message; not every file carries one.
//
// Feeds one contiguous buffer to `on_message(Bytes)`, one message at a time, and returns
// the number of bytes consumed. A trailing partial frame is left unconsumed so a streaming
// reader can carry it into the next buffer.
template <class OnMessage>
std::size_t walk_frames(Bytes buffer, OnMessage&& on_message) {
    if (buffer.size() < 2) {
        return 0;
    }
    const unsigned char* p = buffer.data();
    const unsigned char* const end = p + buffer.size();
    while (end - p >= 2) {
        const std::size_t len = load_be16(p);
        if (static_cast<std::size_t>(end - p - 2) < len) {
            break;
        }
        on_message(Bytes(p + 2, len));
        p += 2 + len;
    }
    return static_cast<std::size_t>(p - buffer.data());
}

// A whole file mapped read-only into memory. Throws std::runtime_error on failure.
class MappedFile {
public:
    explicit MappedFile(const std::string& path);
    ~MappedFile();
    MappedFile(const MappedFile&) = delete;
    MappedFile& operator=(const MappedFile&) = delete;

    [[nodiscard]] Bytes bytes() const { return {data_, size_}; }

    // Touches every page once, so a timed run does not include page faults.
    void prefault() const;

private:
    const unsigned char* data_ = nullptr;
    std::size_t size_ = 0;
};

// Reads a stream (e.g. stdin fed by `gzip -dc day.gz`) in large blocks, carrying partial
// frames across block boundaries. Calls on_message for every complete message and returns
// the number of bytes left over at end of stream (non-zero means a truncated last frame).
// Throws on read errors or an invalid block size, rather than treating errors as clean EOF.
template <class OnMessage>
std::size_t walk_stream(std::FILE* in, OnMessage&& on_message,
                        std::size_t block_size = std::size_t{16} << 20) {
    std::vector<unsigned char> buffer;
    if (block_size == 0) {
        throw std::invalid_argument("stream block size must be positive");
    }
    if (block_size > buffer.max_size() - 65'536) {
        throw std::length_error("stream block size is too large");
    }
    buffer.resize(block_size + 65'536);
    std::size_t carried = 0;
    for (;;) {
        const std::size_t got = std::fread(buffer.data() + carried, 1, block_size, in);
        if (std::ferror(in)) {
            throw std::system_error(errno ? errno : EIO, std::generic_category(),
                                    "cannot read input stream");
        }
        const std::size_t filled = carried + got;
        const std::size_t used = walk_frames(Bytes(buffer.data(), filled), on_message);
        carried = filled - used;
        if (got == 0) {
            return carried;
        }
        if (carried > 0) {
            std::memmove(buffer.data(), buffer.data() + used, carried);
        }
    }
}

}  // namespace itch
