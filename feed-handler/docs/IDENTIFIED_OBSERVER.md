# Identified replacements and delayed knowledge in C++

Build and run the example from the **matching-engine repository root**:

```sh
cmake -S . -B build-combined -DCMAKE_BUILD_TYPE=Release -DME_BUILD_FEED_HANDLER=ON
cmake --build build-combined --target itch_identified_demo --parallel 2
./build-combined/feed-handler/itch_identified_demo
```

The example reads no file and downloads no market data. Its
[source](../tools/identified_demo.cpp) encodes two fictional U messages with the
project's own `itch::Writer` and passes them to the
[`itch::identified`](../include/itch/identified_observer.hpp) API.

## Why another layer

The [L3 book](../include/itch/book.hpp) already applies an ITCH U (order replace)
correctly: the old reference leaves its queue and the new reference joins the back of
the queue at its price. It does not answer three questions that a queue-position study
needs:

1. **Which** order moved, and where it stood before moving (rank and visible shares
   ahead at its old price).
2. A **copy** of the complete displayed inventory after each event. The book's order
   slots are reused by the next replacement, so a pointer kept from an earlier event
   can silently describe a different order later.
3. **When** a strategy could have known each state. A retrospective history contains
   the future; reading it directly at an earlier time leaks information.

`itch::identified` adds exactly those three things for one stock and U messages only.
It reuses `L3Book::find`, `for_each_order`, `visit` and `replace`; it does not
reimplement replacement or matching.

## The fictional example

The seed is a complete displayed book for locate 7, holding from 10 ns:

| Side | Price(4) | FIFO order |
|---|---:|---|
| Bid | 10000 | 1 (10 shares) |
| Ask | 10010 | 11 (30), then 12 (40) |
| Ask | 10020 | 13 (25) |

Two replacements arrive, both stamped 12 ns:

- **U1** replaces 11 by 21 for 60 shares at 10010. Order 11 was first in its queue with
  nothing ahead. Order 21 joins **behind** 12, even at the same price: a replacement
  loses priority.
- **U2** replaces 21 by 22 for 35 shares at 10020. Order 21 was second, with 40 shares
  ahead. Order 22 joins behind 13.

The example prints:

```text
verification=unverified_by_module
fact seq=11 t=12 S11@10010/30 -> S21@10010/60 rank_before=1 shares_ahead_before=0
fact seq=13 t=12 S21@10010/60 -> S22@10020/35 rank_before=2 shares_ahead_before=40
snapshot 0 origin=10: B1@10000/10 S11@10010/30 S12@10010/40 S13@10020/25
snapshot 1 origin=12: B1@10000/10 S12@10010/40 S21@10010/60 S13@10020/25
snapshot 2 origin=12: B1@10000/10 S12@10010/40 S13@10020/25 S22@10020/35
delay=5 horizon=17: t10=none t14=none t15=0 t16=0 t17=2 pending=0
delay=5 horizon=16: t10=none t14=none t15=0 t16=0 pending=2
reuse: refused (new reference already seen in this window)
```

With a 5 ns delivery delay, the seed reaches the strategy at 15 ns, and both
replacements at 17 ns. A probe at 16 ns therefore still sees snapshot 0, even though
the exchange changed at 12 ns. At 17 ns both deliveries have arrived, and the probe
sees snapshot 2, the later of two equal-time events in source order. With horizon 16 the
same two deliveries remain **pending**: they are reported, never flushed into the
last probe.

The last line shows a whole-input refusal. U2 tries to reuse reference 11, which U1
retired. The native book would accept it, because 11 is no longer live. The observer
refuses it, because a reference seen earlier in the window cannot identify a new order.

## Contract

**Inputs.** One `Seed` (symbol, locate, source cut, effective time, ordered orders),
U `Occurrence`s (source cut, tracking number, 37-byte framed record), the expected
source list and `Limits`. Seed and replacement orders carry `Attribution::Unknown`.

**Source cuts.** Each cut has a sequence, frame start and end offsets, timestamp, body
length and type. Sequences must be positive and increasing. A cut must have a known
type and its exact length, a span `end = start + 2 + body` inside the declared input,
no overlap with the previous cut, and timestamps that never decrease. The seed cut may
be any message type; every occurrence must be a U. The seed cut followed by the
occurrence cuts must equal the caller's expected list exactly.

**Framing.** The length prefix must be 35 and the type byte `U`. The encoded locate,
tracking number and timestamp must equal the selected locate and the occurrence's
declared values. Fields are decoded through the existing `OrderReplace` view only
after this check.

