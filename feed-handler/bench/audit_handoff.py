#!/usr/bin/env python3
"""Audit a frozen displayed-history projection's bounded causal simulator handoff.

Raw source identity is retained from the earlier full-source evidence; this utility
does not reopen the raw day. Per-event audits and source joins remain private.
"""
import argparse
import csv
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
LIMIT = 1_000_000_000
U64 = (1 << 64) - 1
I64 = (1 << 63) - 1
TIME_LIMIT = (1 << 48) - 1
MAX_ROWS = 100_000
HEX = re.compile(r"[0-9a-f]{64}\Z")
UINT = re.compile(r"(?:0|[1-9][0-9]*)\Z")
SINT = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")
LENGTHS = dict(S=12, R=39, H=25, Y=20, L=26, V=35, W=12, K=28, J=35,
               h=21, A=36, F=40, E=31, C=36, X=23, D=19, U=35, P=44,
               Q=40, B=19, I=50, N=20, O=48)
EVENT_HEADER = ("timestamp_ns", "kind", "quantity", "opposite_price4")
SOURCE_HEADER = ("sequence", "frame_offset", "timestamp_ns", "body_bytes", "type")
PROVENANCE_HEADER = (*SOURCE_HEADER, "reason", "reference", "new_reference", "match",
    "before_quantity", "before_opposite_price4", "before_opposite_quantity",
    "after_quantity", "after_opposite_price4", "after_opposite_quantity", "normalised_row")
AUDIT_HEADER = ("time_ns", "origin_ns", "phase", "serial", "event", "source_index",
    "event_quantity", "external_quantity", "opposite_price4", "ahead", "remaining",
    "exchange_state", "exchange_filled", "exchange_position", "exchange_cash4", "exchange_fees4",
    "observed", "observed_timestamp_ns", "observed_quantity", "observed_opposite_price4",
    "known_remaining", "local_state", "local_filled", "local_position", "local_cash4", "local_fees4")
STATES = {"idle", "pending", "live", "filled", "cancelled", "rejected"}
CONFIG_KEYS = ("side", "cancel_model", "price4", "quantity", "fee4", "decision_ns", "cancel_ns",
               "horizon_ns", "feed_delay_ns", "order_delay_ns", "response_delay_ns")
SOURCE_SUFFIXES = {".cpp", ".hpp", ".h", ".c", ".py", ".cmake"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, minimum=0, maximum=U64):
    return type(value) is int and minimum <= value <= maximum


def strict_json(text):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON key")
            result[key] = value
        return result

    def invalid(_):
        raise ValueError("non-finite JSON value")

    def finite(value):
        number = float(value)
        require(math.isfinite(number), "non-finite JSON number")
        return number

    value = json.loads(text, object_pairs_hook=unique, parse_constant=invalid, parse_float=finite)
    require(type(value) is dict, "JSON root must be an object")
    return value


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def identity(path):
    value = Path(path).stat()
    require(stat.S_ISREG(value.st_mode), "input artefact must be a regular file")
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def file_info(path):
    before = identity(path)
    digest = sha256(path)
    require(identity(path) == before, "artefact changed during hashing")
    return {"bytes": before[2], "sha256": digest}


def read_object(path, maximum=8 << 20):
    require(identity(path)[2] <= maximum, "JSON artefact exceeds the bounded audit size")
    return strict_json(Path(path).read_text(encoding="utf-8"))


def table(path, header, strings, signed=(), maximum_rows=MAX_ROWS, maximum_bytes=64 << 20):
    require(identity(path)[2] <= maximum_bytes, "CSV artefact exceeds the bounded audit size")
    text = Path(path).read_text(encoding="ascii")
    require('"' not in text and "\x00" not in text, "quoted or NUL CSV fields are unsupported")
    lines = text.splitlines()
    require(lines and tuple(lines[0].split(',')) == tuple(header), "CSV header mismatch")
    require(0 < len(lines) - 1 <= maximum_rows, "CSV has empty or excessive row coverage")
    result = []
    for line in lines[1:]:
        require(len(line) <= 2048, "CSV line exceeds the bounded audit size")
        fields = line.split(',')
        require(len(fields) == len(header), "CSV column count mismatch")
        row = {}
        for key, value in zip(header, fields):
            if key in strings:
                require(bool(value), "empty CSV text field")
                row[key] = value
            else:
                require(bool((SINT if key in signed else UINT).fullmatch(value)), "invalid CSV integer")
                parsed = int(value)
                require(integer(parsed, -I64 - 1 if key in signed else 0, I64 if key in signed else U64),
                        "CSV integer exceeds its storage range")
                row[key] = parsed
        result.append(row)
    return result


def read_audit(path):
    rows = table(path, AUDIT_HEADER, {"event", "exchange_state", "local_state"},
        {"exchange_position", "exchange_cash4", "exchange_fees4", "local_position", "local_cash4", "local_fees4"},
        3 * MAX_ROWS + 10, 256 << 20)
    for row in rows:
        require(row["exchange_state"] in STATES and row["local_state"] in STATES, "unknown audit order state")
        require(row["observed"] in (0, 1) and 1 <= row["phase"] <= 5, "invalid audit phase/observation flag")
    return rows


