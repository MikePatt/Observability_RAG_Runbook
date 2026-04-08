# obs-rag

Production-style Observability Runbook RAG Assistant for interview portfolios.

## Why this repo stands out

- Typed, validated runtime config (`src/settings.py`)
- FastAPI API with request ID middleware and structured error handling
- Prometheus metrics endpoint (`/metrics`)
- Query timeout guard for reliability
- Dockerized runtime and GitHub Actions CI
- Test suite for health/query behavior
- Architecture, deployment, operations, and decisions docs

## Quick start

```bash
python -m venv .venv
. .venv/Scripts/Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# set OPENAI_API_KEY in .env
python server.py
```

API docs: <http://localhost:8000/docs>

## Endpoints

- `GET /health`
- `GET /metrics`
- `POST /query`

## Test

```bash
pytest
```

## Docker

```bash
docker compose up --build
```

## Project docs

- `ARCHITECTURE.md`
- `DEPLOY.md`
- `RUNBOOK.md`
- `DECISIONS.md`