from pydantic import BaseModel, Field
from datetime import datetime


class DocumentInfo(BaseModel):
    id: str
    filename: str
    original_filename: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    total: int
    items: list[DocumentInfo]


class ChunkInfo(BaseModel):
    id: str
    content: str
    chunk_index: int
    title: str
    source: str


class DocumentChunksResponse(BaseModel):
    document: DocumentInfo
    chunks: list[ChunkInfo]


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchResult(BaseModel):
    content: str
    source: str
    title: str
    document_id: str
    chunk_index: int
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
