/**
 * shareCardRenderer.ts — Canvas 2D "Evidence Card" generator
 *
 * Draws a 1200x630 share card (matching OG/Twitter card dimensions) entirely
 * via the Canvas API. No npm dependencies, no DOM-to-image conversion, no
 * font embedding issues. Hardcodes dark-mode colors since social cards
 * always render on the Evening Edition palette.
 *
 * Used by DeepDive share handler to produce a PNG blob for:
 *   - navigator.share({ files }) on mobile
 *   - Direct download on desktop
 */

import type { Story } from "./types";
import { leanLabel, senseLabel, rigorLabel } from "./biasColors";

/* ── Dark-mode palette (card always renders dark) ──────────────────────── */

const BG          = "#1C1A17";
const BG_TRACK    = "#252320";
const BG_BADGE    = "#252320";
const FG_PRIMARY  = "#EDE8E0";
const FG_SECONDARY= "#B8B0A5";
const FG_TERTIARY = "#A09890";
const FG_MUTED    = "#686260";
const FG_FAINT    = "#5A5550";
const RULE_COLOR  = "#3A3530";

/* ── Lean spectrum stops ───────────────────────────────────────────────── */

const LEAN_STOPS: [number, string][] = [
  [0,   "#4A6FA5"],
  [17,  "#6B8DB5"],
  [33,  "#8FAAB8"],
  [50,  "#9A9590"],
  [67,  "#C09A8A"],
  [83,  "#B07060"],
  [100, "#964A3A"],
];

/* ── Color math ────────────────────────────────────────────────────────── */

function lerpHex(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

function interpolateStops(v: number, stops: [number, string][]): string {
  if (v <= stops[0][0]) return stops[0][1];
  if (v >= stops[stops.length - 1][0]) return stops[stops.length - 1][1];
  for (let i = 0; i < stops.length - 1; i++) {
    if (v >= stops[i][0] && v <= stops[i + 1][0]) {
      const t = (v - stops[i][0]) / (stops[i + 1][0] - stops[i][0]);
      return lerpHex(stops[i][1], stops[i + 1][1], t);
    }
  }
  return stops[Math.floor(stops.length / 2)][1];
}

/* ── Per-axis colors (dark mode, no CSS vars) ──────────────────────────── */

function leanColor(v: number): string {
  return interpolateStops(v, LEAN_STOPS);
}

function senseColor(v: number): string {
  if (v <= 50) return lerpHex("#22C55E", "#EAB308", v / 50);
  return lerpHex("#EAB308", "#EF4444", (v - 50) / 50);
}

function rigorColor(v: number): string {
  if (v <= 50) return lerpHex("#EF4444", "#EAB308", v / 50);
  return lerpHex("#EAB308", "#22C55E", (v - 50) / 50);
}

function framingColor(v: number): string {
  return senseColor(v); // Same scale — low=good, high=bad
}

function opinionColor(v: number): string {
  if (v <= 33) return lerpHex("#6B8DB5", "#8B5CF6", v / 33);
  if (v <= 66) return lerpHex("#8B5CF6", "#F97316", (v - 33) / 33);
  return "#F97316";
}

/* ── Per-axis descriptors ──────────────────────────────────────────────── */

function opinionDescriptor(v: number): string {
  if (v <= 25) return "Reporting";
  if (v <= 50) return "Analysis";
  if (v <= 75) return "Opinion";
  return "Editorial";
}

function framingDescriptor(v: number): string {
  if (v <= 20) return "Neutral";
  if (v <= 45) return "Mild";
  if (v <= 65) return "Moderate";
  return "Heavy";
}

/* ── Canvas helpers ────────────────────────────────────────────────────── */

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number, r: number,
): void {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.arcTo(x + w, y, x + w, y + r, r);
  ctx.lineTo(x + w, y + h - r);
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r);
  ctx.lineTo(x + r, y + h);
  ctx.arcTo(x, y + h, x, y + h - r, r);
  ctx.lineTo(x, y + r);
  ctx.arcTo(x, y, x + r, y, r);
  ctx.closePath();
}

/** Word-wrap text into lines that fit within maxWidth. */
function wrapText(
  ctx: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
): string[] {
  const words = text.split(/\s+/);
  const lines: string[] = [];
  let current = "";

  for (const word of words) {
    const test = current ? `${current} ${word}` : word;
    if (ctx.measureText(test).width > maxWidth && current) {
      lines.push(current);
      current = word;
    } else {
      current = test;
    }
  }
  if (current) lines.push(current);
  return lines;
}

/* ── Font availability check ───────────────────────────────────────────── */

/**
 * Build a font string that gracefully degrades. Canvas measureText/fillText
 * silently fall back if a web font isn't loaded. The first available font
 * in the family list wins.
 */
const EDITORIAL = "'Playfair Display', Georgia, serif";
const STRUCTURAL = "'Inter', system-ui, sans-serif";
const META = "'Barlow Condensed', 'Arial Narrow', sans-serif";
const DATA = "'IBM Plex Mono', 'Courier New', monospace";

/* ── Main renderer ─────────────────────────────────────────────────────── */