def validate_events(events, config):
    require(0 < len(events) <= MAX_ROWS, "invalid normalised event count")
    visible = opposite = previous = 0
    for i, event in enumerate(events):
        require(type(event) is dict and set(event) == set(EVENT_HEADER), "invalid normalised event fields")
        require(integer(event["timestamp_ns"], previous, config["horizon_ns"]), "market clock outside ordered horizon")
        previous = event["timestamp_ns"]
        q, p, kind = event["quantity"], event["opposite_price4"], event["kind"]
        require(integer(q, 0, LIMIT) and integer(p, 0, LIMIT), "market value outside model bounds")
        if i == 0:
            require(kind == "seed", "initial seed is missing")
            visible, opposite = q, p
        elif kind == "add":
            require(q > 0 and p == 0 and visible + q <= LIMIT, "invalid market addition")
            visible += q
        elif kind in {"cancel", "trade"}:
            require(0 < q <= visible and p == 0, "invalid market reduction")
            visible -= q
        elif kind == "quote":
            require(q == 0, "quote must have zero quantity")
            opposite = p
        else:
            raise ValueError("unknown or repeated seed event")
        require(visible == 0 or opposite == 0 or passive(config, opposite), "market quote crosses fixed level")
        require(max(previous + config["feed_delay_ns"], previous + config["response_delay_ns"]) <= U64,
                "derived market clock overflows")


def validate_config(config):
    require(type(config) is dict and set(config) == set(CONFIG_KEYS), "invalid simulator configuration fields")
    require(config["side"] in {"buy", "sell"} and config["cancel_model"] in {"optimistic", "conservative"},
            "invalid simulator configuration enum")
    for key in ("price4", "quantity"):
        require(integer(config[key], 1, LIMIT), "invalid bounded simulator value")
    require(integer(config["fee4"], -LIMIT, LIMIT), "invalid signed fee")
    for key in ("decision_ns", "horizon_ns", "feed_delay_ns", "order_delay_ns", "response_delay_ns"):
        require(integer(config[key]), "invalid simulator clock")
    require(config["decision_ns"] <= config["horizon_ns"], "decision is after horizon")
    cancel = config["cancel_ns"]
    require(cancel is None or integer(cancel, config["decision_ns"], config["horizon_ns"]), "invalid cancel clock")
    for time in (config["decision_ns"], cancel):
        require(time is None or time + config["order_delay_ns"] + config["response_delay_ns"] <= U64,
                "derived action clock overflows")


def passive(config, opposite):
    return opposite > 0 and (config["price4"] < opposite if config["side"] == "buy" else config["price4"] > opposite)


def validate_provenance(events, rows, summary):
    require(0 < len(rows) <= MAX_ROWS, "invalid provenance coverage")
    require(summary["provenance_rows"] == len(rows) and summary["normalised_rows"] == len(events),
            "projection row counts disagree")
    source_rows, previous, state, execution_shares = {}, None, None, 0
    counts = {}
    for i, row in enumerate(rows):
        require(type(row) is dict and set(row) == set(PROVENANCE_HEADER), "invalid provenance fields")
        for key in set(PROVENANCE_HEADER) - {"type", "reason"}:
            require(integer(row[key]), "invalid provenance unsigned field")
        require(row["type"] in LENGTHS and row["body_bytes"] == LENGTHS[row["type"]], "source type/body length mismatch")
        require(1 <= row["sequence"] <= summary["source_messages"] and
                row["frame_offset"] + row["body_bytes"] + 2 <= summary["source_bytes"], "source point exceeds retained raw input")
        require(integer(row["timestamp_ns"], 0, TIME_LIMIT), "invalid source timestamp")
        if previous:
            require(row["sequence"] > previous["sequence"] and
                    row["frame_offset"] >= previous["frame_offset"] + previous["body_bytes"] + 2 and
                    row["timestamp_ns"] >= previous["timestamp_ns"], "provenance source order regresses")
        before = tuple(row[f"before_{key}"] for key in ("quantity", "opposite_price4", "opposite_quantity"))
        after = tuple(row[f"after_{key}"] for key in ("quantity", "opposite_price4", "opposite_quantity"))
        require(all(integer(value, 1, LIMIT) for value in (*before, *after)), "provenance needs positive bounded BBO values")
        require(passive(summary, before[1]) and passive(summary, after[1]), "provenance opposite quote crosses target")
        require(state is None or before == state, "provenance pre/post BBO ledger is discontinuous")
        row_number, reason = row["normalised_row"], row["reason"]
        kind = None
        if i == 0:
            require(reason == "seed_boundary" and row_number == 1 and before == after and
                    row["timestamp_ns"] <= summary["start_ns"] and
                    row["reference"] == row["new_reference"] == row["match"] == 0, "invalid whole-group seed provenance")
            kind, amount, quote, timestamp = "seed", after[0], after[1], summary["start_ns"]
        else:
            require(summary["start_ns"] < row["timestamp_ns"] <= summary["end_ns"], "provenance lies outside source window")
            counts[row["type"]] = counts.get(row["type"], 0) + 1
            amount = quote = 0
            timestamp = row["timestamp_ns"]
            if reason == "displayed_add":
                require(row["type"] in {"A", "F"} and after[0] > before[0] and before[1:] == after[1:], "invalid add provenance")
                kind, amount = "add", after[0] - before[0]
            elif reason in {"displayed_cancel", "displayed_execution"}:
                require(row["type"] in ({"D", "X"} if reason == "displayed_cancel" else {"E"}) and
                        after[0] < before[0] and before[1:] == after[1:], "invalid reduction provenance")
                kind, amount = ("trade" if reason == "displayed_execution" else "cancel"), before[0] - after[0]
                if kind == "trade":
                    require(row["match"] > 0, "execution match identity is missing")
                    execution_shares += amount
            elif reason == "opposite_quote":
                require(row["type"] in {"A", "F", "E", "D", "X", "U"} and before[0] == after[0] and
                        before[1] != after[1], "invalid opposite quote provenance")
                kind, quote = "quote", after[1]
            elif reason in {"no_represented_change", "non_displayed_print", "unrelated_broken_trade"}:
                require(before[:2] == after[:2] and row_number == 0, "excluded source event changes normalised state")
                if reason == "non_displayed_print":
                    require(row["type"] == "P", "non-displayed print has wrong wire type")
                elif reason == "unrelated_broken_trade":
                    require(row["type"] == "B", "unrelated break has wrong wire type")
                else:
                    require(row["type"] in {"A", "F", "E", "D", "X", "U", "H", "h", "N", "Y", "L"},
                            "unsupported excluded wire type")
            else:
                raise ValueError("unknown or repeated seed projection reason")
            if row["type"] in {"A", "F", "E", "D", "X", "U"}:
                require(row["reference"] > 0, "order source reference is missing")
            require((row["new_reference"] > 0) == (row["type"] == "U"), "replacement provenance identity mismatch")
            if row["type"] not in {"E", "P", "B"}:
                require(row["match"] == 0, "unused match identity is nonzero")
        if kind:
            require(row_number == len(source_rows) + 1 and row_number <= len(events), "duplicate, missing or reordered normalised provenance")
            expected = dict(timestamp_ns=timestamp, kind=kind, quantity=amount, opposite_price4=quote)
            require(events[row_number - 1] == expected, "normalised row does not match its source delta")
            source_rows[row_number] = row
        state, previous = after, row
    require(len(source_rows) == len(events), "normalised row has no source provenance")
    require(counts == summary["window_type_counts"] and len(rows) - 1 == summary["reconciled_messages"], "selected source census disagrees")
    require(execution_shares == summary["displayed_executed_shares"], "mapped displayed execution quantity disagrees")
    require(state == (summary["final_quantity"], summary["final_opposite_price4"], summary["final_opposite_quantity"]),
            "final retained BBO does not match provenance")
    return source_rows


