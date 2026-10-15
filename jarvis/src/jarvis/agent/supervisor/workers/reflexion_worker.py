from jarvis.agent.reflexion import create_reflexion_graph
from jarvis.agent.reflexion.state import EvaluationVerdict
from jarvis.agent.supervisor.state import AgentStatus, SupervisorState, WorkerResult, WorkerType
from jarvis.logger import get_logger
from jarvis.tools import HUMAN_INPUT_INDICATOR

logger = get_logger("worker.reflexion")

DEFAULT_MAX_TRIALS: int = 3
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
    task = state.get("task", "")
    logger.info(f"Reflexion worker invoked for task: '{task[:60]}'")

    try:
        graph = get_reflexion_graph()

        initial_reflexion_state = {
            "task": task.strip(),
            "plan": "",
            "execution_outcome": "",
            "evaluation": {
                "analysis": "",
                "verdict": EvaluationVerdict.FAILURE.value,
                "reason": "",
                "has_reusable_lesson": False,
                "learning_reason": "",
            },
            "reflection": "",
            "reflexion_memeory": [],
            "execution_events": [],
            "trial_number": 0,
            "max_trials": DEFAULT_MAX_TRIALS,
            "messages": [],
        }

        final_state = graph.invoke(initial_reflexion_state)
        outcome = final_state.get("execution_outcome", "") or ""
        evaluation = final_state.get("evaluation")

        if evaluation:
            if hasattr(evaluation, "verdict"):
                verdict = evaluation.verdict
                reason = getattr(evaluation, "reason", "Task could not be verified successfully.")
            elif isinstance(evaluation, dict):
                verdict = evaluation.get("verdict", EvaluationVerdict.FAILURE.value)
                reason = evaluation.get("reason", "Task could not be verified successfully.")
            else:
                verdict = EvaluationVerdict.FAILURE.value
                reason = "Unknown evaluation structure."
        else:
            verdict = EvaluationVerdict.FAILURE.value
            reason = "No evaluation returned."

        is_success = verdict == EvaluationVerdict.SUCCESS.value
        events = final_state.get("execution_events", []) or []

        if HUMAN_INPUT_INDICATOR in outcome:
            prompt = outcome.split(HUMAN_INPUT_INDICATOR, 1)[1].strip()
            logger.info(f"Reflexion worker requested human input: {prompt}")
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.NEED_HUMAN_INPUT,
                outcome=outcome,
                needs_human_input=True,
                human_prompt=prompt,
                events=events,
            )
        elif is_success:
            logger.info(f"Reflexion worker completed successfully: verdict={verdict}")
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.COMPLETED,
                outcome=outcome,
                events=events,
            )
        else:
            logger.warning(f"Reflexion worker evaluated to failure: {reason}")
            worker_res = WorkerResult(
                worker=WorkerType.REFLEXION.value,
                status=AgentStatus.ERROR,
                outcome=outcome,
                error=f"Reflexion evaluation failed: {reason}",
                events=events,
            )
    except Exception as e:
        logger.error(f"Reflexion worker crashed with exception: {e}", exc_info=True)
        worker_res = WorkerResult(
            worker=WorkerType.REFLEXION.value,
            status=AgentStatus.ERROR,
            outcome=f"Reflexion worker runtime error: {str(e)}",
            error=str(e),
        )

    return {"worker_result": worker_res.to_dict()}
