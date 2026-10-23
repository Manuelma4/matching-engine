#!/usr/bin/env python3
"""Build authenticated synthetic Mold packets from retained identified history.

Only small accepted artefacts are read. Raw-day identity and independent reference
execution are inherited from earlier evidence, never freshly claimed by this tool.
Pure helpers validate structure and explicit occurrence identity without granting
repository trust or imposing the logical observer's historical reference policy.
"""
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import struct
import sys


def _sibling(name):
    specification = importlib.util.spec_from_file_location('transport_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


history = _sibling('identified_history')
events, l3 = history.events, history.l3
require, uint, same = events.require, events.uint, events.same
read_blob, source_snapshot, write_bytes = history.read_blob, history.source_snapshot, history.write_bytes
ROOT = Path(__file__).resolve().parent.parent
SCOPE = 'selected_locate_projection_v1'
GATE = 'authenticated_canonical_repacketisation_v1'
MAX_JSON_BYTES = 8 << 20
MAX_CSV_BYTES = 8 << 20
MAX_REPORT_BYTES = 1 << 20
MAX_ROWS = 100_000
MAX_FACTS = 16
MAX_ORDERS = 4_096
MAX_PACKETS = 64
BASE_SEQUENCE = 0x1122334455660000
PRODUCER_COMMIT = '464e4a7b9f190187d931181a2f49abbf100689b9'
PRODUCER_IDENTITY = {'bytes': 42_575, 'sha256': '12734d2522555d8036b78bb999b19087c33aed3c5c28cc402ef8ed95bf63dc08'}
PINS = {
    'history': ('docs/validation/2026-10-22-identified-history/canonical.json',
        '456ad39f4e683309afd05661c0c6f1d6f058229b', 'b7e29cf063fba8aff5d0494e872fa17363ea4fde7c2d28bf210fb17100533d25'),
    'l3': ('docs/validation/2026-10-22-l3/canonical.json',
        '0248264829dca038a936ded493e64e4942a739a2', 'a4ae84974f0ce09da32af8cd6dfc91c0be0cfd7ed775abf7c5816f5f3d291811'),
}
WINDOW_HEADER = ('schema_version', 'scope', 'window_id', 'symbol', 'locate', 'effective_ns', 'end_ns',
    'session_hex', 'initial_next', 'raw_input_bytes', 'raw_input_sha256', 'retained_prefix_bytes',
    'retained_prefix_sha256', 'history_evidence_sha256', 'l3_evidence_sha256', 'history_producer_sha256')
SEED_HEADER = ('side', 'price4', 'fifo_rank', 'reference', 'shares', 'attribution_status')
SOURCE_HEADER = ('window_id', 'event_index', 'origin_kind', *l3.SOURCE_KEYS, 'frame_hex', 'frame_sha256')
PACKET_HEADER = ('window_id', 'layout', 'packet_index', 'datagram_hex')
OCCURRENCE_HEADER = ('window_id', 'layout', 'packet_index', 'packet_message_index', 'transport_sequence',
    'body_offset', 'event_index', *l3.SOURCE_KEYS, 'frame_sha256', 'body_sha256')
IDENTITY_KEYS = {'input_bytes', 'input_sha256', 'retained_prefix_bytes', 'retained_prefix_sha256',
    'history_evidence_sha256', 'l3_evidence_sha256', 'history_producer_sha256'}
WINDOW_KEYS = {'window_id', 'symbol', 'locate', 'effective_ns', 'end_ns', 'seed_source', 'seed_orders', 'facts', 'states'}
CORE_ORDER_KEYS = {'side', 'price4', 'fifo_rank', 'reference', 'shares'}
WINDOW_FILES = ('ledger.json', 'expected_sources.json', 'joins.json')
L3_FILES = ('checkpoints.csv', 'reference.orders.csv', 'reference.summary.json')
LAYOUTS = ('single', 'batched')


def canonical_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False) + '\n').encode('utf-8')


