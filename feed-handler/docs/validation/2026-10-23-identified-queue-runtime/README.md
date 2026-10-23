# One identified shadow order around an atomic U

Gate 26 implements [the pure overlay](../../../bench/identified_queue.py) and passes
its first focused and canonical executions. A hypothetical one-share buy marker stays
outside the historical order-reference namespace. Its exchange state, locally known
state and complete delivered inventory remain separate. The old quantity-only queue
and its target-U refusal are unchanged.

[Aggregate evidence](verification.json) binds the frozen expectations, implementation,
independent verifier, retained reference inventories and actual outputs. Per-event
results, order rows, fixtures and test harnesses remain ignored.

| Actual verification | Result |
| --- | --- |
| Focused API calls | 40 pass: nine positive synthetic scenarios and 31 intended refusals |
| Frozen positive trace rows | 61 synthetic; 38 canonical, written before implementation |
| Canonical API calls | Six scenarios repeated twice; all twelve pass |
| Actual canonical trace rows | 76 across both batches |
| Complete historical order-row instances compared | 180,864 across twelve calls; two reused source states |
| Repeat result bytes | Every scenario matches exactly between batches |
| Altered actual-output controls | Four rejected at their intended semantic paths |
| Protected input identities | 79 focused; 80 canonical |
| Fills, cash changes and fees | Zero in every admitted scenario |
| New independent historical states | Zero; distinct retained coverage stays 37 |

The six canonical cases use the original 871 ns PRE/U interval. F/O/R below are
hypothetical feed/order/response delays, not estimated exchange or network latency.

| Scenario | F/O/R ns | Final exchange / local state | Shares ahead | Pending at the horizon |
| --- | --- | --- | ---: | --- |
| Accepted before U | 0/0/0 | live / live | 5,200 | None |
| Arrival at the closed U time | 0/870/0 | live / live | 5,300 | None |
| Seed not delivered | 872/0/0 | idle / idle | 0 | Two feed deliveries |
| Arrival beyond the horizon | 0/871/0 | idle / pending | 0 | Own arrival |
| Own acknowledgement beyond the horizon | 0/0/872 | live / pending | 5,200 | Own acknowledgement |
| Own cancellation before U | 0/0/0 | cancelled / cancelled | 0 | None |

The strategy decision is PRE+1 ns; own cancellation in the last case is PRE+2 ns.
External target-level quantity stays 5,300. Under the declared shadow-tail convention,
U removes 100 external shares ahead of an already live marker and appends the
replacement behind it. An arrival after the complete U timestamp group joins behind
all 5,300 instead. Neither transition is an execution or proof of actual venue priority.

## Small interface and explicit knowledge

`simulate_one_u(ledger, config, expected_sources=None)` returns complete
historical snapshots captured from the validated ledger, an own-state trace, pending metadata and final state. Configuration
has exactly quantity, decision, optional cancellation, inclusive horizon and three
delays. Only quantity one, passive buy, one globally adjacent/byte-contiguous same-price
best-bid U, two uncrossed displayed quotes and a horizon exactly at U are supported.
Invalid configuration/profile/derived uint64 clocks refuse without returning partial state.

The model reuses the existing identified ledger validator once per call. It schedules
captured source snapshots with equal-time phases source, feed, strategy, request arrival
and own response. A zero-delay child has a later phase than its parent. An order arriving
at U therefore sees POST even when its decision used PRE. The local requested quantity
becomes one on submission; confirmed remainder stays null until an own response.
Historical feed never acknowledges our order or cancellation.

The returned `observed_inventory_sha256` binds the entire ordered logical order list,
using compact sorted-key ASCII JSON with a final newline. The same captured orders
supply the decision. This distinguishes PRE from POST under identical BBO. All three
pure-module authentication flags remain false: the module itself opens no market file
and authenticates no session status. The private retained-input boundary separately
admits the fixed source pair and Gate 25's status/closure proof before canonical calls.
Its scoped `queue_admitted:true` concerns this hypothetical model only.

