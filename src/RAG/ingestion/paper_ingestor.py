from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from langchain_core.documents import Document

from src.utils.file_handler import get_file_md5_hex


SECTION_PATTERNS = [
    ("abstract", re.compile(r"^\s*(abstract)\s*$", re.IGNORECASE)),
    ("introduction", re.compile(r"^\s*(\d+\.?\s*)?introduction\s*$", re.IGNORECASE)),
    ("related_work", re.compile(r"^\s*(\d+\.?\s*)?(related work|background)\s*$", re.IGNORECASE)),
    ("method", re.compile(r"^\s*(\d+\.?\s*)?(method|methods|methodology|approach|model)\s*$", re.IGNORECASE)),
    ("experiment", re.compile(r"^\s*(\d+\.?\s*)?(experiment|experiments|experimental setup|evaluation)\s*$", re.IGNORECASE)),
    ("result", re.compile(r"^\s*(\d+\.?\s*)?(results|analysis|discussion)\s*$", re.IGNORECASE)),
    ("conclusion", re.compile(r"^\s*(\d+\.?\s*)?(conclusion|conclusions)\s*$", re.IGNORECASE)),
    ("references", re.compile(r"^\s*(references|bibliography)\s*$", re.IGNORECASE)),
]

PROTECTED_BLOCK_PATTERNS = [
    re.compile(r"^\s*(definition|theorem|lemma|proposition|corollary|proof|remark|example|assumption|algorithm)\b", re.IGNORECASE),
    re.compile(r"^\s*(equation|objective|loss function|optimization problem)\b", re.IGNORECASE),
]
MATH_TOKEN_RE = re.compile(r"(\\[A-Za-z]+|[=<>+\-*/^_{}\[\]()])")


@dataclass(frozen=True)
class PaperIngestionConfig:
    target_chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 1600
    drop_references: bool = True
    min_chunk_chars: int = 80


@dataclass(frozen=True)
class PageText:
    page_number: int
    text: str


