# Public evidence and private artefacts

This repository publishes source code, technical explanations and aggregate validation
results. Market data, detailed order inventories, per-event output, test harnesses and
machine-specific provenance remain private. This component now lives inside the
original matching-engine repository; its earlier separate publication is retained.

Some aggregate reports were originally recorded with absolute local paths. Their
publication copies replace the workspace/home directories with portable labels and
internal review identifiers with numbered review labels. Changed JSON reports carry
`_publication` metadata containing the original report's byte length and SHA-256.
The original reports and development history are retained privately.

Recorded input, executable, output and source identities describe the original
artefacts used in the experiments. A redacted JSON file has different bytes and a
different hash from its original report; do not use the original hash as a digest of
the publication copy. Portable path labels document provenance and are not executable
local paths. Old source commits identify the private development history; the public
feed-component publication began with this reviewed snapshot. Consolidation preserves
the original matching-engine repository history and nests that snapshot; it does not
make private historical source commits public ancestors. See [the integration note](INTEGRATION.md).

Publication does not rerun the experiments or widen their claims. BBO samples,
complete inventory samples, deterministic replay checks, timing observations and
model conventions retain their respective limits. In particular, repeated comparisons
add no independent historical states, matching fingerprints are not collision-proof
proofs, and zero hypothetical fills do not calibrate real execution probability.

The initial publication review checks that the verified implementation bytes are unchanged,
that changed reports preserve their non-location fields, and that the tracked tree
contains no raw data, detailed exports, private harness sources or credentials. The
complete local provenance and original report identities remain available for an
appropriately scoped review without placing those artefacts in this public repository.
