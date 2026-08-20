from __future__ import annotations

import json
from typing import Callable

from langchain.agents import AgentState
from langchain.agents.middleware import ModelRequest, before_model, dynamic_prompt, wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain_core.messages import ToolMessage
from langgraph.runtime import Runtime
from langgraph.types import Command

from src.log.logger import logger
from src.utils.prompt_loader import load_report_prompts, load_system_prompts


MAX_MODEL_CALLS_PER_TURN = 3
MAX_TOOL_CALLS_PER_TURN = 3
SINGLE_USE_TOOLS = {"arxiv_download", "arxiv_download_and_import"}
DEDUPED_TOOLS = {"arxiv_search", "web_search", "rag_summarize"}


class AgentBudgetExceeded(RuntimeError):
    pass


@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    tool_name = request.tool_call["name"]
    tool_args = request.tool_call.get("args", {})
    tool_calls = request.runtime.context.setdefault("tool_calls", [])
    seen_tool_keys = request.runtime.context.setdefault("seen_tool_keys", set())

    tool_key = _tool_key(tool_name, tool_args)
    if tool_name in DEDUPED_TOOLS and tool_key in seen_tool_keys:
        raise AgentBudgetExceeded(
            f"Repeated tool call blocked in one turn: {tool_name}. Ask the user to choose from the existing result."
        )
    if tool_name in SINGLE_USE_TOOLS and any(name == tool_name for name in tool_calls):
        raise AgentBudgetExceeded(
            f"Repeated {tool_name} blocked in one turn. Ask the user before another download/import."
        )
    if len(tool_calls) >= MAX_TOOL_CALLS_PER_TURN:
        raise AgentBudgetExceeded(
            f"Tool budget exceeded: max {MAX_TOOL_CALLS_PER_TURN} tool calls per turn. Stop and ask the user for clarification."
        )

    tool_calls.append(tool_name)
    seen_tool_keys.add(tool_key)
    logger.info("[tool monitor] %s/%s tool=%s args=%s", len(tool_calls), MAX_TOOL_CALLS_PER_TURN, tool_name, tool_args)

    try:
        result = handler(request)
        logger.info("[tool monitor] tool=%s succeeded", tool_name)

        if tool_name == "fill_context_for_report":
            request.runtime.context["report"] = True

        return result
    except Exception as exc:
        logger.error("[tool monitor] tool=%s failed: %s", tool_name, exc)
        raise


@before_model
def log_before_model(state: AgentState, runtime: Runtime):
    model_calls = runtime.context.setdefault("model_calls", 0) + 1
    runtime.context["model_calls"] = model_calls
    if model_calls > MAX_MODEL_CALLS_PER_TURN:
        raise AgentBudgetExceeded(
            f"Model budget exceeded: max {MAX_MODEL_CALLS_PER_TURN} model calls per turn. Stop and ask the user for clarification."
        )

    logger.info(
        "[log_before_model] %s/%s calling model with %s messages",
        model_calls,
        MAX_MODEL_CALLS_PER_TURN,
        len(state["messages"]),
    )
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


def _tool_key(tool_name: str, tool_args: dict) -> str:
    try:
        args = json.dumps(tool_args, ensure_ascii=True, sort_keys=True)
    except TypeError:
        args = str(tool_args)
    return f"{tool_name}:{args}"
