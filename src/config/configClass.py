from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _getenv(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip()


def _get_int(name: str, default: int) -> int:
    value = _getenv(name)
    if value is None or value.lower() == "none":
        return default
    return int(value)


def _get_float_or_none(name: str) -> Optional[float]:
    value = _getenv(name)
    if value is None or value.lower() == "none":
        return None
    return float(value)


def _get_str_or_none(name: str) -> Optional[str]:
    value = _getenv(name)
    if value is None or value.lower() == "none":
        return None
    return value


def _get_list(name: str, default: list[str]) -> list[str]:
    value = _getenv(name)
    if value is None:
        return default

    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return default

    if isinstance(parsed, (list, tuple)):
        return [str(item) for item in parsed]
    return default


@dataclass
class ChatModelInfo:
    model_name: str
    api_key: Optional[str]
    temperature: float = 0
    max_tokens: Optional[int] = None
    timeout: Optional[float] = None
    max_retries: int = 0


@dataclass
class VectorStoreServiceInfo:
    embedding_model_name: str
    api_key: Optional[str]
    collection_name: str
    k: int
    persist_directory: str
    data_path: str
    md5_hex_store: str
    allow_knowledge_file_type: list[str]
    chunk_size: int
    chunk_overlap: int
    separators: list[str] = field(default_factory=list)


@dataclass
class PromptInfo:
    main_prompt_path: str
    rag_prompt_path: str


@dataclass
class AgentInfo:
    external_data_path: str


class Configer:
    def __init__(self):
        self.chatModelInfo = self.loadChatModelInfo()
        self.vectorStoreServiceInfo = self.loadVectorStoreServiceInfo()
        self.promptInfo = self.loadPromptInfo()
        self.agentInfo = self.loadAgentInfo()

    def loadChatModelInfo(self) -> ChatModelInfo:
        max_tokens = _getenv("MAX_TOKENS", "1200")
        return ChatModelInfo(
            model_name=_getenv("DEEPSEEK_MODEL_NAME", "deepseek-chat"),
            api_key=_getenv("DEEPSEEK_API_KEY"),
            temperature=float(_getenv("TEMPERATURE", "0")),
            max_tokens=None if max_tokens is None or max_tokens.lower() == "none" else int(max_tokens),
            timeout=_get_float_or_none("TIMEOUT"),
            max_retries=_get_int("MAX_RETRIES", 0),
        )

    def loadVectorStoreServiceInfo(self) -> VectorStoreServiceInfo:
        return VectorStoreServiceInfo(
            embedding_model_name=_getenv("embedding_model_name", "text-embedding-v4"),
            api_key=_getenv("DashScopeAPI"),
            collection_name=_getenv("collection_name", "RAG"),
            k=_get_int("k", 3),
            persist_directory=_getenv("persist_directory", "chroma_db"),
            data_path=_getenv("data_path", "data/papers"),
            md5_hex_store=_getenv("md5_hex_store", "md5.text"),
            allow_knowledge_file_type=_get_list("allow_knowledge_file_type", ["txt", "pdf"]),
            chunk_size=_get_int("chunk_size", 1200),
            chunk_overlap=_get_int("chunk_overlap", 250),
            separators=_get_list(
                "separators",
                ["\n\n", "\n", ".", "!", "?", "\u3002", "\uff1b", "\uff0c", " ", ""],
            ),
        )

    def loadPromptInfo(self) -> PromptInfo:
        return PromptInfo(
            main_prompt_path=_getenv("main_prompt_path", "prompts/main_prompt.txt"),
            rag_prompt_path=_getenv("rag_summarize_prompt_path", _getenv("rag_prompt_path", "prompts/rag.txt")),
        )

    def loadAgentInfo(self) -> AgentInfo:
        return AgentInfo(
            external_data_path=_getenv("external_data_path", "data/external/records.csv"),
        )

    def getChatModelInfo(self) -> ChatModelInfo:
        return self.chatModelInfo

    def getVectorStoreServiceInfo(self) -> VectorStoreServiceInfo:
        return self.vectorStoreServiceInfo

    def getPromptInfo(self) -> PromptInfo:
        return self.promptInfo

    def getAgentInfo(self) -> AgentInfo:
        return self.agentInfo


configer = Configer()
