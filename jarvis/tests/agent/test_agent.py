from pathlib import Path
import pytest

from jarvis.agent import AgentExecutionResult, AgentRunner, JarvisAgent


def test_agent_initialization(tmp_path: Path):
    custom_ws = tmp_path / "custom_agent_ws"
    agent = JarvisAgent(workspace_dir=custom_ws, max_trials=2, auto_save_results=False)

    assert agent.workspace_dir == custom_ws.resolve()
    assert agent.max_trials == 2
    assert agent.auto_save_results is False
    assert custom_ws.exists()


def test_agent_runner_alias():
    assert AgentRunner is JarvisAgent


def test_agent_execution_result_summary():
    res = AgentExecutionResult(
        task="Create report",
        success=True,
        outcome="Report created at /tmp/report.txt",
        verdict="SUCCESS",
        trials=1,
        plan="1. write report",
        reflection="Good execution",
    )
    summary = res.summary()
    assert "[SUCCESS]" in summary
    assert "1 trial(s)" in summary
    assert "SUCCESS" in summary


def test_agent_save_result(tmp_path: Path):
    ws = tmp_path / "ws"
    agent = JarvisAgent(workspace_dir=ws, auto_save_results=False)

    res = AgentExecutionResult(
        task="Test task",
        success=True,
        outcome="Done",
        verdict="SUCCESS",
        trials=1,
        plan="Plan",
        reflection="Lesson",
    )

    saved_file = agent.save_result(res)
    assert saved_file.exists()
    assert (ws / "results").exists()


def test_agent_empty_task(tmp_path: Path):
    ws = tmp_path / "ws_empty"
    agent = JarvisAgent(workspace_dir=ws, auto_save_results=False)

    res = agent.run("")
    assert res.success is False
    assert res.verdict == "INVALID_INPUT"
    assert "No valid task" in res.outcome

    res2 = agent.run("   \n\t  ")
    assert res2.success is False
    assert res2.verdict == "INVALID_INPUT"


def test_agent_graph_exception_handling(tmp_path: Path):
    from unittest.mock import MagicMock
    ws = tmp_path / "ws_graph_err"
    agent = JarvisAgent(workspace_dir=ws, auto_save_results=False)

    # Simulate catastrophic graph execution failure
    agent._graph = MagicMock()
    agent._graph.invoke.side_effect = RuntimeError("Fatal LLM API timeout")

    res = agent.run("Do something important")
    assert res.success is False
    assert res.verdict == "ERROR"
    assert "Fatal LLM API timeout" in res.outcome
    assert res.error == "Fatal LLM API timeout"
    assert "ERROR" in res.summary()


def test_agent_save_result_exception_tolerance(tmp_path: Path):
    from unittest.mock import patch
    ws = tmp_path / "ws_save_err"
    agent = JarvisAgent(workspace_dir=ws, auto_save_results=False)

    res = AgentExecutionResult(
        task="Test task",
        success=True,
        outcome="Done",
        verdict="SUCCESS",
        trials=1,
        plan="Plan",
        reflection="",
    )

    with patch("builtins.open", side_effect=PermissionError("Read-only filesystem")):
        saved = agent.save_result(res)
        assert saved is None  # Handled gracefully, did not raise PermissionError


def test_supervisor_iteration_budget_prevents_infinite_loop():
    from langgraph.graph import END
    from jarvis.agent.supervisor.state import AgentStatus, SupervisorState
    from jarvis.agent.supervisor.supervisor_node import supervisor_node
    from jarvis.agent.supervisor.graph import route_from_supervisor

    state: SupervisorState = {
        "task": "infinite loop simulation",
        "conversation_history": [],
        "status": AgentStatus.RUNNING,
        "selected_worker": "fast_react",
        "worker_history": [],
        "worker_result": None,
        "human_input_prompt": None,
        "human_input_response": None,
        "final_response": None,
        "routing_reason": None,
        "iteration": 5,
        "max_iterations": 5,
    }

    # supervisor_node detects iteration > max_iterations (5 + 1 > 5)
    res = supervisor_node(state)
    assert res["status"] == AgentStatus.ERROR
    assert "exceeded maximum iteration budget" in res["final_response"]

    # route_from_supervisor routes to END
    state["status"] = res["status"]
    state["iteration"] = res["iteration"]
    route = route_from_supervisor(state)
    assert route == END


def test_reflexion_trial_budget_prevents_infinite_loop():
    from jarvis.agent.reflexion.graph import route_after_evaluation, route_after_reflection
    from jarvis.agent.reflexion.state import EvaluationVerdict, ReflexionRoute, ReflexionState

    state: ReflexionState = {
        "task": "complex coding task",
        "plan": "1. step",
        "execution_outcome": "error",
        "evaluation": {
            "verdict": EvaluationVerdict.FAILURE.value,
            "analysis": "failed",
            "reason": "error in step",
            "has_reusable_lesson": True,
            "learning_reason": "fix error",
        },
        "reflection": "Fix the bug",
        "reflexion_memeory": [],
        "execution_events": [],
        "trial_number": 3,
        "max_trials": 3,
        "messages": [],
    }

    # route_after_evaluation terminates when trial_number >= max_trials
    route_eval = route_after_evaluation(state)
    assert route_eval == ReflexionRoute.FINISH.value

    # route_after_reflection terminates when trial_number >= max_trials
    route_refl = route_after_reflection(state)
    assert route_refl == ReflexionRoute.FINISH.value
