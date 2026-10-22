# Design

## Layers

```
            add_limit / add_market / modify / cancel
                              |
                     +--------v--------+
                     |   Book<Store>   |   matching: price-time priority, IOC market
                     +--------+--------+   orders, exchange-style modify
                              |
          +-------------------v-------------------+
          |         Store<Levels, Index>          |   resting orders only; never matches
          |  +-----------+  +--------+  +-------+ |
          |  | OrderPool |  | Levels |  | Index | |
          |  +-----------+  +--------+  +-------+ |
          +---------------------------------------+
```

`Store` owns the resting orders and knows nothing about matching. The ITCH feed handler
shares the slab, level FIFO and open-addressing index primitives, rather than the entire
store: it needs one global reference index across instruments. Its replica applies feed
events without crossing orders.
`Book` adds the matching rules on top and has the same interface as the original `BookV1`,
which is kept as the behavioural reference. `BookV1` only received the validation rules
shared by every variant and an exception-safety fix; its containers and matching are those
of the first version.

## Data structures

| Piece | Implementation | Notes |
|---|---|---|
| Order | 32 bytes: id, qty, level slot, prev/next slots, side | Four per 128-byte cache line on Apple Silicon. The price lives in the level |
| Level | 32 bytes: price, total qty, FIFO head/tail, order count | `volume_at` is O(1) |
| Order pool | One `std::vector<Order>` sized to `max_orders`, free list threaded through `next` | Freed slots are reused LIFO, so the most recently freed, cache-hot slot comes back first. Construction writes every element, which pre-faults the pages |
| FIFO per level | Intrusive doubly linked list of order slots | Append, unlink and move-to-back are O(1) with no separate nodes |
| Order index | `OpenAddrIndex`: 16-byte entries, power-of-two table of at least `2 * max_orders` | Load factor never exceeds 0.5 and the table never rehashes. fmix64 hash, linear probing, backward-shift deletion (no tombstones) |
| Levels (default) | `LadderLevels`: a `Level` for every price in the band, indexed by `price - band_low` | Finding or creating a level is one array access |
| Best price | Cached per side, with a three-level, 64-way occupancy bitmap | When the best level empties, the next one is the bitmap's highest bid or lowest ask: three count-zero instructions, however many empty ticks lie between levels |

Slots are 32-bit indices into preallocated arrays rather than pointers: half the size, and
never invalidated, because nothing is reallocated after construction.

### Variants

Each variant changes one container relative to the previous one, so each effect can be
measured on its own. All of them produce the same event stream (see
[BENCHMARKS.md](BENCHMARKS.md)).

| Variant | Levels | Index | Per-operation allocation |
|---|---|---|---|
| `BookV1` | `std::map<Price, std::list<Order>>` | `std::unordered_map` | list node and hash node per order, map node per level |
| `BookMap` | `std::map<Price, Slot>` + level pool | `std::unordered_map` | hash node per order, map node per level |
| `BookMapOA` | `std::map<Price, Slot>` + level pool | `OpenAddrIndex` | map node per level |
| `BookVec` | sorted vector of `{price, level slot}`, best at the back | `OpenAddrIndex` | none |
| `BookLadder` (default `OrderBook`) | price ladder + bitmap | `OpenAddrIndex` | none |

### Memory

With the default configuration (`max_orders = 2^20`, a band of `2^16` ticks):

| Piece | Size |
|---|---|
| Order pool | 2^20 × 32 B = 32 MiB |
| Order index | 2^21 × 16 B = 32 MiB |
| Price ladder | 2 sides × 2^16 × 32 B = 4 MiB |
| Bitmaps | 2 × 8.3 KiB |
| **Total** | **about 68 MiB, all allocated and touched in the constructor** |

The `std::map` and vector variants size their level pools to `min(2^band_log2, max_orders)`
per side: a level is released as soon as its last order leaves, so live levels never
exceed live orders.

## Semantics

