from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from src.RAG.ragService import RagService


@lru_cache(maxsize=1)
def get_rag_service() -> RagService:
    return RagService()


def clear_rag_tool_cache() -> None:
    get_rag_service.cache_clear()


@tool(description="Search the local imported paper knowledge base and answer using retrieved paper chunks. Use this for imported paper content, methods, formulas, experiments, and conclusions.")
def rag_summarize(query: str) -> str:
    return get_rag_service().rag_summarize(query)