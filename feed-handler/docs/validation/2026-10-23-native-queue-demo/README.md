# Native C++ queue teaching example

The [self-contained example](../../QUEUE_DEMO.md) calls the existing C++20 aggregate
queue kernel on one fictional four-event path. It adds a runnable API example and
build target; queue rules, ITCH reconstruction and historical admission stay unchanged.

## Verification

Three configurations were hand-derived and frozen before the first execution:
optimistic/horizon45, conservative/horizon45 and optimistic/horizon44. The hand oracle
was prepared independently from the existing native header and implementation.

Fresh builds from the consolidated matching-engine root pass in Release and Debug
with AddressSanitizer/UndefinedBehaviorSanitizer. Both the queue kernel and demo
compile as C++20; compile/link metadata confirms sanitiser coverage and linkage only
to the existing queue library. Apple clang 21.0.0 on macOS/arm64 was used, with the
SDK and C++ include directory set explicitly. No build or run emits a warning or
sanitiser diagnostic. macOS leak detection is disabled; no leak-check claim follows.

Each build runs twice. All four stdout files are byte-identical (3,494 bytes each),
with successful exits and empty stderr. Every printed trace row matches its frozen
hand expectation: 12/11/11 rows across the three configurations, or 34 per executable
run. These are 136 row instances across repeats, not 136 independent scenarios.

The private checker compares the twelve printed trace fields, configurations, four
source rows, final states/remainders/pending counts, complete printed accounts and
marks. The native trace has other fields which this compact demo does not print;
those unprinted fields are not claimed as compared here. Three isolated altered
output copies are rejected: an early local fill, double depletion of external shares
and an engaged zero mark misreported as missing. These are checker controls, not
mutations of the native kernel.

## Outcomes and limits

Optimistic cancellation fills ten shares; conservative cancellation leaves ten
shares ahead and the entire shadow order live. External quantity ends at ten in both
cases. At horizon44, the optimistic exchange is filled but local state remains live:
the fill response at45 is pending. Local marked equity in twice-Price(4) units is
100/0/0 across the three cases. The nonzero mark is unrealised and has no liquidation
or empirical-profit interpretation.

[The aggregate](result.json) retains source, binary, oracle, output and private
evidence identities. Private expectations, checks, compiler/command logs and per-event
output stay outside this repository. The example source and public build instructions
are sufficient to run its fictional scenarios without those private artefacts.

Historical independent displayed L3/FIFO coverage remains **41 states**, with zero
new historical states. No market data, external reference book or historical replay
runs in this increment. This is no performance, measured-network-latency,
actual-priority, session-status or historical-fill calibration result.
