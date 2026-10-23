#!/usr/bin/env python3
"""Compare a full-day validation report with a pinned independent census.

Only aggregate evidence is read or written. Census equality does not independently
validate prices, the reconstructed BBO, order priority, or full depth of book.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


# TotalView-ITCH 5.0 types understood by include/itch/messages.hpp. Omitted known
# types mean zero; unexpected types are always reported and rejected, even at zero.
KNOWN_TYPES = tuple(sorted("SRHYLVWKJhAFECXDUPQ BINO".replace(" ", "")))
REQUIRED_CHECKS = {
    "tools_succeeded", "same_raw_input", "same_message_count", "census_byte_identity",
    "no_trailing_bytes", "system_C_seen", "book_empty_at_end", "no_replay_anomalies",
}
SCOPE = ("Independent aggregate census comparison only; this does not independently "
         "validate prices, BBO, full depth of book, queue priority, or execution semantics.")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"invalid JSON numeric constant: {value}")


def read_document(path, label, evidence):
    identity = {"path": str(path.resolve()), "sha256": None}
    try:
        data = path.read_bytes()
        identity["sha256"] = hashlib.sha256(data).hexdigest()
        document = json.loads(data, object_pairs_hook=unique_object,
                              parse_constant=reject_constant)
        if not isinstance(document, dict):
            raise ValueError("root must be a JSON object")
        return document, identity
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        evidence["errors"].append(f"{label}: {exc}")
        return None, identity


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def digest(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_census(document, label, evidence, reference=False):
    """Check types before equality: Python treats True == 1, JSON must not."""
    problems = []
    if type(document.get("schema_version")) is not int or document["schema_version"] != 1:
        problems.append("schema_version must be integer 1")
    summary = document if reference else document.get("summary")
    if not isinstance(summary, dict):
        problems.append("summary must be an object")
        summary = {}
    for name in ("messages", "raw_bytes"):
        if not integer(summary.get(name), 1):
            problems.append(f"{name} must be a positive integer")
    counts = summary.get("message_counts")
    if not isinstance(counts, dict):
        problems.append("message_counts must be an object")
    else:
        for kind, count in counts.items():
            if len(kind) != 1 or not 33 <= ord(kind) <= 126:
                problems.append(f"message_counts key {kind!r} must be one printable ASCII character")
            if not integer(count):
                problems.append(f"message_counts[{kind!r}] must be a nonnegative integer")
    if reference:
        name = document.get("archive_name")
        if not isinstance(name, str) or not name or Path(name).name != name:
            problems.append("archive_name must be a nonempty archive basename")
        for name in ("raw_sha256", "archive_sha256"):
            if name in document and not digest(document[name]):
                problems.append(f"{name} must be a lowercase SHA-256 digest")
        if "compressed_bytes" in document and not integer(document["compressed_bytes"], 1):
            problems.append("compressed_bytes must be a positive integer")
        if "live_orders" in document:
            orders = document["live_orders"]
            if not isinstance(orders, dict):
                problems.append("live_orders must be an object")
            else:
                for name in ("peak", "final"):
                    if name in orders and not integer(orders[name]):
                        problems.append(f"live_orders.{name} must be a nonnegative integer")
        source = document.get("source")
        if not isinstance(source, dict):
            problems.append("source must be an object with pinned provenance")
        else:
            for name in ("repository", "commit", "path", "url"):
                if not isinstance(source.get(name), str) or not source[name].strip():
                    problems.append(f"source.{name} must be a nonempty string")
            if not re.fullmatch(r"[0-9a-f]{40}", str(source.get("commit", ""))):
                problems.append("source.commit must pin a full lowercase 40-character Git commit")
            limitations = source.get("provenance_limitations")
            if not ((isinstance(limitations, str) and limitations.strip()) or
                    (isinstance(limitations, list) and limitations and
                     all(isinstance(item, str) and item.strip() for item in limitations))):
                problems.append("source.provenance_limitations must describe the reference limitations")
    else:
        archive = document.get("archive")
        if not isinstance(archive, dict):
            problems.append("archive must be an object")
            archive = {}
        if not isinstance(archive.get("name"), str) or not archive["name"]:
            problems.append("archive.name must be a nonempty string")
        if not integer(archive.get("bytes"), 1):
            problems.append("archive.bytes must be a positive integer")
        if not digest(archive.get("sha256")):
            problems.append("archive.sha256 must be a lowercase SHA-256 digest")
        if not digest(summary.get("raw_sha256")):
            problems.append("summary.raw_sha256 must be a lowercase SHA-256 digest")
        if not integer(summary.get("live_orders_at_end")):
            problems.append("summary.live_orders_at_end must be a nonnegative integer")
        if not integer(summary.get("peak_orders")):
            problems.append("summary.peak_orders must be a nonnegative integer")
        if type(document.get("passed")) is not bool:
            problems.append("passed must be a JSON boolean")
        checks = document.get("checks")
        if not isinstance(checks, dict):
            problems.append("checks must be an object")
        else:
            missing = sorted(REQUIRED_CHECKS - checks.keys())
            if missing:
                problems.append(f"missing required full-day checks: {', '.join(missing)}")
            for name, value in checks.items():
                if type(value) is not bool:
                    problems.append(f"checks.{name} must be a JSON boolean")
        runs = document.get("runs")
        if not isinstance(runs, dict):
            problems.append("runs must be an object")
            runs = {}
        for name in ("itch_census", "itch_replay"):
            run = runs.get(name)
            if not isinstance(run, dict):
                problems.append(f"runs.{name} must be an object")
                continue
            if type(run.get("exit_code")) is not int:
                problems.append(f"runs.{name}.exit_code must be an integer")
            if "error" not in run or not (run["error"] is None or isinstance(run["error"], str)):
                problems.append(f"runs.{name}.error must be null or an error string")
            if not integer(run.get("raw_bytes"), 1):
                problems.append(f"runs.{name}.raw_bytes must be a positive integer")
            if not digest(run.get("raw_sha256")):
                problems.append(f"runs.{name}.raw_sha256 must be a lowercase SHA-256 digest")
    evidence["errors"].extend(f"{label}: {problem}" for problem in problems)
    return not problems


def compare(local, reference, evidence):
    checks = evidence["checks"]
    if reference is not None and isinstance(reference.get("source"), dict):
        evidence["reference"]["source"] = reference["source"]
    checks["validation_schema_valid"] = (local is not None and
        validate_census(local, "validation", evidence))
    checks["reference_schema_valid"] = (reference is not None and
        validate_census(reference, "reference", evidence, reference=True))
    if not all(checks.values()):
        return
    summary = local["summary"]
    evidence["validation_checks"] = local["checks"]
    checks["full_day_validation_passed"] = local["passed"] is True
    checks["all_validation_checks_passed"] = all(value is True for value in local["checks"].values())
    runs = list(local["runs"][name] for name in ("itch_census", "itch_replay"))
    checks["local_tools_succeeded"] = all(run["exit_code"] == 0 and run["error"] is None for run in runs)
    checks["local_raw_input_consistent"] = all(
        run["raw_bytes"] == summary["raw_bytes"] and run["raw_sha256"] == summary["raw_sha256"]
        for run in runs)
    checks["local_book_empty_at_end"] = summary["live_orders_at_end"] == 0
    fields = [("archive_name", Path(local["archive"]["name"]).name, reference["archive_name"]),
              ("raw_bytes", summary["raw_bytes"], reference["raw_bytes"]),
              ("messages", summary["messages"], reference["messages"])]
    if "compressed_bytes" in reference:
        fields.append(("compressed_bytes", local["archive"]["bytes"], reference["compressed_bytes"]))
    for name, local_name in (("peak", "peak_orders"), ("final", "live_orders_at_end")):
        if name in reference.get("live_orders", {}):
            fields.append((f"live_orders_{name}", summary[local_name], reference["live_orders"][name]))
    for name in ("raw_sha256", "archive_sha256"):
        if name in reference:
            actual = summary["raw_sha256"] if name == "raw_sha256" else local["archive"]["sha256"]
            fields.append((name, actual, reference[name]))
    evidence["comparisons"] = {}
    for name, actual, expected in fields:
        matched = actual == expected
        checks[f"{name}_matches"] = matched
        evidence["comparisons"][name] = {"local": actual, "reference": expected, "matched": matched}
    local_counts, ref_counts = summary["message_counts"], reference["message_counts"]
    checks["local_message_total_consistent"] = sum(local_counts.values()) == summary["messages"]
    checks["reference_message_total_consistent"] = sum(ref_counts.values()) == reference["messages"]
    unexpected = sorted((local_counts.keys() | ref_counts.keys()) - set(KNOWN_TYPES))
    evidence["unexpected_message_types"] = unexpected
    checks["no_unexpected_message_types"] = not unexpected
    evidence["message_counts"] = {
        kind: {"local": local_counts.get(kind, 0), "reference": ref_counts.get(kind, 0),
               "difference": local_counts.get(kind, 0) - ref_counts.get(kind, 0),
               "matched": local_counts.get(kind, 0) == ref_counts.get(kind, 0)}
        for kind in sorted(set(KNOWN_TYPES) | local_counts.keys() | ref_counts.keys())}
    checks["message_type_counts_match"] = all(item["matched"] for item in evidence["message_counts"].values())
    external_digests = [name for name in ("raw_sha256", "archive_sha256") if name in reference]
    evidence["identity_verified"] = bool(external_digests) and all(
        checks[f"{name}_matches"] for name in external_digests) and checks["local_raw_input_consistent"]
    evidence["identity_basis"] = external_digests
    evidence["comparison_strength"] = ("identity_verified" if evidence["identity_verified"] else
        "identity_mismatch" if external_digests else "filename_counts_bytes_only")
    for name, passed in checks.items():
        if not passed:
            evidence["errors"].append(f"check failed: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("validation", type=Path, help="validation.json produced by bench/validate.py")
    parser.add_argument("reference", type=Path, help="pinned independent reference JSON")
    parser.add_argument("--output", type=Path, required=True, help="new comparison JSON file")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output already exists; use a new file to preserve evidence")
    evidence = {"schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                "scope": SCOPE, "checks": {}, "errors": [], "passed": False,
                "identity_verified": False, "identity_basis": [], "comparison_strength": "not_compared"}
    local, evidence["validation"] = read_document(args.validation, "validation", evidence)
    reference, evidence["reference"] = read_document(args.reference, "reference", evidence)
    compare(local, reference, evidence)
    evidence["passed"] = not evidence["errors"] and all(value is True for value in evidence["checks"].values())
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as output:
            json.dump(evidence, output, indent=2)
            output.write("\n")
    except OSError as exc:
        parser.error(f"cannot create new comparison output: {exc}")
    print(f"{'PASS' if evidence['passed'] else 'FAIL'}: {args.output}")
    print(SCOPE)
    for error in evidence["errors"]:
        print(f"  {error}", file=sys.stderr)
    return 0 if evidence["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
