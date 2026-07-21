import pytest
import numpy as np
from fastbot.vlas.navigation import navigation_vla_func, _mock_nav_action
from fastbot.vlas.balance import balance_vla_func

class MockSignalBus:
    def read(self, name):
        if name == "camera_rgb":
            return np.zeros((256, 256, 3), dtype=np.uint8)
        if name == "lidar_scan":
            return np.ones(360, dtype=np.float32) * 10.0
        if name == "joint_states":
            return np.zeros(26, dtype=np.float32)
        return None

@pytest.mark.asyncio
async def test_navigation_vla_output():
    state = {"llm": {"goal": "go forward", "speed": 0.5, "behavior_mode": "explore"}}
    signal_bus = MockSignalBus()
    result = await navigation_vla_func(state, signal_bus)
    assert "legs" in result
    assert "arms" in result

@pytest.mark.asyncio
async def test_navigation_vla_emergency():
    state = {
        "llm": {"goal": "go forward", "speed": 0.5, "behavior_mode": "evade"},
        "vla": {"emergency": True},
    }
    signal_bus = MockSignalBus()
    result = await navigation_vla_func(state, signal_bus)
    assert "legs" in result

@pytest.mark.asyncio
async def test_balance_vla_output():
    state = {"vla": {}}
    signal_bus = MockSignalBus()
    result = await balance_vla_func(state, signal_bus)
    assert "legs" in result

@pytest.mark.asyncio
async def test_balance_vla_emergency():
    state = {"vla": {"emergency": True}}
    signal_bus = MockSignalBus()
    result = await balance_vla_func(state, signal_bus)
    assert "legs" in result

def test_mock_nav_action_shapes():
    state = {"llm": {"goal": "test", "speed": 0.5, "behavior_mode": "explore"}}
    action = _mock_nav_action(None, None, state["llm"]["goal"], state["llm"]["speed"],
                               state["llm"]["behavior_mode"], False)
    assert len(action["legs"]) == 12
    assert len(action["arms"]) == 14