def read_projection(directory, run, input_identity):
    directory = Path(directory).resolve(strict=True)
    files = {key: directory / filename for key, filename in (("summary_file", "summary.json"),
        ("normalised_file", "normalised.csv"), ("provenance_file", "provenance.csv"), ("stderr", "stderr.txt"))}
    files = {key: path.resolve(strict=True) for key, path in files.items()}
    for key, path in files.items():
        manifest = run.get(key)
        require(type(manifest) is dict and set(manifest) == {"bytes", "sha256"} and
                integer(manifest["bytes"]) and type(manifest["sha256"]) is str and HEX.fullmatch(manifest["sha256"]),
                "invalid frozen projection file manifest")
        require(file_info(path) == manifest, f"frozen projection {key} identity mismatch")
    require(run["stderr"]["bytes"] == 0 and type(run.get("exit_code")) is int and run["exit_code"] == 0,
            "frozen projection had diagnostics or failed")
    summary = read_object(files["summary_file"])
    require(summary == run.get("summary"), "retained projection summary disagrees with evidence")
    require(summary.get("schema_version") == 1 and type(summary.get("schema_version")) is int and
            summary.get("model") == "strict_displayed_window_v1" and summary.get("passed") is True and
            summary.get("source_identity_stable") is True, "projection is not strict passed version one")
    for key in ("price4", "start_ns", "end_ns", "max_orders", "max_levels", "locate", "source_messages",
                "source_end_records", "source_bytes", "reconciled_messages", "displayed_executed_shares",
                "final_quantity", "final_opposite_price4", "final_opposite_quantity", "normalised_rows", "provenance_rows"):
        require(integer(summary.get(key)), "projection summary has an invalid unsigned field")
    require(summary.get("side") in {"buy", "sell"} and summary.get("symbol") == run.get("symbol") and
            re.fullmatch(r"[A-Z0-9.\-^/]{1,8}", summary["symbol"]) is not None, "invalid projection symbol/side")
    require(0 < summary["price4"] <= LIMIT and summary["start_ns"] < summary["end_ns"] <= TIME_LIMIT and
            summary["end_ns"] - summary["start_ns"] > 20_000 and 0 < summary["locate"] <= 65535 and
            0 < summary["max_orders"] <= 4_194_304 and 0 < summary["max_levels"] <= 2_097_152 and
            summary["source_messages"] > 0 and summary["source_end_records"] <= 1 and
            summary["source_bytes"] == input_identity["bytes"], "projection bounds/source identity disagree")
    require(run.get("configuration") == {key: summary[key] for key in ("side", "price4", "start_ns", "end_ns")},
            "frozen projection configuration disagrees")
    require(type(summary.get("source_type_counts")) is dict and
            all(kind in LENGTHS and integer(count, 1) for kind, count in summary["source_type_counts"].items()) and
            sum(summary["source_type_counts"].values()) == summary["source_messages"] and
            sum((LENGTHS[kind] + 2) * count for kind, count in summary["source_type_counts"].items()) +
                2 * summary["source_end_records"] == summary["source_bytes"], "retained full-source census is inconsistent")
    require(type(summary.get("window_type_counts")) is dict and
            all(kind in LENGTHS and integer(count, 1) for kind, count in summary["window_type_counts"].items()), "invalid selected wire census")
    comparison = run.get("comparison")
    require(type(comparison) is dict and all(integer(comparison.get(key)) for key in
        ("different_states", "compared_states", "seed_states", "post_source_message_states")), "invalid independent comparison counters")
    require(comparison.get("different_states") == 0 and type(comparison.get("different_states")) is int and
            comparison.get("compared_states") == summary["provenance_rows"] and
            comparison.get("seed_states") == 1 and comparison.get("post_source_message_states") == summary["reconciled_messages"] and
            comparison.get("compared_bbo_fields") == ["same_price4", "same_quantity", "opposite_price4", "opposite_quantity"] and
            comparison.get("source_identity_fields") == list(SOURCE_HEADER) and
            comparison.get("all_normalised_rows_have_source_delta_provenance") is True and
            comparison.get("same_price_fixed_and_both_quotes_positive") is True, "frozen independent state comparison did not pass")
    eligibility = summary.get("eligibility")
    require(type(eligibility) is dict and eligibility.get("operational_action") in {"?", "T"} and
            eligibility.get("retail_interest") in {"?", "N"}, "retained seed eligibility is unsupported")
    for key, kind in (("directory", "R"), ("trading_action", "H"), ("market_hours", "S"), ("opening_cross", "Q"), ("operational", "h")):
        point = eligibility.get(key)
        if key == "operational" and point is None:
            require(eligibility["operational_action"] == '?', "absent operational announcement has an invented state")
            continue
        require(type(point) is dict and set(point) == set(SOURCE_HEADER) and point.get("type") == kind,
                "missing or malformed retained eligibility source point")
        require(all(integer(point.get(field)) for field in SOURCE_HEADER if field != "type") and
                0 < point["sequence"] <= summary["source_messages"] and
                point["timestamp_ns"] <= summary["start_ns"] and point["body_bytes"] == LENGTHS[kind] and
                point["frame_offset"] + point["body_bytes"] + 2 <= summary["source_bytes"], "eligibility source point is outside seed/input")
    events = table(files["normalised_file"], EVENT_HEADER, {"kind"})
    provenance = table(files["provenance_file"], PROVENANCE_HEADER, {"type", "reason"})
    cfg = dict(side=summary["side"], cancel_model="conservative", price4=summary["price4"], quantity=100,
        fee4=1, decision_ns=summary["start_ns"], cancel_ns=None, horizon_ns=summary["end_ns"],
        feed_delay_ns=0, order_delay_ns=0, response_delay_ns=0)
    validate_events(events, cfg)
    require(events[0]["timestamp_ns"] == summary["start_ns"], "normalised seed timestamp mismatch")
    source_rows = validate_provenance(events, provenance, summary)
    seed = provenance[0]
    for key in ("directory", "trading_action", "market_hours", "opening_cross", "operational"):
        point = eligibility.get(key)
        require(point is None or (point["sequence"] <= seed["sequence"] and
            point["frame_offset"] + point["body_bytes"] <= seed["frame_offset"] + seed["body_bytes"]),
            "eligibility source point is after the complete seed boundary")
    return dict(events=events, provenance=provenance, source_rows=source_rows, summary=summary, files=files)


