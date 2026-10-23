# Retained same-price replacement observation

This bounded profile connects the two independently matched QQQ inventories in
[Gate 21](validation/2026-10-23-same-price-l3/README.md) to the unchanged
[identified observer](IDENTIFIED_EVENTS.md). This is its admission and expectation
contract. Frozen expectations are a design result; runtime comparison requires a
separate evidence record. The profile grants no queue, strategy or fill eligibility.

## Fixed admission and completeness

Admit exactly one window, ID 1, QQQ locate 6556, with state IDs 1 and 2 at global
post-message boundaries 15,536,746 and 15,536,747. The seed is the complete first
independent inventory; its effective time is its original source timestamp. The
only fact is the original second frame, one complete U. Keep the six-field source
points, complete inventories, frame identities, original QQQ directory and O/S/Q
origins from the accepted retained records. Never select another occurrence.

The PRE source frame concerns another instrument. It identifies the exact global
boundary of QQQ's imported state; it is not a QQQ add fact. The source ordinals
are consecutive and the PRE frame end equals the U frame start. Consequently
the open/closed interval `(PRE, POST]` contains exactly one global frame, with no
omitted selected-locate event. The original timestamps differ by 871 ns. No
timestamp-group extension, invented seed gap, later witness or new scan is needed.
Completeness applies only to that interval, not to an enlarged history.

Authenticate fixed retained inputs against their accepted identities before use.
The Gate 21 public aggregate is 35,461 bytes, SHA-256
`698f849714ce62b2927e926df14e062b0751be72624b31820c6982271c481bfe`,
committed at `957ed8c04d49edd297ae6ba40debd1268e17bb2d`. The private canonical
receipt is 84,288 bytes, SHA-256
`da98ad6c5edb8fa63a7558e54bdc0d52470a6c9be5f3244b1ac29161f816d19f`.
Its metadata-only postcommit receipt is 133,806 bytes, SHA-256
`80c124e0ae198402940d67c09c11c5bb37896351a6e3b9fcc1ad026d7555892e`.
The original classification receipt is 93,414 bytes, SHA-256
`10cfb567ca8e1fbbcba81ebbb813065ff8313f80d975fa6b07bea7ab93c07536`.
The reference CSV/summary must be the first unchanged Gate 21 reference exports,
with the recorded complete two-state schema, boundaries and zero anomaly counters.
Retain their exact identities in the freeze and runtime records.

The canonical raw identity and 509,933,991-byte/15,536,747-message export prefix
identity are inherited from Gate 21. The prefix SHA-256 is
`47d19f447eaa60aaabc1f041c6cce28b83261358cbc0c0436052a3afb8fb9a10`.
This profile does not open or freshly authenticate raw data, execute either book,
or claim an in-parser digest. Gate 21's separate coordinator hashing passes and
its explicit timing qualification remain the source of that input evidence.

## Reuse the existing logical APIs

A new, fixed retained-input binder may construct the generic binding described
in [identified transitions](IDENTIFIED_TRANSITIONS.md). It must authenticate this
case itself. Do not call, bypass or relax the older fixed-case CLI admission,
`bind_inputs`, `authenticate_anchor`, `_canonical_profile` or `scan_prefix`.
The legacy A/D/E history and canonical four-window transition profiles keep their
existing contracts and inputs.

After that separate admission, reuse `validate_binding` and `build_window` from
`bench/identified_transitions.py`. Supply the original PRE frame as the boundary
frame and the original U as the only framed fact. `build_window` constructs the
ledger twice, requires deterministic bytes and compares both complete ranked
inventories against their independent rows. Its four generic observation profiles
are reused unchanged. No changes to the observer's event logic are required.

All 7,536 imported seed orders have attribution `{kind:"unknown",mpid:null}`.
The inventory does not expose their original attribution or birth clocks. U
inherits that unknown knowledge, removes the old order once and appends the new
total at the same level's tail as one atomic fact. Do not create a transient
deletion state, interpret removed shares as a trade, infer an MPID, label an
inherited unknown as absent in wire, or use numerical references as birth clocks.

