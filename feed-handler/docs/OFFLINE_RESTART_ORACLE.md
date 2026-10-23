# Offline restart oracle schema v1

This machine-readable expectation schema accompanies the independently reviewed
[restart policy](OFFLINE_RESTART.md), SHA-256
`29b57fb1f0070c3f7f6c6b01b4418474898c240418252a4e0b0ad1e99e338673`.
It specifies a frozen oracle for future Gate 13 checks, not a restart execution result.
All `expected` objects and lifecycle flags are obligations to test later.

## Common representation and boundaries

Use UTF-8 JSON, exact closed object key sets, canonical decimal integer values, no
duplicate keys or non-finite/floating values, and actual serialised size at most 8 MiB.
Canonical encoding is sorted keys, separators `,`/`:`, ASCII escapes and one final LF.
Integers must be exact integers rather than booleans. Lists have the policy bounds;
all unknown/missing fields, enum values or out-of-range numbers are rejected.

`FileRef = {path,bytes,sha256}` uses a fixed repository-relative POSIX path, positive
byte count and lowercase 64-character SHA-256. Do not accept absolute or `..` paths.
Roles have fixed allowed filenames: anchor paths are the policy's accepted documents,
manifests/reference CSVs plus these two new documents. Oracle window/layout file refs
point only to their fixed Gate 11 frozen fixture paths. A row cannot choose a new file.
Rehash the references against the accepted old manifests before/after serialisation.
Do not copy mutable new implementation output into expectations.

`StateRef = {window_ref,event_index,state_id}` identifies the original retained state;
`window_ref` is `qqq`, `msft` or `synthetic`. Event zero is imported seed, never a
transport callback. State IDs are inherited unchanged from the selected oracle scope.
Each state reference resolves to the complete independently frozen ordered inventory
and BBO. Cross-generation references deliberately reuse the same old state IDs.

`TokenContext = {case_id,input_manifest_sha256,seed_sha256,window_id,layout}`.
`Token = TokenContext + {generation_ordinal}`. Digests use the policy's exact complete
file bytes. `layout` is `single` or `batched`; ordinal is 1 or 2. Case IDs are frozen
unique ASCII identifiers. A token is local provenance, not an authentication credential.

`ReceiverDiagnostic = {state,fault,next_sequence,receive_attempts}` uses actual Mold enum
strings (`ready`, `ended`, `failed`; fault includes `none`) and bounded unsigned values.
`Failure = {layer,reason}` has layer `admission`, `binding`, `transport`, `consumer` or
`completion`. Reasons in this matrix are `seed_mismatch`, `unavailable_packet`,
`binding_mismatch`, `gap`, `stale_data`, `injected_handler_failure`,
`incomplete_coverage` and `incomplete_end`. Checker failure is never an expected outcome.

An invalid generation's later arrivals are supervisor-blocked before a new receiver
call, regardless of its underlying receiver state. Keep the stored receiver diagnostics
and first failure unchanged. This is stricter caller accounting than the unchanged
receiver's own blocked-call API; no new Mold result is fabricated for an unmade call.

The eight control-probe bound excludes the two separately bounded initial/admitted
restart attempts, which live in `attempts`. It includes denied extra start requests,
promotion and late-token/input probes. No array can hide unbounded failed starts.

## Top-level and source roles

The exact root keys are:

```text
schema_version,model,phase,runtime_executed,limits,anchors,oracle_refs,cases
```

Values are version 1, model `offline_restart_oracle_v1`, phase
`contract_and_frozen_oracle_only`, and `runtime_executed: false`.
`anchors` contains FileRefs with exact keys `gate11_evidence`, `original_bundle_manifest`,
`gate11_fixture_manifest`, `gate9_evidence`, `gate7_evidence`, `independent_orders`,
`independent_checkpoints`, `independent_summary`, `restart_policy`, `oracle_schema`.

`limits` has exact keys and ceilings:

```text
max_cases=16
max_reserved_attempts=2
max_constructed_generations=2
max_arrivals_per_generation=64
max_arrivals_per_case=128
max_control_probes=8
max_facts_per_window=16
max_orders_per_window=4096
max_compared_row_instances_per_case=1000000
max_json_bytes=8388608
max_csv_bytes=8388608
max_combined_reference_rows=100000
```

`oracle_refs` has exact keys `qqq`, `msft`, `synthetic`. Each value has:

