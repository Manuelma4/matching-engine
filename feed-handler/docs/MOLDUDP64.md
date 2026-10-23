# Offline MoldUDP64 admission profile v1

The Gate 10 contract was written and independently approved before implementation.
This stage is a bounded,
synchronous C++ library with private offline integration fixtures. It opens no sockets,
issues no requests and does not alter order-book logic or the queue/fill model.

## Source and scope

The primary source is Nasdaq's [MoldUDP64 Protocol Specification v1.00](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/moldudp64.pdf),
including the formatting revision dated 2 August 2024. A fresh copy retrieved on
22 October 2026 has 86,837 bytes and SHA-256
`96cdd02b8728a441cb970d1371a96e73c01e1edaffb2891d43667e2a0ad8add5`.
The PDF and rendered tables remain ignored under `data/reference/`.

Pages 2–4 define big-endian protocol integers, a 20-byte header (session bytes 0–9,
first message sequence at 10–17, count at 18–19), and consecutive message numbers.
Each ordinary block contains a two-byte body length followed by that many body bytes.
A zero-length body is legal at the transport layer. Count zero is a heartbeat;
count 65,535 is end of session. Both controls advertise the next expected message
sequence, rather than a message that should be dispatched. Pages 3–6 discuss terminated
sessions, requests and partial responses; this profile implements none of that recovery.

Every restriction below is our profile policy, rather than an extra Nasdaq rule.
This is a datagram payload parser, without IP/UDP headers, capture formats, reception
clocks or a live receiver. It cannot establish that an offline packet was transmitted
by Nasdaq. Synthetic repacketisation does not turn a BinaryFILE frame into a captured
network packet.

## Bounds and parser

Default positive bounds are 65,535 datagram bytes, 1,024 ordinary messages per packet
and 100,000 receive attempts per receiver. Configuration cannot exceed these ceilings.
A parser validates the entire datagram before exposing a packet view: at least 20 bytes,
all declared block lengths, exactly the declared number of blocks and no trailing bytes.
Controls are exactly 20 bytes. Count 65,535 is never interpreted as 65,535 blocks.
An ordinary zero-length body remains ordinary data. All non-wrapping arithmetic is
checked: `first + count` must be representable as uint64. Thus a data message numbered
UINT64_MAX is outside this profile. Sequence zero is also outside this profile.

Views borrow the original immutable datagram. The caller must retain its storage and
must not mutate it during parsing, validation or synchronous callbacks. The parser owns a bounded transient vector of message descriptors, whose bodies
borrow the datagram. There is no historical payload/digest cache, reorder buffer or
unbounded packet retention; allocation-free parsing is not claimed.

## Session and sequence state machine

The caller supplies all ten session bytes and a positive initial next sequence. Session
bytes are compared exactly, without trimming, character normalisation or inferred padding.
No first packet can establish an initial sequence on the caller's behalf. Invalid constructor bounds or zero initial next throw before reception. Initial next
UINT64_MAX permits matching controls but no data. A configured
checkpoint is only an assumption until its seed/source provenance is independently checked.

The states are `ready`, `ended` and `failed`. Each call entered before failure counts
towards the attempt bound, including controls and the call that first exceeds the bound
(which records limit + 1).
After failure the counter is frozen, later calls are blocked and invoke no validators or
handlers, and the first fault is retained. No reset/retry/recovery API is provided.

| Input while ready | Result | Dispatch | Next sequence |
| --- | --- | --- | --- |
| Ordinary data beginning exactly at next | accepted, after complete preflight | all bodies in order | exclusive end after all callbacks succeed |
| Ordinary range entirely before next | stale data; fail | none | unchanged |
| Ordinary range crossing next | unsupported overlap; fail | none | unchanged |
| Ordinary data beginning after next | gap; fail | none | unchanged |
| Heartbeat advertising next exactly | heartbeat | none | unchanged |
| End advertising next exactly | end; enter ended | none | unchanged |
| Either control advertising a different sequence | control sequence mismatch; fail | none | unchanged |
| Any session mismatch, malformed packet or bound violation | fail | none | unchanged |

An entirely old range is diagnosed as stale, without claiming byte-identical duplication.
The profile deliberately refuses to continue even if those bytes happen to be identical.
A forward packet followed later by the missing packet remains failed. Gaps are never
healed by adopting a packet's sequence, comparing BBO, or reaching a final empty book.

