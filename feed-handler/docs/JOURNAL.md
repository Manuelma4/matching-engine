# Deterministic observed-wire journal, version 1

The journal preserves an observed Nasdaq BinaryFILE byte stream and makes that
observation reproducible. Replaying it sends the original messages through the same
`BookBuilder` used for raw input. The format is deliberately small: fixed-size byte
blocks, explicit byte order, checksums, source identity and a mandatory footer.

This is an observed-event journal. It does not store only accepted book changes.
Directory messages, metadata ignored by the builder, messages later rejected during
reconstruction and the optional zero-length BinaryFILE end record are all preserved.
It performs no price/quantity normalisation, message rewriting or timestamp sorting.
A valid container can therefore contain malformed ITCH: container verification and
market-protocol validation are separate responsibilities.

## Binary contract

All numeric container fields use unsigned, big-endian integers. Byte offsets below
are relative to the start of each structure. Sizes and source offsets count bytes,
rather than messages. Magic values are literal ASCII bytes with a final NUL.

The file is exactly `HEADER + (DATA header + payload)* + FOOTER`. The header is 32
bytes, each DATA header is 24 bytes and the footer is 72 bytes. At least one non-empty
DATA block is required. Every payload except the final one contains exactly
1,048,576 bytes (1 MiB); the final payload contains 1 through 1,048,576 bytes.
A full final block is legal. A short block followed by another DATA block is rejected.

### Header: 32 bytes

| Offset | Size | Field | Version 1 requirement |
|---:|---:|---|---|
| 0 | 8 | Magic | `ITCHJNL\0` |
| 8 | 2 | Version | 1 |
| 10 | 2 | Header length | 32 |
| 12 | 4 | Maximum DATA payload | 1,048,576 |
| 16 | 4 | Flags | 1: observed Nasdaq BinaryFILE / TotalView-ITCH 5.0 bytes |
| 20 | 12 | Reserved | All zero |

### DATA header: 24 bytes, followed immediately by its payload

| Offset | Size | Field | Version 1 requirement |
|---:|---:|---|---|
| 0 | 4 | Tag | `DATA` |
| 4 | 4 | Payload length | 1 through 1,048,576 |
| 8 | 8 | Source offset | Total payload bytes in all preceding blocks |
| 16 | 4 | Payload CRC-32 | Checksum of this payload only |
| 20 | 4 | Reserved | Zero |

Blocks are byte chunks, so a two-byte BinaryFILE length prefix or its message body can
cross a block boundary. The C++ reader carries incomplete frames into the next block;
it does not require record-aligned packing. Canonical fixed packing makes identical
observed bytes produce an identical journal, independent of message boundaries.

### Footer: 72 bytes

| Offset | Size | Field | Version 1 requirement |
|---:|---:|---|---|
| 0 | 8 | Magic | `ITCHEND\0` |
| 8 | 8 | Source byte count | Sum of all DATA payload lengths |
| 16 | 8 | DATA block count | Number of DATA blocks |
| 24 | 32 | Source SHA-256 | Digest of concatenated DATA payloads |
| 56 | 4 | Prefix CRC-32 | Header plus every DATA header and payload; excludes footer |
| 60 | 4 | Reserved | Zero |
| 64 | 4 | Footer CRC-32 | Checksum of footer bytes 0 through 63 |
| 68 | 4 | Reserved | Zero |

CRC-32 uses the reflected ISO-HDLC convention, matching `zlib.crc32`. No bytes may
follow the footer. Unknown versions, flags or non-zero reserved fields are rejected;
reserved space is not permission to silently reinterpret a version-1 file.

Raw ITCH payloads retain their original units: timestamps are nanoseconds since
midnight (US Eastern by feed convention; no zone is encoded); Price(4) integers
represent price × 10,000; quantities retain each
message type's wire width. The journal adds no clock conversion or currency field.
The original `R` directory messages preserve the day's locate-to-symbol mapping.

## Checksums, identity and determinism

The Python [journal utility](../bench/journal.py) verifies structure, counts, canonical
packing and CRC-32, then recomputes SHA-256 over the recovered source bytes and compares
it with the footer. It also reports a SHA-256 of the complete journal. Successful
creation independently verifies the completed file before reporting success.

