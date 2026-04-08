from env.environment import IncidentResponseEnv
from env.models import Action

print("=== Phase 2 Simulation ===")
all_ok = True

for task in ["alert-triage", "root-cause", "full-incident-response"]:
    env = IncidentResponseEnv(task_type=task, seed=42)
    env.reset()

    # worst case
    if task == "alert-triage":
        a = Action(action_type="classify", severity="P4", affected_service="unknown", explanation="test")
    elif task == "root-cause":
        a = Action(action_type="investigate", root_cause="unknown", explanation="test")
    else:
        a = Action(action_type="classify", severity="P4", affected_service="unknown", explanation="test")

    result = env.step(a)
    r = result.reward
    ok = 0 < r < 1
    if not ok:
        all_ok = False
    print(f"  {task}: reward={r} {'OK' if ok else 'FAIL'}")

    # best case
    env2 = IncidentResponseEnv(task_type=task, seed=42)
    env2.reset()
    if task == "alert-triage":
        a2 = Action(action_type="classify", severity="P1", affected_service="payment-service", explanation="test")
    elif task == "root-cause":
        a2 = Action(action_type="investigate", root_cause="redis memory exhaustion causing cache eviction", correlated_alerts=["ALT-401","ALT-402","ALT-403"], explanation="detailed root cause analysis of memory exhaustion and cache eviction cascade failure")
    else:
        a2 = Action(action_type="classify", severity="P2", affected_service="etl-service", explanation="test")

    result2 = env2.step(a2)
    r2 = result2.reward
    ok2 = 0 < r2 < 1
    if not ok2:
        all_ok = False
    print(f"  {task}: best_reward={r2} {'OK' if ok2 else 'FAIL'}")

print()
print("RESULT:", "ALL PASS" if all_ok else "SOME FAILED")