def expected_trace(events, config):
    """Apply the declared clock/queue contract without calling the C++ kernel.

    The agenda carries immutable delivered snapshots and explicit request lineage.
    Every audit field is checked, rather than just final accounts or event counts.
    """
    validate_config(config)
    validate_events(events, config)
    agenda, serial = [], 0

    def enqueue(time, phase, label, source=0, origin=None, amount=0, snapshot=None, decision_row=0):
        nonlocal serial
        require(integer(time), "derived clock overflows")
        heapq.heappush(agenda, (time, phase, serial, label, source,
            time if origin is None else origin, amount, snapshot, decision_row))
        serial += 1

    for index, event in enumerate(events, 1):
        enqueue(event["timestamp_ns"], 1, "market_" + event["kind"], index, amount=event["quantity"])
    enqueue(config["decision_ns"], 3, "decision", amount=config["quantity"])
    if config["cancel_ns"] is not None:
        enqueue(config["cancel_ns"], 3, "cancel_decision")
    q = opposite = ahead = remaining = known = 0
    observed_q = observed_opposite = observed_time = latest_row = 0
    observed = submitted = cancel_requested = False
    exchange_state = local_state = "idle"
    accounts = {"exchange": dict(filled=0, position=0, cash4=0, fees4=0),
                "local": dict(filled=0, position=0, cash4=0, fees4=0)}
    trace, lineage = [], []
    submit_decision_row = 0

    def credit(which, amount):
        account = accounts[which]
        sign = 1 if config["side"] == "buy" else -1
        account["filled"] += amount
        account["position"] += sign * amount
        account["fees4"] += amount * config["fee4"]
        account["cash4"] -= amount * (sign * config["price4"] + config["fee4"])

    while agenda and agenda[0][0] <= config["horizon_ns"]:
        time, phase, order, label, source, origin, amount, snapshot, decision_row = heapq.heappop(agenda)
        if phase == 1:
            # An exchange-side queue update/fill also belongs to the original
            # submitted intent, even when its local response is past the horizon.
            if exchange_state == "live":
                decision_row = submit_decision_row
            event = events[source - 1]
            kind = event["kind"]
            if kind == "seed":
                q, opposite = event["quantity"], event["opposite_price4"]
            elif kind == "add":
                q += amount
            elif kind == "cancel":
                if exchange_state == "live":
                    behind = q - ahead
                    ahead -= min(ahead, amount) if config["cancel_model"] == "optimistic" else max(0, amount - behind)
                q -= amount
            elif kind == "trade":
                if exchange_state == "live":
                    depletion_ahead = min(ahead, amount)
                    fill = min(remaining, amount - depletion_ahead)
                    ahead -= depletion_ahead
                    if fill:
                        remaining -= fill
                        credit("exchange", fill)
                        if remaining == 0:
                            exchange_state, ahead = "filled", 0
                        enqueue(time + config["response_delay_ns"], 5, "response_fill", source,
                                time, fill, decision_row=submit_decision_row)
                q -= amount
            else:
                opposite = event["opposite_price4"]
            enqueue(time + config["feed_delay_ns"], 2, "feed_" + kind, source,
                    time, amount, (q, opposite))
        elif phase == 2:
            observed, observed_time, latest_row = True, origin, source
            observed_q, observed_opposite = snapshot
        elif label == "decision":
            decision_row = latest_row
            if observed and observed_q > 0 and passive(config, observed_opposite):
                label, submitted, local_state, known = "submit", True, "pending", config["quantity"]
                submit_decision_row = latest_row
                enqueue(time + config["order_delay_ns"], 4, "arrival", origin=time,
                        amount=config["quantity"], decision_row=decision_row)
            else:
                label = "decision_skip"
        elif label == "cancel_decision":
            decision_row = latest_row
            if local_state == "live" and known > 0:
                label, cancel_requested = "cancel_request", True
                enqueue(time + config["order_delay_ns"], 4, "cancel_arrival", origin=time,
                        decision_row=decision_row)
            else:
                label = "cancel_skip"
        elif label == "arrival":
            if passive(config, opposite):
                label, exchange_state, remaining, ahead = "arrival_accept", "live", config["quantity"], q
                response, response_amount = "response_accept", config["quantity"]
            else:
                label, exchange_state = "arrival_reject", "rejected"
                response, response_amount = "response_reject", 0
            enqueue(time + config["response_delay_ns"], 5, response, origin=time,
                    amount=response_amount, decision_row=decision_row)
        elif label == "cancel_arrival":
            if exchange_state == "live":
                label, response, response_amount = "arrival_cancel", "response_cancel", remaining
                exchange_state, remaining, ahead = "cancelled", 0, 0
            else:
                label, response, response_amount = "arrival_cancel_reject", "response_cancel_reject", 0
            enqueue(time + config["response_delay_ns"], 5, response, origin=time,
                    amount=response_amount, decision_row=decision_row)
        elif label == "response_accept":
            local_state = "live"
        elif label == "response_reject":
            local_state, known = "rejected", 0
        elif label == "response_fill":
            credit("local", amount)
            known -= amount
            if known == 0:
                local_state = "filled"
        elif label == "response_cancel":
            local_state, known = "cancelled", 0
        elif label != "response_cancel_reject":
            raise ValueError("unknown audit agenda event")
        row = dict(time_ns=time, origin_ns=origin, phase=phase, serial=order, event=label,
            source_index=source, event_quantity=amount, external_quantity=q, opposite_price4=opposite,
            ahead=ahead, remaining=remaining, exchange_state=exchange_state,
            observed=int(observed), observed_timestamp_ns=observed_time, observed_quantity=observed_q,
            observed_opposite_price4=observed_opposite, known_remaining=known, local_state=local_state)
        for which, account in accounts.items():
            row.update({which + '_' + key: value for key, value in account.items()})
        trace.append(row)
        action_clock = config["decision_ns"] if decision_row else 0
        if label in {"submit", "decision_skip", "arrival_accept", "arrival_reject", "response_accept", "response_reject", "response_fill"}:
            action_clock = config["decision_ns"]
        elif label in {"cancel_request", "cancel_skip", "arrival_cancel", "arrival_cancel_reject", "response_cancel", "response_cancel_reject"}:
            action_clock = config["cancel_ns"]
        lineage.append(dict(origin_normalised_row=source, latest_delivered_normalised_row=latest_row,
                            action_decision_normalised_row=decision_row, action_decision_time_ns=action_clock))
    mark = None
    if observed and observed_q > 0 and passive(config, observed_opposite):
        mark = 2 * accounts["local"]["cash4"] + accounts["local"]["position"] * (config["price4"] + observed_opposite)
    final = dict(exchange=accounts["exchange"], local=accounts["local"], exchange_state=exchange_state,
        local_state=local_state, remaining=remaining, known_remaining=known, ahead=ahead,
        pending_events=len(agenda), submitted=submitted, cancel_requested=cancel_requested,
        local_marked_equity_twice4=mark, audit_rows=len(trace), market_events=len(events))
    pending = {key: 0 for key in ("feed", "arrival", "response")}
    for event in agenda:
        label = event[3]
        pending["feed" if label.startswith("feed_") else "response" if label.startswith("response_") else "arrival"] += 1
    return trace, lineage, final, pending


