from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from jarvis.agent.agent import AgentExecutionResult, AgentRunner, JarvisAgent


def __getattr__(name: str):
    if name in ("JarvisAgent", "AgentRunner", "AgentExecutionResult"):
        from jarvis.agent.agent import (
            AgentExecutionResult,
            AgentRunner,
            JarvisAgent,
        )
        mapping = {
            "JarvisAgent": JarvisAgent,
            "AgentRunner": AgentRunner,
            "AgentExecutionResult": AgentExecutionResult,
        }
        return mapping[name]
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    "JarvisAgent",
    "AgentRunner",
    "AgentExecutionResult",
]