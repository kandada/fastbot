"""FastBot 核心引擎: 组装 FastMind 应用"""
import json
import logging
import time
import yaml
import asyncio
from pathlib import Path

from fastmind import FastMind, Graph, ToolNode, Event, Agent, Tool, VLAConfig, Signal, VLAActionNode
from fastmind.core.engine import Engine
from fastmind.core.node import AgentNode

from fastbot.core.prompts import SYSTEM_PROMPT, TOOL_SCHEMAS
from fastbot.core.metrics import _tick_times_balance, _tick_times_nav
from fastbot.agents.brain import brain_agent
from fastbot.vlas.navigation import navigation_vla_func
from fastbot.vlas.balance import balance_vla_func
from fastbot.signals.camera import camera_signal_func
from fastbot.signals.joints import joint_signal_func
from fastbot.signals.lidar import lidar_signal_func
from fastbot.perceptions.hazards import hazard_detector_func
from fastbot.actions.legs import legs_executor_func
from fastbot.actions.arms import arms_executor_func
from fastbot.tools.shell import run_shell_func

logger = logging.getLogger("fastbot.core")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)-15s] %(message)s",
                    datefmt="%H:%M:%S")


def _load_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "configs" / "default.yaml"
    if Path(config_path).exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def _load_dotenv():
    try:
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


def build_app(config_path: str = None, mock_isaac: bool = False) -> FastMind:
    _load_dotenv()
    config = _load_config(config_path)

    app = FastMind()

    app.register_tool("run_shell", Tool(
        name="run_shell",
        description="Execute a shell command on the robot's control system",
        func=run_shell_func,
    ))

    app.register_agent("brain", Agent(
        name="brain",
        func=brain_agent,
        tools=["run_shell"],
    ))

    tool_node = ToolNode(app.get_tools())

    graph = Graph()

    def route(state, event):
        if state.get("tool_calls"):
            return "tools"
        return None

    graph.add_node("brain", AgentNode(app.get_agent("brain")))
    graph.add_node("tools", tool_node)
    graph.add_conditional_edges("brain", route, {"tools": "tools", None: "__end__"})
    graph.add_edge("tools", "brain")
    graph.set_entry_point("brain")

    app.register_graph("main", graph)

    nav_cfg = config.get("vla", {}).get("navigation", {})
    app.register_vla("navigation_vla", VLAConfig(
        name="navigation_vla",
        func=navigation_vla_func,
        frequency=nav_cfg.get("frequency", 10.0),
        input_signals=["camera_rgb", "lidar_scan"],
    ))

    bal_cfg = config.get("vla", {}).get("balance", {})
    app.register_vla("balance_vla", VLAConfig(
        name="balance_vla",
        func=balance_vla_func,
        frequency=bal_cfg.get("frequency", 50.0),
        input_signals=["joint_states"],
    ))

    sensor_cfg = config.get("sensors", {})
    app.register_signal("camera_rgb", Signal(
        name="camera_rgb",
        interval=1.0 / sensor_cfg.get("camera", {}).get("frequency", 30),
        func=camera_signal_func,
    ))
    app.register_signal("joint_states", Signal(
        name="joint_states",
        interval=1.0 / sensor_cfg.get("joints", {}).get("frequency", 50),
        func=joint_signal_func,
    ))
    app.register_signal("lidar_scan", Signal(
        name="lidar_scan",
        interval=1.0 / sensor_cfg.get("lidar", {}).get("frequency", 10),
        func=lidar_signal_func,
    ))

    app.register_vla_action("legs", VLAActionNode(
        name="legs",
        func=legs_executor_func,
    ))
    app.register_vla_action("arms", VLAActionNode(
        name="arms",
        func=arms_executor_func,
    ))

    return app


