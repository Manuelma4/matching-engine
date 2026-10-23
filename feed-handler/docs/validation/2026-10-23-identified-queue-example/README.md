# Run the identified queue model without private data

The [public example](../../../bench/identified_queue_demo.py) constructs fictional
`DEMO` orders in memory and calls the existing ledger builder and one-U model.
From the feed checkout, run:

```bash
python3 bench/identified_queue_demo.py
python3 bench/identified_queue_demo.py --scenario delayed-seed
python3 bench/identified_queue_demo.py --help
```

Only Python's standard library and three adjacent public files are needed:
`identified_queue_demo.py`, `identified_queue.py` and `identified_events.py`.
No C++ build, market-data download or private harness is required to run the example.
An absolute script path also works from another working directory. The command prints
one complete sorted-key JSON report after all selected scenarios finish. It creates
no result files. Use the declared scenario names; abbreviated, repeated and invalid
options fail with exit code `2` and empty stdout.

## Read the result

The hand-supplied PRE inventory is bid `[10:10,20:40,30:30]`, ask `[50:20]`, with
reference followed by shares. Bid `price4` is 100, ask 101: these are **0.0100** and
**0.0101** currency units. Four generated A frames at fictional time 100 precede
U at 110, replacing reference 20 with 40 at the same bid and quantity. PRE ends at
byte 152; U ends at 189. No session directory or status history is supplied.

| Scenario | Meaning of selected final fields |
| --- | --- |
| `before-u` / `at-u` | External bid quantity stays 80; shares ahead are 40 / 80 under the declared tail convention |
| `no-feed` | No captured inventory at decision; submission is skipped and feed remains pending |
| `arrival-pending` / `ack-pending` | Exchange idle / live; locally both requests remain pending |
| `cancel` | Own exchange/local remainder reaches zero; historical U still applies |
| `cancel-ack-pending` | Exchange cancelled; local state `cancel_pending`, confirmed remainder 1; response due 112 |
| `cancel-arrival-pending` | Exchange still live; cancel arrival due 111, beyond horizon 110 |
| `delayed-seed` | Observed PRE origin 100/delivery 110; exchange already POST, with 80 shares ahead |

`inventory_sha256.pre/post` identifies the entire ordered logical inventories.
`observed_inventory.sha256` identifies the captured inventory delivered to the strategy;
join it to those top-level digests. Identical BBO does not mean identical references
or FIFO. A feed delivery never acknowledges our own submission. Null confirmed quantity
means unknown. `pending_by_kind` and `next_pending_ns` describe unapplied events; printing
them never extends the inclusive horizon. A repeated command starts a new example.

The five frames total 189 bytes. Their generated SHA-256 identifies fictional bytes;
all three raw/status/source authentication flags remain false. The seed is explicitly
hand supplied, with consistent `absent_in_wire` MPID knowledge for A orders. The existing
builder parses the U; this example does not reconstruct a historical prefix. Fills,
positions, cash changes and fees stay zero. No empirical fill or actual venue-priority
claim follows.

## What was checked

The [aggregate evidence](verification.json) binds the first integration execution and
independent retained-output review. Full expected reports were frozen before the public
example existed, using the previous synthetic hand literals; only fictional source,
attribution and inventory identities are mechanically projected. Expected queue outcomes
are never calculated by the example or its CLI verifier.

| First execution | Result |
| --- | --- |
| Child commands | 20 pass: two defaults, nine singles, help and eight intended refusals |
| Accepted reports | 11, containing 27 scenario instances across nine distinct configurations |
| Full typed objects and serialised stdout | Exact agreement with frozen expectations |
| Repeated default stdout | Byte-identical |
| Child environment | Three byte-identical public source copies, empty cwd, Python `-B -E -s` |
| Protected inputs / retained outputs | 87 / 44, unchanged |
| Independent retained review | 136 small files authenticated; no discrepancy |
| New historical states, fills or performance measurements | Zero |

Each child has a 10-second timeout and 1 MiB limit per stdout/stderr stream. Actual argv,
working directory, exit and timeout state are recorded before result checking; both
logs are retained on disk.
All normal child stderr and both parent logs are empty. The first run has no unexpected
refusal, timeout or child-created file; no implementation correction or rerun follows.
Eight invalid commands deliberately produce argparse errors. Dependency isolation here
is not an operating-system filesystem sandbox.

Tests, literal fixtures and execution outputs stay private/ignored. For a maintainer
with the sibling harness, the recorded pre-commit verification command, expressed
from the feed checkout, is:

```bash
python3 ../itch-feed-handler-tests/test_one_u_demo.py \
  --demo-sha256 485f4970a0cbf9ea7a21095408d21b41b0f237e718b55a59eeec6de612113658 \
  --output out/one-u-demo-integration-fresh
```

The output path must be new. This one-shot evidence runner admits main
`5f2ad7dc068682fad63eed6a680ba460f4db389b` plus the exact untracked demo; it
refuses a later committed checkout. The public example commands above remain usable.
The retained actual command used absolute paths from the dossier root. At that
execution, the old 60 implementation files matched current main HEAD;
the new demo was separately hash-bound and uncommitted. Later documentation/commit
checks do not rerun the model. No raw scan/hash, vendor or C++ book replay, build,
sanitiser or benchmark runs in this increment. Complete independent historical coverage
remains 37 states, established by the earlier records.
