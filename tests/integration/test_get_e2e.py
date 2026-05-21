import httpx
import pytest


class TestGetRequirementE2E:
    @pytest.fixture(autouse=True)
    def _require_data(self, ingest_data):  # noqa: ARG002
        pass

    def test_get_existing_requirement(self, rag_client: httpx.Client):
        resp = rag_client.get("/requirement/ASVS/V1.1.1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["req_id"] == "V1.1.1"
        assert data["standard"] == "ASVS"

    def test_get_requirement_schema(self, rag_client: httpx.Client):
        resp = rag_client.get("/requirement/ASVS/V1.1.1")
        assert resp.status_code == 200
        data = resp.json()
        for field in (
            "req_id", "standard", "version", "level",
            "chapter_id", "chapter_name", "section_id", "section_name",
            "description",
        ):
            assert field in data, f"Missing field: {field}"

    def test_get_nonexistent_requirement_returns_404(self, rag_client: httpx.Client):
        resp = rag_client.get("/requirement/ASVS/V9.9.9")
        assert resp.status_code == 404

    def test_get_invalid_standard_returns_400(self, rag_client: httpx.Client):
        resp = rag_client.get("/requirement/MASVS/V1.1.1")
        assert resp.status_code == 400

    def test_get_aisvs_requirement(self, rag_client: httpx.Client):
        resp = rag_client.get("/requirement/AISVS/C1.1.1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["standard"] == "AISVS"
