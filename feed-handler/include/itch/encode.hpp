#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <string_view>
#include <vector>

#include "itch/book.hpp"
#include "itch/endian.hpp"

namespace itch {

// Appends ITCH 5.0 messages, each with its BinaryFILE 2-byte length prefix, to a buffer.
// Field offsets mirror the decoding views in messages.hpp. Used to publish a feed from the
// matching engine and to generate reproducible synthetic days.
class Writer {
public:
    [[nodiscard]] const std::vector<unsigned char>& bytes() const { return out_; }
    void clear() { out_.clear(); }

    // Zero-length BinaryFILE record: the end of the session.
    void end_of_session() { out_.insert(out_.end(), {0, 0}); }

    void system_event(std::uint64_t ts, char event) {
        unsigned char* m = begin('S', 12, 0, ts);
        m[11] = static_cast<unsigned char>(event);
    }

    void stock_directory(Locate locate, std::uint64_t ts, std::string_view stock) {
        unsigned char* m = begin('R', 39, locate, ts);
        alpha(m + 11, 8, stock);
        m[19] = 'Q';                 // market category: Nasdaq Global Select
        m[20] = 'N';                 // financial status: normal
        store_be32(m + 21, 100);     // round lot
        m[25] = 'N';                 // round lots only
        m[26] = 'C';                 // common stock
        alpha(m + 27, 2, "Z");       // issue sub-type: not applicable
        m[29] = 'P';                 // production
        m[30] = 'N';                 // short sale threshold
        m[31] = 'N';                 // IPO flag
        m[32] = '1';                 // LULD tier 1
        m[33] = 'N';                 // not an ETP
        store_be32(m + 34, 0);       // ETP leverage
        m[38] = 'N';                 // not inverse
    }

    void add(Locate locate, std::uint64_t ts, Ref ref, BookSide side, Shares shares,
             std::string_view stock, Price4 price) {
        unsigned char* m = begin('A', 36, locate, ts);
        store_be64(m + 11, ref);
        m[19] = side == BookSide::Bid ? 'B' : 'S';
        store_be32(m + 20, shares);
        alpha(m + 24, 8, stock);
        store_be32(m + 32, price);
    }

    void executed(Locate locate, std::uint64_t ts, Ref ref, Shares shares, std::uint64_t match) {
        unsigned char* m = begin('E', 31, locate, ts);
        store_be64(m + 11, ref);
        store_be32(m + 19, shares);
        store_be64(m + 23, match);
    }

    void cancel(Locate locate, std::uint64_t ts, Ref ref, Shares shares) {
        unsigned char* m = begin('X', 23, locate, ts);
        store_be64(m + 11, ref);
        store_be32(m + 19, shares);
    }

    void remove(Locate locate, std::uint64_t ts, Ref ref) {
        unsigned char* m = begin('D', 19, locate, ts);
        store_be64(m + 11, ref);
    }

    void replace(Locate locate, std::uint64_t ts, Ref old_ref, Ref new_ref, Shares shares,
                 Price4 price) {
        unsigned char* m = begin('U', 35, locate, ts);
        store_be64(m + 11, old_ref);
        store_be64(m + 19, new_ref);
        store_be32(m + 27, shares);
        store_be32(m + 31, price);
    }

private:
    // Appends the length prefix and the common header; returns the message start.
    unsigned char* begin(char type, std::uint16_t len, Locate locate, std::uint64_t ts) {
        const std::size_t at = out_.size();
        out_.resize(at + 2 + len);
        unsigned char* frame = out_.data() + at;
        store_be16(frame, len);
        unsigned char* m = frame + 2;
        m[0] = static_cast<unsigned char>(type);
        store_be16(m + 1, locate);
        store_be16(m + 3, 0);  // tracking number
        store_be48(m + 5, ts);
        return m;
    }

    static void alpha(unsigned char* dst, std::size_t len, std::string_view text) {
        std::memset(dst, ' ', len);
        std::memcpy(dst, text.data(), std::min(len, text.size()));
    }

    std::vector<unsigned char> out_;
};

}  // namespace itch
