---
title: Incident Response OpenEnv
emoji: 🚨
colorFrom: red
colorTo: yellow
sdk: docker
pinned: false
app_port: 7860
base_path: /docs
tags:
  - openenv
  - incident-response
---

# OpenEnv — Incident Response v1.1

An OpenEnv-compliant reinforcement learning environment that simulates real-world DevOps/SRE incident response. An AI agent receives production alerts, logs, and metrics, then must triage, investigate, remediate, and document incidents — exactly as an on-call engineer would.

---

## Why This Environment

Every technology company runs 24/7 on-call rotations. Engineers respond to production incidents under pressure, correlating alerts, identifying root causes, and executing remediation steps. This environment trains and evaluates AI agents on that exact workflow — a task with immediate real-world deployment value.

---

## Environment Description

The agent operates in an incident management system. Each episode presents a production incident with:
- **Alerts** — triggered monitoring rules with timestamps and messages
- **Logs** — raw service logs around the incident window
- **Metrics** — quantitative signals (CPU, memory, error rates, latency)
- **Runbook** — operational playbook (Task 3 only)

The agent must take structured actions to resolve the incident.

---

## Action Space

```json
{
  "action_type": "classify | investigate | remediate | verify | postmortem",
  "severity": "P1 | P2 | P3 | P4",
  "affected_service": "string",
  "root_cause": "string",
  "explanation": "string",
  "remediation_steps": ["step1", "step2"],
  "postmortem": "string"
}
```

## Observation Space

```json
{
  "task_id": "string",
  "task_type": "alert-triage | root-cause | full-incident-response",
  "incident_id": "string",
  "alerts": [{"id": "ALT-XXX", "name": "...", "source": "...", "message": "..."}],
  "logs": ["2024-01-15T14:23:00Z ERROR service: message"],
  "metrics": {"key": "value"},
  "runbook": "string | null",
  "step_number": 0,
  "max_steps": 8,
  "context": "string | null"
}
```

---

## Tasks

| Task | Difficulty | Max Steps | Reward Breakdown |
|------|-----------|-----------|-----------------|
| `alert-triage` | Easy | 3 | Severity match (0.6) + Service match (0.4) |
| `root-cause` | Medium | 5 | Root cause (0.5) + Alert correlation F1 (0.3) + Explanation (0.2) |
| `full-incident-response` | Hard | 8 | Severity (0.15) + Root cause (0.25) + Remediation (0.40) + Efficiency (0.20) |

### Task 1 — Alert Triage (Easy)
Classify the incident severity (P1–P4) and identify the affected service from alerts and logs. Single-step evaluation with partial credit for adjacent severity levels.

### Task 2 — Root Cause Analysis (Medium)
Identify the root cause from correlated alerts and metrics. Graded on root cause keyword overlap, alert correlation F1 score, and explanation quality.

### Task 3 — Full Incident Response (Hard)
Multi-step resolution: classify → investigate → remediate → verify → postmortem. Graded on all dimensions with an efficiency penalty for excessive steps. Genuinely challenges frontier models due to multi-step reasoning and runbook adherence.

---

## Reward Function

Rewards are shaped across the full trajectory — not sparse end-of-episode signals:

- **Partial credit** at every step (not just final)
- **Severity adjacency** — P1 vs P2 scores 0.5, not 0.0
- **Keyword overlap** for root cause (handles paraphrasing)
- **F1 scoring** for alert correlation (precision + recall)
- **Efficiency penalty** in Task 3 — fewer steps = higher reward
- **Remediation penalty** — empty remediation steps penalised
- **Wrong action penalty** — invalid action_type returns 0.0 reward

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/reset` | Start new episode |
| POST | `/step` | Take action, get observation + reward |
| GET | `/state` | Current episode state |
| GET | `/tasks` | List all tasks |
| GET | `/health` | Health check |

---

## Quick Demo

```bash
# 1. Start an episode
curl -X POST https://asuml21-incident-response-openenv.hf.space/reset \
  -H "Content-Type: application/json" \
  -d '{"task_type": "alert-triage"}'

# 2. Take an action
curl -X POST https://asuml21-incident-response-openenv.hf.space/step \
  -H "Content-Type: application/json" \
  -d '{"task_type": "alert-triage", "action": {"action_type": "classify", "severity": "P1", "affected_service": "payment-service", "explanation": "Payment service OOMKilled with 0 TPS"}}'

# 3. Check state
curl https://asuml21-incident-response-openenv.hf.space/state?task_type=alert-triage
```

---

## Setup & Usage

### Local

```bash
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 7860
```

### Docker

```bash
docker build -t incident-response-openenv .
docker run -p 7860:7860 incident-response-openenv
```

### Run Inference

```bash
export HF_TOKEN=your_token
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
export ENV_BASE_URL=http://localhost:7860
python inference.py
```

---

## Baseline Scores

Scores produced by `Qwen/Qwen2.5-72B-Instruct` with `temperature=0.2`:

| Task | Score | Notes |
|------|-------|-------|
| `alert-triage` | ~1.00 | Perfect severity + service classification |
| `root-cause` | ~0.45 | Good alert correlation, partial root cause overlap |
| `full-incident-response` | ~0.30 | Multi-step reasoning is genuinely hard, runbook adherence challenging |

---

## Project Structure

```
├── inference.py          # Baseline inference script
├── app.py                # FastAPI server
├── openenv.yaml          # OpenEnv spec metadata
├── Dockerfile
├── requirements.txt
├── README.md
└── env/
    ├── __init__.py
    ├── models.py         # Pydantic typed models
    ├── environment.py    # step/reset/state logic
    ├── tasks.py          # graders for all 3 tasks
    └── data.py           # synthetic incident dataset
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HF_TOKEN` | Yes | — | Hugging Face / OpenAI API key |
| `API_BASE_URL` | No | `https://router.huggingface.co/v1` | LLM API endpoint |
| `MODEL_NAME` | No | `Qwen/Qwen2.5-72B-Instruct` | Model identifier |
| `ENV_BASE_URL` | No | `http://localhost:7860` | Environment server URL |
