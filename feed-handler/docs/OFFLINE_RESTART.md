# Bounded offline restart profile v1

This is the Gate 12 design contract. It precedes restart implementation and execution.
Gate 13 must implement and verify the contract against independently frozen plans;
the existence of this document is not a runtime recovery result.

## Purpose and scope

After a gap, wrong occurrence or callback failure, the earlier receiver/consumer stays
invalid. An explicit application restart may discard that mutable consumer and replay
the same bounded projection from its original authenticated seed. There are at most
two generation attempts, with no reset, suffix continuation or automatic retry. This
checks recomputation and the conditions for promoting a completed result.

Use the two accepted QQQ/MSFT windows and separately labelled synthetic D/A/D control
from [Gate 11](CANONICAL_TRANSPORT.md). Keep its selected-locate projection, original
source points, imported seed, artificial session/initial sequence and fixed layout.
No new historical states, captured packets or timing observations are introduced.
Do not connect this experiment to the queue/fill kernel or treat replayed events as
new observations delivered to a strategy.

The pinned primary source is Nasdaq's [MoldUDP64 specification](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/moldudp64.pdf),
86,837 bytes, SHA-256 `96cdd02b8728a441cb970d1371a96e73c01e1edaffb2891d43667e2a0ad8add5`.
Its request/unicast-response mechanism, partial responses and terminated-session
availability are outside this profile. Page 6 discusses configuring a restarted
client's expected session and sequence. Here the new receiver uses a fixed original
synthetic session/sequence, not a newly observed Nasdaq session. Replaying local files
does not implement protocol retransmission, network recovery or venue availability.

## Accepted inputs and authenticity

Pin Gate 11's aggregate at evidence commit
`5ada51a59911cbff665f97165566f8ebb05547ba`:
`docs/validation/2026-10-22-canonical-transport/verification.json`, 19,053 bytes, SHA-256
`d3055c07edf93bff5fb29d8014d9d159d9f77cb5a5ec00a8f1f5a776e81e5ea7`.
Check both its accepted historical Git blob and the current tracked blob. Its producer
source commit is `88ff5d76daafb70726f7fb442b4954f2ff38cb98`; do not confuse the two.

The accepted original bundle is retained under `out/canonical-transport-canonical-v1/`.
Its 24,064-byte manifest has SHA-256
`b736130dd04013ee8811efe575856503d169b56495e8b94b0bd7e20fea19ae08`.
Authenticate every consumed CSV against its recorded identity. The fourteen CSVs are
also byte-equal to the independently frozen Gate 11 bundle. Keep the Gate 9 retained
ledger/producer and Gate 7 reference identities and source joins bound through that
manifest and their accepted aggregate blobs. Freshly hash the small files actually
consumed before/after; detect changed bytes, path/inode aliases and unstable input.
Fixed filenames and numbered directories cannot be supplied by market-data rows.

The independent Gate 11 fixture manifest has 6,169 bytes and SHA-256
`cf6da1ee6558fac63b109101c8f71e5612c687f74c1f1d746e713c52b8bd867b`.
Expected inventories still come from its authenticated old external export, not the
restart implementation. Preserve that manifest and all original fixture bytes.
New plans can refer to these immutable source/state IDs; no new-producer or replay
imports may be used to derive expected outcomes. The synthetic D/A/D control is local
L3 mutation coverage, not evidence that reference reuse is valid Nasdaq history.

The raw day and independent implementation are not reopened or rerun. Set
`raw_full_identity_freshly_verified: false` and `independent_reference_replayed: false`.
C++ compares exact message bytes and declared digest strings; Python freshly hashes
the retained files. No C++ SHA recomputation claim follows.

## Generation ownership and identities

One case fixes one window, one layout and the complete pristine packet list. A generation
attempt reserves ordinal 1 or 2 before per-generation admission, construction or seed
import. Admission or construction failure consumes that ordinal, so failed starts
cannot evade the bound. A global untrusted-corpus failure refuses the experiment before
any case; it cannot be converted into a recoverable scenario.

Every admitted generation exclusively owns a new `Receiver`, new `L3Book`, occurrence
cursor/seen set, attempt/callback counters and validity latch. Import the original
independent seed in its original price/FIFO order, with attribution still unknown.
The receiver begins at the original configured session and initial-next, with zero
attempts. Never seed from a failed book, its last sequence, an intermediate checkpoint,
a callback counter or a final BBO match. No reset is added to `Receiver` or `L3Book`.
Keep the orchestration synchronous and small; no generic recovery framework is required.

After saving bounded immutable diagnostics, destroy the failed mutable consumer before
allocating its successor. No receiver, book, order pointer, span, cursor or callback
closure from generation 1 may mutate generation 2. Input bytes may be shared read-only;
each synchronous receive call retains its immutable datagram storage for all callbacks.
Object-lifetime/source checks must supplement state equality: identical output alone
cannot prove that a new object was constructed or that mutable aliases were discarded.
Count construction/destruction epochs by generation and lexical lifetime; a conforming
allocator may reuse the same address, so differing raw addresses are not required.

