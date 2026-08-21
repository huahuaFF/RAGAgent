from __future__ import annotations

from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver

from src.agent.tools.arxiv_tool import (
    arxiv_download,
    arxiv_download_and_import,
    arxiv_search,
    import_paper_to_vector_store,
)
from src.agent.tools.middleware import log_before_model, monitor_tool
from src.agent.tools.rag_tool import rag_summarize
from src.agent.tools.web_search_tool import web_search
from src.model.chatModel import chatModel
from src.utils.prompt_loader import load_system_prompts


class MainAgent:
    def __init__(self):
        self.checkpointer = InMemorySaver()
        self.agent = create_agent(
            model=chatModel,
            tools=[
                rag_summarize,
                arxiv_search,
                arxiv_download,
                arxiv_download_and_import,
                import_paper_to_vector_store,
                web_search,
            ],
            middleware=[monitor_tool, log_before_model],
            system_prompt=load_system_prompts(),
            checkpointer=self.checkpointer,
        )

    def execute(self, query: str, session_id: str = "default") -> str:
        result = self.agent.invoke(
            {"messages": [{"role": "user", "content": query}]},
            config=self._config(session_id),
        )
        latest_message = result["messages"][-1]
        return str(getattr(latest_message, "content", "")).strip()

    def execute_stream(self, query: str, session_id: str = "default"):
        answer = self.execute(query, session_id)
        if answer:
            yield answer

    def _config(self, session_id: str) -> dict:
        return {"configurable": {"thread_id": session_id or "default"}, "recursion_limit": 6}


ReactAgent = MainAgent
