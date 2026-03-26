"""
AMR (Autonomous Mobile Robot) Simulator — Backend
===================================================
REST API that simulates a warehouse robot for the employee admittance test.
Supports webhook callbacks for real-time status updates.
"""
import random
import time
import threading
import uuid
import requests as http_client
from flask import Flask, request, jsonify
from flask_cors import CORS

import config
from models import robot, warehouse

app = Flask(__name__)
CORS(app)

# Registered callback URL (set by the candidate)
callback_state = {
    "url": None,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_coordinate(data, key):
    """Extract and validate a coordinate dict {x, y} from request JSON."""
    coord = data.get(key)
    if coord is None:
        return None, f"Missing '{key}' in request body."
    if not isinstance(coord, dict):
        return None, f"'{key}' must be an object with 'x' and 'y' fields."
    try:
        x = float(coord["x"])
        y = float(coord["y"])
    except (KeyError, TypeError, ValueError):
        return None, f"'{key}' must contain numeric 'x' and 'y' fields."
    return {"x": x, "y": y}, None


def _make_task_entry(task_id, task_type, source, destination, result, reason=None):
    entry = {
        "task_id": task_id,
        "task_type": task_type,
        "source": source,
        "destination": destination,
        "result": result,
        "timestamp": time.time(),
    }
    if reason:
        entry["reason"] = reason
    return entry


def _send_callback(task_id, status, detail=None):
    """Send an HTTP POST callback to the registered URL (fire-and-forget)."""
    url = callback_state["url"]
    if not url:
        return
    payload = {
        "task_id": task_id,
        "status": status,
        "robot": robot.to_dict(),
        "timestamp": time.time(),
    }
    if detail:
        payload["detail"] = detail
    try:
        http_client.post(url, json=payload, timeout=3)
    except Exception:
        pass  # candidate's server may be down — don't block the simulation


def _run_transport_async(task_id, task_type, source, destination,
                         src_type, src_loc, dst_type, dst_loc):
    """Execute the transport in a background thread, sending callbacks at each phase."""
    delays = config.CALLBACK_DELAYS

    # Phase 1: Moving to source
    robot.state = "moving"
    _send_callback(task_id, "moving_to_source", {
        "message": f"Robot is moving to {src_loc['id']} at ({source['x']}, {source['y']}).",
        "from": {"x": robot.x, "y": robot.y},
        "to": source,
    })
    time.sleep(delays["moving_to_source"])

    # Phase 2: Arrived at source
    robot.x = source["x"]
    robot.y = source["y"]
    robot.state = "idle"
    _send_callback(task_id, "arrived_at_source", {
        "message": f"Robot arrived at {src_loc['id']}.",
    })
    time.sleep(delays["arrived_at_source"])

    # Phase 3: Lifting item
    robot.state = "lifting"
    warehouse.item_counter += 1
    item_id = f"ITEM-{warehouse.item_counter:04d}"
    _send_callback(task_id, "lifting", {
        "message": f"Robot is lifting item {item_id} at {src_loc['id']}.",
        "item_id": item_id,
    })
    time.sleep(delays["lifting"])

    # Phase 4: Item lifted
    robot.carrying_item = item_id
    robot.state = "carrying"
    if src_type == "storage":
        src_loc["current_load"] -= 1
    _send_callback(task_id, "item_lifted", {
        "message": f"Item {item_id} lifted successfully.",
        "item_id": item_id,
    })
    time.sleep(delays["item_lifted"])

    # Phase 5: Moving to destination
    robot.state = "moving"
    _send_callback(task_id, "moving_to_destination", {
        "message": f"Robot is moving to {dst_loc['id']} at ({destination['x']}, {destination['y']}).",
        "from": source,
        "to": destination,
        "item_id": item_id,
    })
    time.sleep(delays["moving_to_destination"])

    # Phase 6: Arrived at destination
    robot.x = destination["x"]
    robot.y = destination["y"]
    _send_callback(task_id, "arrived_at_destination", {
        "message": f"Robot arrived at {dst_loc['id']}.",
        "item_id": item_id,
    })
    time.sleep(delays["arrived_at_destination"])

    # Phase 7: Lowering item
    robot.state = "lowering"
    _send_callback(task_id, "lowering", {
        "message": f"Robot is lowering item {item_id} at {dst_loc['id']}.",
        "item_id": item_id,
    })
    time.sleep(delays["lowering"])

    # Phase 8: Item placed
    if dst_type == "storage":
        dst_loc["current_load"] += 1
    robot.carrying_item = None
    _send_callback(task_id, "item_placed", {
        "message": f"Item {item_id} placed at {dst_loc['id']}.",
        "item_id": item_id,
    })
    time.sleep(delays["item_placed"])

    # Phase 9: Completed
    robot.state = "idle"
    robot.current_task_id = None
    msg = (f"Transport complete ({task_type}). Item {item_id} moved from "
           f"{src_loc['id']} to {dst_loc['id']}.")
    _send_callback(task_id, "completed", {
        "message": msg,
        "item_id": item_id,
        "task_type": task_type,
        "source_location": src_loc["id"],
        "destination_location": dst_loc["id"],
    })

    robot.task_log.append(_make_task_entry(task_id, task_type, source, destination, "success"))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.route("/api/warehouse/info", methods=["GET"])
def warehouse_info():
    """Return warehouse layout, storage locations, workstation docking points,
    and restricted zones so the candidate can plan movements."""
    return jsonify({
        "warehouse": {
            "width": config.WAREHOUSE_WIDTH,
            "height": config.WAREHOUSE_HEIGHT,
        },
        "storage_locations": warehouse.storage_locations,
        "workstation_locations": warehouse.workstation_locations,
        "restricted_zones": warehouse.restricted_zones,
        "docking_tolerance": config.DOCKING_TOLERANCE,
    })


@app.route("/api/callback/register", methods=["POST"])
def register_callback():
    """
    Register a callback URL to receive status updates during transport.
    Body JSON: {"url": "http://localhost:XXXX/your-endpoint"}
    """
    data = request.get_json(silent=True) or {}
    url = data.get("url")
    if not url or not isinstance(url, str):
        return jsonify({"success": False, "message": "Missing or invalid 'url' field."}), 400
    callback_state["url"] = url
    return jsonify({
        "success": True,
        "message": f"Callback registered: {url}",
        "callback_url": url,
    })


@app.route("/api/callback/unregister", methods=["POST"])
def unregister_callback():
    """Remove the registered callback URL."""
    callback_state["url"] = None
    return jsonify({"success": True, "message": "Callback unregistered."})


@app.route("/api/callback/status", methods=["GET"])
def callback_status():
    """Check the currently registered callback URL."""
    return jsonify({
        "callback_url": callback_state["url"],
        "registered": callback_state["url"] is not None,
    })


@app.route("/api/robot/status", methods=["GET"])
def robot_status():
    """Return the robot's current position and state."""
    return jsonify({
        "robot": robot.to_dict(),
        "current_task_id": robot.current_task_id,
    })


@app.route("/api/robot/transport", methods=["POST"])
def transport():
    """
    Main command endpoint.
    Body JSON:
    {
        "source":      {"x": <float>, "y": <float>},
        "destination": {"x": <float>, "y": <float>}
    }
    The robot will:
      1. Move to source, pick up an item.
      2. Move to destination, drop off the item.

    The endpoint returns immediately with a task_id and "accepted" status.
    If a callback URL is registered, the backend will send HTTP POST
    updates to that URL as the robot progresses through each phase.

    Returns {"success": true/false, "message": "...", "task_id": "..."}.
    """
    data = request.get_json(silent=True) or {}

    # --- Parse coordinates ---------------------------------------------------
    source, err = _validate_coordinate(data, "source")
    if err:
        return jsonify({"success": False, "message": err}), 400

    destination, err = _validate_coordinate(data, "destination")
    if err:
        return jsonify({"success": False, "message": err}), 400

    task_id = str(uuid.uuid4())[:8]

    # --- Pre-flight checks ---------------------------------------------------
    # Robot must be idle
    if robot.state not in ("idle",):
        msg = f"Robot is currently '{robot.state}'. Wait until it is idle."
        robot.task_log.append(_make_task_entry(task_id, "transport", source, destination, "failure", msg))
        return jsonify({"success": False, "message": msg, "task_id": task_id}), 409

    # Bounds check
    for label, coord in [("source", source), ("destination", destination)]:
        if not warehouse.is_in_bounds(coord["x"], coord["y"]):
            msg = f"The {label} coordinate ({coord['x']}, {coord['y']}) is outside the warehouse boundaries (0-{config.WAREHOUSE_WIDTH}, 0-{config.WAREHOUSE_HEIGHT})."
            robot.task_log.append(_make_task_entry(task_id, "transport", source, destination, "failure", msg))
            return jsonify({"success": False, "message": msg, "task_id": task_id}), 400

    # Restricted zone check
    for label, coord in [("source", source), ("destination", destination)]:
        restricted, zone_label = warehouse.is_in_restricted_zone(coord["x"], coord["y"])
        if restricted:
            msg = f"The {label} coordinate ({coord['x']}, {coord['y']}) is inside restricted zone '{zone_label}'."
            robot.task_log.append(_make_task_entry(task_id, "transport", source, destination, "failure", msg))
            return jsonify({"success": False, "message": msg, "task_id": task_id}), 400

    # Source must be a known location (storage or workstation)
    src_type, src_loc = warehouse.find_location_at(source["x"], source["y"])
    if src_loc is None:
        msg = (f"No known location (storage or workstation) found at source "
               f"({source['x']}, {source['y']}). The robot can only pick up "
               f"from registered locations.")
        robot.task_log.append(_make_task_entry(task_id, "transport", source, destination, "failure", msg))
        return jsonify({"success": False, "message": msg, "task_id": task_id}), 400

    # Destination must be a known location
    dst_type, dst_loc = warehouse.find_location_at(destination["x"], destination["y"])
    if dst_loc is None:
        msg = (f"No known location (storage or workstation) found at destination "
               f"({destination['x']}, {destination['y']}). The robot can only "
               f"drop off at registered locations.")
        robot.task_log.append(_make_task_entry(task_id, "transport", source, destination, "failure", msg))
        return jsonify({"success": False, "message": msg, "task_id": task_id}), 400

    # --- Determine task type (inbound / outbound / transfer) -----------------
    if src_type == "workstation" and dst_type == "storage":
        task_type = "inbound"
    elif src_type == "storage" and dst_type == "workstation":
        task_type = "outbound"
    elif src_type == "storage" and dst_type == "storage":
        task_type = "transfer"
    elif src_type == "workstation" and dst_type == "workstation":
        task_type = "ws-transfer"
    else:
        task_type = "transport"

    # --- Inbound: check storage capacity at destination ----------------------
    if dst_type == "storage":
        if dst_loc["current_load"] >= dst_loc["capacity"]:
            msg = (f"Storage {dst_loc['id']} is full "
                   f"({dst_loc['current_load']}/{dst_loc['capacity']}). "
                   f"Choose a different storage location.")
            robot.task_log.append(_make_task_entry(task_id, task_type, source, destination, "failure", msg))
            return jsonify({"success": False, "message": msg, "task_id": task_id}), 409

    # --- Outbound: check storage has items to retrieve -----------------------
    if src_type == "storage":
        if src_loc["current_load"] <= 0:
            msg = (f"Storage {src_loc['id']} is empty — nothing to pick up.")
            robot.task_log.append(_make_task_entry(task_id, task_type, source, destination, "failure", msg))
            return jsonify({"success": False, "message": msg, "task_id": task_id}), 409

    # --- Random transient failure (simulates real-world hiccups) -------------
    if random.random() < config.RANDOM_FAILURE_RATE:
        robot.state = "error"
        msg = "Transient sensor error detected during navigation. Please retry."
        robot.task_log.append(_make_task_entry(task_id, task_type, source, destination, "failure", msg))
        # Auto-recover after reporting
        robot.state = "idle"
        return jsonify({"success": False, "message": msg, "task_id": task_id}), 503

    # --- Accept and execute transport asynchronously -------------------------
    robot.state = "moving"
    robot.current_task_id = task_id

    thread = threading.Thread(
        target=_run_transport_async,
        args=(task_id, task_type, source, destination,
              src_type, src_loc, dst_type, dst_loc),
        daemon=True,
    )
    thread.start()

    return jsonify({
        "success": True,
        "message": (f"Transport accepted ({task_type}). Task {task_id} is now in progress. "
                    f"Robot moving from {src_loc['id']} to {dst_loc['id']}."),
        "task_id": task_id,
        "task_type": task_type,
        "source_location": src_loc["id"],
        "destination_location": dst_loc["id"],
        "callback_registered": callback_state["url"] is not None,
    })


@app.route("/api/robot/task-log", methods=["GET"])
def task_log():
    """Return the list of all executed (and failed) tasks."""
    return jsonify({"tasks": robot.task_log})


@app.route("/api/reset", methods=["POST"])
def reset():
    """Reset the simulator to its initial state."""
    robot.reset()
    warehouse.reset()
    return jsonify({"success": True, "message": "Simulator reset to initial state."})


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

@app.errorhandler(404)
def not_found(_):
    return jsonify({"success": False, "message": "Endpoint not found."}), 404


@app.errorhandler(405)
def method_not_allowed(_):
    return jsonify({"success": False, "message": "Method not allowed."}), 405


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("  AMR Simulator Backend")
    print("  http://localhost:5000")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
