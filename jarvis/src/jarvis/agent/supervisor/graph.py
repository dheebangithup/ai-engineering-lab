from langgraph.graph import END, START, StateGraph

from jarvis.agent.supervisor.state import (
    AgentStatus,
    SupervisorState,
    WorkerType,
)
from jarvis.agent.supervisor.supervisor_node import supervisor_node
from jarvis.agent.supervisor.workers import (
    direct_worker,
    fast_react_worker,
    reflexion_worker,
)


def human_interaction_node(state: SupervisorState) -> dict:
    """
    Pause/breakpoint node indicating that human input or approval is needed.
    """
    return {
        "status": AgentStatus.NEED_HUMAN_INPUT,
    }


def route_from_supervisor(state: SupervisorState) -> str:
    """
    Conditional edge routing from the supervisor based on status and chosen worker.
    """
    status = state.get("status")

    if status == AgentStatus.NEED_HUMAN_INPUT:
        return "human_interaction"

    if status in (AgentStatus.COMPLETED, AgentStatus.ERROR):
        return END

    selected = state.get("selected_worker")
    if selected == WorkerType.DIRECT.value:
        return "direct_worker"
    elif selected == WorkerType.FAST_REACT.value:
        return "fast_react_worker"
    elif selected == WorkerType.REFLEXION.value:
        return "reflexion_worker"

    return END


def create_supervisor_graph():
    """
    Create and compile the LangGraph Hierarchical Supervisor Agent graph.
    """
    workflow = StateGraph(SupervisorState)

    # 1. Register Nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("direct_worker", direct_worker)
    workflow.add_node("fast_react_worker", fast_react_worker)
    workflow.add_node("reflexion_worker", reflexion_worker)
    workflow.add_node("human_interaction", human_interaction_node)

    # 2. Add Edges
    workflow.add_edge(START, "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "human_interaction": "human_interaction",
            "direct_worker": "direct_worker",
            "fast_react_worker": "fast_react_worker",
            "reflexion_worker": "reflexion_worker",
            END: END,
        },
    )

    # Every worker reports its findings directly back to the supervisor
    workflow.add_edge("direct_worker", "supervisor")
    workflow.add_edge("fast_react_worker", "supervisor")
    workflow.add_edge("reflexion_worker", "supervisor")
    workflow.add_edge("human_interaction", END)

    return workflow.compile()
