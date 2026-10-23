# A source-traceable displayed-history window

`itch_queue_window` projects a deliberately narrow part of a full BinaryFILE into the
fixed-level queue model's four-column input schema. It exports external observations,
not hypothetical fills. A provenance ledger retains every selected-symbol message in
the interval, including observations that produce no normalised event.

The adapter replays the entire source through `BookBuilder`. It seeds the window from
that reconstructed state and checks the represented quantity and opposite price before
and after every selected message. Opposite sizes are also retained in the ledger, even
though the queue input models only the opposite price. This separation prevents an
unrepresented size update from becoming an invented execution.

## What the source establishes

Nasdaq's [ITCH 5.0 specification](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf)
distinguishes displayed executions (`E`), executions with a different price (`C`),
non-displayed prints (`P`), cross prints (`Q`) and broken executions (`B`). The printable
flag affects volume reporting; it does not undo a displayed reduction. Replacement
`U` supplies the old reference and new order details in one message. `K` names a stock
but uses locate zero. The relevant sections are 1.1, 1.2, 1.4 and 1.5.

Reading identity: April 28, 2023 revision, retrieved 2026-10-22, 1,200,722 bytes,
SHA-256 `45e0531d1b4b3beb886e9618b2ab824a5aa9bda3a99c0dff03509306e68aacc3`.
The downloaded PDF stays in ignored reference storage. This is a later specification
reading applied to the observed 2019 message layouts; it is not a newly discovered
2019 exchange validation report.

An `E` identifies a resting-order execution, not the full size or identity of an
incoming aggressor. Nasdaq's [indexed FAQ text, page 3](https://www.nasdaqtrader.com/Content/TechnicalSupport/FAQs/ITCH_FAQ.pdf)
also distinguishes an execution's match number from a multi-fill incoming order.
Live FAQ retrieval returned HTML/error during this session, so no FAQ PDF digest is
claimed. Inference: the supported execution fields do not establish an aggressor or
atomic transaction boundary. The adapter does not aggregate by match number or
timestamp to invent one.

## Deliberate version-1 eligibility rules

These are the adapter's restrictions, rather than a complete exchange order-entry
eligibility model:

- One production symbol with a unique directory mapping and matching stock text/locate.
  Supported ticker text has one to eight uppercase letters, digits or `.-^/`.
- A buy window fixes the best bid; a sell window fixes the best ask. That price must
  remain the positive same-side best after every selected source message. Both sides
  must remain present, positive, uncrossed and within the one-billion price/size bound.
- Before seeding: system market hours have started, the latest selected trading action
  is `T`, and the selected stock's latest completed cross is its opening cross `O`.
  A market-hours flag alone does not establish that the stock has completed its cross.
- The latest announced Nasdaq operational state cannot be halted. An absent `h` is
  recorded as no announcement observed, not an invented normal-status message.
  Any MWCB breach before or during the interval excludes it; v1 has no resumption rule.
- Active legacy retail-interest indications are unsupported. Absence is recorded as
  unknown; this check does not establish the absence of hidden liquidity.
- A selected-stock IPO announcement `K` before or during the interval is unsupported.
  Its zero locate is handled explicitly. Selected `C`, `Q`, `I`, `J` or direct-listing
  `O` within the interval are rejected rather than converted into regular flow.

The source must begin with system `O`, then contain `S/Q/M/E/C` in order. Every raw
timestamp must be non-decreasing; the adapter never sorts wire observations. Framing,
known lengths, directory uniqueness, the existing builder's anomaly counters and a
complete empty-book lifecycle must pass. The optional BinaryFILE zero-length end
record can appear once after system C. Empty-book completion is this validation
criterion, not a universal claim about every market-data feed.

The book uses positive capacities no larger than its default 4,194,304 orders and
2,097,152 levels. Configuration is checked before allocating those pools. The interval
contains at most 99,999 selected messages plus its seed: at most 100,000 provenance
and normalised rows each. The source itself can contain the full day.

## Boundaries and mappings