def validate_trace(events, provenance, config, summary, audit_rows):
    expected, lineage, final, pending = expected_trace(events, config)
    require(type(summary) is dict and summary.get("schema_version") == 1 and type(summary.get("schema_version")) is int and
            summary.get("model") == "synthetic_shadow_single_level_v1" and summary.get("passed") is True and
            summary.get("source_identity_stable") is True, "simulator did not report strict version-one success")
    for key in CONFIG_KEYS:
        require(type(summary.get(key)) is type(config[key]) and summary.get(key) == config[key], "simulator configuration mismatch: " + key)
    require(integer(summary.get("input_bytes"), 1), "simulator input byte count is invalid")
    for key, value in final.items():
        require(type(summary.get(key)) is type(value) and summary.get(key) == value, "simulator final summary mismatch: " + key)
    for which in ("exchange", "local"):
        require(type(summary[which]) is dict and set(summary[which]) == {"filled", "position", "cash4", "fees4"} and
                all(type(value) is int for value in summary[which].values()), "invalid account field types")
    require(len(audit_rows) == len(expected), "missing or extra simulator audit rows")
    mapping = {}
    for row in provenance:
        index = row.get("normalised_row")
        require(integer(index, 0, len(events)), "invalid normalised-row source join")
        if index:
            require(index not in mapping, "duplicate normalised-row source join")
            require(all(integer(row.get(key)) for key in SOURCE_HEADER if key != "type") and
                    row.get("type") in LENGTHS and row["body_bytes"] == LENGTHS[row["type"]] and
                    row["sequence"] > 0 and row["timestamp_ns"] <= events[index - 1]["timestamp_ns"] and
                    (index == 1 or row["timestamp_ns"] == events[index - 1]["timestamp_ns"]), "invalid joined source point")
            mapping[index] = row
    require(set(mapping) == set(range(1, len(events) + 1)), "normalised row lacks source provenance")
    joined = []
    for number, (actual, wanted, links) in enumerate(zip(audit_rows, expected, lineage), 1):
        require(type(actual) is dict and set(actual) == set(AUDIT_HEADER), "invalid audit field set")
        for key in AUDIT_HEADER:
            require(type(actual[key]) is type(wanted[key]) and actual[key] == wanted[key],
                    f"causal audit row {number} field mismatch: {key}")
        require(actual["exchange_filled"] >= actual["local_filled"] and
                actual["exchange_filled"] <= config["quantity"] and actual["ahead"] <= actual["external_quantity"],
                "queue/account conservation failed")
        record = dict(actual)
        record.update(links)
        for prefix in ("origin", "latest_delivered", "action_decision"):
            index = links[prefix + "_normalised_row"]
            point = mapping.get(index)
            for field in SOURCE_HEADER:
                record[prefix + "_source_" + field] = point[field] if point else ("" if field == "type" else 0)
            record[prefix + "_derived_seed"] = int(index == 1)
        joined.append(record)
    exchange_unfilled = config["quantity"] - final["exchange"]["filled"] if final["submitted"] else 0
    require(exchange_unfilled >= final["remaining"], "own-order residual quantity exceeds submitted quantity")
    return {"checks": {"exact_clock_phase_serial_schedule": True, "immutable_delayed_snapshots": True,
        "decisions_use_delivered_information": True, "queue_and_account_conservation": True,
        "all_origin_and_decision_source_joins": True, "horizon_pending_events_reconciled": True,
        "complete_audit_and_final_summary": True}, "joined_rows": joined, "pending_by_kind": pending,
        "trace_rows": len(joined), "normalised_source_rows": len(mapping),
        "exchange_unfilled_quantity": exchange_unfilled,
        "exchange_live_quantity": final["remaining"] if final["exchange_state"] == "live" else 0,
        "in_flight_order_quantity": config["quantity"] if final["local_state"] == "pending" and final["exchange_state"] == "idle" else 0,
        "unobserved_filled_quantity": final["exchange"]["filled"] - final["local"]["filled"]}


