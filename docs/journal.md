# Performance journal

One entry per meaningful change, with numbers from `me_bench` before and after.

```
### YYYY-MM-DD: <change>
- Hypothesis:
- Change:
- Before: throughput=… p50=… p99=… p99.9=…
- After:  throughput=… p50=… p99=… p99.9=…
- Notes:
```

## Entries

### 2026-10-22: v1 baseline
- Change: order book on `std::map` + `std::list` + `std::unordered_map`.
- Result: throughput ≈ 11.4 M ops/s, p50 = 42 ns, p90 = 166 ns, p99 = 417 ns, p99.9 = 917 ns.
- Notes: the max (several ms) is OS noise (interrupts, scheduling), not the algorithm,
  which is why only percentiles are tracked.

### 2026-10-22: order modify
- Hypothesis: modify should cost about the same as cancel + add, and the refactor that
  extracted `execute_limit` and `remove` should not change the existing paths.
- Change: `OrderBook::modify`. A decrease is applied in place; an increase relinks the
  node at the back of its level with `std::list::splice` (no allocation, iterator stays
  valid); a price change leaves the level and re-enters through matching.
- Before (old 60/10/30 mix, new code, 3 runs): 12.7 – 13.8 M ops/s, p50 ≤ 42 ns,
  p99 = 292 – 333 ns, p99.9 = 750 – 875 ns.
- After (55/10/10/25 mix, 3 runs): 12.7 – 13.5 M ops/s. Per operation, p50 ≤ 42 ns for
  every type; p99: limit 167 – 208, market 291 – 292, modify 333, cancel 333 ns.
- Notes:
  - The first baseline was a single run, and re-running the unchanged mix came out ~15%
    faster, so that gap is run-to-run noise, not the refactor. Every number is now a
    range over at least 3 runs.
  - The first version of the modify mix picked targets from all earlier ids. Counting
    which paths it hit showed 57% of modifies were rejects (15% pointed at market orders,
    which never rest) and under 1% reached the same-price paths. Targets now come from
    limit orders only, and half the modifies change size at the same price.
  - `steady_clock` on Apple Silicon ticks at 24 MHz (41.67 ns), measured directly: the
    smallest non-zero gap between two reads is 41–42 ns. A p50 of 42 ns therefore means
    "one tick or less", and the median cost of each operation is below what this clock
    can resolve. `cntvct_el0` runs off the same 24 MHz timer, so sub-tick numbers need
    batch timing here, or `rdtsc` on x86.
  - A price-change modify frees and reallocates the list node and the index entry
    (2 allocations, like cancel + add). Reusing them is queued for stage 2.

## Stage 2

All numbers below come from one run of the final protocol (`bench/run.sh`, 10 interleaved
launches, commit `3980a79`), so the variants are compared under the same conditions.
Throughput is the median in M ops/s; the order is fixed-mid / random-walk / deep-book /
flash-crash / cancel-heavy.

### 2026-10-22: benchmark harness v2
- Hypothesis: one workload and single runs cannot show where a structure breaks, and
  cannot prove two implementations behave the same.
- Change: private xoshiro256** generator, five regimes, an FNV-1a hash over the full event
  stream, per-operation-type latency, the timer floor, and an interleaved launch protocol
  with medians, ranges and a noise flag. `BookV1` is kept as the reference.
- Result: `v1` 12.5 / 16.9 / 10.3 / 18.1 / 33.0.

### 2026-10-22: order pool and intrusive FIFO (`BookMap`)
- Hypothesis: the list node and the hash node allocated per order dominate; removing them
  should give the largest single gain.
- Change: 32-byte orders in a preallocated slab with a LIFO free list, linked into an
  intrusive FIFO per level; levels still in `std::map`, lookup still `std::unordered_map`.
  A price-change modify now keeps the order's slot and index entry.
