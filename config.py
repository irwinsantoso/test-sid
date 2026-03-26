"""
AMR Simulator Configuration
Defines warehouse layout, storage locations, and simulation parameters.
"""

# Warehouse grid dimensions (meters)
WAREHOUSE_WIDTH = 50
WAREHOUSE_HEIGHT = 30

# Predefined storage locations (the candidate does NOT get these directly —
# they must query GET /api/warehouse/info to discover them)
STORAGE_LOCATIONS = [
    {"id": "S-01", "x": 5,  "y": 5,  "capacity": 10, "current_load": 3},
    {"id": "S-02", "x": 5,  "y": 10, "capacity": 10, "current_load": 7},
    {"id": "S-03", "x": 5,  "y": 15, "capacity": 8,  "current_load": 8},  # full
    {"id": "S-04", "x": 5,  "y": 20, "capacity": 12, "current_load": 0},
    {"id": "S-05", "x": 10, "y": 5,  "capacity": 10, "current_load": 5},
    {"id": "S-06", "x": 10, "y": 10, "capacity": 10, "current_load": 9},
]

# Predefined workstation docking points (candidates should query these)
WORKSTATION_LOCATIONS = [
    {"id": "WS-01", "x": 40, "y": 5,  "name": "Assembly Line A"},
    {"id": "WS-02", "x": 40, "y": 12, "name": "Assembly Line B"},
    {"id": "WS-03", "x": 40, "y": 19, "name": "Quality Control"},
    {"id": "WS-04", "x": 45, "y": 5,  "name": "Packaging Station"},
    {"id": "WS-05", "x": 45, "y": 15, "name": "Receiving Dock"},
]

# Restricted zones (obstacles — robot cannot pass through or stop here)
RESTRICTED_ZONES = [
    {"x_min": 20, "y_min": 10, "x_max": 25, "y_max": 20, "label": "Pillar Block A"},
    {"x_min": 30, "y_min": 0,  "x_max": 32, "y_max": 8,  "label": "Electrical Panel"},
]

# Robot defaults
ROBOT_START_X = 25
ROBOT_START_Y = 15
ROBOT_SPEED = 2.0  # meters per "tick"

# Simulation: probability of random transient failure (e.g., obstacle detected)
RANDOM_FAILURE_RATE = 0.05  # 5%

# Coordinate tolerance for docking (meters)
DOCKING_TOLERANCE = 1.0

# Status callback delays (seconds) — simulates real-time robot progress
# Each transport goes through these phases with a delay between callbacks
CALLBACK_DELAYS = {
    "moving_to_source":   1.0,
    "arrived_at_source":  0.5,
    "lifting":            1.5,
    "item_lifted":        0.5,
    "moving_to_destination": 1.5,
    "arrived_at_destination": 0.5,
    "lowering":           1.0,
    "item_placed":        0.5,
    "completed":          0.3,
}
