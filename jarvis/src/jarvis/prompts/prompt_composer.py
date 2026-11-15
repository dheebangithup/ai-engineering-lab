"""
Prompt Composer for J.A.R.V.I.S.
Assembles layered runtime prompts by composing Core System Identity + Agent Persona +
Recalled Memory XML + Meta-Tools Instructions + Conversation History.
"""

from typing import Any, Dict, List, Optional
from jarvis.llm.schemas import LLMMessage, MessageRole
from jarvis.prompts.prompt_templates import (
    JARVIS_CORE_SYSTEM,
    MEMORY_INJECTION_PROMPT,
    TEMPLATES,
)
from jarvis.prompts.schemas import PromptContext, PromptTemplate
from jarvis.workspace import get_workspace


class PromptComposer:
    """Central prompt composition engine for J.A.R.V.I.S."""

    def __init__(self, templates: Optional[Dict[str, PromptTemplate]] = None):
        self.templates = templates or TEMPLATES.copy()

    def get_template(self, template_id: str) -> PromptTemplate:
        """Retrieve an agent template or fallback to direct_agent."""
        return self.templates.get(template_id, self.templates["direct_agent"])

    def compose_system_prompt(
        self,
        template_id: str,
        context: PromptContext,
    ) -> str:
        """
        Layered system prompt composition:
        1. Core JARVIS Persona & Rules
        2. Agent Template Instructions
        3. Recalled Strata Memory Context (if present)
        4. Workspace & Environment Sandbox Boundaries
        5. Response Guidelines
        """
        template = self.get_template(template_id)
        sections = [JARVIS_CORE_SYSTEM.strip()]

        # 2. Agent Archetype Instructions
        sections.append(f"### Current Role: {template.name}\n{template.system_instructions.strip()}")

        # 3. Workspace Sandbox context
        ws = get_workspace()
        sections.append(
            f"### Active Workspace Sandbox:\n"
            f"Root: {ws.root_dir}\n"
            f"Code/Artifacts: {ws.code_workspace_dir}\n"
            f"All file creation and code generation must be rooted inside this directory."
        )

        # 4. Injected Memory Context (Strata 4-Pillar Memory)
        if context.memory_context and context.memory_context.strip():
            sections.append(
                MEMORY_INJECTION_PROMPT.format(memory_context=context.memory_context.strip()).strip()
            )

        # 5. Response Guidelines
        if template.response_guidelines:
            guidelines_text = "\n".join(f"- {g}" for g in template.response_guidelines)
            sections.append(f"### Response Guidelines:\n{guidelines_text}")

        # 6. Custom/Session Instructions
        if context.custom_instructions:
            sections.append(f"### Specific Directives:\n{context.custom_instructions.strip()}")

        return "\n\n".join(sections)

    def compose_messages(
        self,
        template_id: str,
        context: PromptContext,
    ) -> List[LLMMessage]:
        """
        Build complete list of messages including composed system prompt,
        prior conversation turns, and current user query.
        """
        system_content = self.compose_system_prompt(template_id, context)
        messages: List[LLMMessage] = [
            LLMMessage(role=MessageRole.SYSTEM, content=system_content)
        ]

        # Append prior conversation session history
        for item in context.session_history:
            role = item.get("role", "user")
            content = item.get("content", "")
            messages.append(LLMMessage(role=MessageRole(role), content=content))

        # Append current user prompt
        messages.append(LLMMessage(role=MessageRole.USER, content=context.query))

        return messages
