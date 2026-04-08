# Runbook: Alert Fatigue & Anomaly Detection Tuning

## Overview

This runbook covers procedures for diagnosing and reducing alert fatigue
in the time-series forecasting and anomaly detection platform, including
tuning Prophet models and signal smoothing strategies.

## Symptoms of Alert Fatigue

- On-call engineers acknowledging alerts without investigation
- False positive rate > 30% over a 7-day rolling window
- Multiple alerts firing simultaneously for the same root cause
- Alerts resolving without any engineer action within 5 minutes

## Diagnosing False Positives

### Step 1: Review Alert History

Pull the last 7 days of alerts and categorize by resolution type:

```sql
SELECT alert_id, service, resolved_by, resolution_time_minutes
FROM alerts
WHERE fired_at > NOW() - INTERVAL 7 DAY
  AND resolved_by = 'auto'
  AND resolution_time_minutes < 5
ORDER BY fired_at DESC;
```

Auto-resolved alerts under 5 minutes are strong false positive candidates.

### Step 2: Check Prophet Confidence Intervals

If Prophet's uncertainty interval is too narrow, legitimate variance triggers
alerts. Review the model configuration:

```python
model = Prophet(
    interval_width=0.95,       # increase from 0.80 to reduce false positives
    changepoint_prior_scale=0.05,  # lower = less sensitive to trend changes
    seasonality_prior_scale=10.0
)
```

Widening `interval_width` from 0.80 to 0.95 typically reduces false positives
by 20–40% for services with high natural variance.

### Step 3: Apply Signal Smoothing

Before feeding metrics into the forecasting model, apply a rolling average to
reduce noise from transient spikes:

```python
import pandas as pd

df['value_smoothed'] = df['value'].rolling(window=5, min_periods=1).mean()
```

Use a 5-minute window for high-frequency metrics, 15-minute for lower-frequency.

## Tuning Alert Thresholds

### Suppression Windows

For non-critical services, add a suppression window to prevent flapping:

- Minimum alert duration before firing: **5 minutes**
- Cooldown after resolution: **10 minutes**
- Maximum alert frequency: **1 per 30 minutes per service**

Configure in the alerting system:

```yaml
alert:
  name: forecasting_anomaly
  condition: predicted_vs_actual_delta > threshold
  for: 5m
  labels:
    severity: warning
  annotations:
    suppress_for: 10m
```

### Per-Service Thresholds

High-variance services (e.g., batch ingestion pipelines) need wider thresholds:

| Service | Default Threshold | Recommended Threshold |
|---|---|---|
| forecasting-service | 2.0 sigma | 2.5 sigma |
| metric-aggregator | 2.0 sigma | 3.0 sigma |
| hive-ingestion-pipeline | 2.0 sigma | 3.5 sigma |

## Model Retraining Triggers

Retrain Prophet models when:

1. False positive rate exceeds 35% for 3+ consecutive days
2. A significant traffic pattern change occurs (new product launch, etc.)
3. Seasonal patterns shift (e.g., daylight saving time, holiday periods)

Trigger retraining via the pipeline API:

```bash
curl -X POST http://forecasting-service/retrain \
  -H "Content-Type: application/json" \
  -d '{"service": "metric-aggregator", "lookback_days": 90}'
```

## Escalation

If alert fatigue is systemic (affecting 5+ services), schedule a postmortem
within 48 hours to review the alerting strategy with the platform team.
