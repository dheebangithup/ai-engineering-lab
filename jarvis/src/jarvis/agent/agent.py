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

    def summary(self) -> str:
        status = "SUCCESS" if self.success else "FAILURE"
        return (
            f"[{status}] Task completed in {self.trials} trial(s)\n"
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
    ) -> None:
        if workspace_dir is not None:
            self.workspace_dir = Path(workspace_dir).resolve()
        else:
            self.workspace_dir = default_workspace().root

        self.workspace_dir.mkdir(parents=True, exist_ok=True)
        self.max_trials = max_trials
        self.auto_save_results = auto_save_results

        # Set workspace environment variable for tool implementations
        os.environ["JARVIS_WORKSPACE"] = str(self.workspace_dir)

        # Compile the underlying execution graph
        self._graph = create_reflexion_graph()

    def run(
        self,
        task: str,
        max_trials: Optional[int] = None,
    ) -> AgentExecutionResult:
        """
        Execute a task using the Reflexion agent graph.
        Returns a structured AgentExecutionResult.
        """
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

        # Invoke the graph
        state = self._graph.invoke(initial_state)

        # Parse evaluation
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

    print("\n--- Execution Result ---")
    print(res.summary())
    print("\nFinal Outcome:\n", res.outcome)


if __name__ == "__main__":
    main()
