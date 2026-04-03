/**
 * shareCardRenderer.ts — Canvas 2D "Evidence Card" generator
 *
 * Draws a shareable card focused on the STORY OUTPUT:
 *   - Headline + summary (what happened)
 *   - Spectrum strip with source positions (who said what)
 *   - Sigil (the visual bias indicator)
 *   - Brand mark
 *
 * Three formats:
 *   - OG card: 1200x630 (Twitter/LinkedIn)
 *   - Square card: 1080x1080 (Instagram/feed)
 *   - Story card: 1080x1920 (9:16 — Stories/TikTok/Reels)
 *     Two variants: "Split" (divergent headlines) and "Verdict" (6-axis forensic)
 *
 * Uses qrcode npm package for QR generation.
 */

import type { Story, StorySource } from "./types";
import { leanLabel } from "./biasColors";
import QRCode from "qrcode";

/* ── Dark-mode palette ────────────────────────────────────────────────── */

const BG           = "#1C1A17";
const BG_ELEVATED  = "#252320";
const FG_PRIMARY   = "#EDE8E0";
const FG_SECONDARY = "#B8B0A5";
const FG_TERTIARY  = "#A09890";
const FG_MUTED     = "#686260";
const FG_FAINT     = "#5A5550";
const RULE_COLOR   = "#3A3530";
const AMBER        = "#C8A96E";

/* ── Lean spectrum ────────────────────────────────────────────────────── */

const LEAN_STOPS: [number, string][] = [
  [0,   "#4A6FA5"], [17,  "#6B8DB5"], [33,  "#5E9CAE"],
  [50,  "#3D9B6A"], [67,  "#B08A6A"], [83,  "#B07060"], [100, "#964A3A"],
];

function lerpHex(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg_ = (bh >> 8) & 0xff, bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg_ - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

function leanColor(v: number): string {
  if (v <= LEAN_STOPS[0][0]) return LEAN_STOPS[0][1];
  if (v >= LEAN_STOPS[LEAN_STOPS.length - 1][0]) return LEAN_STOPS[LEAN_STOPS.length - 1][1];
  for (let i = 0; i < LEAN_STOPS.length - 1; i++) {
    if (v >= LEAN_STOPS[i][0] && v <= LEAN_STOPS[i + 1][0]) {
      const t = (v - LEAN_STOPS[i][0]) / (LEAN_STOPS[i + 1][0] - LEAN_STOPS[i][0]);
      return lerpHex(LEAN_STOPS[i][1], LEAN_STOPS[i + 1][1], t);
    }
  }
  return LEAN_STOPS[3][1];
}

/* ── Fonts ────────────────────────────────────────────────────────────── */

const EDITORIAL  = "'Playfair Display', Georgia, serif";
const STRUCTURAL = "'Inter', system-ui, sans-serif";
const META       = "'Barlow Condensed', 'Arial Narrow', sans-serif";
const DATA       = "'IBM Plex Mono', 'Courier New', monospace";

/* ── Helpers ──────────────────────────────────────────────────────────── */

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y); ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r); ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r); ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r); ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r); ctx.closePath();
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = "";
  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && current) {
      lines.push(current);
      current = word;
    } else { current = test; }
  }
  if (current) lines.push(current);
  return lines;
}