- **Priority.** Price, then time. A trade executes at the resting order's price.
- **Limit orders** match against the opposite side up to their limit price; any remainder
  rests at the back of its level.
- **Market orders** never rest: the unfilled remainder is cancelled (IOC).
- **Modify** follows Nasdaq Rule 4756 (SEC Release 34-68762): a size reduction at the same
  price keeps priority; any other change gets a new timestamp. Concretely, an increase
  moves the order to the back of its level, and a new price takes it out of the queue and
  re-enters it through matching, so it may trade. `new_qty` is the new open quantity.
  The order keeps its slot and index entry throughout, so a price-change modify neither
  frees nor allocates.
- **Validation** happens before anything is changed, so a rejected request leaves the book
  exactly as it was and emits no trades. The checks, in order:

  | Request | Checks |
  |---|---|
  | `add_limit` | quantity > 0, price > 0, price in band, id ≠ 0, id not resting, pool not full |
  | `add_market` | quantity > 0, id ≠ 0, id not resting |
  | `modify` | quantity > 0, price > 0, price in band, id resting |
  | `cancel` | id resting (otherwise returns `false`) |

- **Price band.** Limit prices and modify prices must lie in
  `[band_low, band_low + 2^band_log2)`. This is an engine-level price collar, stricter than
  exchange price banding (which typically rejects only aggressive prices far from the last
  trade). It bounds the price ladder, and every variant applies it so all of them behave
  identically.
- **Capacity.** The pool holds `max_orders` resting orders. A limit order is rejected up
  front when the pool is full, even if it would have filled completely; market orders and
  modifies never need a new slot.
- **Order id 0** is reserved: the index uses key 0 to mark empty entries.
- **Configuration** is validated once, at construction: `max_orders` must lie in
  `[1, 2^32 - 2]` (slot `2^32 - 1` is the null slot) and `band_log2` must be at most 62, or
  18 for the price ladder. The band check computes the distance from `band_low` unsigned, so
  no configuration can overflow it.
- **Allocation failure.** Only the `std::map` and `std::unordered_map` containers can
  throw, and only `BookV1` and `BookMap` use them per order. Resting an order creates its
  level before taking a pool slot and rolls back if indexing throws, so a failed insert
  changes nothing. If the caller's trade buffer cannot grow during a price-changing modify,
  the order is dropped as a cancel, as `BookV1` does, never left indexed outside a queue.

## Invariants

Checked after every operation by the private verification harness (below), directly or by
comparison with the reference book:

1. Every resting order is in exactly one level FIFO and in the index; the index, the pool
   and `order_count()` agree.
2. A level's total equals the sum of its orders' quantities, and its count equals their
   number. An empty level is released at once and is never visible.
3. In the ladder, a bitmap bit is set exactly when its level is non-empty, and the cached
   best equals the highest set bid and the lowest set ask.
4. The book is never crossed at rest: after any operation, best bid < best ask.
5. `filled + resting + cancelled` equals the requested quantity.

## Verification

The test suite is kept outside this repository and is available on request. It consists of:

- Typed unit tests run against all five variants: priority rules, modify cases, partial
  fills, multi-level sweeps, rejects, capacity, the price band, sparse levels across the
  whole band, the L3 visitor, configuration edge cases, and allocation failure injected at
  each allocation of an insert and at the trade buffer of a price-changing modify.
- Direct tests of `OpenAddrIndex` against `std::unordered_map` at 50% load with a small
  table (many collisions and wrap-arounds), and of the bitmap against `std::set` for band
  sizes from 2^3 to 2^18.
- A differential fuzzer that replays random operation streams through each variant and a
  naive linear-scan reference book, compares every report, every trade, best prices, level
  counts, per-price volumes and the exact queue order at every price after every
  operation, and shrinks any divergence to a minimal reproduction. It runs with and
  without a small capacity, and under AddressSanitizer and UndefinedBehaviorSanitizer.

The public evidence is the event-stream hash in [BENCHMARKS.md](BENCHMARKS.md): on every
regime, all variants produce byte-identical output.
