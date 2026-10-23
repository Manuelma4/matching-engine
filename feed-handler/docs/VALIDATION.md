# Validation record

Validation establishes separate properties. A clean real-day lifecycle is useful
evidence, but it does not establish external BBO agreement or correctness at every tick.

Subsequent [independent BBO validation](BBO_VALIDATION.md) compares five instruments
on the canonical day at one second (306,140 rows), plus MSFT and QQQ at 100 ms
(1,224,560 rows). All sampled prices and aggregate quantities agree exactly. The
two implementations consume independently hashed identical raw bytes. The later
[L3 comparison](L3_VALIDATION.md) also checks complete displayed depth and reconstructed
FIFO at 37 distinct identified states, including the
[X/U extension](validation/2026-10-23-l3-transitions/README.md) and
[same-price replacement pair](validation/2026-10-23-same-price-l3/README.md).
Every-event quotes/depth, actual exchange priority and a separate vendor oracle remain unverified.

The [technical walkthrough](TECHNICAL_WALKTHROUGH.md) maps the existing evidence to
its invariants and limits, including the negative storage/search results. It adds no
new experiment or historical sample.

## Canonical Nasdaq, 2019-12-30

Validated on 2026-10-22 from the [official Nasdaq archive](https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/12302019.NASDAQ_ITCH50.gz),
using clean source commit `609acaff7a9804ded07c1ce047021c0b3c19f082`.
The complete [validation report](validation/2026-10-22-nasdaq-2019-12-30/validation.json)
and [independent comparison](validation/2026-10-22-nasdaq-2019-12-30/independent_comparison.json)
both passed.

| Check | Local result | Independent reference |
|---|---:|---:|
| Compressed bytes | 3,524,013,057 | 3,524,013,057 |
| Decompressed bytes | 8,251,407,909 | 8,251,407,909 |
| Messages | 268,744,780 | 268,744,780 |
| Observed message types | 18 | 18 |
| Peak live orders | 1,924,078 | 1,924,078 |
| Final live orders | 0 | 0 |
| Unknown/duplicate references, share underflows, capacity failures | All zero | See source census for its own lifecycle counters |
| Invalid sides, locate mismatches, unknown types, wrong lengths | All zero | Outside the independent histogram comparison |
| Trailing bytes / records after end | 0 / 0 | Outside the independent histogram comparison |
| System event C | Seen | Outside the independent histogram comparison |

Every observed message-type count matches exactly:

| Type | Local count | Reference count |
|---|---:|---:|
| A | 117,145,568 | 117,145,568 |
| C | 99,917 | 99,917 |
| D | 114,360,997 | 114,360,997 |
| E | 5,722,824 | 5,722,824 |
| F | 1,485,888 | 1,485,888 |
| H | 8,966 | 8,966 |
| I | 4,024,315 | 4,024,315 |
| J | 34 | 34 |
| K | 3 | 3 |
| L | 215,161 | 215,161 |
| P | 1,218,602 | 1,218,602 |
| Q | 17,836 | 17,836 |
| R | 8,906 | 8,906 |
| S | 6 | 6 |
| U | 21,639,067 | 21,639,067 |
| V | 1 | 1 |
| X | 2,787,676 | 2,787,676 |
| Y | 9,013 | 9,013 |

The other recognised types (`B`, `N`, `O`, `W`, `h`) have zero occurrences on this
sample. Missing known keys are compared as zero; an unexpected type is rejected even
if its reported count is zero. The sample has no optional BinaryFILE end record:
`sum(count × (message length + 2)) = 8,251,407,909` exactly.

Locally computed archive SHA-256:
`ef03df46a27e6bda4dead017f84c2e3979df7211f02c7868b51d53fceb99c689`.
Decompressed SHA-256:
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
The runner checks gzip CRC and independently hashes the bytes sent to census and replay.
The listed Nasdaq `.md5sum` sidecar returned HTTP 404 during this run.