function drawSigil(ctx: CanvasRenderingContext2D, cx: number, cy: number, size: number, lean: number, sourceCount: number): void {
  const color = leanColor(lean);
  // Outer ring — coverage indicator
  ctx.beginPath();
  ctx.arc(cx, cy, size, 0, Math.PI * 2);
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1.5;
  ctx.stroke();

  // Coverage arc — fills proportionally to source count (max at ~15 sources)
  const coverage = Math.min(1, sourceCount / 15);
  ctx.beginPath();
  ctx.arc(cx, cy, size, -Math.PI / 2, -Math.PI / 2 + coverage * Math.PI * 2);
  ctx.strokeStyle = color;
  ctx.lineWidth = 3;
  ctx.stroke();

  // Inner beam (the scale)
  const tilt = ((lean - 50) / 50) * 12 * (Math.PI / 180); // max ±12 degrees
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(tilt);
  // Beam
  ctx.beginPath();
  ctx.moveTo(-size * 0.55, 0);
  ctx.lineTo(size * 0.55, 0);
  ctx.strokeStyle = FG_PRIMARY;
  ctx.lineWidth = 2;
  ctx.stroke();
  // Left pan
  ctx.beginPath();
  ctx.moveTo(-size * 0.55, 0);
  ctx.lineTo(-size * 0.45, size * 0.2);
  ctx.lineTo(-size * 0.65, size * 0.2);
  ctx.closePath();
  ctx.fillStyle = lean < 50 ? color : FG_MUTED;
  ctx.globalAlpha = lean < 50 ? 0.8 : 0.3;
  ctx.fill();
  ctx.globalAlpha = 1;
  // Right pan
  ctx.beginPath();
  ctx.moveTo(size * 0.55, 0);
  ctx.lineTo(size * 0.45, size * 0.2);
  ctx.lineTo(size * 0.65, size * 0.2);
  ctx.closePath();
  ctx.fillStyle = lean > 50 ? color : FG_MUTED;
  ctx.globalAlpha = lean > 50 ? 0.8 : 0.3;
  ctx.fill();
  ctx.globalAlpha = 1;
  // Fulcrum
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(-size * 0.08, size * 0.35);
  ctx.lineTo(size * 0.08, size * 0.35);
  ctx.closePath();
  ctx.fillStyle = FG_SECONDARY;
  ctx.fill();
  ctx.restore();
}

