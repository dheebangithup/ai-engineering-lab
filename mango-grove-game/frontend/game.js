/**
 * மாந்தோப்பு வாட்ச்மேன் (The Mango Grove Watchman)
 * HTML5 2D Canvas Engine & Strata Cognitive AI Controller
 */

// Grid Config: 16 x 12 tiles, 50px per tile = 800 x 600
const TILE_SIZE = 50;
const COLS = 16;
const ROWS = 12;

const OBJECT_DEFS = {
  main_gate: { x: 8, y: 0, label: "மெயின் கேட் (Main Gate)", type: "gate" },
  back_fence: { x: 15, y: 8, label: "பின்பக்க முள்வேலி (Back Fence)", type: "fence" },
  drain_pipe: { x: 0, y: 9, label: "மதகு குழாய் (Drain Pipe)", type: "pipe" },
  pumpset_switch: { x: 2, y: 3, label: "பம்பு செட் சுவிட்ச் (Light Switch)", type: "switch" },
  mango_tree: { x: 8, y: 6, label: "பங்கனப்பள்ளி மாமரம் (Central Tree)", type: "tree" },
  haystack: { x: 3, y: 9, label: "வைக்கோல் போர் (Haystack)", type: "hiding" },
  mud_well: { x: 11, y: 9, label: "கிணற்று மேடு (Old Well)", type: "hiding" }
};

// Map Obstacles (Walls & Shed)
const WALL_TILES = new Set();
// Top border except gate
for (let c = 0; c < COLS; c++) {
  if (c !== 8) WALL_TILES.add(`${c},0`);
}
// Bottom border
for (let c = 0; c < COLS; c++) {
  WALL_TILES.add(`${c},11`);
}
// Left border except drain pipe
for (let r = 0; r < ROWS; r++) {
  if (r !== 9) WALL_TILES.add(`0,${r}`);
}
// Right border except back fence
for (let r = 0; r < ROWS; r++) {
  if (r !== 8) WALL_TILES.add(`15,${r}`);
}
// Pumpset room walls (tiles 1,2 to 3,4)
WALL_TILES.add(`1,2`);
WALL_TILES.add(`2,2`);
WALL_TILES.add(`3,2`);
WALL_TILES.add(`1,3`);
WALL_TILES.add(`1,4`);
WALL_TILES.add(`3,4`);

// ----------------- Web Audio Sound Effects Synthesizer -----------------
class SoundManager {
  constructor() {
    this.ctx = null;
    this.enabled = true;
  }

  init() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      this.ctx = new AudioCtx();
    }
    if (this.ctx.state === "suspended") {
      this.ctx.resume();
    }
  }

  playFootstep(isSprinting) {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sine";
    const freq = isSprinting ? 95 : 65;
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(30, this.ctx.currentTime + 0.08);

    gain.gain.setValueAtTime(isSprinting ? 0.25 : 0.1, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.08);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.09);
  }

  playStoneThrow() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "triangle";
    osc.frequency.setValueAtTime(450, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(140, this.ctx.currentTime + 0.18);

    gain.gain.setValueAtTime(0.2, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.18);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.19);
  }

  playStoneHit() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(750, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(110, this.ctx.currentTime + 0.09);

    gain.gain.setValueAtTime(0.35, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.09);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.1);
  }

  playGateCreak() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(150, this.ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(230, this.ctx.currentTime + 0.16);
    osc.frequency.linearRampToValueAtTime(120, this.ctx.currentTime + 0.35);

    gain.gain.setValueAtTime(0.25, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.38);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.4);
  }

  playGateRattle() {
    if (!this.enabled) return;
    this.init();
    [180, 220, 160, 240].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "square";
      const startT = this.ctx.currentTime + idx * 0.06;
      osc.frequency.setValueAtTime(freq, startT);
      gain.gain.setValueAtTime(0.25, startT);
      gain.gain.exponentialRampToValueAtTime(0.01, startT + 0.1);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startT);
      osc.stop(startT + 0.12);
    });
  }

  playCanClatter() {
    if (!this.enabled) return;
    this.init();
    [880, 620, 1200, 750, 950].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "triangle";
      const startT = this.ctx.currentTime + idx * 0.05;
      osc.frequency.setValueAtTime(freq, startT);
      gain.gain.setValueAtTime(0.3, startT);
      gain.gain.exponentialRampToValueAtTime(0.01, startT + 0.15);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startT);
      osc.stop(startT + 0.16);
    });
  }

  playRustle() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(180, this.ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(80, this.ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.12, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.12);
    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.13);
  }

  playSwitchClick() {
    if (!this.enabled) return;
    this.init();
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "square";
    osc.frequency.setValueAtTime(950, this.ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(80, this.ctx.currentTime + 0.12);

    gain.gain.setValueAtTime(0.3, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, this.ctx.currentTime + 0.12);

    osc.connect(gain);
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.13);
  }

  playMangoPluck() {
    if (!this.enabled) return;
    this.init();
    [523.25, 659.25].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      const startT = this.ctx.currentTime + idx * 0.08;
      osc.frequency.setValueAtTime(freq, startT);

      gain.gain.setValueAtTime(0.28, startT);
      gain.gain.exponentialRampToValueAtTime(0.01, startT + 0.25);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startT);
      osc.stop(startT + 0.26);
    });
  }

  playCaught() {
    if (!this.enabled) return;
    this.init();
    [320, 480, 240].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sawtooth";
      const startT = this.ctx.currentTime + idx * 0.1;
      osc.frequency.setValueAtTime(freq, startT);
      gain.gain.setValueAtTime(0.35, startT);
      gain.gain.exponentialRampToValueAtTime(0.01, startT + 0.2);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startT);
      osc.stop(startT + 0.22);
    });
  }

  playWinFanfare() {
    if (!this.enabled) return;
    this.init();
    [261.6, 329.6, 392.0, 523.2].forEach((freq, idx) => {
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = "sine";
      const startT = this.ctx.currentTime + idx * 0.12;
      osc.frequency.setValueAtTime(freq, startT);
      gain.gain.setValueAtTime(0.3, startT);
      gain.gain.exponentialRampToValueAtTime(0.01, startT + 0.4);

      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(startT);
      osc.stop(startT + 0.45);
    });
  }
}

const sounds = new SoundManager();

class GameState {
  constructor() {
    this.nightNumber = 1;
    this.timer = 0.0;
    this.spawnGraceTimer = 4.0; // 4 seconds of stealth grace on entry
    this.hasTriggeredEntryCreak = false;
    this.isRunning = true;
    this.lightsOn = true;
    this.mangoesCollected = 0;
    this.mangoesOnTree = 3;
    this.stonesLeft = 3;

    // Dynamic Countermeasures
    this.lockedObjects = new Set();
    this.blockedObjects = new Set();
    this.trappedObjects = new Set();

    // Player State - Safe entry at Main Gate
    this.player = {
      x: 8 * TILE_SIZE + 25,
      y: 0 * TILE_SIZE + 35,
      radius: 14,
      speed: 3.2,
      sprintSpeed: 5.2,
      isSprinting: false,
      isHidden: false,
      hiddenIn: null,
      holdingMangoes: 0,
      channeling: false,
      channelProgress: 0.0,
      channelDuration: 2.0,
      channelTarget: null,
      rustleTimer: 0.0
    };

    // Watchman State (Murugesan Mama) - Starts deep in grove near well/tree, facing away from gate!
    this.watchman = {
      x: 8 * TILE_SIZE + 25,
      y: 8 * TILE_SIZE + 25,
      radius: 16,
      angle: Math.PI / 2, // Facing South away from entrance
      speed: 1.9,
      chaseSpeed: 3.3,
      isChasing: false,
      chaseLostTimer: 0.0,
      scanTimer: 0.0,
      targetTile: [11, 9],
      currentAction: "PATROL",
      stickSwinging: false,
      speechText: "ராத்திரி ஆச்சு... பங்கனப்பள்ளி மாம்பழத்தை பத்திரமா பாத்துக்கணும்!",
      speechEn: "Night has fallen... gotta guard the prized Banganapalli mangoes!",
      speechTimer: 5.0
    };

    // Projectile stones flying through the air
    this.flyingStones = [];

    // Audio & Visual ripples
    this.soundRipples = []; // { x, y, maxRadius, currentRadius, alpha, color }

    // Night Summary tracking
    this.nightLog = {
      entryUsed: "main_gate",
      exitUsed: null,
      hidingSpotsUsed: new Set(),
      stonesThrownAt: [],
      lightsCutCount: 0,
      mangoesStolen: 0,
      watchmanWon: false,
      playerEscaped: false
    };

    // Decision tick timing
    this.lastDecisionTick = 0;

    // Autonomous AI vs AI Simulation Mode
    this.isAiMode = false;
    this.simSpeed = 1.0;
    this.autoNextNight = true;

    // AI Kid (Velu) Cognitive State
    this.velu = {
      state: "INFILTRATE", // INFILTRATE, CUT_LIGHTS, DISTRACT, APPROACH_TREE, PLUCK, ESCAPE, HIDE
      dialogueTa: "மெயின் கேட் வழியா நைசா உள்ளே போவோம்...",
      dialogueEn: "Sneaking in quietly through the entrance...",
      reasoning: "Assessing Mama's initial patrol trajectory.",
      targetTile: [8, 3],
      targetPos: { x: 8 * TILE_SIZE + 25, y: 3 * TILE_SIZE + 25 },
      stoneCooldown: 0.0,
      decisionTimer: 0.0,
      stuckTimer: 0.0,
      lastPos: { x: 0, y: 0 },
      speechTimer: 4.0
    };
  }
}

// Global instances
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
let game = new GameState();

let toastMessage = null;
let toastTimer = 0;
function alertToast(msg, duration = 3.5) {
  toastMessage = msg;
  toastTimer = duration;
}

// Key states
const keys = {};
window.addEventListener("keydown", (e) => {
  keys[e.key.toLowerCase()] = true;
  if (e.key === " " || e.code === "Space") {
    e.preventDefault();
    throwStoneAtCursor();
  }
  if (e.key.toLowerCase() === "e") {
    handleInteractKeyPress();
  }
  if (e.key.toLowerCase() === "r") {
    restartNight();
  }
});

window.addEventListener("keyup", (e) => {
  keys[e.key.toLowerCase()] = false;
});

let mousePos = { x: 400, y: 300 };
canvas.addEventListener("mousemove", (e) => {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  mousePos.x = (e.clientX - rect.left) * scaleX;
  mousePos.y = (e.clientY - rect.top) * scaleY;
});

canvas.addEventListener("click", () => {
  throwStoneAtCursor();
});

