# ITCH Feed Handler

A C++20 decoder for Nasdaq TotalView-ITCH 5.0 BinaryFILE feeds and a full-depth,
multi-instrument order book replica. The matching engine produces trades; this replica
applies the exchange's published order events without matching them again.

The library recognises all 23 message types, checks their lengths before decoding, and
shares the fixed order slab, level FIFO and open-addressing index with
[matching-engine](https://github.com/Manuelma4/matching-engine). Price levels use sorted
vectors because the feed's price range is not restricted to a narrow ladder.

Start with [the ten-minute technical walkthrough](docs/TECHNICAL_WALKTHROUGH.md)
for the data flow, evidence, measured trade-offs and remaining gaps.

## Run the queue example without market data

For a direct C++ API example, run from the **parent matching-engine repository root**:

```sh
cmake -S . -B build-combined -DCMAKE_BUILD_TYPE=Release -DME_BUILD_FEED_HANDLER=ON
cmake --build build-combined --target itch_queue_demo --parallel 2
./build-combined/feed-handler/itch_queue_demo
```

Four compiled-in synthetic events demonstrate two cancellation assumptions, separate
exchange/local accounts and a pending fill response. Read the
[hand calculation and C++ API guide](docs/QUEUE_DEMO.md) alongside its source.

### Supplementary identified-order prototype

Use Python 3 from this checkout; no build or data download is required:

```bash
python3 bench/identified_queue_demo.py
python3 bench/identified_queue_demo.py --scenario delayed-seed
```

The example generates fictional `DEMO` orders in memory and reuses the public ledger
builder and one-U shadow model. Its JSON shows nine timing/lifecycle cases, complete
observed-inventory identities, separate exchange/local state and pending events at
the inclusive horizon. All fills and account changes are zero. Generated hashes do
not establish exchange authenticity; all authentication flags remain false.
[Commands, output interpretation and verification](docs/validation/2026-10-23-identified-queue-example/README.md)
explain the scope and the first passing isolated CLI check.

For report identities, portable paths and private artefact boundaries, see
[the publication note](docs/PUBLICATION.md).

## Build

Requires CMake 3.21+, a C++20 Clang/GCC compiler, and POSIX file mapping. There are no
runtime third-party dependencies. From the repository root, enable
`ME_BUILD_FEED_HANDLER` to reuse the parent targets. For a standalone build from this
component directory, supply the parent checkout explicitly (or omit the override to
fetch the historical pinned engine):

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE="$(cd .. && pwd)"
cmake --build build -j 4
```

See [integration and historical provenance](docs/INTEGRATION.md) before running older
measurement or source-authentication protocols from the consolidated layout.

## Use

```bash
./build/itch_census day.itch
./build/itch_replay day.itch
set -o pipefail
gzip -dc day.gz | ./build/itch_replay -
./build/itch_replay --allow-partial excerpt.itch
mkdir -p out
./build/itch_snapshots --symbol MSFT --interval-ms 1000 \
  --out out/MSFT.bbo.csv --summary out/MSFT.bbo.json day.itch
./build/itch_loopback --ops 100000 --seed 42 --out out/synthetic.itch
./build/itch_bench --runs 5 day.itch
python3 bench/journal.py create day.itch out/day.jnl
python3 bench/journal.py verify out/day.jnl
./build/itch_journal_replay --checkpoints out/journal.checkpoints.csv out/day.jnl
```

Create `out/` before asking the loopback to write there. Full-day replay requires a
non-empty, well-framed feed, no reported anomalies, the system event `C`, and no orders
left at the end. `--allow-partial` waives the last two requirements for excerpts and
synthetic loopbacks, which intentionally retain resting orders. It still rejects empty,
truncated and anomalous input. The BinaryFILE zero-length end record is optional.

`itch_census` validates framing and message lengths. `itch_replay` maintains the L3 book,
reports order lifecycle counters and a final-state hash, and returns a failing exit code
when its validation criteria are not met. Reading from stdin keeps decompression outside
the C++ library. Use `pipefail` so a gzip error also fails a shell pipeline.

## Validation

The engine loopback compares best price, total quantity and order count on both sides
after every operation, then compares every resting order in queue order. This checks
the encoder, decoder and replica against a separately maintained matching book.

A reproducible full-day evidence runner checks the archive CRC, computes SHA-256 for
the compressed and decompressed inputs, runs both tools, and saves aggregate reports:

```bash
python3 bench/validate.py data/20190730.BX_ITCH_50.gz \
  --bin-dir build --output out/bx-validation \
  --source-url 'https://emi.nasdaq.com/ITCH/Nasdaq%20BX%20ITCH/20190730.BX_ITCH_50.gz'
```

The output directory must be new. A failed check produces a failing exit code and a
JSON report. Market data remains local and ignored by Git. Recorded results and the
limits of each check are in [docs/VALIDATION.md](docs/VALIDATION.md).

For the canonical Nasdaq day, compare the full-day report with the pinned census from
a separate implementation:

```bash
python3 bench/validate.py data/12302019.NASDAQ_ITCH50.gz \
  --bin-dir build --output out/nasdaq-validation \
  --source-url 'https://emi.nasdaq.com/ITCH/Nasdaq%20ITCH/12302019.NASDAQ_ITCH50.gz'
python3 bench/compare_reference.py out/nasdaq-validation/validation.json \
  docs/reference/nasdaq-2019-12-30-itchbook.json \
  --output out/nasdaq-independent-comparison.json
```

The comparison checks every message type, byte and message totals, and the reference's
published peak/final live-order counts. Its JSON separates aggregate agreement from
cryptographic input identity. The reference has no market-data input digest, and a
matching census does not independently validate prices, depth or queue priority.

The canonical 2019-12-30 run passed with 268,744,780 messages, zero reported anomalies,
a peak of 1,924,078 live orders and zero orders remaining. All 18 observed type counts
and peak/final live-order counts matched the pinned reference. The complete record is
in [docs/VALIDATION.md](docs/VALIDATION.md#canonical-nasdaq-2019-12-30).

Independent BBO reconstruction now agrees exactly for MSFT, QQQ, ALLE, AQB and MKD
at one-second intervals (306,140 rows), and for MSFT and QQQ at 100 ms intervals
(1,224,560 rows). There are no differing sampled prices or sizes. Both programs
consume SHA-256-identical decompressed input. Method, boundary controls, coverage
and commands are in [docs/BBO_VALIDATION.md](docs/BBO_VALIDATION.md). Agreement on a
time grid leaves states between samples, deeper levels and queue priority unverified.

The reference index can also be selected per build with
`-DITCH_REFERENCE_INDEX=std_unordered`, retaining the same order/level logic. The
default is `open_addressed`. Separate builds, transactional allocation-failure rules,
real-flow state checks and the repeated timing/memory protocol are described in
[docs/STORAGE.md](docs/STORAGE.md). A selectable alternative alone establishes no
performance advantage.

The completed comparison has 48 interleaved timing runs on full Nasdaq and BX days,
with matching populated checkpoints across both indices and default/fitted capacities.
Flat replay is faster in each matched profile here; standard-index construction medians
are lower. Fitting capacity reduces memory but gives a higher Nasdaq median replay time
with overlapping ranges. The [recorded results](docs/STORAGE.md#recorded-results-2026-10-22)
retain that negative result and the limits of the desktop experiment.

The separate price-level experiment now supports `-DITCH_LEVEL_SEARCH=binary`,
with `reverse_linear` retained as default. Eight focused correctness builds pass,
along with the deep-lookup negative control and the separate Python admission checks.
The [execution interface](docs/LEVEL_SEARCH_RUNTIME.md) preserves the original C++
matrix and explicitly identifies the Python-only follow-up. Both policies exactly
match the 35 retained independent L3 states. All eight full-day correctness replays,
eight separate memory passes and 48 timing runs pass. Binary is slower in all 24
matched pairs: median paired replay-time increases are 7.01%/5.93% on Nasdaq and
17.06%/32.45% on BX for default/fitted capacities. The
[executed results](docs/validation/2026-10-23-level-search/README.md) retain every
sample, fitted Nasdaq's overlapping ranges and the limits of whole-process RSS.
Reverse-linear remains the default.

Tests are maintained in the private sibling `itch-feed-handler-tests/`, including
framing, known wire bytes, queue priority, allocation failures, and command-line
regressions under AddressSanitizer and UndefinedBehaviorSanitizer.

## Causal queue simulation

`itch_queue_sim` runs a bounded synthetic trace with one passive order at one fixed
price level. It schedules market events, delayed feed observations, local decisions,
order arrivals and delayed responses separately. Optimistic/conservative cancellation
assumptions change queue position; fees, cash and positions use exact integer units.
The audit CSV records exchange state and locally known state after each event.

This is a foundation for testing causal assumptions, without hidden-liquidity modelling,
market impact or empirical fill calibration. Historical external quantity remains
separate from the hypothetical order. See the
[contract and worked example](docs/QUEUE_SIMULATOR.md) before interpreting a fill.

The foundation passes 22 private C++ cases and 22 CLI methods in Release and under
ASan/UBSan. Eleven hand-worked scenarios repeat with identical output; a deliberate
future-aware mutation fails the no-look-ahead check. The
[evidence record](docs/VALIDATION.md#bounded-synthetic-causal-queue-foundation) separates
these synthetic checks from the earlier real-data reconstruction evidence.

The separate `itch_queue_window` now exports a restricted displayed-history projection
from a complete ITCH source. It requires an eligible regular-session window with a
positive fixed best level, reconciles every selected message, preserves source offsets
and rejects unsupported priced executions or target replacements. It exports no fills.
The [historical window contract](docs/HISTORICAL_WINDOW.md) defines its mappings,
boundary/status rules and the limits of retrospective window selection.

Canonical MSFT/QQQ windows now pass complete-source validation and match all 15 checked
BBO states against the pinned independent decoder/book. An earlier pre-opening QQQ
window is rejected. The [recorded projection evidence](docs/VALIDATION.md#canonical-bounded-displayed-history-projection)
does not claim real hypothetical fills, untested windows or a separate vendor oracle.

`bench/audit_handoff.py` now binds those committed projections to 24 frozen simulator
configurations. A separate Python schedule checks all 284 processed audit events,
including immutable observations, decision/source joins and pending horizon state.
Independent hand calculations match every complete summary. All cases have zero fills;
the [handoff contract and evidence](docs/HANDOFF.md) explain the remaining live,
in-flight and locally unconfirmed orders without claiming empirical fill accuracy.

The [independent L3 comparison](docs/L3_VALIDATION.md) also matches every displayed
reference, remaining quantity, price and FIFO rank at the same fifteen source points:
16,886 ordered row instances across 5,665 level instances, with zero differences.
Both exports include complete selected-symbol depth. The comparison validates those
reconstructed states and their ordering convention; hidden priority and hypothetical
fills remain separate questions.

The [canonical X/U extension](docs/validation/2026-10-23-l3-transitions/README.md)
adds twenty new complete states, 22,089 exact ordered row instances and 6,840 level
instances, giving 35 distinct independently matched states in total. Two partial
cancellations and four moved-price replacements pass copied-state checks. All four
replacements leave BBO unchanged, demonstrating why full depth matters. Both rejected
deadline searches and the intervening source-only availability study remain retained.
Selection was informed by wire availability and frozen before its book exports.

The [identified-event observer](docs/IDENTIFIED_EVENTS.md) preserves original framed
fields, copied named-order transitions and one atomic delivery per replacement. Two
hand-frozen cases match all 29 facts, 31 source states and 77 probes across seven
observation profiles. It keeps FIFO diagnostics and attribution uncertainty explicit.
A bounded raw historical adapter must separately bind this layer to authenticated
source identity and complete selected-message coverage before richer queue experiments.

The [bounded raw producer contract](docs/IDENTIFIED_HISTORY.md) defines that connection
for the reviewed canonical windows. It pins the accepted evidence, verifies complete
raw and retained-prefix hashes, scans through later-timestamp witnesses and compares
every generated inventory with the retained independent L3 states. It preserves the
observer's explicit identity label and adds no own-order or fill model.

The canonical connection now passes all thirteen selected facts and fifteen complete
states (16,886 order-row instances), plus 58 probes across six fixed delay profiles.
A separate parser agrees on every selected frame and actual seed/end witnesses.
Full raw identity is freshly verified before/after; the independent inventories are
reused from Gate 7. Both one-millisecond profiles retain their final delivery pending.
The [recorded results](docs/IDENTIFIED_HISTORY.md#recorded-canonical-baseline) keep that
bounded evidence separate from actual exchange priority and empirical fills.

## Deterministic journal

The version-1 observed-wire journal preserves every BinaryFILE byte, including stock
directories and metadata that the book does not model. Fixed-size blocks, explicit
big-endian fields, CRC-32 checks and a mandatory SHA-256-bearing footer make the format
deterministic and detect incomplete files. Python verification recomputes the source
SHA-256; the C++ reader checks structure and CRCs before dispatch and reports the stored
digest as metadata. These are separate checks.

`itch_journal_replay --raw` replays the original BinaryFILE through the same core. Compare
its post-message checkpoints with journal replay to check intermediate order/FIFO state,
instrument mappings, volumes and lifecycle counters. The evidence runner creates two
journals and checks byte determinism plus raw/journal checkpoint equivalence:

```bash
python3 bench/validate_journal.py day.itch --replay-tool build/itch_journal_replay \
  --checkpoint-every 10000000 --output out/journal-validation
```

This is an offline observed-event container. It preserves rejected events rather than
claiming they are accepted book mutations. Schema, identity checks, ordering rules and
limits are in [docs/JOURNAL.md](docs/JOURNAL.md).

The canonical day passes: two creations produce the same journal size (8,251,596,893
bytes) and SHA-256, and raw plus both journal replays match at 27 checkpoints, 26 with resting
orders. Every replay processes all 268,744,780 messages with no anomalies. This checks
the sampled states; it leaves intervening real-day states unverified.

## Measurement limits

`itch_bench` reports framing, dispatch and replica costs separately on a mapped input.
Replay setup, final hashing and destruction are outside the timed replay section.
Prefaulting touches pages in advance; it cannot prevent subsequent OS eviction.
Streaming validation includes gzip, Python hashing and pipe I/O, so its elapsed times
are not estimates of the C++ hot-path cost. A final empty-book hash is only an end-state
check; it does not prove that every intermediate state was correct.

## Offline transport admission

`itch_mold` is a separate bounded MoldUDP64 parser and synchronous sequence gate.
It preflights complete datagrams and all application body lengths/types before dispatch,
requires an explicit session and initial sequence, and stops on gaps, stale ranges,
overlaps or session changes. Heartbeats and transport end markers remain separate from
BinaryFILE framing and ITCH lifecycle events. A downstream failure invalidates the run;
existing book mutations cannot be rolled back as a packet transaction.

The [profile, API and verification limits](docs/MOLDUDP64.md) distinguish Nasdaq protocol
fields from this deliberately restricted offline policy. No sockets, recovery requests,
reordering buffer or live gateway are included. Tests and hand-encoded per-message
fixtures remain in the private sibling harness; source/input identities and aggregate
results are versioned separately. The first synthetic baseline passes 38 unit methods
and 17 integration cases in Release and ASan/UBSan, comparing 194 returned-message states
and 518 FIFO row instances with zero discrepancies. This adds no canonical network or
live-recovery claim.

The [canonical packet connection](docs/CANONICAL_TRANSPORT.md) now authenticates two
retained QQQ/MSFT windows and binds every synthetic packet/message slot to its original
source occurrence. Both packetisations match all fifteen retained independent inventories;
four complete layouts compare thirty states and 33,772 FIFO row instances. Nineteen
canonical fault cases and a separate synthetic identity control also pass Release and
ASan/UBSan. All 33 producer/CLI methods complete, bundles and replay summaries repeat
exactly, and an occurrence-alias mutant is caught. Raw identity and external reconstruction
are inherited from accepted evidence; no original Nasdaq network capture is claimed.

Gate 12 now records a reviewed [offline restart policy](docs/OFFLINE_RESTART.md),
[oracle schema](docs/OFFLINE_RESTART_ORACLE.md) and independently checked
[frozen expectations](docs/validation/2026-10-22-offline-restart/design.json).
Its twelve planned cases describe fresh generations replaying the original authenticated
seed and packet list. The expectation audit and four changed-copy controls pass;
these remain design evidence, separate from the runtime results below.

Gate 13's private [restart runtime](docs/OFFLINE_RESTART_RUNTIME.md) now matches all
twelve cases: 21 fresh generations are constructed and disposed, with nine promotions.
Two Release and two ASan/UBSan runs produce identical reports. Each run compares 285
complete inventories and 151,398 ordered row instances from the retained states.
Precise negative controls catch partial-seed reuse and omitted generation-ordinal
validation. The [run record](docs/validation/2026-10-23-offline-restart-runtime/README.md)
and [aggregate evidence](docs/validation/2026-10-23-offline-restart-runtime/verification.json)
retain the earlier recorder/build diagnostics and the final clean run. This adds no
historical samples, live recovery, allocation-exhaustion, fill or performance claim.

Gate 15 freezes the separate [exact-source identified-transition profile](docs/IDENTIFIED_TRANSITIONS.md)
and [closed expectation schema](docs/IDENTIFIED_TRANSITIONS_ORACLE.md) for the four
independently checked X/U histories. Two six-file freezes repeat exactly; a separate
auditor derives all sixteen profiles/164 probes and rejects four altered-expectation
controls. The [design record](docs/validation/2026-10-23-identified-transitions-design/README.md)
reuses twenty independent states, with no adapter or observer execution in that design
milestone. Gate 16's actual results follow separately.

The [separate exact-source adapter](docs/IDENTIFIED_TRANSITIONS_RUNTIME.md) now passes
twenty focused Python methods and two canonical producer/verifier pairs. Per run, all
twenty retained inventories, sixteen facts and 164 probes match the frozen oracle;
all 32 detail files repeat exactly. Full raw and prefix hashes pass before and after
each producer. Two altered actual-output controls are caught by each independent
verifier. The [runtime record](docs/validation/2026-10-23-identified-transitions-runtime/README.md)
keeps these actual results separate from the design counts and synthetic fixture.
The 42 legacy implementation files, old history profile, transport and queue model
remain unchanged; the new adapter adds no independent reference replay or C++ run.

## Next steps

The [execution-prefix runtime](docs/validation/2026-10-23-execution-prefix-runtime/README.md)
now passes fourteen repeated positive calls, sixteen intended input refusals and five
altered actual-output controls. Across 184 scheduled events it preserves complete
captured information and named D/E reductions; the hypothetical marker ends behind
594 shares with zero fills under its explicit convention. Six reused inventories add
no independent samples. The technical walkthrough joins those results to the BBO,
L3, journal and storage evidence. The subsequent
[later-session comparison](docs/validation/2026-10-23-later-session-l3/README.md)
adds four independently matched MSFT/QQQ inventories at noon and 15:30: 55,105 ordered
row instances and 11,837 level instances, bringing sampled coverage to 41 distinct
states. Both C++ exporters repeat byte-for-byte under the original resource policies.
The [first attempt](docs/validation/2026-10-23-later-session-attempt/README.md) remains
preserved; its unavailable RSS measurement is still unexplained. The later success
establishes neither provider reliability nor session-status or fill admission.


- The [self-contained synthetic example](docs/validation/2026-10-23-identified-queue-example/README.md)
  now makes the verified one-U shadow model runnable without private data. The [identified queue prerequisite review](docs/IDENTIFIED_QUEUE_PREREQUISITES.md)
  and its completed status/closure audit support the bounded model below.
  The fixed-level input cannot preserve atomic U;
  keep its existing rejection. The same-price QQQ observer connection is complete. The reviewed
  [same-price U contract](docs/L3_SAME_PRICE_REPLACEMENT.md) fixes the predicate,
  source boundary and comparison. The earlier
  [design record](docs/validation/2026-10-23-same-price-design/README.md) adds no new state.
  The subsequent [bounded classification](docs/validation/2026-10-23-same-price-classification/README.md)
  now passes independently: QQQ has one qualifying same-price replacement, MSFT none
  in the right-censored prefix. The subsequent
  [complete FIFO comparison](docs/validation/2026-10-23-same-price-l3/README.md) now
  matches all 15,072 ordered rows across those two QQQ states, bringing distinct
  independent L3 coverage to 37. The old order at best-bid rank two is replaced at
  the thirteen-order level's tail while BBO price, size and count remain unchanged.
  Whole copied-prestate checks and repeated exports pass; this establishes the
  reconstructed convention at that occurrence, with no queue/fill calibration.
  Gate 22's [observer contract](docs/SAME_PRICE_OBSERVER.md) and
  [frozen design](docs/validation/2026-10-23-same-price-observer-design/README.md)
  now pass the independent expectation audit and four altered-copy controls.
  The subsequent [runtime](docs/validation/2026-10-23-same-price-observer-runtime/README.md)
  now passes 26 focused variants and two producer/verifier pairs: all full inventories,
  four profiles/17 probes and both actual-output controls match. All ten producer
  files repeat exactly. The initial design refusal remains retained; distinct
  historical coverage stays at 37, with inherited raw/reference authentication.
  Extended observation horizons establish no source coverage beyond POST or session
  eligibility. Gate 24's reviewed prerequisites now pass the
  [Gate 25 status/closure audit](docs/validation/2026-10-23-identified-queue-status/README.md):
  56 focused invocations and two independent canonical scans agree. U closes its
  timestamp; the selected A 211 ns later is only a witness. Fresh nested prefix hashes
  pass, full-file identity remains inherited and absent h/N stays unknown. The
  [Gate 26 identified shadow overlay](docs/validation/2026-10-23-identified-queue-runtime/README.md)
  now passes forty focused calls, two identical six-scenario canonical batches and
  four intended actual-output refusals. Complete inventories and delivered-payload
  digests match; exchange/local acknowledgements and pending cancellations stay separate.
  The fixed one-share, one-U model has zero fills and reuses two states; distinct
  coverage stays 37. Gate 27's public example passes twenty isolated CLI commands.
  The [retained execution prerequisite review](docs/IDENTIFIED_EXECUTION_PREREQUISITES.md)
  now fixes the earliest original QQQ E and preserves its whole-seed five-fact prefix.
  Six independent inventories match, and limited inherited QQQ status facts can be
  joined explicitly. Exact global endpoint metadata and the later one-U admission
  do not transfer. The [five-fact causal contract](docs/IDENTIFIED_EXECUTION_PROFILE.md)
  now freezes seven hand schedules before implementation. Its expectation audit is
  separate from runtime acceptance; sixteen invalid-input descriptions must first
  be materialised and reviewed.
  No new C++/vendor-book/performance run or empirical-fill claim follows.
  Preserve the [negative search result](docs/validation/2026-10-23-level-search/README.md)
  and reverse-linear default; another policy needs a concrete measured question.
- Extend reference-index measurements to other flows and consider price-level
  containers separately if a concrete cost justifies their allocation complexity.
- Extend independent full-depth/order comparison beyond the 41 selected states.
- Extend independently checked identified history beyond the current bounded profiles
  before expanding queue/fill assumptions.
  Normalisation directly from the observed-wire journal remains future work.

Design and message semantics: [docs/DESIGN.md](docs/DESIGN.md). Sources and licences:
[docs/REFERENCES.md](docs/REFERENCES.md). MIT licence: [LICENSE](LICENSE).