function drawSpectrumWithSources(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  clusterLean: number,
  sourceCount: number,
): void {
  // Gradient bar
  const grad = ctx.createLinearGradient(x, 0, x + w, 0);
  grad.addColorStop(0, "#4A6FA5"); grad.addColorStop(0.14, "#6B8DB5");
  grad.addColorStop(0.28, "#5E9CAE"); grad.addColorStop(0.42, "#3D9B6A");
  grad.addColorStop(0.57, "#B08A6A"); grad.addColorStop(0.71, "#B07060");
  grad.addColorStop(1, "#964A3A");
  ctx.fillStyle = grad;
  roundRect(ctx, x, y, w, h, 4);
  ctx.fill();

  // Simulated source dots spread around the cluster lean
  const dotCount = Math.min(sourceCount, 12);
  const spread = 15; // ±15 points spread
  ctx.globalAlpha = 0.7;
  for (let i = 0; i < dotCount; i++) {
    // Distribute dots with slight randomness based on index
    const offset = ((i - dotCount / 2) / (dotCount / 2)) * spread;
    const dotLean = Math.max(2, Math.min(98, clusterLean + offset));
    const dotX = x + (dotLean / 100) * w;
    const dotY = y + h / 2 + ((i % 3) - 1) * 3; // slight vertical jitter
    ctx.beginPath();
    ctx.arc(dotX, dotY, 4, 0, Math.PI * 2);
    ctx.fillStyle = leanColor(dotLean);
    ctx.fill();
    ctx.strokeStyle = BG;
    ctx.lineWidth = 1.5;
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  // Main cluster marker (larger, prominent)
  const mainX = x + Math.max(8, Math.min(w - 8, (clusterLean / 100) * w));
  ctx.beginPath();
  ctx.arc(mainX, y + h / 2, 8, 0, Math.PI * 2);
  ctx.fillStyle = FG_PRIMARY;
  ctx.fill();
  ctx.strokeStyle = BG;
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Zone labels
  ctx.font = `600 9px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.textAlign = "center";
  const zones = ["LEFT", "CENTER-LEFT", "CENTER", "CENTER-RIGHT", "RIGHT"];
  const zonePositions = [0.1, 0.3, 0.5, 0.7, 0.9];
  zones.forEach((lbl, i) => {
    ctx.fillText(lbl, x + zonePositions[i] * w, y + h + 16);
  });
  ctx.textAlign = "left";
}

/* ── OG Card (1200x630) ──────────────────────────────────────────────── */

export async function generateShareCardImage(story: Story): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d")!;

  if (typeof document !== "undefined" && document.fonts) {
    try { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 500))]); } catch { /* proceed */ }
  }

  const lean = story.biasScores.politicalLean;

  /* ═══ BACKGROUND ═══ */
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, 1200, 630);
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, 1199, 629);

  /* ═══ TOP BAR: Brand + Category + Source count ═══ */
  // Brand mark
  ctx.textBaseline = "alphabetic";
  ctx.font = `700 16px ${EDITORIAL}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.fillText("void", 48, 44);
  const vw = ctx.measureText("void").width;
  ctx.font = `400 16px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 48 + vw, 44);

  // Category badge
  ctx.font = `600 11px ${META}`;
  ctx.fillStyle = AMBER;
  ctx.textAlign = "center";
  const catText = story.category.toUpperCase();
  const catW = ctx.measureText(catText).width + 16;
  roundRect(ctx, 600 - catW / 2, 30, catW, 22, 2);
  ctx.fillStyle = BG_ELEVATED;
  ctx.fill();
  ctx.strokeStyle = AMBER;
  ctx.lineWidth = 1;
  roundRect(ctx, 600 - catW / 2, 30, catW, 22, 2);
  ctx.stroke();
  ctx.fillStyle = AMBER;
  ctx.fillText(catText, 600, 46);
  ctx.textAlign = "left";

  // Source count
  ctx.font = `500 13px ${DATA}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.textAlign = "right";
  ctx.fillText(`${story.source.count} sources`, 1152, 44);
  ctx.textAlign = "left";

  /* ═══ THIN RULE ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(48, 62); ctx.lineTo(1152, 62); ctx.stroke();

  /* ═══ SIGIL (left side, large) ═══ */
  drawSigil(ctx, 130, 170, 56, lean, story.source.count);

  // Lean label under sigil
  ctx.font = `700 14px ${DATA}`;
  ctx.fillStyle = leanColor(lean);
  ctx.textAlign = "center";
  ctx.fillText(leanLabel(lean), 130, 245);
  ctx.font = `400 11px ${META}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(`${story.source.count} SOURCES`, 130, 262);
  ctx.textAlign = "left";

  /* ═══ HEADLINE (right of sigil) ═══ */
  ctx.font = `700 36px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  const headLines = wrapText(ctx, story.title, 880);
  headLines.slice(0, 3).forEach((line, i) => {
    const display = i === 2 && headLines.length > 3 ? line.slice(0, -3) + "..." : line;
    ctx.fillText(display, 230, 110 + i * 44);
  });

  /* ═══ SUMMARY (below headline) ═══ */
  const summaryY = 110 + Math.min(headLines.length, 3) * 44 + 16;
  ctx.font = `400 15px ${STRUCTURAL}`;
  ctx.fillStyle = FG_TERTIARY;
  const summaryLines = wrapText(ctx, story.summary, 880);
  const maxSummaryLines = Math.min(4, Math.floor((310 - summaryY + 110) / 22));
  summaryLines.slice(0, maxSummaryLines).forEach((line, i) => {
    const display = i === maxSummaryLines - 1 && summaryLines.length > maxSummaryLines
      ? line.slice(0, -3) + "..."
      : line;
    ctx.fillText(display, 230, summaryY + i * 22);
  });

  /* ═══ SPECTRUM WITH SOURCES ═══ */
  const specY = 340;
  drawSpectrumWithSources(ctx, 48, specY, 1104, 28, lean, story.source.count);

  /* ═══ STORY CONTEXT BAR ═══ */
  // A warm amber accent bar with key data points
  ctx.fillStyle = BG_ELEVATED;
  roundRect(ctx, 48, 400, 1104, 52, 4);
  ctx.fill();
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  roundRect(ctx, 48, 400, 1104, 52, 4);
  ctx.stroke();

  // Three data points inside the bar
  const dataPoints = [
    { label: "LEAN", value: leanLabel(lean), color: leanColor(lean) },
    { label: "SOURCES", value: String(story.source.count), color: FG_PRIMARY },
    { label: "COVERAGE", value: story.divergenceScore > 60 ? "DIVERGENT" : story.divergenceScore > 30 ? "MIXED" : "CONSENSUS", color: story.divergenceScore > 60 ? "#D4645A" : story.divergenceScore > 30 ? "#EAB308" : "#22C55E" },
  ];

  dataPoints.forEach((dp, i) => {
    const dpX = 48 + 20 + i * 368;
    ctx.font = `600 10px ${META}`;
    ctx.fillStyle = FG_MUTED;
    ctx.fillText(dp.label, dpX, 422);
    ctx.font = `700 18px ${DATA}`;
    ctx.fillStyle = dp.color;
    ctx.fillText(dp.value, dpX, 443);
  });

  /* ═══ FOOTER ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(48, 480); ctx.lineTo(1152, 480); ctx.stroke();

  // Warm amber accent line
  ctx.strokeStyle = AMBER;
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(48, 478); ctx.lineTo(200, 478); ctx.stroke();

  // Brand + tagline
  ctx.font = `700 24px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  ctx.fillText("void", 48, 520);
  const vw2 = ctx.measureText("void").width;
  ctx.font = `400 24px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 48 + vw2, 520);

  ctx.font = `400 13px ${STRUCTURAL}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.fillText("See through the void.", 48, 545);

  // Right side — key stats
  ctx.textAlign = "right";
  ctx.font = `600 11px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.fillText("951 CURATED SOURCES  ·  6-AXIS ANALYSIS  ·  FREE", 1152, 520);
  ctx.font = `400 12px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("voidnews.app", 1152, 545);
  ctx.textAlign = "left";

  /* ═══ VIGNETTE (subtle corner darkening) ═══ */
  const vignette = ctx.createRadialGradient(600, 280, 200, 600, 315, 700);
  vignette.addColorStop(0, "rgba(0,0,0,0)");
  vignette.addColorStop(1, "rgba(0,0,0,0.15)");
  ctx.fillStyle = vignette;
  ctx.fillRect(0, 0, 1200, 630);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("toBlob failed")), "image/png");
  });
}

