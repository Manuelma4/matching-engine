# References

Sources used while building this feed handler. Open-source projects were read for ideas
and cross-checks only: no code was copied. Licences as recorded on 2026-10-22.

## Specifications and data

| Source | Use |
|---|---|
| Nasdaq, [TotalView-ITCH 5.0](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf) (revision of April 2023) | Message layouts and semantics. Every offset in `messages.hpp` was extracted from this document and checked byte by byte against an independent reading of open-source parsers: no differences |
| Nasdaq, [BinaryFILE](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/binaryfile.pdf) | Framing of the sample files: 2-byte big-endian length prefix, zero-length end-of-session record |
| Nasdaq, [MoldUDP64](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/moldudp64.pdf) | Packet framing for a future live receiver |
| [emi.nasdaq.com/ITCH](https://emi.nasdaq.com/ITCH/) | Public sample days. Market data and derived per-message files are never committed |

## Related work

| Project | Licence | Relation |
|---|---|---|
| [groovg/itch-book](https://github.com/groovg/itch-book) | MIT | ITCH book reconstruction with an index-structure ablation and BBO validation against a vendor feed; the validation approach to follow on real data |
| [KareemJandali/itchbook](https://github.com/KareemJandali/itchbook) | MIT | ITCH parser, L3 book and fill models in one repository; its published message census of 2019-12-30 is the reference count for that day |
| [chronoxor/CppTrader](https://github.com/chronoxor/CppTrader) | MIT | ITCH handler and market manager with published per-tier costs on a 2017 sample day |
| [Manuelma4/matching-engine](https://github.com/Manuelma4/matching-engine) | MIT | Source of the order slab, level FIFO and open-addressing index used here, and of the order flow behind the engine loopback |

## Pinned canonical census

The independent reference for `12302019.NASDAQ_ITCH50.gz` is
[itchbook's published census](https://github.com/KareemJandali/itchbook/blob/3c646f9da182136125059243b475f7b8baa53773/validation/census-2019-12-30.json),
pinned to commit `3c646f9da182136125059243b475f7b8baa53773`. A small
[normalised manifest](reference/nasdaq-2019-12-30-itchbook.json) retains the factual
aggregates, source artifact identity and provenance limits. No implementation code or
market-data records were copied.

The reference was produced by a separate implementation of the same exchange feed.
Its histogram first appeared in August 2026, before this project's validation run.
Repository and commit dates are metadata rather than independent archival timestamps.
The census publishes no SHA-256 of its market-data input: its own JSON artifact hash
identifies the reference document, not the Nasdaq archive. Aggregate agreement must
therefore be described separately from input identity and independent quote validation.

## Historical-window semantic reading

The bounded projector uses the April 28, 2023 TotalView-ITCH 5.0 specification linked
above, retrieved 2026-10-22: 1,200,722 bytes, SHA-256
`45e0531d1b4b3beb886e9618b2ab824a5aa9bda3a99c0dff03509306e68aacc3`.
Sections 1.1–1.2 and 1.4–1.5 inform the status, execution and replacement distinctions;
the [projector contract](HISTORICAL_WINDOW.md) separately identifies its own restrictions.

Nasdaq's [ITCH FAQ](https://www.nasdaqtrader.com/Content/TechnicalSupport/FAQs/ITCH_FAQ.pdf),
search-indexed page 3, supports the execution/multi-fill distinction. Live retrieval
returned HTML/error, so no downloaded FAQ PDF identity is asserted. Reference PDF
bytes and external implementation archives remain ignored; only identities and
aggregate evidence are versioned.