Original `(window_id, event_index, SourcePoint)` and transmitted
`(window_id, layout, packet_index, packet_message_index)` identities remain unchanged
across generations. Add local provenance `(case_id, input_manifest_sha256, seed_sha256,
window_id, layout, generation_ordinal)`. These are deterministic computation labels
within the experiment, not authentication credentials or exchange/receipt times.
A generation ordinal is not part of an original source identity or Mold sequence.
`seed_sha256` is SHA-256 of the complete authenticated `seed.csv` bytes, including its
header and LF endings. For canonical cases `input_manifest_sha256` is the original
24,064-byte accepted bundle manifest's SHA above; for the separately synthetic case it
is the 6,169-byte frozen Gate 11 fixture manifest's SHA above, which binds its own
synthetic seed/bundle files. Do not invent a different JSON or order serialisation for
either digest. Case IDs are frozen ASCII identifiers, unique within the experiment.

No live objects escape a generation. A narrow implementation may use a one-shot
`replay_generation(authenticated_projection, frozen_arrivals, ordinal)` and return
immutable diagnostics plus a tagged candidate. The case supervisor stores at most
two outcomes and at most one promoted final candidate. The concrete code interface
must be frozen and independently reviewed before its implementation is executed.

## Invalidation and explicit restart

All callback states are provisional. Separate a consistent diagnostic prefix from a
fully completed, promotable result. First invalidation can arise at admission, outer
binding, transport, consumer or completion. Preserve the layer and first reason; later
input stays blocked without changing it. Binding failure may leave the receiver ready;
restartability depends on invalid consumer/generation status, not only `State::failed`.
Retain receiver state/fault/next/attempts as diagnostics without relabelling outer errors
as Mold faults. EOF is an application completion boundary, never a fabricated packet.
If admission refuses construction, receiver diagnostics and applied/returned event
indices are absent/null, not invented ready/zero values. A successfully imported seed
has event index zero but contributes no transport callback. Constructor/import refusal
has its own admission/consumer reason even when no runtime receiver result is available.

An ordinary handler may mutate the book before it throws. Record `last_applied_event`
separately from `last_returned_event`, the attempted/returned counts for that call and
the receiver's committed next. After a batched callback failure those values can differ.
The failed receiver's next is not a safe consumer checkpoint. Check the resulting
partial inventory as diagnostic evidence, revoke the entire consumer and discard it.
Do not roll it back, continue it or count the failing callback as returned.

Restart is an explicit case action after invalidation, never a response inferred from
late data. Generation 2 must be admitted against the same trusted original seed,
configuration and stored complete packet corpus. Recheck actual consumed small inputs;
failure or absence of any required packet/proof refuses the new consumer before any
Receiver/L3Book construction or seed import.
An explicitly modelled unavailable packet is a private test condition, not observed
local/Nasdaq retransmission availability. Do not reconstruct it from facts, renumber
later packets, import a different seed or promote a checkpoint to conceal its absence.
Modelled refusal changes a copied declaration or availability mask after authenticating
the unchanged original corpus. Actual on-disk identity instability is a global integrity
failure and aborts verification; it is not a scenario that can be certified by restart.

Successful generation 1 forbids a restart; successful generation 2 cannot be restarted.
After invalid generation 2 or refused second admission the case is terminal. A third
start request is denied before file I/O, construction or callbacks and cannot replace
either earlier diagnosis. Denied control requests do not allocate a generation or
reset its attempt budget. Late packets offered to an old invalid generation remain
blocked even if a new generation subsequently succeeds.
Once an old consumer is destroyed, these late-input probes are supervisor-level
blocked diagnostics using saved immutable metadata. They must not invoke a destroyed
or retained old receiver, closure, order pointer or span.

## Completion and promotion

Promotion requires all of the following, not merely `Receiver::ended`:

- The current admitted generation has no binding, transport, consumer, anomaly or
  completion failure, and every planned supplied arrival has been consumed.
- Every expected original fact occurs exactly once in source order, through its exact
  frozen packet/message slot and body. Exactly-once applies within a generation;
  repeating those same sources in a later fresh generation is expected recomputation.
- The imported seed and every applied/returned state agree with the independently
  frozen complete inventory/BBO, including intermediate states within batches. The
  final full inventory also matches its original independent state.
- A matching transport end is accepted after full fact coverage. Optional matching
  repeated end has the Gate 11 semantics. File exhaustion alone is incomplete.
- The candidate's case/input/seed/window/layout/ordinal token matches the current valid
  generation, and that case has not already promoted a candidate.

A valid end at the current sequence before expected facts is an immediate application
`incomplete_coverage` failure even if Mold enters `ended`; later data is blocked at the
supervisor, preserving `ended` rather than creating a later `post_end` diagnosis.
An exhausted arrival list
with all facts but no accepted end is `incomplete_end`, even if the book matches.
Subsequent data cannot heal either completed invalid generation. Wrong/stale tokens
or a second promotion request are denied without replacing or invalidating an already
healthy promoted candidate. No output from an invalid generation becomes valid merely
because its book equals the new generation's book.

