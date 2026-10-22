#pragma once

#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>
#include <vector>

#include "me/types.hpp"

namespace bench {

enum class OpType : std::uint8_t { Limit, Market, Modify, Cancel };
inline constexpr std::size_t kOpTypes = 4;
inline constexpr std::array<const char*, kOpTypes> kOpNames{"limit", "market", "modify", "cancel"};

struct Op {
    OpType type;
    me::Side side;
    me::OrderId id;
    me::Price price;
    me::Quantity qty;
};

// Deterministic order-flow regimes. Each one stresses a different part of a book:
//   fixed-mid     the original workload: narrow book around a constant mid
//   random-walk   the mid drifts, leaving stale orders behind and widening the book
//   deep-book     ~1,000 levels per side with long queues, sustained; inserts and cancels deep
//   flash-crash   random walk with periodic 3,000-tick crashes swept by market orders
//   cancel-heavy  market-maker style quoting at the touch, 60% cancels
enum class Regime : std::uint8_t { FixedMid, RandomWalk, DeepBook, FlashCrash, CancelHeavy };
inline constexpr std::array<Regime, 5> kRegimes{Regime::FixedMid, Regime::RandomWalk,
                                                Regime::DeepBook, Regime::FlashCrash,
                                                Regime::CancelHeavy};

const char* regime_name(Regime regime);
std::optional<Regime> parse_regime(std::string_view name);

// All prices stay inside the default BookConfig band, [1, 65536].
std::vector<Op> generate(Regime regime, std::uint64_t seed, std::size_t n);

}  // namespace bench
