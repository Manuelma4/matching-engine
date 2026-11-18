#!/usr/bin/env python3
"""Summarise bench/run.sh output into Markdown tables.

For every (regime, book) it reports the median over launches of throughput and of each
latency percentile, the min-max range of throughput, and flags NOISY rows whose range
exceeds 10% of the median. It checks that each recorded event fingerprint is a
16-digit hexadecimal value and compares the fingerprints within each regime.
The complete five-book, five-regime matrix must use one seed, operation count and
capacity, with an equal number of launches for every operation row. Pass
--launches to verify the count declared by the producer.
Zero-operation runs report zero throughput. Throughput must be finite and nonnegative.
Aggregate latency samples must match the workload size. Sample counts agree
for each regime and operation across deterministic launches, and the per-type
counts sum to the workload size. Latency percentiles must be nonnegative
integers in percentile order and at most the recorded maximum. The latency
statistics must be zero for empty sample sets. Each operation's maxima must fit
within the available aggregate maxima across launches in any row order. The peak
resting order count must be nonnegative, fit the configured capacity and workload
size, and agree across each regime.
"""

import argparse
import csv
import io
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

NOISE_LIMIT = 0.10
OPS = ["limit", "market", "modify", "cancel"]
BOOKS = ("v1", "map", "map-oa", "vec", "ladder")
REGIMES = ("fixed-mid", "random-walk", "deep-book", "flash-crash", "cancel-heavy")


def validate_matrix(rows, expected_launches, books=BOOKS):
    if not rows:
        raise ValueError("no benchmark rows")
    if expected_launches is not None and expected_launches < 1:
        raise ValueError("expected launches must be positive")
    settings = {(r["seed"], r["ops"], r["max_orders"]) for r in rows}
    if len(settings) != 1:
        raise ValueError("mixed seed, operation-count or capacity settings")
    for field, minimum, maximum in (
        ("seed", 0, (1 << 64) - 1), ("ops", 0, (1 << 64) - 1),
        ("max_orders", 1, (1 << 32) - 2),
    ):
        value = rows[0][field]
        if re.fullmatch(r"[0-9]+", value) is None or not minimum <= int(value) <= maximum:
            raise ValueError(f"invalid benchmark setting {field}")
    counts = Counter((r["regime"], r["book"], r["op"]) for r in rows)
    expected = set(product(REGIMES, books, ["all", *OPS]))
    if set(counts) != expected:
        raise ValueError("incomplete or unexpected regime/book/operation matrix")
    launches = set(counts.values())
    if len(launches) != 1:
        raise ValueError("uneven launch counts across the benchmark matrix")
    if expected_launches is not None and launches != {expected_launches}:
        raise ValueError(f"expected {expected_launches} launches per matrix entry, got {min(launches)}")


def read_rows(reader):
    fields = reader.fieldnames or []
    if len(fields) != len(set(fields)):
        raise ValueError("duplicate benchmark column names")
    rows = list(reader)
    if any(None in row or None in row.values() for row in rows):
        raise ValueError("benchmark row width does not match the header")
    return rows


def append_captures(path, capture_index):
    with open(capture_index, encoding="utf-8") as index, open(path, "a+", newline="") as raw:
        raw.seek(0)
        header = raw.readline()
        if not header.endswith("\n") or raw.read(1):
            raise ValueError("staged benchmark CSV must contain only its header")
        fields = next(csv.reader([header], strict=True))
        for line in index:
            filename, book = line.rstrip("\n").split("\t")
            try:
                capture = Path(capture_index).parent / filename
                with capture.open(newline="") as sample:
                    body = sample.read()
                reader = csv.DictReader(io.StringIO(body, newline=""), fieldnames=fields, strict=True)
                rows = read_rows(reader)
                validate_matrix(rows, expected_launches=1, books=(book,))
                for regime in REGIMES:
                    maxima = {row["op"]: int(row["max"]) for row in rows if row["regime"] == regime}
                    if maxima["all"] != max(maxima[op] for op in OPS):
                        raise ValueError(f"capture latency maxima disagree for {regime}")
                if not body.endswith("\n"):
                    raise ValueError("capture must end with a newline")
            except (OSError, KeyError, ValueError, csv.Error) as error:
                raise ValueError(f"Invalid capture {filename} for {book}: {error}") from error
            raw.write(body)


