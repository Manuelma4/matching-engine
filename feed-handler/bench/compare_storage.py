#!/usr/bin/env python3
"""Compare two concrete reference indexes after complete replay equivalence.

Correctness, streaming-memory and prefaulted-input timing passes use separate
processes. All child processes run sequentially. Checkpoint rows stay private;
the aggregate report retains identities, checks, execution order and measurements.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ORDERS = 1 << 22
DEFAULT_LEVELS = 1 << 21
VARIANTS = ("open_addressed", "std_unordered")
PAIR_ORDER = (VARIANTS, VARIANTS[::-1], VARIANTS[::-1], VARIANTS)
ANOMALIES = ("after_end", "unknown_type", "bad_length", "unknown_ref", "duplicate_ref",
             "share_underflow", "capacity", "invalid_side", "locate_mismatch", "trailing_bytes")
COUNTERS = ("messages", "records", "input_bytes", "consumed_bytes", "end_records", "peak_orders",
            "final_orders", "adds", "executions", "executed_shares", "non_printable_shares",
            "trade_shares", "cross_shares", "broken_trades", *ANOMALIES)
CHECKPOINT_HEADER = ("sequence", "source_offset", "timestamp_ns", "live_orders", "book_hash", "state_hash")
HEX16 = re.compile(r"[0-9a-f]{16}\Z")
UINT_TEXT = re.compile(r"(?:0|[1-9][0-9]*)\Z")
STAGES = ("construction_seconds", "replay_seconds", "teardown_seconds")
RSS_FIELDS = ("baseline_peak_rss_bytes", "post_construct_peak_rss_bytes", "process_peak_rss_bytes")
SOURCE_SUFFIXES = {".hpp", ".h", ".cpp", ".c", ".py", ".cmake"}


def uint(value, minimum=0, maximum=(1 << 64) - 1):
    return type(value) is int and minimum <= value <= maximum


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def stat_identity(path):
    info = path.stat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def strict_json(data):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    def invalid(_):
        raise ValueError("non-finite JSON numeric constant")

    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("JSON numeric exponent exceeds the finite floating-point range")
        return number
    document = json.loads(data, object_pairs_hook=unique, parse_constant=invalid, parse_float=finite_float)
    if not isinstance(document, dict):
        raise ValueError("JSON root must be an object")
    return document


def git(directory, *arguments):
    result = subprocess.run(["git", "-C", str(directory), *arguments], capture_output=True)
    return result.stdout.decode("utf-8") if result.returncode == 0 else None


def source_snapshot(directory):
    directory = directory.resolve(strict=True)
    listed = git(directory, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if listed is None:
        paths = [path.relative_to(directory).as_posix() for path in directory.rglob("*")
            if path.is_file() and not any(part in {".git", "data", "out", "__pycache__"} or
                part.startswith("build") for part in path.relative_to(directory).parts)]
    else:
        paths = [name for name in listed.split("\0") if name]
    files = {name: sha256(directory / name) for name in sorted(paths)
        if ((Path(name).name == "CMakeLists.txt" or Path(name).suffix in SOURCE_SUFFIXES)
            and (directory / name).is_file())}
    if not files:
        raise ValueError("source provenance directory contains no implementation files")
    status = git(directory, "status", "--porcelain")
    commit = git(directory, "rev-parse", "HEAD")
    return {"path": str(directory), "git_commit": commit.strip() if commit else None,
            "git_dirty": bool(status) if status is not None else None, "file_sha256": files}


def read_cache(directory, variant):
    path = next((path for path in (directory / "CMakeCache.txt", directory.parent / "CMakeCache.txt")
                 if path.is_file()), None)
    if path is None:
        raise ValueError("Release CMakeCache.txt is required for both performance builds")
    values = {}
    for line in path.read_text().splitlines():
        if line and not line.startswith(("#", "//")) and ":" in line and "=" in line:
            key, value = line.split("=", 1)
            values[key.split(":", 1)[0]] = value
    if values.get("ITCH_REFERENCE_INDEX") != variant:
        raise ValueError("build cache does not identify the requested reference-index variant")
    if values.get("CMAKE_BUILD_TYPE") != "Release" or values.get("ITCH_SANITIZE", "OFF").upper() not in {"OFF", "FALSE", "0"}:
        raise ValueError("performance evidence requires Release builds without sanitizers")
    if not values.get("CMAKE_CXX_COMPILER") or "CMAKE_CXX_FLAGS_RELEASE" not in values:
        raise ValueError("compiler and Release flag metadata are required")
    flags_path = path.parent / "CMakeFiles" / "itch.dir" / "flags.make"
    flags_text = flags_path.read_text()
    definitions = next((line.split("=", 1)[1].strip() for line in flags_text.splitlines()
                        if line.startswith("CXX_DEFINES =")), None)
    flags = next((line.split("=", 1)[1].strip() for line in flags_text.splitlines()
                 if line.startswith("CXX_FLAGS =")), None)
    expected_definition = f"-DITCH_STD_REFERENCE_INDEX={int(variant == 'std_unordered')}"
    if definitions is None or flags is None or expected_definition not in definitions.split():
        raise ValueError("generated compiler definitions do not select the requested index")
    if any("-fsanitize" in text.lower() for text in
            (flags_text, values.get("CMAKE_CXX_FLAGS", ""), values.get("CMAKE_CXX_FLAGS_RELEASE", ""))):
        raise ValueError("sanitizer compiler flags cannot produce performance evidence")
    return {"path": str(path.resolve()), "sha256": sha256(path), "values": {
        key: values.get(key) for key in ("ITCH_REFERENCE_INDEX", "CMAKE_BUILD_TYPE", "CMAKE_CXX_COMPILER",
        "CMAKE_CXX_FLAGS", "CMAKE_CXX_FLAGS_RELEASE", "CMAKE_CXX_FLAGS_RELWITHDEBINFO",
        "CMAKE_GENERATOR", "CMAKE_OSX_ARCHITECTURES", "ITCH_SANITIZE")},
        "generated_flags": {"path": str(flags_path.resolve()), "sha256": sha256(flags_path),
                            "definitions": definitions, "flags": flags},
        "compile_commands": ({"path": str((path.parent / "compile_commands.json").resolve()),
            "sha256": sha256(path.parent / "compile_commands.json")}
            if (path.parent / "compile_commands.json").is_file() else None)}, values


def semantic(summary, source_bytes, variant, max_orders, max_levels):
    for key in ("schema_version", "fingerprint_version", *COUNTERS):
        if not uint(summary.get(key)):
            raise ValueError(f"missing or invalid unsigned summary field: {key}")
    if summary["schema_version"] != 1 or summary["fingerprint_version"] != 1:
        raise ValueError("unsupported summary or fingerprint version")
    if summary.get("reference_index") != variant:
        raise ValueError("tool reference_index does not identify the requested variant")
    for key, expected in (("max_orders", max_orders), ("max_levels", max_levels)):
        if not uint(summary.get(key), 1, 0xffffffff) or summary[key] != expected:
            raise ValueError(f"tool did not use the requested {key}")
    if (summary.get("passed") is not True or summary.get("end_of_messages") is not True or
            summary["messages"] == 0 or summary["records"] != summary["messages"] + summary["end_records"] or
            summary["end_records"] > 1 or summary["input_bytes"] != source_bytes or
            summary["consumed_bytes"] != source_bytes or summary["final_orders"] != 0 or
            not 0 < summary["peak_orders"] <= max_orders):
        raise ValueError("tool did not complete the identified full day with valid order counts")
    if any(summary[key] != 0 for key in ANOMALIES):
        raise ValueError("nonzero replay anomaly")
    for key in ("book_hash", "state_hash"):
        if not isinstance(summary.get(key), str) or HEX16.fullmatch(summary[key]) is None:
            raise ValueError("missing or malformed state fingerprint")
    return {key: summary[key] for key in ("schema_version", "fingerprint_version", *COUNTERS,
                                         "book_hash", "state_hash", "end_of_messages", "passed")}


def checkpoints(path, summary, every):
    rows = nonempty = max_live = 0
    previous_offset = 0
    last = None
    with path.open(newline="", encoding="ascii") as stream:
        reader = csv.reader(stream, strict=True)
        if tuple(next(reader, ())) != CHECKPOINT_HEADER:
            raise ValueError("unexpected checkpoint CSV header")
        for rows, row in enumerate(reader, 1):
            if len(row) != len(CHECKPOINT_HEADER) or any(UINT_TEXT.fullmatch(cell) is None for cell in row[:4]):
                raise ValueError("malformed checkpoint row")
            sequence, offset, timestamp, live = map(int, row[:4])
            if (sequence != min(rows * every, summary["messages"]) or
                    not previous_offset < offset <= summary["input_bytes"] or
                    not 0 <= timestamp < (1 << 48) or not 0 <= live <= summary["peak_orders"] or
                    any(HEX16.fullmatch(value) is None for value in row[4:])):
                raise ValueError("invalid checkpoint sequence, source extent or state")
            previous_offset = offset
            nonempty += live > 0
            max_live = max(max_live, live)
            last = row
    if (rows != (summary["messages"] + every - 1) // every or not last or not nonempty or
            previous_offset != summary["input_bytes"] - 2 * summary["end_records"] or
            int(last[3]) != summary["final_orders"] or last[4] != summary["book_hash"] or
            last[5] != summary["state_hash"]):
        raise ValueError("checkpoints lack populated intermediate or complete terminal coverage")
    if not uint(summary.get("checkpoints"), 1) or summary["checkpoints"] != rows:
        raise ValueError("checkpoint count differs from tool summary")
    return {"rows": rows, "nonempty_book_rows": nonempty, "maximum_sampled_live_orders": max_live,
            "last_source_offset": previous_offset, "bytes": path.stat().st_size, "sha256": sha256(path)}


def validate_benchmark(summary, mode, wall_seconds=None):
    if summary.get("mode") != mode or any(summary.get(key) is not True for key in
            ("preflight_passed", "replay_performed")):
        raise ValueError("benchmark mode or preflight/replay checks are invalid")
    for field in STAGES:
        value = summary.get(field)
        try:
            valid = type(value) in (float, int) and math.isfinite(float(value)) and value > 0
        except OverflowError:
            valid = False
        if not valid:
            raise ValueError(f"invalid finite positive duration: {field}")
    stage_total = sum(float(summary[field]) for field in STAGES)
    if not math.isfinite(stage_total) or (wall_seconds is not None and stage_total > wall_seconds + 0.05):
        raise ValueError("reported stage durations exceed the child process wall time")
    if any(not uint(summary.get(field), 1) for field in RSS_FIELDS):
        raise ValueError("missing or invalid process peak RSS fields")
    if not summary[RSS_FIELDS[0]] <= summary[RSS_FIELDS[1]] <= summary[RSS_FIELDS[2]]:
        raise ValueError("process RSS high-water marks are not monotonic")
    if any(not isinstance(summary.get(key), str) or not summary[key].strip() for key in ("rss_scope", "timing_scope")):
        raise ValueError("benchmark must disclose RSS and timing scopes")


def run(command, output, label, execution, timeout):
    execution.update(command=[str(arg) for arg in command], passed=False)
    stdout_path, stderr_path = output / f"{label}.json", output / f"{label}.stderr"
    started = time.monotonic()
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.run([str(arg) for arg in command], stdout=stdout, stderr=stderr,
                                     timeout=timeout, check=False)
        execution["exit_code"] = process.returncode
        for key, path in (("stdout", stdout_path), ("stderr", stderr_path)):
            execution[key] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        if process.returncode != 0 or stderr_path.stat().st_size != 0:
            raise ValueError("subprocess failed or produced diagnostics; inspect private logs")
        summary = strict_json(stdout_path.read_bytes())
        if summary.get("passed") is not True:
            raise ValueError("subprocess summary does not report boolean success")
        execution["passed"] = True
        return summary
    finally:
        execution["wall_seconds"] = round(time.monotonic() - started, 6)


def distribution(values):
    ordered = sorted(map(float, values))
    # Positive durations permit this overflow-safe midpoint. (a + b) / 2 can
    # overflow for two finite values; a + (b - a) / 2 stays between a and b.
    lower, upper = ordered[(len(ordered) - 1) // 2], ordered[len(ordered) // 2]
    median = lower + (upper - lower) / 2
    if not all(math.isfinite(value) and value > 0 for value in (*ordered, median)):
        raise ValueError("non-finite or nonpositive timing distribution")
    return {"count": len(ordered), "median": median, "minimum": ordered[0], "maximum": ordered[-1]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--open-dir", type=Path, required=True)
    parser.add_argument("--std-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", nargs=3, required=True, metavar=("NAME", "RAW_PATH", "FIT_ORDER_CAP"))
    parser.add_argument("--runs", type=int, default=6)
    parser.add_argument("--checkpoint-every", type=int, default=10_000_000)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    if args.runs < 5 or not 0 < args.checkpoint_every < (1 << 64) or args.timeout_seconds <= 0:
        parser.error("at least five runs, positive uint64 checkpoint spacing and positive timeout required")
    names = [case[0] for case in args.case]
    if len(set(names)) != len(names) or any(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", name) is None for name in names):
        parser.error("case names must be distinct safe identifiers")
    try:
        cases = [{"name": name, "path": Path(path).resolve(), "fit_orders": int(cap)} for name, path, cap in args.case]
    except ValueError:
        parser.error("fit order capacities must be integers")
    if any(not 0 < case["fit_orders"] < DEFAULT_ORDERS for case in cases):
        parser.error("fit order capacity must be positive and smaller than the default")
    output = args.output.resolve()
    report_path = args.report.resolve() if args.report else output / "evidence.json"
    if output.exists() or report_path.exists():
        parser.error("private output directory and aggregate report must both be fresh")
    if ROOT in output.parents:
        ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "-q", str(output)], capture_output=True)
        if ignored.returncode != 0:
            parser.error("private output inside the repository must be ignored by Git (use out/)")
    output.mkdir(parents=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    evidence = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "passed": False, "errors": [], "checks": {}, "inputs": [], "tools": {}, "source": {},
        "correctness": [], "memory": [], "timings": [], "execution_order": [], "statistics": [],
        "protocol": {"runs": args.runs, "checkpoint_every": args.checkpoint_every,
            "variant_pair_order_by_round": [list(PAIR_ORDER[index % 4]) for index in range(args.runs)],
            "group_order": "rotate case/profile pairs by round index", "fresh_process_per_run": True,
            "concurrent_children": 1, "correctness_scope": "complete raw replay and sampled populated FIFO/state checkpoints",
            "timing_scope": "separate construction, prefaulted mapped-input replay and teardown; state walks outside timers",
            "memory_scope": "separate streaming pass; total process RSS high-water marks, not isolated index memory",
            "comparison_scope": "concrete OpenAddrIndex versus StdIndex including hash functions, bucket policies and allocation",
            "limitations": "No allocation-only attribution, latency distribution, cold-cache claim or index-only RSS claim."},
        "environment": {"platform": platform.platform(), "python": platform.python_version()}}
    tracked = {}
    snapshots = {}

    def track(path, label):
        path = path.resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"{label} must be a regular file")
        before = stat_identity(path)
        entry = {"path": str(path), "bytes": before[2], "sha256": sha256(path)}
        if stat_identity(path) != before:
            raise ValueError(f"{label} changed while its identity was being recorded")
        tracked[label] = (path, before, entry["sha256"])
        return entry

    def execute(phase, case, profile, variant, command, round_index=None):
        label = f"{len(evidence['execution_order']):04d}-{phase}-{case['name']}-{profile}-{variant}"
        entry = {"index": len(evidence["execution_order"]), "phase": phase, "case": case["name"],
                 "profile": profile, "reference_index": variant, "round": round_index}
        evidence["execution_order"].append(entry)
        print(f"{phase}: {case['name']} {profile} {variant}" +
              (f" round {round_index + 1}/{args.runs}" if round_index is not None else ""), flush=True)
        return run(command, output, label, entry, args.timeout_seconds), label

    try:
        directories = {VARIANTS[0]: args.open_dir.resolve(strict=True), VARIANTS[1]: args.std_dir.resolve(strict=True)}
        binaries, caches, dependency_paths = {}, {}, {}
        for variant, directory in directories.items():
            binaries[variant] = {}
            evidence["tools"][variant] = {}
            for role in ("itch_journal_replay", "itch_storage_bench"):
                path = (directory / role).resolve(strict=True)
                if not os.access(path, os.X_OK):
                    raise ValueError("comparison tool is not executable")
                binaries[variant][role] = path
                evidence["tools"][variant][role] = track(path, f"{variant}:{role}")
            cache, values = read_cache(directory, variant)
            caches[variant] = cache
            if cache:
                track(Path(cache["path"]), f"{variant}:build_cache")
                track(Path(cache["generated_flags"]["path"]), f"{variant}:generated_flags")
                if cache["compile_commands"]:
                    track(Path(cache["compile_commands"]["path"]), f"{variant}:compile_commands")
            dependency = (values or {}).get("FETCHCONTENT_SOURCE_DIR_MATCHING_ENGINE") or (
                values or {}).get("matching_engine_SOURCE_DIR")
            dependency_paths[variant] = Path(dependency).resolve() if dependency else ROOT.parent / "matching-engine"
        for role in ("itch_journal_replay", "itch_storage_bench"):
            if evidence["tools"][VARIANTS[0]][role]["sha256"] == evidence["tools"][VARIANTS[1]][role]["sha256"]:
                raise ValueError("the two index variants must not resolve to the same executable bytes")
        if bool(caches[VARIANTS[0]]) != bool(caches[VARIANTS[1]]):
            raise ValueError("build metadata is available for only one variant")
        if all(caches.values()):
            comparable = [{key: value for key, value in caches[variant]["values"].items()
                           if key != "ITCH_REFERENCE_INDEX"} for variant in VARIANTS]
            generated_flags = [caches[variant]["generated_flags"]["flags"] for variant in VARIANTS]
            definitions = [re.sub(r"(?:^| )-DITCH_STD_REFERENCE_INDEX=[01](?= |$)", "",
                caches[variant]["generated_flags"]["definitions"]).strip() for variant in VARIANTS]
            if comparable[0] != comparable[1] or generated_flags[0] != generated_flags[1] or definitions[0] != definitions[1]:
                raise ValueError("compiler, build type or flags differ between index builds")
        evidence["build_caches"] = caches
        for label, path in (("itch", ROOT), *[(f"engine:{variant}", path) for variant, path in dependency_paths.items()]):
            snapshots[label] = source_snapshot(path)
        if snapshots["engine:open_addressed"]["file_sha256"] != snapshots["engine:std_unordered"]["file_sha256"]:
            raise ValueError("matching-engine implementation differs between the compared builds")
        evidence["source"] = snapshots.copy()
        for case in cases:
            case["identity"] = track(case["path"], f"input:{case['name']}")
            if case["identity"]["bytes"] == 0:
                raise ValueError("input contains no observed bytes")
            evidence["inputs"].append({"case": case["name"], "fit_orders": case["fit_orders"], **case["identity"]})
        baselines = {}
        groups = [(case, profile, cap, min(cap, DEFAULT_LEVELS)) for case in cases
                  for profile, cap in (("default", DEFAULT_ORDERS), ("fit", case["fit_orders"]))]
        for case, profile, cap, level_cap in groups:
            for variant in VARIANTS:
                checkpoint_path = output / f"correctness-{case['name']}-{profile}-{variant}.csv"
                summary, _ = execute("correctness", case, profile, variant, [binaries[variant]["itch_journal_replay"],
                    "--raw", "--max-orders", cap, "--checkpoint-every", args.checkpoint_every,
                    "--checkpoints", checkpoint_path, case["path"]])
                state = semantic(summary, case["identity"]["bytes"], variant, cap, level_cap)
                if (summary.get("format") != "raw" or summary.get("source_sha256", "missing") is not None or
                        summary.get("source_identity_verified") is not False or summary.get("allow_partial") is not False or
                        not uint(summary.get("journal_blocks")) or summary["journal_blocks"] != 0 or
                        not uint(summary.get("checkpoint_every"), 1) or summary["checkpoint_every"] != args.checkpoint_every):
                    raise ValueError("unexpected raw correctness replay metadata")
                checkpoint = checkpoints(checkpoint_path, summary, args.checkpoint_every)
                track(checkpoint_path, f"checkpoint:{case['name']}:{profile}:{variant}")
                row = {"case": case["name"], "profile": profile, "reference_index": variant,
                       "max_orders": cap, "max_levels": level_cap, "summary": summary, "checkpoints": checkpoint}
                evidence["correctness"].append(row)
                if case["name"] not in baselines:
                    baselines[case["name"]] = (state, checkpoint["sha256"])
                    if case["fit_orders"] < summary["peak_orders"]:
                        raise ValueError("fit capacity is smaller than the observed full-day peak")
                if (state, checkpoint["sha256"]) != baselines[case["name"]]:
                    raise ValueError("reference-index/capacity configurations differ in semantic state or intermediate checkpoints")
        evidence["checks"]["all_correctness_profiles_equivalent"] = True
        for index, (case, profile, cap, level_cap) in enumerate(groups):
            for variant in PAIR_ORDER[index % 4]:
                summary, _ = execute("memory", case, profile, variant, [binaries[variant]["itch_storage_bench"],
                    "--memory", "--max-orders", cap, "--max-levels", level_cap, case["path"]])
                state = semantic(summary, case["identity"]["bytes"], variant, cap, level_cap)
                validate_benchmark(summary, "memory", evidence["execution_order"][-1]["wall_seconds"])
                if state != baselines[case["name"]][0]:
                    raise ValueError("memory replay semantics differ from correctness baseline")
                evidence["memory"].append({"case": case["name"], "profile": profile, "summary": summary})
        evidence["checks"]["all_memory_passes_equivalent"] = True
        for round_index in range(args.runs):
            rotation = round_index % len(groups)
            for case, profile, cap, level_cap in groups[rotation:] + groups[:rotation]:
                for variant in PAIR_ORDER[round_index % 4]:
                    summary, _ = execute("timing", case, profile, variant, [binaries[variant]["itch_storage_bench"],
                        "--max-orders", cap, "--max-levels", level_cap, case["path"]], round_index)
                    state = semantic(summary, case["identity"]["bytes"], variant, cap, level_cap)
                    validate_benchmark(summary, "timing", evidence["execution_order"][-1]["wall_seconds"])
                    if state != baselines[case["name"]][0]:
                        raise ValueError("timed replay semantics differ from correctness baseline")
                    evidence["timings"].append({"case": case["name"], "profile": profile,
                                               "round": round_index, "summary": summary})
        evidence["checks"]["all_timing_passes_equivalent"] = True
        for case, profile, cap, level_cap in groups:
            for variant in VARIANTS:
                rows = [row["summary"] for row in evidence["timings"] if row["case"] == case["name"] and
                        row["profile"] == profile and row["summary"]["reference_index"] == variant]
                if len(rows) != args.runs:
                    raise ValueError("incomplete fresh-process timing repetitions")
                evidence["statistics"].append({"case": case["name"], "profile": profile,
                    "reference_index": variant, "max_orders": cap, "max_levels": level_cap,
                    **{stage: distribution([row[stage] for row in rows]) for stage in STAGES}})
        evidence["checks"]["all_requested_runs_complete"] = True
    except (OSError, ValueError, RuntimeError, KeyError, UnicodeError, csv.Error, subprocess.SubprocessError) as exc:
        evidence["errors"].append(f"comparison failed: {type(exc).__name__}: {exc}")
    finally:
        unchanged = bool(tracked)
        for label, (path, original, expected_hash) in tracked.items():
            try:
                if stat_identity(path) != original or sha256(path) != expected_hash:
                    unchanged = False
                    evidence["errors"].append(f"identified file changed: {label}")
            except OSError:
                unchanged = False
                evidence["errors"].append(f"identified file disappeared: {label}")
        evidence["checks"]["inputs_binaries_caches_and_checkpoints_unchanged"] = unchanged
        source_unchanged = bool(snapshots)
        for label, snapshot in snapshots.items():
            try:
                if source_snapshot(Path(snapshot["path"]))["file_sha256"] != snapshot["file_sha256"]:
                    source_unchanged = False
                    evidence["errors"].append(f"implementation source changed: {label}")
            except (OSError, ValueError):
                source_unchanged = False
                evidence["errors"].append(f"implementation source disappeared: {label}")
        evidence["checks"]["implementation_sources_unchanged"] = source_unchanged
    evidence["passed"] = (not evidence["errors"] and
        evidence["checks"].get("all_requested_runs_complete") is True and
        all(value is True for value in evidence["checks"].values()))
    with report_path.open("x") as stream:
        json.dump(evidence, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(f"{'PASS' if evidence['passed'] else 'FAIL'}: {report_path}")
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
