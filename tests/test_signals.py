import pytest
import numpy as np
from fastbot.signals.camera import camera_signal_func
from fastbot.signals.joints import joint_signal_func
from fastbot.signals.lidar import lidar_signal_func

@pytest.mark.asyncio
async def test_camera_signal():
    result = await camera_signal_func()
    assert isinstance(result, np.ndarray)
    assert result.shape == (256, 256, 3)
    assert result.dtype == np.uint8

@pytest.mark.asyncio
async def test_joint_signal():
    result = await joint_signal_func()
    assert isinstance(result, np.ndarray)

@pytest.mark.asyncio
async def test_lidar_signal():
    result = await lidar_signal_func()
    assert isinstance(result, np.ndarray)
    assert len(result) == 360
