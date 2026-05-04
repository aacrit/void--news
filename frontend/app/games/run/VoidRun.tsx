"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";

/* ==========================================================================
   VoidRun — void --run: Infinite Side-Scrolling Runner

   Canvas-based endless runner. You are a glowing amber dash running through
   a corridor made of text and static. Jump over obstacles. Survive.

   Tagline: "run until the signal breaks"

   The corridor is language. The obstacles are noise, static, corruption.
   You are the signal trying to survive.

   Controls: Space / ArrowUp / Tap to jump. Double-jump available once
   per flight.

   States: idle -> running -> dead
   ========================================================================== */

/* ---- Constants ---- */
const CANVAS_W = 800;
const CANVAS_H = 300;

const GRAVITY = 0.45;
const JUMP_FORCE = -17;
const DOUBLE_JUMP_FORCE = -14;

const PLAYER_X = 120;
const PLAYER_Y_GROUND = 230;
const PLAYER_H = 3;
const PLAYER_W = 28;

const GROUND_Y = 235;

const TRAIL_LENGTH = 8;

/* ---- Tilt / Lean color system ----
   Cinematographic motivation: the player dash IS a signal, and signals lean.
   Vertical velocity maps to political lean — rising = left (cool blue),
   falling = right (warm red), neutral = void cream. The tilt angle uses
   spring-based smoothing (Lubezki Steadicam lag) so the visual trails
   the physics by ~3-4 frames, creating inertial weight. Color shifts
   cross-dissolve like Bradford Young's temperature grades in "Arrival."
*/
const TILT_MAX_DEG = 28;
const TILT_VELOCITY_SCALE = 2.5;
const TILT_SMOOTHING = 0.12; // Exponential smoothing factor — lower = more lag

// Lean palette: left-blue / neutral-cream / right-red
const LEAN_LEFT  = { r: 100, g: 140, b: 220, a: 0.9 };
const LEAN_NEUTRAL = { r: 245, g: 240, b: 232, a: 0.95 };
const LEAN_RIGHT = { r: 220, g: 100, b: 80,  a: 0.9 };

// Shadow palette mirrors lean (key light temperature shift)
const SHADOW_LEFT    = "rgba(80, 120, 200, 0.7)";
const SHADOW_NEUTRAL = "#c9a84c";
const SHADOW_RIGHT   = "rgba(200, 90, 60, 0.7)";

// Lean label config
const LEAN_LABEL_HOLD_FRAMES = 60;   // ~1s at 60fps
const LEAN_LABEL_FADE_FRAMES = 20;   // ~0.33s fade out

type LeanCategory = "left" | "neutral" | "right";

