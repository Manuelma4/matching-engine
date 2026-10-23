# Prerequisites for one identified shadow queue

This read-only Gate 24 review concerns the exact QQQ same-price U already checked by
[the retained observer](validation/2026-10-23-same-price-observer-runtime/README.md).
It establishes a finite next audit, without running a queue or granting admission.
Both repositories stay on existing `main`; the legacy queue/history APIs stay unchanged.

## What existing interfaces can support

The [fixed-level simulator](QUEUE_SIMULATOR.md) has Seed/Add/Cancel/Trade/Quote events,
aggregate quantity ahead and cancellation assumptions. It has no order reference or
atomic replacement input. The [historical projector](HISTORICAL_WINDOW.md) explicitly
rejects a U touching its target level (`src/queue_window.cpp`, target replacement guard).
Splitting this U into cancel/add would lose identity and expose a transient state.
Do not relax that guard or feed such a split into the old simulator.

The identified observer already supplies immutable full inventories and one atomic U.
A later small, separate shadow overlay can consume those admitted objects after the
status/coverage audit below passes. Keep own state outside the historical reference
namespace; never insert the hypothetical order into the recorded external book.
This justifies a bounded new interface, not a general matching engine or strategy.

The current seed has a production directory and original system O/S/Q provenance.
It lacks an admitted latest selected H/cross/status census at this particular pair.
Earlier full-day counters and exploratory status notes are retained clues. They are
not a substitute for fixed-pair admission and must not manufacture an h(T) message.
The observer itself deliberately establishes no session/strategy eligibility.

## Exact source cut versus a completed timestamp

Let t0 be PRE, 34,645,316,895,296 ns, and t1 be U, 34,645,316,896,167 ns.
The global source ordinals are 15,536,746 and 15,536,747; the latter frame ends at
509,933,991 bytes. PRE concerns a foreign symbol. Consecutive ordinals and contiguous
bytes prove that `(PRE, POST]` contains exactly one global frame.

Because U's timestamp is strictly later, it also closes the entire t0 timestamp group.
It does not close t1: another frame with timestamp t1 can follow U. Existing scheduler
phases process the entire supplied market timestamp before feed, decisions, requests
and responses. An arrival at t1 therefore needs proof of the complete group.

A strictly interior arrival can be placed before U under a declared model. However,
a full scheduled endpoint at t1, or a decision/arrival after U at that time, needs the
closure audit. Extending the observer horizon only delivers admitted information;
it authenticates no later exchange path. Refuse requests to execute after covered
history rather than carrying the last external book forward.

## Gate 25: fixed prefix authentication and closure audit

Use only the canonical file and fixed pair. Retain these accepted evidence identities:

- Gate 20 classification receipt: `out/same-price-classification-v1/verification.json`,
  93,414 bytes, SHA-256
  `10cfb567ca8e1fbbcba81ebbb813065ff8313f80d975fa6b07bea7ab93c07536`.
  Its committed public record is
  [the classification evidence](validation/2026-10-23-same-price-classification/verification.json).
- Its complete 16,000,000-frame prefix is exactly 524,152,398 bytes, SHA-256
  `c8e4fff1b993f8ebc5eae8c43d94e110935fa5e3d883853c3812d43e0b8f1b96`.
- The nested Gate 21 pair prefix is 509,933,991 bytes, SHA-256
  `47d19f447eaa60aaabc1f041c6cce28b83261358cbc0c0436052a3afb8fb9a10`.
  [Gate 21](validation/2026-10-23-same-price-l3/README.md) retains the independent rows,
  exact original PRE/U frames and separate-pass hash timing qualification.

The larger authenticated prefix already extends past t1. A new status audit can
freshly authenticate its bounded bytes without freshly hashing all 8,251,407,909 raw
bytes. Pin the current and accepted committed public records, private classification,
Gate 23 runtime aggregate and postcommit receipt before following their fixed roles.
Never admit an arbitrary input path or digest supplied by a new document.

Write two independently structured private scanners, with no book/observer/project
imports. Each requires the accepted full file length of 8,251,407,909 bytes, opens the fixed
regular raw file through one stable descriptor, and:

1. Reads from byte zero, with exact framing, all 23 known lengths, non-decreasing
   timestamps and contiguous global source ordinals/offsets. Reject partial frames,
   zero-length/unknown messages, premature EOF and overflow. Bound decoded messages
   to 16,000,000 and all physical reads to exactly 524,152,398 bytes, within the old
   536,870,912-byte ceiling. Never peek beyond the fixed prefix.
2. Checks the exact retained PRE and U occurrences, their complete frame hashes,
   foreign PRE identity and QQQ locate 6556. Enumerates every selected message through
   the complete t1 group before filtering it. The first strictly later global frame
   is a closure witness: retain its source point/body hash and validate framing/time,
   but never apply it to status snapshots or interval censuses.
3. Freezes status immediately after PRE and after the final frame with time t1.
   Any additional QQQ book mutation A/F/E/C/X/D/U after the fixed U at t1 refuses this
   one-U profile, even with unchanged BBO. Do not choose another U, widen a time window
   or export replacement independent states to make this profile pass.
4. After the witness, reads the remaining known prefix for authentication only. That
   tail changes no semantic clock, status, selected census, candidate or observation.
   It need not be decoded. Distinguish actual decoded-frame counts from the inherited
   16,000,000-frame extent of the known authentication prefix.