```text
scope,window_id,fact_count,state_ids,window_csv,seed_csv,sources_csv,
states_csv,orders_csv,layouts
```

Scopes are `canonical_selected_projection_v1` or `synthetic_occurrence_control_v1`.
The five CSV role values are FileRefs. `state_ids` lists seed then each post-state;
`layouts` has exact `single` and `batched` values, each
`{packets_csv,occurrences_csv}` with FileRefs. Canonical window IDs are 1/2; the synthetic
window is separately scoped ID 1. Canonical fact counts are 7/6 and synthetic count 3.
The fixed filenames themselves remain unchanged from Gate 11.

## Case and admission

`cases` contains exactly the twelve policy matrix cases, in that table's order. Each
case has exact keys:

```text
case_id,scope,window_ref,layout,token_context,attempts,controls,expected_final
```

An attempt has exact keys:

```text
ordinal,request_kind,admission_mutation,unavailable_packet_ids,
expected_admission,arrivals,eof,expected_outcome
```

`request_kind` is `initial` or `restart`. `admission_mutation` is `none`,
`seed_mismatch` or `unavailable_packet`. The unavailable list is empty except for its
explicit refusal control; no actual trusted source file is deleted. Attempt 2 exists
only after an invalid first outcome. Reserved ordinals are consecutive from 1.

`expected_admission` has exact keys:

```text
reserved_attempts,constructed_generations,admitted,reason,receiver,seed_state_ref
```

Counts are cumulative across the case. Admitted attempts use reason null, a fresh ready
receiver with no fault/zero receive attempts/original initial-next, and original seed
StateRef. Refused attempts use a policy refusal reason, receiver/seed ref null, no
arrivals, `eof: null` and no new objects. Reserving attempt 2 still consumes its ordinal.
Constructed generation means both fresh receiver and book were created; this matrix's
admission refusals happen before either construction. It does not test allocation failure.

## Arrival expectations

An arrival has exact keys `{arrival_index,packet_index,mutation,expected}`. Arrival
indices are consecutive from zero within that generation; packet IDs retain their
original immutable meaning. `mutation` is `none`, `source_point`, `occurrence_alias`,
`after_apply_throw` or `early_end_initial_sequence`. Private mutations operate only on
arrival copies after the original corpus is authenticated. The throw applies after the
first valid MSFT A mutation and before its callback returns. Early end changes only the
copied end marker's sequence to original initial-next.

The exact expected keys are:

```text
layer,disposition,mold_called,mold_disposition,first_failure,receiver,
handler_attempted,handler_returned,applied_event_indices,returned_event_indices,
last_applied_event,last_returned_event,state_checks,diagnostic_state_ref,
generation_status,promotable
```

`layer` is `mold`, `binding`, `consumer`, `completion` or `supervisor`; `disposition`
uses normal Mold strings, plus outer `rejected`/`blocked`. If `mold_called` is false,
`mold_disposition` is null. Otherwise it is the actual Mold disposition; early end is
Mold `end` with application `completion/rejected`. `first_failure` is Failure or null.
`receiver` is the exact stored ReceiverDiagnostic even on a supervisor-blocked row.

Handler counts and applied/returned event lists are per-call; last-event indices are
cumulative, starting at zero after seed import. Applied and returned lists must refer
to the exact original occurrences, not body lookups. `state_checks` is a list of StateRef
plus `{phase}`, where phase is `applied` or `partial_after_apply`. A normal successful
handler is in both lists. The injected failing handler appears only in applied, with
its independent post-state tagged partial. `diagnostic_state_ref` is the current full
book boundary even for a revoked partial state; it is not a restart checkpoint.

`generation_status` is `active` or `invalid`. Every arrival has `promotable: false`:
successful end cannot promote before the complete supplied list has been checked.
Later invalid arrivals are supervisor-blocked with empty event lists, zero handler
counts and unchanged diagnostics. No old receiver/closure/pointer is invoked.

## EOF, candidate and immutable outcome

For admitted attempts `eof = {expected}`, with exact expected keys:

```text
first_failure,status,receiver,last_applied_event,last_returned_event,
diagnostic_state_ref,promotable,candidate
```

Status is `complete` or `invalid`. Missing end invalidates at EOF without a receiver
call; early coverage failure was already latched at the end arrival. A previous failure
stays first. `promotable` is true only for complete coverage, successful end and no
failure. That produces a Candidate; otherwise candidate is null.