function clampTilt(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/** Interpolate between two RGBA color objects. t=0 → a, t=1 → b */
function lerpColor(
  a: { r: number; g: number; b: number; a: number },
  b: { r: number; g: number; b: number; a: number },
  t: number
): { r: number; g: number; b: number; a: number } {
  const tc = Math.max(0, Math.min(1, t));
  return {
    r: a.r + (b.r - a.r) * tc,
    g: a.g + (b.g - a.g) * tc,
    b: a.b + (b.b - a.b) * tc,
    a: a.a + (b.a - a.a) * tc,
  };
}

/** Convert RGBA object to CSS rgba() string */
function rgbaStr(c: { r: number; g: number; b: number; a: number }): string {
  return `rgba(${Math.round(c.r)}, ${Math.round(c.g)}, ${Math.round(c.b)}, ${c.a.toFixed(3)})`;
}

/** Get lean color based on normalized tilt (-1 = full left, 0 = neutral, +1 = full right) */
function getLeanColor(normalizedTilt: number): { r: number; g: number; b: number; a: number } {
  if (normalizedTilt < 0) {
    // Left lean: interpolate left → neutral
    return lerpColor(LEAN_LEFT, LEAN_NEUTRAL, 1 + normalizedTilt);
  } else {
    // Right lean: interpolate neutral → right
    return lerpColor(LEAN_NEUTRAL, LEAN_RIGHT, normalizedTilt);
  }
}

/** Get shadow color string based on normalized tilt */
function getLeanShadow(normalizedTilt: number): string {
  if (normalizedTilt < -0.3) return SHADOW_LEFT;
  if (normalizedTilt > 0.3) return SHADOW_RIGHT;
  return SHADOW_NEUTRAL;
}

/** Determine lean category from normalized tilt */
function getLeanCategory(normalizedTilt: number): LeanCategory {
  if (normalizedTilt < -0.15) return "left";
  if (normalizedTilt > 0.15) return "right";
  return "neutral";
}

/* ---- Difficulty configs ---- */
const DIFFICULTY_CONFIGS = {
  clear:  { initialSpeed: 3,   speedIncrement: 0.0004, minGap: 340, maxGap: 580, label: "CLEAR",  hint: "slow start · wide gaps" },
  signal: { initialSpeed: 5,   speedIncrement: 0.0008, minGap: 220, maxGap: 420, label: "SIGNAL", hint: "default" },
  static: { initialSpeed: 7.5, speedIncrement: 0.0016, minGap: 155, maxGap: 300, label: "STATIC", hint: "fast · tight gaps" },
} as const;

type Difficulty = keyof typeof DIFFICULTY_CONFIGS;

/* ---- Obstacle types ---- */
const OBSTACLE_TYPES = [
  { chars: ["\u2588", "\u2593", "\u2592", "\u2591"], color: "rgba(200,200,200,0.6)", h: 60 },
  { chars: ["|", "|", "|", "|"], color: "rgba(201,168,76,0.4)", h: 80 },
  { chars: ["N", "O", "I", "S", "E"], color: "rgba(180,180,180,0.3)", h: 50 },
  { chars: ["S", "T", "A", "T", "I", "C"], color: "rgba(150,150,200,0.3)", h: 70 },
  { chars: ["\u2591", "\u2592", "\u2593", "\u2588", "\u2593", "\u2592"], color: "rgba(200,200,200,0.5)", h: 90 },
  { chars: ["0", "1", "0", "1", "1", "0", "1"], color: "rgba(201,168,76,0.2)", h: 75 },
  { chars: ["\u2502", "\u2502", "\u2502", "\u2502", "\u2502"], color: "rgba(180,160,120,0.35)", h: 65 },
];

interface Obstacle {
  x: number;
  type: (typeof OBSTACLE_TYPES)[number];
  width: number;
}

type GameState = "idle" | "running" | "dead";

/* ---- Static noise characters for death screen ---- */
const NOISE_CHARS = "\u2588\u2593\u2592\u2591|/-\\:;!?#@$%&*()0101";

/* ---- Drawing helpers ---- */

function drawPlayer(
  ctx: CanvasRenderingContext2D,
  y: number,
  trail: number[],
  smoothedTilt: number
) {
  /* Tilt angle in radians — smoothedTilt is already in degrees, spring-smoothed.
     Negative tilt = rising = lean left (nose down).
     Positive tilt = falling = lean right (nose up). */
  const tiltRad = (smoothedTilt * Math.PI) / 180;

  /* Normalized tilt for color lookup: -1 (full left) to +1 (full right) */
  const normalizedTilt = clampTilt(smoothedTilt / TILT_MAX_DEG, -1, 1);
  const leanColor = getLeanColor(normalizedTilt);
  const shadowColor = getLeanShadow(normalizedTilt);

  /* Trail color: lean color at reduced opacity — inherits the tilt hue */
  const trailColor = { ...leanColor, a: leanColor.a * 0.35 };

  ctx.shadowBlur = 12;
  ctx.shadowColor = shadowColor;

  // Trail — each segment inherits tilt color, progressively fading
  for (let i = 0; i < trail.length; i++) {
    const t = i / trail.length;
    ctx.globalAlpha = t * 0.3;
    ctx.fillStyle = rgbaStr({ ...trailColor, a: trailColor.a * t });
    ctx.fillRect(
      PLAYER_X - (trail.length - i) * 3,
      trail[i],
      PLAYER_W * t,
      PLAYER_H
    );
  }

  // Main dash — rotated around its center point (Steadicam pivot)
  ctx.globalAlpha = 1;
  const cx = PLAYER_X + PLAYER_W / 2;
  const cy = y + PLAYER_H / 2;

  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(tiltRad);
  ctx.fillStyle = rgbaStr(leanColor);
  ctx.fillRect(-PLAYER_W / 2, -PLAYER_H / 2, PLAYER_W, PLAYER_H);
  ctx.restore();

  ctx.shadowBlur = 0;
}

function drawBackground(
  ctx: CanvasRenderingContext2D,
  bgOffset: number
) {
  // Dark canvas
  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

  // Parallax speed lines
  for (let layer = 0; layer < 3; layer++) {
    const speed = (layer + 1) * 0.4;
    const opacity = (layer + 1) * 0.04;
    ctx.strokeStyle = `rgba(201, 168, 76, ${opacity})`;
    ctx.lineWidth = 0.5;
    for (let i = 0; i < 8; i++) {
      const y = (CANVAS_H / 8) * i + 10;
      const x = ((-bgOffset * speed) % CANVAS_W + CANVAS_W) % CANVAS_W;
      ctx.beginPath();
      ctx.moveTo(x, y);
      ctx.lineTo(x + CANVAS_W * 0.3, y);
      ctx.stroke();
      // Wrap-around segment
      if (x + CANVAS_W * 0.3 > CANVAS_W) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo((x + CANVAS_W * 0.3) - CANVAS_W, y);
        ctx.stroke();
      }
    }
  }
}

