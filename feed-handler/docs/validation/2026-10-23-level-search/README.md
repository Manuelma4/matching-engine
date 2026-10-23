# Price-level search: executed correctness and measurements

Binary search is correct at all checked states and slower in all 24 matched timing
pairs in this experiment. Reverse-linear remains the default. This is a useful
negative result: a lower search-comparison bound did not produce a faster complete
replay on these two days and this host.

The [comparison](comparison.json) preserves every sample, child command, execution
position, summary, fingerprint identity, build/source identity and environment record.
It is a portable publication copy of the successful private report. The original
report has 326,882 bytes and SHA-256
`2c8961b3892d21db95ab41c29a4d1e83bea786b6efcf5a90ab45756d84967c1c`.
The [accepted prerequisites](prerequisites.json) bind the actual original C++ matrix,
separate Python follow-up and four retained-state exports before measurement.
The [verification aggregate](verification.json) joins those executed stages and two
independent retained-output reviews. Publication itself adds no replay or timing.

## Observed replay times

Seconds: median (minimum–maximum), six fresh processes per configuration.
The final column is the median of six within-round `(binary/linear - 1)` percentages;
it is different from the ratio of the two marginal medians.

| Flow / capacity | Reverse-linear | Binary | Paired median time increase |
|---|---:|---:|---:|
| NASDAQ / default | 28.451 (28.349–28.951) | 30.514 (30.349–31.356) | 7.01% |
| NASDAQ / fit | 32.237 (31.701–34.160) | 34.087 (33.857–34.362) | 5.93% |
| BX / default | 0.957 (0.925–0.986) | 1.133 (1.101–1.141) | 17.06% |
| BX / fit | 0.708 (0.705–0.714) | 0.936 (0.933–0.948) | 32.45% |

Every paired ratio exceeds one. The smallest is 1.000679773 in fitted Nasdaq,
only about 0.068% longer in that pair. Fitted Nasdaq's marginal ranges overlap;
the other three pairs of ranges are disjoint here. These observations describe
this finite experiment. They establish no significance level or universal ranking.
No run was discarded and no timing-driven retry or parameter tuning occurred.
Construction and teardown are measured separately, with all six values retained
in the comparison. They are excluded from the replay times above.

## Separately observed process memory

MiB, one streaming observation per configuration, sampled immediately after replay.

| Flow / capacity | Reverse-linear | Binary |
|---|---:|---:|
| NASDAQ / default | 354.3 | 355.3 |
| NASDAQ / fit | 226.7 | 226.6 |
| BX / default | 343.4 | 343.1 |
| BX / fit | 35.4 | 35.4 |

The representation is unchanged. These whole-process high-water marks include pools,
vectors, allocator, program and input buffer. One observation gives no RSS variability,
allocation count or isolated directory-memory estimate. Mapped timing RSS is not used
for this memory comparison; streaming elapsed time is not a replay timing sample.

## Executed evidence and identities

- Implementation commit: `4a1e294e0388a824b9ec4d8a8e41bc45afc78dda`.
  Accepted-prerequisite/measurement commit: `ac4c22867795e47b708e7bf0af00ea63c5e767f5`.
  All 44 implementation file identities stay fixed during measurement.
- Eight small builds: two search policies × two reference indices × Release/ASan-UBSan.
  Each registers 49 methods; 380 case instances pass and twelve expected standard-only
  instances are skipped in flat builds. All 24 selected CLI group instances pass.
  A private copied-source mutant fails at the intended deep-price lookup assertion
  after correct BBO and complete visitation. A GoogleTest header warning is retained;
  normal test process stderr is empty.
- Eighteen initial runner controls pass. The separate Python-only follow-up passes
  22 controls with the original eighteen method ASTs unchanged. Its four additions
  address empty log identities, exact tested-tool binding, export aliasing and engine
  compile coverage. The original eight-build report is preserved rather than relabelled.
- Four fresh prefix exports: both policies exactly match the retained 15/20-point
  independent ordered CSVs and typed local summaries. This is 70 state comparisons,
  77,950 ordered row instances and **35 distinct reused independent states**.
  No external reference is executed anew.
- Eight complete correctness replays: 269 Nasdaq checkpoints (268 populated) and
  29 BX checkpoints (28 populated) per configuration. Ordered checkpoint bytes and
  complete semantic summaries match across policies/capacities and the accepted
  prior full-day semantics. All lifecycle/anomaly checks pass. Across the eight runs
  there are 1,192 checkpoint-row instances; these are sampled regression checks.
- Eight separate streaming RSS passes, then 48 fresh timing processes in the exact
  preregistered AB, BA, BA, AB, AB, BA schedule with rotating flow/capacity groups.
  All 64 full-day children exit zero with empty stderr and accepted semantic summaries.
- Both complete raw inputs are freshly SHA-256 checked before/after the prerequisite
  phase and before/after the full matrix. Final source/binary/cache/checkpoint/output
  identities remain unchanged. Market data, ordered exports and child output stay ignored.

## Host, scope and reproduction

Apple M4 Pro, 12 CPU cores, 24 GiB RAM; macOS 26.6.2; Apple clang 21.0.0,
Release `-O3 -DNDEBUG`, fixed open-addressed reference index. AC power is observed
before/after; the sampled thermal query reports no recorded warning and no recorded
CPU power status. That is not controlled frequency or a proof of no throttling.
No affinity, thermal, cache or frequency control is claimed. The complete load/power
observations and actual compile/link/cache commands are retained in the comparison.

Follow the [execution interface](../../LEVEL_SEARCH_RUNTIME.md) and
[frozen protocol](../../LEVEL_SEARCH.md), using fresh ignored destinations and the
identified private harness/data. This run uses `out/level-search-realflow-v1` and
`out/level-search-realflow-v1.json`; their first-attempt successful report is retained.
The public repository does not contain private harnesses, raw data or per-event exports.

The existing order/state fingerprints omit some directory aggregates and empty entries;
explicit API fixtures and 35 independent full-depth points supplement them. States
between independent samples, actual exchange priority, hidden liquidity, empirical
fills, live/tail latency and performance on other machines remain unverified. Source
hypotheses about near-touch probes, branches and vector movement require a separate
measurement to explain causes; elapsed-time ratios alone cannot do that.

Next review later-session independent L3/FIFO coverage before extending queue claims
or tuning another search policy. Preserve this negative result and the default.
