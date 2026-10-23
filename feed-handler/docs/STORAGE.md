# Reference-index comparison on real order flow

The experiment changes the global reference-to-order-slot index while preserving
the order slab, level pool, sorted price vectors, FIFO rules and wire decoder. It
compares two concrete implementations already supplied by the matching engine:

| Build setting | Index | Allocation and lookup policy |
|---|---|---|
| `open_addressed` | `me::OpenAddrIndex` | Flat power-of-two table, fmix64 hashing, linear probing and backward-shift deletion; reserved for at least twice the order capacity |
| `std_unordered` | `me::StdIndex` | `std::unordered_map` with its default integral hash and implementation-specific bucket policy; bucket reservation at construction and node allocation during replay |

This compares complete implementations, including their hash functions, load factors,
bucket sizing and allocator behaviour. It does not isolate one of those mechanisms.
No result should be attributed solely to cache misses or allocation without further
measurements. The default remains `open_addressed`.

## Build and mutation safety

Use separate build directories in the same source checkout; neither directory is a Git
branch or worktree. CMake rejects an unrecognised setting and propagates the selected
layout to every consumer of the `itch` target. This matters because the index is a
member of the public `L3Book` class. Do not mix a library and headers compiled with
different settings in one process.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine \
  -DITCH_REFERENCE_INDEX=open_addressed
cmake --build build -j4
cmake -S . -B build-std-index -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine \
  -DITCH_REFERENCE_INDEX=std_unordered
cmake --build build-std-index -j4
```

An allocating index changes the failure cases. Adding an order stages the reference
mapping and destination level before linking the order; failed preparation releases
the index entry and order slot. Replacement retains the original order and FIFO until
all allocating preparation succeeds, then reuses its order slot and joins the tail
of the destination level. A rejected or failed preparation preserves the original.

Only the standard index stages an additional replacement mapping before committing.
With one order of capacity, the flat table has two slots: temporarily filling both
would remove the empty sentinel required by its deletion algorithm. The flat path
changes its mapping after preparation, when no allocating step remains. The private
harness checks allocation failures at separate stages, populated FIFO states and the
single-order/full-pool boundary.

## Separate correctness, timing and memory passes

Correctness comes first. Replay the identical raw bytes through both builds and both
capacity profiles, recording post-message checkpoints with `itch_journal_replay`.
Require clean full-day lifecycle, matching counts, volumes and fingerprints, and exact
checkpoint-file identity with non-empty intermediate coverage. State fingerprints are
non-cryptographic regression evidence. Equality on selected checkpoints leaves states
between those points unverified; the independent BBO experiment remains separate.

`itch_storage_bench` performs one replay per process. Its timing mode constructs the
builder separately, maps and prefaults the input outside the replay timer, and validates
framing/type/session order before timing. The timed walk dispatches into the builder;
final validation, state hashing and destruction remain outside that interval.
Standard-index node allocations during replay remain inside the timer. Constructor,
replay and teardown seconds are separate fields.

Memory uses a separate `--memory` process which streams through a bounded 16 MiB
buffer. Its peak resident set includes the program, book storage, allocator retention
and stream buffer. It is total process memory, not index-only or exact live-heap bytes.
The mapped timing process's peak also includes input pages, which can dominate an
8.25 GB day; do not label that figure book memory. Neither subtraction of unrelated
high-water marks nor an assumption about node size measures the index footprint.

```bash
./build/itch_storage_bench --max-orders 2097152 --max-levels 2097152 \
  data/12302019.NASDAQ_ITCH50.itch
./build/itch_storage_bench --memory --max-orders 2097152 --max-levels 2097152 \
  data/12302019.NASDAQ_ITCH50.itch
```

RSS uses `getrusage`: bytes on macOS and KiB converted to bytes on Linux. The local
experiment does not establish Linux performance. The memory pass's streaming elapsed
time includes input I/O and is excluded from mapped replay comparisons. There is one
streaming memory pass per variant/profile; the repeated observations apply to timing.

## Repeated protocol

Use the complete canonical Nasdaq 2019-12-30 day and the complete BX 2019-07-30 day.
Their observed live-order peaks are 1,924,078 and 67,283 respectively. Compare the
default 4,194,304-order capacity with fitted capacities of 2,097,152 and 131,072.
These are the next powers of two covering each observed peak, with different amounts
of headroom; they are historical experiment settings, not production sizing advice.
Pass the level capacity explicitly: 2,097,152 by default, and the minimum of that
value and the fitted order capacity in the fitted profile.

Each variant/profile pair must use identical capacities. Sizing changes order storage,
level storage and index reservation together, so a capacity effect cannot be assigned
to the index alone. Hash source files and actual executables, retain build flags and
dependency identities, and check that inputs, binaries and sources remain unchanged.

Launch fresh processes sequentially, with at least five observations per configuration.
Alternate the paired variant order using `AB`, `BA`, `BA`, `AB` across rounds, which
forms `ABBA`/`BAAB` blocks, and rotate case/profile order. Retain every aggregate row
and launch order; report median and min–max range. Do not run other development builds
or heavy validation simultaneously. Prefaulting does not prevent later OS eviction,
and this desktop protocol does not provide CPU pinning or thermal control.

The runner command is:

```bash
python3 bench/compare_storage.py --open-dir build --std-dir build-std-index \
  --case nasdaq data/12302019.NASDAQ_ITCH50.itch 2097152 \
  --case bx data/20190730.BX_ITCH_50.itch 131072 \
  --runs 6 --checkpoint-every 1000000 --output out/storage-comparison \
  --report docs/validation/storage-comparison.json
