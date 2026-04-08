import requests
import json

base = "http://localhost:7860"
all_ok = True

for task in ["alert-triage", "root-cause", "full-incident-response"]:
    print(f"--- {task} ---")
    rewards = []

    r = requests.post(f"{base}/reset", json={"task_type": task, "seed": 42}, timeout=30)
    obs = r.json()["observation"]

    for step in range(1, 9):
        if task == "alert-triage":
            action = {"action_type": "classify", "severity": "P1", "affected_service": "payment-service", "explanation": "test"}
        elif task == "root-cause":
            action = {"action_type": "investigate", "root_cause": "redis memory exhaustion", "correlated_alerts": ["ALT-401", "ALT-402", "ALT-403"], "explanation": "redis memory exhaustion causing cache eviction cascade"}
        else:
            actions_seq = [
                {"action_type": "classify", "severity": "P2", "affected_service": "etl-service", "explanation": "test"},
                {"action_type": "investigate", "root_cause": "iam permission revoked s3 putobject", "correlated_alerts": ["ALT-601","ALT-602","ALT-603","ALT-604"], "explanation": "iam permission issue"},
                {"action_type": "remediate", "remediation_steps": ["restore s3 putobject permission", "restart etl workers"], "explanation": "fix iam"},
                {"action_type": "verify", "explanation": "verified kafka lag decreasing"},
                {"action_type": "postmortem", "postmortem": "iam permission was revoked causing etl pipeline failure"},
            ]
            action = actions_seq[min(step-1, len(actions_seq)-1)]

        s = requests.post(f"{base}/step", json={"task_type": task, "action": action}, timeout=30)
        data = s.json()
        reward = float(data.get("reward", 0.0))
        done = bool(data.get("done", False))
        obs = data.get("observation", obs)

        ok = 0 < reward < 1
        if not ok:
            all_ok = False
        print(f"  step={step} reward={reward:.2f} done={done} {'OK' if ok else 'FAIL <<<<<'}")
        rewards.append(reward)

        if done:
            break

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"  [END] rewards={rewards_str}")
    print()

print("=" * 40)
print("RESULT:", "ALL PASS" if all_ok else "SOME FAILED")
print("=" * 40)
