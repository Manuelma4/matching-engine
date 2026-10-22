# Matching Engine

A limit order book and matching engine in C++20: price-time priority, limit and market
orders, order modification with exchange-style queue priority rules, O(1) cancel, and a
latency benchmark.

The first version favours correctness and readability. Each later stage replaces one
piece with a faster one, and every change is measured against the previous baseline
(see [docs/journal.md](docs/journal.md)).

## Build

Requires CMake 3.20+ and a C++20 compiler.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/me_bench
```

AddressSanitizer + UndefinedBehaviorSanitizer build:

```bash
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug -DME_SANITIZE=ON
cmake --build build-asan -j && ./build-asan/me_bench
```

## Design

| Component | Current implementation | Reason |
|---|---|---|
| Price | `int64_t` ticks | Floating point cannot represent most decimal prices exactly |
| Price levels | `std::map<Price, Level>`, bids descending, asks ascending | Best price is `begin()`, O(log n) per level |
| FIFO queue per level | `std::list<RestingOrder>` | Stable iterators, so cancelling or moving one order never invalidates others |
| Order lookup | `std::unordered_map<OrderId, Locator>` | O(1) cancel and modify |
| Trade output | Caller-owned `std::vector<Trade>&` | No allocation on the hot path once the buffer has grown |

### Matching rules

- A trade always executes at the resting order's price.
- A crossing limit order sweeps the best levels first; any remainder rests.
- A market order never rests: the unfilled remainder is cancelled (IOC).
- Every report satisfies `filled + resting + cancelled == qty`.

### Modify rules

Queue position is valuable, so a modification only keeps it when it cannot hurt the
orders queued behind it. This follows the usual exchange convention (CME, Eurex).

| Change | Queue priority | Implementation |
|---|---|---|
| Lower quantity, same price | Kept | Updated in place, O(1) |
| Higher quantity, same price | Lost: moves to the back of the level | `std::list::splice`, O(1), no allocation |
| New price | Lost | Leaves its level and re-enters through matching, so it may trade |

All validation happens before the book is touched, so a rejected modify (unknown order,
zero quantity, invalid price) leaves the book exactly as it was. `new_qty` is the new
open quantity. Exchanges usually take the new *total* size instead, to protect against
fills that arrive while the modify is in flight; that variant is on the roadmap.

```
include/me/   public headers (types, OrderBook)
src/          implementation
bench/        latency / throughput benchmark
docs/         performance journal
```

## Benchmark

`me_bench` replays one million deterministic operations around a fixed mid price
(55% limit, 10% market, 10% modify, 25% cancel) and reports throughput and latency per
operation type. Modifies and cancels target earlier limit orders, some already filled;
half of the modifies keep the price and only change size.

| | |
|---|---|
| Machine | Apple M4 Pro, 12 cores, macOS 26.6 |
| Compiler | Apple clang 21, `-O3 -DNDEBUG` (CMake Release) |
| Method | 3 runs, single thread, no pinning, `steady_clock` around each operation |

Throughput: **12.7 – 13.5 M ops/s**. Latency in ns (range over 3 runs):

| Operation | Count | p50 | p90 | p99 | p99.9 |
|---|---:|---:|---:|---:|---:|
| All | 1,000,000 | ≤ 42 | 125 | 291 | 584 |
| Limit | 548,799 | ≤ 42 | 84 | 167 – 208 | 792 |
| Market | 100,033 | ≤ 42 | 167 | 291 – 292 | 416 – 417 |
| Modify | 100,343 | ≤ 42 | 167 | 333 | 459 |
| Cancel | 250,825 | ≤ 42 | 166 | 333 | 458 – 459 |

On Apple Silicon `steady_clock` is driven by the 24 MHz system timer, so every value is a
multiple of one 41.67 ns tick and a p50 of "≤ 42" means one tick or less. The cost of the
two clock reads is included. Not measured yet: sub-tick latency (needs batch timing on
Apple Silicon or `rdtsc` on x86), pinned cores, Linux, and deeper books.

## Roadmap

### Stage 1: features
- [x] Modify (decrease keeps queue priority; price change or increase loses it)
- [ ] Modify by total order size, so in-flight fills cannot cause an overfill
- [ ] IOC and FOK limit orders
- [ ] Event listener interface (compare `std::function`, virtual dispatch and templates)
- [ ] L2 depth snapshot with O(1) per-level volume

### Stage 2: performance
- [ ] Sub-tick timing: batch timing on Apple Silicon (its counters tick at 24 MHz), `rdtsc` and CPU pinning on x86 Linux
- [ ] Profile with Instruments / `perf` before optimising
- [ ] Price-change modify that reuses the list node and index entry (today it frees and reallocates both, and an allocation failure midway can drop the order)
- [ ] Preallocated object pool for orders
- [ ] Intrusive doubly linked list instead of `std::list`
- [ ] Price-indexed array of levels instead of `std::map`
- [ ] Open-addressing hash map for the order index

### Stage 3: system
- [ ] Multiple instruments
- [ ] Gateway thread → matching thread over a lock-free SPSC ring buffer
- [ ] Binary order-entry protocol over TCP
- [ ] Deterministic replay: same input log, same trades

## Beyond the engine

This book is the core of two follow-up projects:

- **ITCH 5.0 feed handler**: decode Nasdaq's binary market data feed and rebuild full-depth
  books with this engine, detecting sequence gaps and keeping exchange and receive
  timestamps separate.
- **Event-driven backtester**: replay those books tick by tick, with queue position and
  realistic fills. It complements the bar-level, walk-forward backtests in
  [MAYAROSERO-Investments](https://github.com/Manuelma4/MAYAROSERO-Investments) and can
  measure the trading costs left open by the insider event study in
  [EU Disclosure Atlas](https://github.com/Manuelma4/eu-disclosure-atlas).

## References

- Scott Meyers, *Effective Modern C++*
- Anthony Williams, *C++ Concurrency in Action*
- Larry Harris, *Trading and Exchanges*
- Carl Cook, "When a Microsecond Is an Eternity", CppCon 2017

## Licence

MIT. See [LICENSE](LICENSE).
