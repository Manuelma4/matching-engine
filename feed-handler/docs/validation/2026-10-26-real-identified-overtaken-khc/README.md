# Overtaken same-price replacements: CSX, ADP, VRTX and KHC

[The first overtaken run](../2026-10-25-real-identified-overtaken/README.md) and
[its repeat on four more symbols](../2026-10-25-real-identified-overtaken-new-symbols/README.md)
found nine same-price replacements that other displayed orders overtake on the canonical
Nasdaq TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes);
[the next request set](../2026-10-26-real-identified-overtaken-null/README.md) found none.
This record asks the same question for four further symbols no earlier request named.
The [identified observer](../../IDENTIFIED_OBSERVER.md), the capture tool and both
exporters are unchanged since the first overtaken run: same source, same binary.

## Selection, frozen before reading the file

The rule is the earlier one, unchanged: the first maximal run, at or after the stated
time, of at least three of the symbol's own messages that are all U, keeping at most 16,
with `need = queued_same_price_overtaken` (a kept U keeps the old order's price while at
least one displayed order stands ahead of it and at least one behind it). The eight
requests are CSX, ADP, VRTX and KHC from 10:20:00 and from 13:50:00, two times not used
before on this day. The file was hashed before the run. A request that finds nothing is
recorded as null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | Same price, queued | With orders behind | States | Rows |
|---|---|---:|---:|---:|---:|---:|---:|
| CSX from 10:20 | none | | | | | | |
| ADP from 10:20 | none | | | | | | |
| VRTX from 10:20 | none | | | | | | |
| KHC from 10:20 | 11:01:07.947316 | 5,971 | 3 | 1 | 1 | 4 | 23,884 |
| CSX from 13:50 | none | | | | | | |
| ADP from 13:50 | none | | | | | | |
| VRTX from 13:50 | none | | | | | | |
| KHC from 13:50 | 15:52:57.361939 | 6,849 | 12 | 1 | 1 | 13 | 89,037 |

- **17 distinct states, 112,921 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical. Both
  exporters report zero on every validation counter. The two KHC windows are different.
- **15 facts recomputed from the reference export alone**, and the condition re-checked
  from it: each captured window holds a same-price replacement with orders behind.
- **Six nulls, confirmed independently.** A re-scan of the whole file with its own
  parser and FIFO book in Python (no shared code) finds no window for CSX, ADP or VRTX at
  either time, under both readings of the rule, and reproduces both KHC windows exactly
  (seed, first U and fact count). CSX, ADP and VRTX have 369, 315 and 409 U-only runs of
  three or more after 10:20, and 147, 126 and 182 after 13:50; none holds a same-price
  replacement. KHC has 589 such runs after 10:20, and only the two captured ones hold a
  same-price replacement behind other orders.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all eighteen earlier runs on this file (one of them empty). None
  recurs. Distinct, independently matched displayed L3/FIFO states rise from **458 to
  475**.
- **Input identity:** the full file hashed before and after the capture, and again after
  the re-scan, gives SHA-256 `5d81c2e1…5bac610f` each time.

## What the two overtaking cases show

Each KHC window holds exactly one same-price replacement behind other orders, and both
had orders behind. The state after the replacement, read from the reference export, puts
the new order last at its level, with its rank raised by exactly the number of orders that
stood behind it and its shares ahead raised by exactly their shares:

| Request | Side | Rank before → after | Shares ahead before → after |
|---|---|---|---|
| KHC from 10:20 | bid | 9 → 10 | 1,100 → 1,450 |
| KHC from 13:50 | bid | 7 → 21 | 2,196 → 4,135 |

Both orders keep their 100 shares in the replacement and still move behind 1 and 14
orders. U carries no participant identity, so no cause or intent is assigned.

## Limits

This is one trading day from 2019, not live data. Windows are chosen for the event, not
sampled, so the two cases, the six nulls and the run counts say nothing about how often
this happens. Agreement with an independent implementation can still share a
specification misunderstanding, and displayed FIFO rank is not exchange priority: hidden
and reserve interest is not in the feed. The capture took 160 s and 375 MB peak resident
memory under background QoS: a single run, not a benchmark. [The aggregate](result.json)
records every identity and the position counts. Order references, prices per row and
per-event outputs stay private.
