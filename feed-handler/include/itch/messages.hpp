#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <string_view>

#include "itch/book.hpp"
#include "itch/endian.hpp"
#include "itch/framing.hpp"

namespace itch {

// Nasdaq TotalView-ITCH 5.0 (specification revision of April 2023). Every message starts
// with the same 11-byte header: type (1), stock locate (2), tracking number (2) and a
// 6-byte timestamp in nanoseconds since midnight. All integers are big-endian; alpha
// fields are ASCII, left-justified and space-padded.
//
// The views below wrap a pointer into the feed buffer and decode a field only when it is
// read, so dispatching a message costs nothing until a handler asks for something.

// Total length of each message type (including the type byte); 0 marks unknown types.
inline constexpr std::array<std::uint8_t, 256> kMessageLength = [] {
    std::array<std::uint8_t, 256> len{};
    len['S'] = 12;  // system event
    len['R'] = 39;  // stock directory
    len['H'] = 25;  // stock trading action
    len['Y'] = 20;  // Reg SHO short sale price test restriction
    len['L'] = 26;  // market participant position
    len['V'] = 35;  // MWCB decline level
    len['W'] = 12;  // MWCB status
    len['K'] = 28;  // IPO quoting period update
    len['J'] = 35;  // LULD auction collar
    len['h'] = 21;  // operational halt
    len['A'] = 36;  // add order
    len['F'] = 40;  // add order with MPID attribution
    len['E'] = 31;  // order executed
    len['C'] = 36;  // order executed with price
    len['X'] = 23;  // order cancel (partial)
    len['D'] = 19;  // order delete
    len['U'] = 35;  // order replace
    len['P'] = 44;  // trade (non-cross), non-displayed liquidity
    len['Q'] = 40;  // cross trade
    len['B'] = 19;  // broken trade
    len['I'] = 50;  // net order imbalance indicator
    len['N'] = 20;  // retail price improvement indicator
    len['O'] = 48;  // direct listing with capital raise price discovery
    return len;
}();

struct Header {
    const unsigned char* p;