5. Computes SHA-256 from the bytes actually read: nested prefix exactly at 509,933,991
   and complete prefix exactly at 524,152,398. Both must equal the fixed identities.
   Descriptor/path identity, size and modification metadata must remain stable through
   publication. Every read is bounded by remaining prefix bytes; no buffered overread.

A witness before the nested prefix cannot close this fixed U. A missing witness,
a decoded-frame/byte bound reached before a valid complete witness, malformed coverage
or a digest mismatch is a refusal. A valid witness may end exactly at an inclusive
bound. Successful authentication must reach its exact fixed byte extent; reaching
that required hash boundary is not itself a refusal. Complete authentication must
finish before a successful receipt is published. Record `raw_opened:true`,
`fresh_prefix_sha256_verified:true`, `fresh_full_raw_sha256_verified:false`; the full
canonical identity remains inherited. No L3 reconstruction, independent book replay,
new historical state or full-day semantic validation follows from this audit.

## Status policy for this audit

Use the existing projector's deliberate restrictions, separately from venue order-entry
eligibility. [Nasdaq's ITCH specification](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf)
was checked on 2026-10-23: sections 1.1, 1.2.1/2/5/8, 1.5.2 and 1.7 distinguish these
wire fields. Its revision log still ends at April 28, 2023; this is a later specification
reading of the 2019 layouts, not a 2019 exchange validation report.

| Input | Bounded admission policy |
| --- | --- |
| R | One unique production QQQ/6556 mapping; validate stock text/locate agreement, including zero-locate stock-named K separately |
| System S | Global locate zero; first source frame is O, then S/Q in exact order before seed, rejecting repeats/out-of-order codes; any M/E/C through the closed endpoint refuses |
| Selected H | Latest action T at seed and throughout the interval; preserve exact origin and reason bytes |
| Selected Q | Latest completed cross at seed is O; any selected cross in the interval refuses this profile |
| Global W | Any breach through the endpoint refuses; no inferred resumption rule |
| Selected h | Validate Q/B/X market and H/T action; track Nasdaq Q separately; absent is unknown/null, latest Q/H refuses |
| Selected N | Retail indication is absent/unknown or N; active B/S/A refuses under the existing restriction |
| Selected K/I/J/O/R/C/Q in the interval | Unsupported context refuses; selected K before seed also refuses |

Maintain latest-origin records and bounded counters, with explicit nulls for absent
announcements. Preserve h by market so BX/PSX cannot overwrite Nasdaq's state. Do not
confuse retail N with Reg SHO Y. Y is not a source of retail status. This passive-buy
profile is not a complete regulatory, order-type, routing or market-access model.

Freeze the PRE seed snapshot before any later status is processed. Before PRE, parse,
validate and remember startup/status history: an earlier H or active retail indication
can be superseded before seeding, subject to the explicit sticky W/IPO exclusions.
Require the stated latest-state policy at PRE, then re-evaluate at every selected
status/global system or W update through t1 rather than checking only final values. Record all selected non-mutation exclusions explicitly. Source
point order, not a sorted reconstruction, determines the latest announcement.

Before raw execution, freeze tiny synthetic positive streams and at least twelve
literal refusal families: missing H/cross, wrong H/h/N, sticky W, unsupported context,
identity disagreement, malformed lengths/order, missing witness, extra same-time
mutation, wrong nested/full digest and exceeded bounds. Include a future witness
whose status differs, to prove it cannot rewrite the earlier admission. Review both
sources before two canonical scans, require exact independently derived status/census/
closure agreement, and retain all first refusals. No actual outcome is predicted here.

## Conditional queue work after audit success

Only after status, complete t1 closure and unchanged POST inventory pass may a later
implementation freeze concrete expected traces from the independent rows. The first
model is one passive buy at the delivered seed best bid, synthetic quantity one,
with no trades, fees or P&L inference. All queue positions are declared shadow FIFO
conventions, not actual exchange priority.

Keep external historical inventory, own exchange state and delivered local knowledge
separate. Acceptance puts every current external order at that price ahead. A later
atomic U removes the old order from the ahead set if present and places its replacement
behind an already accepted own marker. If arrival follows U, all POST external orders
are ahead. Own cancellation removes only the marker. Seed MPIDs/birth times stay unknown.
A decision must read delivered observations, never validation-only future inventories
or exchange ahead/remainder. Submission immediately records local Pending and the
requested quantity. Exchange acceptance/rejection, cancellation and fill outcomes
become locally known only through delayed responses; historical feed is never an own
acknowledgement.

The finite candidate scenarios are pre-U acceptance, arrival exactly at t1 after the
closed market group, undelivered-seed skip, arrival pending beyond horizon, acceptance
response pending, and own-only cancellation before U. Use the existing market/feed/
decision/arrival/response phase order and inclusive horizon; keep events after it
pending without inventing their effects. An explicit request to execute beyond source
coverage refuses. Information-only delivery of already admitted snapshots is a different
scope, not permission to advance the external market. Every such scenario has zero
fills because the only admitted book fact is U, which is never a Trade.

If status or closure fails, preserve that refusal and the original case. Further
history, unknown same-time book mutations, sells, priced executions, hidden liquidity,
market reaction and empirical fill calibration require separate evidence and review.
