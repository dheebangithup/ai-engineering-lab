from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Union

import dotenv

# Ensure 'src' is available in sys.path
src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from jarvis.config import load_env

# Auto-discover root .env regardless of working directory
load_env()

from jarvis.agent.reflexion import create_reflexion_graph
from jarvis.agent.reflexion.state import EvaluationVerdict
from jarvis.agent.supervisor import (
    AgentStatus,
    SupervisorState,
    WorkerType,
    create_supervisor_graph,
)
from jarvis.logger import get_logger
from jarvis.tools import TraceEventType
from jarvis.workspace import (
    ENV_JARVIS_WORKSPACE,
    WorkspaceDirectory,
    default_workspace,
)

logger = get_logger("agent")


class AgentVerdict(str, Enum):
    """Execution verdict statuses returned by J.A.R.V.I.S."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    ERROR = "ERROR"
    NEED_CLARIFICATION = "NEED_CLARIFICATION"
    INVALID_INPUT = "INVALID_INPUT"
    UNKNOWN = "UNKNOWN"


DEFAULT_MAX_TRIALS: int = 3
DEFAULT_RESULTS_DIR: str = WorkspaceDirectory.RESULTS.value
DEFAULT_TIMESTAMP_FORMAT: str = "%Y-%m-%d_%H-%M-%S"
DEFAULT_FILE_ENCODING: str = "utf-8"
UNKNOWN_WORKER: str = "unknown"
DEFAULT_GRAPH_RECURSION_LIMIT: int = 25
MAX_INTERACTIVE_TURNS: int = 10
DEFAULT_CLI_TASK: str = (
    "Create a file named status.txt containing 'JARVIS online'. "
    "Verify the file exists and read its content."
)
CLI_EXIT_COMMANDS: frozenset[str] = frozenset({"exit", "quit"})


@dataclass
class AgentExecutionResult:
    """
    Structured outcome returned by the high-level JarvisAgent runner.
    """
    task: str
    success: bool
    outcome: str
    verdict: Union[AgentVerdict, str]
    trials: int
    plan: str
    reflection: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    raw_state: Dict[str, Any] = field(default_factory=dict)
    worker: Optional[str] = None
    needs_human_input: bool = False
    clarification_question: Optional[str] = None
    error: Optional[str] = None

    def summary(self) -> str:
        if self.needs_human_input:
            return (
                f"[NEED_CLARIFICATION / HUMAN_INPUT]\n"
                f"Question: {self.clarification_question or 'Clarification required.'}"
            )
        status = (
            AgentVerdict.SUCCESS.value
            if self.success
            else (
                AgentVerdict.ERROR.value
                if self.verdict == AgentVerdict.ERROR.value
                else AgentVerdict.FAILURE.value
            )
        )
        worker_info = f" (Worker: {self.worker})" if self.worker else ""
        outcome_str = self.outcome or ""
        outcome_preview = (outcome_str[:300] + "...") if len(outcome_str) > 300 else outcome_str
        err_info = f"\nError: {self.error}" if self.error else ""
        return (
            f"[{status}]{worker_info} Task completed in {self.trials} trial(s)\n"
            f"Verdict: {self.verdict}\n"
            f"Outcome: {outcome_preview}{err_info}"
        )


class JarvisAgent:
    """
    High-level driver class and runner for the J.A.R.V.I.S. AI agent.
    Coordinates workflow graphs, tool execution, and reflection loops.
    """

    def __init__(
        self,
        workspace_dir: Optional[Path | str] = None,
        max_trials: int = DEFAULT_MAX_TRIALS,
        auto_save_results: bool = True,
        use_supervisor: bool = True,
    ) -> None:
        if workspace_dir is not None:
            self.workspace_dir = Path(workspace_dir).resolve()
        else:
            self.workspace_dir = default_workspace().root

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.max_trials = max_trials
        self.auto_save_results = auto_save_results
        self.use_supervisor = use_supervisor

        # Set workspace environment variable for tool implementations
        os.environ[ENV_JARVIS_WORKSPACE] = str(self.workspace_dir)

        # Compile the execution graph (Supervisor by default or direct Reflexion)
        try:
            if self.use_supervisor:
                self._graph = create_supervisor_graph()
            else:
                self._graph = create_reflexion_graph()
        except Exception as e:
            logger.error(f"Failed to initialize execution graph: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize agent workflow graph: {e}") from e

    def run(
        self,
        task: str,
        max_trials: Optional[int] = None,
        human_response: Optional[str] = None,
    ) -> AgentExecutionResult:
        """
        Execute a task using the Hierarchical Supervisor or Reflexion agent graph.
        Returns a structured AgentExecutionResult. Guaranteed not to crash on unexpected runtime errors.
        """
        clean_task = str(task or "").strip()
        if not clean_task:
            logger.warning("Agent run called with empty or invalid task.")
            empty_result = AgentExecutionResult(
                task=str(task or ""),
                success=False,
                outcome="No valid task description was provided to execute.",
                verdict=AgentVerdict.INVALID_INPUT,
                trials=0,
                plan="",
                reflection="",
                events=[],
                raw_state={},
                error="Empty or whitespace-only task description.",
            )
            if self.auto_save_results:
                self.save_result(empty_result)
            return empty_result

        logger.info(f"Agent starting task: '{clean_task}' (supervisor={self.use_supervisor}, max_trials={max_trials or self.max_trials})")

        try:
            if self.use_supervisor:
                initial_state: SupervisorState = {
                    "task": clean_task,
                    "conversation_history": [],
                    "status": AgentStatus.IDLE,
                    "selected_worker": None,
                    "worker_history": [],
                    "worker_result": None,
                    "human_input_prompt": None,
                    "human_input_response": human_response,
                    "final_response": None,
                    "routing_reason": None,
                    "iteration": 0,
                    "max_iterations": max_trials or self.max_trials,
                }

                state = self._graph.invoke(
                    initial_state,
                    config={"recursion_limit": DEFAULT_GRAPH_RECURSION_LIMIT},
                )
                if not isinstance(state, dict):
                    raise ValueError(f"Graph returned invalid state type: {type(state)}")

                status = state.get("status")
                needs_human = status == AgentStatus.NEED_HUMAN_INPUT
                is_success = status == AgentStatus.COMPLETED
                outcome = state.get("final_response") or state.get("human_input_prompt") or ""
                worker = state.get("selected_worker")
                
                if is_success:
                    verdict = AgentVerdict.SUCCESS
                    err = None
                elif needs_human:
                    verdict = AgentVerdict.NEED_CLARIFICATION
                    err = None
                elif status == AgentStatus.ERROR:
                    verdict = AgentVerdict.ERROR
                    err = outcome or "Supervisor worker encountered an error."
                else:
                    verdict = AgentVerdict.FAILURE
                    err = outcome or None

                result = AgentExecutionResult(
                    task=clean_task,
                    success=is_success,
                    outcome=outcome,
                    verdict=verdict,
                    trials=state.get("iteration", 1),
                    plan=state.get("routing_reason", "") or "",
                    reflection="",
                    events=state.get("worker_history", []) or [],
                    raw_state=state,
                    worker=worker,
                    needs_human_input=needs_human,
                    clarification_question=state.get("human_input_prompt"),
                    error=err,
                )
            else:
                trial_budget = max_trials if max_trials is not None else self.max_trials
                initial_state = {
                    "task": clean_task,
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
                    "max_trials": trial_budget,
                    "messages": [],
                }

                state = self._graph.invoke(
                    initial_state,
                    config={"recursion_limit": DEFAULT_GRAPH_RECURSION_LIMIT},
                )
                if not isinstance(state, dict):
                    raise ValueError(f"Graph returned invalid state type: {type(state)}")

                evaluation = state.get("evaluation")
                if evaluation:
                    if hasattr(evaluation, "verdict"):
                        verdict = evaluation.verdict
                    elif isinstance(evaluation, dict):
                        verdict = evaluation.get("verdict", AgentVerdict.UNKNOWN.value)
                    else:
                        verdict = AgentVerdict.UNKNOWN.value
                else:
                    verdict = AgentVerdict.UNKNOWN.value

                is_success = verdict == EvaluationVerdict.SUCCESS.value or verdict == AgentVerdict.SUCCESS.value
                outcome = state.get("execution_outcome", "") or ""

                result = AgentExecutionResult(
                    task=clean_task,
                    success=is_success,
                    outcome=outcome,
                    verdict=verdict,
                    trials=state.get("trial_number", 1),
                    plan=state.get("plan", "") or "",
                    reflection=state.get("reflection", "") or "",
                    events=state.get("execution_events", []) or [],
                    raw_state=state,
                    worker=WorkerType.REFLEXION.value,
                    error=None if is_success else (outcome if "error" in outcome.lower() else None),
                )

        except Exception as exc:
            logger.error(f"Agent execution encountered an unhandled exception: {exc}", exc_info=True)
            result = AgentExecutionResult(
                task=clean_task,
                success=False,
                outcome=f"Agent execution halted due to an unexpected error: {str(exc)}",
                verdict=AgentVerdict.ERROR,
                trials=1,
                plan="",
                reflection="",
                events=[{"event_type": TraceEventType.FATAL_ERROR.value, "error": str(exc)}],
                raw_state={"error": str(exc)},
                worker=UNKNOWN_WORKER,
                error=str(exc),
            )

        if self.auto_save_results:
            try:
                self.save_result(result)
            except Exception as e:
                logger.error(f"Failed to auto-save result: {e}", exc_info=True)

        return result

    def save_result(
        self,
        result: AgentExecutionResult,
        output_path: Optional[Path | str] = None,
    ) -> Optional[Path]:
        """
        Persist execution state to a JSON file in the workspace results folder.
        Safely catches and logs any disk or serialization errors.
        """
        try:
            results_dir = self.workspace_dir / DEFAULT_RESULTS_DIR
            results_dir.mkdir(parents=True, exist_ok=True)

            if output_path is not None:
                dest_file = Path(output_path).resolve()
            else:
                timestamp = datetime.now().strftime(DEFAULT_TIMESTAMP_FORMAT)
                dest_file = results_dir / f"agent_run_{timestamp}.json"

            data = {
                "task": result.task,
                "success": result.success,
                "verdict": result.verdict.value if isinstance(result.verdict, Enum) else result.verdict,
                "trials": result.trials,
                "outcome": result.outcome,
                "plan": result.plan,
                "reflection": result.reflection,
                "events_count": len(result.events),
                "worker": result.worker,
                "error": result.error,
                "timestamp": datetime.now().isoformat(),
            }

            with open(dest_file, "w", encoding=DEFAULT_FILE_ENCODING) as f:
                json.dump(data, f, indent=4, default=str)

            logger.info(f"Execution result persisted to: {dest_file}")
            return dest_file
        except Exception as e:
            logger.error(f"Failed to persist execution result: {e}", exc_info=True)
            return None


# Alias for runner naming preference
AgentRunner = JarvisAgent


def main():
    """CLI runner entry point."""
    try:
        from jarvis.workspace import initialize_workspace
        initialize_workspace()
    except Exception as e:
        logger.error(f"Workspace initialization error: {e}", exc_info=True)
        print(f"Warning: Failed to initialize workspace: {e}")

    if len(sys.argv) > 1:
        task_query = " ".join(sys.argv[1:])
    else:
        task_query = DEFAULT_CLI_TASK

    print(f"\n--- Running J.A.R.V.I.S. Agent Runner ---")
    print(f"Task: {task_query}\n")

    try:
        agent = JarvisAgent()
        res = agent.run(task_query)

        # Interactive Human-in-the-Loop clarification/approval loop with maximum turns guard
        interactive_turn = 0
        while res.needs_human_input and interactive_turn < MAX_INTERACTIVE_TURNS:
            interactive_turn += 1
            print(f"\n--- Clarification / Approval Required (Turn {interactive_turn}/{MAX_INTERACTIVE_TURNS}) ---")
            print(f"Supervisor Question: {res.clarification_question}\n")
            try:
                user_input = input("Your response (or 'exit' to cancel): ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nExiting interactive session.")
                break

            if not user_input or user_input.lower() in CLI_EXIT_COMMANDS:
                print("Cancelled by user.")
                break

            res = agent.run(task_query, human_response=user_input)

        if res.needs_human_input and interactive_turn >= MAX_INTERACTIVE_TURNS:
            print(f"\n[WARNING] Maximum interactive turns ({MAX_INTERACTIVE_TURNS}) reached. Session ended.")

        print("\n--- Execution Result ---")
        print(res.summary())
        print("\nFinal Outcome:\n", res.outcome)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user (Ctrl+C).")
    except Exception as e:
        logger.error(f"Fatal error in CLI runner: {e}", exc_info=True)
        print(f"\nError: CLI runner encountered an unhandled exception: {e}")


if __name__ == "__main__":
    main()