## Expectations, independent checks and controls

Before implementation, hand-literal own states and 99 positive trace rows were frozen:
six canonical scenarios and nine synthetic ones. The latter also cover a pending cancel
arrival, pending cancel response and a delayed PRE seed delivered at U after the source
has advanced to POST. Expected complete canonical snapshots come from the previously
accepted independent CSV, not the overlay's output. The fixture writer performs only
literal composition, wire encoding, inventory projection and hashing; it imports no
project or queue code.

The independent verifier imports no project helper or overlay. It parses the pinned
reference CSV itself, validates source manifests, ranked FIFO, side totals, attribution
knowledge and every complete ordered row. Typed full trace/pending/final comparison
uses the frozen literals. Causal payload identity, own-response lifecycle and source
coverage guards run before literal equality. The runner retains each actual file before
verification, compiles authenticated source bytes, checks input immutability and quiet
pure calls, and rejects file/process/network/project-import activity during those calls.
These are reviewed tripwires, not a security sandbox.

Four isolated copies of actual canonical output are rejected:

- POST inventory digest with valid PRE observation metadata: causal payload identity.
- Replacement left at its previous FIFO position with unchanged BBO: full historical inventory.
- Locally live/confirmed quantity before the pending own acknowledgement: own lifecycle.
- Horizon extended by the observed 211 ns witness gap: source coverage.

Source review improved refusal isolation, captured inventory identity and opened-descriptor
output checks before the first execution. The runner also preserves the original
exception alongside a simultaneous late immutability error. These are pre-execution
corrections. Both actual phases pass first time. Independent retained review authenticates 118
small-file identities and has no findings; it reruns no model or verifier. The 31
intended refusals and four
controls are successful negative checks, not failed normal runs.

## Recorded reproduction and scope

Both commands record the actual interpreter and runtime version. They used absolute
paths from the dossier root; these equivalent abbreviations assume the feed checkout:

```sh
python3 ../itch-feed-handler-tests/run_one_u_queue.py --phase focused \
  --module-sha256 80eee7883cf26bf05b67e7bef32f9efa40a5ee036ea93b6ac70ba6ea08a55a69 \
  --output out/one-u-queue-focused-v1
python3 ../itch-feed-handler-tests/run_one_u_queue.py --phase canonical \
  --module-sha256 80eee7883cf26bf05b67e7bef32f9efa40a5ee036ea93b6ac70ba6ea08a55a69 \
  --focused-evidence out/one-u-queue-focused-v1/verification.json \
  --focused-sha256 7931e041e0f7592450cf80259e82fc2ed0e405bdb5328aa3cfb5fbfb7223aae8 \
  --output out/one-u-queue-canonical-v1
```

The harness and frozen private inputs are required. Existing output paths refuse.
Execution source context is feed main `573ccf2fd807ab2029ab06755c4de68a0b9f2960` and engine
main `dbd280185a0d45f0839881caeff8d535bcd56779`: old 44+15 implementation files match HEAD,
while the new overlay is explicitly uncommitted at execution and separately hash-bound.
The verified module is committed only after checks pass. Future contexts need reviewed
pins and fresh paths; publication metadata checks require no model reruns.

No historical raw file is opened, statted or hashed in Gate 26. Gate 25's fresh prefix
hashes and whole-file inherited identity stay retained prerequisites. The existing
ledger is logically validated per call; no C++/vendor book reconstruction, raw replay,
sanitiser or performance experiment occurs. Complete inventory comparisons reuse two
states rather than adding independent samples. No trades occur in this fixed interval,
so zero fills test lifecycle separation without establishing fill calibration, hidden
liquidity, market reaction, routing or actual exchange priority.

Tutorial Chapter 36, Exercises 80–82, explains these results. The next increment makes
this bounded model reproducible as a self-contained synthetic learning example, without
requiring the private canonical data or suggesting broader historical coverage.
