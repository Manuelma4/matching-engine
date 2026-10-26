# Identified replacements for four new symbols at 10:30 and 13:45

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to four
symbols not requested before, ADBE, COST, AVGO and TXN, on the same canonical Nasdaq
TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes). The tools are the
ones used for [the mid-session run](../2026-10-24-real-identified-midsession/README.md);
only the frozen request set is new.

## Selection, frozen before reading the file

The window rule is unchanged: for each request, the first maximal run of at least three
of the symbol's own messages that are all U, keeping at most 16. Any other message for
that symbol ends a run. The seed is the symbol's complete displayed book after the
global message just before the first U. No queue condition is applied. The eight
requests are the four symbols from 10:30:00 and from 13:45:00, two times not used before
on this day. None of the four symbols appears in any earlier selection or checkpoint list.
A request that found nothing would have been recorded as null, with no substitute. All
eight found a window.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| ADBE from 10:30 | 10:30:13.147891 | 2,664 | 4 | 5 | 13,320 |
| COST from 10:30 | 10:30:05.321976 | 5,498 | 3 | 4 | 21,992 |
| AVGO from 10:30 | 10:30:32.264970 | 3,740 | 3 | 4 | 14,960 |
| TXN from 10:30 | 10:33:17.685788 | 1,688 | 3 | 4 | 6,752 |
| ADBE from 13:45 | 13:45:33.027559 | 2,759 | 3 | 4 | 11,036 |
| COST from 13:45 | 13:45:30.883779 | 5,582 | 3 | 4 | 22,328 |
| AVGO from 13:45 | 13:45:42.287920 | 3,875 | 3 | 4 | 15,500 |
| TXN from 13:45 | 13:46:43.781790 | 1,751 | 3 | 4 | 7,004 |

- **33 states, 112,892 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter; the reference validates the
  selected symbols only, the local exporter every symbol of the prefix.
- **25 facts recomputed from the reference export alone:** the old order's rank,
  visible shares ahead and values in the preceding state, the new order at the back of
  its level in the following state, and an unchanged order count. All match.
- **Delayed observation (1 ms) recomputed** from the snapshot origins. No probe sees a
  snapshot before its delivery.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all thirteen earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **349 to 382**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

Every replacement keeps its size, and none keeps its price, so this run adds no
same-price case. Twenty-two of the 25 old orders were alone at the front of their level
(rank 1, no shares ahead). The others: in TXN from 13:45 a 100-share bid ranked 12th, with
807 shares ahead, and a 100-share ask ranked 3rd, with 110 shares ahead, each move one
cent; in ADBE from 13:45 a 50-share bid ranked 2nd moves up seven cents. In ADBE from
10:30 a 100-share ask moves up seven cents, back down, up and down again; in AVGO from
13:45 a 100-share ask does the same by eight cents three times. U carries no participant
identity, so no cause is assigned to these patterns.

## Limits

This is one trading day from 2019, not live data. Only U-only windows are captured; every
window here is short (three or four facts), so none reached the 16-fact limit. Agreement
with an independent implementation can still share a specification misunderstanding,
and displayed FIFO rank is not exchange priority. The capture took 155 s and 373 MB peak
resident memory under background QoS: a single run, not a benchmark. [The
aggregate](result.json) records every identity. Order references, prices per row and
per-event outputs stay private.
