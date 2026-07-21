"""相机信号 (30Hz)"""
import logging
import numpy as np
from fastbot.isaac.bridge import get_bridge

logger = logging.getLogger("fastbot.camera")


async def camera_signal_func():
    bridge = get_bridge()
    frame = await bridge.get_camera_frame()
    if frame is None:
        return np.zeros((256, 256, 3), dtype=np.uint8)
    return frame
