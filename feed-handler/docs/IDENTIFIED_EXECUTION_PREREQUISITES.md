# Prerequisites for a retained named execution

Gate 28 reviews existing evidence before extending the identified shadow model.
It executes no queue, reconstructs no book and calculates no hypothetical fills.
The [review record](validation/2026-10-23-identified-execution-prerequisites/README.md)
binds the retained inputs and independent reviews. The current one-U API and public
fictional example keep their existing scope.

## Select by source order, then assess suitability

Use the original two canonical identified histories: thirteen selected facts and
fifteen complete independently checked states. Select the earliest global source
ordinal whose type is E, without filtering on head position, quantity or a favourable
result. This fixes QQQ event 5, global sequence 7,349,884. The other retained E is MSFT
sequence 7,993,582; retain it as a counterexample, with no fallback reselection.

| Retained E | QQQ, selected | MSFT, catalogue only |
| --- | ---: | ---: |
| Locate |6556|5291|
| Source timestamp, ns |34,201,718,415,103|34,214,938,994,341|
| Framed byte interval, end exclusive |251,021,615–251,021,648|273,665,526–273,665,559|
| Resting side / resolved price |Buy / 213.5400|Buy / 158.9000|
| Executed shares in E |6|196|
| Named remaining shares before / after |500 / 494|265 / 69|
| Reconstructed per-price FIFO rank before |1|6|
| Displayed shares before that reference |0|221|
| Best-bid displayed shares before / after |600 / 594|934 / 738|

The complete retained independent PRE/POST inventories agree with the named reduction.
The QQQ peer at that price retains its 100 shares. No better bid is present at either
execution boundary. The QQQ ask remains 213.5500; the MSFT ask remains 158.9200.
These are reconstructed displayed facts. A non-head execution is preserved without
inventing a cause or distributing its shares across earlier references.

Nasdaq's [ITCH specification, section 1.4.1](https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHspecification.pdf#page=14)
defines E as a named whole or partial execution, with reference, executed shares and
match number. E carries no explicit price or printable flag. The resting price above
is resolved from inventory. Its fields do not identify an incoming parent order or
its total demand. Inferring our own fill from those fields would add a model assumption.

## Preserve the original seed and the intervening history

Use QQQ's original whole-timestamp seed, rather than relabelling the preceding selected
event as an adjacent raw source. The proposed prefix is:

| Boundary | Source sequence | Timestamp, ns | End byte |
| --- | ---: | ---: | ---: |
| Original seed, D |7,343,112|34,201,694,396,241|250,772,235|
| Immediate next global frame, foreign A |7,343,113|34,201,694,403,283|250,772,273|
| Selected A immediately before E in selected order |7,349,506|34,201,716,865,462|251,007,945|
| Selected E and proposed inclusive end |7,349,884|34,201,718,415,103|251,021,648|
| Next selected D, outside that end |7,350,337|34,201,720,017,517|251,038,717|

The five selected facts from the original seed are **A,D,A,A,E**, with six retained
complete inventories. They include ask additions, deletion of an 800-share bid and
an addition below the best bid. Those changes must survive any future handoff.
The original QQQ suffix D/A remains excluded from this proposed E endpoint.
Across all six inventories, bid 213.5400 and ask 213.5500 stay strictly uncrossed and
unchanged. Bid quantity changes 1,400→600→594; ask quantity changes 300→500→600.
The deep bid addition contributes 35 at 213.5300 and must remain in the complete book,
even though it changes neither best quote.

There are 377 global frames between the previous selected A and E. They are absent
from the selected list because they concern other locates or global context, not
because the bytes are adjacent or the exchange was silent. The existing one-U API
requires U and global adjacency; it remains incompatible with this candidate.

The original producer and independent enumerator scanned all selected-locate messages
before filtering, through the later original window end. No further selected message
has E's timestamp. This establishes **selected-book timestamp closure** for the proposed
prefix. The exact last global source at E's timestamp and its first-greater global
witness were not materialised. The original window's later witness cannot be moved
backwards or renamed as E's witness. A future contract must state explicitly whether
selected-book closure is sufficient; this review grants no own-action admission.

## Reuse status facts at their actual scope

Gate 9's history and Gate 25's later QQQ status audit retain the same canonical identity:
8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
This review checks retained small-file identities. It performs no fresh raw-file
operation and does not upgrade any pure-module authentication flag.

Gate 25's complete through-endpoint census contains exactly one selected QQQ R, H and Q.
Their source origins 6,571/21,992/7,203,970 all precede the original QQQ seed. The directory
is production QQQ/6556; H is T and the cross is O. There are no additional selected H/Q
before its later endpoint, so those limited facts also hold over the earlier E prefix.
Global S has exactly the original O/S/Q events, all before the seed; global W/h/N and
selected K are zero through that endpoint. This supports inherited restricted status
facts when an explicit new admission contract binds the shared identity and census.
It is offline evidence about history, not later information delivered to a strategy.

Absent h/N announcements remain unknown. The later one-U interval census, global
adjacency, 211 ns witness and queue-admission result do not transfer. QQQ-specific H,
cross and IPO context do not establish MSFT status. None proves complete venue access,
regulatory eligibility, routing availability or actual order acceptance.

## Admission and refusal matrix

| Requested claim or use | Decision from this review |
| --- | --- |
| The two named external E reductions and retained complete inventories | Supported by inherited, independently checked structural evidence |
| QQQ original seed and first five selected facts | Fixed candidate for the next design; preserve every deep change |
| No additional selected event at E's clock | Supported by retained complete selected enumeration |
| Limited QQQ production/H/cross/global-status facts over that prefix | Transferable only through an explicit shared-identity and census join |
| Exact global adjacency or exact global endpoint witness at E | Not established; refuse fabricated identities |
| Pass E to the unchanged one-U overlay | Refuse the unsupported event/profile |
| Treat E shares as anonymous demand or a fill for our marker | Refuse; named reduction alone does not establish that counterfactual |
| Redistribute MSFT's 196 shares over 221 earlier shares | Refuse; preserve its named rank-six reduction |
| Infer normal h/N states from absent messages | Refuse; retain unknown knowledge |
| Apply QQQ status to MSFT, or import the later one-U admission | Refuse the scope change |
| Change input/frame/inventory identities, omit a selected fact or extend the horizon | Refuse; no fallback to another candidate |
| Run a new own-order experiment now | Design pending; no new queue or fill-model acceptance |

Gate 29 should freeze and independently audit a **five-fact causal profile**, using
the original seed, complete inventories, selected closure and explicit inherited
status admission. Define all supported external mutations, own-state separation,
delivered knowledge, finite clocks and pending events before implementation. Preserve
named execution semantics; make no empirical fill claim. If a required global-boundary
identity is genuinely missing under that chosen contract, record the exact missing
proof and propose a finite remedy. Do not launch another raw scan to manufacture an
unnecessary adjacency requirement or add a general simulator for this small question.
