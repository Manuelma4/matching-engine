# Bounded offline restart runtime interface

Gate 13 implements the [reviewed restart policy](OFFLINE_RESTART.md) against the
[frozen oracle](OFFLINE_RESTART_ORACLE.md). This document freezes the concrete private
runner interface before its first implementation execution. It specifies obligations;
runtime results will be recorded separately. Public `Receiver`, `L3Book`, producers and
the queue/fill kernel remain unchanged.

The accepted oracle is 159,212 bytes, SHA-256
`aa4ba251f3a3294d3589a8128257d5f62259f218430458ee25f1d6fad9d80db5`;
its manifest is 13,784 bytes, SHA-256
`987ae273e587d6536b6e9cab7b6adedbca818354de624f1c7327a9ef1f49fc95`.
The design evidence is committed as `cef89d1e567f8aa1abffd251f803304fda391228`.
No changed runtime output may replace these expectations.

## Private components and inputs

Add `itch-feed-handler-tests/offline_restart.cpp`, a standalone private
`restart-runtime/CMakeLists.txt`, and an independent Python verifier in the same sibling
harness. Preserve the existing private top-level CMake file, Gate 11 worker and earlier
fixtures. The new worker may include the unchanged `canonical_transport.cpp` with its
`main` renamed solely to reuse strict loaders, original-slot binding, application and
complete FIFO/BBO comparison helpers. Pin its SHA-256
`43acf19c60275ca360d472a14f2aabd6d3b88bdd618f612cbb5313031a6e7758`.
Never execute its old main, `run_case` or plan loader: their single last-event counter
and failed-receiver continuation semantics do not implement this restart policy.

```text
offline_restart BUNDLE_DIR GATE11_ORACLE_DIR SCHEDULE_DIR
```

The Python verifier first authenticates the accepted oracle, manifests, original
bundle, independent inventories and source joins. It materialises four schedule-only
CSVs from input/action fields, without any expected outcomes. These are the exact
headers, with unquoted ASCII, LF endings and canonical unsigned integers:

```text
cases.csv:
case_index,case_id,scope,window_ref,window_id,layout,input_manifest_sha256,seed_sha256
attempts.csv:
case_id,ordinal,request_kind,admission_mutation,unavailable_packet_index,eof
arrivals.csv:
case_id,ordinal,arrival_index,packet_index,mutation
controls.csv:
case_id,control_index,after_attempt,action,token_source,token_mutation,payload_window_ref,payload_event_index,payload_state_id,packet_index
```

Optional fields are empty except `eof`, which is always `0` or `1`: use `1` for an
admitted attempt's planned EOF and `0` for a refused attempt, which has no EOF or arrivals.
The version-1 unavailable index is empty or the specified packet 6. Paths are fixed
roles selected by the three directory arguments; rows cannot supply filenames. Apply
the policy bounds before allocation/iteration, including sixteen cases, two attempts,
64 arrivals per generation, 128 per case, eight controls and 8 MiB per file/report.
Require complete consecutive keys and reject unknown enums, extra files and aliases.
Authenticate all consumed files and scripts before/after execution; recheck the original
used CSVs against cached authenticated bytes and metadata before each admission.
Copied seed/availability controls operate after corpus authentication and before any
consumer construction. Unexpected file, constructor, allocation or checker failures
abort verification rather than become expected restart outcomes.

## One ownership scope per generation

Use a small synchronous `run_generation` function taking immutable authenticated
projection/oracle data, action-only attempt data, case identity and a lifetime monitor.
It returns a value-only record. Prepare the result outside an explicit inner scope.
Declare a lifetime guard before the local book and receiver, so its destructor records
disposal only after their destructors run. Mark construction only after both constructors
succeed. Import and compare the original seed before any callback.

The supervisor reserves an ordinal before admission, keeps at most two value-only
outcomes and one optional promoted candidate, and owns no retained mutable consumer.
Every admitted generation gets a fresh book, receiver and source cursor. At most one
generation is live. Record monotonic construction epochs; addresses may be reused.
After leaving the local scope, establish zero live generations and completed disposal
before setting `mutable_objects_discarded` or starting another attempt. No book, receiver,
callback, borrowed span, order pointer or reference to them escapes.