// UI Elements
const hudNight = document.getElementById("hudNight");
const hudTimer = document.getElementById("hudTimer");
const hudMangoes = document.getElementById("hudMangoes");
const hudStones = document.getElementById("hudStones");
const hudLights = document.getElementById("hudLights");
const soundToggleBtn = document.getElementById("soundToggleBtn");
if (soundToggleBtn) {
  soundToggleBtn.addEventListener("click", () => {
    sounds.enabled = !sounds.enabled;
    soundToggleBtn.textContent = sounds.enabled ? "🔊 Audio: ON" : "🔇 Audio: MUTED";
    soundToggleBtn.classList.toggle("muted", !sounds.enabled);
  });
}

// AI Simulation Mode Elements
const simModeBtn = document.getElementById("simModeBtn");
const simModeIcon = document.getElementById("simModeIcon");
const simModeLabel = document.getElementById("simModeLabel");
const simSpeedControls = document.getElementById("simSpeedControls");
const autoNextCheckbox = document.getElementById("autoNextCheckbox");
const veluCard = document.getElementById("veluCard");
const veluActionBadge = document.getElementById("veluActionBadge");
const veluDialogueTa = document.getElementById("veluDialogueTa");
const veluDialogueEn = document.getElementById("veluDialogueEn");
const veluReasoning = document.getElementById("veluReasoning");

if (simModeBtn) {
  simModeBtn.addEventListener("click", () => {
    game.isAiMode = !game.isAiMode;
    if (game.isAiMode) {
      simModeBtn.classList.add("active-sim");
      if (simModeIcon) simModeIcon.textContent = "🤖";
      if (simModeLabel) simModeLabel.textContent = "AI Kid Mode";
      if (simSpeedControls) simSpeedControls.style.display = "flex";
      if (veluCard) veluCard.style.display = "flex";
      alertToast("🤖 AI Simulation Mode Activated! Watch Velu vs Murugesan Mama!");
      updateVeluUI();
    } else {
      simModeBtn.classList.remove("active-sim");
      if (simModeIcon) simModeIcon.textContent = "🎮";
      if (simModeLabel) simModeLabel.textContent = "Manual Play";
      if (simSpeedControls) simSpeedControls.style.display = "none";
      if (veluCard) veluCard.style.display = "none";
      alertToast("🎮 Switched back to Manual Player Control.");
    }
  });
}

document.querySelectorAll(".speed-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    game.simSpeed = parseFloat(btn.dataset.speed || "1");
  });
});

if (autoNextCheckbox) {
  autoNextCheckbox.addEventListener("change", (e) => {
    game.autoNextNight = e.target.checked;
  });
}
const interactPrompt = document.getElementById("interactPrompt");
const channelWrapper = document.getElementById("channelWrapper");
const channelFill = document.getElementById("channelFill");
const channelLabel = document.getElementById("channelLabel");

const strataStatusPill = document.getElementById("strataStatusPill");
const strataStatusText = document.getElementById("strataStatusText");

const mamaActionBadge = document.getElementById("mamaActionBadge");
const mamaDialogueTa = document.getElementById("mamaDialogueTa");
const mamaDialogueEn = document.getElementById("mamaDialogueEn");
const mamaReasoning = document.getElementById("mamaReasoning");

const listSemantic = document.getElementById("listSemantic");
const listEpisodic = document.getElementById("listEpisodic");
const listProcedural = document.getElementById("listProcedural");
const listEntity = document.getElementById("listEntity");
const countSemantic = document.getElementById("countSemantic");
const countEpisodic = document.getElementById("countEpisodic");
const countProcedural = document.getElementById("countProcedural");
const countEntity = document.getElementById("countEntity");

const dawnModal = document.getElementById("dawnModal");
const dawnOutcomeBanner = document.getElementById("dawnOutcomeBanner");
const dawnNarrativeBox = document.getElementById("dawnNarrativeBox");
const dawnPatchDetails = document.getElementById("dawnPatchDetails");
const startNextNightBtn = document.getElementById("startNextNightBtn");

startNextNightBtn.addEventListener("click", () => {
  dawnModal.classList.add("hidden");
  startNextNight();
});

// Manual Memory Injection
document.getElementById("injectBtn").addEventListener("click", async () => {
  const textInput = document.getElementById("injectTextInput");
  const pillarSelect = document.getElementById("injectPillarSelect");
  const text = textInput.value.trim();
  if (!text) return;

  try {
    const res = await fetch("/api/memory/inject", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, pillar: pillarSelect.value })
    });
    if (res.ok) {
      textInput.value = "";
      refreshMemoryState();
    }
  } catch (err) {
    console.error("Injection failed:", err);
  }
});

// ----------------- Game Loop -----------------

let lastTimestamp = performance.now();

function gameLoop(timestamp) {
  const baseDt = Math.min((timestamp - lastTimestamp) / 1000.0, 0.1);
  lastTimestamp = timestamp;
  const dt = baseDt * (game.isAiMode ? game.simSpeed : 1.0);

  if (game.isRunning) {
    if (game.isAiMode) {
      updateKidAI(dt);
    }
    update(dt);
  }
  render();

  requestAnimationFrame(gameLoop);
}
requestAnimationFrame(gameLoop);

// ----------------- Autonomous AI Kid Controller (Velu) -----------------

function updateKidAI(dt) {
  const p = game.player;
  const w = game.watchman;
  const v = game.velu;

  if (p.channeling) {
    // If channeling and Mama is within 95px, abort plucking and run!
    const distToMama = Math.hypot(w.x - p.x, w.y - p.y);
    if (distToMama < 95 && w.isChasing) {
      p.channeling = false;
      channelWrapper.classList.add("hidden");
      v.state = "ESCAPE";
      v.dialogueTa = "அய்யய்யோ! மாமா கிட்ட வந்துட்டாரு! ஓடு!";
      v.dialogueEn = "Mama is right on top of me! Run!";
      v.reasoning = "Aborted channeling due to imminent capture risk.";
      updateVeluUI();
    }
    return;
  }

  // Stone throw cooldown
  if (v.stoneCooldown > 0) v.stoneCooldown -= dt;

  // Decision loop every 0.18s
  v.decisionTimer = (v.decisionTimer || 0) + dt;
  if (v.decisionTimer > 0.18) {
    v.decisionTimer = 0.0;
    evaluateKidTactics();
    updateVeluUI();
  }

  // Execute movement
  executeKidMovement(dt);
}

