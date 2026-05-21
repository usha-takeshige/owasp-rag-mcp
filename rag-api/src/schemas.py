from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str
    standard: str | None = None
    level: int | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class RequirementResult(BaseModel):
    req_id: str
    standard: str
    version: str
    level: int
    chapter_id: str
    chapter_name: str
    section_id: str
    section_name: str
    description: str
    score: float


class SearchResponse(BaseModel):
    results: list[RequirementResult]
    total: int
    query: str


class RequirementDetail(BaseModel):
    req_id: str
    standard: str
    version: str
    level: int
    chapter_id: str
    chapter_name: str
    section_id: str
    section_name: str
    description: str


class SectionInfo(BaseModel):
    section_id: str
    section_name: str
    count: int


class ChapterInfo(BaseModel):
    chapter_id: str
    chapter_name: str
    sections: list[SectionInfo]


class StandardInfo(BaseModel):
    standard: str
    version: str
    total_requirements: int
    chapters: list[ChapterInfo]


class CategoriesResponse(BaseModel):
    standards: list[StandardInfo]


class HealthResponse(BaseModel):
    status: str
    embedder: str
    qdrant: str
