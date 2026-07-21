"""腿部动作执行器"""
import logging
import numpy as np
from fastbot.isaac.bridge import get_bridge

logger = logging.getLogger("fastbot.legs")


async def legs_executor_func(action_vector):
    """将腿部关节角度发送到 Isaac Sim / Mock"""
    if isinstance(action_vector, dict):
        action_vector = action_vector.get("legs", np.zeros(12))
    if isinstance(action_vector, np.ndarray):
        action_vector = action_vector.flatten().tolist()

    bridge = get_bridge()
    await bridge.send_joint_commands("legs", action_vector)
    logger.debug("[legs] sent %d joint targets", len(action_vector) if action_vector else 0)