In `ended`, an exact same-session end marker at the same next sequence is an idempotent
repeated end. Any other well-formed input fails as post-end input (a session mismatch
retains its own diagnosis). A malformed repeated end still fails. End markers cannot
conceal a gap. Ordinary file exhaustion leaves a receiver ready: only a checked end
marker establishes ended within this model.

## Application validation and failure

`receive` takes a side-effect-free payload validator and a synchronous message handler.
It parses every block, checks the session/sequence and runs the validator on every body
before invoking the first handler. A validator exception fails the packet with zero
handlers. The ITCH integration validator rejects empty, unknown-type or wrong-length
bodies using the existing ITCH 5.0 length table. Passing an empty Mold body to the
BinaryFILE `dispatch` function would incorrectly return its framing-terminator result
`Dispatch::EndOfSession`, so it is forbidden. That result is distinct from ITCH system
event `C` and does not itself set the book builder's end-of-messages flag.
A no-op validator is available only when a caller deliberately wants generic Mold bodies.

Admission order is: already-failed guard, attempt bound, re-entry guard, complete
structural parse, session, ended/sequence policy, all validators, all handlers, then next
commit. The handler receives the transport sequence, zero-based index within the packet,
zero-based body offset within the datagram (first body at 22) and body bytes. None is a historical `SourcePoint`, a timestamp or receipt
time. Fixture joins must retain original source identity/offsets separately.

Structural admission is atomic. Existing `BookBuilder` mutations are not transactional.
If a handler throws after an earlier body has changed the book, the receiver fails,
reports the attempted and successfully returned callback counts and does not advance
next. The consumer must discard the entire run, including that partial book. The failed
receiver cannot be reused. An anomaly that the book reports without throwing must be
converted into a handler exception by the integration. Validation callbacks must not
modify the consumer. Re-entering the same receiver from either callback latches a
re-entry fault; the outer call checks that latch after each callback and stops.

Results capture callback exceptions into typed faults rather than rethrowing them. Each
result gives the disposition, first fault, next sequence and per-call handler-attempted/
handler-returned counts. A returned handler is not proof that its external side effects
were transactional. The receiver exposes the cumulative bounded attempt count. A later
blocked call returns zero per-call counts and cannot replace the first fault.

## Acceptance before release

Freeze independently hand-encoded packets, expected dispositions, callback order and
book inventories before executing the implementation. Cover asymmetric endian values,
all truncation boundaries, count/length/trailing errors, a malformed or invalid later
body with zero handlers, empty Mold bodies versus ITCH rejection, numeric/resource bounds,
stale packets, unsupported overlap, reorder, session bytes, control mismatches, repeated
end and post-end data. Cover a throwing validator and downstream failure after a partial
application, with all later input blocked. A dropped deep update must leave BBO unchanged
while the sequence gate still rejects the gap. Repacketisation must preserve independently
identified message order and intermediate full order states. Keep hand coverage distinct
from historical and captured-network coverage; no throughput or network-latency claim follows.

## C++ interface

Link `itch_mold` for the generic receiver. `itch/mold.hpp` contains the types and
`parse_packet`, which returns a bounded descriptor vector borrowing the datagram.
`Receiver` owns only its fixed configuration, counters and state. It is non-copyable,
single threaded and not thread safe. A generic caller explicitly supplies
`accept_generic_payload`; the ITCH integration includes `itch/mold_itch.hpp` and links
`itch` for the existing application headers/core.

The synchronous call shape is:

```cpp
itch::mold::Session session{'E','X','A','M','P','L','E',' ',' ',' '};
itch::mold::Receiver receiver(session, 41);
auto result = receiver.receive(datagram, itch::mold::validate_itch_payload,
    [&](const itch::mold::MessageView& message) {
        // Copy or consume these borrowed bytes before the datagram storage expires.
        // A BookBuilder integration must throw if dispatch reports any anomaly.
        consume(message.transport_sequence, message.body);
    });
if (result.state == itch::mold::State::failed) {
    discard_consumer_run();
}
```

`datagram`, `consume` and `discard_consumer_run` are application placeholders. The library
adds no public network executable. `Result` contains typed `disposition`, `fault`, `state`,
`next_sequence`, `receive_attempts`, `handler_attempted` and `handler_returned` fields;
`to_string` supplies stable diagnostic names. Validation is type/length preflight,
not semantic order-lifecycle validation or authentication of exchange origin.

