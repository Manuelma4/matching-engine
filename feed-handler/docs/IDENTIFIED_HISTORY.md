# Bounded raw source to identified observations

This producer connects the [identified observer](IDENTIFIED_EVENTS.md) to the two
previously checked canonical MSFT/QQQ windows. It authenticates source bytes and
selected-message coverage, then compares every produced inventory with the retained
[independent L3 states](L3_VALIDATION.md). It introduces no own orders, accounts,
eligibility decisions, aggressive demand estimates or hypothetical fills.

## Trust and retained evidence

The command line requires a clean committed existing `main`. Both supplied evidence
files must be tracked repository files equal to their current committed Git blobs.
This canonical profile also pins the accepted evidence bytes explicitly:

| Repository path | Accepted evidence commit | SHA-256 |
|---|---|---|
| `docs/validation/2026-10-22-window/canonical.json` | `daba80ef63a6b1585b16652686cc6568898953d1` | `1fea28b743676140a4c48d1f774554554fbca4c3211db9ef892d9d1d8d0d1ad7` |
| `docs/validation/2026-10-22-l3/canonical.json` | `0248264829dca038a936ded493e64e4942a739a2` | `a4ae84974f0ce09da32af8cd6dfc91c0be0cfd7ed775abf7c5816f5f3d291811` |

Check the accepted historical blob and current blob against those same bytes. An
arbitrary newly committed `passed` report is not another accepted oracle. These are
evidence commits, distinct from the producer source commits recorded inside reports.
Require passed, correctly typed Gate 5 window and Gate 7 L3 reports, zero errors and
zero comparison differences. The L3 report's window-evidence identity must match the
supplied window report. Its before/after raw identities must agree with each other
and the window report. These checks bind the run to reviewed repository evidence;
they do not authenticate an arbitrary repository's honesty or a vendor feed.

Read explicit filenames from supplied artefact directories. Never execute commands
or follow artefact paths found inside evidence. Hash the checkpoint CSV, both ordered
exports and both complete summaries against the successful Gate 7 artefact records.
Validate both exports independently with the existing strict L3 comparison contract,
require exact agreement, and bind every manifest state to the retained checkpoint list.
Hash each original Gate 5 projection/provenance/summary against its window run record.
Validate their source lists, counts and source-to-row mappings, including rows with
`normalised_row: 0`. The earlier failed v1 L3 helper is not a successful input.

The committed anchors retain the independent implementation revision, licence, helper
and archive identities. This producer reuses the independently checked inventories;
it does not rerun the external implementation or claim a fresh vendor oracle. Fresh
small-file hashes and full raw hashes are separate from retained reference execution.

## Window and inventory binding

Derive windows from the passed window report; do not accept new symbol, interval or
price choices on this command line. There are two in the current canonical profile.
Each has symbol, locate, effective start and inclusive end. Derive the seed and every
expected subsequent SourcePoint from that window's authenticated provenance. Convert
its frame length to an exclusive end offset without changing the original fields.
The checkpoint CSV and complete L3 manifests must expose precisely this same request
set, grouped by selected symbol/locate and sorted by global source sequence.
Number windows in ascending seed-source sequence, independently of the order of
entries in an input report. The retained canonical order is QQQ then MSFT.

The first inventory is a seed at its exact post-source-frame boundary. It is never
decoded or emitted as a selected add/delete. Its raw frame may belong to another
symbol or global context. Copy every seed reference in B/S, best-price/FIFO order
from the independent reference export and mark attribution `unknown` with null MPID.
Retain the effective seed time separately. All seed orders must satisfy the stricter
observer's positive Price(4) ceiling of 2,000,000,000 and unsigned reference/share
domains; fail rather than silently discard an out-of-domain level.

For every subsequent fact, compare the complete generated inventory with the next
independently checked state. Compare side, price, per-price FIFO rank, reference and
remaining shares exactly. Do not compare allocator values or claim independent MPID
agreement: that CSV exposes no attribution. New wire attribution and inheritance are
validated by the observer's separate field contract. Matching a final inventory alone
is insufficient.

## Fresh source authentication and coverage

Open raw input as a checked regular file with nonblocking descriptors and bound
device/inode/size/time identities. Stream SHA-256 over the entire trusted-size file
before and after production. In those passes also hash exactly the retained Gate 7
prefix length. Both full and prefix digests must equal the anchored identities and
remain unchanged. Use bounded reads, checked close and actual consumed-byte counts;
do not retain the entire raw day in memory or mmap a file that might be truncated.
Record the retained L3 prefix length and fresh framing-scan length separately: the
latter extends through a closing witness and can be longer. A digest of that longer
scan, if recorded, is a new identity rather than the retained L3 prefix digest.

Independently parse BinaryFILE frames from byte zero through a valid frame with a
timestamp strictly greater than the greatest window end. Check every prefix frame's
known type/length and nondecreasing unsigned 48-bit timestamp, count its global sequence
and preserve original byte offsets. A zero-length end record, EOF or truncated frame
before the required closing witness fails this profile. The first frame after each
window end is its closing witness; validate it, but do not emit it as a fact.
An otherwise unsupported selected message after that window end can be a valid
closing witness; only its framing/header is in scope, not a selected fact.