- Result: 20.7 / 26.9 / 15.3 / 27.0 / 50.5, 1.5× to 1.7× over `v1`; p99 lower or equal in
  every regime.

### 2026-10-22: open-addressing index (`BookMapOA`)
- Hypothesis: a flat table with no per-order node beats `std::unordered_map` everywhere.
- Change: power-of-two table of 16-byte entries at load ≤ 0.5, fmix64, linear probing,
  backward-shift deletion.
- Result: 22.8 / 28.9 / 18.7 / 28.3 / 47.7. Better with many live orders (deep-book +22%),
  worse with few (cancel-heavy −6%).
- Notes: the hypothesis was wrong as stated. With 2^20 capacity the table is 32 MiB, twice
  the 16 MB cluster L2, and every lookup lands on a random line of it however few orders
  are live. See the capacity entry.

### 2026-10-22: sorted level vector (`BookVec`)
- Hypothesis: following Optiver's CppCon 2024 talk, a vector with the best price at the back,
  searched linearly from the touch, beats `std::map`.
- Change: per side, a vector of `{price, level slot}` sorted best-last. The first version
  stored only slots and read each price through the level pool; prices are now inline.
- Result: 20.6 / 21.4 / 5.6 / 21.7 / 49.8. Ahead of `map-oa` only on cancel-heavy, and a
  collapse on the sustained 1,000-level deep book (limit p99 rises sharply as inserts walk
  and shift hundreds of entries).
- Notes: a negative result here, and an informative one. The layout pays off when activity
  sits at the top few levels; these regimes spread it over 50 ticks or more, and only
  cancel-heavy (quotes within 5 ticks) concentrates it at the touch. Moving prices inline
  did not change the ranking. Real ITCH order flow is the test still to run.

### 2026-10-22: price ladder with an occupancy bitmap (`BookLadder`)
- Hypothesis: direct indexing removes the search entirely; the classic weakness, walking
  empty ticks when the best level empties, disappears with a hierarchical bitmap.
- Change: a level per price in the band, the best level cached per side, and a 64-way,
  three-level bitmap giving the next best price in three count-zero instructions.
- Result: 30.0 / 35.3 / 27.7 / 34.9 / 56.2, 1.7× to 2.7× over `v1` and the best in every
  regime, including flash-crash. Now the default `OrderBook`.

### 2026-10-22: capacity sizing
- Hypothesis: if the index misses cache because of its size, shrinking the capacity to the
  workload should help most where few orders are live.
- Change: none in code; `--max-orders 262144` (16 MiB of pool and index) against the
  default 2^20 (64 MiB), on the regimes whose peak fits.
- Result: ladder +53% / +15% / +67% / +50% on random-walk / deep-book / flash-crash /
  cancel-heavy; `map-oa` +32% / +6% / +39% / +42%.
- Notes: confirmed from both sides. The gain is largest where the live set is small
  relative to the capacity, and small on deep-book, whose ~200,000 live orders keep a large
  working set anyway. Both pool and index shrink, so the split between them needs hardware
  counters.

### 2026-10-22: review fixes and a flawed regime
- An adversarial review found six robustness defects, all reproduced independently and
  fixed with regression tests: signed overflow in the band check for a negative
  `band_low`, unvalidated `band_log2` (a 32-bit shift in the level pools), a slot leak
  and a stuck "full" book when a `std::map` level allocation throws, an order left indexed
  outside every queue when the trade buffer fails to grow during a price-changing modify,
  a division by zero in the deep-book generator for tiny runs, and a silently truncated
  `--max-orders`. Allocation-failure injection then showed `BookV1` itself could leave an
  empty level or an unindexed order behind; its `rest()` now rolls back.
- The first deep-book regime removed about six times more volume per operation than it
  added, so its book drained soon after the build phase and the "deep" results mostly
  measured the build. Market orders were rebalanced (2% of the flow, 100–1,000 lots) and
  the benchmark now reports final resting orders next to the peak: 200,007 / 196,600.