/* ── Square Card (1080x1080) for Instagram/TikTok ────────────────────── */

export async function generateSquareCardImage(story: Story): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1080;
  const ctx = canvas.getContext("2d")!;

  if (typeof document !== "undefined" && document.fonts) {
    try { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 500))]); } catch { /* proceed */ }
  }

  const lean = story.biasScores.politicalLean;

  /* ═══ BACKGROUND ═══ */
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, 1080, 1080);
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, 1079, 1079);

  /* ═══ TOP: Brand + Category ═══ */
  ctx.textBaseline = "alphabetic";
  ctx.font = `700 18px ${EDITORIAL}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.fillText("void", 56, 56);
  const vw = ctx.measureText("void").width;
  ctx.font = `400 18px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 56 + vw, 56);

  ctx.font = `600 12px ${META}`;
  ctx.fillStyle = AMBER;
  ctx.textAlign = "right";
  ctx.fillText(story.category.toUpperCase(), 1024, 56);
  ctx.textAlign = "left";

  /* ═══ RULE ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.beginPath(); ctx.moveTo(56, 74); ctx.lineTo(1024, 74); ctx.stroke();

  /* ═══ SIGIL (centered, hero size) ═══ */
  drawSigil(ctx, 540, 180, 80, lean, story.source.count);

  // Lean label under sigil
  ctx.font = `700 20px ${DATA}`;
  ctx.fillStyle = leanColor(lean);
  ctx.textAlign = "center";
  ctx.fillText(leanLabel(lean), 540, 285);
  ctx.font = `500 13px ${META}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(`${story.source.count} SOURCES`, 540, 306);
  ctx.textAlign = "left";

  /* ═══ RULE ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.beginPath(); ctx.moveTo(56, 325); ctx.lineTo(1024, 325); ctx.stroke();
  // Amber accent
  ctx.strokeStyle = AMBER;
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(56, 323); ctx.lineTo(200, 323); ctx.stroke();
  ctx.lineWidth = 1;

  /* ═══ HEADLINE (centered, large) ═══ */
  ctx.font = `700 38px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  ctx.textAlign = "center";
  const sqHeadLines = wrapText(ctx, story.title, 900);
  sqHeadLines.slice(0, 3).forEach((line, i) => {
    const display = i === 2 && sqHeadLines.length > 3 ? line.slice(0, -3) + "..." : line;
    ctx.fillText(display, 540, 375 + i * 48);
  });
  ctx.textAlign = "left";

  /* ═══ SUMMARY (centered) ═══ */
  const sqSumY = 375 + Math.min(sqHeadLines.length, 3) * 48 + 24;
  ctx.font = `400 16px ${STRUCTURAL}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.textAlign = "center";
  const sqSumLines = wrapText(ctx, story.summary, 900);
  const maxSqSum = Math.min(5, Math.floor((740 - sqSumY) / 24));
  sqSumLines.slice(0, maxSqSum).forEach((line, i) => {
    const display = i === maxSqSum - 1 && sqSumLines.length > maxSqSum ? line.slice(0, -3) + "..." : line;
    ctx.fillText(display, 540, sqSumY + i * 24);
  });
  ctx.textAlign = "left";

  /* ═══ SPECTRUM WITH SOURCES ═══ */
  const sqSpecY = 770;
  drawSpectrumWithSources(ctx, 56, sqSpecY, 968, 32, lean, story.source.count);

  /* ═══ DATA BAR ═══ */
  ctx.fillStyle = BG_ELEVATED;
  roundRect(ctx, 56, 830, 968, 48, 4);
  ctx.fill();
  ctx.strokeStyle = RULE_COLOR;
  roundRect(ctx, 56, 830, 968, 48, 4);
  ctx.stroke();

  const sqData = [
    { label: "LEAN", value: leanLabel(lean), color: leanColor(lean) },
    { label: "SOURCES", value: String(story.source.count), color: FG_PRIMARY },
    { label: "COVERAGE", value: story.divergenceScore > 60 ? "DIVERGENT" : story.divergenceScore > 30 ? "MIXED" : "CONSENSUS", color: story.divergenceScore > 60 ? "#D4645A" : story.divergenceScore > 30 ? "#EAB308" : "#22C55E" },
  ];
  sqData.forEach((dp, i) => {
    const dpX = 56 + 24 + i * 322;
    ctx.font = `600 9px ${META}`;
    ctx.fillStyle = FG_MUTED;
    ctx.fillText(dp.label, dpX, 850);
    ctx.font = `700 16px ${DATA}`;
    ctx.fillStyle = dp.color;
    ctx.fillText(dp.value, dpX, 869);
  });

  /* ═══ FOOTER ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.beginPath(); ctx.moveTo(56, 910); ctx.lineTo(1024, 910); ctx.stroke();
  ctx.strokeStyle = AMBER;
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(56, 908); ctx.lineTo(200, 908); ctx.stroke();

  // Brand
  ctx.font = `700 28px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  ctx.fillText("void", 56, 960);
  const sqvw = ctx.measureText("void").width;
  ctx.font = `400 28px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 56 + sqvw, 960);

  ctx.font = `400 14px ${STRUCTURAL}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.fillText("See through the void.", 56, 990);

  // Stats right
  ctx.textAlign = "right";
  ctx.font = `600 11px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.fillText("951 SOURCES  ·  6-AXIS ANALYSIS  ·  FREE", 1024, 958);
  ctx.font = `400 13px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("voidnews.app", 1024, 985);
  ctx.textAlign = "left";

  /* ═══ VIGNETTE ═══ */
  const vig = ctx.createRadialGradient(540, 450, 250, 540, 540, 650);
  vig.addColorStop(0, "rgba(0,0,0,0)");
  vig.addColorStop(1, "rgba(0,0,0,0.12)");
  ctx.fillStyle = vig;
  ctx.fillRect(0, 0, 1080, 1080);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("toBlob failed")), "image/png");
  });
}

