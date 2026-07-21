import pytest
from fastbot.agents.brain import brain_agent, _mock_brain

class MockEvent:
    def __init__(self, type="user_input", payload=None):
        self.type = type
        self.payload = payload or {}

def test_brain_agent_mock_go_to_center():
    state = {}
    event = MockEvent(payload={"text": "go to center"})
    result = _mock_brain(state, event)
    assert "llm" in state
    assert state["llm"]["behavior_mode"] == "explore"
    assert result["messages"][0]["role"] == "assistant"

def test_brain_agent_mock_collect():
    state = {}
    event = MockEvent(payload={"text": "collect energy"})
    result = _mock_brain(state, event)
    assert state["llm"]["behavior_mode"] == "collect"

def test_brain_agent_mock_hazard():
    state = {}
    event = MockEvent(type="hazard_detected", payload={"text": "trap detected"})
    result = _mock_brain(state, event)
    assert state["llm"]["behavior_mode"] == "evade"
    assert state["llm"]["urgency"] == 3

def test_brain_agent_returns_messages():
    state = {}
    event = MockEvent(payload={"text": "hello"})
    result = _mock_brain(state, event)
    assert "messages" in result
    assert len(result["messages"]) > 0
