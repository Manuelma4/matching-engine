"""One passive share over a bounded identified A,D,A,A,E prefix.

Own state stays outside historical references. Named external executions reduce
shares ahead only; they never imply a fill for our hypothetical marker. The
selected-book closure/status policy and retained source identities require a
separate canonical boundary. This pure module authenticates none of them.
"""
from copy import deepcopy
import heapq

import identified_events as identified
from identified_queue import CONFIG_KEYS, MAX_RESULT_BYTES, clock_add, inventory_sha256, require

MODEL = "identified_execution_prefix_shadow_queue_v1"
MAX_TRACE_ROWS = 32
MAX_PENDING_EVENTS = 32


def simulate_execution_prefix(document, config, expected_sources=None):
    """Return a bounded named-order trace without inferring own fills.

    Consume exactly A,D,A,A,E and six complete immutable source inventories.
    Equal-time phases are selected source, captured feed, strategy, request
    arrival and own response. Foreign source gaps are permitted; canonical
    coverage/status admission belongs to a separately verified boundary.
    Pending events never extend the inclusive final-E horizon. Invalid inputs
    raise ValueError without returning partial state or mutating caller input.
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
    facts = document["facts"]
    require(len(facts) == 5, "profile", "exactly five source facts are required")
    require([fact["source"]["type"] for fact in facts] == ["A", "D", "A", "A", "E"],
            "profile", "only the A,D,A,A,E source pattern is supported")
    snapshots = validated["snapshots"]
    start = snapshots[0]["source"]["timestamp_ns"]
    end = snapshots[-1]["source"]["timestamp_ns"]
    times = [snapshot["origin_ns"] for snapshot in snapshots]
    require(len(snapshots) == 6 and times[0] == start and
            all(earlier < later for earlier, later in zip(times, times[1:])),
            "profile", "exact seed time and strictly increasing source times are required")
    require(config["horizon_ns"] == end, "profile", "horizon must remain the final E time")

    best, levels = [], []
    for snapshot in snapshots:
        orders = snapshot["orders"]
        bid = next((row["price4"] for row in orders if row["side"] == "B"), None)
        ask = next((row["price4"] for row in orders if row["side"] == "S"), None)
        require(bid is not None and ask is not None and bid < ask,
                "profile", "two populated strictly uncrossed quotes are required")
        require(not best or (bid, ask) == best[0],
                "profile", "both best prices must stay fixed across the prefix")
        best.append((bid, ask))
    execution = facts[-1]["before_order"]
    price = best[0][0]
    require(execution["side"] == "B" and execution["price4"] == price,
            "profile", "the named E must concern the fixed best bid")
    for snapshot in snapshots:
        levels.append([row for row in snapshot["orders"]
                       if row["side"] == "B" and row["price4"] == price])
    require(start <= config["decision_ns"] <= end,
            "config", "decision lies outside the source interval")
    require(cancel is None or config["decision_ns"] <= cancel <= end,
            "config", "cancel lies outside decision-to-horizon interval")

    queue, serial = [], 0

    def push(time, phase, event, origin, index=None):
        nonlocal serial
        heapq.heappush(queue, (time, phase, serial, event, origin, index))
        serial += 1

    for index, snapshot in enumerate(snapshots):
        origin = snapshot["origin_ns"]
        suffix = "seed" if index == 0 else facts[index - 1]["source"]["type"]
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
        if event.startswith("source_"):
            historical_index = index
            if index and exchange_state == "live":
                fact = facts[index - 1]
                if fact["source"]["type"] in ("D", "E") and fact["after_order"] is None:
                    # Only the named depleted reference leaves the ahead cohort.
                    ahead = [ref for ref in ahead if ref != fact["before_order"]["reference"]]
                # Partial E keeps that reference's place. Capture reads its new
                # remaining shares from the current complete historical inventory.
                # New A references never join an already accepted marker's cohort.
        elif event.startswith("feed_"):
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
