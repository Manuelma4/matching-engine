# Price-level search design evidence

Gate 17 reviews the remaining price-level question from the earlier storage study.
Three independent source/correctness/protocol reviews approve the
[frozen contract](../../LEVEL_SEARCH.md), SHA-256
`6551554e3b4c96b2802dfeed14932dfdb6d0e4f619ada61acdbbc41f25325a79`
(14,506 bytes). The [aggregate record](design.json) identifies the inspected code,
private harness, inherited records and planned acceptance matrix.

The decision is one search experiment: reverse-linear versus binary lookup within
the same sorted price-level vectors. Reverse-linear remains the default. A tree
would change allocation and transactional replacement preparation; the engine's
ladder assumes a bounded price band absent from the feed. Both are deferred.
This decision changes no implementation and supplies no new performance result.

## What the review established

The source cost model distinguishes lookup from vector entry shifts, allocation,
direct-slot reductions and best-price access. Binary search lowers the search bound;
it does not remove insertion/erase movement. The candidate must preserve global
slabs, stable order/level slots, FIFO, allocation ordering and rollback guarantees.

The review identified two qualifications that acceptance now makes explicit:

- Existing order/state hashes omit some deep directory aggregates and empty entries.
  Full API controls and the 35 retained independent L3 states supplement those hashes;
  sampled equality still does not establish every-event historical correctness.
- The benchmark preflights framing, type lengths and after-end placement before replay.
  Required S(C), final empty book and semantic anomaly checks occur after replay,
  outside the timer. The contract preserves those actual boundaries.

Protocol review also fixes the numeric policy definition, prefix-child timeouts and
whole-process RSS sampling scope. All three reviewers approve the same final bytes.
Their reviews concern local source and contract consistency, not independent execution.

## Planned execution, still pending

Eight small correctness builds cover two policies, two reference indices and
Release/ASan-UBSan. Only the two unsanitised flat-index builds enter the real-flow
experiment. Four untimed prefix exports reuse the original 15-point and 20-point
request sets for each policy. They reuse 35 distinct independent states and execute
no external reference anew.

The fixed full-day matrix has eight correctness replays, eight separate streaming RSS
passes and 48 timing runs: 64 full-day children, plus the four prefix children.
Six rounds use AB, BA, BA, AB, AB, BA with rotating flow/capacity groups. Both inputs,
capacities, compiler/flags and reference index are fixed within each comparison.
The future record must retain every value, median/range, paired ratio, first failure
and identity guard, including a slower or inconclusive outcome.

No candidate, build, test, raw read, reference replay or timing is executed in Gate 17.
Historical independent depth coverage remains 35 states. The prior reference-index
study and all transport, observer, queue and fill evidence remain separate.

## Next gate

Gate 18 implements only the reviewed search alternative, freezes explicit focused
test expectations before execution, and passes correctness before measurement.
Its actual results require a separate runtime record. The contract is a prerequisite,
not a substitute for those results. Private harnesses and per-event output stay local;
all work stays in the existing main checkouts.
