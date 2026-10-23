# Named executions in a bounded causal queue

The separate [pure overlay](../../../bench/identified_execution_queue.py) implements
`simulate_execution_prefix(ledger, config, expected_sources=None)` for the frozen
[five-fact contract](../../IDENTIFIED_EXECUTION_PROFILE.md). Its first runtime passes
all thirty API calls. Complete historical inventories, delivered information and our
hypothetical marker remain separate. The original one-U API remains unchanged.

[Aggregate evidence](verification.json) binds the source-reviewed implementation,
independent verifier, pre-implementation expectations, materialised refusals and actual
outputs. Market data, full inventories, traces and private harnesses remain ignored.

| Actual verification | Result |
| --- | --- |
| Positive calls | Seven scenarios repeated twice: fourteen pass |
| Scheduled trace / pending rows | 184 / 26 across both batches |
| Complete historical order-row instances | 38,976; six reused inventories per call |
| Repeat result bytes | Identical for every scenario |
| Intended input refusals | Sixteen: configuration eight, profile seven, clock one |
| Altered actual-output controls | Five rejected at their intended checks |
| Protected input / actual artefact identities | 115 / 22 |
| New independent historical states | Zero; distinct coverage remains 37 |
| Own fills, position, cash changes and fees | Zero under the declared convention |

## Historical changes and the own marker

The original QQQ seed is 34,201,694,396,241 ns; the inclusive final E clock is
34,201,718,415,103 ns. The 24,018,862 ns interval contains selected A,D,A,A,E facts.
All six complete inventories retain best bid 213.5400 and ask 213.5500. Ask additions
and the lower-price bid still matter to complete payload identity.

The marker joins the best bid's tail. Its initial named cohort has 1,400 shares:
reference 7952763 has 500, reference 7982447 has 800, and reference 7983155 has 100.
D removes reference 7982447, leaving 600 ahead. E reduces reference 7952763 from
500 to 494, leaving 594 ahead. The marker never enters the historical inventory.
E names an external executed reference; this model provides no rule converting that
execution into our own fill. Zero own fills therefore check a convention, not real
execution probability, hidden liquidity or market response.

| Scenario | Final exchange / local state | Ahead | Pending at H |
| --- | --- | ---: | --- |
| Before all facts | live / live | 594 | None |
| Arrival at E after source processing | live / live | 594 | None |
| No seed delivered | idle / idle | 0 | Six feeds |
| Arrival after H | idle / pending | 0 | Own arrival |
| Acknowledgement after H | live / pending | 594 | Own acknowledgement |
| Own cancellation before the facts | cancelled / cancelled | 0 | None |
| Seed delivered at E | live / live | 594 | Five later feeds |

Equal-time phases are source, feed, strategy, arrival and own response. The last case
has feed delay H−S and decision H: it receives the captured PRE inventory at H while
exchange state is already POST. Its observed digest stays PRE; arrival joins behind
594. The inclusive horizon never advances to clear pending messages. The old one-U
example remains the available self-contained public demonstration; this increment
adds no general CLI or resumption framework.

## Independent verification and honest refusals

Before implementation, sixteen complete invalid inputs were materialised and reviewed.
Every ledger passes the existing structural validator; refusal checks can therefore
exercise the declared configuration/profile/clock boundary rather than accidental
malformation. Materialisation executes the existing ledger builder/validator only.
The original seven hand schedules were frozen earlier, before this model existed.

The separate verifier imports no project helper and does not inspect the model source.
It parses the retained independent CSV, checks all fifteen reference manifests and
16,886 rows, then derives the six selected inventories with explicit attribution
knowledge. It checks every ordered row, logical hash, frozen event envelope, pending
entry, final projection and intermediate cohort/lifecycle invariant. Each positive
call compares 2,784 historical row instances. Repetition adds checks, not samples.

The runner stores actual output before verification, authenticates exact source bytes,
checks unchanged arguments and checks quiet pure calls. Its file/process/network/import
tripwires are reviewed checks, not a security sandbox. Five altered actual copies fail:

- Swapped external FIFO references: complete historical inventory.
- POST digest under valid PRE observation clocks: captured information identity.
- Locally confirmed/live before own acknowledgement: own lifecycle.
- Horizon extended beyond E: coverage.
- Six executed external shares left ahead: named cohort quantity.

These five controls differ from the earlier four altered *expectation* controls.
The independent verifier's cancellation-state update was corrected during source
review, before any runtime call. The first actual execution passed with empty stdout
and stderr; no model rerun was needed.

## Reproduction and limits

The public entry point is `simulate_execution_prefix(ledger, config, expected_sources=None)`.
Read the frozen contract alongside the source to understand the accepted ledger and
closed configuration. The existing one-U example remains the self-contained runnable
learning example. Canonical reproduction additionally requires private retained inputs
and the reviewed harness; exact invocations and machine-specific provenance stay in
local ignored records. Existing output directories refuse reuse.

Execution used feed main `f56716ebca73d8e536859728a864e9881a40ad1f` and engine main
`dbd280185a0d45f0839881caeff8d535bcd56779`. The new overlay was separately hash-bound
and uncommitted. Old 61 implementation files matched HEAD; this module adds the 62nd.
Publication metadata checks require no runtime rerun. The public aggregate retains
content hashes and counts without exposing private filenames or local directories.

Admission joins retained common raw identity, complete selected coverage and the
restricted status census. It grants this finite model's policy only. The pure module's
authentication flags remain false. No raw file is opened, statted or hashed, and no
reference/book replay, C++ build, sanitiser or performance experiment runs here.
There is no materialised exact global endpoint/witness at E; selected-book closure
remains the supported claim. Absent h/N stays unknown. No empirical fill calibration,
actual exchange priority, wider historical coverage or general backtester is established.

Tutorial Chapter 40, Exercises 92–94, connects the actual evidence to those limits.
The next useful step is a compact learning and evidence walkthrough across the existing
pipeline, identifying concrete remaining gaps before choosing further implementation.