**Book consistency.** Seed orders are bids then asks, best price first, FIFO within a
price, with no zero reference, share count or price, and prices up to 2,000,000,000.
Seed references must be distinct. A U must name a live old reference. Its new
reference must be non-zero, different from the old one, and unseen in this window
(neither live nor retired). It needs positive shares and an in-range price. The
displayed book may never be locked or crossed (best bid ≥ best ask), after the seed or
after any U, because the exchange's own displayed book never is.

**Identity.** `SourceIdentity` declares input bytes and lower-case SHA-256 values. The
module never reads input bytes, so every history declares
`verification() == "unverified_by_module"`. This is a fixed output, not a caller
flag. Metadata equality authenticates neither raw bytes, the symbol directory, nor
messages outside the supplied cuts.

**Limits.** `max_orders` (1–2²⁰), `max_facts` (0–256), `max_captured_rows`
(0–2²⁴) and `max_probes` (1–2¹⁶) may only narrow these hard bounds, which are sized
for one real stock's full displayed book over a short window. The private book
reserves `max_orders` slots, so callers should narrow it. Captured rows count the seed
and every post-replacement snapshot. A replacement reuses its order slot, so a
four-order book with `max_orders = 4` admits it. (A first profile used bounds of
64/16/1024/64; it was raised before any real-data use, and the fixture was refrozen.)

**Delivery.** `observe` takes one fixed non-negative delay, an inclusive horizon and
nondecreasing probes within it. Every snapshot origin must be within the horizon. The
seed's origin is its effective time, and each fact's origin is its source timestamp.
Every delivery addition is checked for overflow, pending or not. A delivery at a probe's
time is visible to that probe. Probes may precede the seed's delivery, and then see
nothing; an available empty book is a snapshot, not nothing.

**Errors.** Malformed or inconsistent input, and limits outside their hard range,
throw `std::invalid_argument`. Exceeding a configured limit throws `std::length_error`.
A delivery time that does not fit in 64 bits throws `std::overflow_error`. Allocation
failure propagates. No partial history or observation is returned. A moved-from
`History` is no longer admitted, and `observe` refuses it.

## Real ITCH files

`itch_identified_capture` applies the observer to a real BinaryFILE. It takes a CSV
of requests (`request_id,symbol,from_ns,min_run,max_facts`) and reads the file once.
For each request it takes the first maximal run, at or after `from_ns`, of the
symbol's own messages that are all U, with at least `min_run` of them (keeping at most
`max_facts`). An optional sixth column, `need`, is `any` (the default),
`queued_same_price` or `queued_same_price_overtaken`. With `queued_same_price`, the kept
U must include one that keeps the old order's price while that order had a displayed
order ahead of it at its price and side; `queued_same_price_overtaken` also requires at
least one displayed order behind it, so that moving to the back really puts others in
front. A run without such a U is skipped whole, up to the symbol's next non-U message,
and the search continues. The seed is the symbol's complete displayed book, from the full-day
book, after the global message immediately before the first U. Its effective time is
that message's timestamp. The tool writes post-message checkpoints and the captured
states as `state_id,side,price4,fifo_rank,reference,shares` rows: the same format as
the independent exporters, so every state can be compared byte-for-byte. It also writes
a JSON summary of facts and a delayed observation. The input SHA-256 is passed by the
caller and only declared.

