# Later-session source agreement; book comparison refused

The first bounded attempt on Nasdaq 2019-12-30 selected the same four requests in
two independently written C++20 source enumerators. The subsequent local book replay
was stopped because its resident-memory measurement became unavailable. The phase
failed; no reference book, repeated export or order comparator ran. Independent
displayed L3/FIFO coverage remains **37 distinct states**, with **zero new states**.

## What passed

- The frozen prerequisite cases passed once: eight hash-vector checks (two successes,
  six intended refusals) and thirteen metadata checks (four successes, nine intended
  refusals). These are synthetic checks, not additional market states.
- Both C++ selectors agreed on the fixed noon and 15:30 feed-clock targets for MSFT
  and QQQ, their exact global cuts, first-greater witnesses, directories and all four
  requests. They consumed 235,718,762 frames through a 7,196,832,374-byte prefix.
- The cuts retain their actual timestamps: 11:59:59.999541726 and 15:29:59.999654927.
  The witnesses close the inclusive targets; they are not applied to exported books.
- Fresh full-file SHA-256 checks before and after the attempt matched the fixed
  8,251,407,909-byte input. Four separate cut/witness prefix hashes were retained.
  Source identities and the consolidated source commit remained unchanged.

## Why the phase failed

The first local replay produced 558 valid RSS samples, then the metric provider
returned no usable measurement while the child was still running. The supervisor
recorded `metric_unavailable`, sent SIGTERM and reaped the child with return code
`-15`. The measured stop-to-reap delay was approximately 22.7 ms. No order export or
summary had been produced; the child logs were empty.

The maximum **observed** RSS was 4,010,147,840 bytes. This is not an instantaneous
peak bound. No sample exceeded the 12 GiB stop threshold; the largest recorded
sampling interval was approximately 213.2 ms, below the 250 ms interval allowance.
An unavailable sample is a separate refusal condition. A small observed value cannot
justify continuing without measurements.

The provider used `/bin/ps` with a 100 ms command timeout. It returned the same
unavailable value for several failure categories and retained no category detail.
A timeout is plausible but **not established** by this record. The next diagnostic
step must distinguish provider failures on synthetic inputs before another canonical
attempt. Keep this first failure, its fixed requests and the existing resource limits.

## Scope and reproducibility

[The aggregate](result.json) binds the source/input/reference identities, executed
stages and original private phase-record digest. Detailed requests, supervision
samples, per-child files and private harness sources remain outside Git under the
existing private-test convention. This aggregate is not a standalone rerun script.
The [prospective contract](../../LATER_SESSION_L3.md) defines the unchanged experiment.

This is a failed measurement admission, with no established local/reference book
discrepancy and no successful independent comparison. Both selectors share the
wire/header specification, so their agreement is implementation independence rather
than a separate vendor oracle. The attempt grants no queue, status, fill or performance
claim. C++20 runs the source selection and book reconstruction; Python coordinates
the private checks and reports. No core implementation or model policy changed.
