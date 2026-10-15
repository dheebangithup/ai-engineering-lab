from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional

import dotenv

# Ensure 'src' is available in sys.path
src_dir = Path(__file__).resolve().parent.parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from jarvis.config import load_env

# Auto-discover root .env regardless of working directory
load_env()

from jarvis.agent.reflexion import create_reflexion_graph
from jarvis.agent.supervisor import (
    AgentStatus,
    SupervisorState,
    create_supervisor_graph,
)
from jarvis.workspace import default_workspace


@dataclass
class AgentExecutionResult:
    """
    Structured outcome returned by the high-level JarvisAgent runner.
    """
    task: str
    success: bool
    outcome: str
    verdict: str
    trials: int
    plan: str
    reflection: str
    events: List[Dict[str, Any]] = field(default_factory=list)
    raw_state: Dict[str, Any] = field(default_factory=dict)
    worker: Optional[str] = None
    needs_human_input: bool = False
    clarification_question: Optional[str] = None

    def summary(self) -> str:
        if self.needs_human_input:
            return (
                f"[NEED_CLARIFICATION / HUMAN_INPUT]\n"
                f"Question: {self.clarification_question}"
            )
        status = "SUCCESS" if self.success else "FAILURE"
        worker_info = f" (Worker: {self.worker})" if self.worker else ""
        return (
            f"[{status}]{worker_info} Task completed in {self.trials} trial(s)\n"
            f"Verdict: {self.verdict}\n"
            f"Outcome: {self.outcome[:300]}..."
        )


class JarvisAgent:
    """
    High-level driver class and runner for the J.A.R.V.I.S. AI agent.
    Coordinates workflow graphs, tool execution, and reflection loops.
    """

    def __init__(
        self,
        workspace_dir: Optional[Path | str] = None,
        max_trials: int = 3,
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
        os.environ["JARVIS_WORKSPACE"] = str(self.workspace_dir)

        # Compile the execution graph (Supervisor by default or direct Reflexion)
        if self.use_supervisor:
            self._graph = create_supervisor_graph()
        else:
            self._graph = create_reflexion_graph()

    def run(
        self,
        task: str,
        max_trials: Optional[int] = None,
        human_response: Optional[str] = None,
    ) -> AgentExecutionResult:
        """
        Execute a task using the Hierarchical Supervisor or Reflexion agent graph.
        Returns a structured AgentExecutionResult.
        """
        if self.use_supervisor:
            initial_state: SupervisorState = {
                "task": task.strip(),
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

            state = self._graph.invoke(initial_state)
            status = state.get("status")
            needs_human = status == AgentStatus.NEED_HUMAN_INPUT
            is_success = status == AgentStatus.COMPLETED
            outcome = state.get("final_response") or state.get("human_input_prompt") or ""
            worker = state.get("selected_worker")

            result = AgentExecutionResult(
                task=task,
                success=is_success,
                outcome=outcome,
                verdict="SUCCESS" if is_success else ("NEED_CLARIFICATION" if needs_human else "FAILURE"),
                trials=state.get("iteration", 1),
                plan=state.get("routing_reason", ""),
                reflection="",
                events=state.get("worker_history", []),
                raw_state=state,
                worker=worker,
                needs_human_input=needs_human,
                clarification_question=state.get("human_input_prompt"),
            )
        else:
            trial_budget = max_trials if max_trials is not None else self.max_trials
            initial_state = {
                "task": task.strip(),
                "plan": "",
                "execution_outcome": "",
                "evaluation": {
                    "analysis": "",
                    "verdict": "FAILURE",
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

            state = self._graph.invoke(initial_state)
            evaluation = state.get("evaluation")
            verdict = getattr(evaluation, "verdict", "UNKNOWN") if evaluation else "UNKNOWN"
            is_success = verdict == "SUCCESS"

            result = AgentExecutionResult(
                task=task,
                success=is_success,
                outcome=state.get("execution_outcome", ""),
                verdict=verdict,
                trials=state.get("trial_number", 1),
                plan=state.get("plan", ""),
                reflection=state.get("reflection", ""),
                events=state.get("execution_events", []),
                raw_state=state,
                worker="reflexion",
            )

        if self.auto_save_results:
            self.save_result(result)

        return result

    def save_result(
        self,
        result: AgentExecutionResult,
        output_path: Optional[Path | str] = None,
    ) -> Path:
        """
        Persist execution state to a JSON file in the workspace results folder.
        """
        results_dir = self.workspace_dir / "results"
        results_dir.mkdir(parents=True, exist_ok=True)

        if output_path is not None:
            dest_file = Path(output_path).resolve()
        else:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            dest_file = results_dir / f"agent_run_{timestamp}.json"

        data = {
            "task": result.task,
            "success": result.success,
            "verdict": result.verdict,
            "trials": result.trials,
            "outcome": result.outcome,
            "plan": result.plan,
            "reflection": result.reflection,
            "events_count": len(result.events),
            "timestamp": datetime.now().isoformat(),
        }

        with open(dest_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        return dest_file


# Alias for runner naming preference
AgentRunner = JarvisAgent


def main():
    """CLI runner entry point."""
    from jarvis.workspace import initialize_workspace
    initialize_workspace()

    if len(sys.argv) > 1:
        task_query = " ".join(sys.argv[1:])
    else:
        task_query = (
            "Create a file named status.txt containing 'JARVIS online'. "
            "Verify the file exists and read its content."
        )

    print(f"\n--- Running J.A.R.V.I.S. Agent Runner ---")
    print(f"Task: {task_query}\n")

    agent = JarvisAgent()
    res = agent.run(task_query)

    # Interactive Human-in-the-Loop clarification/approval loop
    while res.needs_human_input:
        print("\n--- Clarification / Approval Required ---")
        print(f"Supervisor Question: {res.clarification_question}\n")
        try:
            user_input = input("Your response (or 'exit' to cancel): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting interactive session.")
            break

        if not user_input or user_input.lower() in ("exit", "quit"):
            print("Cancelled by user.")
            break

        res = agent.run(task_query, human_response=user_input)

    print("\n--- Execution Result ---")
    print(res.summary())
    print("\nFinal Outcome:\n", res.outcome)


if __name__ == "__main__":
    main()
