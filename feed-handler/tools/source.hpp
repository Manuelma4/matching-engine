#pragma once

// Shared input handling for the command-line tools: a path is memory-mapped, "-" reads
// standard input in blocks (e.g. `gzip -dc day.gz | itch_census -`).
#include <cstdio>
#include <string>

#include "itch/framing.hpp"

namespace itch::tools {

struct WalkResult {
    std::size_t bytes = 0;     // input size
    std::size_t consumed = 0;  // bytes in complete frames
};

template <class OnMessage>
WalkResult walk_input(const std::string& path, OnMessage&& on_message, bool prefault = false) {
    if (path == "-") {
        std::size_t total = 0;
        auto counting = [&](Bytes m) {
            total += m.size() + 2;
            on_message(m);
        };
        const std::size_t leftover = walk_stream(stdin, counting);
        return {total + leftover, total};
    }
    MappedFile file(path);
    if (prefault) {
        file.prefault();
    }
    const std::size_t used = walk_frames(file.bytes(), on_message);
    return {file.bytes().size(), used};
}

}  // namespace itch::tools
