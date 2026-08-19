from langchain.agents import create_agent

from src.agent.tools.middleware import log_before_model, monitor_tool, report_prompt_switch
from src.agent.tools.rag_tool import rag_summarize
from src.model.chatModel import chatModel
from src.utils.prompt_loader import load_system_prompts


class MainAgent:
    def __init__(self):
        self.agent = create_agent(
            model=chatModel,
            tools=[rag_summarize],
            middleware=[monitor_tool, log_before_model, report_prompt_switch],
            system_prompt=load_system_prompts(),
        )

    def execute_stream(self, query: str):
        input_dict = {
            "messages": [
                {"role": "user", "content": query},
            ]
        }

        for chunk in self.agent.stream(input_dict, stream_mode="values", context={"report": False}):
            latest_message = chunk["messages"][-1]
            if latest_message.content:
                yield latest_message.content.strip() + "\n"


ReactAgent = MainAgent
