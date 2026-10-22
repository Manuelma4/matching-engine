# Benchmarks

## What the numbers mean

| Number | Covers | Excludes |
|---|---|---|
| Throughput (M ops/s) | One timer around a replay of 1,000,000 operations on a fresh book, closed loop, single thread | Book construction, workload generation |
| Per-operation latency | Two `steady_clock` reads around each operation, percentiles per operation type | Queueing (closed loop, so there is no coordinated omission to correct) |
| Clock resolution | Apple Silicon `steady_clock` runs on the 24 MHz system timer: every latency is a multiple of 41.67 ns, and "≤ 42" means one tick or less | Sub-tick costs, which need batch timing or hardware counters |
| Output hash | FNV-1a over every report field, every trade field and every cancel result, in order | Nothing: two variants with the same hash produced byte-identical event streams |

## Environment and protocol

| | |
|---|---|
| Machine | Apple M4 Pro (8P + 4E), 24 GB, macOS 26.6.2, AC power, automatic power mode |
| Compiler | Apple clang 21.0.0, `-O3 -DNDEBUG` (CMake Release), no LTO or PGO |
| Process | QoS user-interactive; no core pinning (not available on macOS); nothing else heavy running |
| Protocol | `bench/run.sh`: 10 launches, every variant on every regime per launch, variant order alternating between launches. Medians over launches with the min–max range |
| Raw data | [`bench/2026-10-22/`](bench/2026-10-22/): `raw.csv`, `summary.md`, `env.txt` (commit `3980a79`), `capacity.csv` |

## Regimes

Seed 42, 1,000,000 operations each, generated from a private xoshiro256\*\* stream so they do
not depend on the standard library.

| Regime | Flow | Stresses | Peak resting orders |
|---|---|---|---:|
| `fixed-mid` | 55% limit, 10% market, 10% modify, 25% cancel within 50 ticks of a constant mid | the original workload | 266,516 |
| `random-walk` | same mix, the mid drifts | stale orders far from the touch | 88,871 |
| `deep-book` | 200,000 orders over 1,000 levels per side, then balanced deep adds, cancels, re-prices and touch-clearing market orders; about 197,000 orders still rest at the end | level search far from the touch | 200,007 |
| `flash-crash` | random walk with periodic 3,000-tick crashes and recoveries swept by market orders | finding the next level after the best one empties | 46,098 |
| `cancel-heavy` | market-maker quoting within 5 ticks of the touch, 60% cancels of recent orders | churn at the top of the book | 1,361 |

## Results

Throughput, M ops/s, median over 10 launches (range):

| Variant | fixed-mid | random-walk | deep-book | flash-crash | cancel-heavy |
|---|---:|---:|---:|---:|---:|
| `v1` | 12.5 (12.2–12.9) | 16.9 (16.6–17.2) | 10.3 (9.6–10.6) | 18.1 (17.9–18.5) | 33.0 (32.7–33.5) |
| `map` | 20.7 (19.3–21.6) | 26.9 (26.0–27.3) | 15.3 (12.9–16.8) | 27.0 (25.8–27.2) | 50.5 (49.7–51.5) |
| `map-oa` | 22.8 (21.5–23.4) | 28.9 (28.3–29.9) | 18.7 (16.7–19.2) | 28.3 (25.0–29.1) | 47.7 (43.2–49.7) |
| `vec` | 20.6 (19.6–21.4) | 21.4 (21.1–21.9) | **5.6** (5.4–5.6) | 21.7 (19.3–22.2) | 49.8 (47.6–50.9) |
| `ladder` | **30.0** (28.5–30.8) | **35.3** (34.4–35.9) | **27.7** (25.4–28.6) | **34.9** (34.1–36.2) | **56.2** (54.1–58.5) |

p99 latency of all operations, ns, median over launches:

| Variant | fixed-mid | random-walk | deep-book | flash-crash | cancel-heavy |
|---|---:|---:|---:|---:|---:|
| `v1` | 354 | 208 | 583 | 209 | 125 |
| `map` | 333 | 125 | 459 | 167 | 84 |
| `map-oa` | 209 | 167 | 375 | 167 | 125 |
| `vec` | 209 | 208 | 625 | 208 | 125 |
| `ladder` | 208 | 167 | 250 | 167 | 125 |

Latency of the default book (`ladder`) by operation type, ns:

| Regime | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---:|---:|---:|---:|---:|---:|---:|
| fixed-mid | ≤ 42 | 208 | 292 | 166 | 167 | 250 | 250 |
| random-walk | ≤ 42 | 167 | 250 | 167 | 167 | 167 | 166 |
| deep-book | ≤ 42 | 250 | 625 | 166 | 875 | 250 | 250 |
| flash-crash | ≤ 42 | 167 | 375 | 166 | 375 | 125 | 125 |
| cancel-heavy | ≤ 42 | 125 | 208 | 166 | 167 | 42 | 42 |

Full per-variant tables: [`summary.md`](bench/2026-10-22/summary.md).

### Reading the results

- **Removing per-order allocation is the first large step.** `map` keeps `std::map` and
  `std::unordered_map` and only moves orders into the pool with an intrusive FIFO: 1.5× to
  1.7× over `v1` in every regime.
- **The open-addressing index is not a free win.** It helps where many orders are live
  (`deep-book` +22%, `fixed-mid` +10%) but loses 6% to `std::unordered_map` on
  `cancel-heavy`, where only about 1,400 orders are live: sized for 2^20 orders, the table
  is 32 MiB, so each lookup lands on a random line of a table twice the size of the M4 Pro's
  16 MB cluster L2. See the capacity experiment below.
- **The sorted vector depends on where the activity is.** Its search starts at the touch, so
  it pays off when activity is concentrated there: on `cancel-heavy` (quotes within 5 ticks)
  it edges out `map-oa`. These regimes spread activity evenly over 50 ticks or more, so the
  scan is long, and on the sustained 1,000-level `deep-book` it collapses to 5.6 M ops/s.
  Optiver's result for this layout comes from real flow, where most activity is at the top
  few levels; replaying real ITCH flow is the comparison still to make.
- **The ladder holds up in every regime**: 1.7× to 2.7× over `v1`, the best throughput, and
  the lowest or equal p99 everywhere. The `deep-book` market p99 of 875 ns is matching work:
  those orders take out a few levels of a 1,000-level book each.

### Capacity sizing

Same variants and hashes, with `--max-orders 262144` (pool 8 MiB, index 8 MiB) instead of
the default 1,048,576 (32 + 32 MiB), on the regimes whose peak fits. Six interleaved
launches; `capacity.csv` has the raw rows.

| Regime | `ladder` 2^20 | `ladder` 2^18 | change | `map-oa` 2^20 | `map-oa` 2^18 | change |
|---|---:|---:|---:|---:|---:|---:|
| random-walk | 33.4 | 51.2 | +53% | 26.5 | 34.9 | +32% |
| flash-crash | 33.5 | 55.9 | +67% | 25.8 | 35.8 | +39% |
| cancel-heavy | 56.2 | 84.3 | +50% | 44.8 | 63.8 | +42% |
| deep-book | 26.1 | 29.9 | +15% | 17.1 | 18.1 | +6% |

Sizing the preallocated memory to the workload is worth more than any single container
change above, and the pattern shows why. The gain is large where few orders are live
relative to the capacity, and small on `deep-book`, whose ~200,000 live orders keep a
large working set whatever the capacity. Both the pool and the index shrink here, so the
effect is not attributed to one of them without hardware counters; the index is the likely
main contributor, since its accesses spread over the whole table while the LIFO pool keeps
reusing recently freed slots. `max_orders` should be sized per instrument to peak live
orders plus a margin. The main tables keep the default so every regime runs with one
configuration.

## Output hashes

All five variants produce these hashes (seed 42, 1,000,000 operations):

| Regime | Hash |
|---|---|
| fixed-mid | `1c2e84d7d42692ee` |
| random-walk | `8645f3b8ca1ccbbe` |
| deep-book | `1e84026647c29865` |
| flash-crash | `8ddf7eaec1fbc873` |
| cancel-heavy | `f5e3d6e69b38ab2b` |

Verified with Apple clang and libc++. The workload generator and the hash use no standard
library randomness or hashing, so other toolchains should reproduce them.

## Reproduce

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
./build/me_bench --book all --regime all          # one launch, human-readable
bench/run.sh                                      # full protocol into docs/bench/<date>/
./build/me_bench --book ladder --max-orders 262144 --regime cancel-heavy
```

## Not measured yet

- Sub-tick latency: needs batch timing or hardware counters (Instruments Processor Trace on
  M4, or `kperf`), or `rdtsc` on x86.
- Linux on bare-metal x86 with isolated cores; numbers from Docker on macOS are not valid
  for timing and are never reported.
- Open-loop latency against offered load (coordinated omission), planned with the stage-3
  gateway.
- Real order flow: replaying a Nasdaq ITCH day through these variants, using the
  [ITCH feed handler](https://github.com/Manuelma4/itch-feed-handler).