The parser's allocation-failure catch path is reviewed in source but is not exercised
by allocation fault injection in this increment. No allocation-free or rollback claim
is made. The independently frozen unit and integration checks are retained in the
private sibling harness rather than published as tests in the source repository.

## Recorded synthetic baseline

Clean source commit `cd9c80e33a23d67b20bcfbc9158621faa0737794` passes on
22 October 2026 with Apple clang 21.0.0 on macOS arm64. The
[aggregate verification](validation/2026-10-22-mold/verification.json) retains source,
fixture, specification, private harness, binary and report identities.

| Check | Result |
| --- | --- |
| Independent unit methods | 38 completed, none skipped, in Release and ASan/UBSan |
| Focused CTest groups | `Validation.MoldUnit` and `Validation.MoldIntegration`, both configurations |
| Frozen original synthetic source | 26 messages, 707 bytes; 27 inventories including empty seed, 84 order rows |
| Fault matrix | 17 cases, 84 supplied datagrams including blocked continuations |
| Returned-message comparisons | 194 states and 518 complete FIFO row instances; zero discrepancies |
| Detailed integration assertions | 16,391 per launch; repeated summaries byte-identical within/across configurations |
| Gap negative control | Removing only forward-gap refusal makes the frozen deep-update test fail; production passes |

Two complete packetisations preserve all 26 original message identities and intermediate
states. Other cases admit prefixes or deliberately fail. The 194 comparisons include
repeated source states across cases; they are not 194 distinct source messages. The deep
loss control preserves BBO while the correct full inventory changes from six orders to
five. Late missing data cannot revive the failed receiver. The matrix also retains a
one-message partial consumer side effect after an injected handler failure and refuses
its continuation. These deliberately failed runs are expected test outcomes.

Independent expectations were frozen before implementation execution. A separate
stdlib-only audit verifies source framing, all source/body/offset/timestamp joins,
all synthetic container/trace bytes and BBO derived from the literal inventories.
The integration compares actual bytes against source bodies; it does not recompute
per-body SHA-256 in C++. The outer runner freshly checks the independently frozen file
hashes. Its 158 retained input identities, both commits/branches, binaries and all 38
unit names remain stable during verification. All runtime stderr is empty; sanitiser
halt-on-error options and effective compile flags are recorded. Leak checking is not
claimed.

The final recorder initially stopped before tests because only the public child targets
appeared in the compile database. Enabling `CMAKE_EXPORT_COMPILE_COMMANDS=ON` at the
root fixed that provenance check; the failed attempt is retained. Fresh GoogleTest
1.15.2 compilation emits a `char8_t` to `char32_t` conversion warning with this compiler.
Project sources emit no warnings in these checks. That dependency diagnostic is retained;
we do not claim a warning-free complete build.

The synthetic source has strictly increasing timestamps and unique body bytes. The
private join rejects ambiguous duplicate bodies. Timestamp ties, canonical historical
repacketisation and actual network captures remain outside this integration baseline.
Earlier canonical evidence is retained rather than rerun by this Gate 10 check.

Gate 11 subsequently completes that selected-locate connection in
[the canonical repacketisation profile](CANONICAL_TRANSPORT.md), using explicit occurrence
keys and separately scoped equal-time/identical-body controls. The figures above remain
the original wholly synthetic Gate 10 baseline. Neither increment adds network recovery.

From the workspace root, the existing private harness and frozen ignored fixture can
repeat the check on the current clean `main` without switching branches:

```bash
mold_source_commit=$(git -C itch-feed-handler rev-parse HEAD)
python3 itch-feed-handler-tests/verify_mold_increment.py \
  --source-commit "$mold_source_commit" \
  --output itch-feed-handler/out/mold-verification-fresh
```

The output directory must be new. This command runs only the two focused groups and
repeats integration summaries in Release and ASan/UBSan. It rejects skipped tests,
changed inputs/binaries/commits and incomplete counts. It performs no canonical raw-data
read. The private harness and ignored fixture are prerequisites; they are intentionally
not published in the source repository. Read Chapter 20 of the workspace tutorial for
worked examples of completeness, atomicity and transport identity.
