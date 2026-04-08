import asyncio
import os
import json
from env import PFMSEnv, Action

async def main():
    print("=========================================")
    print("  Welcome to the PFMS Mock Environment!  ")
    print("=========================================")
    print("Available Tasks: happy_path, traffic_spike, lying_ui")
    task = input("Select a task [happy_path]: ").strip() or "happy_path"
    os.environ["PFMS_TASK"] = task
    
    env = PFMSEnv()
    result = await env.reset()
    
    print("\n--- NEW EPISODE STARTED ---")
    print(f"Initial Observation:\n{json.dumps(result.observation.model_dump(), indent=2)}\n")
    
    step = 0
    total_reward = 0.0
    
    while True:
        step += 1
        print(f"\n--- STEP {step} ---")
        print("Enter your action as a JSON string.")
        print("Example: {\"command\": \"login\"}")
        print("Example: {\"command\": \"navigate\", \"target_page\": \"fund_transfer\"}")
        action_input = input("\nAction > ")
        
        try:
            action_data = json.loads(action_input)
            action = Action(**action_data)
        except Exception as e:
            print(f"\n[!] Invalid JSON or Action format: {e}")
            continue
            
        result = await env.step(action)
        # OpenEnv usually returns numerical scalar or None
        reward = result.reward if result.reward is not None else 0.0
        total_reward += reward
        
        print("\n[ OBSERVED STATE ]")
        print(f"Reward this step: {reward}")
        print(f"Total Reward: {total_reward:.2f}")
        print(f"Done: {result.done}")
        print(f"Observation:\n{json.dumps(result.observation.model_dump(), indent=2)}")
        
        if result.done:
            print(f"\n=========================================")
            print(f"--- EPISODE FINISHED ---")
            print(f"Final Total Reward: {total_reward:.2f}")
            print(f"=========================================\n")
            break

if __name__ == "__main__":
    asyncio.run(main())
