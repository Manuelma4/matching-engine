# Bounded canonical same-price replacement review

This is a reviewed selection and comparison contract, preceding any new source walk
or book export. It addresses one missing question: does a real same-price `U` remove
a non-tail order and append its replacement behind an already resting peer under
the pinned reconstruction convention? Keep reverse-linear as the default and the
[negative search experiment](validation/2026-10-23-level-search/README.md) unchanged.

## Why this question remains open

The [accepted X/U comparison](validation/2026-10-23-l3-transitions/README.md) adds
twenty states, ending 25.154024405 seconds after `S(Q)`. Its six checked transitions
are two partial cancellations and four moved-price replacements. Each replacement
destination was empty. Together with the earlier fifteen states, independent coverage
remains 35 distinct selected MSFT/QQQ states. Synthetic same-price and populated-level
cases do not establish those categories in canonical data.

The earlier [availability study](L3_AVAILABILITY.md) reaches 468.771899246 seconds
after Q within 16,000,000 frames and 524,152,398 consumed bytes. It counts later `U`
messages but retains neither their old prices nor same-level peers. These metadata
establish neither presence nor absence of the predicate below. This proposed selection
is informed by that observed source span, before seeing a matching book result.
Five to eight minutes after Q is later-opening coverage, not a late-session sample.

## Fixed input and finite source-classification stage

Use only the canonical Nasdaq 2019-12-30 BinaryFILE, 8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
Fix MSFT/5291 and QQQ/6556; authenticate their original directory messages and
global `S(O)`, `S(S)`, `S(Q)` ordering. Retain directory/Q identities, not assumed
clock constants. Number every nonempty global frame from one, starting at byte zero.
Offsets include the two-byte length; end offsets are exclusive.

Reuse the earlier fixed budget: stop at the first of 16,000,000 complete global
frames or 536,870,912 consumed-prefix bytes. Exclude a frame straddling the byte cap;
report separately any next length prefix read to identify that boundary. Do not stop
when a candidate is found or at a timestamp. Check every known type's exact length,
global non-decreasing timestamps and stable framing throughout the bounded scan.
Unexpected end records, truncation, unknown types, directory conflicts or malformed
selected state fail admission. A failed run retains diagnostics but admits no requests.
An ordinary early EOF is recorded separately, as in the availability study; it is
never confused with a truncated length/body or zero-length end record. System C,
book emptiness and selected-message counts neither stop the scan nor reset births.

Eligibility is `Q.timestamp + 300,000,000,000 <= U.timestamp < Q.timestamp +
480,000,000,000` nanoseconds. This interval filters candidates; it does not extend
the resource cap. Record the last consumed source point and whether a timestamp at
or beyond the upper bound was observed. If the cap ends earlier, explicitly mark the
interval right-censored. Null means no qualifier in the completely scanned eligible
prefix, with no absence claim about an unscanned part of the interval.

A new private stdlib classifier may maintain only selected live-reference facts
`{locate, side, price4, remaining_shares, birth_sequence}` and same-level membership.
It imports neither the implementation under test nor the reference book, comparator,
previous selectors or expected inventory outputs. This is a small source-derived
state model, not a state-independent wire census or an independent correctness oracle.
It has no sorted price directory and emits no full inventory, BBO or simulated fill.

Decode selected `A/F/E/C/X/D/U` from the start, including pre-Q history. Additions
create a birth sequence; named reductions retain it until complete removal; `D`
removes the named order. `U` inherits locate/side, removes old and creates its stated
new total quantity and price with the current global sequence as its fresh birth.
Do not interpret the quantity as a delta. Require valid positive prices/quantities,
valid sides and symbols, known references, distinct old/new U references, no duplicate
live new reference, no underflow and matching locate. Check a foreign-locate mutation
against any known selected reference before ignoring the foreign state. Follow the
accepted wrappers' common validation rules, including priced executions; do not
broaden their signed positive-price domain in this increment. Although the core and
reference API can handle old-reference reuse, the unchanged local export wrapper
rejects it in whole-prefix preflight. Reject selected same-reference U as invalid
classification input, rather than silently skipping it as a non-candidate. The local
exporter may also reject such an unselected occurrence; retain that failure without
changing the helper or selecting a replacement pair.

Limit selected live references and same-level memberships to 262,144 each, combined
across both symbols from byte zero, with no more nonempty membership groups than live
orders. The retained prefix has 164,374
selected `A/F` occurrences across pre/post-Q counts; `U` replaces one order rather
than increasing that count. This supports feasibility, not a measured memory claim.
Also limit candidate/summary/request output to 1 MiB and one historical process to
1,800 seconds. Do not retain every selected header or every qualifying event.

## Deterministic predicate and candidate freeze

Inspect the pre-U facts before mutation. Qualify only when old/new prices are equal
and another live reference at that locate, side and price has a birth sequence later
than old. This makes old non-tail under the declared birth-order convention. Choose
the peer with the smallest greater birth sequence as the deterministic witness.
Equal exchange timestamps remain distinct global source occurrences.

Select the first qualifying global ordinal for each fixed symbol, at most two anchors;
count all qualifiers through the fixed stop. Preserve explicit null for a symbol with
none. Never select on quantity size, quote, BBO, spread, book emptiness, exporter output
or subsequent agreement. Do not substitute full `X`, a moved-price `U`, another symbol
or a later interval. Missing candidates are a valid censored/negative study result.

