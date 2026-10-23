# Atomic identified displayed observations, version 1

This contract describes observed displayed-order changes. It is separate from the
[aggregate queue kernel](QUEUE_SIMULATOR.md), with no own orders, accounts, fills,
aggressor estimates or strategy eligibility. A later adapter must read actual source
frames and copy pre-dispatch state. Post-state snapshots alone cannot recover the
original execution price, printable byte, match number or replacement fields.

The design follows the retained April 28, 2023 Nasdaq ITCH 5.0 specification,
pages 4 and 13–18, and the independently checked reconstruction interfaces. The
[selected L3 evidence](L3_VALIDATION.md) establishes a useful seed/checkpoint contract;
it does not establish actual exchange priority. One of the two inspected executions
names a non-head reconstructed FIFO order. No reason is inferred from that observation.

## Scope and domains

Version 1 represents one selected symbol/locate and a complete bounded displayed seed.
It admits `A/F/E/C/X/D/U` and explicit `P/Q/B` context observations. Other known message
types are unsupported, rather than silently converted into no-ops. The adapter must
declare the source interval and prove that every selected message is represented.
Foreign-symbol checkpoints are observations of a state, not events for that symbol.

- References and match numbers retain unsigned 64-bit wire values. References naming
  displayed orders must be positive; match numbers are metadata, not ordering keys.
- Individual displayed shares and `P` context shares are positive unsigned 32-bit values. `Q` context shares
  are unsigned 64-bit and may be zero. Aggregate displayed shares use checked uint64.
- Price(4) uses integer wire fields. `A/F/U/C/P` prices and positive-share `Q` prices
  must lie in `1..2000000000`, the pinned specification's supported price range.
  Zero-share `Q` records may carry zero or a positive supported price under this
  declared version-one allowance; zero is rejected for `C/P`. This is a policy, distinct
  from both the decoder's unsigned representation and the L3 comparator's signed
  common domain. Unrelated unselected feed fields are outside this component.
- Source timestamps are unsigned 48-bit nanoseconds since midnight. Derived delivery
  and probe times use checked unsigned 64-bit nanoseconds.
- Hard bounds are 100,000 facts, 1,000,000 seed/live orders and 1,000,000 cumulative
  captured rows across source snapshots and returned probe inventories, 100,000 observation probes, 64 MiB ledger input, 8 MiB
  expected-source input and 1 MiB aggregate report. Exceeding a bound fails; no partial
  success is published. Seen references are bounded by seed count plus fact count
  (at most 1,100,000); removed identifiers are not forgotten within the window.
  Delivery metadata refers to already captured snapshots without duplicating inventories.

Live references are unique within the selected state. The seed references and every
newly admitted reference form a bounded-window seen set: reuse after removal and
same-reference `U` are unsupported in version 1. This is not a proof of day-wide
reference uniqueness, nor a change to the replica's more general API.

## Seed and attribution knowledge

The seed is an initial inventory, not a fabricated add/delete at its source point.
It contains the selected symbol/locate, an effective seed timestamp, the last included
raw SourcePoint and orders in `B` then `S`, best-price/FIFO order. Each order carries
reference, side, Price(4), remaining shares and attribution knowledge. Ranks are given
reconstructed state; original arrival/priority timestamps are not invented.

Attribution knowledge is explicitly one of `unknown`, `absent_in_wire` or `explicit`.
Only `explicit` carries the original four-character MPID. The earlier L3 seed API
does not retain attribution, so a seed produced from that evidence marks every order
`unknown`. An `A` adds `absent_in_wire`; an `F` retains its actual MPID. A replacement
inherits whatever knowledge exists, including `unknown`. A suggested display default
such as `NSDQ` must not be relabelled an observed wire MPID or a client identity.

