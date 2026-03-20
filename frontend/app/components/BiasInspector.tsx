"use client";

import { useState, useId, useEffect, useRef } from "react";
import { X } from "@phosphor-icons/react";
import type {
  StorySource,
  LeanRationale,
  CoverageRationale,
  SensationalismRationale,
  FramingRationale,
} from "../lib/types";

/* ---------------------------------------------------------------------------
   BiasInspector — "Score breakdown" pop-out panel

   Secondary panel that slides out from the Deep Dive panel. Shows cluster-
   level aggregate bias scores (averaged across all sources in the cluster)
   for 4 axes: Political Lean, Sensationalism, Factual Rigor, Framing.

   Opinion vs. Reporting is excluded — the app already surfaces that via
   the News/Opinion content-type tabs.

   Exports:
     BiasInspectorTrigger — the trigger button rendered inside Deep Dive
     BiasInspectorPanel   — the pop-out drawer (conditionally rendered)
   --------------------------------------------------------------------------- */

/* ── Color helpers — reads CSS variables for dark mode awareness ────────── */

let biColorCache: Record<string, string> | null = null;
const BI_SSR: Record<string, string> = {
  "--bias-left": "#3B82F6",
  "--bias-center": "#9CA3AF",
  "--bias-right": "#EF4444",
  "--sense-low": "#22C55E",
  "--sense-medium": "#EAB308",
  "--sense-high": "#EF4444",
  "--rigor-high": "#22C55E",
  "--rigor-medium": "#EAB308",
  "--rigor-low": "#EF4444",
};

function biVars(): Record<string, string> {
  if (biColorCache) return biColorCache;
  if (typeof document === "undefined") return BI_SSR;
  const s = getComputedStyle(document.documentElement);
  biColorCache = {};
  for (const v of Object.keys(BI_SSR))
    biColorCache[v] = s.getPropertyValue(v).trim() || BI_SSR[v];
  return biColorCache;
}

if (typeof window !== "undefined") {
  new MutationObserver((ms) => {
    for (const m of ms)
      if (m.type === "attributes" && m.attributeName === "data-mode")
        biColorCache = null;
  }).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-mode"],
  });
}

