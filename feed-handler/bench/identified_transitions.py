#!/usr/bin/env python3
"""Authenticate exact-source identified transition windows against retained L3 states.

The pure helpers establish bounded structural agreement. Repository trust and fresh
whole-file authentication belong to the CLI; the unchanged logical observer continues
to label its declared raw identity unverified. No external reconstruction is run.
"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import sys


def _sibling(name):
    specification = importlib.util.spec_from_file_location('transitions_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


history = _sibling('identified_history')
events, l3, handoff = history.events, history.l3, history.handoff
require, uint, same = events.require, events.uint, events.same
canonical_bytes, blob_info = history.canonical_bytes, history.blob_info
read_blob, hash_raw = history.read_blob, history.hash_raw
write_bytes, write_json = history.write_bytes, history.write_json
source_snapshot, fresh_destination = history.source_snapshot, history.fresh_destination
ROOT = Path(__file__).resolve().parent.parent
GATE = 'canonical_identified_transitions_v1'
MAX_WINDOWS, MAX_FACTS, MAX_STATES = 4, 4, 20
MAX_PREFIX_MESSAGES, MAX_PREFIX_BYTES = 16_000_000, 512 << 20
MAX_JSON_BYTES, MAX_REPORT_BYTES = 8 << 20, 1 << 20
ALLOWED = {'A', 'D', 'E', 'X', 'U'}
PIN = ('docs/validation/2026-10-23-l3-transitions/verification.json',
       '3c5af0af73320bd9fd9f75476c8ca0b0627eeb7c',
       'a0eb34d2aea23821ed1e4823fe8e84f9ee9c015fad24d9f39ce663e28111b2bc', 81814)
ARTIFACT_NAMES = ('selection/selection.json', 'selection/checkpoints.csv', 'selection/census.csv',
    'local-1.orders.csv', 'local-1.summary.json', 'reference-1.orders.csv', 'reference-1.summary.json',
    'comparison.json', 'independent-enumeration/review.json', 'independent-deltas/review.json')
WINDOW_KEYS = {'window_id', 'symbol', 'locate', 'effective_ns', 'end_ns', 'seed_source',
               'seed_frame_sha256', 'expected_sources', 'expected_frame_sha256s', 'states'}
CENSUS_HEADER = ('window_id', 'symbol', 'locate', *l3.SOURCE_KEYS, 'frame_sha256')
CHECKS = ('pinned_current_and_historical_evidence', 'authenticated_complete_L3_exports_and_reviews',
    'exact_checkpoint_and_anchored_source_binding', 'full_and_retained_prefix_sha256_before_after',
    'complete_global_framing_through_exact_prefix', 'complete_selected_coverage_before_type_filter',
    'exact_source_boundaries_without_timestamp_flush', 'every_independent_inventory_matches',
    'deterministic_two_ledger_constructions', 'sequential_bounded_delayed_observations',
    'protected_inputs_and_source_unchanged')


def _digest(value):
    return type(value) is str and events.HEX64.fullmatch(value) is not None


@contextmanager
def checked_reader(path, maximum, expected_stat=None):
    """Use an unbuffered regular descriptor so the prefix scan cannot read ahead."""
    path = Path(path)
    before = events.stat_identity(path)
    require(before[2] <= maximum and (expected_stat is None or before == expected_stat), 'input exceeds bound or changed before opening')
    descriptor = os.open(path, os.O_RDONLY | os.O_NONBLOCK | getattr(os, 'O_CLOEXEC', 0))
    try:
        require(events._stat_value(os.fstat(descriptor)) == before, 'input changed/became nonregular before open')
        stream = os.fdopen(descriptor, 'rb', buffering=0)
        descriptor = None
        with stream:
            yield stream, before
            require(events._stat_value(os.fstat(stream.fileno())) == before and events.stat_identity(path) == before,
                    'input changed during descriptor consumption')
        require(events.stat_identity(path) == before, 'input changed during descriptor close')
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _frame(frame, point):
    """Validate any known global wire header, without assigning target semantics."""
    require(type(frame) is bytes and len(frame) == point['body_bytes'] + 2 and
            int.from_bytes(frame[:2], 'big') == point['body_bytes'] and chr(frame[2]) == point['type'] and
            int.from_bytes(frame[7:13], 'big') == point['timestamp_ns'], 'framed bytes disagree with SourcePoint')
    return int.from_bytes(frame[3:5], 'big')


def validate_binding(binding):
    """Copy a bounded source/inventory binding; this grants no repository/raw trust."""
    events.exact_object(binding, {'input_identity', 'retained_prefix', 'directories', 'system_events', 'windows'}, 'transition binding')
    raw, prefix = binding['input_identity'], binding['retained_prefix']
    events.exact_object(raw, {'bytes', 'sha256'}, 'raw identity')
    events.exact_object(prefix, {'bytes', 'sha256', 'messages'}, 'retained prefix')
    require(uint(raw['bytes'], 1, history.MAX_RAW_BYTES) and _digest(raw['sha256']) and
            uint(prefix['bytes'], 1, min(raw['bytes'], MAX_PREFIX_BYTES)) and _digest(prefix['sha256']) and
            uint(prefix['messages'], 1, MAX_PREFIX_MESSAGES), 'invalid raw/prefix identity')
    windows = binding['windows']
    require(type(windows) is list and 1 <= len(windows) <= MAX_WINDOWS, 'invalid transition window count')
    symbols, locates, states, points, rows = {}, {}, {}, {}, 0
    for index, window in enumerate(windows, 1):
        events.exact_object(window, WINDOW_KEYS, 'transition window')
        require(uint(window['window_id'], 1) and window['window_id'] == index, 'window IDs must retain supplied consecutive order')
        events.validate_symbol(window['symbol'], window['locate'])
        require(symbols.setdefault(window['symbol'], window['locate']) == window['locate'] and
                locates.setdefault(window['locate'], window['symbol']) == window['symbol'], 'selected symbol/locate mapping changes')
        seed = window['seed_source']
        events.validate_source(seed, raw['bytes'])
        require(uint(window['effective_ns'], 1, events.TIME_MAX) and window['effective_ns'] == seed['timestamp_ns'] and
                uint(window['end_ns'], window['effective_ns'], events.TIME_MAX) and _digest(window['seed_frame_sha256']), 'invalid exact-source seed/end')
        expected, hashes = window['expected_sources'], window['expected_frame_sha256s']
        require(type(expected) is list and 1 <= len(expected) <= MAX_FACTS and type(hashes) is list and
                len(hashes) == len(expected) and all(_digest(value) for value in hashes), 'invalid selected source/hash coverage')
        previous = seed
        for source in expected:
            events.source_sequence(source, previous, window['effective_ns'], raw['bytes'])
            require(source['type'] in ALLOWED and source['timestamp_ns'] <= window['end_ns'], 'unsupported/out-of-window selected source')
            previous = source
        require(window['end_ns'] == expected[-1]['timestamp_ns'], 'end must retain the last fact source clock')
        require(type(window['states']) is list and len(window['states']) == len(expected) + 1, 'complete seed/post-state coverage required')
        for state, point in zip(window['states'], [seed, *expected]):
            events.exact_object(state, {'state_id', 'source', 'orders'}, 'independent state')
            require(uint(state['state_id'], 1, MAX_STATES) and state['state_id'] not in states and same(state['source'], point),
                    'duplicate state ID or mismatched state SourcePoint')
            history._orders(state['orders'])
            rows += len(state['orders'])
            require(rows <= history.MAX_EXPORT_ROWS, 'combined independent inventory row bound exceeded')
            states[state['state_id']] = (window['symbol'], point)
            sequence = point['sequence']
            known, inventories = points.setdefault(sequence, (point, {}))
            require(same(known, point) and window['symbol'] not in inventories, 'duplicate/conflicting selected source request')
            refs = {order['reference'] for order in state['orders']}
            require(all(not (refs & other) for other in inventories.values()), 'reference shared across symbols at the same global boundary')
            inventories[window['symbol']] = refs
    ordered = sorted(states.items(), key=lambda item: (item[1][1]['sequence'], item[0]))
    require([state_id for state_id, _ in ordered] == list(range(1, len(states) + 1)), 'global checkpoint IDs are not in source order')
    previous = None
    for _, (_, point) in ordered:
        require(previous is None or (same(previous, point) if previous['sequence'] == point['sequence'] else
                point['timestamp_ns'] >= previous['timestamp_ns'] and point['frame_offset'] >= previous['frame_end_offset']), 'global state clock/span regression')
        previous = point
    require(previous['sequence'] == prefix['messages'] and previous['frame_end_offset'] == prefix['bytes'], 'prefix must end exactly at the final requested source')
    directories = binding['directories']
    require(type(directories) is list and len(directories) == len(symbols), 'selected directory coverage mismatch')
    covered = set()
    for directory in directories:
        events.exact_object(directory, {'symbol', 'locate', 'source', 'frame_sha256'}, 'selected directory')
        symbol, locate = directory['symbol'], directory['locate']
        require(type(symbol) is str and symbol in symbols and same(locate, symbols[symbol]) and symbol not in covered and
                _digest(directory['frame_sha256']), 'invalid/duplicate selected directory identity')
        events.validate_source(directory['source'], raw['bytes'])
        require(directory['source']['type'] == 'R' and all(directory['source']['sequence'] < window['seed_source']['sequence']
                for window in windows if window['symbol'] == symbol), 'directory must precede every selected seed')
        covered.add(symbol)
    systems = binding['system_events']
    require(type(systems) is list and len(systems) == 3, 'original O/S/Q system origins required')
    previous = None
    for entry, code in zip(systems, 'OSQ'):
        events.exact_object(entry, {'code', 'source', 'frame_sha256'}, 'system origin')
        events.validate_source(entry['source'], raw['bytes'])
        require(entry['code'] == code and type(entry['code']) is str and entry['source']['type'] == 'S' and _digest(entry['frame_sha256']), 'invalid system origin')
        if previous is not None:
            events.source_sequence(entry['source'], previous, 0, raw['bytes'])
        previous = entry['source']
    require(all(previous['sequence'] <= window['seed_source']['sequence'] for window in windows), 'seed precedes original market-open origin')
    return deepcopy(binding)


def _occurrence(value, input_bytes):
    events.exact_object(value, {'source', 'frame_hex', 'frame_sha256', 'body_sha256'}, 'retained occurrence')
    events.validate_source(value['source'], input_bytes)
    require(type(value['frame_hex']) is str and events.HEX_BYTES.fullmatch(value['frame_hex']) is not None and
            len(value['frame_hex']) == 2 * (value['source']['body_bytes'] + 2) and _digest(value['frame_sha256']) and
            _digest(value['body_sha256']), 'invalid retained occurrence bytes/hash')
    frame = bytes.fromhex(value['frame_hex'])
    _frame(frame, value['source'])
    require(hashlib.sha256(frame).hexdigest() == value['frame_sha256'] and
            hashlib.sha256(frame[2:]).hexdigest() == value['body_sha256'], 'retained occurrence digest mismatch')
    return frame


def bind_inputs(evidence, artifact_blobs):
    """Bind immutable retained artefact bytes; production supplies Git-pinned evidence."""
    require(type(evidence) is dict and type(evidence.get('schema_version')) is int and evidence['schema_version'] == 1 and
            evidence.get('gate') == 'independent_canonical_x_u_transitions_v3' and evidence.get('passed') is True and
            evidence.get('errors') == [] and type(evidence.get('errors')) is list, 'retained Gate 14 evidence is not passed version one')
    for key in ('all_requested_states_compared', 'raw_historical_replay_executed', 'repeated_producer_bytes_identical',
                'full_and_prefix_sha256_freshly_verified_after'):
        require(evidence.get(key) is True, 'retained Gate 14 required claim is absent')
    require(type(artifact_blobs) is dict and set(artifact_blobs) == set(ARTIFACT_NAMES), 'missing/extra retained artefact blobs')
    manifests = {'selection/selection.json': evidence.get('selection'), 'comparison.json': evidence.get('comparison_identity'),
        'independent-enumeration/review.json': evidence.get('independent_selection_audit'),
        'independent-deltas/review.json': evidence.get('independent_delta_audit')}
    require(type(evidence.get('artifacts')) is dict, 'missing retained export manifests')
    for prefix in ('local-1', 'reference-1'):
        pair = evidence['artifacts'].get(prefix)
        require(type(pair) is dict and set(pair) == {'orders', 'summary'}, 'invalid retained export manifest')
        manifests[prefix + '.orders.csv'], manifests[prefix + '.summary.json'] = pair['orders'], pair['summary']
    selected = history._object(artifact_blobs['selection/selection.json'])
    events.exact_object(selected, {'schema_version', 'rule', 'passed', 'source', 'input', 'selection', 'artifacts'}, 'selection manifest')
    require(type(selected['schema_version']) is int and selected['schema_version'] == 1 and selected['passed'] is True and
            selected['rule'] == 'first_x_u_four_windows_v3', 'unsupported retained selection rule')
    require(type(selected['artifacts']) is dict and set(selected['artifacts']) == {'checkpoints', 'census'}, 'invalid selection artifact set')
    for key in ('checkpoints', 'census'):
        manifest = selected['artifacts'][key]
        require(type(manifest) is dict and set(manifest) == {'file', 'bytes', 'sha256'} and manifest['file'] == key + '.csv', 'selection artifact filename mismatch')
        manifests['selection/' + key + '.csv'] = manifest
    for name, manifest in manifests.items():
        maximum = history.MAX_EXPORT_BYTES if name.endswith('.orders.csv') else MAX_JSON_BYTES
        history._manifest(artifact_blobs[name], manifest, maximum)
    selection = selected['selection']
    events.exact_object(selection, {'schema_version', 'rule', 'passed', 'symbols', 'bounds', 'deadline_ns', 'system_events',
                                  'directories', 'windows', 'checkpoints', 'census', 'scan'}, 'selection')
    require(type(selection['schema_version']) is int and selection['schema_version'] == 1 and selection['passed'] is True and
            selection['rule'] == selected['rule'] and selection['deadline_ns'] is None, 'invalid source-bounded selection')
    before, after = evidence.get('input_before'), evidence.get('input_after')
    require(type(before) is dict and type(after) is dict and before.get('full_identity_freshly_verified') is True and
            same(selected['input'], before) and same(before.get('bytes'), after.get('bytes')) and
            same(before.get('sha256'), after.get('sha256')), 'retained raw identities disagree')
    raw = {key: after.get(key) for key in ('bytes', 'sha256')}
    scan = selection['scan']
    events.exact_object(scan, {'scanned_messages', 'consumed_prefix_bytes', 'prefix_sha256', 'captured_selected_headers'}, 'retained scan')
    prefix = dict(bytes=scan['consumed_prefix_bytes'], sha256=scan['prefix_sha256'], messages=scan['scanned_messages'])
    require(same(prefix['bytes'], after.get('prefix_bytes')) and same(prefix['sha256'], after.get('prefix_sha256')), 'retained scan prefix disagrees')
    require(sum(artifact_blobs[name].count(b'\n') for name in ('local-1.orders.csv', 'reference-1.orders.csv')) <=
            history.MAX_EXPORT_ROWS + 2, 'combined local/reference physical order row bound exceeded')
    local = history._export(artifact_blobs['local-1.summary.json'], artifact_blobs['local-1.orders.csv'])
    reference = history._export(artifact_blobs['reference-1.summary.json'], artifact_blobs['reference-1.orders.csv'])
    compared = l3.compare_exports(local, reference)
    require(compared['passed'] is True, 'complete local/reference inventories disagree')
    stored = history._object(artifact_blobs['comparison.json'])
    history._passed(stored, 'retained L3 comparison')
    require(all(same(stored.get(key), value) for key, value in compared.items()) and same(evidence.get('comparison'), stored), 'retained comparison disagrees')
    for exported in (local, reference):
        summary = exported['summary']
        require(same(summary['input_bytes'], raw['bytes']) and same(summary['scanned_messages'], prefix['messages']) and
                same(summary['consumed_prefix_bytes'], prefix['bytes']), 'complete export prefix mismatch')
    cp = history._table(artifact_blobs['selection/checkpoints.csv'], history.CHECKPOINT_HEADER, {'symbol', 'type'}, MAX_STATES, MAX_JSON_BYTES)
    requests = [{key: state[key] for key in ('state_id', 'symbol', 'locate')} | state['source'] for state in reference['summary']['states']]
    require(same(cp, requests) and same(selection['checkpoints'], [{key: state[key] for key in ('state_id', 'symbol', 'locate', 'source')}
            for state in reference['summary']['states']]), 'complete request list differs from retained checkpoint manifests')
    for name, phase in (('independent-enumeration/review.json', 'independent_prefix_enumeration'),
                        ('independent-deltas/review.json', 'independent_x_u_deltas')):
        review = history._object(artifact_blobs[name])
        require(type(review.get('schema_version')) is int and review['schema_version'] == 1 and review.get('passed') is True and
                type(review.get('errors')) is list and review['errors'] == [] and review.get('phase') == phase and
                review.get('input_identities_stable') is True, 'independent review did not pass')
        history._manifest(artifact_blobs['selection/selection.json'], review.get('selection_manifest'), MAX_JSON_BYTES)
        if phase == 'independent_prefix_enumeration':
            require(review.get('independent_selection_matches') is True and review.get('prefix_sha256_freshly_verified') is True and
                    same(review.get('scan'), scan) and same(review.get('checkpoints'), len(cp)) and
                    same(review.get('census'), len(selection['census'])), 'independent enumeration coverage mismatch')
        else:
            require(review.get('unaffected_orders_and_fifo_checked') is True and same(review.get('states_compared'), len(cp)), 'independent delta coverage mismatch')
    inventory = {state['state_id']: [] for state in reference['summary']['states']}
    for row in reference['orders']:
        inventory[row['state_id']].append({key: row[key] for key in history.CORE_ORDER_KEYS})
    windows, state_ids, census = [], [], []
    require(type(selection['windows']) is list and 1 <= len(selection['windows']) <= MAX_WINDOWS, 'invalid retained windows')
    for window in selection['windows']:
        events.exact_object(window, {'window_id', 'symbol', 'locate', 'anchor_type', 'roles'}, 'selected window')
        roles = window['roles']
        require(type(roles) is list and 2 <= len(roles) <= MAX_FACTS + 1 and window['anchor_type'] in {'X', 'U'}, 'invalid retained window roles')
        states, sources, hashes = [], [], []
        for index, role in enumerate(roles):
            events.exact_object(role, {'role', 'state_id', 'occurrence'}, 'selected role')
            require(role['role'] == ('seed' if index == 0 else 'anchor' if index == 1 else 'tail' + str(index - 1)) and
                    uint(role['state_id'], 1, len(cp)), 'role position/state ID mismatch')
            frame = _occurrence(role['occurrence'], raw['bytes'])
            point = role['occurrence']['source']
            state = reference['summary']['states'][role['state_id'] - 1]
            require(same(state['source'], point) and same(state['symbol'], window['symbol']) and same(state['locate'], window['locate']), 'role source does not match independent state')
            if index:
                require(_frame(frame, point) == window['locate'] and point['type'] in ALLOWED and
                        (index != 1 or point['type'] == window['anchor_type']), 'selected role is not the declared wire mutation')
                census.append(dict(window_id=window['window_id'], symbol=window['symbol'], locate=window['locate'], source=point,
                                   frame_sha256=role['occurrence']['frame_sha256']))
            sources.append(point)
            hashes.append(role['occurrence']['frame_sha256'])
            states.append(dict(state_id=role['state_id'], source=point, orders=inventory[role['state_id']]))
            state_ids.append(role['state_id'])
        windows.append(dict(window_id=window['window_id'], symbol=window['symbol'], locate=window['locate'],
            effective_ns=sources[0]['timestamp_ns'], end_ns=sources[-1]['timestamp_ns'], seed_source=sources[0],
            seed_frame_sha256=hashes[0], expected_sources=sources[1:], expected_frame_sha256s=hashes[1:], states=states))
    require(sorted(state_ids) == list(range(1, len(cp) + 1)) and same(census, selection['census']), 'roles do not cover exact checkpoints/unfiltered census')
    parsed_census = history._table(artifact_blobs['selection/census.csv'], CENSUS_HEADER, {'symbol', 'type', 'frame_sha256'}, MAX_WINDOWS * MAX_FACTS, MAX_JSON_BYTES)
    require(same(parsed_census, [{key: row[key] for key in ('window_id', 'symbol', 'locate')} | row['source'] |
                               {'frame_sha256': row['frame_sha256']} for row in census]), 'census CSV differs from exact role source coverage')
    directories, systems = [], []
    for entry in selection['directories']:
        events.exact_object(entry, {'symbol', 'locate', 'occurrence'}, 'retained directory')
        frame = _occurrence(entry['occurrence'], raw['bytes'])
        require(_frame(frame, entry['occurrence']['source']) == entry['locate'] and entry['occurrence']['source']['type'] == 'R' and
                frame[13:21] == entry['symbol'].encode('ascii').ljust(8, b' ') and frame[31] == ord('P'), 'retained production directory identity mismatch')
        directories.append({key: entry[key] for key in ('symbol', 'locate')} | {key: entry['occurrence'][key] for key in ('source', 'frame_sha256')})
    for entry in selection['system_events']:
        events.exact_object(entry, {'code', 'occurrence'}, 'retained system event')
        frame = _occurrence(entry['occurrence'], raw['bytes'])
        require(_frame(frame, entry['occurrence']['source']) == 0 and entry['occurrence']['source']['type'] == 'S' and frame[13:] == entry['code'].encode('ascii'), 'retained system event identity mismatch')
        systems.append({'code': entry['code']} | {key: entry['occurrence'][key] for key in ('source', 'frame_sha256')})
    require(same(selection['symbols'], [{key: row[key] for key in ('symbol', 'locate')} for row in directories]), 'selected symbol/directory list mismatch')
    return validate_binding(dict(input_identity=raw, retained_prefix=prefix, directories=directories, system_events=systems, windows=windows))


def scan_prefix(stream, binding):
    """Read exactly the retained prefix, enumerating every selected-locate occurrence."""
    binding = validate_binding(binding)
    prefix, windows = binding['retained_prefix'], binding['windows']
    directories = {entry['locate']: entry for entry in binding['directories']}
    names = {entry['symbol'].encode('ascii').ljust(8, b' '): entry for entry in binding['directories']}
    results = [dict(window_id=window['window_id'], seed_source=None, seed_frame=None, frames=[]) for window in windows]
    seen_directories, seen_systems = set(), []
    buffer, cursor, fetched, offset, sequence, previous_time = b'', 0, 0, 0, 0, 0
    digest = hashlib.sha256()

    def fill(minimum):
        nonlocal buffer, cursor, fetched
        if len(buffer) - cursor >= minimum:
            return
        buffer, cursor = buffer[cursor:], 0
        while len(buffer) < minimum:
            amount = min(history.CHUNK, prefix['bytes'] - fetched)
            require(amount > 0, 'truncated frame at exact prefix boundary')
            chunk = stream.read(amount)
            require(type(chunk) is bytes and 0 < len(chunk) <= amount, 'EOF/truncation before exact retained prefix')
            fetched += len(chunk)
            buffer += chunk

    while offset < prefix['bytes']:
        fill(2)
        length = int.from_bytes(buffer[cursor:cursor + 2], 'big')
        require(11 <= length <= max(events.LENGTHS.values()), 'zero/invalid global frame body length')
        fill(length + 2)
        at = cursor + 2
        kind = chr(buffer[at])
        require(kind in events.LENGTHS and length == events.LENGTHS[kind], 'unknown global type or wrong body length')
        locate = int.from_bytes(buffer[at + 1:at + 3], 'big')
        timestamp = int.from_bytes(buffer[at + 5:at + 11], 'big')
        require(timestamp >= previous_time, 'global source timestamp regression')
        previous_time = timestamp
        sequence += 1
        require(sequence <= prefix['messages'], 'global message count exceeds retained prefix')
        point = None

        def source_point():
            return dict(sequence=sequence, frame_offset=offset, frame_end_offset=offset + length + 2,
                        timestamp_ns=timestamp, body_bytes=length, type=kind)

        def checked_occurrence(expected, window_id=None):
            nonlocal point
            point = point or source_point()
            frame = bytes(buffer[cursor:cursor + length + 2])
            require(same(point, expected['source']) and hashlib.sha256(frame).hexdigest() == expected['frame_sha256'],
                    'framed occurrence mismatch%s: actual sequence %d byte %d, expected sequence %d byte %d' %
                    ('' if window_id is None else ' window %d' % window_id, sequence, offset,
                     expected['source']['sequence'], expected['source']['frame_offset']))
            return frame

        if kind == 'R':
            stock = buffer[at + 11:at + 19]
            directory, named = directories.get(locate), names.get(stock)
            if directory is not None or named is not None:
                require(directory is not None and named is directory and locate not in seen_directories and
                        buffer[at + 29] == ord('P'), 'conflicting/remapped/non-production selected directory')
                checked_occurrence(directory)
                seen_directories.add(locate)
        if kind == 'S' and chr(buffer[at + 11]) in 'OSQ':
            require(locate == 0 and len(seen_systems) < 3, 'duplicate/conflicting original O/S/Q origin')
            expected = binding['system_events'][len(seen_systems)]
            require(chr(buffer[at + 11]) == expected['code'], 'global O/S/Q order mismatch')
            checked_occurrence(expected)
            seen_systems.append(expected['code'])
        for window, result in zip(windows, results):
            if sequence == window['seed_source']['sequence']:
                require(window['locate'] in seen_directories and seen_systems == list('OSQ'), 'seed lacks authenticated directory/market-open origins')
                result['seed_frame'] = checked_occurrence({'source': window['seed_source'], 'frame_sha256': window['seed_frame_sha256']}, window['window_id'])
                result['seed_source'] = point
            if window['seed_source']['sequence'] < sequence <= window['expected_sources'][-1]['sequence']:
                if kind in history.STOCK_OFFSETS:
                    stock_at = at + history.STOCK_OFFSETS[kind]
                    stock = buffer[stock_at:stock_at + 8]
                    if stock == window['symbol'].encode('ascii').ljust(8, b' '):
                        require(locate == window['locate'], 'selected stock carries a conflicting locate inside source interval')
                    if locate == window['locate']:
                        require(stock == window['symbol'].encode('ascii').ljust(8, b' '), 'selected-locate stock identity mismatch')
                if locate == window['locate']:
                    index = len(result['frames'])
                    require(kind in ALLOWED and index < len(window['expected_sources']),
                            'unsupported/extra selected occurrence window %d: sequence %d byte %d type %s' % (window['window_id'], sequence, offset, kind))
                    frame = checked_occurrence({'source': window['expected_sources'][index], 'frame_sha256': window['expected_frame_sha256s'][index]}, window['window_id'])
                    events.parse_frame(frame, point, window['symbol'], window['locate'])
                    result['frames'].append((point, frame))
        frame_bytes = length + 2
        digest.update(buffer[cursor:cursor + frame_bytes])
        cursor += frame_bytes
        offset += frame_bytes
    require(offset == fetched == prefix['bytes'] and sequence == prefix['messages'] and digest.hexdigest() == prefix['sha256'], 'exact prefix bytes/message count/digest mismatch')
    require(len(seen_directories) == len(directories) and seen_systems == list('OSQ'), 'required source origins absent')
    for window, result in zip(windows, results):
        require(result['seed_source'] is not None, 'missing seed window %d: expected sequence %d byte %d' %
                (window['window_id'], window['seed_source']['sequence'], window['seed_source']['frame_offset']))
        require(same([point for point, _ in result['frames']], window['expected_sources']),
                'missing selected coverage window %d: received %d of %d facts; next expected sequence %d byte %d' %
                (window['window_id'], len(result['frames']), len(window['expected_sources']),
                 window['expected_sources'][min(len(result['frames']), len(window['expected_sources']) - 1)]['sequence'],
                 window['expected_sources'][min(len(result['frames']), len(window['expected_sources']) - 1)]['frame_offset']))
    return dict(scanned_messages=sequence, scan_prefix_bytes=offset, scan_prefix_sha256=digest.hexdigest(), windows=results)


def observation_profiles(window):
    times = [window['effective_ns'], *[source['timestamp_ns'] for source in window['expected_sources']]]
    end = window['end_ns']
    for name, delay, horizon in (('zero', 0, end), ('one_ms_clipped', 1_000_000, end),
            ('one_ms_complete', 1_000_000, end + 1_000_000), ('undelivered_seed', end - times[0] + 1, end)):
        require(uint(horizon) and all(uint(time + delay) for time in times), 'observation clock overflows uint64')
        probes = sorted({value for value in [times[0] - 1, *times, *[value for time in times for value in (time + delay - 1, time + delay)]] if 0 <= value <= horizon})
        require(len(probes) <= events.MAX_PROBES, 'observation probe count exceeds bound')
        yield name, delay, horizon, probes


def build_window(binding, scan_window, include_observations=True, *, evidence_sha256=None):
    """Build twice, compare every complete inventory and retain atomic observations."""
    binding = validate_binding(binding)
    require(type(include_observations) is bool and (evidence_sha256 is None or _digest(evidence_sha256)), 'invalid build options')
    events.exact_object(scan_window, {'window_id', 'seed_source', 'seed_frame', 'frames'}, 'scanned window')
    require(uint(scan_window['window_id'], 1, len(binding['windows'])), 'invalid scanned window ID')
    window = binding['windows'][scan_window['window_id'] - 1]
    require(same(scan_window['seed_source'], window['seed_source']) and type(scan_window['seed_frame']) is bytes and
            hashlib.sha256(scan_window['seed_frame']).hexdigest() == window['seed_frame_sha256'], 'scanned seed identity mismatch')
    _frame(scan_window['seed_frame'], window['seed_source'])
    frames = scan_window['frames']
    require(type(frames) is list and len(frames) == len(window['expected_sources']), 'scanned fact coverage mismatch')
    for pair, source, digest in zip(frames, window['expected_sources'], window['expected_frame_sha256s']):
        require(type(pair) in (tuple, list) and len(pair) == 2 and same(pair[0], source) and type(pair[1]) is bytes and
                hashlib.sha256(pair[1]).hexdigest() == digest, 'scanned fact source/hash mismatch')
    seed = dict(source=window['seed_source'], effective_ns=window['effective_ns'], boundary='post_source_message', derived=True,
        orders=[{**{key: order[key] for key in history.CORE_ORDER_KEYS - {'fifo_rank'}}, 'attribution': {'kind': 'unknown', 'mpid': None}}
                for order in window['states'][0]['orders']])
    identity = dict(input_bytes=binding['input_identity']['bytes'], input_sha256=binding['input_identity']['sha256'],
                    evidence_sha256=evidence_sha256, verification='unverified_by_module')
    document = events.build_ledger(window['symbol'], window['locate'], identity, seed, frames, window['expected_sources'])
    first = canonical_bytes(document)
    require(len(first) <= events.MAX_LEDGER_BYTES, 'canonical ledger exceeds byte bound')
    second = events.build_ledger(window['symbol'], window['locate'], identity, seed, frames, window['expected_sources'])
    require(first == canonical_bytes(second), 'two ledger constructions are not byte deterministic')
    del second
    validation = events.validate_ledger(document, window['expected_sources'])
    require(validation['passed'] is True and validation['raw_input_identity_verified'] is False and
            len(validation['snapshots']) == len(window['states']), 'logical validation or complete snapshot coverage failed')
    joins = []
    for snapshot, state in zip(validation['snapshots'], window['states']):
        require(same(snapshot['source'], state['source']) and same(history._ranked(snapshot['orders']), state['orders']),
                'independent inventory mismatch window %d state %d event %d source sequence %d byte %d' %
                (window['window_id'], state['state_id'], snapshot['event_index'], state['source']['sequence'], state['source']['frame_offset']))
        joins.append(dict(event_index=snapshot['event_index'], state_id=state['state_id'], source=state['source'], compared_orders=len(state['orders']), matched=True))
    observations, captured = [], 0
    if include_observations:
        for name, delay, horizon, probes in observation_profiles(window):
            result = events.observe(document, delay, horizon, probes, window['expected_sources'])
            captured += result['captured_rows']
            require(captured <= events.MAX_SNAPSHOT_ROWS, 'combined observation row bound exceeded')
            observations.append(dict(profile=name, feed_delay_ns=delay, horizon_ns=horizon, result=result))
    summary = dict(window_id=window['window_id'], symbol=window['symbol'], locate=window['locate'], effective_ns=window['effective_ns'],
        end_ns=window['end_ns'], seed_orders=len(seed['orders']), facts=len(frames), compared_states=len(joins),
        compared_order_rows=sum(row['compared_orders'] for row in joins), deterministic_ledger_sha256=hashlib.sha256(first).hexdigest(),
        ledger_constructions=2, validation_summary=validation['summary'])
    return dict(ledger=document, validation=validation, joins=joins, observations=observations, summary=summary)


def authenticate_anchor(path, blob):
    relative, commit, digest, size = PIN
    expected = ROOT / relative
    require(Path(path).absolute() == expected.absolute() and Path(path).resolve(strict=True) == expected.resolve(strict=True) and
            blob_info(blob) == {'bytes': size, 'sha256': digest}, 'evidence is not the accepted fixed repository anchor')
    for revision in ('HEAD', commit):
        count = handoff.git(ROOT, 'cat-file', '-s', revision + ':' + relative).decode('ascii').strip()
        require(count == str(size) and handoff.git(ROOT, 'show', revision + ':' + relative) == blob, 'evidence differs from current/accepted historical Git blob')
    return dict(tracked_path=relative, accepted_evidence_commit=commit, bytes=size, sha256=digest,
                matches_head_blob=True, matches_accepted_historical_blob=True)


def _scan_summary(scan):
    return {**{key: scan[key] for key in ('scanned_messages', 'scan_prefix_bytes', 'scan_prefix_sha256')}, 'windows': [dict(
        window_id=window['window_id'], seed_source=window['seed_source'], seed_frame_sha256=hashlib.sha256(window['seed_frame']).hexdigest(),
        selected_messages=len(window['frames']), expected_sources=[point for point, _ in window['frames']],
        frame_sha256s=[hashlib.sha256(frame).hexdigest() for _, frame in window['frames']],
        framed_bytes_sha256=hashlib.sha256(b''.join(frame for _, frame in window['frames'])).hexdigest()) for window in scan['windows']]}


def _canonical_profile(binding):
    require([(window['symbol'], window['locate']) for window in binding['windows']] == [('MSFT', 5291), ('MSFT', 5291), ('QQQ', 6556), ('QQQ', 6556)] and
            all(len(window['expected_sources']) == 4 for window in binding['windows']) and
            sorted(state['state_id'] for window in binding['windows'] for state in window['states']) == list(range(1, 21)), 'production requires exactly the four accepted windows and twenty states')


def _publish_report(path, publication, guard=None):
    """Read back the checked-close report, then guard its inputs before success."""
    require(type(publication) is bytes and len(publication) <= MAX_REPORT_BYTES, 'aggregate report exceeds byte bound')
    stream = Path(path).open('xb')
    opened = os.fstat(stream.fileno())
    owned = opened.st_dev, opened.st_ino
    try:
        with stream:
            require(stream.write(publication) == len(publication), 'aggregate report returned a short write')
        named = Path(path).lstat()
        require(stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned and named.st_size == len(publication), 'aggregate report inode/length changed on close')
        before = events.stat_identity(path)
        require(read_blob(path, MAX_REPORT_BYTES)[0] == publication, 'aggregate report readback differs from publication')
        if guard is not None:
            guard()
        require(events.stat_identity(path) == before and read_blob(path, MAX_REPORT_BYTES)[0] == publication, 'aggregate report changed during final guards')
    except BaseException:
        try:
            named = Path(path).lstat()
            if stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned:
                Path(path).unlink()
        except OSError:
            pass
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('raw', 'evidence', 'artifacts-dir', 'output', 'report'):
        parser.add_argument('--' + name, type=Path, action=events.Once, required=True)
    args = parser.parse_args(argv)
    output, report_path = fresh_destination(args.output), fresh_destination(args.report)
    require(not report_path.is_relative_to(output), 'aggregate report must be outside the private output directory')
    require(report_path.is_relative_to(ROOT), 'aggregate report must be inside this repository ignored storage')
    handoff.git(ROOT, 'check-ignore', '--no-index', str(report_path))
    report = dict(schema_version=1, gate=GATE, passed=False, raw_input_identity_verified=False, errors=[], checks={}, windows=[], limitations=[
        'Retained independently reconstructed inventories are reused; no fresh external book or vendor oracle',
        'Fresh full-file identity is separate from exact bounded-prefix framing and selected-locate semantics',
        'The logical observer retains unverified raw declarations; outer producer authentication is separate',
        'Reconstructed FIFO and inherited unknown attribution do not establish actual exchange priority or parent aggressors',
        'No live transport, eligibility, hidden liquidity, hypothetical fills, accounts, calibration or performance'])
    tracked, published, raw_stat, source_before, paths = {}, {}, None, None, {}
    try:
        source_before = source_snapshot(ROOT)
        report['source_before'] = source_before
        require(output.is_relative_to(ROOT), 'private output must be inside this repository ignored storage')
        handoff.git(ROOT, 'check-ignore', '--no-index', str(output))
        paths = {name: getattr(args, name).expanduser().resolve(strict=True) for name in ('raw', 'evidence', 'artifacts_dir')}
        require(paths['artifacts_dir'].is_dir(), 'retained artefact input is not a directory')
        require(all(not destination.is_relative_to(paths['artifacts_dir']) for destination in (output, report_path)), 'output/report overlaps protected artefact directory')
        report['command'] = [sys.executable, str(Path(__file__).resolve()), *[part for name in ('raw', 'evidence', 'artifacts_dir')
            for part in ('--' + name.replace('_', '-'), str(paths[name]))], '--output', str(output), '--report', str(report_path)]
        small = {paths['evidence']: (MAX_JSON_BYTES, None)}
        artifact_paths = {}
        for name in ARTIFACT_NAMES:
            path = (paths['artifacts_dir'] / name).resolve(strict=True)
            require(path.is_relative_to(paths['artifacts_dir']), 'fixed artefact resolves outside protected directory')
            maximum = history.MAX_EXPORT_BYTES if name.endswith('.orders.csv') else MAX_JSON_BYTES
            rows = history.MAX_EXPORT_ROWS if name.endswith('.orders.csv') else MAX_STATES if name.endswith('checkpoints.csv') else MAX_WINDOWS * MAX_FACTS if name.endswith('census.csv') else None
            artifact_paths[name], small[path] = path, (maximum, rows)
        require(len(small) == len(ARTIFACT_NAMES) + 1 and paths['raw'] not in small, 'protected inputs resolve to one path')
        inodes, captured = set(), {}
        for path in (paths['raw'], *small):
            before = events.stat_identity(path)
            require(before[:2] not in inodes and path != report_path and not path.is_relative_to(output), 'protected input aliases another input/output')
            inodes.add(before[:2])
            if path in small:
                maximum, rows = small[path]
                blob, info = read_blob(path, maximum, rows)
                tracked[path] = (before, info, maximum, rows)
                captured[path] = blob
            else:
                require(before[2] <= history.MAX_RAW_BYTES, 'raw input exceeds profile bound')
                raw_stat = before
        evidence_blob = captured[paths['evidence']]
        report['anchors'] = {'l3': authenticate_anchor(args.evidence.expanduser().absolute(), evidence_blob)}
        evidence = history._object(evidence_blob)
        blobs = {name: captured[path] for name, path in artifact_paths.items()}
        binding = bind_inputs(evidence, blobs)
        _canonical_profile(binding)
        report['inputs'] = {str(path): info for path, (_, info, _, _) in tracked.items()}
        report['retained_reference'] = dict(accepted_source=evidence.get('source'), validation_scopes=history._object(blobs['comparison.json']).get('validation_scopes'),
            selection=evidence['selection'], independent_selection_audit=evidence['independent_selection_audit'], independent_delta_audit=evidence['independent_delta_audit'])
        require(all((ROOT / name).resolve() != report_path and not (ROOT / name).resolve().is_relative_to(output) for name in source_before['files']), 'output/report overlaps implementation source')
        del captured, blobs
        output.mkdir()
        print('Authenticating complete raw input and exact retained prefix before production', flush=True)
        report['raw_before'] = hash_raw(paths['raw'], binding['input_identity'], binding['retained_prefix'], raw_stat)
        print('Scanning global framing through the exact final retained source', flush=True)
        with checked_reader(paths['raw'], history.MAX_RAW_BYTES, raw_stat) as (stream, _):
            scan = scan_prefix(stream, binding)
        report['scan'] = _scan_summary(scan)
        captured_rows = 0
        for window, scanned in zip(binding['windows'], scan['windows']):
            directory = output / ('window-%03d' % window['window_id'])
            directory.mkdir()
            print('Building window %d (%s), %d authenticated facts' % (window['window_id'], window['symbol'], len(scanned['frames'])), flush=True)
            built = build_window(binding, scanned, include_observations=False, evidence_sha256=PIN[2])
            aggregate = dict(built['summary'], observations=[], artefacts={})
            report['windows'].append(aggregate)
            for name, value in (('ledger.json', built['ledger']), ('expected_sources.json', window['expected_sources']),
                                ('validation.json', built['validation']), ('joins.json', built['joins'])):
                maximum = events.MAX_EXPECTED_BYTES if name == 'expected_sources.json' else events.MAX_LEDGER_BYTES
                aggregate['artefacts'][name] = write_json(directory / name, value, maximum)
                published[directory / name] = (events.stat_identity(directory / name), aggregate['artefacts'][name], maximum)
            for name, delay, horizon, probes in observation_profiles(window):
                result = events.observe(built['ledger'], delay, horizon, probes, window['expected_sources'])
                captured_rows += result['captured_rows']
                require(captured_rows <= events.MAX_SNAPSHOT_ROWS, 'combined produced observation row bound exceeded')
                filename = 'observation-' + name + '.json'
                aggregate['artefacts'][filename] = write_json(directory / filename, result)
                published[directory / filename] = (events.stat_identity(directory / filename), aggregate['artefacts'][filename], events.MAX_LEDGER_BYTES)
                aggregate['observations'].append(history._observation_summary(name, delay, result))
                del result
            del built
        print('Re-authenticating complete raw input and exact retained prefix after production', flush=True)
        report['raw_after'] = hash_raw(paths['raw'], binding['input_identity'], binding['retained_prefix'], raw_stat)
        require(same(report['raw_before'], report['raw_after']), 'raw identity changed across production')
        report['checks'].update({name: True for name in CHECKS[:-1]})
        report['passed'] = True
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError, RecursionError) as error:
        report['errors'].append(str(error))
    finally:
        def guard():
            for path, (before, info, maximum, rows) in tracked.items():
                require(events.stat_identity(path) == before and read_blob(path, maximum, rows)[1] == info, 'protected retained input changed during production')
            for path, (before, info, maximum) in published.items():
                require(events.stat_identity(path) == before and read_blob(path, maximum)[1] == info, 'published detail artefact changed during production')
            if raw_stat is not None:
                require(events.stat_identity(paths['raw']) == raw_stat, 'raw inode/size/time changed during production')
            if source_before is not None:
                report['source_after'] = source_snapshot(ROOT)
                require(same(source_before, report['source_after']), 'public source changed during production')
            report['checks']['protected_inputs_and_source_unchanged'] = bool(tracked) and source_before is not None

        try:
            guard()
        except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError) as error:
            report['passed'] = False
            report['errors'].append(str(error))
        if report['errors']:
            report['passed'] = False
        report['raw_input_identity_verified'] = report['passed'] is True
        publication = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
        try:
            _publish_report(report_path, publication, guard if report['passed'] else None)
        except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError) as error:
            report['passed'] = report['raw_input_identity_verified'] = False
            report['errors'].append('aggregate publication/final guard failed: ' + str(error))
            # The checked publisher has removed only its own failed inode. A
            # retained failure receipt is safe only when the name remains fresh.
            require(not os.path.lexists(report_path), 'aggregate report path no longer owned after publication failure')
            publication = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')
            write_bytes(report_path, publication, MAX_REPORT_BYTES)
    if not report['passed']:
        print('Identified transitions failed; see the aggregate report', file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
