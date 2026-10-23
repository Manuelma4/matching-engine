# Design

## Pipeline

```
 BinaryFILE (mmap or stdin)
        |
        v
 walk_frames      2-byte big-endian length prefix per message; partial frames carried
        |         across stream blocks
        v
 dispatch         type byte -> length check -> zero-copy view -> handler member chosen at
        |         compile time; unknown types and wrong lengths are counted, never fatal
        v
 BookBuilder      applies order messages to the L3Book, keeps day statistics
        |
        v
 L3Book           full-depth books for every stock, one global order-reference index
```

Decompression stays outside the binary (`gzip -dc day.gz | itch_replay -`), so the library
has no dependency beyond the C++20 standard library and the matching engine.

## Message handling

ITCH 5.0, specification revision of April 2023. All 23 message types are recognised and
length-checked; the ones below change the book or the statistics.

| Type | Message | Effect |
|---|---|---|
| `R` | Stock directory | Records the symbol for the day's stock locate |
| `A` / `F` | Add order (with MPID for `F`) | New resting order; the order is never matched against the book |
| `E` | Order executed | Reduces the resting order at its display price; counts as volume |
| `C` | Order executed with price | Reduces the resting order; counts as volume only when printable |
| `X` | Order cancel | Reduces the displayed size; the order keeps its queue position |
| `D` | Order delete | Removes the order |
| `U` | Order replace | Removes the original; adds a new order with a new reference, same side and stock, at the back of its price level |
| `P` | Trade (non-cross) | Execution against non-displayed liquidity: volume only |
| `Q` | Cross trade | Auction print: volume only (zero shares means no cross) |
| `B` | Broken trade | Counted; no book effect |
| `S` | System event | `C` (end of messages) marks a complete day |

Book updates are never gated on trading-action (`H`) halts: the feed is authoritative.

The specification does not state queue priority. The table follows the common reading: a
replace carries a new reference number, so it is a new order and joins the back of its
level; a partial cancel only reduces the displayed size. A zero-length BinaryFILE record
marks the end of the session; files without one are accepted. Timestamps are nanoseconds
since midnight; the specification names no time zone, and US Eastern is the convention.

## Order book

| Piece | Implementation |
|---|---|
| Order | 32 bytes: reference, shares, price, level slot, FIFO links, stock locate, side |
| Order storage | `me::Slab` from the matching engine: fixed capacity, LIFO free list, pre-faulted |
| Reference index | `me::OpenAddrIndex`, one for the whole feed, because references are unique across the day |
| Levels | Per stock and side, a vector of `{price, level slot}` sorted with the best price at the back and searched from the touch; each level is an `me::Level` FIFO |
| Capacity | 4.2 M orders and 2.1 M levels by default, about 320 MiB; the peak on a busy Nasdaq day is about 2 M live orders |

The matching engine's `Store` is not reused as a whole: it holds one index per book, and a
feed has around 8,900 stocks. Its price ladder does not apply either, because ITCH prices
are not bounded to a small band (stub quotes reach 199,999.99); the sorted vector with
inline prices is the matching engine's lesson that carries over.

## Anomalies

A message that does not fit the book is counted and skipped, never fatal: an unknown order
reference, a duplicate reference, an execution or cancel larger than the open size (the
order is removed), or a full pool. `itch_replay` prints every counter and exits non-zero if
any is non-zero, so a clean day is one line to check.

The builder also rejects invalid add-side bytes and updates whose stock locate disagrees
with the referenced order, before changing the book or attributing volume. A rejected
replacement preserves the original order and its queue priority; failed level-vector
allocation cannot consume a slab slot. Full-day replay additionally requires non-empty,
complete framing, no records after the session end, system event C and no residual
orders. `--allow-partial` explicitly waives the last two lifecycle checks for excerpts.

## Validation

