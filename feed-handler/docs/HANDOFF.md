# From observed history to a causal queue audit

This audit connects the [bounded historical projector](HISTORICAL_WINDOW.md) to the
[single-level shadow queue model](QUEUE_SIMULATOR.md). The projector establishes an
external displayed-liquidity path. The simulator places one hypothetical passive
order against that fixed path, subject to declared information and request delays.
These are different claims: matching observed BBO states does not establish what
would have happened after adding an order to the exchange.

The inputs are the two frozen MSFT and QQQ buy windows already recorded in the
[canonical projection evidence](validation/2026-10-22-window/canonical.json). That
evidence covers the complete source and compares all 15 selected seed/post-message
states with the pinned independent book. The handoff uses the small normalised
files and their provenance, rather than reconstructing the raw day again.

## Keep the identity chain intact

Retain the producer's clean source commit, raw-input SHA-256, projector binary hash,
window configuration, aggregate summary and both output-file hashes. Then retain
the simulator source/binary identity, exact configuration, normalised/provenance
hashes, audit hash and aggregate result. A result without its configuration and
input identity cannot be compared meaningfully with another run.

The simulator's one-based `source_index` refers to a normalised CSV row. Join that
index to the projector ledger's `normalised_row`, then to the original source
sequence, frame offset, timestamp, body length and message type. Ledger rows with
`normalised_row=0` remain explicit exclusions; they are not missing simulator events.
The seed is a derived post-boundary observation, not an exchange-published snapshot.

Strategy actions use `source_index=0`. A submission is justified by the latest
delivered immutable snapshot and the fixed decision time, rather than falsely
assigned to a raw execution. Arrivals and responses follow from the originating
action and configured delays. Audit time, origin, phase and stable serial make
those relationships inspectable.

## Frozen experiment

Each window uses one buy order of 100 shares, its fixed projected best-bid price,
and `fee4=1`: a charge of 0.0001 currency unit per filled share. Both cancellation
assumptions are run with each profile, giving 2 symbols × 6 profiles × 2 models =
24 cases. These settings illustrate the model; they are not measured venue latencies
or a Nasdaq fee schedule.

Let `S` be the seed timestamp, `H` the final source timestamp, and `L=H-S`. Every
profile uses the inclusive horizon `H`. All delays and offsets below are integer
nanoseconds. There is no cancellation opportunity unless listed.

| Profile | Feed delay | Order delay | Response delay | Decision | Cancellation decision |
|---|---:|---:|---:|---|---|
| `immediate` | 0 | 0 | 0 | `S` | None |
| `delayed` | 1,000 | 2,000 | 5,000 | `S+1,000` | None |
| `undelivered_seed` | `L+1` | 0 | 0 | `S` | None |
| `arrival_pending` | 0 | `L+1` | 0 | `S` | None |
| `cancel_confirmed` | 1,000 | 2,000 | 5,000 | `S+1,000` | `H-10,000` |
| `cancel_response_pending` | 1,000 | 2,000 | 5,000 | `S+1,000` | `H-4,000` |

MSFT has `S=34214907518545`, `H=34214938994341`, `L=31475796`, and
`price4=1589000`. QQQ has `S=34201694396241`, `H=34201723909063`,
`L=29512822`, and `price4=2135400`. Absolute timestamps are preserved; the
relative notation only makes the schedule easier to read.

At equal times the phases remain market update, feed delivery, strategy decision,
request arrival, then response. Thus the delayed decision sees its seed delivered
at `S+1,000`. Its order arrives at `S+3,000`, before the next normalised market event
in either window, and acceptance becomes known at `S+8,000`.

## Derive the expected queue path before running

Let `Q` be external displayed quantity, `A` shares ahead of the shadow order, and
`R` its remaining quantity. Acceptance sets `A=Q`; subsequent additions join behind.
Optimistic cancellations remove ahead first. Conservative cancellations remove
behind first, keeping `A` no larger than the remaining external quantity.

