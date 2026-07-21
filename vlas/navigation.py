"""导航 VLA (10Hz): 视觉+雷达 → 行走动作"""
import logging
import time
import numpy as np
import requests
import os

from fastbot.core.metrics import _tick_times_nav

logger = logging.getLogger("fastbot.navigation")

# GR00T N1.5 HTTP service endpoint
GR00T_API = os.getenv("GR00T_API_URL", "http://localhost:8000/act")

# Fallback mode when GR00T is not available
_use_mock = True


async def navigation_vla_func(state: dict, signal_bus) -> dict:
    """VLA Fast Loop: navigation at 10Hz"""
    _tick_times_nav.append(time.monotonic())

    image = signal_bus.read("camera_rgb")
    lidar = signal_bus.read("lidar_scan")
    goal = state.get("llm", {}).get("goal", "stand still")
    speed = state.get("llm", {}).get("speed", 0.5)
    mode = state.get("llm", {}).get("behavior_mode", "explore")
    emergency = state.get("vla", {}).get("emergency", False)

    if image is None or lidar is None:
        logger.debug("navigation_vla: waiting for sensor data")
        return _default_action()

    try:
        action = await _predict_gr00t(image, lidar, goal, speed, mode, emergency)
    except Exception as e:
        logger.warning("GR00T inference failed: %s, falling back to mock", e)
        action = _mock_nav_action(image, lidar, goal, speed, mode, emergency)

    state.setdefault("vla", {})["position"] = _estimate_position(action)
    state["vla"]["stuck"] = _is_stuck(action)

    legs_action = action.get("legs", np.zeros(12, dtype=np.float32))
    arms_action = action.get("arms", np.zeros(14, dtype=np.float32))

    return {
        "legs": legs_action,
        "arms": arms_action,
    }


async def _predict_gr00t(image, lidar, goal, speed, mode, emergency):
    """Call GR00T N1.5 HTTP API for action prediction"""
    if _use_mock:
        return _mock_nav_action(image, lidar, goal, speed, mode, emergency)

    if emergency:
        goal = "evade hazard immediately"

    obs = {
        "video.ego_view": image.astype(np.uint8).tolist() if isinstance(image, np.ndarray) else image,
        "state.left_arm": np.zeros((1, 7), dtype=np.float32).tolist(),
        "state.right_arm": np.zeros((1, 7), dtype=np.float32).tolist(),
        "state.left_hand": np.zeros((1, 6), dtype=np.float32).tolist(),
        "state.right_hand": np.zeros((1, 6), dtype=np.float32).tolist(),
        "state.waist": np.array([[float(speed), 0.0, 1.0 if emergency else 0.0]], dtype=np.float32).tolist(),
        "annotation.human.action.task_description": [goal],
    }

    resp = requests.post(GR00T_API, json={"observation": obs}, timeout=5)
    if resp.status_code != 200:
        raise RuntimeError(f"GR00T API error: {resp.status_code}")

    data = resp.json()
    raw_action = data.get("action", {})

    action = {}
    for k, v in raw_action.items():
        if isinstance(v, list):
            action[k.replace("action.", "")] = np.array(v, dtype=np.float32)
        else:
            action[k.replace("action.", "")] = v

    return action


def _mock_nav_action(image, lidar, goal, speed, mode, emergency):
    """Mock navigation action generator"""
    arm_dim = 14
    arms = np.zeros(arm_dim, dtype=np.float32)

    if emergency:
        legs = np.array([0.5, 0.3, -0.8, -1.2, 0.0, -0.3, 0.8, -0.3, 0.8, 1.2, 0.0, 0.3], dtype=np.float32)
        return {"legs": legs * speed, "arms": arms}

    if mode == "evade":
        legs = np.array([0.0, 0.0, -0.5, -0.8, 0.0, -0.2, 0.0, 0.0, 0.5, 0.8, 0.0, 0.2], dtype=np.float32)
    elif mode == "collect":
        legs = np.array([0.0, 0.0, -0.3, -0.5, 0.0, -0.1, 0.0, 0.0, 0.3, 0.5, 0.0, 0.1], dtype=np.float32)
        arms = np.array([0.0, 0.5, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5, -1.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    else:
        legs = np.array([0.0, 0.1, -0.4, -0.6, 0.0, -0.1, 0.0, 0.1, 0.4, 0.6, 0.0, 0.1], dtype=np.float32)

    legs = legs * speed
    return {"legs": legs, "arms": arms}


def _default_action():
    return {"legs": np.zeros(12, dtype=np.float32), "arms": np.zeros(14, dtype=np.float32)}


def _estimate_position(action):
    legs = action.get("legs", np.zeros(12))
    x = float(np.mean(legs[0:3]))
    y = float(np.mean(legs[3:6]))
    z = float(np.mean(legs[6:9]))
    return [x, y, z]


def _is_stuck(action):
    legs = action.get("legs", np.zeros(12))
    return float(np.abs(legs).sum()) < 0.01
