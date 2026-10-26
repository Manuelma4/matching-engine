# Identified replacements on the real Nasdaq day

The [identified observer](../../IDENTIFIED_OBSERVER.md) was run on real U messages from
the canonical Nasdaq TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909
bytes). Every captured state was compared byte-for-byte with two independent exports.

## Selection, frozen before reading the file

For MSFT and QQQ, from 10:00:00 and from 14:00:00, the rule takes the first maximal
run of at least three of the symbol's own messages that are all U, keeping at most 16.
Any other message for that symbol ends a run. The seed is the symbol's complete
displayed book after the global message just before the first U. A request that found
nothing would have been recorded as null, with no substitute. All four found a window.

## Results

| Request | First U | Seed orders | Facts | States | Rows |
|---|---|---:|---:|---:|---:|
| MSFT from 10:00 | 10:00:15.319005 | 18,673 | 3 | 4 | 74,692 |
| QQQ from 10:00 | 10:00:00.734654 | 7,220 | 3 | 4 | 28,880 |
| MSFT from 14:00 | 14:00:00.245877 | 19,572 | 4 | 5 | 97,860 |
| QQQ from 14:00 | 14:00:00.510338 | 7,530 | 4 | 5 | 37,650 |

- **18 states, 239,082 order rows:** the observer's output, the export of the
  independent `itchbook` implementation and the local exporter are byte-identical.
  The reference and local validation counters are all zero. Their scopes differ: the
  reference validates the selected symbols only, the local exporter every symbol of the
  prefix.
- **14 facts recomputed from the reference export alone:** the old order's rank and
  visible shares ahead in the preceding state, the old row's values, the new order at
  the back of its level in the following state, and an unchanged order count. All
  match.
- **Delayed observation (1 ms) recomputed** from the snapshot origins. No probe sees
  a snapshot before its delivery.
- **The 18 states do not overlap** the 41 states validated earlier. Distinct,
  independently matched displayed L3/FIFO states rise from **41 to 59**.
- **Input identity:** the full file hashed before and after the phase gives SHA-256
  `5d81c2e1…5bac610f` both times.

The windows show participants moving whole groups of orders one by one. At 14:00 a
QQQ seller re-prices four asks one cent lower. Each order was tenth in its
queue with 5,310 shares ahead and joins the back of the lower level. The rank stays
the same because each move removes the order just ahead of the next one.

## Smoke test on BX

Before the Nasdaq run, the ASan/UBSan build captured MSFT on the BX file of 30 July
2019: 6 states and 5 facts, byte-identical with both exporters, no sanitiser
diagnostics. This was a tool check and is not counted in the coverage above.

## Limits

This is one trading day from 2019, not live data. Only U-only windows are captured.
Agreement with an independent implementation can still share a specification
misunderstanding, and it is not exchange priority. The capture took 121 s under
background QoS. That is a single run, not a benchmark. [The aggregate](result.json)
records every identity. Order references, prices per row and per-event outputs stay
private.
