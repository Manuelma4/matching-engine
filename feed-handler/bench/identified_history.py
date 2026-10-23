#!/usr/bin/env python3
"""Authenticate bounded raw history and reuse independently checked L3 inventories.

The library helpers establish structural consistency. Only the production CLI binds
the fixed repository anchors and freshly hashes the complete raw input before/after.
No external commands from evidence are executed and no fill model is introduced.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import sys


def _sibling(name):
    specification = importlib.util.spec_from_file_location("history_" + name, Path(__file__).with_name(name + ".py"))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


events = _sibling("identified_events")
l3 = _sibling("compare_l3")
handoff = _sibling("audit_handoff")
require, uint, same = events.require, events.uint, events.same
ROOT = Path(__file__).resolve().parent.parent
GATE = "bounded_identified_history_v1"
MAX_WINDOWS = 8
MAX_RAW_BYTES = 64 << 30
MAX_PREFIX_BYTES = 512 << 20
MAX_PREFIX_MESSAGES = 10_000_000
MAX_JSON_BYTES = 8 << 20
MAX_CHECKPOINT_BYTES = 1 << 20
MAX_PROJECTION_BYTES = 64 << 20
MAX_EXPORT_BYTES = 128 << 20
MAX_EXPORT_ROWS = 1_000_000
MAX_REPORT_BYTES = 1 << 20
MAX_SOURCE_BYTES = 16 << 20
CHUNK = 8 << 20
CHECKPOINT_HEADER = ("state_id", "symbol", "locate", *l3.SOURCE_KEYS)
CORE_ORDER_KEYS = {"reference", "side", "price4", "fifo_rank", "shares"}
WINDOW_KEYS = {"window_id", "symbol", "locate", "effective_ns", "end_ns", "seed_source", "expected_sources", "states"}
STOCK_OFFSETS = {**dict.fromkeys("RHYKJhNO", 11), "L": 15, **dict.fromkeys("AFP", 24), "Q": 19, "I": 28}
PINS = {
    "window": ("docs/validation/2026-10-22-window/canonical.json", "daba80ef63a6b1585b16652686cc6568898953d1",
               "1fea28b743676140a4c48d1f774554554fbca4c3211db9ef892d9d1d8d0d1ad7"),
    "l3": ("docs/validation/2026-10-22-l3/canonical.json", "0248264829dca038a936ded493e64e4942a739a2",
           "a4ae84974f0ce09da32af8cd6dfc91c0be0cfd7ed775abf7c5816f5f3d291811"),
}
PROJECTION_NAMES = {"summary.json": "summary_file", "normalised.csv": "normalised_file",
                    "provenance.csv": "provenance_file", "stderr.txt": "stderr"}
L3_NAMES = ("checkpoints.csv", "local.orders.csv", "reference.orders.csv", "local.summary.json",
            "reference.summary.json", "comparison.json")


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def blob_info(blob):
    require(type(blob) is bytes, "artefact must be an immutable byte string")
    return {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def _digest(value):
    return type(value) is str and events.HEX64.fullmatch(value) is not None


def _manifest(blob, manifest, maximum):
    require(type(blob) is bytes and len(blob) <= maximum, "small artefact exceeds its byte bound")
    require(type(manifest) is dict and uint(manifest.get("bytes")) and _digest(manifest.get("sha256")),
            "invalid retained artefact manifest")
    require(blob_info(blob) == {key: manifest[key] for key in ("bytes", "sha256")}, "retained artefact hash/length mismatch")


def _object(blob, maximum=MAX_JSON_BYTES):
    require(type(blob) is bytes and len(blob) <= maximum, "JSON artefact exceeds its byte bound")
    result = events.strict_json(blob.decode('utf-8'))
    require(type(result) is dict, "JSON artefact root must be an object")
    return result


def _table(blob, header, strings, maximum_rows, maximum_bytes):
    require(type(blob) is bytes and len(blob) <= maximum_bytes, "CSV artefact exceeds its byte bound")
    require(blob.count(b'\n') <= maximum_rows + 1, "CSV row bound exceeded before parsing")
    text = blob.decode('ascii')
    require('"' not in text and all(32 <= ord(character) <= 126 or character in '\r\n' for character in text) and
            '\r' not in text.replace('\r\n', ''), "invalid CSV physical encoding")
    require(text.endswith('\n'), "CSV must end with a complete physical row")
    lines = text.splitlines()
    require(lines and tuple(lines[0].split(',')) == tuple(header), "CSV header mismatch")
    require(len(lines) - 1 <= maximum_rows, "CSV row bound exceeded")
    result = []
    for line in lines[1:]:
        require(0 < len(line) <= 2048, "CSV physical row exceeds its bound")
        fields = line.split(',')
        require(len(fields) == len(header), "CSV column count mismatch")
        row = {}
        for key, value in zip(header, fields):
            if key in strings:
                require(bool(value), "empty CSV text field")
                row[key] = value
            else:
                require(l3.UINT_TEXT.fullmatch(value) is not None, "noncanonical unsigned CSV field")
                number = int(value)
                require(uint(number), "CSV unsigned field exceeds uint64")
                row[key] = number
        result.append(row)
    return result


def _orders(orders):
    """Validate an exact ordered inventory, including each per-price FIFO rank."""
    require(type(orders) is list and len(orders) <= MAX_EXPORT_ROWS, "inventory exceeds its row bound")
    previous, references, shares = None, set(), 0
    for order in orders:
        events.exact_object(order, CORE_ORDER_KEYS, "independent order")
        require(type(order['side']) is str and order['side'] in {'B', 'S'} and
                uint(order['reference'], 1) and uint(order['shares'], 1, events.U32) and
                uint(order['price4'], 1, events.PRICE_MAX) and uint(order['fifo_rank'], 1, MAX_EXPORT_ROWS),
                "independent inventory exceeds observer field domains")
        require(order['reference'] not in references, "duplicate independent reference")
        references.add(order['reference'])
        key = events.price_key(order)
        require(previous is None or key >= events.price_key(previous), "inventory is not best-price B/S ordered")
        at_level = previous is not None and key == events.price_key(previous)
        require(order['fifo_rank'] == (previous['fifo_rank'] + 1 if at_level else 1), "inventory FIFO rank is not consecutive")
        shares += order['shares']
        require(shares <= events.U64, "inventory aggregate shares exceed uint64")
        previous = order


def validate_binding(binding):
    """Validate/copy an admitted synthetic or anchored binding; this hashes no file."""
    events.exact_object(binding, {"input_identity", "retained_prefix", "windows"}, "history binding")
    raw, prefix = binding['input_identity'], binding['retained_prefix']
    for identity in (raw, prefix):
        events.exact_object(identity, {'bytes', 'sha256'}, "binding identity")
        require(uint(identity['bytes'], 1, MAX_RAW_BYTES) and _digest(identity['sha256']), "invalid binding byte/hash identity")
    require(prefix['bytes'] <= min(raw['bytes'], MAX_PREFIX_BYTES), "retained prefix exceeds input/scan bound")
    windows = binding['windows']
    require(type(windows) is list and 1 <= len(windows) <= MAX_WINDOWS, "invalid admitted window count")
    identities, state_ids, state_points, total_rows = set(), set(), [], 0
    previous_seed = 0
    by_source = {}
    for index, window in enumerate(windows, 1):
        events.exact_object(window, WINDOW_KEYS, "admitted window")
        require(uint(window['window_id'], 1) and window['window_id'] == index, "window ids must be consecutive in seed order")
        events.validate_symbol(window['symbol'], window['locate'])
        require(window['symbol'] not in identities and window['locate'] not in identities, "duplicate selected symbol/locate")
        identities.update((window['symbol'], window['locate']))
        events.validate_source(window['seed_source'], raw['bytes'])
        seed = window['seed_source']
        require(seed['sequence'] > previous_seed, "windows must be ordered by ascending global seed sequence")
        previous_seed = seed['sequence']
        require(uint(window['effective_ns'], seed['timestamp_ns'], events.TIME_MAX) and
                uint(window['end_ns'], window['effective_ns'] + 1, events.TIME_MAX), "invalid effective window bounds")
        expected = window['expected_sources']
        events.expected_list(expected, raw['bytes'])
        previous = seed
        for source in expected:
            events.source_sequence(source, previous, window['effective_ns'], raw['bytes'])
            require(window['effective_ns'] < source['timestamp_ns'] <= window['end_ns'], "expected source outside strict-start/inclusive-end window")
            require(source['type'] in events.SUPPORTED, "expected source has unsupported identified variant")
            previous = source
        states = window['states']
        require(type(states) is list and len(states) == len(expected) + 1, "independent state coverage must include seed and every fact")
        for state, source in zip(states, [seed, *expected]):
            events.exact_object(state, {'state_id', 'source', 'orders'}, "bound independent state")
            require(uint(state['state_id'], 1, l3.MAX_STATES) and state['state_id'] not in state_ids, "duplicate or invalid checkpoint state id")
            state_ids.add(state['state_id'])
            require(same(state['source'], source), "independent state/source request mismatch")
            _orders(state['orders'])
            total_rows += len(state['orders'])
            require(total_rows <= MAX_EXPORT_ROWS, "combined independent inventories exceed row bound")
            state_points.append((source['sequence'], state['state_id'], source))
            sequence = source['sequence']
            known_source, known_refs = by_source.setdefault(sequence, (source, set()))
            require(same(known_source, source), "same global sequence has conflicting source identity")
            refs = {order['reference'] for order in state['orders']}
            require(not (known_refs & refs), "reference is shared across symbols at the same source boundary")
            known_refs.update(refs)
    state_points.sort()
    require([point[1] for point in state_points] == list(range(1, len(state_points) + 1)), "checkpoint ids do not follow global source order")
    previous = None
    for _, _, source in state_points:
        require(previous is None or (same(previous, source) if previous['sequence'] == source['sequence'] else
                source['timestamp_ns'] >= previous['timestamp_ns'] and source['frame_offset'] >= previous['frame_end_offset']),
                "combined checkpoint source clocks/spans regress")
        previous = source
    require(state_points[-1][2]['frame_end_offset'] == prefix['bytes'], "retained prefix does not end at the final requested state")
    return deepcopy(binding)


def _passed(report, description):
    require(type(report) is dict and type(report.get('schema_version')) is int and report['schema_version'] == 1 and
            report.get('passed') is True and type(report.get('errors')) is list and report['errors'] == [], description + " is not passed version one")
    checks = report.get('checks')
    require(type(checks) is dict and bool(checks) and all(type(value) is bool and value for value in checks.values()), description + " has absent/failed checks")


def _export(summary_blob, orders_blob):
    """The existing L3 export contract, applied to already bounded immutable bytes."""
    summary = _object(summary_blob)
    events.exact_object(summary, {'schema_version', 'boundary', 'input_bytes', 'scanned_messages', 'consumed_prefix_bytes',
        'validation_scope', 'validation', 'states', 'passed'}, "L3 summary")
    require(type(summary['schema_version']) is int and summary['schema_version'] == 1 and summary['passed'] is True and
            summary['boundary'] == 'post_message' and type(summary['validation_scope']) is str and summary['validation_scope'] in l3.SCOPES,
            "invalid L3 summary version/scope/boundary")
    require(all(uint(summary[key], 1) for key in ('input_bytes', 'scanned_messages', 'consumed_prefix_bytes')) and
            summary['consumed_prefix_bytes'] <= summary['input_bytes'], "invalid L3 prefix counters")
    events.exact_object(summary['validation'], l3.VALIDATION_KEYS, "L3 validation counters")
    require(all(type(value) is int and value == 0 for value in summary['validation'].values()), "nonzero or untyped L3 validation counter")
    states = summary['states']
    require(type(states) is list and 1 <= len(states) <= l3.MAX_STATES, "invalid L3 state coverage")
    rows = _table(orders_blob, l3.ORDER_HEADER, {'side'}, MAX_EXPORT_ROWS, MAX_EXPORT_BYTES)
    grouped = {index: [] for index in range(1, len(states) + 1)}
    previous_id = 0
    for row in rows:
        state_id = row.pop('state_id')
        require(uint(state_id, 1, len(states)) and state_id >= previous_id, "L3 CSV state order/domain mismatch")
        grouped[state_id].append(row)
        previous_id = state_id
    coverage = dict(states=len(states), order_rows=len(rows), empty_sides=0, empty_books=0,
                    both_sided_states=0, deep_multiorder_states=0, levels=0, shares=0)
    previous = None
    symbols, locates, selected, by_source = {}, {}, set(), {}
    flat = []
    for index, state in enumerate(states, 1):
        events.exact_object(state, {'state_id', 'symbol', 'locate', 'source', 'bid', 'ask', 'exported_orders', 'complete'}, "L3 state")
        require(uint(state['state_id'], 1) and state['state_id'] == index and state['complete'] is True, "incomplete or out-of-order L3 state")
        require(type(state['symbol']) is str and l3.SYMBOL.fullmatch(state['symbol']) is not None and uint(state['locate'], 1, 65535), "invalid L3 selected identity")
        require(symbols.setdefault(state['symbol'], state['locate']) == state['locate'] and locates.setdefault(state['locate'], state['symbol']) == state['symbol'], "L3 symbol/locate mapping changes")
        source = state['source']
        events.validate_source(source, summary['input_bytes'])
        require(source['sequence'] <= summary['scanned_messages'] and source['frame_end_offset'] <= summary['consumed_prefix_bytes'], "L3 state exceeds prefix")
        require((state['symbol'], source['sequence']) not in selected, "duplicate L3 request")
        selected.add((state['symbol'], source['sequence']))
        if previous:
            require(source['timestamp_ns'] >= previous['timestamp_ns'] and
                    ((same(source, previous)) if source['sequence'] == previous['sequence'] else
                     source['sequence'] > previous['sequence'] and source['frame_offset'] >= previous['frame_end_offset']), "L3 source order regresses")
        previous = source
        inventory = grouped[index]
        _orders(inventory)
        known_source, refs = by_source.setdefault(source['sequence'], (source, set()))
        require(same(known_source, source) and not (refs & {order['reference'] for order in inventory}), "cross-symbol L3 source/ref conflict")
        refs.update(order['reference'] for order in inventory)
        require(uint(state['exported_orders']) and state['exported_orders'] == len(inventory), "L3 complete order count mismatch")
        sides = []
        for name, code in (('bid', 'B'), ('ask', 'S')):
            actual_rows = [order for order in inventory if order['side'] == code]
            actual = dict(orders=len(actual_rows), levels=sum(order['fifo_rank'] == 1 for order in actual_rows),
                shares=sum(order['shares'] for order in actual_rows), best_price4=actual_rows[0]['price4'] if actual_rows else None)
            events.exact_object(state[name], actual, "L3 side counts")
            require(same(state[name], actual) and actual['shares'] <= events.U64, "L3 rows/side manifest mismatch")
            coverage['empty_sides'] += int(not actual_rows)
            coverage['levels'] += actual['levels']
            coverage['shares'] += actual['shares']
            sides.append(actual)
        both = all(side['orders'] > 0 for side in sides)
        coverage['both_sided_states'] += int(both)
        coverage['empty_books'] += int(not inventory)
        coverage['deep_multiorder_states'] += int(both and any(side['levels'] > 1 for side in sides) and any(order['fifo_rank'] > 1 for order in inventory))
        flat.extend(dict(state_id=index, **order) for order in inventory)
    require(previous['sequence'] == summary['scanned_messages'] and previous['frame_end_offset'] == summary['consumed_prefix_bytes'], "L3 prefix does not end at last request")
    require(coverage['deep_multiorder_states'] > 0, "L3 evidence lacks populated deep/FIFO coverage")
    return dict(summary=summary, orders=flat, coverage=coverage)


def bind_inputs(window_report, l3_report, projection_blobs, l3_blobs):
    """Bind authenticated small byte strings to complete source requests/inventories.

    This pure helper does not grant repository trust or authenticate a raw file.
    The production entry point supplies bytes pinned to accepted Git evidence.
    """
    _passed(window_report, "window evidence")
    _passed(l3_report, "L3 evidence")
    require(window_report.get('source_clean_at_launch') is True and
            type(window_report.get('source_commit')) is str and re.fullmatch('[0-9a-f]{40}', window_report['source_commit']), "invalid retained window producer identity")
    require(l3_report.get('gate') == 'independent_displayed_order_fifo_v1', "unsupported L3 evidence gate")
    raw = window_report.get('input')
    require(type(raw) is dict and uint(raw.get('bytes'), 1, MAX_RAW_BYTES) and _digest(raw.get('sha256_before')) and
            same(raw.get('sha256_before'), raw.get('sha256_after')), "retained raw identity does not agree")
    before, after = l3_report.get('input_before'), l3_report.get('input_after')
    require(type(before) is dict and set(before) == {'bytes', 'sha256', 'prefix_bytes', 'prefix_sha256'} and same(before, after), "L3 before/after identity disagrees")
    require(same(before['bytes'], raw['bytes']) and same(before['sha256'], raw['sha256_before']) and
            uint(before['prefix_bytes'], 1, MAX_PREFIX_BYTES) and _digest(before['prefix_sha256']), "window/L3 raw identity crosslink mismatch")
    crosslink = l3_report.get('window_evidence')
    # The reports were decoded from authenticated bytes; canonical JSON is not
    # substituted for their original byte identity at the production boundary.
    require(type(crosslink) is dict and _digest(crosslink.get('sha256')) and uint(crosslink.get('bytes'), 1) and
            crosslink.get('matches_head_blob') is True, "invalid L3/window evidence crosslink")
    require(type(l3_blobs) is dict and set(l3_blobs) == set(L3_NAMES), "missing/extra L3 artefact blobs")
    artefacts = l3_report.get('artefacts')
    require(type(artefacts) is dict and set(artefacts) == set(L3_NAMES) - {'checkpoints.csv'}, "invalid L3 artefact manifest set")
    for name, blob in l3_blobs.items():
        require(type(blob) is bytes, "L3 artefact must be an immutable byte string")
        maximum = MAX_CHECKPOINT_BYTES if name == 'checkpoints.csv' else MAX_EXPORT_BYTES if name.endswith('.csv') else MAX_JSON_BYTES
        if name.endswith('.csv'):
            require(blob.count(b'\n') <= (l3.MAX_STATES if name == 'checkpoints.csv' else MAX_EXPORT_ROWS) + 1,
                    "CSV row bound exceeded before retained hashing")
        _manifest(blob, l3_report['checkpoints'] if name == 'checkpoints.csv' else artefacts[name], maximum)
    local = _export(l3_blobs['local.summary.json'], l3_blobs['local.orders.csv'])
    reference = _export(l3_blobs['reference.summary.json'], l3_blobs['reference.orders.csv'])
    require(len(local['orders']) + len(reference['orders']) <= MAX_EXPORT_ROWS, "combined supplied order exports exceed row bound")
    comparison = l3.compare_exports(local, reference)
    require(comparison['passed'] is True, "complete local/reference L3 inventories disagree")
    stored_comparison = _object(l3_blobs['comparison.json'])
    _passed(stored_comparison, "retained L3 comparison")
    require(all(same(stored_comparison.get(key), value) for key, value in comparison.items()) and
            same(l3_report.get('comparison'), stored_comparison), "retained L3 comparison aggregate disagrees")
    require(reference['summary']['input_bytes'] == raw['bytes'] and
            reference['summary']['consumed_prefix_bytes'] == before['prefix_bytes'], "retained prefix/L3 summary mismatch")
    checkpoints = _table(l3_blobs['checkpoints.csv'], CHECKPOINT_HEADER, {'symbol', 'type'}, l3.MAX_STATES, MAX_CHECKPOINT_BYTES)
    require(len(checkpoints) == len(reference['summary']['states']), "checkpoint list and state manifest coverage differ")
    for checkpoint, state in zip(checkpoints, reference['summary']['states']):
        require(same(checkpoint, {key: state[key] for key in ('state_id', 'symbol', 'locate')} | state['source']), "checkpoint request does not match complete L3 manifest")
    runs = window_report.get('runs')
    require(type(runs) is list and 1 <= len(runs) <= MAX_WINDOWS and all(type(run) is dict for run in runs), "invalid window run coverage")
    require(type(projection_blobs) is dict and len(projection_blobs) == len(runs), "projection symbol coverage mismatch")
    inventories = {}
    for row in reference['orders']:
        inventories.setdefault(row['state_id'], []).append({key: row[key] for key in CORE_ORDER_KEYS})
    windows, requests = [], []
    for run in runs:
        symbol = run.get('symbol')
        require(type(symbol) is str and l3.SYMBOL.fullmatch(symbol) and symbol in projection_blobs, "invalid projection symbol identity")
        blobs = projection_blobs[symbol]
        require(type(blobs) is dict and set(blobs) == set(PROJECTION_NAMES), "missing/extra projection blobs")
        for name, manifest_key in PROJECTION_NAMES.items():
            require(type(blobs[name]) is bytes, "projection artefact must be an immutable byte string")
            if name.endswith('.csv'):
                require(blobs[name].count(b'\n') <= events.MAX_FACTS + 1, "projection row bound exceeded before retained hashing")
            _manifest(blobs[name], run.get(manifest_key), MAX_JSON_BYTES if name.endswith('.json') else MAX_PROJECTION_BYTES)
        require(blobs['stderr.txt'] == b'' and type(run.get('exit_code')) is int and run['exit_code'] == 0, "retained projection process failed or had diagnostics")
        summary = _object(blobs['summary.json'])
        require(same(summary, run.get('summary')) and summary.get('passed') is True and summary.get('source_identity_stable') is True and
                type(summary.get('schema_version')) is int and summary['schema_version'] == 1 and summary.get('model') == 'strict_displayed_window_v1', "retained projection summary mismatch")
        for key in ('price4', 'start_ns', 'end_ns', 'max_orders', 'max_levels', 'locate', 'source_messages', 'source_end_records',
                    'source_bytes', 'reconciled_messages', 'displayed_executed_shares', 'final_quantity', 'final_opposite_price4',
                    'final_opposite_quantity', 'normalised_rows', 'provenance_rows'):
            require(uint(summary.get(key)), "invalid projection summary unsigned field")
        require(summary.get('symbol') == symbol and summary.get('side') in {'buy', 'sell'} and
                summary['source_bytes'] == raw['bytes'] and uint(summary['price4'], 1, handoff.LIMIT) and
                uint(summary['locate'], 1, 65535) and uint(summary['max_orders'], 1, 4_194_304) and
                uint(summary['max_levels'], 1, 2_097_152) and 0 <= summary['start_ns'] < summary['end_ns'] <= events.TIME_MAX,
                "projection bounds/identity invalid")
        require(same(run.get('configuration'), {key: summary[key] for key in ('side', 'price4', 'start_ns', 'end_ns')}), "projection configuration mismatch")
        census = summary.get('source_type_counts')
        require(type(census) is dict and all(key in events.LENGTHS and uint(count, 1) for key, count in census.items()) and
                sum(census.values()) == summary['source_messages'] and summary['source_end_records'] <= 1 and
                sum((events.LENGTHS[key] + 2) * count for key, count in census.items()) + 2 * summary['source_end_records'] == raw['bytes'], "full-source projection census mismatch")
        census = summary.get('window_type_counts')
        require(type(census) is dict and all(key in events.LENGTHS and uint(count, 1) for key, count in census.items()),
                "invalid typed selected-window census")
        comparison = run.get('comparison')
        require(type(comparison) is dict and all(uint(comparison.get(key)) for key in ('different_states', 'compared_states', 'seed_states', 'post_source_message_states')) and
                comparison['different_states'] == 0 and comparison['compared_states'] == summary['provenance_rows'] and comparison['seed_states'] == 1 and
                comparison['post_source_message_states'] == summary['reconciled_messages'] and
                same(comparison.get('compared_bbo_fields'), ['same_price4', 'same_quantity', 'opposite_price4', 'opposite_quantity']) and
                same(comparison.get('source_identity_fields'), list(handoff.SOURCE_HEADER)) and
                comparison.get('all_normalised_rows_have_source_delta_provenance') is True and comparison.get('same_price_fixed_and_both_quotes_positive') is True,
                "retained projection independent comparison failed")
        normalised = _table(blobs['normalised.csv'], handoff.EVENT_HEADER, {'kind'}, events.MAX_FACTS, MAX_PROJECTION_BYTES)
        provenance = _table(blobs['provenance.csv'], handoff.PROVENANCE_HEADER, {'type', 'reason'}, events.MAX_FACTS, MAX_PROJECTION_BYTES)
        handoff.validate_events(normalised, dict(horizon_ns=summary['end_ns'], side=summary['side'], price4=summary['price4'], feed_delay_ns=0, response_delay_ns=0))
        require(normalised[0]['timestamp_ns'] == summary['start_ns'], "projection effective seed time mismatch")
        handoff.validate_provenance(normalised, provenance, summary)
        eligibility = summary.get('eligibility')
        require(type(eligibility) is dict and eligibility.get('operational_action') in {'?', 'T'} and
                eligibility.get('retail_interest') in {'?', 'N'}, "retained seed eligibility is unsupported")
        for key, kind in (('directory', 'R'), ('trading_action', 'H'), ('market_hours', 'S'), ('opening_cross', 'Q'), ('operational', 'h')):
            point = eligibility.get(key)
            if key == 'operational' and point is None:
                require(eligibility['operational_action'] == '?', "absent operational metadata has an invented action")
                continue
            require(type(point) is dict and set(point) == set(handoff.SOURCE_HEADER) and point.get('type') == kind,
                    "retained eligibility lacks an exact source point")
            require(all(uint(point[field]) for field in handoff.SOURCE_HEADER if field != 'type') and
                    0 < point['sequence'] <= provenance[0]['sequence'] and point['timestamp_ns'] <= summary['start_ns'] and
                    point['body_bytes'] == events.LENGTHS[kind] and point['frame_offset'] + point['body_bytes'] <=
                    provenance[0]['frame_offset'] + provenance[0]['body_bytes'], "retained eligibility lies outside the seed boundary")
        points = [{**{key: row[key] for key in handoff.SOURCE_HEADER}, 'frame_end_offset': row['frame_offset'] + row['body_bytes'] + 2} for row in provenance]
        states = []
        for point in points:
            matches = [state for state in reference['summary']['states'] if state['symbol'] == symbol and same(state['source'], point)]
            require(len(matches) == 1 and matches[0]['locate'] == summary['locate'], "projection source does not identify one independent state")
            state_id = matches[0]['state_id']
            requests.append(state_id)
            states.append(dict(state_id=state_id, source=point, orders=inventories.get(state_id, [])))
        windows.append(dict(window_id=0, symbol=symbol, locate=summary['locate'], effective_ns=summary['start_ns'], end_ns=summary['end_ns'],
                            seed_source=points[0], expected_sources=points[1:], states=states))
    require(sorted(requests) == list(range(1, len(checkpoints) + 1)), "anchored source list does not cover exactly the retained checkpoint requests")
    windows.sort(key=lambda window: window['seed_source']['sequence'])
    for index, window in enumerate(windows, 1):
        window['window_id'] = index
    return validate_binding(dict(input_identity=dict(bytes=raw['bytes'], sha256=raw['sha256_before']),
        retained_prefix=dict(bytes=before['prefix_bytes'], sha256=before['prefix_sha256']), windows=windows))


def scan_prefix(stream, binding):
    """Scan actual frames from byte zero through a strictly later global witness.

    ``stream`` supplies bytes via read(n), e.g. an io.BytesIO in a hand fixture.
    Its descriptor identity and whole-file hashing are orchestration concerns.
    Every selected-locate frame is enumerated before supported-type filtering.
    """
    binding = validate_binding(binding)
    windows = binding['windows']
    input_bytes = binding['input_identity']['bytes']
    maximum_end = max(window['end_ns'] for window in windows)
    selected = {window['locate']: window for window in windows}
    padded = {window['symbol'].encode('ascii').ljust(8, b' '): window for window in windows}
    directories = set()
    results = [dict(window_id=window['window_id'], seed_source=None, seed_next_source=None, closing_witness=None, frames=[])
               for window in windows]
    seed_sequences = {window['seed_source']['sequence']: index for index, window in enumerate(windows)}
    sequence = offset = fetched = 0
    previous_time = 0
    buffer, cursor = b'', 0
    digest = hashlib.sha256()

    def fill(minimum):
        nonlocal buffer, cursor, fetched
        if len(buffer) - cursor >= minimum:
            return
        digest.update(buffer[:cursor])
        buffer = buffer[cursor:]
        cursor = 0
        while len(buffer) < minimum:
            amount = min(CHUNK, MAX_PREFIX_BYTES - fetched, input_bytes - fetched)
            require(amount > 0, "framing scan reached input/prefix bound before closing witness")
            chunk = stream.read(amount)
            require(type(chunk) is bytes and 0 < len(chunk) <= amount, "EOF/truncated frame before required closing witness")
            fetched += len(chunk)
            buffer += chunk

    while True:
        # At most one small incomplete frame is carried between bounded chunks.
        fill(2)
        length = int.from_bytes(buffer[cursor:cursor + 2], 'big')
        require(length != 0, "zero-length end record before required closing witness")
        require(11 <= length <= max(events.LENGTHS.values()), "invalid global frame body length")
        frame_bytes = length + 2
        fill(frame_bytes)
        body_at = cursor + 2
        kind = chr(buffer[body_at])
        require(kind in events.LENGTHS and length == events.LENGTHS[kind], "unknown global type or wrong body length")
        locate = int.from_bytes(buffer[body_at + 1:body_at + 3], 'big')
        timestamp = int.from_bytes(buffer[body_at + 5:body_at + 11], 'big')
        require(timestamp >= previous_time, "global source timestamp regression")
        previous_time = timestamp
        sequence += 1
        require(sequence <= MAX_PREFIX_MESSAGES and offset + frame_bytes <= MAX_PREFIX_BYTES, "framing scan exceeds message/byte bound")
        point = None

        def source_point():
            return dict(sequence=sequence, frame_offset=offset, frame_end_offset=offset + frame_bytes,
                        timestamp_ns=timestamp, body_bytes=length, type=kind)

        window = selected.get(locate)
        if kind == 'R':
            stock = buffer[body_at + 11:body_at + 19]
            named = padded.get(stock)
            if window is not None or named is not None:
                require(window is not None and named is window and buffer[body_at + 29] == ord('P') and
                        window['window_id'] not in directories and sequence < window['seed_source']['sequence'],
                        "conflicting/remapped/non-production selected directory")
                directories.add(window['window_id'])
        if kind in STOCK_OFFSETS:
            stock_at = body_at + STOCK_OFFSETS[kind]
            named = padded.get(buffer[stock_at:stock_at + 8])
            if named is not None and sequence > named['seed_source']['sequence'] and timestamp <= named['end_ns']:
                require(locate == named['locate'], "selected in-window wire stock carries a conflicting locate")
            if window is not None and sequence > window['seed_source']['sequence'] and timestamp <= window['end_ns']:
                require(buffer[stock_at:stock_at + 8] == window['symbol'].encode('ascii').ljust(8, b' '), "selected wire stock does not match its locate")
        if sequence in seed_sequences:
            index = seed_sequences[sequence]
            admitted = windows[index]
            point = source_point()
            require(same(point, admitted['seed_source']), "actual global seed SourcePoint mismatch")
            require(admitted['window_id'] in directories, "selected production directory was not observed before seed")
            results[index]['seed_source'] = point
        for index, admitted in enumerate(windows):
            result = results[index]
            if sequence == admitted['seed_source']['sequence'] + 1:
                point = point or source_point()
                require(timestamp > admitted['effective_ns'], "seed is stale: next global frame remains at/before effective start")
                result['seed_next_source'] = point
            if timestamp > admitted['end_ns'] and result['closing_witness'] is None:
                point = point or source_point()
                require(result['seed_source'] is not None, "closing witness precedes admitted seed")
                result['closing_witness'] = point
            if locate == admitted['locate'] and sequence > admitted['seed_source']['sequence'] and timestamp <= admitted['end_ns']:
                require(result['seed_source'] is not None and timestamp > admitted['effective_ns'], "selected frame precedes complete seed boundary")
                point = point or source_point()
                require(kind in events.SUPPORTED, "unsupported selected in-window message cannot be omitted")
                require(len(result['frames']) < events.MAX_FACTS, "selected fact count exceeds observer bound")
                result['frames'].append((point, bytes(buffer[cursor:cursor + frame_bytes])))
        cursor += frame_bytes
        offset += frame_bytes
        if timestamp > maximum_end:
            digest.update(buffer[:cursor])
            break
    for admitted, result in zip(windows, results):
        require(result['seed_source'] is not None and result['seed_next_source'] is not None and result['closing_witness'] is not None,
                "missing seed or whole-group/end witness")
        require(same([point for point, _ in result['frames']], admitted['expected_sources']), "fresh selected coverage differs from independently anchored source list")
    return dict(scanned_messages=sequence, scan_prefix_bytes=offset, scan_prefix_sha256=digest.hexdigest(), windows=results)


def observation_profiles(window):
    origin_times = [window['effective_ns'], *[source['timestamp_ns'] for source in window['expected_sources']]]
    horizon = window['end_ns']
    for name, delay in (('zero', 0), ('one_ms', 1_000_000), ('undelivered', horizon - window['effective_ns'] + 1)):
        require(all(uint(time + delay) for time in origin_times), "delayed source clock overflows uint64")
        probes = sorted({*origin_times, horizon, *[time + delay for time in origin_times if time + delay <= horizon]})
        require(len(probes) <= events.MAX_PROBES, "observation probe count exceeds bound")
        yield name, delay, probes


def _ranked(orders):
    result, previous, rank = [], None, 0
    for order in orders:
        key = events.price_key(order)
        rank = rank + 1 if key == previous else 1
        result.append({**{field: order[field] for field in CORE_ORDER_KEYS - {'fifo_rank'}}, 'fifo_rank': rank})
        previous = key
    return result


def build_window(binding, scan_window, include_observations=True, *, evidence_sha256=None):
    """Build twice and compare every complete post-state with retained CSV orders.

    Returned ledger/source declarations remain explicitly unverified by the logical
    module. Production writes profiles sequentially via include_observations=False.
    """
    binding = validate_binding(binding)
    require(type(include_observations) is bool, "include_observations must be a boolean")
    require(evidence_sha256 is None or _digest(evidence_sha256), "invalid retained evidence SHA-256")
    require(type(scan_window) is dict and set(scan_window) == {'window_id', 'seed_source', 'seed_next_source', 'closing_witness', 'frames'}, "invalid scanned window fields")
    require(uint(scan_window['window_id'], 1, len(binding['windows'])), "invalid scanned window id")
    window = binding['windows'][scan_window['window_id'] - 1]
    require(same(scan_window['seed_source'], window['seed_source']), "scanned seed differs from admitted seed")
    for key in ('seed_next_source', 'closing_witness'):
        events.validate_source(scan_window[key], binding['input_identity']['bytes'])
    require(scan_window['seed_next_source']['sequence'] == window['seed_source']['sequence'] + 1 and
            scan_window['seed_next_source']['frame_offset'] == window['seed_source']['frame_end_offset'] and
            scan_window['seed_next_source']['timestamp_ns'] > window['effective_ns'] and
            scan_window['closing_witness']['timestamp_ns'] > window['end_ns'], "invalid scanned seed/end witnesses")
    frames = scan_window['frames']
    require(type(frames) is list and all(type(pair) in (tuple, list) and len(pair) == 2 for pair in frames) and
            same([pair[0] for pair in frames], window['expected_sources']), "scanned frames do not match anchored expected list")
    seed = dict(source=window['seed_source'], effective_ns=window['effective_ns'], boundary='post_source_message', derived=True,
                orders=[{**{key: order[key] for key in CORE_ORDER_KEYS - {'fifo_rank'}}, 'attribution': {'kind': 'unknown', 'mpid': None}}
                        for order in window['states'][0]['orders']])
    identity = dict(input_bytes=binding['input_identity']['bytes'], input_sha256=binding['input_identity']['sha256'],
                    evidence_sha256=evidence_sha256, verification='unverified_by_module')
    document = events.build_ledger(window['symbol'], window['locate'], identity, seed, frames, window['expected_sources'])
    first = canonical_bytes(document)
    require(len(first) <= events.MAX_LEDGER_BYTES, "canonical ledger exceeds byte bound")
    second = events.build_ledger(window['symbol'], window['locate'], identity, seed, frames, window['expected_sources'])
    require(first == canonical_bytes(second), "independent ledger constructions are not byte deterministic")
    del second
    validation = events.validate_ledger(document, window['expected_sources'])
    joins = []
    require(len(validation['snapshots']) == len(window['states']), "generated independent state coverage mismatch")
    for snapshot, state in zip(validation['snapshots'], window['states']):
        require(same(snapshot['source'], state['source']) and same(_ranked(snapshot['orders']), state['orders']), "complete generated inventory differs from independent post-message state")
        joins.append(dict(event_index=snapshot['event_index'], state_id=state['state_id'], source=state['source'], compared_orders=len(state['orders']), matched=True))
    observations = []
    if include_observations:
        captured = 0
        for name, delay, probes in observation_profiles(window):
            result = events.observe(document, delay, window['end_ns'], probes, window['expected_sources'])
            captured += result['captured_rows']
            require(captured <= events.MAX_SNAPSHOT_ROWS, "combined returned observations exceed captured inventory row bound")
            observations.append(dict(profile=name, feed_delay_ns=delay, result=result))
    summary = dict(window_id=window['window_id'], symbol=window['symbol'], locate=window['locate'], effective_ns=window['effective_ns'],
        end_ns=window['end_ns'], seed_orders=len(seed['orders']), facts=len(frames), compared_states=len(joins),
        compared_order_rows=sum(row['compared_orders'] for row in joins), deterministic_ledger_sha256=hashlib.sha256(first).hexdigest(),
        ledger_constructions=2, validation_summary=validation['summary'])
    return dict(ledger=document, validation=validation, observations=observations, joins=joins, summary=summary)


@contextmanager
def checked_reader(path, maximum, expected_stat=None):
    """Bind a nonblocking regular descriptor to the same named file before/after."""
    path = Path(path)
    before = events.stat_identity(path)
    require(before[2] <= maximum, "input exceeds its byte bound before reading/hashing")
    require(expected_stat is None or before == expected_stat, "protected input identity changed before opening")
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_CLOEXEC', 0))
    try:
        require(events._stat_value(os.fstat(descriptor)) == before, "input changed or became nonregular before descriptor open")
        stream = os.fdopen(descriptor, 'rb', buffering=CHUNK)
        descriptor = None
        with stream:
            yield stream, before
            require(events._stat_value(os.fstat(stream.fileno())) == before and events.stat_identity(path) == before,
                    "input changed during checked descriptor consumption")
        require(events.stat_identity(path) == before, "input changed during descriptor close")
    finally:
        if descriptor is not None:
            os.close(descriptor)


def read_blob(path, maximum, maximum_rows=None):
    """Bound the declared size before both hashing and allocation; reject growth."""
    with checked_reader(path, maximum) as (stream, before):
        chunks, consumed, line_count = [], 0, 0
        while True:
            chunk = stream.read(min(CHUNK, maximum - consumed + 1))
            if not chunk:
                break
            consumed += len(chunk)
            require(consumed <= maximum and consumed <= before[2], "input grew beyond declared/bounded size")
            if maximum_rows is not None:
                line_count += chunk.count(b'\n')
                require(line_count <= maximum_rows + 1, "CSV row bound exceeded before hashing")
            chunks.append(chunk)
        require(consumed == before[2], "input consumed-byte count differs from declared size")
        blob = b''.join(chunks)
    return blob, blob_info(blob)


def hash_raw(path, input_identity, retained_prefix, expected_stat=None):
    """Stream full and retained-prefix SHA-256 in one pass, with checked close."""
    require(type(input_identity) is dict and uint(input_identity.get('bytes'), 1, MAX_RAW_BYTES) and
            _digest(input_identity.get('sha256')), "invalid trusted raw identity")
    require(type(retained_prefix) is dict and uint(retained_prefix.get('bytes'), 1, input_identity['bytes']) and
            _digest(retained_prefix.get('sha256')), "invalid trusted prefix identity")
    size, prefix_size = input_identity['bytes'], retained_prefix['bytes']
    full, prefix, consumed = hashlib.sha256(), hashlib.sha256(), 0
    with checked_reader(path, MAX_RAW_BYTES, expected_stat) as (stream, before):
        require(before[2] == size, "raw input size does not match retained evidence")
        while True:
            chunk = stream.read(min(CHUNK, size - consumed + 1))
            if not chunk:
                break
            require(consumed + len(chunk) <= size, "raw input grew beyond trusted size")
            full.update(chunk)
            if consumed < prefix_size:
                prefix.update(chunk[:prefix_size - consumed])
            consumed += len(chunk)
        require(consumed == size, "raw consumed-byte count differs from trusted size")
    result = dict(bytes=consumed, sha256=full.hexdigest(), prefix_bytes=prefix_size, prefix_sha256=prefix.hexdigest())
    require(result['sha256'] == input_identity['sha256'] and result['prefix_sha256'] == retained_prefix['sha256'],
            "fresh full/prefix raw digest differs from accepted evidence")
    return result


def authenticate_anchor(kind, path, blob):
    """Require the accepted historical blob and the current blob at a fixed path."""
    relative, commit, digest = PINS[kind]
    expected_path = ROOT / relative
    require(Path(path).resolve(strict=True) == expected_path.resolve(strict=True) and
            Path(path).absolute() == expected_path.absolute(), "evidence is not the accepted repository path")
    require(blob_info(blob)['sha256'] == digest, "evidence differs from accepted SHA-256")
    for revision in ('HEAD', commit):
        size = handoff.git(ROOT, 'cat-file', '-s', revision + ':' + relative).decode('ascii').strip()
        require(l3.UINT_TEXT.fullmatch(size) is not None and int(size) == len(blob) <= MAX_JSON_BYTES,
                "committed evidence blob has an unexpected size")
        require(handoff.git(ROOT, 'show', revision + ':' + relative) == blob,
                "evidence differs from accepted current/historical committed blob")
    return dict(tracked_path=relative, accepted_evidence_commit=commit, **blob_info(blob), matches_head_blob=True,
                matches_accepted_historical_blob=True)


def source_snapshot(directory=ROOT):
    """Clean-main provenance with the same checked bounded IO as other inputs."""
    directory = Path(directory).resolve(strict=True)
    require(handoff.git(directory, 'branch', '--show-current').strip() == b'main', "history production requires existing main")
    require(handoff.git(directory, 'status', '--porcelain', '--untracked-files=normal') == b'', "history production requires committed clean main")
    commit = handoff.git(directory, 'rev-parse', 'HEAD').decode('ascii').strip()
    require(re.fullmatch('[0-9a-f]{40}', commit) is not None, "invalid source commit identity")
    names = handoff.git(directory, 'ls-files', '-z').decode('utf-8').split('\0')
    files = {}
    for name in sorted(name for name in names if name and (Path(name).suffix in handoff.SOURCE_SUFFIXES or Path(name).name == 'CMakeLists.txt')):
        path = (directory / name).resolve(strict=True)
        require(path.is_relative_to(directory), "tracked implementation resolves outside this repository")
        files[name] = read_blob(path, MAX_SOURCE_BYTES)[1]
    require(bool(files), "source provenance has no implementation files")
    return dict(commit=commit, branch='main', clean=True, files=files)


def fresh_destination(path):
    requested = Path(path).expanduser().absolute()
    require(not os.path.lexists(requested), "output/report must be fresh, including no dangling symlink")
    resolved = requested.resolve()
    require(not os.path.lexists(resolved) and resolved.parent.is_dir(), "fresh destination parent must already exist")
    return resolved


def write_bytes(path, publication, maximum):
    """Publish exclusively; failed writes/closes remove only this owned inode."""
    require(type(publication) is bytes and len(publication) <= maximum, "publication exceeds actual serialised byte bound")
    stream = Path(path).open('xb')
    opened = os.fstat(stream.fileno())
    owned = opened.st_dev, opened.st_ino
    try:
        with stream:
            require(stream.write(publication) == len(publication), "publication returned a short write")
        named = Path(path).lstat()
        require(stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned and named.st_size == len(publication),
                "publication path/inode/byte count changed during write/close")
    except BaseException:
        try:
            named = Path(path).lstat()
            if stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned:
                Path(path).unlink()
        except OSError:
            pass
        raise
    return blob_info(publication)


def write_json(path, value, maximum=events.MAX_LEDGER_BYTES):
    return write_bytes(path, canonical_bytes(value), maximum)


def _observation_summary(name, delay, result):
    return dict(profile=name, feed_delay_ns=delay, horizon_ns=result['horizon_ns'], probe_count=len(result['probes']),
        available_probes=sum(int(probe['available']) for probe in result['probes']), delivered_snapshots=len(result['deliveries']),
        pending_deliveries=result['pending_deliveries'], latest_delivered_event_index=result['latest_delivered_event_index'],
        captured_rows=result['captured_rows'])


def _scan_summary(scan):
    return {**{key: scan[key] for key in ('scanned_messages', 'scan_prefix_bytes', 'scan_prefix_sha256')},
        'windows': [{**{key: window[key] for key in ('window_id', 'seed_source', 'seed_next_source', 'closing_witness')},
            'selected_messages': len(window['frames']), 'framed_bytes_sha256': hashlib.sha256(b''.join(frame for _, frame in window['frames'])).hexdigest()}
            for window in scan['windows']]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('raw', 'window-evidence', 'l3-evidence', 'projection-dir', 'l3-dir', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, action=events.Once, required=True)
    args = parser.parse_args(argv)
    # Lexical freshness precedes resolve(), including for existing dangling links.
    output, report_path = fresh_destination(args.output), fresh_destination(args.report)
    require(not report_path.is_relative_to(output), "aggregate report must be outside the private output directory")
    report = dict(schema_version=1, gate=GATE, passed=False, raw_input_identity_verified=False, errors=[], checks={}, windows=[],
        limitations=['Independent L3 inventories are reused from pinned retained evidence; no fresh external replay or vendor oracle',
            'Fresh whole-file SHA-256 is identity; global framing and semantic observations cover only the reported bounded prefix',
            'Source declarations remain unverified inside the logical observer; the producer authenticates them separately',
            'Insertion FIFO is a reconstruction convention, not proof of exchange priority, parent aggressor or full incoming demand',
            'No own orders, hidden liquidity, market response, hypothetical fills, calibration or strategy performance'])
    tracked, published, raw_stat, source_before = {}, {}, None, None
    try:
        source_before = source_snapshot(ROOT)
        report['source_before'] = source_before
        require(output.is_relative_to(ROOT), "private output must be inside this repository's ignored storage")
        handoff.git(ROOT, 'check-ignore', '--no-index', str(output))
        paths = {name: getattr(args, name).expanduser().resolve(strict=True) for name in
                 ('raw', 'window_evidence', 'l3_evidence', 'projection_dir', 'l3_dir')}
        report['command'] = [sys.executable, str(Path(__file__).resolve()), *[part for name in
            ('raw', 'window_evidence', 'l3_evidence', 'projection_dir', 'l3_dir') for part in ('--' + name.replace('_', '-'), str(paths[name]))],
            '--output', str(output), '--report', str(report_path)]
        require(paths['projection_dir'].is_dir() and paths['l3_dir'].is_dir(), "artefact directory input is not a directory")
        small = {paths['window_evidence']: MAX_JSON_BYTES, paths['l3_evidence']: MAX_JSON_BYTES}
        row_bounds = {paths['window_evidence']: None, paths['l3_evidence']: None}
        window_blob, window_info = read_blob(paths['window_evidence'], MAX_JSON_BYTES)
        l3_blob, l3_info = read_blob(paths['l3_evidence'], MAX_JSON_BYTES)
        report['anchors'] = {'window': authenticate_anchor('window', args.window_evidence.expanduser().absolute(), window_blob),
                             'l3': authenticate_anchor('l3', args.l3_evidence.expanduser().absolute(), l3_blob)}
        window_report, l3_report = _object(window_blob), _object(l3_blob)
        crosslink = l3_report.get('window_evidence')
        require(type(crosslink) is dict and {key: crosslink.get(key) for key in ('bytes', 'sha256')} == window_info and
                crosslink.get('tracked_path') == PINS['window'][0], "L3 evidence does not bind the supplied original window report bytes")
        runs = window_report.get('runs')
        require(type(runs) is list and len(runs) == 2 and all(type(run) is dict and type(run.get('symbol')) is str for run in runs) and
                {run['symbol'] for run in runs} == {'MSFT', 'QQQ'}, "production requires exactly the two accepted canonical windows")
        projection_paths, l3_paths = {}, {}
        for run in runs:
            projection_paths[run['symbol']] = {}
            for name in PROJECTION_NAMES:
                fixed = (paths['projection_dir'] / run['symbol'] / name).resolve(strict=True)
                projection_paths[run['symbol']][name] = fixed
                small[fixed] = MAX_JSON_BYTES if name.endswith('.json') else MAX_PROJECTION_BYTES
                row_bounds[fixed] = events.MAX_FACTS if name.endswith('.csv') else None
        for name in L3_NAMES:
            fixed = (paths['l3_dir'] / name).resolve(strict=True)
            l3_paths[name] = fixed
            small[fixed] = MAX_CHECKPOINT_BYTES if name == 'checkpoints.csv' else MAX_EXPORT_BYTES if name.endswith('.csv') else MAX_JSON_BYTES
            row_bounds[fixed] = l3.MAX_STATES if name == 'checkpoints.csv' else MAX_EXPORT_ROWS if name.endswith('.csv') else None
        require(len(small) == 2 + len(runs) * len(PROJECTION_NAMES) + len(L3_NAMES), "two protected inputs resolve to the same path")
        require(all(not destination.is_relative_to(paths[key]) for destination in (output, report_path) for key in ('projection_dir', 'l3_dir')),
                "output/report cannot be placed inside a protected artefact directory")
        # Resolve each consumed path once and keep its inode identity. Reports
        # supply no filenames or executable arguments to this construction.
        input_paths = [paths['raw'], *small]
        input_inodes, captured = set(), {}
        for path in input_paths:
            before = events.stat_identity(path)
            require(before[:2] not in input_inodes, "input paths alias one inode")
            input_inodes.add(before[:2])
            require(path != report_path and not path.is_relative_to(output), "output/report aliases or contains a protected input")
            if path in small:
                require(before[2] <= small[path], "small input exceeds bound before hashing")
                blob, digest = read_blob(path, small[path], row_bounds[path])
                tracked[path] = (before, digest, small[path], row_bounds[path])
                captured[path] = blob
            else:
                require(before[2] <= MAX_RAW_BYTES, "raw source exceeds trusted profile bound")
                raw_stat = before
        report['inputs'] = {str(path): digest for path, (_, digest, _, _) in tracked.items()}
        projection_blobs = {}
        for run in runs:
            projection_blobs[run['symbol']] = {name: captured[projection_paths[run['symbol']][name]] for name in PROJECTION_NAMES}
        l3_blobs = {name: captured[l3_paths[name]] for name in L3_NAMES}
        binding = bind_inputs(window_report, l3_report, projection_blobs, l3_blobs)
        del captured, projection_blobs
        report['retained_reference'] = dict(window_producer_commit=window_report['source_commit'], l3_producer_source=l3_report.get('source'),
            reference=l3_report.get('reference'), scopes=_object(l3_blobs['comparison.json']).get('validation_scopes'))
        # The public aggregate retains source identities but never per-order rows.
        require(report_path != ROOT / 'bench' / 'identified_history.py' and
                all(not (ROOT / name).resolve().is_relative_to(output) and (ROOT / name).resolve() != report_path for name in source_before['files']),
                "output/report overlaps protected implementation")
        output.mkdir()
        print('Authenticating complete raw input and retained prefix before production', flush=True)
        report['raw_before'] = hash_raw(paths['raw'], binding['input_identity'], binding['retained_prefix'], raw_stat)
        print('Scanning global frames through the final closing witness', flush=True)
        with checked_reader(paths['raw'], MAX_RAW_BYTES, raw_stat) as (stream, _):
            scan = scan_prefix(stream, binding)
        report['scan'] = _scan_summary(scan)
        for window, scan_window in zip(binding['windows'], scan['windows']):
            directory = output / ('window-%03d' % window['window_id'])
            directory.mkdir()
            print('Building window %d (%s), %d authenticated facts' % (window['window_id'], window['symbol'], len(scan_window['frames'])), flush=True)
            built = build_window(binding, scan_window, include_observations=False, evidence_sha256=report['anchors']['l3']['sha256'])
            aggregate = dict(built['summary'], observations=[], artefacts={})
            report['windows'].append(aggregate)
            for name, value in (('ledger.json', built['ledger']), ('expected_sources.json', window['expected_sources']),
                                ('validation.json', built['validation']), ('joins.json', built['joins'])):
                maximum = events.MAX_EXPECTED_BYTES if name == 'expected_sources.json' else events.MAX_LEDGER_BYTES
                aggregate['artefacts'][name] = write_json(directory / name, value, maximum)
                published[directory / name] = (events.stat_identity(directory / name), aggregate['artefacts'][name], maximum)
            # Observe/write/release each profile instead of retaining three full
            # copied snapshot/probe inventories for every admitted window.
            for name, delay, probes in observation_profiles(window):
                observed = events.observe(built['ledger'], delay, window['end_ns'], probes, window['expected_sources'])
                filename = 'observation-' + name + '.json'
                aggregate['artefacts'][filename] = write_json(directory / filename, observed)
                published[directory / filename] = (events.stat_identity(directory / filename), aggregate['artefacts'][filename], events.MAX_LEDGER_BYTES)
                aggregate['observations'].append(_observation_summary(name, delay, observed))
                del observed
            del built
        print('Re-authenticating complete raw input and retained prefix after production', flush=True)
        report['raw_after'] = hash_raw(paths['raw'], binding['input_identity'], binding['retained_prefix'], raw_stat)
        require(same(report['raw_before'], report['raw_after']), "raw identity changed across production")
        report['raw_input_identity_verified'] = True
        report['checks'].update(pinned_current_and_historical_evidence=True, authenticated_projection_and_complete_L3_exports=True,
            exact_checkpoint_and_anchored_source_binding=True, full_and_retained_prefix_sha256_before_after=True,
            complete_global_framing_through_later_witness=True, complete_selected_coverage_before_type_filter=True,
            whole_timestamp_seeds_and_inclusive_end=True, every_independent_inventory_matches=True,
            deterministic_two_ledger_constructions=True, sequential_bounded_delayed_observations=True)
        report['passed'] = True
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError, RecursionError) as error:
        report['errors'].append(str(error))
    finally:
        try:
            for path, (before, digest, maximum, rows) in tracked.items():
                require(events.stat_identity(path) == before and read_blob(path, maximum, rows)[1] == digest, "protected small input changed during production")
            for path, (before, digest, maximum) in published.items():
                require(events.stat_identity(path) == before and read_blob(path, maximum)[1] == digest, "published detail artefact changed during production")
            if raw_stat is not None:
                require(events.stat_identity(paths['raw']) == raw_stat, "protected raw inode/size/time changed during production")
            if source_before is not None:
                report['source_after'] = source_snapshot(ROOT)
                require(same(source_before, report['source_after']), "public source changed during production")
            report['checks']['protected_inputs_and_source_unchanged'] = bool(tracked) and source_before is not None
        except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError) as error:
            report['passed'] = False
            report['errors'].append(str(error))
        if report['errors']:
            report['passed'] = False
        publication = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
        write_bytes(report_path, publication, MAX_REPORT_BYTES)
    if not report['passed']:
        print('Bounded identified history failed; see the aggregate report', file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
