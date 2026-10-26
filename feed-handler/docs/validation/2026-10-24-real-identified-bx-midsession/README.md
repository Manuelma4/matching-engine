# Mid-session symbols on BX: one window, six confirmed nulls

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to the Nasdaq
BX TotalView-ITCH 5.0 file for 30 July 2019 (837,472,908 bytes) with the four symbols of
the [Nasdaq mid-session run](../2026-10-24-real-identified-midsession/README.md). The
tools and the window rule are those of the
[first BX run](../2026-10-23-real-identified-bx/README.md); only the frozen request set is
new. Three of the four symbols find no window, and every null was confirmed
independently.

## Selection, frozen before reading the file

For each request: the first maximal run of at least three of the symbol's own messages
that are all U, keeping at most 16. Any other message for that symbol ends a run. The
seed is the symbol's complete displayed book after the global message just before the
first U. The eight requests, written and hashed before the file was opened in this
gate, are CSCO, CMCSA, PEP and NFLX from 10:45:00 and from 14:45:00. None of these
symbols had been requested on BX, and neither time had been used there; a search of the
earlier BX checkpoint lists found no row for them. A request that finds nothing is
recorded as null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| CSCO from 10:45 | null | | | | |
| CMCSA from 10:45 | null | | | | |
| PEP from 10:45 | null | | | | |
| NFLX from 10:45 | 15:59:30.465734 | 29 | 3 | 4 | 116 |
| CSCO from 14:45 | null | | | | |
| CMCSA from 14:45 | null | | | | |
| PEP from 14:45 | null | | | | |
| NFLX from 14:45 | same window as from 10:45 | 29 | 3 | 4 | 116 |

- **8 state rows, 232 order rows:** the observer's output, the export of the independent
  `itchbook` implementation and the local exporter are byte-identical. Both exporters
  report zero on every validation counter.
- **4 distinct states and 3 distinct facts.** NFLX has no U-only run of three between
  10:45 and the last half-minute of the session, so both of its requests reach the same
  window. Those states are counted once.
- **6 fact checks recomputed from the reference export alone** (each request's facts,
  including the repeated ones). All match, and the 1 ms delayed observation is
  recomputed from the snapshot origins.
- **Six nulls, confirmed independently.** CSCO, CMCSA and PEP are in the BX stock
  directory, but none has a U-only run of three after 10:45 or after 14:45. A separate
  re-scan in Python, with its own parser and FIFO book, finds no window for them under
  the tool's reading of the rule or under its literal text, and finds the NFLX window at
  the same seed and first-U sequence numbers, with the same fact count, as the C++
  capture. It reads the same 28,734,686 messages with no book anomaly.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the five earlier BX checkpoint lists. Distinct, independently matched displayed
  L3/FIFO states rise from **345 to 349**.
- **Input identity:** the full file hashed before and after the phase, and again after
  the re-scan, gives SHA-256 `6741035b…a4b842e5` each time.

The seed cut is a deletion. Like the two windows of the earlier BX partial-null run,
this one sits in the closing seconds. It shows three NFLX asks of 100 shares, each first at
its level with no visible shares ahead, each moved down one cent. Who sent them, and
why, is not visible in the feed.

## Disjointness check

The private disjointness check decides which earlier checkpoint lists belong to the same
input file. It treats every fixture list as another input, whatever its path tags say.
Five controls on recorded checkpoint lists, without reading market data, cover both
modes, a run that must fail against itself and an unchanged result for the previous BX
run.

## Limits

One BX trading day from 2019, not live data. Only U-only windows are captured; the one
window lies in the last half-minute of the session, so this is not a sample of the day,
and a null says only that these requests found no window, not how often such windows
occur. Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority. The capture took
10 s and 360 MB peak resident memory under background QoS: a single run, not a
benchmark. [The aggregate](result.json) records every identity. Order references, prices
per row and per-event outputs stay private.
