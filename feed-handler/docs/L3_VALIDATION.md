# Independent resting-order and FIFO comparison

This gate compares displayed resting orders in two reconstructions of the same
identified ITCH input. It extends the earlier [BBO comparison](BBO_VALIDATION.md)
and [bounded window checks](HISTORICAL_WINDOW.md). Equal prices, aggregate sizes
and order counts can conceal a different order sequence or per-reference quantity.
Those differences matter before modelling identified visible volume ahead of an order.

The independent implementation remains `KareemJandali/itchbook` commit
`3c646f9da182136125059243b475f7b8baa53773`, from the retained MIT-licensed source
archive. Its headers are used without modification in a private validation wrapper;
external implementation code is not copied into this repository. The local wrapper
uses the existing `BookBuilder` and `L3Book` without changing their semantics.

## Common state contract

Each checkpoint means **after one identified source message has been applied**.
Sequence counts every nonempty BinaryFILE frame from one. Offsets count source bytes
from zero, including two-byte frame lengths. The end offset is exclusive. A checkpoint
retains sequence, frame start/end, original timestamp, body length and type, plus the
selected symbol and locate. Source sequence resolves equal timestamps: sorting by
timestamp or reference would change the experiment.

For the canonical comparison, checkpoints are the same fifteen source-identified
states used in the previous MSFT/QQQ window validation: two seeds and thirteen selected
post-message states. The seed is a reconstructed boundary state. This contract keeps
its original source point separate from the historical projector's chosen seed time.
Both sides and every displayed price level of the selected symbol are exported,
including levels away from the BBO. This is not an every-message full-day comparison.

The private checkpoint CSV has this exact header:

```text
state_id,symbol,locate,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type
```

State IDs are consecutive from one in source order; a source message can request more
than one symbol's state. Each wrapper checks the requested point against the frame
actually read and resolves symbol/locate from the directory before exporting.
It stops after the last requested frame. The resulting prefix is not a full closing
lifecycle validation. The separate full-day evidence retains that earlier claim.

Each wrapper produces an order CSV with the exact header:

```text
state_id,side,price4,fifo_rank,reference,shares
```

Rows use ascending state ID, bids (`B`) before asks (`S`), best price first, then the
book's linked FIFO. Rank starts at one for each price. References remain unsigned
64-bit values; quantities are positive unsigned 32-bit remaining displayed shares.
The common price domain is `1..INT32_MAX` in Price(4), because the reference uses a
signed price and the local book uses an unsigned price. This is wider than the queue
simulator's restricted domain. Out-of-domain orders fail the comparison instead of
wrapping or being silently dropped. Aggregated shares use unsigned 64-bit bounds.

Original priority timestamps and MPID attribution are not common order fields in
these APIs. Allocator addresses, slots and internal level indices are excluded.
The ordered tuples compare the reconstructed FIFO convention, rather than asserting
exchange-calibrated priority for every displayed or hidden order.

## Explicit completeness

A mandatory version-one JSON summary lists **every requested state**, including empty
sides and empty books. Each state has:

- `state_id`, `symbol`, `locate` and `source` with the six source-point fields above;
- `bid` and `ask`, each containing `orders`, `levels`, `shares` and `best_price4`
  (`null` only when empty);
- `exported_orders` and `complete: true`.

The top-level fields are `schema_version: 1`, `boundary: "post_message"`, full-file
`input_bytes`, `scanned_messages`, `consumed_prefix_bytes`, `validation_scope`,
`validation`, `states` and `passed: true`. The validation object contains integer
zero counters named `unknown_references`, `duplicate_references`, `share_underflows`,
`locate_mismatches`, `invalid_messages`, `capacity_failures` and
`timestamp_regressions`. A Boolean zero is not an integer counter.

The local scope is `full_prefix_all_symbols`; its builder processes every source
symbol. The reference scope is `selected_symbols_only`; it applies the selected
symbols while checking framing and timestamps throughout the prefix. These scopes
are recorded separately rather than treated as equivalent whole-feed validation.

The reference wrapper constructs shared storage with the actual locate-bound books.
A default standalone reference book stores locate zero, which would make a claimed
node-locate comparison misleading. Every exported node must agree with its book's
symbol/locate, side, price and lookup result. Enumeration totals must agree with
independently maintained book order/share totals and level aggregates. The reference's
`for_each_order` has a finite level cap; a truncated traversal must fail reconciliation.
The local traversal also reconciles with its level totals. Hard state/order bounds
produce failure, never a successful partial export.

