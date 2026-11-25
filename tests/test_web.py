from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from findex.index import build_index
from findex.web.app import app
from findex.web.dependencies import get_index, get_settings
from findex.web.settings import Settings


@pytest.fixture
def client(tmp_path: Path):
    (tmp_path / "first.txt").write_text(
        "Python asyncio search engine",
        encoding="utf-8",
    )
    (tmp_path / "second.txt").write_text(
        "Python web application",
        encoding="utf-8",
    )
    index = build_index(tmp_path, with_positions=True)
    app.dependency_overrides[get_index] = lambda: index
    app.dependency_overrides[get_settings] = lambda: Settings(
        corpus_path=tmp_path,
    )
    app.state.documents = {
        str(tmp_path / "first.txt"): "Python asyncio search engine",
        str(tmp_path / "second.txt"): "Python web application",
    }
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        app.state.documents = {}


def test_search_success(client):
    response = client.get("/search", params={"q": "python"})
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["results"]) == 2
    assert "X-Request-ID" in response.headers


def test_search_pagination(client):
    first = client.get(
        "/search",
        params={"q": "python", "k": 1, "page": 1},
    )
    second = client.get(
        "/search",
        params={"q": "python", "k": 1, "page": 2},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["results"][0]["doc_id"] != second.json()["results"][0]["doc_id"]


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": ""},
        {"q": "python", "k": 0},
        {"q": "python", "k": 101},
        {"q": "python", "page": 0},
        {"q": "python", "scorer": "invalid"},
    ],
)
def test_search_validation(client, params):
    response = client.get("/search", params=params)
    assert response.status_code == 422


def test_document_success(client):
    response = client.get("/docs/1")
    assert response.status_code == 200
    assert response.json()["doc_id"] == 1
    assert response.json()["text"] == "Python asyncio search engine"


def test_document_not_found(client):
    response = client.get("/docs/99999")
    assert response.status_code == 404


def test_stats(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["doc_count"] == 2


def test_health_success(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_unavailable(monkeypatch):
    monkeypatch.setattr(
        app.state,
        "index",
        None,
        raising=False,
    )
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 503
