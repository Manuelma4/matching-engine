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
