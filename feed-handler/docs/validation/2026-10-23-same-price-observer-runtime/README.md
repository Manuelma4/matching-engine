# Retained same-price observer runtime evidence

Gate 23 passes the [reviewed contract](../../SAME_PRICE_OBSERVER.md) against
[Gate 22's frozen target](../2026-10-23-same-price-observer-design/README.md).
Two actual producer/verifier pairs agree on one atomic QQQ replacement, two reused
complete inventories and all four profiles/17 probes. The [aggregate](verification.json)
records source/input identities, commands, controls, independent reviews and limits.

## Executed result

Twenty-six focused variants across sixteen frozen families pass before production:
one complete positive binding and twenty-five expected refusals. The pure binder
opens no files, starts no subprocesses and imports no observer within that boundary.
Copied malformed inputs have their declared FileRefs coherently rebound, so source
adjacency, coverage, inventories and quantity mutations reach semantic guards.
Immutable copied bytes and mapping behaviour, quiet calls and original-object
preservation are checked. No generic ledger or observer runs in these focused calls.

After fixed-path, source-lineage, file and semantic admission, the producer imports
only the unchanged generic structural helpers. It derives actual binding from the
original classification and independent CSV/summary, without using frozen outcomes
to produce observations. Each invocation constructs the ledger twice; all ten output
files also repeat byte for byte between the two invocations. The ledger SHA-256 is
`f8e0ffabac6729e911c7429552a919c18a303611c53d79b45782a1916f08f59e`.
Each ten-file set occupies 13,789,447 bytes; this extent is not a timing result.

The separately written verifier imports neither producer nor observer. It derives
expected complete inventories and U diagnostics from the frozen oracle and full
independent inventories, checks the original U, and compares every ordered row,
attribution, source join, probe, clock, null and pending delivery.

| Actual profile | Probes | Available | Delivered snapshots | Pending | Captured row instances |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero | 4 | 3 | 2 | 0 | 37,680 |
| one_ms_clipped | 3 | 0 | 0 | 2 | 15,072 |
| one_ms_complete | 7 | 3 | 2 | 0 | 37,680 |
| undelivered_seed | 3 | 0 | 0 | 2 | 15,072 |
| Total per pair | 17 | 6 | 4 | 4 | 105,504 |

The 105,504 rows count repeated source and returned inventories across four profiles.
The ledger seed adds 7,536 and standalone validation adds 15,072: 128,112 inventory
row instances across eight detail payloads per pair. Copied named-order diagnostics
are additional checks. These totals count neither distinct historical states nor
internal comparison-function invocations. Both runs reuse the same two states;
independent historical coverage remains **37 distinct states**.

## Deliberate actual-output errors

After authenticating original files, each verifier changes two in-memory copies:

- A delayed-seed probe receives coherent future POST metadata and contents. The
  verifier rejects `observation-one_ms_complete.probes[4].delivery_ns`, exposing
  information 871 ns before its delivery.
- POST leaves the replacement in the old FIFO position, preserving BBO. The verifier
  rejects `validation.snapshots[1].orders[1].reference` at the first displaced row.

Both controls are caught by each verifier, without changing original objects or
files. These are two controls repeated twice, distinct from Gate 22's four altered
expectation controls. Deterministic wrong output alone would not detect either error.

## Source review and retained-result review

All four child commands exit zero with empty stderr; the first focused and runtime
executions report no actual failures. Before those calls, source review corrected
verifier list/count metadata, added explicit fixed-path/ancestry admission, aligned
producer refusal labels, made the focused mutator update projected source-point
copies coherently, and strengthened recorder failure/log/late-output retention.
Earlier reviewed sources remain ignored and identified in the private review trail.
These were pre-execution corrections, not runtime discrepancies or changed outcomes.

Independent retained-result review reconciles both complete outputs against the
original independent rows and frozen clocks, all ten repeat files, focused semantic
routes, both controls per pair and 126 consumed identities. It has no findings and
runs no project module. Each producer protects 74 originals; each verifier protects
95 identities. All 44 feed/fifteen engine implementation files match current and
committed blobs. Execution is on feed main `8096f41b297163acf2fe2bbce903dc30dcd138e1`
and engine main `dbd280185a0d45f0839881caeff8d535bcd56779`.

## Recorded commands and boundaries

The private commands ran from the feed checkout; complete argv and log identities
are in the aggregate:

```bash
python3 ../itch-feed-handler-tests/test_same_price_observer.py \
  --output out/same-price-observer-focused-v1
python3 ../itch-feed-handler-tests/record_same_price_observer.py \
  --output out/same-price-observer-runtime-v1 \
  --focused out/same-price-observer-focused-v1/verification.json \
  --producer-sha bf1949d049efbc3a100a1f5d73d49d0b271d2aa702ad7987410cb815655f0624 \
  --verifier-sha 07f9c31821352fcee35a1d0a9914632b5ffe68a6ab9ff0b5cbfd7de35c3aa52a
```

Existing outputs are immutable and refused on reuse. These commands require private
scripts and original fixed admission context; a later context needs reviewed pins
and fresh paths. Full inventories, real quotes, references and frames remain ignored.

The foreign PRE boundary, complete adjacent U interval of 871 ns and inherited unknown
attribution remain intact. Raw/reference authentication comes from
[Gate 21](../2026-10-23-same-price-l3/README.md), whose unchanged helpers have separate
coordinator hashes before/after, rather than in-parser digests. Logical and
retained-input raw verification stay false. This gate runs no raw scan/hash, book or
reference reconstruction, C++ build/test, sanitiser or performance experiment.

Extending the observation horizon permits delivery of admitted facts. It authenticates
no extra source events beyond POST, including later messages at its timestamp.
Original O/S/Q/directory provenance does not prove continuous-trading eligibility.
The next gate reviews exact coverage, status, ties and decision/order clocks before
any bounded identified queue handoff. This result adds no actual exchange-priority,
hidden-liquidity, market-reaction or empirical-fill claim.
