# Canonical cancellation and replacement evidence

Gate 14 investigates independently checked displayed L3 states around real `X/U`
messages. The experiments below are separate records. Source availability, successful
selection and agreement between reconstructed books are different claims.

The [accepted aggregate](verification.json), [one-second rejection](initial_selection_failure.json),
[ten-second rejection](ten_second_selection_failure.json) and [availability aggregate](availability.json)
retain their separate outcomes and exact input/source identities.

## Preserve the rejected timed profiles

The original [one-second contract](../../L3_TRANSITIONS.md) fixed the first post-open
`X` and `U` for MSFT and QQQ, a preceding seed, and the next three same-symbol book
mutations. The one-second selection failed because no MSFT `X` appeared before its
exclusive deadline. Its other three windows were complete, but the whole experiment
failed. It produced no successful checkpoints, book exports or accepted states.

The separately reviewed [ten-second experiment](../../L3_TRANSITIONS_TEN_SECOND.md)
retained the first failure and changed only the rule/deadline allowance. It also failed
without a qualifying MSFT `X`; neither book exporter ran. Its partial windows are not
validated states. Both sources, failure receipts and independent failure reviews remain
retained. Neither failed profile needs to be rerun to reproduce the later experiment.

## Study availability before another comparison

The separate [availability study](../../L3_AVAILABILITY.md) scanned all 16,000,000 frames
in its fixed resource budget, consuming 524,152,398 complete-prefix bytes. It did not
stop at a target event or elapsed-time deadline. The first post-Q MSFT `X` was at global
sequence 8,294,190, **25.002318269 seconds after Q**. That is an observed wire identity,
not an independently validated order transition.

The study used a fresh full raw-file size/SHA-256 before walking and an independent
rehash of its consumed prefix afterwards. It did not perform a second full-file hash,
construct a book, request checkpoints or run the external implementation. Its twelve
focused controls check the bounded parser and source-counting behaviour. A small
independent retained-evidence audit is qualified separately; short raw spot checks do
not constitute a second independent full census.

## Source-informed comparison rule

The [source-bounded v3 contract](../../L3_TRANSITIONS_SOURCE_BOUNDED.md) explicitly uses
the preceding availability observation. It was frozen before reconstructing the new
requested books. This selection was not chosen before observing that source prefix;
it remains blind to book agreement and contains no quote or inventory filter.

Rule `first_x_u_four_windows_v3` keeps MSFT/5291 and QQQ/6556, authenticated directory
identities, and global system events `O`, `S`, then `Q`. For each symbol, take its first
post-Q `X` and first post-Q `U`. Each anchor and its next three same-symbol mutations
form a window. The mutation alphabet is exactly `A/F/E/C/X/D/U`; the seed is the latest
same-symbol mutation after Q and before the anchor, or global Q if none exists.

Both `bounds.search_duration_ns` and `deadline_ns` are explicitly null. The original
resource caps remain: 16,000,000 global frames, 536,870,912 parsed-prefix bytes,
100,000 captured selected post-Q headers, 4,096 census rows per window, twenty unique
checkpoints and 8 MiB selection artefacts. There is no fallback, later-anchor choice
or progressively extended clock deadline.

Requests are deduplicated only by symbol/global sequence, sorted in source order and
linked to all window roles. Equal timestamps retain source sequence. The census includes
all selected-locate messages within each seed-exclusive, tail-inclusive interval before
filtering to mutations. Empty sides and books remain explicit observations.

The current v3 selection produced twenty unique requests and twenty role memberships,
with sixteen census rows. Its source prefix ends at frame 8,300,042 and byte
284,563,784, SHA-256
`1a64008af2e7c9ec0bece0d99d63e0dc35c6e07a5dd1185a044e4b4a6d75a925`.
These are selection facts; successful enumeration alone did not establish book
agreement. The completed comparison is recorded separately below.

## Recorded v3 comparison

The coordinator passed all twenty unique complete states: 22,089 ordered row instances
and 6,840 level instances, with zero differences. All twenty role memberships are
distinct, with no overlap among these windows or with the earlier fifteen independent
states. The combined coverage is therefore **35 distinct selected state boundaries**,
not continuous validation between them. The row/level counts describe one exported
state set, not four new samples created by repeating the producers.

