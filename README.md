# Matching Engine

A limit order book and matching engine in C++20: price-time priority, limit and market
orders, O(1) cancel, a GoogleTest suite and a latency benchmark.

The first version favours correctness and readability. Each later stage replaces one
piece with a faster one, and every change is measured against the previous baseline
(see [docs/journal.md](docs/journal.md)).

## Build

Requires CMake 3.20+ and a C++20 compiler. GoogleTest is fetched automatically.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
ctest --test-dir build
./build/me_bench
```

AddressSanitizer + UndefinedBehaviorSanitizer build:

```bash
cmake -S . -B build-asan -DCMAKE_BUILD_TYPE=Debug -DME_SANITIZE=ON
cmake --build build-asan -j && ./build-asan/me_tests
```

## Design

| Component | Current implementation | Reason |
|---|---|---|
| Price | `int64_t` ticks | Floating point cannot represent most decimal prices exactly |
| Price levels | `std::map<Price, Level>`, bids descending, asks ascending | Best price is `begin()`, O(log n) per level |
| FIFO queue per level | `std::list<RestingOrder>` | Stable iterators, so cancelling one order never invalidates others |
| Order lookup | `std::unordered_map<OrderId, Locator>` | O(1) cancel |
| Trade output | Caller-owned `std::vector<Trade>&` | No allocation on the hot path once the buffer has grown |

Matching rules:

- A trade always executes at the resting order's price.
- A crossing limit order sweeps the best levels first; any remainder rests.
- A market order never rests: the unfilled remainder is cancelled (IOC).
- Every report satisfies `filled + resting + cancelled == qty`.

```
include/me/   public headers (types, OrderBook)
src/          implementation
tests/        GoogleTest suite
bench/        latency / throughput benchmark
docs/         performance journal
```

## Benchmark

`me_bench` replays one million deterministic operations (60% limit, 10% market,
30% cancel) around a fixed mid price and reports throughput and per-operation latency.

Baseline on Apple Silicon (M-series), Release build:

```
throughput : ~11.4 M ops/s
latency ns : p50=42  p90=166  p99=417  p99.9=917
```

Per-op timing uses `steady_clock`, whose own overhead (~20-40 ns) is included in these numbers.

## Roadmap

### Stage 1: features
- [ ] Modify / replace (decrease keeps queue priority; price change or increase loses it)
- [ ] IOC and FOK limit orders
- [ ] Event listener interface (compare `std::function`, virtual dispatch and templates)
- [ ] L2 depth snapshot with O(1) per-level volume
- [ ] Randomised differential tests against a naive reference book

### Stage 2: performance
- [ ] Cycle-counter timing (`cntvct_el0` / `rdtsc`), repeated runs, CPU pinning on Linux
- [ ] Profile with Instruments / `perf` before optimising
- [ ] Preallocated object pool for orders
- [ ] Intrusive doubly linked list instead of `std::list`
- [ ] Price-indexed array of levels instead of `std::map`
- [ ] Open-addressing hash map for the order index

### Stage 3: system
- [ ] Multiple instruments
- [ ] Gateway thread → matching thread over a lock-free SPSC ring buffer (tested under TSan)
- [ ] Binary order-entry protocol over TCP
- [ ] Deterministic replay: same input log, same trades

## References

- Scott Meyers, *Effective Modern C++*
- Anthony Williams, *C++ Concurrency in Action*
- Larry Harris, *Trading and Exchanges*
- Carl Cook, "When a Microsecond Is an Eternity", CppCon 2017
