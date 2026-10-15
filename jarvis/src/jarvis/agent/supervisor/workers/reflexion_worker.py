from jarvis.agent.reflexion import create_reflexion_graph
from jarvis.agent.supervisor.state import AgentStatus, SupervisorState, WorkerResult, WorkerType


_reflexion_graph = None


def get_reflexion_graph():
    global _reflexion_graph
    if _reflexion_graph is None:
        _reflexion_graph = create_reflexion_graph()
    return _reflexion_graph


def reflexion_worker(state: SupervisorState) -> dict:
    """
    Executes the multi-stage iterative Reflexion agent worker.
    Uses planning, execution with ToolsGateway, evaluation, and reflection loops.
    Reports outcome, errors, or human input requests back to the supervisor.
    """
    task = state["task"]
    graph = get_reflexion_graph()

    initial_reflexion_state = {
        "task": task.strip(),
        "plan": "",
        "execution_outcome": "",
        "evaluation": {
            "analysis": "",
            "verdict": "FAILURE",
            "reason": "",
            "has_reusable_lesson": False,
            "learning_reason": "",
        },
        "reflection": "",
        "reflexion_memeory": [],
        "execution_events": [],
        "trial_number": 0,
        "max_trials": 3,
        "messages": [],
    }

    try:
        final_state = graph.invoke(initial_reflexion_state)
        outcome = final_state.get("execution_outcome", "")
        evaluation = final_state.get("evaluation")
        verdict = getattr(evaluation, "verdict", "FAILURE") if evaluation else "FAILURE"
        is_success = verdict == "SUCCESS"
        events = final_state.get("execution_events", [])

        if "NEED_HUMAN_INPUT:" in outcome:
            prompt = outcome.split("NEED_HUMAN_INPUT:", 1)[1].strip()
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.NEED_HUMAN_INPUT,
                outcome=outcome,
                needs_human_input=True,
                human_prompt=prompt,
                events=events,
            )
        elif is_success:
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.COMPLETED,
                outcome=outcome,
                events=events,
            )
        else:
            reason = getattr(evaluation, "reason", "Task could not be verified successfully.")
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.ERROR,
                outcome=outcome,
                error=f"Reflexion evaluation failed: {reason}",
                events=events,
            )
    except Exception as e:
        worker_res = WorkerResult(
            worker=WorkerType.REFLEXION.value,
            status=AgentStatus.ERROR,
            outcome=f"Reflexion worker runtime error: {str(e)}",
            error=str(e),
        )

    return {"worker_result": worker_res.to_dict()}
