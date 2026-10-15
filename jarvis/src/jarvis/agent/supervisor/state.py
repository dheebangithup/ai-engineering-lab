from dataclasses import dataclass, field
from enum import Enum
import operator
from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    NEED_HUMAN_INPUT = "need_human_input"  # Waiting for human clarification or approval
    ERROR = "error"
    COMPLETED = "completed"


class WorkerType(str, Enum):
    DIRECT = "direct"
    FAST_REACT = "fast_react"
    REFLEXION = "reflexion"


@dataclass
class WorkerResult:
    worker: str
    status: AgentStatus
    outcome: str
    needs_human_input: bool = False
    human_prompt: Optional[str] = None
    error: Optional[str] = None
    events: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "worker": self.worker,
            "status": self.status.value if isinstance(self.status, AgentStatus) else self.status,
            "outcome": self.outcome,
            "needs_human_input": self.needs_human_input,
            "human_prompt": self.human_prompt,
            "error": self.error,
            "events": self.events,
        }


class SupervisorState(TypedDict):
    """
    Central shared state for the Hierarchical Supervisor Agent.
    """
    task: str
    conversation_history: Annotated[List[Dict[str, str]], operator.add]
    status: AgentStatus
    selected_worker: Optional[str]
    worker_history: Annotated[List[Dict[str, Any]], operator.add]
    worker_result: Optional[Dict[str, Any]]
    human_input_prompt: Optional[str]
    human_input_response: Optional[str]
    final_response: Optional[str]
    routing_reason: Optional[str]
    iteration: int
    max_iterations: int
