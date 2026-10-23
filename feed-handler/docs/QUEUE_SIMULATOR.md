# A bounded causal queue simulator

`itch_queue_sim` evaluates one hypothetical passive order at one fixed price against
a synthetic, normalised external-liquidity trace. It is an executable teaching model
with explicit event ordering, information delays, cancellation assumptions and accounts.
A successful run validates those rules; it does not establish empirical fill accuracy.

Start with the [self-contained C++ API example](QUEUE_DEMO.md) to see four literal
events, two cancellation assumptions and a pending response without preparing a CSV.

The simulator is separate from the validated ITCH reconstruction and observed-wire
journal. Its input is the CSV described below, not raw ITCH. The separate
[bounded historical projector](HISTORICAL_WINDOW.md) can export that schema while
retaining source provenance; it does not validate hypothetical fills. Multi-level
matching, hidden-liquidity modelling, market impact, a gateway and a strategy optimiser
remain outside this simulator.

## External observations and a shadow order

Choose one side and fixed `price4`. External quantity `Q` is the displayed quantity at
that level in the synthetic source, excluding our order. Our shadow state tracks
quantity ahead `A` and our remaining quantity `R`. Source events never include our
hypothetical order, and our fills/cancellation never rewrite the external trace.

At order arrival, acceptance puts all current external quantity ahead: `A = Q`.
Subsequent external additions increase `Q` and join behind the shadow order, leaving
`A` unchanged. Reductions of size `x` must satisfy `0 < x <= Q`.

For a trade while the order is live:

```text
fill = min(R, max(0, x - A_before))
A_after = max(0, A_before - x)
R_after = R_before - fill
Q_after = Q_before - x
```

The source's `Q` is depleted exactly once; do not subtract the shadow fill again.
This is an overlay on an unchanged external path, not conservation of a combined
historical-plus-hypothetical order book. It assumes the added order does not change
future external events. That counterfactual assumption limits interpretation.

A cancellation contains no order identities, so it cannot reveal which shares were
ahead. `optimistic` removes ahead shares first: `A_after = max(0, A_before - x)`.
`conservative` removes behind shares first: `A_after = min(A_before, Q_before - x)`.
Both set `Q_after = Q_before - x` and leave `R` unchanged. These names describe two
queue assumptions, not calibrated probabilities or guarantees about actual executions.

## Clocks and equal-time events

The model uses a common integer-nanosecond scheduling timeline with separate exchange
and local information states. It models fixed delivery delays, rather than independent
clock drift, timestamp uncertainty or a calibrated network.

An exchange market event at `t` creates an immutable post-event feed snapshot delivered
at `t + feed_delay_ns`. The local decision can read only delivered snapshots; it cannot
inspect the current exchange state. A request sent locally at `s` arrives at
`s + order_delay_ns`. An exchange acknowledgement, fill or cancellation result at `u`
becomes locally known at `u + response_delay_ns`.

At equal scheduled time, the phases are:

| Phase | Events | Ordering within the phase |
|---:|---|---|
| 1 | External market updates | Original CSV row order |
| 2 | Feed deliveries | Stable scheduling serial |
| 3 | Fixed submit/cancel decisions | Stable serial; submit precedes cancel when equal |
| 4 | Request arrivals at the exchange | Stable scheduling serial |
| 5 | Acknowledgement/fill/cancel responses | Stable scheduling serial |

A zero-delay child uses a later phase than its parent. An order arriving at the same
timestamp as a source trade therefore joins after that trade and cannot fill on it.
A response does not trigger another strategy decision. The audit records time, origin,
phase, serial and source row so equal-time decisions can be reproduced.

There is one submission opportunity at absolute local `decision_ns`. It submits only
if a snapshot has arrived, its same-side external quantity is positive and the opposite
quote is present and strictly passive for the configured price. Otherwise it skips,
with no retry. Arrival rechecks the current opposite quote and rejects a missing or
marketable quote. A limit buy must be below the ask; a limit sell must be above the bid.

