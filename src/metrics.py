from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from fastapi import APIRouter, Response

request_counter = Counter("obsrag_requests_total", "Total API requests", ["endpoint", "status"])
query_latency_seconds = Histogram("obsrag_query_latency_seconds", "Query endpoint latency")

router = APIRouter()


@router.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)