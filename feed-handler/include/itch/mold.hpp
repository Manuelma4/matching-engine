#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <stdexcept>
#include <string_view>
#include <vector>

#include "itch/framing.hpp"

namespace itch::mold {

inline constexpr std::size_t kHeaderBytes = 20;
inline constexpr std::size_t kMaxDatagramBytes = 65'535;
inline constexpr std::size_t kMaxMessages = 1'024;
inline constexpr std::uint64_t kMaxAttempts = 100'000;

using Session = std::array<unsigned char, 10>;

struct Limits {
    std::size_t max_datagram_bytes = kMaxDatagramBytes;
    std::size_t max_messages = kMaxMessages;
    std::uint64_t max_attempts = kMaxAttempts;
};

enum class PacketKind : std::uint8_t { data, heartbeat, end };
enum class State : std::uint8_t { ready, ended, failed };
enum class Disposition : std::uint8_t { accepted, heartbeat, end, repeated_end, rejected, blocked };
enum class Fault : std::uint8_t {
    none,
    datagram_too_large,
    truncated_header,
    message_limit,
    zero_sequence,
    sequence_overflow,
    truncated_length,
    truncated_body,
    trailing_bytes,
    session_mismatch,
    stale_data,
    overlap,
    gap,
    control_sequence_mismatch,
    post_end,
    attempt_limit,
    validator_exception,
    handler_exception,
    reentry,
    resource_failure,
};

[[nodiscard]] std::string_view to_string(PacketKind value) noexcept;
[[nodiscard]] std::string_view to_string(State value) noexcept;
[[nodiscard]] std::string_view to_string(Disposition value) noexcept;
[[nodiscard]] std::string_view to_string(Fault value) noexcept;

class PacketError : public std::runtime_error {
public:
    explicit PacketError(Fault fault);
    [[nodiscard]] Fault fault() const noexcept { return fault_; }
private:
    Fault fault_;
};

// These identities belong to the transport, not to BinaryFILE source framing.
// The index is zero-based; body_offset excludes its two-byte length prefix.
struct MessageView {
    std::uint64_t transport_sequence = 0;
    std::uint16_t packet_message_index = 0;
    std::size_t body_offset = 0;
    Bytes body;
};

struct PacketView {
    Session session{};
    std::uint64_t first_sequence = 0;
    std::uint64_t next_sequence = 0;  // Exclusive end for data; advertised next for controls.
    std::uint16_t count = 0;          // Original header value, including control sentinels.
    PacketKind kind = PacketKind::data;
    std::vector<MessageView> messages;
};

// All blocks and the exact datagram extent are checked before returning. Message
// bodies borrow immutable caller storage; zero-length generic bodies are legal.
// Invalid configuration throws invalid_argument; bad packets throw PacketError.
[[nodiscard]] PacketView parse_packet(Bytes datagram, const Limits& limits = {});

using Validator = std::function<void(Bytes)>;
using Handler = std::function<void(const MessageView&)>;

// A caller must choose this explicitly for application-agnostic Mold messages.
void accept_generic_payload(Bytes) noexcept;

struct Result {
    Disposition disposition = Disposition::rejected;
    Fault fault = Fault::none;
    State state = State::ready;
    std::uint64_t next_sequence = 0;
    std::uint64_t receive_attempts = 0;
    std::size_t handler_attempted = 0;
    std::size_t handler_returned = 0;
};

// Bounded, synchronous, fail-stop admission. There is no automatic initial
// sequence, recovery buffer, reset or retry. Session bytes are opaque and exact.
// A receiver is single-threaded; concurrent access is not supported.
class Receiver {
public:
    Receiver(Session session, std::uint64_t next_sequence, const Limits& limits = {});
    Receiver(const Receiver&) = delete;
    Receiver& operator=(const Receiver&) = delete;

    // Validator calls for the entire eligible packet precede every handler.
    // Callback exceptions and recursive calls latch failure without advancing
    // next. Downstream side effects cannot be rolled back: discard a failed run.
    // Datagrams must remain immutable/alive throughout the synchronous call.
    [[nodiscard]] Result receive(Bytes datagram, const Validator& validator, const Handler& handler) noexcept;

    [[nodiscard]] State state() const noexcept { return state_; }
    [[nodiscard]] Fault fault() const noexcept { return fault_; }
    [[nodiscard]] std::uint64_t next_sequence() const noexcept { return next_sequence_; }
    [[nodiscard]] std::uint64_t attempts() const noexcept { return attempts_; }

private:
    void fail(Fault fault) noexcept;
    [[nodiscard]] Result result(Disposition disposition, std::size_t attempted = 0,
                                std::size_t returned = 0) const noexcept;

    Session session_;
    Limits limits_;
    std::uint64_t next_sequence_;
    std::uint64_t attempts_ = 0;
    State state_ = State::ready;
    Fault fault_ = Fault::none;
    bool active_ = false;
};

}  // namespace itch::mold
