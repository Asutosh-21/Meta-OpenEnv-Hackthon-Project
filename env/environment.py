import random
from typing import Optional, Dict, Any, List

from .data import TASK_INCIDENTS
from .models import Observation, Action, StepResult
from .tasks import grade_alert_triage, grade_root_cause, grade_full_incident_response

TASK_TYPES = ["alert-triage", "root-cause", "full-incident-response"]
MAX_STEPS = {"alert-triage": 3, "root-cause": 5, "full-incident-response": 8}
VALID_ACTIONS = {"alert-triage": ["classify"], "root-cause": ["investigate"], "full-incident-response": ["classify", "investigate", "remediate", "verify", "postmortem"]}




class IncidentResponseEnv:
    def __init__(self, task_type: str = "alert-triage", seed: Optional[int] = None):
        if task_type not in TASK_TYPES:
            raise ValueError(f"task_type must be one of {TASK_TYPES}")
        self.task_type = task_type
        self.seed = seed
        self._rng = random.Random(seed)  # None = truly random
        self._incident: Optional[Dict[str, Any]] = None
        self._step_num: int = 0
        self._done: bool = False
        self._actions_taken: List[Dict[str, Any]] = []
        self._rewards: List[float] = []

    def reset(self) -> Observation:
        incidents = TASK_INCIDENTS[self.task_type]
        self._incident = self._rng.choice(incidents)
        self._step_num = 0
        self._done = False
        self._actions_taken = []
        self._rewards = []
        return self._make_observation()

    def step(self, action: Action) -> StepResult:
        if self._done:
            raise RuntimeError("Episode is done. Call reset() first.")

        self._step_num += 1
        action_dict = action.model_dump()
        self._actions_taken.append(action_dict)

        # penalise invalid action_type
        valid = VALID_ACTIONS.get(self.task_type, [])
        if action_dict.get("action_type") not in valid:
            self._rewards.append(0.1)
            max_s = MAX_STEPS[self.task_type]
            done = self._step_num >= max_s
            self._done = done
            obs = self._make_observation()
            return StepResult(observation=obs, reward=0.2, done=done,
                              info={"step": self._step_num, "max_steps": max_s,
                                    "incident_id": self._incident["incident_id"],
                                    "cumulative_reward": 0.2, "error": "invalid action_type"})

        reward, done = self._compute_reward(action_dict)
        self._rewards.append(reward)

        max_s = MAX_STEPS[self.task_type]
        if self._step_num >= max_s:
            done = True
        self._done = done

        obs = self._make_observation()
        info = {
            "step": self._step_num,
            "max_steps": max_s,
            "incident_id": self._incident["incident_id"],
            "cumulative_reward": round(sum(self._rewards), 4),
        }
        return StepResult(observation=obs, reward=round(reward, 4), done=done, info=info)

    def state(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "incident_id": self._incident["incident_id"] if self._incident else None,
            "step_number": self._step_num,
            "done": self._done,
            "actions_taken": self._actions_taken,
            "rewards": self._rewards,
            "cumulative_reward": round(sum(self._rewards), 4) if self._rewards else 0.1,
        }

    # ── internal helpers ──────────────────────────────────────────────────────

    def _make_observation(self) -> Observation:
        inc = self._incident
        max_s = MAX_STEPS[self.task_type]
        context = None
        if self._step_num > 0 and self._actions_taken:
            last = self._actions_taken[-1]
            last_reward = self._rewards[-1] if self._rewards else 0.1
            context = (
                f"Previous action reward: {last_reward:.2f}. "
                f"Steps remaining: {max_s - self._step_num}."
            )
        return Observation(
            task_id=f"{self.task_type}-{inc['incident_id']}",
            task_type=self.task_type,
            incident_id=inc["incident_id"],
            alerts=inc["alerts"],
            logs=inc["logs"],
            metrics=inc["metrics"],
            runbook=inc.get("runbook"),
            step_number=self._step_num,
            max_steps=max_s,
            context=context,
        )

    def _compute_reward(self, action_dict: Dict[str, Any]) -> tuple:
        gt = self._incident["ground_truth"]

        if self.task_type == "alert-triage":
            score, _, _ = grade_alert_triage(action_dict, gt)
            return score, True  # single-step task

        elif self.task_type == "root-cause":
            score, _, _ = grade_root_cause(action_dict, gt)
            # add step-based bonus to ensure varying rewards
            step_bonus = round(self._step_num * 0.02, 4)
            score = round(min(max(score + step_bonus, 0.15), 0.85), 4)
            done = action_dict.get("action_type") == "investigate"
            return score, done

        else:  # full-incident-response
            score, _, _ = grade_full_incident_response(self._actions_taken, gt)
            # shaped reward: delta from previous cumulative
            prev = sum(self._rewards[:-1]) if len(self._rewards) > 1 else 0.1
            # penalise wrong remediation
            if action_dict.get("action_type") == "remediate":
                rem_steps = action_dict.get("remediation_steps") or []
                if not rem_steps:
                    score = max(0.1, score - 0.1)
            done = action_dict.get("action_type") == "postmortem"
            return score, done
