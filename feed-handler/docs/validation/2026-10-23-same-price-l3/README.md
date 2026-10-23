# Same-price replacement: complete independent FIFO agreement

The fixed QQQ pre/post pair passes: both implementations agree on all 15,072 ordered
rows and 4,730 level instances across two complete states. A separately tested
whole-inventory delta also matches both post-states. These are two new distinct
independently checked boundaries, bringing historical L3 coverage from 35 to 37.
No discrepancy was found in the admitted pair.

The [aggregate evidence](verification.json) identifies the actual sources, input,
commands, literal controls, retained exports and reviews. The earlier
[source classification](../2026-10-23-same-price-classification/README.md) remains a
separate result. The [contract](../../L3_SAME_PRICE_REPLACEMENT.md) was frozen before
the new source walk, then candidate and request identities were committed before
these complete inventories were computed. No candidate was substituted or selected
on book agreement.

## What the canonical event demonstrates

The same-price replacement occurs at the best bid. The old order has rank two in
a thirteen-order level. Its copied immediate peer moves from rank three to rank
two, while the new reference appears at rank thirteen, the tail. Every surviving
reference keeps its quantity, price, side and relative order. Numerical ranks after
the removed order close up by one; unchanged absolute ranks would be the wrong test.

Both best bid and best ask keep the same price, aggregate displayed size and order
count. The replacement's new total equals the old remaining quantity. Thus exact
BBO agreement can coexist with a changed named-order queue. This is direct evidence
for the pinned reconstruction convention at this source event. It does not establish
actual exchange priority, hidden liquidity or hypothetical fills.

The BBO checks sum the actual first price-level rows on each side. A summary's
`bid.shares` or `ask.shares` totals the whole side across every level; using it as
a best-quote size would be a measurement error. Per-order references, actual quote
values and source frames remain in ignored local artefacts.

## Controls and execution

Before writing the new pure delta module, freeze two hand-worked complete inventories
and fourteen input refusal cases. Both positive outputs retain unrelated levels and
correctly remove old once, append the stated new total and re-rank. The refusals
cover copied fact mismatches, a non-immediate peer, reference collision/reuse,
moved price, stale birth order, malformed ranks and exact integer domains. All
sixteen cases pass on their first execution; input copies remain unchanged and the
API is quiet. Those synthetic cases create no historical state coverage.

After source review and literal checks, the first canonical execution runs exactly
four unchanged argc-five helpers, in this order: local 1, reference 1, local 2,
reference 2. Each starts at byte zero and stops after the final frozen request.
All four exit zero with empty stdout/stderr. CSV and summary bytes repeat exactly
within each implementation. All four actual order CSVs are also byte-identical;
local/reference summaries retain their intentionally different validation scopes.

One unchanged comparator process then passes its exact ten integer-zero mismatch
fields and complete traversal/manifest checks. Both states independently satisfy
the inherited same-state both-sided, deeper-level and multiorder coverage guard.
The local summary reports whole-prefix/all-symbol validation; the reference applies
the selected symbol while validating framing/timestamps globally. All seven counters
are integer zero in every export. No scope is silently widened or treated as equal
whole-feed validation.

Derive the complete expected post-inventory once from the independent reference
pre-inventory, using the admitted copied old/peer/new facts. Save it before comparing
either actual post-state. All 7,536 post rows match both local and reference results;
all 7,536 pre rows are retained, including unrelated sides and levels. A separate
retained-output auditor independently groups the pre-state, applies the one U and
compares every row of all four actual post exports, without importing the delta
module or reopening the market file.

The runner retains attempted outputs and first failures, and removes its owned
overall-success receipt after a late identity/publication failure. Pre-execution
review corrected missing comparator-field admission, execution-count placement,
failure retention of the derived post-state and output-directory overlap. These
source corrections precede the first canonical comparison execution; no outcome was discarded
or rerun to obtain agreement.

## Source boundaries and evidence counts

The exact QQQ requests remain global post-message 15,536,746 and 15,536,747.
The former is the immediate foreign-instrument predecessor, not the previous QQQ
event. The helper endpoint is byte 509,933,991, SHA-256
`47d19f447eaa60aaabc1f041c6cce28b83261358cbc0c0436052a3afb8fb9a10`.
Keep it separate from classification's later 524,152,398-byte/16-million-frame cap.
Logical dispatch stops at the request; mmap/stdio may map or prefetch further bytes.

Fresh complete 8,251,407,909-byte raw hashes and exact helper-prefix hashes agree
before/after the combined four-export/comparator/delta phase. Full raw SHA-256 remains
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
The unchanged helpers report logical extent; the coordinator computes digests in
separate identity passes. No checksum computed inside either helper is claimed.
Gate 20 hashes during source parsing. For this comparison, the contract's general
in-parse hashing sentence has this explicit timing qualification: the mandated
unchanged helpers provide no in-parser digest, and coordinator passes bind their
reported prefix instead. This is a written-protocol timing qualification, with no
observed input-identity or inventory mismatch.
This is a new bounded book replay, with complete-file identity checks; it is not
a new full-day book replay or separate full hashing around every child. All 214
protected input identities and 28 retained output identities stay fixed.

| Evidence unit | Actual count |
| --- | ---: |
| New distinct complete source states | 2 |
| Rows in one two-state export/comparison | 15,072 |
| Level instances in that export | 4,730 |
| Whole pre-inventory / whole post-inventory rows | 7,536 / 7,536 |
| Helper processes / comparator processes | 4 / 1 |
| Exported state instances, including repeats | 8 |
| Delta derivations / complete post comparisons in the runner | 1 / 2 |
| Distinct historical states after this gate | 37 |

Old fifteen- and twenty-state source manifests are authenticated and disjoint from
the new pair. Repeated exports, delta comparisons and retained-output audits do not
create additional distinct historical states. MSFT remains null in its scanned,
right-censored eligible prefix; this comparison does not classify its unobserved tail.

## Reproduction and limits

The private sibling harness retains these commands, run from the feed checkout in
fresh ignored destinations:

```text
python3 ../itch-feed-handler-tests/record_same_price_delta_units.py \
  --module-sha256 477003fe6dc5ae58d655da9aa6187c7453f6d3cd24487414f89e4c20ee9fbae6 \
  --output out/same-price-delta-unit-v1
python3 ../itch-feed-handler-tests/record_same_price_comparison.py \
  --delta-evidence out/same-price-delta-unit-v1/verification.json \
  --delta-sha256 9058bf62ea44566358a76199e2c238c80af678dae8362d2b8255c4628ed34df6 \
  --output out/same-price-comparison-v1
```

The private canonical receipt is 84,288 bytes, SHA-256
`da98ad6c5edb8fa63a7558e54bdc0d52470a6c9be5f3244b1ac29161f816d19f`.
The source, binaries, MIT itchbook revision and request hashes are retained. All
44 feed and fifteen engine implementation files remain unchanged on existing main;
no C++ build/test or sanitised replay is added. No branch/worktree is created.

This adds neither continuous whole-day FIFO validation, an exchange/vendor oracle,
attribution history, live recovery, queue/fill calibration nor performance evidence.
Reverse-linear remains the default. Next review a bounded exact-source identified
observer connection for this newly validated transition before expanding any queue
assumptions; retain the older identified-history profiles unchanged.
