"use client";

import { useState, useId } from "react";
import type { StorySource, LeanRationale, OpinionRationale, CoverageRationale, SensationalismRationale, FramingRationale } from "../lib/types";

/* ---------------------------------------------------------------------------
   BiasInspector — "How this was scored"

   Bloomberg Terminal for news bias. Shows per-source breakdown of all 5 axes
   with full rationale details. Progressive disclosure: collapsed rows show
   axis name + score + mini bar. Expanded shows evidence and sub-scores.

   Receives sources array from DeepDive (already fetched, no additional
   Supabase calls needed).
   --------------------------------------------------------------------------- */

interface BiasInspectorProps {
  sources: StorySource[];
}

/* ── Color helpers (self-contained — no import from BiasLens) ───────────── */

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

// Political lean: blue(left) → gray(center) → red(right)
function getLeanColor(v: number): string {
  const LEFT = "#3B82F6", CENTER = "#9CA3AF", RIGHT = "#EF4444";
  if (v <= 50) return lerpHex(LEFT, CENTER, v / 50);
  return lerpHex(CENTER, RIGHT, (v - 50) / 50);
}

// Sensationalism: green(low) → yellow(medium) → red(high)
function getSenseColor(v: number): string {
  const LOW = "#22C55E", MED = "#EAB308", HIGH = "#EF4444";
  if (v <= 50) return lerpHex(LOW, MED, v / 50);
  return lerpHex(MED, HIGH, (v - 50) / 50);
}

// Opinion: blue(reporting) → purple(analysis) → orange(opinion)
function getOpinionColor(v: number): string {
  const RPT = "#3B82F6", ANA = "#8B5CF6", OPN = "#F97316";
  if (v <= 50) return lerpHex(RPT, ANA, v / 50);
  return lerpHex(ANA, OPN, (v - 50) / 50);
}

// Factual rigor: red(low) → yellow(medium) → green(high) — INVERTED: high=good
function getRigorColor(v: number): string {
  const LOW = "#EF4444", MED = "#EAB308", HIGH = "#22C55E";
  if (v <= 50) return lerpHex(LOW, MED, v / 50);
  return lerpHex(MED, HIGH, (v - 50) / 50);
}

// Framing: green(neutral) → yellow → red(heavy framing)
function getFramingColor(v: number): string {
  return getSenseColor(v); // same scale: low=neutral(good), high=bad
}

// Confidence: same as rigor (high is good)
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