The ledger seed boundary is an exact post-source-message prefix, not a claim that an
entire timestamp group has been consumed. Keep effective seed time separate from raw
source time, and mark the seed derived. Require raw seed time <= effective seed time
<= first fact time (where present), with effective seed time <= observation horizon.
Subsequent facts have strictly increasing source sequences, increasing non-overlapping
frame spans and nondecreasing original timestamps. Every span equals two bytes plus
the known body length and lies within the declared input size. Same-time later facts
are valid at an exact-prefix seed. A producer using the older historical projector
also preserves its independently established whole-boundary-group policy.
The seed SourcePoint may identify any recognised message type from another instrument
or global context; it is not decoded as a selected-symbol mutation.

## One source frame, one atomic fact

Every fact retains:

- a consecutive fact index and SourcePoint: sequence, frame start/end offsets,
  original timestamp, body length and type;
- original source locate and internal tracking number, which is not a parent order ID;
- the complete framed bytes as hex and their SHA-256, plus typed original wire fields;
- copied `before_order` and `after_order` values, or explicit `null` where absent;
- derived pre-event per-price FIFO rank and displayed shares before the named reference,
  plus a separately labelled resolved resting price where available.

The wire bytes and typed fields must agree exactly. A SourcePoint alone cannot prove
the frame's position in the original file; an adapter must bind it to identified input
and independently retained coverage. A frame hash verifies the retained frame bytes,
not the authenticity of a self-declared raw-file hash.

| Type | Original wire fields after the common header | Structural effect |
|---|---|---|
| `A` | ref, side, shares, stock, display price | Append a new order |
| `F` | `A` fields plus MPID | Append with explicit attribution |
| `E` | ref, executed shares, match | Reduce only the named order; retain rank if live |
| `C` | `E` fields plus original `Y/N` printable byte and explicit execution price | Same named displayed reduction, independently of printable status |
| `X` | ref, cancelled displayed shares | Reduce only the named order; retain rank if live |
| `D` | ref | Remove its complete copied remaining quantity |
| `U` | old ref, new ref, new total displayed shares, new display price | Remove old and append replacement as one indivisible change |
| `P` | wire ref/side, shares, stock, price, match | Context only; no displayed mutation |
| `Q` | uint64 shares, stock, price, match, cross type | Context only; no displayed mutation |
| `B` | broken match | Context only; no current displayed mutation |

`D` has no wire quantity. Its removed quantity is derived from copied pre-state.
`E` has neither an explicit price nor a printable flag: retain their absence, and
label any resting-price resolution as derived. `C` execution price remains distinct
from resting display price; retain the original printable byte before any Boolean
conversion. Non-printable executions still remove displayed shares.

For `U`, replacement shares are the new total displayed size. Side, stock and known
attribution are inherited. Even an unchanged price/size moves the replacement to its
destination tail under this reconstruction convention. There is one fact and one
delivery, with no observer callback between removal and insertion. A transient deeper
best quote must never become a separately observable event.

Modern `P` fields do not identify a resting reference or aggressor direction. Neither
`P` quantity nor `Q` bulk shares become displayed executions. `B` affects trade
accounting outside this structural model; it does not resurrect a removed order.
Status, tape/volume, hidden liquidity and strategy eligibility remain unmodelled.

The admitted modern `P` policy requires wire reference zero and side `B`, without
using either as a resting identity or direction. Supported `Q` cross codes are `O`,
`C` and `H`; legacy alternatives are unsupported. `A/F` side is exactly `B/S`, `C`
printability exactly `Y/N`, and explicit MPID is four original printable ASCII bytes.
Unknown/absent attribution carries `mpid: null`. Context observations always have
null before/after order and rank diagnostics; they never look up their wire reference
or match number in the current displayed book.

Copy pre-state before mutation; never keep a pointer to a freed/reused slab slot.
For mutations, reject absent old references or duplicate/previously seen new references,
zero/oversized reductions, wrong locate/stock,
unsupported fields and any producer anomalies. Rejection leaves the prior state
unchanged and cannot become a successful no-op. The event model follows named
reductions even when they are not at reconstructed head. It never redistributes
execution shares across earlier references to manufacture a FIFO sweep.

## Replay and coverage

