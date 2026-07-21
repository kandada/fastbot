"""平衡 VLA (50Hz): 关节状态 → 平衡修正"""
import logging
import time
import numpy as np
from collections import deque

from fastbot.core.metrics import _tick_times_balance

logger = logging.getLogger("fastbot.balance")

_joint_history = deque(maxlen=10)
_imu_buffer = deque(maxlen=5)

KP = 50.0
KD = 5.0
KI = 2.0
_error_integral = np.zeros(12)


async def balance_vla_func(state: dict, signal_bus) -> dict:
    """VLA Fast Loop: balance control at 50Hz using PID controller"""
    _tick_times_balance.append(time.monotonic())

    joints = signal_bus.read("joint_states")
    emergency = state.get("vla", {}).get("emergency", False)

    if joints is None:
        return {"legs": np.zeros(12, dtype=np.float32)}

    if emergency:
        correction = _emergency_dodge(joints)
    else:
        correction = _balance_pid(joints)

    return {"legs": correction}


def _balance_pid(joints):
    """PID balance controller"""
    global _error_integral

    if isinstance(joints, np.ndarray):
        j = joints.flatten()
    else:
        j = np.array(joints).flatten()

    leg_start = min(len(j), 12)
    leg_angles = j[:leg_start]

    target = np.zeros(leg_start)
    error = target - leg_angles

    _error_integral = np.clip(_error_integral + error * 0.02, -10, 10)

    derivative = np.zeros(leg_start)
    if _joint_history:
        prev = _joint_history[-1]
        pl = prev[:leg_start]
        derivative = (leg_angles - pl) / 0.02

    correction = KP * error + KD * derivative + KI * _error_integral

    _joint_history.append(leg_angles)

    result = np.zeros(12, dtype=np.float32)
    result[:leg_start] = correction
    return result


def _emergency_dodge(joints):
    """Emergency dodge maneuver - rapid lateral step"""
    if isinstance(joints, np.ndarray):
        j = joints.flatten()
    else:
        j = np.array(joints).flatten()

    dodge = np.array([0.0, 0.5, -1.0, -1.5, 0.0, -0.5,
                       0.0, -0.5, 1.0, 1.5, 0.0, 0.5], dtype=np.float32)

    logger.info("[balance_vla] EMERGENCY DODGE!")
    return dodge
