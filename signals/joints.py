"""关节状态信号 (50Hz)"""
import logging
import numpy as np
from fastbot.isaac.bridge import get_bridge

logger = logging.getLogger("fastbot.joints")


async def joint_signal_func():
    bridge = get_bridge()
    states = await bridge.get_joint_states()
    if states is None:
        return np.zeros(26, dtype=np.float32)
    return states
