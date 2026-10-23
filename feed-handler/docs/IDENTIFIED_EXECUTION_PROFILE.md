# A bounded identified execution profile

Status: Gate 29 design and expectation-audit draft. No implementation or runtime
acceptance is claimed. Hand expectations and their independent audit must be frozen
before this profile is implemented. The existing one-U API and its public example
remain unchanged.

The [prerequisite review](IDENTIFIED_EXECUTION_PREREQUISITES.md) fixes the earliest
retained canonical E by global ordinal. Keep QQQ's original seed and first five
selected facts, **A,D,A,A,E**. Do not rebase the seed, select a later execution or
discard a deep change to simplify the model. This profile tracks one hypothetical
passive buy marker and changes only its ahead set when named external orders change.
It deliberately infers no own fill, incoming-parent demand or actual venue priority.

## Exact retained input and separate admission

The canonical source is the previously authenticated 8,251,407,909-byte file with
SHA-256 `5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
That identity and the earlier independent reconstruction remain inherited. This gate
opens only bounded retained metadata, frames and inventories; it performs no raw-file
stat, read or checksum, project import, model run or book reconstruction.

| Fixed evidence | Required identity |
| --- | --- |
| Gate 28 public review | `validation/2026-10-23-identified-execution-prerequisites/review.json`, 16,431 bytes, SHA-256 `92734ee6a962535fc988ba56da2920f5beae0db76aa03c22f4f569e62c9b9be6` |
| Original QQQ ledger | `out/identified-history-canonical-v1/producer/window-001/ledger.json`, 56,275 bytes, SHA-256 `298b37421421f845211e800e390a80da7081078fd4370f87e72f9f6b315369e9` |
| Independent orders | `out/l3-canonical-v2/reference.orders.csv`, 434,409 bytes, SHA-256 `775f99545d84f47d7031bb8f245176ab81ccdaf8aa44d5f16f80499229c74e2b` |
| Independent summary | `out/l3-canonical-v2/reference.summary.json`, 5,878 bytes, SHA-256 `32bd1c10bfedaff5628537f24b42771a2daae1710f48c2e93f051e066c1373ee` |

A future canonical boundary must authenticate the accepted evidence and its explicit
FileRefs before interpreting them. It must bind current/historical tracked evidence,
unchanged implementation identities, original independent selected coverage, Gate 28's
catalogue/prefix/status reviews and the complete six-state inventory request. Matching
an arbitrary document's `passed` field or a supplied checksum is insufficient.

Build a detached prefix of the original ledger: preserve symbol `QQQ`, locate 6556,
source identity and complete seed; retain exactly facts 1–5 and the same first five
expected source points. Verify every retained frame's length prefix, bytes/hash,
header locate/tracking/time, wire fields, before/after order and diagnostics through
the existing identified validator. No later original D/A fact enters this profile,
even though the authenticated original ledger still contains that suffix.

| Event index / independent state | Type | Global sequence | Timestamp, ns | Framed interval, end exclusive |
| --- | --- | ---: | ---: | --- |
| 0 / 1 | Seed D | 7,343,112 | 34,201,694,396,241 | 250,772,214–250,772,235 |
| 1 / 2 | A | 7,343,264 | 34,201,694,792,271 | 250,777,858–250,777,896 |
| 2 / 3 | D | 7,346,274 | 34,201,707,006,385 | 250,890,706–250,890,727 |
| 3 / 4 | A | 7,346,293 | 34,201,707,069,166 | 250,891,449–250,891,487 |
| 4 / 5 | A | 7,349,506 | 34,201,716,865,462 | 251,007,907–251,007,945 |
| 5 / 6 | E | 7,349,884 | 34,201,718,415,103 | 251,021,615–251,021,648 |

Compare all ordered structural rows of states 1–6, not only BBO or the named target:
463, 464, 463, 464, 465 and 465 orders, respectively; 2,784 row instances in total.
Each state must match its exact source manifest, side/price/FIFO/reference/shares,
level totals and both best quotes. Seed MPID knowledge stays unknown; later A records
wire-field absence. This knowledge annotation is not an independent MPID oracle or a
claim that an imported order's original birth time is known.

### Selected closure and inherited status

The original whole-timestamp seed remains the start. The retained immediate next
global frame is strictly later, so its group is closed. There are 377 global frames
between the preceding selected A and E; adjacency is neither claimed nor required.
Complete unfiltered selected enumeration through the original later window proves no
other selected message at E's timestamp. That establishes selected-book closure.

For this finite selected-book scheduler, selected closure plus the inherited relevant
global-status proof is sufficient. Foreign orders cannot change this selected book;
the relevant system/status histories are fixed by the explicit census join below.
Do not manufacture an exact last global frame at E's clock or rename a later full-window
witness as E's first-greater witness. This is a declared restricted model boundary,
not general global timestamp closure or permission to execute after E.

Bind Gate 9 and Gate 25 to the same retained canonical identity. Gate 25's complete
through-endpoint census has exactly one selected QQQ R/H/Q, with origins
6,571/21,992/7,203,970 before the original seed: production QQQ/6556, H=T and cross O.
Global S contains the original O/S/Q only; W/h/N and selected K are zero through that
later endpoint. These counts and actual origins support the limited earlier facts.
Absent h/N remains null/unknown. This is offline admission evidence, not later
information delivered to a strategy. It supplies neither MSFT status nor the later
one-U interval census, adjacency, 211 ns witness or queue-admission result. No actual
venue-access, regulatory, routing or order-acceptance certification follows.

## Future pure interface and profile restrictions

The proposed separate API is
`simulate_execution_prefix(ledger, config, expected_sources=None)`. It may reuse the
existing identified ledger validator; it must not encode E as an anonymous Trade or
route this prefix through `simulate_one_u`. Its proposed module is
`bench/identified_execution_queue.py`; the expectation freeze must prove that path is
absent. The 61 existing implementation files remain unchanged. This gate writes no
implementation.

Configuration has exactly `quantity`, `decision_ns`, `cancel_ns`, `horizon_ns`,
`feed_delay_ns`, `order_delay_ns` and `response_delay_ns`. Quantity is exact integer
one; Boolean integers are invalid. Times/delays are exact non-negative uint64 values,
except cancellation may be null. The seed's effective time equals its source time;
all five source times are strictly increasing after it. Require exactly A,D,A,A,E,
five facts and six validated snapshots. Global source ordinals/bytes increase without
overlap; gaps are allowed because coverage is selected-locate, not global adjacency.

The selected buy price is the unchanged best bid throughout all six snapshots. Both
best prices must remain fixed, populated and strictly uncrossed. The named E concerns
that bid; missing/changed/crossed quotes or a different execution side/price refuse.
The decision lies within seed-to-E and optional cancellation within decision-to-E.
The inclusive horizon is exactly E's source time. All additions for actually scheduled
feed, arrival and response events must fit uint64, including events left pending.

The pure result authenticates no source/status by itself: `raw_input_identity_verified`,
`status_admission_verified` and `source_coverage_authenticated` remain false. A separately
reviewed fixed boundary must admit the canonical data before calling it. It must not
reuse the old one-U admission flag as this profile's admission.

## Named external changes and our separate marker

Never insert our marker into historical reference space or change any historical
shares because of its submission/cancellation. A source event applies one complete
atomic fact. Historical snapshots are immutable complete inventories from validation.

- A appends its named external order according to reconstructed FIFO. If a marker is
  already live at that bid, a new same-price add is behind it, not newly ahead.
- D removes only its named order. Remove that reference from the ahead set if present.
- E reduces only its named remaining shares. An ahead reference keeps its place while
  shares remain; remove it on full depletion. Unaffected references retain order and
  quantity. Never redistribute named executed shares across earlier references.

Acceptance puts all current external references at the selected price ahead. An own
cancellation clears only the marker/ahead set. Our exchange remainder stays one from
acceptance until own cancellation; external E never creates an own fill in this
conservative convention. Both exchange/local accounts (`filled`, `position`, `cash4`,
`fees4`) stay zero. E is a real external execution, so these own zeros are a declared
model choice, not a consequence of an interval without executions or empirical proof.

Equal-time phases are selected source, captured feed, strategy, request arrival and
own response. Each phase preserves scheduling/source order. Source/feed labels are
`source_seed`/`feed_seed` at index 0; later labels are `source_A`, `source_D`,
`source_E`, `feed_A`, `feed_D` and `feed_E` at indices 1–5.
The index distinguishes repeated A labels. All source events at a clock precede feed
and own actions there. A zero-delay child uses a later phase than its parent.

A decision uses only the most recently delivered complete captured payload; its
inventory digest hashes the same orders the decision reads. No delivery means skip.
Submission records local pending/requested one immediately; confirmed remainder is
null until an own response. Historical feed never acknowledges our request. Cancel
only when locally live with a delivered observation; otherwise record a skip.
Cancel request, exchange cancellation and local cancellation confirmation remain
separate. Requested quantity stays one after submission, even after cancellation;
it is zero when no submission occurred. No event beyond E is applied, and no
EOF/pending flush is permitted.

## Finite schedules before implementation

Let S=34,201,694,396,241, H=34,201,718,415,103 and
L=H−S=24,018,862 ns. F/O/R mean hypothetical feed/order/response delays, not estimated
latencies. All cases use quantity one and horizon H.

| Frozen case name | Decision | F/O/R | Cancellation |
| --- | --- | --- | --- |
| `before-all` | S+1 | 0/0/0 | null |
| `at-E` | S+1 | 0/(L−1)/0 | null |
| `no-feed` | S+1 | (L+1)/0/0 | null |
| `arrival-pending` | S+1 | 0/L/0 | null |
| `ack-pending` | S+1 | 0/0/L | null |
| `cancelled` | S+1 | 0/0/0 | S+2 |
| `delayed-seed` | H | L/0/0 | null |

The last case deliberately delivers the captured original seed at H after source E
has applied. Its observed event index/digest must still identify PRE; acceptance uses
current external POST. Later feeds remain pending. Complete payload identity is needed
because a quote alone cannot establish which inventory reached the strategy.

## Closed hand expectations and refused inputs

The private hand table `execution_prefix_hand_expectations.json` is 39,879 bytes,
SHA-256 `82fa006a4eba2e4d15fadd659883c9a94bf3e3438393dad91e70597328910059`.
It is design evidence, not a runtime result. Its independent expectation audit is
pending; no audit pass is claimed here. Freeze its literal data without importing a
future model or deriving queue outcomes from model output.

Every object below has exactly the stated keys. `schema_version` is exact int1;
Boolean integers, duplicate JSON keys and non-finite numbers are invalid. Root keys
are `schema_version,model,scope,inputs,phase_order,window,cases,expected_totals,limitations`.
The model is `identified_execution_prefix_hand_expectations_v1`. `phase_order` is
`{source:1,feed:2,strategy:3,arrival:4,response:5}`. Scope keys are `design_only`,
`model_imported_or_executed`, `raw_statted_read_or_hashed`, `reference_or_book_replayed`,
`new_historical_states`, `empirical_fill_claim`: true, false, false, false, 0, false.

`inputs` has exactly `prefix_review,ledger,validation,prerequisites_public,reference_orders,`
`reference_summary,prior_trace_contract,prior_frozen_schema`; each is a FileRef with
`path,bytes,sha256`. These pin the retained sources and old hand-schema provenance;
no later actual queue result is an expectation input.

`window` has `symbol,locate,seed_ns,end_ns,duration_ns,seed_source,retained_state_ids,`
`facts,inventory_states`. The six retained state IDs are 1–6. Every fact entry has
`event_index,source,frame_sha256,kind`; SourcePoint has the existing exact six fields
`sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type`. Each inventory
entry has `event_index,state_id,origin_ns,orders,inventory_sha256,level_shares,`
`bid_price4,ask_price4,ask_shares`; `orders` is the complete order count, not a row list.
Its digest is SHA-256 of the complete ordered logical orders, including attribution,
using compact sorted-key ASCII JSON, `ensure_ascii=true`, `allow_nan=false` and one
final newline. The independent CSV and original frames supply those full inventories
and the explicit unknown/absent knowledge rules, not merely BBO totals.

Every case has `name,config,trace,pending,final`, in the seven-name order above.
Trace and pending rows have exactly `time_ns,phase,event,origin_ns,event_index`.
Source/feed origins are original source times; strategy origins are the decision or
cancel-request time; arrival origins are their request times; response origins are
their exchange-arrival times. Own event indices are null. Own trace labels are
`submit,decision_skip,cancel_request,cancel_skip,arrival_accept,cancel_accept,`
`response_accept,response_cancel`; pending incoming requests use `arrival` and
`cancel_arrival`. Source/feed labels retain the typed labels and indices defined above.

`final` has exactly `external,own,observed`:

- `external`: `event_index,origin_ns,state_id,inventory_sha256,complete_order_count,`
  `level_price4,level_shares`.
- `observed`: `event_index,origin_ns,delivery_ns,inventory_sha256`. All four are null
  before any delivery; they describe the captured delivered payload, not current history.
- `own`: `limit_price4,ahead_references,ahead_quantities,ahead_shares,exchange_state,`
  `exchange_remaining,accepted_quantity,cancelled_quantity,local_state,`
  `local_request_quantity,local_confirmed_remaining,submitted,cancel_requested,`
  `exchange_account,local_account`. `ahead_quantities` is an ordered list of
  `{reference,shares}`. Each account has exactly `filled,position,cash4,fees4`, all zero.

A future implementation may retain the existing flat final-state style. Its verifier
must use this explicit projection, rather than introduce competing expectation names:

| Hand field group | Projection from an actual result |
| --- | --- |
| `external.event_index` | Final `historical_event_index` |
| Remaining `external` fields | The actual complete historical snapshot at that index; bind its source to the authenticated independent state ID and rows, compute its logical inventory digest/count and target-level price/quantity |
| `observed` | Final `observed_event_index,observed_origin_ns,observed_delivery_ns,observed_inventory_sha256` |
| `own` | Same-named flat fields; derive `ahead_quantities` from actual ordered `ahead_references` and their shares in the actual historical snapshot |
| Trace/pending | Exact five-field envelopes; additional runtime state diagnostics cannot substitute for these fields or the complete final checks |

Future acceptance must compare all six complete historical inventories, not trust a
supplied digest alone, then every envelope, pending row and projected final field.
The model's delivered digest must describe the same captured object read by strategy.
The independent auditor must check these hand expectations before implementation;
any additional runtime fixtures must also be frozen before their first model run.

`expected_totals` has exactly `cases,trace_events,pending_events,source_snapshots_per_case,`
`cases_with_pending,retained_source_states,new_historical_states`: 7, 92, 13, 6, 4, 6, 0.
These are expected fixture counts, not executed checks or additional historical states.
Detailed inventories, source frames and private hand tables stay ignored; publish only
bounded aggregate evidence.

Refusal descriptors must be fixed before implementation, with coherent changed input
materialisation before any new model code is written in Gate 30. The fixed private
`execution_prefix_refusals.json` is 2,705 bytes, SHA-256
`cee7839422ecbd9ad61e73ee2f7bacf2a206ab523da9302234938ae4f31e1bf3`:
sixteen descriptors, comprising eight configuration, seven profile and one clock case.
It contains descriptions, not materialised invalid ledgers or executed refusal results.
The exact changed inputs require source review before implementation, with otherwise
valid alternative ledgers isolating their intended predicate. Stable error families are:

- `config:` unknown/missing keys; quantity other than exact int1; Boolean, non-integer,
  negative or out-of-uint64 clocks/delays; decision/cancel outside their intervals.
- `profile:` invalid identified ledger or independent expected-source mismatch; wrong
  fact count/type sequence; seed-effective mismatch; non-increasing source times;
  wrong horizon; invalid fixed quotes or wrong named E side/price. The fixed canonical
  boundary also refuses changed frame/inventory identities, omitted selected changes,
  fabricated global boundaries, unsupported status or unknown rewritten as normal.
- `clock:` uint64 overflow in a scheduled delivery, arrival or own response. Do not
  manufacture a request merely to overflow a branch that was never scheduled.

Basic configuration fields/types are checked before the ledger/profile; decision and
cancel interval checks follow a validated profile; derived clock checks occur when an
event is actually scheduled. Canonical metadata admission precedes any model call.

At most six complete source snapshots/five facts, 32 trace rows and 32 pending events
are permitted. Existing identified-validator row/domain limits and the 32 MiB result
bound remain in force. A failure returns no partially accepted result. No current
module, old fixture or historical profile may be changed to accommodate this design.
