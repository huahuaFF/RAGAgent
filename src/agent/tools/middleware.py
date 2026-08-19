from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.log.logger import logger
from src.utils.prompt_loader import load_report_prompts, load_system_prompts


@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    logger.info("[tool monitor] tool=%s args=%s", request.tool_call["name"], request.tool_call["args"])

    try:
        result = handler(request)
        logger.info("[tool monitor] tool=%s succeeded", request.tool_call["name"])

        if request.tool_call["name"] == "fill_context_for_report":
            request.runtime.context["report"] = True

        return result
    except Exception as exc:
        logger.error("[tool monitor] tool=%s failed: %s", request.tool_call["name"], exc)
        raise


@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    logger.info("[log_before_model] calling model with %s messages", len(state["messages"]))
    if state["messages"]:
        latest_message = state["messages"][-1]
        content = getattr(latest_message, "content", "")
        logger.debug("[log_before_model] %s | %s", type(latest_message).__name__, str(content).strip())
    return None


@dynamic_prompt
def report_prompt_switch(request: ModelRequest):
    if request.runtime.context.get("report", False):
        return load_report_prompts()
    return load_system_prompts()
