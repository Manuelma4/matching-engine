#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>
#include <vector>

#include "me/core.hpp"
#include "me/index.hpp"

namespace itch {

// Separate build directories/processes must be used for the two layouts. The CMake
// target propagates this ABI-affecting definition to every consumer of the header.
#if defined(ITCH_STD_REFERENCE_INDEX) && ITCH_STD_REFERENCE_INDEX
inline constexpr bool kUsesStdReferenceIndex = true;
inline constexpr std::string_view kReferenceIndexName = "std_unordered";
using ReferenceIndex = me::StdIndex;
#else
inline constexpr bool kUsesStdReferenceIndex = false;
inline constexpr std::string_view kReferenceIndexName = "open_addressed";
using ReferenceIndex = me::OpenAddrIndex;
#endif

// Search policy changes no representation. Keep its label consistent in every
// consumer by propagating the build definition through the itch target.
#if defined(ITCH_BINARY_LEVEL_SEARCH) && ITCH_BINARY_LEVEL_SEARCH
inline constexpr bool kUsesBinaryLevelSearch = true;
inline constexpr std::string_view kLevelSearchName = "binary";
#else
inline constexpr bool kUsesBinaryLevelSearch = false;
inline constexpr std::string_view kLevelSearchName = "reverse_linear";
#endif

using Locate = std::uint16_t;  // per-day stock id, from the stock directory
using Ref = std::uint64_t;     // order reference number, unique for the whole day
using Price4 = std::uint32_t;  // Price(4): four implied decimal places
using Shares = std::uint32_t;

enum class BookSide : std::uint8_t { Bid, Ask };

// A resting order. The stock id fits in the padding, which keeps the node at 32 bytes.
struct BookOrder {
    Ref ref;
    Shares shares;
    Price4 price;
    me::Slot level;
    me::Slot prev;
    me::Slot next;
    Locate locate;
    BookSide side;
};
static_assert(sizeof(BookOrder) == 32);

struct Quote {
    Price4 price;
    std::uint64_t shares;
    std::uint32_t orders;

    friend bool operator==(const Quote&, const Quote&) = default;
};

// Counters for messages that do not fit the book: they are counted, never fatal.
struct Anomalies {
    std::uint64_t unknown_ref = 0;
    std::uint64_t duplicate_ref = 0;
    std::uint64_t share_underflow = 0;  // executed or cancelled more than was open
    std::uint64_t capacity = 0;
};

// Full-depth (L3) books for every stock of a feed, maintained from order messages only:
// it applies what the feed says and never matches. Built from the matching engine's
// primitives: a fixed slab of 32-byte orders with a LIFO free list, one global
// reference index from order reference to slot (references are unique across the
// day, so one index serves every stock), and a pool of me::Level FIFOs.
//
// Price levels are kept per (stock, side) in a vector sorted with the best price at the
// back, prices stored inline, and by default searched from the touch. ITCH prices are
// not bounded to a small band (stub quotes reach 199,999.99), so a price ladder does
// not apply here.
class L3Book {
public:
    struct Config {
        std::uint32_t max_orders = 1u << 22;  // peak live orders on a busy day is ~2M
        std::uint32_t max_levels = 1u << 21;
    };

    // A book for every possible stock locate: the field is 16 bits, so no value read from a
    // feed, however malformed, can index outside the books.
    static constexpr std::size_t kLocates = std::size_t{1} << 16;

    explicit L3Book(const Config& cfg);

    // Order messages. Each returns false (and counts the anomaly) if it does not apply.
    bool add(Locate locate, Ref ref, BookSide side, Shares shares, Price4 price);
    bool execute(Ref ref, Shares shares);  // E and C
    bool cancel(Ref ref, Shares shares);   // X: partial cancel, keeps priority
    bool remove(Ref ref);                  // D
    // U: back of queue. Rejection or allocation failure preserves the original order.
    bool replace(Ref old_ref, Ref new_ref, Shares shares, Price4 price);

    // Order lookup, valid until the order changes. nullptr if not resting.
    [[nodiscard]] const BookOrder* find(Ref ref) const;

    [[nodiscard]] std::optional<Quote> best(Locate locate, BookSide side) const;
    [[nodiscard]] std::size_t level_count(Locate locate, BookSide side) const;
    [[nodiscard]] std::size_t order_count() const { return orders_.live(); }
    [[nodiscard]] std::size_t peak_orders() const { return peak_orders_; }
    [[nodiscard]] const Anomalies& anomalies() const { return anomalies_; }

    // Visits one stock's levels from the best price outwards: f(Price4, total shares, orders).
    template <class F>
    void for_each_level(Locate locate, BookSide side, F&& f) const {
        const auto& v = sides(locate, side);
        for (auto it = v.rbegin(); it != v.rend(); ++it) {
            const me::Level& l = levels_[it->level];
            f(it->price, l.total, l.count);
        }
    }

    // Visits every order of one side of a stock, best price first and in time priority
    // within a price: f(Price4, Ref, Shares).
    template <class F>
    void visit(Locate locate, BookSide side, F&& f) const {
        const auto& v = sides(locate, side);
        for (auto it = v.rbegin(); it != v.rend(); ++it) {
            for (me::Slot s = levels_[it->level].head; s != me::kNil; s = orders_[s].next) {
                f(it->price, orders_[s].ref, orders_[s].shares);
            }
        }
    }

    // Visits the orders at one price in priority order: f(Ref, Shares).
    template <class F>
    void for_each_order(Locate locate, BookSide side, Price4 price, F&& f) const {
        const me::Slot l = find_level(locate, side, price);
        if (l == me::kNil) {
            return;
        }
        for (me::Slot s = levels_[l].head; s != me::kNil; s = orders_[s].next) {
            f(orders_[s].ref, orders_[s].shares);
        }
    }

private:
    struct LevelEntry {
        Price4 price;
        me::Slot level;
    };
    using SideLevels = std::vector<LevelEntry>;  // best price at the back

    [[nodiscard]] const SideLevels& sides(Locate locate, BookSide side) const {
        return books_[locate][side == BookSide::Bid ? 0 : 1];
    }
    SideLevels& sides(Locate locate, BookSide side) {
        return books_[locate][side == BookSide::Bid ? 0 : 1];
    }

    [[nodiscard]] me::Slot find_level(Locate locate, BookSide side, Price4 price) const;
    me::Slot find_or_create_level(Locate locate, BookSide side, Price4 price);
    void release_level(Locate locate, BookSide side, Price4 price);

    void link(me::Slot s);
    void unlink(me::Slot s);
    void reduce(me::Slot s, Shares shares);

    me::Slab<BookOrder, &BookOrder::next> orders_;
    me::Slab<me::Level, &me::Level::head> levels_;
    ReferenceIndex index_;
    std::vector<std::array<SideLevels, 2>> books_;
    std::size_t peak_orders_ = 0;
    Anomalies anomalies_;
};

}  // namespace itch
