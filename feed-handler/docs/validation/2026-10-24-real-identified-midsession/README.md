# Identified replacements mid-morning and mid-afternoon

This record applies the [identified observer](../../IDENTIFIED_OBSERVER.md) to four
symbols not requested before, CSCO, CMCSA, PEP and NFLX, on the same canonical Nasdaq
TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes). The tools are the
ones used for [the wider run](../2026-10-23-real-identified-wider/README.md); only the
frozen request set is new.

## Selection, frozen before reading the file

The window rule is unchanged: for each request, the first maximal run of at least three
of the symbol's own messages that are all U, keeping at most 16. Any other message for
that symbol ends a run. The seed is the symbol's complete displayed book after the
global message just before the first U. No queue condition is applied. The eight
requests, written and hashed before the file was opened in this gate, are the four
symbols from 10:45:00 and from 14:45:00, two times not used before on this day. None of
the four symbols appears in any earlier checkpoint list. A request that found nothing
would have been recorded as null, with no substitute. All eight found a window.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| CSCO from 10:45 | 10:45:03.345935 | 11,232 | 16 | 17 | 190,944 |
| CMCSA from 10:45 | 10:45:01.711834 | 2,856 | 16 | 17 | 48,552 |
| PEP from 10:45 | 10:45:04.943964 | 2,519 | 3 | 4 | 10,076 |
| NFLX from 10:45 | 10:45:02.198641 | 9,818 | 4 | 5 | 49,090 |
| CSCO from 14:45 | 14:45:38.976982 | 11,377 | 4 | 5 | 56,885 |
| CMCSA from 14:45 | 14:45:41.141882 | 2,877 | 16 | 17 | 48,909 |
| PEP from 14:45 | 14:45:22.597039 | 2,522 | 3 | 4 | 10,088 |
| NFLX from 14:45 | 14:45:10.245102 | 9,962 | 4 | 5 | 49,810 |

- **74 states, 464,354 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter; the reference validates the
  selected symbols only, the local exporter every symbol of the prefix.
- **66 facts recomputed from the reference export alone:** the old order's rank,
  visible shares ahead and values in the preceding state, the new order at the back of
  its level in the following state, and an unchanged order count. All match.
- **Delayed observation (1 ms) recomputed** from the snapshot origins. No probe sees a
  snapshot before its delivery.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all twelve earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **271 to 345**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

Two of the 66 replacements keep their price. In CSCO from 14:45, a 300-share ask ranked
16th of 25 at its level, with 4,610 shares ahead, is replaced at the same price and the
same size; the new order is 25th, with 5,612 shares ahead. The displayed book therefore
shows nine places lost by an order whose price and size did not change. In PEP from
10:45, a 200-share ask alone at its level is replaced by 46 shares at the same price, so
no change of position can be seen. These are observations of the displayed FIFO order,
not of exchange priority. [Same-price losses have their own record](../2026-10-23-real-identified-queued/README.md).

The two long 10:45 windows look alike: in CSCO and in CMCSA, 16 bids each move up one
cent at an unchanged size, every old order standing 16th to 20th at its level, with up
to 3,022 and 2,857 shares ahead. CMCSA from 14:45 is the mirror image on the ask side.
U carries no participant identity, and this run did not check how the replaced orders
were added, so no cause is assigned.

## Limits

This is one trading day from 2019, not live data. Only U-only windows are captured, and
three of the eight reached the 16-fact limit, so their runs may continue beyond what is
recorded. Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority. The capture took
127 s and 387 MB peak resident memory under background QoS: a single run, not a
benchmark. [The aggregate](result.json) records every identity. Order references,
prices per row and per-event outputs stay private.
