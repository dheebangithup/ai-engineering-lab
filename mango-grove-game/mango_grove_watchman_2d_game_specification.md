# Master Game Specification: "மாந்தோப்பு வாட்ச்மேன்" (The Mango Grove Watchman)
## A Real-Time 2D Stealth Sandbox Powered by the Strata 4-Pillar Memory Engine

---

## 1. Executive Summary & Game Concept

* **Game Title:** **மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)**
* **Genre:** Top-Down 2D Real-Time Stealth & AI Memory Sandbox
* **Core Purpose:** A visual, interactive testbed for the **Strata 4-Pillar Cognitive Memory Engine** (`Semantic`, `Episodic`, `Procedural`, `Entity`).
* **The Hook:** You play a village kid sneaking into a South Indian mango grove at night to pluck prized **Banganapalli mangoes (பங்கனப்பள்ளி மாம்பழம்)** from the central tree. The grove is guarded by **Murugesan Mama (முருகேசன் மாமா)**—an AI watchman with a flashlight and stick whose brain is wired directly to **Strata**.
* **Why It's Special:** Unlike traditional games with static patrol scripts, Murugesan Mama remembers every stone thrown, every power cut at the pump-set room, every broken fence, and every hiding spot across nights. Between rounds, he consolidates his memories and evolves his patrol procedures (`v1 -> v2 -> v3`) in real time.

---

## 2. Screen Layout: Split-Screen "Game + Brain Inspector"

To make the memory system visible for learning and debugging, the web UI is split into two live panels:

```
+---------------------------------------------------+------------------------------------+
|           LEFT PANEL (65% Width)                  |       RIGHT PANEL (35% Width)      |
|      2D TOP-DOWN GAME CANVAS (800 x 600)          |   LIVE STRATA MEMORY INSPECTOR     |
|                                                   |                                    |
|  [North Wall]======[Main Gate]=====[North Wall]   |  [Active Night: #3 | Timer: 00:42] |
|  |                                            |   |  [Lights: ON | Mangoes: 1/3]       |
|  |  [Pump-Set Room]                           |   |                                    |
|  |   (Main Switch)        (Banganapalli)      |   |  --- MURUGESAN MAMA'S THOUGHTS --- |
|  |                         (Mango Tree)       |   |  "கேட் பக்கம் கல்லு சத்தம்... ஆனா  |
|  |                           [M][M][M]        |   |   நேத்து மாதிரி முள்வேலி பக்கம்    |
|  |                                            |   |   வர்றானான்னு பார்ப்போம்!"         |
|  |                                    [Thorn] |   |                                    |
|  |  [Haystack]         [Mud Well]     [Fence] |   |  --- 4-PILLAR LIVE MEMORY FEED --- |
|  |  (Hiding Spot)     (Hiding Spot)   (Entry) |   |  [EPISODIC] Night 2: Stone at gate |
|  |                                            |   |  [SEMANTIC] Power cut = Tree rush  |
|  +============================================+   |  [PROCEDURAL] Patrol_v2 (85% win)  |
|  Controls: WASD/Arrows | E: Interact | Space:     |  [ENTITY] Kid -> HidesIn -> Hay    |
|  Throw Stone (3 left) | R: Next Night             |                                    |
+---------------------------------------------------+------------------------------------+
```

---

## 3. The 2D Map Specification (16 x 12 Tile Grid, 50px per Tile)

The entire game takes place on a single-screen `16x12` grid (`800x600px` HTML5 Canvas) with **6 key interactive zones/objects**:

| Object ID | Tamil / English Name | Tile Coords `(x, y)` | Player Interaction (`E` Key) | Watchman Interaction (AI Action) |
| :--- | :--- | :---: | :--- | :--- |
| `main_gate` | **மெயின் கேட்** (Iron Main Gate) | `(8, 0)` | Fast entry/exit, but makes a **LOUD** `"CREAK!"` noise (radius 6 tiles). | Can inspect or `LOCK_OBJECT("main_gate")`. |
| `back_fence` | **பின்பக்க முள்வேலி** (Back Thorn Fence) | `(15, 8)` | Silent entry/exit, takes `1.5s` to squeeze through. | Can inspect or block with thorns `BLOCK_FENCE("back_fence")`. |
| `drain_pipe` | **மதகு குழாய்** (Stone Drain Culvert) | `(0, 9)` | Secret low-profile entry/exit on the West wall. | Can place a tin-can alarm `SET_TRAP("drain_pipe")`. |
| `pumpset_switch` | **பம்பு செட் சுவிட்ச்** (Motor Room Switch) | `(2, 3)` | Toggles grove floodlights `OFF/ON`. When `OFF`, Watchman only sees inside his flashlight cone. | Can turn switch back `ON`, or ignore it and ambush at the tree. |
| `mango_tree` | **பங்கனப்பள்ளி மாமரம்** (Central Mango Tree) | `(8, 6)` | Plucks 1 mango (`1.0s` channel). Collect **2 mangoes** and exit the grove to win the night! | Primary guard target; can `AMBUSH("mango_tree")` in the dark. |
| `haystack` | **வைக்கோல் போர்** (Haystack Hiding Spot) | `(3, 9)` | Hides player completely from sight unless Watchman directly pokes it. | `SEARCH_HIDING("haystack")` pokes with stick and catches hidden player. |
| `mud_well` | **கிணற்று மேடு** (Old Well Parapet) | `(11, 9)` | Secondary hiding spot behind the stone well wall. | `SEARCH_HIDING("mud_well")` checks behind the well. |

### Player Mechanics
* **Movement:** `WASD` or `Arrow Keys` (Walk) + `Shift` (Sprint — faster, but creates footstep noise rings of radius 3).
* **Throw Stone (`Spacebar` or Left-Click on tile):** Throws a pebble up to 6 tiles away. Creates a visible ripple and a sound event (`STONE_NOISE`) at `(target_x, target_y)`. Player starts each night with **3 stones**.
* **Objective:** Enter the grove $\to$ Pluck **2 Mangoes** from `(8, 6)` $\to$ Escape out any entry point (`main_gate`, `back_fence`, or `drain_pipe`) before the 60-second night timer runs out or Murugesan Mama catches you.

---

## 4. Watchman AI Sensors & Strata 4-Pillar Integration

Murugesan Mama does **not** cheat by reading the player's `(x, y)` coordinates directly when the player is out of sight. He only perceives the world through **3 honest sensors**:

1. **Vision Cone Sensor:**
   * A `75°` flashlight cone extending `4.5 tiles` in front of him (or `6 tiles` when the grove floodlights are `ON`).
   * Raycasted against walls (`pumpset_room` walls, `mango_tree` trunk).
2. **Audio Sensor:**
   * Detects any noise event (`STONE_NOISE`, `GATE_CREAK`, `SPRINT_STEPS`, `TIN_CAN_TRAP`) where distance $\le \text{noise\_radius}$.
3. **World-State Diff Sensor:**
   * When his flashlight sweeps over an object, he notices state changes: `"Back fence is parted"`, `"Mangoes missing from tree"`, `"Pump-set switch is OFF"`.

### How All 4 Strata Pillars Drive Gameplay

```
+-----------------------------------------------------------------------------------+
|                      NIGHT-BY-NIGHT SELF-EVOLUTION CYCLE                          |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  1. DURING THE NIGHT (Hot-Path Recall & Decision Tick every 3 seconds or on event)|
|     - Sensor triggers event (e.g., Heard stone at Main Gate)                      |
|     - Calls Strata `POST /recall` with query:                                     |
|       "Heard stone noise at main_gate while lights are ON"                        |
|     - Strata returns in <15ms:                                                    |
|       * EPISODIC: "Night 1: Stone at main_gate was a distraction for back_fence"  |
|       * SEMANTIC: "Player uses stones to fake out the opposite side of the map"   |
|       * PROCEDURAL: "patrol_plan v2: Check back_fence immediately on gate noise"  |
|       * ENTITY: "(Player) -[ENTERS_VIA]-> (back_fence)"                           |
|     - Watchman AI outputs JSON decision:                                          |
|       `{"action": "INVESTIGATE", "target": "back_fence",                          |
|         "dialogue_ta": "மறுபடியும் கேட்ல கல்லா? முள்வேலி பக்கம் தான் வருவ!"}`    |
|                                                                                   |
|  2. END OF NIGHT ("Dawn Reflection" — Cold-Path Consolidation)                    |
|     - Game sends full Night Summary to Strata `POST /ingest` & `POST /feedback`   |
|     - If Player escaped with mangoes (`success = false` for Watchman):            |
|       * Strata logs the Episodic trace                                            |
|       * Strata updates Entity Graph (`Player -> FAVORITE_ENTRY -> back_fence`)    |
|       * Strata auto-patches `procedural_memories` (`watchman_patrol` v1 -> v2)    |
|         so Night N+1 starts with a brand-new counter-strategy!                    |
+-----------------------------------------------------------------------------------+
```

