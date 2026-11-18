"""Validate benchmark evidence with tiny synthetic CSVs, without running a benchmark."""
import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from summarize import main

BOOKS = ("v1", "map", "map-oa", "vec", "ladder")
REGIMES = ("fixed-mid", "random-walk", "deep-book", "flash-crash", "cancel-heavy")
OPS = ("all", "limit", "market", "modify", "cancel")


def fixture():
    return [{"book": book, "regime": regime, "seed": "42", "ops": "100", "hash": "a" * 16,
             "peak_orders": "10", "max_orders": "1000", "mops": "1", "op": op,
             "count": "100" if op == "all" else "25",
             "p50": "42", "p90": "42", "p99": "42", "p999": "42", "max": "84"}
            for book in BOOKS for regime in REGIMES for op in OPS]


class SummaryEvidenceTests(unittest.TestCase):
    def run_summary(self, rows, launches=None):
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fixture()[0].keys())
        writer.writeheader()
        writer.writerows(rows)
        return self.run_raw_summary(stream.getvalue(), launches)

    def run_raw_summary(self, body, launches=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.csv"
            path.write_text(body, newline="")
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = main(str(path), launches)
            return result, output.getvalue()

    def test_complete_matrix_is_accepted(self):
        result, output = self.run_summary(fixture())
        self.assertEqual(result, 0)
        self.assertIn("identical across all variants", output)

    def test_ambiguous_csv_structure_is_rejected(self):
        fields = list(fixture()[0])
        original = [[row[field] for field in fields] for row in fixture()]
        for case in ("extra-cell", "duplicate-header", "missing-cell", "malformed-quote"):
            with self.subTest(case=case):
                header = fields.copy()
                rows = [row.copy() for row in original]
                if case == "extra-cell":
                    rows[0].append("ignored")
                elif case == "duplicate-header":
                    header.append("ops")
                    for row in rows:
                        row.append(row[fields.index("ops")])
                elif case == "missing-cell":
                    header.append("note")
                    for row in rows[1:]:
                        row.append("")
                stream = io.StringIO(newline="")
                writer = csv.writer(stream)
                writer.writerow(header)
                if case == "malformed-quote":
                    # A trailing character after a closed quoted field is invalid.
                    first, *rest = rows[0]
                    stream.write(f'"{first[:-1]}"{first[-1]},{",".join(rest)}\r\n')
                    writer.writerows(rows[1:])
                else:
                    writer.writerows(rows)
                result, output = self.run_raw_summary(stream.getvalue())
                self.assertEqual(result, 2, output)
                self.assertIn("Invalid benchmark CSV", output)
                self.assertNotIn("Output hashes", output)

    def test_impossible_numeric_settings_are_rejected(self):
        for field, value in (
            ("seed", "-1"), ("seed", "invalid"), ("seed", str(1 << 64)),
            ("ops", "1.0"), ("ops", str(1 << 64)),
            ("max_orders", "0"), ("max_orders", "-1"), ("max_orders", str((1 << 32) - 1)),
        ):
            with self.subTest(field=field, value=value):
                rows = fixture()
                for row in rows:
                    row[field] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2, output)
                self.assertIn("invalid benchmark setting", output)
                self.assertNotIn("Output hashes", output)

    def test_supported_numeric_setting_boundaries_are_accepted(self):
        for seed, capacity in (("0", "1"), (str((1 << 64) - 1), str((1 << 32) - 2))):
            rows = fixture()
            for row in rows:
                row.update(seed=seed, max_orders=capacity, peak_orders="0")
            result, output = self.run_summary(rows)
            self.assertEqual(result, 0, output)

    def test_missing_variant_is_rejected(self):
        result, output = self.run_summary([r for r in fixture() if r["book"] != "ladder"])
        self.assertNotEqual(result, 0)
        self.assertNotIn("identical across all variants", output)

    def test_missing_regime_is_rejected(self):
        result, _ = self.run_summary([r for r in fixture() if r["regime"] != "cancel-heavy"])
        self.assertNotEqual(result, 0)

    def test_uneven_launches_are_rejected(self):
        rows = fixture()
        rows.extend(dict(row) for row in fixture() if row["book"] == "v1")
        result, _ = self.run_summary(rows)
        self.assertNotEqual(result, 0)

    def test_mixed_workloads_are_rejected(self):
        for field in ("seed", "ops", "max_orders"):
            with self.subTest(field=field):
                rows = fixture()
                rows[0][field] = "999"
                result, _ = self.run_summary(rows)
                self.assertNotEqual(result, 0)

    def test_missing_operation_is_rejected(self):
        result, _ = self.run_summary([r for r in fixture() if r["op"] != "market"])
        self.assertNotEqual(result, 0)

    def test_mismatched_hashes_are_rejected(self):
        rows = fixture()
        rows[0]["hash"] = "b" * 16
        result, output = self.run_summary(rows)
        self.assertNotEqual(result, 0)
        self.assertIn("MISMATCH", output)

    def test_equal_invalid_event_hashes_are_rejected_before_reporting(self):
        for value in ("", "a", "z" * 16, "a" * 17):
            with self.subTest(value=value):
                rows = fixture()
                for row in rows:
                    row["hash"] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertIn("Invalid benchmark CSV", output)
                self.assertNotIn("Output hashes", output)

    def test_event_hash_comparison_ignores_hexadecimal_case(self):
        rows = fixture()
        rows[0]["hash"] = rows[0]["hash"].upper()
        result, output = self.run_summary(rows)
        self.assertEqual(result, 0)
        self.assertIn("identical across all variants", output)

    def test_invalid_peak_orders_are_rejected_before_reporting(self):
        for value in ("", "-1", "1.5"):
            with self.subTest(value=value):
                rows = fixture()
                rows[0]["peak_orders"] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertIn("Invalid benchmark CSV", output)
                self.assertNotIn("Output hashes", output)

    def test_inconsistent_peak_orders_are_rejected_in_either_row_order(self):
        rows = fixture()
        rows[0]["peak_orders"] = "11"
        for ordered in (rows, list(reversed(rows))):
            result, output = self.run_summary(ordered)
            self.assertEqual(result, 2)
            self.assertIn("peak resting orders disagree", output)
            self.assertNotIn("Output hashes", output)

    def test_peak_orders_cannot_exceed_capacity_or_workload(self):
        for peak, capacity in ((11, 10), (101, 1000)):
            with self.subTest(peak=peak, capacity=capacity):
                rows = fixture()
                for row in rows:
                    row.update(peak_orders=str(peak), max_orders=str(capacity))
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertIn("peak resting orders exceed", output)
                self.assertNotIn("Output hashes", output)

    def test_peak_orders_can_equal_capacity_or_workload(self):
        for peak, capacity in ((10, 10), (100, 1000), (100, 100)):
            with self.subTest(peak=peak, capacity=capacity):
                rows = fixture()
                for row in rows:
                    row.update(peak_orders=str(peak), max_orders=str(capacity))
                result, output = self.run_summary(rows)
                self.assertEqual(result, 0)
                self.assertIn("Output hashes", output)

    def test_declared_launch_count_is_enforced(self):
        result, output = self.run_summary(fixture(), launches=2)
        self.assertNotEqual(result, 0)
        self.assertIn("expected 2 launches", output)
        result, _ = self.run_summary(fixture() + fixture(), launches=2)
        self.assertEqual(result, 0)

    def test_empty_input_is_rejected(self):
        result, output = self.run_summary([])
        self.assertNotEqual(result, 0)
        self.assertIn("no benchmark rows", output)

    def test_invalid_sample_count_is_rejected_before_reporting(self):
        for operation, count in (("all", "0"), ("all", ""), ("limit", "-1"), ("limit", "101")):
            with self.subTest(operation=operation, count=count):
                rows = fixture()
                next(row for row in rows if row["op"] == operation)["count"] = count
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertNotIn("Output hashes", output)

    def test_zero_operations_can_be_summarized(self):
        rows = fixture()
        for row in rows:
            row.update(ops="0", count="0", mops="0.000", peak_orders="0",
                       p50="0", p90="0", p99="0", p999="0", max="0")
        result, output = self.run_summary(rows)
        self.assertEqual(result, 0)
        self.assertIn("0.0 (0.0-0.0)", output)
        self.assertNotIn("NOISY", output)

    def test_empty_workload_cannot_report_positive_throughput(self):
        rows = fixture()
        for row in rows:
            row.update(ops="0", count="0", mops="0.000", peak_orders="0",
                       p50="0", p90="0", p99="0", p999="0", max="0")
        rows[0]["mops"] = "0.001"
        result, output = self.run_summary(rows)
        self.assertEqual(result, 2)
        self.assertIn("zero operations", output)
        self.assertNotIn("Output hashes", output)

    def test_zero_samples_cannot_supply_positive_percentiles(self):
        rows = fixture()
        for row in rows:
            row.update(ops="0", count="0", mops="0.000")
        result, output = self.run_summary(rows)
        self.assertEqual(result, 2)
        self.assertIn("zero latency samples", output)

    def test_operation_counts_must_cover_workload(self):
        rows = fixture()
        for row in rows:
            if row["op"] == "limit":
                row["count"] = "24"
        result, output = self.run_summary(rows)
        self.assertEqual(result, 2)
        self.assertIn("do not sum", output)

    def test_launches_cannot_hide_compensating_sample_counts(self):
        first, second = fixture(), fixture()
        next(row for row in first if row["op"] == "limit")["count"] = "24"
        next(row for row in second if row["op"] == "limit")["count"] = "26"
        result, output = self.run_summary(first + second, launches=2)
        self.assertEqual(result, 2)
        self.assertIn("sample counts disagree", output)

    def test_reordered_rows_can_be_summarized(self):
        rows = fixture()
        result, output = self.run_summary(sorted(rows, key=lambda row: row["op"]), launches=1)
        self.assertEqual(result, 0)
        self.assertIn("identical across all variants", output)

    def test_nonzero_range_with_zero_median_is_noisy(self):
        rows = fixture() + fixture() + fixture()
        for row in rows:
            row["mops"] = "0.000"
        rows[0]["mops"] = "1.000"
        result, output = self.run_summary(rows, launches=3)
        self.assertEqual(result, 0)
        self.assertIn("0.0 (0.0-1.0) NOISY", output)

    def test_invalid_throughput_is_rejected_before_reporting(self):
        for value in ("nan", "inf", "-1", "", "unavailable"):
            with self.subTest(value=value):
                rows = fixture()
                rows[0]["mops"] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertIn("Invalid benchmark CSV", output)
                self.assertNotIn("Output hashes", output)

    def test_invalid_latency_percentiles_are_rejected_before_reporting(self):
        for field, value in (("p50", "bad"), ("p90", ""), ("p50", "-1"), ("p99", "84")):
            with self.subTest(field=field, value=value):
                rows = fixture()
                rows[0][field] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertIn("Invalid benchmark CSV", output)
                self.assertNotIn("Output hashes", output)

    def test_invalid_latency_maximum_is_rejected_before_reporting(self):
        for value in ("", "-1", "41"):
            with self.subTest(value=value):
                rows = fixture()
                rows[0]["max"] = value
                result, output = self.run_summary(rows)
                self.assertEqual(result, 2)
                self.assertNotIn("Output hashes", output)

    def test_operation_maxima_must_fit_available_aggregate_maxima(self):
        first, second = fixture(), fixture()
        first_market, second_all, second_market = (
            next(row for row in launch if (row["regime"], row["book"], row["op"]) == ("fixed-mid", "v1", op))
            for launch, op in ((first, "market"), (second, "all"), (second, "market"))
        )
        second_all["max"] = second_market["max"] = "126"
        # The compatible rows remain valid when interleaved or reversed.
        rows = [row for pair in zip(first, second) for row in pair]
        for ordered in (rows, list(reversed(rows))):
            result, output = self.run_summary(ordered, launches=2)
            self.assertEqual(result, 0, output)

        # Two market maxima of 126 cannot fit into aggregate maxima of 84 and 126.
        first_market["max"] = "126"
        result, output = self.run_summary(list(reversed(rows)), launches=2)
        self.assertEqual(result, 2, output)
        self.assertIn("operation latency maxima exceed available aggregate maxima", output)
        self.assertNotIn("Output hashes", output)

    def test_aggregate_maximum_must_equal_largest_operation_maximum(self):
        for operation in ("all", "limit"):
            with self.subTest(operation=operation):
                rows = fixture() + fixture()
                row = next(item for item in rows if item["op"] == operation)
                row["max"] = "85"
                result, output = self.run_summary(rows, launches=2)
                self.assertEqual(result, 2)
                self.assertIn("latency maxima disagree", output)
                self.assertNotIn("Output hashes", output)

    def test_matching_maxima_do_not_require_launch_order(self):
        rows = fixture() + fixture()
        for row in rows[:len(rows) // 2]:
            if row["book"] == "v1" and row["regime"] == "fixed-mid" and row["op"] in ("all", "market"):
                row["max"] = "85"
        shuffled = sorted(rows, key=lambda row: (row["op"], row["max"], row["book"]))
        result, output = self.run_summary(shuffled, launches=2)
        self.assertEqual(result, 0)
        self.assertIn("identical across all variants", output)

    def test_one_latency_sample_requires_equal_percentiles_and_maximum(self):
        rows = fixture()
        for row in rows:
            if row["op"] == "limit":
                row["count"] = "49"
            elif row["op"] == "market":
                row.update(count="1", p50="84", p90="84", p99="84", p999="84", max="84")
        result, output = self.run_summary(rows)
        self.assertEqual(result, 0, output)

        next(row for row in rows if row["op"] == "market")["p50"] = "42"
        result, output = self.run_summary(rows)
        self.assertEqual(result, 2)
        self.assertIn("one latency sample", output)
        self.assertNotIn("Output hashes", output)

    def test_empty_samples_cannot_supply_a_positive_maximum(self):
        rows = fixture()
        for row in rows:
            row.update(ops="0", count="0", mops="0", peak_orders="0",
                       p50="0", p90="0", p99="0", p999="0", max="0")
        rows[0]["max"] = "1"
        result, output = self.run_summary(rows)
        self.assertEqual(result, 2)
        self.assertIn("zero latency samples", output)


if __name__ == "__main__":
    unittest.main()