function evaluateKidTactics() {
  const p = game.player;
  const w = game.watchman;
  const v = game.velu;

  const TREE_X = 8 * TILE_SIZE + 25;
  const TREE_Y = 6 * TILE_SIZE + 25;
  const SWITCH_X = 2 * TILE_SIZE + 25;
  const SWITCH_Y = 3 * TILE_SIZE + 25;
  const GATE_X = 8 * TILE_SIZE + 25;
  const GATE_Y = 0 * TILE_SIZE + 35;
  const FENCE_X = 15 * TILE_SIZE + 25;
  const FENCE_Y = 8 * TILE_SIZE + 25;
  const PIPE_X = 0 * TILE_SIZE + 25;
  const PIPE_Y = 9 * TILE_SIZE + 25;
  const HAY_X = 3 * TILE_SIZE + 25;
  const HAY_Y = 9 * TILE_SIZE + 25;
  const WELL_X = 11 * TILE_SIZE + 25;
  const WELL_Y = 9 * TILE_SIZE + 25;

  const distToMama = Math.hypot(w.x - p.x, w.y - p.y);
  const mamaToTree = Math.hypot(w.x - TREE_X, w.y - TREE_Y);

  // 1. If currently hidden, check if guard walked away
  if (p.isHidden) {
    if (distToMama > 160) {
      // Safe to emerge!
      p.isHidden = false;
      p.hiddenIn = null;
      v.dialogueTa = "மாமா தூரமா போயிட்டாரு, இப்ப நைசா வெளிய வருவோம்...";
      v.dialogueEn = "Mama walked away, emerging from hiding spot...";
      v.reasoning = "Guard cleared perimeter. Resuming orchard extraction.";
    }
    return;
  }

  // 2. Mission Phase: Escape (Holding 2 mangoes)
  if (p.holdingMangoes >= 2) {
    v.state = "ESCAPE";
    v.isSprinting = true; // Run for your life with the loot!

    // Determine safest unlocked exit
    const mainGateLocked = game.lockedObjects.has("main_gate");
    let targetExit = { x: GATE_X, y: GATE_Y, name: "main_gate" };

    if (mainGateLocked) {
      // Main Gate is locked! Choose between Back Fence and Drain Pipe
      const distToFence = Math.hypot(p.x - FENCE_X, p.y - FENCE_Y);
      const distToPipe = Math.hypot(p.x - PIPE_X, p.y - PIPE_Y);
      const mamaToFence = Math.hypot(w.x - FENCE_X, w.y - FENCE_Y);
      const mamaToPipe = Math.hypot(w.x - PIPE_X, w.y - PIPE_Y);

      // Prefer exit that has greater distance from Mama
      if (mamaToFence > mamaToPipe) {
        targetExit = { x: FENCE_X, y: FENCE_Y, name: "back_fence" };
      } else {
        targetExit = { x: PIPE_X, y: PIPE_Y, name: "drain_pipe" };
      }
      v.dialogueTa = `மெயின் கேட் பூட்டியிருக்கு! ${targetExit.name === 'back_fence' ? 'முள்வேலி' : 'மதகு குழாய்'} வழியா தப்பிப்போம்!`;
      v.dialogueEn = `Main Gate is padlocked! Escaping through ${targetExit.name}!`;
    } else {
      v.dialogueTa = "ரெண்டு பங்கனப்பள்ளி மாம்பழம் கிடைச்சாச்சு! மெயின் கேட் வழியா ஓடுவோம்!";
      v.dialogueEn = "Got both Banganapalli mangoes! Sprinting out the main gate!";
    }

    v.targetPos = { x: targetExit.x, y: targetExit.y };
    v.reasoning = `Objective fulfilled. Evading guard toward ${targetExit.name}.`;

    // If near exit (< 48px), trigger interact to escape!
    if (Math.hypot(p.x - targetExit.x, p.y - targetExit.y) < 48) {
      handleInteractKeyPress();
    }
    return;
  }

  // 3. Danger Reaction: Chase / Caught in flashlight
  if (w.isChasing || (distToMama < 125 && Math.abs(Math.atan2(p.y - w.y, p.x - w.x) - w.angle) < 0.6)) {
    // If adjacent to haystack or well, duck in!
    if (Math.hypot(p.x - HAY_X, p.y - HAY_Y) < 42) {
      p.isHidden = true;
      p.hiddenIn = "haystack";
      game.nightLog.hidingSpotsUsed.add("haystack");
      v.state = "HIDE";
      v.dialogueTa = "வைக்கோல் போருக்குள்ள ஒளிஞ்சாச்சு! மாமாவுக்கு தெரியாது!";
      v.dialogueEn = "Dived into the haystack! Mama lost visual.";
      v.reasoning = "Broke visual cone by diving into haystack refuge.";
      return;
    }
    if (Math.hypot(p.x - WELL_X, p.y - WELL_Y) < 42) {
      p.isHidden = true;
      p.hiddenIn = "mud_well";
      game.nightLog.hidingSpotsUsed.add("mud_well");
      v.state = "HIDE";
      v.dialogueTa = "கிணற்று மேட்டுல பதுங்கியாச்சு!";
      v.dialogueEn = "Crouched behind old well parapet!";
      v.reasoning = "Broke visual cone behind old well.";
      return;
    }

    // Try stone distraction if available
    if (game.stonesLeft > 0 && v.stoneCooldown <= 0) {
      // Throw stone opposite to Mama
      const stoneTileX = w.x > 400 ? 2 : 14;
      const stoneTileY = w.y > 300 ? 2 : 10;
      throwStoneToTile(stoneTileX, stoneTileY);
      v.stoneCooldown = 4.5;
      v.state = "DISTRACT";
      v.dialogueTa = "மாமா துரத்துறாரு! கல்லை தூக்கி வீசி திசை திருப்புவோம்!";
      v.dialogueEn = "Mama is chasing! Throwing pebble to mislead him!";
      v.reasoning = `Deployed acoustic decoy to tile (${stoneTileX}, ${stoneTileY}) to divert pursuit.`;
      return;
    }

    // Otherwise sprint to break line of sight behind tree or shed
    v.isSprinting = true;
    v.state = "EVADE";
    v.targetPos = { x: p.x < 400 ? 80 : 720, y: p.y < 300 ? 520 : 80 };
    v.dialogueTa = "மாமா தடியோட வர்றாரு! ஓடி ஒளிவோம்!";
    v.dialogueEn = "Mama is swinging his stick! Sprinting to cover!";
    v.reasoning = "Active pursuit evasion: running along shadows.";
    return;
  }

  // 4. Sabotage: Flip Light Switch if close and night >= 2
  if (game.lightsOn && game.nightNumber >= 2 && p.holdingMangoes === 0 && Math.hypot(p.x - SWITCH_X, p.y - SWITCH_Y) < 140 && Math.hypot(w.x - SWITCH_X, w.y - SWITCH_Y) > 180) {
    v.state = "CUT_LIGHTS";
    v.targetPos = { x: SWITCH_X, y: SWITCH_Y };
    v.isSprinting = false;
    v.dialogueTa = "பம்பு செட் சுவிட்ச்சை அணைச்சாச்சுன்னா இருட்டுல மாமாவுக்கு கண்ணு தெரியாது!";
    v.dialogueEn = "Flipping light switch OFF to reduce guard's vision cone!";
    v.reasoning = "Opportunistic power cut: guard is on opposite perimeter.";
    if (Math.hypot(p.x - SWITCH_X, p.y - SWITCH_Y) < 38) {
      handleInteractKeyPress();
    }
    return;
  }

  // 5. Infiltration / Harvest: Tree Raiding
  if (mamaToTree < 135) {
    // Guard is camping the tree! Distract him with a stone
    if (game.stonesLeft > 0 && v.stoneCooldown <= 0) {
      const decoyTileX = w.x > 400 ? 2 : 13;
      const decoyTileY = 9;
      throwStoneToTile(decoyTileX, decoyTileY);
      v.stoneCooldown = 5.0;
      v.state = "DISTRACT";
      v.dialogueTa = "மாமா மரத்தண்டை நிக்கிறாரு! கிணத்து மேட்டுல கல்லை வீசி திசை திருப்புவோம்!";
      v.dialogueEn = "Guard is guarding tree! Throwing stone at the well to pull him away!";
      v.reasoning = `Acoustic decoy thrown to (${decoyTileX}, ${decoyTileY}) to pull guard off central tree.`;
      v.targetPos = { x: 4 * TILE_SIZE + 25, y: 5 * TILE_SIZE + 25 };
      v.isSprinting = false;
    } else {
      // Stalk from safe distance
      v.state = "STALK";
      v.targetPos = { x: 4 * TILE_SIZE + 25, y: 5 * TILE_SIZE + 25 };
      v.isSprinting = false;
      v.dialogueTa = "மாமா மரத்தை விட்டு நகர்ற வரைக்கும் பதுங்கி பாப்போம்...";
      v.dialogueEn = "Waiting in shadows until guard leaves tree area...";
      v.reasoning = "Tree heavily contested. Patiently awaiting patrol rotation.";
    }
  } else {
    // Tree is clear! Approach and pluck mangoes!
    v.state = "PLUCK";
    v.targetPos = { x: TREE_X, y: TREE_Y };
    v.isSprinting = false;
    v.dialogueTa = "மரம் காலியா இருக்கு! டக்குனு மாம்பழத்தை பறிப்போம்!";
    v.dialogueEn = "Tree is unguarded! Moving in to harvest Banganapalli mangoes!";
    v.reasoning = "Guard has rotated away from central tree. Harvesting window open.";

    if (Math.hypot(p.x - TREE_X, p.y - TREE_Y) < 55) {
      handleInteractKeyPress();
    }
  }
}

function executeKidMovement(dt) {
  const p = game.player;
  const v = game.velu;
  if (p.channeling || p.isHidden) return;

  const dx = v.targetPos.x - p.x;
  const dy = v.targetPos.y - p.y;
  const dist = Math.hypot(dx, dy);

  if (dist > 6) {
    const angle = Math.atan2(dy, dx);
    const speed = v.isSprinting ? p.sprintSpeed : p.speed;
    const nextX = p.x + Math.cos(angle) * speed * 60 * dt;
    const nextY = p.y + Math.sin(angle) * speed * 60 * dt;

    let moved = false;
    if (!isWallCollision(nextX, nextY, p.radius)) {
      p.x = nextX;
      p.y = nextY;
      moved = true;
    } else {
      if (!isWallCollision(nextX, p.y, p.radius)) {
        p.x = nextX;
        moved = true;
      } else if (!isWallCollision(p.x, nextY, p.radius)) {
        p.y = nextY;
        moved = true;
      }
    }

    // Unstuck mechanic
    if (!moved || Math.hypot(p.x - v.lastPos.x, p.y - v.lastPos.y) < 0.5) {
      v.stuckTimer = (v.stuckTimer || 0) + dt;
      if (v.stuckTimer > 0.25) {
        p.x += (Math.random() - 0.5) * 12;
        p.y += (Math.random() - 0.5) * 12;
        v.stuckTimer = 0.0;
      }
    } else {
      v.stuckTimer = 0.0;
    }

    v.lastPos.x = p.x;
    v.lastPos.y = p.y;

    // Creaking gate entry detection for AI
    if (!game.hasTriggeredEntryCreak && p.y > 60 && !game.lockedObjects.has("main_gate")) {
      game.hasTriggeredEntryCreak = true;
      sounds.playGateCreak();
      spawnSoundRipple(8 * TILE_SIZE + 25, 30, 280, "rgba(239, 68, 68, 0.7)", "GATE_CREAK");
      const w = game.watchman;
      if (!w.isChasing) {
        w.targetTile = [8, 4];
        w.angle = -Math.PI / 2;
        w.speechText = "மெயின் கேட் திறக்குற சத்தம் கேக்குதே! யார்டா அங்கே?!";
        w.speechEn = "I hear the main gate creaking! Who's there?!";
        w.speechTimer = 4.5;
        mamaActionBadge.textContent = "INVESTIGATE";
        mamaDialogueTa.textContent = `"${w.speechText}"`;
        mamaDialogueEn.textContent = `"${w.speechEn}"`;
        mamaReasoning.innerHTML = "<strong>Reasoning:</strong> Rusty iron hinges creaked loudly at north gate.";
        dispatchSensorEvent("NOISE_HEARD", "main_gate", 8, 1, "Main gate iron hinges creaked upon entering orchard.");
      }
    }

    // Sprint noise
    if (v.isSprinting) {
      v.sprintTimer = (v.sprintTimer || 0) + dt;
      if (v.sprintTimer > 0.18) {
        v.sprintTimer = 0.0;
        spawnSoundRipple(p.x, p.y, 320, "rgba(251, 191, 36, 0.65)", "SPRINT_STEPS");
      }
    } else {
      v.sprintTimer = 0.0;
    }
  }
}

function updateVeluUI() {
  if (!game.isAiMode) return;
  const v = game.velu;
  if (veluActionBadge) veluActionBadge.textContent = v.state;
  if (veluDialogueTa) veluDialogueTa.textContent = `"${v.dialogueTa}"`;
  if (veluDialogueEn) veluDialogueEn.textContent = `"${v.dialogueEn}"`;
  if (veluReasoning) veluReasoning.innerHTML = `<strong>Strategy:</strong> ${v.reasoning}`;
}

// ----------------- Update Logic -----------------

function update(dt) {
  // 1. Endless Survival Timer (Plays until caught or escaped with mangoes!)
  game.timer += dt;

  // Toast alert countdown
  if (toastTimer > 0) {
    toastTimer -= dt;
  }

  // Decrease spawn stealth grace timer
  if (game.spawnGraceTimer > 0) {
    game.spawnGraceTimer -= dt;
  }

  // 2. Handle Player Movement (Manual only if not AI mode)
  handlePlayerMovement(dt);

  // 3. Handle Channeling Actions (Plucking / Squeezing fence)
  handleChanneling(dt);

  // 4. Update Flying Stones and Sound Ripples
  updateFlyingStones(dt);
  updateSoundRipples(dt);

  // 5. Watchman AI Sensors & Movement
  updateWatchman(dt);

  // 6. Check Win/Loss Intersections
  checkInteractions();

  // 7. Update HUD values
  updateHUD();
}

