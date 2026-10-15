from langgraph.graph import END, START, StateGraph

from jarvis.agent.reflexion.answer_node import answer_node
from jarvis.agent.reflexion.evaluator_node import evaluator_node
from jarvis.agent.reflexion.executor_node import executor_node
from jarvis.agent.reflexion.planner_node import planner_node
from jarvis.agent.reflexion.reflection_node import reflection_node
from jarvis.agent.reflexion.state import ReflexionState


def route_after_evaluation(state: ReflexionState) -> str:
    evaluation = state["evaluation"]
    if evaluation.verdict == "SUCCESS":
        if evaluation.has_reusable_lesson:
            return "reflect_success"
        return "finish"

    if state["trial_number"] >= state["max_trials"]:
        return "finish"

    return "reflect_failure"


def route_after_reflection(state: ReflexionState) -> str:
    if state["evaluation"].verdict == "SUCCESS":
        return "finish"
    return "retry"


def create_reflexion_graph():
    """
    Build and compile the Reflexion agent StateGraph.
    """
    builder = StateGraph(ReflexionState)

    # Add nodes to graph
    builder.add_node("planner_node", planner_node)
    builder.add_node("executor_node", executor_node)
    builder.add_node("evaluator_node", evaluator_node)
    builder.add_node("reflection_node", reflection_node)
    builder.add_node("answer_node", answer_node)

    # Add edges
    builder.add_edge(START, "planner_node")
    builder.add_edge("planner_node", "executor_node")
    builder.add_edge("executor_node", "evaluator_node")

    builder.add_conditional_edges(
        "evaluator_node",
        route_after_evaluation,
        {
            "finish": "answer_node",
            "reflect_success": "reflection_node",
            "reflect_failure": "reflection_node",
        },
    )
    builder.add_conditional_edges(
        "reflection_node",
        route_after_reflection,
        {
            "finish": "answer_node",
            "retry": "planner_node",
        },
    )
    builder.add_edge("answer_node", END)

    return builder.compile()


graph = create_reflexion_graph()