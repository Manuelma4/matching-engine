# Offline restart design evidence

This is Gate 12's reviewed design and frozen expectations, recorded on 2026-10-22.
It does not execute a restart. Read the [policy](../../OFFLINE_RESTART.md),
[closed expectation schema](../../OFFLINE_RESTART_ORACLE.md) and
[aggregate report](design.json) together. Gate 13 owes the private runtime and actual
ownership, replay and promotion verification.

The policy/schema commit is `72d13f5849ca56fc42f583081e16b3b03b2adcc5`. The 42 public
implementation files remain identical to Gate 11's verified source commit
`88ff5d76daafb70726f7fb442b4954f2ff38cb98`; its evidence was committed separately as
`5ada51a59911cbff665f97165566f8ebb05547ba`. The design report keeps those roles distinct.

Two separate writer processes produce identical oracle and manifest bytes. A separately
written auditor accepts every complete case object, source join and retained state
reference, with 69 consumed input identities unchanged. Four in-memory altered copies
fail at the intended semantic/type path. These are expectation-auditor checks. No
restart implementation, C++ test, new sanitiser run or historical/reference replay ran
for this increment. The aggregate recorder freshly hashes 137 distinct small retained
files, including the implementation files and process/review receipts.

| Frozen artefact | Bytes | SHA-256 |
|---|---:|---|
| Private `oracle.json` | 159,212 | `aa4ba251f3a3294d3589a8128257d5f62259f218430458ee25f1d6fad9d80db5` |
| Private `freeze-manifest.json` | 13,784 | `987ae273e587d6536b6e9cab7b6adedbca818354de624f1c7327a9ef1f49fc95` |
| Private independent `review.json` | 23,098 | `95092f4e265f0592982cbc4cf824f9a12ca2b3d2f4a30ef87fe81266be3ca0df` |

The twelve cases plan 149 arrivals, 85 applied callbacks, 84 returned callbacks, 42
control probes and two admission refusals. No runtime success rate follows. The
395 state references and 212,549 referenced rows count repeated metadata references,
including seed, diagnostic, outcome and control references. They are not executed book
comparisons or new historical coverage. Canonical coverage remains thirteen source
facts and fifteen independently reconstructed inventories/16,886 ordered row instances.

The four negative controls change a returned-callback count, early-end promotion,
a refused admission's null receiver and an integer to a boolean. Each is rejected at
its exact expected field, rather than an unrelated manifest/hash failure. Frozen disk
files are untouched. The MSFT applied/returned difference is intentional: one callback
physically applies an add, then throws before returning. The design requires its
partial book to be discarded and the next generation to start from the original seed.

To reproduce the oracle serialisation and expectation audit in the original workspace,
the private sibling scripts and pinned ignored Gate 7/9/11 artefacts must be present.
Run from the workspace parent using fresh output directories:

```bash
python3 itch-feed-handler-tests/freeze_restart_oracle.py \
  itch-feed-handler/out/offline-restart-oracle-fresh
python3 itch-feed-handler-tests/review_restart_oracle.py \
  --oracle-dir itch-feed-handler/out/offline-restart-oracle-fresh \
  --freeze-sha256 987ae273e587d6536b6e9cab7b6adedbca818354de624f1c7327a9ef1f49fc95 \
  --output itch-feed-handler/out/offline-restart-review-fresh
```

These commands do not download market data, recreate the independent historical
reference or run C++. The exact writer, auditor, interpreter, inputs and original
commands are identified by the aggregate report and its retained receipts. The private
aggregate recorder is bound to the pre-publication contract commit and original evidence;
its recorded source snapshot predates this documentation/evidence commit.

The official MoldUDP64 PDF is retained and rehashed, with the receiver example on page
six reread during design. The profile models recomputation from authenticated local
inputs. Requests, venue packet availability, sockets, live timing, allocation exhaustion
and queue/fill integration remain outside the evidence.