/* ── QR Code Helper ──────────────────────────────────────────────────── */

async function drawQR(ctx: CanvasRenderingContext2D, url: string, x: number, y: number, size: number): Promise<void> {
  try {
    const dataUrl = await QRCode.toDataURL(url, {
      width: size,
      margin: 0,
      color: { dark: "#EDE8E0", light: "#00000000" },
      errorCorrectionLevel: "M",
    });
    const img = new Image();
    await new Promise<void>((resolve, reject) => {
      img.onload = () => resolve();
      img.onerror = reject;
      img.src = dataUrl;
    });
    ctx.drawImage(img, x, y, size, size);
  } catch {
    // QR failed — draw placeholder box
    ctx.strokeStyle = RULE_COLOR;
    ctx.lineWidth = 1;
    ctx.strokeRect(x, y, size, size);
    ctx.font = `400 11px ${DATA}`;
    ctx.fillStyle = FG_MUTED;
    ctx.textAlign = "center";
    ctx.fillText("QR", x + size / 2, y + size / 2 + 4);
    ctx.textAlign = "left";
  }
}

/* ── Lean badge color ────────────────────────────────────────────────── */

function leanBadgeColor(v: number): string {
  if (v <= 35) return "#4A6FA5";  // left-blue
  if (v <= 65) return "#3D9B6A";  // center-green
  return "#964A3A";               // right-red
}

