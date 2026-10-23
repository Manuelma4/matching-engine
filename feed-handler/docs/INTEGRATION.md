# One repository, two market-system components

The original `Manuelma4/matching-engine` repository contains the matching engine at
its root and the offline replica under `feed-handler/`. The engine's history and
layout are preserved. The earlier separate feed-handler repository remains intact;
this consolidation copies its reviewed public snapshot at `6d2e38809aee4a38b5bfb614d75e7e96f71fcf17`.
No market data, detailed inventories, private tests, ignored outputs or private Git
history are copied. Each component retains its MIT licence.

## Current builds and examples

Run the combined build commands in the [root README](../../README.md#build-the-feed-handler-in-this-repository).
`ME_BUILD_FEED_HANDLER=ON` adds the component after the root `me` and `me_workloads`
targets; the component reuses both. A partial target pair is rejected. With the option
off, the original engine-only build remains available. Standalone component builds
still accept a local parent checkout or the unchanged pinned FetchContent dependency.

The current C++ tools and data-free Python examples use this layout. Raw data and
per-event output belong in ignored component `data/` and `out/` directories. Private
harnesses and build/check receipts remain outside the public source tree.

## Historical experiments retain their original context

The copied aggregate reports document experiments run before consolidation. Their
source commits, executable hashes, original input/output hashes and portable path
labels retain their original meanings. They are not hashes of newly built binaries
or evidence that consolidation repeated the experiment. No new independently checked
historical state is added: the retained displayed-depth/FIFO scope is 37 distinct states.

Some historical measurement and authenticated-source producers deliberately pin old
Git commits, private artefacts and sibling-checkout paths, including the level-search
runner. Those protocols require their recorded original context; they are not current
one-command reproductions from this nested directory. Older documentation commands
using `../matching-engine` describe that sibling layout. For a new standalone build
here, the engine is the parent directory instead. Keep the original checkout and
private evidence when auditing those historical records.

The [later-session contract](LATER_SESSION_L3.md) is prospective: noon and 15:30 for
MSFT/QQQ are planned source cuts, not four validated new states. Private synthetic
selection checks cannot replace canonical source authentication and complete book
comparison. No queue, session-status or fill admission follows from this migration.

## Verified migration checks

[The consolidation record](validation/2026-10-23-consolidation/README.md) reports the
Release/ASan/UBSan integration groups, explicit skipped cases, standalone/engine-only
builds and expected partial-dependency refusals. The current data-free example also
passes in this layout. These checks exercise the new CMake integration and imported
code; they do not repeat the historical market-data experiments.
