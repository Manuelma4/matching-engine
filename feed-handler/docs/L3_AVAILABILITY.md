# Bounded source availability study

The one-second and separate ten-second transition experiments both ended without a
post-open MSFT `X`. Their failures remain evidence; neither produced successful
checkpoints, book exports or newly validated states. Before designing another
comparison, measure source-message availability under the existing resource budget.
This is a separate read-only discovery study, frozen before its new source scan.

## Fixed input, symbols and stopping rule

Use only `data/12302019.NASDAQ_ITCH50.itch`, 8,251,407,909 bytes, SHA-256
`5d81c2e14a0f748b29c674b6a342796932702034b4dd341e39e9a9ec5bac610f`.
Authenticate MSFT/locate 5291 and QQQ/locate 6556 from original directory messages.
Start at byte zero and count every nonempty global BinaryFILE frame from one.
Offsets include two-byte lengths and end offsets are exclusive. Check every known
type's exact ITCH 5.0 body length and globally non-decreasing 48-bit timestamps.
Authenticate global `S(O)`, `S(S)`, `S(Q)` in order, with both directories before Q.

Scan **all complete frames** until the first of 16,000,000 global frames or
536,870,912 parsed-prefix bytes is reached. Do not include a frame that would
straddle the byte limit. A length prefix inspected to establish a straddling next
frame is outside the consumed-prefix digest; report that distinction. Do not apply
a time cutoff or stop when a target occurrence is found. Missing target events are
valid availability results, rather than a reason to expand either resource cap.
An earlier ordinary EOF may be recorded as such; malformed/truncated framing, an
unexpected end record, directory conflict or timestamp regression fails the study.

## Output and interpretation

For each fixed symbol, count `A/F/E/C/X/D/U` separately before Q and after Q. The Q
frame itself is not a mutation. Record the first and last post-Q `X` and `U` with
their exact source points and frame SHA-256, or explicit null when absent. Count
all selected-locate post-Q headers before filtering by mutation type. Retain Q's
original source point and the last included frame's point so the observed source
span is explicit. Integer counts do not imply a uniform event rate.

The study emits no checkpoint request, reconstructed state, book export or candidate
ranking. It imports no book/selector implementation and runs no external book.
Do not describe an observed wire event as independently validated L3 state. A future
comparison must declare its source-based selection separately, acknowledge these
prior availability observations, and still retain discrepancies without substitution.
It must satisfy the original complete-inventory and independent-reference gates.

## Verification and retention

Keep the original and ten-second selector/auditor/coordinator sources and fixtures
unchanged. Use a new private sibling Python utility and a small literal fixture suite.
Review sources and the committed contract before first execution. Fixtures must
check exact cap boundaries, no early target-triggered stop, null absent events,
pre/post-Q separation, unfiltered headers, original source offsets and malformed
global input. Run only the new focused tests; old C++ builds need no rerun.

Open a stable regular canonical file, freshly verify its full size/SHA before walking,
and hash the consumed prefix while parsing. Independently rehash that same prefix
after the walk. Check descriptor/named-file metadata throughout and source/contract
bytes before and after publication. This establishes a freshly checked initial full
identity and a freshly rechecked prefix; it does not claim a second full-file hash.
Retain small source snapshots and checked, bounded JSON output in a fresh ignored
directory. Publish aggregate counts, source/input identities, cap/stop scope and honest
limitations; keep detailed occurrence data local. Preserve both previous negative
experiments. Queue/fill, attribution, actual priority, performance and every-event
book correctness remain outside this source-only study.