def blob_info(blob):
    require(type(blob) is bytes, 'artefact must be an immutable byte string')
    return {'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest()}


def _digest(value):
    return type(value) is str and events.HEX64.fullmatch(value) is not None


def _json(blob, maximum=MAX_JSON_BYTES):
    require(type(blob) is bytes and len(blob) <= maximum, 'JSON artefact exceeds its byte bound')
    return events.strict_json(blob.decode('utf-8'))


def _object(blob):
    value = _json(blob)
    require(type(value) is dict, 'JSON artefact root must be an object')
    return value


def _manifest(blob, declared, maximum=MAX_JSON_BYTES, rows=None):
    require(type(blob) is bytes and len(blob) <= maximum, 'retained artefact exceeds its byte bound before hashing')
    if rows is not None:
        require(blob.count(b'\n') <= rows + 1, 'CSV exceeds its row bound before hashing')
    require(type(declared) is dict and uint(declared.get('bytes')) and _digest(declared.get('sha256')),
            'invalid retained artefact manifest')
    require(blob_info(blob) == {key: declared[key] for key in ('bytes', 'sha256')}, 'retained artefact bytes/hash mismatch')


def _orders(orders):
    require(type(orders) is list and len(orders) <= MAX_ORDERS, 'seed/live inventory exceeds its order bound')
    history._orders(orders)
    require(all(uint(order['fifo_rank'], 1, MAX_ORDERS) for order in orders), 'FIFO rank exceeds order bound')


def validate_binding(binding):
    """Validate/copy a small structural binding, without asserting raw authenticity.

    The canonical admission helper separately revalidates its logical ledgers and
    retained independent inventories. Generic transport fixtures can contain a
    valid D/A/D reference lifecycle without adopting the observer's seen-ref policy.
    """
    events.exact_object(binding, {'source_identity', 'windows'}, 'transport binding')
    identity = binding['source_identity']
    events.exact_object(identity, IDENTITY_KEYS, 'retained source declarations')
    require(uint(identity['input_bytes'], 1, 64 << 30) and uint(identity['retained_prefix_bytes'], 1, identity['input_bytes']),
            'invalid declared raw/prefix byte counts')
    require(all(_digest(identity[key]) for key in IDENTITY_KEYS - {'input_bytes', 'retained_prefix_bytes'}),
            'invalid declared raw/evidence digest')
    windows = binding['windows']
    require(type(windows) is list and 1 <= len(windows) <= 2, 'generic binding needs one or two windows')
    symbols, locates, state_ids, total_orders = set(), set(), set(), 0
    for index, window in enumerate(windows, 1):
        events.exact_object(window, WINDOW_KEYS, 'transport window')
        require(type(window['window_id']) is int and window['window_id'] == index, 'window ids must be consecutive from one')
        require(type(window['symbol']) is str and l3.SYMBOL.fullmatch(window['symbol']) is not None and
                uint(window['locate'], 1, 65535), 'invalid selected symbol/locate')
        require(window['symbol'] not in symbols and window['locate'] not in locates, 'duplicate window symbol/locate')
        symbols.add(window['symbol'])
        locates.add(window['locate'])
        events.validate_source(window['seed_source'], identity['input_bytes'])
        require(uint(window['effective_ns'], window['seed_source']['timestamp_ns'], events.TIME_MAX) and
                uint(window['end_ns'], window['effective_ns'] + 1, events.TIME_MAX), 'invalid effective window bounds')
        seed_orders = window['seed_orders']
        require(type(seed_orders) is list and len(seed_orders) <= MAX_ORDERS, 'seed inventory exceeds its bound')
        core_seed = []
        for order in seed_orders:
            events.exact_object(order, CORE_ORDER_KEYS | {'attribution_status'}, 'imported seed order')
            require(type(order['attribution_status']) is str and order['attribution_status'] == 'unknown',
                    'imported seed attribution must remain unknown')
            core_seed.append({key: order[key] for key in CORE_ORDER_KEYS})
        _orders(core_seed)
        facts = window['facts']
        require(type(facts) is list and 1 <= len(facts) <= MAX_FACTS, 'fact count outside bounded projection profile')
        points, previous = [window['seed_source']], window['seed_source']
        for event_index, fact in enumerate(facts, 1):
            events.exact_object(fact, {'event_index', 'source', 'frame_hex', 'frame_sha256'}, 'retained fact')
            require(type(fact['event_index']) is int and fact['event_index'] == event_index, 'fact indices must be consecutive')
            source = fact['source']
            events.source_sequence(source, previous, window['effective_ns'], identity['input_bytes'])
            require(window['effective_ns'] < source['timestamp_ns'] <= window['end_ns'] and source['type'] in {'A', 'D', 'E'},
                    'fact lies outside admitted A/D/E window')
            require(type(fact['frame_hex']) is str and events.HEX_BYTES.fullmatch(fact['frame_hex']) is not None and
                    len(fact['frame_hex']) <= 2 * 52 and _digest(fact['frame_sha256']), 'invalid retained framed hex/digest')
            frame = bytes.fromhex(fact['frame_hex'])
            require(hashlib.sha256(frame).hexdigest() == fact['frame_sha256'], 'retained framed SHA-256 mismatch')
            events.parse_frame(frame, source, window['symbol'], window['locate'])
            points.append(source)
            previous = source
        states = window['states']
        require(type(states) is list and len(states) == len(points), 'independent seed/post-state coverage mismatch')
        for event_index, (state, point) in enumerate(zip(states, points)):
            events.exact_object(state, {'event_index', 'state_id', 'source', 'orders'}, 'independent occurrence state')
            require(type(state['event_index']) is int and state['event_index'] == event_index and uint(state['state_id'], 1) and
                    state['state_id'] not in state_ids, 'invalid or duplicate independent state identity')
            state_ids.add(state['state_id'])
            require(same(state['source'], point), 'independent state SourcePoint differs from its occurrence')
            _orders(state['orders'])
            total_orders += len(state['orders'])
            require(total_orders <= MAX_ROWS, 'combined independent order rows exceed bound')
        require(same(states[0]['orders'], core_seed), 'imported seed differs from independent complete inventory')
        require(all(point['frame_end_offset'] <= identity['retained_prefix_bytes'] for point in points),
                'source point exceeds the retained prefix declaration')
    return deepcopy(binding)


def _packetise_window(window, layout):
    require(type(layout) is str and layout in LAYOUTS, 'unsupported packet layout')
    window_id = window['window_id']
    session = ('QH%08d' % window_id).encode('ascii')
    first = BASE_SEQUENCE + 256 * window_id
    packets, occurrences = [], []

    def packet(sequence, count, blocks=()):
        data = struct.pack('>10sQH', session, sequence, count) + b''.join(blocks)
        require(len(data) <= 65_535 and len(packets) < MAX_PACKETS, 'packet/layout resource bound exceeded')
        packets.append(dict(window_id=window_id, layout=layout, packet_index=len(packets), datagram_hex=data.hex()))

    packet(first, 0)
    cursor, group_index = 0, 0
    pattern = (2, 3, 2) if window_id == 1 else (2,)
    facts = window['facts']
    while cursor < len(facts):
        count = 1 if layout == 'single' else min(pattern[group_index % len(pattern)], len(facts) - cursor)
        selected = facts[cursor:cursor + count]
        packet_index, body_offset, blocks = len(packets), 22, []
        for message_index, fact in enumerate(selected):
            frame = bytes.fromhex(fact['frame_hex'])
            body = frame[2:]
            blocks.append(struct.pack('>H', len(body)) + body)
            occurrences.append(dict(window_id=window_id, layout=layout, packet_index=packet_index,
                packet_message_index=message_index, transport_sequence=first + fact['event_index'] - 1,
                body_offset=body_offset, event_index=fact['event_index'], **fact['source'],
                frame_sha256=fact['frame_sha256'], body_sha256=hashlib.sha256(body).hexdigest()))
            body_offset += 2 + len(body)
        packet(first + selected[0]['event_index'] - 1, count, blocks)
        cursor += count
        group_index += 1
    for marker in (0, 65_535, 65_535):
        packet(first + len(facts), marker)
    return dict(packets=packets, occurrences=occurrences)


def packetise(binding, window_id, layout):
    """Construct immutable packet-position joins; identical bodies are not keys."""
    binding = validate_binding(binding)
    require(uint(window_id, 1, len(binding['windows'])), 'invalid packetisation window id')
    return _packetise_window(binding['windows'][window_id - 1], layout)


def _csv(header, rows):
    require(type(rows) is list and len(rows) <= MAX_ROWS, 'CSV row bound exceeded')
    lines = [','.join(header)]
    for row in rows:
        events.exact_object(row, header, 'CSV row')
        fields = []
        for key in header:
            value = row[key]
            require(type(value) in (str, int), 'CSV field is not an exact text/integer value')
            text = str(value)
            require(all(32 <= ord(character) <= 126 and character not in ',"' for character in text), 'CSV field needs unsupported quoting')
            fields.append(text)
        lines.append(','.join(fields))
    result = ('\n'.join(lines) + '\n').encode('ascii')
    require(len(result) <= MAX_CSV_BYTES, 'CSV exceeds its actual serialised byte bound')
    return result


def build_bundle(binding):
    """Return deterministic CSV bytes only; no file reads, writes or trust grant."""
    binding = validate_binding(binding)
    identity = binding['source_identity']
    files = {}
    for window in binding['windows']:
        window_id = window['window_id']
        prefix = 'window-%03d/' % window_id
        configuration = dict(schema_version=1, scope=SCOPE, window_id=window_id, symbol=window['symbol'], locate=window['locate'],
            effective_ns=window['effective_ns'], end_ns=window['end_ns'], session_hex=('QH%08d' % window_id).encode('ascii').hex(),
            initial_next=BASE_SEQUENCE + 256 * window_id, raw_input_bytes=identity['input_bytes'], raw_input_sha256=identity['input_sha256'],
            retained_prefix_bytes=identity['retained_prefix_bytes'], retained_prefix_sha256=identity['retained_prefix_sha256'],
            history_evidence_sha256=identity['history_evidence_sha256'], l3_evidence_sha256=identity['l3_evidence_sha256'],
            history_producer_sha256=identity['history_producer_sha256'])
        files[prefix + 'window.csv'] = _csv(WINDOW_HEADER, [configuration])
        files[prefix + 'seed.csv'] = _csv(SEED_HEADER, window['seed_orders'])
        source_rows = [dict(window_id=window_id, event_index=0, origin_kind='imported_seed', **window['seed_source'],
                            frame_hex='', frame_sha256='')]
        source_rows.extend(dict(window_id=window_id, event_index=fact['event_index'], origin_kind='retained_fact', **fact['source'],
            frame_hex=fact['frame_hex'], frame_sha256=fact['frame_sha256']) for fact in window['facts'])
        files[prefix + 'sources.csv'] = _csv(SOURCE_HEADER, source_rows)
        for layout in LAYOUTS:
            result = _packetise_window(window, layout)
            files[prefix + layout + '/packets.csv'] = _csv(PACKET_HEADER, result['packets'])
            files[prefix + layout + '/occurrences.csv'] = _csv(OCCURRENCE_HEADER, result['occurrences'])
    return files


def _passed(value, gate):
    require(type(value) is dict and type(value.get('schema_version')) is int and value['schema_version'] == 1 and
            value.get('gate') == gate and value.get('passed') is True and type(value.get('errors')) is list and value['errors'] == [],
            'retained evidence is not passed version one: ' + gate)
    checks = value.get('checks')
    require(type(checks) is dict and bool(checks) and all(type(item) is bool and item for item in checks.values()),
            'retained evidence has absent/untyped/failed checks')


def _raw_identity(value):
    events.exact_object(value, {'bytes', 'sha256', 'prefix_bytes', 'prefix_sha256'}, 'retained raw identity')
    require(uint(value['bytes'], 1, 64 << 30) and uint(value['prefix_bytes'], 1, value['bytes']) and
            _digest(value['sha256']) and _digest(value['prefix_sha256']), 'invalid retained raw identity')


def bind_inputs(history_blob, l3_blob, producer_blob, window_blobs, l3_blobs):
    """Bind only the accepted canonical small artefacts, without reopening raw data.

    Repository location/current/historical Git checks belong to orchestration.
    Exact accepted report digests and every supplied artefact are also checked here.
    """
    require(all(type(blob) is bytes and len(blob) <= MAX_JSON_BYTES for blob in (history_blob, l3_blob, producer_blob)),
            'canonical evidence exceeds its byte bound before hashing')
    require(blob_info(history_blob)['sha256'] == PINS['history'][2] and blob_info(l3_blob)['sha256'] == PINS['l3'][2],
            'canonical evidence differs from the accepted pinned bytes')
    evidence, independent, producer = _object(history_blob), _object(l3_blob), _object(producer_blob)
    _passed(evidence, 'canonical_bounded_identified_history_v1')
    _passed(independent, 'independent_displayed_order_fifo_v1')
    _passed(producer, 'bounded_identified_history_v1')
    require(evidence.get('source_clean_before_after') is True and evidence.get('raw_identity_freshly_verified_by_producer') is True and
            evidence.get('logical_observer_raw_identity_verified') is False and producer.get('raw_input_identity_verified') is True,
            'retained verification provenance is inconsistent')
    source = evidence.get('source')
    require(type(source) is dict and source.get('commit') == PRODUCER_COMMIT and source.get('branch') == 'main' and source.get('clean') is True and
            same(source, producer.get('source_before')) and same(source, producer.get('source_after')),
            'retained producer code identity differs from accepted history evidence')
    require(blob_info(producer_blob) == PRODUCER_IDENTITY, 'history producer report is not the accepted retained file')
    _manifest(producer_blob, evidence.get('producer_report'))
    raw = evidence.get('raw_before')
    _raw_identity(raw)
    require(same(raw, evidence.get('raw_after')) and same(raw, producer.get('raw_before')) and same(raw, producer.get('raw_after')) and
            same(raw, independent.get('input_before')) and same(raw, independent.get('input_after')),
            'retained history/producer/reference raw identities disagree')
    anchors = evidence.get('anchors')
    require(type(anchors) is dict and type(anchors.get('l3')) is dict and type(anchors.get('window')) is dict,
            'retained anchor chain is incomplete')
    anchor = anchors['l3']
    require({key: anchor.get(key) for key in ('bytes', 'sha256')} == blob_info(l3_blob) and
            anchor.get('tracked_path') == PINS['l3'][0] and anchor.get('accepted_evidence_commit') == PINS['l3'][1] and
            anchor.get('matches_head_blob') is True and anchor.get('matches_accepted_historical_blob') is True,
            'history does not bind the supplied accepted L3 evidence')
    require(same(producer.get('anchors'), anchors), 'history and its retained producer anchor chains differ')
    window_anchor = independent.get('window_evidence')
    require(type(window_anchor) is dict and all(same(window_anchor.get(key), anchors['window'].get(key)) for key in ('tracked_path', 'bytes', 'sha256')),
            'reference/window evidence chain disagrees')
    reference = independent.get('reference')
    require(type(reference) is dict and reference.get('commit') == '3c646f9da182136125059243b475f7b8baa53773',
            'independent implementation revision is not the accepted reference')
    coverage = evidence.get('coverage')
    expected_counts = dict(windows=2, facts=13, seed_states=2, post_message_states=13, total_states=15,
                           order_row_instances=16_886, fixed_level_excluded_mutations_retained=5, exact_discrepancies=0)
    require(type(coverage) is dict and all(type(coverage.get(key)) is int and coverage[key] == count for key, count in expected_counts.items()) and
            same(coverage.get('type_counts'), {'A': 7, 'D': 4, 'E': 2}) and coverage.get('independent_selected_coverage') is True,
            'accepted canonical coverage is incomplete')

    require(type(l3_blobs) is dict and set(l3_blobs) == set(L3_FILES), 'missing or extra retained reference input')
    require(all(type(blob) is bytes for blob in l3_blobs.values()), 'reference artefacts must be immutable byte strings')
    require(sum(blob.count(b'\n') - 1 for name, blob in l3_blobs.items() if name.endswith('.csv')) <= MAX_ROWS,
            'combined reference CSV rows exceed bound before parsing')
    artefacts = independent.get('artefacts')
    require(type(artefacts) is dict, 'reference artefact manifests absent')
    for name in L3_FILES:
        declared = independent.get('checkpoints') if name == 'checkpoints.csv' else artefacts.get(name)
        _manifest(l3_blobs[name], declared, MAX_CSV_BYTES if name.endswith('.csv') else MAX_JSON_BYTES,
                  MAX_ROWS if name.endswith('.csv') else None)
    exported = history._export(l3_blobs['reference.summary.json'], l3_blobs['reference.orders.csv'])
    summary = exported['summary']
    require(summary['validation_scope'] == 'selected_symbols_only' and summary['input_bytes'] == raw['bytes'] and
            summary['consumed_prefix_bytes'] == raw['prefix_bytes'] and len(summary['states']) == 15 and len(exported['orders']) == 16_886,
            'retained reference prefix/state coverage mismatch')
    checkpoints = history._table(l3_blobs['checkpoints.csv'], history.CHECKPOINT_HEADER, {'symbol', 'type'}, MAX_ROWS, MAX_CSV_BYTES)
    require(len(checkpoints) == len(summary['states']), 'checkpoint list does not cover every independent state')
    by_state, inventories = {}, {}
    for checkpoint, state in zip(checkpoints, summary['states']):
        require(same(checkpoint, {key: state[key] for key in ('state_id', 'symbol', 'locate')} | state['source']),
                'retained checkpoint differs from reference state manifest')
        by_state[state['state_id']] = state
        inventories[state['state_id']] = []
    for row in exported['orders']:
        inventories[row['state_id']].append({key: row[key] for key in CORE_ORDER_KEYS})

    retained_windows, produced_windows = evidence.get('windows'), producer.get('windows')
    require(type(retained_windows) is list and type(produced_windows) is list and len(retained_windows) == len(produced_windows) == 2 and
            type(window_blobs) is dict and set(window_blobs) == {1, 2} and all(type(key) is int for key in window_blobs),
            'canonical profile requires both numbered retained windows')
    windows, consumed_states, type_counts = [], set(), {}
    for window_id, (retained, produced) in enumerate(zip(retained_windows, produced_windows), 1):
        require(type(retained) is dict and type(produced) is dict, 'invalid retained window summary')
        for key in ('window_id', 'symbol', 'locate', 'effective_ns', 'end_ns', 'seed_orders', 'facts', 'compared_states',
                    'compared_order_rows', 'deterministic_ledger_sha256', 'ledger_constructions'):
            require(same(retained.get(key), produced.get(key)), 'retained producer/window metadata mismatch: ' + key)
        symbol, locate = ('QQQ', 6556) if window_id == 1 else ('MSFT', 5291)
        facts_count, seed_count = (7, 463) if window_id == 1 else (6, 1881)
        require(type(retained.get('window_id')) is int and retained['window_id'] == window_id and retained.get('symbol') == symbol and
                type(retained.get('locate')) is int and retained['locate'] == locate and type(retained.get('facts')) is int and retained['facts'] == facts_count and
                type(retained.get('seed_orders')) is int and retained['seed_orders'] == seed_count and
                type(retained.get('ledger_constructions')) is int and retained['ledger_constructions'] == 2,
                'canonical window identity/count differs from accepted profile')
        blobs = window_blobs[window_id]
        require(type(blobs) is dict and set(blobs) == set(WINDOW_FILES), 'missing/extra retained window input')
        retained_files, produced_files = retained.get('artefacts'), produced.get('artefacts')
        require(type(retained_files) is dict and type(produced_files) is dict, 'retained window file identities absent')
        for name in WINDOW_FILES:
            require(same(retained_files.get(name), produced_files.get(name)), 'history/producer window file identities disagree')
            _manifest(blobs[name], retained_files.get(name))
        require(retained['deterministic_ledger_sha256'] == retained_files['ledger.json']['sha256'], 'retained ledger construction identity mismatch')
        document = _object(blobs['ledger.json'])
        expected_sources, joins = _json(blobs['expected_sources.json']), _json(blobs['joins.json'])
        validation = events.validate_ledger(document, expected_sources)
        require(document['symbol'] == symbol and document['locate'] == locate and document['source_identity']['input_bytes'] == raw['bytes'] and
                document['source_identity']['input_sha256'] == raw['sha256'] and
                document['source_identity']['evidence_sha256'] == blob_info(l3_blob)['sha256'] and
                document['source_identity']['verification'] == 'unverified_by_module', 'logical ledger source declarations mismatch')
        require(document['seed']['effective_ns'] == retained['effective_ns'] and len(document['facts']) == facts_count and
                len(document['seed']['orders']) == seed_count and type(joins) is list and len(joins) == facts_count + 1,
                'retained seed/time/source-join coverage mismatch')
        require(all(same(order['attribution'], {'kind': 'unknown', 'mpid': None}) for order in document['seed']['orders']),
                'actual imported ledger seed attribution is not exactly unknown')
        points = [document['seed']['source'], *expected_sources]
        states = []
        for event_index, (point, join, snapshot) in enumerate(zip(points, joins, validation['snapshots'])):
            events.exact_object(join, {'event_index', 'state_id', 'source', 'compared_orders', 'matched'}, 'retained source/state join')
            require(type(join['event_index']) is int and join['event_index'] == event_index and uint(join['state_id'], 1) and
                    join['state_id'] not in consumed_states and uint(join['compared_orders']) and join['matched'] is True and
                    same(join['source'], point), 'invalid, duplicate or incomplete retained source/state join')
            state = by_state.get(join['state_id'])
            require(state is not None and state['symbol'] == symbol and state['locate'] == locate and same(state['source'], point),
                    'original occurrence does not identify its independent source boundary')
            orders = inventories[state['state_id']]
            require(join['compared_orders'] == len(orders) and same(history._ranked(snapshot['orders']), orders),
                    'complete logical inventory differs from retained independent orders')
            consumed_states.add(state['state_id'])
            states.append(dict(event_index=event_index, state_id=state['state_id'], source=point, orders=orders))
        facts = []
        for fact in document['facts']:
            require(fact['source']['type'] in {'A', 'D', 'E'}, 'retained canonical fact outside admitted type set')
            type_counts[fact['source']['type']] = type_counts.get(fact['source']['type'], 0) + 1
            facts.append({key: fact[key] for key in ('event_index', 'source', 'frame_hex', 'frame_sha256')})
        windows.append(dict(window_id=window_id, symbol=symbol, locate=locate, effective_ns=retained['effective_ns'], end_ns=retained['end_ns'],
            seed_source=document['seed']['source'], seed_orders=[dict(order, attribution_status='unknown') for order in states[0]['orders']], facts=facts, states=states))
    require(consumed_states == set(range(1, 16)) and same(type_counts, {'A': 7, 'D': 4, 'E': 2}),
            'canonical source type/state request coverage incomplete')
    identity = dict(input_bytes=raw['bytes'], input_sha256=raw['sha256'], retained_prefix_bytes=raw['prefix_bytes'], retained_prefix_sha256=raw['prefix_sha256'],
        history_evidence_sha256=blob_info(history_blob)['sha256'], l3_evidence_sha256=blob_info(l3_blob)['sha256'], history_producer_sha256=blob_info(producer_blob)['sha256'])
    return validate_binding(dict(source_identity=identity, windows=windows))


def authenticate_anchor(kind, path, blob):
    """Bind exact supplied bytes to the accepted historical and current Git blob."""
    relative, commit, digest = PINS[kind]
    expected = ROOT / relative
    require(Path(path).expanduser().absolute() == expected.absolute() and
            Path(path).resolve(strict=True) == expected.resolve(strict=True),
            'evidence is not the fixed accepted repository path')
    require(type(blob) is bytes and len(blob) <= MAX_JSON_BYTES and blob_info(blob)['sha256'] == digest,
            'evidence differs from accepted bounded SHA-256')
    for revision in ('HEAD', commit):
        specification = revision + ':' + relative
        size = history.handoff.git(ROOT, 'cat-file', '-s', specification).decode('ascii').strip()
        require(l3.UINT_TEXT.fullmatch(size) is not None and int(size) == len(blob) <= MAX_JSON_BYTES,
                'committed evidence blob size differs or exceeds bound')
        require(history.handoff.git(ROOT, 'show', specification) == blob,
                'evidence differs from current or accepted historical Git blob')
    return dict(tracked_path=relative, accepted_evidence_commit=commit, **blob_info(blob),
                matches_head_blob=True, matches_accepted_historical_blob=True)


def _coverage(binding):
    windows, packet_count, occurrence_count = [], 0, 0
    for window in binding['windows']:
        layouts = []
        for layout in LAYOUTS:
            data = _packetise_window(window, layout)
            layouts.append(dict(layout=layout, packets=len(data['packets']), occurrences=len(data['occurrences'])))
            packet_count += len(data['packets'])
            occurrence_count += len(data['occurrences'])
        windows.append(dict(window_id=window['window_id'], symbol=window['symbol'], locate=window['locate'],
            effective_ns=window['effective_ns'], end_ns=window['end_ns'], imported_seed_orders=len(window['seed_orders']),
            facts=len(window['facts']), original_states=len(window['states']),
            independent_order_row_instances=sum(len(state['orders']) for state in window['states']), layouts=layouts))
    return windows, dict(windows=len(windows), layouts=len(windows) * len(LAYOUTS),
        imported_seed_orders=sum(window['imported_seed_orders'] for window in windows),
        facts=sum(window['facts'] for window in windows), original_states=sum(window['original_states'] for window in windows),
        complete_layout_states=sum(window['original_states'] for window in windows) * len(LAYOUTS),
        complete_layout_order_row_instances=sum(window['independent_order_row_instances'] for window in windows) * len(LAYOUTS),
        packets=packet_count, transmitted_occurrences=occurrence_count)


def _protected_inputs(args, output):
    """Freeze consumed paths once, preflight all sizes, then read bounded descriptors."""
    history_dir = args.history_dir.expanduser().resolve(strict=True)
    l3_dir = args.l3_dir.expanduser().resolve(strict=True)
    require(history_dir.is_dir() and l3_dir.is_dir(), 'retained artefact inputs must be directories')
    require(all(not output.is_relative_to(directory) and not directory.is_relative_to(output)
                for directory in (history_dir, l3_dir)), 'output overlaps a protected input directory')
    paths = {'history-evidence': args.history_evidence.expanduser().resolve(strict=True),
             'l3-evidence': args.l3_evidence.expanduser().resolve(strict=True),
             'history/producer.json': (history_dir / 'producer.json').resolve(strict=True)}
    for window_id in (1, 2):
        for name in WINDOW_FILES:
            label = 'history/producer/window-%03d/%s' % (window_id, name)
            paths[label] = (history_dir / 'producer' / ('window-%03d' % window_id) / name).resolve(strict=True)
    for name in L3_FILES:
        paths['l3/' + name] = (l3_dir / name).resolve(strict=True)
    require(len(set(paths.values())) == len(paths), 'protected input paths alias each other')
    tracked, inodes = {}, set()
    for label, path in paths.items():
        before = events.stat_identity(path)
        require(before[:2] not in inodes, 'protected input paths alias one inode')
        inodes.add(before[:2])
        maximum = MAX_CSV_BYTES if label.endswith('.csv') else MAX_JSON_BYTES
        rows = MAX_ROWS if label.endswith('.csv') else None
        require(before[2] <= maximum, 'protected input exceeds bound before hashing')
        require(path != output and not path.is_relative_to(output), 'output contains a protected input')
        tracked[label] = dict(path=path, before=before, maximum=maximum, rows=rows)
    captured = {}
    for label, item in tracked.items():
        require(events.stat_identity(item['path']) == item['before'], 'protected input changed before bounded read')
        captured[label], item['identity'] = read_blob(item['path'], item['maximum'], item['rows'])
        require(events.stat_identity(item['path']) == item['before'], 'protected input changed during bounded read')
    return captured, tracked


def _guard_inputs(tracked):
    for item in tracked.values():
        require(events.stat_identity(item['path']) == item['before'] and
                read_blob(item['path'], item['maximum'], item['rows'])[1] == item['identity'] and
                events.stat_identity(item['path']) == item['before'], 'protected small input changed during packet production')


def _guard_outputs(published):
    for path, (before, identity) in published.items():
        require(events.stat_identity(path) == before and read_blob(path, MAX_CSV_BYTES, MAX_ROWS)[1] == identity and
                events.stat_identity(path) == before, 'published CSV changed during packet production')


def _unlink_owned(path, identity):
    try:
        named = path.lstat()
        if stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == identity:
            path.unlink()
    except OSError:
        pass


def _publish_manifest(path, publication):
    """Keep inode ownership available even when publication's later guards fail."""
    require(type(publication) is bytes and len(publication) <= MAX_REPORT_BYTES, 'manifest exceeds serialised byte bound')
    stream = path.open('xb')
    opened = os.fstat(stream.fileno())
    owned = opened.st_dev, opened.st_ino
    try:
        with stream:
            require(stream.write(publication) == len(publication), 'manifest returned a short write')
        named = path.lstat()
        require(stat.S_ISREG(named.st_mode) and (named.st_dev, named.st_ino) == owned and named.st_size == len(publication),
                'manifest path/inode/byte count changed during write or close')
    except BaseException:
        _unlink_owned(path, owned)
        raise
    return blob_info(publication), owned


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for name in ('history-evidence', 'l3-evidence', 'history-dir', 'l3-dir', 'output'):
        parser.add_argument('--' + name, type=Path, action=events.Once, required=True)
    args = parser.parse_args(argv)
    output, manifest_inode, owned_output = None, None, False
    try:
        output = history.fresh_destination(args.output)
        private_root = (ROOT / 'out').resolve(strict=True)
        require(output != private_root and output.is_relative_to(private_root), 'private output must be inside repository out/')
        history.handoff.git(ROOT, 'check-ignore', '--no-index', str(output))
        source_before = source_snapshot(ROOT)
        require(all(not (ROOT / name).resolve(strict=True).is_relative_to(output) for name in source_before['files']),
                'output overlaps protected implementation files')
        captured, tracked = _protected_inputs(args, output)
        anchors = {
            'history': authenticate_anchor('history', args.history_evidence, captured['history-evidence']),
            'l3': authenticate_anchor('l3', args.l3_evidence, captured['l3-evidence'])}
        window_blobs = {window_id: {name: captured['history/producer/window-%03d/%s' % (window_id, name)]
                                  for name in WINDOW_FILES} for window_id in (1, 2)}
        l3_blobs = {name: captured['l3/' + name] for name in L3_FILES}
        binding = bind_inputs(captured['history-evidence'], captured['l3-evidence'], captured['history/producer.json'],
                              window_blobs, l3_blobs)
        first, second = build_bundle(binding), build_bundle(binding)
        require(first == second and len(first) == 14, 'two complete bundle constructions are not byte identical')
        windows, coverage = _coverage(binding)
        require(coverage == dict(windows=2, layouts=4, imported_seed_orders=2344, facts=13, original_states=15,
            complete_layout_states=30, complete_layout_order_row_instances=33772, packets=35, transmitted_occurrences=26),
            'canonical projection coverage differs from accepted profile')
        retained = _object(captured['history-evidence'])
        independent = _object(captured['l3-evidence'])
        # Loaded implementations must themselves belong to this clean source snapshot.
        for name in ('identified_history.py', 'identified_events.py', 'compare_l3.py'):
            key = 'bench/' + name
            require(source_before['files'].get(key) == retained['source']['files'].get(key),
                    'retained logical validation implementation has changed')
        require(source_before['files'].get('bench/repacketise_history.py') ==
                read_blob(Path(__file__).resolve(), history.MAX_SOURCE_BYTES)[1], 'producer is absent from clean source provenance')
        _guard_inputs(tracked)
        require(same(source_before, source_snapshot(ROOT)), 'source changed before publication')
        # Admission has completed before any output mutation.
        output.mkdir()
        owned_output = True
        published, file_identities = {}, {}
        for relative, blob in sorted(first.items()):
            path = output / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            identity = write_bytes(path, blob, MAX_CSV_BYTES)
            published[path] = events.stat_identity(path), identity
            file_identities[relative] = identity
        _guard_inputs(tracked)
        _guard_outputs(published)
        source_after = source_snapshot(ROOT)
        require(same(source_before, source_after), 'public implementation changed during packet production')
        report = dict(schema_version=1, gate=GATE, scope=SCOPE, passed=True, errors=[],
            raw_full_identity_freshly_verified=False, independent_reference_replayed=False,
            bundle_constructions=2, deterministic_bundle=True, source_before=source_before, source_after=source_after,
            anchors=anchors, inputs={label: item['identity'] for label, item in sorted(tracked.items())},
            retained_source_identity=binding['source_identity'],
            retained_producer=dict(commit=PRODUCER_COMMIT, **PRODUCER_IDENTITY,
                raw_identity_verified_in_prior_evidence=True, evidence_commit=PINS['history'][1]),
            retained_reference=independent['reference'], windows=windows, coverage=coverage, files=file_identities,
            checks=dict(pinned_current_and_historical_evidence=True, exact_retained_small_artefact_hashes=True,
                complete_original_occurrence_and_independent_inventory_binding=True, actual_unknown_seed_attribution=True,
                exact_framed_wire_validation=True, explicit_packet_message_source_joins=True,
                deterministic_two_bundle_constructions=True, bounded_checked_publication=True,
                protected_inputs_and_source_unchanged=True),
            limitations=['New datagrams contain only the selected-locate A/D/E projection; original Nasdaq packet boundaries and session ordinals are unknown',
                'Raw and prefix identities are retained from accepted prior evidence; neither raw data nor the independent implementation is reread or replayed here',
                'Imported seed attribution is unknown; insertion FIFO does not establish hidden exchange priority or parent aggressor identity',
                'No live network, recovery, receipt times, throughput, own orders, fills or strategy performance is modelled'])
        manifest_path = output / 'manifest.json'
        publication = canonical_bytes(report)
        manifest_identity, manifest_inode = _publish_manifest(manifest_path, publication)
        _guard_inputs(tracked)
        _guard_outputs(published)
        require(same(source_before, source_snapshot(ROOT)), 'public implementation changed during manifest publication')
        require(read_blob(manifest_path, MAX_REPORT_BYTES)[1] == manifest_identity, 'manifest changed during checked publication')
        print('Authenticated two-window bundle: 13 facts, 35 packets, 26 explicit occurrence joins', flush=True)
        return 0
    except (OSError, ValueError, KeyError, TypeError, OverflowError, UnicodeError, RuntimeError, RecursionError) as error:
        if owned_output and output is not None:
            if manifest_inode is not None:
                _unlink_owned(output / 'manifest.json', manifest_inode)
            try:
                write_bytes(output / 'failure.json', canonical_bytes(dict(schema_version=1, gate=GATE, passed=False,
                    raw_full_identity_freshly_verified=False, independent_reference_replayed=False, errors=[str(error)])), MAX_REPORT_BYTES)
            except (OSError, ValueError, TypeError, OverflowError):
                pass
        print('Canonical repacketisation failed: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
