try:
    from openenv.core.rubrics.base import Rubric as _BaseRubric
    _HAS_OPENENV = True
except ImportError:
    _HAS_OPENENV = False
    class _BaseRubric:
        def __call__(self, action, observation):
            return self.forward(action, observation)
        def forward(self, action, observation):
            raise NotImplementedError

from env.tasks import grade_alert_triage, grade_root_cause, grade_full_incident_response


class AlertTriageRubric(_BaseRubric):
    def forward(self, action: dict, observation: dict) -> float:
        gt = observation.get("ground_truth", {})
        if not gt:
            return 0.5
        score, _, _ = grade_alert_triage(action, gt)
        return float(score)


class RootCauseRubric(_BaseRubric):
    def forward(self, action: dict, observation: dict) -> float:
        gt = observation.get("ground_truth", {})
        if not gt:
            return 0.5
        score, _, _ = grade_root_cause(action, gt)
        return float(score)


class FullIncidentRubric(_BaseRubric):
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
