# FastBot

> Isaac Sim Humanoid Robot Survival Challenge -- powered by FastMind Dual-Loop Architecture

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastMind 0.2.6](https://img.shields.io/badge/fastmind-0.2.6-green.svg)](https://github.com/kandada/fastmind)
[![GPLv3](https://img.shields.io/badge/license-GPLv3-blue.svg)](./LICENSE)
[![GR00T N1.5](https://img.shields.io/badge/VLA-GR00T%20N1.5%20(3B)-orange.svg)](https://huggingface.co/nvidia/GR00T-N1.5-3B)

---

## What is FastBot?

A virtual humanoid robot surviving a dynamic hazard environment (collapsing traps, falling obstacles, energy blocks). You input text commands, and the robot autonomously survives using **FastMind's dual-loop architecture**:

- **LLM Slow Loop (System 2)**: Parses commands, plans paths, assesses risk (DeepSeek API)
- **VLA Fast Loop (System 1)**: Balance control @50Hz + navigation @10Hz + emergency dodge <20ms

**Core Highlight: Swap VLA model by changing 1 line of code. Zero retraining required.**

### Powered by FastMind

FastBot is built entirely on [FastMind](https://github.com/kandada/fastmind) (v0.2.6), a framework-centric architecture for embodied intelligence. Key FastMind components used:

| Component | Role in FastBot |
|:--|:--|
| `Graph` | ReAct loop: brain(LLM) + tools, with conditional routing |
| `VLAConfig` | navigation_vla @10Hz and balance_vla @50Hz, time-driven scheduling |
| `Signal` / `SignalBus` | Camera(30Hz), lidar(10Hz), joint states(50Hz) — decoupled sensor push |
| `State` dict | Shared blackboard: LLM writes llm/, VLA reads & writes vla/, perception writes world/ |
| `Event` | User text + hazard_detected events — asynchronous slow-loop triggers |
| `Engine` | Session management, event queue, VLA scheduler orchestration |

The entire dual-loop system is assembled in a single `app.py` (~120 lines), demonstrating FastMind's zero-boilerplate design.

---

## Demo Video

![FastBot Demo](./docs/demo_preview.gif)

[Download full MP4](./docs/demo.mp4)

The video demonstrates the complete dual-loop collaboration across 10 phases. Below is a frame-by-frame breakdown of how the LLM and VLA interact through the State blackboard:

### Video Walkthrough

| Time | Phase | What's Happening | LLM (Slow Loop) | VLA (Fast Loop) |
|:--|:--|:--|:--|:--|
| 0:00 | **Architecture Init** | FastMind engine starts: Graph (brain+tools ReAct loop) + 2 VLAs + 3 Signal sources registered. 3 robot sessions initialized (Exp 4). | Brain agent waiting for user input events | Balance VLA holding stance @50Hz; Navigation VLA idle |
| 0:06 | **User Text -> Walk** | User types "Go to platform center, avoid red zones". Text pushed as Event to LLM brain agent. | LLM parses intent via DeepSeek: writes `{goal: "go to center", mode: EXPLORE, speed: 0.8}` to State["llm"] | VLA reads new goal from State -> generates forward walking action (leg joints scaled by speed=0.8). VLA frequency verified: 49.7Hz/9.9Hz stable (Exp 1+2). |
| 0:18 | **Trap Detection -> Dodge -> Re-plan** | Lidar detects trap at (8,5) within 1.2m. Perception writes `State["vla"]["emergency"]=TRUE` and pushes hazard_detected event. | LLM wakes up on hazard event -> emergency re-planning: writes `{mode: EVADE, speed: 1.0, urgency: 3}` to override previous goal. | **VLA balance reads emergency=TRUE -> DODGE within <20ms** (before LLM responds!). Then VLA navigation reads new State values -> switches to evasion gait. HITL cycle complete <15ms (Exp 5). |
| 0:28 | **Collect Energy** | User types "Collect energy blocks". LLM re-plans mode change: EVADE -> COLLECT. | LLM writes `{mode: COLLECT, speed: 0.7}` to State. | VLA reads mode=COLLECT -> arms extend forward, legs slow to stable approach gait. Energy block at (35,5) reached and collected (Exp 1). |
| 0:38 | **Obstacle Drop** | Obstacle drops from above at (25,7). Perception detects new threat within 0.5m. | LLM re-plans for falling obstacle: mode=EVADE, speed=1.0. | VLA dodge backward within <20ms. After LLM re-plan, switches to lateral evasion to safe zone. |
| 0:46 | **Dual-Loop Parallel** | LLM reasoning and VLA control run simultaneously -- the core dual-loop decoupling. 3 sessions active concurrently. | LLM analyzing scene context ("4 hazards known, 3 energy remaining"). | VLA balance: 50Hz PID maintaining posture continuously. VLA nav: 10Hz path planning in parallel. 243.9 evt/s throughput (Exp 4). |
| 0:52 | **Model Hot-Swap (Exp 6)** | **THE KEY DEMO**: VLA model swapped from GR00T N1.5 (3B) to Mock VLA. | LLM continues planning -- completely unaffected. | Robot continues walking without interruption -- **same Graph, same State, same Signals, different model**. Code change: 1 line. Retraining: zero. |
| 1:04 | **Code Comparison** | Framework-centric vs model-centric comparison (Exp 3). fastbot: ~500 lines. Bare Isaac Sim script: ~2000+ lines. Same Graph works for all VLA/LLM combinations. | | |
| 1:12 | **Full Autonomous** | Robot runs full autonomous survival mode: all systems active simultaneously. New trap detected during autonomous run -> VLA dodges -> LLM re-plans -> recovery, all without human intervention. | | |
| 1:20 | **Summary** | All 6 paper experiments verified: Exp 1 latency 0.11ms, Exp 2 VLA 49.7Hz, Exp 3 500 vs 2000 lines, Exp 4 3 sessions, Exp 5 HITL <15ms, Exp 6 1-line model swap. | | |

### Key Dual-Loop Interaction Patterns

```
PATTERN 1: User Text -> Action
  USER says "go to center" 
    -> [LLM] parses -> writes State: {goal, mode=EXPLORE, speed=0.8}
    -> [VLA] reads State -> generates walking action -> robot moves

PATTERN 2: Hazard -> Emergency -> Recovery
  HAZARD detected
    -> [VLA] reads emergency=TRUE -> DODGE (<20ms, no LLM needed)
    -> [LLM] receives hazard event -> re-plans -> writes State: {mode=EVADE}
    -> [VLA] reads new mode -> switches to evasion behavior

PATTERN 3: Model Swap (framework-centric)
  OLD MODEL -> [1 line code change] -> NEW MODEL
  Graph: unchanged | Signals: unchanged | State: unchanged
  Robot continues moving with zero interruption
```

---

## Quick Start

```bash
# 1. Install
pip install fastmind
cd fastbot && pip install -e ".[dev]"

# 2. Configure API Key
cp .env.example .env
# Edit .env: add LLM_API_KEY (DeepSeek)

# 3. Run (mock mode, no Isaac Sim needed)
python main.py start --mock

# 4. Input commands
> go to center, avoid red zones
> collect energy blocks
```

---

## Architecture

```
                     Isaac Sim (Simulation)
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
       camera_rgb    joint_states    lidar_scan
         (30Hz)          (50Hz)         (10Hz)
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                    SignalBus
                           │
       ┌───────────────────┼───────────────────┐
       │         FastMind Session              │
       │                                       │
       │  Slow Loop (Graph, event-driven)       │
       │  user text -> brain(LLM) <-> tools    │
       │                | writes               │
       │           State["llm"]  <-- blackboard│
       │                | reads                │
       │  Fast Loop (VLA, time-driven)          │
       │  navigation_vla(10Hz)                 │
       │  balance_vla(50Hz)                    │
       │                |                       │
       │       Action Channel -> Isaac Sim      │
       └───────────────────────────────────────┘
```

## Paper Experiments

| Experiment | Metric | Verified |
|:--|:--|:--|
| Exp 1: End-to-end latency | push_event p99 < 0.3ms | 0.11ms |
| Exp 2: VLA frequency stability | 0.0%-2.8% error | 49.7/9.9Hz |
| Exp 3: Orchestration comparison | Code lines | ~500 vs ~2000 (75% less) |
| Exp 4: Concurrency scaling | 3 sessions, throughput | 243.9 evt/s |
| Exp 5: HITL interrupt | Checkpoint/resume | <15ms |
| **Exp 6: Model swap** | **1 line vs retrain** | **Zero retraining** |

## File Structure

```
fastbot/
├── __init__.py
├── main.py               # CLI entry (start/test/benchmark)
├── docs/
│   ├── demo.mp4          # Full demo video
│   └── demo_preview.gif  # Video preview for README
├── core/
│   ├── app.py            # Graph assembly: brain+tools+VLAs+Signals
│   ├── prompts.py        # LLM system prompt
│   └── metrics.py        # VLA frequency tracking
├── agents/
│   └── brain.py          # LLM Slow Loop (DeepSeek API + mock fallback)
├── vlas/
│   ├── navigation.py     # GR00T N1.5 / Mock VLA @10Hz
│   └── balance.py        # PID balance controller @50Hz
├── signals/
│   ├── camera.py         # Camera signal @30Hz
│   ├── joints.py         # Joint state signal @50Hz
│   └── lidar.py          # Lidar scan signal @10Hz
├── perceptions/
│   └── hazards.py        # Hazard detection loop
├── actions/
│   ├── legs.py           # Leg action executor
│   └── arms.py           # Arm action executor
├── tools/
│   └── shell.py          # Shell command tool (LLM-callable)
├── isaac/
│   └── bridge.py         # Isaac Sim bridge (Mock + Real)
└── tests/
    ├── test_graph.py     # Graph structure + routing (5 cases)
    ├── test_agents.py    # LLM brain agent (4 cases)
    ├── test_vlas.py      # VLA navigation + balance (5 cases)
    └── test_signals.py   # Sensor signals (3 cases)
```

## Model Swap (Framework-Centric Advantage)

```python
# fastbot/vlas/navigation.py

# Before: GR00T N1.5
MODEL = "/path/to/GR00T-N1.5-3B"

# After: OpenVLA -- only change these 2 lines
# MODEL = "openvla-7b"
# vla = OpenVLA.from_pretrained(MODEL)

# Graph: unchanged | Signals: unchanged | State: unchanged
# Actions: unchanged | Retraining: ZERO
```

## Requirements

| Component | Minimum | Recommended |
|:--|:--|:--|
| GPU | RTX 3090 24GB | RTX 4090 24GB |
| System | Ubuntu 22.04 | Ubuntu 24.04 |
| Isaac Sim | 4.x (optional) | 4.x |

## License

GNU General Public License v3.0. See [LICENSE](./LICENSE).
