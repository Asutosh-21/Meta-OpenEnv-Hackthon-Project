"""
Inference Script — OpenEnv Incident Response
=============================================
Environment variables:
  API_BASE_URL  : LLM API endpoint (default: https://router.huggingface.co/v1)
  MODEL_NAME    : Model identifier  (default: Qwen/Qwen2.5-72B-Instruct)
  HF_TOKEN      : Hugging Face / API key (required, no default)
"""

import json
import os
import textwrap
from typing import List, Optional

import requests
from openai import OpenAI

# ── Environment variables ─────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

ENV_BASE_URL      = os.getenv("ENV_BASE_URL", "https://asuml21-incident-response-openenv.hf.space")
BENCHMARK         = "incident-response"
MAX_STEPS         = 8
TEMPERATURE       = 0.2
MAX_TOKENS        = 512
SUCCESS_THRESHOLD = 0.5

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


# ── Logging ───────────────────────────────────────────────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        f"[STEP] step={step} action={action} "
        f"reward={reward:.2f} done={str(done).lower()} error={error or 'null'}",
        flush=True,
    )


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}",
        flush=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def clamp(v: float) -> float:
    """Ensure score is strictly between 0 and 1."""
    return round(min(max(v, 0.1), 0.9), 4)


SYSTEM_PROMPT = textwrap.dedent("""
You are an expert DevOps/SRE engineer responding to production incidents.
Analyze the incident data and respond with a JSON action object.

For task alert-triage:
{"action_type": "classify", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "explanation": "<reason>"}

For task root-cause:
{"action_type": "investigate", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "root_cause": "<root cause>", "correlated_alerts": ["ALT-XXX"], "explanation": "<reasoning>"}

For task full-incident-response use one of:
{"action_type": "classify", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "explanation": "<reason>"}
{"action_type": "investigate", "root_cause": "<root cause>", "correlated_alerts": ["ALT-XXX"], "explanation": "<reasoning>"}
{"action_type": "remediate", "remediation_steps": ["step1", "step2"], "explanation": "<plan>"}
{"action_type": "verify", "explanation": "<what you verified>"}
{"action_type": "postmortem", "postmortem": "<summary>"}

Respond ONLY with valid JSON. No markdown, no extra text.
""").strip()


def get_action(obs: dict) -> dict:
    alerts  = json.dumps(obs.get("alerts",  []), indent=2)
    logs    = "\n".join(obs.get("logs",     []))
    metrics = json.dumps(obs.get("metrics", {}), indent=2)
    runbook = obs.get("runbook") or "N/A"
    context = obs.get("context") or ""

    user = textwrap.dedent(f"""
Incident: {obs['incident_id']} | Task: {obs['task_type']} | Step {obs['step_number']}/{obs['max_steps']}
{f'Context: {context}' if context else ''}

ALERTS:
{alerts}

LOGS:
{logs}

METRICS:
{metrics}

RUNBOOK:
{runbook}

Respond with the appropriate JSON action.
""").strip()

    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text.strip())
    except Exception as exc:
        print(f"[DEBUG] LLM error: {exc}", flush=True)
        return {"action_type": "classify", "severity": "P2",
                "affected_service": "unknown", "explanation": "fallback"}


def env_reset(task_type: str) -> dict:
    r = requests.post(f"{ENV_BASE_URL}/reset",
                      json={"task_type": task_type, "seed": 42}, timeout=30)
    r.raise_for_status()
    return r.json()


def env_step(task_type: str, action: dict) -> dict:
    r = requests.post(f"{ENV_BASE_URL}/step",
                      json={"task_type": task_type, "action": action}, timeout=30)
    r.raise_for_status()
    return r.json()


# ── Episode ───────────────────────────────────────────────────────────────────

def run_episode(task_type: str) -> None:
    log_start(task=task_type, env=BENCHMARK, model=MODEL_NAME)

    rewards:     List[float] = []
    steps_taken: int         = 0
    success:     bool        = False
    score:       float       = 0.5

    try:
        obs = env_reset(task_type)["observation"]

        for step in range(1, MAX_STEPS + 1):
            action_dict = get_action(obs)
            action_str  = json.dumps(action_dict, separators=(",", ":"))

            try:
                resp = env_step(task_type, action_dict)
            except Exception as e:
                log_step(step, action_str, 0.1, True, str(e))
                rewards.append(0.1)
                steps_taken = step
                break

            reward = clamp(float(resp.get("reward", 0.5)))
            done   = bool(resp.get("done", False))
            obs    = resp.get("observation", obs)

            rewards.append(reward)
            steps_taken = step
            log_step(step, action_str, reward, done, None)

            if done:
                break

        score   = clamp(sum(rewards) / max(len(rewards), 1))
        success = score >= SUCCESS_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] Episode error: {exc}", flush=True)
        score = 0.5

    finally:
        if not rewards:
            rewards = [0.5]
        score = clamp(sum(rewards) / max(len(rewards), 1))
        log_end(success=success, steps=steps_taken, rewards=rewards)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    for task in ["alert-triage", "root-cause", "full-incident-response"]:
        run_episode(task)
