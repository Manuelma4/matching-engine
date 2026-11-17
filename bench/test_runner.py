"""Exercise the benchmark runner with a fake executable and small synthetic reports."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE = r"""#!/usr/bin/env bash
if [[ "$1" == --help ]]; then
    echo '  books: v1 map map-oa vec ladder'
    if [[ "$MODE" == help-failure ]]; then exit 42; fi
    if [[ "$MODE" == help-success ]]; then exit 0; fi
    exit 2
fi
if [[ "$MODE" == abort && "$2" == map ]]; then exit 7; fi
balance=
if [[ "$MODE" == balanced-captures && "$2" == v1 ]]; then
    if [[ -f "$OUT/../first-v1" ]]; then
        balance=duplicate
    else
        balance=omit
        : > "$OUT/../first-v1"
    fi
fi
for regime in fixed-mid random-walk deep-book flash-crash cancel-heavy; do
    for op in all limit market modify cancel; do
        hash=0123456789abcdef
        if [[ "$MODE" == mismatch && "$2" == map ]]; then hash=1123456789abcdef; fi
        count=0
        if [[ "$op" == limit || ( "$op" == all && "$MODE" != sample-mismatch ) ]]; then count=1; fi
        copies=1
        if [[ "$regime" == fixed-mid && "$op" == market ]]; then
            if [[ "$balance" == omit ]]; then copies=0; fi
            if [[ "$balance" == duplicate ]]; then copies=2; fi
        fi
        for ((copy = 0; copy < copies; copy++)); do
            printf '%s,%s,42,1,%s,0,0,%s,%s,0,0,0,0,0,1024\n' "$2" "$regime" "$hash" "$op" "$count"
        done
    done
done
"""
REPORTS = ("env.txt", "raw.csv", "summary.md")


class RunnerEvidenceTests(unittest.TestCase):
    def test_replaces_previous_reports_only_after_valid_summary(self):
        for mode, code in (
            ("help-failure", 42), ("abort", 7), ("mismatch", 1), ("sample-mismatch", 2),
            ("help-success", 0), ("ok", 0), ("balanced-captures", 2),
        ):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                scratch = Path(directory)
                binary = scratch / "me_bench"
                binary.write_text(FAKE)
                binary.chmod(0o700)
                output = scratch / "reports"
                output.mkdir()
                previous = {name: f"previous {name}\n".encode() for name in REPORTS}
                for name, content in previous.items():
                    (output / name).write_bytes(content)

                env = os.environ | {
                    "BIN": str(binary), "OUT": str(output), "RUNS": "2", "OPS": "1", "SEED": "42", "MODE": mode,
                }
                result = subprocess.run(
                    ["bash", "bench/run.sh"], cwd=ROOT, env=env, capture_output=True, text=True, check=False,
                )
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual({path.name for path in output.iterdir()}, set(REPORTS))
                contents = {name: (output / name).read_bytes() for name in REPORTS}
                if code:
                    self.assertEqual(contents, previous)
                else:
                    self.assertIn(b"Launches per variant: 2", contents["summary.md"])
                    rows = contents["raw.csv"].splitlines()
                    self.assertEqual(len(rows), 251)
                    forward = [b"v1", b"map", b"map-oa", b"vec", b"ladder"]
                    self.assertEqual(
                        [row.split(b",", 1)[0] for row in rows[1::25]], forward + forward[::-1],
                    )
                if mode == "mismatch":
                    self.assertIn("MISMATCH", result.stderr)
                if mode == "balanced-captures":
                    self.assertIn("Invalid capture 1-0.csv for v1", result.stderr)

    def test_invalid_report_destination_preserves_existing_files(self):
        for kind in ("directory", "symlink"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                scratch = Path(directory)
                binary = scratch / "me_bench"
                binary.write_text(FAKE)
                binary.chmod(0o700)
                for name in ("env.txt", "raw.csv"):
                    (scratch / name).write_text("previous " + name)
                invalid = scratch / "summary.md"
                target = scratch / "target"
                target.mkdir()
                if kind == "directory":
                    invalid.mkdir()
                else:
                    invalid.symlink_to(target, target_is_directory=True)

                result = subprocess.run(
                    ["bash", "bench/run.sh"], cwd=ROOT, capture_output=True, text=True, check=False,
                    env=os.environ | {
                        "BIN": str(binary), "OUT": str(scratch), "RUNS": "1", "OPS": "1", "SEED": "42", "MODE": "ok",
                    },
                )
                self.assertEqual(result.returncode, 2)
                self.assertIn("Invalid report destination", result.stderr)
                self.assertEqual((scratch / "env.txt").read_text(), "previous env.txt")
                self.assertEqual((scratch / "raw.csv").read_text(), "previous raw.csv")
                self.assertEqual(list(target.iterdir()), [])
                if kind == "directory":
                    self.assertEqual(list(invalid.iterdir()), [])
