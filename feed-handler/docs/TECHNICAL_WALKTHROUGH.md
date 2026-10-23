# A ten-minute technical walkthrough

Follow an order from exchange bytes to a reconstructed book, then explain what a
hypothetical strategy can know. For each stage, state its invariant, show the evidence
and identify one limit. The links below lead to recorded experiments; this guide
adds no new replay, benchmark or historical sample.

## 1. Separate intentions from observations — one minute

The [matching engine](https://github.com/Manuelma4/matching-engine) accepts order
intentions and decides trades. This feed handler applies published exchange facts.
A crossed quote in a replica is not permission to manufacture another match.

Read [the book interface](../include/itch/book.hpp) and [reconstruction rules](DESIGN.md).
References identify individual external orders; price levels maintain their displayed
quantities and reconstructed FIFO. Wire prices use four decimal places: integer
`1576300` means 157.6300. Shares, prices and nanoseconds are different units.

The engine's slab, FIFO and reference index are shared primitives. Its whole `Store`
is not reused: the feed needs one global reference index across instruments. Feed
price-level vectors can allocate, so the engine's preallocated hot-path claim does
not describe the complete replica.

## 2. Establish input identity and independent quotes — two minutes

[Canonical validation](VALIDATION.md#canonical-nasdaq-2019-12-30) records
268,744,780 messages, zero reported lifecycle anomalies and zero final live orders.
The recorded counters summarise the validated framing and lifecycle conditions;
counts alone are not a correctness certificate. They do not establish correct prices
or queues between the first and final message.

[Independent BBO validation](BBO_VALIDATION.md) compares four exact integers: bid and
ask prices and their aggregate displayed shares. A separately built, pinned MIT
implementation consumes identical hashed raw bytes. Five symbols at one second give
306,140 compared rows; MSFT/QQQ at 100 ms give another 1,224,560. All agree. The grids
overlap, so 1,530,700 comparisons are not that many unique event boundaries. This
is displayed Nasdaq BBO, with no consolidated NBBO or second-vendor-feed claim.

The sampling clock is part of correctness. At grid time g, an update timestamped g
is excluded: emit the snapshot before applying that message. There is no EOF flush.
A [synthetic boundary control](validation/2026-10-22-bbo/boundary_control.json)
deliberately reverses that rule and changes three of five rows. Those constructed
differences are not discrepancies discovered in the canonical data.

Ask: can two readers agree on counts while one has the wrong quote? Yes. Can two
readers agree at sampled quotes while differing between samples? Also yes.

## 3. Inspect complete inventories before claiming priority — one minute

[L3 validation](L3_VALIDATION.md) compares references, remaining shares, price levels
and per-price relative FIFO across both displayed sides. Fifteen baseline states,
[twenty X/U states](validation/2026-10-23-l3-transitions/README.md) and
[two same-price-U states](validation/2026-10-23-same-price-l3/README.md) give
37 distinct independently compared boundaries. Repeated exports add checks, not states.
The reference does not independently supply MPID knowledge or actual exchange priority.

The same-price U is a useful demonstration: the old order is at rank two, its immediate
peer moves from rank three to two, and the replacement joins rank thirteen at the tail.
BBO prices, sizes and counts stay unchanged. A BBO-only check would miss a stale queue.
Complete displayed FIFO corroborates a reconstruction convention at those boundaries;
it does not reveal hidden liquidity or guarantee a hypothetical fill.

## 4. Preserve observations and replay deterministically — two minutes

[Journal version 1](JOURNAL.md) preserves observed wire bytes, including ignored
metadata and rejected events. A structurally valid container does not certify valid
ITCH. CRCs check container integrity; Python independently recomputes the retained
source SHA-256. The C++ journal reader does not claim source identity verification.

Two canonical creations have the same 8,251,596,893-byte size and SHA-256. Raw and two
journal replays each process all 268,744,780 messages, agreeing at 27 sampled checkpoint
rows, 26 populated. The populated states address the empty-final-book false pass.
Both replay paths use the same reconstruction core, so this is transport/determinism
and sampled semantic-equivalence evidence; independent BBO/L3 supplies a different check.

State fingerprints are finite hashes and checkpoints are samples. Matching them is
useful regression evidence, with collision and coverage limits. Completed-file fsync is provided. The journal does not supply live network recovery,
per-event persistence, append-log crash recovery, cross-day instrument identity or
market response.

## 5. Measure a trade-off without inventing its cause — two minutes

[The reference-index experiment](STORAGE.md#recorded-results-2026-10-22) separates eight
correctness, eight streaming-memory and 48 timing processes. Each timing configuration
has six observations; Nasdaq/BX have 269/29 sampled checkpoints per configuration.
Correctness checks precede comparison of the concrete flat and standard indices.

For the flat Nasdaq build, fitting capacity reduces the observed whole-process RSS
from 354.4 to 226.2 MiB, while replay median rises from 29.497 to 32.950 seconds. The
time ranges overlap; memory was observed once per configuration. Lower reservation
was not a replay speedup there, and one RSS observation supplies no variability estimate.

[Binary versus reverse-linear level search](validation/2026-10-23-level-search/README.md)
is a separate experiment on the same vector representation. Binary is correct at
checked states and slower in all 24 matched timing pairs. Reverse-linear stays the
default. These finite host/workload observations supply no universal ranking or
hardware-counter explanation of cache misses, branches or memory movement.

Batch replay time is not per-message tail latency. Whole-process RSS is not isolated
index memory. The matching engine's synthetic closed-loop throughput is yet another
measurement, with its own [host and protocol](https://github.com/Manuelma4/matching-engine/blob/main/docs/BENCHMARKS.md).

## 6. Separate exchange state, delivered knowledge and own responses — two minutes

Try the existing fictional one-U example from the feed checkout:

```sh
python3 bench/identified_queue_demo.py --scenario delayed-seed
```

It requires no market data. Its [interpretation guide](validation/2026-10-23-identified-queue-example/README.md)
explains immutable captured inventories, exchange/local own state and pending responses.
The generated identities authenticate no exchange source. This one-U example is
separate from the retained A,D,A,A,E execution-prefix API.

[That prefix's runtime](validation/2026-10-23-execution-prefix-runtime/README.md) passes
seven positive configurations twice, sixteen intended refusals and five altered-output
controls. Across both batches, 184 event rows, 26 pending rows and 38,976 complete
historical order-row instances match independent checks. Six existing inventories
are reused, so distinct historical coverage stays 37.

An early marker joins behind 1,400 named shares. D removes an 800-share reference;
E reduces another named reference by six, leaving 594 ahead. The marker stays outside
the historical inventory. E is an observed external execution; zero own fills are
this model's declared convention, with no counterfactual incoming-demand allocation.
They do not estimate real fill probability.

A delayed PRE seed can arrive at the final E clock while exchange state is already
POST. Preserve PRE's captured full inventory and digest. Equal BBO cannot justify
replacing it with POST. Own acceptance at the exchange also cannot confirm local
quantity before its acknowledgement arrives. Pending events stay pending at the
inclusive horizon; printing their due time does not extend source coverage.

## Decide the next experiment from the missing evidence

| Question | Current support | Remaining gap |
| --- | --- | --- |
| Do quotes agree independently? | Exact sampled venue BBO | Every-event states and separate vendor source |
| Does complete displayed FIFO agree? | 37 distinct selected boundaries | Broader session coverage and actual venue priority |
| Does the journal preserve replay? | Original bytes and sampled same-core equivalence | Live gaps, per-event persistence/crash recovery and cross-day instrument identity |
| Is one representation faster? | Recorded finite host/workload comparisons | Other hosts, controlled attribution and open-loop tail latency |
| Would an own order fill? | Explicit bounded lifecycle conventions | Empirical fills, hidden liquidity, impact and counterfactual response |

The next acceptance gate should define deterministic later-session complete-inventory
checkpoints and a finite resource budget before new scans or exports. First tabulate
the existing source-time coverage and distinguish source selection from book agreement.
Freeze intended requests and refusal/coverage criteria before inspecting new books.
A failed or empty selected case must be reported, rather than replaced with a convenient
one. Broader independent samples can address reconstruction uncertainty; they cannot
calibrate fills by themselves. No new matching/strategy framework is needed for that
question.

Public report copies and original private evidence have different byte identities.
Use [the publication note](PUBLICATION.md) when following recorded hashes and old
source commits. Explain what was checked, what the check can detect and where its
support ends; that is the substance of the walkthrough.
