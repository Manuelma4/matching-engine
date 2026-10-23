# Canonical identified-transition design evidence

Gate 15 freezes admission of four independently checked MSFT/QQQ histories to the
identified observer. The [admission contract](../../IDENTIFIED_TRANSITIONS.md) and
[oracle schema](../../IDENTIFIED_TRANSITIONS_ORACLE.md) were reviewed and committed as
`ce8cdfecce18ba57937f2fdd06a7306fac1c698f` before either freezer execution. The
[aggregate record](design.json) identifies the inputs, private sources and outputs.

The design reuses Gate 14's twenty complete independent inventories and sixteen actual
`A/D/E/X/U` facts. It adds no new historical state: combined independent depth coverage
remains 35 distinct source boundaries. No new adapter, observer, book, raw-day scan,
transport, simulator or sanitiser execution occurs in this increment.

## What passed

The private freezer copies the pinned hand-derived expectations without calculating
outcomes. Two fresh ignored directories contain the same six files byte-for-byte:
the oracle, freeze manifest, freezer source, handwork and two contract snapshots.
The oracle has 123,352 bytes, SHA-256
`44b1f3cb3e0d4c7412c176a0afb52e867e43cee934979bb4d79e047c15729497`.
The manifest has 4,973 bytes, SHA-256
`a040e9a808f69057798f7028b40db988ee6c22a8f0daf976bf4c18c10b37f4d5`.

A separately written auditor derives the complete expected document from the pinned
reference CSV, complete summary, original selected frames and source clocks. It hashes
the handwork and freezer without reading handwork outcomes or importing the freezer,
observer or historical producer. All twenty full ordered inventory hashes, sixteen
copied mutation diagnostics, attribution chains and sixteen observation profiles match.
Its 21 consumed identities remain unchanged through checked report publication.

These are expected observation counts, not observer execution counts:

| Profile, across four windows | Probes | Available probes | Delivered snapshots | Pending deliveries | Captured row instances |
|---|---:|---:|---:|---:|---:|
| zero | 40 | 36 | 20 | 0 | 61,851 |
| one_ms_clipped | 36 | 18 | 6 | 14 | 57,358 |
| one_ms_complete | 64 | 45 | 20 | 0 | 77,130 |
| undelivered_seed | 24 | 0 | 0 | 20 | 22,089 |
| Total | 164 | 99 | 46 | 34 | 218,428 |

Captured rows count repeated source inventories and available probe inventories.
They do not count new samples, distinct orders or newly executed comparisons. The
complete profile explicitly permits observation until source end plus one millisecond;
it admits no additional source events and does not flush a pending queue at EOF.

Four independent in-memory altered copies are rejected after authenticating the
unchanged disk oracle:

- QQQ_X confuses 1,474 removed shares with 1,026 remaining shares.
- QQQ_U's second replacement loses inherited unknown attribution.
- A probe receives the first MSFT_U post-state one nanosecond before delivery. Its
  state and source-clock metadata agree internally, but the causal guard rejects it.
- A Boolean replaces an integer event index and fails the exact-type check.

These controls test the expectation auditor. They do not test an adapter or observer.
The 10,344-byte independent audit has SHA-256
`7b5dff99a689ee2ebcd5cccdb3597460feaf7557e975f756115482c0f90d0f02`.
A separate retained-result review and source/identity checks are linked in the aggregate.
All 42 public implementation files still match `88ff5d76daafb70726f7fb442b4954f2ff38cb98`;
all 119 protected Gate 14 artefact identities remain unchanged.

## Reproduce in the private working environment

Run from the feed repository with the fixed retained inputs and reviewed private
sources present. Each output directory must be fresh and ignored:

```bash
python3 ../itch-feed-handler-tests/freeze_identified_transitions.py \
  --output out/identified-transition-oracle-v1
python3 ../itch-feed-handler-tests/freeze_identified_transitions.py \
  --output out/identified-transition-oracle-repeat-v1
python3 ../itch-feed-handler-tests/audit_identified_transitions_oracle.py \
  --oracle out/identified-transition-oracle-v1/oracle.json \
  --output out/identified-transition-oracle-audit-v1
```

The freezer requires clean main and the committed contracts. Its manifest records
the source commit, so rerunning at a later documentation commit changes that field;
repeat runs at the same source commit must still agree. The public repository does
not include the private harness, market data or per-event expectations.

Earlier three-profile notes and a superseded scratch metadata-writer failure remain
retained. An auxiliary identity precheck initially rejected accepted empty stderr
files because it incorrectly required every artefact to have positive length; the
corrected check verifies all recorded byte counts, including zero. Neither incident
ran or failed an adapter/observer. Both successful freezes and the independent audit
exit zero with empty stderr. The aggregate identifies these retained diagnostics.

## Next acceptance gate

Gate 16 must implement the separate exact-source adapter and compare its actual
ledgers, complete inventories, diagnostics and all 164 probes with this frozen oracle.
It must freshly authenticate the full raw file and exact prefix before and after
production, enumerate the unfiltered selected-locate census, and preserve the legacy
producer's stricter timestamp-group contract. Its results need a separate runtime record.

Raw authentication and reference execution here are retained Gate 14 evidence. The
selected U destinations were empty; there are no real same-price U, full X depletion,
tied-source or raw/effective seed-gap examples. Actual exchange priority, attribution,
hidden liquidity, empirical fills and performance remain outside the evidence.
