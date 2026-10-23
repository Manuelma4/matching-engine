# Matching Engine

A limit order book and matching engine in C++20: price-time priority, limit and market
orders, Nasdaq-style modify, O(1) cancel, and five book variants that each replace one
container of the previous one, benchmarked across five market regimes with identical
output proven by event-stream hashes.

The same repository also contains the [ITCH feed handler](feed-handler/README.md):
an offline Nasdaq decoder and multi-instrument L3 replica that reuses the engine's
storage primitives. The engine decides trades; the replica reconstructs published
exchange events. Start with the [pipeline walkthrough](feed-handler/docs/TECHNICAL_WALKTHROUGH.md)
and [validation record](feed-handler/docs/VALIDATION.md) for independent BBO/depth
comparisons, deterministic journalling, measured storage and bounded causal examples.
The [later-session inventory comparison](feed-handler/docs/validation/2026-10-23-later-session-l3/README.md)
now brings sampled independent displayed L3/FIFO coverage to 41 distinct states,
including four noon/15:30 states with 55,105 ordered row instances and zero differences.

The matching engine, decoder, L3 reconstruction, journal/replay and native queue
simulator are C++20. Python supports experiment orchestration, identity checks,
comparisons and reports; some supplementary observer/queue examples are Python
model prototypes. Their checks are separate from C++ runtime and performance evidence.

## Results at a glance

Single thread, Apple M4 Pro, macOS 26.6, Apple clang 21 `-O3`, no core pinning. Medians of
10 interleaved launches, 1,000,000 operations per regime ([details](docs/BENCHMARKS.md)).

| Regime | First version (`BookV1`) | Default book (`BookLadder`) | p99, default book |
|---|---:|---:|---:|
| fixed-mid | 12.5 M ops/s | **30.0 M ops/s** | 208 ns |
| random-walk | 16.9 M ops/s | **35.3 M ops/s** | 167 ns |
| deep-book (1,000 levels per side) | 10.3 M ops/s | **27.7 M ops/s** | 250 ns |
| flash-crash | 18.1 M ops/s | **34.9 M ops/s** | 167 ns |
| cancel-heavy | 33.0 M ops/s | **56.2 M ops/s** | 125 ns |

Median latency is one tick of the 24 MHz system timer or less (≤ 42 ns) in every regime.
All five variants produce byte-identical event streams on every regime.

## What this is, and is not

- **Is:** a single-threaded matching core with exchange-style semantics, preallocated
  memory and no allocation on the hot path, a reproducible benchmark harness, and a
  measured record of each optimisation, including the ones that did not pay off.
- **Is not:** a networked exchange. There is no gateway, persistence or multi-threading
  yet (stage 3 below), and numbers are from macOS without pinning or kernel bypass.

## Design

```
add_limit / add_market / modify / cancel
                   |
             Book<Store>            matching rules, same interface for every variant
                   |
      Store<Levels, Index>          resting orders only; never matches
      OrderPool | Levels | Index    primitives shared with the market-data replica
```

| Variant | Levels | Order index |
|---|---|---|
| `BookV1` (reference) | `std::map` of `std::list` | `std::unordered_map` |
| `BookMap` | `std::map` to pooled levels, intrusive FIFO | `std::unordered_map` |
| `BookMapOA` | as above | open addressing, backward-shift deletion |
| `BookVec` | sorted vector, best price at the back, searched from the touch | open addressing |
| `BookLadder` (default) | price-indexed ladder, three-level occupancy bitmap for the next best price in O(1) | open addressing |

Orders and levels are 32-byte records addressed by 32-bit slots in preallocated arrays;
the default configuration allocates and touches about 68 MiB once, at construction.
Modify follows Nasdaq Rule 4756: a size reduction keeps priority, any other change takes a
new timestamp, and a re-priced order re-enters through matching. Full semantics,
invariants and memory layout: [docs/DESIGN.md](docs/DESIGN.md).

## What the measurements showed

- Removing per-order allocation alone gave 1.5× to 1.7×.
- An open-addressing index sized for a million orders loses to `std::unordered_map` when few
  orders are live: its 32 MiB table does not fit in cache.
