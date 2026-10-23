# Authenticated canonical repacketisation profile v1

This Gate 11 contract precedes implementation. It connects the accepted canonical
identified windows to the existing offline MoldUDP64 receiver. It changes neither
that receiver nor the order book, queue model or fill assumptions.

## Scope and trust chain

The input is a selected-locate projection: QQQ's seven and MSFT's six admitted `A/D/E`
facts, following two imported complete seed inventories. Other global frames are absent.
Synthetic consecutive transport ordinals must therefore differ from original global
source sequence numbers. Packets are newly constructed for this experiment, rather
than captured Nasdaq datagrams or a reconstruction of the original packet boundaries.
A synthetic end marker closes this finite projected stream with resting orders; it
is not ITCH system event `C` or completion of the original day/session.

Authenticate these fixed versioned anchors against both their accepted historical Git
blobs and current clean `main` files/HEAD blobs:

| Anchor | Accepted evidence commit | SHA-256 |
| --- | --- | --- |
| Gate 9 `docs/validation/2026-10-22-identified-history/canonical.json` | `456ad39f4e683309afd05661c0c6f1d6f058229b` | `b7e29cf063fba8aff5d0494e872fa17363ea4fde7c2d28bf210fb17100533d25` |
| Gate 7 `docs/validation/2026-10-22-l3/canonical.json` | `0248264829dca038a936ded493e64e4942a739a2` | `a4ae84974f0ce09da32af8cd6dfc91c0be0cfd7ed775abf7c5816f5f3d291811` |

Gate 9 pins the retained `producer.json` (42,575 bytes, SHA-256
`12734d2522555d8036b78bb999b19087c33aed3c5c28cc402ef8ed95bf63dc08`)
and each numbered window's `ledger.json`, `expected_sources.json` and `joins.json`.
The producer's original code commit is `464e4a7b9f190187d931181a2f49abbf100689b9`;
that differs from the evidence commit. Check required pass/schema/coverage fields,
source identity and identical current artefact hashes, not just a filename or pass flag.
The ledger hashes are `298b37421421f845211e800e390a80da7081078fd4370f87e72f9f6b315369e9`
and `38a34c2585436409cafaede5cb2d71af804ecca3d6a613cea18f7a13712ed03e`.

Freshly hash the retained Gate 7 checkpoints, reference orders and reference summary
against the accepted identities. Reference orders have 434,409 bytes and SHA-256
`775f99545d84f47d7031bb8f245176ab81ccdaf8aa44d5f16f80499229c74e2b`.
Use their fifteen state IDs and complete ordered inventories as independent expectations.
They came from the pinned MIT reference implementation at
`3c646f9da182136125059243b475f7b8baa53773`; it is not rerun here. Do not construct an
expected order state from the new packet producer or C++ consumer's output.

Fresh verification applies to these small retained artefacts and the new packet replay.
Set `raw_full_identity_freshly_verified: false` and `independent_reference_replayed: false`.
Retain Gate 9's recorded raw/prefix hashes and original verification provenance without
upgrading them to a new raw check. No `--raw` input or raw scanner is part of this stage.
The five earlier fixed-level exclusions remain among the thirteen selected facts.

## Original occurrences and imported seeds

An original occurrence is `(window_id, event_index, SourcePoint)`, with event zero the
imported seed and positive event indices the consecutive selected facts. SourcePoint
has exactly `sequence`, `frame_offset`, `frame_end_offset`, `timestamp_ns`, `type` and
`body_bytes`. Verify equality across ledger, expected-source list, joins and retained
independent checkpoint boundaries. Preserve actual global gaps, source order and the
seed's effective time separately from its original raw timestamp.

Each fact retains the original two-byte BinaryFILE length prefix and body. Check exact
framed SHA-256, declared length/type, header timestamp/locate and accepted `A/D/E` type.
Strip only the original two-byte prefix when constructing a Mold block. Message bytes,
reference numbers, timestamps or hashes cannot independently identify an occurrence.
No body-to-source lookup is permitted. Synthetic tests must include identical bodies
at distinct source points and equal event times, without claiming historical tie coverage.

Import the seed directly into `L3Book` in best-price order and FIFO order within each
level. Do not manufacture historical add/directory messages to seed `BookBuilder` or
claim that its lifecycle counters have been reconstructed. Seed attribution remains
explicitly `unknown`; raw `A` attribution remains absent in the wire. The book comparison
covers the reference, side, price, remaining quantity and reconstructed FIFO rank, rather
than hidden exchange priority or independently observed MPIDs.

## Deterministic bundle

