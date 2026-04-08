# Runbook: PySpark Pipeline Failures

## Overview

This runbook covers diagnosis and recovery procedures for failures in the
PySpark data pipeline that feeds time-series data from Hive tables into
the forecasting layer.

## Common Failure Modes

| Failure Type | Symptom | First Action |
|---|---|---|
| Executor OOM | Job fails with `ExecutorLostFailure` | Increase executor memory |
| Hive partition missing | Job fails at data read stage | Check partition completeness |
| Schema drift | `AnalysisException` on column read | Validate Hive schema |
| Shuffle spill | Job extremely slow, writing to disk | Increase `spark.shuffle.spill` buffer |
| Checkpoint timeout | Job hangs without progress | Check HDFS/S3 checkpoint path |

## Diagnosis Steps

### Step 1: Check Spark UI

Access the Spark history server to review the failed job:

```bash
kubectl port-forward svc/spark-history-server 18080:18080 -n pipelines
# Open http://localhost:18080 in browser
```

Look for:
- Failed stages (red)
- Executor memory usage over time
- GC time > 20% of task time (memory pressure signal)

### Step 2: Validate Hive Table Partitions

Before rerunning, verify all required partitions exist:

```sql
SHOW PARTITIONS observability.metrics_raw
WHERE dt >= DATE_SUB(CURRENT_DATE, 2);
```

If partitions are missing, check the upstream ingestion job. Do not rerun
the pipeline against incomplete data — it will produce incorrect forecasts.

### Step 3: Check Row Counts

Validate that partition row counts are within expected range:

```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("validation").getOrCreate()
df = spark.sql("SELECT dt, COUNT(*) as row_count FROM observability.metrics_raw GROUP BY dt ORDER BY dt DESC LIMIT 7")
df.show()

# Expected: ~50M-80M rows per day. Anything below 40M is suspicious.
```

## Recovery Procedures

### Executor OOM Fix

Increase executor memory in the job configuration:

```python
spark = SparkSession.builder \
    .config("spark.executor.memory", "8g") \      # was 4g
    .config("spark.executor.memoryFraction", "0.8") \
    .config("spark.sql.shuffle.partitions", "400") \  # increase for large datasets
    .getOrCreate()
```

### Re-triggering the Pipeline

After confirming data completeness, re-trigger the pipeline:

```bash
# Via Airflow DAG
airflow dags trigger obs_metrics_pipeline \
  --conf '{"execution_date": "2025-03-15", "force_rerun": true}'

# Or directly via spark-submit
spark-submit \
  --master k8s://https://<cluster-endpoint> \
  --deploy-mode cluster \
  --conf spark.executor.memory=8g \
  jobs/metrics_aggregation.py --date 2025-03-15
```

### Schema Drift Recovery

If a schema mismatch is detected:

1. Compare current Hive schema against the expected schema in the schema registry
2. If new columns were added upstream, update the pipeline to select explicitly:
   ```python
   df = spark.table("observability.metrics_raw").select("service", "metric_name", "value", "ts")
   ```
3. If columns were removed, escalate to the upstream team immediately — do not run

## Monitoring After Recovery

After a successful re-run:

- Verify row counts in the output Hive tables match expectations
- Check that the forecasting service picks up the new data (usually within 15 min)
- Confirm anomaly detection alerts return to normal frequency
- Add a note to the incident with the root cause and mitigation taken