- Sizing capacity to the workload (2^18 instead of 2^20 orders) adds up to 67%: more than
  any container change.
- The sorted vector wins only when activity sits at the touch, and collapses on a deep
  book; the price ladder holds up in every regime.

Each step, with hypothesis and numbers, is in [docs/journal.md](docs/journal.md).

## Correctness

Every variant must reproduce the event stream of `BookV1` exactly: the hashes in
[BENCHMARKS.md](docs/BENCHMARKS.md) cover every report, trade and cancel result of 1,000,000
operations per regime. The test suite is maintained outside this repository and is
available on request: typed unit tests for all variants, allocation-failure injection, and
a differential fuzzer against a naive reference book that checks every report, trade and
queue position after each operation, run under AddressSanitizer and
UndefinedBehaviorSanitizer.

## Build and reproduce

Requires CMake 3.21+ and a C++20 compiler; no third-party dependencies.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/me_bench --book all --regime all   # every variant on every regime
bench/run.sh                               # full protocol, results in docs/bench/<date>/
```

The library is consumable with CMake `FetchContent` (`me` for the books, `me_workloads`
for the order-flow regimes); the benchmark only builds when this is the top-level project.

## Build the feed handler in this repository

The engine-only build remains the default. To build both components without fetching
another engine checkout:

```bash
cmake -S . -B build-combined -DCMAKE_BUILD_TYPE=Release \
  -DME_BUILD_FEED_HANDLER=ON
cmake --build build-combined -j 4
./build-combined/feed-handler/itch_loopback --ops 10000 --seed 42
./build-combined/feed-handler/itch_queue_demo
```

The [native C++ queue example](feed-handler/docs/QUEUE_DEMO.md) needs no input files.
It shows two cancellation assumptions and a fill response pending at the horizon.

The feed handler also supports a [standalone component build](feed-handler/README.md#build).
For an integrated ASan/UBSan build enable both `ME_SANITIZE` and `ITCH_SANITIZE`.
[Integration and historical provenance](feed-handler/docs/INTEGRATION.md) explains
which commands are current and which retained experiments depend on their original
layout. Consolidation does not rerun market-data validation or increase its coverage.

## Roadmap

### Stage 1: features
- [x] Modify with exchange-style priority rules
- [ ] Modify by total order size, so in-flight fills cannot cause an overfill
- [ ] IOC and FOK limit orders, self-trade prevention
- [ ] Event listener interface (compare `std::function`, virtual dispatch and templates)
- [ ] L2 depth snapshot

### Stage 2: performance
- [x] Reproducible harness: deterministic regimes, output hashes, interleaved protocol
- [x] Order pool and intrusive FIFO
- [x] Open-addressing order index
- [x] Sorted level vector searched from the touch
- [x] Price ladder with an occupancy bitmap
- [x] Price-change modify that reuses the order's slot and index entry
- [ ] Sub-tick timing (Processor Trace or `kperf` on Apple Silicon, `rdtsc` on x86)
- [ ] Replay real ITCH order flow through every variant
- [ ] Cold-path splitting, `-mcpu=native`, LTO and PGO, each measured

### Stage 3: system
- [ ] Multiple instruments
- [ ] Gateway thread to matching thread over a lock-free SPSC ring buffer
- [ ] Binary order-entry protocol, append-only input journal and deterministic replay
- [ ] Open-loop load generator: latency against offered rate

## Related projects

- [itch-feed-handler](https://github.com/Manuelma4/itch-feed-handler): decodes Nasdaq
  TotalView-ITCH 5.0 and rebuilds full-depth books on this engine's primitives. Its
  loopback publishes this engine's events as ITCH and checks that the rebuilt books match.
- [MAYAROSERO-Investments](https://github.com/Manuelma4/MAYAROSERO-Investments) and
  [EU Disclosure Atlas](https://github.com/Manuelma4/eu-disclosure-atlas): bar-level
  backtests and an insider-trading event study whose open question, the cost of trading on
  the signal, a tick-level backtester on this engine can measure.

## References

Ideas, sources and their licences: [docs/REFERENCES.md](docs/REFERENCES.md).

## Licence

MIT. See [LICENSE](LICENSE).
