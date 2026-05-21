from unittest.mock import MagicMock

import pytest

from src.search import COLLECTION_MAP, build_filter, search, get_requirement


def _make_hit(payload: dict, score: float) -> MagicMock:
    hit = MagicMock()
    hit.payload = payload
    hit.score = score
    return hit


def _sample_payload(req_id: str = "V1.1.1", standard: str = "ASVS") -> dict:
    return {
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


class TestBuildFilter:
    def test_none_returns_none(self):
        assert build_filter(None) is None

    def test_level_returns_filter(self):
        f = build_filter(2)
        assert f is not None
        assert len(f.must) == 1
        assert f.must[0].key == "level"
        assert f.must[0].match.value == 2


class TestSearch:
    def _make_embedder(self) -> MagicMock:
        embedder = MagicMock()
        embedder.encode.return_value = [0.1] * 1024
        return embedder

    def test_search_single_standard(self):
        client = MagicMock()
        client.search.return_value = [_make_hit(_sample_payload(), score=0.9)]
        embedder = self._make_embedder()

        result = search(client, embedder, "query", standard="ASVS", level=None, top_k=5)

        client.search.assert_called_once()
        call_kwargs = client.search.call_args.kwargs
        assert call_kwargs["collection_name"] == "asvs_requirements"
        assert result.total == 1
        assert result.query == "query"
        assert result.results[0].req_id == "V1.1.1"

    def test_search_uses_query_prefix(self):
        client = MagicMock()
        client.search.return_value = []
        embedder = self._make_embedder()

        search(client, embedder, "test query", standard="ASVS", level=None, top_k=5)

        embedder.encode.assert_called_once_with("query: test query")

    def test_search_all_standards_merges_and_sorts(self):
        client = MagicMock()

        def side_effect(**kwargs):
            if kwargs["collection_name"] == "asvs_requirements":
                return [_make_hit(_sample_payload("V1.1.1", "ASVS"), score=0.8)]
            else:
                return [_make_hit(_sample_payload("C1.1.1", "AISVS"), score=0.95)]

        client.search.side_effect = side_effect
        embedder = self._make_embedder()

        result = search(client, embedder, "query", standard=None, level=None, top_k=5)

        assert client.search.call_count == 2
        assert result.total == 2
        assert result.results[0].score == 0.95
        assert result.results[1].score == 0.8

    def test_search_all_standards_top_k_truncates(self):
        client = MagicMock()

        def side_effect(**kwargs):
            return [
                _make_hit(_sample_payload(), score=0.9),
                _make_hit(_sample_payload(), score=0.8),
            ]

        client.search.side_effect = side_effect
        embedder = self._make_embedder()

        result = search(client, embedder, "query", standard=None, level=None, top_k=3)

        assert result.total == 3

    def test_search_with_level_filter(self):
        client = MagicMock()
        client.search.return_value = []
        embedder = self._make_embedder()

        search(client, embedder, "query", standard="ASVS", level=2, top_k=5)

        call_kwargs = client.search.call_args.kwargs
        assert call_kwargs["query_filter"] is not None


class TestGetRequirement:
    def test_found_returns_detail(self):
        client = MagicMock()
        point = MagicMock()
        point.payload = _sample_payload("V1.1.1", "ASVS")
        client.scroll.return_value = ([point], None)

        result = get_requirement(client, "ASVS", "V1.1.1")

        assert result is not None
        assert result.req_id == "V1.1.1"
        assert result.standard == "ASVS"

    def test_not_found_returns_none(self):
        client = MagicMock()
        client.scroll.return_value = ([], None)

        result = get_requirement(client, "ASVS", "V9.9.9")

        assert result is None

    def test_uses_correct_collection(self):
        client = MagicMock()
        point = MagicMock()
        point.payload = _sample_payload("C1.1.1", "AISVS")
        client.scroll.return_value = ([point], None)

        get_requirement(client, "AISVS", "C1.1.1")

        call_kwargs = client.scroll.call_args.kwargs
        assert call_kwargs["collection_name"] == "aisvs_requirements"