class PaperIngestor:
    def __init__(self, config: PaperIngestionConfig | None = None):
        self.config = config or PaperIngestionConfig()

    def build_documents(self, file_path: str) -> list[Document]:
        path = Path(file_path)
        file_hash = get_file_md5_hex(str(path)) or ""
        suffix = path.suffix.lower()

        if suffix == ".pdf":
            pages = self._load_pdf_pages(path)
        elif suffix == ".txt":
            pages = self._load_txt_pages(path)
        else:
            return []

        chunks = self._chunk_pages(pages)
        documents: list[Document] = []
        chunk_index = 0
        for chunk in chunks:
            if len(chunk["text"].strip()) < self.config.min_chunk_chars:
                continue
            documents.append(
                Document(
                    page_content=chunk["text"].strip(),
                    metadata={
                        "source": str(path),
                        "file_name": path.name,
                        "file_hash": file_hash,
                        "chunk_index": chunk_index,
                        "page_start": chunk["page_start"],
                        "page_end": chunk["page_end"],
                        "section": chunk["section"],
                        "has_protected_block": chunk["has_protected_block"],
                    },
                )
            )
            chunk_index += 1
        return documents

    def _load_pdf_pages(self, path: Path) -> list[PageText]:
        try:
            import pymupdf
        except ImportError as exc:
            raise RuntimeError("PyMuPDF is required for paper PDF ingestion. Install dependency 'pymupdf'.") from exc

        pages: list[PageText] = []
        with pymupdf.open(path) as pdf:
            for page_index, page in enumerate(pdf):
                raw_text = page.get_text("text", sort=True)
                text = self._clean_text(raw_text)
                if text:
                    pages.append(PageText(page_number=page_index + 1, text=text))
        return pages

    def _load_txt_pages(self, path: Path) -> list[PageText]:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return [PageText(page_number=1, text=self._clean_text(text))]

    def _clean_text(self, text: str) -> str:
        text = text.replace("\x00", " ")
        text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if not self._is_noise_line(line)]
        return "\n".join(lines).strip()

    def _is_noise_line(self, line: str) -> bool:
        if not line:
            return False
        if re.fullmatch(r"\d+", line):
            return True
        if len(line) <= 3 and not any(ch.isalpha() for ch in line):
            return True
        return False

    def _chunk_pages(self, pages: Iterable[PageText]) -> list[dict]:
        chunks: list[dict] = []
        current_parts: list[str] = []
        current_page_start: int | None = None
        current_page_end: int | None = None
        current_section = "unknown"
        stopped_at_references = False

        for page in pages:
            if stopped_at_references:
                break

            blocks = self._split_page_to_blocks(page.text)
            for block in blocks:
                section = self._detect_section(block)
                if section == "references" and self.config.drop_references:
                    stopped_at_references = True
                    break
                if section:
                    if current_parts:
                        self._append_chunk(chunks, current_parts, current_page_start, current_page_end, current_section)
                        current_parts = []
                    current_section = section
                    continue

                block_len = len(block)
                current_len = len("\n\n".join(current_parts))
                protected = self._is_protected_block(block)
                should_flush = current_parts and current_len + block_len > self.config.target_chunk_size and not protected

                if should_flush:
                    self._append_chunk(chunks, current_parts, current_page_start, current_page_end, current_section)
                    current_parts = self._overlap_tail(current_parts)
                    current_page_start = page.page_number if not current_parts else current_page_start

                if block_len > self.config.max_chunk_size and not protected:
                    for part in self._split_long_block(block):
                        if current_parts and len("\n\n".join(current_parts)) + len(part) > self.config.target_chunk_size:
                            self._append_chunk(chunks, current_parts, current_page_start, current_page_end, current_section)
                            current_parts = self._overlap_tail(current_parts)
                        if not current_parts:
                            current_page_start = page.page_number
                        current_parts.append(part)
                        current_page_end = page.page_number
                else:
                    if not current_parts:
                        current_page_start = page.page_number
                    current_parts.append(block)
                    current_page_end = page.page_number

        if current_parts:
            self._append_chunk(chunks, current_parts, current_page_start, current_page_end, current_section)
        return chunks

    def _split_page_to_blocks(self, text: str) -> list[str]:
        blocks: list[str] = []
        for paragraph in re.split(r"\n\s*\n", text):
            lines = [line.strip() for line in paragraph.splitlines() if line.strip()]
            if not lines:
                continue

            merged: list[str] = []
            for line in lines:
                if self._detect_section(line):
                    if merged:
                        blocks.append(" ".join(merged).strip())
                        merged = []
                    blocks.append(line)
                else:
                    merged.append(line)
            if merged:
                blocks.append(" ".join(merged).strip())
        return blocks

    def _detect_section(self, text: str) -> str | None:
        normalized = text.strip()
        if len(normalized) > 80:
            return None
        normalized = normalized.rstrip(".:")
        for section, pattern in SECTION_PATTERNS:
            if pattern.match(normalized):
                return section
        return None

    def _is_protected_block(self, text: str) -> bool:
        if any(pattern.search(text) for pattern in PROTECTED_BLOCK_PATTERNS):
            return True

        math_tokens = MATH_TOKEN_RE.findall(text)
        if len(math_tokens) < 12:
            return False

        token_density = len(math_tokens) / max(len(text), 1)
        return token_density >= 0.04
    def _split_long_block(self, block: str) -> list[str]:
        sentences = re.split(r"(?<=[.!?])\s+", block)
        parts: list[str] = []
        current: list[str] = []
        for sentence in sentences:
            if current and len(" ".join(current)) + len(sentence) > self.config.target_chunk_size:
                parts.append(" ".join(current).strip())
                current = []
            current.append(sentence)
        if current:
            parts.append(" ".join(current).strip())
        return parts

    def _append_chunk(
        self,
        chunks: list[dict],
        parts: list[str],
        page_start: int | None,
        page_end: int | None,
        section: str,
    ) -> None:
        text = "\n\n".join(part.strip() for part in parts if part.strip()).strip()
        if not text:
            return
        chunks.append(
            {
                "text": text,
                "page_start": page_start or 1,
                "page_end": page_end or page_start or 1,
                "section": section,
                "has_protected_block": self._is_protected_block(text),
            }
        )

    def _overlap_tail(self, parts: list[str]) -> list[str]:
        if self.config.chunk_overlap <= 0:
            return []

        tail: list[str] = []
        total = 0
        for part in reversed(parts):
            total += len(part)
            tail.insert(0, part)
            if total >= self.config.chunk_overlap:
                break
        return tail