An oracle/checker mismatch is a harness failure and aborts verification. It must never
be swallowed as an expected handler failure, accepted restart trigger or successful
fault outcome. Private injected callback failure needs its own unambiguous marker;
checker exceptions retain an independent failure latch outside receiver callbacks.

## Frozen scenario matrix

Freeze these twelve cases before new restart implementation execution. Packet IDs refer
to the unchanged Gate 11 bundle; arrival order is separate. Exact per-arrival outcomes
and inventory/state references must be serialised independently, not inferred from a
new implementation's trace. Canonical faults use authentic stored packets or declared
private mutations of arrival copies after corpus authentication. No public bypass mode
is added. Each case preserves its original scope, with the tiny case separately synthetic.

| Case | First generation | Explicit second action | Required final result |
| --- | --- | --- | --- |
| Clean QQQ batched | Complete original list | Restart request denied as already valid | Promote generation 1 once |
| QQQ deep loss | Existing deep-gap plan, with late missing packet blocked | Full original single list | Promote generation 2; first failure remains recorded |
| QQQ wrong source | Existing source-point mutation and blocked continuation | Full original single list | Binding failure remains diagnostic; generation 2 valid |
| QQQ duplicate | Existing stale-arrival plan | Full original single list | New receiver begins at original next and succeeds |
| MSFT partial apply | Batched first add applied, then intentional throw before return | Full original batched list | Discard partial book; reimport original seed; generation 2 valid |
| Synthetic tied alias | Existing identical-body wrong-occurrence plan | Full original single list | Explicit original identities preserved; generation 2 valid |
| Rejected seed | Synthetic alias failure | Changed seed declaration refused before consumer construction | Two reserved attempts, one constructed generation, no promotion |
| Replay unavailable | QQQ deep-gap failure | Required original packet privately declared unavailable at admission | No second consumer, no fabrication, no promotion |
| Second generation stale | QQQ deep-gap failure | Generation 2 receives heartbeat, fact 1, duplicate fact 1, blocked fact 2 | Terminal failure; third/repeated start denied |
| Missing end | QQQ single heartbeat, all facts and final heartbeat, then EOF | Full original single list | First receiver ready but generation incomplete; generation 2 valid |
| Early end | QQQ initial heartbeat then end-copy advertising initial next, then blocked fact 1 | Full original single list | First receiver ended but incomplete coverage; generation 2 valid |
| QQQ reordered | Existing reorder plan | Full original single list | Original future packet causes gap; generation 2 valid |

Add lifecycle probes to successful restart cases: a generation-1 candidate/token after
generation-2 success is rejected, the healthy candidate remains unchanged, and a second
promotion is denied. The clean case also rejects wrong case/input/seed/window/layout
tokens. These are bounded synchronous checks, not concurrent or asynchronous delivery.

The partial MSFT control must record the first add's independent post-state while
`handler_attempted=1`, `handler_returned=0` and committed next remains initial-next.
Its original seed is checked again before the second generation's first handler.
The deep QQQ omission changes the correct inventory from 465 to 464 at that source
boundary while BBO is unchanged. A later source packet must expose the gap before a
handler. Neither fact can be replaced by final-inventory/BBO agreement alone.

## Bounds and acceptance evidence

At most 16 cases, two reserved attempts and two constructed generations per case,
64 supplied arrivals per generation, 128 per case and eight lifecycle/token/control
probes per case. Failed-start denials are included in that finite control plan.
Keep Gate 11's two windows, 16 facts/window, 4,096 live/seed orders and existing Mold
packet/body bounds. No packet cache or reorder buffer is added. Bound all compared
row instances across both generations at 1,000,000 per case, including diagnostics;
source/oracle CSVs remain at 100,000 rows combined, 8 MiB/file and bounded regular,
non-blocking stable reads. JSON and aggregate output have explicit actual-byte bounds.
Retain at most one mutable consumer at a time; discard it before constructing another.

Record unavailable/admission/constructed/invalid/complete/promoted outcomes separately,
reserved attempts versus created generations, original and generation identities,
first failure, all provisional states, applied versus returned callbacks and promotion
denials. Per-event records stay ignored. Version only aggregate evidence and identity
manifests; split canonical and wholly synthetic counts and distinguish unique old
historical states from repeated per-generation comparisons.

Gate 12 acceptance is the reviewed contract plus independently frozen source/state,
arrival and lifecycle oracles. Gate 13 runtime acceptance additionally requires all
expected outcomes and intermediate inventories, object-lifetime/ownership review,
meaningful failed-state-reuse or identity/promotion negative controls, repeated exact
summaries and focused Release/ASan/UBSan checks. Source/runtime/input/binary identities
must stay stable. Allocation-exhaustion injection remains unverified unless actually
performed; constructor/pre-import admission refusal is not a claim of allocator testing.
No performance, live recovery, receipt time, hidden priority, order eligibility, fills
or strategy result follows from either gate.
