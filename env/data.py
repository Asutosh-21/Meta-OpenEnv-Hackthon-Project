from typing import List, Dict, Any

INCIDENTS: List[Dict[str, Any]] = [
    # ── TASK 1: alert-triage (Easy) ──────────────────────────────────────────
    {
        "incident_id": "INC-001",
        "task_type": "alert-triage",
        "alerts": [
            {"id": "ALT-101", "name": "DatabaseConnectionPoolExhausted",
             "source": "postgres-prod", "timestamp": "2024-01-15T14:23:00Z",
             "message": "Connection pool exhausted: 500/500 connections used"},
            {"id": "ALT-102", "name": "APILatencyHigh",
             "source": "api-gateway", "timestamp": "2024-01-15T14:23:05Z",
             "message": "p99 latency 8200ms, threshold 2000ms"},
        ],
        "logs": [
            "2024-01-15T14:22:58Z ERROR postgres-prod: too many connections",
            "2024-01-15T14:23:01Z ERROR api-gateway: upstream timeout after 8000ms",
            "2024-01-15T14:23:03Z WARN  api-gateway: retrying request (attempt 3/3)",
        ],
        "metrics": {"db_connections": 500, "db_max_connections": 500,
                    "api_p99_latency_ms": 8200, "error_rate_pct": 34.5},
        "runbook": None,
        "ground_truth": {"severity": "P1", "affected_service": "postgres-prod",
                         "root_cause": "database_connection_exhaustion"},
    },
    {
        "incident_id": "INC-002",
        "task_type": "alert-triage",
        "alerts": [
            {"id": "ALT-201", "name": "DiskUsageHigh",
             "source": "worker-node-3", "timestamp": "2024-01-15T09:10:00Z",
             "message": "Disk usage at 82%, threshold 80%"},
        ],
        "logs": [
            "2024-01-15T09:09:55Z WARN worker-node-3: disk usage 82%",
            "2024-01-15T09:10:00Z INFO worker-node-3: log rotation scheduled",
        ],
        "metrics": {"disk_usage_pct": 82, "disk_free_gb": 18},
        "runbook": None,
        "ground_truth": {"severity": "P3", "affected_service": "worker-node-3",
                         "root_cause": "disk_space_warning"},
    },
    {
        "incident_id": "INC-003",
        "task_type": "alert-triage",
        "alerts": [
            {"id": "ALT-301", "name": "ServiceDown",
             "source": "payment-service", "timestamp": "2024-01-15T18:05:00Z",
             "message": "Health check failed 3 consecutive times"},
            {"id": "ALT-302", "name": "RevenueDropDetected",
             "source": "billing-monitor", "timestamp": "2024-01-15T18:05:30Z",
             "message": "Revenue processing dropped to 0 transactions/min"},
        ],
        "logs": [
            "2024-01-15T18:04:45Z ERROR payment-service: OOMKilled",
            "2024-01-15T18:04:50Z ERROR payment-service: container restart failed",
            "2024-01-15T18:05:00Z ERROR billing-monitor: no transactions received",
        ],
        "metrics": {"payment_tps": 0, "payment_service_restarts": 5,
                    "memory_usage_mb": 4096, "memory_limit_mb": 4096},
        "runbook": None,
        "ground_truth": {"severity": "P1", "affected_service": "payment-service",
                         "root_cause": "oom_kill"},
    },

    # ── TASK 2: root-cause (Medium) ──────────────────────────────────────────
    {
        "incident_id": "INC-004",
        "task_type": "root-cause",
        "alerts": [
            {"id": "ALT-401", "name": "CacheHitRateLow", "source": "redis-cluster",
             "timestamp": "2024-01-16T11:00:00Z", "message": "Cache hit rate 12%, normal 94%"},
            {"id": "ALT-402", "name": "DatabaseCPUHigh", "source": "postgres-prod",
             "timestamp": "2024-01-16T11:00:30Z", "message": "CPU usage 98%"},
            {"id": "ALT-403", "name": "APIResponseTimeDegraded", "source": "api-gateway",
             "timestamp": "2024-01-16T11:01:00Z", "message": "p50 latency 3200ms, normal 120ms"},
        ],
        "logs": [
            "2024-01-16T10:58:00Z INFO  redis-cluster: node redis-2 evicted 50000 keys (maxmemory)",
            "2024-01-16T10:58:30Z WARN  redis-cluster: memory usage 99.8%",
            "2024-01-16T10:59:00Z ERROR redis-cluster: OOM eviction policy active",
            "2024-01-16T11:00:00Z WARN  postgres-prod: query cache miss rate elevated",
        ],
        "metrics": {"redis_memory_pct": 99.8, "redis_hit_rate": 0.12,
                    "db_cpu_pct": 98, "api_p50_ms": 3200, "evicted_keys": 50000},
        "runbook": None,
        "ground_truth": {
            "severity": "P1",
            "affected_service": "redis-cluster",
            "root_cause": "redis_memory_exhaustion_causing_cache_eviction",
            "correlated_alerts": ["ALT-401", "ALT-402", "ALT-403"],
        },
    },
    {
        "incident_id": "INC-005",
        "task_type": "root-cause",
        "alerts": [
            {"id": "ALT-501", "name": "DeploymentFailed", "source": "ci-cd-pipeline",
             "timestamp": "2024-01-16T15:30:00Z", "message": "Deployment v2.4.1 failed rollout"},
            {"id": "ALT-502", "name": "PodCrashLooping", "source": "k8s-cluster",
             "timestamp": "2024-01-16T15:31:00Z", "message": "auth-service pods CrashLoopBackOff x8"},
            {"id": "ALT-503", "name": "AuthFailureRateHigh", "source": "auth-service",
             "timestamp": "2024-01-16T15:31:30Z", "message": "401 error rate 89%"},
        ],
        "logs": [
            "2024-01-16T15:30:00Z ERROR auth-service: missing env var JWT_SECRET",
            "2024-01-16T15:30:01Z ERROR auth-service: panic: runtime error nil pointer",
            "2024-01-16T15:30:05Z INFO  k8s: restarting container auth-service (exit code 1)",
        ],
        "metrics": {"auth_error_rate_pct": 89, "pod_restarts": 8,
                    "deployment_success": False},
        "runbook": None,
        "ground_truth": {
            "severity": "P1",
            "affected_service": "auth-service",
            "root_cause": "missing_environment_variable_in_deployment",
            "correlated_alerts": ["ALT-501", "ALT-502", "ALT-503"],
        },
    },

    # ── TASK 3: full-incident-response (Hard) ────────────────────────────────
    {
        "incident_id": "INC-006",
        "task_type": "full-incident-response",
        "alerts": [
            {"id": "ALT-601", "name": "DataPipelineStalled", "source": "etl-service",
             "timestamp": "2024-01-17T03:00:00Z", "message": "Pipeline jobs queued > 10000, processing 0"},
            {"id": "ALT-602", "name": "KafkaConsumerLag", "source": "kafka-cluster",
             "timestamp": "2024-01-17T03:00:30Z", "message": "Consumer lag 2.4M messages on topic events"},
            {"id": "ALT-603", "name": "S3WriteErrors", "source": "etl-service",
             "timestamp": "2024-01-17T03:01:00Z", "message": "S3 PutObject failures 100%"},
            {"id": "ALT-604", "name": "DashboardDataStale", "source": "analytics-service",
             "timestamp": "2024-01-17T03:15:00Z", "message": "Dashboard data 75 minutes stale"},
        ],
        "logs": [
            "2024-01-17T02:58:00Z ERROR etl-service: S3 AccessDenied on bucket prod-data-lake",
            "2024-01-17T02:58:01Z ERROR etl-service: IAM role etl-prod-role missing s3:PutObject",
            "2024-01-17T02:58:05Z WARN  etl-service: retrying S3 write (attempt 1/5)",
            "2024-01-17T03:00:00Z ERROR etl-service: all retries exhausted, job failed",
            "2024-01-17T03:00:01Z INFO  kafka: consumer group etl-consumer lag increasing",
        ],
        "metrics": {"kafka_consumer_lag": 2400000, "etl_jobs_queued": 10000,
                    "s3_error_rate_pct": 100, "data_freshness_minutes": 75},
        "runbook": (
            "ETL Pipeline Runbook:\n"
            "1. Check IAM role permissions for S3 access\n"
            "2. Verify S3 bucket policy allows etl-prod-role\n"
            "3. If IAM issue: update role policy via AWS Console or CLI\n"
            "4. Restart ETL workers after fixing permissions\n"
            "5. Monitor Kafka consumer lag — should decrease within 10 min\n"
            "6. Verify dashboard data freshness returns to < 5 min\n"
            "7. Write postmortem documenting root cause and prevention"
        ),
        "ground_truth": {
            "severity": "P2",
            "affected_service": "etl-service",
            "root_cause": "iam_permission_revoked_s3_putobject",
            "remediation_steps": [
                "identify_iam_permission_issue",
                "restore_s3_putobject_permission",
                "restart_etl_workers",
                "verify_kafka_lag_decreasing",
                "confirm_dashboard_data_fresh",
            ],
            "correlated_alerts": ["ALT-601", "ALT-602", "ALT-603", "ALT-604"],
        },
    },
    {
        "incident_id": "INC-007",
        "task_type": "full-incident-response",
        "alerts": [
            {"id": "ALT-701", "name": "SSLCertExpiringSoon", "source": "cert-monitor",
             "timestamp": "2024-01-17T08:00:00Z", "message": "SSL cert for api.prod.com expires in 2 days"},
            {"id": "ALT-702", "name": "WebhookDeliveryFailing", "source": "webhook-service",
             "timestamp": "2024-01-17T08:00:30Z", "message": "Webhook delivery failure rate 67%"},
        ],
        "logs": [
            "2024-01-17T07:59:00Z WARN  cert-monitor: certificate expiry in 48h",
            "2024-01-17T08:00:00Z ERROR webhook-service: SSL handshake failed — cert untrusted",
            "2024-01-17T08:00:05Z ERROR webhook-service: TLS verification failed for partner endpoints",
        ],
        "metrics": {"cert_days_remaining": 2, "webhook_failure_rate_pct": 67,
                    "affected_partners": 12},
        "runbook": (
            "SSL Certificate Runbook:\n"
            "1. Verify certificate expiry date with: openssl s_client\n"
            "2. Initiate certificate renewal via cert-manager or ACM\n"
            "3. Deploy renewed certificate to load balancer\n"
            "4. Verify new cert is active and trusted\n"
            "5. Monitor webhook delivery rate recovery\n"
            "6. Notify affected partners of temporary disruption\n"
            "7. Set up automated renewal alerts at 30/14/7 days"
        ),
        "ground_truth": {
            "severity": "P2",
            "affected_service": "api.prod.com",
            "root_cause": "ssl_certificate_near_expiry",
            "remediation_steps": [
                "verify_certificate_expiry",
                "initiate_certificate_renewal",
                "deploy_new_certificate",
                "verify_webhook_recovery",
                "notify_affected_partners",
            ],
            "correlated_alerts": ["ALT-701", "ALT-702"],
        },
    },
]

TASK_INCIDENTS = {
    "alert-triage": [i for i in INCIDENTS if i["task_type"] == "alert-triage"],
    "root-cause": [i for i in INCIDENTS if i["task_type"] == "root-cause"],
    "full-incident-response": [i for i in INCIDENTS if i["task_type"] == "full-incident-response"],
}