---

## 5. Target Project Directory Structure

Antigravity must create this clean, self-contained project inside `mango-grove-game/` (which connects to your running `strata-memory` service or runs an embedded bridge):

```
mango-grove-game/
├── pyproject.toml                  # FastAPI game server + Strata client dependencies
├── .env.example                    # Strata API URL + Local LLM / Ollama settings
├── README.md                       # Quickstart & Tamil/English gameplay guide
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI server serving static frontend + AI WebSocket/REST
│   ├── models.py                   # Pydantic schemas for GameState, SensorEvent, WatchmanAction
│   ├── strata_bridge.py            # Async client connecting to Strata (/ingest, /recall, /feedback)
│   └── watchman_brain.py           # Watchman decision engine + Dawn Reflection consolidator
└── frontend/
    ├── index.html                  # Split-screen layout (Canvas Left, Strata Inspector Right)
    ├── style.css                   # Village night theme, speech bubbles & memory pillar badges
    └── game.js                     # Complete 2D Canvas engine, raycasting, sound ripples & UI
```

---

## 6. Backend Implementation Specifications (`backend/`)

### 6.1 `backend/models.py` (Game & AI Action Contracts)

```python
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any

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
```

### 6.2 `backend/strata_bridge.py` (Connecting to Strata Memory Engine)

This module connects to your **Strata REST API** (`http://localhost:8080` by default) using namespace `"mango_grove_murugesan"`:

1. **`bootstrap_initial_memories()`:**
   On first startup, seeds Murugesan Mama's initial Procedural Memory (`watchman_night_patrol` v1):
   * `trigger_condition`: `"Start of night patrol or standard guard duty in mango grove"`
   * `steps`: `["Walk from main_gate to pumpset_switch", "Check mango_tree", "Walk back to main_gate", "If noise heard, walk directly to noise source"]`
2. **`recall_for_event(sensor_event: SensorEvent) -> Dict`:**
   Calls `POST /recall` on Strata with `query = f"{sensor_event.event_type} at {sensor_event.location_name}: {sensor_event.details}"`, `pillars=["semantic", "episodic", "procedural", "entity"]`, `top_k=4`, `token_budget=1000`.
3. **`consolidate_night(summary: NightSummaryReport) -> Dict`:**
   * Builds a rich natural-language narrative of what happened during the night (e.g., *"In Night 2, the kid threw a stone at main_gate as a decoy, cut the pumpset_switch lights, entered via back_fence, hid in the haystack, stole 2 mangoes, and escaped via back_fence."*).
   * Calls Strata `POST /ingest` so Strata's Memory-Side Small LLM extracts **Semantic rules**, **Episodic logs**, **Procedural patrol updates**, and **Entity Graph links**.
   * Calls Strata `POST /feedback` with `procedure_name="watchman_night_patrol"`, `success=summary.watchman_won`, and `failure_reason` if the player escaped, automatically evolving the patrol procedure to `v2`, `v3`, etc.

### 6.3 `backend/watchman_brain.py` (Real-Time Decision & Deterministic Fallback)

* **Primary Mode (Local LLM / Ollama):**
  Combines the current `SensorEvent` + Strata's `formatted_context` XML block and asks the local model (`qwen2.5:3b-instruct` or `llama3.2:3b`) to return a strict JSON `WatchmanDecision` including authentic village Tamil dialogue (`dialogue_ta`).
