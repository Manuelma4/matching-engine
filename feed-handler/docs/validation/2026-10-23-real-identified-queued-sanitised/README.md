# Queued same-price capture under ASan/UBSan on real data

[The queued same-price record](../2026-10-23-real-identified-queued/README.md) added a
new selection path to the capture tool: before a replacement is applied, the tool looks
up the old order's level and counts the displayed orders ahead of it. That path had been
run under AddressSanitizer and UndefinedBehaviorSanitizer only on a 13-message
hand-built file. This record runs the same eight frozen Nasdaq-day requests again, on
the full real file, with an instrumented build, and compares every output byte with the
Release capture.

## Method, fixed before the run

A short plan was written and hashed before the file was read. It names the request file
(unchanged from the queued record), the instrumented binary and its source, and three
pass criteria: exit status 0 with no sanitiser report; the checkpoint list, the state
snapshots and the JSON summary byte-identical with the Release capture; and the full
input hash equal before and after. A failure was to be kept on record, not replaced.

The build is Debug with `-fsanitize=address,undefined -fno-sanitize-recover=all
-fno-omit-frame-pointer`, applied to the decoder, the book, the observer library and the
tool alike, so any memory error or undefined behaviour stops the run.

## Results

- **Sanitisers:** exit status 0; no AddressSanitizer or UndefinedBehaviorSanitizer
  report over 190,393,850 messages, with zero book anomalies and zero bad frames.
- **Outputs:** the checkpoint list, the 414,187 snapshot rows of the 37 states and the
  summary with its facts are byte-identical with the Release capture (snapshot SHA-256
  `e9512e2e…`), so the queued-rank test selects the same windows and reports the same
  ranks in both builds.
- **Input identity:** the full file hashes to `5d81c2e1…` before and after.
- **Coverage:** unchanged at **161**. The states are those of the queued record; a
  re-run checks the tool, it does not add states.

## Limits

One day, one request set and one instrumented run. The sanitisers check only the code
paths that these requests reach; they prove no absence of defects elsewhere. The
instrumented run took about 40 minutes under background QoS and a debug build; that
figure describes the check, not the tool's speed. [The aggregate](result.json) records
every identity. Order references, prices and per-event outputs stay private.