The C++ [container preflight](../src/journal.cpp) checks structure and CRC-32 before
the [reader](../include/itch/journal.hpp) exposes any messages. It reads the stored
source SHA-256 but does not recompute that cryptographic digest. Consequently its JSON
always reports `source_identity_verified: false`. A digest field copied from a footer
is an assertion, not an identity check. Use the Python verifier to establish that the
stored digest matches the recovered payload, then compare it with the intended raw
source's independently recorded SHA-256 when establishing provenance.

CRC detects accidental corruption efficiently; it does not provide authentication.
SHA-256 gives a strong content identity, but an attacker able to rewrite the file can
also replace its stored digest. Neither checksum is an exchange signature.

The binary format contains no wall clock, file path, machine identifier or random
value. Repeated creation from unchanged bytes with version 1 must produce identical
journal bytes. JSON reports can contain paths; that does not affect binary determinism.
For `N` source bytes and `B = ceil(N / 1,048,576)` blocks, container size is
`N + 24 × B + 104` bytes. There is no compression in version 1.

The creator requires a non-empty regular input and a fresh output file. It detects
input identity changes during creation/verification and removes its own failed output.
A crash can leave a partial file; mandatory footer verification rejects it. This is a
completed-file format, rather than an appendable, crash-recoverable trading log.
Creation fsyncs the completed file; it supplies no per-event persistence guarantee,
recovery/repair operation or indexed random access.

## Replay and meaningful state checkpoints

`itch_journal_replay` defaults to journal input; `--raw` selects ordinary BinaryFILE
input and also permits `-` for stdin. Both paths dispatch into the same reconstruction
core in source order. Equal timestamps retain their original message ordering, which
can determine FIFO priority. Sequence numbers are not derived by sorting timestamps.

Checkpoints are written after every `--checkpoint-every N` non-empty messages
(default 10,000,000), plus the final non-empty message if it was not already sampled.
The optional empty end record contributes to record/byte counts, not message sequence.
Its presence therefore does not create an extra checkpoint.

```text
sequence,source_offset,timestamp_ns,live_orders,book_hash,state_hash
```

`source_offset` is the byte position immediately after the checkpoint's non-empty
BinaryFILE frame, including its two-byte length prefix. `timestamp_ns` is that message's
header time. These are post-message states, unlike the pre-message time-grid convention
used for [BBO comparison](BBO_VALIDATION.md).

`book_hash` fingerprints every resting order, ordered by locate, side, price and FIFO
priority. The version-1 `state_hash` additionally fingerprints directory mappings,
per-locate volume, builder lifecycle/decode counters and peak/live order totals.
Both use non-cryptographic 64-bit FNV-1a and can collide; equality is regression evidence,
not a mathematical proof. Ignored metadata is preserved by the wire identity even
though it does not change these semantic fingerprints.

Compare entire checkpoint files and relevant replay summary fields. A final empty
book has the same book hash for many different histories, and even final counters can
coincide. Intermediate checkpoints exercise non-empty state and ordering. Sampling
every ten million messages still leaves unobserved intermediate states; smaller traces
can checkpoint every message for diagnosis.

By default replay requires clean framing, recognised message lengths/types, no book
or side/locate anomalies, no records after session end, system `C` and zero final
orders. `--allow-partial` explicitly relaxes the last two requirements; it does not
permit corruption or reconstruction anomalies. Checkpoint output must be fresh and
write/close failures are fatal. A partial checkpoint file is not success evidence.

## Reproduction

Run from the repository root with fresh output paths. Creation/verification JSON is
aggregate; journal payloads and detailed checkpoints stay in ignored local storage.

