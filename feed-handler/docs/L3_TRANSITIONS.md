# Independent canonical cancellation and replacement coverage

Gate 14 extends the [displayed L3 comparison](L3_VALIDATION.md) beyond its original
fifteen `A/D/E` states. This contract fixes selection before any new raw-data scan or
book comparison. It is a bounded reconstruction check. The identified observer,
transport/restart fixtures and queue/fill eligibility remain unchanged.

## Source and common semantics

Use the same canonical 2019-12-30 BinaryFILE: 8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
Freshly hash it before selection/replay and after comparison, with stable regular-file
identity checks. Hash the actual newly consumed prefix separately; do not substitute
the old 273,665,559-byte prefix identity for this experiment's boundary.

The retained primary reference is Nasdaq's
[TotalView-ITCH specification](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf),
1,200,722 bytes, SHA-256
`45e0531d1b4b3beb886e9618b2ab824a5aa9bda3a99c0dff03509306e68aacc3`.
Pages 15–16 define `X` cancellation as a quantity removed from displayed shares and
`U` replacement as removal of the old order plus a new reference, new total displayed
quantity and price. Replacement inherits side, symbol and attribution. The compared
APIs expose side/symbol, but not attribution or original order-priority timestamps.
Observe a `U` once after its complete wire message; expose no invented delete/add
midpoint. Replacement at the tail of its destination price level is the pinned books'
reconstruction convention, not independent proof of actual exchange priority.

Existing local and independent exporters already process `A/F/E/C/X/D/U`. `C` reduces
the named displayed order regardless of its printable flag; tape volume and execution
price are outside the common resting-order fields. `P/Q/B` are not displayed-inventory
mutations. A same-reference `U`, zero/oversized reduction, duplicate live reference or
other invalid input fails this gate. Keep the wrappers' different malformed-input and
allocation-failure policies distinct; never accept a failed helper run or partial export.

## Frozen selection rule

Version the rule as `first_x_u_four_windows_v1`. Its fixed symbols, in order, are
`MSFT` and `QQQ`, with expected canonical locates 5291 and 6556. Authenticate both
mappings from the prefix's actual `R` messages. Do not impose requested-symbol filename
restrictions on unrelated directory symbols.

Scan from byte zero. Count all nonempty global frames from one; retain zero-based
frame start and exclusive end offsets. Check complete BinaryFILE framing, known exact
message lengths, header fields and nondecreasing 48-bit timestamps throughout the
scanned prefix. Authenticate global `S(O)`, `S(S)`, then the first `S(Q)` in source order.
Let that market-open message be `q`. Its timestamp defines a search deadline, not a
claim of instrument tradability or strategy eligibility.

The selected book-mutation alphabet is exactly `M={A,F,E,C,X,D,U}`. For each fixed symbol
and each anchor type in order `X,U`:

1. Choose its **first** `M` occurrence of that anchor type with global sequence greater
   than `q.sequence` and timestamp strictly less than `q.timestamp + 1,000,000,000` ns.
2. The seed is the immediately preceding same-symbol `M` occurrence after `q`, or `q`
   itself if none exists. It denotes the complete post-message book, reconstructed
   from the start of the raw input. It is not an imported-order clock or reset point.
3. Admit the anchor and the next three same-symbol `M` occurrences, all before that
   same exclusive deadline. Request a checkpoint after each, irrespective of message
   type, BBO, queue position, quantity, trading status or eventual agreement.

This yields four windows, each with one seed and four contiguous selected mutations.
Deduplicate checkpoint requests only by `(symbol,global_sequence)`. Sort unique points
by global sequence and then fixed symbol order; assign consecutive state IDs. Preserve
all window/role-to-state links when windows overlap. A shared global source point may
request both symbols. Source order resolves timestamp ties; never sort by reference.

Stop successfully at the last required tail frame, without scanning future outcomes
to improve selection. Hard limits are 16,000,000 nonempty global frames and a consumed
frame end of 536,870,912 bytes. A frame cannot straddle that byte cap. A deadline, cap,
EOF, missing anchor/tail, directory conflict, framing or identity violation fails the
whole selection. Retain its first witness and partial origins; do not widen the time,
change symbols or substitute a later anchor. Keep scan-consumed and replay-prefix ends
separate if a failure witness extends beyond the last requested state.

No filter may depend on reconstructed orders, quote quality, partial/full cancellation,
same/moved replacement price, queue rank, reference reuse history or comparator results.
Classify those observations only after independently checked inventories are available.
The finite source-point windows do not claim to cover a whole timestamp group or every
event in the one-second search horizon.

## Private selection artefacts and independent enumeration

