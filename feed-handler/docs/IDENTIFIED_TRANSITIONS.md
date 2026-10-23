# Exact-source admission of canonical identified X/U histories

Gate 15 freezes this admission profile and independent expectations. It implements no
adapter or observer run. Gate 16 must implement and verify the profile below against
those frozen expectations. The existing `identified_events.py`, `identified_history.py`,
their accepted profiles, fixtures, transport and queue interfaces remain unchanged.

## Accepted source and state inputs

Use only the four windows in the accepted [Gate 14 record](validation/2026-10-23-l3-transitions/README.md).
Its committed `verification.json` is 81,814 bytes, SHA-256
`a0eb34d2aea23821ed1e4823fe8e84f9ee9c015fad24d9f39ce663e28111b2bc`,
accepted in `3c5af0af73320bd9fd9f75476c8ca0b0627eeb7c`. Authenticate that historical
Git blob and the current tracked blob; an arbitrary newly committed passed report is
not an accepted oracle. Read fixed artefact filenames, never execute commands or follow
untrusted paths from evidence. Verify selection, checkpoints, unfiltered census, both
complete exports/summaries and their independent review identities against that anchor.

Preserve Gate 14 window IDs: 1 MSFT_X, 2 MSFT_U, 3 QQQ_X, 4 QQQ_U. They are not
chronological and deliberately repeat symbol/locate pairs. Preserve their twenty
global checkpoint IDs and four separate seed states. Each independent ledger contains
event indices 0 through 4: one seed followed by four facts. The sixteen facts comprise
three A, six D, one E, two X and four U. Do not select a different window or omit a fact.

All twenty complete inventories, including deep levels, must satisfy the observer's
positive Price(4) domain through 2,000,000,000 and its unsigned reference/share bounds.
Gate 14's wider INT32_MAX export domain does not widen the observer. Reject the whole
profile on a domain error, without dropping a level or adding a quote-quality filter.
Copy seed inventories from the retained independent reference in B/S, best-price/FIFO
order. Mark all seed attribution unknown with null MPID. The current oracle is reused
independent execution, not a new vendor feed or fresh independent reconstruction.

## Exact source boundaries, not timestamp groups

Each interval is `(seed.sequence, last_tail.sequence]` for its selected locate. The
seed is the complete selected-symbol inventory after its original global frame; it
is never decoded again as the first fact. MSFT_U's seed is global S(Q), with wire
locate zero. Set `seed.effective_ns` to that seed's original timestamp. This snapshot
clock does not assign fresh arrival or priority times to its imported orders.

Enumerate every selected-locate frame in each sequence interval before type filtering,
and require exact equality with the accepted Gate 14 census and expected source list.
Admit only the actual A/D/E/X/U facts in this fixed profile. Unsupported selected
metadata or variants fail; they cannot disappear or become invented no-ops. Preserve
all original sequence, offsets, timestamps, length, type, tracking fields and bytes.

The raw scan begins at byte zero and ends exactly after global frame 8,300,042,
byte 284,563,784, prefix SHA-256
`1a64008af2e7c9ec0bece0d99d63e0dc35c6e07a5dd1185a044e4b4a6d75a925`.
Validate every included global frame's known length and non-decreasing 48-bit clock,
authenticate selected directories before seeds, and verify every seed/fact/census join.
There is no next-global-clock or later-timestamp witness requirement. A later same-time
frame outside the declared source interval is outside coverage. Equal timestamps inside
an interval retain global source order; no synthetic nanosecond is added.

The legacy history producer's unique-symbol, chronological-window and whole-timestamp
rules remain valid for its separate profile. Do not relax or route this new profile
through its incompatible binding/scanner. A separate `identified_transitions.py`
adapter may reuse compatible bounded I/O/export helpers and the unchanged logical
observer through `build_ledger`, `validate_ledger` and `observe`.

## Mutation and inventory requirements

X removes the wire quantity from the named order, retaining remaining relative FIFO
on partial cancellation. U is one atomic source fact and delivery: remove the old
reference and install the new total quantity, new reference and new price, inheriting
side, symbol and attribution knowledge. Copy the pre-order before removal. Never emit
an observable delete/add midpoint. A new U reference does not imply A's
`absent_in_wire` attribution; uncertainty must propagate through replacement chains.

The seen-reference set starts from each independent seed and retains in-window retired
references. It establishes bounded-window constraints, not day-wide reference history.
Keep four windows isolated even when their symbols match. Named X/E reductions do
not sweep other references to manufacture aggressive FIFO execution.

Build each ledger twice and require identical canonical bytes. Validate every original
frame and copied before/after/rank/ahead diagnostic, then compare all five complete
ranked inventories per window with the retained independent states. Preserve explicit
empty sides/books; neither population nor a BBO match substitutes for complete depth.
No attribution or actual exchange-priority agreement is inferred from the reference CSV.

## Fixed observation cases

For each window let `t[0]` be the exact seed time, `t[1..4]` the fact times, and
`end=t[4]`. Use these four profiles in the stated order:

| Profile | Feed delay F | Inclusive observation horizon H |
|---|---:|---:|
| zero | 0 | end |
| one_ms_clipped | 1,000,000 ns | end |
| one_ms_complete | 1,000,000 ns | end + 1,000,000 ns |
| undelivered_seed | end - t[0] + 1 ns | end |

Canonical seeds are strictly positive. Probes are the sorted unique union of
`t[0]-1`, all five source origins, and each `t[i]+F-1` and `t[i]+F` that is at most H.
All probes are non-negative and bounded by H. At a tie, deliver all due snapshots in
source order before probing. Return the greatest delivered event index; unavailable
means null orders, distinct from an available empty inventory. Seed delivery also
incurs F. Preserve pending deliveries at H; never flush at EOF.

The complete profile intentionally extends observation time, without admitting any
post-tail source event or claiming a complete market state at that later time. Its
probe at the original source end exposes local delay. The clipped profile retains
pending vectors [4], [1,2,3,4], [0,1,2,3,4], [1,2,3,4] for windows 1 through 4.
The frozen [oracle schema](IDENTIFIED_TRANSITIONS_ORACLE.md) defines all sixteen cases,
164 probes, 99 available probes and 218,428 expected captured row instances. These
are expectations, not executed observer comparisons or new historical samples.

## Verification stages and limits

Gate 15 reads and hashes retained small artefacts only. Freeze two byte-identical
expectation serialisations, independently audit their complete contents and demonstrate
the four specified altered-expectation rejections before writing the adapter. Keep
expected outcomes independent of that adapter and of observer execution.

Gate 16's canonical producer must freshly hash the full fixed 8,251,407,909-byte raw
file and exact retained prefix before and after production, with stable regular-file
descriptor/path identities and checked close. Re-enumerate the exact prefix and census;
reuse independent inventories without rerunning the external book. The logical module
must still report raw identity unverified by itself; the outer producer owns the fresh
authentication claim. Keep retained and fresh identity/reference scopes separate.

This sample has only partial X and moved-price U, with initially empty U destinations.
It adds no real same-price U, full X depletion, populated-destination priority, source
timestamp-tie or raw/effective seed-gap case. Existing synthetic evidence retains those
separate scopes. No execution-price/tape, hidden-liquidity, eligibility, hypothetical
fill, account, live transport/recovery or performance claim follows. Per-event data and
inventories stay ignored; publish aggregate design/runtime evidence separately.
