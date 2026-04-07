"""
client.py — Interactive client for Incident Response OpenEnv
Usage: python client.py --scenario scenario_config.json
"""

import argparse
import json
import os
import sys
from typing import Optional

import requests
from openai import OpenAI


def load_config(path: str) -> dict:
    with open(path) as f:
        return json.load(f)


def build_prompt(obs: dict, system_prompt: str) -> tuple:
    alerts = json.dumps(obs.get("alerts", []), indent=2)
    logs = "\n".join(obs.get("logs", []))
    metrics = json.dumps(obs.get("metrics", {}), indent=2)
    runbook = obs.get("runbook") or "N/A"
    context = obs.get("context") or ""

    user = (
        f"Incident: {obs['incident_id']} | Task: {obs['task_type']} | "
        f"Step {obs['step_number']}/{obs['max_steps']}\n"
        f"{f'Context: {context}' if context else ''}\n\n"
        f"ALERTS:\n{alerts}\n\nLOGS:\n{logs}\n\n"
        f"METRICS:\n{metrics}\n\nRUNBOOK:\n{runbook}\n\n"
        "Respond with a JSON action object only."
    )
    return system_prompt, user


def get_action(client: OpenAI, model: str, system: str, user: str, temperature: float) -> dict:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=temperature,
            max_tokens=512,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        print(f"[WARN] LLM error: {e}", file=sys.stderr)
        return {"action_type": "classify", "severity": "P2",
                "affected_service": "unknown", "explanation": "fallback"}


def run_scenario(config: dict, task: dict) -> dict:
    base = config.get("env_base_url", "http://localhost:7860")
    task_type = task["task_type"]
    max_steps = task.get("max_steps", 8)
    temperature = config.get("temperature", 0.2)
    system_prompt = config.get("system_prompt", "You are an SRE engineer.")

    api_key = config.get("llm_api_key") or os.getenv("HF_TOKEN") or os.getenv("API_KEY")
    api_base = config.get("api_base_url", "https://api.openai.com/v1")
    model = config.get("llm_model", "gpt-4.1-mini")
    client = OpenAI(base_url=api_base, api_key=api_key)

    # reset
    r = requests.post(f"{base}/reset", json={"task_type": task_type, "seed": task.get("seed", 42)})
    r.raise_for_status()
    obs = r.json()["observation"]

    rewards = []
    actions_log = []

    for step in range(1, max_steps + 1):
        system, user = build_prompt(obs, system_prompt)
        action = get_action(client, model, system, user, temperature)

        r = requests.post(f"{base}/step", json={"task_type": task_type, "action": action})
        r.raise_for_status()
        result = r.json()

        reward = float(result.get("reward", 0.0))
        done = bool(result.get("done", False))
        obs = result.get("observation", obs)

        rewards.append(reward)
        actions_log.append({"step": step, "action": action, "reward": reward, "done": done})
        print(f"  step={step} reward={reward:.2f} done={done}", flush=True)

        if done:
            break

    score = sum(rewards) / max(len(rewards), 1)
    return {"task_type": task_type, "steps": len(rewards),
            "score": round(score, 4), "rewards": rewards, "actions": actions_log}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="scenario_config.json")
    args = parser.parse_args()

    config = load_config(args.scenario)
    results = []

    for task in config.get("tasks", []):
        print(f"\n[TASK] {task['task_type']}")
        result = run_scenario(config, task)
        results.append(result)
        print(f"[DONE] score={result['score']:.4f} steps={result['steps']}")

    os.makedirs("response_output", exist_ok=True)
    out_path = "response_output/results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OUTPUT] saved to {out_path}")


if __name__ == "__main__":
    main()
