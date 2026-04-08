from openenv.core.rubrics.base import Rubric
from env.tasks import grade_alert_triage, grade_root_cause, grade_full_incident_response


class AlertTriageRubric(Rubric):
    def forward(self, action: dict, observation: dict) -> float:
        gt = observation.get("ground_truth", {})
        if not gt:
            return 0.5
        score, _, _ = grade_alert_triage(action, gt)
        return float(score)


class RootCauseRubric(Rubric):
    def forward(self, action: dict, observation: dict) -> float:
        gt = observation.get("ground_truth", {})
        if not gt:
            return 0.5
        score, _, _ = grade_root_cause(action, gt)
        return float(score)


class FullIncidentRubric(Rubric):
    def forward(self, action: dict, observation: dict) -> float:
        gt = observation.get("ground_truth", {})
        actions = observation.get("actions_taken", [action])
        if not gt:
            return 0.5
        score, _, _ = grade_full_incident_response(actions, gt)
        return float(score)


TASK_RUBRICS = {
    "alert-triage": AlertTriageRubric(),
    "root-cause": RootCauseRubric(),
    "full-incident-response": FullIncidentRubric(),
}