/* ── 9:16 Story Card (1080x1920) — Split & Verdict formats ──────────── */

/**
 * Generates a 9:16 (1080x1920) share card optimized for Stories/TikTok/Reels.
 *
 * Two formats auto-selected:
 *   - "Split": Two divergent source headlines side-by-side (when sources have
 *     high lean divergence and available headlines)
 *   - "Verdict": 6-axis forensic scorecard (fallback)
 *
 * Both include a QR code linking to the story's deep dive.
 */
export async function generateStoryCardImage(
  story: Story,
  sources: StorySource[] = [],
  storyUrl?: string,
): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1920;
  const ctx = canvas.getContext("2d")!;

  if (typeof document !== "undefined" && document.fonts) {
    try { await Promise.race([document.fonts.ready, new Promise(r => setTimeout(r, 500))]); } catch { /* proceed */ }
  }

  const lean = story.biasScores.politicalLean;
  const url = storyUrl || (typeof window !== "undefined" ? window.location.href : "https://voidnews.app");

  /* Determine format: Split vs Verdict */
  const splitPair = pickSplitPair(sources);
  const useSplit = !!splitPair;

  /* ═══ BACKGROUND ═══ */
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, 1080, 1920);

  /* Outer border */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, 1079, 1919);

  /* ═══ TOP: Brand label ═══ */
  ctx.textBaseline = "alphabetic";
  ctx.font = `600 14px ${META}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("void --deep-dive", 64, 72);

  /* Category badge (right) */
  ctx.font = `600 12px ${META}`;
  ctx.fillStyle = AMBER;
  ctx.textAlign = "right";
  ctx.fillText(story.category.toUpperCase(), 1016, 72);
  ctx.textAlign = "left";

  /* Rule */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(64, 92); ctx.lineTo(1016, 92); ctx.stroke();

  if (useSplit) {
    drawSplitFormat(ctx, story, splitPair!, sources.length);
  } else {
    drawVerdictFormat(ctx, story);
  }

  /* ═══ SPECTRUM STRIP (shared) ═══ */
  const specY = 1380;
  drawSpectrumWithSources(ctx, 64, specY, 952, 28, lean, story.source.count);

  /* ═══ RULE ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(64, 1450); ctx.lineTo(1016, 1450); ctx.stroke();

  /* ═══ PROVOCATION LINE ═══ */
  ctx.font = `500 18px ${STRUCTURAL}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.textAlign = "center";
  ctx.fillText(
    useSplit ? "Same story. Different cut." : "How is your source covering this?",
    540, 1490,
  );
  ctx.textAlign = "left";

  /* ═══ RULE ═══ */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(64, 1520); ctx.lineTo(1016, 1520); ctx.stroke();
  ctx.strokeStyle = AMBER;
  ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(64, 1518); ctx.lineTo(250, 1518); ctx.stroke();

  /* ═══ BOTTOM: QR + Brand lockup ═══ */
  await drawQR(ctx, url, 64, 1560, 140);

  // Brand lockup (right of QR)
  ctx.font = `700 32px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  ctx.fillText("void", 230, 1600);
  const bw = ctx.measureText("void").width;
  ctx.font = `400 32px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 230 + bw, 1600);

  ctx.font = `400 16px ${DATA}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.fillText("See through the void.", 230, 1635);

  ctx.font = `400 14px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("voidnews.app", 230, 1665);

  /* ═══ FOOTER STATS ═══ */
  ctx.font = `600 12px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.textAlign = "center";
  ctx.fillText("951 SOURCES  ·  6-AXIS ANALYSIS  ·  FREE", 540, 1760);
  ctx.textAlign = "left";

  /* ═══ VIGNETTE ═══ */
  const vig = ctx.createRadialGradient(540, 900, 400, 540, 960, 1000);
  vig.addColorStop(0, "rgba(0,0,0,0)");
  vig.addColorStop(1, "rgba(0,0,0,0.12)");
  ctx.fillStyle = vig;
  ctx.fillRect(0, 0, 1080, 1920);

  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(blob => blob ? resolve(blob) : reject(new Error("toBlob failed")), "image/png");
  });
}

/* ── Split Pair Selection ────────────────────────────────────────────── */

interface SplitPair {
  left: StorySource;
  right: StorySource;
}

function pickSplitPair(sources: StorySource[]): SplitPair | null {
  if (sources.length < 2) return null;

  // Filter sources that have headlines
  const withTitles = sources.filter(s => s.articleTitle && s.articleTitle.length > 10);
  if (withTitles.length < 2) return null;

  // Find the pair with maximum lean divergence
  let bestPair: SplitPair | null = null;
  let maxDelta = 0;

  for (let i = 0; i < withTitles.length; i++) {
    for (let j = i + 1; j < withTitles.length; j++) {
      const delta = Math.abs(
        withTitles[i].biasScores.politicalLean - withTitles[j].biasScores.politicalLean
      );
      if (delta > maxDelta) {
        maxDelta = delta;
        const [a, b] = withTitles[i].biasScores.politicalLean <= withTitles[j].biasScores.politicalLean
          ? [withTitles[i], withTitles[j]]
          : [withTitles[j], withTitles[i]];
        bestPair = { left: a, right: b };
      }
    }
  }

  // Require minimum 20-point lean delta for the Split format
  if (maxDelta < 20 || !bestPair) return null;
  return bestPair;
}

/* ── Split Format Drawing ────────────────────────────────────────────── */

function drawSplitFormat(
  ctx: CanvasRenderingContext2D,
  story: Story,
  pair: SplitPair,
  totalSources: number,
): void {
  let curY = 130;

  /* Source A card */
  curY = drawSourceCard(ctx, pair.left, curY);

  /* "vs" separator */
  curY += 32;
  ctx.font = `400 20px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.textAlign = "center";
  ctx.fillText("vs", 540, curY);
  ctx.textAlign = "left";
  curY += 32;

  /* Source B card */
  curY = drawSourceCard(ctx, pair.right, curY);

  /* Stats line */
  curY += 48;
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(64, curY); ctx.lineTo(1016, curY); ctx.stroke();
  curY += 36;

  ctx.font = `600 16px ${DATA}`;
  ctx.fillStyle = FG_TERTIARY;
  ctx.textAlign = "center";
  ctx.fillText(`SAME STORY. ${totalSources} SOURCES.`, 540, curY);
  curY += 30;

  // Count unique framing approaches (approximate from divergence score)
  const framings = Math.min(totalSources, Math.max(2, Math.ceil(story.divergenceScore / 15)));
  ctx.fillText(`${framings} DIFFERENT FRAMINGS.`, 540, curY);
  ctx.textAlign = "left";
}