async def input_loop(app: FastMind, bridge):
    engine = Engine(app)
    await engine.start()
    session = engine.get_or_create_session("main_user")

    print("\n" + "=" * 60)
    print("  FastBot Survival Challenge")
    print("  Type commands to control the robot:")
    print("    - 'go to center'  (走到平台中央)")
    print("    - 'collect energy' (收集能量)")
    print("    - 'avoid hazards'  (避开危险)")
    print("    - 'status'         (显示状态)")
    print("    - 'quit'           (退出)")
    print("=" * 60 + "\n")

    while True:
        try:
            cmd = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            cmd = cmd.strip()
            if not cmd:
                continue
            if cmd.lower() == "quit":
                break
            if cmd.lower() == "status":
                _print_status()
                continue

            event = Event(type="user_input", payload={"text": cmd}, session_id=session.session_id)
            await engine.push_event(session.session_id, event)
            logger.info("Pushed event: %s", cmd)

        except (EOFError, KeyboardInterrupt):
            break

    await engine.stop()


def _print_status():
    logger.info("VLA Status - balance_vla ticks: %d, nav_vla ticks: %d",
                len(_tick_times_balance), len(_tick_times_nav))
    if len(_tick_times_balance) > 1:
        intervals = [b - a for a, b in zip(_tick_times_balance[:-1], _tick_times_balance[1:])]
        avg = sum(intervals) / len(intervals) * 1000
        logger.info("balance_vla avg interval: %.1fms (target 20ms @ 50Hz)", avg)
    if len(_tick_times_nav) > 1:
        intervals = [b - a for a, b in zip(_tick_times_nav[:-1], _tick_times_nav[1:])]
        avg = sum(intervals) / len(intervals) * 1000
        logger.info("navigation_vla avg interval: %.1fms (target 100ms @ 10Hz)", avg)


async def run_benchmark(app: FastMind, bridge, mode: str):
    engine = Engine(app)
    await engine.start()
    session = engine.get_or_create_session("bench_user")

    if mode in ("latency", "all"):
        logger.info("=== Benchmark: End-to-end Latency ===")
        latencies = []
        for i in range(10):
            t0 = time.monotonic()
            event = Event(type="user_input", payload={"text": f"benchmark test {i}"}, session_id=session.session_id)
            await engine.push_event(session.session_id, event)
            t1 = time.monotonic()
            latencies.append((t1 - t0) * 1000)
        avg_lat = sum(latencies) / len(latencies)
        logger.info("push_event latency: avg=%.3fms, min=%.3fms, max=%.3fms",
                    avg_lat, min(latencies), max(latencies))

    if mode in ("frequency", "all"):
        logger.info("=== Benchmark: VLA Frequency Stability (60s) ===")
        _tick_times_balance.clear()
        _tick_times_nav.clear()
        logger.info("Collecting VLA frequency data for 60 seconds...")
        await asyncio.sleep(60)
        expected_balance = 50 * 60
        actual_balance = len(_tick_times_balance)
        err_balance = abs(actual_balance - expected_balance) / expected_balance * 100
        expected_nav = 10 * 60
        actual_nav = len(_tick_times_nav)
        err_nav = abs(actual_nav - expected_nav) / expected_nav * 100
        logger.info("balance_vla: expected=%d, actual=%d, error=%.1f%%",
                    expected_balance, actual_balance, err_balance)
        logger.info("navigation_vla: expected=%d, actual=%d, error=%.1f%%",
                    expected_nav, actual_nav, err_nav)

    if mode in ("concurrency", "all"):
        logger.info("=== Benchmark: Concurrency (3 sessions) ===")
        sessions = [engine.get_or_create_session(f"robot_{i}") for i in range(3)]
        logger.info("3 sessions created, pushing events...")
        t0 = time.monotonic()
        for s in sessions:
            await engine.push_event(s.session_id, Event(type="user_input", payload={"text": "go forward"}, session_id=s.session_id))
        await asyncio.sleep(3)
        t1 = time.monotonic()
        logger.info("3 sessions, push events in %.2fs, throughput=%.1f evt/s",
                    t1 - t0, 3 / (t1 - t0) if t1 > t0 else 0)

    if mode in ("hitl", "all"):
        logger.info("=== Benchmark: HITL Interrupt ===")
        t0 = time.monotonic()
        logger.info("Triggering hazard interrupt...")
        event = Event(type="hazard_detected", payload={"hazards": [{"type": "trap", "distance": 2.0, "severity": "critical"}]}, session_id=session.session_id)
        await engine.push_event(session.session_id, event)
        await asyncio.sleep(0.5)
        t1 = time.monotonic()
        logger.info("HITL cycle latency: %.2fms", (t1 - t0) * 1000)

    await engine.stop()
