# AMR System Integration — Admittance Test

## Overview

You are tasked with building a **client application** that integrates with an Autonomous Mobile Robot (AMR) simulator running in a warehouse environment. The simulator backend is already running and exposes a REST API.

Your goal is to create a program that can command the robot to perform **inbound** and **outbound** transport tasks within the warehouse.

**Important:** The robot operates **asynchronously**. When you send a transport command, the backend accepts the task and the robot begins executing it in the background. The backend will send **real-time status callbacks** (HTTP POST) to your application as the robot progresses through each phase of the transport. You must set up an HTTP server to receive these callbacks.

---

## Definitions

| Term         | Meaning |
|--------------|---------|
| **Inbound**  | Pick up an item from a **workstation** and store it in a **storage location**. |
| **Outbound** | Retrieve an item from a **storage location** and deliver it to a **workstation**. |
| **Workstation** | A fixed point in the warehouse where items are produced or consumed (e.g., assembly line, packaging station). |
| **Storage Location** | A rack/shelf area where items are kept. Each has a finite capacity. |
| **AMR** | The autonomous mobile robot that physically moves items between locations. |

---

## Backend API Reference

The simulator backend runs at **`http://localhost:5000`**.

### 1. `GET /api/warehouse/info`

Returns the full warehouse layout including:

- Warehouse dimensions (width × height in meters)
- All **storage locations** with their coordinates, capacity, and current load
- All **workstation locations** with their coordinates and names
- **Restricted zones** the robot cannot enter
- **Docking tolerance** (how close coordinates must be to match a location)

**Example response:**

```json
{
  "warehouse": { "width": 50, "height": 30 },
  "storage_locations": [
    { "id": "S-01", "x": 5, "y": 5, "capacity": 10, "current_load": 3 }
  ],
  "workstation_locations": [
    { "id": "WS-01", "x": 40, "y": 5, "name": "Assembly Line A" }
  ],
  "restricted_zones": [
    { "x_min": 20, "y_min": 10, "x_max": 25, "y_max": 20, "label": "Pillar Block A" }
  ],
  "docking_tolerance": 1.0
}
```

### 2. `GET /api/robot/status`

Returns the robot's current position, state, and whether it is carrying an item.

**Example response:**

```json
{
  "robot": {
    "x": 25, "y": 15,
    "state": "idle",
    "carrying_item": null
  },
  "current_task_id": null
}
```

Possible states: `idle`, `moving`, `lifting`, `carrying`, `lowering`, `error`.

### 3. `POST /api/robot/transport`

**This is the main command endpoint.** Send a source coordinate and a destination coordinate. The robot will pick up from the source and deliver to the destination.

**The transport is asynchronous.** The endpoint validates the request and returns immediately with a `task_id`. The robot then executes the transport in the background, sending status callbacks to your registered callback URL.

**Request body:**

```json
{
  "source":      { "x": 40, "y": 5 },
  "destination": { "x": 5,  "y": 5 }
}
```

**Success response (200) — task accepted:**

```json
{
  "success": true,
  "message": "Transport accepted (inbound). Task a1b2c3d4 is now in progress. Robot moving from WS-01 to S-01.",
  "task_id": "a1b2c3d4",
  "task_type": "inbound",
  "source_location": "WS-01",
  "destination_location": "S-01",
  "callback_registered": true
}
```

**Failure response (400 / 409 / 503):**

```json
{
  "success": false,
  "message": "Storage S-03 is full (8/8). Choose a different storage location.",
  "task_id": "e5f6g7h8"
}
```

**Note:** While a task is in progress, the robot is **busy**. Sending another transport command will return a `409` error with `"Robot is currently 'moving'. Wait until it is idle."`. You must wait for the current task to complete before sending the next command.

### 4. `POST /api/callback/register`

**Register your application's callback URL** to receive real-time status updates from the robot.

**Request body:**

```json
{
  "url": "http://localhost:3000/amr/callback"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Callback registered: http://localhost:3000/amr/callback",
  "callback_url": "http://localhost:3000/amr/callback"
}
```

### 5. `POST /api/callback/unregister`

Remove the registered callback URL. No request body required.

### 6. `GET /api/callback/status`

Check the currently registered callback URL.

### 7. `GET /api/robot/task-log`

Returns a chronological log of all transport tasks (both successful and failed).

### 8. `POST /api/reset`

Resets the simulator to its initial state (robot position, storage loads, task log, callback registration).

---

## Status Callback System

When you register a callback URL, the backend will send **HTTP POST requests** to your URL as the robot progresses through each phase of a transport task.

### Callback Phases (in order)

Each transport task goes through these phases:

| # | Status | Robot State | Description |
|---|--------|-------------|-------------|
| 1 | `moving_to_source` | `moving` | Robot is navigating to the pickup location |
| 2 | `arrived_at_source` | `idle` | Robot has arrived at the source location |
| 3 | `lifting` | `lifting` | Robot is lifting/picking up the item |
| 4 | `item_lifted` | `carrying` | Item has been picked up, robot is holding it |
| 5 | `moving_to_destination` | `moving` | Robot is navigating to the drop-off location |
| 6 | `arrived_at_destination` | `moving` | Robot has arrived at the destination |
| 7 | `lowering` | `lowering` | Robot is lowering/placing the item |
| 8 | `item_placed` | `lowering` | Item has been placed at the destination |
| 9 | `completed` | `idle` | Transport task is complete, robot is ready for next command |

### Callback Payload Format

Each callback is an HTTP POST with a JSON body:

