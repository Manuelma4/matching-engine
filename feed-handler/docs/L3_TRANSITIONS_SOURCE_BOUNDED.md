# Source-informed, resource-bounded transition comparison

This separate experiment uses source availability learned before reconstructing its
requested books. It incorporates the original [complete comparison contract](L3_TRANSITIONS.md),
11,223 bytes, SHA-256 `49792512e02954e1b7f48c7fddc6c07f40f034f6ab6d41421a074af6405cd572`,
committed in `cf25f599ab6d9aea7382be56f86eb73ed8399c50`. Freeze this document and the
small private source changes before executing the new selection or either exporter.

## Prior observations and retained failures

The original one-second and separate ten-second selections both failed without a
post-open MSFT `X`. Neither generated successful checkpoints, exports or comparisons.
Their sources and independent failure reviews remain unchanged. The subsequent
[availability study](L3_AVAILABILITY.md), committed in
`4a2b1ec8d3878b799d0ade7a6ec26ff6db08a6dc`, scanned exactly 16,000,000 frames and
524,152,398 complete-prefix bytes. Its retained 9,529-byte result has SHA-256
`dc9e87ced77d2be27f36f5f1745ae062a24e137bd174a6bd640f0c65daf14d21`.
It found the first post-Q MSFT `X` at global sequence 8,294,190, 25,002,318,269 ns
after Q. Its initial full input hash and separate post-walk prefix hash passed.

That study counted wire messages only, supplying no independent book states or
candidate ranking by agreement. This selection is explicitly informed by its source
availability observations; do not describe it as chosen before seeing that prefix.
No book export or comparison ran for either rejected profile or the study. Preserve
both negative results rather than relabelling them as this experiment's successes.

## Fixed source-based selection

Use rule `first_x_u_four_windows_v3`. Apply the original fixed MSFT/QQQ directory
identities, first post-Q `X/U` anchors, latest post-Q mutation seed or global Q seed,
next three same-symbol mutations, unfiltered census, source ordering and deduplication.
The complete role/state/occurrence schemas and interfaces remain unchanged.

There is **no elapsed-time deadline**: `bounds.search_duration_ns` and `deadline_ns`
are explicitly JSON null under this rule. No caller may override them. All other
original caps remain fixed: 16,000,000 global frames, 536,870,912 consumed-prefix
bytes, 100,000 captured post-Q selected headers, 4,096 census rows per window,
twenty unique checkpoints and 8 MiB selection artefacts. Selection succeeds only
when all four windows have all five roles, stopping exactly at the last required tail.
Missing anchors/tails at a resource cap, malformed input, incomplete inventories or
any discrepancy fail the whole experiment. There is no fallback or candidate
substitution. This is a resource-bounded first-occurrence rule, not another trial
of progressively later clock deadlines or continuous coverage of the studied prefix.

Empty sides/books remain mandatory observations. Do not filter on quotes, quantity,
partial/full cancellation, same/moved replacement price, queue position, trading status
or agreement. Classify actual X/U semantics and BBO effects only after full comparison.

## Execution and scope

Preserve all v1/v2 code and fixture bytes. New private `_v3.py` copies may change only
the rule/module/contract identities, the two nullable time fields and removal of time
arithmetic/checks. Replace the former deadline rejection control with a successful
forward-time fixture that still obeys frame/byte caps; retain all other controls.
Authenticate this document and the immutable incorporated original contract.

Run source-independent enumeration before exports, each unchanged retained Release
exporter twice, the unchanged complete L3 comparator, then independent copied-state
X/U delta checks. Require every requested complete state, explicit empty inventories,
zero validation counters, repeated producer bytes and original source joins. Freshly
check the full raw identity before selection and after comparison, and the newly
consumed prefix separately. Retain source/reference/helper/binary/process identities
and any first failure. Publish aggregate outcomes; detailed source and order data
stay ignored. Attribute coverage to unique checkpoints, separately counting role
memberships and overlap with the earlier fifteen states.

The accepted Release binaries are reused: no new compilation, sanitised historical
replay or compile-time dependency-equivalence claim follows. Reconstruction FIFO is
the pinned convention, without attribution, actual exchange priority, hidden liquidity,
eligibility, queue/fill or performance claims. The identified-history and transport
profiles remain restricted to `A/D/E`; this gate does not expand causal admission.