    [[nodiscard]] char type() const { return static_cast<char>(p[0]); }
    [[nodiscard]] Locate locate() const { return load_be16(p + 1); }
    [[nodiscard]] std::uint16_t tracking() const { return load_be16(p + 3); }
    [[nodiscard]] std::uint64_t timestamp() const { return load_be48(p + 5); }

protected:
    [[nodiscard]] std::string_view alpha(std::size_t offset, std::size_t len) const {
        return {reinterpret_cast<const char*>(p + offset), len};
    }
};

// 'S': O start of messages, S start of system hours, Q start of market hours,
// M end of market hours, E end of system hours, C end of messages.
struct SystemEvent : Header {
    [[nodiscard]] char event() const { return static_cast<char>(p[11]); }
};

// 'R': assigns the day's stock locate codes.
struct StockDirectory : Header {
    [[nodiscard]] std::string_view stock() const { return alpha(11, 8); }
    [[nodiscard]] char market_category() const { return static_cast<char>(p[19]); }
    [[nodiscard]] char financial_status() const { return static_cast<char>(p[20]); }
    [[nodiscard]] std::uint32_t round_lot_size() const { return load_be32(p + 21); }
    [[nodiscard]] char issue_classification() const { return static_cast<char>(p[26]); }
    [[nodiscard]] char authenticity() const { return static_cast<char>(p[29]); }
    [[nodiscard]] char luld_tier() const { return static_cast<char>(p[32]); }
    [[nodiscard]] bool etp() const { return p[33] == 'Y'; }
};

// 'H': H halted, P paused, Q quotation only, T trading.
struct TradingAction : Header {
    [[nodiscard]] std::string_view stock() const { return alpha(11, 8); }
    [[nodiscard]] char state() const { return static_cast<char>(p[19]); }
    [[nodiscard]] std::string_view reason() const { return alpha(21, 4); }
};

// 'A' and 'F' share their first 36 bytes; 'F' adds a 4-character MPID.
struct AddOrder : Header {
    [[nodiscard]] Ref ref() const { return load_be64(p + 11); }
    [[nodiscard]] bool valid_side() const { return p[19] == 'B' || p[19] == 'S'; }
    [[nodiscard]] BookSide side() const { return p[19] == 'B' ? BookSide::Bid : BookSide::Ask; }
    [[nodiscard]] Shares shares() const { return load_be32(p + 20); }
    [[nodiscard]] std::string_view stock() const { return alpha(24, 8); }
    [[nodiscard]] Price4 price() const { return load_be32(p + 32); }
    [[nodiscard]] bool attributed() const { return p[0] == 'F'; }
    [[nodiscard]] std::string_view attribution() const {
        return attributed() ? alpha(36, 4) : std::string_view("NSDQ");
    }
};

// 'E': executes a resting order at its display price.
struct OrderExecuted : Header {
    [[nodiscard]] Ref ref() const { return load_be64(p + 11); }
    [[nodiscard]] Shares shares() const { return load_be32(p + 19); }
    [[nodiscard]] std::uint64_t match() const { return load_be64(p + 23); }
};

// 'C': executes a resting order at a different price. A non-printable execution still
// reduces the order but is excluded from volume (it is reported later in a bulk print).
struct OrderExecutedWithPrice : Header {
    [[nodiscard]] Ref ref() const { return load_be64(p + 11); }
    [[nodiscard]] Shares shares() const { return load_be32(p + 19); }
    [[nodiscard]] std::uint64_t match() const { return load_be64(p + 23); }
    [[nodiscard]] bool printable() const { return p[31] == 'Y'; }
    [[nodiscard]] Price4 price() const { return load_be32(p + 32); }
};

// 'X': removes some shares and keeps time priority.
struct OrderCancel : Header {
    [[nodiscard]] Ref ref() const { return load_be64(p + 11); }
    [[nodiscard]] Shares shares() const { return load_be32(p + 19); }
};

// 'D': removes the whole order.
struct OrderDelete : Header {
    [[nodiscard]] Ref ref() const { return load_be64(p + 11); }
};

// 'U': cancel-replace. The new order takes a new reference, keeps the side, stock and
// attribution of the original, and goes to the back of the queue at its price.
struct OrderReplace : Header {
    [[nodiscard]] Ref old_ref() const { return load_be64(p + 11); }
    [[nodiscard]] Ref new_ref() const { return load_be64(p + 19); }
    [[nodiscard]] Shares shares() const { return load_be32(p + 27); }
    [[nodiscard]] Price4 price() const { return load_be32(p + 31); }
};

// 'P': an execution against non-displayed liquidity. No book effect; counts as volume.
struct Trade : Header {
    [[nodiscard]] Shares shares() const { return load_be32(p + 20); }
    [[nodiscard]] std::string_view stock() const { return alpha(24, 8); }
    [[nodiscard]] Price4 price() const { return load_be32(p + 32); }
    [[nodiscard]] std::uint64_t match() const { return load_be64(p + 36); }
};

// 'Q': opening, closing or halt cross. Shares may be 0 (no cross). No book effect.
struct CrossTrade : Header {
    [[nodiscard]] std::uint64_t shares() const { return load_be64(p + 11); }
    [[nodiscard]] std::string_view stock() const { return alpha(19, 8); }
    [[nodiscard]] Price4 price() const { return load_be32(p + 27); }
    [[nodiscard]] std::uint64_t match() const { return load_be64(p + 31); }
    [[nodiscard]] char cross_type() const { return static_cast<char>(p[39]); }
};

// 'B': voids an earlier E, C or P execution. No book effect.
struct BrokenTrade : Header {
    [[nodiscard]] std::uint64_t match() const { return load_be64(p + 11); }
};

// 'I': auction imbalance information.
struct Imbalance : Header {
    [[nodiscard]] std::uint64_t paired_shares() const { return load_be64(p + 11); }
    [[nodiscard]] std::uint64_t imbalance_shares() const { return load_be64(p + 19); }
    [[nodiscard]] char direction() const { return static_cast<char>(p[27]); }
    [[nodiscard]] std::string_view stock() const { return alpha(28, 8); }
    [[nodiscard]] Price4 far_price() const { return load_be32(p + 36); }
    [[nodiscard]] Price4 near_price() const { return load_be32(p + 40); }
    [[nodiscard]] Price4 reference_price() const { return load_be32(p + 44); }
    [[nodiscard]] char cross_type() const { return static_cast<char>(p[48]); }
};

// EndOfSession: a zero-length BinaryFILE record, which marks the end of the session.
enum class Dispatch : std::uint8_t { Handled, Ignored, EndOfSession, UnknownType, BadLength };

// Decodes the type of one framed message and calls the matching handler member, if the
// handler defines it; the check happens at compile time, so unhandled types cost one
// switch. Messages whose length does not match the specification are not dispatched.
template <class H>
Dispatch dispatch(Bytes msg, H& h) {
    if (msg.empty()) {
        return Dispatch::EndOfSession;
    }
    const unsigned char* p = msg.data();
    const std::uint8_t expected = kMessageLength[p[0]];
    if (expected == 0) {
        return Dispatch::UnknownType;
    }
    if (msg.size() != expected) {
        return Dispatch::BadLength;
    }
    switch (p[0]) {
        case 'A':
        case 'F':
            if constexpr (requires { h.on_add(AddOrder{p}); }) {
                h.on_add(AddOrder{p});
                return Dispatch::Handled;
            }
            break;
        case 'E':
            if constexpr (requires { h.on_execute(OrderExecuted{p}); }) {
                h.on_execute(OrderExecuted{p});
                return Dispatch::Handled;
            }
            break;
        case 'C':
            if constexpr (requires { h.on_execute_with_price(OrderExecutedWithPrice{p}); }) {
                h.on_execute_with_price(OrderExecutedWithPrice{p});
                return Dispatch::Handled;
            }
            break;
        case 'X':
            if constexpr (requires { h.on_cancel(OrderCancel{p}); }) {
                h.on_cancel(OrderCancel{p});
                return Dispatch::Handled;
            }
            break;
        case 'D':
            if constexpr (requires { h.on_delete(OrderDelete{p}); }) {
                h.on_delete(OrderDelete{p});
                return Dispatch::Handled;
            }
            break;
        case 'U':
            if constexpr (requires { h.on_replace(OrderReplace{p}); }) {
                h.on_replace(OrderReplace{p});
                return Dispatch::Handled;
            }
            break;
        case 'P':
            if constexpr (requires { h.on_trade(Trade{p}); }) {
                h.on_trade(Trade{p});
                return Dispatch::Handled;
            }
            break;
        case 'Q':
            if constexpr (requires { h.on_cross(CrossTrade{p}); }) {
                h.on_cross(CrossTrade{p});
                return Dispatch::Handled;
            }
            break;
        case 'B':
            if constexpr (requires { h.on_broken(BrokenTrade{p}); }) {
                h.on_broken(BrokenTrade{p});
                return Dispatch::Handled;
            }
            break;
        case 'S':
            if constexpr (requires { h.on_system(SystemEvent{p}); }) {
                h.on_system(SystemEvent{p});
                return Dispatch::Handled;
            }
            break;
        case 'R':
            if constexpr (requires { h.on_directory(StockDirectory{p}); }) {
                h.on_directory(StockDirectory{p});
                return Dispatch::Handled;
            }
            break;
        case 'H':
            if constexpr (requires { h.on_trading_action(TradingAction{p}); }) {
                h.on_trading_action(TradingAction{p});
                return Dispatch::Handled;
            }
            break;
        case 'I':
            if constexpr (requires { h.on_imbalance(Imbalance{p}); }) {
                h.on_imbalance(Imbalance{p});
                return Dispatch::Handled;
            }
            break;
        default:
            break;
    }
    if constexpr (requires { h.on_other(Header{p}); }) {
        h.on_other(Header{p});
    }
    return Dispatch::Ignored;
}

}  // namespace itch
