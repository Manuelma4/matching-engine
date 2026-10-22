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
