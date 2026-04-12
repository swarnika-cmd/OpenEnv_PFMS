---
title: PFMS Env
emoji: 🏛️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# 🏛️ OpenEnv: Mock PFMS Portal

<div align="center">
  <img src="https://img.shields.io/badge/OpenEnv-Compatible-blue?style=for-the-badge&logo=huggingface" alt="OpenEnv">
  <img src="https://img.shields.io/badge/Environment-Python-green?style=for-the-badge&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Status-HuggingFace_Ready-orange?style=for-the-badge&logo=appveyor" alt="HuggingFace">
</div>

<br/>

> **The Ultimate RL Obstacle Course:** A highly deceptive, purely API-driven Reinforcement Learning environment simulating the notoriously flaky legacy infrastructure of a government financial portal. 

---

## 🚀 The Mission

Current LLM-based agents are optimized for pristine APIs and predictable DOMs. But what happens when the server fails? What happens when the UI outright *lies* to the agent?

This environment strips away the HTML to test an AI agent's raw logical reasoning, patience, and verification skills when faced with **Temporal Backoffs** and **State Inconsistencies**.

## 🧠 The Chaos Vectors (Tasks)

The environment serves three escalating difficulty tiers, testing specific problem-solving paradigms:

| Task | Difficulty | The Challenge (What the AI Must Learn) |
|---|:---:|---|
| **`happy_path`** | 🟢 Easy | Basic JSON state navigation and structured action formatting. |
| **`traffic_spike`** | 🟡 Medium | **Exponential Backoff**. The server dynamically triggers `504 Gateway Timeouts`. The agent must use `NoOp()` to let time pass before resubmitting. Spamming submission crashes the server for a catastrophic `-10.0` points penalty. |
| **`lying_ui`** | 🔴 Hard | **Independent Verification**. The portal will fake a successful transfer and return HTTP `200` visually, but silently drop the data. The AI must independently confirm the transactional intent on the `ledger` page and retry if hijacked. |

## 🕹️ Human Testing Arena

Don't trust the AI to have all the fun. You can play against the environment yourself using the built-in CLI tester!

```bash
# Install the core OpenEnv requirements
uv pip install -r requirements.txt

# Start the game loop
uv run python play.py
```

> [!TIP]
> **The Traffic Spike Challenge:** Try passing the `traffic_spike` task manually. Look very closely at the `Observation` responses before you decide to click submit!

## ⚙️ Architecture & Deployment

This project was built to bypass the fragility of headless web browsers (Playwright) in isolated Docker containers, creating an impenetrable and lightning-fast pure-Python state machine.

- **`env.py`** - Core state machine, scoring Graders, and time-cost terminators (`-0.01` per step).
- **`server.py`** - FastAPI wrapper to keep Hugging Face Spaces alive and fulfill REST API interactions (`/step`, `/reset`).
- **`inference.py`** - Zero-shot inference script optimized for Frontier Models, explicitly forcing pure JSON execution and conforming to the rigorous OpenEnv `[START]/[STEP]/[END]` STDOUT specification.

---

<div align="center">
  <i>"In legacy systems, patience isn't a virtue. It's a mathematically optimal path."</i>
</div>