function handlePlayerMovement(dt) {
  if (game.isAiMode) return; // In AI simulation mode, Velu's cognitive brain controls movement!
  const p = game.player;
  if (p.channeling) return; // Player cannot move while plucking or squeezing

  let dx = 0;
  let dy = 0;

  if (keys["w"] || keys["arrowup"]) dy -= 1;
  if (keys["s"] || keys["arrowdown"]) dy += 1;
  if (keys["a"] || keys["arrowleft"]) dx -= 1;
  if (keys["d"] || keys["arrowright"]) dx += 1;

  if (dx !== 0 && dy !== 0) {
    dx *= 0.7071;
    dy *= 0.7071;
  }

  const isSprinting = (keys["shift"] || keys["sprint"]) && (dx !== 0 || dy !== 0);
  p.isSprinting = isSprinting;
  const speed = isSprinting ? p.sprintSpeed : p.speed;

  // Unhide if player moves away from hiding spot
  if (p.isHidden && (dx !== 0 || dy !== 0)) {
    p.isHidden = false;
    p.hiddenIn = null;
  }

  const nextX = p.x + dx * speed * 60 * dt;
  const nextY = p.y + dy * speed * 60 * dt;

  // Collision with map borders & walls
  if (!isWallCollision(nextX, p.y, p.radius)) {
    p.x = Math.max(p.radius, Math.min(800 - p.radius, nextX));
  }
  if (!isWallCollision(p.x, nextY, p.radius)) {
    p.y = Math.max(p.radius, Math.min(600 - p.radius, nextY));
  }

  // Creaking gate alert when stepping into the grove from Main Gate!
  if (!game.hasTriggeredEntryCreak && p.y > 60 && !game.lockedObjects.has("main_gate")) {
    game.hasTriggeredEntryCreak = true;
    sounds.playGateCreak();
    spawnSoundRipple(8 * TILE_SIZE + 25, 30, 280, "rgba(239, 68, 68, 0.7)", "GATE_CREAK");
    const w = game.watchman;
    if (!w.isChasing) {
      w.targetTile = [8, 4];
      w.angle = -Math.PI / 2; // Face north towards entrance
      w.speechText = "மெயின் கேட் திறக்குற சத்தம் கேக்குதே! யார்டா அங்கே?!";
      w.speechEn = "I hear the main gate creaking! Who's there?!";
      w.speechTimer = 4.5;
      mamaActionBadge.textContent = "INVESTIGATE";
      mamaDialogueTa.textContent = `"${w.speechText}"`;
      mamaDialogueEn.textContent = `"${w.speechEn}"`;
      mamaReasoning.innerHTML = "<strong>Reasoning:</strong> Rusty iron hinges creaked loudly at north gate. Turning flashlight to inspect entrance.";
      dispatchSensorEvent("NOISE_HEARD", "main_gate", 8, 1, "Main gate iron hinges creaked upon entering orchard.");
    }
  }

  // If sprinting, spawn footstep noise rings periodically with 320px audible radius
  if (isSprinting) {
    p.sprintTimer = (p.sprintTimer || 0) + dt;
    if (p.sprintTimer > 0.18) {
      p.sprintTimer = 0.0;
      spawnSoundRipple(p.x, p.y, 320, "rgba(251, 191, 36, 0.65)", "SPRINT_STEPS");
    }
  } else {
    p.sprintTimer = 0.0;
  }
}

function isWallCollision(x, y, radius) {
  const minTileX = Math.floor((x - radius) / TILE_SIZE);
  const maxTileX = Math.floor((x + radius) / TILE_SIZE);
  const minTileY = Math.floor((y - radius) / TILE_SIZE);
  const maxTileY = Math.floor((y + radius) / TILE_SIZE);

  for (let tx = minTileX; tx <= maxTileX; tx++) {
    for (let ty = minTileY; ty <= maxTileY; ty++) {
      if (WALL_TILES.has(`${tx},${ty}`)) {
        return true;
      }
    }
  }
  return false;
}

function handleChanneling(dt) {
  const p = game.player;
  if (!p.channeling) {
    channelWrapper.classList.add("hidden");
    return;
  }

  channelWrapper.classList.remove("hidden");
  p.channelProgress += dt;
  const pct = Math.min(100, (p.channelProgress / p.channelDuration) * 100);
  channelFill.style.width = `${pct}%`;

  // Leaf rustle noise while plucking mangoes
  if (p.channelTarget === "mango_tree") {
    p.rustleTimer = (p.rustleTimer || 0) + dt;
    if (p.rustleTimer > 0.6) {
      p.rustleTimer = 0.0;
      sounds.playRustle();
      spawnSoundRipple(p.x, p.y, 140, "rgba(34, 197, 94, 0.55)", "LEAF_RUSTLE");
      const distMama = Math.hypot(game.watchman.x - p.x, game.watchman.y - p.y);
      if (distMama <= 170 && !game.watchman.isChasing) {
        const w = game.watchman;
        w.currentAction = "INVESTIGATE";
        w.targetTile = [8, 6];
        w.angle = Math.atan2(p.y - w.y, p.x - w.x);
        w.speechText = "மாமரத்தில சலசலப்பு கேக்குது! மாங்காயை பறிக்கிறியாடா?!";
        w.speechEn = "Rustling leaves in the mango tree! Plucking my mangoes, are you?!";
        w.speechTimer = 4.0;
        mamaActionBadge.textContent = "INVESTIGATE";
        mamaDialogueTa.textContent = `"${w.speechText}"`;
        mamaDialogueEn.textContent = `"${w.speechEn}"`;
        mamaReasoning.innerHTML = "<strong>Reasoning:</strong> Acoustic leaf rustle detected at central mango tree asset.";
        dispatchSensorEvent("NOISE_HEARD", "mango_tree", 8, 6, "Acoustic leaf rustle detected at central mango tree.");
      }
    }
  }

  if (p.channelProgress >= p.channelDuration) {
    p.channeling = false;
    channelWrapper.classList.add("hidden");
    completeChannelAction(p.channelTarget);
  }
}

function completeChannelAction(target) {
  const p = game.player;
  if (target === "mango_tree") {
    if (game.mangoesOnTree > 0) {
      game.mangoesOnTree--;
      p.holdingMangoes++;
      game.nightLog.mangoesStolen++;
      sounds.playMangoPluck();
      spawnSoundRipple(p.x, p.y, 90, "rgba(34, 197, 94, 0.6)", "MANGO_PLUCKED");
    }
  } else if (target === "back_fence") {
    // Escaped through back fence!
    if (p.holdingMangoes >= 2) {
      sounds.playWinFanfare();
      game.nightLog.exitUsed = "back_fence";
      triggerNightEnd(true, "Successfully slipped through the back thorn fence with 2 Banganapalli mangoes!");
    }
  }
}