Optional `cancel_ns` makes one local cancellation attempt. It sends a request only if
acceptance is already locally known and a positive remainder is known. It can skip
while an acknowledgement is pending or arrive after the order has filled. Exchange
state and locally known state can therefore differ without an error.

The explicit horizon is inclusive. Events scheduled after `horizon_ns` remain counted
in `pending_events`; there is no EOF flush. Arrival, feed or response delay can leave
information pending even after the final source row has been processed.

## Input and CLI contract

The first line is exactly:

```text
timestamp_ns,kind,quantity,opposite_price4
```

| Kind | Quantity | Opposite price | Meaning |
|---|---|---|---|
| `seed` | Zero or positive | Zero means missing | Required first row; initial external state |
| `add` | Positive | Must be zero | Add external shares at the configured level |
| `cancel` | Positive, no larger than `Q` | Must be zero | Remove shares under the selected queue assumption |
| `trade` | Positive, no larger than `Q` | Must be zero | Aggressive quantity reaching this level |
| `quote` | Must be zero | Zero means missing | Replace the displayed opposite quote |

There is exactly one initial seed. Times are non-decreasing and all source rows fall
within the horizon; equal timestamps preserve input order. Prices, quantities, total
external quantity and absolute per-share fee are bounded by 1,000,000,000. Unsigned
values contain no sign or whitespace. Blank rows, quoting, extra columns, duplicate
CLI options, more than 100,000 source rows and lines longer than 128 bytes are rejected.
LF/CRLF and a final unterminated row are accepted. Input must be a regular file.

When `Q > 0`, the fixed price is the assumed displayed same-side best price and a
present opposite quote must not cross it. When `Q = 0`, the fixed price is not an
observed same-side best quote. A crossing opposite is then allowed in the source,
but a hypothetical marketable arrival is still rejected. Later quote changes alone
never infer fills, even if they would cross a live shadow order; taker handling is
outside this fixed-level model.

All these options are required:

```text
--side buy|sell --price4 N --quantity N
--decision-ns N --horizon-ns N
--feed-delay-ns N --order-delay-ns N --response-delay-ns N
--cancel-model optimistic|conservative --audit FRESH.csv TRACE.csv
```

`--cancel-ns N` is optional; `--fee4 SIGNED` defaults to zero. Times are unsigned
64-bit values; every possible derived clock addition is checked for overflow before
simulation. This conservative preflight checks each market timestamp plus both feed
and response delay, including non-trade rows that cannot generate a response. It also
checks decision/cancel time plus order and response delay even if that action would
ultimately skip. These are input-domain checks, not claims that every row creates a
response. Decision/cancel times must lie in ordered relation within the horizon.
Every error returns exit code 1. Existing audit files, including symlinks, are preserved.
Audit write/close and summary flush failures are fatal.

## Exact accounts, fees and spread

Prices and signed cash use Price(4): one integer unit represents 0.0001 currency unit.
For signed filled quantity `d` (positive buy, negative sell), each fill updates:

```text
position += d
fees4 += abs(d) * fee4
cash4 -= d * price4 + abs(d) * fee4
```

A positive fee is charged per filled share; a negative value is a rebate. Fees are
fixed synthetic settings, not a venue fee schedule. The exchange account changes at
execution; the local account changes only when its fill response is delivered.

`local_marked_equity_twice4 = 2 * local.cash4 + local.position * (price4 + observed_opposite)`.
This uses the latest delivered external midpoint and preserves odd midpoint halves
exactly. One result unit is 0.00005 currency unit, not eight decimal places. The mark
is null unless a same-side external quote (`observed Q > 0`) and valid passive opposite
are locally known. It can be stale because observation is delayed.

Cash uses the actual modelled limit fill price, not the midpoint. Spread is therefore
already represented in execution price versus marking price; subtracting an additional
half-spread would double-count that effect. A midpoint mark is neither realised P&L
nor an executable liquidation value. The model has no exit-order or liquidation stage.

## Reproduce a hand-worked cancellation example

