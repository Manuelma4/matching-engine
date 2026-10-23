# Identified queue prerequisite review

Gate 24 completes a read-only review of the fixed QQQ same-price replacement.
The [contract](../../IDENTIFIED_QUEUE_PREREQUISITES.md) and [aggregate](review.json)
record two independent approvals, input/source identities, the next finite audit and
its limits. **No scanner or identified queue has run, and admission remains unproved.**

## Decisions

The existing fixed-level queue has no order-reference or atomic replacement event.
Its historical projector correctly refuses a U at the target level. Preserve that
behaviour; splitting U into cancel/add is not a faithful connection.

The adjacent PRE/U pair closes the PRE timestamp group, because U is strictly later.
It does not prove U is the last global frame at its timestamp. Whole-timestamp
market-before-request scheduling needs that closure. Directory and system O/S/Q
origins also leave the fixed pair's latest selected trading/cross/status admission open.
Earlier full-day and exploratory status clues remain at their original scope.

Both final reviewers approve the bounded remedy: parse status from byte zero through
an included first later-time witness, freeze seed/end status before it, then hash the
remaining already authenticated larger prefix without applying future information.
The next audit freshly checks the 524,152,398-byte c8 prefix and nested pair prefix;
full 8,251,407,909-byte identity stays inherited. A witness exactly on an inclusive
bound is allowed; missing coverage before the bound refuses. No full raw checksum,
book reconstruction or reference replay is needed for that prefix-scoped claim.

Any additional selected book mutation after U at the same time refuses this one-U
profile even if BBO is unchanged. Status is evaluated at PRE and every interval
update; ordinary superseded premarket states do not falsely fail seed admission.
Absent h/N knowledge remains unknown, and BX/PSX status cannot overwrite Nasdaq h.
The legacy restrictions are model choices, not complete venue order-entry eligibility.

## Review precision and next work

Review clarified accepted raw size, exact system sequence, preseed status supersession,
inclusive cap semantics and immediate local Pending at submit versus delayed exchange
outcomes. Earlier draft/approval snapshots remain identified. The final contract is
12,101 bytes, SHA-256
`3d15a6e3cea9cc834fbfbb7baaa8406197076f7d4baed6e0081281ce19774d52`.
These are source-review clarifications; no runtime discrepancy was measured.

Gate 25 must first freeze focused synthetic streams/refusals, review both private
scanner sources, then require exact independent canonical status/coverage results.
Keep original pair/caps and every refusal, without reselection. Only after success
may a later tiny identified shadow overlay freeze its concrete expected traces.
Conditional scenarios cover pre-U/at-U acceptance, skipped/pending actions, pending
responses and own-only cancellation. Historical liquidity, own marker and delivered
knowledge stay separate; U is never a trade and these scenarios infer no fills.

All 59 public implementation files remain unchanged at feed main
`a3c6aa15f6966e9a4e9caeedfc17e5f77e0acad9` and engine main
`dbd280185a0d45f0839881caeff8d535bcd56779`. No branches/worktrees are created.
This gate adds no raw scan/hash, C++ check, book/reference/observer/queue run,
performance experiment or independently reconstructed state. The historical total
remains 37. The English tutorial's Chapter 34 adds Exercises 74–76.
