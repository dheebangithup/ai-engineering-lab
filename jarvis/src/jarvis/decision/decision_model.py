"""
Dedicated Decision Model for J.A.R.V.I.S.
Provides fast (<5ms), deterministic, structured complexity analysis and intent classification
without requiring a heavy generative LLM chat loop.
"""

import re
from typing import Any, Dict, List, Optional, Tuple
from jarvis.decision.schemas import TaskClassification, TaskComplexity, TaskIntent
from jarvis.logger import get_logger

logger = get_logger("decision.decision_model")


class DecisionModel:
    """
    Dedicated Decision Model.
    Analyzes complexity signals, task verbs, linguistic patterns, entity graphs,
    and workflow structures to produce accurate task classification.
    """

    # Complexity triggers
    COMPLEX_PATTERNS = [
        r"\b(refactor|architect|redesign|overhaul|re-architect|rewrite)\b",
        r"\b(microservices?|distributed|multi-stage|multi-step|pipeline|end-to-end)\b",
        r"\b(benchmark|load test|stress test|chaos test)\b",
        r"\b(across all|entire codebase|entire repository|all projects)\b",
        r"\b(step by step|comprehensive plan|deeply think|strategy)\b",
    ]

    MODERATE_PATTERNS = [
        r"\b(search and summarize|compare|analyze|extract and format)\b",
        r"\b(read .* and write|find .* and replace|fix bug|resolve error)\b",
        r"\b(inspect|audit|evaluate|verify)\b",
    ]

    # Durable memory signals (identity, preferences, tech stack, project facts, updates)
    DURABLE_FACT_PATTERNS = [
        r"\b(my name is|i am a|i am an|i'm a|i'm an|call me|i work as|my role is|my title is)\b",
        r"\b(i prefer|i like|i always|i never|my preference is|my favorite|i usually use)\b",
        r"\b(our project is|our stack is|we use|our database is|the architecture is|we are building|my repository is)\b",
        r"\b(remember this|keep in mind|note that|make a note of|save this info|store this)\b",
        r"\b(actually|correction|change my|update my|switch from|instead of|replace .* with|no longer|not anymore)\b",
        r"\b(update the (runbook|procedure|steps|guide|memory))\b",
    ]

    # Intent markers
    INTENT_MAP = [
        (TaskIntent.WEB_SEARCH, [
            r"\b(web search|google|duckduckgo|search the web|browse|look up online|latest news)\b",
            r"\b(check web|research online|find online|articles? on)\b",
        ]),
        (TaskIntent.FILE_PROCESSING, [
            r"\b(read file|write file|list files?|search files?|directory|folder|document|pdf|csv)\b",
            r"\b(parse file|edit file|delete file|workspace path)\b",
        ]),
        (TaskIntent.CODE_DEV, [
            r"\b(python|javascript|typescript|function|class|method|module|unit test|pytest|git)\b",
            r"\b(implement|code|syntax|exception|stack trace|pull request)\b",
        ]),
        (TaskIntent.SYSTEM_COMMAND, [
            r"\b(run command|execute command|shell|bash|terminal|cli|sub-process|daemon)\b",
        ]),
        (TaskIntent.MEMORY_QUERY, [
            r"\b(remember|recall|memory|past experience|what did we do|have I told you|runbook)\b",
            r"\b(forget|prune memory|store memory|ingest memory)\b",
        ]),
        (TaskIntent.PLANNING, [
            r"\b(plan|roadmap|milestone|phases?|strategy|architecture|break down)\b",
        ]),
    ]

    # Tool Category mapping
    TOOL_CATEGORY_SIGNALS = {
        "web": [r"\b(web|search|online|url|http|site|browser)\b"],
        "filesystem": [r"\b(file|folder|dir|directory|read|write|save|load|content|path)\b"],
        "shell": [r"\b(command|bash|terminal|exec|run|process|cli)\b"],
        "memory": [r"\b(memory|recall|remember|learned|experience|strata|history)\b"],
    }

    def evaluate(self, query: str, context: Optional[str] = None) -> TaskClassification:
        """
        Evaluate task query using the Decision Model.
        Produces deterministic, sub-5ms classification.
        """
        text = query.strip()
        text_lower = text.lower()

        # 1. Complexity Signals
        complex_hits = sum(1 for p in self.COMPLEX_PATTERNS if re.search(p, text_lower))
        moderate_hits = sum(1 for p in self.MODERATE_PATTERNS if re.search(p, text_lower))
        
        words = text.split()
        word_count = len(words)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        sentence_count = len(sentences)

        # 2. Determine Complexity
        if complex_hits > 0 or word_count > 35 or sentence_count >= 3:
            complexity = TaskComplexity.COMPLEX
            requires_planning = True
            confidence = 0.95
            reason = f"Decision Model: Identified {complex_hits} complexity triggers and {sentence_count} stages"
        elif moderate_hits > 0 or word_count > 12 or sentence_count == 2:
            complexity = TaskComplexity.MODERATE
            requires_planning = False
            confidence = 0.90
            reason = f"Decision Model: Identified moderate multi-tool workflow ({moderate_hits} signals)"
        else:
            complexity = TaskComplexity.SIMPLE
            requires_planning = False
            confidence = 0.95
            reason = "Decision Model: Single-step or direct stimulus-response"

        # 3. Detect Intent
        detected_intent = TaskIntent.CONVERSATION
        best_intent_hits = 0
        for intent, patterns in self.INTENT_MAP:
            hits = sum(1 for p in patterns if re.search(p, text_lower))
            if hits > best_intent_hits:
                best_intent_hits = hits
                detected_intent = intent

        # If complex and no specific intent matched, default to PLANNING
        if complexity == TaskComplexity.COMPLEX and detected_intent == TaskIntent.CONVERSATION:
            detected_intent = TaskIntent.PLANNING

        # 4. Map Suggested Tools
        suggested_tools: List[str] = []
        for cat, patterns in self.TOOL_CATEGORY_SIGNALS.items():
            if any(re.search(p, text_lower) for p in patterns):
                suggested_tools.append(cat)

        # Every non-conversational task benefits from memory
        if detected_intent != TaskIntent.CONVERSATION and "memory" not in suggested_tools:
            suggested_tools.append("memory")

        # Check durable memory signals (identity, user preferences, project facts)
        has_durable_facts = any(re.search(p, text_lower) for p in self.DURABLE_FACT_PATTERNS)
        if has_durable_facts and "memory" not in suggested_tools:
            suggested_tools.append("memory")

        # 5. Map Suggested Agent
        if complexity == TaskComplexity.COMPLEX or detected_intent == TaskIntent.PLANNING:
            suggested_agent = "planning_agent"
        elif detected_intent == TaskIntent.WEB_SEARCH:
            suggested_agent = "research_agent"
        elif detected_intent == TaskIntent.CODE_DEV:
            suggested_agent = "code_agent"
        elif complexity == TaskComplexity.MODERATE:
            suggested_agent = "reflex_agent"
        else:
            suggested_agent = "direct_agent"

        # 6. Extract Entity Candidates
        entities = self._extract_entities(text)

        classification = TaskClassification(
            complexity=complexity,
            intent=detected_intent,
            requires_planning=requires_planning,
            requires_memory_recall=True,  # Default mandatory memory grounding across all agents
            requires_memory_ingest=has_durable_facts,
            suggested_agent=suggested_agent,
            suggested_tool_categories=suggested_tools,
            confidence=confidence,
            reasoning=reason,
            extracted_entities=entities,
            fast_path=True,
        )

        logger.info(
            f"Decision Model evaluated '{text[:40]}...': "
            f"complexity={classification.complexity.value}, "
            f"intent={classification.intent.value}, "
            f"agent={classification.suggested_agent}"
        )
        return classification

    def _extract_entities(self, text: str) -> List[str]:
        """Extract potential technical terms, filenames, and capital identifiers."""
        candidates = set()
        # Identity patterns like "my name is <Name>", "call me <Name>"
        for match in re.finditer(r"(?:my name is|call me|i am|i'm)\s+([A-Z][a-zA-Z]+)", text, re.IGNORECASE):
            candidates.add(match.group(1))
        # CamelCase or snake_case or dotted paths
        for match in re.finditer(r"\b([A-Za-z0-9_]+(?:\.[a-z0-9]+|_v\d+))\b", text):
            candidates.add(match.group(1))
        # Words in quotes
        for match in re.finditer(r"['\"]([^'\"]+)['\"]", text):
            candidates.add(match.group(1))
        return sorted(list(candidates))[:5]
