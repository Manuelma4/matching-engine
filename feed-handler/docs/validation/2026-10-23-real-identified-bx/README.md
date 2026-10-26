# Identified replacements on a second venue (BX)

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to a second
venue: the Nasdaq BX TotalView-ITCH 5.0 file for 30 July 2019 (837,472,908 bytes). The
tools and the window rule are those of the [first](../2026-10-23-real-identified-windows/README.md)
and [second](../2026-10-23-real-identified-wider/README.md) real-window runs on the
Nasdaq day; only the frozen request set and the input are new.

## Selection, frozen before reading the file

For each request: the first maximal run of at least three of the symbol's own messages
that are all U, keeping at most 16. Any other message for that symbol ends a run. The
seed is the symbol's complete displayed book after the global message just before the
first U. The eight requests, written and hashed before the file was opened in this
gate, are AAPL, SPY, QQQ and AMZN from 10:30:00 and from 14:30:00. A request that found
nothing would have been recorded as null, with no substitute. All eight found a window.

The request file also fixed, in advance, how shared windows are counted: if two
requests land on the same window, its states count once.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| AAPL from 10:30 | 15:55:00.194076 | 40 | 4 | 5 | 200 |
| SPY from 10:30 | 10:37:45.326240 | 40 | 3 | 4 | 160 |
| QQQ from 10:30 | 15:58:53.621795 | 97 | 3 | 4 | 388 |
| AMZN from 10:30 | 15:59:30.204044 | 12 | 5 | 6 | 72 |
| AAPL from 14:30 | same window as from 10:30 | 40 | 4 | 5 | 200 |
| SPY from 14:30 | 14:56:16.446540 | 51 | 3 | 4 | 204 |
| QQQ from 14:30 | same window as from 10:30 | 97 | 3 | 4 | 388 |
| AMZN from 14:30 | same window as from 10:30 | 12 | 5 | 6 | 72 |

- **38 state rows, 1,684 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter.
- **23 distinct states and 18 distinct facts.** U-only runs are rare on BX: AAPL, QQQ
  and AMZN have none between 10:30 and 14:30, so both of their requests reach the same
  window shortly before the close. Those states are counted once.
- **30 fact checks recomputed from the reference export alone** (each request's facts,
  including the repeated ones): the old order's rank, visible shares ahead and values
  in the preceding state, the new order at the back of its level in the following
  state, and an unchanged order count. All match. The 1 ms delayed observation is
  recomputed from the snapshot origins; no probe sees a snapshot before its delivery.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the earlier BX checkpoint list (the MSFT smoke test, which is not counted). The
  Nasdaq-day lists are a different input. Distinct, independently matched displayed
  L3/FIFO states rise from **101 to 124**, now over two venues.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `6741035b…a4b842e5` both times, the value recorded when the file was first validated.

The books are thin: 12 to 97 displayed orders per symbol, against thousands on the
Nasdaq day. The AAPL window shows four consecutive asks, each sixth in its level with
500 shares ahead, each moving down one cent: the same pattern of successive orders at
one queue position that the Nasdaq runs showed for QQQ and SPY. In AMZN every replaced
order was first in its level, with no visible shares ahead.

## Shared windows

Three symbols reach the same window from both start times, so their states are listed
twice. The local exporter refuses repeated checkpoints by design, so the comparison
gives it the distinct states and relabels its output to the observer's state ids before
the byte comparison. This relabelling reproduces the earlier Nasdaq exports exactly and
detects a mutated row.

## Limits

One BX trading day from 2019, not live data. Only U-only windows are captured; seven of
the eight requests land in the last 65 minutes of the session, so this is not a sample
of the day. Agreement with an independent implementation can still share a
specification misunderstanding, and it is not exchange priority. The capture took
11 s and 361 MB peak resident memory under background QoS: a single run, not a
benchmark. [The aggregate](result.json) records every identity. Order references,
prices per row and per-event outputs stay private.
