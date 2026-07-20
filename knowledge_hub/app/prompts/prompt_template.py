"""
PromptTemplate domain model representing versioned, templateable prompts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from knowledge_hub.app.prompts.rendered_prompt import RenderedPrompt

logger = logging.getLogger("app")


@dataclass
class PromptTemplate:
    """
    Enterprise Prompt Template model supporting versioning and dynamic parameter binding.

    Attributes:
        name: Identifier for the prompt (e.g. 'rag_qa')
        version: Version string (e.g. 'v1.0.0')
        system_prompt: System prompt template string with {placeholders}
        user_template: User prompt template string with {placeholders}
        description: Human-readable description of prompt purpose
        input_variables: List of required variable names for template rendering
        is_active: Whether this version is marked as default/active
    """
    name: str
    version: str
    system_prompt: str
    user_template: str
    description: str = ""
    input_variables: list[str] = field(default_factory=list)
    is_active: bool = True

    def render(self, variables: dict[str, Any]) -> RenderedPrompt:
        """
        Renders the prompt template using provided variable dictionary.

        Args:
            variables: Dict containing parameter values matching input_variables.

        Returns:
            RenderedPrompt instance.

        Raises:
            ValueError: If required input variables are missing.
        """
        logger.debug(
            "PromptTemplate.render: rendering prompt '%s' [version=%s]",
            self.name, self.version,
        )

        missing_vars = [var for var in self.input_variables if var not in variables]
        if missing_vars:
            logger.error(
                "PromptTemplate.render: missing required variables for prompt '%s' [version=%s]: missing=%s, provided=%s",
                self.name, self.version, missing_vars, list(variables.keys()),
            )
            raise ValueError(
                f"Missing required variables for prompt '{self.name}' [v{self.version}]: {missing_vars}"
            )

        try:
            rendered_system = self.system_prompt.format(**variables)
            rendered_user = self.user_template.format(**variables)
            
            logger.info(
                "PromptTemplate.render: successfully rendered prompt '%s' [version=%s]",
                self.name, self.version,
            )
            return RenderedPrompt(
                system_prompt=rendered_system,
                user_prompt=rendered_user,
                prompt_name=self.name,
                version=self.version,
                variables_used=variables,
            )
        except Exception as e:
            logger.error(
                "PromptTemplate.render: formatting error for prompt '%s' [version=%s]: %s",
                self.name, self.version, str(e),
                exc_info=True,
            )
            raise RuntimeError(
                f"Failed to render prompt '{self.name}' [v{self.version}]: {str(e)}"
            ) from e