The JSON document has exact top-level fields `schema_version: 1`,
`model: "identified_displayed_observations_v1"`, `symbol`, `locate`, `source_identity`,
`seed`, `expected_sources` and `facts`. Selected symbols are unpadded printable ASCII
strings of one to eight characters, including valid punctuation/internal spaces;
paths are never derived from symbol names. Each wire stock remains its original
eight-character padded ASCII field and must resolve to that selected symbol.

`source_identity` declares `input_bytes`, `input_sha256`, nullable `evidence_sha256`
and literal `verification: "unverified_by_module"`. A seed has `source`, `effective_ns`,
`boundary: "post_source_message"`, `derived: true` and ordered `orders`. An order has
`reference`, `side`, `price4`, `shares` and `attribution: {kind, mpid}`. The `expected_sources`
array lists the original SourcePoints for the facts; an independently supplied expected
list can also be required by a caller. It is distinct from the seed source.

A fact has exact fields `event_index`, `source`, `source_locate`, `tracking_number`,
`frame_hex`, `frame_sha256`, `kind`, `wire`, `before_order`, `after_order`,
`derived_removed_shares`, `fifo_rank_before`, `visible_shares_ahead_before` and
`resolved_resting_price4`. The kind is `add`, `execute_named`, `cancel_named`,
`delete_named`, `replace` or `no_displayed_order_change`. The removed-share diagnostic
is zero for adds/context, the named reduction for `E/C/X`, and the complete old size
for `D/U`; for `U` it is structural removal, not a cancellation/trade quantity.
Pre-order rank/ahead/resting-price fields are null for adds/context. Frame hex and
SHA-256 use canonical lower-case encoding.

Wire object fields are exact per variant: `A` has `reference,side,shares,stock,price4`;
`F` adds `mpid`; `E` has `reference,shares,match`; `C` adds `printable,execution_price4`;
`X` has `reference,shares`; `D` has `reference`; `U` has
`old_reference,new_reference,new_shares,new_price4`; `P` has
`reference,side,shares,stock,price4,match`; `Q` has
`shares,stock,price4,match,cross_type`; `B` has `match`. Absent wire fields are absent
from these objects, not manufactured as zero/default values.

A version-one ledger contains the seed, ordered facts, the independently expected
source-point list and source/evidence identity declarations. Replay validates each
fact's original bytes and copied pre/post state, then reproduces the ordered book.
The final empty book alone is insufficient: exact intermediate tuple comparisons
remain necessary. The producer must supply the request list from trusted evidence;
two self-consistent files omitting the same event do not establish coverage.

The module validates internal consistency only. It must label raw input identity as
not verified by the module. A later raw adapter is responsible for source hashing,
frame/sequence/locate binding, complete selected-message coverage and independent
checkpoint comparison. Per-event ledgers, raw frames and snapshots stay ignored;
public evidence contains aggregate checks and identities.

The stdlib-only `bench/identified_events.py` provides `build_ledger`, `validate_ledger`
and `observe`. The builder takes the selected symbol/locate, declared source identity,
seed, ordered `(SourcePoint, complete framed bytes)` pairs and expected source list.
Validation re-decodes the bytes rather than trusting the supplied typed facts. Its
private result includes every immutable captured post-state, beginning with the seed;
the command line emits aggregate counts and file identities only.

Use independently retained expected-source lists and fresh report paths:

```bash
python3 bench/identified_events.py validate out/example/ledger.json \
  --expected-sources out/example/expected-sources.json \
  --report out/example/validation.json
python3 bench/identified_events.py observe out/example/ledger.json \
  --expected-sources out/example/expected-sources.json \
  --feed-delay-ns 5 --horizon-ns 16 --probe-ns 12 --probe-ns 15 \
  --report out/example/observation.json
```

These commands consume logical bundles; they do not read or authenticate a canonical
raw file. Report identity applies to the bundle bytes actually read. The private API
returns detailed states/probes, which must remain in ignored working storage.

## Delayed observation

The first observation model uses one fixed nonnegative feed delay. The derived seed
captures its initial state at its **effective seed time**, and delivery is effective
seed time plus delay. A fact captures immutable whole post-state at its original
source timestamp; delivery is that timestamp plus delay. Source order is preserved
for equal delivery times. For example, raw seed time 7, effective time 10 and delay 5
means the seed is unavailable at 12 and delivered at 15. A replacement
cannot be split across deliveries, and a delayed payload cannot read the current
mutable exchange book when it arrives.

