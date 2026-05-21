import asyncio
from unittest.mock import MagicMock, patch

import pytest

from mcp.shared.exceptions import McpError


def _make_search_response(query: str = "test") -> dict:
    return {
        "results": [
            {
                "req_id": "V1.1.1",
                "standard": "ASVS",
                "version": "5.0.0",
                "level": 1,
                "chapter_id": "V1",
                "chapter_name": "Encoding",
                "section_id": "V1.1",
                "section_name": "Encoding Arch",
                "description": "Verify that...",
                "score": 0.9,
            }
        ],
        "total": 1,
        "query": query,
    }


def _make_requirement_response() -> dict:
    return {
        "req_id": "V1.1.1",
        "standard": "ASVS",
        "version": "5.0.0",
        "level": 1,
        "chapter_id": "V1",
        "chapter_name": "Encoding",
        "section_id": "V1.1",
        "section_name": "Encoding Arch",
        "description": "Verify that...",
    }


class TestSearchRequirements:
    def test_invalid_standard_raises_mcp_error(self):
        from src.tools import search_requirements

        with pytest.raises(McpError) as exc_info:
            asyncio.run(search_requirements(query="test", standard="MASVS"))

        assert exc_info.value.error.code == -32602

    def test_invalid_level_raises_mcp_error(self):
        from src.tools import search_requirements

        with pytest.raises(McpError) as exc_info:
            asyncio.run(search_requirements(query="test", level=5))

        assert exc_info.value.error.code == -32602

    def test_top_k_too_large_raises_mcp_error(self):
        from src.tools import search_requirements

        with pytest.raises(McpError) as exc_info:
            asyncio.run(search_requirements(query="test", top_k=21))

        assert exc_info.value.error.code == -32602

    def test_calls_client_with_correct_args(self):
        mock_client = MagicMock()
        mock_client.search.return_value = _make_search_response("session")

        with patch("src.tools._client", mock_client):
            from src.tools import search_requirements
            result = asyncio.run(
                search_requirements(query="session", standard="ASVS", level=1, top_k=3)
            )

        mock_client.search.assert_called_once_with("session", "ASVS", 1, 3)
        assert result["total"] == 1

    def test_rag_api_error_converts_to_mcp_error(self):
        from src.rag_client import RagApiError
        from src.tools import search_requirements

        mock_client = MagicMock()
        mock_client.search.side_effect = RagApiError(-32603, "Qdrant down")

        with patch("src.tools._client", mock_client):
            with pytest.raises(McpError) as exc_info:
                asyncio.run(search_requirements(query="test"))

        assert exc_info.value.error.code == -32603


class TestGetRequirement:
    def test_invalid_standard_raises_mcp_error(self):
        from src.tools import get_requirement

        with pytest.raises(McpError) as exc_info:
            asyncio.run(get_requirement(req_id="V1.1.1", standard="MASVS"))

        assert exc_info.value.error.code == -32602

    def test_calls_client_with_correct_args(self):
        mock_client = MagicMock()
        mock_client.get_requirement.return_value = _make_requirement_response()

        with patch("src.tools._client", mock_client):
            from src.tools import get_requirement
            result = asyncio.run(get_requirement(req_id="V1.1.1", standard="ASVS"))

        mock_client.get_requirement.assert_called_once_with("ASVS", "V1.1.1")
        assert result["req_id"] == "V1.1.1"


class TestListCategories:
    def test_invalid_standard_raises_mcp_error(self):
        from src.tools import list_categories

        with pytest.raises(McpError) as exc_info:
            asyncio.run(list_categories(standard="INVALID"))

        assert exc_info.value.error.code == -32602

    def test_calls_client_with_standard(self):
        mock_client = MagicMock()
        mock_client.get_categories.return_value = {"standards": []}

        with patch("src.tools._client", mock_client):
            from src.tools import list_categories
            asyncio.run(list_categories(standard="ASVS"))

        mock_client.get_categories.assert_called_once_with("ASVS")

    def test_calls_client_without_standard(self):
        mock_client = MagicMock()
        mock_client.get_categories.return_value = {"standards": []}

        with patch("src.tools._client", mock_client):
            from src.tools import list_categories
            asyncio.run(list_categories())

        mock_client.get_categories.assert_called_once_with(None)


class TestCheckCoverage:
    def test_invalid_standard_raises_mcp_error(self):
        from src.tools import check_coverage

        with pytest.raises(McpError) as exc_info:
            asyncio.run(check_coverage(feature="auth", standard="INVALID"))

        assert exc_info.value.error.code == -32602

    def test_top_k_too_large_raises_mcp_error(self):
        from src.tools import check_coverage

        with pytest.raises(McpError) as exc_info:
            asyncio.run(check_coverage(feature="auth", top_k=51))

        assert exc_info.value.error.code == -32602

    def test_response_has_feature_instead_of_query(self):
        mock_client = MagicMock()
        mock_client.search.return_value = _make_search_response("auth feature")

        with patch("src.tools._client", mock_client):
            from src.tools import check_coverage
            result = asyncio.run(check_coverage(feature="auth feature"))

        assert "feature" in result
        assert "query" not in result
        assert result["feature"] == "auth feature"

    def test_calls_search_with_feature_as_query(self):
        mock_client = MagicMock()
        mock_client.search.return_value = _make_search_response("my feature")

        with patch("src.tools._client", mock_client):
            from src.tools import check_coverage
            asyncio.run(check_coverage(feature="my feature", standard="ASVS", top_k=15))

        mock_client.search.assert_called_once_with("my feature", "ASVS", None, 15)

    def test_default_top_k_is_10(self):
        mock_client = MagicMock()
        mock_client.search.return_value = _make_search_response("feat")

        with patch("src.tools._client", mock_client):
            from src.tools import check_coverage
            asyncio.run(check_coverage(feature="feat"))

        call_kwargs = mock_client.search.call_args
        assert call_kwargs[0][3] == 10
