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


def test_route_after_evaluation_dict_state():
    state_dict = {
        "evaluation": {
            "verdict": "SUCCESS",
            "has_reusable_lesson": False,
        },
        "trial_number": 1,
        "max_trials": 3,
    }
    assert route_after_evaluation(state_dict) == "finish"

    state_dict_retry = {
        "evaluation": {
            "verdict": "FAILURE",
            "has_reusable_lesson": False,
        },
        "trial_number": 1,
        "max_trials": 3,
    }
    assert route_after_evaluation(state_dict_retry) == "reflect_failure"


def test_reflexion_nodes_llm_exception_tolerance():
    from unittest.mock import MagicMock, patch
    from jarvis.agent.reflexion.planner_node import planner_node
    from jarvis.agent.reflexion.evaluator_node import evaluator_node
    from jarvis.agent.reflexion.reflection_node import reflection_node
    from jarvis.agent.reflexion.answer_node import answer_node

    state = {
        "task": "Test task",
        "plan": "",
        "execution_outcome": "Some error occurred",
        "execution_events": [],
        "reflexion_memeory": [],
        "trial_number": 1,
        "max_trials": 3,
    }

    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = RuntimeError("Planner LLM failed")
    with patch("jarvis.agent.reflexion.planner_node.chat_llm", mock_llm):
        p_res = planner_node(state)
        assert "<plan>" in p_res["plan"]

    mock_llm_eval = MagicMock()
    mock_llm_eval.with_structured_output.side_effect = RuntimeError("Structured LLM failed")
    with patch("jarvis.agent.reflexion.evaluator_node.chat_llm", mock_llm_eval):
        e_res = evaluator_node(state)
        assert e_res["evaluation"].verdict == "FAILURE"

    state["evaluation"] = e_res["evaluation"]
    mock_llm_ref = MagicMock()
    mock_llm_ref.invoke.side_effect = RuntimeError("Reflection LLM failed")
    with patch("jarvis.agent.reflexion.reflection_node.chat_llm", mock_llm_ref):
        r_res = reflection_node(state)
        assert "<reflection>" in r_res["reflection"]

    mock_llm_ans = MagicMock()
    mock_llm_ans.invoke.side_effect = RuntimeError("Answer LLM failed")
    with patch("jarvis.agent.reflexion.answer_node.chat_llm", mock_llm_ans):
        a_res = answer_node(state)
        assert "<final_answer>" in a_res["reflection"]

