"""主控 Agent: LLM Slow Loop (DeepSeek API)"""
import os
import json
import logging
from openai import AsyncOpenAI
from fastbot.core.prompts import SYSTEM_PROMPT, TOOL_SCHEMAS

logger = logging.getLogger("fastbot.brain")

_client = AsyncOpenAI(
    api_key=os.getenv("LLM_API_KEY", ""),
    base_url=os.getenv("LLM_API_URL", "https://api.deepseek.com/v1"),
)

_mock_mode = not os.getenv("LLM_API_KEY", "").startswith("sk-")


async def brain_agent(state: dict, event) -> dict:
    """LLM 主控: 解析指令 + 规划 + 风险评估"""
    if _mock_mode:
        return _mock_brain(state, event)

    model = os.getenv("LLM_MODEL_NAME", "deepseek-chat")

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(state.get("messages", []))

    if event and event.payload:
        text = event.payload.get("text", str(event.payload))
        messages.append({"role": "user", "content": text})

    context = json.dumps({
        "vla_status": state.get("vla", {}),
        "world": state.get("world", {}),
        "current_goal": state.get("llm", {}).get("goal", ""),
    }, default=str)
    messages.append({"role": "user", "content": f"[Scene Context]: {context}"})

    try:
        response = await _client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
        )
    except Exception as e:
        logger.error("LLM API error: %s", e)
        return _mock_brain(state, event)

    msg = response.choices[0].message
    updates = {"messages": [msg.model_dump()]}

    if msg.content:
        _parse_llm_output(msg.content, state)

    if msg.tool_calls:
        updates["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]

    return updates


def _parse_llm_output(content: str, state: dict):
    try:
        if content.strip().startswith("{"):
            parsed = json.loads(content)
            state["llm"] = {
                "goal": parsed.get("goal", ""),
                "sub_goals": parsed.get("sub_goals", []),
                "behavior_mode": parsed.get("mode", "explore"),
                "speed": parsed.get("speed", 0.5),
                "urgency": parsed.get("urgency", 1),
            }
            logger.info("[brain] goal=%s, mode=%s, speed=%.1f, urgency=%d",
                        state["llm"]["goal"], state["llm"]["behavior_mode"],
                        state["llm"]["speed"], state["llm"]["urgency"])
        else:
            state["llm"] = {
                "goal": content.strip(),
                "sub_goals": [],
                "behavior_mode": "explore",
                "speed": 0.5,
                "urgency": 1,
            }
            logger.info("[brain] goal=%s", content.strip())
    except json.JSONDecodeError:
        state["llm"] = {
            "goal": content.strip(),
            "sub_goals": [],
            "behavior_mode": "explore",
            "speed": 0.5,
            "urgency": 1,
        }


def _mock_brain(state: dict, event) -> dict:
    """Mock LLM 推理 - 用于无 API key 时的测试"""
    text = ""
    if event and event.payload:
        text = event.payload.get("text", str(event.payload)).lower()

    if event and event.type == "hazard_detected":
        goal = "evade immediately from detected hazard"
        mode = "evade"
        speed = 1.0
        urgency = 3
    elif "collect" in text or "能量" in text or "energy" in text:
        goal = "collect nearby energy blocks while avoiding hazards"
        mode = "collect"
        speed = 0.7
        urgency = 1
    elif "avoid" in text or "避开" in text or "hazard" in text:
        goal = "evade hazards and move to safe zone"
        mode = "evade"
        speed = 0.8
        urgency = 2
    elif "center" in text or "中央" in text or "go to" in text:
        goal = f"walk to target: {text}"
        mode = "explore"
        speed = 0.6
        urgency = 1
    else:
        goal = f"navigate toward target: {text}"
        mode = "explore"
        speed = 0.5
        urgency = 1

    state["llm"] = {
        "goal": goal,
        "sub_goals": [],
        "behavior_mode": mode,
        "speed": speed,
        "urgency": urgency,
    }
    logger.info("[mock brain] goal=%s, mode=%s, speed=%.1f", goal, mode, speed)
    return {"messages": [{"role": "assistant", "content": json.dumps(state["llm"])}]}
