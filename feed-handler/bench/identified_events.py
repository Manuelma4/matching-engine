#!/usr/bin/env python3
"""Validate atomic identified displayed observations and bounded delayed probes.

This is an internal-consistency observer, not a raw-feed adapter or a fill model.
Source-file SHA declarations are deliberately never labelled verified here.
"""
import argparse
from bisect import bisect_right
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import sys

MODEL = "identified_displayed_observations_v1"
U64 = (1 << 64) - 1
U32 = (1 << 32) - 1
TIME_MAX = (1 << 48) - 1
PRICE_MAX = 2_000_000_000
MAX_FACTS = 100_000
MAX_ORDERS = 1_000_000
MAX_SNAPSHOT_ROWS = 1_000_000
MAX_PROBES = 100_000
MAX_LEDGER_BYTES = 64 << 20
MAX_EXPECTED_BYTES = 8 << 20
MAX_REPORT_BYTES = 1 << 20
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX_BYTES = re.compile(r"(?:[0-9a-f]{2})+\Z")
LENGTHS = dict(S=12, R=39, H=25, Y=20, L=26, V=35, W=12, K=28, J=35,
               h=21, A=36, F=40, E=31, C=36, X=23, D=19, U=35, P=44,
               Q=40, B=19, I=50, N=20, O=48)
SUPPORTED = {"A", "F", "E", "C", "X", "D", "U", "P", "Q", "B"}
SOURCE_KEYS = {"sequence", "frame_offset", "frame_end_offset", "timestamp_ns", "body_bytes", "type"}
ORDER_KEYS = {"reference", "side", "price4", "shares", "attribution"}
FACT_KEYS = {"event_index", "source", "source_locate", "tracking_number", "frame_hex", "frame_sha256",
    "kind", "wire", "before_order", "after_order", "derived_removed_shares", "fifo_rank_before",
    "visible_shares_ahead_before", "resolved_resting_price4"}
