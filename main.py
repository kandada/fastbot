"""FastBot CLI 入口"""
import sys
import asyncio
import argparse
import logging
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from fastbot.core.app import build_app

logger = logging.getLogger("fastbot")


async def cmd_start(config_path: str = None, benchmark: str = None, mock_isaac: bool = False):
    """启动 fastbot (Isaac Sim 模式 或 Mock 模式)"""
    app = build_app(config_path, mock_isaac=mock_isaac)

    from fastbot.isaac.bridge import get_bridge
    bridge = get_bridge(mock=mock_isaac)
    await bridge.connect()

    if benchmark:
        logger.info("Benchmark mode: %s", benchmark)
        from fastbot.core.app import run_benchmark
        await run_benchmark(app, bridge, benchmark)
        return

    logger.info("FastBot started. Type text commands, Ctrl+C to stop.")
    logger.info("Available commands: go forward, collect energy, avoid hazards, etc.")

    try:
        from fastbot.core.app import input_loop
        await input_loop(app, bridge)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await bridge.disconnect()


async def cmd_test():
    """运行单元测试"""
    import pytest
    test_dir = _PROJECT_ROOT / "fastbot" / "tests"
    exit_code = pytest.main([str(test_dir), "-v", "--asyncio-mode=auto"])
    sys.exit(exit_code)


def cli_main():
    parser = argparse.ArgumentParser(prog="fastbot")
    sub = parser.add_subparsers(dest="command")

    start_parser = sub.add_parser("start", help="启动机器人控制")
    start_parser.add_argument("-c", "--config", help="配置文件路径")
    start_parser.add_argument("--benchmark", choices=["latency", "frequency", "concurrency", "hitl", "all"],
                              help="运行 benchmark 模式")
    start_parser.add_argument("--mock", action="store_true", help="使用 mock Isaac Sim (无需实际 Isaac Sim)")

    sub.add_parser("test", help="运行单元测试")

    args = parser.parse_args()
    if args.command == "start":
        asyncio.run(cmd_start(args.config, args.benchmark, args.mock))
    elif args.command == "test":
        asyncio.run(cmd_test())
    else:
        parser.print_help()


if __name__ == "__main__":
    cli_main()
