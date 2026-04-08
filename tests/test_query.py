import pytest
from fastapi.testclient import TestClient

from src import app as app_module


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "rag_chain", object())

    def fake_query(_chain, question):
        return {
            "question": question,
            "answer": "grounded answer",
            "sources": ["oom-memory-incidents.md"],
            "num_chunks_retrieved": 4,
        }

    monkeypatch.setattr(app_module, "query", fake_query)
    return TestClient(app_module.app)


def test_query_success(client):
    response = client.post("/query", json={"question": "How to handle OOM?"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "grounded answer"
    assert body["num_chunks_retrieved"] == 4


def test_query_empty_question(client):
    response = client.post("/query", json={"question": "   "})
    assert response.status_code == 400