```

## Recorded results, 2026-10-22

The protocol passed at clean source commit
`52229945705389323519c50a0c234e9fbbcd956c`, using an Apple M4 Pro with 24 GiB RAM,
macOS 26.6.2, Apple clang 21 and Release `-O3 -DNDEBUG`. The machine was on AC power;
core placement, desktop activity and thermal state were not controlled. The tool does
not request an explicit QoS class. Retained evidence includes the
[complete aggregate report](validation/2026-10-22-storage/comparison.json),
[prior-code continuity checks](validation/2026-10-22-storage/prior_code_equivalence.json),
[verification and test record](validation/2026-10-22-storage/verification.json) and
[build/environment record](validation/2026-10-22-storage/build-info.txt).

All eight variant/capacity configurations process their entire identified day with zero
reported anomalies, identical semantic summaries and exact checkpoint-file agreement
within each case. Nasdaq has 269 checkpoints, 268 populated; BX has 29, 28 populated.
Their sampled maxima are 1,920,917 and 67,198 live orders; the full replay peaks are
1,924,078 and 67,283. The canonical checkpoints at the previous ten-million-message
grid also match the earlier validated code exactly. All BX dense checkpoints match a
retained replay binary from that same earlier source commit.

There are 64 sequential launches: eight correctness, eight streaming memory and 48
timing runs. Each timing configuration has six observations and three launches first
in its pair. Constructor and replay values below are medians; parentheses give the
replay min–max range. Streaming RSS is one whole-process observation per configuration.

| Case | Profile | Index | Construct ms | Replay seconds, median (range) | Streaming peak MiB |
|---|---|---|---:|---:|---:|
| Nasdaq | default | open_addressed | 31.74 | 29.497 (28.636–35.016) | 354.4 |
| Nasdaq | default | std_unordered | 16.88 | 49.627 (47.099–53.396) | 309.6 |
| Nasdaq | fit | open_addressed | 13.99 | 32.950 (32.114–35.479) | 226.2 |
| Nasdaq | fit | std_unordered | 10.83 | 54.929 (53.166–67.106) | 230.2 |
| BX | default | open_addressed | 26.12 | 0.991 (0.957–1.017) | 343.5 |
| BX | default | std_unordered | 15.80 | 1.335 (1.324–1.503) | 249.5 |
| BX | fit | open_addressed | 1.08 | 0.722 (0.706–0.755) | 35.4 |
| BX | fit | std_unordered | 0.96 | 1.279 (1.258–1.370) | 34.5 |

Construction medians are lower for the standard index in every matched profile, while its replay
range is entirely above the matching flat-index range in these observations. The
default standard profile has lower streaming RSS; the fitted Nasdaq standard profile
has slightly higher RSS than flat. Memory was not repeated, so these figures provide
no estimate of RSS variability. Teardown timings and every individual measurement are
retained in the aggregate report.

The fitted flat profile uses less memory in both flows. Its Nasdaq replay median rises
from 29.497 to 32.950 seconds and the ranges overlap; reduced reservation did not produce
a speedup in this experiment. BX instead falls from 0.991 to 0.722 seconds, with
disjoint observed ranges. Capacity changes the table load, memory layout and pool sizes;
these observations do not identify the cause of the different outcomes. The negative
Nasdaq result remains part of the evidence.

The default remains `open_addressed`. These two historical venue/day flows on one
desktop establish a bounded comparison of the concrete implementations. They supply
no universal ranking, isolated index-memory measurement, latency percentiles or
hardware-counter explanation. Price-level container alternatives remain unmeasured.

Private verification includes the complete release harness for both builds excluding
the shared runner suite: 51 selected CTests, with three standard-only allocation cases
skipped on flat and no failures; all 51 pass on standard. The shared storage-runner
suite separately passes 16 cases. Standard-index allocation cases (13) and storage-tool
cases (12) also pass ASan/UBSan. Detailed checkpoints and process logs stay ignored;
the public report retains per-run aggregates and identities.
