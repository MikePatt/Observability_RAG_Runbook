## Deploy Guide

### Local

1. Copy `.env.example` to `.env`
2. Set `OPENAI_API_KEY`
3. Run `python server.py`

### Docker

1. Copy `.env.example` to `.env`
2. Set `OPENAI_API_KEY`
3. Run `docker compose up --build`

### Production recommendations

- Store API keys in a secret manager.
- Inject secrets as environment variables at runtime.
- Set `APP_ENV=prod` and `ENABLE_DOCS=false`.
- Put the service behind a reverse proxy with TLS.
- Scrape `/metrics` from Prometheus.