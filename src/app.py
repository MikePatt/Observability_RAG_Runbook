from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from contextlib import asynccontextmanager
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.logging_utils import configure_logging
from src.metrics import query_latency_seconds, request_counter, router as metrics_router
from src.middleware.request_id import RequestIdMiddleware
from src.pipeline import initialize_pipeline, query
from src.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
configure_logging(settings.log_level)

rag_chain = None


class QueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class QueryResponse(BaseModel):
    question: str
    answer: str
    sources: list[str]
    num_chunks_retrieved: int


@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain
    logger.info("initializing_rag_pipeline")
    rag_chain = initialize_pipeline(
        force_rebuild=settings.force_rebuild,
        persist_path=settings.persist_path,
        model=settings.openai_model,
        embedding_model=settings.embedding_model,
        top_k=settings.top_k,
    )
    logger.info("pipeline_ready")
    yield
    rag_chain = None


app = FastAPI(
    title=settings.app_name,
    description="Observability Runbook RAG Assistant",
    version=settings.app_version,
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)
app.include_router(metrics_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("unhandled_exception", extra={"request_id": getattr(request.state, "request_id", "unknown")})
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "Unexpected server error."}})


@app.get("/")
def root() -> dict[str, Any]:
    return {"name": settings.app_name, "docs": "/docs", "health": "/health", "query": "POST /query"}


@app.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "pipeline_ready": rag_chain is not None, "environment": settings.app_env}


@app.post("/query", response_model=QueryResponse)
def run_query(request: QueryRequest, raw_request: Request):
    if rag_chain is None:
        request_counter.labels(endpoint="query", status="503").inc()
        raise HTTPException(status_code=503, detail="RAG pipeline not initialized")

    question = request.question.strip()
    if not question:
        request_counter.labels(endpoint="query", status="400").inc()
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        with query_latency_seconds.time():
            with ThreadPoolExecutor(max_workers=1) as executor:
                result = executor.submit(query, rag_chain, question).result(timeout=settings.query_timeout_seconds)
        request_counter.labels(endpoint="query", status="200").inc()
        return QueryResponse(
            question=result["question"],
            answer=result["answer"],
            sources=result["sources"],
            num_chunks_retrieved=result["num_chunks_retrieved"],
        )
    except FuturesTimeoutError as exc:
        request_counter.labels(endpoint="query", status="504").inc()
        logger.warning("query_timeout", extra={"request_id": getattr(raw_request.state, "request_id", "unknown")})
        raise HTTPException(status_code=504, detail="Query timed out") from exc


if __name__ == "__main__":
    uvicorn.run("src.app:app", host=settings.host, port=settings.port, reload=settings.app_env != "prod")