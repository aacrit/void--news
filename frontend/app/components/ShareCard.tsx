"use client";

/**
 * ShareCard — "The Evidence Card"
 *
 * 1200x630 shareable social media card rendering per-article 6-axis bias analysis.
 * Pure inline styles (self-contained for potential SVG export). Always renders on
 * a dark (#1C1A17) background — no theme switching.
 *
 * Fonts referenced by CSS variable name in comments but rendered with font-family
 * strings for portability.
 */

import { tiltLabel, tiltLabelAbbr, senseLabel, rigorLabel } from "../lib/biasColors";

/* ── Dark-mode bias colors (hardcoded — card always renders dark) ────────── */

const LEAN_COLORS: Record<string, string> = {
  "far-left":     "#5078AE",
  "left":         "#6490B8",
  "center-left":  "#6BA0BC",
  "center":       "#4D9B6A",
  "center-right": "#C07A6A",
  "right":        "#C56D5C",
  "far-right":    "#B25748",
};

const SPECTRUM_GRADIENT = `linear-gradient(to right, ${LEAN_COLORS["far-left"]}, ${LEAN_COLORS["left"]} 14%, ${LEAN_COLORS["center-left"]} 28%, ${LEAN_COLORS["center"]} 42%, ${LEAN_COLORS["center-right"]} 57%, ${LEAN_COLORS["right"]} 71%, ${LEAN_COLORS["far-right"]})`;

const ZONE_LABELS = ["FL", "L", "CL", "C", "CR", "R", "FR"];

/* ── Color computation (dark-mode only, no CSS var lookups) ─────────────── */

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

function cardLeanColor(v: number): string {
  if (v <= 14) return LEAN_COLORS["far-left"];
  if (v <= 20) return lerpHex(LEAN_COLORS["far-left"], LEAN_COLORS["left"], (v - 14) / 6);
  if (v <= 35) return lerpHex(LEAN_COLORS["left"], LEAN_COLORS["center-left"], (v - 20) / 15);
  if (v <= 45) return LEAN_COLORS["center-left"];
  if (v <= 55) return LEAN_COLORS["center"];
  if (v <= 65) return LEAN_COLORS["center-right"];
  if (v <= 80) return lerpHex(LEAN_COLORS["center-right"], LEAN_COLORS["right"], (v - 65) / 15);
  if (v <= 86) return lerpHex(LEAN_COLORS["right"], LEAN_COLORS["far-right"], (v - 80) / 6);
  return LEAN_COLORS["far-right"];
}

/** Sensationalism: green (low) → yellow (mid) → red (high) */
function cardSenseColor(v: number): string {
  if (v <= 50) return lerpHex("#22C55E", "#EAB308", v / 50);
  return lerpHex("#EAB308", "#EF4444", (v - 50) / 50);
}

/** Factual rigor: red (low) → yellow (mid) → green (high) */
function cardRigorColor(v: number): string {
  if (v <= 50) return lerpHex("#EF4444", "#EAB308", v / 50);
  return lerpHex("#EAB308", "#22C55E", (v - 50) / 50);
}

/** Framing: same scale as sensationalism (low=good, high=bad) */
function cardFramingColor(v: number): string {
  return cardSenseColor(v);
}

/** Opinion: reporting=blue, analysis=purple, opinion=orange */
function cardOpinionColor(v: number): string {
  if (v <= 33) return lerpHex("#6490B8", "#8B5CF6", v / 33);
  if (v <= 66) return lerpHex("#8B5CF6", "#F97316", (v - 33) / 33);
  return "#F97316";
}

/** Agreement: green (high agreement/low score) → yellow → red (high disagreement) */
function cardAgreementColor(v: number): string {
  if (v <= 50) return lerpHex("#22C55E", "#EAB308", v / 50);
  return lerpHex("#EAB308", "#EF4444", (v - 50) / 50);
}

/* ── Descriptors ────────────────────────────────────────────────────────── */

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

function agreementDescriptor(v: number): string {
  if (v <= 25) return "Consensus";
  if (v <= 50) return "Mostly agree";
  if (v <= 75) return "Mixed";
  return "Divergent";
}

/* ── Props ──────────────────────────────────────────────────────────────── */

export interface ShareCardProps {
  headline: string;
  sourceName: string;
  sourceCount: number;
  category: string;
  publishedAt: string;
  scores: {
    politicalLean: number;
    sensationalism: number;
    opinionFact: number;
    factualRigor: number;
    framing: number;
  };
  agreement?: number;
  divergenceFlag?: string;
}

/* ── Shared inline style constants ──────────────────────────────────────── */

const BG = "#1C1A17";
const BG_TRACK = "#252320";
const BG_BADGE = "#252320";
const FG_PRIMARY = "#EDE8E0";
const FG_SECONDARY = "#B8B0A5";
const FG_TERTIARY = "#A09890";
const FG_MUTED = "#686260";
const FG_FAINT = "#5A5550";
const RULE_COLOR = "#3A3530";

