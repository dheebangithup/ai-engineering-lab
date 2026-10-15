from jarvis.agent.llm import chat_llm
from jarvis.agent.supervisor.state import AgentStatus, SupervisorState, WorkerResult, WorkerType


SYSTEM_PROMPT = """You are the DIRECT Q&A worker of the J.A.R.V.I.S. multi-agent system.
Your job is to answer questions, explain concepts, or hold conversations directly without tools.
Provide accurate, helpful, and concise responses.
"""


def direct_worker(state: SupervisorState) -> dict:
    """
    Executes a direct LLM call for conceptual or conversational queries.
    """
    task = state["task"]
    history = state.get("conversation_history", [])

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        messages.append(msg)
    messages.append({"role": "user", "content": task})

    try:
        response = chat_llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        result = WorkerResult(
            worker=WorkerType.DIRECT.value,
            status=AgentStatus.COMPLETED,
            outcome=content,
        )
    except Exception as e:
        result = WorkerResult(
            worker=WorkerType.DIRECT.value,
            status=AgentStatus.ERROR,
            outcome=f"Direct worker error: {str(e)}",
            error=str(e),
        )

    return {"worker_result": result.to_dict()}
