"""
In-memory models for the AMR simulator.
"""
import copy
import config


class Robot:
    def __init__(self):
        self.x = config.ROBOT_START_X
        self.y = config.ROBOT_START_Y
        self.state = "idle"  # idle | moving | lifting | carrying | lowering | error
        self.carrying_item = None
        self.task_log = []
        self.current_task_id = None

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "state": self.state,
            "carrying_item": self.carrying_item,
        }

    def reset(self):
        self.__init__()


class Warehouse:
    def __init__(self):
        self.storage_locations = copy.deepcopy(config.STORAGE_LOCATIONS)
        self.workstation_locations = copy.deepcopy(config.WORKSTATION_LOCATIONS)
        self.restricted_zones = copy.deepcopy(config.RESTRICTED_ZONES)
        self.item_counter = 0

    def get_storage_by_id(self, storage_id):
        for s in self.storage_locations:
            if s["id"] == storage_id:
                return s
        return None

    def get_workstation_by_id(self, ws_id):
        for w in self.workstation_locations:
            if w["id"] == ws_id:
                return w
        return None

    def find_location_at(self, x, y, tolerance=config.DOCKING_TOLERANCE):
        """Find any known location (storage or workstation) near (x,y)."""
        for s in self.storage_locations:
            if abs(s["x"] - x) <= tolerance and abs(s["y"] - y) <= tolerance:
                return ("storage", s)
        for w in self.workstation_locations:
            if abs(w["x"] - x) <= tolerance and abs(w["y"] - y) <= tolerance:
                return ("workstation", w)
        return (None, None)

    def is_in_restricted_zone(self, x, y):
        for z in self.restricted_zones:
            if z["x_min"] <= x <= z["x_max"] and z["y_min"] <= y <= z["y_max"]:
                return True, z["label"]
        return False, None

    def is_in_bounds(self, x, y):
        return 0 <= x <= config.WAREHOUSE_WIDTH and 0 <= y <= config.WAREHOUSE_HEIGHT

    def reset(self):
        self.__init__()


# Singletons
robot = Robot()
warehouse = Warehouse()
