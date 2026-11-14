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


@dataclass
class LayaDecision:
    """Outcome of Laya Decision Engine analysis."""
    complexity: Literal["simple", "complex"]
    primary_pillar: Literal["semantic", "episodic", "procedural", "entity"]
    confidence: float
    is_supersede: bool = False
    supersede_target_id: Optional[str] = None
    extraction_plan: Optional[MemoryExtractionPlan] = None
    signals: Dict[str, Any] = field(default_factory=dict)


class LayaDecisionEngine:
    """Laya Decision Model: Fast pre-routing & classification layer (<5ms).

    Determines whether incoming unstructured text can be directly decomposed
    and routed to the appropriate memory pillar without waking up an LLM,
    or if it contains multi-pillar complexity that requires the generative Small LLM.
    """

    # Keyword and regex signals for each pillar
    EPISODIC_PATTERNS = [
        r"\b(succeeded|failed|failure|success|error|exception|crash|incident)\b",
        r"\b(deployed|built|tested|executed|ran|restarted|migrated|created)\b",
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
        """Extracts common domain keywords as tags."""
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
    ) -> LayaDecision:
        """Evaluates raw input against pre-fetched context to determine routing & complexity."""
        text = raw_text.strip()
        text_lower = text.lower()
        threshold = (
            contradiction_threshold
            if contradiction_threshold is not None
            else settings.contradiction_threshold
        )

        # 1. Match signals
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

        # Sentence count heuristic (avoid splitting on decimal numbers like 3.12 or v1.5)
        sentences = [s for s in re.split(r"(?<=[.!?])\s+|\n+", text) if s.strip()]
        sentence_count = len(sentences)

        # 2. Check for contradiction / auto-supersede against pre-fetched semantic memories
        supersede_id = None
        is_supersede = False
        existing_semantics = context_data.get("existing_semantic_memories", [])
        # If the input explicitly signals an update/correction:
        update_indicators = ["update:", "change:", "correction:", "no longer", "instead of", "replaced"]
        has_update_signal = any(ind in text_lower for ind in update_indicators)

        if existing_semantics:
            top_sem = existing_semantics[0]
            if has_update_signal:
                supersede_id = top_sem.get("id")
                is_supersede = True

        # 3. Assess multi-pillar complexity
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
        elif sentence_count >= 2 and not has_update_signal:
            # Multi-sentence input contains multiple facts/entities -> delegate to generative Small LLM
            is_complex = True

        # 4. Determine Primary Pillar
        scores = {
            "episodic": episodic_hits * 1.5,
            "procedural": procedural_hits * 2.0,
            "entity": entity_hits * 2.0,
            "semantic": 1.0,  # Baseline default fact
        }
        primary_pillar = max(scores, key=scores.get)

        confidence = 0.85
        if is_complex:
            confidence = 0.50

        # 5. Build Direct Extraction Plan if Simple
        extraction_plan: Optional[MemoryExtractionPlan] = None
        if not is_complex:
            tags = self._extract_tags(text)
            if primary_pillar == "episodic":
                # Determine outcome & success
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
                # Simple procedural extraction
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
                            reason_for_change="Extracted via Laya Decision Model",
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
                # Default to semantic fact
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
            is_supersede=is_supersede,
            supersede_target_id=supersede_id,
            extraction_plan=extraction_plan,
            signals={
                "episodic_hits": episodic_hits,
                "procedural_hits": procedural_hits,
                "entity_hits": entity_hits,
                "complexity_hits": complexity_hits,
                "sentence_count": sentence_count,
            },
        )


laya_engine = LayaDecisionEngine()
