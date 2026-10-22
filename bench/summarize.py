#!/usr/bin/env python3
"""Summarise bench/run.sh output into Markdown tables.

For every (regime, book) it reports the median over launches of throughput and of each
latency percentile, the min-max range of throughput, and flags NOISY rows whose range
exceeds 10% of the median. It also checks that every variant produced the same event
hash on a given regime, which is the evidence that the variants behave identically.
"""

import csv
import statistics
import sys
from collections import defaultdict

NOISE_LIMIT = 0.10
OPS = ["limit", "market", "modify", "cancel"]


def main(path: str) -> int:
    with open(path, newline="") as f:
        rows = list(csv.DictReader(f))

    regimes = list(dict.fromkeys(r["regime"] for r in rows))
    books = list(dict.fromkeys(r["book"] for r in rows))
    mops = defaultdict(list)
    lat = defaultdict(list)
    hashes = defaultdict(set)
    peak = {}
    for r in rows:
        key = (r["regime"], r["book"])
        hashes[r["regime"]].add(r["hash"])
        peak[r["regime"]] = r["peak_orders"]
        if r["op"] == "all":
            mops[key].append(float(r["mops"]))
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
            spread = (max(m) - min(m)) / centre
            flag = " NOISY" if spread > NOISE_LIMIT else ""
            cells = [f"{centre:.1f} ({min(m):.1f}-{max(m):.1f}){flag}",
                     str(med(key + ("all", "p50"))), str(med(key + ("all", "p99"))),
                     str(med(key + ("all", "p999")))]
            cells += [str(med(key + (op, "p99"))) for op in OPS]
            print(f"| {book} | " + " | ".join(cells) + " |")
        print()
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