Resolve each selected directory symbol/locate from actual raw `R` bytes before its seed.
Reject conflicting selected identity or remapping within the scanned prefix. Foreign
names and price representations must not inherit selected-symbol restrictions. A
foreign known message still counts for sequence and clock validation; a stock-bearing
selected event must retain the exact selected padded wire stock.

Freshly verify each original global seed SourcePoint against its actual frame. Preserve
the historical projector's stronger whole-timestamp rule: the seed is the last global
frame at or before the effective start, so the next global frame must have a strictly
later timestamp. This producer profile is narrower than the logical observer's generic
exact-prefix seed. A raw/effective time gap is valid only when no intervening global
frame remains at or before effective start.

Enumerate **every** selected-locate frame after that seed and through the inclusive end,
before any supported-type filter. Keep original framed bytes and SourcePoints in wire
order. An unsupported selected type fails; it cannot become a no-op or disappear.
Require this freshly enumerated list to equal the separately anchored expected list
exactly. Pass the anchored list, rather than the newly collected list, to the observer.
The list must also agree with every requested independent post-message state.

Continue through the first global timestamp strictly after each end, including foreign
frames at the final timestamp. This catches an omitted last same-time selected event;
stopping at the final expected point would make the coverage check circular. Retain
the later witness separately from ledger facts. Global framing covers only this prefix;
hashing the whole file does not turn it into a new full-day semantic replay.

Final acceptance also requires a separate private raw-frame enumerator. It imports
neither the producer, observer nor old expected-list constructor. From actual raw
bytes and the admitted window parameters it derives selected points, framed-byte
digests and seed/end witnesses before comparing them with the producer and anchored
lists. Producer-internal enumeration alone is not this independent coverage check.
Selected metadata before the seed and after its end remains prefix context; it must
not be misclassified as an unsupported in-window fact.

## Output and bounded observation

The CLI shape is:

```bash
python3 bench/identified_history.py \
  --raw data/12302019.NASDAQ_ITCH50.itch \
  --window-evidence docs/validation/2026-10-22-window/canonical.json \
  --l3-evidence docs/validation/2026-10-22-l3/canonical.json \
  --projection-dir out/window-canonical-v1 --l3-dir out/l3-canonical-v2 \
  --output out/identified-history-v1 --report out/identified-history-v1.json
```

Output directory and report must be fresh, including no dangling symlinks. Per-event
files belong in ignored storage. Use numbered window directories, never stock names
as paths. Check all publication writes/closes; a failed run must not leave a successful
aggregate report. Retain a failed aggregate and partial ignored outputs where useful,
but label them failed. Reject aliased inputs/outputs and changed source or tool files.

Each private window output contains the version-one ledger, its independently expected
source list, source/checkpoint joins and complete validation snapshots. The ledger
sets `evidence_sha256` to the accepted Gate 7 report digest and keeps
`verification: "unverified_by_module"`; the producer's aggregate separately
records fresh full-file/prefix authentication and coverage. No logical module hash
claim is silently upgraded. Serialise two ledger constructions from the same admitted
frames with canonical JSON and require byte identity; include neither wall-clock time
nor output path in ledger bytes.

Bounded delayed-observation profiles use the accepted fixed-delay model, with probes
at source/delivery ties and the inclusive horizon. Check unavailable seeds, immutable
past inventories and pending final deliveries where the chosen profiles exercise them.
Use three fixed profiles per window: delay zero, delay 1,000,000 ns, and delay
`end_ns - effective_seed_ns + 1`. Keep the observation horizon equal to the inclusive
window end. For each profile, probes are the sorted distinct union of effective seed
time, fact times, end time and delivery times that fall within that horizon. The last
profile deliberately leaves the seed undelivered; the first two retain their actual
delivery/pending outcomes rather than selecting favourable observations.
Independently calculate the probe prefix index from retained independent CSV inventories
and anchored source/effective times in the private harness; do not use inventories
returned by the production observer to create its own expectations.
Reject probes outside the horizon and delivery overflow. Do not flush pending data.

Inherited limits are 100,000 facts and probes, 1,000,000 live/seed orders and captured
source-plus-probe rows per observer run, 64 MiB logical ledger and 1 MiB aggregate
report. This producer also bounds framing to 10,000,000 messages / 512 MiB of prefix,
with a 64 GiB maximum trusted raw input and at most eight admitted windows. Small
artefact readers admit byte limits before reading/hashing, and check CSV row limits
on bounded bytes before constructing parsed rows.
Use 8 MiB per JSON artefact, 1 MiB/256 rows for checkpoints, 64 MiB/100,000 rows per
projection/provenance file and the existing L3 export limits of 128 MiB/1,000,000 rows
per export. Additionally cap combined supplied order-export rows at 1,000,000. Process
windows and observation profiles sequentially, publishing their ignored details before
releasing inventories; do not accumulate eight independent full snapshot sets in memory.
Exceeding a limit fails the whole run. The canonical profile is far below those bounds.
Pure library helpers may be checked with independently frozen synthetic bindings;
only the production orchestration may label raw identity verified after completing
its before/after checks. Provide no command-line trust bypass or test-mode flag.