The independent census is [KareemJandali/itchbook at a pinned commit](https://github.com/KareemJandali/itchbook/blob/3c646f9da182136125059243b475f7b8baa53773/validation/census-2019-12-30.json).
Its [normalised reference](reference/nasdaq-2019-12-30-itchbook.json) preserves source
provenance and the identity of the reference JSON. This is a separate implementation
of the same exchange feed, not a separate venue or vendor. It publishes no input
SHA-256, so the comparison correctly records `passed: true` alongside
`identity_verified: false` and `comparison_strength: filename_counts_bytes_only`.
The source artifact hash must not be mistaken for a hash of the market data.

Counts and byte totals establish aggregate framing agreement. Peak/final order counts
add aggregate lifecycle agreement. Neither proves matching prices, timestamps, BBO,
depth or queue position at each event. The final empty-book FNV hash is constant and
cannot supply that missing evidence. External quote validation remains a separate gate.

Reproduce from this repository, using new output paths:

```bash
python3 bench/validate.py data/12302019.NASDAQ_ITCH50.gz \
  --bin-dir build --output out/canonical-validation \
  --source-url 'https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/12302019.NASDAQ_ITCH50.gz'
python3 bench/compare_reference.py out/canonical-validation/validation.json \
  docs/reference/nasdaq-2019-12-30-itchbook.json \
  --output out/canonical-independent-comparison.json
```

The comparator has 21 private regression cases, including mismatched types/totals,
peak/final orders, failed lifecycle checks, malformed JSON, non-boolean truthy values,
optional external input hashes and preservation of previous evidence. The expanded
private release CTest run passed 31/31 tests. Its two existing Python suites have 14
CLI cases and four evidence-runner cases; the new comparison suite adds those 21 cases.
The streaming elapsed time includes Python, gzip, hashing and pipe I/O. Concurrent
validation processes also ran, so these elapsed values are not performance benchmarks.

The full 268,744,780-message day was also replayed with AddressSanitizer and
UndefinedBehaviorSanitizer. It exited successfully, produced no diagnostic bytes and
matched every release semantic report line (excluding elapsed timing). The
[sanitised report](validation/2026-10-22-nasdaq-2019-12-30/asan_replay.txt) and
[additional checks](validation/2026-10-22-nasdaq-2019-12-30/additional_checks.json)
record the result, commands and executable hash. The separate mmap input's SHA-256
also matches the streamed raw input; their lifecycle and volume reports agree.

## Nasdaq BX, 2019-07-30

Run on 2026-10-22 using the [official sample archive](https://emi.nasdaq.com/ITCH/Nasdaq%20BX%20ITCH/20190730.BX_ITCH_50.gz).
The archive stays in ignored local `data/`. Only aggregate reports are versioned.

| Check | Result |
|---|---:|
| Compressed size | 391,242,214 bytes |
| Decompressed BinaryFILE size | 837,472,908 bytes |
| Messages | 28,734,686 |
| Add messages, A + F | 10,629,593 |
| Executions, E + C | 681,693 |
| Peak live orders | 67,283 |
| Live orders at end | 0 |
| Unknown references / duplicate references | 0 / 0 |
| Share underflows / exhausted capacity | 0 / 0 |
| Unknown message types / wrong lengths | 0 / 0 |
| Invalid sides / reference-locate mismatches | 0 / 0 |
| Trailing bytes / records after end | 0 / 0 |
| System event C | Seen |

Archive SHA-256:
`a0a057010cc5172cfaf2d8a7b4d5f133557fa47b3a5837fcf985b6e5533e50eb`.
Decompressed SHA-256:
`6741035beda0c237fc2d30e03756f30449791844f372de955a29da32a4b842e5`.
These are locally computed identities, not signatures supplied by Nasdaq.

The runner independently decompresses the archive for census and replay, checks gzip's
CRC, hashes every decompressed byte, and requires both tools to succeed on identical
input. The byte identity includes the optional two-byte zero-length end record. The
full reports, source and binary hashes, and environment are retained in
[validation/2026-10-22-bx/validation.json](validation/2026-10-22-bx/validation.json).

```bash
python3 bench/validate.py data/20190730.BX_ITCH_50.gz \
  --bin-dir build --output out/bx-validation \
  --source-url 'https://emi.nasdaq.com/ITCH/Nasdaq%20BX%20ITCH/20190730.BX_ITCH_50.gz'
```

The output directory must be new. A corrupted archive, incomplete record, tool failure
or failed lifecycle criterion produces a non-zero exit code and failed JSON evidence.
The runner's elapsed times include Python, gzip, hashing and pipes; use the C++ benchmark
for per-layer costs.

The same decompressed bytes were replayed through mmap. Message count, all lifecycle
counters, the final hash and the ranked volume rows matched the streaming report.
[Additional checks](validation/2026-10-22-bx/additional_checks.json) and the
[mapped report](validation/2026-10-22-bx/mapped_replay.txt) retain that comparison.

## Engine loopback

Five synthetic instruments, one per matching-engine regime, seed 42, 1,000,000
operations per instrument:

| Check | Result |
|---|---:|
| Engine operations | 5,000,000 |
| Bid/ask comparisons after operations | 10,000,000, all equal |
| Final queues, every stock and price | Identical |
| Replica anomalies | None |
| Final book hash | `deeac4250bf08677` |

```bash
mkdir -p out
./build/itch_loopback --ops 1000000 --seed 42 --out out/loopback.itch
./build/itch_replay --allow-partial out/loopback.itch
```

The loopback intentionally retains orders after its synthetic system C, which is why
standalone replay requires `--allow-partial`. This differs from the selected BX sample's
observed zero-live end state. The full-day CLI policy is a validation criterion, not a
claim that the presence of C alone guarantees an empty book on every feed.

## Regression checks

Private tests cover known independent wire bytes; unaligned integer decoding; framing
across small blocks; truncated frames; stream read errors; invalid numeric arguments;
empty inputs; end-marker ordering; invalid side fields; cross-stock reference misuse;
pool capacity; and order priority preserved after a rejected replacement. Allocation
failure injection checks both level capacity recovery and unchanged original queues.

Evidence-runner tests use synthetic wire bytes to check SHA-256 and message counts,
truncation, gzip CRC and invalid-deflate failures, and preservation of existing reports.
The suite runs in release and with AddressSanitizer + UndefinedBehaviorSanitizer. Tests
and CI remain outside the public source repository, following this portfolio's convention.

The BX validation run passed 30/30 CTests in each feed configuration, including 28 C++
cases and two Python integration suites (14 CLI cases and four evidence-runner cases).
The matching engine's 172 release CTests also passed. A separate ASan/UBSan mutation
campaign used seed 42 and 200 rounds: 5,536,099 decoded messages, expected anomaly
counters, and no sanitizer failure. This is a bounded robustness campaign.

## Local replay measurement

Five runs per layer on the mapped BX file, Release (`-O3 -DNDEBUG`), Apple Silicon,
Apple clang, without CPU pinning. Setup, final hashing and teardown are excluded from
replay timing. The full [benchmark log](validation/2026-10-22-bx/benchmark.txt) and
[compiler/build record](validation/2026-10-22-bx/build-info.txt) are retained.

| Layer | Median | Range |
|---|---:|---:|
| Framing | 543.1 M messages/s | 523.0–557.2 |
| Dispatch | 550.4 M messages/s | 546.9–556.2 |
| L3 replay | 28.9 M messages/s | 28.0–29.2 |

These are independent loop timings from one process with a fixed layer order, not an
interleaved comparison across implementations. Framing and dispatch overlap in range;
subtracting the medians would not measure an incremental dispatch cost. The 34.6 ns
per message for replay is a batch average, not an individually timed latency or p99.

## Deterministic observed-wire journal

The canonical Nasdaq day also passes version-1 journal determinism and replay checks
at source commit `f3750781ef8b34b47dba0d4194f11fcae9c2939d`. Two creations have the same
8,251,596,893-byte size and SHA-256, preserving the independently identified raw input.
Raw input and both journals each replay all 268,744,780 messages cleanly, with matching
semantic summaries and 27 identical intermediate checkpoint rows, 26 populated.

The format preserves observed wire bytes, including metadata and rejected events;
it does not encode only accepted changes. Python recomputes SHA-256, whereas C++ checks
container structure and CRCs and marks the stored source digest unverified. Schema,
hand-worked FIFO controls, corruption checks and limits are in [JOURNAL.md](JOURNAL.md).
The [aggregate report](validation/2026-10-22-journal/canonical_journal.json) includes
source/binary identities, input stability and deterministic checkpoint-file digests.
Private detailed journals and checkpoint rows remain ignored.

## Reference-index comparison on real flow

The flat and standard hash-map builds, each with default and fitted capacity, agree
on all counters and populated checkpoints for the identified full Nasdaq and BX days:
269 Nasdaq checkpoints and 29 BX checkpoints per configuration. Their corresponding
previous-code checkpoints also agree exactly, preserving the established baseline.
All eight correctness, eight memory and 48 timing processes complete without reported
anomalies. Source commit: `52229945705389323519c50a0c234e9fbbcd956c`.

The six-observation timing comparison favours flat replay and standard-index construction
in each matched profile. Capacity fitting reduces streaming process RSS, but the Nasdaq
flat median increases with overlapping ranges. The protocol retains this negative
result. [STORAGE.md](STORAGE.md) records the measurements, allocation-failure transaction
tests, input/build identities and limitations. The
[aggregate report](validation/2026-10-22-storage/comparison.json) contains every run;
the [prior-code checks](validation/2026-10-22-storage/prior_code_equivalence.json)
retain continuity with the earlier validated implementation.

## Bounded synthetic causal queue foundation

Source commit `670925437deaf00c0412bb4575604d4a6f201749` adds the standalone
`itch_queue` model and `itch_queue_sim` CLI. It does not alter the decoder, L3
reconstruction, journal or matching-engine code. The [model contract](QUEUE_SIMULATOR.md)
defines fixed-level observations, immutable delayed snapshots, equal-time phases,
shadow fills, cancellation assumptions, exact fees and separate exchange/local accounts.

The private harness now registers 75 Release CTests. This increment passes the 23
selected queue CTests: 22 C++ cases and one CLI suite with 22 Python methods.
The same 22 C++ cases and 22 CLI methods pass focused ASan/UBSan checks without
diagnostics. Earlier reconstruction/storage checks remain the prior evidence;
no full-day replay or performance measurement was repeated for this separate component.

Eleven hand-worked scenarios each run twice from the clean source commit: 22 CLI
processes, matching expected accounts/states and byte-identical summaries/audits within
each pair. They include optimistic/conservative fills, sell accounting, equal-time
zero-delay ordering, stale-quote rejection, partial fills followed by cancellation,
undelivered feed data and fill/cancellation responses left pending at the horizon.
Input, binary and audit digests are retained in the
[aggregate report](validation/2026-10-22-queue/hand_worked.json); detailed rows remain ignored.

A private mutated copy deliberately makes the decision read current exchange quantity
and quotes instead of its delivered snapshot. The baseline no-look-ahead test passes;
the mutated executable fails the expected submission assertion. The production source
is unchanged. [Negative-control identities](validation/2026-10-22-queue/lookahead_control.json)
and the [verification record](validation/2026-10-22-queue/verification.json) retain commands,
hashes, test coverage and limits. The initial combined Release CTest attempt found an
unbuilt private CLI target; building it resolved that harness setup failure without a
production-code change, and all 23 selected CTests then passed.

These are synthetic model checks, with hand-calculated references. They do not add an
exchange/vendor execution oracle, calibrate fill probabilities or establish realised
P&L. A historical adapter needs separate source provenance, trading-state and changing
price-level rules before real-event fill experiments are justified.

## Canonical bounded displayed-history projection

Source commit `40f22c6a945b7512c8c6dd8866e3e60cdbed05b5` adds the strict historical
projector, without changing the decoder, replica, journal, queue kernel or matching
engine. The [contract](HISTORICAL_WINDOW.md) defines its full-source lifecycle checks,
fixed-positive-best scope, regular-session prerequisites, per-wire reconciliation and
explicit unsupported-event rejection.

Both Release projections consume all 268,744,780 canonical messages and 8,251,407,909
raw bytes, matching the eighteen observed type counts. SHA-256 before and after equals
the earlier BBO/journal/storage input identity. Each succeeds only after the complete
source closes cleanly; the source contains no `B`, `h`, `W`, `N` or direct-listing `O`
messages. Those paths are exercised by hand-encoded fixtures rather than this day.

| Buy-side window | Start ns, exclusive after seed | End ns, inclusive | Duration ms | Independent states | Normalised rows | Own-level displayed executed shares |
|---|---:|---:|---:|---:|---:|---:|
| MSFT at Price(4) 1589000 | 34214907518545 | 34214938994341 | 31.475796 | 7 | 6 | 196 |
| QQQ at Price(4) 2135400 | 34201694396241 | 34201723909063 | 29.512822 | 8 | 4 | 6 |

A private helper uses only the pinned independent itchbook reader, decoder and book at
`3c646f9da182136125059243b475f7b8baa53773`; its source archive and headers are verified,
and no implementation is copied into the project. It replays 7,993,582 prefix messages,
273,665,559 bytes, sufficient to cover the final chosen window. Each projector seed and
selected post-message state matches four BBO fields: fixed same-side price/quantity and
opposite price/quantity. Source sequence, offset, timestamp, length and type match too.
All 15 states agree, comprising two seeds and thirteen subsequent observations.

A separate local-book helper also agrees with the reference's exposed order counts at
those states. The projector itself exposes no order counts, so they are not part of
its four-field comparison. This is an independent implementation of the same bytes,
not another exchange/vendor market-data source. The
[canonical aggregate](validation/2026-10-22-window/canonical.json) retains commands,
source/input/tool/reference identities, coverage and comparison counts.

The real-data negative control selects an earlier QQQ window ending at
34200184812955 ns, before its opening cross at 34200963039891 ns. Market hours and
trading status are already announced, but the opening prerequisite is missing.
The adapter correctly returns 1 with empty stdout and creates neither output file.
Selecting supported later intervals is a retrospective adapter test, not a causal
strategy sampling rule.

Private checks pass 21 C++ cases and 18 CLI methods in Release and ASan/UBSan. The
combined Release selection passes 22 CTests; the harness now registers 97 in total.
Fixtures independently encode byte offsets, equal-timestamp seed/end groups, atomic
opposite replacements, target-replacement rejection, priced executions, non-displayed
prints, absent/invalid status, stock/locate identity, later broken executions and the
99,999-message bound. [Verification](validation/2026-10-22-window/verification.json)
records focused logs, harness/binary hashes, the official specification reading and
scope. Full canonical projector sanitizer and performance runs were not performed.

No historical queue/fill simulation was launched. Matching displayed-state projections
does not establish parent aggressor demand, hidden liquidity, counterfactual response,
calibrated fills or strategy P&L. Detailed event/provenance rows remain ignored under
`out/window-canonical-v1/`.

## Bounded historical causal handoff

Source commit `83973d9a5a350810bcf0f373d5fceb534f4605ac` adds a Python handoff audit
without changing the reconstruction, projector, queue kernel or matching-engine code.
Its clean-`main` run uses the two frozen Gate 5 projections, six declared delay/cancel
profiles and both cancellation assumptions: 24 configurations. All 284 processed
audit rows agree field for field with a separately implemented Python schedule,
including clocks/phases/serials, immutable observations, queues, exchange/local accounts,
decision lineage and pending events at the inclusive horizon.

Before any matrix launch, a separate worker froze literal CSV inputs and hand-derived
complete summaries, final audit fields and pending schedules. The oracle SHA-256 is
`4ccb5e7ccc1d9c3d6f4c1f1382d529335e08aff207e9978dfd6463b00e621c6e`.
All 24 summaries and their final-state expectations agree. Detailed source/audit joins
stay ignored under `out/handoff-canonical-v1/`; the
[aggregate report](validation/2026-10-22-handoff/canonical.json) retains configurations,
commands, artefact hashes and causal checks. The
[verification record](validation/2026-10-22-handoff/verification.json) retains the
private harness, logs, frozen oracle and independent final-comparison identities.

There are zero fills, positions, cash movements and paid fees in all cases. Immediate
MSFT orders retain 538 shares ahead under optimistic cancellation and 648 under
conservative cancellation; QQQ retains 594 under either assumption. With 1,000 ns feed
delay, the final observed quantities are MSFT 934 versus external 738 and QQQ 594 versus
external 1394. A late cancellation has completed at the simulated exchange while still
locally live; its response and the final feed remain pending. The arrival-pending control keeps
100 shares in transit. No horizon flush, forced liquidation or profitable replacement
sample is introduced. [HANDOFF.md](HANDOFF.md) derives every profile.

Private verification passes 29 Python methods and the focused `Validation.Handoff`
CTest; 98 CTests are registered overall. Nonzero synthetic buy/sell fills, rebate/fee
accounts, future-information/intent mutations, missing/altered rows, false summaries,
projection/anchor changes, failed child processes and protected-input mutation are
checked. Review also found and fixed a dangling-symlink freshness defect; both report
and output controls now reject it before creating the target. Full main-loop synthetic
controls mock Git clean/anchor witnesses, whose guards have separate tests; the
production runner has no bypass.

The simulator binary digest equals the earlier Gate 4 Release binary; the relevant
kernel source hashes remain unchanged. No additional C++ sanitizer or performance run
is claimed. The raw day was not reopened: its hash and independent BBO comparison are
anchored to the committed earlier evidence, while small projection files are rehashed.
This establishes the bounded handoff and stated model's consistency, not empirical
execution probabilities, parent aggressor volume, counterfactual response or strategy
P&L. The two windows were selected retrospectively.

## Independent displayed-order and FIFO baseline

Clean source commit `acd2f29d483b688dd5ece18202dfbb9cadf6291f` adds a strict per-order
comparator and contract. Private wrappers use the unchanged local book and pinned
itchbook source. At all fifteen selected MSFT/QQQ source points, every displayed
reference, price, remaining quantity and per-level FIFO rank agrees exactly:
16,886 ordered row instances across 5,665 level instances. Both order CSVs are
434,409 bytes with the same SHA-256. These are repeated states, not distinct day-wide
orders. [The contract](L3_VALIDATION.md) records per-symbol coverage and limitations.

Each wrapper replays 7,993,582 frames / 273,665,559 prefix bytes. Full raw-file and
prefix SHA-256 identities are freshly verified before and after; the canonical raw
digest matches the earlier records. The complete selected-symbol displayed depth is
exported, with totals reconciling to level/book state. The local validation scope is
all symbols in the prefix; the reference's book scope is the selected symbols.
All 54 reference headers, build definition and licence match the pinned archive.
The [canonical aggregate](validation/2026-10-22-l3/canonical.json) retains identities,
commands, checked source boundaries and all zero discrepancy counters.

Private verification passes 30 methods in Release and focused ASan/UBSan, plus CTest
`Validation.L3Comparison`; 99 CTests are registered overall. Both wrappers match the
hand-frozen eleven-state / 49-row fixture. Three changes preserving BBO totals are
correctly rejected, alongside missing/invalid states, false totals, reference aliases,
write/close failures and nonregular inputs. Sanitiser runs cover those private tests;
canonical replay is Release, with no performance claim. LeakSanitizer is unsupported
by this Apple runtime and was disabled.

The [initial failure](validation/2026-10-22-l3/initial_failure.json) is preserved:
the private local wrapper rejected unrelated `ACEL+` by confusing requested checkpoint
names with the full feed's symbol domain. The correction also limits signed-price
restrictions to selected exports. Regressions retain warrant/class names and unsigned
unselected prices while rejecting selected prices outside the common domain. Core
book/simulator semantics did not change. The
[verification manifest](validation/2026-10-22-l3/verification.json) records both the
corrected checks and retained failed helper/source identities.

Independent retained-output review also checks all tuples, manifests, hashes and
source-point requests without reopening the raw file. Of the two inspected named
execution transitions, one targets a non-head reconstructed FIFO order. That is an
observed transition diagnostic, not a book mismatch or an inferred explanation of
exchange priority. It motivates the next identified-event contract.

## Atomic identified observer contract

Source commit `a5c99b1ed624b0c25944c1cf24ea3751c0764d69` adds a separate stdlib-only
logical observer without changing the C++ decoder, book, historical projector, journal,
queue kernel or matching engine. The [contract](IDENTIFIED_EVENTS.md) preserves original
framed fields, copied pre/post orders, named reductions, atomic replacement and explicit
attribution knowledge. It computes reconstructed rank/ahead diagnostics without turning
them into aggressive demand or hypothetical fills.

The [clean-source hand-worked evidence](validation/2026-10-22-identified/hand_worked.json)
matches two independently frozen complete ledgers: 29 facts, 31 source states and 240
order-row instances. Seven profiles compare every field of 77 probes, delivered snapshot
metadata and pending indices. Two ledger pairs and nine aggregate-report pairs are
byte-identical; all eighteen CLI processes return zero. The private driver also binds
the tiny synthetic frame files, positions and complete post-seed selected-locate list.
The module itself correctly leaves original raw input identity unverified.

Thirty-three private methods and CTest 100 pass. Checks include strict schemas/types,
all ten admitted wire variants, non-head named execution, six atomic replacements,
unknown/absent/explicit attribution, source/tie ordering, effective seed time, immutable
delivery, pending horizons, byte/count bounds, changed files, nonblocking input,
symlinks/hard links and checked close/short-write publication. Pre-commit review defects
were fixed and given regressions. The
[private seed-clock mutation](validation/2026-10-22-identified/clock_control.json)
fails three of seven frozen probes while the production source passes all seven.

The [verification manifest](validation/2026-10-22-identified/verification.json) records
fixture, generator, harness, process and final-review identities. Detailed ledgers,
frames, inventories and probe rows remain ignored. This increment does not reopen
canonical raw input or claim a new C++ sanitiser/performance run. Its next gate is an
actual bounded raw adapter bound to independently compared L3 seeds/checkpoints and
complete source coverage. Actual exchange priority and empirical fills remain unverified.

## Source-authenticated bounded identified history

Source commit `464e4a7b9f190187d931181a2f49abbf100689b9` adds the
[bounded raw producer](IDENTIFIED_HISTORY.md). Accepted Gate 5/7 reports are pinned
by historical commit, current Git blob and exact content hash. Actual raw bytes are
freshly hashed before and after, including the retained L3 prefix in each pass. The
complete 8,251,407,909-byte identity matches; framing extends through one later witness
to 7,993,583 messages / 273,665,597 bytes. The older prefix remains 273,665,559 bytes.

The [canonical aggregate](validation/2026-10-22-identified-history/canonical.json)
matches every field in thirteen source facts: seven adds, four deletes and two partial
executions. A separate parser imports neither producer nor observer and agrees on
all selected points/framed hashes, actual global seeds, seed successors, closing
witnesses and the entire scanned-prefix digest. All five changes absent from the old
fixed-level rows remain identified L3 facts. One named execution is non-head under
the reconstructed convention; no reason or hypothetical fill is inferred.

Two seeds and thirteen post-message inventories match 16,886 ordered row instances
at the same fifteen independent boundaries as Gate 7. Those external inventories
are rehashed and reused, not freshly rerun or additional historical samples. Six fixed
delay profiles match all 58 complete probes, delivery and pending fields. Each
one-millisecond profile leaves its final fact pending; longer-than-window delays leave
both seeds undelivered. Two constructions per ledger serialise identically.

Thirty-three new private methods and focused CTest 101 pass. Full-source frozen hand
fixtures and negative controls cover end-time ties, foreign seed boundaries, deep
changes, source/stock conflicts, unsupported metadata, short reads, pinned admission,
bounds, changed files and checked writes. The
[verification manifest](validation/2026-10-22-identified-history/verification.json)
retains source, fixture, harness, independent-driver and final-review identities.
Detailed source points, ledgers, inventories and coverage rows stay ignored.

The producer records fresh raw authentication separately from the logical ledger's
`unverified_by_module` declaration. There is no new external/vendor replay, C++
sanitiser or performance run, and no C++ or queue/fill-model change. Canonical
`F/C/X/U/P/Q/B` coverage, actual exchange priority and empirical fills remain unverified.

## Authenticated canonical packet replay

The [Gate 11 contract and results](CANONICAL_TRANSPORT.md#recorded-baseline) connect the
two accepted identified windows to synthetic MoldUDP64 packets. Four complete layouts
match thirty seed/post-message states and 33,772 ordered row instances against the same
fifteen retained external inventories. Nineteen canonical fault cases plus three wholly
synthetic identity/tie cases bring the matrix to 26 cases, 117 arrivals and 66 states,
with zero discrepancies. These repeated comparisons do not expand historical coverage.

All three focused groups pass Release and ASan/UBSan, including 24 producer and nine CLI
methods with no skips. Entire bundles and replay summaries repeat exactly; explicit
source joins catch an alias even when bytes and resulting inventory match. The
[aggregate evidence](validation/2026-10-22-canonical-transport/verification.json) retains
244 stable input identities and the initial recorder-output failure. Packet generation
freshly verifies small retained artefacts; it neither reopens the raw day nor reruns the
external implementation. Per-event data and private harnesses remain outside Git.

## Reviewed offline restart design and frozen expectations

Gate 12's [policy](OFFLINE_RESTART.md) and [closed oracle schema](OFFLINE_RESTART_ORACLE.md)
define an explicit restart from the original authenticated seed and complete stored
packet list, with at most two reserved attempts. They preserve the first fault and
immutable diagnostics, and require complete occurrence coverage plus a checked end
before promotion.
The [design evidence](validation/2026-10-22-offline-restart/design.json) records twelve
planned cases, 149 planned arrivals, 85 applied versus 84 returned callbacks, 42 control
probes and two admission refusals. These are normative expectations, not runtime results.

Two oracle and freeze-manifest serialisations are byte-identical. A separate independent
expectation auditor checks the complete plans and retained source/state references;
its 69 consumed input identities remained unchanged. Four altered in-memory expectation
copies are rejected at their intended semantic or type paths, covering partial callback
counts, early-end promotion, refused-admission nulls and boolean/integer confusion.
The frozen disk files remain unchanged.

That design milestone claimed no restart implementation, new C++ test or sanitiser
run, raw-day reread or external replay. Gate 13's actual runtime results are recorded
separately below.

## Verified bounded offline restart runtime

The private [Gate 13 runtime](OFFLINE_RESTART_RUNTIME.md) matches all twelve frozen
cases. Each run records 23 reserved attempts, 21 constructed and disposed generations,
nine promotions, 149 supplied arrivals, 85 applied versus 84 returned callbacks,
42 controls and two admission refusals. Complete inventory/BBO checks include seeds,
applied callbacks, arrival diagnostics, EOF and promoted values: 285 comparisons and
151,398 ordered row instances per run. These are repeated comparisons of retained
independent states, rather than new historical samples or Gate 12's metadata counts.

Two Release and two ASan/UBSan runs emit byte-identical 141,169-byte reports. All frozen
outcomes and lifetime epochs match, with at most one live generation; 241 verifier
input identities stay unchanged. The 42 public implementation files and earlier
private Gate 11 harness remain unchanged. The
[aggregate evidence](validation/2026-10-23-offline-restart-runtime/verification.json)
identifies the sources, binaries, compiler/linker flags, inputs and independent audit.

A private negative build imports the failed MSFT partial state into a fresh second
book and fails its original-seed check before that generation's first handler.
Another omits the generation ordinal from token validation and produces
`already_promoted` where the stale-token probe requires `token_mismatch`; the verifier
rejects that precise field. This demonstrates guard detection, without claiming a
successful unauthorised promotion. The
[run record](validation/2026-10-23-offline-restart-runtime/README.md) preserves the initial
legacy-metadata recorder stop and v2 build-warning cleanup. Final v3 builds and normal
runs have empty stderr; the intentional bad-seed failure has its exact diagnostic.

No raw-day or independent-reference replay, allocation-exhaustion test, live recovery,
queue/fill integration or performance measurement is added. The transport remains the
restricted `A/D/E` projection. Broader independent canonical L3 cancellation/replacement
coverage is the next acceptance target.

## Additional independently checked X/U states

The [transition record](validation/2026-10-23-l3-transitions/README.md) and
[aggregate](validation/2026-10-23-l3-transitions/verification.json) add twenty complete
MSFT/QQQ states with 22,089 matching ordered row instances and 6,840 matching level
instances. All requested states, relative FIFO, side/level totals and BBO agree.
They have no overlap with the earlier fifteen: combined coverage is 35 distinct states,
38,975 ordered row instances and 12,505 level instances. Repeated producers do not
increase the number of independent source states.

Both first-X/U searches with one-second and ten-second deadlines failed without a
qualifying MSFT X. No successful checkpoint manifest or book comparison followed either
failure. The source-only availability study found the first MSFT X 25.002318269 seconds
after Q. The separate final source-informed contract was committed before exports,
uses explicit null time fields and retains all original resource caps. Its independently
enumerated prefix has 8,300,042 frames and 284,563,784 bytes; full raw hashes before
and after comparison and the separate prefix digest pass. Both failures remain published.

Each unchanged Release producer runs twice; its CSV/JSON bytes repeat exactly, and
cross-implementation order CSVs match. All eight pipeline stages exit zero with empty
stderr and 119 run input identities remain stable. The separate
final reviewer rehashes 176 small identities and independently checks actual inventories
and six copied wire deltas without new raw reads, replay or tests. The six deltas are
two partial X cancellations and four moved-price U replacements; all four replacements
leave BBO unchanged. No full X depletion or same-price U is observed here. The new
Python controls pass 48 methods per selection profile and twelve availability methods;
these executions do not constitute that many different historical samples.

Accepted binaries are reused, with no new build or sanitised historical replay. Current
engine dependency sources are recorded separately from retained compile-time provenance.
Actual exchange priority, attribution, hidden liquidity and empirical fills remain
unverified. The legacy identified-history and transport contracts remain restricted to A/D/E.

## Frozen identified-transition admission and expectations

Gate 15's [admission contract](IDENTIFIED_TRANSITIONS.md) and
[closed oracle schema](IDENTIFIED_TRANSITIONS_ORACLE.md) were committed before freezing
expectations. They define four separate exact-source windows, atomic X/U facts,
inherited attribution knowledge, original source clocks and explicit observation
horizons. The legacy whole-timestamp history profile and transport/queue contracts
retain their existing scope.

Two fresh ignored freezes have identical oracle, manifest and four snapshot files.
A separately written auditor derives the complete expected document from the retained
independent inventories and original frames, without reading handwork outcomes or
importing the observer, historical producer or freezer. It accepts all sixteen
profiles/164 probes, including 99 expected available observations, and rejects four
altered copies at the cancellation, attribution-lineage, future-delivery and exact-type
guards. All 21 consumed identities remain stable through report publication.

The [design evidence](validation/2026-10-23-identified-transitions-design/README.md) and
[aggregate](validation/2026-10-23-identified-transitions-design/design.json) distinguish
these expectations from runtime results. The 218,428 expected captured row instances
reuse twenty Gate 14 states; distinct independent coverage remains 35. This increment
opens no raw file and executes no adapter, observer, reference book, transport or
simulator. All 42 public implementation files and 119 protected Gate 14 identities
remain unchanged.
Gate 16's separate adapter now has the actual runtime acceptance recorded below.

## Verified exact-source identified-transition runtime

The separate [adapter interface](IDENTIFIED_TRANSITIONS_RUNTIME.md) preserves the
legacy producer and unchanged logical observer. Twenty focused Python methods pass
against a hand-frozen synthetic prefix, including shared global Q seeds, same-clock
source boundaries, non-head X, populated/same-price U destinations, unknown knowledge
lineage, omitted coverage and checked publication failures. These synthetic controls
are separate from the canonical historical sample.

At clean source `8087757bdc08b8ee407abd9815c571d21be21e90`, two producer runs and two
independent verifier processes pass on their first attempt. Each run matches all
twenty retained complete inventories/22,089 ordered rows, sixteen original facts and
sixteen profiles/164 probes, including 99 available observations. The 218,428 captured
observer rows count repeated source/probe inventories. All 32 detail files repeat
exactly. Aggregate reports differ in output paths; their byte equality is not claimed.

Each producer freshly hashes the complete 8,251,407,909-byte raw file and exact
284,563,784-byte prefix before/after production, and scans exactly 8,300,042 global
frames. Its selected-source census and original framed identities match the retained
independent inputs. The independent verifier imports no implementation under test,
compares whole typed objects, and rejects two altered actual-output cases at the
inherited-attribution and future-delivery guards. All 174 recorder inputs and each
verifier's 99 consumed identities remain stable through publication. Four processes
exit zero with empty stderr; unit progress uses ordinary unittest stderr.

The [runtime record](validation/2026-10-23-identified-transitions-runtime/README.md) and
[aggregate](validation/2026-10-23-identified-transitions-runtime/verification.json)
identify sources, actual commands, identities, checks and limitations. The 42 legacy
implementation files remain unchanged; the adapter is the forty-third. This reuses
Gate 14's twenty states, so independent historical coverage remains 35 distinct states.
No new external book, C++ build/test, sanitiser, transport, queue/fill or performance
evidence is added. Synthetic populated-destination/same-price U and tied-source checks
do not create those missing categories in the canonical sample.

## Reviewed price-level search experiment

Gate 17's [source-reviewed contract](LEVEL_SEARCH.md) selects binary search within
the existing sorted vectors, retaining reverse-linear as the default. Three independent
reviews approve the same frozen bytes. The
[design record](validation/2026-10-23-level-search-design/README.md) and
[aggregate](validation/2026-10-23-level-search-design/design.json) retain inspected
implementation/harness identities and planned acceptance, without implementing,
building, testing or timing the candidate or reading raw market data anew.

The protocol fixes deep-level/API and allocation checks, eight small correctness
builds, reuse of 35 independent L3 states, eight full-day correctness replays, eight
separate streaming RSS passes and 48 paired timings. These are planned counts.
Existing fingerprints omit some directory aggregates; the contract does not upgrade
their scope. The design itself establishes no candidate runtime result.

## Executed price-level search comparison

Gate 18 implements only the reviewed compile-time search policy, preserving the
sorted vectors, pools, allocation preparation and FIFO. Eight small builds register
49 C++ methods each: 380 case instances pass and twelve expected standard-index-only
instances skip in flat builds. All 24 selected CLI group instances pass. A copied-source
deep-lookup mutant is caught after correct BBO/full visitation. Build logs retain a
GoogleTest header character-conversion warning; normal test stderr is empty.

Eighteen initial runner controls pass. A separate Python-only follow-up passes 22
controls, preserving the original eighteen method ASTs and all C++ source/binary
identities. This qualification is retained with the unchanged original unit report.
Both policies then exactly match the retained 15/20-point ordered independent exports
and typed summaries: 70 comparisons, 77,950 order-row instances, 35 distinct reused
states. No new external reference or independent historical state is claimed.

Eight full correctness replays agree at 269 Nasdaq/29 BX checkpoints per configuration:
1,192 row instances, 1,184 populated. Eight separate streaming RSS passes and 48 fresh
timing processes complete the fixed 64-child matrix. Every child exits zero with empty
stderr and accepted lifecycle/census checks; no run is discarded or retried. Complete
input hashes pass before/after both historical phases. All 44 implementation files,
tested binaries and build/protected identities remain stable. Two independent retained
reviews verify statistics, histories and provenance without replaying the input.

Binary is slower in every observed matched pair. Median paired time increases are
7.01%/5.93% on Nasdaq and 17.06%/32.45% on BX for default/fitted capacities. Fitted
Nasdaq's ranges overlap and one pair differs by only 0.068%. Reverse-linear remains
the default. These finite elapsed-time results supply no significance claim,
universal ranking, hardware-counter attribution or isolated memory estimate.

The [execution record](validation/2026-10-23-level-search/README.md),
[verification aggregate](validation/2026-10-23-level-search/verification.json) and
[full comparison](validation/2026-10-23-level-search/comparison.json) retain all
samples, commands, identities, fixed schedule, actual host and scope limitations.

## Reviewed canonical same-price replacement extension

Gate 19 reviews one missing category: a same-price U moving a non-tail order behind
an existing peer under the pinned reconstruction convention. Three independent
reviews approve the same 12,957-byte [contract](L3_SAME_PRICE_REPLACEMENT.md).
The [design record](validation/2026-10-23-same-price-design/README.md) and
[aggregate](validation/2026-10-23-same-price-design/design.json) retain fixed
source/helper identities, the limited classifier predicate, independent enumeration
and request freeze, right-censored null scope and conditional complete-state checks.

Review corrects two inherited admission limits: the local wrapper rejects same-reference
U even though the core/reference API can handle it, and the comparator still requires
a both-sided/deep/multiorder state. Any later fixed-pair failure must remain retained
without candidate substitution or comparator changes. The proposed 300–480-second
post-Q eligibility is bounded by the same 16-million-frame/512-MiB resource budget;
the retained prefix reaches only Q+468.771899246 seconds. No new raw walk, classifier,
external book, test/build or replay occurs in this design stage. All 44 feed/15 engine
implementation identities remain fixed; independent historical coverage stays 35 states.

## Independently agreed bounded same-price source classification

Gate 20 follows the frozen contract and literal expectations. Two private, separately
written models use birth/reference sets and intrusive FIFO links respectively. Both
pass 41 literal variants each plus six additional one-byte-read calls: 88 API
invocations, including fifty expected rejections. All six CLI controls pass, and a
copied stale-U-birth mutant fails at its intended two-to-one qualifier-count assertion
while leaving the first anchor and witness unchanged.

The first canonical execution also passes. Both quiet children scan exactly sixteen
million global frames/524,152,398 bytes, agree on the entire typed result and match
the independently rehashed prefix. Fresh full raw hashes pass before/after their
combined phase. QQQ has one qualifier at global 15,536,747; MSFT has none in the
scanned eligible prefix, despite one same-price U. Exactly two QQQ requests are frozen
at that anchor and its immediate foreign-symbol predecessor. Peak selected references
are 27,616; no memory-use claim follows from this state count.

The scan ends at Q+468.771899246s, leaving 11.228100754s before the eligibility upper
bound unobserved. Null is right-censored, not full-interval absence. The
[execution record](validation/2026-10-23-same-price-classification/README.md) and
[aggregate](validation/2026-10-23-same-price-classification/verification.json) retain
actual commands, source/input/fixture identities, reviews and frozen request hashes.
Original frames and named-order details remain ignored. All 44 feed/fifteen engine
implementation files stay fixed; no complete book, reference, C++ build/test or
sanitiser runs here. The two frozen requests are not validated inventories: independent
historical coverage remains 35 distinct states. Gate 21 may compare only that fixed
pair, retaining inherited wrapper/comparator refusals without reselection.

## Independently compared canonical same-price FIFO replacement

Gate 21 admits only Gate 20's committed QQQ pair. Two hand-frozen complete inventory
examples and fourteen expected refusals precede the new pure delta module; all sixteen
controls pass first time. The first canonical run then passes four unchanged helper
processes and one unchanged comparator, all quiet with zero exit status. CSV/summary
bytes repeat within each implementation. Both complete states satisfy the inherited
both-sided/deeper-level/multiorder guard. All 15,072 ordered row instances and 4,730
level instances match, with exact source manifests and typed integer-zero counters.

The whole expected post-inventory is derived once from the independent pre-state and
retained before actual comparison. All 7,536 rows match both actual post-states;
unaffected levels and relative order remain unchanged. Independent retained-output
review also derives the whole transition without importing the module and checks
all four actual post exports. The old best-bid order at rank two is replaced at the
thirteen-order level's tail; the peer moves from rank three to two. Both sides' BBO
prices, displayed sizes and order counts stay equal. First-level row sums establish
that finding; whole-side summary quantities are not BBO quantities.

Fresh complete raw and 509,933,991-byte helper-prefix hashes agree before/after the
combined phase. That endpoint is earlier than classification's capped prefix. All
214 protected input and 28 retained output identities stay fixed. Authenticated old
source manifests prove the two new boundaries disjoint from the previous 35, so
distinct independent L3 coverage is now 37; eight repeated export state instances
do not constitute eight new samples.

The [execution record](validation/2026-10-23-same-price-l3/README.md) and
[aggregate](validation/2026-10-23-same-price-l3/verification.json) retain commands,
identities, literal results, comparator counters and limitations. All 59 public
implementation identities stay unchanged, with no new C++/sanitiser or full-day book
replay. MSFT's censored null is preserved. This supplies a reconstructed FIFO case,
not exchange-calibrated priority, broader observer/queue eligibility or fill evidence.

## Frozen same-price identified-observer expectations

Gate 22's [reviewed contract](SAME_PRICE_OBSERVER.md) connects only the independently
matched QQQ PRE/POST pair to the existing logical observer. Consecutive global
boundaries and contiguous frame bytes establish one complete U interval, 871 ns
long. The foreign PRE frame remains a boundary for QQQ's imported inventory;
all seed attribution stays unknown and the replacement is atomic.

Two corrected five-file freezes repeat exactly. A separately written auditor
derives every expected state/fact/profile field from the retained independent
rows and original frame, without importing the observer or reading handwork
outcomes. All 81 consumed identities remain stable. Four altered copies are
rejected for inherited attribution, tail rank, future delivery and Boolean index.
The expected four profiles contain 17 probes/six available probes and 105,504
repeated source/returned row instances; these are not executed observer results.

The first audit refuses manifest ordering before oracle parsing: component-wise
Path sorting differs from full absolute-string ordering. The first logs/freezes
are retained. A one-line freezer correction and an auditor pin-only update precede
the successful audit; oracle bytes stay unchanged. The
[design evidence](validation/2026-10-23-same-price-observer-design/README.md) and
[aggregate](validation/2026-10-23-same-price-observer-design/design.json) keep the
failure, source identities and remaining runtime gate explicit. No raw, book,
reference, observer or performance execution occurs; all 59 public implementation
files stay fixed and independent historical coverage remains 37 states.

## Executed retained same-price observer connection

Gate 23's [runtime evidence](validation/2026-10-23-same-price-observer-runtime/README.md)
and [aggregate](validation/2026-10-23-same-price-observer-runtime/verification.json)
record 26 passing focused variants, then two actual producer/verifier pairs matching
one atomic U, both complete inventories and all four profiles/17 probes. All ten
producer files repeat exactly. Each independent verifier imports neither producer
nor observer and catches two actual-output controls: future POST disclosure and
unchanged-BBO stale FIFO, at the intended causal/full-inventory fields.

Per pair, 105,504 profile source/returned inventory rows plus 7,536 ledger seed rows
and 15,072 standalone validation rows total 128,112 repeated inventory instances.
Both runs reuse the same two states; distinct independent coverage stays at 37.
Each producer protects 74 originals; each verifier protects 95 identities. Independent
retained-result review reconciles 126 consumed identities with no findings.
Source-review corrections precede execution; no Gate 23 actual invocation fails.
All 59 public implementation files stay unchanged. No raw/hash/book/reference,
C++/sanitiser or performance run occurs; logical raw verification remains false.

Observation-horizon extension permits delivery of admitted facts and authenticates
no events beyond the exact POST boundary, including further same-timestamp messages.
O/S/Q/directory provenance does not establish continuous-trading eligibility. The
next read-only gate reviews coverage, status and action clocks before any bounded
identified queue handoff; actual priority and empirical fills remain unverified.

## Identified queue prerequisites reviewed

Gate 24's [contract](IDENTIFIED_QUEUE_PREREQUISITES.md) and
[review evidence](validation/2026-10-23-identified-queue-prerequisites/README.md)
identify two concrete gaps: the fixed-level queue input cannot preserve atomic U,
and an exact source cut after U does not close its timestamp group or admit selected
latest status. A separate small overlay is justified only after a fixed status/closure
audit passes; the existing projector's U refusal stays unchanged.

The next audit pins the already accepted 524,152,398-byte prefix and nested pair
prefix, decodes through the first later timestamp witness, then authenticates the
tail without importing future status. Fresh bounded-prefix authentication and inherited
full-file identity remain separate. Unsupported status or extra same-time selected
book mutations refuse the original case. The review executes no scanner, queue,
raw read, book/reference reconstruction, C++ check or performance experiment. All
59 implementation files and 37 distinct historical states remain unchanged.

## Identified status and timestamp closure verified

Gate 25's [execution record](validation/2026-10-23-identified-queue-status/README.md)
and [aggregate](validation/2026-10-23-identified-queue-status/verification.json)
record 56 passing focused invocations and two independently written canonical status
scans with exactly equal complete typed results. Each decodes 15,536,748 frames,
including the first later-time witness, and reads exactly 524,152,398 bytes. Both
fresh nested prefix hashes match. Full-file identity remains inherited.

U is the final global frame at its timestamp; no additional same-time message
changes the retained POST inventory. The selected QQQ A 211 ns later authenticates
closure only and is excluded from status, census and the fixed horizon. Selected
interval census is U=1 and all other types zero. Latest H/T and opening cross Q/O
pass the restricted policy; absent per-market h and retail N stay null/unknown.
The independent retained review finds no discrepancy. Pre-execution source corrections
are recorded separately from the first passing actual runs.

This adds no complete-book state, queue execution, observer run, C++/sanitiser check
or performance measurement; all 59 public implementation files and 37 distinct
historical states remain unchanged. Actual venue eligibility and empirical fills
are unverified. Next implement the finite identified shadow overlay only after
freezing concrete traces, preserving delivered knowledge and the original U horizon.

## One identified shadow queue verified

Gate 26's [execution record](validation/2026-10-23-identified-queue-runtime/README.md)
and [aggregate](validation/2026-10-23-identified-queue-runtime/verification.json)
add a pure [one-U overlay](../bench/identified_queue.py). The first forty focused
API calls pass: nine hand-frozen synthetic scenarios/61 rows and 31 intended refusals.
Then six original-pair canonical cases repeat twice with exact output bytes. The
independent verifier matches 76 trace rows and 180,864 full historical order-row
instances against accepted inventories and literal own states.

Our one-share marker stays outside the external reference namespace. Atomic U removes
old shares ahead of an already accepted marker and places its replacement behind;
an arrival after U joins behind the complete POST level. Delivered full-inventory
digests, own acknowledgement timing, pending arrivals/responses and own-only
cancellation agree. Four actual-output controls reject mixed POST payload/PRE metadata,
stale FIFO under unchanged BBO, premature own acknowledgement and a horizon extension
at their intended semantic checks. Independent retained review has no findings.

Source context preserves the new module as uncommitted at execution, with its reviewed
hash separately pinned; old 44 feed/15 engine implementations match HEAD. No raw file
is opened/statted/hashed and no C++/vendor-book replay, sanitiser or performance check
is run. The existing ledger is logically validated per call. This uses two retained
states; distinct coverage remains 37. Zero fills/account changes follow the admitted
no-execution interval and do not establish actual priority or empirical calibration.
The following public example makes the API reproducible without private data.

## Self-contained identified queue example verified

Gate 27 adds [a runnable public example](../bench/identified_queue_demo.py), using the
existing ledger builder and model with four fictional A messages and one U. It creates
189 source bytes in memory, hand supplies the consistent seed, and preserves false
raw/status/source authentication flags. The generated digest is an identifier for
fictional bytes, not an external source or session proof.

The [execution record](validation/2026-10-23-identified-queue-example/README.md) and
[aggregate](validation/2026-10-23-identified-queue-example/verification.json) retain the
first passing integration check: twenty child commands, eleven accepted report commands
covering 27 scenario instances, one help command and eight intended CLI refusals.
Complete reports match pre-implementation frozen expectations; both default outputs
are byte-identical. Only three public Python sources are copied onto the child script
path, with empty working directories and `-B -E -s`. This checks dependency isolation;
it is not an operating-system filesystem sandbox. All 87 protected inputs and 44
retained outputs stay unchanged during execution. No implementation discrepancy,
unexpected refusal, timeout or child-created file is reported.

Own lifecycle and pending events remain bounded by U at fictional time 110. There are
no fills, positions, cash changes or fees. This increment adds no independently checked
historical state, raw/reference scan, C++ replay, sanitiser run or performance measurement;
distinct historical coverage stays 37. The prior sixty implementation files are unchanged.

## Retained execution prerequisites reviewed

Gate 28's [review](IDENTIFIED_EXECUTION_PREREQUISITES.md) and
[aggregate](validation/2026-10-23-identified-execution-prerequisites/review.json)
select the earliest E among the original thirteen identified facts, without a rank
filter. QQQ's named 500-share order is reduced by 6 to 494; the other MSFT execution
reduces a rank-six order 265→69 while its 221 preceding shares remain unchanged.
These are named structural reductions; no hypothetical fill is calculated.

The original QQQ whole-timestamp seed plus A,D,A,A,E retains six independently checked
inventories/2,784 structural row instances. All six quotes remain uncrossed at the
same prices. Complete selected enumeration establishes no extra selected message
at E's clock, while its exact global endpoint/witness is unmaterialised. There are
377 global frames between E and its preceding selected A; they are not adjacent.

An explicitly joined shared raw identity and complete later census supports limited
inherited QQQ production/H/cross/global-status facts over the earlier interval. Absent
h/N remains unknown. The later one-U interval, witness, adjacency and queue-admission
result do not transfer. The current one-U API remains unchanged and incompatible with E.

This is a retained-evidence review with no new raw operation, reference/book replay,
model/test execution, build, sanitiser or performance measurement. All 61 implementation
files are unchanged and distinct independent historical coverage remains 37 states.
The following design fixes that causal profile and its scoped admission.

## Execution-prefix design and hand expectations

The [five-fact contract](IDENTIFIED_EXECUTION_PROFILE.md) and
[design evidence](validation/2026-10-23-execution-prefix-design/design.json)
freeze seven configurations, 92 expected event envelopes and 13 pending entries before
any new model implementation. Complete captured inventory identities distinguish
PRE delivery at E from the current POST book. Named D/E changes update ahead references;
external executions never imply an own fill under this conservative convention.

Sixteen negative-input descriptions fix future refusal categories, with exact coherent
fixture materialisation/source review required before code. The independent oracle
audit and its altered-expectation controls assess the expectations; runtime outputs
and actual input refusals remain separate work. The existing 61 implementation files
are unchanged, no raw/reference replay or empirical fill claim is added, and distinct
historical coverage remains 37 states.

## Execution-prefix runtime

The [separate runtime record](validation/2026-10-23-execution-prefix-runtime/README.md)
and [aggregate](validation/2026-10-23-execution-prefix-runtime/verification.json)
report the first actual execution: fourteen positive calls in two identical batches,
sixteen intended refusals, 184 trace rows and 26 pending rows. The independent verifier
compares 38,976 complete ordered row instances across the fourteen calls and rejects
five altered actual-output copies at their intended semantic paths. All normal calls
pass, input/source identities remain unchanged, and the first execution is quiet.

Concrete refusal ledgers were validated and independently reviewed before this new
model was written. The old 61 implementations stay unchanged; the separate module
adds the 62nd. Named D removes 800 shares ahead and E removes six, giving 1,400→600→594.
Zero own fills are the declared conservative convention despite actual external E.
Admission inherits limited retained source/status facts; the pure module authenticates
no files or status. Six previously checked inventories add no independent samples:
coverage remains 37. No raw operation, reference/book replay, C++/sanitiser run,
performance measurement or empirical fill claim occurs in this gate.

## What remains unverified

- BBO/depth outside the tested states and a separate exchange/vendor oracle.
- Intermediate real-day queues: a final empty-book FNV hash is constant and cannot
  establish their correctness. The journal comparison agrees at 27 sampled full-state
  checkpoints; the storage comparison extends Nasdaq coverage to 269 and BX to 29,
  using common book semantics. The synthetic loopback checks intermediate touch
  states and final queues, using the same project's encoder and decoder.
- Feed recovery after network gaps and actual network captures. Historical input is
  BinaryFILE; offline synthetic MoldUDP64 admission and selected-locate repacketisation
  have separate bounded checks, without sockets or a live recovery service.
- Big-endian execution, Linux performance and hardware-counter attribution. Endian
  conversion is conditional on the host, but this run is on little-endian Apple Silicon.
- Other price-level containers and isolated index-memory attribution. The binary/linear
  search comparison preserves the same vectors. Streaming RSS covers
  the whole process and was observed once per storage configuration.
- Empirical fills and historical identified queue priority. The bounded handoff checks
  its declared model on two windows; hidden liquidity, market impact, routing, auctions,
  risk/funding constraints and an exit/liquidation model remain open. Reconstructed
  FIFO agrees at 37 distinct points; the identified observer contract passes hand-frozen
  cases, its legacy canonical connection passes two admitted windows, and the separate
  exact-source adapter passes four more using the twenty retained X/U states.
  Broader identified flow and richer queue assumptions remain separate acceptance gates.
