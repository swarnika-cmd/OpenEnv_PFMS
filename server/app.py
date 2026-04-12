import uvicorn
from fastapi import FastAPI
from env import PFMSEnv, Action

app = FastAPI()
_env = PFMSEnv()

@app.get("/")
async def root():
    return {"status": "PFMS Environment is running! Use POST /reset and POST /step to interact."}

@app.post("/reset")
async def reset():
    result = await _env.reset()
    return {"observation": result.observation.model_dump(), "info": {}}

@app.post("/step")
async def step(action: Action):
    result = await _env.step(action)
    return {
        "observation": result.observation.model_dump(),
        "reward": result.reward,
        "done": result.done,
        "info": {}
    }

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
