from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient

from src.embedder import Embedder
from src.qdrant_client import get_client
from src.schemas import (
    CategoriesResponse,
    ChapterInfo,
    HealthResponse,
    RequirementDetail,
    SearchRequest,
    SearchResponse,
    SectionInfo,
    StandardInfo,
)
from src.search import (
    VALID_LEVELS,
    VALID_STANDARDS,
    get_categories,
    get_requirement,
    search,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.embedder = Embedder()
    app.state.qdrant = get_client()
    yield


app = FastAPI(lifespan=lifespan)


def _get_embedder(request: Request) -> Embedder:
    return request.app.state.embedder


def _get_qdrant(request: Request) -> QdrantClient:
    return request.app.state.qdrant


@app.post("/search", response_model=SearchResponse)
def search_endpoint(body: SearchRequest, request: Request) -> SearchResponse:
    if body.standard is not None and body.standard not in VALID_STANDARDS:
        raise HTTPException(status_code=400, detail=f"Invalid standard: {body.standard}")
    if body.level is not None and body.level not in VALID_LEVELS:
        raise HTTPException(status_code=400, detail=f"Invalid level: {body.level}")

    embedder = _get_embedder(request)
    client = _get_qdrant(request)

    try:
        return search(
            client=client,
            embedder=embedder,
            query=body.query,
            standard=body.standard,
            level=body.level,
            top_k=body.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail="Qdrant is unavailable") from e


@app.get("/requirement/{standard}/{req_id}", response_model=RequirementDetail)
def get_requirement_endpoint(standard: str, req_id: str, request: Request) -> RequirementDetail:
    if standard not in VALID_STANDARDS:
        raise HTTPException(status_code=400, detail=f"Invalid standard: {standard}")

    client = _get_qdrant(request)

    try:
        result = get_requirement(client, standard, req_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail="Qdrant is unavailable") from e

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Requirement '{req_id}' not found in {standard}",
        )
    return result


@app.get("/categories", response_model=CategoriesResponse)
def categories_endpoint(
    request: Request,
    standard: Annotated[str | None, Query()] = None,
) -> CategoriesResponse:
    if standard is not None and standard not in VALID_STANDARDS:
        raise HTTPException(status_code=400, detail=f"Invalid standard: {standard}")

    client = _get_qdrant(request)

    try:
        data = get_categories(client, standard)
    except Exception as e:
        raise HTTPException(status_code=503, detail="Qdrant is unavailable") from e

    standards_list = []
    for std, std_data in data.items():
        chapters_list = []
        total = 0
        for ch_id, ch_data in std_data["chapters"].items():
            sections_list = []
            for sec_id, sec_data in ch_data["sections"].items():
                sections_list.append(SectionInfo(
                    section_id=sec_id,
                    section_name=sec_data["name"],
                    count=sec_data["count"],
                ))
                total += sec_data["count"]
            chapters_list.append(ChapterInfo(
                chapter_id=ch_id,
                chapter_name=ch_data["name"],
                sections=sections_list,
            ))
        standards_list.append(StandardInfo(
            standard=std,
            version=std_data["version"],
            total_requirements=total,
            chapters=chapters_list,
        ))

    return CategoriesResponse(standards=standards_list)


@app.get("/health", response_model=HealthResponse)
def health_endpoint(request: Request) -> HealthResponse:
    embedder = _get_embedder(request)
    client = _get_qdrant(request)

    qdrant_status = "ok"
    try:
        client.get_collections()
    except Exception as e:
        qdrant_status = f"error: {e}"

    status = "ok" if qdrant_status == "ok" else "degraded"

    return HealthResponse(
        status=status,
        embedder=embedder.model_name,
        qdrant=qdrant_status,
    )
