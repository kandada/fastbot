"""Shell 工具 - LLM 可调用的系统命令执行"""
import subprocess
import logging

logger = logging.getLogger("fastbot.tools")


async def run_shell_func(command: str = "", **kwargs) -> str:
    """Execute a shell command and return output"""
    if not command:
        return "No command provided"

    logger.info("[shell] executing: %s", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip() or result.stderr.strip()
        logger.info("[shell] result: %s", output[:200])
        return output
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Error: {e}"