```json
{
  "task_id": "a1b2c3d4",
  "status": "lifting",
  "robot": {
    "x": 40, "y": 5,
    "state": "lifting",
    "carrying_item": null
  },
  "timestamp": 1711468800.123,
  "detail": {
    "message": "Robot is lifting item ITEM-0001 at WS-01.",
    "item_id": "ITEM-0001"
  }
}
```

### Important Notes on Callbacks

- Callbacks are **fire-and-forget** — if your server is down or returns an error, the robot continues its task anyway.
- You must have your HTTP server running **before** registering the callback URL.
- The `completed` callback indicates the robot is idle and ready for the next command.
- Use the `task_id` to correlate callbacks with the transport command you sent.

---

## Your Tasks

You must write a program (in **any programming language**) that accomplishes the following:

### Task 1 — Warehouse Discovery

Query the backend to retrieve all workstation and storage locations. Display or store them in a structured way within your application.

### Task 2 — Callback Receiver

Set up an HTTP server endpoint in your application that:

1. Listens for incoming POST requests from the AMR backend.
2. Parses the callback payload (task_id, status, robot state, detail).
3. Logs or displays each status update as it arrives (e.g., print to console).
4. Register this endpoint with the backend using `POST /api/callback/register`.

### Task 3 — Inbound Operations

Create a function/command that performs an **inbound** transport:

1. Accept a workstation identifier (e.g., `WS-01`) as input.
2. Automatically select an available storage location (one that is **not full**).
3. Send the transport command to the robot using the correct coordinates.
4. Wait for the `completed` callback (or poll robot status) to confirm the task finished.
5. Report success or failure to the user.

### Task 4 — Outbound Operations

Create a function/command that performs an **outbound** transport:

1. Accept a storage location identifier (e.g., `S-01`) and a workstation identifier (e.g., `WS-03`) as input.
2. Verify the storage location has items to retrieve (current_load > 0).
3. Send the transport command to the robot.
4. Wait for the `completed` callback to confirm the task finished.
5. Report success or failure to the user.

### Task 5 — Error Handling

Your program must handle the following failure scenarios gracefully:

- **Full storage**: Automatically pick a different storage location when one is full.
- **Empty storage**: Inform the user and prevent sending a doomed request.
- **Transient errors (503)**: Implement a retry mechanism (the backend has a 5% random failure rate).
- **Out-of-bounds coordinates**: Validate coordinates before sending.
- **Robot busy (409)**: Wait for the current task to complete (listen for `completed` callback or poll `/api/robot/status`) before sending the next command.

### Task 6 — Batch Operations (Bonus)

Implement a batch mode that processes a list of inbound/outbound commands sequentially. Each command must wait for the previous one to complete (via callback) before starting the next.

**Example input:**

```
INBOUND  WS-01
INBOUND  WS-02
OUTBOUND S-01 WS-03
INBOUND  WS-04
OUTBOUND S-05 WS-01
```

---

## Evaluation Criteria

| Criteria                  | Weight | Description |
|---------------------------|--------|-------------|
| **Correctness**           | 25%    | Does the program correctly perform inbound and outbound operations? |
| **Callback Handling**     | 20%    | Does it properly receive, parse, and act on status callbacks? |
| **Error Handling**        | 20%    | Does it handle edge cases (full storage, empty storage, transient errors, retries, robot busy)? |
| **Code Quality**          | 15%    | Is the code well-structured, readable, and maintainable? |
| **API Integration**       | 10%    | Does it correctly parse and use the warehouse info from the API? |
| **Bonus (Batch Mode)**    | 10%    | Is a batch processing mode implemented with proper sequencing? |

---

## Getting Started

1. **Start the backend:**

   ```bash
   pip install -r requirements.txt
   python app.py
   ```

   The server will start on `http://localhost:5000`.

2. **Verify the backend is running:**

   ```bash
   curl http://localhost:5000/api/warehouse/info
   ```

3. **Set up your callback receiver** — create an HTTP server in your application that listens on a port (e.g., `http://localhost:3000/amr/callback`).

4. **Register your callback URL:**

   ```bash
   curl -X POST http://localhost:5000/api/callback/register \
     -H "Content-Type: application/json" \
     -d '{"url": "http://localhost:3000/amr/callback"}'
   ```

5. **Test a transport command:**

   ```bash
   curl -X POST http://localhost:5000/api/robot/transport \
     -H "Content-Type: application/json" \
     -d '{"source": {"x": 40, "y": 5}, "destination": {"x": 5, "y": 5}}'
   ```

   You should see status callbacks arriving at your server within a few seconds.

---

## Rules

- You may use **any programming language and libraries** of your choice.
- You may **not** modify the backend code.
- Your program should work against a **fresh simulator state** (call `POST /api/reset` at the start if needed).
- Time limit: **2 hours**.

---

## Warehouse Layout (Visual Reference)

```
 Y
30 ┌──────────────────────────────────────────────────┐
   │                                                  │
25 │                                                  │
   │                                                  │
20 │    S-04          ┌─────┐                         │
   │    (5,20)        │RESTR│                         │
15 │    S-03  S-06    │ICTED│         ★ Robot Start    │  WS-05
   │    (5,15)(10,10) │ZONE │         (25,15)          │  (45,15)
   │                  └─────┘                         │
10 │    S-02  S-06                          WS-02     │
   │    (5,10)(10,10)              ┌──┐     (40,12)   │
 8 │                               │EL│              │
 5 │    S-01  S-05                 │EC│  WS-01 WS-04  │
   │    (5,5) (10,5)              └──┘  (40,5) (45,5) │
 0 └──────────────────────────────────────────────────┘
   0    5    10   15   20   25   30   35   40   45   50  X
```

Good luck!
