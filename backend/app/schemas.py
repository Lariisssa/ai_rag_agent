from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class DocumentOut(BaseModel):
    id: str
    title: str
    page_count: int

class PageImageOut(BaseModel):
    id: str
    file_url: str
    position: Optional[dict] = None
    dimensions: Optional[dict] = None

class DocumentPageOut(BaseModel):
    id: str
    document_id: str
    page_number: int
    content: Optional[str] = None
    images: List[PageImageOut] = Field(default_factory=list)

class UploadResponse(BaseModel):
    documents: List[DocumentOut]

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    document_ids: Optional[List[str]] = None
    force_web: Optional[bool] = False

class Citation(BaseModel):
    kind: Literal["doc","web"]
    doc_id: Optional[str] = None
    title: Optional[str] = None
    page: Optional[int] = None
    url: Optional[str] = None

class SourceDocItem(BaseModel):
    doc_id: str
    title: str
    page: int
    similarity: float
    snippet: str

class SourcesEnvelope(BaseModel):
    type: Literal["doc","web"]
    items: List[SourceDocItem] = Field(default_factory=list)

class FinalEnvelope(BaseModel):
    citations: List[Citation]
    sources: SourcesEnvelope
