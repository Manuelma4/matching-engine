#pragma once

#include <charconv>
#include <stdexcept>
#include <string>
#include <string_view>
#include <type_traits>

namespace itch::tools {

// from_chars rejects signs, partial numbers and overflow without wrapping an allocation
// size. Parse every argument before constructing the large preallocated order book.
template <class UInt>
UInt number(std::string_view option, std::string_view value, bool allow_zero = false) {
    static_assert(std::is_unsigned_v<UInt>);
    UInt parsed{};
    if (value.empty()) {
        throw std::invalid_argument(std::string(option) + ": missing integer");
    }
    const auto [end, error] = std::from_chars(value.data(), value.data() + value.size(), parsed);
    if (error != std::errc{} || end != value.data() + value.size() ||
        (!allow_zero && parsed == 0)) {
        throw std::invalid_argument(std::string(option) + ": expected " +
                                    (allow_zero ? "a non-negative" : "a positive") +
                                    " integer in range");
    }
    return parsed;
}

}  // namespace itch::tools
