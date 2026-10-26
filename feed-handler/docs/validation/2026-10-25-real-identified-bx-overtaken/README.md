# Same-price replacements that other orders overtake, on BX: a null result

[The Nasdaq-day record](../2026-10-25-real-identified-overtaken/README.md) asked for
windows holding a replacement that keeps the old order's price while at least one
displayed order stood ahead of the old order and at least one stood behind it, and six
of eight requests found one. This record asks the same question of the second venue,
Nasdaq BX on 30 July 2019, with its own frozen requests. None of the eight requests
finds a window. The null was confirmed by an independent re-scan rather than replaced
by a request that would succeed.

## Selection, frozen before the file was read

The rule and the capture tool are those of the Nasdaq-day record, unchanged (same source
and binary): the first maximal run of at least three of the symbol's own messages that
are all U, keeping at most 16, whose kept U include a same-price replacement with orders
both ahead of and behind the old order (`need = queued_same_price_overtaken`); a run
that fails is skipped whole. The requests are AMD, MU and EBAY, the three symbols with
windows on the Nasdaq day, plus TSLA, each from 12:00:00 and from 15:15:00. No earlier
BX request named these symbols, and neither time had been used on BX. The request file
was written and hashed before the BX file was opened, and it states that a request
finding nothing is recorded as null, without substitution.

## Results

- **Capture:** the whole file was scanned (28,734,686 messages), with zero book
  anomalies and zero bad frames; every request reports no window, so no state was
  captured and nothing was exported. The harness records the empty checkpoint list as
  such instead of starting the exporters.
- **Independent confirmation:** a separate re-scan with its own ITCH parser and FIFO
  book (Python, no code shared with the C++ tool or the exporters) finds no window
  either, both under the tool's documented behaviour and under the literal wording of
  the rule, with zero book anomalies over the same 28,734,686 messages. As a positive
  control on the same file, the unchanged re-scan reproduces
  [the earlier BX mid-session record](../2026-10-24-real-identified-bx-midsession/README.md)
  exactly: its NFLX window (seed and first replacement message, three facts) and its
  six nulls, under both readings.
- **Why there is none:** after 12:00, AMD has 1 U-only run of three or more messages,
  TSLA 10, MU and EBAY none; after 15:15, TSLA has the same 10 and the others none. No
  replacement in any of these runs keeps its price, so none can satisfy the condition.
- **Input identity:** the full file hashed before and after the capture, and again
  after the re-scans, gives SHA-256 `6741035b…a4b842e5` each time.
- **Coverage:** unchanged at **441** distinct, independently matched displayed L3/FIFO
  states. A null adds none.

## Limits

One BX trading day from 2019, not live data. The null holds for these eight requests
and this rule only; it says nothing about BX at other times, other symbols or other
days, and it is not a frequency estimate. The run counts cover only U-only runs of at
least three messages from the stated times. Displayed FIFO rank is not actual exchange
priority. Timings in the aggregate are single runs under background QoS, not a
benchmark. [The aggregate](result.json) records every identity. Order references, prices
and per-event outputs stay private.
