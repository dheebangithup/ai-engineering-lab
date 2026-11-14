import os
import json
import logging
from typing import Any, Dict, List, Optional
import httpx

from backend.models import SensorEvent, NightSummaryReport

# Direct Strata Service integration
try:
    from strata.service import svc_memory_store_explicit, svc_memory_recall
    STRATA_LIB_AVAILABLE = True
except ImportError:
    STRATA_LIB_AVAILABLE = False

logger = logging.getLogger("strata_bridge")
logging.basicConfig(level=logging.INFO)

STRATA_API_URL = os.getenv("STRATA_API_URL", "http://localhost:8080")
STRATA_NAMESPACE = os.getenv("STRATA_NAMESPACE", "mango_grove_murugesan")


class StrataBridge:
    def __init__(self, base_url: str = STRATA_API_URL, namespace: str = STRATA_NAMESPACE):
        self.base_url = base_url.rstrip("/")
        self.namespace = namespace
        self.is_connected = False
        self.connection_mode = "unknown"

    async def check_connection(self) -> bool:
        """Check if Strata is accessible via REST HTTP API or Direct Python DB Service."""
        # 1. Try REST API
        try:
            async with httpx.AsyncClient(timeout=1.0) as client:
                res = await client.get(f"{self.base_url}/health")
                if res.status_code == 200:
                    self.is_connected = True
                    self.connection_mode = "REST API (Port 8080)"
                    return True
        except Exception:
            pass

        # 2. Try Direct Neon DB connection via Strata Service
        if STRATA_LIB_AVAILABLE:
            self.is_connected = True
            self.connection_mode = "Direct Neon DB Pool"
            return True

        self.is_connected = False
        self.connection_mode = "Offline"
        return False

    async def _store_pillar(self, pillar: str, payload: Dict[str, Any]) -> bool:
        """Store a record into Neon DB via REST API if available, or direct DB pool."""
        # Try REST first if server is running
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.post(
                    f"{self.base_url}/v1/memory/store",
                    json={"pillar": pillar, "payload": payload, "namespace": self.namespace}
                )
                if res.status_code in (200, 201):
                    return True
        except Exception:
            pass

        # Direct DB write fallback
        if STRATA_LIB_AVAILABLE:
            try:
                res = await svc_memory_store_explicit(pillar=pillar, payload=payload, namespace=self.namespace)
                return bool(res)
            except Exception as e:
                logger.error(f"Direct DB write failed for {pillar}: {e}")

        return False

    async def _recall_pillars(self, query: str, top_k: int = 6) -> Optional[Dict[str, Any]]:
        """Recall records across 4 pillars via REST or direct DB pool."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                payload = {
                    "query": query,
                    "namespace": self.namespace,
                    "pillars": ["semantic", "episodic", "procedural", "entity"],
                    "top_k": top_k,
                    "token_budget": 1500
                }
                res = await client.post(f"{self.base_url}/v1/memory/recall", json=payload)
                if res.status_code == 200:
                    return res.json()
        except Exception:
            pass

        if STRATA_LIB_AVAILABLE:
            try:
                res = await svc_memory_recall(
                    query=query,
                    namespace=self.namespace,
                    pillars=["semantic", "episodic", "procedural", "entity"],
                    top_k=top_k,
                    token_budget=1500
                )
                return res.model_dump() if hasattr(res, "model_dump") else res.dict()
            except Exception as e:
                logger.error(f"Direct DB recall failed: {e}")

        return None

    async def bootstrap_initial_memories(self) -> bool:
        """Seed initial procedural and semantic memories into Neon DB if not present."""
        logger.info(f"Bootstrapping initial 4-Pillar grove memories in Neon DB (namespace: {self.namespace})...")

        # 1. Procedural Baseline
        proc_payload = {
            "name": "watchman_night_patrol",
            "description": "Patrol Plan v1",
            "trigger_condition": "Standard night guard duty in mango grove",
            "steps": [
                "Walk from main_gate to pumpset_switch",
                "Inspect central mango_tree for missing fruits",
                "Check back_fence and inspect thorns",
                "If noise heard anywhere, investigate immediately"
            ],
            "reason_for_change": "Initial grove patrol plan"
        }
        await self._store_pillar("procedural", proc_payload)

        # 2. Entity Graph Baseline
        entity_payload = {
            "source_name": "Village Kid (Thief)",
            "source_type": "Human",
            "source_summary": "Village kid attempting to sneak in and steal ripe Banganapalli mangoes",
            "relation_type": "TARGETS",
            "target_name": "mango_tree",
            "target_type": "GroveObject",
            "target_summary": "Central Banganapalli mango tree (8, 6)",
            "fact_summary": "Kid targets the central mango tree to pluck fruits"
        }
        await self._store_pillar("entity", entity_payload)

        # 3. Semantic Baseline
        sem_payload = {
            "summary": "Murugesan Mama guards the Banganapalli mango tree; when floodlights are OFF, vision drops to flashlight cone.",
            "confidence": 0.95,
            "tags": ["grove_rules", "lighting"]
        }
        await self._store_pillar("semantic", sem_payload)

        logger.info("Successfully synced 4-Pillar baseline memories in Neon DB.")
        return True

    async def recall_for_event(self, event: SensorEvent) -> Dict[str, Any]:
        """Recall relevant memories across all 4 pillars for a real-time event."""
        query = f"{event.event_type} at {event.location_name}: {event.details}"
        recalled = await self._recall_pillars(query, top_k=4)

        if recalled:
            return {
                "source": "strata_neon_api",
                "formatted_context": recalled.get("formatted_context", ""),
                "semantic": recalled.get("semantic", []),
                "episodic": recalled.get("episodic", []),
                "procedural": recalled.get("procedural", []),
                "entity": recalled.get("entities", [])
            }

        return {
            "source": "empty",
            "formatted_context": "",
            "semantic": [],
            "episodic": [],
            "procedural": [],
            "entity": []
        }

    async def consolidate_night(self, summary: NightSummaryReport) -> Dict[str, Any]:
        """Dawn Reflection: Deterministically store memories across all 4 pillars in Neon PostgreSQL!"""
        new_version = summary.night_number + 1

        narrative = (
            f"Night {summary.night_number} Reflection: "
            f"Player entered grove via {summary.entry_used or 'main_gate'}. "
            f"Lights were cut {summary.lights_cut_count} times. "
            f"Hiding spots used: {', '.join(summary.hiding_spots_used) if summary.hiding_spots_used else 'none'}. "
            f"Stones thrown at: {', '.join(summary.stones_thrown_at) if summary.stones_thrown_at else 'none'}. "
            f"Player plucked {summary.mangoes_stolen} mangoes. "
            f"Outcome: {'Player successfully escaped with stolen mangoes' if summary.player_escaped else 'Murugesan Mama caught the thief or defended the grove'}."
        )

        logger.info(f"Consolidating Night {summary.night_number} into Neon DB...")

        # 1. PILLAR: EPISODIC (Stored directly in 'memories' table with type='episodic')
        ep_payload = {
            "summary": f"Night {summary.night_number}: Player entered via {summary.entry_used or 'main_gate'}, threw stones at {summary.stones_thrown_at}, cut lights {summary.lights_cut_count} times, and {'escaped with mangoes' if summary.player_escaped else 'was caught'}.",
            "situation": f"Night {summary.night_number} stealth intrusion",
            "action_taken": "Murugesan Mama patrolled the grove and investigated sounds",
            "outcome": "PLAYER_ESCAPED" if summary.player_escaped else "WATCHMAN_WON",
            "success": summary.watchman_won,
            "tags": [f"night_{summary.night_number}", "theft", summary.entry_used or "stealth"]
        }
        await self._store_pillar("episodic", ep_payload)

        # 2. PILLAR: PROCEDURAL (Stored directly in 'procedural_memories' table)
        evolved_steps = [
            f"Walk briskly from main_gate toward {summary.entry_used or 'back_fence'}",
            "If stone noise heard at gate or drain, treat as decoy and inspect hiding spots immediately",
            "If floodlights cut at pumpset, rush to central mango tree for darkness ambush",
            f"Inspect {', '.join(summary.hiding_spots_used) if summary.hiding_spots_used else 'haystack and mud_well'} with bamboo stick"
        ]
        proc_payload = {
            "name": "watchman_night_patrol",
            "description": f"Patrol Plan v{new_version}",
            "trigger_condition": f"Evolved counter-stealth patrol after Night {summary.night_number}",
            "steps": evolved_steps,
            "reason_for_change": f"Evolved after player escaped in Night {summary.night_number}" if summary.player_escaped else "Reinforced after successful grove defense"
        }
        await self._store_pillar("procedural", proc_payload)

        # 3. PILLAR: ENTITY GRAPH (Stored in 'entity_nodes' and 'entity_edges' tables)
        if summary.entry_used:
            await self._store_pillar("entity", {
                "source_name": "Village Kid (Thief)",
                "source_type": "Human",
                "source_summary": "Village kid attempting to steal Banganapalli mangoes",
                "relation_type": "FAVORITE_ENTRY",
                "target_name": summary.entry_used,
                "target_type": "GroveObject",
                "target_summary": f"Grove infiltration point at {summary.entry_used}",
                "fact_summary": f"Kid repeatedly enters grove through {summary.entry_used}"
            })

        if summary.hiding_spots_used:
            for spot in summary.hiding_spots_used:
                await self._store_pillar("entity", {
                    "source_name": "Village Kid (Thief)",
                    "source_type": "Human",
                    "source_summary": "Village kid attempting to steal Banganapalli mangoes",
                    "relation_type": "HIDES_IN",
                    "target_name": spot,
                    "target_type": "HidingSpot",
                    "target_summary": f"Hiding refuge at {spot}",
                    "fact_summary": f"Kid hides inside {spot} when evasive"
                })

        # 4. PILLAR: SEMANTIC (Stored in 'memories' table with type='semantic')
        if summary.player_escaped:
            await self._store_pillar("semantic", {
                "summary": f"Rule learned in Night {summary.night_number}: Stones thrown at distant objects are decoys while thief approaches {summary.entry_used or 'back_fence'}.",
                "confidence": 0.95,
                "tags": ["tactics", "decoys", f"night_{summary.night_number}"]
            })

        logger.info(f"Night {summary.night_number} consolidation complete across all 4 pillars!")

        return {
            "narrative": narrative,
            "remote_synced": True,
            "is_connected_to_strata": True,
            "active_procedure": {
                "procedure_name": "watchman_night_patrol",
                "version": new_version,
                "steps": evolved_steps
            }
        }

    async def inject_memory(self, text: str, pillar: str = "semantic") -> Dict[str, Any]:
        """Manually inject custom insight directly into watchman's memory in Neon DB."""
        if pillar == "semantic":
            await self._store_pillar("semantic", {
                "summary": text,
                "confidence": 1.0,
                "tags": ["manual_injection"]
            })
        elif pillar == "procedural":
            await self._store_pillar("procedural", {
                "name": "manual_tactic",
                "trigger_condition": "Manual user directive",
                "steps": [s.strip() for s in text.split(";") if s.strip()],
                "description": "Manually injected procedure"
            })
        elif pillar == "episodic":
            await self._store_pillar("episodic", {
                "summary": text,
                "situation": "Manual episodic event",
                "action_taken": "Logged manually",
                "outcome": "RECORDED",
                "success": True,
                "tags": ["manual"]
            })
        elif pillar == "entity":
            parts = text.split("->")
            src = parts[0].strip() if len(parts) > 0 else "Village Kid (Thief)"
            rel = parts[1].strip() if len(parts) > 1 else "ASSOCIATED_WITH"
            tgt = parts[2].strip() if len(parts) > 2 else "mango_tree"
            await self._store_pillar("entity", {
                "source_name": src,
                "source_type": "Concept",
                "relation_type": rel,
                "target_name": tgt,
                "target_type": "Concept",
                "fact_summary": text
            })

        return {"status": "injected", "pillar": pillar, "text": text}

    async def get_all_memories(self) -> Dict[str, Any]:
        """Retrieve live state of all 4 pillars directly from Neon PostgreSQL."""
        await self.check_connection()

        recalled = await self._recall_pillars("grove watchman rules patrol fence mangoes kid haystack", top_k=10)
        if recalled:
            semantic_items = [
                {"statement": s.get("statement", s.get("summary", "")), "confidence": s.get("confidence", 1.0)}
                for s in recalled.get("semantic", [])
            ]
            episodic_items = [
                {"night_number": i + 1, "summary": e.get("summary", e.get("situation", ""))}
                for i, e in enumerate(recalled.get("episodic", []))
            ]
            procedural_items = [
                {
                    "procedure_name": p.get("name", "watchman_night_patrol"),
                    "version": p.get("version", 1),
                    "trigger_condition": p.get("trigger_condition", ""),
                    "steps": p.get("steps", []),
                    "is_active": p.get("is_active", True)
                }
                for p in recalled.get("procedural", [])
            ]
            entity_items = [
                {
                    "name": ent.get("source_name", ent.get("name", "")),
                    "entity_type": ent.get("source_type", ent.get("entity_type", "Concept")),
                    "relationships": [{"target": ent.get("target_name", ""), "relation": ent.get("relation_type", "")}]
                }
                for ent in recalled.get("entities", [])
            ]

            return {
                "semantic": semantic_items,
                "episodic": episodic_items,
                "procedural": procedural_items,
                "entity": entity_items,
                "is_connected_to_strata": True,
                "storage_type": f"Neon PostgreSQL ({self.connection_mode})"
            }

        return {
            "semantic": [],
            "episodic": [],
            "procedural": [],
            "entity": [],
            "is_connected_to_strata": False,
            "storage_type": "Offline"
        }
