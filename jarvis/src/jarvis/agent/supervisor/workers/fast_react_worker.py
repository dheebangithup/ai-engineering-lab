from typing import Any, Dict
from langchain_core.callbacks import BaseCallbackHandler
from langgraph.prebuilt import create_react_agent

from jarvis.agent.llm import chat_llm
from jarvis.agent.supervisor.state import AgentStatus, SupervisorState, WorkerResult, WorkerType
from jarvis.logger import get_logger
from jarvis.tools import (
    DEFAULT_ALLOWED_COMMANDS,
    HUMAN_INPUT_INDICATOR,
    ToolRegistry,
    ToolsGateway,
    TraceEventType,
    create_gateway_tools,
    register_default_tools,
)
from jarvis.workspace import default_workspace

logger = get_logger("worker.fast_react")


class ReactTraceHandler(BaseCallbackHandler):
    def __init__(self) -> None:
        self.events: list[dict] = []

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_START.value,
            "tool": serialized.get("name", "unknown"),
            "input": input_str,
        })

    def on_tool_end(self, output: Any, **kwargs: Any) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_END.value,
            "output": str(output),
        })

    def on_tool_error(self, error: BaseException, **kwargs: Any) -> None:
        self.events.append({
            "event_type": TraceEventType.TOOL_ERROR.value,
            "error": str(error),
        })


_ws = default_workspace()
_registry = ToolRegistry()
register_default_tools(
    _registry,
    allowed_base_dir=_ws.root,
    allowed_commands=DEFAULT_ALLOWED_COMMANDS,
)
_gateway = ToolsGateway(_registry)
_tools = create_gateway_tools(_gateway)

SYSTEM_PROMPT = f"""You are the FAST REACT WORKER of the J.A.R.V.I.S. multi-agent system.
Your workspace directory is: {_ws.root}

Rules:
1. Use your available tools (list_files, read_file, write_file, search_files, run_command) to execute the task efficiently.
2. If you realize mid-execution that critical information is missing or you need human confirmation before performing an irreversible action, output:
{HUMAN_INPUT_INDICATOR} <clearly describe what clarification or confirmation you need>
3. Otherwise, perform the tool calls, complete the task, and return a clear summary of what was done.
"""

_agent = create_react_agent(
    model=chat_llm,
    tools=_tools,
    prompt=SYSTEM_PROMPT,
)


DEFAULT_REACT_RECURSION_LIMIT: int = 15


def fast_react_worker(state: SupervisorState) -> dict:
    """
    Executes a single-pass ReAct agent for fast deterministic or single-step tool tasks.
    Reports outcomes, errors, or human input requests back to the supervisor.
    """
    task = state.get("task", "")
    trace = ReactTraceHandler()
    logger.info(f"Fast ReAct worker executing task: '{task[:60]}'")

    try:
        result = _agent.invoke(
            {"messages": [{"role": "user", "content": task}]},
            config={"callbacks": [trace], "recursion_limit": DEFAULT_REACT_RECURSION_LIMIT},
        )
        messages = result.get("messages", []) if isinstance(result, dict) else []
        if messages:
            last_message = messages[-1]
            outcome = last_message.content if hasattr(last_message, "content") else str(last_message)
            if not isinstance(outcome, str):
                outcome = str(outcome)
        else:
            outcome = "Fast ReAct worker completed without output messages."

        if HUMAN_INPUT_INDICATOR in outcome:
            prompt = outcome.split(HUMAN_INPUT_INDICATOR, 1)[1].strip()
            logger.info(f"Fast ReAct requested human input: {prompt}")
            worker_res = WorkerResult(
                worker=WorkerType.FAST_REACT.value,
                status=AgentStatus.NEED_HUMAN_INPUT,
                outcome=outcome,
                needs_human_input=True,
                human_prompt=prompt,
                events=trace.events,
            )
        else:
            logger.info(f"Fast ReAct completed ({len(trace.events)} tool events executed)")
            worker_res = WorkerResult(
                worker=WorkerType.FAST_REACT.value,
                status=AgentStatus.COMPLETED,
                outcome=outcome,
                events=trace.events,
            )
    except Exception as e:
        logger.error(f"Fast ReAct execution failed: {e}", exc_info=True)
        worker_res = WorkerResult(
            worker=WorkerType.FAST_REACT.value,
            status=AgentStatus.ERROR,
            outcome=f"Fast ReAct worker failed: {str(e)}",
            error=str(e),
            events=trace.events,
        )

    return {"worker_result": worker_res.to_dict()}