function lerpHex(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff,
    ag = (ah >> 8) & 0xff,
    ab = ah & 0xff;
  const br = (bh >> 16) & 0xff,
    bg = (bh >> 8) & 0xff,
    bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

function getLeanColor(v: number): string {
  const c = biVars();
  if (v <= 50) return lerpHex(c["--bias-left"], c["--bias-center"], v / 50);
  return lerpHex(c["--bias-center"], c["--bias-right"], (v - 50) / 50);
}

function getSenseColor(v: number): string {
  const c = biVars();
  if (v <= 50) return lerpHex(c["--sense-low"], c["--sense-medium"], v / 50);
  return lerpHex(c["--sense-medium"], c["--sense-high"], (v - 50) / 50);
}

function getRigorColor(v: number): string {
  const c = biVars();
  if (v <= 50) return lerpHex(c["--rigor-low"], c["--rigor-medium"], v / 50);
  return lerpHex(c["--rigor-medium"], c["--rigor-high"], (v - 50) / 50);
}

function getFramingColor(v: number): string {
  return getSenseColor(v);
}

function getConfidenceColor(pct: number): string {
  return getRigorColor(pct);
}

/* ── Label helpers ──────────────────────────────────────────────────────── */

function leanLabel(v: number): string {
  if (v <= 20) return "Far Left";
  if (v <= 35) return "Left";
  if (v <= 45) return "Center-Left";
  if (v <= 55) return "Center";
  if (v <= 65) return "Center-Right";
  if (v <= 80) return "Right";
  return "Far Right";
}

function senseLabel(v: number): string {
  if (v <= 25) return "Measured";
  if (v <= 50) return "Moderate";
  if (v <= 75) return "Elevated";
  return "Inflammatory";
}

function rigorLabel(v: number): string {
  if (v >= 75) return "High rigor";
  if (v >= 50) return "Good rigor";
  if (v >= 25) return "Moderate rigor";
  return "Low rigor";
}

function framingLabel(v: number): string {
  if (v <= 25) return "Neutral";
  if (v <= 50) return "Light framing";
  if (v <= 75) return "Moderate framing";
  return "Heavy framing";
}

/* ── Cluster-level averages ─────────────────────────────────────────────── */

interface ClusterAverages {
  lean: number;
  sensationalism: number;
  factualRigor: number;
  framing: number;
  confidence: number;
  leanRationale?: LeanRationale;
  sensationalismRationale?: SensationalismRationale;
  coverageRationale?: CoverageRationale;
  framingRationale?: FramingRationale;
}

function avg(values: number[]): number {
  if (values.length === 0) return 50;
  return Math.round(values.reduce((a, b) => a + b, 0) / values.length);
}

function avgFloat(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
}

function computeClusterAverages(sources: StorySource[]): ClusterAverages {
  const valid = sources.filter((s) => s.biasScores != null);
  if (valid.length === 0) {
    return {
      lean: 50,
      sensationalism: 30,
      factualRigor: 60,
      framing: 30,
      confidence: 0.5,
    };
  }

  const lean = avg(valid.map((s) => s.biasScores.politicalLean));
  const sensationalism = avg(valid.map((s) => s.biasScores.sensationalism));
  const factualRigor = avg(valid.map((s) => s.biasScores.factualRigor));
  const framing = avg(valid.map((s) => s.biasScores.framing));
  const confidence = avgFloat(
    valid.map((s) =>
      typeof s.confidence === "number"
        ? s.confidence
        : s.lensData
          ? s.lensData.coverage / 100
          : 0.5
    )
  );

  // Aggregate rationales: average numeric fields, merge arrays
  const leanRats = valid
    .map((s) => s.lensData?.leanRationale)
    .filter(Boolean) as LeanRationale[];
  const senseRats = valid
    .map((s) => s.lensData?.sensationalismRationale)
    .filter(Boolean) as SensationalismRationale[];
  const coverageRats = valid
    .map((s) => s.lensData?.coverageRationale)
    .filter(Boolean) as CoverageRationale[];
  const framingRats = valid
    .map((s) => s.lensData?.framingRationale)
    .filter(Boolean) as FramingRationale[];

  const leanRationale: LeanRationale | undefined =
    leanRats.length > 0
      ? {
          keywordScore: avg(leanRats.map((r) => r.keywordScore)),
          framingShift: avgFloat(leanRats.map((r) => r.framingShift)),
          entityShift: avgFloat(leanRats.map((r) => r.entityShift)),
          sourceBaseline: avg(leanRats.map((r) => r.sourceBaseline)),
          topLeftKeywords: dedupeStrings(leanRats.flatMap((r) => r.topLeftKeywords ?? [])).slice(0, 6),
          topRightKeywords: dedupeStrings(leanRats.flatMap((r) => r.topRightKeywords ?? [])).slice(0, 6),
          framingPhrasesFound: dedupeStrings(leanRats.flatMap((r) => r.framingPhrasesFound ?? [])).slice(0, 5),
          entitySentiments: mergeEntitySentiments(leanRats.map((r) => r.entitySentiments ?? {})),
        }
      : undefined;

  const sensationalismRationale: SensationalismRationale | undefined =
    senseRats.length > 0
      ? {
          headlineScore: avg(senseRats.map((r) => r.headlineScore)),
          bodyScore: avg(senseRats.map((r) => r.bodyScore)),
          clickbaitSignals: Math.round(avgFloat(senseRats.map((r) => r.clickbaitSignals))),
          superlativeDensity: avgFloat(senseRats.map((r) => r.superlativeDensity)),
          urgencyDensity: avgFloat(senseRats.map((r) => r.urgencyDensity)),
          hyperboleDensity: avgFloat(senseRats.map((r) => r.hyperboleDensity)),
          measuredDensity: avgFloat(senseRats.map((r) => r.measuredDensity)),
        }
      : undefined;

  const coverageRationale: CoverageRationale | undefined =
    coverageRats.length > 0
      ? {
          factualRigor: avg(coverageRats.map((r) => r.factualRigor)),
          namedSourcesCount: Math.round(avgFloat(coverageRats.map((r) => r.namedSourcesCount))),
          orgCitationsCount: Math.round(avgFloat(coverageRats.map((r) => r.orgCitationsCount))),
          dataPointsCount: Math.round(avgFloat(coverageRats.map((r) => r.dataPointsCount))),
          directQuotesCount: Math.round(avgFloat(coverageRats.map((r) => r.directQuotesCount))),
          vagueSourcesCount: Math.round(avgFloat(coverageRats.map((r) => r.vagueSourcesCount))),
          specificityRatio: avgFloat(coverageRats.map((r) => r.specificityRatio)),
        }
      : undefined;

  const framingRationale: FramingRationale | undefined =
    framingRats.length > 0
      ? {
          connotationScore: avg(framingRats.map((r) => r.connotationScore)),
          keywordEmphasisScore: avg(framingRats.map((r) => r.keywordEmphasisScore)),
          omissionScore: avg(framingRats.map((r) => r.omissionScore)),
          headlineBodyDivergence: avg(framingRats.map((r) => r.headlineBodyDivergence)),
          passiveVoiceScore: avg(framingRats.map((r) => r.passiveVoiceScore)),
          hasClusterContext: framingRats.some((r) => r.hasClusterContext),
        }
      : undefined;

  return {
    lean,
    sensationalism,
    factualRigor,
    framing,
    confidence,
    leanRationale,
    sensationalismRationale,
    coverageRationale,
    framingRationale,
  };
}

function dedupeStrings(arr: string[]): string[] {
  return [...new Set(arr)];
}

function mergeEntitySentiments(
  maps: Record<string, number>[]
): Record<string, number> {
  const merged: Record<string, number[]> = {};
  for (const m of maps) {
    for (const [entity, sentiment] of Object.entries(m)) {
      if (!merged[entity]) merged[entity] = [];
      merged[entity].push(sentiment);
    }
  }
  const result: Record<string, number> = {};
  for (const [entity, values] of Object.entries(merged)) {
    result[entity] = avgFloat(values);
  }
  // Return top 8 by absolute sentiment magnitude
  return Object.fromEntries(
    Object.entries(result)
      .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
      .slice(0, 8)
  );
}

/* ── Mini score bar ─────────────────────────────────────────────────────── */

interface MiniBarProps {
  value: number;
  color: string;
  max?: number;
  animate?: boolean;
}

function MiniBar({ value, color, max = 100, animate = false }: MiniBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="bi-minibar">
      <div className="bi-minibar__track">
        <div
          className={`bi-minibar__fill${animate ? " bi-minibar__fill--animate" : ""}`}
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* ── Gradient bar for Tier 1 axis summary ───────────────────────────────── */

interface GradientBarProps {
  value: number;
  /** CSS gradient string left→right */
  gradient: string;
  color: string;
}

function GradientBar({ value, gradient, color }: GradientBarProps) {
  const pct = Math.max(2, Math.min(98, value));
  return (
    <div className="bi-gradient-bar">
      <div className="bi-gradient-bar__track" style={{ background: gradient }}>
        <div
          className="bi-gradient-bar__marker"
          style={{ left: `${pct}%`, backgroundColor: color }}
          aria-hidden="true"
        />
      </div>
    </div>
  );
}

/* ── Sub-score row (label + thin bar + value) ───────────────────────────── */

interface SubScoreProps {
  label: string;
  value: number;
  color: string;
  max?: number;
  isPct?: boolean;
  suffix?: string;
}

function SubScore({
  label,
  value,
  color,
  max = 100,
  isPct,
  suffix,
}: SubScoreProps) {
  const displayVal = isPct
    ? `${Math.round(value * 100)}%`
    : `${Math.round(value)}${suffix ?? ""}`;
  const barVal = isPct ? value * 100 : value;

  return (
    <div className="bi-subscore">
      <span className="bi-subscore__label">{label}</span>
      <div className="bi-subscore__bar-wrap">
        <div className="bi-subscore__track">
          <div
            className="bi-subscore__fill"
            style={{
              width: `${Math.max(0, Math.min(100, (barVal / max) * 100))}%`,
              backgroundColor: color,
            }}
          />
        </div>
      </div>
      <span className="bi-subscore__value" style={{ color }}>
        {displayVal}
      </span>
    </div>
  );
}

/* ── Density mini-chart (4 bars side by side for sensationalism) ────────── */

interface DensityChartProps {
  superlative: number;
  urgency: number;
  hyperbole: number;
  measured: number;
}

function DensityChart({
  superlative,
  urgency,
  hyperbole,
  measured,
}: DensityChartProps) {
  const max = Math.max(superlative, urgency, hyperbole, measured, 1);
  const bars = [
    { label: "Supr.", value: superlative, color: "#EF4444" },
    { label: "Urgn.", value: urgency, color: "#F97316" },
    { label: "Hypr.", value: hyperbole, color: "#EAB308" },
    { label: "Mesr.", value: measured, color: "#22C55E" },
  ];
  return (
    <div className="bi-density-chart" aria-label="Word density comparison chart">
      {bars.map(({ label, value, color }) => (
        <div key={label} className="bi-density-chart__col">
          <div className="bi-density-chart__bar-wrap">
            <div
              className="bi-density-chart__bar"
              style={{
                height: `${Math.round((value / max) * 100)}%`,
                backgroundColor: color,
              }}
            />
          </div>
          <span className="bi-density-chart__label">{label}</span>
          <span className="bi-density-chart__value" style={{ color }}>
            {(value ?? 0).toFixed(1)}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ── Evidence tally (factual rigor) ────────────────────────────────────── */

interface TallyProps {
  items: { label: string; value: number; positive: boolean }[];
}

function EvidenceTally({ items }: TallyProps) {
  return (
    <div className="bi-tally">
      {items.map(({ label, value, positive }) => (
        <div key={label} className="bi-tally__item">
          <span
            className="bi-tally__count"
            style={{
              color: positive ? "var(--rigor-high)" : "var(--rigor-low)",
            }}
          >
            {value}
          </span>
          <span className="bi-tally__label">{label}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Tag chip ───────────────────────────────────────────────────────────── */

function Tag({
  children,
  color,
}: {
  children: React.ReactNode;
  color?: string;
}) {
  return (
    <span
      className="bi-tag"
      style={color ? { borderColor: color, color } : undefined}
    >
      {children}
    </span>
  );
}

/* ── Axis row component ─────────────────────────────────────────────────── */

interface AxisRowProps {
  axisId: string;
  label: string;
  score: number;
  color: string;
  scoreLabel: string;
  gradient: string;
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  hasRationale: boolean;
  /** Stagger index for entrance animation delay */
  staggerIndex: number;
  contentVisible: boolean;
}

function AxisRow({
  axisId,
  label,
  score,
  color,
  scoreLabel,
  gradient,
  isExpanded,
  onToggle,
  children,
  hasRationale,
  staggerIndex,
  contentVisible,
}: AxisRowProps) {
  const headingId = `${axisId}-heading`;
  const contentId = `${axisId}-content`;
  const staggerDelay = staggerIndex * 60;

  return (
    <div
      className={`bi-axis bi-panel__axis-stagger${contentVisible ? " bi-panel__axis-stagger--visible" : ""}`}
      style={{ transitionDelay: contentVisible ? `${staggerDelay}ms` : "0ms" }}
      role="region"
      aria-labelledby={headingId}
    >
      <button
        className={`bi-axis__header${isExpanded ? " bi-axis__header--expanded" : ""}`}
        aria-expanded={isExpanded}
        aria-controls={hasRationale ? contentId : undefined}
        onClick={onToggle}
        disabled={!hasRationale}
        id={headingId}
      >
        {/* Left: axis name + gradient bar */}
        <div className="bi-axis__left">
          <span className="bi-axis__name">{label}</span>
          <GradientBar value={score} gradient={gradient} color={color} />
        </div>

        {/* Right: score number + label + caret */}
        <div className="bi-axis__score-row">
          <span className="bi-axis__score" style={{ color }}>
            {score}
          </span>
          <span className="bi-axis__badge" style={{ color }}>
            {scoreLabel}
          </span>
          {hasRationale && (
            <svg
              className={`bi-axis__caret${isExpanded ? " bi-axis__caret--open" : ""}`}
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M2 4L6 8L10 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </div>
      </button>

      {hasRationale && (
        <div
          id={contentId}
          className={`bi-axis__content${isExpanded ? " bi-axis__content--expanded" : ""}`}
          aria-hidden={!isExpanded}
        >
          <div className="bi-axis__rationale">{children}</div>
        </div>
      )}
    </div>
  );
}

/* ── Axis 1: Political Lean ─────────────────────────────────────────────── */

function LeanAxis({
  score,
  rationale,
  isExpanded,
  onToggle,
  axisId,
  staggerIndex,
  contentVisible,
}: {
  score: number;
  rationale?: LeanRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
  staggerIndex: number;
  contentVisible: boolean;
}) {
  const color = getLeanColor(score);
  const gradient =
    "linear-gradient(to right, var(--bias-left), var(--bias-center), var(--bias-right))";

  return (
    <AxisRow
      axisId={axisId}
      label="Political Lean"
      score={score}
      color={color}
      scoreLabel={leanLabel(score)}
      gradient={gradient}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={!!rationale}
      staggerIndex={staggerIndex}
      contentVisible={contentVisible}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore
              label="Keyword score"
              value={rationale.keywordScore}
              color={getLeanColor(rationale.keywordScore)}
            />
            <SubScore
              label="Framing shift"
              value={rationale.framingShift + 15}
              color={getLeanColor(
                ((rationale.framingShift + 15) * 100) / 30
              )}
              max={30}
            />
            <SubScore
              label="Entity shift"
              value={rationale.entityShift + 15}
              color={getLeanColor(
                ((rationale.entityShift + 15) * 100) / 30
              )}
              max={30}
            />
            <SubScore
              label="Source baseline"
              value={rationale.sourceBaseline}
              color={getLeanColor(rationale.sourceBaseline)}
            />
          </div>
          {(rationale.topLeftKeywords?.length > 0 ||
            rationale.topRightKeywords?.length > 0) && (
            <div className="bi-evidence-group">
              {rationale.topLeftKeywords?.length > 0 && (
                <div className="bi-keyword-row">
                  <span
                    className="bi-keyword-row__label"
                    style={{ color: "var(--bias-left)" }}
                  >
                    Left signals
                  </span>
                  <div className="bi-keyword-row__tags">
                    {rationale.topLeftKeywords.slice(0, 5).map((kw) => (
                      <Tag key={kw} color="var(--bias-left)">
                        {kw}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
              {rationale.topRightKeywords?.length > 0 && (
                <div className="bi-keyword-row">
                  <span
                    className="bi-keyword-row__label"
                    style={{ color: "var(--bias-right)" }}
                  >
                    Right signals
                  </span>
                  <div className="bi-keyword-row__tags">
                    {rationale.topRightKeywords.slice(0, 5).map((kw) => (
                      <Tag key={kw} color="var(--bias-right)">
                        {kw}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
          {rationale.framingPhrasesFound?.length > 0 && (
            <div className="bi-evidence-group">
              <span className="bi-evidence-label">Framing phrases detected</span>
              <div className="bi-keyword-row__tags">
                {rationale.framingPhrasesFound.slice(0, 4).map((ph) => (
                  <Tag key={ph}>{ph}</Tag>
                ))}
              </div>
            </div>
          )}
          {rationale.entitySentiments &&
            Object.keys(rationale.entitySentiments).length > 0 && (
              <div className="bi-evidence-group">
                <span className="bi-evidence-label">Entity sentiments</span>
                <div className="bi-entity-grid">
                  {Object.entries(rationale.entitySentiments)
                    .slice(0, 6)
                    .map(([entity, sentiment]) => (
                      <div key={entity} className="bi-entity-item">
                        <span className="bi-entity-item__name">{entity}</span>
                        <span
                          className="bi-entity-item__value"
                          style={{
                            color:
                              sentiment > 0
                                ? "var(--sense-low)"
                                : sentiment < 0
                                  ? "var(--sense-high)"
                                  : "var(--fg-muted)",
                          }}
                        >
                          {sentiment > 0 ? "+" : ""}
                          {sentiment.toFixed(2)}
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            )}
        </>
      )}
    </AxisRow>
  );
}

/* ── Axis 2: Sensationalism ─────────────────────────────────────────────── */

function SensationalismAxis({
  score,
  rationale,
  isExpanded,
  onToggle,
  axisId,
  staggerIndex,
  contentVisible,
}: {
  score: number;
  rationale?: SensationalismRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
  staggerIndex: number;
  contentVisible: boolean;
}) {
  const color = getSenseColor(score);
  const gradient =
    "linear-gradient(to right, var(--sense-low), var(--sense-medium), var(--sense-high))";

  return (
    <AxisRow
      axisId={axisId}
      label="Sensationalism"
      score={score}
      color={color}
      scoreLabel={senseLabel(score)}
      gradient={gradient}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={!!rationale}
      staggerIndex={staggerIndex}
      contentVisible={contentVisible}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore
              label="Headline score"
              value={rationale.headlineScore}
              color={getSenseColor(rationale.headlineScore)}
            />
            <SubScore
              label="Body score"
              value={rationale.bodyScore}
              color={getSenseColor(rationale.bodyScore)}
            />
          </div>
          <div className="bi-evidence-group">
            <span className="bi-evidence-label">Clickbait signals detected</span>
            <span
              className="bi-evidence-value"
              style={{
                color:
                  rationale.clickbaitSignals > 0
                    ? "var(--sense-high)"
                    : "var(--sense-low)",
              }}
            >
              {rationale.clickbaitSignals}
            </span>
          </div>
          <div className="bi-evidence-group">
            <span className="bi-evidence-label">Word density (per 100 words)</span>
            <DensityChart
              superlative={rationale.superlativeDensity}
              urgency={rationale.urgencyDensity}
              hyperbole={rationale.hyperboleDensity}
              measured={rationale.measuredDensity}
            />
          </div>
        </>
      )}
    </AxisRow>
  );
}

/* ── Axis 3: Factual Rigor ──────────────────────────────────────────────── */

function RigorAxis({
  score,
  rationale,
  isExpanded,
  onToggle,
  axisId,
  staggerIndex,
  contentVisible,
}: {
  score: number;
  rationale?: CoverageRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
  staggerIndex: number;
  contentVisible: boolean;
}) {
  const color = getRigorColor(score);
  // Inverted: low rigor = red (left), high rigor = green (right)
  const gradient =
    "linear-gradient(to right, var(--rigor-low), var(--rigor-medium), var(--rigor-high))";

  return (
    <AxisRow
      axisId={axisId}
      label="Factual Rigor"
      score={score}
      color={color}
      scoreLabel={rigorLabel(score)}
      gradient={gradient}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={!!rationale}
      staggerIndex={staggerIndex}
      contentVisible={contentVisible}
    >
      {rationale && (
        <>
          <EvidenceTally
            items={[
              {
                label: "Named sources",
                value: rationale.namedSourcesCount,
                positive: true,
              },
              {
                label: "Org. citations",
                value: rationale.orgCitationsCount,
                positive: true,
              },
              {
                label: "Data points",
                value: rationale.dataPointsCount,
                positive: true,
              },
              {
                label: "Direct quotes",
                value: rationale.directQuotesCount,
                positive: true,
              },
              {
                label: "Vague sources",
                value: rationale.vagueSourcesCount,
                positive: false,
              },
            ]}
          />
          {typeof rationale.specificityRatio === "number" && (
            <div
              className="bi-subscore-group"
              style={{ marginTop: "var(--space-3)" }}
            >
              <SubScore
                label="Specificity ratio"
                value={rationale.specificityRatio}
                color={getRigorColor(rationale.specificityRatio * 100)}
                isPct
              />
            </div>
          )}
        </>
      )}
    </AxisRow>
  );
}

/* ── Axis 4: Framing Analysis ───────────────────────────────────────────── */

function FramingAxis({
  score,
  rationale,
  isExpanded,
  onToggle,
  axisId,
  staggerIndex,
  contentVisible,
}: {
  score: number;
  rationale?: FramingRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
  staggerIndex: number;
  contentVisible: boolean;
}) {
  const color = getFramingColor(score);
  const gradient =
    "linear-gradient(to right, var(--sense-low), var(--sense-medium), var(--sense-high))";

  return (
    <AxisRow
      axisId={axisId}
      label="Framing Analysis"
      score={score}
      color={color}
      scoreLabel={framingLabel(score)}
      gradient={gradient}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={!!rationale}
      staggerIndex={staggerIndex}
      contentVisible={contentVisible}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore
              label="Connotation"
              value={rationale.connotationScore}
              color={getFramingColor(rationale.connotationScore)}
            />
            <SubScore
              label="Keyword emphasis"
              value={rationale.keywordEmphasisScore}
              color={getFramingColor(rationale.keywordEmphasisScore)}
            />
            <SubScore
              label="Omission"
              value={rationale.omissionScore}
              color={getFramingColor(rationale.omissionScore)}
            />
            <SubScore
              label="Headline/body divergence"
              value={rationale.headlineBodyDivergence}
              color={getFramingColor(rationale.headlineBodyDivergence)}
            />
            <SubScore
              label="Passive voice"
              value={rationale.passiveVoiceScore}
              color={getFramingColor(rationale.passiveVoiceScore)}
            />
          </div>
          <div className="bi-evidence-group">
            <Tag
              color={
                rationale.hasClusterContext
                  ? "var(--sense-low)"
                  : "var(--fg-muted)"
              }
            >
              {rationale.hasClusterContext
                ? "Cross-article analysis"
                : "Single-article only"}
            </Tag>
          </div>
        </>
      )}
    </AxisRow>
  );
}

/* ── Confidence meter ───────────────────────────────────────────────────── */

function ConfidenceMeter({
  confidence,
  contentVisible,
}: {
  confidence: number;
  contentVisible: boolean;
}) {
  const pct = Math.round(confidence * 100);
  const color = getConfidenceColor(pct);

  return (
    <div
      className={`bi-confidence bi-panel__axis-stagger${contentVisible ? " bi-panel__axis-stagger--visible" : ""}`}
      style={{ transitionDelay: contentVisible ? "300ms" : "0ms" }}
    >
      <div className="bi-confidence__header">
        <span className="bi-confidence__label">Analysis confidence</span>
        <span className="bi-confidence__value" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div
        className="bi-confidence__track"
        role="meter"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Analysis confidence: ${pct}%`}
      >
        <div
          className="bi-confidence__fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <p className="bi-confidence__note">
        Cluster average: text length, text availability, and signal strength
        relative to source baselines.
      </p>
    </div>
  );
}

/* ── Score dot — tiny colored dot for trigger button preview ────────────── */

function ScoreDot({ color }: { color: string }) {
  return (
    <span
      className="bi-trigger__dot"
      style={{ backgroundColor: color }}
      aria-hidden="true"
    />
  );
}

/* ── Trigger button ─────────────────────────────────────────────────────── */

export interface BiasInspectorTriggerProps {
  sources: StorySource[];
  onClick: () => void;
}

export function BiasInspectorTrigger({
  sources,
  onClick,
}: BiasInspectorTriggerProps) {
  if (sources.length === 0) return null;

  // Compute quick preview colors (no full average needed)
  const valid = sources.filter((s) => s.biasScores != null);
  const leanAvg = valid.length > 0
    ? avg(valid.map((s) => s.biasScores.politicalLean))
    : 50;
  const senseAvg = valid.length > 0
    ? avg(valid.map((s) => s.biasScores.sensationalism))
    : 30;
  const rigorAvg = valid.length > 0
    ? avg(valid.map((s) => s.biasScores.factualRigor))
    : 60;
  const framingAvg = valid.length > 0
    ? avg(valid.map((s) => s.biasScores.framing))
    : 30;

  return (
    <button
      className="bi-trigger"
      onClick={onClick}
      aria-label="Open score breakdown panel"
      aria-haspopup="dialog"
    >
      <div className="bi-trigger__dots" aria-hidden="true">
        <ScoreDot color={getLeanColor(leanAvg)} />
        <ScoreDot color={getSenseColor(senseAvg)} />
        <ScoreDot color={getRigorColor(rigorAvg)} />
        <ScoreDot color={getFramingColor(framingAvg)} />
      </div>
      <span className="bi-trigger__label">Score breakdown</span>
      <svg
        className="bi-trigger__arrow"
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M2 6h8M6 2l4 4-4 4"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}

/* ── Pop-out panel ──────────────────────────────────────────────────────── */

export interface BiasInspectorPanelProps {
  sources: StorySource[];
  onClose: () => void;
  /** Whether the panel is currently open (controls animation) */
  isOpen: boolean;
}

export function BiasInspectorPanel({
  sources,
  onClose,
  isOpen,
}: BiasInspectorPanelProps) {
  const [contentVisible, setContentVisible] = useState(false);
  const [expandedAxes, setExpandedAxes] = useState<Set<string>>(new Set());
  const [isDesktop, setIsDesktop] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const headingId = useId();

  /* ---- Detect desktop for slide direction ------------------------------ */
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);
    function handleChange(e: MediaQueryListEvent) {
      setIsDesktop(e.matches);
    }
    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

  /* ---- Stagger content reveal after panel slides in ------------------- */
  useEffect(() => {
    if (isOpen) {
      // Panel slides in for ~300ms, then content staggers
      const t = setTimeout(() => setContentVisible(true), 200);
      return () => clearTimeout(t);
    } else {
      setContentVisible(false);
    }
  }, [isOpen]);

  /* ---- Focus trap ------------------------------------------------------- */
  useEffect(() => {
    if (!isOpen) return;

    // Focus the panel on open
    const raf = requestAnimationFrame(() => {
      panelRef.current?.focus();
    });

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        e.stopPropagation(); // Don't also close DeepDive
        onClose();
        return;
      }

      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown, true);
    return () => {
      cancelAnimationFrame(raf);
      document.removeEventListener("keydown", handleKeyDown, true);
    };
  }, [isOpen, onClose]);

  function toggleAxis(key: string) {
    setExpandedAxes((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const averages = computeClusterAverages(sources);

  /* ---- Slide transform ------------------------------------------------- */
  // Desktop: slides in from left edge of DeepDive panel (translateX)
  // Mobile: slides up from bottom (translateY)
  const slideTransform = isOpen
    ? "translate(0, 0)"
    : isDesktop
      ? "translateX(-100%)"
      : "translateY(100%)";

  return (
    <>
      {/* Backdrop — dims the rest of the Deep Dive panel */}
      <div
        className="bi-panel__backdrop"
        aria-hidden="true"
        onClick={onClose}
        style={{
          opacity: isOpen ? 1 : 0,
          transition: "opacity 150ms var(--ease-out)",
          pointerEvents: isOpen ? "auto" : "none",
        }}
      />

      {/* Drawer */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={headingId}
        tabIndex={-1}
        className="bi-panel__drawer"
        style={{
          transform: slideTransform,
          transition: "transform 500ms var(--spring)",
        }}
      >
        {/* Header */}
        <header className="bi-panel__header">
          <div
            className={`bi-panel__header-inner bi-panel__axis-stagger${contentVisible ? " bi-panel__axis-stagger--visible" : ""}`}
          >
            <div>
              <h3 id={headingId} className="bi-panel__title">
                Score breakdown
              </h3>
              <p className="bi-panel__subtitle">
                Cluster average across {sources.length}{" "}
                {sources.length === 1 ? "source" : "sources"}
              </p>
            </div>
            <button
              className="bi-panel__close"
              onClick={onClose}
              aria-label="Close score breakdown"
            >
              <X size={18} weight="regular" aria-hidden="true" />
            </button>
          </div>
        </header>

        {/* Scorecard — 4 axes */}
        <div className="bi-panel__body">
          <div
            className="bi-scorecard"
            role="region"
            aria-label="Cluster bias scores"
          >
            <LeanAxis
              axisId={`${headingId}-lean`}
              score={averages.lean}
              rationale={averages.leanRationale}
              isExpanded={expandedAxes.has("lean")}
              onToggle={() => toggleAxis("lean")}
              staggerIndex={0}
              contentVisible={contentVisible}
            />
            <SensationalismAxis
              axisId={`${headingId}-sense`}
              score={averages.sensationalism}
              rationale={averages.sensationalismRationale}
              isExpanded={expandedAxes.has("sense")}
              onToggle={() => toggleAxis("sense")}
              staggerIndex={1}
              contentVisible={contentVisible}
            />
            <RigorAxis
              axisId={`${headingId}-rigor`}
              score={averages.factualRigor}
              rationale={averages.coverageRationale}
              isExpanded={expandedAxes.has("rigor")}
              onToggle={() => toggleAxis("rigor")}
              staggerIndex={2}
              contentVisible={contentVisible}
            />
            <FramingAxis
              axisId={`${headingId}-framing`}
              score={averages.framing}
              rationale={averages.framingRationale}
              isExpanded={expandedAxes.has("framing")}
              onToggle={() => toggleAxis("framing")}
              staggerIndex={3}
              contentVisible={contentVisible}
            />
          </div>

          {/* Confidence meter */}
          <ConfidenceMeter
            confidence={averages.confidence}
            contentVisible={contentVisible}
          />
        </div>
      </div>
    </>
  );
}

/* ── Default export: legacy inline version (kept for any other callers) ─── */
// This is now a no-op shell — callers should use BiasInspectorTrigger +
// BiasInspectorPanel instead. Exported for backward compatibility.
export default function BiasInspector({ sources }: { sources: StorySource[] }) {
  const [isOpen, setIsOpen] = useState(false);
  if (sources.length === 0) return null;
  return (
    <div className="bias-inspector">
      <BiasInspectorTrigger sources={sources} onClick={() => setIsOpen(true)} />
      {isOpen && (
        <BiasInspectorPanel
          sources={sources}
          onClose={() => setIsOpen(false)}
          isOpen={isOpen}
        />
      )}
    </div>
  );
}
