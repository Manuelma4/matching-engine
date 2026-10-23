# Same-price identified-observer design evidence

Gate 22 freezes one QQQ replacement for the existing atomic identified observer.
The [contract](../../SAME_PRICE_OBSERVER.md) was independently reviewed and committed
at `4d016da2744fec6709fb102b03044471c42a836c` before freezing. The
[aggregate](design.json) records identities, source reviews, the first refusal,
corrected repeated freezes and independent expectation audit.

This is a design result. No observer, retained-input runtime producer, book helper,
raw scan, reference replay, C++ test/build or performance experiment runs here.
The two complete inventories were already independently matched in
[Gate 21](../2026-10-23-same-price-l3/README.md); historical coverage stays at
37 distinct source states.

## What passed

Two corrected fresh freezes contain the same five files byte-for-byte. The oracle
is 16,935 bytes, SHA-256
`1128c4beded4c28c4e70cc543809c861628db1a044fd30dbe785d6c33fdfb928`.
Its manifest is 24,893 bytes, SHA-256
`eaf7d2e40d24d5fe81c0c83ed35fc43df93d3f1d80a9726f0e845492143ace79`.
All 74 protected originals remain unchanged through each corrected publication.

A separately written auditor derives all state summaries, complete ordered core
hashes, watched FIFO ranks, U diagnostics and observation profiles from the pinned
independent CSV/summary, original frame and source clocks. It does not import the
observer or freezer, read handwork outcomes, or use produced observer states as
expected data. Its 81 consumed identities remain unchanged through publication.
The successful audit is 28,160 bytes, SHA-256
`4596c220073a9136e7a2c64c520af01b0b7db7a79dd26ac7fc810677d7a764b6`.

The expected profile counts are:

| Profile | Probes | Available | Delivered snapshots | Pending | Captured row instances |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero | 4 | 3 | 2 | 0 | 37,680 |
| one_ms_clipped | 3 | 0 | 0 | 2 | 15,072 |
| one_ms_complete | 7 | 3 | 2 | 0 | 37,680 |
| undelivered_seed | 3 | 0 | 0 | 2 | 15,072 |
| Total | 17 | 6 | 4 | 4 | 105,504 |

Captured rows count repeated source inventories and returned probe inventories.
The 105,504 expected instances add no independent historical source points.
The complete profile explicitly extends its observation horizon by one millisecond;
it admits no additional source events and performs no EOF flush. The final profile
places seed delivery exactly one nanosecond beyond its horizon.

All four isolated altered-expectation copies are rejected at their intended guards:
inherited unknown attribution relabelled absent in wire; new POST rank changed from
tail rank 13 to 2; a coherent-looking final clipped probe supplied with event/state
1/2 before delivery; and a Boolean supplied as integer fact index. The causal
preflight rejects the future probe at its `delivery_ns`, before literal equality.
These controls test the expectation auditor; they are not observer-runtime tests.

## First refusal and source-review correction

The first two freezes repeated, but the first auditor invocation exited 1 before
oracle parsing or outcome derivation, at `manifest.protected_inputs[0].path`.
The freezer sorted `Path` objects by their components; the auditor expected
alphabetical ordering of the complete absolute-path strings. Both lists contained
the same 74 identities. The failed command, empty stdout, 1,711-byte stderr, first
source snapshots and initial repeated freezes are retained and identified in the
aggregate. No successful audit receipt was published for that attempt.

The only freezer correction is `sorted(guard.files, key=str)`. Fresh version-two
freezes repeat exactly; their oracle bytes equal the initial oracle bytes. The
auditor then changes only its freezer/manifest identity pins and admitted directory
names. Its derivation, strict ordering/type/clock guards and four controls stay
unchanged. The second audit invocation exits zero with empty stderr. Expectations
were not changed to fit output.

Before the first invocation, source review also replaced two unbounded audit-receipt
readbacks with bounded regular-descriptor reads, exact bytes and owned-inode checks.
The original reviewed source is retained. That correction precedes execution and
is separate from the actual manifest-ordering refusal.

## Recorded commands and next gate

The accepted commands ran from the feed repository at clean main `4d016da`, with
the unchanged engine at `dbd280185a0d45f0839881caeff8d535bcd56779`:

```bash
python3 ../itch-feed-handler-tests/freeze_same_price_observer.py \
  --output out/same-price-observer-oracle-v2
python3 ../itch-feed-handler-tests/freeze_same_price_observer.py \
  --output out/same-price-observer-oracle-repeat-v2
python3 ../itch-feed-handler-tests/audit_same_price_observer_design.py \
  --oracle out/same-price-observer-oracle-v2/oracle.json \
  --output out/same-price-observer-oracle-audit-v2
```

These are the recorded private-environment commands. Existing output directories
are immutable and rejected on reuse; the auditor pins its original source context
and freeze paths. A later run needs a separately reviewed context/path update,
rather than silently admitting a later commit. The public repository excludes the
private harness, named-order expectations, frames and historical data.

Gate 23 must implement the separate fixed retained-input binder, use the unchanged
generic structural helpers after admission, and compare two actual producer/verifier
runs against this frozen target. It must check the complete inventories and probe
contents: unchanged BBO cannot reveal an incorrectly delivered replacement FIFO.
Preserve the foreign PRE boundary, one atomic U, inherited unknown attribution and
all pending deliveries. Do not relax either legacy canonical admission profile.

Raw and prefix authentication and the external reconstruction are inherited from
Gate 21, including its separate-pass hashing timing qualification. Logical raw
verification remains false. This design establishes neither a new source sample nor
actual matching priority, hidden liquidity, session/strategy eligibility, hypothetical
fills or a performance result. All 59 public implementation files remain unchanged.
