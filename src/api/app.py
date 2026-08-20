from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from src.RAG.ragService import RagService
from src.RAG.vectorStoreService import VectorStoreService
from src.agent.react_agent import MainAgent
from src.agent.tools.middleware import AgentBudgetExceeded
from src.agent.tools.rag_tool import clear_rag_tool_cache
from src.api.schemas import (
    ChatRequest,
    ChatResponse,
    HealthResponse,
    ImportRequest,
    ImportResponse,
    StoredFileInfo,
    StoredFilesResponse,
    UploadResponse,
)
from src.config.configClass import configer
from src.utils.path_tool import get_abs_path


UPLOAD_DIR = Path(get_abs_path("data/uploads"))
ALLOWED_SUFFIXES = {f".{suffix.lower().lstrip('.')}" for suffix in configer.getVectorStoreServiceInfo().allow_knowledge_file_type}

app = FastAPI(title="RAGAgent API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    return RagService(get_vector_store())


@lru_cache(maxsize=1)
def get_agent() -> MainAgent:
    return MainAgent()


def refresh_rag_service() -> None:
    get_rag_service.cache_clear()
    get_agent.cache_clear()
    clear_rag_tool_cache()


def format_runtime_error(exc: Exception) -> str:
    message = str(exc)
    if isinstance(exc, AgentBudgetExceeded):
        return "Agent tool budget exceeded. This turn was stopped to prevent repeated tool calls and token waste. Please narrow the request or choose one candidate explicitly."
    if "Insufficient Balance" in message or "Error code: 402" in message:
        return (
            "Model provider balance is insufficient. The Agent must call the chat model "
            "before it can decide which tool to use. Check the account balance for "
            "DEEPSEEK_API_KEY or switch to an available model."
        )
    return message


def safe_uploaded_name(filename: str) -> str:
    name = Path(filename).name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")
    return name


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@app.get("/files", response_model=StoredFilesResponse)
def list_files() -> StoredFilesResponse:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    files = [
        StoredFileInfo(name=path.name, path=str(path), size=path.stat().st_size)
        for path in sorted(UPLOAD_DIR.iterdir())
        if path.is_file() and path.suffix.lower() in ALLOWED_SUFFIXES
    ]
    return StoredFilesResponse(files=files)


@app.post("/files/upload", response_model=UploadResponse)
async def upload_files(files: list[UploadFile] = File(...)) -> UploadResponse:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved_files: list[str] = []

    for file in files:
        original_name = safe_uploaded_name(file.filename or "uploaded")
        data = await file.read()
        if not data:
            raise HTTPException(status_code=400, detail=f"Empty file: {original_name}")

        source = Path(original_name)
        digest = hashlib.md5(data).hexdigest()[:10]
        target = UPLOAD_DIR / f"{source.stem}_{digest}{source.suffix.lower()}"
        target.write_bytes(data)
        saved_files.append(str(target))

    return UploadResponse(saved_files=saved_files)


@app.post("/knowledge/import", response_model=ImportResponse)
def import_knowledge(request: ImportRequest) -> ImportResponse:
    stats = get_vector_store().load_document(
        file_paths=request.file_paths,
        reset=request.reset,
        reindex=request.reindex,
    )
    refresh_rag_service()
    return ImportResponse(**stats)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        answer = get_agent().execute(request.query, request.session_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=format_runtime_error(exc)) from exc
    return ChatResponse(answer=answer)


@app.post("/chat/stream")
def chat_stream(request: ChatRequest):
    def generate():
        try:
            yield from get_agent().execute_stream(request.query, request.session_id)
        except Exception as exc:
            yield f"\n[ERROR] {format_runtime_error(exc)}"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.post("/rag/chat", response_model=ChatResponse)
def rag_chat(request: ChatRequest) -> ChatResponse:
    try:
        answer = get_rag_service().rag_summarize(request.query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=format_runtime_error(exc)) from exc
    return ChatResponse(answer=answer)


@app.post("/rag/chat/stream")
def rag_chat_stream(request: ChatRequest):
    def generate():
        try:
            yield from get_rag_service().rag_summarize_stream(request.query)
        except Exception as exc:
            yield f"\n[ERROR] {format_runtime_error(exc)}"

    return StreamingResponse(generate(), media_type="text/plain; charset=utf-8")


@app.get("/retrieval/preview")
def retrieval_preview(query: str, limit: int = 8):
    docs = get_rag_service().retriever_docs(query)[:limit]
    return {
        "query": query,
        "results": [
            {
                "rank": index + 1,
                "metadata": doc.metadata,
                "content_preview": doc.page_content[:800],
            }
            for index, doc in enumerate(docs)
        ],
    }