The public Python producer writes only a fresh ignored directory under repository
`out/`, with no public per-event report. It takes the retained history and L3 directories,
authenticates them and constructs each bundle twice, requiring byte identity. It exposes
no trust-bypass switch. Inputs/tool/source identities must remain unchanged through
checked publication. The root `manifest.json` contains bounded aggregate provenance,
counts and relative file identities, distinguishing retained identity from fresh checks.

There are exactly two numbered `window-001`/`window-002` directories. Each contains:

- `window.csv`: one configuration row, including window ID, symbol, locate, effective/end
  times, synthetic ten-byte session, artificial initial next, raw identity declarations
  and retained evidence digest. No file paths come from this row.
- `seed.csv`: `side,price4,fifo_rank,reference,shares,attribution_status`, ordered best
  price first and FIFO within a level. There are 463 and 1,881 imported orders.
- `sources.csv`: event index, origin kind, all six SourcePoint fields, original framed
  hex and framed SHA-256. Seed row zero is `imported_seed` with no original frame bytes;
  fact rows are `retained_fact`. Seed frame hex and framed digest are both empty,
  rather than a digest of an empty string. An empty seed frame is never a transport body.
- `single/packets.csv` and `batched/packets.csv`: zero-based packet index and full
  datagram hex in supplied arrival order.
- `single/occurrences.csv` and `batched/occurrences.csv`: explicit packet/message index,
  transport sequence, zero-based body offset, event index, complete original SourcePoint,
  framed SHA-256 and body SHA-256. Every ordinary block has one join and controls have none.

All CSVs use exact fixed headers, canonical decimal integers, lowercase hex, unquoted
ASCII fields and LF endings. The implementation must freeze exact headers/API before
independent fixtures are serialised or the producer/consumer is executed.

Synthetic sessions are ASCII `QH00000001` and `QH00000002`. Initial next is
`0x1122334455660000 + 256 * window_id`. Fact event `i` receives `initial_next + i - 1`.
Neither is an original Nasdaq session/sequence. Complete layouts begin with a heartbeat,
then the data packets, then a matching heartbeat, end and exact repeated end. Singles
carry one fact per packet. Fixed batch sizes are QQQ `[2,3,2]` and MSFT `[2,2,2]`.
There are no inserted receipt times or simulated network delays. A packet's bundle
index is immutable. Fault scenarios supply an arrival list of those original packet
IDs, including omissions, repetitions or reordering; they do not renumber packets,
message sequences or occurrence joins. Missing/duplicate joins refer to transmitted-slot
keys, not a repeated original occurrence. Complete layouts require exactly-once fact
coverage; the independently frozen fault arrival plan may repeat, omit or reorder
original occurrences. The complete occurrence key includes window,
layout, packet index and message index, separately from the call's arrival ordinal.

## Replay and fault boundaries

A private C++ worker loads the imported seed and uses the unchanged Mold receiver plus
a restricted selected-locate `A/D/E` adapter over the existing `L3Book` mutations.
A separate independently frozen oracle directory supplies original occurrence metadata,
configuration, seeds, event-indexed reference inventories/BBO and arrival/fault plans.
It is produced from the pinned Gate 7 exports plus authenticated retained frames, with
no new-producer imports. The worker never treats generated bundle rows as its own oracle.
Python freshly recomputes file/frame/body SHA-256; the C++ worker compares exact body
bytes and declared digest strings at explicit keys, without claiming C++ SHA recomputation.
Every admitted handler must be followed by comparison of its complete inventory and
BBO to the independently frozen reference, including intermediate states within batches.
Check the seed before first transport. Two complete layouts compare thirty states and
33,772 FIFO row instances; extra fault-prefix comparisons are counted separately.

Before calling the receiver for a packet, an outer binding preflight verifies every
ordinary block's occurrence key, source point, body bytes, sequence, index and offset
against the explicitly expected immutable bundle occurrence. The guards check an already
failed outer/receiver layer before inspecting later input and preserve the first failure.
Structural parse failures are passed to unchanged `Receiver.receive` for its normal wire
fault/attempt accounting; binding checks run only for structurally parsed packets.
A correctly bound packet
may arrive late, early or repeatedly; the Mold receiver diagnoses its sequence. Binding
checks do not turn a transport reorder into a source-identity mismatch. Missing/duplicate/extra joins,
changed frames/seed/source metadata and wrong-window joins fail before any handler for
that packet. Identity/seed/body mutations in the private fault matrix occur in memory
after authenticating the unchanged complete bundle; they are deliberate injection, not
a public hash-bypass mode. This is an outer binding failure, not a new Mold fault. It invalidates the
consumer and blocks all subsequent input; the underlying receiver's unchanged state is
only diagnostic. No source-body uniqueness assumption can substitute for these joins.
The binding layer does not compare an entire injected packet with its pristine blob.
A data header first-sequence mutation violates its assigned occurrence ordinals and is
an outer binding failure. An unchanged future packet following a loss reaches Mold's
gap check. A session-only mutation leaves occurrence binding intact and reaches Mold's
session check; control sequence faults have no source joins. Wire sequence failures
use existing Mold dispositions/faults. A later missing packet
cannot reset either failed layer. Earlier partial book state remains an invalid diagnostic
prefix; no rollback or recovery is claimed.

