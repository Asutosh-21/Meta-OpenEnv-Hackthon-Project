import requests

base = "https://asuml21-incident-response-openenv.hf.space"

for task in ["alert-triage", "root-cause", "full-incident-response"]:
    print(f"\n=== {task} ===")
    
    # reset
    r = requests.post(f"{base}/reset", json={"task_type": task, "seed": 42}, timeout=30)
    print(f"reset reward: {r.json().get('reward')}")
    
    # multiple steps
    actions = {
        "alert-triage": [
            {"action_type": "classify", "severity": "P1", "affected_service": "payment-service", "explanation": "test"},
            {"action_type": "classify", "severity": "P4", "affected_service": "unknown", "explanation": "test"},
        ],
        "root-cause": [
            {"action_type": "investigate", "root_cause": "redis memory exhaustion", "correlated_alerts": ["ALT-401","ALT-402","ALT-403"], "explanation": "redis oom"},
            {"action_type": "investigate", "root_cause": "", "correlated_alerts": [], "explanation": ""},
        ],
        "full-incident-response": [
            {"action_type": "classify", "severity": "P2", "affected_service": "etl-service", "explanation": "test"},
            {"action_type": "investigate", "root_cause": "iam permission", "explanation": "test"},
            {"action_type": "remediate", "remediation_steps": ["fix iam", "restart workers"], "explanation": "test"},
            {"action_type": "postmortem", "postmortem": "resolved"},
        ],
    }
    
    for action in actions[task]:
        # reset first for clean state
        requests.post(f"{base}/reset", json={"task_type": task, "seed": 42}, timeout=30)
        s = requests.post(f"{base}/step", json={"task_type": task, "action": action}, timeout=30)
        reward = s.json().get("reward")
        ok = isinstance(reward, (int, float)) and 0 < float(reward) < 1
        print(f"  action={action['action_type']} reward={reward} {'OK' if ok else 'FAIL <<<<'}")