/* Font family strings (match CSS vars, not importing next/font here) */
const FONT_EDITORIAL = "'Playfair Display', Georgia, serif";
const FONT_STRUCTURAL = "'Inter', system-ui, sans-serif";
const FONT_META = "'Barlow Condensed', 'Arial Narrow', sans-serif";
const FONT_DATA = "'IBM Plex Mono', 'Courier New', monospace";

/* ── Bar axis config ────────────────────────────────────────────────────── */

interface AxisConfig {
  key: string;
  label: string;
  score: number;
  color: string;
  descriptor: string;
}

function buildAxes(scores: ShareCardProps["scores"], agreement?: number): AxisConfig[] {
  const axes: AxisConfig[] = [
    {
      key: "lean",
      label: "LEAN",
      score: scores.politicalLean,
      color: cardLeanColor(scores.politicalLean),
      descriptor: tiltLabel(scores.politicalLean),
    },
    {
      key: "rigor",
      label: "RIGOR",
      score: scores.factualRigor,
      color: cardRigorColor(scores.factualRigor),
      descriptor: rigorLabel(scores.factualRigor),
    },
    {
      key: "tone",
      label: "TONE",
      score: scores.sensationalism,
      color: cardSenseColor(scores.sensationalism),
      descriptor: senseLabel(scores.sensationalism),
    },
    {
      key: "framing",
      label: "FRAMING",
      score: scores.framing,
      color: cardFramingColor(scores.framing),
      descriptor: framingDescriptor(scores.framing),
    },
    {
      key: "opinion",
      label: "OPINION",
      score: scores.opinionFact,
      color: cardOpinionColor(scores.opinionFact),
      descriptor: opinionDescriptor(scores.opinionFact),
    },
    {
      key: "agreement",
      label: "AGREEMENT",
      score: agreement ?? 50,
      color: cardAgreementColor(agreement ?? 50),
      descriptor: agreementDescriptor(agreement ?? 50),
    },
  ];
  return axes;
}

/* ── Component ──────────────────────────────────────────────────────────── */

