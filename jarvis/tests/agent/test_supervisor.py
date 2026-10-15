from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from jarvis.agent.supervisor import (
    AgentStatus,
    SupervisorState,
    WorkerResult,
    WorkerType,
    create_supervisor_graph,
)
from jarvis.agent.supervisor.supervisor_node import (
    SupervisorDecision,
    _classify_task,
    supervisor_node,
)


def test_supervisor_state_and_worker_result():
    res = WorkerResult(
        worker=WorkerType.FAST_REACT.value,
        status=AgentStatus.COMPLETED,
        outcome="Files listed successfully.",
    )
    d = res.to_dict()
    assert d["worker"] == "fast_react"
    assert d["status"] == "completed"
    assert d["outcome"] == "Files listed successfully."
    assert d["needs_human_input"] is False


def test_supervisor_graph_creation():
    graph = create_supervisor_graph()
    assert graph is not None


def test_supervisor_node_ambiguity_counter_question():
    ambiguous_state: SupervisorState = {
        "task": "Please delete the files and process it",
        "conversation_history": [],
        "status": AgentStatus.IDLE,
        "selected_worker": None,
        "worker_history": [],
        "worker_result": None,
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 0,
        "max_iterations": 5,
    }

    mock_decision = SupervisorDecision(
        is_ambiguous=True,
        clarification_question="Which files would you like to delete, and how should they be processed?",
        pattern="fast_react",
        reasoning="Task does not specify file names or processing steps.",
    )

    with patch("jarvis.agent.supervisor.supervisor_node._classify_task", return_value=mock_decision):
        result = supervisor_node(ambiguous_state)
        assert result["status"] == AgentStatus.NEED_HUMAN_INPUT
        assert "Which files" in result["human_input_prompt"]


def test_supervisor_node_clear_task_routes_to_worker():
    clear_state: SupervisorState = {
        "task": "Read file status.txt",
        "conversation_history": [],
        "status": AgentStatus.IDLE,
        "selected_worker": None,
        "worker_history": [],
        "worker_result": None,
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 0,
        "max_iterations": 5,
    }

    mock_decision = SupervisorDecision(
        is_ambiguous=False,
        clarification_question=None,
        pattern="fast_react",
        reasoning="Simple deterministic file read operation.",
    )

    with patch("jarvis.agent.supervisor.supervisor_node._classify_task", return_value=mock_decision):
        result = supervisor_node(clear_state)
        assert result["status"] == AgentStatus.RUNNING
        assert result["selected_worker"] == "fast_react"


def test_supervisor_worker_reports_completion():
    worker_done_state: SupervisorState = {
        "task": "Read file status.txt",
        "conversation_history": [],
        "status": AgentStatus.RUNNING,
        "selected_worker": "fast_react",
        "worker_history": [],
        "worker_result": {
            "worker": "fast_react",
            "status": "completed",
            "outcome": "File content: JARVIS online",
            "needs_human_input": False,
        },
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 1,
        "max_iterations": 5,
    }

    result = supervisor_node(worker_done_state)
    assert result["status"] == AgentStatus.COMPLETED
    assert result["final_response"] == "File content: JARVIS online"


def test_supervisor_worker_reports_need_human_input():
    worker_ask_state: SupervisorState = {
        "task": "Clean working directory",
        "conversation_history": [],
        "status": AgentStatus.RUNNING,
        "selected_worker": "fast_react",
        "worker_history": [],
        "worker_result": {
            "worker": "fast_react",
            "status": "need_human_input",
            "outcome": "NEED_HUMAN_INPUT: Are you sure you want to delete all temporary files?",
            "needs_human_input": True,
            "human_prompt": "Are you sure you want to delete all temporary files?",
        },
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 1,
        "max_iterations": 5,
    }

    result = supervisor_node(worker_ask_state)
    assert result["status"] == AgentStatus.NEED_HUMAN_INPUT
    assert "delete all temporary files" in result["human_input_prompt"]


def test_supervisor_escalates_on_fast_react_error():
    worker_error_state: SupervisorState = {
        "task": "Write complex code and test edge cases",
        "conversation_history": [],
        "status": AgentStatus.RUNNING,
        "selected_worker": "fast_react",
        "worker_history": [],
        "worker_result": {
            "worker": "fast_react",
            "status": "error",
            "outcome": "Execution failed on complex assertions",
            "error": "AssertionError: edge cases failed",
        },
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 1,
        "max_iterations": 5,
    }

    result = supervisor_node(worker_error_state)
    assert result["status"] == AgentStatus.RUNNING
    assert result["selected_worker"] == "reflexion"
    assert "Escalated" in result["routing_reason"]
