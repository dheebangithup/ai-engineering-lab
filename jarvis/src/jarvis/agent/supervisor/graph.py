from langgraph.graph import END, START, StateGraph

from jarvis.agent.supervisor.state import (
    AgentStatus,
    SupervisorNodeName,
    SupervisorState,
    WorkerType,
)
from jarvis.agent.supervisor.supervisor_node import supervisor_node
from jarvis.agent.supervisor.workers import (
    direct_worker,
    fast_react_worker,
    reflexion_worker,
)
from jarvis.logger import get_logger

logger = get_logger("supervisor.graph")


def human_interaction_node(state: SupervisorState) -> dict:
    """
    Pause/breakpoint node indicating that human input or approval is needed.
    """
    logger.info("Graph entering human_interaction_node (awaiting clarification/approval).")
    return {
        "status": AgentStatus.NEED_HUMAN_INPUT,
    }


def route_from_supervisor(state: SupervisorState) -> str:
    """
    Conditional edge routing from the supervisor based on status and chosen worker.
    """
    if not state or not isinstance(state, dict):
        logger.warning("Empty or invalid state encountered in route_from_supervisor -> END")
        return END

    status = state.get("status")

    if status == AgentStatus.NEED_HUMAN_INPUT:
        logger.info(f"Supervisor routed -> {SupervisorNodeName.HUMAN_INTERACTION.value}")
        return SupervisorNodeName.HUMAN_INTERACTION.value

    if status in (AgentStatus.COMPLETED, AgentStatus.ERROR):
        logger.info(f"Supervisor graph terminal status: {status} -> END")
        return END

    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 5)
    if iteration > max_iterations:
        logger.warning(
            f"Supervisor iteration limit exceeded ({iteration}/{max_iterations}) -> END"
        )
        return END

    selected = state.get("selected_worker")
    if selected == WorkerType.DIRECT.value:
        logger.info(f"Supervisor routed -> {SupervisorNodeName.DIRECT_WORKER.value}")
        return SupervisorNodeName.DIRECT_WORKER.value
    elif selected == WorkerType.FAST_REACT.value:
        logger.info(f"Supervisor routed -> {SupervisorNodeName.FAST_REACT_WORKER.value}")
        return SupervisorNodeName.FAST_REACT_WORKER.value
    elif selected == WorkerType.REFLEXION.value:
        logger.info(f"Supervisor routed -> {SupervisorNodeName.REFLEXION_WORKER.value}")
        return SupervisorNodeName.REFLEXION_WORKER.value

    logger.info(f"Unknown routing state for worker '{selected}' -> END")
    return END


def create_supervisor_graph():
    """
    Create and compile the LangGraph Hierarchical Supervisor Agent graph.
    """
    workflow = StateGraph(SupervisorState)

    # 1. Register Nodes
    workflow.add_node(SupervisorNodeName.SUPERVISOR.value, supervisor_node)
    workflow.add_node(SupervisorNodeName.DIRECT_WORKER.value, direct_worker)
    workflow.add_node(SupervisorNodeName.FAST_REACT_WORKER.value, fast_react_worker)
    workflow.add_node(SupervisorNodeName.REFLEXION_WORKER.value, reflexion_worker)
    workflow.add_node(SupervisorNodeName.HUMAN_INTERACTION.value, human_interaction_node)

    # 2. Add Edges
    workflow.add_edge(START, SupervisorNodeName.SUPERVISOR.value)

    workflow.add_conditional_edges(
        SupervisorNodeName.SUPERVISOR.value,
        route_from_supervisor,
        {
            SupervisorNodeName.HUMAN_INTERACTION.value: SupervisorNodeName.HUMAN_INTERACTION.value,
            SupervisorNodeName.DIRECT_WORKER.value: SupervisorNodeName.DIRECT_WORKER.value,
            SupervisorNodeName.FAST_REACT_WORKER.value: SupervisorNodeName.FAST_REACT_WORKER.value,
            SupervisorNodeName.REFLEXION_WORKER.value: SupervisorNodeName.REFLEXION_WORKER.value,
            END: END,
        },
    )

    # Every worker reports its findings directly back to the supervisor
    workflow.add_edge(SupervisorNodeName.DIRECT_WORKER.value, SupervisorNodeName.SUPERVISOR.value)
    workflow.add_edge(SupervisorNodeName.FAST_REACT_WORKER.value, SupervisorNodeName.SUPERVISOR.value)
    workflow.add_edge(SupervisorNodeName.REFLEXION_WORKER.value, SupervisorNodeName.SUPERVISOR.value)
    workflow.add_edge(SupervisorNodeName.HUMAN_INTERACTION.value, END)

    return workflow.compile()
