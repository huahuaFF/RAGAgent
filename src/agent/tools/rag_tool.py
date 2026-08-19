from langchain_core.tools import tool

from src.RAG.ragService import RagService


rag = RagService()


@tool(description="从已入库的论文资料中检索相关片段，并基于论文内容回答用户问题。")
def rag_summarize(query: str) -> str:
    return rag.rag_summarize(query)
