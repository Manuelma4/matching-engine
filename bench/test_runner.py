"""Exercise the benchmark runner with a fake executable and small synthetic reports."""
import os
import shutil
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
if [[ ( "$MODE" == balanced-captures || "$MODE" == crossed-maxima || "$MODE" == valid-maxima ) && "$2" == v1 ]]; then
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
        if [[ "$MODE" == balanced-captures && "$regime" == fixed-mid && "$op" == market ]]; then
            if [[ "$balance" == omit ]]; then copies=0; fi
            if [[ "$balance" == duplicate ]]; then copies=2; fi
        fi
        latency=0
        if [[ ( "$MODE" == crossed-maxima || "$MODE" == valid-maxima ) && "$2" == v1 && "$regime" == fixed-mid ]]; then
            aggregate_latency=84
            limit_latency=126
            if [[ "$balance" == duplicate ]]; then
                aggregate_latency=126
                limit_latency=84
            fi
            if [[ "$MODE" == valid-maxima ]]; then limit_latency=$aggregate_latency; fi
            if [[ "$op" == all ]]; then latency=$aggregate_latency; fi
            if [[ "$op" == limit ]]; then latency=$limit_latency; fi
        fi
        for ((copy = 0; copy < copies; copy++)); do
            printf '%s,%s,42,1,%s,0,0,%s,%s,%s,%s,%s,%s,%s,1024\n' "$2" "$regime" "$hash" "$op" "$count" "$latency" "$latency" "$latency" "$latency" "$latency"
        done
    done
done
"""
REPORTS = ("env.txt", "raw.csv", "summary.md")


class RunnerEvidenceTests(unittest.TestCase):
    def test_promotion_failure_restores_previous_reports_or_absence(self):
        for failed_report in REPORTS:
            cases = [(True, False), (False, False)]
            if failed_report != "env.txt":
                cases.append((True, True))
            for existing, rollback_failure in cases:
                with self.subTest(failed_report=failed_report, existing=existing, rollback_failure=rollback_failure), tempfile.TemporaryDirectory() as directory:
                    scratch = Path(directory)
                    binary = scratch / "me_bench"
                    binary.write_text(FAKE)
                    binary.chmod(0o700)
                    output = scratch / "reports"
                    output.mkdir()
                    previous = {name: f"previous {name}\n".encode() for name in REPORTS} if existing else {}
                    for name, content in previous.items():
                        (output / name).write_bytes(content)
                    wrappers = scratch / "wrappers"
                    wrappers.mkdir()
                    move = wrappers / "mv"
                    move.write_text('''#!/usr/bin/env bash
if [[ "$2" == "$OUT"/.run.*/"$FAILED_REPORT" && ! -e "$FAIL_MARKER" ]]; then
    : > "$FAIL_MARKER"
    exit 23
fi
if [[ "$ROLLBACK_FAILURE" == 1 && "$2" == "$OUT"/.run.*/previous/env.txt ]]; then exit 24; fi
exec "$REAL_MV" "$@"
''')
                    move.chmod(0o700)
                    result = subprocess.run(["bash", "bench/run.sh"], cwd=ROOT, capture_output=True, text=True, check=False,
                        env=os.environ | {"BIN": str(binary), "OUT": str(output), "RUNS": "1", "OPS": "1",
                            "SEED": "42", "MODE": "ok", "PATH": str(wrappers) + os.pathsep + os.environ["PATH"],
                            "REAL_MV": shutil.which("mv"), "FAILED_REPORT": failed_report,
                            "FAIL_MARKER": str(scratch / "failed"), "ROLLBACK_FAILURE": str(int(rollback_failure))})
                    self.assertEqual(result.returncode, 23, result.stderr)
                    if rollback_failure:
                        stages = list(output.glob(".run.*"))
                        self.assertEqual(len(stages), 1, result.stderr)
                        backup = stages[0] / "previous" / "env.txt"
                        self.assertEqual(backup.read_bytes(), previous["env.txt"])
                        self.assertIn(str(stages[0] / "previous"), result.stderr)
                        self.assertIn("Report rollback failed", result.stderr)
                    else:
                        self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, previous)

    def test_replaces_previous_reports_only_after_valid_summary(self):
        for mode, code in (
            ("help-failure", 42), ("abort", 7), ("mismatch", 1), ("sample-mismatch", 2),
            ("help-success", 0), ("ok", 0), ("balanced-captures", 2),
            ("wrong-ops", 2), ("wrong-seed", 2), ("crossed-maxima", 2), ("valid-maxima", 0),
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

                requested_ops = "2" if mode == "wrong-ops" else "1"
                requested_seed = "43" if mode == "wrong-seed" else "42"
                env = os.environ | {
                    "BIN": str(binary), "OUT": str(output), "RUNS": "2", "OPS": requested_ops, "SEED": requested_seed, "MODE": mode,
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
                if mode.startswith("wrong-"):
                    self.assertIn("does not match requested", result.stderr)
                if mode == "mismatch":
                    self.assertIn("MISMATCH", result.stderr)
                if mode == "crossed-maxima":
                    self.assertIn("capture latency maxima disagree", result.stderr)
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
