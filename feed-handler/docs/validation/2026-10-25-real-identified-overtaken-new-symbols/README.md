# Overtaken same-price replacements for four more symbols

[The first overtaken run](../2026-10-25-real-identified-overtaken/README.md) found five
same-price replacements that other displayed orders overtake on the canonical Nasdaq
TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes), and
[the same question on BX](../2026-10-25-real-identified-bx-overtaken/README.md) found
none. This record asks the Nasdaq day the same question for four symbols no earlier
request named. The [identified observer](../../IDENTIFIED_OBSERVER.md), the capture tool
and both exporters are unchanged since the first overtaken run: same source, same binary.

## Selection, frozen before reading the file

The rule is the earlier one, unchanged: the first maximal run, at or after the stated
time, of at least three of the symbol's own messages that are all U, keeping at most 16,
with `need = queued_same_price_overtaken` (a kept U keeps the old order's price while at
least one displayed order stands ahead of it and at least one behind it). The eight
requests are ORCL, QCOM, GILD and SBUX from 11:15:00 and from 14:35:00, two times not used
before on this day. The file was hashed before the run. A request that finds nothing is
recorded as null, with no substitute.

## Results

| Request | First U | Seed orders | Facts | Same price, queued | With orders behind | States | Rows |
|---|---|---:|---:|---:|---:|---:|---:|
| ORCL from 11:15 | 11:21:49.917379 | 551 | 3 | 3 | 1 | 4 | 2,204 |
| QCOM from 11:15 | none | | | | | | |
| GILD from 11:15 | 15:15:25.106078 | 4,945 | 3 | 3 | 1 | 4 | 19,780 |
| SBUX from 11:15 | 11:50:05.133494 | 7,065 | 3 | 1 | 1 | 4 | 28,260 |
| ORCL from 14:35 | 14:49:55.706151 | 591 | 4 | 1 | 1 | 5 | 2,955 |
| QCOM from 14:35 | none | | | | | | |
| GILD from 14:35 | 15:15:25.106078 | 4,945 | 3 | 3 | 1 | 4 | 19,780 |
| SBUX from 14:35 | none | | | | | | |

- **21 state rows, 17 distinct states, 72,979 order rows:** the observer's output, the
  export of the independent `itchbook` implementation and the local exporter are
  byte-identical. Both exporters report zero on every validation counter. GILD finds no
  qualifying window between 11:15 and 14:35, so both GILD requests take the same 15:15
  window and its four states count once.
- **16 facts recomputed from the reference export alone**, and the condition re-checked
  from it: every captured window holds a same-price replacement with orders behind.
- **Three nulls, confirmed independently.** A re-scan of the whole file with its own
  parser and FIFO book in Python (no shared code) finds no window for QCOM at either time
  or for SBUX from 14:35, under both readings of the rule, and reproduces all five
  captured windows exactly (seed, first U and fact count). QCOM has 802 U-only runs of
  three or more after 11:15; one holds a same-price replacement behind other orders and
  none has an order behind it. SBUX has 218 such runs after 14:35 and none holds a
  same-price replacement.
- **No overlap:** every captured `(symbol, sequence, frame offset)` was checked against
  the checkpoint lists of all sixteen earlier runs on this file. None recurs. Distinct,
  independently matched displayed L3/FIFO states rise from **441 to 458**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

## What the four overtaking cases show

Counting the GILD window once, the windows hold 8 same-price replacements behind other
orders, and 4 of them had orders behind. For each of the 4, the state after the
replacement, read from the reference export, puts the new order last at its level, with
its rank raised by exactly the number of orders that stood behind it and its shares ahead
raised by exactly their shares:

| Request | Side | Rank before → after | Shares ahead before → after |
|---|---|---|---|
| ORCL from 11:15 | ask | 3 → 6 | 500 → 900 |
| GILD (both times) | ask | 10 → 13 | 1,000 → 1,300 |
| SBUX from 11:15 | bid | 11 → 13 | 1,100 → 1,300 |
| ORCL from 14:35 | ask | 16 → 26 | 3,021 → 4,621 |

Three of the orders shrink in the replacement (ORCL from 11:15, GILD and SBUX); the ORCL
order from 14:35 keeps its 100 shares and still moves behind 10 orders. In the ORCL
window from 11:15 and the GILD window, the same order is then replaced twice more at that
price while already last, so its rank stays 6 and 13. U carries no participant identity,
so no cause or intent is assigned.

## Limits

This is one trading day from 2019, not live data. Windows are chosen for the event, not
sampled, so the four cases and the run counts say nothing about how often this happens.
Agreement with an independent implementation can still share a specification
misunderstanding, and displayed FIFO rank is not exchange priority: hidden and reserve
interest is not in the feed. The capture took 162 s and 375 MB peak resident memory under
background QoS: a single run, not a benchmark. [The aggregate](result.json) records every
identity and the position counts. Order references, prices per row and per-event outputs
stay private.
