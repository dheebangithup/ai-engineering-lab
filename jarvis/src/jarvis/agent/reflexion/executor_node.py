import os
from pathlib import Path
from typing import Any, Dict

from langchain_core.callbacks import BaseCallbackHandler
from langgraph.prebuilt import create_react_agent

from jarvis.agent.llm import chat_llm
from jarvis.agent.reflexion.state import ReflexionState
from jarvis.tools import (
    ToolRegistry,
    ToolsGateway,
    create_gateway_tools,
    register_default_tools,
)
from jarvis.workspace import default_workspace


class ExecutionTraceHandler(BaseCallbackHandler):
    """Callback handler to track tool executions during agent runs."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def on_tool_start(
        self, serialized: Dict[str, Any], input_str: str, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": "tool_started",
            "tool": serialized.get("name", "unknown"),
            "run_id": str(run_id),
        })

    def on_tool_end(
        self, output: Any, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": "tool_completed",
            "run_id": str(run_id),
            "output": str(output)[:2000],
        })

    def on_tool_error(
        self, error: BaseException, *, run_id: Any,
        parent_run_id: Any = None, **kwargs: Any
    ) -> None:
        self.events.append({
            "event_type": "tool_error",
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
    allowed_commands={"python", "python3", "echo", "date", "whoami", "pwd", "ls", "git"},
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


def executor_node(state: ReflexionState) -> dict:
    """
    Executes the current plan using the ReAct agent powered by ToolsGateway.
    """
    task = state["task"]
    plan = state["plan"]
    trace = ExecutionTraceHandler()

    prompt = f"""Execute the following task according to the plan.

TASK:
{task}

PLAN:
{plan}

Actually execute the plan using your tools and verify the result.
Return only the execution outcome and relevant results.
"""

    result = executor_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]},
        config={"callbacks": [trace]},
    )

    print("\n========== AGENT EXECUTION TRACE ==========")
    for message in result.get("messages", []):
        msg_type = type(message).__name__
        print(f"\n[{msg_type}]")
        if getattr(message, "content", None):
            print("CONTENT:", message.content)
        if getattr(message, "tool_calls", None):
            print("TOOL CALLS:", message.tool_calls)
    print("\n========== END TRACE ==========\n")

    last_message = result["messages"][-1]
    outcome_content = last_message.content if hasattr(last_message, "content") else str(last_message)

    return {
        "execution_outcome": outcome_content,
        "execution_events": trace.events,
    }