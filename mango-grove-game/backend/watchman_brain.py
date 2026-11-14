import os
import re
import json
import logging
from typing import Any, Dict, List, Optional
import httpx
from openai import AsyncOpenAI
from backend.models import SensorEvent, WatchmanDecision, WatchmanActionType
from backend.strata_bridge import StrataBridge

logger = logging.getLogger("watchman_brain")
logging.basicConfig(level=logging.INFO)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DECISION_MODEL = os.getenv("DECISION_MODEL", "laya")
NARRATIVE_MODEL = os.getenv("NARRATIVE_MODEL", "qwen3:8b")

OBJECT_COORDS = {
    "main_gate": [8, 0],
    "back_fence": [15, 8],
    "drain_pipe": [0, 9],
    "pumpset_switch": [2, 3],
    "mango_tree": [8, 6],
    "haystack": [3, 9],
    "mud_well": [11, 9]
}


class WatchmanBrain:
    def __init__(self, strata: StrataBridge):
        self.strata = strata
        self.client = AsyncOpenAI(
            base_url=f"{OLLAMA_BASE_URL}/v1",
            api_key="ollama"
        )

    async def decide_action(self, event: SensorEvent) -> WatchmanDecision:
        """
        Synthesize sensor event with recalled Strata 4-Pillar memory to produce
        the next tactical decision and authentic village Tamil dialogue.
        """
        # Step 1: Recall relevant memories from Strata engine
        recalled = await self.strata.recall_for_event(event)

        # Step 2: Spotting player is high priority immediate pursuit
        if event.event_type == "PLAYER_SPOTTED":
            return WatchmanDecision(
                action="CHASE",
                target_object="player",
                target_tile=[event.tile_x, event.tile_y],
                dialogue_ta="டேய்! நில்லுடா திருட்டுப் பயலே! மாம்பழத்தையா திருட பாக்குற?!",
                dialogue_en="Hey! Stop right there, thief! Trying to steal my mangoes?!",
                reasoning="Player spotted directly in flashlight vision cone. Immediate pursuit.",
                confidence=1.0,
                recalled_memories=recalled
            )

        # Step 3: Check Strata memories for tactical adjustments (Decoys, Ambush, Hiding spot counter)
        decision = self._evaluate_memory_heuristics(event, recalled)
        if decision:
            return decision

        # Step 4: If local LLM is available, consult model for nuanced dialogue / action
        llm_decision = await self._query_llm_decision(event, recalled)
        if llm_decision:
            return llm_decision

        # Step 5: Default fallback action
        return self._default_action(event, recalled)

    def _evaluate_memory_heuristics(self, event: SensorEvent, recalled: Dict[str, Any]) -> Optional[WatchmanDecision]:
        """Fast <15ms memory-conditioned tactical rules."""
        context_str = recalled.get("formatted_context", "").lower()
        event_type = event.event_type
        loc = event.location_name

        # Heuristic 1: If lights cut, and memories note player rushes mango_tree
        if event_type == "LIGHTS_CUT" or not event.lights_on:
            if "mango_tree" in context_str or "ambush" in context_str:
                return WatchmanDecision(
                    action="AMBUSH",
                    target_object="mango_tree",
                    target_tile=OBJECT_COORDS["mango_tree"],
                    dialogue_ta="பம்பு செட் சுவிட்ச்சை அணைச்சிட்டியா? மாமரத்தண்டை வந்து பதுங்கி நிக்கிறேன்டா, மாட்டாமலா போவ!",
                    dialogue_en="Cut the pumpset lights? I'll wait in ambush near the mango tree. You can't escape!",
                    reasoning="Recalled past pattern: light cuts are distractions to raid the central mango tree in the dark.",
                    confidence=0.92,
                    recalled_memories=recalled
                )
            else:
                return WatchmanDecision(
                    action="TOGGLE_LIGHTS",
                    target_object="pumpset_switch",
                    target_tile=OBJECT_COORDS["pumpset_switch"],
                    dialogue_ta="இருட்டாக்கிட்டான்! முதல்ல போயி பம்பு செட் மெயின் சுவிட்ச்சை போடணும்!",
                    dialogue_en="He darkened the grove! First let me rush to the pumpset room and flip the switch ON!",
                    reasoning="Floodlights cut. Standard procedure is to restore lighting to regain wide vision.",
                    confidence=0.88,
                    recalled_memories=recalled
                )

        # Heuristic 2: Known Decoy counter-tactic (only after Night 1 if memory contains explicit decoy rule)
        if event_type == "NOISE_HEARD":
            is_known_decoy = (
                event.night_number > 1
                and ("decoy" in context_str or "stones thrown at distant objects are decoys" in context_str)
                and loc in ("main_gate", "drain_pipe")
            )
            if is_known_decoy:
                return WatchmanDecision(
                    action="INVESTIGATE",
                    target_object="back_fence",
                    target_tile=OBJECT_COORDS["back_fence"],
                    dialogue_ta="மறுபடியும் கேட்ல கல்லா? நேத்து இதே மாதிரி ஏமாத்துன! முள்வேலியை பாக்குறேன்!",
                    dialogue_en="Stone decoy at the gate again? You tricked me yesterday; I'm checking the fence!",
                    reasoning="Learned episodic pattern: gate noise is a distraction; player sneaks via back fence.",
                    confidence=0.94,
                    recalled_memories=recalled
                )

            # Heuristic 3: Check hiding spots if player has a history of hiding there
            if "hides_in" in context_str and loc in ("haystack", "mud_well"):
                return WatchmanDecision(
                    action="SEARCH_HIDING",
                    target_object=loc,
                    target_tile=OBJECT_COORDS.get(loc, [event.tile_x, event.tile_y]),
                    dialogue_ta=f"{loc} போருக்குள்ள தான் பதுங்கியிருக்கான்! இந்தா என் தடி வச்சு குத்தி பாக்குறேன்!",
                    dialogue_en=f"He's hiding near the {loc}! Let me poke it with my bamboo stick!",
                    reasoning=f"Entity graph marks {loc} as player's known hiding refuge.",
                    confidence=0.92,
                    recalled_memories=recalled
                )

            # Heuristic 4: Sprint footsteps investigation
            if loc in ("sprint_footsteps", "SPRINT_STEPS"):
                return WatchmanDecision(
                    action="INVESTIGATE",
                    target_object="sprint_footsteps",
                    target_tile=[event.tile_x, event.tile_y],
                    dialogue_ta="டேய்! காலடி சத்தம் கேக்குதே! யார்டா அங்கே ஓடுறது?!",
                    dialogue_en="Hey! I hear footsteps running! Who is sprinting over there?!",
                    reasoning=f"Heard loud sprinting footsteps at coordinates ({event.tile_x}, {event.tile_y}). Investigating acoustic source.",
                    confidence=0.96,
                    recalled_memories=recalled
                )

            # Heuristic 5: Direct acoustic distraction investigation at exact stone coordinates!
            return WatchmanDecision(
                action="INVESTIGATE",
                target_object=loc,
                target_tile=[event.tile_x, event.tile_y],
                dialogue_ta="டேய்! அங்கே என்னடா சத்தம்?! யாருடா கல்லை வீசுனது?!",
                dialogue_en="Hey! What was that noise over there?! Who threw that stone?!",
                reasoning=f"Investigating stone impact directly at coordinates ({event.tile_x}, {event.tile_y}).",
                confidence=0.95,
                recalled_memories=recalled
            )

        return None

    async def _query_llm_decision(self, event: SensorEvent, recalled: Dict[str, Any]) -> Optional[WatchmanDecision]:
        """Ask local Ollama model to synthesize creative context-aware decision."""
        system_prompt = (
            "You are Murugesan Mama, a strict, sharp, veteran South Indian watchman guarding a Banganapalli mango grove at night. "
            "You speak in authentic, colloquial Tamil (with occasional Tamil-English mix) like a village elder. "
            "You have a flashlight and bamboo stick. "
            "Based on the provided sensor event and your 4-pillar Strata memory, choose ONE valid tactical action:\n"
            "['PATROL', 'INVESTIGATE', 'AMBUSH', 'SEARCH_HIDING', 'BLOCK_OBJECT', 'SET_TRAP', 'TOGGLE_LIGHTS', 'CHASE']\n"
            "Return strictly valid JSON matching this schema:\n"
            "{\n"
            "  \"action\": \"PATROL\",\n"
            "  \"target_object\": \"mango_tree\",\n"
            "  \"dialogue_ta\": \"Short punchy Tamil speech bubble\",\n"
            "  \"dialogue_en\": \"English translation\",\n"
            "  \"reasoning\": \"Why you chose this\"\n"
            "}"
        )

        user_content = (
            f"Sensor Event: {event.event_type} at {event.location_name} (coords: {event.tile_x}, {event.tile_y}). "
            f"Grove lights ON: {event.lights_on}. Mangoes left: {event.mangoes_remaining}.\n"
            f"Details: {event.details}\n\n"
            f"Strata Cognitive Context:\n{recalled.get('formatted_context', '')}"
        )

        try:
            # We use narrative model with strict 4s timeout for fast gameplay response
            res = await self.client.chat.completions.create(
                model=NARRATIVE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                temperature=0.3,
                max_tokens=300,
                timeout=4.0
            )
            raw = res.choices[0].message.content or ""
            # Strip reasoning / think tags if any
            clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            # Find json block
            json_match = re.search(r"\{.*\}", clean, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                act = parsed.get("action", "PATROL")
                target = parsed.get("target_object", "mango_tree")
                tile = OBJECT_COORDS.get(target, [event.tile_x, event.tile_y])
                return WatchmanDecision(
                    action=act,
                    target_object=target,
                    target_tile=tile,
                    dialogue_ta=parsed.get("dialogue_ta", "யாரோ தோப்புக்குள்ள வந்திருக்காங்க!"),
                    dialogue_en=parsed.get("dialogue_en", "Someone entered the grove!"),
                    reasoning=parsed.get("reasoning", "LLM-synthesized procedural reaction."),
                    confidence=0.9,
                    recalled_memories=recalled
                )
        except Exception as e:
            logger.debug(f"LLM decision timed out or unavailable ({e}); using heuristic fallback.")
            return None

    def _default_action(self, event: SensorEvent, recalled: Dict[str, Any]) -> WatchmanDecision:
        """Central anchor patrol cycle: Tree -> Border -> Tree -> Border."""
        waypoints = ["mango_tree", "pumpset_switch", "mango_tree", "back_fence", "mango_tree", "mud_well"]
        current_loc = event.location_name
        next_target = "mango_tree"
        if current_loc in waypoints:
            idx = (waypoints.index(current_loc) + 1) % len(waypoints)
            next_target = waypoints[idx]

        tamil_patrol_lines = [
            "பங்கனப்பள்ளி மாம்பழத்தை எந்த பையனும் தொட விடமாட்டேன்!",
            "டார்ச் லைட்டை சுத்தி அடிச்சு பாப்போம், யாராவது பதுங்கியிருக்கானா...",
            "இந்த வருஷம் மாங்காய் நல்லா காய்ச்சிருக்கு, திருடன் கண்ணு படாம பாத்துக்கணும்!",
            "மாமரத்தை சுத்தி நல்லா ஒரு ரவுண்ட்ஸ் அடிப்போம்..."
        ]
        import random
        line_ta = random.choice(tamil_patrol_lines)

        return WatchmanDecision(
            action="PATROL",
            target_object=next_target,
            target_tile=OBJECT_COORDS.get(next_target, [8, 6]),
            dialogue_ta=line_ta,
            dialogue_en="Patrolling around the central tree and border perimeters.",
            reasoning="Procedural patrol cycle step: actively safeguarding the central asset.",
            confidence=0.85,
            recalled_memories=recalled
        )
