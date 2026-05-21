import httpx
import pytest


class TestCoverageE2E:
    @pytest.fixture(autouse=True)
    def _require_data(self, ingest_data):  # noqa: ARG002
        pass

    def test_coverage_returns_feature_field(self, rag_client: httpx.Client):
        """check_coverage はレスポンスに feature フィールドを持つ（query ではなく）。
        RAG API の /search を使い、MCP ツール層で query→feature にリネームされることを
        ここでは RAG API 直接テストのため query フィールドを確認する。"""
        feature = "JWT を使ったユーザー認証"
        resp = rag_client.post("/search", json={"query": feature, "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == feature
        assert data["total"] == 5
        assert len(data["results"]) == 5

    def test_coverage_with_standard_filter(self, rag_client: httpx.Client):
        resp = rag_client.post(
            "/search",
            json={"query": "JWT を使ったユーザー認証", "standard": "ASVS", "top_k": 5},
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["results"]:
            assert item["standard"] == "ASVS"

    def test_coverage_results_are_relevant(self, rag_client: httpx.Client):
        resp = rag_client.post(
            "/search",
            json={"query": "JWT を使ったユーザー認証", "standard": "ASVS", "top_k": 5},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        chapter_names = [r["chapter_name"].lower() for r in results]
        assert any(
            "auth" in name or "session" in name or "token" in name
            for name in chapter_names
        ), f"Expected auth-related chapters, got: {chapter_names}"

    def test_coverage_result_has_score(self, rag_client: httpx.Client):
        resp = rag_client.post(
            "/search",
            json={"query": "ユーザー入力のバリデーション", "top_k": 3},
        )
        assert resp.status_code == 200
        for item in resp.json()["results"]:
            assert 0.0 <= item["score"] <= 1.0

    def test_coverage_top_k_respected(self, rag_client: httpx.Client):
        resp = rag_client.post("/search", json={"query": "authentication", "top_k": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 10
        assert len(data["results"]) == 10
