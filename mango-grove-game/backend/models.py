from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

WatchmanActionType = Literal[
    "PATROL",           # Walk along current procedural patrol waypoints
    "INVESTIGATE",      # Walk briskly to a specific tile or object_id
    "AMBUSH",           # Turn off flashlight and wait silently near mango_tree or entry
    "SEARCH_HIDING",    # Poke haystack or mud_well with stick
    "BLOCK_OBJECT",     # Put thorns on back_fence or lock main_gate
    "SET_TRAP",         # Tie tin-can alarm to drain_pipe, main_gate, or back_fence
    "TOGGLE_LIGHTS",    # Walk to pumpset_switch and turn floodlights back ON
    "CHASE"             # Sprint directly toward spotted player
]


class SensorEvent(BaseModel):
    night_number: int
    time_elapsed: float
    event_type: Literal[
        "NOISE_HEARD",
        "PLAYER_SPOTTED",
        "LIGHTS_CUT",
        "OBJECT_TAMPERED",
        "PATROL_TICK"
    ]
    location_name: str
    tile_x: int
    tile_y: int
    lights_on: bool
    mangoes_remaining: int
    blocked_objects: List[str] = Field(default_factory=list)
    trapped_objects: List[str] = Field(default_factory=list)
    details: str


class WatchmanDecision(BaseModel):
    action: WatchmanActionType
    target_object: str = "mango_tree"
    target_tile: Optional[List[int]] = None
    dialogue_ta: str = Field(description="Short Tamil speech bubble text for Murugesan Mama")
    dialogue_en: str = Field(description="English translation of the thought")
    reasoning: str = Field(description="Why this action was chosen based on Strata memory")
    confidence: float = 1.0
    recalled_memories: Dict[str, Any] = Field(default_factory=dict)


class NightSummaryReport(BaseModel):
    night_number: int
    watchman_won: bool          # True if Watchman caught player or time ran out
    player_escaped: bool        # True if player stole mangoes and exited
    entry_used: Optional[str] = None
    exit_used: Optional[str] = None
    hiding_spots_used: List[str] = Field(default_factory=list)
    stones_thrown_at: List[str] = Field(default_factory=list)
    lights_cut_count: int = 0
    mangoes_stolen: int = 0
    chronological_log: List[str] = Field(default_factory=list)
    memory_ids_used: List[str] = Field(default_factory=list)


class ManualMemoryInjection(BaseModel):
    text: str
    pillar: Literal["semantic", "episodic", "procedural", "entity"] = "semantic"
