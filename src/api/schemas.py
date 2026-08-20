from __future__ import annotations

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    saved_files: list[str]


class StoredFileInfo(BaseModel):
    name: str
    path: str
    size: int


class StoredFilesResponse(BaseModel):
    files: list[StoredFileInfo]


class ImportRequest(BaseModel):
    file_paths: list[str] | None = Field(default=None, description="Selected files to import. None scans configured data_path.")
    reset: bool = False
    reindex: bool = False


class ImportResponse(BaseModel):
    total: int
    loaded: int
    skipped: int
    failed: int


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    session_id: str = Field(default="default", min_length=1, max_length=128)


class ChatResponse(BaseModel):
    answer: str


class HealthResponse(BaseModel):
    status: str