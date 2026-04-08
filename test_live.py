import requests

base = "https://asuml21-incident-response-openenv.hf.space"
all_ok = True

for task in ["alert-triage", "root-cause", "full-incident-response"]:
    print(f"--- {task} ---")

    r = requests.post(f"{base}/reset", json={"task_type": task, "seed": 42}, timeout=30)
    print(f"  reset HTTP: {r.status_code}")
    reset_reward = r.json().get("reward", "MISSING")
    ok = isinstance(reset_reward, (int, float)) and 0 < float(reset_reward) < 1
    print(f"  reset reward: {reset_reward} {'OK' if ok else 'FAIL <<<<<'}")
    if not ok:
        all_ok = False

    if task == "alert-triage":
        action = {"action_type": "classify", "severity": "P4", "affected_service": "unknown", "explanation": "test"}
    elif task == "root-cause":
        action = {"action_type": "investigate", "root_cause": "unknown", "explanation": "test"}
    else:
        action = {"action_type": "classify", "severity": "P4", "affected_service": "unknown", "explanation": "test"}

    s = requests.post(f"{base}/step", json={"task_type": task, "action": action}, timeout=30)
    step_reward = s.json().get("reward", "MISSING")
    ok2 = isinstance(step_reward, (int, float)) and 0 < float(step_reward) < 1
    print(f"  step reward:  {step_reward} {'OK' if ok2 else 'FAIL <<<<<'}")
    if not ok2:
        all_ok = False
    print()

print("=" * 40)
print("LIVE HF SPACE:", "ALL PASS" if all_ok else "SOME FAILED")
print("=" * 40)
