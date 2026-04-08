## Architecture

`obs-rag` is a runbook-grounded RAG API for incident response.

- Ingestion: markdown runbooks from `runbooks/`
- Chunking: markdown header-aware + recursive chunking
- Retrieval: FAISS similarity search (`TOP_K` chunks)
- Generation: OpenAI chat model with strict grounding prompt
- Serving: FastAPI with request ID middleware and metrics endpoint

### Runtime flow

1. App starts and initializes or loads FAISS index.
2. `/query` validates input and executes retrieval + generation.
3. Response returns answer, source files, and chunk count.
4. `/metrics` exports Prometheus counters/histograms.

### Reliability controls

- Startup fails fast on invalid config.
- Query execution timeout (`QUERY_TIMEOUT_SECONDS`).
- Structured JSON logs and request IDs.