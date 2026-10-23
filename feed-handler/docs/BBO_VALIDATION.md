# Independent BBO validation

This experiment compares reconstructed Nasdaq displayed best bid and offer (BBO)
against a separately implemented order book. It strengthens the aggregate census
checks in [VALIDATION.md](VALIDATION.md): two implementations can agree on message
counts while assigning the wrong price or quantity to a live quote.

The comparison uses the canonical 2019-12-30 Nasdaq ITCH input and local source
commit `0c45da9`. The external implementation is
[KareemJandali/itchbook](https://github.com/KareemJandali/itchbook/tree/3c646f9da182136125059243b475f7b8baa53773),
pinned to `3c646f9da182136125059243b475f7b8baa53773`. Its source has an
[MIT licence](https://github.com/KareemJandali/itchbook/blob/3c646f9da182136125059243b475f7b8baa53773/LICENSE).
It is built separately; its library code is not incorporated into this reconstruction.

## What is compared

At each common sample time, compare four exact integer values:

| Field | Meaning | Unit |
|---|---|---|
| `ask_px_1` | Lowest resting displayed ask price | Price(4), or price × 10,000 |
| `ask_sz_1` | Total displayed shares at that ask price | Shares across all orders at the price |
| `bid_px_1` | Highest resting displayed bid price | Price(4), or price × 10,000 |
| `bid_sz_1` | Total displayed shares at that bid price | Shares across all orders at the price |

For example, integer price `1576300` represents 157.6300. Integer comparison avoids
rounding tolerances. A missing ask is `9999999999,0`; a missing bid is
`-9999999999,0`. These sentinel prices require signed 64-bit parsing, although valid
wire prices occupy unsigned 32 bits. The CSV header is exactly:

```text
ts,ask_px_1,ask_sz_1,bid_px_1,bid_sz_1
```

This is the Nasdaq venue's displayed BBO. It does not establish consolidated NBBO,
quotes on other venues, hidden liquidity, full depth, order counts at the touch or
queue priority. The external CSV exposes prices and aggregate shares only. Fixed time grids leave the states between samples unverified, even when every
sampled quote agrees.

## The sampling clock is part of the contract

Timestamps are integer nanoseconds since Eastern midnight as carried by ITCH. The
comparison preserves that coordinate system; no UTC or daylight-saving conversion
is required to align two readers of the same file.

For interval `I` and first accepted positive timestamp `t0`, the first grid point is
`(floor(t0 / I) + 1) × I`. If `t0` lies exactly on a boundary, sampling starts at the
following boundary. Before applying each accepted message at time `t`, emit the
current book at every pending grid point `g <= t`, then apply the message.

Therefore an update timestamped exactly `g` is excluded from the snapshot at `g`.
Several updates sharing `g` are all excluded there. Their feed order still governs
the state later observed. A snapshot timestamp identifies the grid, rather than
the timestamp of the last order mutation.

The external clock accepts modelled types `S,R,A,F,E,C,X,D,U,P,Q,H` for the selected
locate, plus every global `S` system event. An `R` directory message resolves the
ticker's locate before that message is filtered, so the matching `R` can advance
the clock. Global `S` can start the grid before any directory message. Other
instruments and metadata types do not advance this selected-symbol clock.

The local exporter nevertheless sends the complete feed through `BookBuilder` for
anomaly and full-day checks. Filtering its sample clock does not suppress validation
of other instruments. Canonical input places directories before their order flow.

There is no EOF flush. Only an accepted message supplies the time that authorises
grid advancement; the byte stream ending is not evidence of a later exchange time.
The implementation is documented in [snapshots.hpp](../include/itch/snapshots.hpp)
and follows the pinned external
[replay entry point](https://github.com/KareemJandali/itchbook/blob/3c646f9da182136125059243b475f7b8baa53773/tools/book_replay.cpp).

## A boundary example you can work through by hand

A separately constructed 245-byte BinaryFILE contains nine messages for synthetic
MSFT: system `O` at 1 ns; directory at 2 ns; bid 10 shares at 10000 and ask 30 at
10100 at 1 ms; execution of five bid shares and cancellation of ten ask shares at
2 ms; bid deletion at 3.5 ms; ask deletion at 4 ms; system `C` at 5 ms.

At a 1 ms interval, the expected five rows are:

| Grid time | Ask price | Ask shares | Bid price | Bid shares | Why this state appears |
|---:|---:|---:|---:|---:|---|
| 1 ms | 9999999999 | 0 | -9999999999 | 0 | Both adds occur at the boundary, after this snapshot |
| 2 ms | 10100 | 30 | 10000 | 10 | Execution and cancellation have not applied yet |
| 3 ms | 10100 | 20 | 10000 | 5 | Both reductions have applied; bid deletion is later |
| 4 ms | 10100 | 20 | -9999999999 | 0 | Bid is deleted; ask deletion is still excluded |
| 5 ms | 9999999999 | 0 | -9999999999 | 0 | Both deletions have applied before system `C` |

Both implementations match this manually derived table byte for byte. As an
intentional negative control, move boundary events before their boundary snapshot:
the rows at 1, 2 and 4 ms change, giving three differing rows out of five. That is a
constructed timing counterexample, not a discrepancy discovered in Nasdaq data.
It demonstrates why a plausible quote sequence can disagree solely because the
sampling contract differs. The [recorded boundary control](validation/2026-10-22-bbo/boundary_control.json)
preserves input/output identities and the observed three-row rejection. The private
fixture and detailed control discrepancies stay under `out/`.

## Reproduce the pinned build and comparison

Run from the repository root. Use fresh output paths on each run. The source
archive avoids creating an external Git checkout or branch. Inspect its CMake and
replay source before building. Only `book_replay` is needed; its prerequisites are
CMake 3.20+, C++20, zlib and Threads.

```bash
mkdir -p data/reference
curl --fail --location \
  'https://codeload.github.com/KareemJandali/itchbook/tar.gz/3c646f9da182136125059243b475f7b8baa53773' \
  --output data/reference/itchbook-3c646f9.tar.gz
tar -xzf data/reference/itchbook-3c646f9.tar.gz -C data/reference
cmake -S data/reference/itchbook-3c646f9da182136125059243b475f7b8baa53773 \
  -B data/reference/build-3c646f9 -DCMAKE_BUILD_TYPE=Release
cmake --build data/reference/build-3c646f9 --target book_replay -j2
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine
cmake --build build --target itch_snapshots -j2
```

Skip download/extraction when the verified pinned source is already present. With
the previously identified archive and raw BinaryFILE available, the full comparison is:

```bash
python3 bench/compare_bbo.py \
  --local-tool build/itch_snapshots \
  --reference-tool data/reference/build-3c646f9/book_replay \
  --reference-source data/reference/itchbook-3c646f9da182136125059243b475f7b8baa53773 \
  --archive data/12302019.NASDAQ_ITCH50.gz \
  --raw-input data/12302019.NASDAQ_ITCH50.itch \
  --symbol MSFT --symbol QQQ --symbol ALLE --symbol AQB --symbol MKD \
  --interval-ms 1000 \
  --output out/bbo-reproduction-1s \
  --report docs/validation/bbo-reproduction-1s.json
```

The reference receives the gzip archive; the local exporter receives raw bytes.
The runner decompresses the archive itself, checking gzip integrity, and requires
its raw size and SHA-256 to equal the independently hashed raw file. Thus this
experiment compares the same identified bytes, strengthening the earlier comparison
to an external published census whose underlying input hash was unavailable.

The canonical raw identity is 8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
The runner also records both executables' hashes and checks SHA-256 of the pinned
external replay entry point and CMake definition. Before/after file identities detect
changes during the run. This identifies the artefacts used; it does not attest the
compiler or prove the provenance of every dependency in either executable.

## Rejecting misleading agreement

[compare_bbo.py](../bench/compare_bbo.py) rejects empty or malformed CSV/JSON, invalid
integer ranges or sentinels, duplicate JSON keys, missing/extra grid points, truncated
coverage and row counts inconsistent with either summary. It requires a non-empty
common grid and evidence that each instrument's book was non-empty during the day.
It compares every exposed price and size exactly, without a numerical tolerance.

The local side must report strict success, system `C`, zero final orders, zero
trailing bytes and zero framing, reconstruction, locate/side or clock anomalies.
The reference must report system `C`, zero unknown references, zero final resting
orders/shares and null final best quotes. Both full-input message counts must agree.
Both processes must succeed without stderr. Exit code zero alone is insufficient:
the reference can return it despite unknown references or unchecked CSV write errors.

Private output retains snapshots, tool logs, complete summaries and bounded first
discrepancy examples containing both sets of quote values. The separate public JSON
contains hashes, counts, coverage, per-field mismatch totals and first discrepancy
timestamps/categories, without publishing historical quote rows. Missing timestamps
are distinct from mismatched quote fields. Investigate the first divergence and its
preceding events before changing either implementation or accepting a convention.
The completed private release suite passed 41/41 CTests, including 26 comparison-runner
cases. Focused exporter and input checks also passed under ASan/UBSan.

## Results

The completed MSFT pilot produced 61,228 one-second rows, including 57,600 non-empty
and two-sided rows, with zero differing rows. Local and external CSV bytes had the
same SHA-256: `05c8c6bed6aa2fa7db91518743268e463f6b516697ef3a29f633fd043f84655e`.
Both readers consumed all 268,744,780 messages and ended with empty books; the local
full-feed checks and external unknown-reference check were clean.

The completed five-instrument [aggregate report](validation/2026-10-22-bbo/independent_bbo.json)
passed every comparison. All four quote fields agree exactly at every sampled time:

| Symbol | One-second snapshots | Non-empty book | Both sides present | Differing rows |
|---|---:|---:|---:|---:|
| MSFT | 61,228 | 57,600 | 57,600 | 0 |
| QQQ | 61,228 | 57,600 | 57,600 | 0 |
| ALLE | 61,228 | 26,987 | 26,985 | 0 |
| AQB | 61,228 | 44,246 | 44,246 | 0 |
| MKD | 61,228 | 43,058 | 40,576 | 0 |
| **Total** | **306,140** | **229,491** | **227,007** | **0** |

The grid spans 11,073,000,000,000 to 72,300,000,000,000 nanoseconds, inclusive.
Local and reference CSV SHA-256 values are identical for each symbol. Every local
run consumed all 268,744,780 messages, reported zero anomalies and ended with no
orders. Every external run read the same message count and reported zero unknown
references and no final orders or shares.

There were no real-data discrepancies in this measured basket. The different counts
of non-empty and both-sides-present rows are genuine coverage facts, not errors.
For example, MKD has 2,482 sampled rows with only one quoted side; both implementations
agree on those states. AQB has only 893 applied reference events but 44,246 non-empty
samples: a quote can persist over many sample times without a new event.
The three differences in the synthetic timing control remain deliberately introduced
and are not included as real-day mismatches.

The [100 ms follow-up](validation/2026-10-22-bbo/independent_bbo_100ms.json) also passed:

| Symbol | 100 ms snapshots | Non-empty book | Both sides present | Differing rows |
|---|---:|---:|---:|---:|
| MSFT | 612,280 | 576,000 | 575,999 | 0 |
| QQQ | 612,280 | 575,993 | 575,993 | 0 |
| **Total** | **1,224,560** | **1,151,993** | **1,151,992** | **0** |

This grid starts at 11,072,100,000,000 ns and ends at 72,300,000,000,000 ns.
The denser MSFT sample includes one state with only one quoted side; no such state
appeared on its one-second grid. That difference in coverage is not an implementation
discrepancy: both readers agree on it exactly. Changing a sample rate changes which
states are observed. Even the 100 ms result cannot establish agreement between its
sample times. Reproduce it with the same command, symbols MSFT and QQQ only,
`--interval-ms 100`, and new private output/report paths.

Across both experiments, 1,530,700 sampled rows were compared with zero discrepancies.
The counts include overlapping sample times between the two grids; they are not
1,530,700 unique event states.

An independently written decoder is useful corroboration, while common assumptions
or bugs can remain. This experiment supplies neither a separate vendor/exchange
oracle nor proof of correct queues, deeper levels or every intermediate event state.
