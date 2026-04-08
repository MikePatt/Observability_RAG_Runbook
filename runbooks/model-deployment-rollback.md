# Runbook: Model Deployment & Rollback

## Overview

This runbook covers the end-to-end procedure for deploying new ML models
to production via Azure ML, validating deployments, and executing rollbacks
when a deployment causes degradation.

## Pre-Deployment Checklist

Before deploying any model:

- [ ] Ragas evaluation scores meet minimum bar (faithfulness > 0.85, context relevance > 0.80)
- [ ] Model version registered in Azure ML Model Registry
- [ ] Offline evaluation run logged to MLflow with passing metrics
- [ ] Canary deployment plan defined (% traffic split)
- [ ] Rollback version identified and tested

## Deployment Procedure

### Step 1: Register Model in Azure ML

```python
import mlflow
from azure.ai.ml import MLClient
from azure.ai.ml.entities import Model

ml_client = MLClient(credential, subscription_id, resource_group, workspace)

model = Model(
    path="./model_artifacts",
    name="forecasting-prophet-v3",
    description="Prophet forecasting model with updated seasonality",
    type="custom_model"
)
registered_model = ml_client.models.create_or_update(model)
print(f"Registered: {registered_model.name} version {registered_model.version}")
```

### Step 2: Deploy as REST Endpoint

```python
from azure.ai.ml.entities import ManagedOnlineEndpoint, ManagedOnlineDeployment

endpoint = ManagedOnlineEndpoint(name="forecasting-endpoint", auth_mode="key")
ml_client.online_endpoints.begin_create_or_update(endpoint).wait()

deployment = ManagedOnlineDeployment(
    name="forecasting-v3",
    endpoint_name="forecasting-endpoint",
    model=registered_model.id,
    instance_type="Standard_DS3_v2",
    instance_count=2
)
ml_client.online_deployments.begin_create_or_update(deployment).wait()
```

### Step 3: Validate Deployment

Run the validation suite before shifting traffic:

```bash
python scripts/validate_endpoint.py \
  --endpoint forecasting-endpoint \
  --deployment forecasting-v3 \
  --test-queries evals/validation_queries.json
```

Expected output: all test queries return 200, latency p99 < 500ms.

### Step 4: Traffic Shift

Start with 10% canary traffic. Monitor for 30 minutes before full cutover:

```python
ml_client.online_endpoints.begin_create_or_update(
    ManagedOnlineEndpoint(
        name="forecasting-endpoint",
        traffic={"forecasting-v3": 10, "forecasting-v2": 90}
    )
).wait()
```

After 30 minutes with no degradation, shift to 100%:

```python
ml_client.online_endpoints.begin_create_or_update(
    ManagedOnlineEndpoint(
        name="forecasting-endpoint",
        traffic={"forecasting-v3": 100}
    )
).wait()
```

## Rollback Procedure

### Immediate Rollback (P0/P1 incidents)

If the new deployment causes alerts, metric degradation, or errors:

```python
# Shift all traffic back to previous stable version immediately
ml_client.online_endpoints.begin_create_or_update(
    ManagedOnlineEndpoint(
        name="forecasting-endpoint",
        traffic={"forecasting-v2": 100, "forecasting-v3": 0}
    )
).wait()
print("Traffic shifted to v2. Monitor for 5 minutes before confirming stability.")
```

Then delete the bad deployment:

```bash
az ml online-deployment delete \
  --name forecasting-v3 \
  --endpoint-name forecasting-endpoint \
  --workspace-name <workspace> \
  --yes
```

### Verifying Rollback Success

Check the health endpoint and verify response latency returns to baseline:

```bash
curl -X GET https://forecasting-endpoint.inference.ml.azure.com/health \
  -H "Authorization: Bearer <key>"
# Expected: {"status": "healthy", "model_version": "forecasting-v2"}
```

Confirm alert resolution within 5 minutes. If alerts persist after rollback,
escalate — the issue may be upstream of the model.

## Post-Deployment Monitoring

After any deployment, monitor for 24 hours:

- Error rate < 0.1%
- P99 latency < 500ms
- False positive alert rate unchanged from baseline
- MLflow tracking shows consistent metric distribution
