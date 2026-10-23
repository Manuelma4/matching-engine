#include "itch/mold.hpp"

#include <algorithm>
#include <limits>
#include <string>

#include "itch/endian.hpp"

namespace itch::mold {
namespace {

void validate_limits(const Limits& limits) {
    if (limits.max_datagram_bytes == 0 || limits.max_datagram_bytes > kMaxDatagramBytes ||
        limits.max_messages == 0 || limits.max_messages > kMaxMessages ||
        limits.max_attempts == 0 || limits.max_attempts > kMaxAttempts) {
        throw std::invalid_argument("Mold bounds must be positive and within the profile ceilings");
    }
}

class ActiveCall {
public:
    explicit ActiveCall(bool& active) : active_(active) { active_ = true; }
    ~ActiveCall() { active_ = false; }
    ActiveCall(const ActiveCall&) = delete;
    ActiveCall& operator=(const ActiveCall&) = delete;
private:
    bool& active_;
};

}  // namespace

std::string_view to_string(PacketKind value) noexcept {
    switch (value) {
        case PacketKind::data: return "data";
        case PacketKind::heartbeat: return "heartbeat";
        case PacketKind::end: return "end";
    }
    return "unknown";
}

std::string_view to_string(State value) noexcept {
    switch (value) {
        case State::ready: return "ready";
        case State::ended: return "ended";
        case State::failed: return "failed";
    }
    return "unknown";
}

std::string_view to_string(Disposition value) noexcept {
    switch (value) {
        case Disposition::accepted: return "accepted";
        case Disposition::heartbeat: return "heartbeat";
        case Disposition::end: return "end";
        case Disposition::repeated_end: return "repeated_end";
        case Disposition::rejected: return "rejected";
        case Disposition::blocked: return "blocked";
    }
    return "unknown";
}

std::string_view to_string(Fault value) noexcept {
    switch (value) {
        case Fault::none: return "none";
        case Fault::datagram_too_large: return "datagram_too_large";
        case Fault::truncated_header: return "truncated_header";
        case Fault::message_limit: return "message_limit";
        case Fault::zero_sequence: return "zero_sequence";
        case Fault::sequence_overflow: return "sequence_overflow";
        case Fault::truncated_length: return "truncated_length";
        case Fault::truncated_body: return "truncated_body";
        case Fault::trailing_bytes: return "trailing_bytes";
        case Fault::session_mismatch: return "session_mismatch";
        case Fault::stale_data: return "stale_data";
        case Fault::overlap: return "overlap";
        case Fault::gap: return "gap";
        case Fault::control_sequence_mismatch: return "control_sequence_mismatch";
        case Fault::post_end: return "post_end";
        case Fault::attempt_limit: return "attempt_limit";
        case Fault::validator_exception: return "validator_exception";
        case Fault::handler_exception: return "handler_exception";
        case Fault::reentry: return "reentry";
        case Fault::resource_failure: return "resource_failure";
    }
    return "unknown";
}

PacketError::PacketError(Fault fault) : std::runtime_error(std::string(to_string(fault))), fault_(fault) {}

PacketView parse_packet(Bytes datagram, const Limits& limits) {
    validate_limits(limits);
    if (datagram.size() > limits.max_datagram_bytes) throw PacketError(Fault::datagram_too_large);
    if (datagram.size() < kHeaderBytes) throw PacketError(Fault::truncated_header);

    PacketView packet;
    std::copy_n(datagram.data(), packet.session.size(), packet.session.begin());
    packet.first_sequence = load_be64(datagram.data() + 10);
    packet.next_sequence = packet.first_sequence;
    packet.count = load_be16(datagram.data() + 18);
    if (packet.first_sequence == 0) throw PacketError(Fault::zero_sequence);

    if (packet.count == 0 || packet.count == 65'535) {
        packet.kind = packet.count == 0 ? PacketKind::heartbeat : PacketKind::end;
        if (datagram.size() != kHeaderBytes) throw PacketError(Fault::trailing_bytes);
        return packet;
    }
    if (packet.count > limits.max_messages) throw PacketError(Fault::message_limit);
    if (packet.first_sequence > std::numeric_limits<std::uint64_t>::max() - packet.count) {
        throw PacketError(Fault::sequence_overflow);
    }
    packet.next_sequence += packet.count;
    packet.messages.reserve(packet.count);
    std::size_t cursor = kHeaderBytes;
    for (std::uint16_t index = 0; index < packet.count; ++index) {
        if (datagram.size() - cursor < 2) throw PacketError(Fault::truncated_length);
        const std::size_t length = load_be16(datagram.data() + cursor);
        cursor += 2;
        if (length > datagram.size() - cursor) throw PacketError(Fault::truncated_body);
        packet.messages.push_back({packet.first_sequence + index, index, cursor, datagram.subspan(cursor, length)});
        cursor += length;
    }
    if (cursor != datagram.size()) throw PacketError(Fault::trailing_bytes);
    return packet;
}

void accept_generic_payload(Bytes) noexcept {}

Receiver::Receiver(Session session, std::uint64_t next_sequence, const Limits& limits)
    : session_(session), limits_(limits), next_sequence_(next_sequence) {
    validate_limits(limits_);
    if (next_sequence_ == 0) throw std::invalid_argument("Mold initial next sequence must be positive");
}

void Receiver::fail(Fault fault) noexcept {
    if (fault_ == Fault::none) fault_ = fault;
    state_ = State::failed;
}

Result Receiver::result(Disposition disposition, std::size_t attempted, std::size_t returned) const noexcept {
    return {disposition, fault_, state_, next_sequence_, attempts_, attempted, returned};
}

Result Receiver::receive(Bytes datagram, const Validator& validator, const Handler& handler) noexcept {
    if (state_ == State::failed) return result(Disposition::blocked);
    // The first failing call is counted. Afterwards the bounded counter freezes.
    ++attempts_;
    if (attempts_ > limits_.max_attempts) {
        fail(Fault::attempt_limit);
        return result(Disposition::rejected);
    }
    if (active_) {
        fail(Fault::reentry);
        return result(Disposition::rejected);
    }
    ActiveCall active(active_);
    try {
        const PacketView packet = parse_packet(datagram, limits_);
        if (packet.session != session_) {
            fail(Fault::session_mismatch);
            return result(Disposition::rejected);
        }
        if (state_ == State::ended) {
            if (packet.kind == PacketKind::end && packet.first_sequence == next_sequence_) {
                return result(Disposition::repeated_end);
            }
            fail(Fault::post_end);
            return result(Disposition::rejected);
        }
        if (packet.kind != PacketKind::data) {
            if (packet.first_sequence != next_sequence_) {
                fail(Fault::control_sequence_mismatch);
                return result(Disposition::rejected);
            }
            if (packet.kind == PacketKind::end) {
                state_ = State::ended;
                return result(Disposition::end);
            }
            return result(Disposition::heartbeat);
        }
        if (packet.first_sequence < next_sequence_) {
            fail(packet.next_sequence <= next_sequence_ ? Fault::stale_data : Fault::overlap);
            return result(Disposition::rejected);
        }
        if (packet.first_sequence > next_sequence_) {
            fail(Fault::gap);
            return result(Disposition::rejected);
        }
        for (const auto& message : packet.messages) {
            try {
                validator(message.body);
            } catch (...) {
                fail(Fault::validator_exception);
                return result(Disposition::rejected);
            }
            if (state_ == State::failed) return result(Disposition::rejected);
        }
        std::size_t attempted = 0, returned = 0;
        for (const auto& message : packet.messages) {
            ++attempted;
            try {
                handler(message);
            } catch (...) {
                fail(Fault::handler_exception);
                return result(Disposition::rejected, attempted, returned);
            }
            ++returned;
            if (state_ == State::failed) return result(Disposition::rejected, attempted, returned);
        }
        next_sequence_ = packet.next_sequence;
        return result(Disposition::accepted, attempted, returned);
    } catch (const PacketError& error) {
        fail(error.fault());
    } catch (...) {
        // Allocation failure, including construction of an error, cannot escape
        // or leave the receiver reusable. Callbacks have their own fault types.
        fail(Fault::resource_failure);
    }
    return result(Disposition::rejected);
}

}  // namespace itch::mold
