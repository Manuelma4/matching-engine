Launches per variant: 10. Latency in ns, median over launches; values are multiples of the 41.67 ns timer tick.

Output hashes: identical across all variants on every regime

### fixed-mid

Peak resting orders: 266516. Hash: `1c2e84d7d42692ee`

| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 12.5 (12.2-12.9) | 42 | 354 | 542 | 209 | 292 | 417 | 438 |
| map | 20.7 (19.3-21.6) NOISY | 42 | 333 | 500 | 125 | 250 | 354 | 417 |
| map-oa | 22.8 (21.5-23.4) | 42 | 209 | 292 | 167 | 209 | 250 | 250 |
| vec | 20.6 (19.6-21.4) | 42 | 209 | 292 | 167 | 208 | 250 | 250 |
| ladder | 30.0 (28.5-30.8) | 42 | 208 | 292 | 166 | 167 | 250 | 250 |

### random-walk

Peak resting orders: 88871. Hash: `8645f3b8ca1ccbbe`

| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 16.9 (16.6-17.2) | 42 | 208 | 292 | 208 | 250 | 208 | 125 |
| map | 26.9 (26.0-27.3) | 41 | 125 | 250 | 125 | 208 | 125 | 125 |
| map-oa | 28.9 (28.3-29.9) | 42 | 167 | 250 | 167 | 208 | 167 | 167 |
| vec | 21.4 (21.1-21.9) | 42 | 208 | 291 | 208 | 208 | 208 | 167 |
| ladder | 35.3 (34.4-35.9) | 41 | 167 | 250 | 167 | 167 | 167 | 166 |

### deep-book

Peak resting orders: 200007. Hash: `1e84026647c29865`

| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 10.3 (9.6-10.6) | 83 | 583 | 1666 | 208 | 2250 | 417 | 416 |
| map | 15.3 (12.9-16.8) NOISY | 42 | 459 | 1250 | 125 | 1688 | 333 | 375 |
| map-oa | 18.7 (16.7-19.2) NOISY | 42 | 375 | 917 | 167 | 1166 | 250 | 250 |
| vec | 5.6 (5.4-5.6) | 125 | 625 | 833 | 625 | 1020 | 583 | 250 |
| ladder | 27.7 (25.4-28.6) NOISY | 42 | 250 | 625 | 166 | 875 | 250 | 250 |

### flash-crash

Peak resting orders: 46098. Hash: `8ddf7eaec1fbc873`

| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 18.1 (17.9-18.5) | 42 | 209 | 750 | 167 | 708 | 167 | 125 |
| map | 27.0 (25.8-27.2) | 41 | 167 | 375 | 125 | 375 | 125 | 84 |
| map-oa | 28.3 (25.0-29.1) NOISY | 42 | 167 | 375 | 166 | 375 | 125 | 125 |
| vec | 21.7 (19.3-22.2) NOISY | 42 | 208 | 459 | 208 | 375 | 167 | 166 |
| ladder | 34.9 (34.1-36.2) | 41 | 167 | 375 | 166 | 375 | 125 | 125 |

### cancel-heavy

Peak resting orders: 1361. Hash: `f5e3d6e69b38ab2b`

| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | limit p99 | market p99 | modify p99 | cancel p99 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| v1 | 33.0 (32.7-33.5) | 41 | 125 | 208 | 125 | 209 | 125 | 83 |
| map | 50.5 (49.7-51.5) | 0 | 84 | 167 | 84 | 208 | 42 | 42 |
| map-oa | 47.7 (43.2-49.7) NOISY | 0 | 125 | 209 | 167 | 208 | 42 | 42 |
| vec | 49.8 (47.6-50.9) | 0 | 125 | 208 | 167 | 167 | 42 | 42 |
| ladder | 56.2 (54.1-58.5) | 0 | 125 | 208 | 166 | 167 | 42 | 42 |

