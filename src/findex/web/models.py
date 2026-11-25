from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    q: str = Field(min_length=1, max_length=200)
    k: int = Field(default=10, ge=1, le=100)
    scorer: Literal["bm25", "tfidf"] = "bm25"
    page: int = Field(default=1, ge=1)


class SearchResult(BaseModel):
    doc_id: int
    title: str
    score: float
    snippet: str


class SearchResponse(BaseModel):
    query: str
    total: int
    took_ms: float
    results: list[SearchResult]


class DocumentResponse(BaseModel):
    doc_id: int
    title: str
    path: str
    text: str


class StatsResponse(BaseModel):
    index_size: int
    doc_count: int
    vocabulary: int
    uptime: float


class HealthResponse(BaseModel):
    status: str
