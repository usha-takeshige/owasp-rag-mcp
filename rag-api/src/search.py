from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.embedder import Embedder
from src.schemas import RequirementDetail, RequirementResult, SearchResponse

COLLECTION_MAP = {
    "ASVS": "asvs_requirements",
    "AISVS": "aisvs_requirements",
}
VALID_STANDARDS = set(COLLECTION_MAP)
VALID_LEVELS = {1, 2, 3}


def build_filter(level: int | None) -> Filter | None:
    if level is None:
        return None
    return Filter(must=[FieldCondition(key="level", match=MatchValue(value=level))])


def _hits_to_results(hits: list[Any]) -> list[RequirementResult]:
    results = []
    for hit in hits:
        p = hit.payload
        results.append(RequirementResult(
            req_id=p["req_id"],
            standard=p["standard"],
            version=p["version"],
            level=p["level"],
            chapter_id=p["chapter_id"],
            chapter_name=p["chapter_name"],
            section_id=p["section_id"],
            section_name=p["section_name"],
            description=p["description"],
            score=hit.score,
        ))
    return results


def _search_collection(
    client: QdrantClient,
    collection_name: str,
    query_vector: list[float],
    query_filter: Filter | None,
    top_k: int,
) -> list[RequirementResult]:
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
        with_payload=True,
    )
    return _hits_to_results(response.points)


def search(
    client: QdrantClient,
    embedder: Embedder,
    query: str,
    standard: str | None,
    level: int | None,
    top_k: int,
) -> SearchResponse:
    query_vector = embedder.encode(f"query: {query}")
    query_filter = build_filter(level)

    if standard is not None:
        collection = COLLECTION_MAP[standard]
        results = _search_collection(client, collection, query_vector, query_filter, top_k)
    else:
        all_results: list[RequirementResult] = []
        for collection in COLLECTION_MAP.values():
            partial = _search_collection(client, collection, query_vector, query_filter, top_k)
            all_results.extend(partial)
        all_results.sort(key=lambda r: r.score, reverse=True)
        results = all_results[:top_k]

    return SearchResponse(results=results, total=len(results), query=query)


def get_requirement(
    client: QdrantClient,
    standard: str,
    req_id: str,
) -> RequirementDetail | None:
    collection = COLLECTION_MAP[standard]
    points, _ = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(
            must=[FieldCondition(key="req_id", match=MatchValue(value=req_id))]
        ),
        limit=1,
        with_payload=True,
        with_vectors=False,
    )
    if not points:
        return None
    p = points[0].payload
    assert p is not None
    return RequirementDetail(
        req_id=p["req_id"],
        standard=p["standard"],
        version=p["version"],
        level=p["level"],
        chapter_id=p["chapter_id"],
        chapter_name=p["chapter_name"],
        section_id=p["section_id"],
        section_name=p["section_name"],
        description=p["description"],
    )


def get_categories(
    client: QdrantClient,
    standard: str | None,
) -> dict[str, Any]:
    collections = (
        {standard: COLLECTION_MAP[standard]}
        if standard is not None
        else COLLECTION_MAP
    )

    standards_data: dict[str, Any] = {}
    for std, collection in collections.items():
        chapters: dict[str, Any] = {}
        version = ""
        offset = None

        while True:
            points, next_offset = client.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in points:
                p = point.payload
                assert p is not None
                if not version:
                    version = p.get("version", "")
                ch_id = p["chapter_id"]
                ch_name = p["chapter_name"]
                sec_id = p["section_id"]
                sec_name = p["section_name"]

                if ch_id not in chapters:
                    chapters[ch_id] = {"name": ch_name, "sections": {}}
                sections = chapters[ch_id]["sections"]
                if sec_id not in sections:
                    sections[sec_id] = {"name": sec_name, "count": 0}
                sections[sec_id]["count"] += 1

            if next_offset is None:
                break
            offset = next_offset

        standards_data[std] = {"version": version, "chapters": chapters}

    return standards_data