Equal-time phases are source application, feed delivery, then observation probe,
followed by source insertion order. These are the first three phases of the existing
kernel; no own-order arrival or response is introduced here. A probe at delivery time
sees that delivery under this declared tie policy. It never sees a future source state.

Every source record must be within the declared inclusive horizon. Delivery beyond
the horizon remains pending: no EOF flush, forced cancellation or liquidation occurs.
With no delivered seed, the local state is unavailable. Variable per-message delays
are unsupported until a separate sequencing/recovery policy is defined.

## Acceptance before a raw adapter

Independent review must check this contract before implementation of a raw adapter.
Hand-frozen framed fixtures must check same-time ordering, high-bit references, partial
and full named reductions, non-head execution, same/moved-price replacement, atomic
best-ask replacement, attribution uncertainty/inheritance, `C` printability/price and
explicit `P/Q/B` context. Tampering with bytes, refs, ranks, match/printable fields,
derived delete size, coverage or replacement atomicity must fail.

Delayed probes must demonstrate immutable past information, feed-before-probe ties,
an undelivered seed and pending final delivery. No correctness, latency or P&L claim
requires a favourable mark or any hypothetical fill. Passing a structural observer
contract does not calibrate execution probability or establish actual exchange priority.

The retained canonical prerequisite contains seven `A`, four `D` and two partial `E`
transitions. All thirteen mutate full L3, including five observations previously
labelled unchanged by the restricted fixed-level projection. Canonical `F/C/X/U` or
context coverage is not claimed here. The present increment validates this logical
contract on hand-frozen frames; a raw historical adapter remains a separate gate.

## Recorded hand-frozen baseline

The [aggregate evidence](validation/2026-10-22-identified/hand_worked.json) passes at
clean `main` source commit `a5c99b1ed624b0c25944c1cf24ea3751c0764d69`.
Two independently frozen cases contain 29 framed facts, 31 complete source states
and 240 order-row instances. Every generated ledger field and intermediate inventory
matches the hand-written oracle. Six atomic replacements, named non-head executions,
wide quantities, high-bit references and all ten admitted wire variants are covered.
These are synthetic observations; their counts estimate no historical frequency.

Seven observation profiles match all 77 probe inventories, delivery metadata and
pending indices exactly, including unavailable seeds, effective seed-time delivery,
same-time source order and a final delivery beyond the horizon. The separate empty-seed
regression distinguishes an available empty book from unavailable information.
Two ledger creations and nine pairs of aggregate CLI reports are byte-identical;
all eighteen clean-source CLI processes return zero. The private driver separately
hashes the tiny synthetic source files and verifies every retained frame's position
and complete post-seed selected-locate coverage. That driver check does not change
the module's explicit `raw_input_identity_verified: false` label.

Thirty-three private methods and `Validation.IdentifiedEvents` pass; the private harness
now registers 100 CTests. Review found duplicate singleton clock options and admission/
publication-bound issues before the source commit. Regressions cover actual byte limits,
nonblocking descriptor checks, changed inputs, symlinks/hard links, close failures and
short writes. A failed write removes only the report created by that attempt.

The [clock mutation control](validation/2026-10-22-identified/clock_control.json)
deliberately schedules a private seed from its raw timestamp instead of effective time.
The unchanged frozen oracle detects three of seven probe discrepancies; the baseline
matches all seven. Production code is unchanged. The
[verification manifest](validation/2026-10-22-identified/verification.json) retains
fixture/generator, harness, process, review and source identities.

No canonical raw input was reopened, and no new C++ sanitiser or performance run is
claimed for this Python component. Canonical prerequisites remain the earlier fifteen
independently compared full-depth states and thirteen selected transitions. A later
adapter must read actual raw frames, authenticate source identity, establish complete
bounded coverage and compare every produced state against those independent states.
This baseline introduces no own orders, fills, accounts or strategy eligibility.
