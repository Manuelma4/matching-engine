#!/usr/bin/env python3
"""Replay identical bytes through two independent books and compare sampled BBO.

Per-snapshot quotes, tool output and full summaries stay in a fresh private work
directory. The separate JSON report contains only aggregate evidence and hashes.
"""

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import zlib


REFERENCE_COMMIT = "3c646f9da182136125059243b475f7b8baa53773"
REFERENCE_REPOSITORY = "https://github.com/KareemJandali/itchbook"
PINNED_SOURCES = {
    "tools/book_replay.cpp": "a0421a30edb9894bb2c32b486448590a0a11910f2a416c1584a79a000483257b",
    "CMakeLists.txt": "eee433bf79d40e5ae6a50879be86f8a39a8cafe7e67f76098de823ce712398ab",
}
HEADER = ("ts", "ask_px_1", "ask_sz_1", "bid_px_1", "bid_sz_1")
INTERVAL_NS = 1_000_000_000
INTEGER = re.compile(r"-?(?:0|[1-9][0-9]*)\Z")
SCOPE = ("Independent implementation comparison of Nasdaq single-venue displayed BBO "
         "on a fixed time grid. This is not NBBO, full-depth, queue-priority, "
         "every-event, execution-quality or independently licensed market-data validation.")
CLOCK = ("First grid point strictly follows the first positive accepted timestamp. "
         "At a grid boundary, snapshots precede the triggering message, including "
         "a message timestamped exactly at the boundary. Only modelled messages "
         "for the selected locate, plus system events, advance the clock. No EOF flush.")
ANOMALIES = ("unknown_ref", "duplicate_ref", "share_underflow", "capacity", "unknown_type",
             "bad_length", "after_end", "invalid_side", "locate_mismatch", "trailing_bytes",
             "clock_regressions")


def sha256_file(path, opener=open):
    digest = hashlib.sha256()
    size = 0
    with opener(path, "rb") as stream:
        while block := stream.read(8 * 1024 * 1024):
            size += len(block)
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}


def file_identity(path):
    return {"path": str(path.resolve()), **sha256_file(path)}


def stat_identity(path):
    value = path.stat()
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(_):
    raise ValueError("non-finite JSON number")


def read_summary(path, label, errors):
    try:
        document = json.loads(path.read_bytes(), object_pairs_hook=unique_object,
                              parse_constant=reject_constant)
        if not isinstance(document, dict):
            raise ValueError("root is not an object")
        return document
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        # Do not copy untrusted summary contents (which can contain quotes) into
        # the public aggregate report.
        errors.append(f"{label}: missing or invalid summary ({type(exc).__name__})")
        return None


def uint(value, minimum=0):
    return type(value) is int and minimum <= value <= (1 << 64) - 1


def validate_summary(summary, label, symbol, raw_bytes, errors, interval_ns=INTERVAL_NS):
    if summary is None:
        return False
    problems = []
    if label == "local":
        if type(summary.get("schema_version")) is not int or summary["schema_version"] != 1:
            problems.append("schema_version must be integer one")
        if not uint(summary.get("locate"), 1) or summary.get("locate", 0) > 65535:
            problems.append("locate must be a positive 16-bit integer")
        for field in ("messages", "input_bytes", "snapshots_written", "first_snapshot_ns",
                      "last_snapshot_ns", "first_accepted_timestamp_ns", "last_accepted_timestamp_ns",
                      "next_snapshot_ns", "interval_ns", "peak_orders"):
            if not uint(summary.get(field), 1):
                problems.append(f"{field} must be a positive integer")
        for field in ("first_snapshot_ns", "last_snapshot_ns", "first_accepted_timestamp_ns",
                      "last_accepted_timestamp_ns"):
            if not uint(summary.get(field), 1) or summary.get(field, 0) >= (1 << 48):
                problems.append(f"{field} must fit the positive ITCH 48-bit timestamp range")
        for field in ("final_orders", "anomalies", *ANOMALIES):
            if not uint(summary.get(field)) or summary.get(field) != 0:
                problems.append(f"{field} must be integer zero")
        for field in ("passed", "strict_passed", "end_of_messages"):
            if summary.get(field) is not True:
                problems.append(f"{field} must be boolean true")
        if summary.get("symbol") != symbol:
            problems.append("symbol does not match requested symbol")
        if summary.get("interval_ns") != interval_ns:
            problems.append("interval_ns does not match the requested time grid")
        if summary.get("input_bytes") != raw_bytes:
            problems.append("input_bytes does not match the identified raw input")
    else:
        for field in ("messages_read", "messages_applied", "snapshots_written"):
            if not uint(summary.get(field), 1):
                problems.append(f"{field} must be a positive integer")
        for field in ("unknown_refs", "resting_orders", "resting_shares"):
            if not uint(summary.get(field)) or summary.get(field) != 0:
                problems.append(f"{field} must be integer zero")
        if summary.get("system_event") != "C":
            problems.append("system_event must be end-of-messages C")
        for field in ("best_bid", "best_ask"):
            if field not in summary or summary[field] is not None:
                problems.append(f"{field} must be present and null after the full-day close")
    errors.extend(f"{label}: {problem}" for problem in problems)
    return not problems


