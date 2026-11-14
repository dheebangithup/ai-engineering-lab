# மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)
### A Real-Time 2D Stealth AI Sandbox Powered by the Strata 4-Pillar Memory Engine & Ollama

---

## 🌳 Game Concept

In a sleepy South Indian village, prized **Banganapalli mangoes (பங்கனப்பள்ளி மாம்பழம்)** hang ripe on the central tree of a walled orchard. You play a mischievous village kid sneaking in at night with three stones in your pocket. Your goal: pluck **2 mangoes** and slip away into the darkness.

Guarding the grove is **Murugesan Mama (முருகேசன் மாமா)**—a veteran watchman equipped with a flashlight, a bamboo stick, and a cognitive brain connected directly to **Strata Memory**.

Unlike traditional video game guards programmed with fixed, predictable patrol loops, Murugesan Mama remembers everything:
- Throw stones as a decoy? He remembers the trick from previous nights and checks the opposite fence instead.
- Cut the floodlights at the pump-set room? He sets up an ambush in the dark near the central tree.
- Hide inside the haystack or behind the old well? His **Entity Graph** associates you with those hiding spots and he begins poking them with his stick.
- At the end of each round, his **Procedural Patrol Plan** auto-patches (`v1 ➔ v2 ➔ v3`) during **Dawn Reflection (விடியற்காலை சிந்தனை)**.

---

## 🤖 AI Models & Their Roles

The game employs a specialized multi-model architecture to balance **sub-20ms real-time gaming reflexes** with **deep cognitive reasoning and authentic dialogue**:

```
+─────────────────────────────────────────────────────────────────────────────────────────+
│                               AI MODEL PIPELINE ARCHITECTURE                            │
+─────────────────────────────────────────────────────────────────────────────────────────+
│                                                                                         │
│  1. TACTICAL REAL-TIME DECISION MODEL (Hot-Path, <20ms)                                │
│     Model: Ollama "laya" (421M Parameters ModernBERT Decision Engine)                   │
│     Purpose: Rapid candidate action ranking and real-time response selection.           │
│                                                                                         │
│  2. NARRATIVE & CONSOLIDATION MODEL (Cold-Path, Authentic Persona)                     │
│     Model: Ollama "qwen3:8b" (8 Billion Parameter LLM)                                 │
│     Purpose: Generating authentic colloquial Tamil speech bubbles for Murugesan Mama,   │
│              and extracting structured 4-pillar facts during Dawn Reflection.           │
│                                                                                         │
│  3. DENSE SEMANTIC VECTOR EMBEDDER (Cognitive Indexing)                                │
│     Model: Ollama "nomic-embed-text" (768-Dimensional Embeddings)                      │
│     Purpose: Vectorizing episodic events and semantic grove rules for Neon DB HNSW      │
│              vector search and Reciprocal Rank Fusion (RRF).                            │
│                                                                                         │
+─────────────────────────────────────────────────────────────────────────────────────────+
```

### Detailed Breakdown of AI Models

| Model Name | Architecture & Size | Primary Purpose & Responsibility | Execution Path |
| :--- | :--- | :--- | :--- |
| **`laya`** | 421M Parameter ModernBERT | **Main Real-Time Decision Engine**: Evaluates sensor events (`NOISE_HEARD`, `LIGHTS_CUT`, `PLAYER_SPOTTED`) against recalled memories to select tactical actions (`PATROL`, `INVESTIGATE`, `AMBUSH`, `SEARCH_HIDING`, `CHASE`) in **under 20ms**. | **Hot-Path** (Game Loop every 2.5s or on sound event) |
| **`qwen3:8b`** | 8B Parameter Reasoning LLM | **Persona Dialogue & Dawn Reflection**: Speaks authentic village Tamil (`dialogue_ta`) with English translation (`dialogue_en`), and parses the night's story during dawn consolidation to create new rules. | **Cold-Path** (Event speech & Round end) |
| **`nomic-embed-text`** | 768-Dimension Dense Embeddings | **Memory Similarity & Recall**: Generates embeddings for memory statements stored in Neon Serverless PostgreSQL (`VECTOR(768)`). | **Memory Engine** (Recall & Ingest) |