TOP_KEYS = {"schema_version", "model", "symbol", "locate", "source_identity", "seed", "expected_sources", "facts"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uint(value, minimum=0, maximum=U64):
    return type(value) is int and minimum <= value <= maximum


def exact_object(value, keys, description):
    require(type(value) is dict and set(value) == set(keys), description + " has an invalid field set")


def same(left, right):
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(same(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


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
        parsed = float(value)
        require(math.isfinite(parsed), "non-finite JSON number")
        return parsed

    try:
        return json.loads(text, object_pairs_hook=unique, parse_constant=invalid, parse_float=finite)
    except RecursionError as error:
        raise ValueError("JSON nesting exceeds the parser bound") from error


def encoded_size(value, limit, description):
    try:
        encoded = json.dumps(value, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, RecursionError) as error:
        raise ValueError(description + " is not bounded finite JSON") from error
    require(len(encoded) <= limit, description + " exceeds its byte bound")
    return len(encoded)


def ascii_text(value, length=None):
    return (type(value) is str and (length is None or len(value) == length) and
            all(32 <= ord(character) <= 126 for character in value))


def validate_symbol(symbol, locate):
    require(ascii_text(symbol) and 1 <= len(symbol) <= 8 and symbol.strip(' ') == symbol,
            "selected symbol must be unpadded printable ASCII of length one through eight")
    require(uint(locate, 1, 65535), "invalid selected locate")


def validate_identity(value):
    exact_object(value, {"input_bytes", "input_sha256", "evidence_sha256", "verification"}, "source identity")
    require(uint(value["input_bytes"], 1) and type(value["input_sha256"]) is str and HEX64.fullmatch(value["input_sha256"]),
            "invalid declared source size/hash")
    evidence = value["evidence_sha256"]
    require(evidence is None or (type(evidence) is str and HEX64.fullmatch(evidence)), "invalid declared evidence hash")
    require(value["verification"] == "unverified_by_module", "raw input identity must remain explicitly unverified")


def validate_source(source, input_bytes):
    exact_object(source, SOURCE_KEYS, "source point")
    for key in SOURCE_KEYS - {"type"}:
        require(uint(source[key]), "invalid unsigned source point field")
    require(uint(source["sequence"], 1) and type(source["type"]) is str and source["type"] in LENGTHS and
            source["body_bytes"] == LENGTHS[source["type"]] and source["timestamp_ns"] <= TIME_MAX and
            source["frame_end_offset"] == source["frame_offset"] + source["body_bytes"] + 2 and
            source["frame_end_offset"] <= input_bytes, "source point has an invalid type, clock or frame span")


def validate_order(order):
    exact_object(order, ORDER_KEYS, "displayed order")
    require(uint(order["reference"], 1) and order["side"] in ("B", "S") and type(order["side"]) is str and
            uint(order["price4"], 1, PRICE_MAX) and uint(order["shares"], 1, U32), "invalid displayed order fields")
    attribution = order["attribution"]
    exact_object(attribution, {"kind", "mpid"}, "attribution knowledge")
    require(type(attribution["kind"]) is str and attribution["kind"] in {"unknown", "absent_in_wire", "explicit"},
            "unknown attribution knowledge kind")
    if attribution["kind"] == "explicit":
        require(ascii_text(attribution["mpid"], 4), "explicit MPID must retain four printable ASCII bytes")
    else:
        require(attribution["mpid"] is None, "unknown/absent attribution must have null MPID")


def price_key(order):
    return (0, -order["price4"]) if order["side"] == "B" else (1, order["price4"])


def validate_seed(seed, identity):
    exact_object(seed, {"source", "effective_ns", "boundary", "derived", "orders"}, "seed")
    validate_source(seed["source"], identity["input_bytes"])
    require(uint(seed["effective_ns"], seed["source"]["timestamp_ns"]) and
            seed["boundary"] == "post_source_message" and seed["derived"] is True, "invalid derived exact-prefix seed boundary")
    orders = seed["orders"]
    require(type(orders) is list and len(orders) <= MAX_ORDERS, "seed order count exceeds its bound")
    seen, previous, total = set(), None, 0
    for order in orders:
        validate_order(order)
        require(order["reference"] not in seen, "duplicate seed reference")
        seen.add(order["reference"])
        key = price_key(order)
        require(previous is None or key >= previous, "seed must retain B/S best-price/FIFO grouping")
        previous = key
        total += order["shares"]
        require(total <= U64, "seed aggregate shares exceed uint64")
    return deepcopy(orders), seen


def source_sequence(source, previous, effective_ns, input_bytes):
    validate_source(source, input_bytes)
    require(source["sequence"] > previous["sequence"] and
            source["frame_offset"] >= previous["frame_end_offset"] and
            source["timestamp_ns"] >= max(previous["timestamp_ns"], effective_ns),
            "fact source sequence/span/time does not follow the exact seed prefix")


def expected_list(value, input_bytes):
    require(type(value) is list and len(value) <= MAX_FACTS, "invalid expected-source list bound")
    encoded_size(value, MAX_EXPECTED_BYTES, "expected-source list")
    for source in value:
        validate_source(source, input_bytes)


def parse_frame(frame, source, symbol, locate):
    require(type(frame) is bytes and 2 <= len(frame) <= 46, "fact must carry one bounded complete binary frame")
    length = int.from_bytes(frame[:2], 'big')
    body = frame[2:]
    require(length == len(body) and length >= 11, "frame length prefix disagrees with retained bytes")
    kind = chr(body[0])
    require(kind in SUPPORTED and length == LENGTHS[kind] and
            source["type"] == kind and source["body_bytes"] == length, "unsupported or mismatched identified wire variant")

    def number(at, size):
        return int.from_bytes(body[at:at + size], 'big')

    def alpha(at, size):
        try:
            value = body[at:at + size].decode('ascii')
        except UnicodeError as error:
            raise ValueError("wire alpha field is not ASCII") from error
        require(ascii_text(value, size), "wire alpha field is not printable ASCII")
        return value

    source_locate, tracking = number(1, 2), number(3, 2)
    require(source_locate == locate and number(5, 6) == source["timestamp_ns"], "wire header locate/time disagrees with source identity")
    if kind in {"A", "F", "P"}:
        wire = dict(reference=number(11, 8), side=alpha(19, 1), shares=number(20, 4), stock=alpha(24, 8), price4=number(32, 4))
        require(wire["stock"] == symbol.ljust(8, ' ') and wire["side"] in {"B", "S"} and
                uint(wire["shares"], 1, U32) and uint(wire["price4"], 1, PRICE_MAX), "invalid add/print wire fields")
        if kind == "F":
            wire["mpid"] = alpha(36, 4)
        if kind == "P":
            wire["match"] = number(36, 8)
            require(wire["reference"] == 0 and wire["side"] == "B", "unsupported non-modern P reference/side fields")
        else:
            require(wire["reference"] > 0, "displayed add reference must be positive")
    elif kind in {"E", "C", "X"}:
        wire = dict(reference=number(11, 8), shares=number(19, 4))
        require(wire["reference"] > 0 and wire["shares"] > 0, "invalid named reduction fields")
        if kind in {"E", "C"}:
            wire["match"] = number(23, 8)
        if kind == "C":
            wire.update(printable=alpha(31, 1), execution_price4=number(32, 4))
            require(wire["printable"] in {"Y", "N"} and uint(wire["execution_price4"], 1, PRICE_MAX), "invalid priced execution fields")
    elif kind == "D":
        wire = dict(reference=number(11, 8))
        require(wire["reference"] > 0, "delete reference must be positive")
    elif kind == "U":
        wire = dict(old_reference=number(11, 8), new_reference=number(19, 8), new_shares=number(27, 4), new_price4=number(31, 4))
        require(wire["old_reference"] > 0 and wire["new_reference"] > 0 and wire["new_shares"] > 0 and
                uint(wire["new_price4"], 1, PRICE_MAX), "invalid replacement wire fields")
    elif kind == "Q":
        wire = dict(shares=number(11, 8), stock=alpha(19, 8), price4=number(27, 4), match=number(31, 8), cross_type=alpha(39, 1))
        require(wire["stock"] == symbol.ljust(8, ' ') and wire["cross_type"] in {"O", "C", "H"} and
                uint(wire["price4"], 0 if wire["shares"] == 0 else 1, PRICE_MAX), "unsupported cross context fields")
    else:
        wire = dict(match=number(11, 8))
    return kind, source_locate, tracking, wire


def insert_order(state, order):
    require(len(state) < MAX_ORDERS, "live order count exceeds its bound")
    key = price_key(order)
    index = next((index for index, existing in enumerate(state) if price_key(existing) > key), len(state))
    state.insert(index, order)


def _make_fact(index, source, frame, symbol, locate, state, seen):
    variant, source_locate, tracking, wire = parse_frame(frame, source, symbol, locate)
    total = sum(order["shares"] for order in state)
    require(len(state) <= MAX_ORDERS and len(seen) <= MAX_ORDERS + MAX_FACTS and total <= U64,
            "pre-state live/seen/share bound exceeded")
    before = after = rank = ahead = resting = None
    removed = 0
    if variant in {"A", "F"}:
        reference = wire["reference"]
        require(reference not in seen, "new reference was already seen in the bounded window")
        require(len(seen) < MAX_ORDERS + MAX_FACTS and total + wire["shares"] <= U64,
                "new order exceeds seen-reference or aggregate-share bound")
        after = dict(reference=reference, side=wire["side"], price4=wire["price4"], shares=wire["shares"],
            attribution=dict(kind="explicit" if variant == "F" else "absent_in_wire", mpid=wire.get("mpid")))
        insert_order(state, deepcopy(after))
        seen.add(reference)
        kind = "add"
    elif variant in {"E", "C", "X", "D", "U"}:
        reference = wire["old_reference"] if variant == "U" else wire["reference"]
        position = next((number for number, order in enumerate(state) if order["reference"] == reference), None)
        require(position is not None, "named mutation has no live pre-order")
        before = deepcopy(state[position])
        resting = before["price4"]
        peers = [order for order in state[:position] if order["side"] == before["side"] and order["price4"] == resting]
        rank, ahead = len(peers) + 1, sum(order["shares"] for order in peers)
        if variant == "U":
            require(wire["new_reference"] not in seen, "replacement reference was already seen in the bounded window")
            require(len(seen) < MAX_ORDERS + MAX_FACTS and total - before["shares"] + wire["new_shares"] <= U64,
                    "replacement exceeds seen-reference or aggregate-share bound")
            after = {**deepcopy(before), "reference": wire["new_reference"], "shares": wire["new_shares"], "price4": wire["new_price4"]}
            removed = before["shares"]
            state.pop(position)
            insert_order(state, deepcopy(after))
            seen.add(wire["new_reference"])
            kind = "replace"
        else:
            removed = before["shares"] if variant == "D" else wire["shares"]
            require(0 < removed <= before["shares"], "named reduction exceeds copied pre-order shares")
            if removed == before["shares"]:
                state.pop(position)
            else:
                after = {**deepcopy(before), "shares": before["shares"] - removed}
                state[position] = deepcopy(after)
            kind = "execute_named" if variant in {"E", "C"} else "cancel_named" if variant == "X" else "delete_named"
    else:
        kind = "no_displayed_order_change"
    return dict(event_index=index, source=deepcopy(source), source_locate=source_locate, tracking_number=tracking,
        frame_hex=frame.hex(), frame_sha256=hashlib.sha256(frame).hexdigest(), kind=kind, wire=wire,
        before_order=before, after_order=after, derived_removed_shares=removed, fifo_rank_before=rank,
        visible_shares_ahead_before=ahead, resolved_resting_price4=resting)


def build_ledger(symbol, locate, source_identity, seed, frames, expected_sources):
    validate_symbol(symbol, locate)
    validate_identity(source_identity)
    state, seen = validate_seed(seed, source_identity)
    require(type(frames) is list and len(frames) <= MAX_FACTS, "framed fact count exceeds its bound")
    expected_list(expected_sources, source_identity["input_bytes"])
    require(len(frames) == len(expected_sources), "expected-source coverage differs from framed fact count")
    facts, previous, captured = [], seed["source"], len(state)
    for index, pair in enumerate(frames, 1):
        require(type(pair) in (tuple, list) and len(pair) == 2, "frame input must pair a source point and framed bytes")
        source, frame = pair
        source_sequence(source, previous, seed["effective_ns"], source_identity["input_bytes"])
        require(same(source, expected_sources[index - 1]), "framed source differs from independently expected coverage")
        facts.append(_make_fact(index, source, frame, symbol, locate, state, seen))
        captured += len(state)
        require(captured <= MAX_SNAPSHOT_ROWS, "cumulative source snapshot rows exceed the bound")
        previous = source
    document = dict(schema_version=1, model=MODEL, symbol=symbol, locate=locate, source_identity=deepcopy(source_identity),
                    seed=deepcopy(seed), expected_sources=deepcopy(expected_sources), facts=facts)
    encoded_size(document, MAX_LEDGER_BYTES, "ledger")
    return document


def validate_ledger(document, expected_sources=None):
    encoded_size(document, MAX_LEDGER_BYTES, "ledger")
    exact_object(document, TOP_KEYS, "ledger")
    require(type(document["schema_version"]) is int and document["schema_version"] == 1 and document["model"] == MODEL,
            "unsupported identified observation schema/model")
    symbol, locate, identity, seed = document["symbol"], document["locate"], document["source_identity"], document["seed"]
    validate_symbol(symbol, locate)
    validate_identity(identity)
    state, seen = validate_seed(seed, identity)
    expected_list(document["expected_sources"], identity["input_bytes"])
    if expected_sources is not None:
        expected_list(expected_sources, identity["input_bytes"])
        require(same(document["expected_sources"], expected_sources), "ledger differs from independently expected source list")
    facts = document["facts"]
    require(type(facts) is list and len(facts) <= MAX_FACTS and len(facts) == len(document["expected_sources"]),
            "fact coverage differs from expected source list")
    snapshots = [dict(event_index=0, source=deepcopy(seed["source"]), origin_ns=seed["effective_ns"], orders=deepcopy(state))]
    summary = dict(fact_count=len(facts), seed_orders=len(state), final_orders=0, snapshot_rows=len(state),
                   non_head_executions=0, replacements=0, context_events=0)
    previous = seed["source"]
    for index, fact in enumerate(facts, 1):
        exact_object(fact, FACT_KEYS, "fact")
        source = fact["source"]
        source_sequence(source, previous, seed["effective_ns"], identity["input_bytes"])
        require(same(source, document["expected_sources"][index - 1]), "fact differs from expected source boundary")
        require(type(fact["frame_hex"]) is str and len(fact["frame_hex"]) <= 92 and HEX_BYTES.fullmatch(fact["frame_hex"]),
                "frame hex must use canonical bounded lower-case bytes")
        require(type(fact["frame_sha256"]) is str and HEX64.fullmatch(fact["frame_sha256"]), "frame SHA-256 is malformed")
        frame = bytes.fromhex(fact["frame_hex"])
        expected = _make_fact(index, source, frame, symbol, locate, state, seen)
        require(same(fact, expected), "fact wire, pre/post state or derived diagnostics disagree")
        summary["snapshot_rows"] += len(state)
        require(summary["snapshot_rows"] <= MAX_SNAPSHOT_ROWS, "cumulative source snapshot rows exceed the bound")
        summary["non_head_executions"] += int(expected["kind"] == "execute_named" and expected["fifo_rank_before"] > 1)
        summary["replacements"] += int(expected["kind"] == "replace")
        summary["context_events"] += int(expected["kind"] == "no_displayed_order_change")
        snapshots.append(dict(event_index=index, source=deepcopy(source), origin_ns=source["timestamp_ns"], orders=deepcopy(state)))
        previous = source
    summary["final_orders"] = len(state)
    return dict(passed=True, raw_input_identity_verified=False, snapshots=snapshots, summary=summary)


def observe(document, feed_delay_ns, horizon_ns, probe_times, expected_sources=None):
    require(uint(feed_delay_ns) and uint(horizon_ns), "invalid observation delay/horizon")
    require(type(probe_times) is list and len(probe_times) <= MAX_PROBES and
            all(uint(time, 0, horizon_ns) for time in probe_times), "observation probes exceed their time/count bounds")
    result = validate_ledger(document, expected_sources)
    snapshots = result["snapshots"]
    require(all(snapshot["origin_ns"] <= horizon_ns for snapshot in snapshots), "source/effective seed time exceeds inclusive horizon")
    times, deliveries, pending = [], [], []
    for snapshot in snapshots:
        delivery = snapshot["origin_ns"] + feed_delay_ns
        require(delivery <= U64, "derived delivery clock overflows uint64")
        times.append(delivery)
        metadata = {key: deepcopy(snapshot[key]) for key in ("event_index", "source", "origin_ns")}
        metadata["delivery_ns"] = delivery
        if delivery <= horizon_ns:
            deliveries.append(metadata)
        else:
            pending.append(snapshot["event_index"])
    probes, captured = [], result["summary"]["snapshot_rows"]
    for time in probe_times:
        index = bisect_right(times, time) - 1
        if index < 0:
            probes.append(dict(time_ns=time, available=False, event_index=None, source=None, origin_ns=None, delivery_ns=None, orders=None))
        else:
            snapshot = snapshots[index]
            captured += len(snapshot["orders"])
            require(captured <= MAX_SNAPSHOT_ROWS, "source plus returned probe snapshot rows exceed the bound")
            probes.append(dict(time_ns=time, available=True, event_index=snapshot["event_index"], source=deepcopy(snapshot["source"]),
                origin_ns=snapshot["origin_ns"], delivery_ns=times[index], orders=deepcopy(snapshot["orders"])))
    result.update(feed_delay_ns=feed_delay_ns, horizon_ns=horizon_ns, deliveries=deliveries, probes=probes,
        pending_deliveries=len(pending), pending_event_indices=pending,
        latest_delivered_event_index=deliveries[-1]["event_index"] if deliveries else None, captured_rows=captured)
    return result


def _stat_value(value):
    require(stat.S_ISREG(value.st_mode), "input artefact must be a regular file")
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def stat_identity(path):
    return _stat_value(Path(path).stat())


def _consume_regular(path, maximum, retain):
    before = stat_identity(path)
    require(before[2] <= maximum, "input artefact exceeds its byte bound before reading")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_CLOEXEC", 0))
    try:
        stream = os.fdopen(descriptor, "rb")
    except BaseException:
        os.close(descriptor)
        raise
    digest = hashlib.sha256()
    chunks, consumed = [], 0
    with stream:
        require(_stat_value(os.fstat(stream.fileno())) == before, "input descriptor differs from the checked path")
        while True:
            block = stream.read(min(8 << 20, maximum + 1 - consumed))
            if not block:
                break
            consumed += len(block)
            require(consumed <= maximum, "input artefact grew beyond its byte bound")
            digest.update(block)
            if retain:
                chunks.append(block)
        require(consumed == before[2] and _stat_value(os.fstat(stream.fileno())) == before and
                stat_identity(path) == before, "input artefact changed during descriptor reading")
    return b''.join(chunks) if retain else None, dict(bytes=consumed, sha256=digest.hexdigest())


def file_info(path, maximum=MAX_LEDGER_BYTES):
    return _consume_regular(path, maximum, False)[1]


def read_json(path, limit):
    raw, _ = _consume_regular(path, limit, True)
    return strict_json(raw.decode("utf-8"))


def cli_uint(value):
    require(re.fullmatch(r"(?:0|[1-9][0-9]*)", value) is not None, "CLI clock must be a canonical unsigned integer")
    parsed = int(value)
    require(uint(parsed), "CLI clock exceeds uint64")
    return parsed


class Once(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        seen = getattr(namespace, "_singleton_options", set())
        if self.dest in seen:
            parser.error("duplicate singleton option: " + option_string)
        setattr(namespace, "_singleton_options", seen | {self.dest})
        setattr(namespace, self.dest, values)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    subparsers = parser.add_subparsers(dest="action", required=True)
    for name in ("validate", "observe"):
        command = subparsers.add_parser(name, allow_abbrev=False)
        command.add_argument("ledger", type=Path)
        command.add_argument("--expected-sources", type=Path, action=Once, required=True)
        command.add_argument("--report", type=Path, action=Once, required=True)
        if name == "observe":
            command.add_argument("--feed-delay-ns", type=cli_uint, action=Once, required=True)
            command.add_argument("--horizon-ns", type=cli_uint, action=Once, required=True)
            command.add_argument("--probe-ns", type=cli_uint, action="append", default=[])
    args = parser.parse_args(argv)
    requested = args.report.expanduser().absolute()
    require(not os.path.lexists(requested), "report must be fresh, including no dangling symlink")
    report_path = requested.resolve()
    require(not os.path.lexists(report_path) and report_path.parent.is_dir(), "report requires a fresh path in an existing parent")
    report = dict(schema_version=1, model=MODEL, operation=args.action, passed=False, raw_input_identity_verified=False,
        checks={}, errors=[], limitations=["Internal consistency only; raw SHA declarations and external event coverage are not authenticated by this module",
            "Reconstructed insertion FIFO is not an exchange-priority or fill oracle",
            "No raw adapter, order decisions, trade accounting, hypothetical fills or market response is implemented"])
    tracked = {}
    try:
        paths = {"ledger": args.ledger.expanduser().resolve(strict=True), "expected_sources": args.expected_sources.expanduser().resolve(strict=True)}
        require(len(set(paths.values())) == 2 and report_path not in paths.values(), "report or expected source input aliases ledger")
        limits = {paths["ledger"]: MAX_LEDGER_BYTES, paths["expected_sources"]: MAX_EXPECTED_BYTES,
                  Path(__file__).resolve(): MAX_LEDGER_BYTES}
        for path in paths.values():
            require(stat_identity(path)[2] <= limits[path], "input JSON file exceeds its byte bound before hashing")
        for path, maximum in limits.items():
            tracked[path] = (stat_identity(path), file_info(path, maximum))
        require(tracked[paths["ledger"]][0][:2] != tracked[paths["expected_sources"]][0][:2], "ledger and expected-source inputs alias one inode")
        report["inputs"] = {name: dict(path=str(path), **tracked[path][1]) for name, path in paths.items()}
        report["module"] = dict(path=str(Path(__file__).resolve()), **tracked[Path(__file__).resolve()][1])
        document = read_json(paths["ledger"], MAX_LEDGER_BYTES)
        expected = read_json(paths["expected_sources"], MAX_EXPECTED_BYTES)
        if args.action == "observe":
            result = observe(document, args.feed_delay_ns, args.horizon_ns, args.probe_ns, expected)
            report["observation"] = {"feed_delay_ns": args.feed_delay_ns, "horizon_ns": args.horizon_ns,
                "probe_count": len(result["probes"]), "available_probes": sum(int(probe["available"]) for probe in result["probes"]),
                "delivered_snapshots": len(result["deliveries"]), "pending_deliveries": result["pending_deliveries"],
                "latest_delivered_event_index": result["latest_delivered_event_index"], "captured_rows": result["captured_rows"]}
        else:
            result = validate_ledger(document, expected)
        report["summary"] = result["summary"]
        report["source_identity_declaration"] = deepcopy(document["source_identity"])
        report["checks"].update(exact_wire_and_typed_fields=True, copied_pre_post_and_atomic_replacement=True,
            reconstructed_fifo_and_named_reductions=True, expected_source_list_matches=True,
            attribution_knowledge_preserved=True, raw_identity_explicitly_unverified=True)
        report["passed"] = True
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError) as error:
        report["errors"].append(str(error))
    finally:
        try:
            for path, (before, digest) in tracked.items():
                require(stat_identity(path) == before and file_info(path) == digest, "input artefact or module changed during validation")
            report["checks"]["artefacts_unchanged"] = bool(tracked)
        except (OSError, ValueError, TypeError, UnicodeError) as error:
            report["passed"] = False
            report["errors"].append(str(error))
        publication = (json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + '\n').encode("utf-8")
        require(len(publication) <= MAX_REPORT_BYTES, "aggregate report exceeds its actual serialised byte bound")
        stream = report_path.open("xb")
        opened = os.fstat(stream.fileno())
        owned = (opened.st_dev, opened.st_ino)
        try:
            with stream:
                written = stream.write(publication)
                require(written == len(publication), "aggregate report publication returned a short write")
        except BaseException:
            # A write/close error must not leave an apparently passed report.
            # Remove only the regular file created by this publication attempt.
            try:
                named = report_path.lstat()
                if stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned:
                    report_path.unlink()
            except OSError:
                pass
            raise
    if not report["passed"]:
        print("Identified observation validation failed; see the aggregate report", file=sys.stderr)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