| Level | Check | Status |
|---|---|---|
| L0 | Framing identity: `sum(count × (length + 2)) + optional end record == file size`, no trailing bytes | Synthetic feed, official BX and canonical Nasdaq days: holds |
| L1 | Encoder and decoder agree field by field | Engine loopback (below) |
| L2 | Engine loopback: the matching engine publishes its events as ITCH; after every engine operation the rebuilt best bid and ask must equal the engine's, and at the end every book must match order by order | 5 M operations, 10 M touch comparisons, all equal |
| L3 | Lifecycle on a real Nasdaq day: zero unknown references, zero share underflows, zero live orders after end of messages | BX 2019-07-30 and canonical Nasdaq 2019-12-30: all checks pass; [record](VALIDATION.md) |
| L4 | Message census against an independent published census of the same named sample | Canonical Nasdaq: all 18 observed type counts and peak/final live-order counts agree; no external input hash or BBO comparison |
| L5 | Sampled BBO against a separately built reconstruction of identical raw bytes | Five instruments at one second; MSFT and QQQ also at 100 ms; exact price/size agreement; [method and controls](BBO_VALIDATION.md) |
| L6 | Deterministic observed-wire journal and raw/journal replay equivalence | Two canonical journal creations have the same digest; three replays match 27 checkpoints, 26 populated; [schema and evidence](JOURNAL.md) |
| L7 | Reference-index alternatives on identical real flow, including capacity profiles | Both builds match 269 Nasdaq and 29 BX checkpoints; 48 interleaved timing runs and separate streaming-memory passes; [protocol and results](STORAGE.md) |
| L8 | Synthetic causal queue rules, accounts and information eligibility | 22 C++ cases and 22 CLI methods pass Release and ASan/UBSan; 11 hand-worked scenarios repeat deterministically; future-aware mutation rejected; [scope and evidence](VALIDATION.md#bounded-synthetic-causal-queue-foundation) |
| L9 | Bounded source-to-normalised displayed-history projection | Two complete canonical source replays; 15 exact independent BBO seed/post-message states; real pre-opening rejection; focused Release/ASan fixtures; [scope and evidence](VALIDATION.md#canonical-bounded-displayed-history-projection) |
| L10 | Identified projection-to-simulator causal handoff | 24 fixed configurations, 284 exact event audits and independently frozen summary/final-state expectations; pending exposure and zero fills retained; [scope and evidence](HANDOFF.md) |
| L11 | Independent displayed orders, depth and reconstructed FIFO | 15 source-identified states, 16,886 exact ordered row instances and 5,665 level instances; full selected-symbol depth; [scope and evidence](L3_VALIDATION.md) |

Each row checks a different failure mode. The later internal comparisons do not add
an independent exchange/vendor oracle or establish every intermediate market state.

The journal adds an I/O layer around the original BinaryFILE bytes rather than changing
book semantics. Python verifies SHA-256 identity; C++ preflights the versioned container
and CRCs, then carries split frames across blocks into the existing dispatcher.
Post-message checkpoints fingerprint ordered resting orders, mappings, volumes and
builder counters. Common-core replay equivalence and independent sampled BBO agreement
are separate evidence; neither establishes every intermediate real-day FIFO state.

## Synthetic causal queue foundation

`itch_queue` is a separate standard-library-only component. Its normalised fixed-level
events deliberately do not bypass the wire decoder's validation or claim to be accepted
ITCH deltas. The bounded historical projector below supplies a separate provenance,
trading-state and equivalence contract; richer adapters need their own validation.

The scheduler orders equal times by market, feed, decision, arrival and response phases,
then insertion serial. All zero-delay generated children have later phases than their
parents. Decisions are preloaded local-time actions; responses never trigger another
same-time decision. Feed payloads capture immutable post-market snapshots.

The no-impact shadow model tracks external visible quantity, external volume ahead of
one hypothetical order, and own remaining quantity separately. External reductions are
applied once. Own fills update cash/position at exchange time and update the strategy's
known account only when their responses arrive. Price/quantity/fee and event-count
bounds keep accounting exact and memory finite. The
[full contract](QUEUE_SIMULATOR.md) defines cancellations, quote races and the horizon.

## Bounded displayed-history projection

`itch_window` combines the existing replica with a strict source-aware projector. It
checks a complete source lifecycle, retains original sequence/offset/timestamps, and
seeds after a whole timestamp group. Within the window it reconciles each selected
message's pre/post fixed-level quantity and opposite BBO price/size. Its emitted schema
has the queue model's external quantity and opposite price; its separate ledger also
retains exclusions and source references/matches.

Target replacements are rejected because the current queue schema cannot express
their atomic cancel/replace observation. Off-target replacement applies once before a
possible opposite-price quote is emitted. Selected priced executions and auction
context are excluded by rejecting the window. A later broken execution matching mapped
flow rejects the result before any output is created. These are declared scope checks,
not changes to reconstruction semantics or proof of real hypothetical fills. See
[HISTORICAL_WINDOW.md](HISTORICAL_WINDOW.md).

## Causal handoff evidence

`bench/audit_handoff.py` accepts the committed canonical projection aggregate and
checks retained output hashes, source deltas and source-point joins. It constructs
its own fixed simulator commands and independently computes the clock/queue contract
in Python. Originating market rows, latest delivered rows and captured action-decision
rows remain distinct, including when an order or cancellation response is pending.

The audit requires a clean committed `main`, fresh ignored detailed output and stable
input/tool/source identities. It retains process status and failure records, checks
every audit field and preserves the inclusive horizon. No C++ semantics are changed.
The raw-day identity is carried from the earlier committed full-source report rather
than reread. See [HANDOFF.md](HANDOFF.md) for the six profiles and restricted claims.