def matrix(summary):
    start, end = summary["start_ns"], summary["end_ns"]
    duration = end - start
    for model in ("optimistic", "conservative"):
        for name, feed, order, response, decision, cancel in (
            ("immediate", 0, 0, 0, start, None),
            ("delayed", 1000, 2000, 5000, start + 1000, None),
            ("undelivered_seed", duration + 1, 0, 0, start, None),
            ("arrival_pending", 0, duration + 1, 0, start, None),
            ("cancel_confirmed", 1000, 2000, 5000, start + 1000, end - 10000),
            ("cancel_response_pending", 1000, 2000, 5000, start + 1000, end - 4000)):
            yield name, dict(side=summary["side"], cancel_model=model, price4=summary["price4"], quantity=100,
                fee4=1, decision_ns=decision, cancel_ns=cancel, horizon_ns=end,
                feed_delay_ns=feed, order_delay_ns=order, response_delay_ns=response)


def git(directory, *arguments):
    child = subprocess.run(["git", "-C", str(directory), *arguments], capture_output=True, check=False)
    require(child.returncode == 0 and child.stderr == b"", "cannot obtain strict Git provenance")
    return child.stdout


def source_snapshot(directory):
    directory = Path(directory).resolve(strict=True)
    require(git(directory, "branch", "--show-current").strip() == b"main", "handoff evidence requires existing main")
    status = git(directory, "status", "--porcelain", "--untracked-files=normal")
    require(status == b"", "handoff evidence requires a committed clean main checkout")
    commit = git(directory, "rev-parse", "HEAD").decode("ascii").strip()
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, "invalid source commit identity")
    names = git(directory, "ls-files", "-z").decode("utf-8").split('\0')
    files = {name: file_info(directory / name) for name in sorted(names) if name and
        (Path(name).suffix in SOURCE_SUFFIXES or Path(name).name == "CMakeLists.txt")}
    require(bool(files), "source provenance has no implementation files")
    return {"commit": commit, "branch": "main", "clean": True, "files": files}


