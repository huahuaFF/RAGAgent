from __future__ import annotations

import re
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import arxiv
from langchain_community.utilities import ArxivAPIWrapper
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from src.RAG.vectorStoreService import VectorStoreService
from src.config.configClass import configer
from src.utils.path_tool import get_abs_path


ARXIV_ID_RE = re.compile(r"^(?:[a-z-]+(?:\.[A-Z]{2})?/\d{7}|\d{4}\.\d{4,5})(?:v\d+)?$", re.IGNORECASE)
PLACEHOLDER_ID_RE = re.compile(r"x{2,}|\?", re.IGNORECASE)


@dataclass
class DownloadedArxivPaper:
    path: Path
    arxiv_id: str
    title: str
    pdf_url: str


class ArxivPaper(BaseModel):
    rank: int = Field(description="1-based rank in the search result list.")
    title: str
    arxiv_id: str
    abs_url: str
    pdf_url: str
    published: str | None = None
    published_first_time: str | None = None
    authors: str
    summary: str
    primary_category: str | None = None
    categories: list[str] = Field(default_factory=list)
    doi: str | None = None
    journal_ref: str | None = None


class ArxivSearchResult(BaseModel):
    query: str
    results: list[ArxivPaper]


@lru_cache(maxsize=1)
def get_vector_store() -> VectorStoreService:
    return VectorStoreService()


@tool(description="Search arXiv and return JSON candidates with exact arXiv IDs in results[].arxiv_id. Use this before downloading if the exact arXiv ID is not known.")
def arxiv_search(query: str) -> str:
    query = query.strip()
    if not query:
        return ArxivSearchResult(query=query, results=[]).model_dump_json()

    wrapper = ArxivAPIWrapper(
        top_k_results=5,
        load_max_docs=5,
        load_all_available_meta=True,
        doc_content_chars_max=4000,
    )
    documents = wrapper.load(query)
    papers = [_paper_from_arxiv_document(index, document.metadata) for index, document in enumerate(documents, start=1)]
    return ArxivSearchResult(query=query, results=papers).model_dump_json()


@tool(description="Download a single arXiv PDF by exact arXiv ID or arXiv URL. Do not call this with guessed or placeholder IDs.")
def arxiv_download(arxiv_id: str) -> str:
    paper = _download_arxiv_pdf(arxiv_id)
    return (
        f"Downloaded arXiv paper to {paper.path}\n"
        f"arXiv ID: {paper.arxiv_id}\n"
        f"Title: {paper.title}\n"
        f"PDF URL: {paper.pdf_url}"
    )


@tool(description="Download one exact arXiv PDF and immediately import it into the vector database. Use only with a real arXiv ID returned by arxiv_search or provided by the user.")
def arxiv_download_and_import(arxiv_id: str, reindex: bool = False) -> str:
    paper = _download_arxiv_pdf(arxiv_id)
    stats = get_vector_store().load_document(file_paths=[str(paper.path)], reindex=reindex)
    return (
        f"Downloaded arXiv paper to {paper.path}\n"
        f"arXiv ID: {paper.arxiv_id}\n"
        f"Title: {paper.title}\n"
        "Vector import finished: "
        f"total={stats['total']}, loaded={stats['loaded']}, "
        f"skipped={stats['skipped']}, failed={stats['failed']}"
    )


@tool(description="Import a local PDF or TXT paper file into the vector database. Use for an already downloaded or uploaded paper file.")
def import_paper_to_vector_store(file_path: str, reindex: bool = False) -> str:
    stats = get_vector_store().load_document(file_paths=[file_path], reindex=reindex)
    return (
        "Vector import finished: "
        f"total={stats['total']}, loaded={stats['loaded']}, "
        f"skipped={stats['skipped']}, failed={stats['failed']}"
    )


def _download_arxiv_pdf(arxiv_id: str) -> DownloadedArxivPaper:
    normalized_id = _normalize_arxiv_id(arxiv_id)
    result = _get_arxiv_result(normalized_id)
    pdf_url = result.pdf_url or f"https://arxiv.org/pdf/{normalized_id}.pdf"

    data_dir = Path(get_abs_path(configer.getVectorStoreServiceInfo().data_path))
    data_dir.mkdir(parents=True, exist_ok=True)
    target = data_dir / f"{_safe_filename(result.get_short_id())}.pdf"

    request = urllib.request.Request(pdf_url, headers={"User-Agent": "RAGAgent/0.1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        target.write_bytes(response.read())

    return DownloadedArxivPaper(
        path=target,
        arxiv_id=result.get_short_id(),
        title=result.title,
        pdf_url=pdf_url,
    )


def _get_arxiv_result(arxiv_id: str) -> arxiv.Result:
    client = arxiv.Client(page_size=1, delay_seconds=3.0, num_retries=3)
    search = arxiv.Search(id_list=[arxiv_id], max_results=1)
    result = next(client.results(search), None)
    if result is None:
        raise ValueError(f"No arXiv paper found for id: {arxiv_id}")
    return result


def _paper_from_arxiv_document(rank: int, metadata: dict) -> ArxivPaper:
    entry_id = str(metadata.get("entry_id") or "")
    arxiv_id = _extract_arxiv_id(entry_id)
    links = [str(link) for link in metadata.get("links", [])]
    abs_url = next((link for link in links if "/abs/" in link), entry_id or f"https://arxiv.org/abs/{arxiv_id}")
    pdf_url = next((link for link in links if "/pdf/" in link), f"https://arxiv.org/pdf/{arxiv_id}.pdf")
    categories = metadata.get("categories") or []
    if isinstance(categories, str):
        categories = [categories]

    return ArxivPaper(
        rank=rank,
        title=metadata.get("Title") or "",
        arxiv_id=arxiv_id,
        abs_url=abs_url,
        pdf_url=pdf_url,
        published=str(metadata.get("Published")) if metadata.get("Published") else None,
        published_first_time=str(metadata.get("published_first_time")) if metadata.get("published_first_time") else None,
        authors=metadata.get("Authors") or "",
        summary=" ".join((metadata.get("Summary") or "").split()),
        primary_category=metadata.get("primary_category"),
        categories=categories,
        doi=metadata.get("doi"),
        journal_ref=metadata.get("journal_ref"),
    )


def _extract_arxiv_id(entry_id: str) -> str:
    value = entry_id.strip()
    value = value.replace("https://arxiv.org/abs/", "")
    value = value.replace("http://arxiv.org/abs/", "")
    return value.strip(" /")


def _normalize_arxiv_id(value: str) -> str:
    value = value.strip()
    value = value.replace("https://arxiv.org/abs/", "")
    value = value.replace("http://arxiv.org/abs/", "")
    value = value.replace("https://arxiv.org/pdf/", "")
    value = value.replace("http://arxiv.org/pdf/", "")
    if value.endswith(".pdf"):
        value = value[:-4]
    value = value.strip(" /")

    if not value or PLACEHOLDER_ID_RE.search(value) or not ARXIV_ID_RE.match(value):
        raise ValueError(
            "Invalid or non-exact arXiv id. Use arxiv_search first and pass an exact ID like 2210.02747v2."
        )
    return value


def _safe_filename(arxiv_id: str) -> str:
    return arxiv_id.replace("/", "_").replace("\\", "_")