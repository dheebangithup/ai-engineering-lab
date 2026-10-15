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
