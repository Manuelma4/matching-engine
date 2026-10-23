# Price-level search experiment: frozen contract

Gate 17 is a source-reviewed design milestone. It selects one experiment and fixes
acceptance before implementation or timing. There is no new measured result here.
The existing [reference-index measurements](STORAGE.md) remain separate evidence.

## Question and decision

Compare reverse-linear search from the best price with binary search within the
**same sorted vector of price/level-slot entries**. The question is whether changing
search alone helps complete Nasdaq and BX reconstruction on this host. It does not
compare vector storage with a tree, establish a memory saving or explain CPU events.
Keep reverse-linear as the production default regardless of this experiment's result;
any later default change needs its own evidence and review.

The inspected baseline is feed commit
`d368267b0544497f18c101486aa579b519bf2d75`, with engine checkout
`dbd280185a0d45f0839881caeff8d535bcd56779`. The latter is documentation-only after
the pinned engine implementation `01656701c973036d88724fbe2d27fa5b98f55cd4`.
The [design record](validation/2026-10-23-level-search-design/design.json) retains
the inspected implementation and private-harness identities.

An ordered tree is deferred: it changes node allocation, per-locate layout and
replacement preparation. Current replacement relies on retained vector capacity
when unlinking the sole old order frees its level. A tree would need a separate
transaction design, including singleton same-price replacement. A dense price ladder
is also deferred: the feed has sparse unsigned Price(4) values across 65,536 locates,
without the matching engine's configured price band. Neither is a clean search-only
experiment. This is a deliberate reduction in scope, not evidence that trees lose.

## Source cost model

`include/itch/book.hpp` defines per-locate, per-side vectors of inline price/slot
entries. Bids ascend and asks descend in storage; the best entry is `back()`.
One global level slab and one global order slab hold the actual levels and FIFO links.
The feed does not reserve each vector's capacity in advance. Engine `VecLevels`
does reserve capacity and has different book/pool bounds; its timings do not predict
this feed's performance.

For n populated levels on one locate/side, and d entries nearer the best price:

| Operation in current `src/book.cpp` | Search or movement cost |
|---|---|
| Existing price lookup / insertion-position search | From the touch, O(d + 1), worst O(n) |
| New level insertion / empty level erasure | Search, then O(d) entry shifts; insertion can also grow the vector |
| Best price / level count | Constant time through vector metadata |
| Partial E/C/X reduction | Direct order and level slots; no price-directory search |
| D or full reduction | Directory search/erase only when its final order leaves |
| U | Destination lookup, possible reservation, old-level release, then destination lookup/create |

The candidate reduces the search bound to O(log n) comparisons. It retains entry
shifts, capacity growth and allocation ordering. For activity near the touch, a few
contiguous linear probes can be cheaper than binary probes. These are source-derived
cost bounds and hypotheses; no comparison counts, cache misses or timings were measured.

## Candidate and invariants

Use build-time `ITCH_LEVEL_SEARCH=reverse_linear|binary`, with reverse-linear the
default. Map this to `ITCH_BINARY_LEVEL_SEARCH=0|1`, respectively. Propagate that
numeric definition to all consumers and expose a stable
`level_search` label in correctness and benchmark reports. Reject unknown options.
Use separate build directories in the existing main checkout, never Git branches.

Only the three directory searches in `find_level`, `find_or_create_level` and
`release_level` may differ. Binary search computes the sorted insertion position:
bids compare `entry.price < target`, asks `entry.price > target`. Equality determines
membership. Use unsigned comparisons, without negation, subtraction or narrowing.
Keep the original reverse-linear path unchanged. There is no runtime policy dispatch
inside the event loop and no representation, level-pool or FIFO change.

All of the following remain fixed:

- `open_addressed` reference index for the measurement matrix; existing standard-index
  compatibility and allocation tests still pass separately.
- Order/level structure layout, global slab capacities, slot acquisition/release order,
  vector ordering, level totals/counts, intrusive FIFO and public API semantics.
- Existing add rollback and all throwing replacement preparation before unlink.
  Destination reservation must not leave an empty directory entry on failure.
  The full-pool singleton path, singleton same-price U and same-reference U keep
  their current behaviour and allocation guarantees.
