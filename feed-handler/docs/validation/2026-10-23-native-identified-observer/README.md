# Native identified observer: frozen fixture and first execution

The [identified observer](../../IDENTIFIED_OBSERVER.md) is a C++20 layer over the
native L3 book. It turns U messages for one stock into owned facts and snapshots, then
reports which snapshot a strategy could know at each probe under a fixed delivery
delay. It is synthetic and bounded: no market data is read.

## Order of work

1. **Contract and fixture before code.** The public header was written together with
   a hand fixture. The fixture holds the seed, two U records, complete post-inventories,
   ranks, shares ahead, four delivery profiles, an empty seed, a four-order limit
   boundary and twenty refusals. Inventories and indices are hand-stated literals. Only
   frame bytes are packed mechanically, with an encoder independent of the project's
   writer, and two frames were also typed out by hand and must match.
2. **Independent review before execution.** A separate reviewer re-derived every value
   by hand and decoded every frame. It found no disagreement, but listed coverage gaps:
   no bid-side U, no U creating or emptying a level, untested source and frame checks,
   and three ambiguities (exception type for invalid limits, timestamp monotonicity,
   crossed books).
3. **Second freeze, still before any execution.** The reviewed first fixture is kept
   unchanged. A second fixture adds the decisions and the missing cases: a three-U
   extended book (bid-side moves, a new level, an emptied level, an ask at the maximum
   price), accessor expectations and 23 more refusals. That makes 43 refusals: 9
   transition, 8 source, 8 limits, 7 clock, 6 seed and 5 frame.
4. **First execution.** Nothing in the fixture or the observer changed in response to
   results.

## Results

From the consolidated matching-engine root, fresh Release and Debug ASan/UBSan builds
(`-fno-sanitize-recover=all`) both pass. Compile commands confirm C++20 and sanitiser
flags for the observer, the L3 book, the driver and the demo. There are no warnings and
no stderr output. Apple clang 21.0.0 on macOS/arm64 was used, with leak detection
disabled, so no leak claim follows.

- Each build runs the private driver twice. All four outputs are byte-identical: 48
  case rows per run.
- **Positive histories (4):** the main case, the empty seed, the order-limit boundary
  and the extended case. Their facts, snapshots, captured rows and accessors equal the
  hand fixture exactly. All nine observation profiles return the stated snapshot
  indices and pending sets.
- **Refusals (43):** each fails at the stated stage (build or observe) with the stated
  exception, and every error message was checked against the case's intended reason.
- **Move semantics:** a moved-from history is no longer admitted and `observe` refuses
  it. Copies stay admitted.
- **Checker controls:** three altered output copies are rejected: a wrong rank, a
  snapshot visible before its delivery (a future leak), and pending deliveries
  flushed at the horizon.
- **Kernel mutants:** three mutated copies of the observer, built outside the
  repository, are each detected:
  - checking only live references instead of every reference seen is caught by
    exactly the two retired-reference refusals;
  - a strict `<` instead of `<=` at a probe is caught by the delivery profiles;
  - an off-by-one in shares ahead is caught by the positive histories.
- **Public example:** `itch_identified_demo` prints the text shown in the guide, in both
  builds, and equals a hand-written expectation byte-for-byte.

[The aggregate](result.json) records source, fixture, binary and output identities.
Private fixtures, generator, driver, checker, logs and per-case outputs stay outside
this repository.

## Rerun after raising the bounds

Before any real-data use, the hard bounds were raised from 64/16/1024/64 to
2²⁰/256/2²⁴/2¹⁶ so that a real stock's book fits. The fixture was refrozen as a third
version in which only the refusal for an over-bound `max_orders` changes. The same
Release and ASan/UBSan protocol passes again, with four identical outputs. The source
identities above describe the first run; the aggregate's `rerun_after_bound_change`
records the current ones.

## Limits

These are logical tests on fictional inputs and add no historical states; the
[real Nasdaq windows](../2026-10-23-real-identified-windows/README.md) are recorded
separately. There is no benchmark here. Nothing here measures actual exchange priority,
hidden liquidity, network latency or fills.
