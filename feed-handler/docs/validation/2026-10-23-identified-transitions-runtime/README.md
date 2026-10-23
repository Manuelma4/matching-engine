# Verified exact-source identified transitions

Gate 16's separate [adapter](../../../bench/identified_transitions.py) connects four
authenticated canonical Nasdaq windows to the unchanged logical observer. Its
[interface](../../IDENTIFIED_TRANSITIONS_RUNTIME.md) implements the reviewed
[admission profile](../../IDENTIFIED_TRANSITIONS.md). Expected results were independently
frozen in [Gate 15](../2026-10-23-identified-transitions-design/README.md) before implementation.
The [aggregate evidence](verification.json) records actual execution and its limits.

## Actual results

The first focused run passes all twenty private Python methods without skips. The
separately reviewed synthetic fixture contains five mutations, nine complete states
and 36 source-row instances; its sixteen profiles check 57 probes, sixteen available,
and 210 captured row instances. It covers repeated symbols, non-chronological IDs,
shared global Q seeds, exact partial timestamp groups, named non-head cancellations,
populated replacement destinations, same-price U and inherited unknown attribution.
It also rejects omitted selected facts, unsupported selected metadata, invalid domains,
retired references, short writes, close failures and publication-time input changes.
Only the synthetic outer evidence admission is mocked; the public CLI has no bypass.

After those checks, implementation and interface documentation were committed on clean
main as `8087757bdc08b8ee407abd9815c571d21be21e90`. Two actual canonical producer runs
and two separate independent verifier processes pass on their first attempt. All four
processes exit zero with empty stderr.

| Canonical quantity, per producer/verifier pair | Actual result |
|---|---:|
| Windows / source facts | 4 / 16 |
| Complete retained independent source states | 20 |
| Ordered source-row instances | 22,089 |
| Observation profiles / probes | 16 / 164 |
| Available / unavailable probes | 99 / 65 |
| Observer captured row instances | 218,428 |
| Detail files | 32 |
| Discrepancies | 0 |

The sixteen facts are three A, six D, one E, two X and four U. Every copied diagnostic,
complete ordered inventory, source join, attribution field, delivery, pending index
and probe agrees with the frozen independent inputs. The verifier imports neither the
adapter nor the observer and derives no expected value from actual output.

The 218,428 counts source and returned-probe inventory rows inside the sixteen
observation results. It includes eighty repeated source snapshots and 99 available
probe inventories. The verifier also checks twenty standalone source inventories and
four ledger seeds; these repeated copies do not add historical samples. Gate 16
reuses Gate 14's twenty states, keeping combined independent depth coverage at 35.

Each producer freshly hashes the full 8,251,407,909-byte raw day and the exact
284,563,784-byte prefix before and after production. Both identities match the accepted
values. Each scan starts at byte zero and ends after global frame 8,300,042, without
consuming a later timestamp witness. Every selected-locate occurrence inside a declared
interval is considered; unsupported types or a mismatch with the retained independent
census fail. Full-file hashing establishes identity; it is not a new full-day semantic
reconstruction.

All 32 detail files repeat byte-for-byte across the two productions. Aggregate reports
contain different output paths, so no report-byte equality is claimed. All 174 recorder
input identities and each verifier's 99 consumed identities remain unchanged through
publication. The 42 legacy implementation files match their accepted Git blobs; the
separate adapter is the forty-third implementation file.

## Controls and publication

After authenticating and completely checking each normal output, the independent
verifier tests two altered in-memory copies. It rejects lost inherited uncertainty in
QQQ's second U at the copied pre/post attribution guard, and a correctly identified
post-first-U MSFT inventory supplied one nanosecond too early at the future-delivery
guard. Both cases are rejected in each verifier run. These are two verifier controls,
separate from normal producer counts and Gate 15's four altered expectations.

Source review found and corrected report-publication gaps before the first execution:
the new report writer now uses bounded readback and final source/input checks, removes
only its owned failed inode, and refuses a non-ignored report destination without
writing there. The focused suite exercises these failures. Both unit and canonical
first execution attempts pass; there is no failed runtime attempt hidden by a rerun.
Earlier Gate 14/15 experiments and recorder failures retain their own scopes.

The private orchestration aggregate has 72,714 bytes, SHA-256
`bd7e31174818d4bf386765fde275114ed5277c23e380bcd3ae8071ebac8bc17d`.
The two 32,849-byte independent runtime audits have SHA-256
`794e0f685e6bf666dfd4a3185f3f51e8b7c62d3a74938c11b57ebe69a3272c53`
and `3bf03beaac76a2d8bbcebe57d069a5a680b7cd75fa638680acd97ac2fba93a59`.
The aggregate links the independent retained-result and unit-evidence reviews.

## Reproduce in the private working environment

Run from the feed repository with the frozen fixture and retained inputs present:

```bash
python3 ../itch-feed-handler-tests/test_identified_transitions.py \
  --module bench/identified_transitions.py \
  --fixture out/identified-transitions-fixture-v1
python3 ../itch-feed-handler-tests/record_identified_transitions.py \
  --output out/FRESH-identified-transitions-runtime \
  --fixture out/identified-transitions-fixture-v1
```

The recorder runs producer → independent verifier → repeated producer → independent
verifier, then checks exact details and final identities. It does not itself reopen
the raw day. A later documentation commit changes the producer's recorded source
commit; it does not require a new historical sample or make report bytes comparable.
The public CLI command is in the interface document. Tests and detailed data stay
in private sibling/ignored storage, rather than the public source repository.

The canonical sample adds no real same-price U, populated-destination queue, full X
depletion, tied-source or raw/effective seed-gap case. The synthetic fixture supplies
separate coverage where stated. Unknown seed attribution remains unknown; reconstructed
FIFO is a declared convention, not recovered exchange priority. No independent book
execution, C++ build/test, sanitiser run, live transport, queue/fill extension, empirical
latency or performance measurement occurs in this increment.
