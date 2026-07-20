from dataclasses import dataclass, field
from typing import Any


@dataclass
class RenderedPrompt:
    """
    Data payload resulting from rendering a versioned prompt template.
    Ready to be consumed by LLM service clients.
    """
    system_prompt: str
    user_prompt: str
    prompt_name: str
    version: str
    variables_used: dict[str, Any] = field(default_factory=dict)

    def to_messages(self) -> list[dict[str, str]]:
        """Format as standard OpenAI/OpenAPI chat completion messages."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]
