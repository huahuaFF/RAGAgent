from pathlib import Path
from typing import Sequence
from langchain_chroma import Chroma
from langchain_community.embeddings import DashScopeEmbeddings
from src.RAG.ingestion.paper_ingestor import PaperIngestionConfig, PaperIngestor
from src.config.configClass import configer
from src.log.logger import logger
from src.utils.file_handler import get_file_md5_hex, listdir_with_allowed_type
from src.utils.path_tool import get_abs_path


vector_info = configer.getVectorStoreServiceInfo()
embed_model = DashScopeEmbeddings(
    model=vector_info.embedding_model_name,
    dashscope_api_key=vector_info.api_key,
)


class VectorStoreService(object):
    def __init__(self):
        info = configer.getVectorStoreServiceInfo()
        self.vector_store = Chroma(
            collection_name=info.collection_name,
            embedding_function=embed_model,
            persist_directory=get_abs_path(info.persist_directory),
        )
        self.ingestor = PaperIngestor(
            PaperIngestionConfig(
                target_chunk_size=max(info.chunk_size, 1000),
                chunk_overlap=max(info.chunk_overlap, 200),
            )
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": max(configer.getVectorStoreServiceInfo().k, 8),
                "fetch_k": max(configer.getVectorStoreServiceInfo().k * 4, 24),
            },
        )

    def reset(self) -> None:
        self.vector_store.reset_collection()
        self._clear_md5_store()

    def load_document(
        self,
        file_paths: Sequence[str] | None = None,
        reset: bool = False,
        reindex: bool = False,
    ) -> dict[str, int]:
        if reset:
            self.reset()

        paths = self._resolve_load_paths(file_paths)
        stats = {"total": len(paths), "loaded": 0, "skipped": 0, "failed": 0}

        for path in paths:
            md5_hex = get_file_md5_hex(path)
            if not md5_hex:
                stats["failed"] += 1
                continue

            if reindex:
                self._delete_file_chunks(md5_hex)
                self._remove_md5_hex(md5_hex)
            elif self._check_md5_hex(md5_hex):
                logger.info("[load_document] skipped existing paper: %s", path)
                stats["skipped"] += 1
                continue

            try:
                documents = self.ingestor.build_documents(path)
                if not documents:
                    logger.warning("[load_document] no valid chunks built from file: %s", path)
                    stats["skipped"] += 1
                    continue

                self.vector_store.add_documents(documents)
                self._save_md5_hex(md5_hex)
                stats["loaded"] += 1
                logger.info("[load_document] loaded paper: %s chunks=%s", path, len(documents))
            except Exception as exc:
                stats["failed"] += 1
                logger.error("[load_document] failed to load %s: %s", path, exc, exc_info=True)
                continue

        return stats

    def _resolve_load_paths(self, file_paths: Sequence[str] | None) -> tuple[str, ...]:
        info = configer.getVectorStoreServiceInfo()
        allowed_types = tuple(info.allow_knowledge_file_type)

        if file_paths is None:
            return listdir_with_allowed_type(get_abs_path(info.data_path), allowed_types)

        normalized_types = {item.lower().lstrip(".") for item in allowed_types}
        resolved_paths: list[str] = []
        for file_path in file_paths:
            path = Path(file_path)
            if not path.is_absolute():
                path = Path(get_abs_path(str(path)))

            if not path.is_file():
                logger.warning("[load_document] selected path is not a file: %s", path)
                continue

            if path.suffix.lower().lstrip(".") not in normalized_types:
                logger.warning("[load_document] unsupported selected file type: %s", path)
                continue

            resolved_paths.append(str(path))

        return tuple(resolved_paths)

    def _delete_file_chunks(self, file_hash: str) -> None:
        try:
            self.vector_store.delete(where={"file_hash": file_hash})
        except Exception as exc:
            logger.warning("[load_document] failed to delete old chunks for hash=%s: %s", file_hash, exc)

    def _md5_store_path(self) -> Path:
        return Path(get_abs_path(configer.getVectorStoreServiceInfo().md5_hex_store))

    def _clear_md5_store(self) -> None:
        md5_store_path = self._md5_store_path()
        md5_store_path.parent.mkdir(parents=True, exist_ok=True)
        md5_store_path.write_text("", encoding="utf-8")

    def _check_md5_hex(self, md5_for_check: str | None) -> bool:
        if not md5_for_check:
            return False

        md5_store_path = self._md5_store_path()
        if not md5_store_path.exists():
            md5_store_path.parent.mkdir(parents=True, exist_ok=True)
            md5_store_path.touch()
            return False

        with md5_store_path.open("r", encoding="utf-8") as f:
            return any(line.strip() == md5_for_check for line in f)

    def _save_md5_hex(self, md5_for_check: str) -> None:
        if self._check_md5_hex(md5_for_check):
            return
        md5_store_path = self._md5_store_path()
        md5_store_path.parent.mkdir(parents=True, exist_ok=True)
        with md5_store_path.open("a", encoding="utf-8") as f:
            f.write(md5_for_check + "\n")

    def _remove_md5_hex(self, md5_for_remove: str) -> None:
        md5_store_path = self._md5_store_path()
        if not md5_store_path.exists():
            return
        lines = [
            line.strip()
            for line in md5_store_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and line.strip() != md5_for_remove
        ]
        md5_store_path.write_text(("\n".join(lines) + "\n") if lines else "", encoding="utf-8")