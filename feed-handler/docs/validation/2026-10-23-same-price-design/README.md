# Same-price replacement: reviewed bounded design

The reviewed question is whether a real same-price U moves a non-tail order behind
an already resting peer under the pinned reconstruction convention. This design
executes no classifier or book, reads no raw market data and adds no validated state.
The [contract](../../L3_SAME_PRICE_REPLACEMENT.md) and [design aggregate](design.json)
bind three independent approvals, source/helper identities, retained metadata and
the two corrections found during review.

The existing 35 independent states include four moved-price replacements into empty
destinations, with no canonical same-price/non-tail case. The retained availability
study counts U messages but lacks old-price/peer facts. It establishes neither
presence nor absence of the proposed predicate.

## Fixed future stages

First freeze literal controls and implement a separate limited source-derived
classifier and independent enumerator. On the fixed Nasdaq input and MSFT/QQQ,
scan from byte zero through the original 16-million-frame/512-MiB cap, regardless of
candidate discovery. A 300–480-second post-Q interval filters eligibility; it never
stops or widens the scan. The known cap ends at Q+468.771899246 seconds. A later
null must therefore state its scanned-prefix scope and right-censoring.

The classifier uses named quantities, prices, fresh A/F/U birth ordinals and level
membership, without UUT/reference imports or complete expected inventories. Freeze
the first same-price U per symbol whose old order has a later-born same-level peer.
Count all qualifiers to the fixed stop. A separately written enumerator must agree
before candidate/request identities are frozen. Nulls, errors and rejected output
remain evidence; there is no alternate symbol, category, deadline or agreement filter.

Only then may a separate comparison gate run the unchanged local/reference helpers
twice each. At most two anchors give four complete post-message boundaries: global
anchor-1 and anchor. Compare every order/rank/quantity and a whole copied-prestate
delta, preserving global ties and foreign-symbol predecessors. These are conditional
maximum counts, not completed executions or new samples.

## Corrections retained from review

- The core/reference API can reuse an old reference, but the unchanged local export
  wrapper rejects it. The classifier must reject selected same-reference U as invalid
  input, and retain any later foreign-prefix rejection without reselection.
- The unchanged comparator requires at least one same state with both sides present,
  deeper levels and a multiorder FIFO. The source predicate alone does not guarantee
  this coverage. Even equal exports can fail admission; retain that result without
  weakening the comparator or choosing another event.

The original and intermediate reviewed drafts and superseded approvals remain
private; all three final approvals bind the same 12,957-byte contract, SHA-256
`2ea30d761ccf051b3828ef8da60d063af38d7760903ffb358e12d24bdde3a661`.
All 44 feed and 15 engine implementation identities remain unchanged. The negative
[level-search result](../2026-10-23-level-search/README.md) and reverse-linear default
remain intact. This review adds no performance, actual exchange priority, hidden
liquidity, late-session, queue eligibility or fill claim.
