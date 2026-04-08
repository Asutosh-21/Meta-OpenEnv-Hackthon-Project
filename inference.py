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
import sys
import textwrap
from typing import List, Optional

import requests
from openai import OpenAI

# ── Environment variables ────────────────────────────────────────────────────
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

if HF_TOKEN is None:
    raise ValueError("HF_TOKEN environment variable is required")

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
BENCHMARK = "incident-response"
MAX_STEPS = 8
TEMPERATURE = 0.2
MAX_TOKENS = 512
SUCCESS_THRESHOLD = 0.5

client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

# ── Logging helpers (exact format required by judges) ────────────────────────

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}", flush=True)


def log_end(success: bool, steps: int, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} rewards={rewards_str}", flush=True)


# ── Prompt builders ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert DevOps/SRE engineer responding to production incidents.
Analyze the incident data and respond with a JSON action object.

For task alert-triage, respond with:
{"action_type": "classify", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "explanation": "<brief reason>"}

For task root-cause, respond with:
{"action_type": "investigate", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "root_cause": "<root cause>", "correlated_alerts": ["ALT-XXX"], "explanation": "<detailed reasoning>"}

For task full-incident-response, respond with one of:
{"action_type": "classify", "severity": "P1|P2|P3|P4", "affected_service": "<service>", "explanation": "<reason>"}
{"action_type": "investigate", "root_cause": "<root cause>", "correlated_alerts": ["ALT-XXX"], "explanation": "<reasoning>"}
{"action_type": "remediate", "remediation_steps": ["step1", "step2", ...], "explanation": "<plan>"}
{"action_type": "verify", "explanation": "<what you verified>"}
{"action_type": "postmortem", "postmortem": "<summary of incident, root cause, fix, prevention>"}

Respond ONLY with valid JSON. No markdown, no explanation outside the JSON.
""").strip()


def build_user_prompt(obs: dict) -> str:
    alerts_str = json.dumps(obs.get("alerts", []), indent=2)
    logs_str = "\n".join(obs.get("logs", []))
    metrics_str = json.dumps(obs.get("metrics", {}), indent=2)
    runbook = obs.get("runbook") or "N/A"
    context = obs.get("context") or ""
    return textwrap.dedent(f"""
Incident ID: {obs['incident_id']}
Task: {obs['task_type']}
Step: {obs['step_number']} / {obs['max_steps']}
{f'Context: {context}' if context else ''}

ALERTS:
{alerts_str}

LOGS:
{logs_str}

METRICS:
{metrics_str}

RUNBOOK:
{runbook}

Respond with the appropriate JSON action.
""").strip()


# ── LLM call ─────────────────────────────────────────────────────────────────

def get_action(obs: dict) -> dict:
    user_prompt = build_user_prompt(obs)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        text = (completion.choices[0].message.content or "").strip()
        # strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as exc:
        print(f"[DEBUG] LLM call failed: {exc}", flush=True)
        return {"action_type": "classify", "severity": "P2",
                "affected_service": "unknown", "explanation": "fallback"}


# ── Env HTTP helpers ──────────────────────────────────────────────────────────

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


# ── Episode runner ────────────────────────────────────────────────────────────

def run_episode(task_type: str) -> None:
    log_start(task=task_type, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    success = False
    error_msg = None

    try:
        reset_resp = env_reset(task_type)
        obs = reset_resp["observation"]

        for step in range(1, MAX_STEPS + 1):
            action_dict = get_action(obs)
            action_str = json.dumps(action_dict, separators=(",", ":"))

            try:
                step_resp = env_step(task_type, action_dict)
            except Exception as e:
                error_msg = str(e)
                log_step(step=step, action=action_str, reward=0.1, done=True, error=error_msg)
                steps_taken = step
                break

            reward = float(step_resp.get("reward", 0.1))
            done = bool(step_resp.get("done", False))
            obs = step_resp.get("observation", obs)
            error_msg = None

            rewards.append(reward)
            steps_taken = step

            log_step(step=step, action=action_str, reward=reward, done=done, error=error_msg)

            if done:
                break

        final_score = sum(rewards) / max(len(rewards), 1)
        final_score = min(max(final_score, 0.1), 0.9)
        success = final_score >= SUCCESS_THRESHOLD
        # ensure no exact 0.0 or 1.0 in rewards list
        rewards = [min(max(r, 0.1), 0.9) for r in rewards]

    except Exception as exc:
        error_msg = str(exc)
        print(f"[DEBUG] Episode error: {exc}", flush=True)

    finally:
        log_end(success=success, steps=steps_taken, rewards=rewards)


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tasks = ["alert-triage", "root-cause", "full-incident-response"]
    for task in tasks:
        run_episode(task)
