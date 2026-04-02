/**
 * shareCardRenderer.ts — Canvas 2D "Evidence Card" generator
 *
 * Draws a shareable card focused on the STORY OUTPUT:
 *   - Headline + summary (what happened)
 *   - Spectrum strip with source positions (who said what)
 *   - Sigil (the visual bias indicator)
 *   - Brand mark
 *
 * Two formats:
 *   - OG card: 1200x630 (Twitter/LinkedIn)
 *   - Square card: 1080x1080 (Instagram/TikTok)
 *
 * No npm dependencies. Hardcodes dark-mode palette.
 */

import type { Story } from "./types";
import { leanLabel } from "./biasColors";

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
  [0,   "#4A6FA5"], [17,  "#6B8DB5"], [33,  "#8FAAB8"],
  [50,  "#9A9590"], [67,  "#C09A8A"], [83,  "#B07060"], [100, "#964A3A"],
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
  grad.addColorStop(0.28, "#8FAAB8"); grad.addColorStop(0.42, "#9A9590");
  grad.addColorStop(0.57, "#C09A8A"); grad.addColorStop(0.71, "#B07060");
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
  ctx.fillText("See every side of the story", 48, 545);

  // Right side — key stats
  ctx.textAlign = "right";
  ctx.font = `600 11px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.fillText("419 CURATED SOURCES  ·  6-AXIS ANALYSIS  ·  FREE", 1152, 520);
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
  ctx.fillText("See every side of the story", 56, 990);

  // Stats right
  ctx.textAlign = "right";
  ctx.font = `600 11px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.fillText("419 SOURCES  ·  6-AXIS ANALYSIS  ·  FREE", 1024, 958);
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
