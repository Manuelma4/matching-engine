# Consolidation verification, 23 October 2026

The original matching-engine repository now builds its feed replica as an optional
component. The engine and feed production C++ files retain their previously published
bytes; only their two CMake entry points change dependency integration. The separate
feed publication and original private evidence remain intact.

The [aggregate result](result.json) records 11 passing CTest groups in each of Release
and ASan/UBSan builds: 299 C++ methods pass, three standard-index-only methods skip
under the selected open-addressed index, and 65 explicit-tool CLI methods pass. These
are the same test cases in two build modes, not independent historical samples.
The engine/feed loopback matches 10,000 touch comparisons and all final resting orders
across 5,000 generated operations in five symbols, with no replica anomalies.

Engine-only and standalone component builds pass. Both incomplete engine target pairs
are rejected with the expected diagnostic. The relocated delayed-seed Python example
also runs without market data. Leak detection is disabled on this macOS sanitizer
run; AddressSanitizer and UndefinedBehaviorSanitizer remain enabled. Recorded framework/
configuration warnings and a reconciled parent-reporting error are retained explicitly.

See [current commands and historical provenance](../../INTEGRATION.md) and the
[root build instructions](../../../../README.md#build-the-feed-handler-in-this-repository).
The private harness, command logs, binary identities and original failed reporting
checks remain outside the public tree. Consolidation performs no canonical replay,
market-data hash pass or timing experiment, and adds zero historical states.
