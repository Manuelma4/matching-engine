# Running the exact-source identified-transition adapter

The [admission contract](IDENTIFIED_TRANSITIONS.md) fixes the historical scope; the
[frozen oracle](IDENTIFIED_TRANSITIONS_ORACLE.md) fixes expected observations before
implementation. This document describes Gate 16's separate adapter interface. Runtime
acceptance needs its own recorded execution and independent comparison; the Gate 15
design results do not establish that acceptance.

## Production command and trust boundary

Run from the feed repository, with the accepted retained artefacts and raw day present:

```bash
python3 bench/identified_transitions.py \
  --raw data/12302019.NASDAQ_ITCH50.itch \
  --evidence docs/validation/2026-10-23-l3-transitions/verification.json \
  --artifacts-dir out/l3-transition-verification-v3 \
  --output out/FRESH-transition-details \
  --report out/FRESH-transition-report.json
```

Use fresh ignored output paths and committed clean `main`. The aggregate report must
be outside the detail directory. Production accepts only the pinned Gate 14 public
evidence, matching both its accepted historical Git blob and the current tracked blob.
It requires the four fixed windows, sixteen facts and twenty complete independent states.
There is no command-line switch to bypass authentication or admit synthetic inputs.

The artefact directory supplies fixed filenames: `selection/selection.json`,
`selection/checkpoints.csv`, `selection/census.csv`, `local-1.orders.csv`,
`local-1.summary.json`, `reference-1.orders.csv`, `reference-1.summary.json`,
`comparison.json`, `independent-enumeration/review.json` and
`independent-deltas/review.json`. Evidence supplies their expected identities, not
executable commands or arbitrary filenames. Both complete exports and their summaries
must agree with the exact source requests. The independent reference execution is reused.

The producer freshly hashes the full raw file and exact retained prefix before and
after production, with checked descriptor/path identities. Between hashes it scans
global framing from byte zero through the exact retained end, authenticating directory,
seed and fact joins. Every selected-locate frame inside a declared source interval is
enumerated before supported-type filtering. A later same-timestamp message beyond that
interval is outside its coverage; the scanner needs no later-clock witness.

The logical observer continues to declare `verification: "unverified_by_module"` and
`raw_input_identity_verified: false`. The outer producer owns the fresh raw identity
claim. Full-file hashing verifies byte identity; semantic reconstruction here covers
only the declared source windows and imported independent seed inventories.

## Library functions

These functions support bounded structural checks and private hand fixtures. Calling
them directly does not perform the production CLI's source or raw-file authentication.

- `bind_inputs(evidence, artifact_blobs)` cross-checks immutable retained bytes and
  constructs a binding. `validate_binding(binding)` checks and copies its closed shape.
- `scan_prefix(stream, binding)` reads the exact prefix and returns original seed and
  fact frames. It preserves same-time global source order and repeated-symbol windows.
- `observation_profiles(window)` yields `(name, delay, horizon, probes)` for the four
  predeclared profiles. Seed delivery incurs the same feed delay as later facts.
- `build_window(binding, scan_window, include_observations=True, *, evidence_sha256=None)`
  builds the unchanged logical ledger twice, checks deterministic bytes and compares
  every complete ranked source inventory with the independent reference. Production
  writes each observation profile sequentially to bound retained inventory copies.

The binding contains `input_identity`, `retained_prefix`, `directories`, `system_events`
and `windows`. The prefix carries its byte count, SHA-256 and message count. Directory
and system-event records bind original sources and framed hashes. Each window carries
its ID, symbol/locate, exact effective/end clocks, seed source/hash, expected source/hash
lists and complete independent `{state_id,source,orders}` states. Seed knowledge is
unknown; an in-window A supplies absent-in-wire knowledge; U inherits its pre-order's
knowledge through replacement chains. Generic structural helpers permit small private
fixtures; production's authenticated canonical count and identity requirements remain fixed.

## Private details and aggregate report

Each `window-001` through `window-004` directory contains exactly eight files:

- `ledger.json`, `expected_sources.json`, `validation.json`, `joins.json`;
- `observation-zero.json`, `observation-one_ms_clipped.json`,
  `observation-one_ms_complete.json`, `observation-undelivered_seed.json`.

There are 32 detail files per production. Their compact sorted ASCII JSON serialisation
has one trailing newline. Full order inventories, framed facts and probe results stay
ignored. The aggregate report retains identities, exact source-coverage diagnostics,
summary counts, source provenance, before/after raw hashes and explicit limitations.
Checked publication and final source/input guards determine whether it may report success.

For independent acceptance, the private verifier reads the fixed Gate 15 oracle and
Gate 14 CSV/summary/selection, without importing the adapter or observer. It compares
complete actual ledger facts, validation states, joins, delivered metadata, pending
indices and every probe, including source clocks, attribution and null versus empty
orders. Expected outcomes come from those frozen independent inputs.

Repeat the producer and verifier in fresh paths. All 32 detail files must repeat
exactly; aggregate reports contain different output paths, so their byte equality is
not required. Compare their authenticated source/raw identities and semantic invariants.
Altered actual-output controls must first authenticate the original files, then reach
the intended attribution or future-delivery guard. They test the verifier separately
from normal observer results and from Gate 15's altered-expectation controls.

## Scope of verification

The private fixture deliberately exercises exact partial timestamp boundaries, a global
Q seed, non-chronological window IDs, repeated symbols, named non-head cancellations
and replacements into populated destinations. It supplies synthetic coverage for
cases absent from the canonical sample; it creates no new historical observation.

This Python adapter reuses the unchanged observer and compatible bounded I/O/export
helpers. It changes no C++ book, transport, queue or fill model. A Python verification
run is not a new C++ or sanitiser run. Repeated comparisons reuse twenty independent
states, keeping combined distinct historical depth coverage at 35. Actual exchange
priority, hidden liquidity, attribution recovery, empirical fills and performance
remain outside this contract.
