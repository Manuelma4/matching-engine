# Four later-session displayed inventories independently matched

MSFT and QQQ at the fixed noon and 15:30 feed-clock targets now pass complete
displayed-order comparison on Nasdaq 2019-12-30. All 55,105 ordered row instances and
11,837 price-level instances across the four states agree exactly with the pinned
MIT-licensed itchbook implementation. Every state is both-sided, deeper-level and
multiorder. Independent displayed L3/FIFO coverage increases from **37 to 41 distinct
states**; these are sampled reconstructed inventories, not actual exchange priority.

## Boundaries and identity

Both independently written C++20 selectors agree on 235,718,762 global frames and
the 7,196,832,374-byte prefix through the final closing witness. Their complete
selection also equals the [first attempt's](../2026-10-23-later-session-attempt/README.md)
selection, before any helper starts. No target, request or helper policy was changed.

The inclusive targets are 12:00 and 15:30, in nanoseconds since Eastern midnight.
The actual last global frames at or before them are timestamped
11:59:59.999541726 and 15:29:59.999654927. A first-greater witness closes each cut;
it is not applied to the exported book. Both symbols share each exact global cut.
The [source contract](../../LATER_SESSION_L3.md) differs explicitly from the earlier
pre-message BBO grid convention.

Fresh full-file hashes before and after this phase match the fixed 8,251,407,909-byte
input. Separate hashes bind each cut prefix and its longer witness prefix. Current
source snapshots remain identical at documentation commit `0deb570`; all functional
C++ files and reused helper identities match their original build authorities.

## What ran and matched

Local and reference exporters each run twice. Every CSV contains 55,105 rows; all
four ordered CSVs are byte-identical. Each implementation's own summary also repeats
byte-for-byte. Cross-implementation summaries retain their different validation
scopes: all prefix symbols locally, selected symbols in the reference. Both scopes
report zero anomalies; matching order files do not validate unselected reference books.

The strict comparator checks all four requested state identities, source boundaries,
references, integer prices, shares, side, FIFO rank, missing/extra rows and reconciled
side totals. All mismatch counters are zero. The four files contain 220,420 exported
row instances, not 220,420 unique orders. They represent sixteen exported state
instances but only four new distinct historical states. Persisting orders may also
reappear between the two target snapshots.

## The first refusal remains part of the record

The first phase stopped safely on an unavailable RSS measurement. After frozen
synthetic diagnostic checks and independent source/launch review, one instrumented
reproduction used the same 100 ms query timeout, 250 ms maximum gap, 12 GiB stop
threshold and every original phase/output/disk limit. Only bounded query-failure
telemetry was added; there was no retry loop or missing-sample allowance.

This phase records 1,514 successful RSS samples, no query failures and no injection.
Maximum observed RSS is 5,794,676,736 bytes; the largest measured sample interval is
approximately 193.5 ms. These observations do not bound instantaneous peaks or prove
provider reliability. The first refusal's underlying cause remains unrecorded. A
later success does not diagnose or erase it. Phase timings are supervision evidence,
not a benchmark or speedup claim.

## Artefacts and limits

[The aggregate](result.json) retains exact input, source, executable and original
private phase-record identities. Full requests, order CSVs, supervision samples and
private harnesses remain ignored and outside this public repository. The record is
not a standalone rerun script. No C++ system implementation changed in this gate;
C++ performs selection/reconstruction and Python supplies supporting orchestration.

Earlier BBO comparison counts are unchanged. This result adds no every-event or
unselected-symbol proof, separate exchange/vendor oracle, session-status admission,
empirical fill calibration, hidden-liquidity knowledge or counterfactual market response.
