"""激光雷达信号 (10Hz)"""
import logging
import numpy as np
from fastbot.isaac.bridge import get_bridge

logger = logging.getLogger("fastbot.lidar")


async def lidar_signal_func():
    bridge = get_bridge()
    scan = await bridge.get_lidar_scan()
    if scan is None:
        return np.ones(360, dtype=np.float32) * 10.0
    return scan