## Acceptance and limitations

Independently review this producer contract before implementing the adapter. Freeze
hand-encoded source bytes, selected source lists and all intermediate inventories first.
Include a foreign/global seed, selected/foreign interleaving, deep changes invisible at
the fixed level, end-time ties followed by a later witness, unknown attribution and
raw/effective seed-time separation. Meaningful controls must detect a missing end-time
fact, dropped deep change, stale whole-group seed, unsupported selected metadata,
conflicting directory identity, framing/time anomalies, wrong raw/artefact hashes and
changed or aliased files. A foreign warrant name and full unsigned foreign price must
remain admissible when selected inventories are valid.

Then use the existing canonical windows without selecting a more favourable result.
Their retained requests comprise two seeds and thirteen mutations: seven `A`, four `D`
and two partial `E`. Five mutations were absent from the restricted fixed-level rows;
they remain full L3 facts here. Fresh scanning must establish this coverage rather than
assuming those counts. Preserve the named non-head execution and do not infer its
reason. Canonical `F/C/X/U/P/Q/B` coverage is not established by hand cases.

Publish aggregate discrepancies, source/input/anchor identities, reproducible commands,
deterministic ledger identities, independent coverage/review results and limitations.
Keep raw bytes, per-reference inventories and per-event output ignored. Reused independent
states, a bounded prefix scan and fresh full-file identity are three different claims.
None establishes actual exchange priority, full incoming demand, hidden liquidity,
market response, calibrated fills or strategy performance.

## Recorded canonical baseline

The [canonical aggregate](validation/2026-10-22-identified-history/canonical.json)
passes at clean `main` source commit `464e4a7b9f190187d931181a2f49abbf100689b9`.
The producer freshly hashes all 8,251,407,909 raw bytes before and after production;
both full digests match the earlier accepted source identity. The retained L3 prefix
is 273,665,559 bytes. Fresh framing extends through one further 38-byte frame, reaching
7,993,583 messages / 273,665,597 bytes, with a separately recorded digest. A private
enumerator using its own parser agrees on the entire scanned prefix, selected source
points/framed hashes, actual global seeds, seed successors and later end witnesses.

| Window | Facts | States including seed | Order-row instances | Profiles | Probes |
|---|---:|---:|---:|---:|---:|
| QQQ | 7 | 8 | 3,713 | 3 | 31 |
| MSFT | 6 | 7 | 13,173 | 3 | 27 |
| Total | 13 | 15 | 16,886 | 6 | 58 |

Every complete ledger field, source/state join, validation object and delayed
observation agrees with separately constructed expectations. The thirteen facts are
seven `A`, four `D` and two partial `E`; all five fixed-level exclusions are retained.
The two seed inventories and thirteen post-message inventories use the same independent
boundaries as Gate 7, rather than adding fifteen different historical samples. Seed
attribution remains unknown; new `A` attribution records wire-field absence. No
independent MPID comparison is claimed. One of two inspected named executions remains
non-head in reconstructed FIFO; this tiny retrospective sample explains no cause.

Zero-delay profiles deliver every snapshot. Each one-millisecond profile retains its
last fact pending beyond the inclusive horizon. Both deliberately longer-delay profiles
retain undelivered seeds. All 58 complete probe objects, snapshot copies, clocks,
delivery metadata and pending indices match expectations from the retained independent
inventories and anchored times. No EOF delivery flush or own-order decision is added.

Each canonical ledger is constructed twice from the same authenticated frames and
serialises identically. There is one production invocation with two ledger pairs,
followed by a separate independent raw coverage invocation; no second external L3
replay is claimed. Detailed ledgers, frames, joins, inventories and coverage points
remain ignored under `out/identified-history-canonical-v1/`.

Thirty-three new private methods and `Validation.IdentifiedHistory` pass; 101 CTests
are registered. Frozen full-source hand fixtures contain two windows, nine facts,
eleven states and six profiles. They include final-time ties, a foreign/global seed,
deep changes and a selected unsupported closing-witness type. Controls check missing
end-time/deep facts, stale seed groups, unsupported in-window metadata, directory/stock
conflicts, one-byte reads, framing/time anomalies, current/historical anchor pins,
byte/row caps, changed files and checked publication. Private outer-pipeline tests mock
only repository/evidence admission; their hashing, scanning, builds and writes use the
actual tiny source. The public CLI has no trust bypass.

The [verification manifest](validation/2026-10-22-identified-history/verification.json)
retains fixture, source, harness, independent driver, process and final-review identities.
No C++ code, matching-engine code or queue/fill model changed. No new sanitiser or
performance run is claimed. Source authentication and exact bounded observations
remain separate from actual exchange priority, incoming demand and empirical fills.
