"""One passive, one-share shadow order around one atomic best-bid replacement.

This pure model consumes a validated identified ledger. It authenticates neither
raw input nor session status: a separate boundary must admit the exact source
pair, completed timestamp group and status policy. The only source horizon is U.
Historical inventories never contain our hypothetical order. Queue position is
a declared tail-insertion convention, with no trades or empirical fill claim.
"""
from copy import deepcopy
import hashlib
import heapq
import json

import identified_events as identified

MODEL = "one_u_identified_shadow_queue_v1"
CONFIG_KEYS = {"quantity", "decision_ns", "cancel_ns", "horizon_ns",
               "feed_delay_ns", "order_delay_ns", "response_delay_ns"}
MAX_TRACE_ROWS = 16
MAX_PENDING_EVENTS = 16
MAX_RESULT_BYTES = 32 << 20


def require(condition, category, message):
    if not condition:
        raise ValueError(category + ": " + message)


def clock_add(origin, delay):
    value = origin + delay
    require(value <= identified.U64, "clock", "derived event time exceeds uint64")
    return value


def inventory_sha256(orders):
    """Identity of a complete logical order list, retaining its price/FIFO order."""
    payload = (json.dumps(orders, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=True, allow_nan=False) + "\n").encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def simulate_one_u(document, config, expected_sources=None):
    """Return bounded trace, complete historical states and pending event metadata.

    Equal-time phases are source (1), captured feed (2), strategy (3), request
    arrival (4), and own response (5). Ties within a phase retain scheduling order.
    The decision uses only the captured delivered inventory; feed is never an own
    acknowledgement. Requests/responses beyond the inclusive U horizon stay pending.
    Invalid input raises ValueError without returning a partial result or mutating
    caller input. Only a same-price buy-side U at the unchanged best bid is supported.
    """
    require(type(config) is dict and set(config) == CONFIG_KEYS,
            "config", "invalid closed configuration fields")
    require(type(config["quantity"]) is int and config["quantity"] == 1,
            "config", "only one share is supported")
    for name in CONFIG_KEYS - {"quantity", "cancel_ns"}:
        require(identified.uint(config[name]), "config", "invalid uint64 " + name)
    cancel = config["cancel_ns"]
    require(cancel is None or identified.uint(cancel), "config", "invalid cancel time")

    try:
        validated = identified.validate_ledger(document, expected_sources)
    except ValueError as error:
        raise ValueError("profile: invalid identified ledger: " + str(error)) from error
    require(len(document["facts"]) == 1, "profile", "exactly one source fact is required")
    fact = document["facts"][0]
    require(fact["kind"] == "replace" and fact["source"]["type"] == "U",
            "profile", "only one atomic U is supported")
    snapshots = validated["snapshots"]
    pre, post = snapshots[0]["source"], snapshots[1]["source"]
    start, end = pre["timestamp_ns"], post["timestamp_ns"]
    require(snapshots[0]["origin_ns"] == start and start < end,
            "profile", "seed must be exact and U strictly later")
    require(post["sequence"] == pre["sequence"] + 1 and
            post["frame_offset"] == pre["frame_end_offset"],
            "profile", "source pair must be globally consecutive and byte-contiguous")
    require(config["horizon_ns"] == end, "profile", "horizon must remain the final U time")
    require(start <= config["decision_ns"] <= end,
            "config", "decision lies outside the source interval")
    require(cancel is None or config["decision_ns"] <= cancel <= end,
            "config", "cancel lies outside decision-to-horizon interval")

    best, levels = [], []
    for snapshot in snapshots:
        orders = snapshot["orders"]
        bid = next((row["price4"] for row in orders if row["side"] == "B"), None)
        ask = next((row["price4"] for row in orders if row["side"] == "S"), None)
        require(bid is not None and ask is not None and bid < ask,
                "profile", "a strictly higher displayed opposite quote is required")
        best.append((bid, ask))
    before, after = fact["before_order"], fact["after_order"]
    price = best[0][0]
    require(before["side"] == after["side"] == "B" and
            before["price4"] == after["price4"] == price == best[1][0],
            "profile", "U must retain the selected best-bid price and buy side")
    for snapshot in snapshots:
        levels.append([row for row in snapshot["orders"]
                       if row["side"] == "B" and row["price4"] == price])

    queue, serial = [], 0

    def push(time, phase, event, origin, index=None):
        nonlocal serial
        heapq.heappush(queue, (time, phase, serial, event, origin, index))
        serial += 1

    for index, snapshot in enumerate(snapshots):
        origin = snapshot["origin_ns"]
        suffix = "seed" if index == 0 else "U"
        push(origin, 1, "source_" + suffix, origin, index)
        push(clock_add(origin, config["feed_delay_ns"]), 2,
             "feed_" + suffix, origin, index)
    push(config["decision_ns"], 3, "decision", config["decision_ns"])
    if cancel is not None:
        push(cancel, 3, "cancel_decision", cancel)

    historical_index = 0
    observed_index = None
    delivered_orders = None
    delivered_digest = None
    limit = None
    ahead = []
    exchange_state, local_state = "idle", "idle"
    exchange_remaining = accepted_quantity = cancelled_quantity = requested = 0
    confirmed = None
    submitted = cancel_requested = False
    trace = []

    def capture():
        current = {row["reference"]: row["shares"] for row in levels[historical_index]}
        require(all(reference in current for reference in ahead),
                "profile", "ahead reference is absent from current external level")
        observed_origin = (None if observed_index is None else
                           snapshots[observed_index]["origin_ns"])
        return dict(historical_event_index=historical_index,
                    observed_event_index=observed_index,
                    observed_origin_ns=observed_origin,
                    observed_delivery_ns=(None if observed_origin is None else
                                          clock_add(observed_origin, config["feed_delay_ns"])),
                    observed_inventory_sha256=delivered_digest,
                    external_level_shares=sum(current.values()), limit_price4=limit,
                    ahead_references=list(ahead), ahead_shares=sum(current[ref] for ref in ahead),
                    exchange_state=exchange_state, exchange_remaining=exchange_remaining,
                    accepted_quantity=accepted_quantity, cancelled_quantity=cancelled_quantity,
                    local_state=local_state, local_request_quantity=requested,
                    local_confirmed_remaining=confirmed, submitted=submitted,
                    cancel_requested=cancel_requested,
                    exchange_account=dict(filled=0, position=0, cash4=0, fees4=0),
                    local_account=dict(filled=0, position=0, cash4=0, fees4=0))

    while queue and queue[0][0] <= end:
        time, phase, _, event, origin, index = heapq.heappop(queue)
        require(len(trace) < MAX_TRACE_ROWS, "profile", "trace row bound exceeded")
        if event == "source_seed":
            historical_index = 0
        elif event == "source_U":
            historical_index = 1
            if exchange_state == "live":
                # Atomic removal changes the ahead set. The replacement joins behind
                # our already accepted marker, and never enters that set.
                ahead = [ref for ref in ahead if ref != before["reference"]]
        elif event in ("feed_seed", "feed_U"):
            observed_index = index
            delivered_orders = snapshots[index]["orders"]
            delivered_digest = inventory_sha256(delivered_orders)
        elif event == "decision":
            if delivered_orders is None:
                event = "decision_skip"
            else:
                # This is the captured payload, not the current exchange inventory.
                limit = next(row["price4"] for row in delivered_orders if row["side"] == "B")
                local_state, requested, submitted = "pending", 1, True
                push(clock_add(time, config["order_delay_ns"]), 4, "arrival", time)
                event = "submit"
        elif event == "arrival":
            require(limit == best[historical_index][0] and limit < best[historical_index][1],
                    "profile", "arrival is outside the passive best-bid profile")
            exchange_state, exchange_remaining, accepted_quantity = "live", 1, 1
            ahead = [row["reference"] for row in levels[historical_index]]
            push(clock_add(time, config["response_delay_ns"]), 5, "response_accept", time)
            event = "arrival_accept"
        elif event == "cancel_decision":
            if local_state != "live" or delivered_orders is None:
                event = "cancel_skip"
            else:
                local_state, cancel_requested = "cancel_pending", True
                push(clock_add(time, config["order_delay_ns"]), 4, "cancel_arrival", time)
                event = "cancel_request"
        elif event == "cancel_arrival":
            require(exchange_state == "live", "profile", "cancel has no live own marker")
            exchange_state, exchange_remaining, cancelled_quantity = "cancelled", 0, 1
            ahead = []
            push(clock_add(time, config["response_delay_ns"]), 5, "response_cancel", time)
            event = "cancel_accept"
        elif event == "response_accept":
            # The immutable own outcome is one accepted share, not a feed update.
            local_state, confirmed = "live", 1
        elif event == "response_cancel":
            local_state, confirmed = "cancelled", 0
        else:
            raise ValueError("profile: unknown scheduled event")
        trace.append(dict(time_ns=time, phase=phase, event=event, origin_ns=origin,
                          event_index=index, state=capture()))

    require(len(queue) <= MAX_PENDING_EVENTS, "profile", "pending event bound exceeded")
    pending = [dict(time_ns=time, phase=phase, event=event, origin_ns=origin, event_index=index)
               for time, phase, _, event, origin, index in sorted(queue)]
    result = dict(schema_version=1, model=MODEL, raw_input_identity_verified=False,
                  status_admission_verified=False, source_coverage_authenticated=False,
                  config=deepcopy(config), symbol=document["symbol"], locate=document["locate"],
                  historical_snapshots=snapshots, trace=trace, pending=pending,
                  final=deepcopy(trace[-1]["state"]))
    identified.encoded_size(result, MAX_RESULT_BYTES, "profile: result")
    return result
