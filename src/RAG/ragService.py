from collections.abc import Iterator

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from src.RAG.vectorStoreService import VectorStoreService
from src.model.chatModel import chatModel
from src.utils.prompt_loader import load_rag_prompts


class RagService(object):
    def __init__(self, vector_store: VectorStoreService | None = None):
        self.vector_store = vector_store or VectorStoreService()
        self.retriever = self.vector_store.get_retriever()
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chatModel
        self.chain = self._init_chain()

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def retriever_docs(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def getPrompt(self, query: str) -> str:
        context_docs = self.retriever_docs(query)
        context = ""
        for counter, doc in enumerate(context_docs, start=1):
            file_name = doc.metadata.get("file_name") or doc.metadata.get("source") or "unknown"
            page = doc.metadata.get("page")
            page_start = doc.metadata.get("page_start")
            if isinstance(page, int):
                location = f"{file_name}, page {page + 1}"
            elif page_start:
                location = f"{file_name}, page {page_start}"
            else:
                location = str(file_name)
            context += f"[Reference {counter}] Source: {location}\nContent: {doc.page_content}\nMetadata: {doc.metadata}\n\n"
        return context

    def rag_summarize(self, query: str) -> str:
        return self.chain.invoke({"input": query, "context": self.getPrompt(query)})

    def rag_summarize_stream(self, query: str) -> Iterator[str]:
        chain_input = {"input": query, "context": self.getPrompt(query)}
        for chunk in self.chain.stream(chain_input):
            if chunk:
                yield str(chunk)


RagSummarizeService = RagService