## Operations Runbook

### Health checks

- API health: `GET /health`
- Metrics: `GET /metrics`

### Common incidents

- `503 RAG pipeline not initialized`
  - Check startup logs for missing `OPENAI_API_KEY`
  - Ensure runbooks exist in `RUNBOOK_DIR`

- `504 Query timed out`
  - Increase `QUERY_TIMEOUT_SECONDS`
  - Reduce `TOP_K`
  - Check upstream model latency

### Recovery actions

- Force index rebuild:
  - Set `FORCE_REBUILD=true`
  - Restart service

- Rotate OpenAI key:
  - Update secret manager
  - Restart deployment