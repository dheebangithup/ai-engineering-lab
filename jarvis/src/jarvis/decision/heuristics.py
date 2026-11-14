"""
Fast-path zero-LLM heuristics for the Decision Engine.
Resolves obvious conversational intents and simple queries in <1ms without calling an LLM.
"""

import re
from typing import Optional
from jarvis.decision.schemas import TaskClassification, TaskComplexity, TaskIntent

GREETINGS = {
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "jarvis", "hey jarvis", "hi jarvis", "hello jarvis", "yo"
}

CLOSINGS = {
    "bye", "goodbye", "see you", "exit", "quit", "thanks", "thank you", "thx",
    "thank you so much", "thanks a lot", "thank you very much", "appreciate it"
}


def evaluate_heuristics(query: str) -> Optional[TaskClassification]:
    """
    Attempt fast zero-LLM classification.
    Returns TaskClassification if a deterministic match is found, else None.
    """
    cleaned = query.strip().lower()
    # Remove simple punctuation
    cleaned_no_punct = re.sub(r"[!?,.]", "", cleaned).strip()

    # 1. Greetings
    if cleaned_no_punct in GREETINGS:
        return TaskClassification(
            complexity=TaskComplexity.SIMPLE,
            intent=TaskIntent.CONVERSATION,
            requires_planning=False,
            requires_memory_recall=False,
            suggested_agent="direct_agent",
            suggested_tool_categories=[],
            confidence=1.0,
            reasoning="Fast-path heuristic: User greeting",
            fast_path=True,
        )

    # 2. Closings & Gratitude
    if cleaned_no_punct in CLOSINGS:
        return TaskClassification(
            complexity=TaskComplexity.SIMPLE,
            intent=TaskIntent.CONVERSATION,
            requires_planning=False,
            requires_memory_recall=False,
            suggested_agent="direct_agent",
            suggested_tool_categories=[],
            confidence=1.0,
            reasoning="Fast-path heuristic: User closing or gratitude",
            fast_path=True,
        )

    return None
