import httpx
import pytest


class TestSearchE2E:
    @pytest.fixture(autouse=True)
    def _require_data(self, ingest_data):  # noqa: ARG002
        pass

    def test_japanese_query_returns_results(self, rag_client: httpx.Client):
        resp = rag_client.post("/search", json={"query": "セッション管理", "top_k": 3})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
        assert data["query"] == "セッション管理"

    def test_search_with_standard_filter(self, rag_client: httpx.Client):
        resp = rag_client.post(
            "/search",
            json={"query": "セッション管理", "standard": "ASVS", "level": 1, "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        for item in data["results"]:
            assert item["standard"] == "ASVS"
            assert item["level"] == 1

    def test_search_result_schema(self, rag_client: httpx.Client):
        resp = rag_client.post("/search", json={"query": "input validation", "top_k": 1})
        assert resp.status_code == 200
        result = resp.json()["results"][0]
        for field in (
            "req_id", "standard", "version", "level",
            "chapter_id", "chapter_name", "section_id", "section_name",
            "description", "score",
        ):
            assert field in result, f"Missing field: {field}"

    def test_invalid_standard_returns_400(self, rag_client: httpx.Client):
        resp = rag_client.post("/search", json={"query": "test", "standard": "MASVS"})
        assert resp.status_code == 400

    def test_invalid_level_returns_400(self, rag_client: httpx.Client):
        resp = rag_client.post("/search", json={"query": "test", "level": 99})
        assert resp.status_code == 400

    def test_ingest_idempotency(self, rag_client: httpx.Client, ingest_data):  # noqa: ARG002
        resp1 = rag_client.post("/search", json={"query": "authentication", "top_k": 5})
        count_before = resp1.json()["total"]

        import os
        import subprocess
        from pathlib import Path

        project_root = Path(__file__).parent.parent.parent
        skip_docker = os.environ.get("INTEGRATION_NO_DOCKER", "").lower() in ("1", "true", "yes")

        if not skip_docker:
            subprocess.run(
                [
                    "docker", "compose",
                    "-f", "docker-compose.yml",
                    "-f", "docker-compose.test.yml",
                    "run", "--rm", "ingest",
                ],
                cwd=project_root,
                check=True,
                timeout=600,
            )

        resp2 = rag_client.post("/search", json={"query": "authentication", "top_k": 5})
        count_after = resp2.json()["total"]

        assert count_before == count_after, (
            f"Ingest is not idempotent: count changed from {count_before} to {count_after}"
        )
