import asyncio
import json
import os
import textwrap
from typing import List, Optional

from openai import OpenAI

from env import Action as PFMSEnvAction, PFMSEnv

HF_TOKEN = os.getenv("HF_TOKEN")
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME = os.getenv("PFMS_TASK", "happy_path")
BENCHMARK = os.getenv("MY_ENV_V4_BENCHMARK", "pfms_mock")
MAX_STEPS = 15
TEMPERATURE = 0.7
MAX_TOKENS = 300
SUCCESS_SCORE_THRESHOLD = 0.1  # normalized score in [0, 1]

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an AI assistant attempting to navigate the Public Financial Management System (PFMS) to complete a task.
    You must output your action as a STRICT JSON object matching the following schema. Do NOT wrap the JSON in markdown blocks like ```json.
    
    ACTION SCHEMA:
    {
       "command": "login" | "navigate" | "submit_transfer" | "noop",
       "target_page": "dashboard" | "fund_transfer" | "ledger" (Optional, only for navigate),
       "amount": integer (Optional, only for submit_transfer),
       "vendor": string (Optional, only for submit_transfer)
    }
    
    WARNING: The server is unstable. If you receive a 504 Gateway Timeout, the server is busy.
    If you immediately try to 'submit_transfer' again while it is busy, you will crash the server and fail.
    You must use the 'noop' command to wait if the server is busy.
    
    WARNING: Do not trust the UI banner implicitly. Always verify important fund transfers in the 'ledger' page.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


def build_user_prompt(step: int, observation: dict, last_reward: float, history: List[str]) -> str:
    history_block = "\n".join(history[-4:]) if history else "None"
    obs_json = json.dumps(observation, indent=2)
    return textwrap.dedent(
        f"""
        Task Context: {os.getenv("PFMS_TASK_PROMPT", "Complete the required disbursement.")}
        
        Step: {step}
        Last Observation: {obs_json}
        Last Reward: {last_reward:.2f}
        Previous steps history:
        {history_block}
        
        Send your next JSON action.
        """
    ).strip()

def get_model_message(client: OpenAI, step: int, observation: dict, last_reward: float, history: List[str]) -> str:
    user_prompt = build_user_prompt(step, observation, last_reward, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()
        if text.startswith("```json"): text = text[7:]
        if text.startswith("```"): text = text[3:]
        if text.endswith("```"): text = text[:-3]
        return text.strip()
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return '{"command": "noop"}'

async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    env = await PFMSEnv.from_docker_image(LOCAL_IMAGE_NAME)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

    try:
        result = await env.reset() 
        last_obs = result.observation.model_dump()
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if hasattr(result, 'done') and result.done:
                break

            action_text = get_model_message(client, step, last_obs, last_reward, history)
            
            error = None
            try:
                action_data = json.loads(action_text)
                action = PFMSEnvAction(**action_data)
                action_str = action_text.replace("\n", "").replace("\r", "")
            except Exception as e:
                error = str(e).replace('\n', ' ')
                action = PFMSEnvAction(command="noop") # Fallback to noop on bad format
                action_str = action_text.replace("\n", "")[:50]

            result = await env.step(action)
            obs = result.observation

            reward = result.reward or 0.0
            done = result.done

            rewards.append(reward)
            steps_taken = step
            last_obs = obs.model_dump()
            last_reward = reward

            log_step(step=step, action=action_str, reward=reward, done=done, error=error)

            history.append(f"Step {step}: {action_str} -> reward {reward:+.2f}")

            if done:
                break

        score = sum(rewards)
        if score > 0:
            score = max(0.0, min(1.0, score))
        else:
            score = 0.0

        success = score >= SUCCESS_SCORE_THRESHOLD

    finally:
        try:
            await env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


if __name__ == "__main__":
    asyncio.run(main())