function drawGround(ctx: CanvasRenderingContext2D) {
  ctx.strokeStyle = "rgba(201, 168, 76, 0.25)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 8]);
  ctx.beginPath();
  ctx.moveTo(0, GROUND_Y);
  ctx.lineTo(CANVAS_W, GROUND_Y);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawObstacle(
  ctx: CanvasRenderingContext2D,
  obs: Obstacle
) {
  const charH = obs.type.h / obs.type.chars.length;
  ctx.font = `${Math.min(charH, 14)}px "IBM Plex Mono", monospace`;
  ctx.fillStyle = obs.type.color;
  ctx.textAlign = "center";

  for (let i = 0; i < obs.type.chars.length; i++) {
    const cy = GROUND_Y - obs.type.h + charH * i + charH * 0.8;
    ctx.fillText(obs.type.chars[i], obs.x + obs.width / 2, cy);
  }
}

function drawScore(
  ctx: CanvasRenderingContext2D,
  score: number,
  best: number,
  speed: number
) {
  ctx.font = '12px "IBM Plex Mono", monospace';

  // Score top-right
  ctx.textAlign = "right";
  ctx.fillStyle = "rgba(201, 168, 76, 0.7)";
  ctx.fillText(`SIGNAL ${String(score).padStart(6, "0")}`, CANVAS_W - 20, 30);

  // Best score below
  if (best > 0) {
    ctx.fillStyle = "rgba(201, 168, 76, 0.3)";
    ctx.fillText(`BEST   ${String(best).padStart(6, "0")}`, CANVAS_W - 20, 48);
  }

  // Speed top-left
  ctx.textAlign = "left";
  ctx.fillStyle = "rgba(245, 240, 232, 0.2)";
  ctx.fillText(`${(speed * 20).toFixed(0)}m/s`, 20, 30);
}

/** Draw the lean indicator label — J-cut reveal: text arrives before tilt settles.
 *  Uses a horizontal clip-path wipe from the left edge, holds, then fades out.
 *  Only re-triggers when the lean category changes. */
function drawLeanLabel(
  ctx: CanvasRenderingContext2D,
  category: LeanCategory,
  framesVisible: number
) {
  if (framesVisible <= 0) return;

  // Determine label text and color
  let text: string;
  let color: { r: number; g: number; b: number; a: number };
  switch (category) {
    case "left":
      text = "\u2190 LEFT LEAN";
      color = { ...LEAN_LEFT, a: 0.7 };
      break;
    case "right":
      text = "RIGHT LEAN \u2192";
      color = { ...LEAN_RIGHT, a: 0.7 };
      break;
    default:
      text = "\u25C7 SIGNAL";
      color = { r: 201, g: 168, b: 76, a: 0.5 };
      break;
  }

  // Phase 1: wipe-in (first 10 frames — J-cut, fast reveal)
  // Phase 2: hold (LEAN_LABEL_HOLD_FRAMES)
  // Phase 3: fade out (LEAN_LABEL_FADE_FRAMES)
  const wipeFrames = 10;
  const totalFrames = wipeFrames + LEAN_LABEL_HOLD_FRAMES + LEAN_LABEL_FADE_FRAMES;
  const elapsed = totalFrames - framesVisible;

  let alpha: number;
  let clipFraction: number; // 0 = fully clipped, 1 = fully revealed

  if (elapsed < wipeFrames) {
    // Wipe in — cinematic horizontal reveal
    clipFraction = elapsed / wipeFrames;
    alpha = 1;
  } else if (elapsed < wipeFrames + LEAN_LABEL_HOLD_FRAMES) {
    // Hold
    clipFraction = 1;
    alpha = 1;
  } else {
    // Fade out
    clipFraction = 1;
    const fadeProgress = (elapsed - wipeFrames - LEAN_LABEL_HOLD_FRAMES) / LEAN_LABEL_FADE_FRAMES;
    alpha = 1 - fadeProgress;
  }

  ctx.save();
  ctx.font = '9px "IBM Plex Mono", monospace';
  ctx.textAlign = "left";

  // Measure text width for clip
  const textWidth = ctx.measureText(text).width;
  const labelX = 20;
  const labelY = 48;

  // Clip-path wipe: only reveal a fraction of the text from the left
  ctx.beginPath();
  ctx.rect(labelX - 2, labelY - 12, (textWidth + 4) * clipFraction, 16);
  ctx.clip();

  ctx.globalAlpha = Math.max(0, alpha);
  ctx.fillStyle = rgbaStr({ ...color, a: color.a * alpha });
  ctx.fillText(text, labelX, labelY);

  ctx.restore();
}

function drawIdleScreen(
  ctx: CanvasRenderingContext2D,
  frame: number,
  isMobile: boolean
) {
  // Flickering text
  const flicker = Math.sin(frame * 0.06) > -0.3;
  if (flicker) {
    ctx.font = '14px "IBM Plex Mono", monospace';
    ctx.textAlign = "center";
    ctx.fillStyle = `rgba(245, 240, 232, ${0.4 + Math.sin(frame * 0.03) * 0.15})`;
    ctx.fillText(
      isMobile ? "TAP TO BEGIN" : "PRESS SPACE TO BEGIN",
      CANVAS_W / 2,
      CANVAS_H / 2 + 40
    );
  }
}

function drawDeathStatic(
  ctx: CanvasRenderingContext2D,
  frame: number
) {
  ctx.font = '10px "IBM Plex Mono", monospace';
  for (let x = 0; x < CANVAS_W; x += 16) {
    for (let y = 0; y < CANVAS_H; y += 14) {
      const char = NOISE_CHARS[Math.floor(Math.random() * NOISE_CHARS.length)];
      ctx.fillStyle = `rgba(${150 + Math.random() * 60}, ${150 + Math.random() * 40}, ${150 + Math.random() * 40}, ${0.03 + Math.random() * 0.08})`;
      ctx.fillText(char, x, y);
    }
  }
  // Apply dim overlay so static is subtle
  ctx.fillStyle = `rgba(10, 10, 10, ${0.85 + Math.sin(frame * 0.1) * 0.05})`;
  ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
}

/* ---- AABB collision with forgiveness margin ---- */
function checkCollision(
  playerY: number,
  obstacles: Obstacle[]
): boolean {
  const px = PLAYER_X + 4;
  const py = playerY + 1;
  const pw = PLAYER_W - 6;
  const ph = PLAYER_H - 1;

  for (const obs of obstacles) {
    const ox = obs.x;
    const oy = GROUND_Y - obs.type.h;
    const ow = obs.width;
    const oh = obs.type.h;

    if (px < ox + ow && px + pw > ox && py < oy + oh && py + ph > oy) {
      return true;
    }
  }
  return false;
}

/* ---- Main component ---- */

export default function VoidRun() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  // Game state refs (mutable for rAF loop; React state for UI overlay)
  const gameStateRef = useRef<GameState>("idle");
  const [gameState, setGameState] = useState<GameState>("idle");
  const [displayScore, setDisplayScore] = useState(0);
  const [displayBest, setDisplayBest] = useState(0);
  const [isMobile, setIsMobile] = useState(false);

  // Difficulty
  const [difficulty, setDifficulty] = useState<Difficulty>("signal");
  const difficultyRef = useRef<Difficulty>("signal");

  // Mutable game vars
  const playerYRef = useRef(PLAYER_Y_GROUND);
  const velocityYRef = useRef(0);
  const onGroundRef = useRef(true);
  const hasDoubleJumpRef = useRef(true);
  const speedRef = useRef<number>(DIFFICULTY_CONFIGS.signal.initialSpeed);
  const scoreRef = useRef(0);
  const bestRef = useRef(0);
  const bgOffsetRef = useRef(0);
  const frameRef = useRef(0);
  const obstaclesRef = useRef<Obstacle[]>([]);
  const trailRef = useRef<number[]>([]);
  const nextObstacleXRef = useRef(CANVAS_W + 100);
  const deathFrameRef = useRef(0);
  const flickerCountRef = useRef(0);

  // Tilt / lean state — spring-smoothed for Steadicam inertia
  const smoothedTiltRef = useRef(0);           // Current smoothed tilt in degrees
  const leanCategoryRef = useRef<LeanCategory>("neutral");
  const leanLabelTimerRef = useRef(0);         // Countdown frames for label visibility
  const leanLabelCategoryRef = useRef<LeanCategory>("neutral"); // Category being displayed

  // Sync difficulty ref, reload best score, and persist preference when difficulty changes
  const handleDifficultyChange = useCallback((d: Difficulty) => {
    if (gameStateRef.current !== "idle") return; // lock during play
    setDifficulty(d);
    difficultyRef.current = d;
    try {
      localStorage.setItem("void-run-difficulty", d);
      const stored = localStorage.getItem(`void-run-best-${d}`);
      const val = stored ? parseInt(stored, 10) : 0;
      bestRef.current = val;
      setDisplayBest(val);
    } catch {
      bestRef.current = 0;
      setDisplayBest(0);
    }
  }, []);

  // Load saved difficulty preference + best score on mount
  useEffect(() => {
    try {
      const savedDiff = localStorage.getItem("void-run-difficulty") as Difficulty | null;
      const diff: Difficulty = savedDiff && savedDiff in DIFFICULTY_CONFIGS ? savedDiff : "signal";
      setDifficulty(diff);
      difficultyRef.current = diff;
      const stored = localStorage.getItem(`void-run-best-${diff}`);
      if (stored) {
        const val = parseInt(stored, 10);
        bestRef.current = val;
        setDisplayBest(val);
      }
    } catch {
      // localStorage unavailable
    }
    setIsMobile(window.matchMedia("(max-width: 767px)").matches);
  }, []);

  /* ---- Jump logic ---- */
  const doJump = useCallback(() => {
    if (gameStateRef.current === "idle") {
      // Start the game
      const cfg = DIFFICULTY_CONFIGS[difficultyRef.current];
      gameStateRef.current = "running";
      setGameState("running");
      playerYRef.current = PLAYER_Y_GROUND;
      velocityYRef.current = 0;
      onGroundRef.current = true;
      hasDoubleJumpRef.current = true;
      speedRef.current = cfg.initialSpeed;
      scoreRef.current = 0;
      bgOffsetRef.current = 0;
      obstaclesRef.current = [];
      trailRef.current = [];
      nextObstacleXRef.current = CANVAS_W + 200;
      // Reset tilt state
      smoothedTiltRef.current = 0;
      leanCategoryRef.current = "neutral";
      leanLabelTimerRef.current = 0;
      leanLabelCategoryRef.current = "neutral";
      // First jump
      velocityYRef.current = JUMP_FORCE;
      onGroundRef.current = false;
      return;
    }

    if (gameStateRef.current === "dead") return;

    if (onGroundRef.current) {
      velocityYRef.current = JUMP_FORCE;
      onGroundRef.current = false;
      hasDoubleJumpRef.current = true;
    } else if (hasDoubleJumpRef.current) {
      velocityYRef.current = DOUBLE_JUMP_FORCE;
      hasDoubleJumpRef.current = false;
    }
  }, []);

  /* ---- Restart ---- */
  const doRestart = useCallback(() => {
    const cfg = DIFFICULTY_CONFIGS[difficultyRef.current];
    gameStateRef.current = "idle";
    setGameState("idle");
    playerYRef.current = PLAYER_Y_GROUND;
    velocityYRef.current = 0;
    onGroundRef.current = true;
    hasDoubleJumpRef.current = true;
    speedRef.current = cfg.initialSpeed;
    scoreRef.current = 0;
    setDisplayScore(0);
    bgOffsetRef.current = 0;
    obstaclesRef.current = [];
    trailRef.current = [];
    nextObstacleXRef.current = CANVAS_W + 200;
    deathFrameRef.current = 0;
    flickerCountRef.current = 0;
    // Reset tilt
    smoothedTiltRef.current = 0;
    leanCategoryRef.current = "neutral";
    leanLabelTimerRef.current = 0;
    leanLabelCategoryRef.current = "neutral";
  }, []);

  /* ---- Death sequence ---- */
  const doDeath = useCallback(() => {
    gameStateRef.current = "dead";
    deathFrameRef.current = 0;
    flickerCountRef.current = 0;

    // Update best for current difficulty
    if (scoreRef.current > bestRef.current) {
      bestRef.current = scoreRef.current;
      setDisplayBest(scoreRef.current);
      try {
        localStorage.setItem(`void-run-best-${difficultyRef.current}`, String(scoreRef.current));
      } catch {
        // localStorage unavailable
      }
    }

    setDisplayScore(scoreRef.current);

    // Delayed state change for overlay (after flicker animation)
    setTimeout(() => {
      setGameState("dead");
    }, 600);
  }, []);

  /* ---- Input handlers ---- */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" || e.code === "ArrowUp") {
        e.preventDefault();
        if (gameStateRef.current === "dead") {
          doRestart();
        } else {
          doJump();
        }
      }
    };

    const handleTouch = (e: TouchEvent) => {
      // Prevent default only on canvas touch to avoid scroll
      const canvas = canvasRef.current;
      if (canvas && canvas.contains(e.target as Node)) {
        e.preventDefault();
      }
      if (gameStateRef.current === "dead") {
        doRestart();
      } else {
        doJump();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    document.addEventListener("touchstart", handleTouch, { passive: false });

    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      document.removeEventListener("touchstart", handleTouch);
    };
  }, [doJump, doRestart]);

  /* ---- Spawn obstacle ---- */
  const spawnObstacle = useCallback(() => {
    const cfg = DIFFICULTY_CONFIGS[difficultyRef.current];
    const type = OBSTACLE_TYPES[Math.floor(Math.random() * OBSTACLE_TYPES.length)];
    const width = 20 + Math.random() * 15;
    obstaclesRef.current.push({
      x: nextObstacleXRef.current,
      type,
      width,
    });
    // Next obstacle distance decreases slightly as speed increases
    const gap =
      cfg.minGap +
      Math.random() * (cfg.maxGap - cfg.minGap) -
      Math.min(speedRef.current * 8, 100);
    nextObstacleXRef.current += Math.max(gap, cfg.minGap);
  }, []);

  /* ---- Game loop ---- */
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const loop = () => {
      frameRef.current++;
      const state = gameStateRef.current;

      if (state === "running") {
        // Update speed
        speedRef.current += DIFFICULTY_CONFIGS[difficultyRef.current].speedIncrement;

        // Update bg offset
        bgOffsetRef.current += speedRef.current;

        // Update score (distance-based)
        scoreRef.current = Math.floor(bgOffsetRef.current * 0.1);

        // Update player physics
        velocityYRef.current += GRAVITY;
        playerYRef.current += velocityYRef.current;

        // Ground clamp
        if (playerYRef.current >= PLAYER_Y_GROUND) {
          playerYRef.current = PLAYER_Y_GROUND;
          velocityYRef.current = 0;
          onGroundRef.current = true;
          hasDoubleJumpRef.current = true;
        }

        // Trail
        trailRef.current.push(playerYRef.current);
        if (trailRef.current.length > TRAIL_LENGTH) {
          trailRef.current.shift();
        }

        // ---- Tilt smoothing (Steadicam spring lag) ----
        // Raw tilt from velocity, clamped to ±TILT_MAX_DEG
        const rawTilt = clampTilt(
          velocityYRef.current * TILT_VELOCITY_SCALE,
          -TILT_MAX_DEG,
          TILT_MAX_DEG
        );
        // Exponential smoothing — the visual tilt trails physics by ~3-4 frames
        smoothedTiltRef.current +=
          (rawTilt - smoothedTiltRef.current) * TILT_SMOOTHING;

        // Lean category detection — triggers label on change
        const newCategory = getLeanCategory(
          smoothedTiltRef.current / TILT_MAX_DEG
        );
        if (newCategory !== leanCategoryRef.current) {
          leanCategoryRef.current = newCategory;
          leanLabelCategoryRef.current = newCategory;
          // Reset label timer — J-cut: label appears immediately
          leanLabelTimerRef.current =
            10 + LEAN_LABEL_HOLD_FRAMES + LEAN_LABEL_FADE_FRAMES;
        }
        // Decrement label timer
        if (leanLabelTimerRef.current > 0) {
          leanLabelTimerRef.current--;
        }

        // Move obstacles
        for (const obs of obstaclesRef.current) {
          obs.x -= speedRef.current;
        }
        // Remove offscreen
        obstaclesRef.current = obstaclesRef.current.filter(
          (obs) => obs.x + obs.width > -20
        );

        // Spawn new obstacles
        const rightmost =
          obstaclesRef.current.length > 0
            ? Math.max(...obstaclesRef.current.map((o) => o.x))
            : 0;
        if (rightmost < nextObstacleXRef.current - CANVAS_W * 0.2) {
          // Check if we need to spawn
        }
        while (
          nextObstacleXRef.current <
          bgOffsetRef.current + CANVAS_W + 200
        ) {
          spawnObstacle();
        }

        // Collision
        if (checkCollision(playerYRef.current, obstaclesRef.current)) {
          doDeath();
        }
      }

      // ---- Render ----
      drawBackground(ctx, bgOffsetRef.current);
      drawGround(ctx);

      if (state === "idle") {
        // Breathing player — neutral tilt, no lean
        const breathe = Math.sin(frameRef.current * 0.04) * 0.5;
        drawPlayer(ctx, PLAYER_Y_GROUND + breathe, [], 0);
        drawIdleScreen(ctx, frameRef.current, isMobile);
        drawScore(ctx, 0, bestRef.current, DIFFICULTY_CONFIGS[difficultyRef.current].initialSpeed);
      }

      if (state === "running") {
        // Draw obstacles
        for (const obs of obstaclesRef.current) {
          drawObstacle(ctx, obs);
        }
        drawPlayer(
          ctx,
          playerYRef.current,
          trailRef.current,
          smoothedTiltRef.current
        );
        drawScore(
          ctx,
          scoreRef.current,
          bestRef.current,
          speedRef.current
        );
        // Lean label — J-cut: appears before tilt fully settles
        drawLeanLabel(
          ctx,
          leanLabelCategoryRef.current,
          leanLabelTimerRef.current
        );
      }

      if (state === "dead") {
        deathFrameRef.current++;

        // Flicker phase: 0-18 frames (~300ms at 60fps)
        if (deathFrameRef.current < 18) {
          flickerCountRef.current++;
          const on = flickerCountRef.current % 6 < 3;
          ctx.fillStyle = "#0a0a0a";
          ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
          if (on) {
            // Flash bright
            ctx.fillStyle = "rgba(201, 168, 76, 0.06)";
            ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
          }
        } else {
          // Static phase
          drawDeathStatic(ctx, deathFrameRef.current);

          // Draw score centered (after overlay is visible)
          if (deathFrameRef.current > 36) {
            ctx.font = '11px "IBM Plex Mono", monospace';
            ctx.textAlign = "center";
            ctx.fillStyle = "rgba(201, 168, 76, 0.5)";
            ctx.fillText("TRANSMISSION LOST", CANVAS_W / 2, CANVAS_H / 2 - 30);

            ctx.font = '12px "IBM Plex Mono", monospace';
            ctx.fillStyle = "rgba(245, 240, 232, 0.6)";
            ctx.fillText(
              `SIGNAL   ${String(scoreRef.current).padStart(6, "0")}`,
              CANVAS_W / 2,
              CANVAS_H / 2
            );
            ctx.fillStyle = "rgba(201, 168, 76, 0.35)";
            ctx.fillText(
              `BEST     ${String(bestRef.current).padStart(6, "0")}`,
              CANVAS_W / 2,
              CANVAS_H / 2 + 20
            );

            // Restart prompt
            const restartFlicker = Math.sin(deathFrameRef.current * 0.05) > -0.2;
            if (restartFlicker) {
              ctx.fillStyle = "rgba(245, 240, 232, 0.25)";
              ctx.font = '10px "IBM Plex Mono", monospace';
              ctx.fillText(
                isMobile ? "TAP TO RESTART" : "[ SPACE ] RESTART",
                CANVAS_W / 2,
                CANVAS_H / 2 + 55
              );
            }
          }
        }
      }

      rafRef.current = requestAnimationFrame(loop);
    };

    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isMobile, spawnObstacle, doDeath]);

  return (
    <div className="run-page">
      {/* Film grain */}
      <div className="run-page__grain" aria-hidden="true">
        <svg width="0" height="0" aria-hidden="true">
          <filter id="run-grain">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="0.65"
              numOctaves="3"
              stitchTiles="stitch"
              result="noise"
            />
            <feColorMatrix
              type="saturate"
              values="0"
              in="noise"
              result="mono"
            />
          </filter>
        </svg>
        <div className="run-page__grain-layer" />
      </div>

      {/* Navigation */}
      <nav className="run-page__nav" aria-label="Breadcrumb">
        <Link href="/games" className="run-page__back">
          <span aria-hidden="true">&larr;</span> void --games
        </Link>
      </nav>

      {/* Header */}
      <header className="run-page__header">
        <h1 className="run-page__title">VOID RUN</h1>
        <p className="run-page__tagline">run until the signal breaks</p>
      </header>

      {/* Difficulty selector */}
      <div
        className={`run-page__difficulty${gameState === "running" ? " run-page__difficulty--locked" : ""}`}
        aria-label="Select difficulty"
        role="group"
      >
        {(Object.keys(DIFFICULTY_CONFIGS) as Difficulty[]).map((d) => (
          <button
            key={d}
            type="button"
            className={`run-page__diff-btn${difficulty === d ? " run-page__diff-btn--active" : ""}`}
            onClick={() => handleDifficultyChange(d)}
            disabled={gameState === "running"}
            aria-pressed={difficulty === d}
            title={DIFFICULTY_CONFIGS[d].hint}
          >
            {DIFFICULTY_CONFIGS[d].label}
          </button>
        ))}
      </div>

      {/* Canvas */}
      <div className="run-page__canvas-wrap">
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          role="img"
          aria-label="Void Run game canvas. Use space bar or tap to jump over obstacles."
        />
        <div className="run-page__scanlines" aria-hidden="true" />
      </div>

      {/* Controls hint */}
      <div className="run-page__controls" aria-hidden="true">
        <span>
          {isMobile
            ? "[TAP] to jump \u00B7 double jump available"
            : "[SPACE] or [TAP] to jump \u00B7 double jump available"}
        </span>
      </div>

      {/* Death overlay (HTML layer for accessibility) */}
      {gameState === "dead" && (
        <div
          className="run-page__death-overlay"
          role="alert"
          aria-live="assertive"
        >
          <p className="run-page__death-title">TRANSMISSION LOST</p>
          <div className="run-page__death-scores">
            <p className="run-page__death-score">
              <span className="run-page__death-label">SIGNAL</span>
              <span className="run-page__death-value">
                {String(displayScore).padStart(6, "0")}
              </span>
            </p>
            <p className="run-page__death-score">
              <span className="run-page__death-label">BEST</span>
              <span className="run-page__death-value">
                {String(displayBest).padStart(6, "0")}
              </span>
            </p>
          </div>
          <button
            type="button"
            className="run-page__restart"
            onClick={doRestart}
            aria-label="Restart game"
          >
            RESTART
          </button>
        </div>
      )}
    </div>
  );
}