function drawSourceCard(
  ctx: CanvasRenderingContext2D,
  source: StorySource,
  y: number,
): number {
  const cardX = 64;
  const cardW = 952;
  const cardPad = 32;
  const titleMaxW = cardW - cardPad * 2;

  /* Source name + lean badge */
  const nameY = y + cardPad + 20;
  ctx.font = `600 15px ${META}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.fillText(source.name.toUpperCase(), cardX + cardPad, nameY);

  // Lean badge
  const lean = source.biasScores.politicalLean;
  const badgeText = leanLabel(lean).toUpperCase();
  ctx.font = `600 11px ${META}`;
  const badgeW = ctx.measureText(badgeText).width + 16;
  const badgeX = 1016 - cardPad - badgeW;
  const badgeY = nameY - 14;

  roundRect(ctx, badgeX, badgeY, badgeW, 20, 3);
  ctx.fillStyle = leanBadgeColor(lean);
  ctx.globalAlpha = 0.15;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.strokeStyle = leanBadgeColor(lean);
  ctx.lineWidth = 1;
  roundRect(ctx, badgeX, badgeY, badgeW, 20, 3);
  ctx.stroke();
  ctx.fillStyle = leanBadgeColor(lean);
  ctx.textAlign = "center";
  ctx.fillText(badgeText, badgeX + badgeW / 2, nameY - 1);
  ctx.textAlign = "left";

  /* Headline */
  const headY = nameY + 28;
  ctx.font = `700 30px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  const headLines = wrapText(ctx, source.articleTitle || source.name, titleMaxW);
  const maxHead = Math.min(headLines.length, 4);
  headLines.slice(0, maxHead).forEach((line, i) => {
    const display = i === maxHead - 1 && headLines.length > maxHead ? line.slice(0, -3) + "..." : line;
    ctx.fillText(display, cardX + cardPad, headY + i * 38);
  });

  const cardH = cardPad + 20 + 28 + maxHead * 38 + cardPad;

  /* Draw card background (behind everything) */
  ctx.save();
  ctx.globalCompositeOperation = "destination-over";
  roundRect(ctx, cardX, y, cardW, cardH, 12);
  ctx.fillStyle = BG_ELEVATED;
  ctx.fill();
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  roundRect(ctx, cardX, y, cardW, cardH, 12);
  ctx.stroke();
  ctx.restore();

  return y + cardH;
}

