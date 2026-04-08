import requests

base = "https://asuml21-incident-response-openenv.hf.space"

print("=== /tasks ===")
r = requests.get(f"{base}/tasks", timeout=30)
import json
print(json.dumps(r.json(), indent=2))

print("\n=== /state after reset ===")
requests.post(f"{base}/reset", json={"task_type": "alert-triage"}, timeout=30)
s = requests.get(f"{base}/state?task_type=alert-triage", timeout=30)
print(json.dumps(s.json(), indent=2))

print("\n=== full step response ===")
requests.post(f"{base}/reset", json={"task_type": "alert-triage", "seed": 42}, timeout=30)
step = requests.post(f"{base}/step", json={
    "task_type": "alert-triage",
    "action": {"action_type": "classify", "severity": "P1", "affected_service": "payment-service", "explanation": "test"}
}, timeout=30)
print(json.dumps(step.json(), indent=2))
