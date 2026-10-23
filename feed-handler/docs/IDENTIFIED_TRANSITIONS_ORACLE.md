# Frozen canonical identified-transition expectations

This schema accompanies the [exact-source admission contract](IDENTIFIED_TRANSITIONS.md).
It specifies expected data before any new adapter or observer execution. It is not
the logical ledger schema and does not extend the legacy history, transport or queue
profiles. Integers require exact JSON integer types; Boolean aliases, floats, duplicate
keys and non-finite values are invalid. Objects have precisely the fields listed below.

## Independent handwork and source identities

The retained hand-derived input is `out/gate15-probe-design-v3/literal-expectations.json`,
125,558 bytes, SHA-256
`4767359773be7a53423464f37be5e24134de92779069c8abedc7ff27f7e45bfb`.
It fixes all sixteen fact scalar sets and literal event-index arrays for all sixteen
profiles using the accepted independent inventories and original role frames. It
imports or executes no observer, adapter, historical producer, tests or book. Earlier
three-profile notes and a superseded scratch metadata-writer error remain retained;
they do not change the normative four-profile table or constitute a runtime failure.

The freezer projects the fixed handwork without recomputing outcomes. An independently
written auditor must not import the freezer, read handwork outcomes, or import/execute
`identified_events.py`, the old history producer or a future adapter. It may hash the
handwork and implementation files as identities. It derives expectations separately
from the pinned reference CSV, complete summary, selection frames and source clocks.

Both implementations use fixed paths for seven input roles: `delta_audit`,
`gate14_public_evidence`, `observer_contract`, `observer_source`, `reference_orders`,
`reference_summary`, `selection`. Each identity is exactly `{path,bytes,sha256}` with
a positive bounded byte count and lower-case SHA-256. The public evidence must match
the accepted `3c5af0af73320bd9fd9f75476c8ca0b0627eeb7c` blob, its current tracked blob
and the 81,814-byte/a0eb34d2… identity in the admission contract. Never follow executable
commands or arbitrary file paths supplied in a JSON record.

## Oracle root

The root fields are `schema_version`, `model`, `source_scope`, `inputs`,
`hand_expectations`, `expected_totals`, `windows`.

- `schema_version` is integer 1; `model` is `canonical_identified_transition_expectations_v1`.
- `source_scope` is exactly `{raw_authentication:"retained_gate14",raw_opened:false,reference_executed:false,observer_executed:false}`.
- `inputs` contains precisely the seven roles above. `hand_expectations` is the fixed
  handwork identity; no handwork outcome is used as ground truth by the auditor.
- `expected_totals` is exactly `{windows:4,facts:16,source_states:20,profiles:16,probes:164,available_probes:99,captured_row_instances:218428}`.
- `windows` has the four fixed Gate 14 window objects in window-ID order.

The oracle contains no newly generated full order inventories. Every state reference
must resolve to the authenticated complete reference CSV, not an observer-produced
snapshot. Both availability of a seed and later facts are governed by original clocks.

## Windows and independent states

Each window has `window_id`, `symbol`, `locate`, `seed_effective_ns`, `source_end_ns`,
`duration_ns`, `state_ids`, `states`, `facts`, `profiles`. The five `state_ids` preserve
the accepted seed/anchor/tail role mapping. Window-ID order is deliberately not global
chronological order. Duration is source end minus exact seed timestamp.

Each of its five states has `event_index`, `state_id`, `source`, `order_count`,
`side_totals`, `bbo`, `core_ordered_inventory_sha256`, `watched_orders`.
SourcePoint is the unchanged six-field sequence/offset/end/timestamp/body-length/type
object from Gate 14. `event_index` is 0 through 4. Side totals use `bid` and `ask`,
each `{orders,levels,shares,best_price4}`; empty best price is null. BBO has `bid` and
`ask`, each null or `{price4,shares,orders}` at that best price.

Core inventory rows have exactly `side`, `price4`, `fifo_rank`, `reference`, `shares`.
Hash their full retained CSV order as UTF-8
`json.dumps(rows,sort_keys=True,separators=(',',':')) + '\n'` with ASCII escaping.
Do not sort the row list or include state IDs/attribution in that hash.
`watched_orders` is the full-inventory-order subsequence of live references named by
any fact in that window, including old/new U references. Retain original per-price
ranks; never rerank the filtered subset. This diagnostic does not replace comparison
of the complete independent inventory.

## Fact scalar expectations

Each of the four facts has `event_index`, `type`, `source`, `source_locate`,
`tracking_number`, `frame_sha256`, `kind`, `wire`, `before_order`, `after_order`,
`expected_before_order`, `expected_after_order`, `after_attribution`,
`derived_removed_shares`, `fifo_rank_before`, `visible_shares_ahead_before`,
`resolved_resting_price4`.

The core before/after orders are null or the five-field independently exported row.
The expected before/after orders are null or `{reference,side,price4,shares,attribution}`
for comparison with logical facts. Attribution is `{kind,mpid}`: unknown for all seeds,
absent_in_wire for these actual A facts, and inherited through every U chain. Removed
orders have null after attribution. Wire fields and fact kinds follow the unchanged
identified-observation contract; original frames come from authenticated selection
roles and their hashes must match. X removed size is its wire quantity; D/U removed
size is the complete pre-order size. U's after size is its new total.

