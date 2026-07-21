import pytest
from fastbot.core.app import build_app


def test_graph_structure():
    app = build_app()
    graph = app.get_graph("main")
    assert graph.entry_point == "brain"
    assert graph.has_node("brain") is True
    assert graph.has_node("tools") is True


def test_graph_routing_has_tool_calls():
    app = build_app()
    graph = app.get_graph("main")
    result = graph.get_next_node("brain", {"tool_calls": ["call_1"]}, None)
    assert result == "tools"


def test_graph_routing_no_tool_calls():
    app = build_app()
    graph = app.get_graph("main")
    result = graph.get_next_node("brain", {}, None)
    assert result is None


def test_app_components():
    app = build_app()
    assert app.get_vla("navigation_vla") is not None
    assert app.get_vla("balance_vla") is not None
    assert app.get_signal("camera_rgb") is not None
    assert app.get_signal("joint_states") is not None
    assert app.get_signal("lidar_scan") is not None
    assert app.get_agent("brain") is not None
    assert app.get_tool("run_shell") is not None
    assert app.get_vla_action("legs") is not None
    assert app.get_vla_action("arms") is not None


def test_graph_detect_cycles():
    app = build_app()
    graph = app.get_graph("main")
    assert graph.detect_cycles() is not None  # ReAct loop has cycle brain->tools->brain