/* ── Verdict Format Drawing ──────────────────────────────────────────── */

function drawVerdictFormat(
  ctx: CanvasRenderingContext2D,
  story: Story,
): void {
  let curY = 130;

  /* Headline */
  ctx.font = `700 38px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  const headLines = wrapText(ctx, story.title, 888);
  headLines.slice(0, 4).forEach((line, i) => {
    const display = i === 3 && headLines.length > 4 ? line.slice(0, -3) + "..." : line;
    ctx.fillText(display, 64, curY + i * 48);
  });
  curY += Math.min(headLines.length, 4) * 48 + 24;

  /* Rule */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(64, curY); ctx.lineTo(1016, curY); ctx.stroke();
  curY += 36;

  /* Section label */
  ctx.font = `600 13px ${META}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("THE EVIDENCE", 64, curY);
  curY += 32;

  /* 6-axis bars */
  const axes: [string, number, string][] = [
    ["LEAN", story.biasScores.politicalLean, leanLabel(story.biasScores.politicalLean)],
    ["RIGOR", story.biasScores.factualRigor, story.biasScores.factualRigor >= 70 ? "Strong" : story.biasScores.factualRigor >= 40 ? "Moderate" : "Weak"],
    ["TONE", story.biasScores.sensationalism, story.biasScores.sensationalism <= 30 ? "Measured" : story.biasScores.sensationalism <= 60 ? "Elevated" : "Inflammatory"],
    ["OPINION", story.biasScores.opinionFact, story.biasScores.opinionFact <= 25 ? "Reporting" : story.biasScores.opinionFact <= 50 ? "Analysis" : story.biasScores.opinionFact <= 75 ? "Opinion" : "Editorial"],
    ["FRAMING", story.biasScores.framing, story.biasScores.framing <= 25 ? "Neutral" : story.biasScores.framing <= 50 ? "Mild" : story.biasScores.framing <= 75 ? "Moderate" : "Heavy"],
    ["AGREEMENT", 100 - story.divergenceScore, story.divergenceScore > 60 ? "Low" : story.divergenceScore > 30 ? "Mixed" : "High"],
  ];

  const barX = 64;
  const barW = 700;
  const barH = 16;

  axes.forEach(([label, value, desc]) => {
    /* Label */
    ctx.font = `600 13px ${META}`;
    ctx.fillStyle = FG_MUTED;
    ctx.fillText(label, barX, curY);

    /* Score */
    ctx.font = `700 20px ${DATA}`;
    ctx.fillStyle = FG_PRIMARY;
    ctx.textAlign = "right";
    ctx.fillText(String(Math.round(value)), 1016, curY);
    ctx.textAlign = "left";

    curY += 12;

    /* Track background */
    roundRect(ctx, barX, curY, barW, barH, 4);
    ctx.fillStyle = RULE_COLOR;
    ctx.fill();

    /* Fill */
    const fillW = Math.max(8, (value / 100) * barW);
    roundRect(ctx, barX, curY, fillW, barH, 4);
    ctx.fillStyle = label === "LEAN" ? leanColor(value) : AMBER;
    ctx.globalAlpha = 0.7;
    ctx.fill();
    ctx.globalAlpha = 1;

    /* Descriptor */
    ctx.font = `400 13px ${META}`;
    ctx.fillStyle = FG_TERTIARY;
    ctx.fillText(desc, barX + barW + 16, curY + 13);

    curY += barH + 28;
  });
}
