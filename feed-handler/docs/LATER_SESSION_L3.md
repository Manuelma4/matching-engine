# Later-session displayed L3: source selection contract

This contract defines the next independent comparison. It authorises no claim that
new inventories already agree. Existing independent displayed L3/FIFO coverage is
37 distinct boundaries; the current temporal audit reuses retained summaries without
opening, statting or hashing raw data, running a book or adding a historical sample.

## The missing dimension is time coverage

The retained boundaries are concentrated near the opening. Seventeen MSFT states
range from 09:30:00.000075566 to 09:30:25.154099971; twenty QQQ states range from
09:30:00.005915318 to 09:37:25.316896167. These are the feed's nanoseconds since Eastern
midnight rendered as clock times. They are not converted to UTC or observation time.

| Offset from the recorded global Q | Distinct boundaries |
| --- | ---: |
| [0, 1 second) | 15 |
| [1, 10 seconds) | 8 |
| [10, 30 seconds) | 12 |
| [30, 300 seconds) | 0 |
| [300, 600 seconds) | 2 |
| 600 seconds or later | 0 |

Thirty-five boundaries are within the first 30 seconds after Q; the remaining two
are QQQ's same-price replacement pair about seven minutes and 25 seconds after Q.
Independent grid BBO has a different, wider time scope. Its agreement cannot fill
this gap in complete displayed depth/FIFO coverage.

## Fixed experiment, before inspecting any new book

Use the same canonical Nasdaq 2019-12-30 BinaryFILE and the same pinned independent
implementation as the existing [L3 comparison](L3_VALIDATION.md). Raw input identity
is 8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
The independent implementation remains itchbook revision
`3c646f9da182136125059243b475f7b8baa53773`, with its MIT licence and separately verified
source archive. Existing proofs are inherited here; fresh raw identity checks belong
to the future execution boundary.

Select MSFT/5291 and QQQ/6556 at two fixed feed-clock targets:

| Target | Nanoseconds since Eastern midnight | Requested symbols |
| --- | ---: | --- |
| 12:00:00 | 43,200,000,000,000 | MSFT, QQQ |
| 15:30:00 | 55,800,000,000,000 | MSFT, QQQ |

These times are chosen to extend temporal coverage, without viewing their inventories,
BBO, size, FIFO or agreement. No successful case may replace a failed or empty one.
The intended output is exactly four requested states, not four already validated
states. Do not choose a convenient last selected mutation independently for each symbol.
Both symbols share the same global cut at each target.

## Inclusive whole-timestamp cut and first-greater witness

For target T, select the last global frame whose timestamp is **at most T**. A complete
first subsequent frame with timestamp **strictly greater than T** closes that cut.
Retain both exact frame identities and their source coordinates privately. The witness
is not applied to the exported state. If there are no frames at T, the last earlier
frame remains the cut; do not fabricate a frame timestamp of T.

All global timestamps through the latest witness must be nondecreasing. Equal-time
frames stay in wire order, including foreign instruments and non-book messages. The
cut can therefore be a foreign frame. Complete global enumeration, not selected-symbol
adjacency, establishes closure. No EOF or optional end record substitutes for a
first-greater witness. The two target cuts must be distinct and increasing; otherwise
refuse this four-state experiment without adjusting either target.

This differs from the existing [BBO grid clock](BBO_VALIDATION.md), which emits before
an update timestamped exactly at the grid. Here all frames equal to T are included.
Do not compare those two conventions as if they named the same instant's book.

## Reuse the unchanged post-message export interface

After two independently written source-only enumerators agree, freeze one request CSV
before either book exporter runs. It has exactly this existing nine-column header:

```text
state_id,symbol,locate,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type
```

Rows are ordered by global source sequence, then symbol: noon MSFT, noon QQQ, 15:30
MSFT, 15:30 QQQ, with consecutive state IDs 1–4. The source fields identify the actual
last frame at or before T, rather than the target or witness. Tied requests for different
symbols have identical source fields; duplicate symbol/source requests are forbidden.

Both existing helpers export the selected symbol after the exact global requested
frame. Neither requires that frame's locate to equal the selected symbol's locate.
Each selected directory must have appeared with the expected mapping before the cut.
Local reconstruction validates the complete prefix across symbols; the independent
reference reconstructs selected symbols and checks global framing/timestamps. Preserve
those different validation scopes and require their own reported counters to be zero.