The reference silently overwrites duplicate references and deletes an order after an
oversized reduction. The local book records those anomalies. The wrappers require
valid inputs and reject those cases; this gate does not compare malformed-input
recovery policies. Live reference uniqueness does not establish that a previously
removed reference is never reused during the day.

## Comparison and controls

`bench/compare_l3.py` validates each export independently, reconciles manifest totals
with its ordered rows, then compares both manifests and every ordered tuple exactly.
It accepts no tolerances and never sorts by reference. Missing checkpoints, duplicate
references, malformed or nonfinite JSON, inconsistent counts, invalid ordering and
unrepresented empty sides fail. An all-empty export cannot establish this gate:
populated both-sided, multi-order and deeper-level coverage is required.

The comparator knows the manifests it receives. Producer evidence must also bind them
to the independently retained request list; two producers omitting the same request
would otherwise conceal that omission. The canonical evidence checks both complete
manifest identity lists against the frozen checkpoint CSV.

Private hand-encoded fixtures freeze their expected states before running either
wrapper. Controls include equal-time adds with references deliberately out of numeric
order; partial cancellations/executions retaining rank; same-price replacement losing
its old position; replacement into another level; one atomic post-replacement best
quote; a second instrument; and explicit empty-side/final-empty checkpoints. Deliberate
reference sorting, retained replacement priority and per-order share redistribution
must fail even when BBO/level totals remain unchanged.

The generic comparison command is:

```bash
python3 bench/compare_l3.py \
  --local-orders out/l3-example/local.orders.csv \
  --local-summary out/l3-example/local.summary.json \
  --reference-orders out/l3-example/reference.orders.csv \
  --reference-summary out/l3-example/reference.summary.json \
  --report out/l3-example/comparison.json
```

Use fresh output paths. Keep the checkpoint list, per-order exports, fixtures, source
archives and helper binaries in ignored/private storage. Version aggregate coverage,
discrepancies, exact commands and source/input/reference/helper identities. A later
evidence record must distinguish freshly hashed input from identities merely retained
from previous reports, and prefix replay from complete-day reconstruction.

Passing these comparisons establishes the declared fields and boundaries for the
selected reconstructions. It would not establish hidden priority, full parent aggressive
orders, market impact, hypothetical fills or strategy performance. Expanding the queue
schema or using identified ahead sets requires a separate design and causal audit.

## Recorded canonical baseline

The [canonical aggregate](validation/2026-10-22-l3/canonical.json) passes at clean
`main` source commit `acd2f29d483b688dd5ece18202dfbb9cadf6291f`. Both helpers replay
7,993,582 source frames through byte 273,665,559. The full 8,251,407,909-byte raw file
and the consumed prefix are freshly SHA-256 verified before and after; the full digest
matches the earlier canonical/BBO/journal identity. All 54 reference headers plus
`CMakeLists.txt` and `LICENSE` match the pinned source archive's bytes.

| Symbol | States | Ordered row instances | Level instances | Maximum orders in one state |
|---|---:|---:|---:|---:|
| MSFT | 7 | 13,173 | 3,633 | 1,883 |
| QQQ | 8 | 3,713 | 2,032 | 465 |
| Total | 15 | 16,886 | 5,665 | — |

There are zero tuple or manifest differences. Both 434,409-byte order CSVs have SHA-256
`775f99545d84f47d7031bb8f245176ab81ccdaf8aa44d5f16f80499229c74e2b`.
These counts include repeated orders/levels across checkpoints, not that many distinct
day-wide orders. Every state has both quotes, deeper levels and a multi-order queue.

The private 868-byte, 31-message fixture froze eleven expected states and 49 rows
before either producer ran. Thirty test methods pass in Release and ASan/UBSan;
`Validation.L3Comparison` passes as CTest 99. Three deliberately changed exports
preserving BBO totals fail: reference sorting, retained replacement priority and
redistributed per-order shares. Checked-close and nonblocking FIFO-input controls
also pass. Sanitiser checks cover the private fixtures; the canonical comparison is
Release. Leak detection is disabled because this Apple runtime does not support it.
No performance measurement is claimed.