```bash
mkdir -p out
python3 bench/journal.py create data/12302019.NASDAQ_ITCH50.itch \
  out/canonical-v1-a.jnl > out/canonical-v1-a.create.json
python3 bench/journal.py verify out/canonical-v1-a.jnl \
  > out/canonical-v1-a.verify.json
python3 bench/journal.py create data/12302019.NASDAQ_ITCH50.itch \
  out/canonical-v1-b.jnl > out/canonical-v1-b.create.json
cmp out/canonical-v1-a.jnl out/canonical-v1-b.jnl
cmake --build build --target itch_journal_replay -j2
./build/itch_journal_replay --raw --checkpoint-every 10000000 \
  --checkpoints out/canonical.raw.checkpoints.csv \
  data/12302019.NASDAQ_ITCH50.itch > out/canonical.raw.replay.json
./build/itch_journal_replay --checkpoint-every 10000000 \
  --checkpoints out/canonical.journal.checkpoints.csv \
  out/canonical-v1-a.jnl > out/canonical.journal.replay.json
cmp out/canonical.raw.checkpoints.csv out/canonical.journal.checkpoints.csv
```

Require successful exits and `passed: true` in all reports. The raw and journal replay
summaries intentionally differ in transport fields (`format`, `journal_blocks` and
stored `source_sha256`), while message/byte counts, lifecycle counters, checkpoint
counts and semantic fingerprints should agree. Verify the stored source digest
separately with Python; C++ success never upgrades its identity-verification flag.

The aggregate evidence harness performs both creations, all three replays, exact
checkpoint-file identity and non-empty intermediate coverage checks:

```bash
python3 bench/validate_journal.py data/12302019.NASDAQ_ITCH50.itch \
  --replay-tool build/itch_journal_replay --output out/journal-reproduction \
  --report docs/validation/journal-reproduction.json \
  --expected-sha256 5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f
```

This measures integrity and equivalence, including hashing, I/O and state walks;
it is not a performance benchmark. Chapter 12 of the workspace's `LEARNING.md`
provides a bounded, reproducible exercise exposing equal-timestamp FIFO order.

## Canonical Nasdaq evidence, 2026-10-22

The complete 2019-12-30 Nasdaq source passed at clean source commit
`f3750781ef8b34b47dba0d4194f11fcae9c2939d`. The
[aggregate report](validation/2026-10-22-journal/canonical_journal.json),
[verification links and controls](validation/2026-10-22-journal/verification.json)
and [build record](validation/2026-10-22-journal/build-info.txt) retain the evidence.

| Check | Result |
|---|---:|
| Original BinaryFILE bytes | 8,251,407,909 |
| Observed messages in each replay | 268,744,780 |
| Journal creations | 2, same size and SHA-256 |
| DATA blocks per journal | 7,870 |
| Bytes per journal | 8,251,596,893 |
| Raw and journal replays | 3, all clean and complete |
| Checkpoints per replay | 27, exact checkpoint-file SHA-256 agreement |
| Checkpoints containing resting orders | 26 |
| Maximum sampled live orders | 1,912,093 |
| Actual peak live orders | 1,924,078 |
| Final live orders | 0 |

Both journals have SHA-256
`6c623834f64a25147eb67f871726b551da97ae1a0d6d076eb02ca13f557e88f4`.
Python recovered and verified the original raw identity
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`,
matching the retained canonical validation and independent BBO input. All three
checkpoint files have SHA-256
`e3c17eeaad9e1084177a4baff00bdae6f420b55d387c8983e1b8057dcb9a86e0`.
Semantic summaries, including lifecycle counters and final state fingerprints, match.

The sampled maximum differs from the actual peak because checkpoints observe only
selected messages. The 26 populated samples address the empty-final-book false pass;
they do not establish equality after every one of the 268 million messages.

Private release checks cover 21 journal integration cases and 16 evidence-runner
cases, alongside the existing regression suite. The 21 journal cases also pass
ASan/UBSan: 20 in the focused suite, plus the maximum split-frame carry case separately.
Controls include hand-written intermediate FIFO ledgers, equal-timestamp reordering
that ends identically empty, checksum-valid incorrect SHA, corruption and truncation,
repaired outer checksums, preserved anomalous events and failed-output handling.
The complete canonical journal was checked in release; the earlier full-day sanitizer
result covers the raw replay, and is not relabelled as a full journal sanitizer run.

Version 1 supplies no network gap recovery, cross-day instrument identity, vendor
cross-check or accepted-state-change encoding. It does not make the historical market
respond to hypothetical orders, provide fills, or replace the later causal simulator.
Raw/journal replay equivalence uses the same core and establishes lossless transport
and deterministic replay; the independent BBO baseline supplies separate corroboration.