Compare every displayed order/reference/share, price level and per-price FIFO rank
using the existing strict comparator. Run local/reference once, then repeat each once;
compare complete ordered CSVs and per-implementation summaries for byte equality.
Do not expect the two differently scoped summary files to be byte-identical to each
other. Explicit empty sides/states remain comparable and must be reported. The unchanged
comparator also requires at least one same state that is both-sided, deeper-level
and multiorder. An all-empty or shallow-only result is therefore a coverage failure
even if all supplied tuples agree; do not remove that guard or add convenient requests.
The parent must match each helper's entire state identity list to all four frozen
requests: agreement between two incomplete manifests cannot establish completeness.
New states increase independent coverage only after actual complete comparison passes.

## Finite resource envelope

All sizes below are binary units. Budgets are refusal limits, not performance claims.
Use sequential children; do not overlap expensive hash, scan, export or build work.

| Resource | Maximum / policy |
| --- | --- |
| Source input | The identified 8,251,407,909-byte file; no download or second raw copy |
| Global enumeration | 268,744,780 frames and no byte beyond the identified file |
| Source-only enumerators | Two independent implementations; no book/project imports |
| Request CSV | Four rows, at most 128 KiB |
| Complete order exports | Existing total limit of 1,000,000 rows per helper process |
| Individual CSV / summary | 128 MiB / 8 MiB |
| Selector metadata / comparison report | 8 MiB each |
| Child stdout and stderr | 1 MiB each; excess is a retained failure |
| Total new retained output | 1 GiB; require at least 2 GiB free before execution |
| Selector / exporter child wall time | 600 seconds each |
| Comparator / full-file hash pass wall time | 120 / 180 seconds each |
| Whole execution phase | 60 minutes; child limits do not extend the phase deadline |
| Resident-memory stop threshold | 12 GiB per active child, sampled at most 250 ms apart |

The memory threshold is a sampled stop policy, not an exact bound on instantaneous
peak RSS. Record sampling/termination delays and stop if metrics cannot be obtained.
The local helper maps the full raw file, so a small address-space limit would reject
its mapping rather than measure resident use. Validate watchdog/output-limit handling
on synthetic children before canonical execution; do not silently omit unsupported
guards. Keep failed outputs/logs within the same budget and report truncation explicitly.

Fresh full-file SHA-256 before and after the combined execution must match the fixed
identity. Keep separate hashes for each helper's consumed prefix and the longer
selector prefix through the first-greater witness. A helper's consumed prefix ends
at the cut, not the witness. Do not relabel this as replay of the complete day.

## Acceptance, refusals and preserved limits

Before any selector implementation, materialise and independently review synthetic
inputs with hand-stated cut/witness/request expectations. Cover exact-time ties,
no exact-time frame, a foreign final frame, shared cuts across the two symbols,
distinct target cuts, missing predecessor/witness, EOF/end before closure, a regressing
clock, malformed length/type, conflicting selected directory, duplicate target cuts,
frame/byte caps and output/watchdog failures. Input descriptions alone are insufficient.
Neither future enumerator may generate its own oracle.

Canonical enumeration must agree exactly on the fixed targets, both global cuts,
the four requested symbol/source identities, witnesses, directory identities and
scanned byte extent before requests are frozen. The coordinator separately binds the
shared full-file and consumed-prefix SHA-256 identities; no in-helper or independent
hash implementation is implied. Protect exact inputs, source/binary/build provenance and all outputs;
use fresh ignored destinations and preserve the first attempted failure. Existing
helper binaries may be reused only with authenticated source/build/previous-check
provenance; do not infer their identity from filenames or rebuild to hide a mismatch.

The common export domain is price 1..2,147,483,647, positive uint64 references and
positive uint32 shares. Existing helper policies are not silently widened. For example,
the local helper rejects old_ref == new_ref U even in an unrelated instrument, while
the reference has a different acceptance scope. Retain such a later-prefix domain
failure rather than filtering its source or changing the helper to obtain agreement.

A bound, anomaly, missing witness/directory, source disagreement, coverage failure or
incomplete export fails the phase. Empty comparable states are an explicit outcome, with no reselection.
Agreement at four new source points establishes sampled displayed reconstruction,
not every-event correctness, actual exchange priority, a separate vendor feed or
empirical fills. It grants no queue, strategy or session-status admission. Keep the
existing finite causal models unchanged.

The current contract and temporal audit run no scanner/exporter/comparator, read no
raw bytes and add zero historical states. The next gate must first pass its concrete
synthetic fixtures and independent source reviews, then perform the bounded source
selection. Book exports follow only after the agreed requests are frozen.