Independently freeze a QQQ deep-gap case: admit facts one through five, omit fact six,
then supply fact seven without renumbering. The omitted deletion changes the correct
inventory from 465 orders to 464 while BBO is unchanged. The receiver must report a gap
with zero handlers for fact seven; late fact six and end remain blocked. Also cover stale
and reordered original occurrences, changed body with valid envelope, wrong event/source
point/window/offset/hash, duplicate/missing occurrence keys and modified seed. Keep outer
admission errors distinct from expected receiver failures and checker failures. A worker pass means every independently
expected outcome matched, including deliberate failures. Seed/input admission errors,
outer binding failure, Mold dispositions/faults, consumer failure and oracle mismatch
remain distinct results. The adapter checks wire locate/time/type/length, positive
references and quantities, B/S and exact padded symbol, and price4 in 1..2,000,000,000.
D/E references must exist on the selected locate; E cannot exceed remaining shares and
executes the named reference even if non-head. Match number zero is not excluded.
False mutations or exceptions invalidate the consumer; no day statistics are claimed.

## Bounds and acceptance

Exactly two accepted windows, at most sixteen facts per window, 4,096 seed/live orders
per window, two complete layouts, at most 64 packets per layout and existing Mold limits.
Bound small JSON inputs at 8 MiB, each CSV at 8 MiB/100,000 rows and all supplied reference
rows at 100,000 combined before parsing. The reference input remains exactly its pinned
identity. Check regular files with non-blocking descriptors and stable identity, byte/row
bounds before materialisation, checked reads/closes and before/after hashes. Use only
fixed filenames and numbered output directories, reject aliased/freshness violations,
and check writes/closes before a successful manifest. Do not leave a partial success.

Acceptance requires reviewed contract before implementation, independently frozen
source/inventory/disposition oracles before execution, meaningful producer negative
controls, all expected C++ states and original occurrence joins, repeated byte-identical
bundles/replay summaries, and focused Release plus ASan/UBSan verification. Keep tests
in the private sibling harness. Version aggregate evidence and input/reference identities;
leave market data, complete inventories, datagrams and per-event diagnostics ignored.
No new canonical type coverage beyond `A/D/E`, raw coverage, network capture, recovery,
latency, throughput, order eligibility, fills or strategy performance follows.

## Frozen CSV headers

These exact unquoted ASCII/LF headers are shared with the independent fixture writer.

```text
window.csv:
schema_version,scope,window_id,symbol,locate,effective_ns,end_ns,session_hex,initial_next,raw_input_bytes,raw_input_sha256,retained_prefix_bytes,retained_prefix_sha256,history_evidence_sha256,l3_evidence_sha256,history_producer_sha256
seed.csv:
side,price4,fifo_rank,reference,shares,attribution_status
sources.csv:
window_id,event_index,origin_kind,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type,frame_hex,frame_sha256
packets.csv:
window_id,layout,packet_index,datagram_hex
occurrences.csv:
window_id,layout,packet_index,packet_message_index,transport_sequence,body_offset,event_index,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type,frame_sha256,body_sha256
```

`window.csv` has schema version1 and scope `selected_locate_projection_v1`. Original
occurrences and transmitted-copy keys have the meanings above; the private synthetic
identity/tie control has its own explicit scope and cannot pass the authenticated
canonical CLI. Freeze the separate oracle CSV headers/plan before implementation
execution; include a locally valid L3 D/A/D control with identical first/third bodies at distinct
source points and equal timestamps as a synthetic occurrence-control case. This is
not a claim about valid Nasdaq reference reuse; canonical ledger admission retains its
accepted seen-reference restrictions.

## Recorded baseline

The public producer is committed on existing `main` at
`88ff5d76daafb70726f7fb442b4954f2ff38cb98`. The receiver, book, matching engine and
queue/fill model are unchanged. The [aggregate evidence](validation/2026-10-22-canonical-transport/verification.json)
binds this source, accepted anchors, private harness, frozen oracle, binaries and logs.

| Scope | Cases | Supplied arrivals | Returned messages | Seed/post-message states | Ordered row instances |
| --- | ---: | ---: | ---: | ---: | ---: |
| Complete canonical packetisations | 4 | 35 | 26 | 30 | 33,772 |
| Canonical fault prefixes and blocked continuations | 19 | 66 | 8 | 27 | 12,509 |
| Separate synthetic identity/tie control | 3 | 16 | 6 | 9 | 5 |
| Total | 26 | 117 | 40 | 66 | 46,286 |

