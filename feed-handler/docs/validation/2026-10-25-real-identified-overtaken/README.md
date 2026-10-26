# Same-price replacements that other orders overtake

[The previous queued run](../2026-10-25-real-identified-queued-new-symbols/README.md) found
that 19 of 20 same-price replacements behind other orders were already last at their
level, so moving to the back changed nothing visible. This record asks the canonical
Nasdaq TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes) only for
replacements where other displayed orders really stand behind the old order. The
[identified observer](../../IDENTIFIED_OBSERVER.md) and both exporters are unchanged; the
capture tool gains one request option.

## Code change

`itch_identified_capture` accepts a third value in its optional `need` column,
`queued_same_price_overtaken`: the kept U must include a replacement that keeps the old
order's price while, just before it, at least one displayed order stood ahead of the old
order and at least one stood behind it at that price and side. The test runs on the book
before the U is applied, as for `queued_same_price`; a run without such a U is still
skipped whole. Five-column requests and the two earlier values behave as before.

Before any market data was read with it:

- a hand-built 17-message file, with one window of each kind the condition must reject
  (already last, price changed, first in queue, qualifying U beyond `max_facts`) and one
  it must accept, passes 9 checks in a Release build and an ASan/UBSan build
  (`-fno-sanitize-recover=all`), twice each, with identical outputs and no warnings;
- four mutants (behind condition dropped, ahead condition dropped, price check dropped,
  whole-run skip dropped) each take the window designed to catch them and fail 3 or 4 of
  the checks;
- the hand-built file of the [first queued run](../2026-10-23-real-identified-queued/README.md)
  reproduces its earlier outputs byte for byte with both new builds.

## Selection, frozen before reading the file

The request set was frozen before the code change and before any read. The rule is the
earlier one (the first maximal run of at least three of the symbol's own messages that
are all U, keeping at most 16) with the stricter condition. The eight requests are AMD,
MU, SIRI and EBAY from 12:00:00 and from 15:15:00: four symbols no earlier request named,
at two times not used before on this day. A request that found nothing is recorded as
null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | Same price, queued | With orders behind | States | Rows |
|---|---|---:|---:|---:|---:|---:|---:|
| AMD from 12:00 | 15:33:15.356316 | 10,156 | 3 | 1 | 1 | 4 | 40,624 |
| MU from 12:00 | 12:05:27.863961 | 8,624 | 3 | 3 | 1 | 4 | 34,496 |
| SIRI from 12:00 | none | | | | | | |
| EBAY from 12:00 | 12:27:23.310268 | 1,603 | 5 | 1 | 1 | 6 | 9,618 |
| AMD from 15:15 | 15:33:15.356316 | 10,156 | 3 | 1 | 1 | 4 | 40,624 |
| MU from 15:15 | 15:17:06.978124 | 8,709 | 3 | 1 | 1 | 4 | 34,836 |
| SIRI from 15:15 | none | | | | | | |
| EBAY from 15:15 | 15:44:37.050566 | 1,705 | 5 | 1 | 1 | 6 | 10,230 |

- **28 state rows, 24 distinct states, 170,428 order rows:** the observer's output, the
  export of the independent `itchbook` implementation and the local exporter are
  byte-identical. Both exporters report zero on every validation counter. AMD finds no
  qualifying window between 12:00 and 15:15, so both AMD requests take the same window
  and its four states count once.
- **22 facts recomputed from the reference export alone**, and the condition re-checked
  from it: every captured window holds a same-price replacement with orders behind.
- **SIRI finds no window after either time.** An independent re-scan of the whole file
  (own parser and FIFO book in Python, no shared code) finds 14 U-only runs of three or
  more after 12:00 and none holds a same-price replacement at all; it confirms the null
  under both readings of the rule and reproduces all six captured windows exactly. It
  also shows how rare the event is for AMD: of 1,403 such runs after 12:00, 14 hold a
  same-price replacement behind other orders and only one has orders behind it.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all fifteen earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **417 to 441**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

## What the five overtaking cases show

Counting the AMD window once, the windows hold 7 same-price replacements behind other
orders, and 5 of them had orders behind. For each of the 5, the state after the
replacement, read from the reference export, puts the new order last at its level, with
its rank raised by exactly the number of orders that stood behind it and its shares ahead
raised by exactly their shares:

| Request | Side | Rank before → after | Shares ahead before → after |
|---|---|---|---|
| AMD (both times) | bid | 8 → 12 | 855 → 1,655 |
| MU from 12:00 | ask | 11 → 13 | 3,100 → 3,300 |
| EBAY from 12:00 | ask | 13 → 24 | 3,247 → 5,647 |
| MU from 15:15 | bid | 14 → 16 | 2,587 → 2,987 |
| EBAY from 15:15 | bid | 14 → 34 | 4,300 → 8,683 |

The AMD order grows from 100 to 300 shares and the MU orders shrink, while both EBAY
orders keep their size and still move behind 11 and 20 orders. After the first MU
replacement from 12:00, the same order is replaced twice more at that price while
already last, so its rank stays 13. U carries no participant identity, so no cause or
intent is assigned.

## Limits

This is one trading day from 2019, not live data. Windows are chosen for the event, not
sampled, so the five cases say nothing about how often this happens. Agreement with an
independent implementation can still share a specification misunderstanding, and
displayed FIFO rank is not exchange priority: hidden and reserve interest is not in the
feed. The capture took 162 s and 379 MB peak resident memory under background QoS: a
single run, not a benchmark. [The aggregate](result.json) records every identity and the
position counts. Order references, prices per row and per-event outputs stay private.
