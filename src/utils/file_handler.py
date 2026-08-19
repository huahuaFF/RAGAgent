import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

from src.log.logger import logger


def get_file_md5_hex(filepath: str) -> str | None:
    path = Path(filepath)
    if not path.exists():
        logger.error("[md5] file does not exist: %s", filepath)
        return None

    if not path.is_file():
        logger.error("[md5] path is not a file: %s", filepath)
        return None

    md5_obj = hashlib.md5()
    try:
        with path.open("rb") as f:
            while chunk := f.read(4096):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except Exception as exc:
        logger.error("[md5] failed to calculate %s: %s", filepath, exc)
        return None


def listdir_with_allowed_type(path: str, allowed_types: tuple[str, ...]) -> tuple[str, ...]:
    data_dir = Path(path)
    if not data_dir.is_dir():
        logger.error("[listdir_with_allowed_type] path is not a directory: %s", path)
        return tuple()

    normalized_types = {item.lower().lstrip(".") for item in allowed_types}
    files = [
        str(file_path)
        for file_path in data_dir.rglob("*")
        if file_path.is_file() and file_path.suffix.lower().lstrip(".") in normalized_types
    ]
    return tuple(files)


def pdf_loader(filepath: str, passwd=None) -> list[Document]:
    return PyPDFLoader(filepath, passwd).load()


def txt_loader(filepath: str) -> list[Document]:
    return TextLoader(filepath, encoding="utf-8").load()
