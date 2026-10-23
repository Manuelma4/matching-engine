# Bounded offline restart runtime evidence

[verification.json](verification.json) records Gate 13's completed runtime checks.
The evidence date is 23 October 2026 in Europe/Paris; the recorded processes ran on
22 October in UTC. The private runner implements the frozen
[runtime interface](../../OFFLINE_RESTART_RUNTIME.md) and
[restart policy](../../OFFLINE_RESTART.md).

Each normal execution matched every frozen admission, arrival, EOF, outcome,
lifecycle control and final result. Two Release executions and two ASan/UBSan
executions produced the same 141,169-byte report, SHA-256
`e327cb8c0fa02a71f7e7d8addcd186b19b0494450e115c56f1cf3bb1ce3a9b54`.
The final configure/build and normal runtime stderr files are empty.

| Executed quantity, per normal run | Canonical projection | Synthetic control | Total |
| --- | ---: | ---: | ---: |
| Cases | 10 | 2 | 12 |
| Reserved attempts | 19 | 4 | 23 |
| Constructed generations | 18 | 3 | 21 |
| Promotions | 8 | 1 | 9 |
| Supplied arrivals | 136 | 13 | 149 |
| Applied callbacks | 82 | 3 | 85 |
| Returned callbacks | 81 | 3 | 84 |
| Lifecycle/token controls | 38 | 4 | 42 |
| Admission refusals | 1 | 1 | 2 |
| Complete inventory comparisons | 262 | 23 | 285 |
| Compared order-row instances | 151,384 | 14 | 151,398 |

The partial MSFT callback applies and checks one real add before its deliberate
exception. It contributes to applied callbacks and does not contribute to returned
callbacks. Its entire generation is discarded. A second generation imports the
original seed into a fresh book and receiver. The 21 construction/destruction epochs
show at most one live generation; reviewed ownership scopes complement those traces.
Object addresses are allowed to repeat.

The 285 comparisons include imported seeds, each applied callback, arrival diagnostics,
admitted EOF boundaries and accepted candidate values. Repeated comparisons of an old
inventory are counted repeatedly. These executed figures differ from Gate 12's
395 metadata references and 212,549 referenced rows; neither count is a benchmark.

Two private Release controls reached their intended boundaries:

- Copying the failed partial book's order values into a fresh MSFT generation 2
  fails the independent seed check before a handler. The worker exits 1 with exactly
  `offline restart verification failed: restart seed FIFO/BBO mismatch: msft_partial_apply/2`.
- Omitting the generation ordinal from promotion-token comparison lets the worker
  exit 0 with the wrong denial reason. The independent verifier detects
  `$.cases[1].controls[1].actual.reason`: expected `token_mismatch`, actual
  `already_promoted`. This checks token precedence; it does not demonstrate a
  successful unauthorised promotion.

The retained v1 verifier attempt stopped before any build or worker process because
an integer-only JSON reader encountered a floating diagnostic in a pinned historical
report. A targeted metadata-reader correction led to v2's successful runtime matrix.
Its four builds each emitted a 297-byte signedness-warning diagnostic. A single explicit
character conversion removed that warning; the focused v3 matrix was then rerun.
All four v2 and all four v3 normal reports are byte-identical. The original failure,
successful v2 report, source snapshots and diagnostic identities remain retained.

## Reproduction

Reproduction requires the private sibling harness, the unchanged matching-engine
checkout and the authenticated retained inputs. A public clone alone does not contain
the private runner, frozen per-event oracle or market inventories. The aggregate
records their exact source/input identities. Per-event files remain ignored.

The accepted run used clean `main` at
`81b6d7ccb2e23437927f6ca06a7a0db59a23b77e`, interface SHA-256
`411afe24b7cbd80c37623071a4783bd77a21a2161bc71656595094b37bd63bf5`,
worker SHA-256
`812cb9c85327aac7934f8e75897473a30c65c16be5c2b76573a68a4b249b4797`,
and matching-engine commit
`dbd280185a0d45f0839881caeff8d535bcd56779`.

From the shared workspace, use the current clean main commit and a fresh output name.
The verifier admits only the retained interface and input identities. It creates new
isolated build directories, materialises four action-only CSVs, checks effective
compiler/linker flags, runs the two normal profiles twice, then checks both private
negative builds. It refuses an existing output directory.

```sh
cd "/path/to/Quantitative finance"
restart_source_commit="$(git -C itch-feed-handler rev-parse HEAD)"
python3 itch-feed-handler-tests/verify_offline_restart.py \
  --source-commit "$restart_source_commit" \
  --output "$PWD/itch-feed-handler/out/offline-restart-runtime-reproduction-v1"
```

The worker's direct interface is:

```text
offline_restart BUNDLE_DIR GATE11_ORACLE_DIR SCHEDULE_DIR
```

Run the verifier to authenticate those roles and produce the schedule. A direct worker
invocation alone does not recompute SHA-256 identities. The final aggregate retains all
14 configure/build/process argument vectors, process exit statuses and log identities,
both normal binaries, compilation databases and link commands. ASan/UBSan executions
use `ASAN_OPTIONS=halt_on_error=1:abort_on_error=1` and
`UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`.

## Scope

The 241 protected identities stayed unchanged during the accepted run, including
42 public implementation files and the retained private Gate 11 worker/harness.
An independent retained-output audit matched all four complete reports against the
frozen expectations, rehashed the 241 protected identities twice and found all
285 consumed files stable. It independently confirmed the epochs, executed comparison
counts, compile/link flags and both negative-control outcomes without rerunning C++
or the runtime verifier. Its first attempt had incorrectly required an order-book ABI
definition on generic `mold.cpp`; the corrected check applies to the worker and book,
which consume the L3 layout. That initial audit failure and source remain retained.

Canonical coverage remains the same two selected-symbol projections: 13 retained
facts, 15 independently reconstructed complete inventories and 16,886 original
order-row instances. This increment reads retained small artefacts. It does not reread
the historical raw day, freshly verify that raw identity or rerun the external book.

This is bounded recomputation from available local inputs, with two reserved attempts
and no reset, checkpoint jump, reorder cache or fabricated packet. Seed/availability
refusals occur before construction and do not test allocation exhaustion. The checks
do not establish live retransmission, network availability, receipt clocks, performance,
order eligibility, queue fills or strategy results.
