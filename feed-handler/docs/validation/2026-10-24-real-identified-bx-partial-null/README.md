# A partly null request set on BX, and null runs in the harness

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to the Nasdaq
BX TotalView-ITCH 5.0 file for 30 July 2019 (837,472,908 bytes) with four symbols not
requested on BX before. The tools and the window rule are those of the
[first BX run](../2026-10-23-real-identified-bx/README.md); only the frozen request set
is new. Half of the requests found nothing, and the null results were confirmed
independently.

## Selection, frozen before reading the file

For each request: the first maximal run of at least three of the symbol's own messages
that are all U, keeping at most 16. Any other message for that symbol ends a run. The
seed is the symbol's complete displayed book after the global message just before the
first U. The eight requests, written and hashed before the file was opened in this
gate, are NVDA, GOOGL, FB (the 2019 ticker) and INTC from 10:00:00 and from 15:00:00,
the symbols of the [Nasdaq opening and close run](../2026-10-23-real-identified-opening-close/README.md).
A request that finds nothing is recorded as null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| NVDA from 10:00 | 15:59:31.095653 | 27 | 6 | 7 | 189 |
| GOOGL from 10:00 | 15:59:30.035360 | 14 | 4 | 5 | 70 |
| FB from 10:00 | null | | | | |
| INTC from 10:00 | null | | | | |
| NVDA from 15:00 | same window as from 10:00 | 27 | 6 | 7 | 189 |
| GOOGL from 15:00 | same window as from 10:00 | 14 | 4 | 5 | 70 |
| FB from 15:00 | null | | | | |
| INTC from 15:00 | null | | | | |

- **24 state rows, 518 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter.
- **12 distinct states and 10 distinct facts.** NVDA and GOOGL have no U-only run of
  three between 10:00 and the last half-minute of the session, so both of their
  requests reach the same window. Those states are counted once.
- **20 fact checks recomputed from the reference export alone** (each request's facts,
  including the repeated ones). All match, and the 1 ms delayed observation is
  recomputed from the snapshot origins.
- **Four nulls, confirmed independently.** FB and INTC are in the BX stock directory,
  but neither has a qualifying run after 10:00 or after 15:00. A separate re-scan in
  Python, with its own parser and FIFO book, finds no window for them under the tool's
  reading of the rule or under its literal text, and finds the NVDA and GOOGL windows
  at the same seed and first-U sequence numbers, with the same fact counts, as the
  C++ capture. It reads the same 28,734,686 messages with no book anomaly.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the earlier BX checkpoint lists (the MSFT smoke test, the first BX run and the
  all-null queued-rule run). Distinct, independently matched displayed L3/FIFO states
  rise from **259 to 271**.
- **Input identity:** the full file hashed before and after the phase, and again after
  the re-scan, gives SHA-256 `6741035b…a4b842e5` each time.

Both windows sit in the closing seconds and every replaced order was first in its
level, with no visible shares ahead. NVDA shows six asks of 100 shares, each moved down
one cent; GOOGL shows four bids of 100 shares moved up by 1, 9, 1 and 2 cents. Who sent
them, and why, is not visible in the feed.

## Null runs in the comparison harness

The exporters refuse an empty checkpoint list, so when every request is null, as in the
[queued-rule run on BX](../2026-10-23-real-identified-bx-queued/README.md), the
comparison harness records the run as "nothing to compare" and checks it on its own
terms: capture exit 0, every
request null, header-only checkpoint and snapshot files, no anomalies, and the full
input hash before and after equal to the declared one. It never counts states. The
check passes on the recorded BX null run and rejects four controls (a run with
captured states, a changed input hash, an added checkpoint row and a failed capture);
these controls read no market data. A run with some null requests, like this one,
takes the normal path: only captured requests are exported and compared.

## Limits

One BX trading day from 2019, not live data. Only U-only windows are captured; both
windows lie in the last half-minute of the session, so this is not a sample of the
day, and a null says only that these requests found no window, not how often such
windows occur. Agreement with an independent implementation can still share a
specification misunderstanding, and displayed FIFO rank is not exchange priority. The
capture took 9 s and 360 MB peak resident memory under background QoS: a single run,
not a benchmark. [The aggregate](result.json) records every identity. Order references,
prices per row and per-event outputs stay private.
