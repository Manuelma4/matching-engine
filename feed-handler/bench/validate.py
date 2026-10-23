#!/usr/bin/env python3
"""Record a full-day census and replay, with SHA-256 identity and gzip CRC checks.

Only aggregate evidence is written; the market data stays in the local input file.
This is an integrity run through Python/gzip/pipes, not a throughput benchmark.
"""

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import zlib


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def run_stream(tool, source, output):
    """Reopen gzip for each tool; validate CRC and hash the exact decompressed bytes."""
    command = [str(tool), "-"]
    digest = hashlib.sha256()
    size = 0
    error = None
    with output.open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=log, stderr=log)
        try:
            with gzip.open(source, "rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
                    size += len(block)
                    process.stdin.write(block)
        except (OSError, EOFError, zlib.error) as exc:
            error = f"{type(exc).__name__}: {exc}"
        finally:
            try:
                process.stdin.close()
            except BrokenPipeError as exc:
                error = error or str(exc)
            code = process.wait()
    return {"command": [tool.name, "-"], "exit_code": code, "error": error,
            "raw_bytes": size, "raw_sha256": digest.hexdigest(), "log": output.name}


def field(pattern, text, convert=int):
    match = re.search(pattern, text, flags=re.MULTILINE)
    if not match:
        raise ValueError(f"missing report field: {pattern}")
    return convert(match.group(1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="official full-day BinaryFILE .gz")
    parser.add_argument("--bin-dir", type=Path, default=Path("build"))
    parser.add_argument("--output", type=Path, required=True, help="new evidence directory")
    parser.add_argument("--source-url", default=None, help="provenance URL, recorded without fetching")
    args = parser.parse_args()
    source = args.archive.resolve()
    tools = [(args.bin_dir / name).resolve() for name in ("itch_census", "itch_replay")]
    if not source.is_file() or not all(tool.is_file() for tool in tools):
        parser.error("archive and both built tools must exist")
    if args.output.exists():
        parser.error("output directory already exists; use a new directory to preserve evidence")
    args.output.mkdir(parents=True)
    root = Path(__file__).resolve().parent.parent
    source_files = (git_output(root, "ls-files", "--cached", "--others", "--exclude-standard") or "").splitlines()
    source_hashes = {name: sha256_file(root / name) for name in sorted(source_files)
                     if (name == "CMakeLists.txt" or
                         (name.split("/")[0] in {"include", "src", "tools", "bench"} and
                          Path(name).suffix in {".hpp", ".cpp", ".py", ".sh"})) and
                     (root / name).is_file()}
    evidence = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "archive": {"name": source.name, "bytes": source.stat().st_size,
                    "sha256": sha256_file(source), "source_url": args.source_url},
        "environment": {"platform": platform.platform(), "machine": platform.machine(),
                        "python": platform.python_version()},
        "source": {"git_commit": git_output(root, "rev-parse", "HEAD"),
                   "git_dirty": bool(git_output(root, "status", "--porcelain")),
                   "file_sha256": source_hashes,
                   "diff_sha256": hashlib.sha256((git_output(root, "diff", "HEAD") or "").encode()).hexdigest()},
        "tools": {tool.name: {"sha256": sha256_file(tool)} for tool in tools},
        "runs": {}, "checks": {}, "passed": False,
        "timing_scope": "Python gzip streaming with hashing and pipe I/O; not a benchmark",
    }
    for tool in tools:
        print(f"Running {tool.name} on {source.name}", flush=True)
        evidence["runs"][tool.name] = run_stream(tool, source, args.output / f"{tool.name}.txt")
    census, replay = [evidence["runs"][tool.name] for tool in tools]
    checks = evidence["checks"]
    checks["tools_succeeded"] = all(run["exit_code"] == 0 and run["error"] is None
                                    for run in (census, replay))
    checks["same_raw_input"] = (census["raw_bytes"] == replay["raw_bytes"] > 0 and
                                census["raw_sha256"] == replay["raw_sha256"])
    try:
        ctext = (args.output / census["log"]).read_text()
        rtext = (args.output / replay["log"]).read_text()
        counts = {match[0]: int(match[1]) for match in
                  re.findall(r"^([A-Za-z])\s+.+?\s+(\d+)\s+\d+\s*$", ctext, re.MULTILINE)}
        c_messages = field(r"^messages\s+(\d+)", ctext)
        r_messages = field(r"^messages\s+(\d+)", rtext)
        evidence["summary"] = {
            "messages": c_messages, "message_counts": counts,
            "raw_bytes": census["raw_bytes"], "raw_sha256": census["raw_sha256"],
            "peak_orders": field(r"^peak orders\s+(\d+)", rtext),
            "live_orders_at_end": field(r"^live at end\s+(\d+)", rtext),
            "final_book_hash": field(r"^book hash\s+([0-9a-f]+)", rtext, str),
        }
        checks["same_message_count"] = c_messages == r_messages == sum(counts.values()) > 0
        checks["census_byte_identity"] = ("== file size" in ctext and
                                         field(r"^file bytes\s+(\d+)", ctext) == census["raw_bytes"])
        checks["no_trailing_bytes"] = all(field(r"^trailing\s+(\d+)", text) == 0
                                          for text in (ctext, rtext))
        checks["system_C_seen"] = bool(re.search(r"^end of messages\s+seen$", rtext, re.MULTILINE))
        checks["book_empty_at_end"] = evidence["summary"]["live_orders_at_end"] == 0
        anomaly_values = re.findall(r"\d+", field(r"^anomalies\s+(.+)$", rtext, str))
        checks["no_replay_anomalies"] = len(anomaly_values) >= 6 and all(int(x) == 0 for x in anomaly_values)
    except ValueError as exc:
        evidence["report_error"] = str(exc)
        checks["reports_parseable"] = False
    evidence["passed"] = all(checks.values())
    report = args.output / "validation.json"
    report.write_text(json.dumps(evidence, indent=2) + "\n")
    print(f"{'PASS' if evidence['passed'] else 'FAIL'}: {report}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