function faviconUrl(articleUrl: string): string {
  try {
    const domain = new URL(articleUrl).hostname.replace(/^www\./, "");
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/* ── Mini score bar ─────────────────────────────────────────────────────── */

interface MiniBarProps {
  value: number;
  color: string;
  max?: number;
}

function MiniBar({ value, color, max = 100 }: MiniBarProps) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div className="bi-minibar">
      <div className="bi-minibar__track">
        <div
          className="bi-minibar__fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
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
  /** When true, formats value as percentage (0-1 input) */
  isPct?: boolean;
  /** Suffix appended after value */
  suffix?: string;
}

function SubScore({ label, value, color, max = 100, isPct, suffix }: SubScoreProps) {
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
            style={{ width: `${Math.max(0, Math.min(100, (barVal / max) * 100))}%`, backgroundColor: color }}
          />
        </div>
      </div>
      <span className="bi-subscore__value" style={{ color }}>{displayVal}</span>
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

function DensityChart({ superlative, urgency, hyperbole, measured }: DensityChartProps) {
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
            {value.toFixed(1)}
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
            style={{ color: positive ? "var(--rigor-high)" : "var(--rigor-low)" }}
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

function Tag({ children, color }: { children: React.ReactNode; color?: string }) {
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
  isExpanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
  hasRationale: boolean;
}

function AxisRow({ axisId, label, score, color, scoreLabel, isExpanded, onToggle, children, hasRationale }: AxisRowProps) {
  const headingId = `${axisId}-heading`;
  const contentId = `${axisId}-content`;

  return (
    <div className="bi-axis" role="region" aria-labelledby={headingId}>
      <button
        className={`bi-axis__header${isExpanded ? " bi-axis__header--expanded" : ""}`}
        aria-expanded={isExpanded}
        aria-controls={hasRationale ? contentId : undefined}
        onClick={onToggle}
        disabled={!hasRationale}
        id={headingId}
      >
        <span className="bi-axis__name">{label}</span>
        <div className="bi-axis__score-row">
          <MiniBar value={score} color={color} />
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
              <path d="M2 4L6 8L10 4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
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
          <div className="bi-axis__rationale">
            {children}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Axis 1: Political Lean ─────────────────────────────────────────────── */

function LeanAxis({ score, rationale, isExpanded, onToggle, axisId }: {
  score: number;
  rationale?: LeanRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
}) {
  const color = getLeanColor(score);
  const hasRationale = !!rationale;

  return (
    <AxisRow
      axisId={axisId}
      label="Political Lean"
      score={score}
      color={color}
      scoreLabel={leanLabel(score)}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={hasRationale}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore label="Keyword score" value={rationale.keywordScore} color={getLeanColor(rationale.keywordScore)} />
            <SubScore label="Framing shift" value={rationale.framingShift + 15} color={getLeanColor((rationale.framingShift + 15) * (100 / 30))} max={30} />
            <SubScore label="Entity shift" value={rationale.entityShift + 15} color={getLeanColor((rationale.entityShift + 15) * (100 / 30))} max={30} />
            <SubScore label="Source baseline" value={rationale.sourceBaseline} color={getLeanColor(rationale.sourceBaseline)} />
          </div>
          {(rationale.topLeftKeywords?.length > 0 || rationale.topRightKeywords?.length > 0) && (
            <div className="bi-evidence-group">
              {rationale.topLeftKeywords?.length > 0 && (
                <div className="bi-keyword-row">
                  <span className="bi-keyword-row__label" style={{ color: "var(--bias-left)" }}>Left signals</span>
                  <div className="bi-keyword-row__tags">
                    {rationale.topLeftKeywords.slice(0, 5).map((kw) => (
                      <Tag key={kw} color="var(--bias-left)">{kw}</Tag>
                    ))}
                  </div>
                </div>
              )}
              {rationale.topRightKeywords?.length > 0 && (
                <div className="bi-keyword-row">
                  <span className="bi-keyword-row__label" style={{ color: "var(--bias-right)" }}>Right signals</span>
                  <div className="bi-keyword-row__tags">
                    {rationale.topRightKeywords.slice(0, 5).map((kw) => (
                      <Tag key={kw} color="var(--bias-right)">{kw}</Tag>
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
          {rationale.entitySentiments && Object.keys(rationale.entitySentiments).length > 0 && (
            <div className="bi-evidence-group">
              <span className="bi-evidence-label">Entity sentiments</span>
              <div className="bi-entity-grid">
                {Object.entries(rationale.entitySentiments).slice(0, 6).map(([entity, sentiment]) => (
                  <div key={entity} className="bi-entity-item">
                    <span className="bi-entity-item__name">{entity}</span>
                    <span
                      className="bi-entity-item__value"
                      style={{ color: sentiment > 0 ? "var(--sense-low)" : sentiment < 0 ? "var(--sense-high)" : "var(--fg-muted)" }}
                    >
                      {sentiment > 0 ? "+" : ""}{sentiment.toFixed(2)}
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

function SensationalismAxis({ score, rationale, isExpanded, onToggle, axisId }: {
  score: number;
  rationale?: SensationalismRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
}) {
  const color = getSenseColor(score);
  const hasRationale = !!rationale;

  return (
    <AxisRow
      axisId={axisId}
      label="Sensationalism"
      score={score}
      color={color}
      scoreLabel={senseLabel(score)}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={hasRationale}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore label="Headline score" value={rationale.headlineScore} color={getSenseColor(rationale.headlineScore)} />
            <SubScore label="Body score" value={rationale.bodyScore} color={getSenseColor(rationale.bodyScore)} />
          </div>
          <div className="bi-evidence-group">
            <span className="bi-evidence-label">Clickbait signals detected</span>
            <span className="bi-evidence-value" style={{ color: rationale.clickbaitSignals > 0 ? "var(--sense-high)" : "var(--sense-low)" }}>
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

/* ── Axis 3: Opinion vs Reporting ───────────────────────────────────────── */

function OpinionAxis({ score, rationale, isExpanded, onToggle, axisId }: {
  score: number;
  rationale?: OpinionRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
}) {
  const color = getOpinionColor(score);
  const hasRationale = !!rationale;
  const classificationColor =
    rationale?.classification === "Reporting" ? "var(--type-reporting)" :
    rationale?.classification === "Analysis" ? "var(--type-analysis)" :
    rationale?.classification === "Opinion" ? "var(--type-opinion)" :
    "var(--fg-tertiary)";

  return (
    <AxisRow
      axisId={axisId}
      label="Opinion vs. Reporting"
      score={score}
      color={color}
      scoreLabel={rationale?.classification ?? (score > 50 ? "Opinion" : "Reporting")}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={hasRationale}
    >
      {rationale && (
        <>
          {rationale.classification && (
            <div className="bi-evidence-group">
              <Tag color={classificationColor}>{rationale.classification}</Tag>
            </div>
          )}
          <div className="bi-subscore-group">
            <SubScore label="First-person pronouns" value={rationale.pronounScore} color={getOpinionColor(rationale.pronounScore)} />
            <SubScore label="Subjectivity" value={rationale.subjectivityScore} color={getOpinionColor(rationale.subjectivityScore)} />
            <SubScore label="Modal language" value={rationale.modalScore} color={getOpinionColor(rationale.modalScore)} />
            <SubScore label="Hedging" value={rationale.hedgingScore} color={getOpinionColor(rationale.hedgingScore)} />
            <SubScore label="Attribution density" value={rationale.attributionScore} color={getOpinionColor(rationale.attributionScore)} />
            <SubScore label="Metadata markers" value={rationale.metadataScore} color={getOpinionColor(rationale.metadataScore)} />
            <SubScore label="Rhetorical questions" value={rationale.rhetoricalScore} color={getOpinionColor(rationale.rhetoricalScore)} />
            <SubScore label="Value judgments" value={rationale.valueJudgmentScore} color={getOpinionColor(rationale.valueJudgmentScore)} />
          </div>
          {rationale.dominantSignals?.length > 0 && (
            <div className="bi-evidence-group">
              <span className="bi-evidence-label">Dominant signals</span>
              <div className="bi-keyword-row__tags">
                {rationale.dominantSignals.slice(0, 4).map((sig) => (
                  <Tag key={sig}>{sig}</Tag>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </AxisRow>
  );
}

/* ── Axis 4: Factual Rigor ──────────────────────────────────────────────── */

function RigorAxis({ score, rationale, isExpanded, onToggle, axisId }: {
  score: number;
  rationale?: CoverageRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
}) {
  const color = getRigorColor(score);
  const hasRationale = !!rationale;

  return (
    <AxisRow
      axisId={axisId}
      label="Factual Rigor"
      score={score}
      color={color}
      scoreLabel={rigorLabel(score)}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={hasRationale}
    >
      {rationale && (
        <>
          <EvidenceTally
            items={[
              { label: "Named sources", value: rationale.namedSourcesCount, positive: true },
              { label: "Org. citations", value: rationale.orgCitationsCount, positive: true },
              { label: "Data points", value: rationale.dataPointsCount, positive: true },
              { label: "Direct quotes", value: rationale.directQuotesCount, positive: true },
              { label: "Vague sources", value: rationale.vagueSourcesCount, positive: false },
            ]}
          />
          {typeof rationale.specificityRatio === "number" && (
            <div className="bi-subscore-group" style={{ marginTop: "var(--space-3)" }}>
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

/* ── Axis 5: Framing Analysis ───────────────────────────────────────────── */

function FramingAxis({ score, rationale, isExpanded, onToggle, axisId }: {
  score: number;
  rationale?: FramingRationale;
  isExpanded: boolean;
  onToggle: () => void;
  axisId: string;
}) {
  const color = getFramingColor(score);
  const hasRationale = !!rationale;

  return (
    <AxisRow
      axisId={axisId}
      label="Framing Analysis"
      score={score}
      color={color}
      scoreLabel={framingLabel(score)}
      isExpanded={isExpanded}
      onToggle={onToggle}
      hasRationale={hasRationale}
    >
      {rationale && (
        <>
          <div className="bi-subscore-group">
            <SubScore label="Connotation" value={rationale.connotationScore} color={getFramingColor(rationale.connotationScore)} />
            <SubScore label="Keyword emphasis" value={rationale.keywordEmphasisScore} color={getFramingColor(rationale.keywordEmphasisScore)} />
            <SubScore label="Omission" value={rationale.omissionScore} color={getFramingColor(rationale.omissionScore)} />
            <SubScore label="Headline/body divergence" value={rationale.headlineBodyDivergence} color={getFramingColor(rationale.headlineBodyDivergence)} />
            <SubScore label="Passive voice" value={rationale.passiveVoiceScore} color={getFramingColor(rationale.passiveVoiceScore)} />
          </div>
          <div className="bi-evidence-group">
            <Tag color={rationale.hasClusterContext ? "var(--sense-low)" : "var(--fg-muted)"}>
              {rationale.hasClusterContext ? "Cross-article analysis" : "Single-article only"}
            </Tag>
          </div>
        </>
      )}
    </AxisRow>
  );
}

/* ── Confidence meter ───────────────────────────────────────────────────── */

function ConfidenceMeter({ confidence }: { confidence: number }) {
  const pct = Math.round(confidence * 100);
  const color = getConfidenceColor(pct);

  return (
    <div className="bi-confidence">
      <div className="bi-confidence__header">
        <span className="bi-confidence__label">Analysis confidence</span>
        <span className="bi-confidence__value" style={{ color }}>
          {pct}%
        </span>
      </div>
      <div className="bi-confidence__track" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={`Analysis confidence: ${pct}%`}>
        <div
          className="bi-confidence__fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <p className="bi-confidence__note">
        Based on text length, text availability, and signal strength relative to source baseline.
      </p>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────────────── */

export default function BiasInspector({ sources }: BiasInspectorProps) {
  const [selectedIdx, setSelectedIdx] = useState(0);
  // Track which axes are expanded: keyed by axis name, per source state resets on source change
  const [expandedAxes, setExpandedAxes] = useState<Set<string>>(new Set());
  const headingId = useId();

  // Reset expanded axes when source changes
  function selectSource(idx: number) {
    setSelectedIdx(idx);
    setExpandedAxes(new Set());
  }

  function toggleAxis(axisKey: string) {
    setExpandedAxes((prev) => {
      const next = new Set(prev);
      if (next.has(axisKey)) {
        next.delete(axisKey);
      } else {
        next.add(axisKey);
      }
      return next;
    });
  }

  if (sources.length === 0) return null;

  const src = sources[Math.min(selectedIdx, sources.length - 1)];
  const lensData = src.lensData;
  const biasScores = src.biasScores;

  // Derive confidence: prefer raw confidence on StorySource, fall back from coverage score
  const rawConfidence = typeof src.confidence === "number"
    ? src.confidence
    : (lensData ? lensData.coverage / 100 : 0.5);

  return (
    <section className="bias-inspector" aria-labelledby={headingId}>
      <h3 id={headingId} className="section-heading bias-inspector__heading">
        How this was scored
      </h3>

      {/* Source selector */}
      {sources.length > 1 && (
        <div className="bi-source-selector" role="tablist" aria-label="Select source to inspect">
          {sources.map((s, i) => {
            const favicon = s.url ? faviconUrl(s.url) : "";
            const abbrev = s.name.length > 16 ? s.name.slice(0, 14) + "\u2026" : s.name;
            const isActive = i === selectedIdx;
            return (
              <button
                key={`${s.name}-${i}`}
                role="tab"
                aria-selected={isActive}
                className={`bi-source-btn${isActive ? " bi-source-btn--active" : ""}`}
                onClick={() => selectSource(i)}
                title={s.name}
              >
                {favicon ? (
                  <img
                    src={favicon}
                    alt=""
                    width={14}
                    height={14}
                    className="bi-source-btn__favicon"
                    loading="lazy"
                  />
                ) : (
                  <span className="bi-source-btn__initial" aria-hidden="true">
                    {s.name.charAt(0)}
                  </span>
                )}
                <span className="bi-source-btn__name">{abbrev}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* 5-axis scorecard */}
      <div className="bi-scorecard" role="tabpanel" aria-label={`Bias analysis for ${src.name}`}>
        <LeanAxis
          axisId={`${headingId}-lean`}
          score={biasScores.politicalLean}
          rationale={lensData?.leanRationale}
          isExpanded={expandedAxes.has("lean")}
          onToggle={() => toggleAxis("lean")}
        />
        <SensationalismAxis
          axisId={`${headingId}-sense`}
          score={biasScores.sensationalism}
          rationale={lensData?.sensationalismRationale}
          isExpanded={expandedAxes.has("sense")}
          onToggle={() => toggleAxis("sense")}
        />
        <OpinionAxis
          axisId={`${headingId}-opinion`}
          score={biasScores.opinionFact}
          rationale={lensData?.opinionRationale}
          isExpanded={expandedAxes.has("opinion")}
          onToggle={() => toggleAxis("opinion")}
        />
        <RigorAxis
          axisId={`${headingId}-rigor`}
          score={biasScores.factualRigor}
          rationale={lensData?.coverageRationale}
          isExpanded={expandedAxes.has("rigor")}
          onToggle={() => toggleAxis("rigor")}
        />
        <FramingAxis
          axisId={`${headingId}-framing`}
          score={biasScores.framing}
          rationale={lensData?.framingRationale}
          isExpanded={expandedAxes.has("framing")}
          onToggle={() => toggleAxis("framing")}
        />
      </div>

      {/* Confidence meter */}
      <ConfidenceMeter confidence={rawConfidence} />
    </section>
  );
}
