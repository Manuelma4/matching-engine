# Queued same-price replacements for four further symbols

This record repeats the [queued same-price request](../2026-10-23-real-identified-queued/README.md)
on four symbols not yet asked for under that condition, CSCO, CMCSA, INTC and PEP, on the
same canonical Nasdaq TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909
bytes). The [identified observer](../../IDENTIFIED_OBSERVER.md), the capture tool and both
exporters are the ones used for [the previous run](../2026-10-25-real-identified-new-symbols/README.md);
only the frozen request set is new.

## Selection, frozen before reading the file

The rule is unchanged: the first maximal run of at least three of the symbol's own
messages that are all U, keeping at most 16, and the kept U must include a replacement
that keeps the old order's price while at least one displayed order stood ahead of it
(`need = queued_same_price`). A run that fails is skipped whole. The eight requests are
the four symbols from 11:30:00 and from 14:15:00, two times not used before on this day.
The four symbols had been requested before only without the queue condition, so states
already in those lists would have counted once; none recurred. A request that found
nothing would have been recorded as null, with no substitute. All eight found a window.

## Results

| Request | First U | Seed orders | Facts | Queued same-price | States | Rows |
|---|---|---:|---:|---:|---:|---:|
| CSCO from 11:30 | 11:30:28.169452 | 11,232 | 5 | 5 | 6 | 67,392 |
| CMCSA from 11:30 | 11:46:57.999363 | 2,833 | 3 | 3 | 4 | 11,332 |
| INTC from 11:30 | 12:41:06.199769 | 7,251 | 3 | 3 | 4 | 29,004 |
| PEP from 11:30 | 11:32:02.135608 | 2,540 | 3 | 1 | 4 | 10,160 |
| CSCO from 14:15 | 14:17:24.960792 | 11,381 | 4 | 4 | 5 | 56,905 |
| CMCSA from 14:15 | 14:15:24.499203 | 2,861 | 3 | 1 | 4 | 11,444 |
| INTC from 14:15 | 14:15:04.790732 | 7,317 | 3 | 1 | 4 | 29,268 |
| PEP from 14:15 | 14:41:09.538846 | 2,528 | 3 | 2 | 4 | 10,112 |

- **35 states, 225,617 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter.
- **27 facts recomputed from the reference export alone**, and the queue condition
  re-checked from it: 20 queued same-price replacements, at least one in every window.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all fourteen earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **382 to 417**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

## What "losing position" shows here

A same-price replacement sends the new order to the back of its level. That is a visible
loss of position only if other orders stood behind the old one. A new private check reads
the state before each of the 20 replacements from the reference export and counts the
orders behind the old order at its level. In 19 of 20 the old order was already last, so
its displayed rank does not change: CSCO from 11:30 replaces one ask five times in a row,
each time 19th with 3,626 shares ahead and nothing behind, changing only its size; CSCO
from 14:15 does the same with a bid ranked 43rd. The one exception is the first CMCSA
replacement from 11:30: a bid ranked 15th with two orders (400 shares) behind it moves
behind them and is 17th afterwards. Applied to the earlier queued run, the same check
finds 8 of its 11 replacements already last. The observer's rank and shares-ahead facts
are correct in every case; what they do not show by themselves is whether anyone was
overtaken. U carries no participant identity, so no cause is assigned.

## Limits

This is one trading day from 2019, not live data. Windows are chosen for the event, not
sampled. Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority. The capture took
118 s and 379 MB peak resident memory under background QoS: a single run, not a
benchmark. [The aggregate](result.json) records every identity and the position counts.
Order references, prices per row and per-event outputs stay private.
