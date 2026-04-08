## Decision Log

### ADR-001: FAISS for retrieval

Chosen for local simplicity and no external infra requirement in interview setting.
Trade-off: no multi-node scaling without migration.

### ADR-002: FastAPI for serving

Chosen for strong typing, OpenAPI docs, and production middleware ecosystem.
Trade-off: synchronous query path can be CPU-bound under heavy load.

### ADR-003: Env-driven config with validation

Chosen to enforce fail-fast startup and clean separation of code vs secrets.
Trade-off: requires strong deploy discipline around secret injection.