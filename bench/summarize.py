#!/usr/bin/env python3
"""Summarise bench/run.sh output into Markdown tables.

For every (regime, book) it reports the median over launches of throughput and of each
latency percentile, the min-max range of throughput, and flags NOISY rows whose range
exceeds 10% of the median. It also checks that every variant produced the same event
hash on a given regime, which is the evidence that the variants behave identically.
The complete five-book, five-regime matrix must use one seed, operation count and
capacity, with an equal number of launches for every operation row. Pass
--launches to verify the count declared by the producer.
Zero-operation runs report zero throughput. Invalid throughput values are rejected.
"""

import argparse
import csv
import math
import statistics
import sys
from collections import Counter, defaultdict
from itertools import product

NOISE_LIMIT = 0.10
OPS = ["limit", "market", "modify", "cancel"]
BOOKS = ("v1", "map", "map-oa", "vec", "ladder")
REGIMES = ("fixed-mid", "random-walk", "deep-book", "flash-crash", "cancel-heavy")


def validate_matrix(rows, expected_launches):
    if not rows:
        raise ValueError("no benchmark rows")
    if expected_launches is not None and expected_launches < 1:
        raise ValueError("expected launches must be positive")
    settings = {(r["seed"], r["ops"], r["max_orders"]) for r in rows}
    if len(settings) != 1:
        raise ValueError("mixed seed, operation-count or capacity settings")
    counts = Counter((r["regime"], r["book"], r["op"]) for r in rows)
    expected = set(product(REGIMES, BOOKS, ["all", *OPS]))
    if set(counts) != expected:
        raise ValueError("incomplete or unexpected regime/book/operation matrix")
    launches = set(counts.values())
    if len(launches) != 1:
        raise ValueError("uneven launch counts across the benchmark matrix")
    if expected_launches is not None and launches != {expected_launches}:
        raise ValueError(f"expected {expected_launches} launches per matrix entry, got {min(launches)}")


def main(path: str, expected_launches=None) -> int:
    mops = defaultdict(list)
    try:
        with open(path, newline="") as f:
            rows = list(csv.DictReader(f))
        validate_matrix(rows, expected_launches)
        for row in rows:
            if row["op"] == "all":
                rate = float(row["mops"])
                if not math.isfinite(rate) or rate < 0:
                    raise ValueError("throughput must be finite and nonnegative")
                mops[(row["regime"], row["book"])].append(rate)
    except (OSError, KeyError, TypeError, ValueError) as error:
        print(f"Invalid benchmark CSV: {error}", file=sys.stderr)
        return 2

    regimes = list(dict.fromkeys(r["regime"] for r in rows))
    books = list(dict.fromkeys(r["book"] for r in rows))
    lat = defaultdict(list)
    hashes = defaultdict(set)
    peak = {}
    for r in rows:
        key = (r["regime"], r["book"])
        hashes[r["regime"]].add(r["hash"])
        peak[r["regime"]] = r["peak_orders"]
        for q in ("p50", "p90", "p99", "p999"):
            lat[key + (r["op"], q)].append(int(r[q]))

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
    args = parser.parse_args()
    sys.exit(main(args.path, args.launches))