Add a private selector and orchestration wrapper in the sibling harness; preserve all
earlier helpers, binaries, source archives and CMake files. The canonical selector CLI
accepts only a fresh ignored output directory and uses the fixed authenticated raw file.
Its reusable parser may accept hand-encoded private fixtures for focused boundary tests;
there is no public bypass or new public reconstruction implementation.

Write `checkpoints.csv` in the existing exact schema:

```text
state_id,symbol,locate,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type
```

Write `census.csv` with all selected-locate messages in each window's seed-exclusive,
tail-inclusive source interval, before filtering to `M`:

```text
window_id,symbol,locate,sequence,frame_offset,frame_end_offset,timestamp_ns,body_bytes,type,frame_sha256
```

Repeated membership in overlapping windows is explicit. Reconcile the mutation
subsequence exactly with its four admitted facts. Cap each window census at 4,096
rows, total captured selected-locate headers after `S(Q)` at 100,000 and each artefact
at 8 MiB. Before `S(Q)`, retain directory/system origins without storing all selected
headers; the raw prefix still supplies the reconstructed seed's complete history.
Keep at most twenty unique requested checkpoints; the unchanged exporters' broader
256-state and one-million-total-exported-order bounds still apply.

Publish `selection.json` last, after checked writes/closes. It identifies the rule,
contract/source/input hashes, directory/system-event origins, exact selected roles,
source point fields, original framed bytes and frame/body digests, census/checkpoint
identities, prefix identity and selection bounds. Per-event content stays ignored.
Failed runs retain a separate failure receipt and source snapshot, never a success
manifest. Preserve owned-file safety on publication failures and require fresh paths.

A separately written enumeration must scan the same authenticated prefix and recover
the four first anchors, contiguous tails, seeds, deduplicated request list, all role
links and census independently. It must not import the selector or inspect book output.
Verify this before either new book export. A changed origin, missed earlier anchor or
omitted mutation must fail, even if later book states would happen to agree.

## Reuse the existing exporters and comparator

Use the unchanged local and pinned `itchbook` wrappers and their accepted Release
binaries. Their interface remains:

```text
HELPER INPUT CHECKPOINTS_CSV ORDERS_CSV SUMMARY_JSON
```

The independent implementation is MIT-licensed `KareemJandali/itchbook` revision
`3c646f9da182136125059243b475f7b8baa53773`. Authenticate its retained source archive and
all 54 headers plus `CMakeLists.txt`/`LICENSE` bytes against that archive. It is an extracted source
tree, not an upstream Git checkout; inherited parent-repository HEAD is not its revision.
Pin both helper sources/binaries and their earlier accepted evidence. Verify the current
local reconstruction source against its earlier compiled baseline; record retained-build
provenance rather than implying a new compilation or sanitised historical replay.

Pass the same frozen checkpoint list to both exporters. Independently require every
returned manifest state to match the exact requested source point, including the
global `S(Q)` boundary if used as a seed. Require zero validation counters, successful
checked output publication and complete exports including explicitly empty sides or
books. Never omit such a state or reselect merely to obtain a populated side. Preserve
the comparator's aggregate coverage requirements; inadequate coverage is a retained
failure, not permission to choose a different window.
Use unchanged `bench/compare_l3.py` for exact full FIFO/order/level/BBO reconciliation.
Preserve its common field/price/quantity domains and explicit completeness requirements.
The local helper validates all symbols in the prefix; the reference validates selected
symbols while checking framing/timestamps throughout. Record these scopes separately.

After state agreement, independently audit the selected `X/U` deltas against exact wire
fields and copied pre/post inventories. For `X`, distinguish a partial quantity change
from complete depletion and check unaffected orders/relative FIFO. For `U`, require old
reference removal, the new total quantity/price, inherited side and destination FIFO
under the declared convention. Do not dereference a removed old-order pointer. Classify
observed same/moved price and BBO effects without demanding favourable examples.
Synthetic controls may exercise missing real categories; label them separately.

## Acceptance and publication

Before raw selection, review/freeze this contract and the selector's concrete source.
Use small hand-frozen fixtures for selection order, ties, adjacent/overlapping windows,
global seed, missing anchors/tails and bounds. Independently freeze the request list
before book execution. Retain exact commands, exit statuses, stderr, checked source,
input/prefix/reference/helper/comparator identities and before/after stability guards.
Repeat the unchanged producers once on the same requests to check exact output identity;
do not infer throughput from recorder timings. Keep raw data and all per-order/event
artefacts ignored. Version aggregate coverage, source/input identities, first differences,
rejections, fresh-versus-retained qualifications and the reproducible command.

This gate adds only the newly observed independent states actually compared. Account
for overlap among the four windows and with the earlier fifteen states explicitly.
It establishes neither every-message full-day FIFO nor actual exchange priority,
attribution, hidden liquidity, causal order eligibility, hypothetical fills, live recovery
or strategy performance. Expanding the restricted `A/D/E` observer remains separate work.
