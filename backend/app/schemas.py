from datetime import datetime

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DocumentResponse(BaseModel):
    id: str
    filename: str
    chunk_count: int
    size_bytes: int
    sha256: str
    created_at: datetime


class UploadResponse(BaseModel):
    document: DocumentResponse
    message: str


class DeleteDocumentResponse(BaseModel):
    document_id: str
    filename: str
    message: str


class DeleteAllDocumentsResponse(BaseModel):
    deleted_count: int
    filenames: list[str]
    message: str


class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)


class SourceSnippet(BaseModel):
    citation: str
    document_id: str
    filename: str
    page: int | None = None
    chunk: int
    snippet: str
    score: float | None = None


class AnswerResponse(BaseModel):
    answer: str
    sources: list[SourceSnippet]
    provider: str
    model: str


class AuditLogResponse(BaseModel):
    id: int
    username: str
    uploaded_files: list[str]
    question: str
    response_summary: str
    status: str
    source_count: int
    created_at: datetime