The source identity passed to the logical module uses Gate 21's public evidence
SHA-256 and `verification:"unverified_by_module"`. Logical validation must retain
`raw_input_identity_verified:false`. The outer record reports inherited Gate 21
provenance explicitly. The directory and O/S/Q origins establish provenance;
the observer has no session/halt/auction or strategy-eligibility model. No new
status census or continuous-trading claim follows from this connection.

## Expected clocks and inventories

Write `t0` for the original PRE time and `t1=t0+871` for U. Delivery occurs at
origin plus feed delay F, at or before the inclusive horizon H. Delivery precedes
a probe at the same time. Probe times are the sorted, deduplicated union of
`t0-1`, both origin times and each origin's `origin+F-1` and `origin+F`, filtered
to `[0,H]`. The following literal outcomes are fixed before runtime:

| Profile | F in ns | H | Probe offsets from t0 | Expected event indices |
| --- | ---: | --- | --- | --- |
| zero | 0 | t1 | -1, 0, 870, 871 | null, 0, 0, 1 |
| one_ms_clipped | 1,000,000 | t1 | -1, 0, 871 | null, null, null |
| one_ms_complete | 1,000,000 | t1+1,000,000 | -1, 0, 871, 999999, 1000000, 1000870, 1000871 | null, null, null, null, 0, 0, 1 |
| undelivered_seed | 872 | t1 | -1, 0, 871 | null, null, null |

The last profile places seed delivery exactly at H+1. Its availability outcome
matches the clipped profile, but it checks a different horizon boundary. Both
retain pending indices `[0,1]` and a null latest delivered index. The other two
profiles deliver `[0,1]`, leave no pending index and finish at index 1. The complete
profile explicitly extends observation time; it admits no new source events and
performs no EOF flush. A seed delivered after U's source time still carries PRE.

An unavailable probe has null event, source, origin, delivery and orders fields.
An available probe must carry the entire independent inventory for its state,
with every order's unknown attribution. Compare the full ranked FIFO list, not
only its BBO, order count or checksum. The original old order is PRE rank 2, its
copied peer becomes POST rank 2, and the new order is POST rank 13. Both best
quotes stay unchanged. Keep actual named-order rows, quotes and frame bytes
private. Diagnostic core hashes and watched rows assist review but cannot replace
the complete runtime inventory comparison.

Expected validation counts are one fact, 7,536 seed and final orders, 15,072
source snapshot rows, one replacement and zero context events/non-head executions.
The four profiles have 17 probes, six available and eleven unavailable. Their
captured-row counts are 37,680, 15,072, 37,680 and 15,072, totalling 105,504 repeated
source/returned row instances. This reuses two existing independent states. The
historical distinct-state total remains 37.

## Frozen expectation document

The oracle root has exactly `schema_version`, `model`, `source_scope`, `inputs`,
`hand_expectations`, `expected_totals`, `windows`. Version is integer 1; model is
`same_price_retained_observer_expectations_v1`. Scope is exactly
`{raw_authentication:"retained_gate21",raw_opened:false,reference_executed:false,observer_executed:false}`.
The handwork root contains only `expected_totals` and `windows`; the freezer copies
those outcomes without deriving them. `hand_expectations` identifies that file.

`inputs` has exactly ten fixed FileRef roles: `gate21_public`, `gate21_canonical`,
`gate21_postcommit`, `reference_orders`, `reference_summary`, `classification`,
`observer_contract`, `observer_source`, `transitions_contract`, `transitions_source`.
FileRefs are exactly `{path,bytes,sha256}`; their paths are predetermined locally,
not commands or arbitrary paths to follow from an untrusted document. Empty input
files are invalid. Every consumed file is bounded, regular and checked before and
after publication. Keep the original clock handwork and machine-handwork provenance
as separately identified retained notes.

