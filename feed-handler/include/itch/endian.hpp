#pragma once

#include <bit>
#include <cstdint>
#include <cstring>

namespace itch {

static_assert(std::endian::native == std::endian::little ||
              std::endian::native == std::endian::big, "mixed-endian hosts are unsupported");

// ITCH fields are big-endian and unaligned. memcpy into a local is the defined way to do
// an unaligned load; compilers turn it plus the byte swap into a single load + rev on
// arm64 (bswap on x86). std::byteswap is C++23, so the builtins are used directly.

inline std::uint16_t load_be16(const unsigned char* p) {
    std::uint16_t v;
    std::memcpy(&v, p, sizeof v);
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap16(v);
    }
    return v;
}

inline std::uint32_t load_be32(const unsigned char* p) {
    std::uint32_t v;
    std::memcpy(&v, p, sizeof v);
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap32(v);
    }
    return v;
}

inline std::uint64_t load_be64(const unsigned char* p) {
    std::uint64_t v;
    std::memcpy(&v, p, sizeof v);
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap64(v);
    }
    return v;
}

// 6-byte timestamp (nanoseconds since midnight). Read as a 16-bit and a 32-bit load rather
// than one 8-byte load, which would run past the end of the shortest messages.
inline std::uint64_t load_be48(const unsigned char* p) {
    return (std::uint64_t{load_be16(p)} << 32) | load_be32(p + 2);
}

inline void store_be16(unsigned char* p, std::uint16_t v) {
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap16(v);
    }
    std::memcpy(p, &v, sizeof v);
}

inline void store_be32(unsigned char* p, std::uint32_t v) {
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap32(v);
    }
    std::memcpy(p, &v, sizeof v);
}

inline void store_be64(unsigned char* p, std::uint64_t v) {
    if constexpr (std::endian::native == std::endian::little) {
        v = __builtin_bswap64(v);
    }
    std::memcpy(p, &v, sizeof v);
}

inline void store_be48(unsigned char* p, std::uint64_t v) {
    store_be16(p, static_cast<std::uint16_t>(v >> 32));
    store_be32(p + 2, static_cast<std::uint32_t>(v));
}

}  // namespace itch