* **Instant Heuristic + Memory Fallback (<20ms):**
  If the local LLM is busy or offline, `watchman_brain.py` parses the recalled Strata memories deterministically:
  * If `entity_graph` or `episodic` memories show `back_fence` was used when a stone hit `main_gate`, it overrides the naive noise investigation and sends `INVESTIGATE("back_fence")` with Tamil dialogue: `"மறுபடியும் கல்லு சத்தமா? நேத்தே ஏமாந்தேன், இன்னைக்கு முள்வேலியைப் பார்ப்போம்!"`
  * If `semantic` memory contains a rule linking `pumpset_switch` power cuts to `mango_tree` theft, cutting the power triggers `AMBUSH("mango_tree")` instead of `TOGGLE_LIGHTS("pumpset_switch")`.

---

## 7. Frontend 2D Game Engine Specifications (`frontend/`)

Antigravity must build a crisp, zero-build-step HTML5 Canvas frontend (`index.html`, `style.css`, `game.js`) with these visual and interactive features:

1. **Rich 2D Top-Down Visuals on HTML5 Canvas:**
   * Lush dark-green mango grove tilemap with dirt footpaths, stone compound walls, a glowing blue water well (`mud_well`), a golden-yellow haystack (`haystack`), a tin-roofed motor shed (`pumpset_switch`), and a large central `mango_tree` with glowing golden Banganapalli mango sprites.
   * **Dynamic Lighting & Flashlight Cone:** When `lights_on = false`, render a dark night overlay (`rgba(5, 8, 22, 0.78)`) with an alpha cutout for Murugesan Mama's rotating `75°` flashlight cone and a small visibility halo around the player.
   * **Expanding Sound Rings:** Whenever a stone lands, the iron gate creaks, or the player sprints, draw expanding cyan/amber concentric sound rings showing the exact radius of the noise.
   * **Tamil + English Speech Bubble:** Render a floating comic speech bubble above Murugesan Mama's head whenever he makes a decision so the player can read his mind in real time.

2. **Right-Hand "Strata Live Memory Inspector" Panel:**
   * **4 Color-Coded Pillar Tabs / Cards:**
     * 🟦 **Semantic (உண்மைகள் / Learned Rules)**
     * 🟨 **Episodic (சம்பவங்கள் / Past Nights)**
     * 🟩 **Procedural (ரவுண்ட்ஸ் திட்டம் / Evolved Patrol `v1 -> v2 -> v3`)**
     * 🟪 **Entity Graph (தொடர்புகள் / Kid's Habits & Object States)**
   * **"Dawn Reflection" Modal Between Nights:** When a night ends (Win or Caught), show a 3-second animated **"விடியற்காலை சிந்தனை (Dawn Memory Consolidation)"** overlay displaying the exact memories Murugesan Mama just wrote into Strata before clicking **"Start Next Night (அடுத்த ராத்திரி)"**.
   * **Manual Memory Injection Box:** Include a small input box in the sidebar where you can type a custom memory directly into Murugesan Mama's brain at runtime (e.g., *"The kid always hides inside the haystack when the lights go out"*) and immediately watch his behavior change!

---

## 8. Execution Prompt for Antigravity

Copy and paste this exact prompt to Antigravity:

> **"Read `MANGO_GROVE_GAME_SPEC.md` and `AGENT_HARNESS_SPEC.md`. Build the complete `mango-grove-game` project (`pyproject.toml`, `.env.example`, `README.md`, `backend/models.py`, `backend/strata_bridge.py`, `backend/watchman_brain.py`, `backend/main.py`, `frontend/index.html`, `frontend/style.css`, and `frontend/game.js`). Connect `strata_bridge.py` to our Strata Memory Engine REST API (`http://localhost:8080`) with an automatic in-memory/SQLite fallback if Strata is not yet running so the game works out-of-the-box. Implement the full 16x12 2D Mango Grove Canvas game, flashlight cone raycasting, stone throwing, pump-set light switch, hiding spots, Tamil speech bubbles for Murugesan Mama, and the live 4-Pillar Strata Memory Inspector sidebar with zero placeholders."**