function handleInteractKeyPress() {
  const p = game.player;
  const tileX = Math.floor(p.x / TILE_SIZE);
  const tileY = Math.floor(p.y / TILE_SIZE);

  // Check pump-set switch
  if (Math.hypot(p.x - (2 * TILE_SIZE + 25), p.y - (3 * TILE_SIZE + 25)) < 40) {
    sounds.playSwitchClick();
    game.lightsOn = !game.lightsOn;
    if (!game.lightsOn) game.nightLog.lightsCutCount++;
    spawnSoundRipple(p.x, p.y, 200, "rgba(244, 63, 94, 0.5)", "LIGHTS_CUT");
    dispatchSensorEvent("LIGHTS_CUT", "pumpset_switch", 2, 3, "Player flipped pumpset floodlights switch.");
    return;
  }

  // Check central mango tree
  if (Math.hypot(p.x - (8 * TILE_SIZE + 25), p.y - (6 * TILE_SIZE + 25)) < 55) {
    if (game.mangoesOnTree > 0 && p.holdingMangoes < 2) {
      p.channeling = true;
      p.channelProgress = 0.0;
      p.channelDuration = 2.0; // 2 seconds per mango
      p.channelTarget = "mango_tree";
      channelLabel.textContent = "Plucking Banganapalli Mango (Hold Still)...";
    }
    return;
  }

  // Check Haystack hiding
  if (Math.hypot(p.x - (3 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 45) {
    p.isHidden = !p.isHidden;
    p.hiddenIn = p.isHidden ? "haystack" : null;
    if (p.isHidden) game.nightLog.hidingSpotsUsed.add("haystack");
    return;
  }

  // Check Mud Well hiding
  if (Math.hypot(p.x - (11 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 45) {
    p.isHidden = !p.isHidden;
    p.hiddenIn = p.isHidden ? "mud_well" : null;
    if (p.isHidden) game.nightLog.hidingSpotsUsed.add("mud_well");
    return;
  }

  // Check Main Gate escape
  if (Math.hypot(p.x - (8 * TILE_SIZE + 25), p.y - (0 * TILE_SIZE + 25)) < 50) {
    if (game.lockedObjects.has("main_gate")) {
      sounds.playGateRattle();
      spawnSoundRipple(p.x, p.y, 160, "rgba(239, 68, 68, 0.7)", "GATE_LOCKED");
      alertToast("🔒 மெயின் கேட் பூட்டியிருக்கு! இரும்பு சங்கிலி மாட்டியிருக்கான்! (Main Gate Padlocked!)");
      return;
    }
    if (p.holdingMangoes >= 2) {
      sounds.playGateCreak();
      sounds.playWinFanfare();
      game.nightLog.exitUsed = "main_gate";
      triggerNightEnd(true, "Burst open the iron main gate and sprinted into the dark with delicious mangoes!");
    }
    return;
  }

  // Check Drain Pipe escape
  if (Math.hypot(p.x - (0 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 50) {
    if (p.holdingMangoes >= 2) {
      if (game.trappedObjects.has("drain_pipe")) {
        sounds.playCanClatter();
        spawnSoundRipple(0 * TILE_SIZE + 25, 9 * TILE_SIZE + 25, 340, "rgba(244, 63, 94, 0.8)", "TRIPWIRE_ALARM");
        const w = game.watchman;
        w.isChasing = false;
        w.currentAction = "INVESTIGATE";
        w.targetTile = [0, 9];
        w.speechText = "மதகு குழாயில் டின் சத்தம் கேக்குதே! யார்டா அங்கே?!";
        w.speechEn = "Tin cans clattering at the drain pipe! Who's there?!";
        w.speechTimer = 5.0;
        dispatchSensorEvent("NOISE_HEARD", "drain_pipe", 0, 9, "Tin can tripwire rattled loudly at drain pipe exit!");
      }
      sounds.playWinFanfare();
      game.nightLog.exitUsed = "drain_pipe";
      triggerNightEnd(true, "Crawled through the old stone drain culvert clutching the ripe mangoes!");
    }
    return;
  }

  // Check Back Fence channel escape
  if (Math.hypot(p.x - (15 * TILE_SIZE + 25), p.y - (8 * TILE_SIZE + 25)) < 50) {
    if (p.holdingMangoes >= 2) {
      const isBlocked = game.blockedObjects.has("back_fence");
      p.channeling = true;
      p.channelProgress = 0.0;
      p.channelDuration = isBlocked ? 4.0 : 2.0;
      p.channelTarget = "back_fence";
      channelLabel.textContent = isBlocked
        ? "🌿 Cutting through reinforced thorn brambles (4s)..."
        : "Squeezing through thorn fence (2s)...";
    }
    return;
  }
}

function throwStoneAtCursor() {
  const targetTileX = Math.min(15, Math.max(0, Math.floor(mousePos.x / TILE_SIZE)));
  const targetTileY = Math.min(11, Math.max(0, Math.floor(mousePos.y / TILE_SIZE)));
  throwStoneToTile(targetTileX, targetTileY);
}

function throwStoneToTile(targetTileX, targetTileY) {
  if (game.stonesLeft <= 0) return false;
  game.stonesLeft--;

  sounds.playStoneThrow();

  const soundX = targetTileX * TILE_SIZE + 25;
  const soundY = targetTileY * TILE_SIZE + 25;

  // Add animated flying stone projectile from player to target
  game.flyingStones.push({
    startX: game.player.x,
    startY: game.player.y,
    targetX: soundX,
    targetY: soundY,
    currX: game.player.x,
    currY: game.player.y,
    progress: 0.0,
    duration: 0.32,
    targetTileX: targetTileX,
    targetTileY: targetTileY
  });

  game.nightLog.stonesThrownAt.push(`(${targetTileX},${targetTileY})`);

  // IMMEDIATE DISTRACTION OF MURUGESAN MAMA!
  // Instantly cancels chase, sets target to stone landing tile, and rotates flashlight!
  const w = game.watchman;
  w.isChasing = false;
  w.currentAction = "INVESTIGATE";
  w.targetTile = [targetTileX, targetTileY];
  w.angle = Math.atan2(soundY - w.y, soundX - w.x);
  w.speechText = "டேய்! அங்கே என்னடா சத்தம்?! கல்லை வீசுனது யாருடா?!";
  w.speechEn = "Hey! What was that noise over there?! Who threw that stone?!";
  w.speechTimer = 5.0;

  // Immediate UI Inspector sync
  mamaActionBadge.textContent = "INVESTIGATE";
  mamaDialogueTa.textContent = `"${w.speechText}"`;
  mamaDialogueEn.textContent = `"${w.speechEn}"`;
  mamaReasoning.innerHTML = `<strong>Reasoning:</strong> Distracted by pebble impact at tile (${targetTileX}, ${targetTileY}). Investigating acoustic source.`;
  return true;
}

function updateFlyingStones(dt) {
  for (let i = game.flyingStones.length - 1; i >= 0; i--) {
    const s = game.flyingStones[i];
    s.progress += dt / s.duration;
    if (s.progress >= 1.0) {
      // Stone lands!
      spawnSoundRipple(s.targetX, s.targetY, 280, "rgba(56, 189, 248, 0.7)", "STONE_NOISE");
      
      // Send single sensor event to Strata
      let closestObj = "ground";
      let minD = 999;
      for (const [k, def] of Object.entries(OBJECT_DEFS)) {
        const d = Math.hypot(s.targetTileX - def.x, s.targetTileY - def.y);
        if (d < minD) {
          minD = d;
          closestObj = k;
        }
      }
      dispatchSensorEvent("NOISE_HEARD", closestObj, s.targetTileX, s.targetTileY, `Stone clatter heard near ${closestObj}.`);

      game.flyingStones.splice(i, 1);
    } else {
      // Parabolic flight arc
      s.currX = s.startX + (s.targetX - s.startX) * s.progress;
      s.currY = s.startY + (s.targetY - s.startY) * s.progress - Math.sin(s.progress * Math.PI) * 45;
    }
  }
}

function spawnSoundRipple(x, y, maxRadius, color, type) {
  if (type === "STONE_NOISE") {
    sounds.playStoneHit();
  } else if (type === "SPRINT_STEPS") {
    sounds.playFootstep(true);
  }

  const ripple = {
    x, y,
    maxRadius,
    currentRadius: 5,
    alpha: 1.0,
    color,
    type
  };
  game.soundRipples.push(ripple);

  // Check if watchman hears this noise (for footsteps or non-stone sounds)
  if (type !== "STONE_NOISE") {
    const distToMama = Math.hypot(game.watchman.x - x, game.watchman.y - y);
    if (distToMama <= maxRadius) {
      const tileX = Math.floor(x / TILE_SIZE);
      const tileY = Math.floor(y / TILE_SIZE);

      // IMMEDIATE REACTIVE ALERT FOR SPRINT FOOTSTEPS!
      if (type === "SPRINT_STEPS") {
        const w = game.watchman;
        // Instantly rotate flashlight toward the footsteps!
        w.angle = Math.atan2(y - w.y, x - w.x);
        w.targetTile = [tileX, tileY];
        if (!w.isChasing) {
          w.currentAction = "INVESTIGATE";
          w.speechText = "டேய்! காலடி சத்தம் கேக்குதே! யார்டா அங்கே ஓடுறது?!";
          w.speechEn = "Hey! I hear running footsteps! Who is sprinting over there?!";
          w.speechTimer = 3.5;
          mamaActionBadge.textContent = "INVESTIGATE";
          mamaDialogueTa.textContent = `"${w.speechText}"`;
          mamaDialogueEn.textContent = `"${w.speechEn}"`;
          mamaReasoning.innerHTML = `<strong>Reasoning:</strong> Loud sprint footsteps heard at (${tileX}, ${tileY}). Turning flashlight to investigate immediately.`;
        }
      }

      // Throttle backend dispatch so network is not flooded
      const now = performance.now();
      if (!game.lastNoiseDispatch || (now - game.lastNoiseDispatch > 1200)) {
        game.lastNoiseDispatch = now;
        dispatchSensorEvent("NOISE_HEARD", type, tileX, tileY, `Acoustic trigger heard at (${tileX}, ${tileY}).`);
      }
    }
  }
}

function updateSoundRipples(dt) {
  for (let i = game.soundRipples.length - 1; i >= 0; i--) {
    const r = game.soundRipples[i];
    r.currentRadius += 220 * dt;
    r.alpha = Math.max(0, 1.0 - (r.currentRadius / r.maxRadius));
    if (r.currentRadius >= r.maxRadius || r.alpha <= 0) {
      game.soundRipples.splice(i, 1);
    }
  }
}

// ----------------- Watchman AI & Sensors -----------------

function updateWatchman(dt) {
  const w = game.watchman;
  const p = game.player;

  // Flashlight Cone Range
  const visionDistance = game.lightsOn ? 6.0 * TILE_SIZE : 4.5 * TILE_SIZE;
  const halfFov = (75 * Math.PI) / 360;

  // Check if Player is spotted
  const distToPlayer = Math.hypot(p.x - w.x, p.y - w.y);
  const angleToPlayer = Math.atan2(p.y - w.y, p.x - w.x);
  let angleDiff = angleToPlayer - w.angle;
  while (angleDiff > Math.PI) angleDiff -= 2 * Math.PI;
  while (angleDiff < -Math.PI) angleDiff += 2 * Math.PI;

  const playerInCone = distToPlayer <= visionDistance && Math.abs(angleDiff) <= halfFov;
  const hasLineOfSight = !isRayBlockedByWalls(w.x, w.y, p.x, p.y);

  // Spotting player - ONLY after spawn grace period ends
  if (game.spawnGraceTimer <= 0 && playerInCone && hasLineOfSight && !p.isHidden) {
    if (!w.isChasing) {
      w.isChasing = true;
      w.chaseLostTimer = 0.0;
      w.currentAction = "CHASE";
      dispatchSensorEvent(
        "PLAYER_SPOTTED",
        "grove_floor",
        Math.floor(p.x / TILE_SIZE),
        Math.floor(p.y / TILE_SIZE),
        "Player clearly visible inside flashlight cone!"
      );
    }
  }

  // Handle active chase and stealth breaks
  if (w.isChasing) {
    if (p.isHidden) {
      // Player dived into a hiding spot (haystack/well)! Mama loses sight!
      w.isChasing = false;
      w.currentAction = "INVESTIGATE";
      w.targetTile = [Math.floor(p.x / TILE_SIZE), Math.floor(p.y / TILE_SIZE)];
      w.speechText = "எங்கே போனான்?! கண்ணு முன்னாடி மறைஞ்சுட்டானே!";
      w.speechEn = "Where did he go?! He vanished right before my eyes!";
      w.speechTimer = 4.0;
    } else if (!playerInCone || !hasLineOfSight) {
      // Player broke line of sight behind trees/shed
      w.chaseLostTimer = (w.chaseLostTimer || 0) + dt;
      if (w.chaseLostTimer > 2.0) {
        // Lost visual for 2 seconds - give up sprint chase and resume patrol!
        w.isChasing = false;
        w.currentAction = "PATROL";
        w.speechText = "ஓடிட்டான் போல... நல்லா சுத்தி பாப்போம்.";
        w.speechEn = "He slipped into the shadows... let me resume my rounds.";
        w.speechTimer = 4.0;
      }
    } else {
      w.chaseLostTimer = 0.0;
    }
  }

  // Movement toward target
  let targetX = w.targetTile[0] * TILE_SIZE + 25;
  let targetY = w.targetTile[1] * TILE_SIZE + 25;

  if (w.isChasing) {
    targetX = p.x;
    targetY = p.y;
  }

  const dx = targetX - w.x;
  const dy = targetY - w.y;
  const distToTarget = Math.hypot(dx, dy);

  if (distToTarget > 8) {
    w.scanTimer = 0.0;
    const moveAngle = Math.atan2(dy, dx);
    w.angle = moveAngle;
    const speed = w.isChasing ? w.chaseSpeed : w.speed;
    const nextX = w.x + Math.cos(moveAngle) * speed * 60 * dt;
    const nextY = w.y + Math.sin(moveAngle) * speed * 60 * dt;

    if (!isWallCollision(nextX, nextY, w.radius)) {
      w.x = nextX;
      w.y = nextY;
    } else {
      // Slide
      if (!isWallCollision(nextX, w.y, w.radius)) w.x = nextX;
      else if (!isWallCollision(w.x, nextY, w.radius)) w.y = nextY;
    }
  } else {
    // Reached destination tile - perform 360-degree flashlight scanning sweep!
    if (!w.isChasing) {
      w.scanTimer = (w.scanTimer || 0) + dt;
      if (w.scanTimer < 2.5) {
        w.angle += 3.0 * dt;
      }
    }
    if (w.currentAction === "SEARCH_HIDING") {
      w.stickSwinging = true;
      // If player is hidden here, catch them!
      if (p.isHidden && distToPlayer < 40) {
        sounds.playCaught();
        triggerNightEnd(false, "Murugesan Mama poked the haystack with his stick and caught you red-handed!");
      }
    }
  }

  // Check Mama catching player (guarded by spawn grace timer)
  if (game.spawnGraceTimer <= 0 && distToPlayer <= w.radius + p.radius && !p.isHidden) {
    sounds.playCaught();
    triggerNightEnd(false, "Murugesan Mama grabbed you by the collar! 'டேய்! மாங்காய் திருடறியா?!'");
  }

  // Periodic decision tick every 2.5s if not chasing
  const now = performance.now();
  if (!w.isChasing && now - game.lastDecisionTick > 2800) {
    game.lastDecisionTick = now;
    const currTileX = Math.floor(w.x / TILE_SIZE);
    const currTileY = Math.floor(w.y / TILE_SIZE);
    let nearestObj = "mango_tree";
    for (const [k, def] of Object.entries(OBJECT_DEFS)) {
      if (Math.hypot(currTileX - def.x, currTileY - def.y) <= 2) {
        nearestObj = k;
        break;
      }
    }
    dispatchSensorEvent("PATROL_TICK", nearestObj, currTileX, currTileY, "Standard routine patrol checkpoint.");
  }
}

function isRayBlockedByWalls(x1, y1, x2, y2) {
  const steps = 15;
  for (let i = 1; i < steps; i++) {
    const rx = x1 + (x2 - x1) * (i / steps);
    const ry = y1 + (y2 - y1) * (i / steps);
    const tx = Math.floor(rx / TILE_SIZE);
    const ty = Math.floor(ry / TILE_SIZE);
    if (WALL_TILES.has(`${tx},${ty}`)) {
      return true;
    }
  }
  return false;
}

// ----------------- Strata API Dispatch & Inspector -----------------

async function dispatchSensorEvent(eventType, locationName, tileX, tileY, details) {
  const payload = {
    night_number: game.nightNumber,
    time_elapsed: Math.round(60.0 - game.timer),
    event_type: eventType,
    location_name: locationName,
    tile_x: tileX,
    tile_y: tileY,
    lights_on: game.lightsOn,
    mangoes_remaining: game.mangoesOnTree,
    blocked_objects: [],
    trapped_objects: [],
    details: details
  };

  try {
    const res = await fetch("/api/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const decision = await res.json();
      applyWatchmanDecision(decision);
    }
  } catch (err) {
    console.error("Action dispatch failed:", err);
  }
}

function applyWatchmanDecision(d) {
  const w = game.watchman;
  w.currentAction = d.action;
  if (d.action !== "CHASE") {
    w.isChasing = false;
  }
  w.speechText = d.dialogue_ta;
  w.speechEn = d.dialogue_en;
  w.speechTimer = 5.0;

  if (d.target_tile && d.target_tile.length === 2) {
    w.targetTile = d.target_tile;
  }

  // Update Right Panel UI
  mamaActionBadge.textContent = d.action;
  mamaDialogueTa.textContent = `"${d.dialogue_ta}"`;
  mamaDialogueEn.textContent = `"${d.dialogue_en}"`;
  mamaReasoning.innerHTML = `<strong>Reasoning:</strong> ${d.reasoning}`;

  // If memory context returned, refresh inspector
  refreshMemoryState();
}

async function refreshMemoryState() {
  try {
    const res = await fetch("/api/memory/state");
    if (!res.ok) return;
    const data = await res.json();

    // Update Live Connection Pill
    if (strataStatusPill) {
      if (data.is_connected_to_strata) {
        strataStatusPill.innerHTML = `
          <span class="status-dot online"></span>
          <span class="status-text">🟢 Strata Live (Neon DB): Connected</span>
        `;
      } else {
        strataStatusPill.innerHTML = `
          <span class="status-dot offline"></span>
          <span class="status-text">🟡 Strata Offline: Local Fallback Mode</span>
        `;
      }
    }

    // Semantic
    countSemantic.textContent = `${data.semantic?.length || 0} rules`;
    listSemantic.innerHTML = (data.semantic || []).map(s => `
      <div class="memory-item">
        <strong>[Rule]</strong> ${s.statement}
      </div>
    `).join("");

    // Episodic
    countEpisodic.textContent = `${data.episodic?.length || 0} nights`;
    if (!data.episodic || data.episodic.length === 0) {
      listEpisodic.innerHTML = `<div class="empty-hint">No past nights recorded yet. Pluck mangoes or get caught!</div>`;
    } else {
      listEpisodic.innerHTML = data.episodic.map(e => `
        <div class="memory-item">
          <strong>[Night ${e.night_number}]</strong> ${e.summary}
        </div>
      `).join("");
    }

    // Procedural
    const activeProc = (data.procedural || []).filter(p => p.is_active !== false);
    countProcedural.textContent = activeProc.length > 0 ? `${activeProc[0].procedure_name} v${activeProc[0].version}` : "v1";
    listProcedural.innerHTML = (data.procedural || []).map(p => `
      <div class="memory-item">
        <strong>${p.procedure_name} (v${p.version}) ${p.is_active ? '✅ Active' : '❌ Superseded'}</strong><br>
        <em>Trigger:</em> ${p.trigger_condition}<br>
        <em>Steps:</em> ${p.steps.join(" ➔ ")}
      </div>
    `).join("");

    // Entity
    countEntity.textContent = `${data.entity?.length || 0} entities`;
    listEntity.innerHTML = (data.entity || []).map(ent => `
      <div class="memory-item">
        <strong>${ent.name}</strong> (${ent.entity_type})<br>
        ${ent.relationships ? ent.relationships.map(r => `➔ <em>${r.relation}</em>: ${r.target}`).join("<br>") : ""}
      </div>
    `).join("");

    // Countermeasures Sync
    if (data.countermeasures) {
      if (data.countermeasures.locked_objects) {
        data.countermeasures.locked_objects.forEach(obj => game.lockedObjects.add(obj));
      }
      if (data.countermeasures.blocked_objects) {
        data.countermeasures.blocked_objects.forEach(obj => game.blockedObjects.add(obj));
      }
      if (data.countermeasures.trapped_objects) {
        data.countermeasures.trapped_objects.forEach(obj => game.trappedObjects.add(obj));
      }
    }

  } catch (err) {
    console.warn("Could not refresh memory state:", err);
  }
}

// ----------------- Night Lifecycle -----------------

async function triggerNightEnd(won, narrativeDetail) {
  game.isRunning = false;
  game.nightLog.watchmanWon = !won;
  game.nightLog.playerEscaped = won;

  const payload = {
    night_number: game.nightNumber,
    watchman_won: !won,
    player_escaped: won,
    entry_used: game.nightLog.entryUsed,
    exit_used: game.nightLog.exitUsed,
    hiding_spots_used: Array.from(game.nightLog.hidingSpotsUsed),
    stones_thrown_at: game.nightLog.stonesThrownAt,
    lights_cut_count: game.nightLog.lightsCutCount,
    mangoes_stolen: game.player.holdingMangoes,
    chronological_log: [narrativeDetail],
    memory_ids_used: []
  };

  // Show Dawn Modal
  dawnModal.classList.remove("hidden");
  dawnOutcomeBanner.className = won ? "dawn-outcome win" : "dawn-outcome caught";
  dawnOutcomeBanner.textContent = won ? "🎉 YOU ESCAPED WITH THE MANGOES!" : "👴🏽 MURUGESAN MAMA CAUGHT YOU!";
  dawnNarrativeBox.textContent = "Dawn Reflection: Murugesan Mama is writing insights into the Strata 4-Pillar cognitive memory engine...";

  try {
    const res = await fetch("/api/night/end", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (res.ok) {
      const data = await res.json();
      const reflection = data.reflection;
      dawnNarrativeBox.textContent = reflection.narrative;

      // Extract countermeasures
      if (reflection.countermeasures) {
        if (reflection.countermeasures.locked_objects) {
          reflection.countermeasures.locked_objects.forEach(obj => game.lockedObjects.add(obj));
        }
        if (reflection.countermeasures.blocked_objects) {
          reflection.countermeasures.blocked_objects.forEach(obj => game.blockedObjects.add(obj));
        }
        if (reflection.countermeasures.trapped_objects) {
          reflection.countermeasures.trapped_objects.forEach(obj => game.trappedObjects.add(obj));
        }
      }

      let patchHtml = "";
      if (reflection.active_procedure) {
        patchHtml += `Patrol Plan upgraded to <strong>v${reflection.active_procedure.version}</strong>.<br><em>Counter-tactics:</em> ${reflection.active_procedure.steps.join(" ➔ ")}`;
      }
      const lockedList = Array.from(game.lockedObjects);
      const blockedList = Array.from(game.blockedObjects);
      const trappedList = Array.from(game.trappedObjects);
      if (lockedList.length > 0) patchHtml += `<br><span style="color:#f87171">🔒 <strong>Padlocked:</strong> ${lockedList.join(", ")}</span>`;
      if (blockedList.length > 0) patchHtml += `<br><span style="color:#4ade80">🌿 <strong>Reinforced Thorns:</strong> ${blockedList.join(", ")}</span>`;
      if (trappedList.length > 0) patchHtml += `<br><span style="color:#fbbf24">🥫 <strong>Acoustic Traps:</strong> ${trappedList.join(", ")}</span>`;
      dawnPatchDetails.innerHTML = patchHtml;

      refreshMemoryState();

      // Auto-advance nights during AI simulation
      if (game.isAiMode && game.autoNextNight) {
        const delay = Math.max(1200, 3200 / game.simSpeed);
        setTimeout(() => {
          if (!dawnModal.classList.contains("hidden")) {
            startNextNightBtn.click();
          }
        }, delay);
      }
    }
  } catch (err) {
    console.error("Dawn consolidation failed:", err);
  }
}

function startNextNight() {
  game.nightNumber++;
  restartNight();
}

function restartNight() {
  game.timer = 0.0;
  game.spawnGraceTimer = 4.0; // 4 seconds of stealth grace on entry
  game.hasTriggeredEntryCreak = false;
  game.isRunning = true;
  game.lightsOn = true;
  game.mangoesOnTree = 3;
  game.stonesLeft = 3;

  // Adaptive Entry Point based on locks!
  if (game.lockedObjects.has("main_gate")) {
    game.player.x = 1 * TILE_SIZE + 25;
    game.player.y = 9 * TILE_SIZE + 25; // Slipped in via Drain Pipe
    game.nightLog.entryUsed = "drain_pipe";
    alertToast("🔒 மெயின் கேட் பூட்டப்பட்டதால் மதகு குழாய் வழியே நுழைந்தாய்! (Infiltrated via Drain Pipe)", 4.5);
  } else {
    game.player.x = 8 * TILE_SIZE + 25;
    game.player.y = 0 * TILE_SIZE + 35; // Main Gate
    game.nightLog.entryUsed = "main_gate";
  }

  game.player.holdingMangoes = 0;
  game.player.isHidden = false;
  game.player.hiddenIn = null;
  game.player.channeling = false;

  // Reset Velu AI State
  game.velu.state = "INFILTRATE";
  game.velu.targetPos = { x: 8 * TILE_SIZE + 25, y: 3 * TILE_SIZE + 25 };
  game.velu.stoneCooldown = 0.0;
  game.velu.stuckTimer = 0.0;
  game.velu.isSprinting = false;
  game.velu.dialogueTa = game.lockedObjects.has("main_gate")
    ? "மெயின் கேட் பூட்டியிருக்கு... மதகு வழியா நைசா மாமரத்தை நெருங்குவோம்!"
    : "மெயின் கேட் வழியா உள்ளே போவோம்... மாமா எங்க நிக்கிறாருன்னு பாப்போம்!";
  game.velu.dialogueEn = "Starting night infiltration...";
  game.velu.reasoning = "Night reset. Assessing entrance vector and guard rounds.";
  updateVeluUI();

  // Watchman starts deep in the grove facing away
  game.watchman.x = 8 * TILE_SIZE + 25;
  game.watchman.y = 8 * TILE_SIZE + 25;
  game.watchman.angle = Math.PI / 2;
  game.watchman.isChasing = false;
  game.watchman.chaseLostTimer = 0.0;
  game.watchman.scanTimer = 0.0;
  game.watchman.currentAction = "PATROL";
  game.watchman.targetTile = [11, 9];
  game.watchman.speechText = `ராத்திரி #${game.nightNumber} ஆரம்பம்! மாம்பழத்தை தொட விடமாட்டேன்!`;
  game.watchman.speechEn = `Night #${game.nightNumber} begins! Won't let anyone touch the mangoes!`;

  game.flyingStones = [];
  game.soundRipples = [];
  game.nightLog = {
    entryUsed: game.nightLog.entryUsed,
    exitUsed: null,
    hidingSpotsUsed: new Set(),
    stonesThrownAt: [],
    lightsCutCount: 0,
    mangoesStolen: 0,
    watchmanWon: false,
    playerEscaped: false
  };

  dawnModal.classList.add("hidden");
  refreshMemoryState();
}

// ----------------- Interaction Prompts & HUD -----------------

function checkInteractions() {
  const p = game.player;
  let promptText = null;

  // Near pumpset switch
  if (Math.hypot(p.x - (2 * TILE_SIZE + 25), p.y - (3 * TILE_SIZE + 25)) < 40) {
    promptText = game.lightsOn ? "Press [E] to Turn Lights OFF" : "Press [E] to Turn Lights ON";
  }
  // Near mango tree
  else if (Math.hypot(p.x - (8 * TILE_SIZE + 25), p.y - (6 * TILE_SIZE + 25)) < 55) {
    if (game.mangoesOnTree > 0 && p.holdingMangoes < 2) {
      promptText = "Hold [E] to Pluck Banganapalli Mango";
    }
  }
  // Near haystack
  else if (Math.hypot(p.x - (3 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 45) {
    promptText = p.isHidden ? "Press [E] to Exit Haystack" : "Press [E] to Hide in Haystack";
  }
  // Near mud well
  else if (Math.hypot(p.x - (11 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 45) {
    promptText = p.isHidden ? "Press [E] to Leave Well Parapet" : "Press [E] to Hide Behind Well";
  }
  // Near main gate
  else if (Math.hypot(p.x - (8 * TILE_SIZE + 25), p.y - (0 * TILE_SIZE + 25)) < 50) {
    if (game.lockedObjects.has("main_gate")) {
      promptText = "🔒 Main Gate is Padlocked! Escape via Fence or Drain Pipe!";
    } else {
      promptText = p.holdingMangoes >= 2 ? "Press [E] to ESCAPE Grove!" : "Need 2 Mangoes to Escape!";
    }
  }
  // Near back fence
  else if (Math.hypot(p.x - (15 * TILE_SIZE + 25), p.y - (8 * TILE_SIZE + 25)) < 50) {
    if (game.blockedObjects.has("back_fence")) {
      promptText = p.holdingMangoes >= 2 ? "Hold [E] to Cut Brambles (4s)!" : "Need 2 Mangoes to Escape!";
    } else {
      promptText = p.holdingMangoes >= 2 ? "Hold [E] to Squeeze Through Fence (2s)!" : "Need 2 Mangoes to Escape!";
    }
  }
  // Near drain pipe
  else if (Math.hypot(p.x - (0 * TILE_SIZE + 25), p.y - (9 * TILE_SIZE + 25)) < 50) {
    if (game.trappedObjects.has("drain_pipe")) {
      promptText = p.holdingMangoes >= 2 ? "Press [E] to Crawl (⚠️ Tripwire Attached)!" : "Need 2 Mangoes to Escape!";
    } else {
      promptText = p.holdingMangoes >= 2 ? "Press [E] to Crawl Through Drain Pipe!" : "Need 2 Mangoes to Escape!";
    }
  }

  if (promptText) {
    interactPrompt.textContent = promptText;
    interactPrompt.classList.remove("hidden");
  } else {
    interactPrompt.classList.add("hidden");
  }
}

function updateHUD() {
  hudNight.textContent = `#${game.nightNumber}`;
  const mins = Math.floor(game.timer / 60);
  const secs = Math.floor(game.timer % 60);
  hudTimer.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  hudMangoes.textContent = `${game.player.holdingMangoes} / 2`;
  hudStones.textContent = "🪨 ".repeat(game.stonesLeft) || "None";

  if (game.lightsOn) {
    hudLights.textContent = "ON";
    hudLights.className = "hud-value lights-on";
  } else {
    hudLights.textContent = "OFF";
    hudLights.className = "hud-value lights-off";
  }
}

// ----------------- Rendering -----------------

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 1. Draw Grove Soil & Grass Tilemap
  drawGroveTilemap();

  // 2. Draw Interactive Objects
  drawInteractiveObjects();

  // 3. Draw Player
  drawPlayer();

  // 4. Draw Murugesan Mama
  drawWatchman();

  // 5. Draw Darkness & Flashlight Cone (Raycasting & Cutout)
  drawLightingAndFlashlight();

  // 6. Draw Flying Stones & Expanding Sound Ripples
  drawFlyingStones();
  drawSoundRipples();

  // 7. Draw Mama's Floating Comic Speech Bubble
  drawSpeechBubble();

  // 8. Draw Stealth Grace Banner
  if (game.spawnGraceTimer > 0) {
    ctx.save();
    ctx.fillStyle = "rgba(16, 185, 129, 0.92)";
    ctx.font = "bold 14px 'Noto Sans Tamil', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`🌿 பதுங்கி உள்ளே வா! (Stealth Entry: ${Math.ceil(game.spawnGraceTimer)}s Grace)`, canvas.width / 2, 32);
    ctx.restore();
  }

  // 9. Draw Toast Alerts
  if (toastTimer > 0 && toastMessage) {
    ctx.save();
    ctx.fillStyle = "rgba(220, 38, 38, 0.94)";
    ctx.fillRect(100, 48, 600, 36);
    ctx.strokeStyle = "#fca5a5";
    ctx.lineWidth = 2;
    ctx.strokeRect(100, 48, 600, 36);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 13px 'Noto Sans Tamil', sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(toastMessage, 400, 71);
    ctx.restore();
  }

  // 10. Draw AI Simulation Header Banner
  if (game.isAiMode) {
    ctx.save();
    ctx.fillStyle = "rgba(124, 58, 237, 0.92)";
    ctx.fillRect(160, 6, 480, 24);
    ctx.strokeStyle = "#a78bfa";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(160, 6, 480, 24);
    ctx.fillStyle = "#ffffff";
    ctx.font = "bold 11px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText(`🤖 AI SIMULATION: VELU (AI KID) vs MURUGESAN MAMA (AI GUARD) [${game.simSpeed}x]`, 400, 22);
    ctx.restore();
  }
}

function drawFlyingStones() {
  for (const s of game.flyingStones) {
    ctx.save();
    ctx.fillStyle = "#cbd5e1";
    ctx.beginPath();
    ctx.arc(s.currX, s.currY, 4.5, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#38bdf8";
    ctx.lineWidth = 1.5;
    ctx.stroke();
    ctx.restore();
  }
}

function drawGroveTilemap() {
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      const x = c * TILE_SIZE;
      const y = r * TILE_SIZE;

      // Walls
      if (WALL_TILES.has(`${c},${r}`)) {
        ctx.fillStyle = "#1e293b";
        ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 1;
        ctx.strokeRect(x, y, TILE_SIZE, TILE_SIZE);
        // Brick hatch
        ctx.fillStyle = "#0f172a";
        ctx.fillRect(x + 4, y + 4, TILE_SIZE - 8, TILE_SIZE - 8);
        continue;
      }

      // Footpath connecting main gate -> central tree -> back fence
      const isPath = (c === 8 && r <= 7) || (r === 6 && c >= 4 && c <= 12) || (c === 15 && r === 8);
      if (isPath) {
        ctx.fillStyle = "#1f1b13"; // Sandy dirt path
        ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
      } else {
        // Lush village grass
        ctx.fillStyle = (r + c) % 2 === 0 ? "#071c0e" : "#092211";
        ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
      }
    }
  }
}

function drawInteractiveObjects() {
  // Main Gate (8, 0)
  const isGateLocked = game.lockedObjects.has("main_gate");
  ctx.fillStyle = isGateLocked ? "#7f1d1d" : "#475569";
  ctx.fillRect(8 * TILE_SIZE + 4, 2, TILE_SIZE - 8, 14);
  ctx.strokeStyle = isGateLocked ? "#ef4444" : "#cbd5e1";
  ctx.lineWidth = 2;
  ctx.strokeRect(8 * TILE_SIZE + 4, 2, TILE_SIZE - 8, 14);
  ctx.fillStyle = isGateLocked ? "#fca5a5" : "#94a3b8";
  ctx.font = "bold 9px sans-serif";
  ctx.fillText(isGateLocked ? "🔒 LOCKED" : "GATE", 8 * TILE_SIZE + (isGateLocked ? 4 : 12), 12);

  // Back Thorn Fence (15, 8)
  const isFenceBlocked = game.blockedObjects.has("back_fence");
  ctx.strokeStyle = isFenceBlocked ? "#15803d" : "#b45309";
  ctx.lineWidth = isFenceBlocked ? 6 : 3;
  ctx.beginPath();
  ctx.moveTo(15 * TILE_SIZE + 40, 8 * TILE_SIZE + 5);
  ctx.lineTo(15 * TILE_SIZE + 40, 8 * TILE_SIZE + 45);
  ctx.stroke();
  ctx.fillStyle = isFenceBlocked ? "#86efac" : "#fbbf24";
  ctx.font = "bold 9px sans-serif";
  ctx.fillText(isFenceBlocked ? "🌿 BRAMBLES" : "FENCE", 15 * TILE_SIZE - 14, 8 * TILE_SIZE + 28);

  // Drain Pipe (0, 9)
  const isPipeTrapped = game.trappedObjects.has("drain_pipe");
  ctx.fillStyle = isPipeTrapped ? "#831843" : "#1e293b";
  ctx.beginPath();
  ctx.arc(0 * TILE_SIZE + 15, 9 * TILE_SIZE + 25, 14, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = isPipeTrapped ? "#f43f5e" : "#38bdf8";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = isPipeTrapped ? "#f43f5e" : "#38bdf8";
  ctx.font = "bold 9px sans-serif";
  ctx.fillText(isPipeTrapped ? "🥫 TRIPWIRE" : "PIPE", 0 * TILE_SIZE + 2, 9 * TILE_SIZE + 48);

  // Pumpset Shed & Switch (2, 3)
  ctx.fillStyle = "#334155";
  ctx.fillRect(2 * TILE_SIZE + 10, 3 * TILE_SIZE + 10, 30, 30);
  ctx.fillStyle = game.lightsOn ? "#4ade80" : "#ef4444";
  ctx.beginPath();
  ctx.arc(2 * TILE_SIZE + 25, 3 * TILE_SIZE + 25, 6, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#e2e8f0";
  ctx.font = "9px sans-serif";
  ctx.fillText("SWITCH", 2 * TILE_SIZE + 6, 3 * TILE_SIZE + 48);

  // Mud Well (11, 9)
  const wellX = 11 * TILE_SIZE + 25;
  const wellY = 9 * TILE_SIZE + 25;
  ctx.fillStyle = "#0284c7";
  ctx.beginPath();
  ctx.arc(wellX, wellY, 18, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#64748b";
  ctx.lineWidth = 4;
  ctx.stroke();
  ctx.fillStyle = "#93c5fd";
  ctx.fillText("WELL", wellX - 12, wellY + 30);

  // Haystack (3, 9)
  const hayX = 3 * TILE_SIZE + 25;
  const hayY = 9 * TILE_SIZE + 25;
  ctx.fillStyle = "#ca8a04";
  ctx.beginPath();
  ctx.arc(hayX, hayY, 20, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#fef08a";
  ctx.lineWidth = 2;
  ctx.stroke();
  ctx.fillStyle = "#fef08a";
  ctx.fillText("HAYSTACK", hayX - 22, hayY + 32);

  // Central Mango Tree (8, 6)
  const treeX = 8 * TILE_SIZE + 25;
  const treeY = 6 * TILE_SIZE + 25;
  // Foliage
  ctx.fillStyle = "#064e3b";
  ctx.beginPath();
  ctx.arc(treeX, treeY, 46, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#047857";
  ctx.beginPath();
  ctx.arc(treeX - 10, treeY - 8, 30, 0, Math.PI * 2);
  ctx.fill();
  // Hanging Banganapalli Mangoes
  for (let i = 0; i < game.mangoesOnTree; i++) {
    const angle = (i * (Math.PI * 2) / 3) + 0.5;
    const mx = treeX + Math.cos(angle) * 24;
    const my = treeY + Math.sin(angle) * 24;
    ctx.fillStyle = "#fbbf24";
    ctx.beginPath();
    ctx.arc(mx, my, 7, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "#d97706";
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
}

function drawPlayer() {
  const p = game.player;
  const v = game.velu;
  if (p.isHidden) return; // Completely hidden in haystack or well!

  // Dotted waypoint trajectory line in AI Mode
  if (game.isAiMode && v.targetPos) {
    ctx.save();
    ctx.strokeStyle = "rgba(56, 189, 248, 0.4)";
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(p.x, p.y);
    ctx.lineTo(v.targetPos.x, v.targetPos.y);
    ctx.stroke();
    // Destination indicator ring
    ctx.strokeStyle = "#38bdf8";
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.arc(v.targetPos.x, v.targetPos.y, 5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  ctx.save();
  ctx.translate(p.x, p.y);

  // Village kid body (blue shirt, purple in AI mode)
  ctx.fillStyle = game.isAiMode ? "#818cf8" : "#38bdf8";
  ctx.beginPath();
  ctx.arc(0, 0, p.radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#fff";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Head
  ctx.fillStyle = "#92400e";
  ctx.beginPath();
  ctx.arc(0, -2, 6, 0, Math.PI * 2);
  ctx.fill();

  // Stolen mango bag / hands
  if (p.holdingMangoes > 0) {
    ctx.fillStyle = "#fbbf24";
    ctx.beginPath();
    ctx.arc(8, 6, 5, 0, Math.PI * 2);
    ctx.fill();
  }

  // Draw [🤖 VELU] tag if in simulation mode
  if (game.isAiMode) {
    ctx.fillStyle = "#c084fc";
    ctx.font = "bold 9px sans-serif";
    ctx.textAlign = "center";
    ctx.fillText("🤖 VELU", 0, -18);
  }

  ctx.restore();
}

function drawWatchman() {
  const w = game.watchman;
  ctx.save();
  ctx.translate(w.x, w.y);
  ctx.rotate(w.angle);

  // Veteran Watchman (Brown skin, white veshti/dhoti)
  ctx.fillStyle = "#f8fafc"; // White veshti
  ctx.beginPath();
  ctx.arc(-4, 0, w.radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "#e2e8f0";
  ctx.stroke();

  // Head / Hair (Grey veteran elder)
  ctx.fillStyle = "#78350f";
  ctx.beginPath();
  ctx.arc(2, 0, 8, 0, Math.PI * 2);
  ctx.fill();

  // Flashlight in right hand
  ctx.fillStyle = "#334155";
  ctx.fillRect(8, 6, 12, 5);

  // Bamboo stick in left hand
  ctx.strokeStyle = "#d97706";
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.moveTo(-6, -14);
  ctx.lineTo(w.stickSwinging ? 14 : 6, -14);
  ctx.stroke();

  ctx.restore();
}

function drawLightingAndFlashlight() {
  const w = game.watchman;
  const p = game.player;

  // Flashlight Cone parameters
  const visionDistance = game.lightsOn ? 6.0 * TILE_SIZE : 4.5 * TILE_SIZE;
  const halfFov = (75 * Math.PI) / 360;

  // Create temporary darkness overlay
  const darknessAlpha = game.lightsOn ? 0.35 : 0.88;

  // Render Darkness with Cutout
  ctx.save();
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = canvas.width;
  maskCanvas.height = canvas.height;
  const mctx = maskCanvas.getContext("2d");

  // Fill dark night
  mctx.fillStyle = `rgba(5, 10, 22, ${darknessAlpha})`;
  mctx.fillRect(0, 0, canvas.width, canvas.height);

  // Punch out Watchman's Flashlight Cone
  mctx.globalCompositeOperation = "destination-out";
  mctx.beginPath();
  mctx.moveTo(w.x, w.y);
  mctx.arc(w.x, w.y, visionDistance, w.angle - halfFov, w.angle + halfFov);
  mctx.closePath();
  mctx.fill();

  // Player personal visibility halo
  mctx.beginPath();
  mctx.arc(p.x, p.y, 45, 0, Math.PI * 2);
  mctx.fill();

  // Central Mango Tree subtle glow if lights ON
  if (game.lightsOn) {
    mctx.beginPath();
    mctx.arc(8 * TILE_SIZE + 25, 6 * TILE_SIZE + 25, 80, 0, Math.PI * 2);
    mctx.fill();
  }

  // Draw mask back onto main canvas
  ctx.drawImage(maskCanvas, 0, 0);
  ctx.restore();

  // Flashlight beam yellow tint
  ctx.save();
  ctx.beginPath();
  ctx.moveTo(w.x, w.y);
  ctx.arc(w.x, w.y, visionDistance, w.angle - halfFov, w.angle + halfFov);
  ctx.closePath();
  const grad = ctx.createRadialGradient(w.x, w.y, 10, w.x, w.y, visionDistance);
  grad.addColorStop(0, "rgba(254, 240, 138, 0.35)");
  grad.addColorStop(1, "rgba(254, 240, 138, 0.0)");
  ctx.fillStyle = grad;
  ctx.fill();
  ctx.restore();
}

function drawSoundRipples() {
  for (const r of game.soundRipples) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(r.x, r.y, r.currentRadius, 0, Math.PI * 2);
    ctx.strokeStyle = r.color.replace(/[\d\.]+\)$/g, `${r.alpha})`);
    ctx.lineWidth = 2.5;
    ctx.stroke();
    ctx.restore();
  }
}

function drawSpeechBubble() {
  const w = game.watchman;
  if (!w.speechText || w.speechTimer <= 0) return;

  const bx = Math.min(680, Math.max(120, w.x));
  const by = Math.max(50, w.y - 45);

  ctx.save();
  ctx.font = "bold 13px 'Noto Sans Tamil', sans-serif";
  const textWidth = ctx.measureText(w.speechText).width;
  const padding = 10;
  const bubbleW = textWidth + padding * 2;
  const bubbleH = 28;

  // Bubble Box
  ctx.fillStyle = "rgba(15, 23, 42, 0.95)";
  ctx.strokeStyle = "#fbbf24";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.roundRect(bx - bubbleW / 2, by - bubbleH, bubbleW, bubbleH, 6);
  ctx.fill();
  ctx.stroke();

  // Small pointer triangle
  ctx.beginPath();
  ctx.moveTo(bx - 6, by);
  ctx.lineTo(bx + 6, by);
  ctx.lineTo(bx, by + 8);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Text
  ctx.fillStyle = "#fef08a";
  ctx.textAlign = "center";
  ctx.fillText(w.speechText, bx, by - 10);
  ctx.restore();
}

// Initial fetch on boot
refreshMemoryState();
