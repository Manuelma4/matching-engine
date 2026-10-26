# Queued same-price replacements on BX: a null result

[The Nasdaq-day record](../2026-10-23-real-identified-queued/README.md) asked for windows
holding a replacement that keeps the old order's price while that order had at least one
displayed order ahead of it, and all eight requests found one. This record asks the
same question of the second venue, Nasdaq BX on 30 July 2019, with its own frozen
requests. None of the eight requests finds a window. The null was confirmed by an
independent re-scan rather than replaced by a request that would succeed.

## Selection, frozen before the file was read

The rule and the capture tool are those of the Nasdaq-day record, unchanged (same
binary): the first maximal run of at least three of the symbol's own messages that are
all U, keeping at most 16, whose kept U include a queued same-price replacement; a run
that fails is skipped whole. The requests are AAPL, SPY, QQQ and AMZN from 11:00:00
and from 13:30:00, times not used on BX before. The request file was written and hashed
before the BX file was opened, and it states that a request finding nothing is
recorded as null, without substitution.

## Results

- **Capture:** the whole file was scanned (28,734,686 messages), with zero book
  anomalies and zero bad frames; every request reports no window, so no state was
  captured and nothing was exported.
- **Independent confirmation:** a separate re-scan with its own ITCH parser and FIFO
  book (Python, no code shared with the C++ tool or the exporters) finds no window
  either, both under the tool's documented behaviour and under the literal wording of
  the rule, with zero book anomalies over the same 28,734,686 messages. As positive
  controls, the same re-scan reproduces the windows of the hand-built test file and all
  eight windows of [the earlier BX record](../2026-10-23-real-identified-bx/README.md)
  (seed and first replacement message, number of facts).
- **Why there is none:** after 11:00, AAPL has 1 U-only run of three or more, SPY 130,
  QQQ 3 and AMZN 11 (after 13:30: 1, 122, 3 and 11). Among the U each run would keep,
  only one run in the whole set (a SPY run after 13:30) contains a replacement at an
  unchanged price at all, and every such replacement in it came from an order that was
  first in its queue, so it gave nothing up.
- **Input identity:** the full file hashed before and after the capture, and again after
  the re-scans, gives SHA-256 `6741035b…a4b842e5` each time.
- **Coverage:** unchanged at **161** distinct, independently matched displayed L3/FIFO
  states. A null adds none.

The comparison stage of the private harness is written for at least one state: with an
empty checkpoint list the exporters stop instead of reporting an empty comparison. That
is recorded as a harness limit; there was nothing to compare.

## Limits

One BX trading day from 2019, not live data. The null holds for these eight requests
and this rule only; it says nothing about BX at other times, other symbols or other
days, and it is not a frequency estimate for queued replacements. Replacements on BX
are mostly at a new price, but the counts above cover only U-only runs of at least
three messages from the stated times. Displayed FIFO rank is not actual exchange
priority. Timings in the aggregate are single runs under background QoS, not a
benchmark. [The aggregate](result.json) records every identity. Order references, prices
and per-event outputs stay private.
