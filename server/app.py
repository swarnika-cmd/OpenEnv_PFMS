"""FastAPI application for the PFMS environment."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uvicorn
from fastapi import FastAPI
from models import PFMSAction
from server.environment import PFMSEnvironment

app = FastAPI(title="PFMS Environment")
env = PFMSEnvironment()


@app.get("/")
async def root():
    return {"status": "PFMS Environment is running!"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/reset")
async def reset():
    obs = env.reset()
    return {"observation": obs.model_dump(), "info": {}}


@app.post("/step")
async def step(action: PFMSAction):
    result = env.step(action)
    return result


@app.get("/state")
async def state():
    return env.state.model_dump()


def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