`Candidate = {token,final_state_ref,applied_event_indices,returned_event_indices,accepted_end}`.
The lists are each exactly `[1,...,fact_count]`; accepted_end is true. No failed
generation has a candidate. The supervisor promotes only a complete current candidate.

`expected_outcome` has exact keys:

```text
status,first_failure,receiver,applied_event_indices,returned_event_indices,
diagnostic_state_ref,candidate,mutable_objects_discarded
```

Status is `complete`, `invalid` or `refused`. Refusal has its admission Failure and all
receiver/event/state/candidate values null. Other outcomes retain exact EOF diagnostics.
`mutable_objects_discarded: true` is an expected lifetime obligation, not a Gate 12
runtime result; a later implementation must establish it before returning immutable
values. Address reuse is permitted, mutable alias reuse is not.

## Control probes and case outcome

Each control has exact keys:

```text
control_index,after_attempt,action,token_source,token_mutation,
payload_state_ref,packet_index,expected
```

Indices are consecutive from zero. `after_attempt` is 1 or 2. Action is `restart_request`,
`promote` or `late_packet`; token source is `current`, `generation1` or
`current_with_mutation`. Mutation is `none`, `case_id`, `input_manifest_sha256`,
`seed_sha256`, `window_id` or `layout`. Non-applicable payload/packet fields are null.
A stale-token probe may relabel the current valid final payload with ordinal 1: it
does not invent a legitimate completed candidate from invalid generation 1.

The exact expected keys are:

```text
verdict,reason,reserved_attempts,constructed_generations,current_generation,
promoted_generation,promoted_state_ref,prior_failures_preserved,
receiver_called,objects_constructed
```

Verdict is `accepted`, `denied` or `blocked`. Reasons are `promoted`, `token_mismatch`,
`already_promoted`, `already_valid`, `generation_invalid` or `generation_limit`.
`current_generation` means the most recent admitted outcome of the current attempt,
not a live object; it is null after a refused current attempt. Promoted fields are null
until valid promotion. These probes all have receiver_called false, objects_constructed
zero and prior_failures_preserved true. Token equality is checked before a promotion's
already-promoted guard; a matched current token cannot promote twice. Late-invalid
generation input is blocked using its stored outcome without entering any old receiver.

The clean case has eight probes: promote once; five mutated-token promotion attempts;
restart denied as already valid; matched second promotion denied. Successful restart
controls promote current once, reject the same valid payload relabelled with a
generation-1 token, block a late old-generation packet and deny duplicate promotion.
The failed constructed second generation in the stale case has two denied extra
starts, neither reserving attempt 3. Refused seed/unavailable second admissions have
no additional probes and preserve their admission-refusal terminal reason. Planned
control count is 42: eight clean, four for each of eight successful restarts and two
for the failed constructed second generation.

`expected_final` has exact keys:

```text
reserved_attempts,constructed_generations,terminal_reason,first_failure,
promoted_generation,promoted_state_ref
```

Terminal reason is `completed`, `seed_mismatch`, `unavailable_packet` or
`generation_limit`. First failure is the earliest case failure and remains recorded
even after successful generation-2 promotion. Each attempt also preserves its own first
failure; the second stale fault cannot replace the earlier deep gap. A frozen valid
result is expected in nine cases, not in seed refusal, unavailability or exhausted
second-generation failure. Counts here are hand expectations, not execution evidence.

## Freeze and audit

Store the canonical `oracle.json` and a separate `freeze-manifest.json` in a fresh
ignored directory. The latter binds the schema/policy/generator bytes, accepted source
anchor identities, referenced file identities, exact oracle bytes and aggregate planned
counts. Record `runtime_executed: false`, no production imports, no new historical raw
read and no independent reference rerun. No implementation is allowed to create its
own expected inventory, arrival result, lifecycle action or promotion token.

A separate stdlib-only audit must rehash all fixed references; check the accepted Git
blobs; resolve every original packet/source/state reference; verify bounds, applied vs
returned partial state, EOF/end differences, refusal nulls and all control outcomes;
and independently recount canonical versus synthetic planned coverage. Repeat oracle
serialisation into another fresh ignored directory and compare its bytes. These are
contract/expectation checks. Gate 13 still owes actual lifetime, runtime and sanitiser
evidence before the project can claim a verified restart implementation.
