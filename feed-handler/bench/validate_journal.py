#!/usr/bin/env python3
"""Prove deterministic journal creation and sampled intermediate replay equivalence.

Raw data, journals and checkpoint rows remain in a fresh private output directory.
The optional public report contains aggregate evidence and identities only. This
includes hashing, CRC checks, file I/O and state walks; it is not a benchmark.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def identity(path):
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def strict_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"non-finite JSON value: {value}")
    return json.loads(text, object_pairs_hook=unique, parse_constant=invalid)


def run(command, output, name):
    with (output / (name + ".json")).open("x") as stdout, \
            (output / (name + ".stderr")).open("x") as stderr:
        result = subprocess.run([str(arg) for arg in command], stdout=stdout, stderr=stderr)
    report = strict_json((output / (name + ".json")).read_text())
    if (result.returncode != 0 or (output / (name + ".stderr")).stat().st_size != 0 or
            not isinstance(report, dict) or report.get("passed") is not True):
        raise ValueError(f"{name} failed; inspect its private logs")
    return report


def validate_replay(report, source_bytes, source_hash, every, raw, blocks):
    integers = ("schema_version", "fingerprint_version", "journal_blocks", "messages", "records",
        "input_bytes", "consumed_bytes", "checkpoint_every", "checkpoints", "final_orders", "peak_orders",
        "adds", "executions", "executed_shares", "non_printable_shares", "trade_shares", "cross_shares",
        "broken_trades", "unknown_ref", "duplicate_ref", "share_underflow", "capacity", "invalid_side",
        "locate_mismatch", "unknown_type", "bad_length", "end_records", "after_end", "trailing_bytes")
    if any(type(report.get(key)) is not int or not 0 <= report[key] <= 0xffffffffffffffff for key in integers):
        raise ValueError("replay summary has missing or invalid unsigned integer fields")
    if (report["schema_version"] != 1 or report["fingerprint_version"] != 1 or
            report.get("format") != ("raw" if raw else "journal_v1") or
            report.get("source_sha256") != (None if raw else source_hash) or
            report.get("source_identity_verified") is not False or report["journal_blocks"] != blocks):
        raise ValueError("unexpected replay format, fingerprint or source identity metadata")
    if (report.get("passed") is not True or report.get("end_of_messages") is not True or
            report.get("allow_partial") is not False or report["messages"] == 0 or
            report["records"] != report["messages"] + report["end_records"] or report["end_records"] > 1 or
            report["input_bytes"] != source_bytes or report["consumed_bytes"] != source_bytes or
            report["checkpoint_every"] != every or report["final_orders"] != 0):
        raise ValueError("replay is not a complete clean day with the requested checkpoint coverage")
    for key in ("unknown_ref", "duplicate_ref", "share_underflow", "capacity", "invalid_side",
                "locate_mismatch", "unknown_type", "bad_length", "after_end", "trailing_bytes"):
        if report[key] != 0:
            raise ValueError(f"nonzero replay anomaly: {key}")
    if not all(isinstance(report.get(key), str) and re.fullmatch(r"[0-9a-f]{16}", report[key])
               for key in ("book_hash", "state_hash")):
        raise ValueError("missing or malformed final replay fingerprints")


def checkpoint_summary(path, report, every):
    messages = report["messages"]
    count = nonempty = max_live = 0
    previous_offset = -1
    with path.open(newline="") as stream:
        rows = csv.DictReader(stream)
        if rows.fieldnames != ["sequence", "source_offset", "timestamp_ns", "live_orders",
                              "book_hash", "state_hash"]:
            raise ValueError("unexpected checkpoint schema")
        for count, row in enumerate(rows, 1):
            if None in row or None in row.values():
                raise ValueError("malformed checkpoint row")
            sequence, offset, timestamp, live = [int(row[key]) for key in
                ("sequence", "source_offset", "timestamp_ns", "live_orders")]
            if (sequence != min(count * every, messages) or not previous_offset < offset <= report["input_bytes"] or
                    not 0 <= timestamp < (1 << 48) or not 0 <= live <= report["peak_orders"]):
                raise ValueError("unexpected checkpoint sequence, source offset or value")
            if not all(re.fullmatch(r"[0-9a-f]{16}", row[key]) for key in ("book_hash", "state_hash")):
                raise ValueError("malformed checkpoint fingerprint")
            previous_offset = offset
            nonempty += live != 0
            max_live = max(max_live, live)
    if count != (messages + every - 1) // every or messages <= 0:
        raise ValueError("checkpoint coverage does not reach the final message")
    if (previous_offset != report["input_bytes"] - 2 * report["end_records"] or
            row["book_hash"] != report["book_hash"] or row["state_hash"] != report["state_hash"] or
            live != report["final_orders"]):
        raise ValueError("final checkpoint does not match the final source event and summary state")
    return {"rows": count, "nonempty_book_rows": nonempty, "maximum_sampled_live_orders": max_live,
            "last_source_offset": previous_offset, "bytes": path.stat().st_size, "sha256": sha256(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="raw full-day BinaryFILE")
    parser.add_argument("--replay-tool", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="new private artefact directory")
    parser.add_argument("--report", type=Path, help="new aggregate JSON report, otherwise output/evidence.json")
    parser.add_argument("--expected-sha256", help="optional independently retained raw input identity")
    parser.add_argument("--checkpoint-every", type=int, default=10_000_000)
    parser.add_argument("--max-orders", type=int, default=1 << 22)
    args = parser.parse_args()
    if args.checkpoint_every <= 0 or not 0 < args.max_orders <= 0xffffffff:
        parser.error("positive checkpoint spacing and uint32 order capacity required")
    if args.expected_sha256 and not re.fullmatch(r"[0-9a-f]{64}", args.expected_sha256):
        parser.error("expected SHA-256 must be 64 lower-case hexadecimal characters")
    source, tool = args.input.resolve(), args.replay_tool.resolve()
    if not source.is_file() or not tool.is_file() or args.output.exists() or (args.report and args.report.exists()):
        parser.error("input/tool must exist and output/report must be fresh")
    output = args.output.resolve()
    output.mkdir(parents=True)
    report_path = args.report.resolve() if args.report else output / "evidence.json"
    root = Path(__file__).resolve().parent.parent
    files = (git(root, "ls-files", "--cached", "--others", "--exclude-standard") or "").splitlines()
    source_hashes = {name: sha256(root / name) for name in sorted(files)
        if (name == "CMakeLists.txt" or (name.split("/")[0] in {"include", "src", "tools", "bench"}
            and Path(name).suffix in {".hpp", ".cpp", ".py"})) and (root / name).is_file()}
    evidence = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "observed-wire journal v1; complete-day replay with sampled FIFO/state checkpoints",
        "timing_scope": "integrity and equivalence run including hashing and I/O; not a benchmark",
        "environment": {"platform": platform.platform(), "python": platform.python_version()},
        "source": {"git_commit": git(root, "rev-parse", "HEAD"),
                   "git_dirty": bool(git(root, "status", "--porcelain")), "file_sha256": source_hashes},
        "replay_tool_sha256": sha256(tool), "runs": {}, "checks": {}, "passed": False}
    try:
        original = identity(source)
        original_tool = identity(tool)
        source_hash = sha256(source)
        evidence["input"] = {"name": source.name, "bytes": original[2], "sha256": source_hash,
                             "expected_sha256": args.expected_sha256}
        if args.expected_sha256 and source_hash != args.expected_sha256:
            raise ValueError("raw input does not match the retained expected identity")
        journals = [output / f"day-{index}.jnl" for index in (1, 2)]
        created = [run([sys.executable, root / "bench/journal.py", "create", source, journal],
                       output, f"create-{index}") for index, journal in enumerate(journals, 1)]
        evidence["journals"] = [{key: value for key, value in result.items()
            if key not in {"journal", "input", "errors"}} for result in created]
        checks = evidence["checks"]
        journal_identities = [identity(path) for path in journals]
        checks["verified_source_identity"] = all(result.get("source_identity_verified") is True and
            type(result.get("source_bytes")) is int and result["source_bytes"] == original[2] and
            result.get("source_sha256") == source_hash and type(result.get("blocks")) is int and result["blocks"] > 0 and
            result.get("canonical_packing") is True and result.get("version") == 1
            for result in created)
        checks["deterministic_journal_bytes"] = (created[0]["journal_sha256"] == created[1]["journal_sha256"]
            and created[0]["journal_bytes"] == created[1]["journal_bytes"])
        runs = evidence["runs"]
        for name, path, raw in (("raw", source, True), ("journal-1", journals[0], False),
                                ("journal-2", journals[1], False)):
            csv_path = output / (name + ".checkpoints.csv")
            command = [tool, "--checkpoint-every", args.checkpoint_every, "--max-orders", args.max_orders,
                       "--checkpoints", csv_path, *(["--raw"] if raw else []), path]
            summary = run(command, output, name)
            validate_replay(summary, original[2], source_hash, args.checkpoint_every, raw,
                            0 if raw else created[0]["blocks"])
            checkpoint = checkpoint_summary(csv_path, summary, args.checkpoint_every)
            if summary.get("checkpoints") != checkpoint["rows"]:
                raise ValueError(f"{name} checkpoint count differs from its summary")
            runs[name] = {"summary": summary, "checkpoints": checkpoint}
        checks["complete_clean_replays"] = all(run["summary"].get("end_of_messages") is True and
            run["summary"].get("allow_partial") is False and run["summary"].get("final_orders") == 0 and
            run["summary"].get("input_bytes") == original[2] and run["summary"].get("trailing_bytes") == 0
            for run in runs.values())
        checks["journal_replay_identity_metadata"] = all(runs[name]["summary"].get("source_sha256") == source_hash
            and runs[name]["summary"].get("source_identity_verified") is False for name in ("journal-1", "journal-2"))
        excluded = {"format", "source_sha256", "source_identity_verified", "journal_blocks"}
        semantic = [{key: value for key, value in run["summary"].items() if key not in excluded}
                    for run in runs.values()]
        checks["same_semantic_summaries"] = semantic[0] == semantic[1] == semantic[2]
        fingerprints = [run["checkpoints"]["sha256"] for run in runs.values()]
        checks["same_intermediate_checkpoints"] = fingerprints[0] == fingerprints[1] == fingerprints[2]
        checks["nonempty_intermediate_coverage"] = runs["raw"]["checkpoints"]["nonempty_book_rows"] > 0
        checks["input_unchanged"] = identity(source) == original
        checks["tool_unchanged"] = identity(tool) == original_tool and sha256(tool) == evidence["replay_tool_sha256"]
        checks["journals_unchanged"] = all(identity(path) == original_identity and sha256(path) == result["journal_sha256"]
            for path, original_identity, result in zip(journals, journal_identities, created))
        checks["source_code_unchanged"] = all(sha256(root / name) == digest for name, digest in source_hashes.items())
        evidence["passed"] = bool(checks) and all(checks.values())
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        evidence["error"] = f"{type(exc).__name__}: {exc}"
    with report_path.open("x") as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{'PASS' if evidence['passed'] else 'FAIL'}: {report_path}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