The interval is `(start_ns, end_ns]`. All source messages at `start_ns` are incorporated
before the seed. Every message at `end_ns` is included. The seed is an explicitly
derived observation at `start_ns`; its source point is the last whole-source message
at or before that boundary, which can belong to another symbol. It is not presented
as an exchange-published snapshot. Later feed/order/response scheduling is outside
this adapter.

| Source event within the interval | Version-1 projection |
|---|---|
| `A/F` at the configured own-side price | `add` with its displayed shares |
| `X` at that price | `cancel` with its removed shares |
| `D` at that price | `cancel` with the resting order's complete remaining shares |
| `E` at that price | `trade` with observed displayed execution shares; no aggressor inference |
| Any selected `E` away from its side's pre-message best price | Reject as outside this continuous best-level scope |
| `U` removing or adding at the configured own-side price | Reject; a compound atomic normalised interface is required |
| Other `U` | Apply once to L3, then emit at most one opposite-price observation |
| Opposite best price changes | One `quote` containing the resulting opposite price |
| Opposite quantity changes without a price change | Ledger update only; the queue schema does not model this size |
| `P` | Explicit non-displayed-print exclusion, never own-side `trade` |
| Unrelated `B` | Ledger exclusion, with the match identity retained |
| A later `B` matching any projected own-level `E` | Reject the entire projection, even after the interval ends |
| Other supported metadata or away-level changes | Reconcile and retain a no-represented-change ledger row |

References and execution match identities are copied before dispatch, which can erase
or reuse an order slot. A target replacement is never split into independently visible
cancel/add snapshots. Off-target replacements can therefore expose only the resulting
opposite quote, preserving the source message's atomic observation.

The entire input is replayed before output creation. This catches a later broken
execution and establishes complete source coverage. Rejecting a later correction is
retrospective data validation, not information available to a strategy at execution.

## CLI and retained provenance

Build from the repository root:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine
cmake --build build --target itch_queue_window -j 4
mkdir -p out
mkdir out/window-example-1
./build/itch_queue_window --symbol MSFT --side buy --price4 1589000 \
  --start-ns 34214907518545 --end-ns 34214938994341 \
  --out out/window-example-1/MSFT.csv \
  --provenance out/window-example-1/MSFT.provenance.csv \
  data/12302019.NASDAQ_ITCH50.itch > out/window-example-1/MSFT.json
```

`--max-orders N` optionally reduces order capacity; level capacity becomes the smaller
of the default level count and that order count. Unsigned values reject signs,
whitespace, overflow and partial strings. Duplicate flags, stdin, empty/non-regular
input, non-fresh output paths and invalid configurations fail with exit code 1.

Normalised CSV: `timestamp_ns,kind,quantity,opposite_price4`, exactly the schema in
[QUEUE_SIMULATOR.md](QUEUE_SIMULATOR.md). A provenance row has the absolute source
sequence, frame offset, original timestamp, body length/type, reason, old/new references,
match, pre/post own quantity and opposite price/size, and a one-based normalised-row
index. Index zero identifies an excluded observation; the seed has index one.

The JSON schema is version 1, model `strict_displayed_window_v1`. It records window
configuration, capacities, source and window type counts, source coverage, row counts,
qualified own-level displayed execution shares, final window quotes and the source
points supporting seed eligibility. It contains no fill, fee or P&L result.

The input is mapped through the same regular-file descriptor that was checked; inode,
size and modification metadata are compared before/after projection/output. This
stability flag is not a cryptographic identity check. Evidence runs separately retain
SHA-256 identities for the full raw input, output files, source and binaries. Fresh
paired outputs are checked on write/close; a failed creation/write removes only new
files still owned by the run. Successful stdout flushing is also required.

## Limits before any historical fill experiment

An external-state projection can match every observed quote in a window and still
leave hypothetical fills uncertain. Hidden demand, exchange priority exceptions,
market response, parent-order grouping and changing levels remain outside this model.
The source's order references could support a richer identified queue model later;
the present queue input deliberately uses cancellation assumptions instead.

Choosing an interval because its best price stays constant is a retrospective sample
filter. These windows are adapter checks, not a causal strategy selection rule or a
representative performance sample. Rejections must remain visible rather than being
silently removed from a profitable result. No real-data queue-fill or strategy-P&L
claim follows from this increment.