export default function ShareCard({
  headline,
  sourceName,
  sourceCount,
  category,
  scores,
  agreement,
}: ShareCardProps) {
  const axes = buildAxes(scores, agreement);

  /* Clamp headline to ~3 lines at 42px — roughly 120 chars */
  const displayHeadline =
    headline.length > 120 ? headline.slice(0, 117) + "..." : headline;

  return (
    <div
      role="img"
      aria-label={`Evidence card for: ${headline}`}
      style={{
        width: 1200,
        height: 630,
        backgroundColor: BG,
        border: `1px solid ${RULE_COLOR}`,
        boxSizing: "border-box",
        position: "relative",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* ═══ BAND A: Headline + Meta (0–340) ═══ */}
      <div
        style={{
          flex: "0 0 340px",
          padding: "28px 40px 16px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          boxSizing: "border-box",
        }}
      >
        {/* Top row: brand + source count badge */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          {/* Brand mark */}
          <div style={{ display: "flex", alignItems: "baseline", gap: 2 }}>
            <span
              style={{
                fontFamily: FONT_EDITORIAL,
                fontSize: 18,
                fontWeight: 700,
                color: FG_SECONDARY,
                letterSpacing: "-0.01em",
              }}
            >
              void
            </span>
            <span
              style={{
                fontFamily: FONT_DATA,
                fontSize: 18,
                fontWeight: 400,
                color: FG_SECONDARY,
              }}
            >
              {" "}--news
            </span>
          </div>

          {/* Source count badge */}
          <div
            style={{
              fontFamily: FONT_DATA,
              fontSize: 13,
              color: FG_TERTIARY,
              backgroundColor: BG_BADGE,
              padding: "4px 12px",
              borderRadius: 4,
              letterSpacing: "0.02em",
            }}
          >
            {sourceCount} sources
          </div>
        </div>

        {/* Headline */}
        <h2
          style={{
            fontFamily: FONT_EDITORIAL,
            fontSize: 42,
            fontWeight: 700,
            color: FG_PRIMARY,
            lineHeight: 1.18,
            margin: 0,
            maxWidth: 1000,
            letterSpacing: "-0.01em",
          }}
        >
          {displayHeadline}
        </h2>

        {/* Meta line */}
        <div
          style={{
            fontFamily: FONT_STRUCTURAL,
            fontSize: 15,
            color: FG_TERTIARY,
            display: "flex",
            alignItems: "center",
            gap: 8,
            letterSpacing: "0.01em",
          }}
        >
          <span>{sourceName}</span>
          <span style={{ color: FG_MUTED }}>·</span>
          <span>{sourceCount} sources</span>
          <span style={{ color: FG_MUTED }}>·</span>
          <span style={{ color: cardLeanColor(scores.politicalLean) }}>
            {tiltLabel(scores.politicalLean)}
          </span>
          <span style={{ color: FG_MUTED }}>·</span>
          <span
            style={{
              fontFamily: FONT_META,
              fontSize: 13,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: FG_MUTED,
            }}
          >
            {category}
          </span>
        </div>
      </div>

      {/* ═══ BAND B: Spectrum Strip (340–390) ═══ */}
      <div
        style={{
          flex: "0 0 50px",
          position: "relative",
          boxSizing: "border-box",
        }}
      >
        {/* Gradient bar */}
        <div
          style={{
            height: 24,
            marginLeft: 40,
            marginRight: 40,
            borderRadius: 3,
            background: SPECTRUM_GRADIENT,
            position: "relative",
          }}
        >
          {/* Marker dot at lean position */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: `${scores.politicalLean}%`,
              transform: "translate(-50%, -50%)",
              width: 14,
              height: 14,
              borderRadius: "50%",
              backgroundColor: FG_PRIMARY,
              border: `2.5px solid ${BG}`,
              boxShadow: `0 0 0 1px ${FG_MUTED}`,
            }}
          />
        </div>

        {/* Zone labels */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            marginLeft: 40,
            marginRight: 40,
            marginTop: 4,
          }}
        >
          {ZONE_LABELS.map((label) => (
            <span
              key={label}
              style={{
                fontFamily: FONT_META,
                fontSize: 9,
                color: FG_FAINT,
                textTransform: "uppercase",
                letterSpacing: "0.08em",
                flex: 1,
                textAlign: "center",
              }}
            >
              {label}
            </span>
          ))}
        </div>
      </div>

      {/* ═══ BAND C: 6-Axis Scorecard (390–580) ═══ */}
      <div
        style={{
          flex: "1 1 auto",
          padding: "12px 40px 0",
          display: "flex",
          boxSizing: "border-box",
        }}
      >
        {/* Left: axis bars */}
        <div
          style={{
            flex: "1 1 auto",
            display: "flex",
            flexDirection: "column",
            gap: 12,
            justifyContent: "center",
          }}
        >
          {axes.map((axis) => (
            <div
              key={axis.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
              }}
            >
              {/* Label */}
              <span
                style={{
                  fontFamily: FONT_META,
                  fontSize: 12,
                  fontWeight: 500,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  color: FG_TERTIARY,
                  width: 90,
                  flexShrink: 0,
                  textAlign: "right",
                }}
              >
                {axis.label}
              </span>

              {/* Track + fill + marker */}
              <div
                style={{
                  position: "relative",
                  width: 400,
                  height: 6,
                  backgroundColor: BG_TRACK,
                  borderRadius: 3,
                  flexShrink: 0,
                }}
              >
                {/* Fill */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    height: "100%",
                    width: `${axis.score}%`,
                    backgroundColor: axis.color,
                    borderRadius: 3,
                    opacity: 0.6,
                  }}
                />
                {/* Marker dot */}
                <div
                  style={{
                    position: "absolute",
                    top: "50%",
                    left: `${axis.score}%`,
                    transform: "translate(-50%, -50%)",
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    backgroundColor: axis.color,
                    border: `2px solid ${BG}`,
                  }}
                />
              </div>

              {/* Score */}
              <span
                style={{
                  fontFamily: FONT_DATA,
                  fontSize: 12,
                  color: axis.color,
                  width: 28,
                  textAlign: "right",
                  flexShrink: 0,
                }}
              >
                {axis.score}
              </span>

              {/* Descriptor */}
              <span
                style={{
                  fontFamily: FONT_STRUCTURAL,
                  fontSize: 11,
                  color: FG_MUTED,
                  whiteSpace: "nowrap",
                }}
              >
                {axis.descriptor}
              </span>
            </div>
          ))}
        </div>

        {/* Right: brand wordmark */}
        <div
          style={{
            flex: "0 0 auto",
            display: "flex",
            flexDirection: "column",
            alignItems: "flex-end",
            justifyContent: "flex-end",
            paddingBottom: 8,
            paddingLeft: 32,
          }}
        >
          <div style={{ display: "flex", alignItems: "baseline", gap: 2 }}>
            <span
              style={{
                fontFamily: FONT_EDITORIAL,
                fontSize: 22,
                fontWeight: 700,
                color: FG_SECONDARY,
                letterSpacing: "-0.01em",
              }}
            >
              void
            </span>
            <span
              style={{
                fontFamily: FONT_DATA,
                fontSize: 22,
                fontWeight: 400,
                color: FG_SECONDARY,
              }}
            >
              {" "}--news
            </span>
          </div>
          <span
            style={{
              fontFamily: FONT_DATA,
              fontSize: 13,
              color: FG_MUTED,
              marginTop: 4,
              letterSpacing: "0.02em",
            }}
          >
            voidnews.org
          </span>
        </div>
      </div>

      {/* ═══ BAND D: Footer (580–630) ═══ */}
      <div
        style={{
          flex: "0 0 50px",
          borderTop: `1px solid ${RULE_COLOR}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "0 40px",
          boxSizing: "border-box",
        }}
      >
        <span
          style={{
            fontFamily: FONT_META,
            fontSize: 10,
            color: FG_FAINT,
            textTransform: "uppercase",
            letterSpacing: "0.12em",
          }}
        >
          6-axis bias analysis&nbsp;&nbsp;·&nbsp;&nbsp;1,013 sources across the spectrum
        </span>
      </div>
    </div>
  );
}
