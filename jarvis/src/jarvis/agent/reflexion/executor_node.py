import os
from pathlib import Path
from typing import Any, Dict

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.prebuilt import create_react_agent

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState
from jarvis.logger import get_logger
from jarvis.tools import (
    DEFAULT_ALLOWED_COMMANDS,
    ToolRegistry,
    ToolsGateway,
    TraceEventType,
    create_gateway_tools,
    register_default_tools,
)
from jarvis.workspace import default_workspace

logger = get_logger("reflexion.executor")

DEFAULT_OUTPUT_TRUNCATE_LIMIT: int = 2000


class ExecutionTraceHandler(BaseCallbackHandler):
    """Callback handler to track tool executions during agent runs."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_STARTED.value,
            "tool": serialized.get("name", "unknown"),
            "run_id": str(run_id),
        })

    def on_tool_end(
        self, output: Any, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_COMPLETED.value,
            "run_id": str(run_id),
            "output": str(output)[:DEFAULT_OUTPUT_TRUNCATE_LIMIT],
        })

    def on_tool_error(
        self, error: BaseException, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_ERROR.value,
            "run_id": str(run_id),
            "error": str(error),
        })


# Single source of truth for the workspace
_workspace = default_workspace()
WORKSPACE_DIR = _workspace.root

# Centralized Tool Registry & Gateway
_registry = ToolRegistry()
register_default_tools(
    _registry,
    allowed_base_dir=WORKSPACE_DIR,
    allowed_commands=DEFAULT_ALLOWED_COMMANDS,
)
_gateway = ToolsGateway(_registry)

# Create LangChain tools backed by our ToolsGateway
tools = create_gateway_tools(_gateway)

SYSTEM_PROMPT = f"""You are the EXECUTOR component of a Reflexion agent.

## Workspace Contract
Your workspace base directory is: {WORKSPACE_DIR}
Your job is to execute the plan provided by the planner using your available tools.

Rules:
1. Carefully follow the plan step by step.
2. Use list_files, read_file, write_file, search_files, and run_command when computation or file operations are needed.
3. Do not just explain how to perform the task; actually execute it and verify the results.
4. When writing code, execute it with run_command if verification is needed.
5. Return a clear execution outcome summarizing what was performed and verified.
6. Do not perform reflection. Evaluation and reflection are handled by other nodes.
"""

# Create the ReAct executor agent
executor_agent = create_react_agent(
    model=chat_llm,
    tools=tools,
    prompt=SYSTEM_PROMPT,
)


DEFAULT_EXECUTOR_RECURSION_LIMIT: int = 25


def executor_node(state: ReflexionState) -> dict:
    """
    Executes the current plan using the ReAct agent powered by ToolsGateway.
    Safely captures tool execution events and runtime errors.
    """
    task = state.get("task", "")
    plan = state.get("plan", "")
    trace = ExecutionTraceHandler()
    logger.info(f"Reflexion executor executing plan for task: '{task[:60]}'")

    prompt = f"""Execute the following task according to the plan.

TASK:
{task}

PLAN:
{plan}

Actually execute the plan using your tools and verify the result.
Return only the execution outcome and relevant results.
"""

    try:
        result = executor_agent.invoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"callbacks": [trace], "recursion_limit": DEFAULT_EXECUTOR_RECURSION_LIMIT},
        )

        messages = result.get("messages", []) if isinstance(result, dict) else []
        if messages:
            last_message = messages[-1]
            outcome_content = last_message.content if hasattr(last_message, "content") else str(last_message)
            if not isinstance(outcome_content, str):
                outcome_content = str(outcome_content)
        else:
            outcome_content = "Executor completed without generating message content."
        logger.info(f"Reflexion executor finished with {len(trace.events)} tool event(s)")
    except Exception as e:
        logger.error(f"Reflexion executor encountered an error: {e}", exc_info=True)
        outcome_content = f"Execution error: {str(e)}"
        trace.events.append({
            "event_type": TraceEventType.EXECUTOR_ERROR.value,
            "error": str(e),
        })

    return {
        "execution_outcome": outcome_content,
        "execution_events": trace.events,
    }