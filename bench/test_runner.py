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
for regime in fixed-mid random-walk deep-book flash-crash cancel-heavy; do
    for op in all limit market modify cancel; do
        hash=0123456789abcdef
        if [[ "$MODE" == mismatch && "$2" == map ]]; then hash=1123456789abcdef; fi
        printf '%s,%s,42,1,%s,0,0,%s,0,0,0,0,0,0,1024\n' "$2" "$regime" "$hash" "$op"
    done
done
"""
REPORTS = ("env.txt", "raw.csv", "summary.md")


class RunnerEvidenceTests(unittest.TestCase):
    def test_replaces_previous_reports_only_after_valid_summary(self):
        for mode, code in (
            ("help-failure", 42), ("abort", 7), ("mismatch", 1), ("help-success", 0), ("ok", 0),
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
                    self.assertEqual(len(contents["raw.csv"].splitlines()), 251)
                if mode == "mismatch":
                    self.assertIn("MISMATCH", result.stderr)