def anchor_evidence(path):
    path = Path(path).resolve(strict=True)
    require(path.is_relative_to(ROOT), "window evidence must be a tracked file inside this checkout")
    relative = path.relative_to(ROOT).as_posix()
    blob = git(ROOT, "show", "HEAD:" + relative)
    require(blob == path.read_bytes(), "window evidence differs from its committed Git blob")
    return {"tracked_path": relative, **file_info(path), "matches_head_blob": True}


def validate_evidence(evidence):
    require(evidence.get("schema_version") == 1 and type(evidence.get("schema_version")) is int and
            evidence.get("passed") is True and evidence.get("source_clean_at_launch") is True and
            evidence.get("errors") == [], "window evidence is not a clean passed aggregate")
    require(type(evidence.get("source_commit")) is str and re.fullmatch(r"[0-9a-f]{40}", evidence["source_commit"]) is not None,
            "window producer commit identity is invalid")
    source = evidence.get("source_file_sha256")
    require(type(source) is dict and bool(source) and
            all(type(key) is str and type(value) is str and HEX.fullmatch(value) for key, value in source.items()),
            "window producer source hash manifest is invalid")
    for name in ("include/itch/queue_sim.hpp", "src/queue_sim.cpp", "tools/queue_sim.cpp"):
        require(name in source and sha256(ROOT / name) == source[name], "simulator source changed since frozen projection evidence")
    checks = evidence.get("checks")
    require(type(checks) is dict and bool(checks) and all(type(value) is bool and value for value in checks.values()),
            "window evidence has a missing or failed check")
    for key in ("both_canonical_windows_projected", "all_fifteen_independent_states_match",
                "input_unchanged_and_sha256_verified_after", "public_source_commit_and_files_unchanged"):
        require(checks.get(key) is True, "required frozen window evidence check is absent")
    raw = evidence.get("input")
    require(type(raw) is dict and type(raw.get("name")) is str and bool(raw["name"]) and
            integer(raw.get("bytes"), 1) and type(raw.get("sha256_before")) is str and
            HEX.fullmatch(raw["sha256_before"]) and raw.get("sha256_after") == raw["sha256_before"],
            "retained raw source identity is inconsistent")
    runs = evidence.get("runs")
    require(type(runs) is list and len(runs) == 2 and all(type(run) is dict for run in runs) and
            {run.get("symbol") for run in runs} == {"MSFT", "QQQ"}, "handoff requires exactly the two frozen canonical windows")
    return raw, runs


