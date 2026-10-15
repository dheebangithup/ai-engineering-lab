import pytest

from jarvis.agent.reflexion import (
    EvaluatorState,
    ReflexionState,
    create_reflexion_graph,
)
from jarvis.agent.reflexion.graph import (
    route_after_evaluation,
    route_after_reflection,
)


def test_evaluator_state_schema():
    eval_state = EvaluatorState(
        verdict="SUCCESS",
        analysis="All test criteria met.",
        reason="Outputs match expected result.",
        has_reusable_lesson=True,
        learning_reason="Valid file structure pattern.",
    )
    assert eval_state.verdict == "SUCCESS"
    assert eval_state.has_reusable_lesson is True


def test_route_after_evaluation_success_with_lesson():
    state = {
        "evaluation": EvaluatorState(
            verdict="SUCCESS",
            analysis="Ok",
            reason="Ok",
            has_reusable_lesson=True,
            learning_reason="Good lesson",
        ),
        "trial_number": 1,
        "max_trials": 3,
    }
    assert route_after_evaluation(state) == "reflect_success"


def test_route_after_evaluation_success_without_lesson():
    state = {
        "evaluation": EvaluatorState(
            verdict="SUCCESS",
            analysis="Ok",
            reason="Ok",
            has_reusable_lesson=False,
            learning_reason="None",
        ),
        "trial_number": 1,
        "max_trials": 3,
    }
    assert route_after_evaluation(state) == "finish"


def test_route_after_evaluation_failure_max_trials():
    state = {
        "evaluation": EvaluatorState(
            verdict="FAILURE",
            analysis="Error",
            reason="Timeout",
            has_reusable_lesson=False,
            learning_reason="None",
        ),
        "trial_number": 3,
        "max_trials": 3,
    }
    assert route_after_evaluation(state) == "finish"


def test_route_after_evaluation_failure_retry():
    state = {
        "evaluation": EvaluatorState(
            verdict="FAILURE",
            analysis="Error",
            reason="Wrong format",
            has_reusable_lesson=False,
            learning_reason="None",
        ),
        "trial_number": 1,
        "max_trials": 3,
    }
    assert route_after_evaluation(state) == "reflect_failure"


def test_route_after_reflection():
    success_state = {
        "evaluation": EvaluatorState(
            verdict="SUCCESS",
            analysis="Ok",
            reason="Ok",
            has_reusable_lesson=True,
            learning_reason="Lesson",
        ),
    }
    assert route_after_reflection(success_state) == "finish"

    failure_state = {
        "evaluation": EvaluatorState(
            verdict="FAILURE",
            analysis="Failed",
            reason="Bug",
            has_reusable_lesson=True,
            learning_reason="Fix bug",
        ),
    }
    assert route_after_reflection(failure_state) == "retry"


def test_create_reflexion_graph():
    graph = create_reflexion_graph()
    assert graph is not None
    # Verify node names in graph
    node_keys = graph.nodes.keys()
    assert "planner_node" in node_keys
    assert "executor_node" in node_keys
    assert "evaluator_node" in node_keys
    assert "reflection_node" in node_keys
    assert "answer_node" in node_keys
