# Separate ten-second canonical transition experiment

This is a prospective second experiment, frozen before scanning beyond the rejected
one-second prefix or inspecting any new reconstructed state. It incorporates the
complete [original contract](L3_TRANSITIONS.md), whose immutable bytes are 11,223 bytes,
SHA-256 `49792512e02954e1b7f48c7fddc6c07f40f034f6ab6d41421a074af6405cd572`,
committed in `cf25f599ab6d9aea7382be56f86eb73ed8399c50`.

## Retain the first negative result

Version 1's one-second search reached its exclusive deadline without a first MSFT
`X`. MSFT `U`, QQQ `U` and QQQ `X` windows were complete, but the entire selection
failed. No successful checkpoint manifest, book replay, comparison or accepted state
result followed. Its sources, fixtures, failure files and independent failure review
remain retained. See the [negative aggregate](validation/2026-10-23-l3-transitions/initial_selection_failure.json).

Do not revise that run, describe it as passed, or treat its three partial windows as
validated states. The source-only scan exposed event scarcity within the proposed time
budget; it supplied no agreement or disagreement about reconstructed books.

## Exactly two selection substitutions

For this separate experiment only:

- The rule identifier is `first_x_u_four_windows_v2`.
- The fixed `search_duration_ns` is **10,000,000,000**. Every anchor and required tail
  must have a timestamp strictly below `S(Q).timestamp_ns + 10,000,000,000`.

All other original selection and comparison requirements remain binding. In particular,
use the same canonical raw identity, fixed MSFT/QQQ symbols and locates, first post-Q
`X/U` anchors, latest post-Q mutation seed or Q seed, next three same-symbol mutations,
mutation alphabet, role links, global source ordering and deduplication. There are still
at most twenty checkpoints, 16,000,000 global frames, 536,870,912 prefix bytes, 100,000
captured selected headers and 4,096 census rows per window. The last required tail is
the successful replay boundary. A deadline witness is a failure boundary, not a state.

The ten seconds are a finite source-search allowance, not ten seconds of continuous
independently checked states. Preserve complete empty sides/books and prohibit all
book-state, quote, quantity, priority, trading-status and comparator-result filters.
Missing anchors/tails, malformed framing, any bound failure or any discrepancy fails
this experiment. Do not widen it, substitute a candidate or reuse only passing windows.

## Separate sources, execution and evidence

Keep version 1's private sources and tests byte-identical. New private `*_v2.py` copies
may substitute this contract's identity/path, the new rule and duration, their matching
script names and the literal deadline controls. The successful manifest schema and
independent enumeration/delta interfaces remain unchanged. Authenticate both this
document and the incorporated original contract; freeze their committed identities
and review the small source changes before any new scan or test execution.

Use a fresh ignored output directory. Repeat the same independent enumeration before
book exports, both retained Release exporters twice, unchanged complete L3 comparator,
and independent copied-state X/U delta audit. Fresh full raw identity before selection
and after comparison, separate prefix identity, source/reference stability, explicit
repeated-byte checks and all original failure/completeness rules remain required.

Version 2 does not erase the rejected version 1 or extend its coverage claim. Publish
its outcome separately, including any subsequent rejection. Classify observed partial
or full cancellations, same or moved replacement prices and BBO effects only after
the full comparison. The inherited FIFO convention, attribution, hidden-liquidity,
actual exchange priority and queue/fill limitations remain unchanged. No new build,
sanitised historical replay or dependency-equivalence claim follows from reusing the
accepted binaries. The restricted identified-history and transport profiles stay
`A/D/E`; broader admission remains a separate acceptance gate.