def read_snapshots(path, label, errors, interval_ns=INTERVAL_NS):
    rows = []
    try:
        with path.open(newline="", encoding="ascii") as stream:
            reader = csv.reader(stream, strict=True)
            if tuple(next(reader, ())) != HEADER:
                raise ValueError("CSV header must exactly match the five BBO columns")
            for line_number, cells in enumerate(reader, 2):
                if len(cells) != len(HEADER) or any(not INTEGER.fullmatch(cell) for cell in cells):
                    raise ValueError(f"malformed integer row at line {line_number}")
                values = tuple(map(int, cells))
                if any(not -(1 << 63) <= value < (1 << 63) for value in values):
                    raise ValueError(f"integer outside signed 64-bit range at line {line_number}")
                ts, ask, ask_size, bid, bid_size = values
                if ts <= 0 or ts % interval_ns:
                    raise ValueError(f"timestamp outside the requested time grid at line {line_number}")
                if rows and ts - rows[-1][0] != interval_ns:
                    raise ValueError(f"duplicate, missing or out-of-order grid point at line {line_number}")
                for price, size, absent in ((ask, ask_size, 9999999999),
                                            (bid, bid_size, -9999999999)):
                    if size < 0 or (size == 0 and price != absent) or (
                            size > 0 and not 0 < price <= 0xffffffff):
                        raise ValueError(f"invalid empty-side sentinel or quote at line {line_number}")
                rows.append(values)
        if not rows:
            raise ValueError("CSV contains no snapshots")
    except (OSError, UnicodeError, ValueError, csv.Error) as exc:
        # Messages above describe locations and categories, never quote values.
        detail = str(exc) if isinstance(exc, ValueError) else type(exc).__name__
        errors.append(f"{label}: {detail}")
    return rows


