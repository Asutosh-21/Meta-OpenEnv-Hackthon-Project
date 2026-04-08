from env.tasks import grade_alert_triage, grade_root_cause, grade_full_incident_response
from env.data import INCIDENTS

all_ok = True

for inc in INCIDENTS:
    gt = inc["ground_truth"]
    tt = inc["task_type"]

    if tt == "alert-triage":
        s1, _, _ = grade_alert_triage({"action_type": "classify", "severity": gt["severity"], "affected_service": gt["affected_service"]}, gt)
        s2, _, _ = grade_alert_triage({"action_type": "classify", "severity": "P4", "affected_service": "unknown"}, gt)
        scores = [("best", s1), ("worst", s2)]

    elif tt == "root-cause":
        s1, _, _ = grade_root_cause({"action_type": "investigate", "root_cause": gt["root_cause"], "correlated_alerts": gt.get("correlated_alerts", []), "explanation": "detailed root cause analysis memory exhaustion cache eviction cascade failure production system"}, gt)
        s2, _, _ = grade_root_cause({"action_type": "investigate", "root_cause": "", "correlated_alerts": [], "explanation": ""}, gt)
        scores = [("best", s1), ("worst", s2)]

    else:
        best = [
            {"action_type": "classify", "severity": gt["severity"], "affected_service": gt["affected_service"], "explanation": "x"},
            {"action_type": "investigate", "root_cause": gt["root_cause"], "correlated_alerts": gt.get("correlated_alerts", []), "explanation": "x"},
            {"action_type": "remediate", "remediation_steps": gt.get("remediation_steps", []), "explanation": "x"},
            {"action_type": "postmortem", "postmortem": "incident resolved root cause fixed prevention steps added"},
        ]
        worst = [{"action_type": "classify", "severity": "P4", "affected_service": "unknown", "explanation": ""}]
        s1, _, _ = grade_full_incident_response(best, gt)
        s2, _, _ = grade_full_incident_response(worst, gt)
        scores = [("best", s1), ("worst", s2)]

    for label, s in scores:
        ok = 0 < s < 1
        status = "OK" if ok else "FAIL <<<<<"
        print(f"  {inc['incident_id']} [{tt}] {label}: {s} {status}")
        if not ok:
            all_ok = False

print()
print("=" * 50)
print("RESULT:", "ALL SCORES PASS (0 < score < 1)" if all_ok else "SOME SCORES FAILED")
print("=" * 50)
