from langgraph.graph import END, START, StateGraph

from jarvis.agent.reflexion.answer_node import answer_node
from jarvis.agent.reflexion.evaluator_node import evaluator_node
from jarvis.agent.reflexion.executor_node import executor_node
from jarvis.agent.reflexion.planner_node import planner_node
from jarvis.agent.reflexion.reflection_node import reflection_node
from jarvis.agent.reflexion.state import (
    EvaluationVerdict,
    ReflexionNode,
    ReflexionRoute,
    ReflexionState,
)
from jarvis.logger import get_logger

logger = get_logger("reflexion.graph")


def route_after_evaluation(state: ReflexionState) -> str:
    evaluation = state.get("evaluation") if isinstance(state, dict) else None
    if evaluation:
        if isinstance(evaluation, dict):
            verdict = evaluation.get("verdict", EvaluationVerdict.FAILURE.value)
            has_reusable_lesson = evaluation.get("has_reusable_lesson", False)
        else:
            verdict = getattr(evaluation, "verdict", EvaluationVerdict.FAILURE.value)
            has_reusable_lesson = getattr(evaluation, "has_reusable_lesson", False)
    else:
        verdict = EvaluationVerdict.FAILURE.value
        has_reusable_lesson = False

    trial_number = state.get("trial_number", 1) if isinstance(state, dict) else 1
    max_trials = state.get("max_trials", 3) if isinstance(state, dict) else 3

    if verdict == EvaluationVerdict.SUCCESS.value:
        if has_reusable_lesson:
            logger.info("Evaluation verdict SUCCESS with reusable lesson -> reflect_success")
            return ReflexionRoute.REFLECT_SUCCESS.value
        logger.info("Evaluation verdict SUCCESS without reusable lesson -> finish")
        return ReflexionRoute.FINISH.value

    if trial_number >= max_trials:
        logger.info(f"Max trials reached ({trial_number}/{max_trials}) -> finish")
        return ReflexionRoute.FINISH.value

    logger.info(f"Evaluation verdict FAILURE (trial {trial_number}/{max_trials}) -> reflect_failure")
    return ReflexionRoute.REFLECT_FAILURE.value


def route_after_reflection(state: ReflexionState) -> str:
    trial_number = state.get("trial_number", 1) if isinstance(state, dict) else 1
    max_trials = state.get("max_trials", 3) if isinstance(state, dict) else 3

    if trial_number >= max_trials:
        logger.warning(
            f"Reflection completed but max trials reached ({trial_number}/{max_trials}) -> finish"
        )
        return ReflexionRoute.FINISH.value

    evaluation = state.get("evaluation") if isinstance(state, dict) else None
    if evaluation:
        if isinstance(evaluation, dict):
            verdict = evaluation.get("verdict", EvaluationVerdict.FAILURE.value)
        else:
            verdict = getattr(evaluation, "verdict", EvaluationVerdict.FAILURE.value)
    else:
        verdict = EvaluationVerdict.FAILURE.value

    if verdict == EvaluationVerdict.SUCCESS.value:
        logger.info("Reflection finished for successful task -> finish")
        return ReflexionRoute.FINISH.value
    logger.info("Reflection finished for failed task -> retry (planner_node)")
    return ReflexionRoute.RETRY.value


def create_reflexion_graph():
    """
    Build and compile the Reflexion agent StateGraph.
    """
    builder = StateGraph(ReflexionState)

    # Add nodes to graph using ReflexionNode enum
    builder.add_node(ReflexionNode.PLANNER.value, planner_node)
    builder.add_node(ReflexionNode.EXECUTOR.value, executor_node)
    builder.add_node(ReflexionNode.EVALUATOR.value, evaluator_node)
    builder.add_node(ReflexionNode.REFLECTION.value, reflection_node)
    builder.add_node(ReflexionNode.ANSWER.value, answer_node)

    # Add edges
    builder.add_edge(START, ReflexionNode.PLANNER.value)
    builder.add_edge(ReflexionNode.PLANNER.value, ReflexionNode.EXECUTOR.value)
    builder.add_edge(ReflexionNode.EXECUTOR.value, ReflexionNode.EVALUATOR.value)

    builder.add_conditional_edges(
        ReflexionNode.EVALUATOR.value,
        route_after_evaluation,
        {
            ReflexionRoute.FINISH.value: ReflexionNode.ANSWER.value,
            ReflexionRoute.REFLECT_SUCCESS.value: ReflexionNode.REFLECTION.value,
            ReflexionRoute.REFLECT_FAILURE.value: ReflexionNode.REFLECTION.value,
        },
    )
    builder.add_conditional_edges(
        ReflexionNode.REFLECTION.value,
        route_after_reflection,
        {
            ReflexionRoute.FINISH.value: ReflexionNode.ANSWER.value,
            ReflexionRoute.RETRY.value: ReflexionNode.PLANNER.value,
        },
    )
    builder.add_edge(ReflexionNode.ANSWER.value, END)

    return builder.compile()


graph = create_reflexion_graph()