- No retained vector pointers or iterators across insertion, erasure or replacement
  preparation. Stable slab slots do not make vector iterators stable. Recompute a
  search position after any intervening mutation.
- Existing wire validation, journal bytes/fingerprint versions, independent reference
  revision, observer, transport, queue and fill rules.

The direct book API's unsigned price endpoints, zero and UINT32_MAX, must continue
to work. This is API compatibility, not admission of such prices by historical
wire validators or the retained independent exporter.

## Correctness before measurement

Freeze explicit private expected rows before executing the candidate. Reuse existing
harnesses and add four focused control families, with expectations derived from
orders and arithmetic rather than by calling the alternative under test:

1. Insert best, middle and worst prices on both sides, including empty/singleton
   vectors, misses between/outside prices, both unsigned endpoints and equal prices
   in different locates. Assert full best-first traversal and per-price FIFO lookup;
   force vector growth and retain unaffected order/level slots across it.
2. Remove final orders at best/middle/worst prices, erase/reinsert and reuse released
   slots, keeping another locate live. Assert exact levels, aggregates, order lookups,
   missing-price empty queues, counts and absence of ghost empty entries.
3. Reduce a non-head order without changing its rank, then replace into a populated
   destination and at the same price. Assert new total quantity, tail insertion and
   exact queues. For example `[10:40, 11:30]` at bid 100 and `[20:50]` at bid 101;
   X(11,5) leaves `[10:40, 11:25]`; U(10→12,60,101) leaves `[11:25]` and
   `[20:50, 12:60]`; U(20→21,35,101) leaves `[12:60, 21:35]`, total 95.
4. Reuse the existing thirteen allocation/replacement-failure methods and extend their
   complete API reconciliation where needed. Failure at each allocating preparation
   preserves the exact old state and permits a successful retry. Verify full-pool
   reuse and no allocating commit for singleton same-price/full-pool paths under the
   flat index. The standard index retains its separately allocating mapping rules.

For both policies, focused assertions reconcile `visit`, `for_each_level`,
`for_each_order`, `find`, `best` and `level_count` with explicit ordered rows, including
deep levels invisible to BBO. Add a private, BBO-preserving bad deep-price lookup
control that fails the exact per-price check. Retain its expected failure separately.
Run relevant existing book/replay/snapshot, journal and benchmark/runner checks in
Release and ASan/UBSan for both policies. Check standard-index compatibility under
both policies/profiles as a separate correctness matrix: eight policy/index/profile
builds in total, with standard-only skips reported for flat-index builds. Only the
two unsanitised flat-index builds enter the real-flow measurement matrix. Do not
rerun unrelated transport/observer matrices solely because a build directory is new.
Record names, skips and diagnostics.

Rebuild the unchanged private `independent_l3_local.cpp` for each policy. Run the
same two retained request sets (15 earlier points and 20 X/U points) and require
exact ordered CSV agreement with their authenticated independent exports, plus
semantic summary/source-boundary agreement. Its internal reconciliation checks
visitation against order lookups, level aggregates, best and counts. The focused
tests additionally exercise `for_each_order`. These four untimed prefix replays
reuse **35 distinct states**, not new reference executions or new historical samples.
Keep its existing bounds/positive-price validator and preserve original request IDs.
Each prefix child has the same 1,800-second timeout as a full replay. The earlier
request set ends at byte 273,665,559; the X/U set ends at byte 284,563,784, global
frame 8,300,042. Authenticate these bounds from the retained requests/reports and
reject any changed end. These limits bound consumed framing, not the helper's
whole-file virtual mapping or an independent cryptographic input check.

Then require eight complete raw correctness replays: two policies × two flows × two
capacity profiles, checkpointed every 1,000,000 messages. Compare identical ordered
checkpoint CSV bytes and semantic summaries within each flow, including all counters,
peak/final orders, lifecycle and zero anomalies. Expected coverage is 269 checkpoints
for Nasdaq and 29 for BX, including respectively 268 and 28 populated points.
These unchanged non-cryptographic order/state fingerprints are regression checks;
they omit some directory aggregates and empty entries. They do not establish full
directory equality at every checkpoint. Exact independent directory/FIFO agreement
is limited to the retained 35 points; focused fixtures cover additional API states.
Every intervening historical state remains outside the independent sample.

