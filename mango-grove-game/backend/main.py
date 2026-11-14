import os
import socket

# Resilient DNS fallback for Neon serverless PostgreSQL when ISP DNS drops/refuses AWS domains
_orig_getaddrinfo = socket.getaddrinfo
def _resilient_getaddrinfo(host, port, *args, **kwargs):
    try:
        return _orig_getaddrinfo(host, port, *args, **kwargs)
    except (socket.gaierror, OSError):
        if host and "neon.tech" in str(host):
            for fallback_ip in ["13.228.46.236", "52.220.170.93", "13.228.184.177"]:
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (fallback_ip, port))]
        raise

socket.getaddrinfo = _resilient_getaddrinfo

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from backend.models import (
    SensorEvent,
    WatchmanDecision,
    NightSummaryReport,
    ManualMemoryInjection
)
from backend.strata_bridge import StrataBridge
from backend.watchman_brain import WatchmanBrain

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

strata = StrataBridge()
brain = WatchmanBrain(strata=strata)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("\n" + "=" * 65)
    print(" 🌳 மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)")
    print(" 🧠 Bootstrapping Strata 4-Pillar Memory Engine...")
    await strata.bootstrap_initial_memories()
    print(" 🚀 Game Server Ready! Open http://localhost:8001")
    print("=" * 65 + "\n")
    yield


app = FastAPI(
    title="மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)",
    description="2D Stealth AI Sandbox powered by Strata Memory & Ollama",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    strata_ok = await strata.check_connection()
    return {
        "status": "healthy",
        "strata_api_connected": strata_ok,
        "connection_mode": strata.connection_mode,
        "strata_namespace": strata.namespace
    }


ACTIVE_COUNTERMEASURES: Dict[str, List[str]] = {
    "locked_objects": [],
    "blocked_objects": [],
    "trapped_objects": []
}


@app.post("/api/action", response_model=WatchmanDecision)
async def decide_action(event: SensorEvent):
    try:
        print(f"📡 [SENSOR] Night #{event.night_number} | {event.event_type} at {event.location_name} ({event.tile_x}, {event.tile_y}) | Lights: {'ON' if event.lights_on else 'OFF'}")
        decision = await brain.decide_action(event)
        print(f"🧠 [DECISION] Mama Action: {decision.action} -> {decision.target_object} | \"{decision.dialogue_ta}\"")
        return decision
    except Exception as e:
        print(f"❌ [ERROR] Action error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/night/end")
async def end_night(summary: NightSummaryReport):
    try:
        print("\n" + "-" * 55)
        print(f"🌅 [DAWN REFLECTION] Night #{summary.night_number} Ended")
        print(f"   Outcome: {'🎉 PLAYER ESCAPED' if summary.player_escaped else '👴🏽 WATCHMAN WON'}")
        print(f"   Entry: {summary.entry_used} | Exit: {summary.exit_used} | Mangoes: {summary.mangoes_stolen}")
        print(f"   Hiding Spots: {summary.hiding_spots_used} | Stones: {summary.stones_thrown_at}")

        consolidation = await strata.consolidate_night(summary)

        # Compute cumulative next-night counter-measures based on player escape vector
        if summary.player_escaped:
            if summary.exit_used == "main_gate" and "main_gate" not in ACTIVE_COUNTERMEASURES["locked_objects"]:
                ACTIVE_COUNTERMEASURES["locked_objects"].append("main_gate")
            elif summary.exit_used == "back_fence" and "back_fence" not in ACTIVE_COUNTERMEASURES["blocked_objects"]:
                ACTIVE_COUNTERMEASURES["blocked_objects"].append("back_fence")
            elif summary.exit_used == "drain_pipe" and "drain_pipe" not in ACTIVE_COUNTERMEASURES["trapped_objects"]:
                ACTIVE_COUNTERMEASURES["trapped_objects"].append("drain_pipe")

        consolidation["countermeasures"] = {
            "locked_objects": list(ACTIVE_COUNTERMEASURES["locked_objects"]),
            "blocked_objects": list(ACTIVE_COUNTERMEASURES["blocked_objects"]),
            "trapped_objects": list(ACTIVE_COUNTERMEASURES["trapped_objects"])
        }
        print(f"🔒 [COUNTER-TACTICS] Cumulative Locks & Traps Applied: {consolidation['countermeasures']}")
        print("-" * 55 + "\n")

        return {
            "status": "consolidated",
            "reflection": consolidation
        }
    except Exception as e:
        print(f"❌ [ERROR] Night end error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/memory/inject")
async def inject_memory(injection: ManualMemoryInjection):
    try:
        print(f"🧪 [MANUAL INJECTION] [{injection.pillar.upper()}] {injection.text}")
        res = await strata.inject_memory(injection.text, injection.pillar)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memory/state")
async def get_memory_state():
    state = await strata.get_all_memories()
    state["countermeasures"] = {
        "locked_objects": list(ACTIVE_COUNTERMEASURES["locked_objects"]),
        "blocked_objects": list(ACTIVE_COUNTERMEASURES["blocked_objects"]),
        "trapped_objects": list(ACTIVE_COUNTERMEASURES["trapped_objects"])
    }
    return state


# Mount frontend static assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Frontend index.html is being prepared."}
