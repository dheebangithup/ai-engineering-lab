"""
Prompt Registry: In-memory registry for versioned prompt provisioning and lifecycle management.
"""

from __future__ import annotations

import logging
from typing import Any

from knowledge_hub.app.prompts.prompt_template import PromptTemplate
from knowledge_hub.app.prompts.rendered_prompt import RenderedPrompt

logger = logging.getLogger("app")


class PromptRegistry:
    """
    Registry for managing enterprise prompt templates and versions.

    Key Features:
      - Register versioned prompt templates.
      - Retrieve active or explicit versioned templates.
      - Provision and render templates seamlessly.
      - Thread-safe, singleton-friendly prompt repository.
    """

    def __init__(self) -> None:
        # Structure: { prompt_name: { version: PromptTemplate } }
        self._templates: dict[str, dict[str, PromptTemplate]] = {}
        # Structure: { prompt_name: active_version_string }
        self._active_versions: dict[str, str] = {}
        logger.info("PromptRegistry: initialised prompt registry")

    def register(self, template: PromptTemplate, set_active: bool = True) -> None:
        """
        Registers a PromptTemplate in the registry.

        Args:
            template: The PromptTemplate instance to register.
            set_active: Whether to set this version as active default for the prompt name.
        """
        name = template.name
        version = template.version

        if name not in self._templates:
            self._templates[name] = {}

        if version in self._templates[name]:
            logger.warning(
                "PromptRegistry.register: overwriting existing prompt template '%s' version '%s'",
                name, version,
            )

        self._templates[name][version] = template
        logger.info(
            "PromptRegistry.register: registered prompt template '%s' [version=%s]",
            name, version,
        )

        if set_active or name not in self._active_versions or template.is_active:
            self._active_versions[name] = version
            logger.info(
                "PromptRegistry.register: set active version for prompt '%s' to '%s'",
                name, version,
            )

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        """
        Retrieves a prompt template by name and optional version.

        Args:
            name: Prompt identifier.
            version: Specific version string. If None, returns current active version.

        Returns:
            PromptTemplate

        Raises:
            KeyError: If prompt name or requested version does not exist.
        """
        if name not in self._templates:
            logger.error("PromptRegistry.get: prompt name '%s' not registered", name)
            raise KeyError(f"Prompt template '{name}' is not registered in registry.")

        if version is None:
            version = self._active_versions.get(name)
            if not version:
                logger.error("PromptRegistry.get: no active version found for prompt '%s'", name)
                raise KeyError(f"No active version set for prompt template '{name}'.")
            logger.debug("PromptRegistry.get: using active version '%s' for prompt '%s'", version, name)

        if version not in self._templates[name]:
            available = list(self._templates[name].keys())
            logger.error(
                "PromptRegistry.get: version '%s' not found for prompt '%s'. Available versions: %s",
                version, name, available,
            )
            raise KeyError(
                f"Version '{version}' for prompt '{name}' not found. Available versions: {available}"
            )

        return self._templates[name][version]

    def render(
        self,
        name: str,
        variables: dict[str, Any],
        version: str | None = None,
    ) -> RenderedPrompt:
        """
        Provisions and renders a registered prompt by name and optional version.

        Args:
            name: Prompt identifier.
            variables: Parameters to bind into the template.
            version: Specific version string or None for active version.

        Returns:
            RenderedPrompt
        """
        logger.info(
            "PromptRegistry.render: provisioning prompt '%s' [version=%s]",
            name, version or "active",
        )
        template = self.get(name=name, version=version)
        return template.render(variables=variables)

    def list_prompts(self) -> dict[str, list[str]]:
        """Returns map of prompt names to available version strings."""
        return {name: list(versions.keys()) for name, versions in self._templates.items()}

    def get_active_versions(self) -> dict[str, str]:
        """Returns map of prompt names to current active version string."""
        return dict(self._active_versions)


# Global singleton instance for app-wide prompt registry
prompt_registry = PromptRegistry()