def compare_outputs(local_csv, reference_csv, local_summary, reference_summary,
                    symbol, raw_bytes, discrepancy_path, max_examples=10, interval_ns=INTERVAL_NS):
    result = {"symbol": symbol, "passed": False, "errors": [], "checks": {}}
    errors, checks = result["errors"], result["checks"]
    local = read_summary(local_summary, "local", errors)
    reference = read_summary(reference_summary, "reference", errors)
    checks["local_summary_valid"] = validate_summary(local, "local", symbol, raw_bytes, errors, interval_ns)
    checks["reference_summary_valid"] = validate_summary(reference, "reference", symbol, raw_bytes, errors, interval_ns)
    local_rows = read_snapshots(local_csv, "local", errors, interval_ns)
    reference_rows = read_snapshots(reference_csv, "reference", errors, interval_ns)
    result["snapshots"] = {}
    for label, path, rows in (("local", local_csv, local_rows),
                              ("reference", reference_csv, reference_rows)):
        nonempty_rows = sum(row[2] > 0 or row[4] > 0 for row in rows)
        result["snapshots"][label] = {"rows": len(rows),
            "first_timestamp_ns": rows[0][0] if rows else None,
            "last_timestamp_ns": rows[-1][0] if rows else None,
            "nonempty_book_rows": nonempty_rows,
            "two_sided_book_rows": sum(row[2] > 0 and row[4] > 0 for row in rows)}
        checks[f"{label}_observed_nonempty_book"] = nonempty_rows > 0
        if path.is_file():
            result["snapshots"][label].update(sha256_file(path))
    if checks["local_summary_valid"] and checks["reference_summary_valid"]:
        checks["same_message_count"] = local["messages"] == reference["messages_read"]
        first = (local["first_accepted_timestamp_ns"] // interval_ns + 1) * interval_ns
        last = local["last_accepted_timestamp_ns"] // interval_ns * interval_ns
        expected_rows = (last - first) // interval_ns + 1
        checks["valid_clock_extent"] = (local["first_accepted_timestamp_ns"] <=
            local["last_accepted_timestamp_ns"] and expected_rows > 0 and
            local["first_snapshot_ns"] == first and local["last_snapshot_ns"] == last and
            local["next_snapshot_ns"] == last + interval_ns)
        result["clock_extent"] = {"first_accepted_timestamp_ns": local["first_accepted_timestamp_ns"],
            "last_accepted_timestamp_ns": local["last_accepted_timestamp_ns"],
            "expected_first_snapshot_ns": first, "expected_last_snapshot_ns": last,
            "expected_rows": expected_rows}
        for label, rows, summary in (("local", local_rows, local),
                                      ("reference", reference_rows, reference)):
            checks[f"{label}_row_count_matches_summary"] = len(rows) == summary["snapshots_written"]
            checks[f"{label}_complete_clock_extent"] = bool(rows) and (
                len(rows) == expected_rows and rows[0][0] == first and rows[-1][0] == last)
        result["counts"] = {"messages": local["messages"],
            "reference_messages_applied": reference["messages_applied"],
            "local_final_orders": local["final_orders"], "local_peak_orders": local["peak_orders"],
            "local_anomalies": local["anomalies"], "reference_unknown_refs": reference["unknown_refs"],
            "reference_final_orders": reference["resting_orders"]}
    mismatches = Counter()
    examples = []
    private_examples = []
    i = j = common = equal = 0
    while i < len(local_rows) or j < len(reference_rows):
        lrow = local_rows[i] if i < len(local_rows) else None
        rrow = reference_rows[j] if j < len(reference_rows) else None
        if rrow is None or (lrow is not None and lrow[0] < rrow[0]):
            category, ts, fields = "extra_local_timestamp", lrow[0], []
            rrow = None
            i += 1
        elif lrow is None or rrow[0] < lrow[0]:
            category, ts, fields = "missing_local_timestamp", rrow[0], []
            lrow = None
            j += 1
        else:
            common += 1
            fields = [HEADER[k] for k in range(1, len(HEADER)) if lrow[k] != rrow[k]]
            i += 1
            j += 1
            if not fields:
                equal += 1
                continue
            category, ts = "quote_mismatch", lrow[0]
            for field in fields:
                mismatches[field] += 1
        mismatches[category] += 1
        if len(examples) < max_examples:
            examples.append({"category": category, "timestamp_ns": ts, "fields": fields})
            private_examples.append([category, ts, *["" if lrow is None else v for v in
                (lrow if lrow is not None else (None,) * 5)],
                *["" if rrow is None else v for v in (rrow if rrow is not None else (None,) * 5)]])
    with discrepancy_path.open("x", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["category", "timestamp_ns", *[f"local_{x}" for x in HEADER],
                         *[f"reference_{x}" for x in HEADER]])
        writer.writerows(private_examples)
    result["comparison"] = {"common_timestamps": common, "equal_rows": equal,
        "mismatch_counts": dict(mismatches), "first_discrepancies": examples,
        "example_limit": max_examples}
    checks["nonempty_common_grid"] = common > 0
    checks["all_sampled_bbo_rows_match"] = not mismatches and equal > 0
    for name, passed in checks.items():
        if passed is not True:
            errors.append(f"check failed: {name}")
    result["passed"] = not errors and all(value is True for value in checks.values())
    return result


def run_tool(command, folder, label, timeout):
    started = time.monotonic()
    result = {"command": command, "exit_code": None, "error": None}
    stdout_path, stderr_path = folder / f"{label}.stdout.txt", folder / f"{label}.stderr.txt"
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=timeout, check=False)
            result["exit_code"] = process.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = type(exc).__name__
    result["elapsed_seconds"] = round(time.monotonic() - started, 6)
    for label, path in (("stdout", stdout_path), ("stderr", stderr_path)):
        if path.exists():
            result[label] = sha256_file(path)
    result["passed"] = (result["exit_code"] == 0 and result["error"] is None and
                        result.get("stderr", {}).get("bytes") == 0)
    return result


