"""臂部动作执行器"""
import logging
import numpy as np
from fastbot.isaac.bridge import get_bridge

logger = logging.getLogger("fastbot.arms")


async def arms_executor_func(action_vector):
    """将臂部关节角度发送到 Isaac Sim / Mock"""
    if isinstance(action_vector, dict):
        action_vector = action_vector.get("arms", np.zeros(14))
    if isinstance(action_vector, np.ndarray):
        action_vector = action_vector.flatten().tolist()

    bridge = get_bridge()
    await bridge.send_joint_commands("arms", action_vector)
    logger.debug("[arms] sent %d joint targets", len(action_vector) if action_vector else 0)
