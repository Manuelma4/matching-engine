# Identified replacements on four more symbols

This record widens the [first real-window run](../2026-10-23-real-identified-windows/README.md)
to AAPL, SPY, AMZN and TSLA on the same canonical Nasdaq TotalView-ITCH 5.0 file for
30 December 2019 (8,251,407,909 bytes). The tools and the
[identified observer](../../IDENTIFIED_OBSERVER.md) are unchanged; only the frozen
request set is new.

## Selection, frozen before reading the file

The window rule is the one used before: for each request, the first maximal run of at
least three of the symbol's own messages that are all U, keeping at most 16. Any other
message for that symbol ends a run. The seed is the symbol's complete displayed book
after the global message just before the first U. The eight requests, written and
hashed before the file was opened in this gate, are the four symbols from 11:00:00 and
from 15:00:00, two times the first run did not use. A request that found nothing would
have been recorded as null, with no substitute. All eight found a window.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| AAPL from 11:00 | 11:00:00.485609 | 21,673 | 3 | 4 | 86,692 |
| SPY from 11:00 | 11:00:00.862672 | 1,851 | 7 | 8 | 14,808 |
| AMZN from 11:00 | 11:00:22.225849 | 30,763 | 7 | 8 | 246,104 |
| TSLA from 11:00 | 11:02:07.254116 | 14,201 | 3 | 4 | 56,804 |
| AAPL from 15:00 | 15:00:09.945642 | 22,124 | 3 | 4 | 88,496 |
| SPY from 15:00 | 15:00:03.301392 | 1,934 | 5 | 6 | 11,604 |
| AMZN from 15:00 | 15:00:57.527440 | 31,279 | 3 | 4 | 125,116 |
| TSLA from 15:00 | 15:00:00.070239 | 14,631 | 3 | 4 | 58,524 |

- **42 states, 688,148 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  Both exporters report zero on every validation counter; the reference validates the
  selected symbols only, the local exporter every symbol of the prefix.
- **34 facts recomputed from the reference export alone:** the old order's rank,
  visible shares ahead and values in the preceding state, the new order at the back of
  its level in the following state, and an unchanged order count. All match.
- **Delayed observation (1 ms) recomputed** from the snapshot origins. No probe sees a
  snapshot before its delivery.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all eight earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **59 to 101**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

Two windows show behaviour the first run did not. In AMZN from 11:00 all seven U form
one chain: each replaces the order the previous one created. The ask cycles through
three prices and three sizes, returns to its starting price and size after four
messages and starts again. The first message of each cycle keeps the price and only
raises the size, yet it still issues a new reference, as every U does. The order was
alone at that price, so this window cannot show the priority a same-price U gives up. In SPY from 11:00, seven bids move up one cent; the
first five each stand eleventh with 1,720 shares ahead, the same pattern of
consecutive orders that the first run showed for QQQ.

## Limits

This is one trading day from 2019, not live data. Only U-only windows are captured,
and all eight lie within a few minutes of their request time. Agreement with an
independent implementation can still share a specification misunderstanding, and it
is not exchange priority. The capture took 135 s and 398 MB peak resident memory under
background QoS: a single run, not a benchmark. [The aggregate](result.json) records
every identity. Order references, prices per row and per-event outputs stay private.