Retain each anchor's original framed bytes/hash, length/type/time/offset/sequence,
literal old/new references and new fields, copied old facts and peer witness. Retain
the immediately preceding global frame's identity as well, even if it belongs to
another symbol or is metadata. Only two anchor/preceding metadata objects are needed;
do not infer a pre-state from a previous same-symbol event or timestamp group.

Before either full exporter runs, a separately written enumerator must independently
derive the same predicate, first ordinals, total qualifier counts, old/peer facts,
requests and prefix digest from authenticated source. It imports no classifier/UUT/
reference code or expected output. A disagreement fails selection without candidate
replacement. Freeze exact candidate metadata and requests, with their hashes, before
computing any complete expected inventories. This independently checks selection;
it is separate from the later pinned book oracle.

For each admitted anchor request two complete selected-symbol states: post-message
at global ordinal `anchor - 1`, then post-U at `anchor`. Sort/deduplicate by
`(global sequence, symbol)`, assign contiguous state IDs and retain all role links.
Use the existing nine-column checkpoint schema. At most two anchors give four
requested state boundaries. A null candidate produces no pair. If both are null,
publish the source-classification result and stop; execute no empty export plan.
One candidate permits only its one pair, honestly retaining the other symbol's null.

## Conditional independent complete-state comparison

This execution requires a later gate after successful, frozen selection. Reuse the
unchanged argc-five helpers: `INPUT CHECKPOINTS_CSV ORDERS_CSV SUMMARY_JSON`.
The current local helper uses the tested Release/open-addressed/reverse-linear build.
The reference remains MIT itchbook revision
`3c646f9da182136125059243b475f7b8baa53773`, with its retained archive/header identities.
Its `Book::replace` removes old, inherits side and calls add, appending at the level
tail. `first_order(side, price)` plus `Order.next` exposes the complete FIFO chain;
the accepted wrapper enumerates all levels and reconciles links, finds and totals.
Do not use the convenience iterator's finite-depth default or invent a new API.

Both helpers start at byte zero and stop at the last requested global frame, within
the bounded prefix. Neither needs a new complete-day replay. Execute each twice in
fresh ignored destinations; require repeat CSV/JSON bytes and exact complete source
manifests. Compare all order tuples `(side, price4, fifo_rank, reference, shares)`,
best-to-worst levels, B before S, contiguous one-based FIFO ranks and full side totals
using unchanged `compare_l3.py`. Empty sides remain observations. The reference's
seven validation counters must be zero; the local wrapper's complete prefix anomaly
checks must pass. Local reconstruction covers all instruments; reference state covers
requested symbols. Neither requires end-of-day C or a final empty book for this prefix.
The comparator additionally requires at least one state simultaneously both-sided,
with more than one level on some side and a multiorder FIFO on some side. The same-price
predicate ensures peers but not an opposite side or depth. A fixed pair can therefore
fail this inherited coverage guard even if its
exports agree. Retain that failed admission without reselection or comparator changes;
an empty side is an observation, not unconditional comparator acceptance.

Retain the existing cumulative one-million-exported-row limit per invocation and
the helper's 256-request limit, narrowed by this contract to four requests. Reject
excess rather than truncating depth. A complete copied-prestate delta oracle must
remove old once and append new with the stated total; all other named quantities,
prices and relative FIFO remain equal to the post-state. Require the retained peer
to precede new and prove old was ahead of that peer before U. Check the whole book,
not merely the changed level or BBO. No invented delete/add midpoint is exported.

## Identity, controls and claims

Before any historical execution, freeze and independently review the new private
sources and literal synthetic expectations. Focus controls on pre-Q seeding,
same-price non-tail/tail rejection, moved-price rejection, birth preservation on
partial reduction, complete depletion, new-total replacement and same-ref rejection,
foreign/global pre-boundary, equal-time source order, first-per-symbol selection,
no early stop, absent/censored intervals, cap boundaries and malformed/over-cap failure.
Include a changed-copy control that preserves the old birth on U: a subsequent
source predicate must expose it. Do not derive these expectations from UUT output.

Freshly verify complete raw size/SHA before and after each canonical classification
or comparison phase. Hash consumed prefixes during parsing and independently after;
check open/named-file identity throughout. Pin sources, contracts, reference headers,
actual tested binaries and requests before/after; preserve all first failures and
rejected output. Use exclusive fresh owned output and retain small aggregate records
with all commands, counters, bounds, identities, nulls and discrepancies. Keep raw,
source-derived details and per-event output ignored, tests private, both checkouts on
existing main. No branch, worktree or network service is required.

The classification aggregate must retain pre/eligible/post-interval selected U counts,
same-price and non-tail qualifier counts, all selected-header/mutation counts, live/peak
selected references, exact stop reason/last point, upper-bound witness or null and each
symbol's candidate or null. Separate the scan-to-cap prefix identity from each helper's
earlier stop-at-last-request identity. Positive signed-int32 price validation applies
only to the selected common domain; do not reject unrelated symbols' price stubs.

This design creates no new validated state, candidate presence/absence result or
performance measurement. A later matching result would extend only the admitted
source boundaries and shared tail-append reconstruction convention. It would not
prove actual exchange priority, hidden liquidity, every-event correctness, full-X
coverage, tied-event coverage, late-session behaviour, queue eligibility or empirical
fills. Do not count repeated exporters as additional independent historical samples.