`expected_totals` is exactly `{windows:1,facts:1,source_states:2,profiles:4,probes:17,available_probes:6,captured_row_instances:105504}`.
The one window uses the unchanged window/state/fact/profile fields specified by
the [prior oracle schema](IDENTIFIED_TRANSITIONS_ORACLE.md), with state IDs `[1,2]`
and event indices 0/1. The watched-order list is the complete-inventory-order
subsequence of the copied old, peer and new references, preserving original ranks.
Core inventory hashes use full retained row order and precisely the five fields
`side,price4,fifo_rank,reference,shares`; hash ASCII JSON with sorted object keys,
compact separators and one trailing newline. Do not sort the list or include
state IDs or attribution. Fact wire fields are decoded from the original frame;
rank and visible shares ahead come from the complete independent PRE inventory.
All other fields and count meanings follow the linked schema.

JSON types are exact: reject Boolean/integer aliases, floats, non-finite values,
duplicate keys and extra/missing fields. Oracle and manifest are bounded to 8 MiB,
using sorted keys, two-space indentation, ASCII escaping and a trailing newline.
Review private sources and commit this contract before two fresh ignored freezes.
Each successful freeze has exactly five files: `oracle.json`, `freeze_manifest.json`,
`source_snapshot.py`, `hand_expectations.json`, `contract_snapshot.md`. The manifest
identifies all consumed originals and four non-manifest artefacts, clean main
source commits, accepted Gate 21 commit and false runtime/raw/observer execution
flags. Use relative artefact names, no generated time or output path in manifest
bytes, checked exclusive writes and no successful manifest after a failed write.
Two freezes at one commit must have identical oracle and manifest bytes.

The manifest has exactly twelve keys: `schema_version:1`,
`model:"same_price_observer_freeze_manifest_v1"`, `passed:true`, `source`,
`accepted_gate21_commit`, `protected_inputs`, `hand_note_provenance`, `artifacts`,
`runtime_executed:false`, `raw_opened:false`, `observer_executed:false` and
`reference_executed:false`. The accepted commit is the full Gate 21 commit above.
`source` has exactly `itch` and `engine`; each has `path`, `branch:"main"`, `commit`
and `file_sha256`, retaining the 44 feed and 15 engine implementation identities.
`protected_inputs` is the unique consumed-original FileRef list sorted by absolute
path, including those implementations, the ten input roles, freezer, handwork,
contract and four notes. Shared roles resolve to one identity in this list.
`hand_note_provenance` has exactly `original_clock_note`, `machine_provenance`,
`derivation_source` and `derivation_readme`, each its fixed FileRef. `artifacts`
has precisely the four non-manifest filenames above; each value is exactly
`{file,bytes,sha256}` with the same relative filename. The three snapshots match
their original source/handwork/contract bytes. No recursive manifest hash is stored.

A separately written auditor derives the expected body from the pinned independent
rows, summary, original U bytes and clock inequalities. It must not import the
freezer or observer, read handwork outcomes or execute project runtime. It may hash
those files as identities. Compare exact types and every expected field, including
the full core hashes, watched ranks and inherited knowledge.

After authenticating the original disk oracle, audit four separate in-memory
altered copies, keeping the original unchanged. Each must reach its intended
semantic/type guard: inherited U attribution changed to absent in wire; the new
POST watched-order rank changed from 13 to 2; the clipped profile's final probe
changed coherently to event/state 1/2 with original origin and future delivery;
and integer fact index 1 changed to Boolean true. The coherent future probe also
changes its literal expected index, so a clock-derived guard must still reject it.
These controls test the expectation auditor, not the observer.

## Subsequent runtime acceptance

Only after the reviewed freeze and independent audit pass, implement the private
fixed binder and focused admission checks. Run two deterministic retained-input
producer/verifier pairs; compare the ledger, one complete U diagnostic, both full
inventories, all probe inventories/clocks/nulls, deliveries, pending state and row
budgets with the frozen oracle. The independent verifier must not import the
producer or observer. Preserve actual-output negative controls and first failures.
Record raw authentication as inherited throughout. Do not read raw or re-execute
the reference to enlarge this case. Claims remain bounded to the one published
replacement convention; actual exchange priority, hidden liquidity, hypothetical
fills, session eligibility, every-event coverage and performance are unmeasured.