The [initial failed attempt](validation/2026-10-22-l3/initial_failure.json) is retained.
Its local wrapper rejected unrelated directory symbol `ACEL+` at sequence 50 because
it applied the requested-symbol character policy globally. It also incorrectly applied
the common signed export ceiling to unselected unsigned feed prices. Only the private
wrapper changed: global directory identity and full unsigned prices remain supported,
while selected exports still enforce the common domain. Two new regressions check
unselected warrant/class names and maximum unsigned prices, plus selected-domain
rejection. The decoder, replica, projector and queue kernel are unchanged.

The [verification manifest](validation/2026-10-22-l3/verification.json) retains fixture,
helper, build, test-log and independent final-review identities. Detailed rows remain
ignored under `out/l3-canonical-v2/`; failed helper/source artefacts remain under
`out/l3-canonical-v1/`. This is full displayed depth at fifteen selected points, with
the reference's reconstruction FIFO convention. It adds no every-message full-day,
separate vendor-feed or empirical queue/fill claim.

An additional retained-state diagnostic inspects the two selected named `E` reductions.
One names a non-head order in the reconstructed pre-event price-level FIFO. Both books
still agree on the order state; no cause is inferred from that observation. A future
model must distinguish published named-order reductions from a hypothetical aggressive
order sweeping reconstructed FIFO. Detailed event/source identities remain ignored;
this tiny retrospective diagnostic is not a frequency estimate.

## Additional canonical cancellation and replacement states

The [source-informed extension](validation/2026-10-23-l3-transitions/README.md) now
matches twenty new complete states across four MSFT/QQQ first-X/U windows. Its 22,089
ordered row instances and 6,840 level instances agree exactly, with no overlap with
the fifteen baseline points above: combined distinct-state coverage is 35. Both retained
Release helpers run twice; the comparator and original source/fixtures stay unchanged.
Independent source enumeration precedes the exports, and copied pre/post inventories
verify all six actual X/U deltas, including every unaffected order and relative FIFO.

The one-second and separate ten-second selections were rejected without a first MSFT
X and produced no validated states. A resource-capped availability study found that
event 25.002318269 seconds after Q. The separate final contract explicitly acknowledges
this source knowledge, keeps the original frame/byte and selection caps, and uses null
time limits. No book-agreement filter selects a window. Both failures remain retained.

The actual sample has two partial cancellations and four moved-price replacements;
all four replacements leave BBO unchanged. No complete X depletion or same-price U
appears in these selected transitions. Fresh full raw identity before/after comparison
and the new 284,563,784-byte prefix identity pass. The independent final review rechecks
176 small identities without another raw replay. These finite observations do not
expand the restricted identified-history or causal/transport admission contracts.

## Same-price extension: 37 distinct states

The [same-price replacement comparison](validation/2026-10-23-same-price-l3/README.md)
adds two disjoint QQQ states to the fifteen baseline and twenty X/U states above.
Its 15,072 ordered row instances and 4,730 level instances match the independent
reference exactly. The old best-bid order at rank two is replaced at the level's
thirteen-order tail; BBO prices, sizes and counts remain equal. This supplies the
same-price case absent from the earlier twenty-state extension.

Independent displayed L3/FIFO coverage at that milestone is 15+20+2 = 37 distinct
boundaries. Repeated comparisons and later causal models reuse states; they do not
increase that count. No actual exchange priority, every-event correctness, hidden
liquidity, empirical fill or broader session-coverage claim follows. The
[technical walkthrough](TECHNICAL_WALKTHROUGH.md) connects these checks to the other
layers and the next coverage question.

## Current combined coverage: 41 distinct states

The [later-session comparison](validation/2026-10-23-later-session-l3/README.md)
adds four disjoint complete MSFT/QQQ states at the fixed noon and 15:30 inclusive
feed-clock targets. They contribute 55,105 ordered row instances and 11,837 level
instances. Both independently written C++ selectors agree on the actual global cuts;
the first-greater witness closes each cut without entering the exported state.

Each C++ exporter runs twice; all four full order files are byte-identical and all
ten strict mismatch counters are zero. Full input and separate cut/witness prefix
hashes pass. The earlier measurement refusal remains preserved and unexplained.
Coverage is now 15+20+2+4 = 41 distinct states. The 220,420 rows across repeated files
are row instances, not unique orders or additional historical states. Earlier BBO
counts stay unchanged. This remains sampled reconstruction agreement, with no actual
exchange priority, every-event, vendor-oracle, session-status or fill admission.