def write_json(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')


def write_joined(path, rows):
    require(bool(rows), "joined causal trace is empty")
    with Path(path).open("x", encoding="ascii", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def command(simulator, projection, config, audit):
    result = [str(simulator)]
    for field, flag in (("side", "--side"), ("price4", "--price4"), ("quantity", "--quantity"),
        ("fee4", "--fee4"), ("decision_ns", "--decision-ns"), ("horizon_ns", "--horizon-ns"),
        ("feed_delay_ns", "--feed-delay-ns"), ("order_delay_ns", "--order-delay-ns"),
        ("response_delay_ns", "--response-delay-ns"), ("cancel_model", "--cancel-model")):
        result.extend((flag, str(config[field])))
    if config["cancel_ns"] is not None:
        result.extend(("--cancel-ns", str(config["cancel_ns"])))
    return [*result, "--audit", str(audit), str(projection)]


def execute(simulator, projection, config, directory):
    directory.mkdir()
    write_json(directory / "configuration.json", config)
    argv = command(simulator, projection, config, directory / "audit.csv")
    with (directory / "summary.json").open("xb") as stdout, (directory / "stderr.txt").open("xb") as stderr:
        try:
            result = subprocess.run(argv, stdout=stdout, stderr=stderr, check=False, timeout=120)
        except subprocess.TimeoutExpired:
            write_json(directory / "process.json", {"completed": False, "timed_out": True, "exit_code": None})
            raise
    write_json(directory / "process.json", {"completed": True, "timed_out": False, "exit_code": result.returncode})
    require(result.returncode == 0 and identity(directory / "stderr.txt")[2] == 0,
            "simulator process failed or produced diagnostics; see private logs")
    summary = read_object(directory / "summary.json")
    rows = read_audit(directory / "audit.csv")
    require(summary.get("input_bytes") == identity(projection)[2] and type(summary.get("input_bytes")) is int,
            "simulator did not consume the identified projection byte count")
    return summary, rows, argv


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window-evidence", type=Path, required=True)
    parser.add_argument("--projection-dir", type=Path, required=True)
    parser.add_argument("--simulator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    report = {"schema_version": 1, "model": "frozen_displayed_window_causal_handoff_v1", "passed": False,
        "scope": "Retrospective bounded model audit; no calibrated fill or strategy P&L claim",
        "raw_source_reopened": False, "runs": [], "errors": [], "checks": {},
        "limitations": ["Raw source SHA-256 is retained from committed prior full-source evidence, not recomputed here",
            "Two retrospectively selected positive fixed-level windows; no statistical strategy sample",
            "Displayed execution volume is not parent aggressor demand or empirical hypothetical fills",
            "Single shadow order, explicit cancellation assumptions, no counterfactual market response",
            "No monotonic relationship between latency and P&L is asserted"]}
    report_requested = args.report.expanduser().absolute()
    require(not os.path.lexists(report_requested), "aggregate report must be a fresh path, including no dangling symlink")
    report_path = report_requested.resolve()
    require(not os.path.lexists(report_path), "aggregate report must be a fresh path")
    require(report_path.parent.is_dir(), "aggregate report parent directory must already exist")
    protected = {}
    source_before = None
    try:
        evidence_path = args.window_evidence.resolve(strict=True)
        projection_dir = args.projection_dir.resolve(strict=True)
        simulator = args.simulator.resolve(strict=True)
        output_requested = args.output.expanduser().absolute()
        require(not os.path.lexists(output_requested), "private output must be fresh, including no dangling symlink")
        output = output_requested.resolve()
        require(not os.path.lexists(output) and output.parent.is_dir(), "private output must be a fresh directory in an existing parent")
        require(not report_path.is_relative_to(output), "aggregate report must be outside the private output directory")
        require(os.access(simulator, os.X_OK) and identity(simulator)[2] > 0, "simulator must be a nonempty executable regular file")
        ignored = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--quiet", str(output)], capture_output=True)
        require(ignored.returncode == 0 and ignored.stderr == b"", "per-event output directory must be ignored by this repository")
        source_before = source_snapshot(ROOT)
        report["source"] = source_before
        for path in (evidence_path, simulator, Path(__file__).resolve()):
            require(path != report_path and not path.is_relative_to(output), "output aliases a protected input artefact")
            protected[path] = (identity(path), file_info(path))
        report["window_evidence"] = anchor_evidence(evidence_path)
        evidence = read_object(evidence_path)
        raw, runs = validate_evidence(evidence)
        report["retained_raw_input_identity"] = raw
        report["projection_producer_commit"] = evidence["source_commit"]
        report["simulator"] = {"path": str(simulator), **file_info(simulator)}
        projections = []
        for run in runs:
            for filename in ("summary.json", "normalised.csv", "provenance.csv", "stderr.txt"):
                path = (projection_dir / run["symbol"] / filename).resolve(strict=True)
                require(path != report_path and not path.is_relative_to(output), "output aliases a protected projection artefact")
                protected[path] = (identity(path), file_info(path))
            selected = read_projection(projection_dir / run["symbol"], run, raw)
            projections.append((run, selected))
        output.mkdir()
        report["private_output"] = str(output)
        for run, selected in projections:
            symbol = run["symbol"]
            for profile, config in matrix(selected["summary"]):
                print(f"Auditing {symbol} {config['cancel_model']} {profile}", flush=True)
                name = f"{symbol}-{config['cancel_model']}-{profile}"
                directory = output / name
                record = {"symbol": symbol, "profile": profile, "configuration": config, "passed": False,
                    "command": command(simulator, selected["files"]["normalised_file"], config, directory / "audit.csv")}
                report["runs"].append(record)
                try:
                    result, rows, _ = execute(simulator, selected["files"]["normalised_file"], config, directory)
                    audit = validate_trace(selected["events"], selected["provenance"], config, result, rows)
                    write_joined(directory / "joined.csv", audit.pop("joined_rows"))
                    record.update(summary=result, causal_audit=audit, passed=True)
                finally:
                    artefacts = {filename: file_info(directory / filename) for filename in
                        ("configuration.json", "process.json", "summary.json", "stderr.txt", "audit.csv", "joined.csv")
                        if (directory / filename).is_file()}
                    for filename in artefacts:
                        path = directory / filename
                        protected[path] = (identity(path), artefacts[filename])
                    record["artefacts"] = artefacts
        require(len(report["runs"]) == 24, "the frozen 24-run matrix is incomplete")
        require(all(run["summary"][account][field] == 0 for run in report["runs"]
                    for account in ("exchange", "local") for field in ("filled", "position", "cash4", "fees4")),
                "the frozen zero-fill handoff baseline changed")
        report["checks"].update(frozen_matrix_complete=True, exact_causal_audits_passed=True,
            every_origin_delivery_and_action_has_source_lineage=True, zero_fill_results_retained=True,
            pending_horizon_and_live_exposure_retained=True, raw_identity_carried_without_rereading=True)
        report["passed"] = True
    except (OSError, ValueError, TypeError, KeyError, OverflowError, UnicodeError, subprocess.SubprocessError) as error:
        report["errors"].append(str(error))
    finally:
        try:
            for path, (before, digest) in protected.items():
                require(identity(path) == before and file_info(path) == digest, "protected handoff artefact changed during audit")
            if source_before is not None:
                require(source_snapshot(ROOT) == source_before, "source checkout changed during handoff audit")
            report["checks"]["source_inputs_tool_and_outputs_unchanged"] = source_before is not None and bool(protected)
        except (OSError, ValueError, TypeError, KeyError, UnicodeError, subprocess.SubprocessError) as error:
            report["passed"] = False
            report["errors"].append(str(error))
        # Publish only after the final clean-source snapshot, so our own new
        # aggregate cannot make a previously clean checkout appear dirty.
        write_json(report_path, report)
    if not report["passed"]:
        print("Handoff audit failed; see the aggregate report and private run logs", file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
