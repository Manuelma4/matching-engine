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
             "p50": "42", "p90": "42", "p99": "42", "p999": "42"}
            for book in BOOKS for regime in REGIMES for op in OPS]


class SummaryEvidenceTests(unittest.TestCase):
    def run_summary(self, rows, launches=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.csv"
            with path.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=fixture()[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = main(str(path), launches)
            return result, output.getvalue()

    def test_complete_matrix_is_accepted(self):
        result, output = self.run_summary(fixture())
        self.assertEqual(result, 0)
        self.assertIn("identical across all variants", output)

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

    def test_zero_operations_can_be_summarized(self):
        rows = fixture()
        for row in rows:
            row.update(ops="0", mops="0.000", peak_orders="0",
                       p50="0", p90="0", p99="0", p999="0")
        result, output = self.run_summary(rows)
        self.assertEqual(result, 0)
        self.assertIn("0.0 (0.0-0.0)", output)
        self.assertNotIn("NOISY", output)

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


if __name__ == "__main__":
    unittest.main()
