# Price-level search implementation and execution

The [frozen experiment contract](LEVEL_SEARCH.md) selects one algorithm comparison
within the same vectors. Builds now accept `-DITCH_LEVEL_SEARCH=reverse_linear`
(the default) or `-DITCH_LEVEL_SEARCH=binary`. The option propagates
`ITCH_BINARY_LEVEL_SEARCH=0|1` to every consumer. Both `itch_journal_replay` and
`itch_storage_bench` identify the selected policy as `level_search` in their JSON.

Only lookup, insertion-position search and empty-level search differ. The binary
path uses unsigned ascending-bid/descending-ask comparisons. The original linear
path, vector representation, slabs, allocation preparation, FIFO and replacement
semantics are preserved. Insertion/erasure movement and vector growth remain costs.

## Focused correctness evidence

Eight private builds cover both policies, both reference indices and Release plus
ASan/UBSan. Each registers 49 C++ methods: 380 case instances pass and twelve
standard-index-only instances are correctly skipped in flat builds. All 24 selected
CLI group instances pass. Six new hand-specified scenarios reconcile complete
traversal, deep quantities, per-price FIFO, references, best and counts, including
unsigned endpoints, vector growth, both-side erasure and replacement tails.

A copied-source negative control returns a missing deep price without changing
add, visitation or BBO. Its dedicated test passes the BBO/full-inventory assertions
and fails exactly at the deep per-price queue. It changes no production source.
All normal GTest/CTest process stderr is empty. Builds retain a GoogleTest 1.15.2
header character-conversion warning, including the mutant build.

The initial eighteen Python runner controls pass. Source review then identifies
admission issues before historical execution: empty successful stderr must have a
valid identity, actual engine compile commands must be required, measured tools
must match their tested binaries, and fresh exports cannot alias retained files.
A separate twenty-two-control follow-up passes after these Python-only corrections.
All original eighteen method ASTs remain identical. The earlier empty-log defect
is reproduced on a private empty file. The original eight-build report remains
unchanged; the follow-up permits exactly one public Python source transition and
checks all C++ source/binary identities without rebuilding or retesting them.

Private records are `out/level-search-unit-v1/verification.json` and
`out/level-search-python-followup-v1/verification.json`. These focused checks alone
establish neither historical equivalence nor a speed advantage. The subsequent
historical and measurement results are recorded below.

## Historical and measurement admission

The private prerequisite recorder must authenticate the fixed accepted unit and
Python-follow-up identities, four local exports against the retained 15/20-point
independent request sets, complete raw hashes and stable source/build inputs.
After reviewing actual execution, save its exact receipt authority in the fixed
committed `docs/validation/2026-10-23-level-search/prerequisites.json`.

That version-one document has eleven closed fields: `schema_version`, `model`,
`passed`, `errors`, `source_file_sha256`, `prerequisite_evidence`, `unit_evidence`,
`execution_receipt`, `producer`, `measured_binaries`, `python_followup`.
Its model is `level_search_prerequisite_acceptance_v1`. It pins the original C++
matrix, separate Python follow-up, actual four-child execution and exact measured
executables. The runner requires its current clean-main Git blob and all identified
bytes. Arbitrary self-declared successful proof labels are insufficient authority.
This staging clarifies evidence admission; it changes no workload, capacity, sample,
pair order, repetition count, timing boundary or statistic in the frozen contract.

After that acceptance is committed, run from the feed checkout:

```bash
python3 bench/compare_level_search.py \
  --reverse-linear-dir ../itch-feed-handler-tests/build-level-search-v1-reverse_linear-open_addressed-release/itch \
  --binary-dir ../itch-feed-handler-tests/build-level-search-v1-binary-open_addressed-release/itch \
  --prerequisite-evidence out/level-search-prerequisites-v1/proof.json \
  --output out/level-search-realflow-v1 \
  --report out/level-search-realflow-v1.json
```

Both destinations must be fresh, distinct and ignored. All eight complete correctness
passes must precede the eight separate RSS and 48 timing passes. The runner fixes
the protocol rather than accepting convenient alternative repetitions or data paths.
Keep every sample, first failure and negative result. Whole-process RSS and six
prefaulted-input timing repeats cannot isolate allocation, cache behaviour or live latency.

## Recorded outcome: 2026-10-23

Both policies exactly match the retained complete 15/20-point ordered exports and
typed local summaries: 70 comparisons and 77,950 order-row instances over 35 distinct
reused independent states. No external reference is executed anew. The accepted
prerequisite record is committed as `ac4c22867795e47b708e7bf0af00ea63c5e767f5`.
All 44 implementation file identities remain fixed throughout measurement.

All 64 full-day children pass on the first execution: eight correctness replays,
eight separate streaming memory passes and 48 timing processes. Checkpoint histories
match across policies/capacities, with 269 Nasdaq and 29 BX rows per configuration.
Both full input hashes pass before/after the prerequisite and measurement phases.

Binary is slower in all 24 observed matched pairs. Median paired replay-time increases
are 7.01%/5.93% on Nasdaq and 17.06%/32.45% on BX for default/fitted capacities.
Fitted Nasdaq includes overlapping marginal ranges and one pair only 0.068% slower.
Reverse-linear remains the default. These elapsed-time observations establish no
universal ranking or cache, branch, allocation or thermal cause.

The [executed evidence](validation/2026-10-23-level-search/README.md),
[aggregate verification](validation/2026-10-23-level-search/verification.json) and
[complete comparison](validation/2026-10-23-level-search/comparison.json) retain every
sample, command, identity, separate memory scope and independent retained-output audit.
Historical correctness remains limited to the checked API cases, retained states and
sampled fingerprints; the existing FNV walks omit some directory aggregates.
