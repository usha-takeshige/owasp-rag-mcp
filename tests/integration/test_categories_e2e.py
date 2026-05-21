import httpx
import pytest


class TestCategoriesE2E:
    @pytest.fixture(autouse=True)
    def _require_data(self, ingest_data):  # noqa: ARG002
        pass

    def test_list_all_categories(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert "standards" in data
        assert len(data["standards"]) >= 1

    def test_list_asvs_categories(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories", params={"standard": "ASVS"})
        assert resp.status_code == 200
        data = resp.json()
        standards = data["standards"]
        assert len(standards) == 1
        assert standards[0]["standard"] == "ASVS"

    def test_asvs_categories_contain_chapters(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories", params={"standard": "ASVS"})
        assert resp.status_code == 200
        asvs = resp.json()["standards"][0]
        chapter_ids = [ch["chapter_id"] for ch in asvs["chapters"]]
        assert "V1" in chapter_ids

    def test_categories_schema(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories", params={"standard": "ASVS"})
        assert resp.status_code == 200
        std = resp.json()["standards"][0]
        for field in ("standard", "version", "total_requirements", "chapters"):
            assert field in std, f"Missing field: {field}"
        ch = std["chapters"][0]
        for field in ("chapter_id", "chapter_name", "sections"):
            assert field in ch, f"Missing chapter field: {field}"
        sec = ch["sections"][0]
        for field in ("section_id", "section_name", "count"):
            assert field in sec, f"Missing section field: {field}"

    def test_invalid_standard_returns_400(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories", params={"standard": "INVALID"})
        assert resp.status_code == 400

    def test_total_requirements_matches_sum(self, rag_client: httpx.Client):
        resp = rag_client.get("/categories", params={"standard": "ASVS"})
        assert resp.status_code == 200
        std = resp.json()["standards"][0]
        section_sum = sum(
            sec["count"]
            for ch in std["chapters"]
            for sec in ch["sections"]
        )
        assert std["total_requirements"] == section_sum
