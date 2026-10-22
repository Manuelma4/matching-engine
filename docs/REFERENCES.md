# References

Sources studied while designing this engine, with the idea taken from each. They were
read for ideas only: no code was copied from any of them. Licences as recorded on
2026-10-22.

## Design

| Source | Licence | Idea used here |
|---|---|---|
| David Gross (Optiver), [When Nanoseconds Matter: Ultrafast Trading Systems in C++](https://github.com/CppCon/CppCon2024/blob/main/Presentations/When_Nanoseconds_Matter.pdf), CppCon 2024 | Slides, study only | The level-container progression replayed in stage 2: `std::map`, then a sorted vector with the best price at the back, searched linearly from the touch |
| Carl Cook (Optiver), [When a Microsecond Is an Eternity](https://github.com/CppCon/CppCon2017/tree/master/Presentations/When%20a%20Microsecond%20Is%20an%20Eternity), CppCon 2017 | Slides, study only | Keep the hot path free of allocation; measure before optimising |
| [chronoxor/CppTrader](https://github.com/chronoxor/CppTrader) | MIT | Pre-allocated orders and array-based levels as the step after standard containers |
| [rigtorp/HashMap](https://github.com/rigtorp/HashMap) | MIT | Open addressing with linear probing and backward-shift deletion instead of tombstones |
| WK Selph, [How to Build a Fast Limit Order Book](http://howtohft.wordpress.com/2011/02/15/how-to-build-a-fast-limit-order-book/) (2011) | Blog | The classic price-level + FIFO + id-index decomposition used by v1 |
| QuantCup 1 winning book ([gist](https://gist.github.com/druska/d6ce3f2bac74db08ee9007cdf98106ef)) | No licence, read only | A price-indexed array of levels, and its weakness: walking empty ticks after the best level empties, which the occupancy bitmap here removes |
| [MurmurHash3](https://github.com/aappleby/smhasher) fmix64 finaliser, Austin Appleby | Public domain | Hash for the order index |
| [xoshiro256\*\* and splitmix64](https://prng.di.unimi.it/), Blackman and Vigna | Public domain | Benchmark random generator, identical on every standard library |

## Semantics

| Source | Idea used here |
|---|---|
| Nasdaq Rule 4756, [SEC Release 34-68762](https://www.sec.gov/files/rules/sro/nasdaq/2013/34-68762.pdf) (SR-NASDAQ-2013-012) | A partial cancellation that reduces size keeps priority; any other modification gets a new timestamp |

## Measurement

| Source | Licence | Idea used here |
|---|---|---|
| [flash1-dev/matching-engine-benchmark](https://github.com/flash1-dev/matching-engine-benchmark) | MIT | Deterministic market regimes and worst-case reporting, because every level structure degrades in some regime |
| [joaquinbejar/OrderBook-rs, BENCHMARKS.md](https://github.com/joaquinbejar/OrderBook-rs/blob/main/BENCHMARKS.md) | MIT | Interleaved A/B launches on Apple Silicon and flagging noisy results |
| [exchange-core](https://github.com/exchange-core/exchange-core) | Apache-2.0 | Latency percentiles against offered load, planned for stage 3 |
| Gil Tene, [How NOT to Measure Latency](https://qconsf.com/sf2012/dl/qcon-sanfran-2012/slides/GilTene_HowNotToMeasureLatency.pdf), QCon 2012 | Slides | Percentile spectra over averages; coordinated omission, to address with an open-loop load generator |
| Denis Bakhvalov, [Performance Analysis and Tuning on Modern CPUs](https://github.com/dendibakh/perf-book) | CC0-1.0 | Profiling method for stage 2 follow-ups |

## Related work

| Project | Licence | Relation |
|---|---|---|
| [KareemJandali/itchbook](https://github.com/KareemJandali/itchbook) | MIT | ITCH parser, L3 book and fill models in one repository; the closest comparable project |
| [groovg/itch-book](https://github.com/groovg/itch-book) | MIT | ITCH book reconstruction with an index-structure ablation |
| [nkaz001/hftbacktest](https://github.com/nkaz001/hftbacktest) | MIT | Queue- and latency-aware tick backtesting, relevant to the planned backtester |