export async function generateShareCardImage(story: Story): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = 1200;
  canvas.height = 630;
  const ctx = canvas.getContext("2d")!;

  // Try to wait for web fonts if document.fonts is available
  if (typeof document !== "undefined" && document.fonts) {
    try {
      await Promise.race([
        document.fonts.ready,
        new Promise((r) => setTimeout(r, 500)),
      ]);
    } catch {
      // Proceed with fallback fonts
    }
  }

  const lean = story.biasScores.politicalLean;
  const sense = story.biasScores.sensationalism;
  const rigor = story.biasScores.factualRigor;
  const framing = story.biasScores.framing;
  const opinion = story.biasScores.opinionFact;

  /* ═══ BACKGROUND ═══ */
  ctx.fillStyle = BG;
  ctx.fillRect(0, 0, 1200, 630);

  /* 1px border */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.strokeRect(0.5, 0.5, 1199, 629);

  /* ═══ BAND A: Header + Headline + Meta (0-340) ═══ */

  /* Brand mark — top left */
  ctx.textBaseline = "alphabetic";
  ctx.font = `700 18px ${EDITORIAL}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.textAlign = "left";
  ctx.fillText("void", 48, 52);
  const voidW = ctx.measureText("void").width;
  ctx.font = `400 18px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", 48 + voidW, 52);

  /* Source count badge — top right */
  const badgeText = `${story.source.count} sources`;
  ctx.font = `500 13px ${DATA}`;
  const badgeTextW = ctx.measureText(badgeText).width;
  const badgePad = 12;
  const badgeW = badgeTextW + badgePad * 2;
  const badgeX = 1152 - badgeW;
  const badgeY = 34;
  const badgeH = 26;
  ctx.fillStyle = BG_BADGE;
  roundRect(ctx, badgeX, badgeY, badgeW, badgeH, 4);
  ctx.fill();
  ctx.fillStyle = FG_TERTIARY;
  ctx.fillText(badgeText, badgeX + badgePad, badgeY + 17);

  /* Headline — max 3 lines */
  ctx.font = `700 42px ${EDITORIAL}`;
  ctx.fillStyle = FG_PRIMARY;
  const headlineLines = wrapText(ctx, story.title, 1104);
  const maxLines = 3;
  const lineHeight = 51;
  const headlineY = 110;
  headlineLines.slice(0, maxLines).forEach((line, i) => {
    const displayLine = i === maxLines - 1 && headlineLines.length > maxLines
      ? line.slice(0, -3) + "..."
      : line;
    ctx.fillText(displayLine, 48, headlineY + i * lineHeight);
  });

  /* Meta line */
  const metaY = headlineY + Math.min(headlineLines.length, maxLines) * lineHeight + 28;
  ctx.font = `600 15px ${STRUCTURAL}`;
  ctx.fillStyle = FG_TERTIARY;
  const catText = story.category;
  ctx.fillText(catText, 48, metaY);
  let metaX = 48 + ctx.measureText(catText).width;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("  ·  ", metaX, metaY);
  metaX += ctx.measureText("  ·  ").width;
  ctx.fillStyle = FG_TERTIARY;
  const srcText = `${story.source.count} sources`;
  ctx.fillText(srcText, metaX, metaY);
  metaX += ctx.measureText(srcText).width;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText("  ·  ", metaX, metaY);
  metaX += ctx.measureText("  ·  ").width;
  ctx.fillStyle = leanColor(lean);
  ctx.fillText(leanLabel(lean), metaX, metaY);

  /* ═══ BAND B: Spectrum Strip (340-390) ═══ */

  const specY = 340;
  const specH = 24;
  const specLeft = 48;
  const specRight = 1152;
  const specW = specRight - specLeft;

  /* Gradient bar */
  const specGrad = ctx.createLinearGradient(specLeft, 0, specRight, 0);
  specGrad.addColorStop(0, "#4A6FA5");
  specGrad.addColorStop(0.14, "#6B8DB5");
  specGrad.addColorStop(0.28, "#8FAAB8");
  specGrad.addColorStop(0.42, "#9A9590");
  specGrad.addColorStop(0.57, "#C09A8A");
  specGrad.addColorStop(0.71, "#B07060");
  specGrad.addColorStop(1, "#964A3A");
  ctx.fillStyle = specGrad;
  roundRect(ctx, specLeft, specY, specW, specH, 3);
  ctx.fill();

  /* Marker dot on spectrum */
  const dotX = specLeft + Math.max(8, Math.min(specW - 8, (lean / 100) * specW));
  const dotCy = specY + specH / 2;
  ctx.beginPath();
  ctx.arc(dotX, dotCy, 8, 0, Math.PI * 2);
  ctx.fillStyle = FG_PRIMARY;
  ctx.fill();
  ctx.strokeStyle = BG;
  ctx.lineWidth = 2.5;
  ctx.stroke();
  /* Outer ring for visibility */
  ctx.beginPath();
  ctx.arc(dotX, dotCy, 9.5, 0, Math.PI * 2);
  ctx.strokeStyle = FG_MUTED;
  ctx.lineWidth = 0.5;
  ctx.stroke();

  /* Zone labels below spectrum */
  ctx.font = `600 9px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.textAlign = "center";
  const zoneLabels = ["FL", "L", "CL", "C", "CR", "R", "FR"];
  const zoneW = specW / 7;
  zoneLabels.forEach((lbl, i) => {
    ctx.fillText(lbl, specLeft + (i + 0.5) * zoneW, specY + specH + 16);
  });
  ctx.textAlign = "left";

  /* ═══ BAND C: 6-Axis Scorecard (400-570) ═══ */

  const axes = [
    { label: "LEAN",    score: lean,    color: leanColor(lean),       desc: leanLabel(lean) },
    { label: "RIGOR",   score: rigor,   color: rigorColor(rigor),     desc: rigorLabel(rigor) },
    { label: "TONE",    score: sense,   color: senseColor(sense),     desc: senseLabel(sense) },
    { label: "FRAMING", score: framing, color: framingColor(framing), desc: framingDescriptor(framing) },
    { label: "OPINION", score: opinion, color: opinionColor(opinion), desc: opinionDescriptor(opinion) },
  ];

  const scoreStartY = 410;
  const scoreRowH = 28;
  const labelRightX = 140;
  const trackX = 160;
  const trackW = 440;
  const trackH = 6;
  const trackR = 3;
  const dotR = 6;

  axes.forEach((axis, i) => {
    const rowY = scoreStartY + i * scoreRowH;

    /* Axis label */
    ctx.font = `600 11px ${META}`;
    ctx.fillStyle = FG_TERTIARY;
    ctx.textAlign = "right";
    ctx.fillText(axis.label, labelRightX, rowY + 4);
    ctx.textAlign = "left";

    /* Track background */
    ctx.fillStyle = BG_TRACK;
    roundRect(ctx, trackX, rowY - 3, trackW, trackH, trackR);
    ctx.fill();

    /* Track fill */
    const fillW = Math.max(3, (axis.score / 100) * trackW);
    ctx.globalAlpha = 0.6;
    ctx.fillStyle = axis.color;
    roundRect(ctx, trackX, rowY - 3, fillW, trackH, trackR);
    ctx.fill();
    ctx.globalAlpha = 1;

    /* Marker dot */
    const mX = trackX + (axis.score / 100) * trackW;
    ctx.beginPath();
    ctx.arc(mX, rowY, dotR, 0, Math.PI * 2);
    ctx.fillStyle = axis.color;
    ctx.fill();
    ctx.strokeStyle = BG;
    ctx.lineWidth = 2;
    ctx.stroke();

    /* Numeric score */
    ctx.font = `600 12px ${DATA}`;
    ctx.fillStyle = axis.color;
    ctx.fillText(String(axis.score), trackX + trackW + 14, rowY + 4);

    /* Descriptor */
    ctx.font = `400 11px ${STRUCTURAL}`;
    ctx.fillStyle = FG_MUTED;
    ctx.fillText(axis.desc, trackX + trackW + 50, rowY + 4);
  });

  /* ═══ Right-side brand watermark ═══ */
  ctx.globalAlpha = 0.35;
  ctx.textAlign = "left";
  /* Measure both parts to position right-aligned from x=1130 */
  ctx.font = `700 28px ${EDITORIAL}`;
  const brandVoidW = ctx.measureText("void").width;
  ctx.font = `400 28px ${DATA}`;
  const brandNewsW = ctx.measureText(" --news").width;
  const brandStartX = 1130 - brandVoidW - brandNewsW;
  ctx.font = `700 28px ${EDITORIAL}`;
  ctx.fillStyle = FG_SECONDARY;
  ctx.fillText("void", brandStartX, 490);
  ctx.font = `400 28px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.fillText(" --news", brandStartX + brandVoidW, 490);
  /* Subtitle */
  ctx.textAlign = "right";
  ctx.font = `400 14px ${DATA}`;
  ctx.fillStyle = FG_MUTED;
  ctx.globalAlpha = 0.3;
  ctx.fillText("evidence card", 1130, 514);
  ctx.globalAlpha = 1;
  ctx.textAlign = "left";

  /* ═══ BAND D: Footer (580-630) ═══ */

  /* Footer rule */
  ctx.strokeStyle = RULE_COLOR;
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(48, 580);
  ctx.lineTo(1152, 580);
  ctx.stroke();

  /* Footer text */
  ctx.font = `500 10px ${META}`;
  ctx.fillStyle = FG_FAINT;
  ctx.textAlign = "left";
  ctx.fillText("6-AXIS BIAS ANALYSIS", 48, 608);
  ctx.textAlign = "center";
  ctx.fillText("·", 600, 608);
  ctx.textAlign = "right";
  ctx.fillText("419 SOURCES ACROSS THE SPECTRUM", 1152, 608);
  ctx.textAlign = "left";

  /* ═══ Export as PNG blob ═══ */
  return new Promise<Blob>((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (blob) resolve(blob);
        else reject(new Error("Canvas toBlob returned null"));
      },
      "image/png",
    );
  });
}