### Which Model is Mainly Being Used?
- **During Active Gameplay (The Real-Time Hot-Path):** **`laya`** is the primary model. Because standard 8B LLMs take several seconds to generate tokens, `laya` (ModernBERT) evaluates candidate moves in <20ms, allowing Murugesan Mama to react instantly to thrown stones and footsteps without lag.
- **Between Nights (The Cognitive Reflection Cold-Path):** **`qwen3:8b`** is the primary model. It performs deep reflection on what happened, extracts rules, and updates the watchman's procedural patrol strategy.

---

## 🎮 Game Controls & Mechanics

| Key / Action | Description |
| :--- | :--- |
| **W, A, S, D** or **Arrow Keys** | Move village kid |
| **Shift** | **Sprint** (Move faster, but generates loud footstep sound ripples) |
| **Spacebar** or **Left-Click** | **Throw Stone** (Pebble distraction up to 6 tiles away; 3 stones per night) |
| **E** | **Interact** (Pluck mango, flip floodlight switch, hide, or escape) |
| **R** | Restart current night |
| **Sound Toggle** | Click `🔊 Audio: ON / MUTED` in the top HUD |

### Key Mechanics:
1. **Endless Survival Mode (No Time Limit):** There is no countdown timer! You can play indefinitely until Murugesan Mama catches you or you escape with 2 mangoes. The timer displays your survival duration.
2. **Dynamic Flashlight Raycasting:** When grove lights are ON, Mama sees 6 tiles ahead. When you turn lights OFF at the pump-set room, visibility drops to a 4.5-tile cone with dynamic darkness.
3. **Web Audio Sound Effects:** Real-time synthesized audio for footsteps, pebble clicks, gate creaks, switch flips, mango plucking, and catch alarms.

---

## 🧠 Strata 4-Pillar Memory Engine Integration

Murugesan Mama's thoughts and actions are governed by 4 distinct memory pillars stored in **Neon PostgreSQL**:

* 🟦 **Semantic Pillar (உண்மைகள் / Learned Rules):**
  - General grove truths: *"Power cuts at the pumpset usually mean the thief is rushing the central mango tree."*
* 🟨 **Episodic Pillar (சம்பவங்கள் / Past Nights):**
  - Historical chronological logs of what the player did on past nights (e.g. *"Night 1: Player threw stone at main gate and slipped in through the back fence"*).
* 🟩 **Procedural Pillar (ரவுண்ட்ஸ் திட்டம் / Evolving Patrol Plan):**
  - Murugesan Mama's step-by-step patrol routine (`v1 ➔ v2 ➔ v3`). Automatically updates counter-tactics whenever the player escapes!
* 🟪 **Entity Graph (தொடர்புகள் / Relationships):**
  - Knowledge graph edges connecting entities: `Village Kid ➔ [FAVORITE_ENTRY] ➔ back_fence`, `Village Kid ➔ [HIDES_IN] ➔ haystack`.

---

## 🚀 How to Run the Game

### Step 1: Start the Strata Memory Server (Terminal 1)
```bash
cd /Users/dheeban/Documents/my_projects/ai-engineering-lab/strata-memory
source .venv/bin/activate
strata-api
```
*(Starts on `http://localhost:8080` and connects to Neon Serverless PostgreSQL)*

### Step 2: Start the Game Server (Terminal 2)
```bash
cd /Users/dheeban/Documents/my_projects/ai-engineering-lab/mango-grove-game
./run_game.py
```
*(Automatically switches to the project virtualenv and starts on port 8001)*

### Step 3: Play in Browser
Open **[http://localhost:8001](http://localhost:8001)** in Chrome or any modern browser!

---

## 📁 Project Directory Structure

```
mango-grove-game/
├── run_game.py                 # One-click launcher with auto-venv detection
├── pyproject.toml              # Dependencies & package configuration
├── .env.example / .env         # Strata API & Ollama configuration
├── README.md                   # Full documentation & AI model architecture
├── backend/
│   ├── __init__.py
│   ├── main.py                 # FastAPI web and static asset server (Port 8001)
│   ├── models.py               # Pydantic schemas (SensorEvent, WatchmanDecision, NightSummary)
│   ├── strata_bridge.py        # Strata REST client + local fallback memory store
│   └── watchman_brain.py       # Dual-brain AI: laya decision logic + qwen3:8b Tamil persona
└── frontend/
    ├── index.html              # Split-screen UI (Left: Canvas, Right: Strata Memory Inspector)
    ├── style.css               # Village night theme, pillar color cards & comic speech bubbles
    └── game.js                 # 16x12 Canvas engine, raycasting, sound ripples & audio synthesizer
```