def is_inside(path, parent):
    return path == parent or parent in path.parents


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("local-tool", "reference-tool", "archive", "raw-input", "reference-source", "output", "report"):
        parser.add_argument(f"--{flag}", type=Path, required=True)
    parser.add_argument("--symbol", action="append", required=True)
    parser.add_argument("--interval-ms", type=int, default=1000,
                        help="positive integer snapshot interval in milliseconds (default: 1000)")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--max-examples", type=int, default=10)
    args = parser.parse_args(argv)
    args.output, args.report = args.output.resolve(), args.report.resolve()
    if args.output.exists() or args.report.exists():
        parser.error("output directory and report must both be new; previous evidence is preserved")
    if is_inside(args.report, args.output):
        parser.error("aggregate report must be separate from the private work directory")
    if args.timeout_seconds <= 0 or not 0 <= args.max_examples <= 100 or not 1 <= args.interval_ms <= 86_400_000:
        parser.error("timeout and interval must be positive; interval <= one day and max-examples <= 100")
    interval_ns = args.interval_ms * 1_000_000
    if len(set(args.symbol)) != len(args.symbol) or any(
            re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,7}", symbol) is None for symbol in args.symbol):
        parser.error("symbols must be distinct, upper-case, safe ITCH identifiers of one to eight characters")
    repository = Path(__file__).resolve().parent.parent
    if is_inside(args.output, repository):
        ignored = subprocess.run(["git", "-C", str(repository), "check-ignore", "-q", str(args.output)],
                                 capture_output=True, check=False)
        if ignored.returncode != 0:
            parser.error("private work directory inside the repository must be ignored by Git (use out/)")
    report = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": SCOPE, "clock_semantics": CLOCK, "interval_ns": interval_ns,
        "passed": False, "checks": {}, "errors": [], "symbols": [],
        "reference_source": {"repository": REFERENCE_REPOSITORY, "commit": REFERENCE_COMMIT,
            "limitations": "Pinned replay entry point and build definition are checked by SHA-256; "
                "binary hashes identify the actual executables. The report does not attest the compiler "
                "or prove every dependency was built from the stated source."}}
    tracked = {}
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        runner = Path(__file__).resolve()
        tracked["comparison_runner"] = (runner, stat_identity(runner))
        report["comparison_runner"] = file_identity(runner)
        # Resolve once: every hashed and subsequently consumed path must refer
        # to the same target even if an input symlink is later retargeted.
        for attribute in ("archive", "raw_input", "local_tool", "reference_tool", "reference_source"):
            setattr(args, attribute, getattr(args, attribute).resolve(strict=True))
        for label, path in (("archive", args.archive), ("raw_input", args.raw_input),
                            ("local_tool", args.local_tool), ("reference_tool", args.reference_tool)):
            path = path.resolve(strict=True)
            if not path.is_file():
                raise ValueError(f"{label} is not a regular file")
            if label.endswith("tool") and not os.access(path, os.X_OK):
                raise ValueError(f"{label} is not executable")
            tracked[label] = (path, stat_identity(path))
            report[label] = file_identity(path)
        report["reference_source"]["files"] = {}
        for relative, expected in PINNED_SOURCES.items():
            path = args.reference_source / relative
            identity = file_identity(path)
            report["reference_source"]["files"][relative] = identity
            if identity["sha256"] != expected:
                raise ValueError(f"reference source does not match pinned commit: {relative}")
            tracked[f"source:{relative}"] = (path, stat_identity(path))
        report["checks"]["reference_entry_point_and_build_definition_pinned"] = True
        report["archive_raw_identity"] = sha256_file(args.archive, gzip.open)
        report["checks"]["identical_decompressed_input"] = (
            report["archive_raw_identity"] == {key: report["raw_input"][key] for key in ("bytes", "sha256")} and
            report["archive_raw_identity"]["bytes"] > 0)
        if not report["checks"]["identical_decompressed_input"]:
            raise ValueError("archive decompression does not match the raw input by byte count and SHA-256")
        for symbol in args.symbol:
            print(f"Comparing {symbol}: {args.interval_ms} ms grid; starting both full-input replays", flush=True)
            folder = args.output / symbol
            folder.mkdir()
            local_csv, reference_csv = folder / "local.csv", folder / "reference.csv"
            local_summary, reference_summary = folder / "local.json", folder / "reference.json"
            local_run = run_tool([str(args.local_tool.resolve()), "--strict", "--symbol", symbol,
                "--interval-ms", str(args.interval_ms), "--out", str(local_csv), "--summary", str(local_summary),
                str(args.raw_input.resolve())], folder, "local", args.timeout_seconds)
            reference_run = run_tool([str(args.reference_tool.resolve()), str(args.archive.resolve()),
                "--symbol", symbol, "--snapshots", str(reference_csv), "--interval-ms", str(args.interval_ms),
                "--levels", "1", "--json", str(reference_summary)], folder, "reference", args.timeout_seconds)
            item = compare_outputs(local_csv, reference_csv, local_summary, reference_summary,
                symbol, report["raw_input"]["bytes"], folder / "first_discrepancies.csv", args.max_examples, interval_ns)
            item["runs"] = {"local": local_run, "reference": reference_run}
            for label, run in item["runs"].items():
                item["checks"][f"{label}_tool_succeeded_without_stderr"] = run["passed"]
                if not run["passed"]:
                    item["errors"].append(f"{label}: subprocess failed or wrote to stderr; inspect private logs")
            for label, path in (("local", local_summary), ("reference", reference_summary)):
                if path.is_file():
                    item.setdefault("summary_files", {})[label] = sha256_file(path)
            item["passed"] = not item["errors"] and all(value is True for value in item["checks"].values())
            report["symbols"].append(item)
            mismatches = item["comparison"]["mismatch_counts"]
            differing_rows = sum(mismatches.get(name, 0) for name in
                ("quote_mismatch", "missing_local_timestamp", "extra_local_timestamp"))
            print(f"{'PASS' if item['passed'] else 'FAIL'} {symbol}: "
                  f"{item['snapshots']['local']['rows']} local rows; "
                  f"{item['snapshots']['reference']['rows']} reference rows; "
                  f"{differing_rows} differing rows", flush=True)
        report["checks"]["all_requested_symbols_compared"] = len(report["symbols"]) == len(args.symbol)
        report["checks"]["all_symbol_comparisons_passed"] = all(item["passed"] for item in report["symbols"])
    except (OSError, EOFError, ValueError, zlib.error, subprocess.SubprocessError) as exc:
        # No raw data contents are included in these high-level exceptions.
        report["errors"].append(f"comparison aborted: {exc}")
    finally:
        report["checks"]["inputs_tools_and_pinned_sources_unchanged"] = bool(tracked)
        for label, (path, before) in tracked.items():
            try:
                if stat_identity(path) != before:
                    report["checks"]["inputs_tools_and_pinned_sources_unchanged"] = False
                    report["errors"].append(f"identified file changed during the run: {label}")
            except OSError:
                report["checks"]["inputs_tools_and_pinned_sources_unchanged"] = False
                report["errors"].append(f"identified file disappeared during the run: {label}")
    for name, passed in report["checks"].items():
        if passed is not True:
            report["errors"].append(f"check failed: {name}")
    report["passed"] = (not report["errors"] and bool(report["symbols"]) and
                        all(value is True for value in report["checks"].values()))
    with args.report.open("x") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{'PASS' if report['passed'] else 'FAIL'}: {args.report}")
    print(SCOPE)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