def main(path: str, expected_launches=None, capture_index=None, expected_ops=None, expected_seed=None) -> int:
    mops = defaultdict(list)
    lat = defaultdict(list)
    sample_counts = defaultdict(dict)
    maxima = defaultdict(lambda: defaultdict(list))
    hashes = defaultdict(set)
    peak = {}
    percentiles = ("p50", "p90", "p99", "p999")
    try:
        if capture_index is not None:
            append_captures(path, capture_index)
        with open(path, newline="") as f:
            rows = read_rows(csv.DictReader(f, strict=True))
        validate_matrix(rows, expected_launches)
        for field, requested in (("ops", expected_ops), ("seed", expected_seed)):
            if requested is not None and int(rows[0][field]) != requested:
                raise ValueError(f"CSV {field} does not match requested {requested}")
        operations = int(rows[0]["ops"])
        for row in rows:
            regime, book, operation = row["regime"], row["book"], row["op"]
            samples = int(row["count"])
            if not 0 <= samples <= operations or (operation == "all" and samples != operations):
                raise ValueError(f"invalid latency sample count for {regime}/{book}/{operation}")
            if sample_counts[regime].setdefault(operation, samples) != samples:
                raise ValueError(f"latency sample counts disagree for {regime}/{operation}")
            if operation == "all":
                rate = float(row["mops"])
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError("throughput must be finite and nonnegative")
                if operations == 0 and rate != 0:
                    raise ValueError(f"nonzero throughput for zero operations in {regime}/{book}")
                mops[(regime, book)].append(rate)
            values = [int(row[percentile]) for percentile in percentiles]
            if values[0] < 0 or values != sorted(values):
                raise ValueError("latency percentiles must be nonnegative and nondecreasing")
            maximum = int(row["max"])
            if maximum < values[-1]:
                raise ValueError(f"latency maximum is below p99.9 for {regime}/{book}/{operation}")
            if samples == 0 and (maximum or any(values)):
                raise ValueError(f"nonzero latency statistics for zero latency samples in {regime}/{book}/{operation}")
            if samples == 1 and values[0] != maximum:
                raise ValueError(f"percentiles and maximum must match for one latency sample in {regime}/{book}/{operation}")
            maxima[regime, book][operation].append(maximum)
            for percentile, value in zip(percentiles, values):
                lat[(regime, book, operation, percentile)].append(value)
            fingerprint = row["hash"]
            if not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-fA-F]{16}", fingerprint) is None:
                raise ValueError("event fingerprint must contain 16 hexadecimal digits")
            hashes[regime].add(fingerprint.lower())
            orders = int(row["peak_orders"])
            if orders < 0:
                raise ValueError("peak resting orders must be nonnegative")
            if orders > min(int(row["max_orders"]), operations):
                raise ValueError("peak resting orders exceed capacity or workload size")
            if peak.setdefault(regime, orders) != orders:
                raise ValueError(f"peak resting orders disagree for regime {regime}")
        for regime, counts in sample_counts.items():
            if sum(counts[op] for op in OPS) != operations:
                raise ValueError(f"operation sample counts do not sum to the workload size for {regime}")
        for (regime, book), group_maxima in maxima.items():
            aggregate = sorted(group_maxima["all"])
            if aggregate[-1] != max(max(group_maxima[op]) for op in OPS):
                raise ValueError(f"aggregate and per-operation latency maxima disagree for {regime}/{book}")
            for op in OPS:
                # Archived CSVs lack launch IDs. The sorted maxima must fit
                # even under the most favorable pairing for each operation.
                operation_maxima = sorted(group_maxima[op])
                if any(value > limit for value, limit in zip(operation_maxima, aggregate)):
                    raise ValueError(
                        f"operation latency maxima exceed available aggregate maxima for {regime}/{book}/{op}"
                    )
    except (OSError, KeyError, TypeError, ValueError, csv.Error) as error:
        print(f"Invalid benchmark CSV: {error}", file=sys.stderr)
        return 2

    regimes = list(dict.fromkeys(r["regime"] for r in rows))
    books = list(dict.fromkeys(r["book"] for r in rows))
    launches = len(mops[(regimes[0], books[0])])
    mismatched = [g for g in regimes if len(hashes[g]) != 1]
    print(f"Launches per variant: {launches}. Latency in ns, median over launches; "
          "values are multiples of the 41.67 ns timer tick.\n")
    print("Output hashes: " + ("MISMATCH in " + ", ".join(mismatched) if mismatched
                               else "identical across all variants on every regime") + "\n")

    def med(key):
        return round(statistics.median(lat[key]))

    for regime in regimes:
        print(f"### {regime}\n")
        print(f"Peak resting orders: {peak[regime]}. Hash: `{' / '.join(sorted(hashes[regime]))}`\n")
        print("| Book | M ops/s (median, range) | all p50 | all p99 | all p99.9 | "
              + " | ".join(f"{op} p99" for op in OPS) + " |")
        print("|---|---|---:|---:|---:|" + "---:|" * len(OPS))
        for book in books:
            key = (regime, book)
            m = mops[key]
            centre = statistics.median(m)
            low, high = min(m), max(m)
            flag = " NOISY" if high - low > NOISE_LIMIT * centre else ""
            cells = [f"{centre:.1f} ({low:.1f}-{high:.1f}){flag}",
                     str(med(key + ("all", "p50"))), str(med(key + ("all", "p99"))),
                     str(med(key + ("all", "p999")))]
            cells += [str(med(key + (op, "p99"))) for op in OPS]
            print(f"| {book} | " + " | ".join(cells) + " |")
        print()
    return 1 if mismatched else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path")
    parser.add_argument("--launches", type=int, help="expected launches from bench/run.sh")
    parser.add_argument("--capture-index", help="runner index of individual captures to append to the staged CSV")
    parser.add_argument("--expected-ops", type=int, help="operation count requested from the executable")
    parser.add_argument("--expected-seed", type=int, help="seed requested from the executable")
    args = parser.parse_args()
    sys.exit(main(args.path, args.launches, args.capture_index, args.expected_ops, args.expected_seed))
