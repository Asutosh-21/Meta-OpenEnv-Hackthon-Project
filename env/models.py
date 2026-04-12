from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class Observation(BaseModel):
    task_id: str
    task_type: str  # alert-triage | root-cause | full-incident-response
    incident_id: str
    alerts: List[Dict[str, Any]]
    logs: List[str]
    metrics: Dict[str, Any]
    runbook: Optional[str] = None
    step_number: int
    max_steps: int
    context: Optional[str] = None


class Action(BaseModel):
    action_type: str = "classify"  # classify | investigate | remediate | verify | postmortem
    severity: Optional[str] = None
    affected_service: Optional[str] = None
    root_cause: Optional[str] = None
    explanation: Optional[str] = None
    remediation_steps: Optional[List[str]] = None
    postmortem: Optional[str] = None
    raw_text: Optional[str] = None


class Reward(BaseModel):
    value: float              # 0.0 - 1.0
    breakdown: Dict[str, float]
    feedback: str


class StepResult(BaseModel):
    observation: Observation
    reward: float
    done: bool
    info: Dict[str, Any]