The independent delta audit found six unique `X/U` transitions: two partial
cancellations and four moved-price replacements. Both partial cancellations changed best-level displayed size; all four replacements
left BBO unchanged while changing deeper inventories. No complete-depletion `X` or same-price `U` was observed in this sample;
those real-data categories remain unverified here. All four replacement destination
levels were empty beforehand, so insertion behind an existing destination queue is
also only synthetically checked. Earlier synthetic controls remain
separate evidence and do not supply missing canonical observations.

Independent enumeration completed before either exporter. Both unchanged helpers'
second CSV/JSON exports matched their first exports exactly; complete manifests and
cross-implementation CSV bytes also matched. All eight recorded processes exited zero
with empty stderr, and all 119 protected identities stayed unchanged during the run.
Fresh full raw hashes before and after the comparison and the separate new-prefix
digest passed. The independent retained-evidence review also passes: it rehashes
176 small input identities, independently reconciles all twenty inventories and the
six copied X/U deltas, and preserves both rejected selections and the availability
study. This final review performs no additional raw reads, replay or tests. Its receipt
is bound in the [published aggregate](verification.json).

## Required comparison and semantics

A separately written enumerator must first recover the same anchors, seeds, contiguous
tails, role links, checkpoints, census and prefix digest. Only then may the unchanged
accepted local and pinned independent Release exporters run, twice each, against the
same requests. Require exact repeated CSV/JSON bytes and complete state manifests,
then use unchanged `compare_l3.py` for all displayed-order/FIFO, level and BBO fields.
An independent copied-state delta audit follows successful full-state comparison.
The focused v3 fixtures comprise 24 selector and 24 independent-audit methods; earlier
C++ builds and the rejected canonical selections do not need to be rerun.

`X` removes its stated quantity from the named order. Partial cancellation keeps the
remaining reference, price and relative FIFO; complete depletion removes it. `U`
removes the old reference and installs the stated **new total** displayed quantity and
price under its new reference, inheriting side and symbol. Check it once after the
complete wire message, without an invented delete/add midpoint.

Appending a replacement at its destination price level's tail is the pinned books'
reconstruction convention. Agreement does not prove actual exchange priority. The
common exports do not expose attribution or original priority timestamps. Classify
partial/full cancellations, same/moved replacement prices and BBO effects only after
comparison; none may select or replace a candidate.

V3 freshly checks the full raw identity before selection **and after comparison**, plus
the new prefix separately. This is stronger full-file rechecking than the availability
study's initial full hash and later prefix hash. Retain original source points, all
requested manifests, zero validation counters and source/reference/process identities.
The local helper validates all instruments in the prefix; the external wrapper validates
selected instruments while checking global framing/timestamps. Keep those scopes distinct.

## Reproduction and limits

The recorded v3 source context is clean main commit
`bcc33c7430c0f0fd7f99e3ee821745a0397905bf`. Reproduction requires the private sibling
harness, accepted retained binaries, fixed reference archive/headers and authenticated
canonical raw file. A public clone alone does not contain those private artefacts.

From the shared workspace, use a fresh ignored output directory. The coordinator checks
the specified clean main commit, the committed v3 contract and its immutable original
base. For a later documentation-only main commit, supply that clean HEAD only while all
pinned contract, helper and relevant implementation identities still match.

```sh
cd "/path/to/Quantitative finance"
python3 itch-feed-handler-tests/l3_transition_evidence_v3.py \
  --source-commit "$(git -C itch-feed-handler rev-parse HEAD)" \
  --output "$PWD/itch-feed-handler/out/l3-transition-reproduction-v3"
```

The accepted Release binaries are reused; no new compilation, sanitised historical
replay or compile-time dependency-equivalence claim follows. Current dependency-source
identities are recorded separately from the retained binary's accepted identity.

This gate compares only the unique states actually admitted and checked, counting
overlapping roles and overlap with the earlier fifteen states separately. It establishes
neither every-message full-day FIFO, attribution, actual priority, hidden liquidity,
eligibility, queue fills, live recovery nor strategy performance. The identified-history
and transport profiles remain restricted to `A/D/E`. Detailed source and order artefacts
stay ignored; publication contains bounded aggregate evidence.
