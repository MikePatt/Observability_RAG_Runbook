# Runbook: High Memory Usage & OOM Failures

## Overview

This runbook covers procedures for responding to Out-Of-Memory (OOM) failures
and high memory utilization alerts across forecasting and observability services.

## Alert Triggers

- `forecasting_service_memory_usage > 85%` for 5+ minutes
- `pod_oom_killed` event in Kubernetes
- `memory_aggregation_lag > 30s` in the observability pipeline

## Immediate Response Steps

### Step 1: Assess Scope

Check the memory utilization dashboard to determine if the issue is isolated to
a single pod or affecting multiple replicas. Look for:

- Pod restart count > 3 in the last 10 minutes
- Memory usage trending upward without plateau
- Correlation with recent deployments or high-volume ingestion windows

### Step 2: Identify the Offending Service

```bash
kubectl top pods -n observability --sort-by=memory
kubectl describe pod <pod-name> -n observability | grep -A5 "OOM"
```

Check the PySpark job logs if the OOM correlates with a batch aggregation run:

```bash
kubectl logs <spark-driver-pod> -n pipelines | grep -i "OutOfMemory\|GC overhead"
```

### Step 3: Immediate Mitigation

If a single pod is OOM-killed and the service has replicas, the load balancer
will route traffic away automatically. Verify by checking the health endpoint.

For a pod in CrashLoopBackOff:

```bash
kubectl rollout restart deployment/forecasting-service -n observability
```

Monitor for 2 minutes. If OOM persists across multiple pods, escalate immediately.

### Step 4: Root Cause Investigation

Common causes:

1. **Memory aggregation leak** — check if the rolling aggregation window is
   accumulating state without eviction. Look for unbounded caches or dictionaries
   growing over time in the aggregator service.

2. **PySpark executor memory** — check if `spark.executor.memory` is undersized
   for the current data volume. Hive table partition sizes may have grown.

3. **Prophet model inference** — large time-series windows passed to Prophet
   can cause memory spikes. Check the `n_changepoints` and `period` parameters.

### Step 5: Escalation

If OOM is not resolved within 15 minutes:
- Page the on-call platform lead via PagerDuty
- Open a P1 incident in the incident management system
- Attach pod logs and memory graphs to the incident

## Prevention

- Set `requests.memory` and `limits.memory` in Kubernetes manifests
- Enable HPA (Horizontal Pod Autoscaler) on memory utilization > 70%
- Review Spark executor configuration quarterly against data volume growth
- Add circuit breakers to the memory aggregation pipeline

## Rollback Procedure

If OOM is caused by a recent deployment:

```bash
kubectl rollout undo deployment/forecasting-service -n observability
kubectl rollout status deployment/forecasting-service -n observability
```

Verify the previous version is stable for 5 minutes before closing the incident.
