"""Isaac Sim 通信桥接层 - 支持 Mock 模式"""
import asyncio
import logging
import numpy as np
import random

logger = logging.getLogger("fastbot.isaac")

_bridge_instance = None
_mock_mode = True


class IsaacSimBridge:
    """与 Isaac Sim 之间的数据通道"""

    def __init__(self, mock: bool = True):
        self._mock = mock
        self._connected = False
        self._tick = 0
        self._position = [0.0, 0.0, 0.0]
        self._hazard_positions = [(3.0, 1.0), (5.0, 3.0), (2.0, 4.0), (7.0, 1.0)]
        self._energy_positions = [(8.0, 2.0), (1.0, 7.0), (6.0, 4.0)]

    async def connect(self):
        if self._mock:
            logger.info("IsaacSimBridge connected (mock mode)")
        else:
            logger.info("IsaacSimBridge connecting to Isaac Sim...")
        self._connected = True

    async def disconnect(self):
        logger.info("IsaacSimBridge disconnected")
        self._connected = False

    async def get_camera_frame(self) -> np.ndarray:
        """模拟相机: 256x256 RGB"""
        self._tick += 1
        if not self._mock:
            return self._real_camera()

        frame = np.zeros((256, 256, 3), dtype=np.uint8)
        color = [100, 120, 80]

        px, py = int(self._position[0] * 20 + 128) % 256, int(self._position[1] * 20 + 128) % 256
        for dx in range(-5, 6):
            for dy in range(-5, 6):
                x, y = (px + dx) % 256, (py + dy) % 256
                frame[x, y] = [255, 255, 255]

        for hx, hy in self._hazard_positions:
            hpx, hpy = int(hx * 20 + 128) % 256, int(hy * 20 + 128) % 256
            for dx in range(-8, 9):
                for dy in range(-8, 9):
                    x, y = (hpx + dx) % 256, (hpy + dy) % 256
                    frame[x, y] = [255, 0, 0]

        for ex, ey in self._energy_positions:
            epx, epy = int(ex * 20 + 128) % 256, int(ey * 20 + 128) % 256
            for dx in range(-4, 5):
                for dy in range(-4, 5):
                    x, y = (epx + dx) % 256, (epy + dy) % 256
                    frame[x, y] = [0, 255, 0]

        noise = np.random.randint(0, 30, (256, 256, 3), dtype=np.uint8)
        frame = np.clip(frame.astype(np.int32) + noise.astype(np.int32), 0, 255).astype(np.uint8)
        return frame

    async def get_joint_states(self) -> np.ndarray:
        """模拟关节状态: 26维"""
        self._tick += 1
        if not self._mock:
            return self._real_joint_states()

        t = self._tick * 0.02
        joints = np.zeros(26, dtype=np.float32)
        joints[0] = 0.3 * np.sin(t * 2.0)
        joints[1] = 0.3 * np.cos(t * 2.0)
        joints[2] = -0.5 * np.sin(t * 2.0)
        joints[3] = -0.5 * np.cos(t * 2.0)
        joints[6] = -0.3 * np.sin(t * 2.0)
        joints[7] = -0.3 * np.cos(t * 2.0)
        joints[8] = 0.5 * np.sin(t * 2.0)
        joints[9] = 0.5 * np.cos(t * 2.0)
        joints[12:] = np.random.randn(14) * 0.05
        return joints

    async def get_lidar_scan(self) -> np.ndarray:
        """模拟激光雷达: 360度距离测量"""
        self._tick += 1
        if not self._mock:
            return self._real_lidar()

        dists = np.ones(360, dtype=np.float32) * 10.0
        for hx, hy in self._hazard_positions:
            dx, dy = hx - self._position[0], hy - self._position[1]
            dist = np.sqrt(dx*dx + dy*dy)
            if dist < 5.0:
                angle = int(np.degrees(np.arctan2(dy, dx))) % 360
                for da in range(-15, 16):
                    idx = (angle + da) % 360
                    dists[idx] = min(dists[idx], dist)

        dists += np.random.randn(360) * 0.1
        return np.clip(dists, 0.1, 10.0)

    async def send_joint_commands(self, channel: str, targets: list):
        """接收动作指令并更新 mock 位置"""
        if channel == "legs" and targets and len(targets) >= 6:
            vx = sum(targets[0:3]) * 0.01
            vy = sum(targets[3:6]) * 0.01
            self._position[0] += vx
            self._position[1] += vy
            self._position[0] = np.clip(self._position[0], 0, 10)
            self._position[1] = np.clip(self._position[1], 0, 10)
        if self._tick % 50 == 0:
            logger.debug("[bridge] robot position: (%.2f, %.2f)",
                         self._position[0], self._position[1])

    def _real_camera(self):
        logger.warning("Real Isaac Sim camera not implemented")
        return np.zeros((256, 256, 3), dtype=np.uint8)

    def _real_joint_states(self):
        logger.warning("Real Isaac Sim joint states not implemented")
        return np.zeros(26, dtype=np.float32)

    def _real_lidar(self):
        logger.warning("Real Isaac Sim lidar not implemented")
        return np.ones(360, dtype=np.float32) * 10.0


def get_bridge(mock: bool = True) -> IsaacSimBridge:
    global _bridge_instance, _mock_mode
    if _bridge_instance is None:
        _mock_mode = mock
        _bridge_instance = IsaacSimBridge(mock=mock)
    return _bridge_instance