Run from the repository root with a fresh output directory. These deliberately small
synthetic times make the schedule easy to inspect; they are not calibrated latencies.

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine
cmake --build build --target itch_queue_sim -j2
mkdir -p out
mkdir out/queue-tutorial-1
cat > out/queue-tutorial-1/trace.csv <<'CSV'
timestamp_ns,kind,quantity,opposite_price4
0,seed,100,10010
15,add,20,0
25,add,40,0
30,cancel,50,0
40,trade,80,0
50,add,10,0
55,trade,35,0
60,quote,0,10020
CSV
for model in optimistic conservative
do
  ./build/itch_queue_sim --side buy --price4 10000 --quantity 10 \
    --decision-ns 10 --cancel-ns 65 --horizon-ns 80 \
    --feed-delay-ns 10 --order-delay-ns 10 --response-delay-ns 5 \
    --cancel-model "$model" --fee4 1 \
    --audit "out/queue-tutorial-1/$model.audit.csv" \
    out/queue-tutorial-1/trace.csv > "out/queue-tutorial-1/$model.json"
done
```

The 156-byte, eight-row trace gives the following causal path:

| Time ns | Event | Optimistic shadow | Conservative shadow |
|---:|---|---|---|
| 10 | Seed reaches local decision; submit | Observed `Q=100` | Observed `Q=100` |
| 20 | Order arrives after the add at 15 | Ahead 120, remaining 10 | Ahead 120, remaining 10 |
| 25 | External add 40; acceptance reaches local state | Ahead 120; behind 40 | Ahead 120; behind 40 |
| 30 | External cancel 50 | Ahead 70 | Ahead 110 after cancelling 40 behind and 10 ahead |
| 40 | Trade 80 | Fill 10; response due 45 | Ahead 30; no fill |
| 55 | Trade 35, after external add 10 at 50 | Already filled | Fill 5; response due 60 |
| 65 | Local cancellation opportunity | Skip: already known filled | Request cancellation of known remainder 5 |
| 75 / 80 | Cancellation arrival / response | No cancellation | Exchange then local state become cancelled |

Both runs end with external `Q=5` and no pending event. Optimistic has 21 audit rows,
position 10, cash4 −100010, fees4 10 and marked equity twice4 180 (0.0090 currency).
Conservative has 23 audit rows, position 5, cash4 −50005, fees4 5 and mark 90 (0.0045).
The external best bid is still 10000: a favourable midpoint mark does not mean selling
back at that bid would realise the marked gain. Extra exit fees are not modelled.

Two additional controls were run on this trace. Ending the conservative horizon at
79 leaves the exchange cancelled while the local state remains live with known
remainder 5: one cancellation response is pending at 80. Setting feed delay to 100
with horizon 80 makes the decision skip, leaves both accounts empty and has eight
feed deliveries pending. A strategy that submitted using the undelivered seed would
violate the information contract. More latency need not reduce realised P&L monotonically.

## Outputs and evidence limits

The aggregate JSON uses schema version 1 and model `synthetic_shadow_single_level_v1`.
It contains every configuration value, input byte/event counts, audit-row count,
exchange/local accounts and states, queue/remainder quantities, submitted/cancel flags,
pending-event count and the optional local mark. `passed: true` means a valid bounded
synthetic run, including valid skips or rejections; it does not mean an order filled.

The audit CSV exposes every processed post-event state, including `time_ns`, `origin_ns`,
phase, stable serial, source row, event quantity, external state, ahead/remainder,
exchange accounts and the immutable observations/local accounts. Keep detailed audits
in ignored `out/`. Source file identity is checked before/after reading and simulation
using file identity, size and modification metadata. `source_identity_stable` does not
claim SHA-256 verification; retain input, binary and source hashes separately when
recording reproducible evidence.

The model does not establish actual queue position, fill probabilities, hidden/reserve
behaviour, exchange priority rules, cross-venue effects or counterfactual market response.
Those require a richer adapter, additional assumptions and independent evidence.
