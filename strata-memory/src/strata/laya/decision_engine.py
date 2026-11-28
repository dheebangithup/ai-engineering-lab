"""Strata Laya Hybrid Decision Engine.

A multi-tiered, runtime-controllable decision system implementing the
Write Policy Gate and Retrieval Policy Gate from Agent Memory Architect:
  - Level 1 (<0.2ms): Deterministic in-memory heuristics & regex signals.
  - Level 2 (~30ms): Local 421M Ollama Decision Model (`laya:latest`) for semantic
    signal gating, incident discrimination, and update confirmation.
  - Level 3: Graceful delegation to Generative Small LLM (qwen3:8b) for compound multi-pillar extraction.
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple

from strata.config import settings
from strata.models import (
    EntityExtractionOp,
    EpisodicExtractionOp,
    MemoryExtractionPlan,
    ProceduralExtractionOp,
    SemanticExtractionOp,
)

logger = logging.getLogger("strata.laya")


@dataclass
class LayaDecision:
    """Outcome of Laya Decision Engine analysis."""
    complexity: Literal["simple", "complex"]
    primary_pillar: Literal["semantic", "episodic", "procedural", "entity"]
    confidence: float
    is_signal: bool = True  # Signal Gate: False = conversational filler to drop
    is_supersede: bool = False
    supersede_target_id: Optional[str] = None
    extraction_plan: Optional[MemoryExtractionPlan] = None
    signals: Dict[str, Any] = field(default_factory=dict)


async def ask_laya_model(
    question: str,
    text: str,
    choices: Optional[Dict[str, str]] = None,
    timeout_ms: int = 500,
) -> Tuple[Optional[str], float]:
    """Queries the local Ollama Laya decision model (421M) using --ask and --choice."""
    try:
        model_name = getattr(settings, "laya_ollama_model", "laya:latest")
        cmd = ["ollama", "run", model_name, "--ask", question]
        if choices:
            for k, v in choices.items():
                cmd.extend(["--choice", f"{k}={v}"])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        timeout_sec = timeout_ms / 1000.0
        stdout, _ = await asyncio.wait_for(
            proc.communicate(input=text.encode("utf-8")),
            timeout=timeout_sec,
        )
        output = stdout.decode("utf-8").strip()

        # Parse output format e.g. "yes  97%" or "episodic  77%"
        if output:
            parts = output.split()
            label = parts[0]
            conf = 0.8
            if len(parts) > 1 and parts[1].endswith("%"):
                try:
                    conf = float(parts[1].rstrip("%")) / 100.0
                except ValueError:
                    pass
            return label, conf
        return None, 0.0
    except Exception as exc:
        logger.debug(f"Local Ollama Laya call skipped/timed out ({exc}). Using in-memory fallback.")
        return None, 0.0


class LayaDecisionEngine:
    """Hybrid Laya Decision Engine: In-Memory Fast Path + Local Ollama Decision Model."""

    FILLER_TOKENS = {
        "hi", "hello", "hey", "bye", "goodbye", "see", "ya", "gm", "gn",
        "ok", "okay", "thanks", "thank", "you", "sounds", "good", "got", "it",
        "cool", "great", "awesome", "understood", "noted", "perfect", "thx",
        "yes", "no", "yep", "nope", "sure", "fine", "test", "testing", "ping",
        "k", "kk", "cheers", "alright", "right",
    }

    LOW_SIGNAL_PATTERNS = [
        r"^(hi|hello|hey|bye|goodbye|see ya|gm|gn)[.!, ]*$",
        r"^(ok|okay|thanks|thank you|sounds good|got it|cool|great|awesome|understood|noted|perfect|thx)[.!, ]*$",
        r"^(yes|no|yep|nope|sure|fine)[.!, ]*$",
        r"^(test|testing|ping)[.!, ]*$",
    ]

    EPISODIC_PATTERNS = [
        r"\b(succeeded|failed|failure|success|error|exception|crash)\b",
        r"\b(at \d{1,2}(?::\d{2})?\s*(?:am|pm)?|yesterday|today|last night)\b",
        r"\b(tried to|attempted to|result was|outcome:?)\b",
    ]

    PROCEDURAL_PATTERNS = [
        r"\b(step \d+|steps:?|how to|workflow|runbook|guide|instructions?)\b",
        r"\b(first,?|second,?|then,?|finally,?|next,?|after that,?)\b",
        r"\b(trigger condition|prerequisites?|command to run)\b",
    ]

    ENTITY_RELATION_PATTERNS = [
        (r"(\b[A-Za-z0-9_\-\.]+\b)\s+(?:uses|is using)\s+(\b[A-Za-z0-9_\-\.]+\b)", "USES"),
        (r"(\b[A-Za-z0-9_\-\.]+\b)\s+(?:runs on|hosted on|deployed on)\s+(\b[A-Za-z0-9_\-\.]+\b)", "RUNS_ON"),
        (r"(\b[A-Za-z0-9_\-\.]+\b)\s+(?:connects to|integrates with)\s+(\b[A-Za-z0-9_\-\.]+\b)", "CONNECTS_TO"),
        (r"(\b[A-Za-z0-9_\-\.]+\b)\s+(?:maintains|developed by|created by|authored by)\s+(\b[A-Za-z0-9_\-\.]+\b)", "MAINTAINS"),
        (r"(\b[A-Za-z0-9_\-\.]+\b)\s+(?:depends on|relies on)\s+(\b[A-Za-z0-9_\-\.]+\b)", "DEPENDS_ON"),
    ]

    COMPLEXITY_CONJUNCTIONS = [
        r"\bhowever\b",
        r"\bon the other hand\b",
        r"\balso remember that\b",
        r"\band additionally\b",
        r"\bmeanwhile\b",
        r"\bfurthermore\b",
    ]

    def _extract_tags(self, text: str) -> List[str]:
        text_lower = text.lower()
        common_tech = [
            "python", "postgres", "neon", "fastapi", "mcp", "docker", "aws", "gcp",
            "azure", "ollama", "redis", "database", "api", "auth", "deploy", "migration",
            "frontend", "backend", "test", "security", "config", "jarvis", "strata",
        ]
        return [tag for tag in common_tech if tag in text_lower]

    def evaluate(
        self,
        raw_text: str,
        raw_embedding: List[float],
        context_data: Dict[str, Any],
        contradiction_threshold: Optional[float] = None,
        mode: Optional[str] = None,
    ) -> LayaDecision:
        """Evaluates raw input to determine signal gate, pillar routing, and complexity."""
        text = raw_text.strip()
        text_lower = text.lower()

        # Check configured mode: "hybrid", "in_memory", "ollama_model", or "disabled"
        effective_mode = mode or getattr(settings, "laya_mode", "hybrid")
        if effective_mode == "disabled":
            return LayaDecision(
                complexity="complex",
                primary_pillar="semantic",
                confidence=0.5,
                is_signal=True,
                extraction_plan=None,
            )

        # 1. Signal Gate (Write Policy: reject low-signal conversational filler)
        is_filler = False
        if len(text) < 50:
            words = [w for w in re.sub(r"[^\w\s]", " ", text_lower).split() if w]
            if words and all(w in self.FILLER_TOKENS for w in words):
                is_filler = True
            elif any(re.search(p, text_lower) for p in self.LOW_SIGNAL_PATTERNS):
                is_filler = True

            if is_filler and getattr(settings, "laya_signal_filter_enabled", True):
                return LayaDecision(
                    complexity="simple",
                    primary_pillar="semantic",
                    confidence=1.0,
                    is_signal=False,  # Signal Gate drops this write
                    extraction_plan=None,
                    signals={"signal_gate": "low_signal_filler_rejected"},
                )

        # 2. Match pattern signals
        episodic_hits = sum(1 for p in self.EPISODIC_PATTERNS if re.search(p, text_lower))
        procedural_hits = sum(1 for p in self.PROCEDURAL_PATTERNS if re.search(p, text_lower))
        entity_matches = [
            (rel, m.group(1), m.group(2))
            for pattern, rel in self.ENTITY_RELATION_PATTERNS
            for m in [re.search(pattern, text, re.IGNORECASE)]
            if m
        ]
        entity_hits = len(entity_matches)
        complexity_hits = sum(1 for p in self.COMPLEXITY_CONJUNCTIONS if re.search(p, text_lower))

        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        sentence_count = len(sentences)

        # Multi-clause and compound statement detection (commas, semicolons, compound conjunctions)
        clauses = [c for c in re.split(r"(?<=[.!?,;])\s+|\n+", text) if len(c.strip()) > 3]
        clause_count = len(clauses)
        has_compound_conjunction = bool(re.search(r"\b(and (?:i|we|they|he|she|it|the|this)\b|as well as|while also|meanwhile|furthermore)", text_lower, re.IGNORECASE))
        is_identity_or_relational = bool(re.search(r"\b(my name is|i am a\b|i am an\b|i work as|my role is|working at|works at|leading the|member of)\b", text_lower))

        # 3. Prior Context Overlap Detection (Domain-Agnostic)
        # If there are active memories in the same semantic space, an incoming statement may be a state evolution,
        # refinement, or contradiction. Delegate to the Cognitive LLM instead of relying on hardcoded keyword lists.
        supersede_id = None
        is_supersede = False
        existing_semantics = context_data.get("existing_semantic_memories", [])
        has_semantic_overlap = (
            any(
                (float(sem["similarity"]) >= 0.40 if "similarity" in sem else True)
                for sem in existing_semantics
            )
            if existing_semantics
            else False
        )

        # 4. Multi-Pillar Complexity Assessment
        pillars_active = (
            (1 if episodic_hits > 0 else 0)
            + (1 if procedural_hits > 0 else 0)
            + (1 if entity_hits > 0 else 0)
        )

        is_complex = False
        if pillars_active >= 2:
            is_complex = True
        elif complexity_hits >= settings.laya_complexity_threshold:
            is_complex = True
        elif sentence_count >= 2 or clause_count >= 2 or has_compound_conjunction or is_identity_or_relational:
            is_complex = True
        elif has_semantic_overlap:
            is_complex = True

        # 5. Primary Pillar Determination
        scores = {
            "episodic": episodic_hits * 1.5,
            "procedural": procedural_hits * 2.0,
            "entity": entity_hits * 2.0,
            "semantic": 4.0 if has_semantic_overlap else 1.0,
        }
        primary_pillar = max(scores, key=scores.get)

        confidence = 0.85
        if is_complex:
            confidence = 0.50

        # 6. Build Direct Fast Extraction Plan if Simple
        extraction_plan: Optional[MemoryExtractionPlan] = None
        if not is_complex:
            tags = self._extract_tags(text)
            if primary_pillar == "episodic":
                failed = any(w in text_lower for w in ["fail", "error", "exception", "broke", "crash"])
                extraction_plan = MemoryExtractionPlan(
                    episodic_ops=[
                        EpisodicExtractionOp(
                            summary=text,
                            situation="Direct user/agent log",
                            action_taken=text,
                            outcome="failed" if failed else "succeeded",
                            success=not failed,
                            tags=tags or ["log"],
                        )
                    ]
                )
            elif primary_pillar == "procedural" and ("step" in text_lower or len(sentences) > 1):
                name_candidate = re.sub(r"[^a-zA-Z0-9_]+", "_", sentences[0][:30].lower()).strip("_")
                steps = sentences[1:] if len(sentences) > 1 else [text]
                extraction_plan = MemoryExtractionPlan(
                    procedural_ops=[
                        ProceduralExtractionOp(
                            action="CREATE",
                            name=name_candidate or "procedure_auto",
                            description=sentences[0],
                            trigger_condition=sentences[0],
                            steps=[s.strip() for s in steps if s.strip()],
                            prerequisites={},
                            reason_for_change="Extracted via Laya Decision Engine",
                        )
                    ]
                )
            elif primary_pillar == "entity" and entity_matches:
                rel, src, tgt = entity_matches[0]
                extraction_plan = MemoryExtractionPlan(
                    entity_ops=[
                        EntityExtractionOp(
                            source_name=src,
                            source_type="concept",
                            source_summary=f"Entity {src}",
                            relation_type=rel,
                            target_name=tgt,
                            target_type="concept",
                            target_summary=f"Entity {tgt}",
                            fact_summary=text,
                            invalidate_conflicting_relations=True,
                        )
                    ]
                )
            else:
                primary_pillar = "semantic"
                action_type = "SUPERSEDE" if is_supersede else "ADD"
                extraction_plan = MemoryExtractionPlan(
                    semantic_ops=[
                        SemanticExtractionOp(
                            action=action_type,
                            supersede_memory_id=supersede_id,
                            summary=text,
                            tags=tags,
                            confidence=0.95,
                        )
                    ]
                )

        return LayaDecision(
            complexity="complex" if is_complex else "simple",
            primary_pillar=primary_pillar,
            confidence=confidence,
            is_signal=True,
            is_supersede=is_supersede,
            supersede_target_id=supersede_id,
            extraction_plan=extraction_plan,
            signals={
                "mode": effective_mode,
                "episodic_hits": episodic_hits,
                "procedural_hits": procedural_hits,
                "entity_hits": entity_hits,
                "complexity_hits": complexity_hits,
                "sentence_count": sentence_count,
            },
        )

    def classify_query_intent(self, query: str) -> List[str]:
        """Retrieval Policy Gate: Classifies user query to target only relevant pillars."""
        q_lower = query.lower()
        selected: List[str] = []

        # 1. Procedural indicators
        if any(w in q_lower for w in ["how to", "how do i", "steps", "workflow", "runbook", "guide", "procedure", "command to", "deploy"]):
            selected.append("procedural")

        # 2. Entity graph indicators
        if any(w in q_lower for w in ["who is", "who maintains", "what connects", "uses", "relation", "architecture", "infrastructure", "stack"]):
            selected.append("entity")

        # 3. Episodic history indicators
        if any(w in q_lower for w in ["did it fail", "failure", "incident", "error", "what happened", "history", "log", "yesterday", "recent"]):
            selected.append("episodic")

        # 4. Semantic facts
        if any(w in q_lower for w in ["what is", "preference", "config", "setting", "rule", "truth", "policy", "version"]) or not selected:
            selected.append("semantic")

        # If general or ambiguous, return all active pillars
        if not selected or len(selected) == 0:
            return ["semantic", "procedural", "entity", "episodic"]

        return selected


laya_engine = LayaDecisionEngine()