The MSFT normalised path is:

```text
seed 844 → add 100 → cancel 100 → add 100 → cancel 10 → trade 196
Q:   844       944          844       944         934          738
A optimistic: 844, 844, 744, 744, 734, 538
A conservative:844, 844, 844, 844, 844, 648
```

The QQQ path is `seed 1400 → cancel 800 → trade 6 → add 800`.
External quantities are `1400,600,594,1394`; ahead quantities after immediate
acceptance are `1400,600,594,594` under both cancellation assumptions. There were
no behind additions before its cancellation, so the assumptions coincide here.

The `immediate` and `delayed` profiles therefore predict zero fills and a live
100-share remainder. The only trade is smaller than the quantity ahead before it.
The cancellation profiles also predict zero fills. Those are useful outcomes to
retain; choosing a more profitable window or reducing the order's initial queue
position would change the experiment.

The following final-state expectations were frozen independently from the literal
CSVs before any simulator matrix run:

| Profile | Exchange / local state | Exchange / known remainder | Final ahead | Pending events |
|---|---|---|---|---|
| `immediate` | Live / live | 100 / 100 | MSFT 538 or 648; QQQ 594 | 0 |
| `delayed` | Live / live | 100 / 100 | MSFT 538 or 648; QQQ 594 | 1 |
| `undelivered_seed` | Idle / idle | 0 / 0 | 0 | MSFT 6; QQQ 4 |
| `arrival_pending` | Idle / pending | 0 / 100 | 0 | 1 |
| `cancel_confirmed` | Cancelled / cancelled | 0 / 0 | 0 | 1 |
| `cancel_response_pending` | Cancelled / live | 0 / 100 | 0 | 2 |

For MSFT, 538 is optimistic and 648 conservative. Cancelling our order clears its
exchange remainder and ahead diagnostic; it does not remove historical external
shares. The six/four undelivered events are feed snapshots, one per normalised row.
An arrival beyond the horizon has not generated an acknowledgement yet: count its
pending request once, rather than inventing a second pending response.

## What the horizon leaves unknown

The final source event at `H` is processed in every profile. With a 1,000ns feed delay,
its snapshot is scheduled at `H+1,000` and remains pending. Consequently MSFT ends
with exchange `Q=738` but observed `Q=934`; QQQ ends with exchange `Q=1394` but observed
`Q=594`. Zero delay delivers the final quantity. The undelivered-seed profile never
receives a snapshot, so its decision skips without a retry.

For `cancel_confirmed`, cancellation arrives at `H-8,000` and its response at
`H-3,000`. The final feed is the sole pending event. For `cancel_response_pending`,
arrival is `H-2,000` and response is `H+3,000`: exchange cancellation is complete,
while the local state still reports a live order with 100 known remaining shares.
Its two pending events are that response and the final feed. The horizon is not
silently extended to make the two accounts or order states agree.

All hand-derived accounts are zero: no filled shares, position, cash movement or
paid fees. Positive `fee4` charges only filled shares. The local midpoint mark is
zero with a delivered valid quote and no position; it is unavailable without any
delivered seed. A zero mark does not establish a profitable strategy or executable
liquidation value. Filled accounting and fee arithmetic are separately exercised by
the synthetic examples in [QUEUE_SIMULATOR.md](QUEUE_SIMULATOR.md).

Check shadow-order conservation separately from external history. Accepted quantity
must reconcile with fills, its live remainder and a completed own cancellation.
Historical `Q` follows only the recorded additions, cancellations and executions.
The hypothetical order is absent from that path: `Q+R` is not a conserved combined
order book, and a shadow fill must never deplete the source twice.

## Reproduce one profile

From the repository root, retain the frozen producer files in ignored local storage
and use a fresh audit path:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
  -DFETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE=../matching-engine
