# Call the queue simulator from C++

Build this example from the **matching-engine repository root**:

```sh
cmake -S . -B build-combined -DCMAKE_BUILD_TYPE=Release -DME_BUILD_FEED_HANDLER=ON
cmake --build build-combined --target itch_queue_demo --parallel 2
./build-combined/feed-handler/itch_queue_demo
```

The executable takes no arguments, reads no file and downloads no market data. Its
[C++ source](../tools/queue_demo.cpp) passes a `constexpr std::array` of four events
to the existing [`itch::queue::simulate`](../include/itch/queue_sim.hpp) API. The
array converts to a read-only `std::span`; the returned `Result` owns its trace.
This is the native aggregate queue model, distinct from the supplementary Python
identified-order prototypes. No matching or queue rule is implemented in the demo.

## Four fictional observations

The order is a passive buy of ten shares at `price4=10000`, or 1.0000 currency unit
per share. The opposite ask is 10010, or 1.0010. Fees are zero. Times are deliberately
tiny synthetic nanoseconds, not measured network delays.

| Time ns | External event | Quantity | External quantity afterwards |
|---:|---|---:|---:|
| 0 | Seed | 100 | 100 |
| 20 | Add | 40 | 140 |
| 30 | Cancel | 50 | 90 |
| 40 | Trade | 80 | 10 |

The local decision submits at 10 ns. Feed and order delay are zero; responses take
5 ns. Arrival therefore puts all 100 external shares ahead of our order at 10 ns.
Acceptance becomes locally known at 15 ns. The later add joins behind us: external
quantity becomes 140 while quantity ahead remains 100.

## The cancellation assumption changes the shadow outcome

The aggregate cancellation has no order identity. Under the optimistic convention,
remove its 50 shares from ahead: 100 − 50 = 50. Under the conservative convention,
remove the 40 shares behind first, then ten ahead: 100 − 10 = 90.

At the trade of 80 shares:

- Optimistic: 80 passes the 50 ahead, so `min(10, 80 − 50) = 10` shares fill.
- Conservative: 80 consumes part of the 90 ahead, leaving ten ahead and our entire
  ten-share order still live.

Both runs leave external quantity 10. Do not subtract the hypothetical fill again:
the shadow order never changes the external observations. This is an explicit
counterfactual model assumption. The two outcomes are neither calibrated fill
probabilities nor guarantees about real exchange executions.

## Execution and knowledge have separate clocks

The executable runs both assumptions through the inclusive horizon 45 ns, then
repeats the optimistic case with horizon 44 ns.

| Assumption / horizon | Exchange state | Local state | Exchange filled | Local filled | Pending events |
|---|---|---|---:|---:|---:|
| Optimistic / 45 | Filled | Filled | 10 | 10 | 0 |
| Conservative / 45 | Live | Live | 0 | 0 | 0 |
| Optimistic / 44 | Filled | Live | 10 | 0 | 1 |

The optimistic exchange executes at 40 ns; its response arrives at 45 ns. At 44 ns,
local knowledge still includes ten remaining shares, even though the exchange has
none. Receiving the external trade feed is separate from receiving an own-fill
response. The horizon does not flush future events.

The trace prints post-event rows. Phases are market (1), feed (2), decision (3),
arrival (4), response (5). Even with zero feed delay, the market row at 40 precedes
its feed row at 40: observed quantity is initially still 90 and then becomes 10.
`unknown` before the first feed means no observation has arrived, not a known empty
level. The first two scenarios print 12 and 11 rows; the shortened third prints 11.

## Read the accounts in their units

The filled exchange account has position 10 and `cash4=-100000`, or −10.0000 currency
units. At horizon 45 the optimistic local account agrees; at horizon 44 the local
account still has zero position and cash. Conservative accounts remain zero.

`local_marked_equity_twice4` uses twice Price(4) money. The optimistic horizon-45
mark is 100, or 0.0050 currency unit: the delivered midpoint is 1.0005 and
−10.0000 + 10 × 1.0005 = 0.0050. The other marks are numeric zero, not missing.
This is an unrealised model mark, not an executable liquidation value or realised
profit. No exit trade or additional exit fee is modelled.

See the [complete model contract](QUEUE_SIMULATOR.md) for the CSV CLI, validation
bounds, fees and tie policy. The [verification record](validation/2026-10-23-native-queue-demo/README.md)
records checks of these literal cases. Historical displayed L3 coverage remains
41 states; this synthetic example adds no historical priority, session-status or
empirical-fill admission.
