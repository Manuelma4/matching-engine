# Same-price replacements that lose queue position

The earlier real-window records ([first](../2026-10-23-real-identified-windows/README.md),
[second](../2026-10-23-real-identified-wider/README.md) and
[BX](../2026-10-23-real-identified-bx/README.md)) take the first U-only run after a
given time, whatever it contains. This record asks for a specific event on the Nasdaq
day of 30 December 2019: a replacement that keeps the old order's price while that
order had at least one displayed order ahead of it. The new order goes to the back of
the same level, so the [identified observer](../../IDENTIFIED_OBSERVER.md) must report a
non-zero rank and visible shares ahead for the order that gave up its place.

## Selection, frozen before the new mode existed

The rule is the earlier one (the first maximal run of at least three of the symbol's
own messages that are all U, keeping at most 16) with one added condition: the kept U
must include a queued same-price replacement. A run that fails is skipped whole, up to
the symbol's next non-U message. The request file (MSFT, AAPL, SPY and QQQ from
10:15:00 and from 13:00:00, times not used by earlier selections) was written and
hashed before the capture tool gained the condition and before the file was read.
Shared states, and states already in the earlier checkpoint lists of the same file,
would have counted once; none occurred.

`itch_identified_capture` takes the condition as an optional sixth request column,
`need`. Five-column requests behave as before.

## Controls before market data

- **A hand-built ITCH file** (13 messages) holds a rejected run whose remainder contains
  a qualifying U, a rank-2 replacement that changes price, and a qualifying run. Eight
  checks pass in Release and in a Debug ASan/UBSan build (`-fno-sanitize-recover=all`),
  each run twice with identical outputs. Three mutants of the tool built outside the
  repository are each caught: no whole-run skip, rank 1 accepted, price change accepted.
- **Regression:** the BX request set re-run with the new binary reproduces the earlier
  BX capture outputs byte for byte.
- **Observer fixture:** the 48-case fixture passes in both builds with four identical
  outputs and no warnings; the observer library itself is unchanged.

## Results

| Request | First U | Seed orders | Facts | Queued same-price facts | Rows |
|---|---|---:|---:|---:|---:|
| MSFT from 10:15 | 10:23:34.408920 | 18,614 | 3 | 1 | 74,456 |
| AAPL from 10:15 | 10:31:00.208080 | 21,350 | 3 | 1 | 85,400 |
| SPY from 10:15 | 10:23:34.389076 | 1,803 | 5 | 1 | 10,818 |
| QQQ from 10:15 | 10:24:57.564631 | 7,289 | 3 | 1 | 29,156 |
| MSFT from 13:00 | 13:00:23.363098 | 19,473 | 3 | 1 | 77,892 |
| AAPL from 13:00 | 13:57:18.514548 | 21,902 | 3 | 1 | 87,608 |
| SPY from 13:00 | 13:01:58.602415 | 1,882 | 5 | 1 | 11,292 |
| QQQ from 13:00 | 13:06:27.084726 | 7,513 | 4 | 4 | 37,565 |

- **37 states, 414,187 order rows:** the observer's output, the independent `itchbook`
  export and the local exporter are byte-identical. Both exporters report zero on every
  validation counter.
- **29 facts recomputed from the reference export alone** (rank, visible shares ahead,
  old and new order values, new order at the back of its level, unchanged order count),
  and the delayed observation from the snapshot origins. All match.
- **The condition, re-checked from the reference export:** every window holds at least
  one queued same-price replacement; 11 facts in all. Ranks before these replacements
  run from 3 to 12, with 101 to 5,800 visible shares ahead.
- **No overlap** with the 60 earlier identified-window states of this file. Distinct,
  independently matched displayed L3/FIFO states rise from **124 to 161**.
- **Input identity:** the full file hashed before and after gives SHA-256
  `5d81c2e1…5bac610f` both times.

The QQQ window from 13:00 is four bids at one price, each eleventh in its level with
5,800 shares ahead, each re-entering at the back: the same position given up four
times in a row. Whether such an order was later filled, or what its owner intended, is
not observable here.

## Limits

One Nasdaq trading day from 2019, not live data. The windows were chosen for the
event, so they are not a sample of the day, and the condition holds by construction
for at least one fact per window. Agreement with an independent implementation can
share a specification misunderstanding, and displayed FIFO rank is not actual
exchange priority: hidden liquidity, fills and latency are outside this record. The
capture took 142 s and 358 MB peak resident memory under background QoS, in a single
run that is not a benchmark. [The aggregate](result.json) records every identity.
Order references, prices per row and per-event outputs stay private.