[Real Nasdaq windows](validation/2026-10-23-real-identified-windows/README.md):
on 30 December 2019, 18 MSFT/QQQ states from four frozen requests match two independent
exports byte-for-byte, and all 14 facts are recomputed from the reference book.
[A second frozen request set](validation/2026-10-23-real-identified-wider/README.md)
adds 42 AAPL, SPY, AMZN and TSLA states at 11:00 and 15:00 with 34 recomputed facts,
none of them overlapping an earlier state.
[A second venue](validation/2026-10-23-real-identified-bx/README.md), BX on 30 July
2019, adds 23 distinct AAPL, SPY, QQQ and AMZN states with 18 distinct recomputed facts;
its thin books and rare U-only runs put most windows near the close.
[Same-price replacements that lose queue position](validation/2026-10-23-real-identified-queued/README.md):
with `need=queued_same_price`, 37 more Nasdaq-day states and 29 recomputed facts, 11 of
them replacements at an unchanged price by orders ranked third to twelfth.
[The same requests under ASan/UBSan](validation/2026-10-23-real-identified-queued-sanitised/README.md)
run cleanly on the full file and reproduce every output byte of the Release capture.
[The same question on BX](validation/2026-10-23-real-identified-bx-queued/README.md)
returns no window for any of eight frozen requests; an independent re-scan confirms the
null, which is recorded rather than replaced, and coverage stays at 161.
[Four symbols not requested before](validation/2026-10-23-real-identified-opening-close/README.md),
NVDA, GOOGL, FB and INTC from 09:45 and 15:45, add 98 Nasdaq-day states with 90
recomputed facts, for 259.
[The same four symbols on BX](validation/2026-10-24-real-identified-bx-partial-null/README.md),
from 10:00 and 15:00, add 12 NVDA and GOOGL states with 10 distinct facts, for 271; FB
and INTC find no window, and an independent re-scan confirms both nulls.
[CSCO, CMCSA, PEP and NFLX from 10:45 and 14:45](validation/2026-10-24-real-identified-midsession/README.md)
add 74 Nasdaq-day states with 66 recomputed facts, for 345; one CSCO ask replaced at an
unchanged price and size moves from 16th to 25th at its level.
[The same request set on BX](validation/2026-10-24-real-identified-bx-midsession/README.md)
adds 4 NFLX states with 3 facts, for 349; CSCO, CMCSA and PEP find no window after
either time, and an independent re-scan confirms all six nulls.
[ADBE, COST, AVGO and TXN from 10:30 and 13:45](validation/2026-10-25-real-identified-new-symbols/README.md)
add 33 Nasdaq-day states with 25 recomputed facts, for 382; every request finds a short
window and no replacement keeps its price.
[CSCO, CMCSA, INTC and PEP from 11:30 and 14:15](validation/2026-10-25-real-identified-queued-new-symbols/README.md),
under `need = queued_same_price`, add 35 states with 27 recomputed facts, for 417; of the
20 queued same-price replacements, 19 were already last at their level, so only one shows
another order overtaking it.
[AMD, MU, SIRI and EBAY from 12:00 and 15:15](validation/2026-10-25-real-identified-overtaken/README.md),
under `need = queued_same_price_overtaken`, add 24 states with 22 recomputed facts, for
441; in five distinct replacements the new order moves behind 2 to 20 orders, and SIRI
finds no window.
[The same question on BX](validation/2026-10-25-real-identified-bx-overtaken/README.md),
for AMD, MU, EBAY and TSLA from the same times, returns no window for any of the eight
frozen requests; an independent re-scan confirms the null, and coverage stays at 441.
[ORCL, QCOM, GILD and SBUX from 11:15 and 14:35](validation/2026-10-25-real-identified-overtaken-new-symbols/README.md),
under the same condition and with the same binary, add 17 states with 16 recomputed
facts, for 458; in four distinct replacements the new order moves behind 2 to 10
orders, and three requests (QCOM at both times, SBUX from 14:35) are independently
confirmed nulls.
[AMGN, BKNG, MDLZ and ISRG from 10:05 and 13:15](validation/2026-10-26-real-identified-overtaken-null/README.md)
return no window for any of the eight frozen requests: AMGN's queued same-price
replacements all come from orders already last at their level. An independent re-scan
confirms the null, and coverage stays at 458.
[CSX, ADP, VRTX and KHC from 10:20 and 13:50](validation/2026-10-26-real-identified-overtaken-khc/README.md),
under the same condition and with the same binary, add 17 KHC states with 15 recomputed
facts, for 475; in both distinct replacements the new order moves behind 1 and 14
orders, and the six CSX, ADP and VRTX requests are independently confirmed nulls.
[ADI, LRCX, MAR and ROST from 11:45 and 14:05](validation/2026-10-26-real-identified-overtaken-adi/README.md)
add 4 ADI states with 3 distinct recomputed facts, for 479: both ADI requests reach one
window, where the new order moves behind 2 orders, and the six LRCX, MAR and ROST
requests are independently confirmed nulls.

```sh
./build-combined/feed-handler/itch_identified_capture DAY.itch SHA256 requests.csv \
    1000000 checkpoints.csv states.csv summary.json
```

## What this does not do

The observer has no journal, network transport or concurrency. It does
not handle messages other than U for the selected stock, and it admits no historical
queue or fill. It knows nothing of our own orders, hidden liquidity or actual
exchange priority. Seen-reference checks cover the supplied window only; they are no
evidence of day-wide reference uniqueness.

[The validation record](validation/2026-10-23-native-identified-observer/README.md)
describes how the contract was frozen, reviewed and tested.
