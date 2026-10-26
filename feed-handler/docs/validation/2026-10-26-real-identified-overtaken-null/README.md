# Overtaken same-price replacements for AMGN, BKNG, MDLZ and ISRG: a null result

[The first overtaken run](../2026-10-25-real-identified-overtaken/README.md) and
[its repeat on four more symbols](../2026-10-25-real-identified-overtaken-new-symbols/README.md)
found nine same-price replacements that other displayed orders overtake on the canonical
Nasdaq TotalView-ITCH 5.0 file for 30 December 2019 (8,251,407,909 bytes). This record
asks the same day the same question for four further symbols. None of the eight requests
finds a window. The null was confirmed by an independent re-scan rather than replaced by
a request that would succeed.

## Selection, frozen before the file was read

The rule, the capture tool and its binary are those of the earlier overtaken records,
unchanged: the first maximal run, at or after the stated time, of at least three of the
symbol's own messages that are all U, keeping at most 16, whose kept U include a
same-price replacement with at least one displayed order ahead of the old order and at
least one behind it (`need = queued_same_price_overtaken`); a run that fails is skipped
whole. The requests are AMGN, BKNG, MDLZ and ISRG from 10:05:00 and from 13:15:00. No
earlier request named these symbols and neither time had been used on this day. The
request file was written and hashed before the file was opened, and it states that a
request finding nothing is recorded as null, without substitution.

## Results

- **Capture:** the whole file was scanned (268,744,780 messages), with zero book
  anomalies and zero bad frames; every request reports no window, so no state was
  captured and nothing was exported. The harness records the empty checkpoint list as
  such instead of starting the exporters.
- **Independent confirmation:** a separate re-scan with its own ITCH parser and FIFO
  book (Python, no code shared with the C++ tool or the exporters) finds no window
  either, under the tool's documented behaviour and under the literal wording of the
  rule, with zero book anomalies over the same 268,744,780 messages; all four symbols are
  present in the stock directory. The same unchanged script, on the same file, had
  reproduced the five windows and three nulls of
  [the previous record](../2026-10-25-real-identified-overtaken-new-symbols/README.md)
  exactly, which serves as its positive control.
- **Why there is none:**

  | Request | U-only runs of 3+ | With a same-price U | Old order not first | With an order behind |
  |---|---:|---:|---:|---:|
  | AMGN from 10:05 | 966 | 40 | 26 | 0 |
  | BKNG from 10:05 | 2,053 | 2 | 1 | 0 |
  | MDLZ from 10:05 | 864 | 0 | 0 | 0 |
  | ISRG from 10:05 | 892 | 0 | 0 | 0 |
  | AMGN from 13:15 | 432 | 17 | 15 | 0 |
  | BKNG from 13:15 | 1,147 | 0 | 0 | 0 |
  | MDLZ from 13:15 | 351 | 0 | 0 | 0 |
  | ISRG from 13:15 | 417 | 0 | 0 | 0 |

  AMGN has many runs with a same-price replacement behind other orders, but in every one
  the replaced order was already last at its level, so no order is overtaken and the
  condition fails. MDLZ and ISRG never keep the price in such runs.
- **Input identity:** the full file hashed before and after the capture, and again
  after the re-scan, gives SHA-256 `5d81c2e1…5bac610f` each time.
- **Coverage:** unchanged at **458** distinct, independently matched displayed L3/FIFO
  states. A null adds none.

## Limits

One Nasdaq trading day from 2019, not live data. The null holds for these eight requests
and this rule only; it says nothing about these symbols at other times or on other days,
and the run counts are not a frequency estimate. They cover only U-only runs of at least
three messages from the stated times. Displayed FIFO rank is not actual exchange
priority. The capture took 159 s under background QoS: a single run, not a benchmark.
[The aggregate](result.json) records every identity. Order references, prices and
per-event outputs stay private.