## Fixed finite measurement matrix

| Flow | Raw bytes | Default orders / levels | Fitted orders / levels |
|---|---:|---:|---:|
| Nasdaq 2019-12-30 | 8,251,407,909 | 4,194,304 / 2,097,152 | 2,097,152 / 2,097,152 |
| BX 2019-07-30 | 837,472,908 | 4,194,304 / 2,097,152 | 131,072 / 131,072 |

Authenticate both complete raw hashes against accepted Gate 3 records before execution
and again afterwards, checking file identity around hashing/children. Retain the current
feed/engine implementation snapshot, clean-main commits, source/build/compiler flags,
cache options, compiler executable/version, tool hashes, commands and reference artefact
hashes. A changed identity invalidates publication; never silently adopt a new baseline.

Use a separate narrowly scoped comparison runner. Preserve `compare_storage.py` and
its old records: its reference-index options, label checks and permitted flag difference
do not certify this new experiment. Reuse its parsing/validation routines only where
their contracts fit without monkeypatching globals or relabelling results. Both builds
must fix `ITCH_REFERENCE_INDEX=open_addressed`, Release, identical compiler/optimisation
and dependency bytes, and no sanitiser flags. Verify actual generated compile/link
commands as well as requested cache options. Permit only the declared search definition
and build-directory paths to differ. Reject identical candidate/baseline executable
bytes, missing/incorrect labels, malformed summaries, diagnostics or missing checkpoints.

After all correctness gates pass, launch eight separate streaming memory children,
one per policy/flow/profile. Then run six fresh timing children per configuration:
48 timing runs. Together with eight full correctness children this is 64 full-day
replays, plus the four untimed retained-state prefix replays. Run one child at a time,
without concurrent builds, validation or other heavy project work. Set a 1,800-second
timeout per full replay; retain timeout/failure logs and publish no partial winner.
Keep all raw, checkpoint, per-order and child output under ignored `out/` storage.

For timing round r=0…5, pair order is AB, BA, BA, AB, AB, BA, with A=reverse_linear
and B=binary. Each policy runs first three times. Rotate the four flow/profile groups
by r positions, using a fixed starting order Nasdaq-default, Nasdaq-fit, BX-default,
BX-fit. Record every actual launch position. No unreported warm-up or discarded outlier.
Report each policy's six replay durations, median, minimum, maximum and paired B/A
ratios; distinguish pair order and profile. Preserve slower/inconclusive results.

Retain existing `itch_storage_bench` timing boundaries: construction separate; mmap,
prefault and framing/type/after-end placement preflight before the replay timer;
dispatch/framing and replay allocations inside. Required S(C), final empty-book and
semantic-anomaly acceptance checks occur after replay, along with final hashes and
summary extraction, outside the replay timer. Destruction is outside it too, with
teardown recorded separately. The memory mode streams through its
existing bounded buffer. Its elapsed time includes I/O/checks and is not a replay
timing sample. Whole-process RSS high-water marks, sampled immediately after replay
before final hashing/destruction, include pools, vectors, allocator, program and input
buffer. One pass per configuration estimates no RSS variability;
unchanged storage predicts no particular observed RSS difference. Do not subtract
high-water marks to claim isolated directory memory.

Freshly record actual host/OS/CPU/RAM, compiler, build flags, power source and observable
load conditions. Previous host descriptions are historical evidence. Without controlled
cache state, CPU affinity, thermal conditions or frequency, report this as prefaulted
mapped-input throughput on that host. No cold-cache, live latency, tail latency,
allocation-count, cache-miss, hardware-counter or Linux-performance claim follows.

## Completion and follow-on

Gate 17 completes when independent source, correctness and protocol reviews resolve
material issues and this contract plus inspected identities are committed on main.
That design acceptance executes no implementation, build, test, raw read or benchmark.
Gate 18 implements only this candidate and runs the fixed acceptance protocol. Retain
its first failures, complete raw measurements and aggregate evidence in a separate
runtime record; explain any amended protocol before execution and never back-fit it
to results. A negative or inconclusive outcome is a successful experiment. Neither
gate expands transport admission, simulator eligibility or empirical fill claims.