Derive named rank and visible shares ahead from the complete independent pre-inventory.
Check all unaffected references and relative FIFO against the post-inventory. For U,
verify the old reference disappears, new reference/side/price/total size and inherited
knowledge are correct, and placement follows the declared reconstruction convention.
No implementation under test may supply these expected scalars.

## Profiles, probes and expected counts

Each profile has `name`, `feed_delay_ns`, `horizon_ns`, `probe_times`,
`all_scheduled_delivery_times_ns`, `literal_expected_event_indices`,
`expected_delivered_event_indices`, `expected_pending_event_indices`,
`expected_latest_delivered_event_index`, `expected_probes`, `expected_summary`.
Names/order and clocks follow the admission contract. Each scheduled time is origin+F;
delivery at or before H is included, and later deliveries remain pending in source order.
The literal index array is fixed before output generation, not inferred from an
observer result. The independent audit recomputes the greatest delivered source index
using original clock inequalities, including the last source in any equal-time group.

Each probe has exactly `time_ns`, `available`, `event_index`, `state_id`, `origin_ns`,
`delivery_ns`. An unavailable probe has all four nullable fields null; an available
probe resolves its state/source/inventory through the window's state table. Availability
does not mean a populated book. A later verifier must compare actual null/empty/full
orders appropriately, plus all original source metadata, not only event indices.

`expected_summary` has `probe_count`, `available_probes`, `delivered_snapshots`,
`pending_deliveries`, `snapshot_rows`, `returned_probe_rows`, `captured_rows`.
Snapshot rows sum all five independent inventories once per profile. Returned rows sum
the reference inventory sizes of available probes. Captured rows are their sum, bounded
by the existing one-million-row observer budget. The aggregate 218,428 is expected
repeated source/returned row instances, not newly executed comparisons or distinct orders.

## Freeze and independent altered-expectation controls

Review the private sources and commit both contracts before creating two fresh ignored
output directories. Publish `oracle.json` and `freeze_manifest.json` with checked writes
and actual byte bounds. Both oracle and manifest serialisations must repeat exactly;
use relative output filenames and no generated clock/path-dependent fields in them.
Retain original handwork/source/contract snapshots and all consumed input identities,
verify them before/after, and leave no successful manifest after a publication failure.
Canonical JSON uses sorted object keys, two-space indentation, ASCII escaping, finite
values and one trailing newline. Oracle and manifest each have an 8 MiB bound.

The successful freeze directory has exactly six files: `oracle.json`,
`freeze_manifest.json`, `source_snapshot.py`, `hand_expectations.json`,
`contract_snapshot.md`, `schema_snapshot.md`. The manifest has exactly these fields:

- `schema_version: 1`, `model: "identified_transitions_freeze_manifest_v1"`, `passed: true`;
- `runtime_executed: false`, `raw_opened: false`, `observer_executed: false`;
- `source_commit`, the current full forty-character clean-main commit; `branch: "main"`;
- `accepted_gate14_commit: "3c5af0af73320bd9fd9f75476c8ca0b0627eeb7c"`;
- `protected_inputs`, thirteen unique FileRefs sorted by absolute path: the freezer
  source, handwork, both new contracts, seven input roles and two prior-note records;
- `hand_note_provenance`, exactly `prior_proposal` and
  `superseded_scratch_writer_failure`, each its retained FileRef;
- `artifacts`, exactly the five non-manifest filenames above. Each value is precisely
  `{file,bytes,sha256}`, with `file` equal to that relative filename. Snapshot bytes
  must equal their respective protected original source/handwork/contract bytes.

The two provenance paths are fixed retained records under
`out/gate15-probe-design-v1/design.json` and
`out/gate15-probe-design-v2/writer-failure.json`; they are identities of prior design
work only. No output-directory path or generated clock enters oracle/manifest bytes.
`runtime_executed` refers to admission/observer runtime; the freezer's own file-copy
execution is reported separately. A manifest does not contain its own recursive hash.

Audit the original frozen oracle, then four independent in-memory copies after its
authentic file identity has been checked. The copies must reach these semantic/type
guards rather than failing an outer file hash check:

1. QQQ_X: change removed shares 1,474 to remaining shares 1,026, retaining valid wire
   and inventory inputs. Reject the incorrect cancellation diagnostic.
2. QQQ_U's second U: label inherited unknown attribution absent_in_wire. Its old
   reference was itself created by U; reject the broken knowledge lineage.
3. At MSFT_U event index 1 (the first U fact) delivery minus one nanosecond in the
   complete profile, supply
   internally consistent post-U event/state/source-clock metadata. Reject information
   whose delivery is still in the future.
4. Replace a fact's integer event index 1 with JSON true. Reject the type alias even
   though Python's ordinary numeric equality can consider them equal.

Retain the four intended rejection paths and unchanged original oracle. This tests the
expectation auditor, not an adapter, observer, transport or book runtime. All current
canonical source clocks are strictly increasing within each window and seed effective
time equals its raw source time, so no new real tied-source or seed-gap case is claimed.
