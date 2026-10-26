# Overtaken same-price replacements: ADI, LRCX, MAR and ROST

[The first overtaken run](../2026-10-25-real-identified-overtaken/README.md),
[its repeat on four more symbols](../2026-10-25-real-identified-overtaken-new-symbols/README.md)
and [the KHC run](../2026-10-26-real-identified-overtaken-khc/README.md) found eleven
same-price replacements that other displayed orders overtake on the canonical Nasdaq
TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes). This record asks the
same question for four further symbols no earlier request named. The
[identified observer](../../IDENTIFIED_OBSERVER.md), the capture tool and both exporters
are unchanged since the first overtaken run: same source, same binary.

## Selection, frozen before reading the file

The rule is the earlier one, unchanged: the first maximal run, at or after the stated
time, of at least three of the symbol's own messages that are all U, keeping at most 16,
with `need = queued_same_price_overtaken` (a kept U keeps the old order's price while at
least one displayed order stands ahead of it and at least one behind it). The eight
requests are ADI, LRCX, MAR and ROST from 11:45:00 and from 14:05:00, two times not used
before on this day. The file was hashed before the run. A request that finds nothing is
recorded as null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | Same price, queued | With orders behind | States | Rows |
|---|---|---:|---:|---:|---:|---:|---:|
| ADI from 11:45 | 15:46:57.307468 | 808 | 3 | 1 | 1 | 4 | 3,232 |
| LRCX from 11:45 | none | | | | | | |
| MAR from 11:45 | none | | | | | | |
| ROST from 11:45 | none | | | | | | |
| ADI from 14:05 | 15:46:57.307468 | 808 | 3 | 1 | 1 | 4 | 3,232 |
| LRCX from 14:05 | none | | | | | | |
| MAR from 14:05 | none | | | | | | |
| ROST from 14:05 | none | | | | | | |

- **Both ADI requests reach the same window.** No qualifying ADI run exists between
  11:45 and 15:46, so the two requests capture one window: 8 captured states, **4
  distinct**, 6,464 order rows (3,232 distinct). The observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical. Both
  exporters report zero on every validation counter.
- **6 facts (3 distinct) recomputed from the reference export alone**, and the condition
  re-checked from it.
- **Six nulls, confirmed independently.** A re-scan of the whole file with its own parser
  and FIFO book in Python (no shared code) finds no window for LRCX, MAR or ROST at either
  time, under both readings of the rule, and reproduces the ADI window exactly (seed,
  first U and fact count) for both requests. LRCX, MAR and ROST have 1,851, 105 and 223
  U-only runs of three or more after 11:45, and 752, 51 and 108 after 14:05; none holds a
  same-price replacement. ADI has 162 such runs after 11:45 and 68 after 14:05; only the
  captured one holds a same-price replacement at all.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all nineteen earlier runs on this file (one of them empty). None
  recurs. Distinct, independently matched displayed L3/FIFO states rise from **475 to
  479**.
- **Input identity:** the full file hashed before and after the capture, and again after
  the re-scan, gives SHA-256 `5d81c2e1…5bac610f` each time.

## What the overtaking case shows

The window holds one same-price replacement on the ask, of an order with six displayed
orders ahead of it and two behind. The state after the replacement, read from the
reference export, puts the new order last at its level, with its rank raised by exactly
the number of orders that stood behind it and its shares ahead raised by exactly their
shares:

| Window | Side | Rank before → after | Shares ahead before → after |
|---|---|---|---|
| ADI, 15:46:57 | ask | 7 → 9 | 336 → 366 |

The order keeps its 100 shares in the replacement and still moves behind 2 orders. U
carries no participant identity, so no cause or intent is assigned.

## Limits

This is one trading day from 2019, not live data. Windows are chosen for the event, not
sampled, so the case, the six nulls and the run counts say nothing about how often this
happens. Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority: hidden and reserve
interest is not in the feed. The capture took 156 s and 374 MB peak resident memory under
background QoS: a single run, not a benchmark. [The aggregate](result.json) records every
identity and the position counts. Order references, prices per row and per-event outputs
stay private.
