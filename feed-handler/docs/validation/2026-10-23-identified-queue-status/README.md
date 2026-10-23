# Fixed-pair status and timestamp closure

Gate 25 passes for the original QQQ pair. Two independently written status parsers
produce exactly equal complete typed results. The original U closes its timestamp
group: the first later global frame is a QQQ A, 211 ns later. It is authenticated as
a closure witness and never applied to endpoint status, census, inventory or actions.
The [aggregate](verification.json) retains identities and counts; frames, named orders,
synthetic fixtures, private sources and execution receipts remain ignored.

| Actual check | Result |
| --- | --- |
| Frozen focused cases | 27 per parser: four positive, 23 intended refusals across sixteen refusal families |
| Focused invocations | 54 normal plus two positive short-read calls; all 56 pass |
| Canonical children | Two, both quiet exit 0; complete typed results agree |
| Decoded frames per child | 15,536,748, including the structurally checked witness |
| Status and census endpoint | Original U, global 15,536,747, end byte 509,933,991 |
| Additional frames at U time | Zero globally and for QQQ |
| Selected interval | One U; all other 22 type counts zero |
| Global / selected census through endpoint | 15,536,747 / 252,794 |
| Physical bytes per child | 524,152,398, with no read past that fixed prefix |
| Hash-only tail per child | 14,218,369 bytes after the decoded witness |
| New complete L3 states | Zero; retained distinct coverage stays 37 |

The common result serialises to 4,402 bytes as compact sorted-key ASCII JSON with a
final newline, SHA256 `097897bf5c8f7a1b4eb115125e5f1dcce21139fe7ec06da0916d048e51f09bed`.
The child receipts differ because they bind different scanner identities. Equality
of the common result is the comparison, rather than repeated execution of one model.
The two implementations share a reviewed schema and literal fixtures; neither imports
the other, the project's book, or a vendor reference implementation.

## Status knowledge

The production QQQ directory and ordered global O/S/Q session events rejoin retained
origins. Latest selected trading action is H/T; latest selected cross is Q/O. These
facts agree at PRE and the closed endpoint. Market-specific h states for Q, B and X
remain null, as does retail N: absence is unknown, not an invented normal announcement.
Global W and selected K counts are zero; the three global K messages concern other
instruments. The restricted model policy passes. This is not proof of actual venue,
regulatory, risk or order-entry eligibility.

The admitted endpoint remains U at 34,645,316,896,167 ns. Witness global 15,536,748
is a selected A at 34,645,316,896,378 ns. Its frame/body hashes and source point are
retained, without frame bytes or the added order. The observed empty 211 ns gap does
not extend the experiment's horizon. Beyond-horizon requests remain pending or refuse.

## Authentication and independence

Both parsers open stable, unbuffered regular descriptors of the accepted 8,251,407,909-byte
canonical file. They parse from byte zero through the first later-time witness, then
hash only. Fresh hashes from actual read bytes match both fixed prefixes:

- 509,933,991 bytes: `47d19f447eaa60aaabc1f041c6cce28b83261358cbc0c0436052a3afb8fb9a10`.
- 524,152,398 bytes: `c8e4fff1b993f8ebc5eae8c43d94e110935fa5e3d883853c3812d43e0b8f1b96`.

The full-file SHA256 and the larger prefix's sixteen-million-frame extent are inherited
identities, not fresh whole-file verification or a new decoded count. The receipt's
`semantic_bytes` is 509,934,029: its structural decode extent includes the witness;
status updates stop at 509,933,991. Across both scanners, physical reads total
1,048,304,796 bytes. No later book state is reconstructed.

Source context is feed main `f0a89bf34a99d60a11254d54cdcf93b706fae3bc` and engine main
`dbd280185a0d45f0839881caeff8d535bcd56779`; all 44 feed and fifteen engine implementation
files match their committed bytes. The frozen [prerequisite contract](../../IDENTIFIED_QUEUE_PREREQUISITES.md)
is unchanged. Gate 21's independent complete inventories and Gate 23's observer results
are retained prerequisites; neither book nor observer is rerun here.

## Execution and review

The 27 hand-frozen cases cover source/frame/hash identity, directory and session
admission, latest status and market separation, complete timestamp groups, witness
isolation, short reads, exact inclusive bounds and intended refusals. Each parser
passes all cases plus one seven-byte short-read call: ten accepted positives and
46 intended refusals in total. An intended refusal is a passing negative test.
The focused runner protects 107 identities and enforces quiet pure API calls and
file/process/network/project-import/mutation tripwires. Positive result equality is
recorded by the reviewed runner; full actual synthetic objects are not separately saved.

Source review corrected directory/coverage ordering, immutable-identity versus read-cap
comparison, descriptor-bound output readback, first-failure preservation and child-row
retention before execution. The final sources and approvals are pinned. The first
actual focused run and the first two-child canonical run pass, with no failed pipeline
execution. Each canonical child and its parent protect 76 identities. The independent
retained-result review authenticates 132 unique small-file identities without a third
raw scan; it has no findings. Recorder, reviewer and publisher do not open market data.

The original private commands, exact interpreter, arguments, output paths and zero-byte
logs are retained in the aggregate. From the recorded clean source context, the calls
were:

```sh
python3 ../itch-feed-handler-tests/test_queue_status_audit.py \
  --output out/identified-queue-status-focused-v1
python3 ../itch-feed-handler-tests/record_queue_status_audit.py \
  --focused-evidence out/identified-queue-status-focused-v1/verification.json \
  --focused-sha256 e86f214999991534b546e8115d588241ac2061c04ea736c21c69ff7e516107b6 \
  --output out/identified-queue-status-canonical-v1
```

These abbreviated paths assume the feed checkout as working directory. Private source
and evidence availability are required. Existing output directories are refused;
later source contexts require reviewed pins and fresh paths. Do not rerun a historical
scan simply to verify publication metadata.

## Next bounded implementation

The audit passes source/status prerequisites; `queue_admitted` remains false because
no identified shadow queue has yet run. Gate 26 must freeze concrete hand-worked traces
before implementing a one-share marker outside the historical reference namespace.
Preserve atomic U, complete independent inventories, delivered-only decisions, own
acknowledgements and an inclusive horizon at U. Keep the legacy quantity-only U refusal.
No C++ build, sanitiser, book/reference replay, observer run or performance measurement
occurs in this gate. Actual priority, hidden liquidity, market reaction and empirical
fills remain unverified. Tutorial Chapter 35, Exercises 77–79, explains the new evidence.