Derive applied and returned occurrence lists separately from actual callback execution.
Every admitted callback checks its exact slot, borrowed bytes and original source point,
applies one fact and compares the complete independent inventory/BBO. The intentional
MSFT throw follows the successful first add and its partial-state comparison, before
returning. Use a dedicated injection marker and a separate checker/unexpected-application
exception latch outside the receiver callback. Inspect that latch after `receive`;
its failure aborts the experiment even though the noexcept receiver catches exceptions.

Derive coverage from actual ordered/seen original occurrences. A bad end invalidates
immediately; EOF cannot substitute for a required end. Later input to any invalid
generation is supervisor-blocked without another receiver call. Emit a diagnostic
StateRef only after comparing the actual complete book at that boundary. A candidate
requires completed supplied input, exact coverage, checked end and final inventory.
Control payload StateRefs are request data: they cannot manufacture a candidate or
proof. Promotion checks the actual current candidate's complete token before its
already-promoted guard. Old-generation probes inspect saved values only.

## Actual worker report

Emit one checked JSON object and LF to stdout only after successful completion, with
these exact root keys:

```text
schema_version,model,runtime_executed,cases,lifetime_trace,counts,
state_checks_passed,cpp_sha256_recomputed,raw_full_identity_freshly_verified,
independent_reference_replayed
```

Values are version 1, model `offline_restart_runtime_v1`, runtime true, state checks
true and all three identity/reference flags false. The outer verifier supplies SHA-256
authentication. The worker does not read the raw day or rerun the external reconstruction.
Failing workers return nonzero and a diagnostic on stderr, without a success report.

Each case has exact keys:

```text
case_id,scope,window_ref,layout,token_context,attempts,controls,final
```

Each attempt has `{ordinal,admission,arrivals,eof,outcome}`. Each arrival has
`{arrival_index,actual}` and each control `{control_index,actual}`. Admission, arrival
actual, EOF, outcome, control actual and final objects use the exact key sets/types of
the oracle's corresponding expected objects. EOF is a direct result object or null.
The Python verifier independently projects the frozen expected objects into this shape
and compares every value with strict types and a precise first-difference path. Expected
values never set actual progress, verdicts, counters, StateRefs or promotion decisions.

Each lifetime entry is `{case_id,ordinal,epoch,event,live_generations}`, with event
`constructed` or `destroyed`. The verifier checks twenty-one distinct construction and
destruction epochs, original attempt order, no overlap, no event for refused admissions
and zero live generations at every return. Source/ownership review complements this
instrumentation; a reported boolean alone cannot prove C++ object lifetime.

`counts` has `{by_scope,total}`. Each count object has:

```text
cases,reserved_attempts,constructed_generations,promotions,controls,supplied_arrivals,
applied_callbacks,returned_callbacks,callback_state_checks,admission_refusals,
inventory_comparisons,compared_order_rows
```

The first ten counters describe actual execution and are compared with frozen planned
totals (renaming `expected_promotions` to `promotions`). Instrument every full-inventory
comparison and its observed row count for the last two. Split canonical and wholly
synthetic scope. Do not substitute Gate 12's 395 metadata references or 212,549 referenced
rows for executed comparisons, or call either figure a benchmark.

## Runtime acceptance

Build the isolated target and run the focused worker twice in Release and twice under
ASan/UBSan. Require exact repeated reports, all frozen outcomes, checked compiler/linker
sanitiser flags, fatal runtime options, no diagnostics and stable inputs/tools/binaries.
Use private test-only negative builds to show that reuse of the failed partial seed and
omission of the generation ordinal from token validation are detected at their intended
boundaries. The ordinal mutant may still deny an already-promoted request, but with the
wrong reason: `already_promoted` instead of `token_mismatch`. This checks token-guard
precedence; it does not demonstrate a successful unauthorised promotion. A
fresh book incorrectly seeded with copied failed state is sufficient to expose the
state-reuse hazard without retaining the old mutable consumer. Keep changed sources,
commands and failing diagnostics identified; no public bypass mode is added.

Publish aggregates only after the actual checks pass. Retain any failed build/recorder
attempt honestly. Allocation exhaustion, live retransmission, availability, timing,
performance and queue/fill behaviour remain outside this gate.
