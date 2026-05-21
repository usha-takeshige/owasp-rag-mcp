from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


def _make_mock_embedder(model_name: str = "multilingual-e5-large") -> MagicMock:
    embedder = MagicMock()
    embedder.encode.return_value = [0.1] * 1024
    embedder.model_name = model_name
    embedder.vector_size = 1024
    return embedder


def _make_mock_qdrant() -> MagicMock:
    return MagicMock()


def _make_hit(req_id: str = "V1.1.1", standard: str = "ASVS", score: float = 0.9) -> MagicMock:
    hit = MagicMock()
    hit.score = score
    hit.payload = {
        "req_id": req_id,
        "standard": standard,
        "version": "5.0.0",
        "level": 1,
        "chapter_id": "V1",
        "chapter_name": "Encoding",
        "section_id": "V1.1",
        "section_name": "Encoding Arch",
        "description": "Verify that...",
    }
    return hit


@pytest.fixture
def client_pair():
    mock_embedder = _make_mock_embedder()
    mock_qdrant = _make_mock_qdrant()

    with (
        patch("src.main.Embedder", return_value=mock_embedder),
        patch("src.main.get_client", return_value=mock_qdrant),
    ):
        from src.main import app
        with TestClient(app) as c:
            yield c, mock_embedder, mock_qdrant


class TestHealth:
    def test_health_ok(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.get_collections.return_value = MagicMock()

        resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["qdrant"] == "ok"
        assert body["embedder"] == "multilingual-e5-large"

    def test_health_qdrant_error_returns_degraded(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.get_collections.side_effect = ConnectionError("refused")

        resp = client.get("/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "degraded"
        assert "error" in body["qdrant"]


class TestSearch:
    def test_search_returns_results(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.search.return_value = [_make_hit()]

        resp = client.post("/search", json={"query": "session management", "standard": "ASVS"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["query"] == "session management"
        assert body["results"][0]["req_id"] == "V1.1.1"

    def test_search_invalid_standard_returns_400(self, client_pair):
        client, _, _ = client_pair

        resp = client.post("/search", json={"query": "test", "standard": "MASVS"})

        assert resp.status_code == 400
        assert "Invalid standard" in resp.json()["detail"]

    def test_search_invalid_level_returns_400(self, client_pair):
        client, _, _ = client_pair

        resp = client.post("/search", json={"query": "test", "level": 5})

        assert resp.status_code == 400
        assert "Invalid level" in resp.json()["detail"]

    def test_search_top_k_out_of_range_returns_422(self, client_pair):
        client, _, _ = client_pair

        resp = client.post("/search", json={"query": "test", "top_k": 21})

        assert resp.status_code == 422

    def test_search_top_k_zero_returns_422(self, client_pair):
        client, _, _ = client_pair

        resp = client.post("/search", json={"query": "test", "top_k": 0})

        assert resp.status_code == 422

    def test_search_qdrant_error_returns_503(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.search.side_effect = ConnectionError("Qdrant down")

        resp = client.post("/search", json={"query": "test", "standard": "ASVS"})

        assert resp.status_code == 503


class TestGetRequirement:
    def test_found_returns_detail(self, client_pair):
        client, _, mock_qdrant = client_pair
        point = MagicMock()
        point.payload = _make_hit().payload
        mock_qdrant.scroll.return_value = ([point], None)

        resp = client.get("/requirement/ASVS/V1.1.1")

        assert resp.status_code == 200
        body = resp.json()
        assert body["req_id"] == "V1.1.1"
        assert body["standard"] == "ASVS"

    def test_not_found_returns_404(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.scroll.return_value = ([], None)

        resp = client.get("/requirement/ASVS/V9.9.9")

        assert resp.status_code == 404
        assert "V9.9.9" in resp.json()["detail"]

    def test_invalid_standard_returns_400(self, client_pair):
        client, _, _ = client_pair

        resp = client.get("/requirement/MASVS/V1.1.1")

        assert resp.status_code == 400
        assert "Invalid standard" in resp.json()["detail"]

    def test_qdrant_error_returns_503(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.scroll.side_effect = ConnectionError("Qdrant down")

        resp = client.get("/requirement/ASVS/V1.1.1")

        assert resp.status_code == 503


class TestCategories:
    def _make_scroll_page(self) -> tuple[list, None]:
        point = MagicMock()
        point.payload = {
            "req_id": "V1.1.1",
            "standard": "ASVS",
            "version": "5.0.0",
            "level": 1,
            "chapter_id": "V1",
            "chapter_name": "Encoding",
            "section_id": "V1.1",
            "section_name": "Encoding Arch",
            "description": "...",
        }
        return [point], None

    def test_categories_all_standards(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.scroll.return_value = self._make_scroll_page()

        resp = client.get("/categories")

        assert resp.status_code == 200
        body = resp.json()
        assert "standards" in body
        assert len(body["standards"]) == 2

    def test_categories_filtered_by_standard(self, client_pair):
        client, _, mock_qdrant = client_pair
        mock_qdrant.scroll.return_value = self._make_scroll_page()

        resp = client.get("/categories?standard=ASVS")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body["standards"]) == 1
        assert body["standards"][0]["standard"] == "ASVS"

    def test_categories_invalid_standard_returns_400(self, client_pair):
        client, _, _ = client_pair

        resp = client.get("/categories?standard=INVALID")

        assert resp.status_code == 400
