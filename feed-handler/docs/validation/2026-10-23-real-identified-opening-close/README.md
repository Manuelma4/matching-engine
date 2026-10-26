# Identified replacements after the open and before the close

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to four
symbols not requested before, NVDA, GOOGL, FB and INTC, on the same canonical Nasdaq
TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes). The tools are the
ones used for [the wider run](../2026-10-23-real-identified-wider/README.md); only the
frozen request set is new.

## Selection, frozen before reading the file

The window rule is unchanged: for each request, the first maximal run of at least three
of the symbol's own messages that are all U, keeping at most 16. Any other message for
that symbol ends a run. The seed is the symbol's complete displayed book after the
global message just before the first U. No queue condition is applied. The eight
requests, written and hashed before the file was opened in this gate, are the four
symbols from 09:45:00 and from 15:45:00, two times not used before on this day. FB was
the ticker in 2019. A request that found nothing would have been recorded as null, with
no substitute. All eight found a window.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| NVDA from 09:45 | 09:45:00.108740 | 10,501 | 16 | 17 | 178,517 |
| GOOGL from 09:45 | 09:45:00.404081 | 6,111 | 16 | 17 | 103,887 |
| FB from 09:45 | 09:45:00.418272 | 11,690 | 16 | 17 | 198,730 |
| INTC from 09:45 | 09:45:00.230591 | 7,032 | 16 | 17 | 119,544 |
| NVDA from 15:45 | 15:45:02.122004 | 11,407 | 3 | 4 | 45,628 |
| GOOGL from 15:45 | 15:45:00.912135 | 6,717 | 3 | 4 | 26,868 |
| FB from 15:45 | 15:45:15.149801 | 13,149 | 4 | 5 | 65,745 |
| INTC from 15:45 | 15:45:02.699958 | 7,814 | 16 | 17 | 132,838 |

- **98 states, 871,757 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter; the reference validates the
  selected symbols only, the local exporter every symbol of the prefix.
- **90 facts recomputed from the reference export alone:** the old order's rank,
  visible shares ahead and values in the preceding state, the new order at the back of
  its level in the following state, and an unchanged order count. All match.
- **Delayed observation (1 ms) recomputed** from the snapshot origins. No probe sees a
  snapshot before its delivery.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all eleven earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **161 to 259**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

The four 09:45 windows begin within 0.31 s of 09:45:00 and look alike: each yields 16
U on the bid side, every one keeping its size and moving a resting bid up by
between 6.60 and 156.95 dollars, and 45 of the 64 old orders had other displayed orders
ahead of them. That simultaneity across four symbols suggests one participant repricing
deep bids on a timer, but U carries no participant identity and this run did not check
how the replaced orders were added, so this stays an observation. In INTC from 15:45, sixteen asks each move down one cent;
every old order stood 32nd at its level, with up to 6,014 shares ahead. None of the 90
replacements keeps its price, so this set adds no example of a same-price U losing
position; [that case has its own record](../2026-10-23-real-identified-queued/README.md).

## Limits

This is one trading day from 2019, not live data. Only U-only windows are captured, and
five of the eight reached the 16-fact limit, so their runs may continue beyond what is
recorded. Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority. The capture took
144 s and 397 MB peak resident memory under background QoS: a single run, not a
benchmark. [The aggregate](result.json) records every identity. Order references,
prices per row and per-event outputs stay private.
