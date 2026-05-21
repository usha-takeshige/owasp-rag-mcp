from unittest.mock import MagicMock, patch

import pytest

from src.rag_client import RagApiError, RagClient


def _make_response(status_code: int, json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = str(json_data)
    resp.raise_for_status = MagicMock()
    return resp


def _make_client_ctx(response: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.post.return_value = response
    mock_client.get.return_value = response
    return mock_client


class TestSearch:
    def test_search_sends_correct_post_request(self):
        resp = _make_response(200, {"results": [], "total": 0, "query": "test"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            client.search("test query", standard="ASVS", level=1, top_k=5)

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == "http://test-api/search"
        body = call_kwargs[1]["json"]
        assert body["query"] == "test query"
        assert body["standard"] == "ASVS"
        assert body["level"] == 1
        assert body["top_k"] == 5

    def test_search_omits_none_fields(self):
        resp = _make_response(200, {"results": [], "total": 0, "query": "test"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            client.search("test query", standard=None, level=None, top_k=5)

        body = mock_client.post.call_args[1]["json"]
        assert "standard" not in body
        assert "level" not in body

    def test_search_400_raises_invalid_params(self):
        resp = _make_response(400, {"detail": "Invalid standard"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            with pytest.raises(RagApiError) as exc_info:
                client.search("test", standard=None, level=None, top_k=5)

        assert exc_info.value.code == -32602

    def test_search_404_raises_invalid_params(self):
        resp = _make_response(404, {"detail": "Not found"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            with pytest.raises(RagApiError) as exc_info:
                client.search("test", standard=None, level=None, top_k=5)

        assert exc_info.value.code == -32602

    def test_search_503_raises_internal_error(self):
        resp = _make_response(503, {"detail": "Qdrant down"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            with pytest.raises(RagApiError) as exc_info:
                client.search("test", standard=None, level=None, top_k=5)

        assert exc_info.value.code == -32603

    def test_search_connection_error_raises_internal_error(self):
        mock_client = _make_client_ctx(MagicMock())
        mock_client.post.side_effect = ConnectionError("refused")

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            with pytest.raises(RagApiError) as exc_info:
                client.search("test", standard=None, level=None, top_k=5)

        assert exc_info.value.code == -32603


class TestGetRequirement:
    def test_get_requirement_correct_url(self):
        resp = _make_response(200, {"req_id": "V1.1.1", "standard": "ASVS"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            client.get_requirement("ASVS", "V1.1.1")

        mock_client.get.assert_called_once()
        url = mock_client.get.call_args[0][0]
        assert url == "http://test-api/requirement/ASVS/V1.1.1"

    def test_get_requirement_404_raises_invalid_params(self):
        resp = _make_response(404, {"detail": "Not found"})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            with pytest.raises(RagApiError) as exc_info:
                client.get_requirement("ASVS", "V9.9.9")

        assert exc_info.value.code == -32602


class TestGetCategories:
    def test_get_categories_no_standard(self):
        resp = _make_response(200, {"standards": []})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            client.get_categories(standard=None)

        call_kwargs = mock_client.get.call_args[1]
        assert call_kwargs.get("params") == {}

    def test_get_categories_with_standard(self):
        resp = _make_response(200, {"standards": []})
        mock_client = _make_client_ctx(resp)

        with patch("src.rag_client.httpx.Client", return_value=mock_client):
            client = RagClient(base_url="http://test-api")
            client.get_categories(standard="ASVS")

        call_kwargs = mock_client.get.call_args[1]
        assert call_kwargs["params"] == {"standard": "ASVS"}
