from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn

from env.environment import IncidentResponseEnv
from env.models import Action

app = FastAPI(
    title="OpenEnv — Incident Response",
    description="RL environment for DevOps incident response triage",
    version="1.0.0",
)

# One env instance per task type, keyed by task
_envs: dict = {}


def _get_env(task_type: str) -> IncidentResponseEnv:
    if task_type not in _envs:
        _envs[task_type] = IncidentResponseEnv(task_type=task_type)
    return _envs[task_type]


class ResetRequest(BaseModel):
    task_type: Optional[str] = "alert-triage"
    seed: Optional[int] = None  # None = random episode each reset


class StepRequest(BaseModel):
    task_type: Optional[str] = "alert-triage"
    action: Action


@app.get("/health")
def health():
    return {"status": "healthy", "service": "incident-response-env"}


@app.post("/reset")
def reset(req: ResetRequest = None):
    if req is None:
        req = ResetRequest()
    task_type = req.task_type or "alert-triage"
    valid = ["alert-triage", "root-cause", "full-incident-response"]
    if task_type not in valid:
        raise HTTPException(status_code=400, detail=f"task_type must be one of {valid}")
    env = IncidentResponseEnv(task_type=task_type, seed=req.seed)
    _envs[task_type] = env
    obs = env.reset()
    return JSONResponse(content={"observation": obs.model_dump(), "done": False, "reward": 0.1, "info": {}})


@app.post("/step")
def step(req: StepRequest):
    task_type = req.task_type or "alert-triage"
    env = _envs.get(task_type)
    if env is None:
        raise HTTPException(status_code=400, detail="Call /reset first")
    try:
        result = env.step(req.action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return JSONResponse(content={
        "observation": result.observation.model_dump(),
        "reward": round(min(max(result.reward, 0.1), 0.9), 4),
        "done": result.done,
        "info": result.info,
    })


@app.get("/state")
def state(task_type: str = "alert-triage"):
    env = _envs.get(task_type)
    if env is None:
        raise HTTPException(status_code=400, detail="Call /reset first")
    return JSONResponse(content=env.state())


@app.get("/tasks")
def list_tasks():
    return {
        "tasks": [
            {
                "id": "alert-triage",
                "difficulty": "easy",
                "description": "Classify incident severity (P1-P4) and identify affected service",
                "max_steps": 3,
                "reward_range": [0.1, 0.9],
                "score_range": [0.1, 0.9],
                "min_score": 0.1,
                "max_score": 0.9,
            },
            {
                "id": "root-cause",
                "difficulty": "medium",
                "description": "Identify root cause from correlated alerts and metrics",
                "max_steps": 5,
                "reward_range": [0.1, 0.9],
                "score_range": [0.1, 0.9],
                "min_score": 0.1,
                "max_score": 0.9,
            },
            {
                "id": "full-incident-response",
                "difficulty": "hard",
                "description": "Full incident lifecycle: diagnose, remediate, verify, postmortem",
                "max_steps": 8,
                "reward_range": [0.1, 0.9],
                "score_range": [0.1, 0.9],
                "min_score": 0.1,
                "max_score": 0.9,
            },
        ]
    }


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=False)
