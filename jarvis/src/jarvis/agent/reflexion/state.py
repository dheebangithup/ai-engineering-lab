from enum import Enum
import operator
from typing import Annotated, Literal, TypedDict, Union

from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages
from pydantic import BaseModel, Field


class EvaluationVerdict(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class ReflexionNode(str, Enum):
    PLANNER = "planner_node"
    EXECUTOR = "executor_node"
    EVALUATOR = "evaluator_node"
    REFLECTION = "reflection_node"
    ANSWER = "answer_node"


class ReflexionRoute(str, Enum):
    FINISH = "finish"
    REFLECT_SUCCESS = "reflect_success"
    REFLECT_FAILURE = "reflect_failure"
    RETRY = "retry"


class EvaluatorState(BaseModel):
    verdict: Union[EvaluationVerdict, Literal["SUCCESS", "FAILURE"]]

    analysis: str = Field(
        description="Point-by-point analysis of the execution outcome "
                    "against the task's success criteria."
    )

    reason: str = Field(
        description="Concise explanation for the final verdict."
    )

    has_reusable_lesson: bool = Field(
        description="Whether the execution history contains a "
                    "meaningful, reusable lesson."
    )

    learning_reason: str = Field(
        description="Explanation of why the execution history "
                    "does or does not contain a reusable lesson."
    )


class ReflexionState(TypedDict):
    task: str
    plan: str
    execution_outcome: str
    evaluation: EvaluatorState
    reflection: str
    reflexion_memeory: Annotated[list[str], operator.add]
    execution_events: Annotated[list[dict], operator.add]
    trial_number: int
    max_trials: Annotated[int, "The maximum number of trials allowed for this task"]
    messages: Annotated[list[BaseMessage], add_messages]