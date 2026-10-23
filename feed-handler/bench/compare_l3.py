#!/usr/bin/env python3
"""Compare complete source-identified displayed-order exports in price/FIFO order.

This utility reads four bounded export artefacts. It does not launch producers or
reopen raw market data. Explicit empty states are checked alongside populated ones.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

MAX_STATES = 256
MAX_ORDERS = 1_000_000
MAX_CSV_BYTES = 128 << 20
MAX_JSON_BYTES = 8 << 20
U64 = (1 << 64) - 1
U32 = (1 << 32) - 1
I32 = (1 << 31) - 1
TIME_MAX = (1 << 48) - 1
UINT_TEXT = re.compile(r"(?:0|[1-9][0-9]*)\Z")
SYMBOL = re.compile(r"[A-Z0-9.\-^/]{1,8}\Z")
ORDER_HEADER = ("state_id", "side", "price4", "fifo_rank", "reference", "shares")
SOURCE_KEYS = ("sequence", "frame_offset", "frame_end_offset", "timestamp_ns", "body_bytes", "type")
VALIDATION_KEYS = ("unknown_references", "duplicate_references", "share_underflows", "locate_mismatches",
                   "invalid_messages", "capacity_failures", "timestamp_regressions")
SCOPES = {"full_prefix_all_symbols", "selected_symbols_only"}
LENGTHS = dict(S=12, R=39, H=25, Y=20, L=26, V=35, W=12, K=28, J=35,
               h=21, A=36, F=40, E=31, C=36, X=23, D=19, U=35, P=44,
               Q=40, B=19, I=50, N=20, O=48)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uint(value, minimum=0, maximum=U64):
    return type(value) is int and minimum <= value <= maximum


def strict_json(text):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, "duplicate JSON key")
            value[key] = item
        return value

    def invalid(_):
        raise ValueError("non-finite JSON value")

    def finite(value):
        parsed = float(value)
        require(math.isfinite(parsed), "non-finite JSON number")
        return parsed

    try:
        result = json.loads(text, object_pairs_hook=unique, parse_constant=invalid, parse_float=finite)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds the parser bound") from error
    require(type(result) is dict, "JSON root must be an object")
    return result


def stat_identity(path):
    value = Path(path).stat()
    require(stat.S_ISREG(value.st_mode), "export artefact must be a regular file")
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def file_info(path):
    before = stat_identity(path)
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    require(stat_identity(path) == before, "export artefact changed during hashing")
    return {"bytes": before[2], "sha256": digest.hexdigest()}


def read_summary(path):
    require(stat_identity(path)[2] <= MAX_JSON_BYTES, "summary exceeds the bounded JSON size")
    summary = strict_json(Path(path).read_text(encoding="utf-8"))
    require(set(summary) == {"schema_version", "boundary", "input_bytes", "scanned_messages", "consumed_prefix_bytes",
        "validation_scope", "validation", "states", "passed"}, "summary field set does not match version one")
    require(type(summary.get("schema_version")) is int and summary["schema_version"] == 1 and
            summary.get("boundary") == "post_message" and summary.get("passed") is True,
            "export must report passed post-message schema version one")
    require(type(summary.get("validation_scope")) is str and summary["validation_scope"] in SCOPES, "unsupported validation scope")
    for field in ("input_bytes", "scanned_messages", "consumed_prefix_bytes"):
        require(uint(summary.get(field), 1), "missing or invalid unsigned prefix field: " + field)
    require(summary["consumed_prefix_bytes"] <= summary["input_bytes"], "consumed prefix exceeds full input size")
    validation = summary.get("validation")
    require(type(validation) is dict and set(validation) == set(VALIDATION_KEYS) and all(type(validation.get(key)) is int and validation[key] == 0
        for key in VALIDATION_KEYS), "export has missing, untyped or nonzero validation counters")
    states = summary.get("states")
    require(type(states) is list and 1 <= len(states) <= MAX_STATES, "missing or excessive state coverage")
    symbol_locates, locate_symbols, selected, previous = {}, {}, set(), None
    total_orders = 0
    for index, state in enumerate(states, 1):
        require(type(state) is dict and type(state.get("state_id")) is int and state["state_id"] == index,
                "state ids must be consecutive from one")
        require(set(state) == {"state_id", "symbol", "locate", "source", "bid", "ask", "exported_orders", "complete"},
                "state manifest field set does not match version one")
        symbol, locate = state.get("symbol"), state.get("locate")
        require(type(symbol) is str and SYMBOL.fullmatch(symbol) is not None and uint(locate, 1, 65535),
                "invalid symbol/locate identity")
        require(symbol_locates.get(symbol, locate) == locate and locate_symbols.get(locate, symbol) == symbol,
                "symbol/locate mapping changes between requested states")
        symbol_locates[symbol], locate_symbols[locate] = locate, symbol
        source = state.get("source")
        require(type(source) is dict and set(source) == set(SOURCE_KEYS), "source identity fields are incomplete")
        for key in SOURCE_KEYS[:-1]:
            require(uint(source[key]), "invalid source identity integer")
        require(type(source["type"]) is str and source["type"] in LENGTHS and
                source["body_bytes"] == LENGTHS[source["type"]] and
                1 <= source["sequence"] <= summary["scanned_messages"] and
                source["timestamp_ns"] <= TIME_MAX and
                source["frame_end_offset"] == source["frame_offset"] + source["body_bytes"] + 2 and
                source["frame_end_offset"] <= summary["consumed_prefix_bytes"], "source boundary/type/length disagrees")
        require((symbol, source["sequence"]) not in selected, "duplicate requested symbol/source state")
        selected.add((symbol, source["sequence"]))
        if previous:
            require(source["sequence"] >= previous["sequence"] and source["timestamp_ns"] >= previous["timestamp_ns"],
                    "requested source order decreases")
            require((source == previous) if source["sequence"] == previous["sequence"] else
                    source["frame_offset"] >= previous["frame_end_offset"], "source frame identities overlap or disagree")
        previous = source
        require(state.get("complete") is True and state.get("truncated", False) is False,
                "an incomplete or truncated state cannot pass")
        require(uint(state.get("exported_orders"), 0, MAX_ORDERS), "invalid state exported-order count")
        for side in ("bid", "ask"):
            counts = state.get(side)
            require(type(counts) is dict and set(counts) == {"orders", "levels", "shares", "best_price4"},
                    "side manifest is incomplete")
            require(uint(counts["orders"], 0, MAX_ORDERS) and uint(counts["levels"], 0, MAX_ORDERS) and
                    uint(counts["shares"]), "invalid side manifest count")
            if counts["orders"] == 0:
                require(counts["levels"] == counts["shares"] == 0 and counts["best_price4"] is None,
                        "empty side must explicitly have zero totals and null best price")
            else:
                require(1 <= counts["levels"] <= counts["orders"] <= counts["shares"] and
                        uint(counts["best_price4"], 1, I32), "populated side has invalid totals/best price")
        require(state["exported_orders"] == state["bid"]["orders"] + state["ask"]["orders"],
                "state order totals disagree")
        total_orders += state["exported_orders"]
        require(total_orders <= MAX_ORDERS, "export exceeds the hard total-order bound")
    require(previous["sequence"] == summary["scanned_messages"] and
            previous["frame_end_offset"] == summary["consumed_prefix_bytes"], "prefix does not end at the last requested state")
    return summary


def read_orders(path, summary):
    require(stat_identity(path)[2] <= MAX_CSV_BYTES, "order export exceeds the bounded CSV size")
    rows, counts = [], {}
    previous = None
    references = set()
    source_references, global_sequence = set(), None
    with Path(path).open("r", encoding="ascii", newline="") as stream:
        header = stream.readline(256)
        require(header in (','.join(ORDER_HEADER) + '\n', ','.join(ORDER_HEADER) + '\r\n'), "order CSV header mismatch")
        for physical in stream:
            require(len(physical) <= 256 and physical.endswith('\n') and
                    physical.count('\r') <= 1 and ('\r' not in physical or physical.endswith('\r\n')),
                    "order CSV has an excessive or noncanonical physical line")
            line = physical.rstrip('\r\n')
            fields = line.split(',')
            require(len(fields) == len(ORDER_HEADER), "order CSV column count mismatch")
            require(fields[1] in {"B", "S"}, "order CSV has an invalid side")
            require(all(UINT_TEXT.fullmatch(value) for i, value in enumerate(fields) if i != 1), "order CSV has a noncanonical unsigned integer")
            row = {key: value if key == "side" else int(value) for key, value in zip(ORDER_HEADER, fields)}
            require(uint(row["state_id"], 1, len(summary["states"])) and uint(row["price4"], 1, I32) and
                    uint(row["fifo_rank"], 1, MAX_ORDERS) and uint(row["reference"], 1) and
                    uint(row["shares"], 1, U32), "order CSV value exceeds its common field domain")
            require(len(rows) < MAX_ORDERS, "order CSV exceeds the hard total-order bound")
            if previous is None or previous["state_id"] != row["state_id"]:
                require(previous is None or row["state_id"] > previous["state_id"], "CSV state ids decrease or repeat in separate blocks")
                references = set()
            else:
                old_side, side = previous["side"], row["side"]
                require(not (old_side == "S" and side == "B"), "CSV side order must be B then S")
                if side == old_side:
                    require(row["price4"] <= previous["price4"] if side == "B" else
                            row["price4"] >= previous["price4"], "CSV prices are not best first")
            same_level = previous is not None and all(row[key] == previous[key] for key in ("state_id", "side", "price4"))
            require(row["fifo_rank"] == (previous["fifo_rank"] + 1 if same_level else 1), "FIFO ranks are missing, repeated or reordered")
            require(row["reference"] not in references, "resting reference is duplicated within a state")
            references.add(row["reference"])
            sequence = summary["states"][row["state_id"] - 1]["source"]["sequence"]
            if sequence != global_sequence:
                source_references, global_sequence = set(), sequence
            require(row["reference"] not in source_references, "live reference is shared by symbols at the same global source point")
            source_references.add(row["reference"])
            key = (row["state_id"], row["side"])
            side_counts = counts.setdefault(key, {"orders": 0, "levels": 0, "shares": 0, "best_price4": row["price4"], "multiorder_level": False})
            side_counts["orders"] += 1
            side_counts["shares"] += row["shares"]
            side_counts["levels"] += int(not same_level)
            side_counts["multiorder_level"] |= row["fifo_rank"] > 1
            require(side_counts["shares"] <= U64, "aggregate side shares overflow uint64")
            rows.append(row)
            previous = row
    coverage = {"states": len(summary["states"]), "order_rows": len(rows), "empty_sides": 0,
                "empty_books": 0, "both_sided_states": 0, "deep_multiorder_states": 0, "levels": 0, "shares": 0}
    for state in summary["states"]:
        sides = []
        for name, code in (("bid", "B"), ("ask", "S")):
            actual = counts.get((state["state_id"], code), {"orders": 0, "levels": 0, "shares": 0, "best_price4": None, "multiorder_level": False})
            require({key: actual[key] for key in state[name]} == state[name], "order rows do not reconcile with side manifest")
            coverage["empty_sides"] += int(actual["orders"] == 0)
            coverage["levels"] += actual["levels"]
            coverage["shares"] += actual["shares"]
            sides.append(actual)
        both = all(side["orders"] > 0 for side in sides)
        coverage["both_sided_states"] += int(both)
        coverage["empty_books"] += int(all(side["orders"] == 0 for side in sides))
        coverage["deep_multiorder_states"] += int(both and any(side["levels"] > 1 for side in sides) and
                                                    any(side["multiorder_level"] for side in sides))
    require(coverage["deep_multiorder_states"] > 0, "no both-sided populated state demonstrates deeper levels and same-price FIFO coverage")
    return rows, coverage


def read_export(orders_path, summary_path):
    orders_path, summary_path = Path(orders_path).resolve(strict=True), Path(summary_path).resolve(strict=True)
    tracked = {path: (stat_identity(path), file_info(path)) for path in (orders_path, summary_path)}
    summary = read_summary(summary_path)
    orders, coverage = read_orders(orders_path, summary)
    for path, (before, digest) in tracked.items():
        require(stat_identity(path) == before and file_info(path) == digest, "export changed while being validated")
    return {"summary": summary, "orders": orders, "coverage": coverage,
            "files": {"orders": {"path": str(orders_path), **tracked[orders_path][1]},
                      "summary": {"path": str(summary_path), **tracked[summary_path][1]}}}


def compare_exports(local, reference):
    mismatches = {key: 0 for key in ("prefix_identity", "state_manifest", *ORDER_HEADER, "missing_local_rows", "extra_local_rows")}
    for field in ("input_bytes", "scanned_messages", "consumed_prefix_bytes", "boundary"):
        mismatches["prefix_identity"] += int(local["summary"][field] != reference["summary"][field])
    local_states, reference_states = local["summary"]["states"], reference["summary"]["states"]
    mismatches["state_manifest"] = abs(len(local_states) - len(reference_states))
    for left, right in zip(local_states, reference_states):
        # Complete source metadata, sides and counts are part of the common state.
        keys = ("state_id", "symbol", "locate", "source", "bid", "ask", "exported_orders", "complete")
        mismatches["state_manifest"] += int(any(left[key] != right[key] for key in keys))
    left_rows, right_rows = local["orders"], reference["orders"]
    mismatches["missing_local_rows"] = max(0, len(right_rows) - len(left_rows))
    mismatches["extra_local_rows"] = max(0, len(left_rows) - len(right_rows))
    differing_rows, differing_states = 0, set()
    for left, right in zip(left_rows, right_rows):
        different = False
        for key in ORDER_HEADER:
            delta = int(left[key] != right[key])
            mismatches[key] += delta
            different |= bool(delta)
        differing_rows += int(different)
        if different:
            differing_states.update((left["state_id"], right["state_id"]))
    return {"passed": not any(mismatches.values()), "mismatches": mismatches,
        "compared_order_rows": min(len(left_rows), len(right_rows)), "differing_order_rows": differing_rows,
        "differing_order_state_count": len(differing_states), "local_coverage": local["coverage"],
        "reference_coverage": reference["coverage"],
        "validation_scopes": {"local": local["summary"]["validation_scope"], "reference": reference["summary"]["validation_scope"]}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("local-orders", "local-summary", "reference-orders", "reference-summary", "report"):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    requested = args.report.expanduser().absolute()
    require(not os.path.lexists(requested), "report must be fresh, including no dangling symlink")
    report_path = requested.resolve()
    require(not os.path.lexists(report_path) and report_path.parent.is_dir(), "report needs a fresh file in an existing parent")
    report = {"schema_version": 1, "scope": "Exact sampled displayed-order price/FIFO comparison",
        "passed": False, "errors": [], "checks": {}, "limitations": [
            "Only the declared source-identified states are compared; this is not every intermediate book state",
            "Validation counters apply to each producer's declared validation scope",
            "The comparator does not run producers or reread raw input; raw source identity must be bound by producer evidence",
            "Producer evidence must bind the exact requested checkpoint list; matching omissions by both exports cannot be detected here",
            "Displayed resting-order agreement does not establish hypothetical fills, hidden liquidity or counterfactual response"]}
    tracked = {}
    try:
        paths = {name: getattr(args, name).expanduser().resolve(strict=True) for name in
                 ("local_orders", "local_summary", "reference_orders", "reference_summary")}
        require(len(set(paths.values())) == 4, "four distinct producer artefacts are required")
        require(report_path not in paths.values(), "report aliases an input artefact")
        for path in (*paths.values(), Path(__file__).resolve()):
            tracked[path] = (stat_identity(path), file_info(path))
        require(len({tracked[path][0][:2] for path in paths.values()}) == 4, "producer artefacts alias the same inode")
        report["input_files"] = {name: {"path": str(path), **tracked[path][1]} for name, path in paths.items()}
        report["comparator"] = {"path": str(Path(__file__).resolve()), **tracked[Path(__file__).resolve()][1]}
        local = read_export(paths["local_orders"], paths["local_summary"])
        reference = read_export(paths["reference_orders"], paths["reference_summary"])
        report["exports"] = {"local": local["files"], "reference": reference["files"]}
        comparison = compare_exports(local, reference)
        report.update(comparison)
        report["checks"].update(complete_declared_state_manifests=True,
            exact_source_boundaries=comparison["mismatches"]["prefix_identity"] == comparison["mismatches"]["state_manifest"] == 0,
            side_totals_reconcile=True, explicit_empty_states_checked=True, populated_depth_and_fifo_coverage=True,
            strict_price_fifo_traversal=True, zero_validation_counters=True)
        if not report["passed"]:
            report["errors"].append("independent displayed-order exports disagree; see aggregate mismatch counts")
    except (OSError, ValueError, TypeError, KeyError, OverflowError, UnicodeError, RuntimeError) as error:
        report["passed"] = False
        report["errors"].append(str(error))
    finally:
        try:
            for path, (before, digest) in tracked.items():
                require(stat_identity(path) == before and file_info(path) == digest, "producer artefact or comparator changed during comparison")
            report["checks"]["artefacts_unchanged"] = bool(tracked)
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            report["passed"] = False
            report["errors"].append(str(error))
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
            stream.write('\n')
    if not report["passed"]:
        print("L3 comparison failed; see the aggregate report", file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
