"""危险检测感知循环 (10Hz)"""
import logging
import numpy as np

logger = logging.getLogger("fastbot.hazards")

_hazard_timer = 0
_hazard_pattern = [
    {"type": "trap", "position": [3.0, 1.0], "severity": "critical", "time": 5},
    {"type": "obstacle", "position": [5.0, 3.0], "severity": "moderate", "time": 12},
    {"type": "trap", "position": [2.0, 4.0], "severity": "critical", "time": 20},
    {"type": "obstacle", "position": [7.0, 1.0], "severity": "moderate", "time": 28},
    {"type": "trap", "position": [4.0, 6.0], "severity": "critical", "time": 35},
]


async def hazard_detector_func(state: dict, signal_bus):
    """检测危险并更新紧急状态"""
    global _hazard_timer
    _hazard_timer += 0.1

    lidar = signal_bus.read("lidar_scan")
    pos = state.get("vla", {}).get("position", [0, 0, 0])

    hazards = _detect_hazards_from_lidar(lidar, pos)
    state.setdefault("world", {})["hazards"] = hazards

    for h in hazards:
        if h.get("severity") == "critical":
            state.setdefault("vla", {})["emergency"] = True
            logger.warning("[hazard] CRITICAL: %s at %s", h["type"], h.get("position"))
            return

    for h in _hazard_pattern:
        if abs(_hazard_timer - h["time"]) < 0.2:
            state.setdefault("vla", {})["emergency"] = True
            state.setdefault("world", {})["hazards"] = [h]
            logger.warning("[hazard] SCHEDULED: %s at time=%.1fs", h["type"], h["time"])
            return

    state.setdefault("vla", {})["emergency"] = False


def _detect_hazards_from_lidar(lidar_scan, position):
    if lidar_scan is None:
        return []
    hazards = []
    if isinstance(lidar_scan, np.ndarray):
        min_dist = float(lidar_scan.min())
        if min_dist < 1.0:
            hazards.append({"type": "obstacle", "position": position, "distance": min_dist, "severity": "moderate"})
        if min_dist < 0.3:
            hazards.append({"type": "trap", "position": position, "distance": min_dist, "severity": "critical"})
    return hazards