The original historical coverage remains thirteen facts and fifteen independently
exported states containing 16,886 ordered row instances. The table counts repeated
state comparisons across layouts/cases, including one seed per case. Controls and
blocked arrivals trigger additional state checks but are not extra returned-message
snapshots. All thirteen facts, including the five earlier fixed-level exclusions,
are retained. The observed named non-head execution keeps its original identity;
its cause and hidden exchange priority remain unknown.

Two clean-source CLI runs produce all fourteen CSVs byte-for-byte equal to an
independently frozen bundle. All fifteen output files, including the root manifest,
are identical between fresh output directories. A stdlib-only audit separately
checks all thirty-four frozen fixture identities, packet/body/source joins, external
inventories and the deep-gap control without importing the producer or worker.

The three private groups `Validation.CanonicalPacketProducer`,
`Validation.CanonicalPacketCLI` and `Validation.CanonicalTransport` pass in fresh
Release and ASan/UBSan builds. All twenty-four producer methods and nine CLI failure
methods complete by their frozen names, without skips; the latter require each
intended rejection reason. Actual callback sequence, message index, borrowed body
pointer, offset and bytes are checked before mutation. Each callback compares full
FIFO inventory and BBO against the independent oracle. Repeated worker stdout is
byte-identical within and across builds, with zero discrepancies. The recorder
retains 244 unchanged identities and confirms effective C++ compile/link sanitiser
flags, fatal runtime options and stable binaries/interpreter/source. The Python
interpreter is not sanitiser-instrumented; leak checking is not claimed.

A private worker copy weakens only the synthetic TEST symbol's exact immutable join
equality to body-hash equality. It fails exactly at the frozen occurrence-alias
arrival. The first and third deletes have identical bytes and identical resulting
empty inventories, so a book comparison alone cannot identify this substitution.
The canonical predicate remains unchanged in this control. No mutant sanitiser or
performance result is claimed.

Strict recorder v1 retained successful Release results but refused truncated JUnit
text: CTest's 1,024-byte successful-output cap hid method names and completion text.
That failure and the original recorder are preserved. Explicit 1 MiB passed/failed
output limits let fresh v2 builds retain all evidence without weakening admission.
The private v2 report has 90,132 bytes and SHA-256
`59080e7c7d7e3cd60d18aae84de8ae5e74adefc7b4b615b3df1747dec1be5504`.
Only these three focused groups run here; older full-day, queue, storage and original
transport checks remain separately recorded evidence.

## Use and repeat the check

Pure helpers accept immutable bytes or a small structural binding:

- `bind_inputs(history_blob, l3_blob, producer_blob, window_blobs, l3_blobs)` authenticates
  the accepted small artefacts and returns the two-window binding.
- `validate_binding(binding)` checks/copies a bounded structural binding. It grants no
  raw-file or repository authenticity and does not impose historical seen-reference
  policy on deliberately synthetic local L3 controls.
- `packetise(binding, window_id, layout)` returns packet and occurrence row dictionaries.
- `build_bundle(binding)` returns fixed relative CSV paths mapped to deterministic bytes,
  with no file I/O or trust grant.

The CLI has no raw-data input and no authentication bypass. From the workspace root,
on clean existing `main`, use new output directories:

```bash
python3 itch-feed-handler/bench/repacketise_history.py \
  --history-evidence itch-feed-handler/docs/validation/2026-10-22-identified-history/canonical.json \
  --l3-evidence itch-feed-handler/docs/validation/2026-10-22-l3/canonical.json \
  --history-dir itch-feed-handler/out/identified-history-canonical-v1 \
  --l3-dir itch-feed-handler/out/l3-canonical-v2 \
  --output itch-feed-handler/out/canonical-packets-repeat
canonical_source_commit=$(git -C itch-feed-handler rev-parse HEAD)
python3 itch-feed-handler-tests/verify_canonical_transport.py \
  --source-commit "$canonical_source_commit" \
  --bundle itch-feed-handler/out/canonical-packets-repeat \
  --output itch-feed-handler/out/canonical-transport-verification-fresh
```

The private harness, retained small inputs and frozen ignored oracle are prerequisites;
they are not published with the source. The verifier pins the accepted baseline manifest
and admits only its two commit fields changing after documentation-only commits: all
implementation hashes and other metadata must remain identical. `--bundle` selects the
new CLI output for CTest as well as direct repeats. Changed implementation requires a
new reviewed baseline, rather than silently reusing this profile's certification.
Choose another fresh name for subsequent runs. No branch switch or full-day read is
required. Chapter 21 of the workspace tutorial works through the identity and coverage
distinctions before any later offline recovery design.
