from typing import Dict, Any, Tuple

SEVERITY_MAP = {"P1": 4, "P2": 3, "P3": 2, "P4": 1}


def _clamp(score: float) -> float:
    """Clamp score to strictly (0, 1) — never exactly 0.0 or 1.0."""
    return round(min(max(score, 0.15), 0.85), 4)


def _severity_score(predicted: str, actual: str) -> float:
    """Partial credit: exact=0.9, adjacent=0.5, off by 2+=0.1"""
    if predicted == actual:
        return 0.9
    diff = abs(SEVERITY_MAP.get(predicted, 0) - SEVERITY_MAP.get(actual, 0))
    if diff == 1:
        return 0.5
    return 0.1


def grade_alert_triage(action: Dict[str, Any], ground_truth: Dict[str, Any]) -> Tuple[float, Dict[str, float], str]:
    """
    Task 1 grader — alert-triage (Easy)
    Severity match: 0.6 weight, service match: 0.4 weight
    """
    sev_score = _severity_score(
        (action.get("severity") or "").upper(),
        ground_truth["severity"]
    ) * 0.6

    pred_svc = (action.get("affected_service") or "").lower().strip()
    true_svc = ground_truth["affected_service"].lower().strip()
    svc_score = 0.4 if (pred_svc and (pred_svc in true_svc or true_svc in pred_svc)) else 0.1

    total = _clamp(sev_score + svc_score)
    breakdown = {"severity": round(sev_score, 4), "service": round(svc_score, 4)}
    feedback = (
        f"Severity: {'correct' if sev_score >= 0.6 else 'partial' if sev_score > 0.1 else 'wrong'} "
        f"({action.get('severity')} vs {ground_truth['severity']}), "
        f"Service: {'correct' if svc_score >= 0.4 else 'wrong'} "
        f"({action.get('affected_service')} vs {ground_truth['affected_service']})"
    )
    return total, breakdown, feedback


def grade_root_cause(action: Dict[str, Any], ground_truth: Dict[str, Any]) -> Tuple[float, Dict[str, float], str]:
    """
    Task 2 grader — root-cause (Medium)
    Root cause: 0.5, alert correlation: 0.3, explanation quality: 0.2
    """
    pred_rc = (action.get("root_cause") or "").lower().replace(" ", "_")
    true_rc = ground_truth["root_cause"].lower()
    rc_keywords = set(true_rc.replace("_", " ").split())
    pred_keywords = set(pred_rc.replace("_", " ").split())
    overlap = len(rc_keywords & pred_keywords) / max(len(rc_keywords), 1)
    rc_score = round(max(min(overlap, 0.9), 0.1) * 0.5, 4)

    true_alerts = set(ground_truth.get("correlated_alerts", []))
    pred_alerts = set(action.get("correlated_alerts", []) or [])
    if true_alerts:
        precision = len(pred_alerts & true_alerts) / max(len(pred_alerts), 1)
        recall = len(pred_alerts & true_alerts) / len(true_alerts)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.1
        f1 = min(f1, 0.9)
        corr_score = round(max(f1, 0.1) * 0.3, 4)
    else:
        corr_score = 0.3

    explanation = action.get("explanation") or ""
    exp_score = round(max(min(len(explanation.split()) / 30, 0.9), 0.1) * 0.2, 4)

    total = _clamp(rc_score + corr_score + exp_score)
    breakdown = {"root_cause": rc_score, "correlation": corr_score, "explanation": exp_score}
    feedback = (
        f"Root cause overlap: {overlap:.0%}, "
        f"Alert correlation F1: {(corr_score/0.3):.0%}, "
        f"Explanation words: {len(explanation.split())}"
    )
    return total, breakdown, feedback


def grade_full_incident_response(
    actions: list, ground_truth: Dict[str, Any]
) -> Tuple[float, Dict[str, float], str]:
    """
    Task 3 grader — full-incident-response (Hard)
    Severity: 0.15, root cause: 0.25, remediation steps: 0.40, efficiency: 0.20
    """
    if not actions:
        return 0.1, {}, "No actions taken"

    # scan all actions for best severity and root_cause
    best_sev = ""
    best_rc = ""
    for a in actions:
        if a.get("severity"):
            best_sev = a["severity"]
        if a.get("root_cause"):
            best_rc = a["root_cause"]

    sev_score = _severity_score(best_sev.upper(), ground_truth["severity"]) * 0.15

    pred_rc = best_rc.lower().replace(" ", "_")
    true_rc = ground_truth["root_cause"].lower()
    rc_keywords = set(true_rc.replace("_", " ").split())
    pred_keywords = set(pred_rc.replace("_", " ").split())
    overlap = len(rc_keywords & pred_keywords) / max(len(rc_keywords), 1)
    rc_score = round(max(min(overlap, 0.9), 0.1) * 0.25, 4)

    true_steps = ground_truth.get("remediation_steps", [])
    pred_steps = []
    for a in actions:
        steps = a.get("remediation_steps") or []
        pred_steps.extend([s.lower().replace(" ", "_") for s in steps])

    matched = 0
    for ts in true_steps:
        ts_kw = set(ts.replace("_", " ").split())
        for ps in pred_steps:
            ps_kw = set(ps.replace("_", " ").split())
            if len(ts_kw & ps_kw) / max(len(ts_kw), 1) >= 0.5:
                matched += 1
                break
    rem_score = round(max(min(matched / max(len(true_steps), 1), 0.9), 0.1) * 0.40, 4)

    max_steps = 8
    steps_used = len(actions)
    efficiency = max(0.1, min(1.0 - (steps_used - 1) / max_steps, 0.9))
    eff_score = round(efficiency * 0.20, 4)

    total = _clamp(sev_score + rc_score + rem_score + eff_score)
    breakdown = {
        "severity": sev_score,
        "root_cause": rc_score,
        "remediation": rem_score,
        "efficiency": eff_score,
    }
    feedback = (
        f"Severity: {sev_score/0.15:.0%}, "
        f"Root cause: {overlap:.0%}, "
        f"Remediation steps matched: {matched}/{len(true_steps)}, "
        f"Efficiency: {efficiency:.0%}"
    )
    return total, breakdown, feedback