cmake --build build --target itch_queue_sim -j2
mkdir -p out
mkdir out/handoff-example-1
./build/itch_queue_sim --side buy --price4 1589000 --quantity 100 --fee4 1 \
  --decision-ns 34214907519545 --horizon-ns 34214938994341 \
  --feed-delay-ns 1000 --order-delay-ns 2000 --response-delay-ns 5000 \
  --cancel-model conservative \
  --audit out/handoff-example-1/MSFT.audit.csv \
  out/window-canonical-v1/MSFT/normalised.csv \
  > out/handoff-example-1/MSFT.json
```

This is the delayed MSFT configuration. Its prediction is live/live, ahead 648,
100 exchange and known remaining shares, no fills, and one pending final feed.
Preserve detailed audit/source joins under ignored `out/`; publish aggregate checks
and cryptographic identities rather than the source rows.

To audit all 24 configurations and their source joins, use a committed, clean `main`
checkout with the original frozen producer files available. Both result paths must
be fresh; the aggregate is outside the detailed output directory:

```bash
python3 bench/audit_handoff.py \
  --window-evidence docs/validation/2026-10-22-window/canonical.json \
  --projection-dir out/window-canonical-v1 \
  --simulator build/itch_queue_sim \
  --output out/handoff-audit-example-1 \
  --report out/handoff-audit-example-1.json
```

The runner checks the committed producer evidence, small-file hashes and byte counts,
configuration, every causal audit transition, and the joins to projected source rows.
It retains the raw identity from the earlier full-source evidence and does not reopen
the raw file. Source, input, simulator and detailed-output identities must remain
unchanged. The example leaves the report ignored for inspection; publishing a report
is a separate step after checking its result.

## Interpretation limits

This is a causal audit of an explicitly restricted retrospective sample. The feed,
request and response schedules can be checked against the declared model. They do
not calibrate network latency, exchange priority, cancellation probabilities, hidden
liquidity, market impact or the market's response to our added order. The four-column
queue schema also omits historical order identities and opposite size, even though
the producer retains them in its provenance.

Zero fills leave limited sensitivity to fill-price and fee assumptions. A live order
at the horizon is outstanding hypothetical exposure, not a completed trade. More
latency need not improve or worsen a marked result monotonically. There is no search
for a profitable configuration and no claim of empirical fill accuracy or strategy
performance from these 24 cases.

## Recorded baseline

The [completed aggregate](validation/2026-10-22-handoff/canonical.json) records a
passing 24-case audit at clean `main` source commit
`83973d9a5a350810bcf0f373d5fceb534f4605ac`. All processes completed with exit code zero
and empty diagnostics. Their 284 processed audit events include market updates,
deliveries and order actions repeated across the declared configurations; they are
not 284 distinct historical source messages.

All hand-derived predictions above matched. A separate retained-output verification
compared every complete summary and final audit state with the expectations frozen
before the runs. It also checked all intermediate external/observed queue states,
original decision-intent joins, inclusive-horizon behaviour, 144 per-case artefact
digests and 24 process-status records. Source, simulator, oracle and retained inputs
remained unchanged. No simulator or raw-source replay was needed for that check.

Every case retained zero fills, position, cash movement and paid fees. Immediate
and delayed accepted orders remained live for 100 shares; MSFT's final ahead was
538 optimistic or 648 conservative, while QQQ's was 594 under either assumption.
The seed-withheld, arrival-pending and two cancellation controls retained their
predicted distinct exchange/local states and pending-event counts. In particular,
the cancellation-response control ended exchange-cancelled but locally live, with
both the final feed and cancellation response pending.

The [verification manifest](validation/2026-10-22-handoff/verification.json) records
the harness, logs, frozen oracle and independent-review identities. Detailed audits,
joined source rows and the independent verification record remain in ignored local
storage. This establishes the bounded source-to-model handoff and
its stated scheduling/queue rules. It adds no empirical fill calibration or strategy
performance claim.
