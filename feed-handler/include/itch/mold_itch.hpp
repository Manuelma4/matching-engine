#pragma once

#include <stdexcept>

#include "itch/messages.hpp"

namespace itch::mold {

// Application preflight only: no handler is invoked and no state is changed.
// Unlike generic Mold bodies, empty ITCH bodies must never reach dispatch(),
// where they would mean a BinaryFILE end record rather than ordinary data.
inline void validate_itch_payload(Bytes body) {
    if (body.empty()) throw std::invalid_argument("empty ITCH payload in Mold data");
    const auto expected = kMessageLength[body.front()];
    if (expected == 0) throw std::invalid_argument("unknown ITCH type in Mold data");
    if (body.size() != expected) throw std::invalid_argument("wrong ITCH payload length in Mold data");
}

}  // namespace itch::mold
