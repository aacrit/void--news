"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import Link from "next/link";
import type { Edition } from "../lib/types";
import { supabase, supabaseError, fetchMethodologyArticles } from "../lib/supabase";
import {
  getLeanColor,
  getSenseColor,
  getRigorColor,
  getFramingColor,
  leanLabel,
  senseLabel,
  rigorLabel,
} from "../lib/biasColors";
import SpectrumChart, { type SpectrumSource, normalizeLean } from "../components/SpectrumChart";
import ThemeToggle from "../components/ThemeToggle";
import PageToggle from "../components/PageToggle";
import EditionIcon from "../components/EditionIcon";
import LogoFull from "../components/LogoFull";
import LogoIcon from "../components/LogoIcon";
import Footer from "../components/Footer";
import { getEditionTimeOfDay, getEditionTimestamp } from "../lib/utils";
import ErrorBoundary from "../components/ErrorBoundary";
import { useInView } from "../lib/sharedObserver";

/* ---------------------------------------------------------------------------
   Sources Page — /sources
   Visualizes all curated news sources on a political lean spectrum.
   Desktop: horizontal spectrum bar with logos above/below.
   Mobile: horizontal swipeable card strip with scroll-snap.
   --------------------------------------------------------------------------- */

type LeanCategory =
  | "far-left" | "left" | "center-left" | "center"
  | "center-right" | "right" | "far-right";

type LeanFilter = "All" | "Left" | "Center" | "Right";

const EDITIONS: { slug: Edition; label: string }[] = [
  { slug: "world", label: "World" },
  { slug: "us", label: "US" },
  { slug: "india", label: "India" },
];

const EDITION_COUNTRIES: Record<Edition, string[] | null> = {
  world: null,
  us: ["US"],
  india: ["IN"],
};

const LEAN_FILTERS: LeanFilter[] = ["Left", "Center", "Right"];

const LEAN_ALLOWED: Record<LeanFilter, LeanCategory[] | null> = {
  All: null,
  Left: ["far-left", "left", "center-left"],
  Center: ["center"],
  Right: ["center-right", "right", "far-right"],
};

const LEAN_DOT_COLOR: Record<string, string> = {
  Left: "var(--bias-left)",
  Center: "var(--bias-center)",
  Right: "var(--bias-right)",
};

/* ---------------------------------------------------------------------------
   Methodology Section — comprehensive trust anchor
   Six sections: Per-Article, Six Axes, Worked Example, Validation,
   Curated Sources, Open Source.
   --------------------------------------------------------------------------- */

const AXES_DATA: {
  id: string;
  name: string;
  range: string;
  low: string;
  high: string;
  what: string;
  signals: string[];
}[] = [
  {
    id: "lean",
    name: "Political Lean",
    range: "0\u2013100",
    low: "Far Left",
    high: "Far Right",
    what: "Where an article lands on the left\u2013right spectrum, independent of its outlet\u2019s reputation.",
    signals: [
      "Keyword lexicons scored against curated left/right phrase lists",
      "Named-entity sentiment via NER + polarity analysis",
      "Framing phrases that signal ideological perspective",
      "Length-adaptive + sparsity-weighted source baseline blending",
    ],
  },
  {
    id: "sensationalism",
    name: "Sensationalism",
    range: "0\u2013100",
    low: "Measured",
    high: "Inflammatory",
    what: "How much the article inflates urgency, emotion, or outrage beyond what the facts warrant.",
    signals: [
      "Clickbait headline patterns (questions, listicles, superlatives)",
      "Superlative density via word-boundary regex",
      "Emotional extremity score",
      "Partisan attack density (capped at 30 points)",
    ],
  },
  {
    id: "opinion",
    name: "Opinion vs Reporting",
    range: "0\u2013100",
    low: "Hard Reporting",
    high: "Editorial",
    what: "Whether the article reports facts or argues a position. 50 marks the analysis midpoint.",
    signals: [
      "First- and second-person pronoun frequency",
      "Subjectivity score",
      "Attribution density (24 investigative verb patterns)",
      "Value judgments and rhetorical questions",
    ],
  },
  {
    id: "rigor",
    name: "Factual Rigor",
    range: "0\u2013100",
    low: "Unsourced",
    high: "Well-sourced",
    what: "How thoroughly an article cites named sources, data, and direct quotes.",
    signals: [
      "Named sources detected via NER + attribution verbs",
      "Organizational citations (agencies, institutions)",
      "Data patterns (percentages, dollar figures, dates)",
      "Direct quotes count; vague-source penalty (\u201cofficials say\u201d)",
    ],
  },
  {
    id: "framing",
    name: "Framing",
    range: "0\u2013100",
    low: "Neutral",
    high: "Heavy Framing",
    what: "Whether word choices, omissions, or structural decisions nudge the reader toward a conclusion.",
    signals: [
      "Charged synonym detection (50+ curated word pairs)",
      "Cluster-aware omission analysis (what peers cover that this article skips)",
      "Headline\u2013body divergence score",
      "Passive voice frequency (capped at 30 points)",
    ],
  },
  {
    id: "tracking",
    name: "Outlet Tracking",
    range: "Adaptive",
    low: "New outlet",
    high: "Established",
    what: "A per-topic, per-outlet exponential moving average (EMA) that tracks how each outlet covers each topic over time.",
    signals: [
      "Adaptive alpha: 0.3 for new outlets, 0.15 for established",
      "Topic-specific tracking (an outlet\u2019s economy coverage vs. its foreign policy coverage)",
      "Smooths single-article noise into a reliable baseline",
    ],
  },
];

const WORKED_EXAMPLE = {
  headline: "Senate Passes Emergency Spending Bill After Marathon Session",
  source: "Associated Press",
  scores: [
    { axis: "Political Lean", score: 48, color: "var(--fg-secondary)", label: "Center", detail: "Neutral framing, balanced quote selection (3 Democratic, 3 Republican sources), no loaded modifiers." },
    { axis: "Sensationalism", score: 18, color: "var(--fg-secondary)", label: "Measured", detail: "\u201cMarathon session\u201d is the only heightened phrase. No superlatives, no clickbait patterns, no partisan attacks." },
    { axis: "Opinion vs Reporting", score: 12, color: "var(--fg-secondary)", label: "Hard reporting", detail: "Zero first-person pronouns. 8 direct attributions. No value judgments or rhetorical questions." },
    { axis: "Factual Rigor", score: 82, color: "var(--accent-warm)", label: "Well-sourced", detail: "6 named sources, 2 org citations (CBO, OMB), 4 direct quotes, specific dollar figures and vote counts." },
    { axis: "Framing", score: 15, color: "var(--fg-secondary)", label: "Neutral", detail: "No charged synonyms detected. Headline matches body content. Active voice throughout." },
    { axis: "Outlet Tracking", score: null, color: "var(--fg-muted)", label: "EMA: 47.2", detail: "AP\u2019s economy coverage averages 47.2 (center) across 342 tracked articles on this topic." },
  ],
};

/* ---------------------------------------------------------------------------
   Axis Glyph SVGs — inline, 20x20 viewBox, stroke-based
   --------------------------------------------------------------------------- */

function AxisGlyph({ id }: { id: string }) {
  const props = { width: 20, height: 20, viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true as const, className: "meth-eq__glyph" };

  switch (id) {
    case "lean":
      // Scale beam: horizontal line + fulcrum triangle
      return (<svg {...props}><line x1="3" y1="8" x2="17" y2="8" /><polygon points="10,18 7,13 13,13" fill="none" /></svg>);
    case "sensationalism":
      // Thermometer: vertical rect with rounded bottom, fill level
      return (<svg {...props}><rect x="8" y="3" width="4" height="14" rx="2" /><line x1="10" y1="12" x2="10" y2="10" strokeWidth="2.5" /></svg>);
    case "opinion":
      // Split page: rect with vertical dashed line, text lines left, wavy right
      return (<svg {...props}><rect x="3" y="3" width="14" height="14" rx="1" /><line x1="10" y1="4" x2="10" y2="16" strokeDasharray="2 2" /><line x1="5" y1="7" x2="8" y2="7" /><line x1="5" y1="10" x2="8" y2="10" /><path d="M12 7 Q13 6 14 7 Q15 8 16 7" /></svg>);
    case "rigor":
      // Citation bracket with ticks
      return (<svg {...props}><path d="M6 3 L4 3 L4 17 L6 17" /><line x1="7" y1="7" x2="14" y2="7" /><line x1="7" y1="10" x2="16" y2="10" /><line x1="7" y1="13" x2="12" y2="13" /></svg>);
    case "framing":
      // Magnifying glass with wavy line inside
      return (<svg {...props}><circle cx="9" cy="9" r="5" /><line x1="13" y1="13" x2="17" y2="17" /><path d="M6 9 Q7.5 7 9 9 Q10.5 11 12 9" strokeWidth="1.4" /></svg>);
    case "tracking":
      // Sparkline: 5 connected points
      return (<svg {...props}><polyline points="3,14 6,8 9,11 13,5 17,9" /></svg>);
    default:
      return null;
  }
}

/* ---------------------------------------------------------------------------
   Score label helpers for each axis
   --------------------------------------------------------------------------- */

function getAxisLabel(id: string, score: number | null): string {
  if (score === null) return "\u2014";
  switch (id) {
    case "lean": return leanLabel(score);
    case "sensationalism": return senseLabel(score);
    case "opinion": return score <= 25 ? "Reporting" : score <= 50 ? "Analysis" : score <= 75 ? "Opinion" : "Editorial";
    case "rigor": return rigorLabel(score);
    case "framing": return score <= 25 ? "Neutral" : score <= 50 ? "Moderate" : score <= 75 ? "Noticeable" : "Heavy";
    case "tracking": return "EMA";
    default: return "";
  }
}

function getAxisColor(id: string, score: number): string {
  switch (id) {
    case "lean": return getLeanColor(score);
    case "sensationalism": return getSenseColor(score);
    case "opinion": return getSenseColor(score); // blue-to-orange via same gradient
    case "rigor": return getRigorColor(score);
    case "framing": return getFramingColor(score);
    default: return "var(--fg-muted)";
  }
}

/* ---------------------------------------------------------------------------
   Axis gradient strings for bar fills
   --------------------------------------------------------------------------- */

function getAxisGradient(id: string): string {
  switch (id) {
    case "lean":
      return "linear-gradient(to right, var(--bias-far-left), var(--bias-left) 14%, var(--bias-center-left) 28%, var(--bias-center) 42%, var(--bias-center-right) 57%, var(--bias-right) 71%, var(--bias-far-right))";
    case "sensationalism":
      return "linear-gradient(to right, var(--sense-low), var(--sense-medium), var(--sense-high))";
    case "opinion":
      return "linear-gradient(to right, var(--type-reporting), var(--type-analysis), var(--type-opinion))";
    case "rigor":
      return "linear-gradient(to right, var(--rigor-low), var(--rigor-medium), var(--rigor-high))";
    case "framing":
      return "linear-gradient(to right, var(--sense-low), var(--sense-medium), var(--sense-high))";
    default:
      return "var(--fg-muted)";
  }
}

/* ---------------------------------------------------------------------------
   EqualizerRow — single axis bar meter with accordion
   --------------------------------------------------------------------------- */

function EqualizerRow({
  axis,
  score,
  index,
  visible,
  animating,
}: {
  axis: typeof AXES_DATA[number];
  score: number | null;
  index: number;
  visible: boolean;
  animating: boolean;
}) {
  const [open, setOpen] = useState(false);
  const panelId = `meth-axis-${axis.id}`;
  const isTracking = axis.id === "tracking";
  const displayScore = score !== null ? score : (isTracking ? null : 50);

  const barStyle: React.CSSProperties = {
    "--eq-fill": displayScore !== null ? `${displayScore}%` : "0%",
    "--eq-delay": `${index * 80}ms`,
    "--eq-gradient": getAxisGradient(axis.id),
  } as React.CSSProperties;

  const markerColor = displayScore !== null ? getAxisColor(axis.id, displayScore) : "var(--fg-muted)";

  return (
    <div className={`meth-eq${open ? " meth-eq--open" : ""}`}>
      <button
        className="meth-eq__trigger"
        onClick={() => setOpen((prev) => !prev)}
        aria-expanded={open}
        aria-controls={panelId}
      >
        <div className="meth-eq__head">
          <AxisGlyph id={axis.id} />
          <span className="meth-eq__name">{axis.name}</span>
          <span className="meth-eq__score" style={{ color: markerColor }}>
            {displayScore !== null ? displayScore : "\u2014"}
          </span>
          <span className="meth-eq__label">{getAxisLabel(axis.id, displayScore)}</span>
          <span className="meth-eq__chevron" aria-hidden="true">{"\u25B8"}</span>
        </div>
        {!isTracking ? (
          <div
            className={`meth-eq__bar${visible ? " meth-eq__bar--visible" : ""}${animating ? " meth-eq__bar--animating" : ""}`}
            style={barStyle}
            role="meter"
            aria-label={`${axis.name}: ${displayScore ?? 0} out of 100`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={displayScore ?? 0}
          >
            <div className="meth-eq__track">
              <div className="meth-eq__fill" />
              <div
                className="meth-eq__marker"
                style={{ backgroundColor: markerColor }}
              />
            </div>
            <div className="meth-eq__endpoints">
              <span>{axis.low}</span>
              <span>{axis.high}</span>
            </div>
          </div>
        ) : (
          <div className={`meth-eq__bar meth-eq__bar--tracking${visible ? " meth-eq__bar--visible" : ""}`} style={barStyle}>
            <svg className="meth-eq__sparkline" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
              <polyline
                points="0,16 15,10 30,14 50,6 70,12 85,4 100,10"
                fill="none"
                stroke="var(--fg-muted)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <div className="meth-eq__endpoints">
              <span>{axis.low}</span>
              <span>{axis.high}</span>
            </div>
          </div>
        )}
      </button>

      <div
        className="meth-eq__panel"
        id={panelId}
        role="region"
        aria-label={`${axis.name} details`}
        aria-hidden={!open}
      >
        <div className="meth-eq__panel-inner">
          <p className="meth-axis__what">{axis.what}</p>
          <ul className="meth-axis__signals">
            {axis.signals.map((s, i) => (
              <li key={i} className="meth-axis__signal">{s}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   MethSection — scroll-revealed section wrapper.
   Uses useInView to trigger the dolly entrance animation when the section
   scrolls into the viewport. Stagger delay is set via CSS custom property.
   --------------------------------------------------------------------------- */

function MethSection({
  index,
  className = "",
  children,
}: {
  index: number;
  className?: string;
  children: React.ReactNode;
}) {
  const [ref, visible] = useInView<HTMLDivElement>();
  const staggerDelay = `${index * 80}ms`;
  return (
    <div
      ref={ref}
      className={`meth__section${visible ? " meth__section--visible" : ""}${className ? ` ${className}` : ""}`}
      style={{ "--meth-stagger-delay": staggerDelay } as React.CSSProperties}
    >
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   ValidationGrid — stat numbers with staggered fade-settle entrance.
   Each stat gets its own IO-driven visibility and a stagger delay.
   --------------------------------------------------------------------------- */

const VALIDATION_STATS = [
  { number: "42", label: "Ground-truth articles", barPct: "42%", barColor: "var(--fg-tertiary)", gate: undefined as string | undefined },
  { number: "9", label: "Categories tested", barPct: "9%", barColor: "var(--fg-tertiary)", gate: undefined as string | undefined },
  { number: "100%", label: "Accuracy", barPct: "100%", barColor: "var(--accent-warm)", gate: undefined as string | undefined },
  { number: "r\u2009<\u20090.70", label: "Cross-axis correlation gate", barPct: "70%", barColor: "var(--fg-tertiary)", gate: "70%" },
];

function ValidationStat({ stat, index }: { stat: typeof VALIDATION_STATS[number]; index: number }) {
  const [ref, visible] = useInView<HTMLDivElement>();
  const [displayNum, setDisplayNum] = useState("0");

  useEffect(() => {
    if (!visible) return;
    // Extract numeric target for counter animation
    const numMatch = stat.number.match(/\d+/);
    if (!numMatch) { setDisplayNum(stat.number); return; }
    const target = parseInt(numMatch[0], 10);
    const suffix = stat.number.replace(/\d+/, "");
    // For non-counting stats (like "r < 0.70"), skip counter — just show final value
    if (stat.number.startsWith("r")) { setDisplayNum(stat.number); return; }
    const dur = 800;
    const start = performance.now();

    function tick(now: number) {
      const t = Math.min((now - start) / dur, 1);
      const eased = 1 - (1 - t) * (1 - t);
      const current = Math.round(eased * target);
      setDisplayNum(`${current}${suffix}`);
      if (t < 1) requestAnimationFrame(tick);
      else setDisplayNum(stat.number);
    }
    requestAnimationFrame(tick);
  }, [visible, stat.number]);

  return (
    <div
      ref={ref}
      className={`meth__validation-stat${visible ? " meth__validation-stat--visible" : ""}`}
      style={{ "--meth-stat-delay": `${index * 100}ms` } as React.CSSProperties}
    >
      <span className="meth__validation-number">{displayNum}</span>
      <div className={`meth__validation-bar${visible ? " meth__validation-bar--visible" : ""}`} style={{ "--meth-stat-delay": `${index * 100}ms` } as React.CSSProperties}>
        <div
          className="meth__validation-bar-fill"
          style={{
            "--val-fill-pct": stat.barPct,
            "--val-fill-color": stat.barColor,
          } as React.CSSProperties}
        />
        {stat.gate && <div className="meth__validation-gate" style={{ left: stat.gate }} />}
      </div>
      <span className="meth__validation-label">{stat.label}</span>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   ArticlePicker — live article selection for the autopsy
   --------------------------------------------------------------------------- */

interface MethodologyArticle {
  id: string;
  title: string;
  published_at: string;
  excerpt: string | null;
  source: { name: string; slug: string; url: string } | null;
  bias_scores: {
    political_lean: number | null;
    sensationalism: number | null;
    opinion_fact: number | null;
    factual_rigor: number | null;
    framing: number | null;
    rationale: Record<string, unknown> | null;
  }[];
}

/** Pick 5 articles from 10 fetched, aiming for lean diversity */
function pickDiverseArticles(articles: MethodologyArticle[]): MethodologyArticle[] {
  if (articles.length <= 5) return articles;
  // Sort by lean to pick from across the spectrum
  const sorted = [...articles].sort((a, b) => {
    const aLean = a.bias_scores?.[0]?.political_lean ?? 50;
    const bLean = b.bias_scores?.[0]?.political_lean ?? 50;
    return aLean - bLean;
  });
  // Pick evenly spaced indices
  const step = sorted.length / 5;
  const picked: MethodologyArticle[] = [];
  for (let i = 0; i < 5; i++) {
    picked.push(sorted[Math.floor(i * step)]);
  }
  return picked;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function getFaviconUrlMeth(sourceUrl: string): string {
  if (!sourceUrl) return "";
  try {
    const domain = new URL(sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch { return ""; }
}

/* ---------------------------------------------------------------------------
   RationaleTree — tree-style decomposition of rationale JSONB
   --------------------------------------------------------------------------- */

function RationaleTree({ axisId, rationale }: { axisId: string; rationale: Record<string, unknown> | null }) {
  if (!rationale) return null;

  // Extract signals per axis from the rationale object
  type Signal = { label: string; value: string };
  const signals: Signal[] = [];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const r = rationale as any;

  switch (axisId) {
    case "lean":
      if (r.political_lean != null || r.keyword_score != null) {
        const lean = r.political_lean ?? r;
        if (lean.keyword_score != null) signals.push({ label: "Keyword score", value: String(Math.round(lean.keyword_score)) });
        if (lean.entity_shift != null) signals.push({ label: "Entity sentiment", value: lean.entity_shift > 0 ? `+${lean.entity_shift.toFixed(2)}` : lean.entity_shift.toFixed(2) });
        if (lean.framing_shift != null) signals.push({ label: "Framing shift", value: String(lean.framing_shift) });
        if (lean.source_baseline != null) signals.push({ label: "Source baseline", value: String(Math.round(lean.source_baseline)) });
      }
      break;
    case "sensationalism":
      if (r.sensationalism != null || r.headline_score != null) {
        const s = r.sensationalism ?? r;
        if (s.headline_score != null) signals.push({ label: "Headline score", value: String(Math.round(s.headline_score)) });
        if (s.body_score != null) signals.push({ label: "Body score", value: String(Math.round(s.body_score)) });
        if (s.superlative_density != null) signals.push({ label: "Superlative density", value: s.superlative_density.toFixed(3) });
        if (s.clickbait_signals != null) signals.push({ label: "Clickbait signals", value: String(s.clickbait_signals) });
      }
      break;
    case "opinion":
      if (r.opinion_fact != null || r.pronoun_score != null) {
        const o = r.opinion_fact ?? r;
        if (o.pronoun_score != null) signals.push({ label: "Pronoun score", value: String(Math.round(o.pronoun_score)) });
        if (o.subjectivity_score != null) signals.push({ label: "Subjectivity", value: String(Math.round(o.subjectivity_score)) });
        if (o.attribution_score != null) signals.push({ label: "Attribution", value: String(Math.round(o.attribution_score)) });
        if (o.classification != null) signals.push({ label: "Classification", value: o.classification });
      }
      break;
    case "rigor":
      if (r.factual_rigor != null || r.named_sources_count != null) {
        const f = r.factual_rigor ?? r;
        if (f.named_sources_count != null) signals.push({ label: "Named sources", value: String(f.named_sources_count) });
        if (f.org_citations_count != null) signals.push({ label: "Org citations", value: String(f.org_citations_count) });
        if (f.data_points_count != null) signals.push({ label: "Data points", value: String(f.data_points_count) });
        if (f.direct_quotes_count != null) signals.push({ label: "Direct quotes", value: String(f.direct_quotes_count) });
      }
      break;
    case "framing":
      if (r.framing != null || r.connotation_score != null) {
        const fr = r.framing ?? r;
        if (fr.connotation_score != null) signals.push({ label: "Connotation", value: String(Math.round(fr.connotation_score)) });
        if (fr.headline_body_divergence != null) signals.push({ label: "Headline-body gap", value: String(Math.round(fr.headline_body_divergence)) });
        if (fr.passive_voice_score != null) signals.push({ label: "Passive voice", value: String(Math.round(fr.passive_voice_score)) });
        if (fr.omission_score != null) signals.push({ label: "Omission score", value: String(Math.round(fr.omission_score)) });
      }
      break;
    default:
      break;
  }

  if (signals.length === 0) return null;

  return (
    <div className="meth-rationale">
      {signals.map((s, i) => (
        <div key={s.label} className="meth-rationale__row">
          <span className="meth-rationale__connector" aria-hidden="true">
            {i < signals.length - 1 ? "\u251C\u2500\u2500" : "\u2514\u2500\u2500"}
          </span>
          <span className="meth-rationale__label">{s.label}:</span>
          <span className="meth-rationale__value">{s.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Methodology — "The Scoring Stage"
   --------------------------------------------------------------------------- */

function Methodology({ sources }: { sources: SpectrumSource[] }) {
  /* Rule curtain-pull entrance */
  const [ruleRef, ruleVisible] = useInView<HTMLDivElement>();

  /* Section 1: Equalizer state */
  const [eqRef, eqVisible] = useInView<HTMLDivElement>();

  /* Section 2: Live articles */
  const [articles, setArticles] = useState<MethodologyArticle[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [eqAnimating, setEqAnimating] = useState(false);

  /* Neutral initial scores for equalizer (before article selection) */
  const neutralScores = useMemo(() => [50, 25, 15, 70, 20, null] as (number | null)[], []);

  /* Scores from selected article or neutral defaults */
  const activeScores = useMemo(() => {
    if (selectedIdx === null || !articles[selectedIdx]) return neutralScores;
    const bs = articles[selectedIdx].bias_scores?.[0];
    if (!bs) return neutralScores;
    return [
      bs.political_lean,
      bs.sensationalism,
      bs.opinion_fact,
      bs.factual_rigor,
      bs.framing,
      null, // tracking always null for individual articles
    ];
  }, [selectedIdx, articles, neutralScores]);

  /* Fetch methodology articles */
  useEffect(() => {
    let cancelled = false;
    fetchMethodologyArticles().then((data) => {
      if (cancelled) return;
      setArticles(data as MethodologyArticle[]);
    });
    return () => { cancelled = true; };
  }, []);

  const diverseArticles = useMemo(() => pickDiverseArticles(articles), [articles]);

  /* Handle article selection with animation trigger */
  const handleSelectArticle = useCallback((idx: number) => {
    setSelectedIdx(idx);
    setEqAnimating(true);
    setTimeout(() => setEqAnimating(false), 500);
  }, []);

  /* Active rationale for tree decomposition */
  const activeRationale = useMemo(() => {
    if (selectedIdx === null || !articles[selectedIdx]) return null;
    return articles[selectedIdx].bias_scores?.[0]?.rationale ?? null;
  }, [selectedIdx, articles]);

  /* Tier data for source bar visualization */
  const tierCounts = useMemo(() => {
    const tiers = [
      { tier: "us_major", label: "US Major", count: 0, total: 42, sources: [] as SpectrumSource[] },
      { tier: "international", label: "International", count: 0, total: 181, sources: [] as SpectrumSource[] },
      { tier: "independent", label: "Independent", count: 0, total: 196, sources: [] as SpectrumSource[] },
    ];
    for (const s of sources) {
      const t = tiers.find((t) => t.tier === s.tier);
      if (t) {
        t.count++;
        if (t.sources.length < 7) t.sources.push(s);
      }
    }
    return tiers;
  }, [sources]);

  return (
    <section id="methodology" className="meth" aria-label="Scoring methodology">
      {/* ---- Section 0: Gradient Bridge ---- */}
      <div
        ref={ruleRef}
        className={`meth__rule meth__rule--gradient${ruleVisible ? " meth__rule--visible" : ""}`}
        aria-hidden="true"
      />
      <h2 className="sr-only">Scoring Methodology</h2>
      <p className="meth__bridge-line">
        Every article above was scored by 6 independent analyzers. Here is how.
      </p>

      {/* ---- Section 1: Six-Axis Equalizer ---- */}
      <MethSection index={0}>
        <h3 className="meth__section-title">Per-Article, Not Per-Outlet</h3>
        <p className="meth__body">
          Most bias tools rate outlets. The New York Times is &ldquo;Lean Left&rdquo;
          regardless of the article. void --news rejects that premise. Every article
          passes through six independent NLP analyzers&mdash;no LLMs, no black boxes.
          The same text produces the same scores every time.
        </p>

        <div ref={eqRef} className="meth-eq__container" role="group" aria-label="Six-axis bias equalizer">
          {AXES_DATA.map((axis, i) => (
            <EqualizerRow
              key={axis.id}
              axis={axis}
              score={activeScores[i]}
              index={i}
              visible={eqVisible}
              animating={eqAnimating}
            />
          ))}
        </div>
      </MethSection>

      {/* ---- Section 2: Live Article Autopsy ---- */}
      <MethSection index={1}>
        <h3 className="meth__section-title">Live Article Autopsy</h3>
        <p className="meth__body">
          Select a recently published article to see how the six axes scored it.
          The equalizer above animates to real scores from the pipeline.
        </p>

        {/* Article picker */}
        <div className="meth-picker" role="listbox" aria-label="Select an article to analyze">
          {diverseArticles.length > 0 ? (
            diverseArticles.map((article, i) => {
              const isActive = selectedIdx === i;
              const favicon = article.source?.url ? getFaviconUrlMeth(article.source.url) : "";
              return (
                <button
                  key={article.id}
                  role="option"
                  aria-selected={isActive}
                  className={`meth-picker__row${isActive ? " meth-picker__row--active" : ""}`}
                  onClick={() => handleSelectArticle(i)}
                >
                  <span className="meth-picker__icon">
                    {favicon ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={favicon} alt="" width={16} height={16} loading="lazy" className="meth-picker__favicon" />
                    ) : (
                      <span className="meth-picker__fallback">{article.source?.name?.charAt(0) ?? "?"}</span>
                    )}
                  </span>
                  <span className="meth-picker__source">{article.source?.name ?? "Unknown"}</span>
                  <span className="meth-picker__time">{timeAgo(article.published_at)}</span>
                  <span className="meth-picker__headline">{article.title}</span>
                </button>
              );
            })
          ) : (
            /* Fallback to worked example */
            <button
              role="option"
              aria-selected={selectedIdx === 0}
              className={`meth-picker__row${selectedIdx === 0 ? " meth-picker__row--active" : ""}`}
              onClick={() => handleSelectArticle(0)}
            >
              <span className="meth-picker__icon">
                <span className="meth-picker__fallback">A</span>
              </span>
              <span className="meth-picker__source">{WORKED_EXAMPLE.source}</span>
              <span className="meth-picker__time">example</span>
              <span className="meth-picker__headline">{WORKED_EXAMPLE.headline}</span>
            </button>
          )}
        </div>

        {/* Rationale decomposition tree */}
        {selectedIdx !== null && activeRationale && (
          <div className="meth-rationale__container">
            {AXES_DATA.filter(a => a.id !== "tracking").map((axis, i) => {
              const score = activeScores[i];
              return (
                <div key={axis.id} className="meth-rationale__axis" style={{ "--rationale-delay": `${i * 80}ms` } as React.CSSProperties}>
                  <div className="meth-rationale__header">
                    <span className="meth-rationale__axis-name">{axis.name}</span>
                    <span className="meth-rationale__axis-score" style={{ color: score != null ? getAxisColor(axis.id, score) : "var(--fg-muted)" }}>
                      {score ?? "\u2014"}
                    </span>
                    <span className="meth-rationale__axis-label">{getAxisLabel(axis.id, score)}</span>
                  </div>
                  <RationaleTree axisId={axis.id} rationale={activeRationale} />
                </div>
              );
            })}
          </div>
        )}

        {/* Fallback: when no live articles, show static worked example inline */}
        {diverseArticles.length === 0 && selectedIdx === null && (
          <div className="meth__example">
            <div className="meth__example-header">
              <p className="meth__example-source">{WORKED_EXAMPLE.source}</p>
              <h4 className="meth__example-headline">{WORKED_EXAMPLE.headline}</h4>
            </div>
            <div className="meth__example-scores">
              {WORKED_EXAMPLE.scores.map((s) => (
                <div className="meth__score-row" key={s.axis}>
                  <div className="meth__score-left">
                    <span className="meth__score-axis">{s.axis}</span>
                    <span className="meth__score-value" style={{ color: s.color }}>
                      {s.score !== null ? s.score : "\u2014"}
                    </span>
                    <span className="meth__score-label">{s.label}</span>
                  </div>
                  <p className="meth__score-detail">{s.detail}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </MethSection>

      {/* ---- Section 3: Validation ---- */}
      <MethSection index={2}>
        <h3 className="meth__section-title">Validation</h3>
        <p className="meth__body">
          The bias engine is tested against a ground-truth corpus of 42 articles spanning
          9 categories&mdash;from hard-news wire copy to partisan opinion columns to
          tabloid sensationalism. Every article has hand-verified expected scores.
        </p>
        <div className="meth__validation-grid">
          {VALIDATION_STATS.map((stat, i) => (
            <ValidationStat key={stat.label} stat={stat} index={i} />
          ))}
        </div>
        <p className="meth__body">
          A CI gate runs the full validation suite on every commit via GitHub Actions.
          If any axis drifts outside its expected range, the pipeline build fails.
        </p>
        <p className="meth__body meth__body--code">
          The validation suite runs on every commit as a CI gate.
        </p>
      </MethSection>

      {/* ---- Section 4: 419 Curated Sources ---- */}
      <MethSection index={3}>
        <h3 className="meth__section-title">419 Curated Sources</h3>
        <p className="meth__body">
          Every source in the spectrum above was added by hand. Each has a tier
          classification, a baseline political lean, a country of origin, and
          credibility notes written by a human editor.
        </p>
        <div className="meth__source-grid">
          {tierCounts.map((tier) => (
            <div key={tier.tier} className="meth__source-stat">
              <div className="meth__source-stat-head">
                <span className="meth__source-tier">{tier.label}</span>
                <span className="meth__source-count">{tier.count || tier.total}</span>
              </div>
              <div className="meth__source-bar-track">
                <div
                  className="meth__source-bar-fill"
                  style={{ width: `${((tier.count || tier.total) / 419) * 100}%` }}
                />
              </div>
              <div className="meth__source-favicons">
                {tier.sources.slice(0, 7).map((s) => {
                  const fav = s.url ? getFaviconUrlMeth(s.url) : "";
                  return (
                    <span key={s.slug} className="meth__source-fav" title={s.name}>
                      {fav ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={fav} alt="" width={14} height={14} loading="lazy" className="meth__source-fav-img" />
                      ) : (
                        <span className="meth__source-fav-letter">{s.name.charAt(0)}</span>
                      )}
                    </span>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        <div className="meth__source-meta">
          <p className="meth__body">
            The lean spectrum uses 7 zones from Far Left to Far Right. The current
            left-to-right ratio across all 419 sources is <strong>1.54:1</strong>&mdash;a
            deliberate tilt toward the center with representation from both wings.
          </p>
        </div>
      </MethSection>

      {/* ---- Section 5: Transparency ---- */}
      <MethSection index={4} className="meth__section--last">
        <h3 className="meth__section-title">Transparency</h3>
        <p className="meth__body">
          No LLMs. No black-box models. No proprietary data sources. Every score is produced by
          deterministic rule-based NLP&mdash;the same text always produces the same result. Every score
          includes a structured rationale explaining the signals that produced it. Every source carries
          hand-written credibility notes and a documented lean baseline. If a score looks wrong, the
          rationale tells you exactly why it scored that way.
        </p>
      </MethSection>
    </section>
  );
}

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function SourcesPageInner() {
  const [sources, setSources] = useState<SpectrumSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeEdition, setActiveEdition] = useState<Edition>("world");
  const [activeLean, setActiveLean] = useState<LeanFilter>("All");
  const editionGroupRef = useRef<HTMLDivElement>(null);
  const leanGroupRef = useRef<HTMLDivElement>(null);

  // Defer date rendering to client to avoid SSG hydration mismatch (#310)
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  /** Arrow-key navigation within a radiogroup container */
  const handleRadioGroupKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const container = e.currentTarget;
      const radios = Array.from(
        container.querySelectorAll<HTMLButtonElement>('[role="radio"]')
      );
      const idx = radios.indexOf(e.target as HTMLButtonElement);
      if (idx < 0) return;
      const next =
        e.key === "ArrowRight"
          ? radios[(idx + 1) % radios.length]
          : radios[(idx - 1 + radios.length) % radios.length];
      next.focus();
      next.click();
    },
    []
  );

  useEffect(() => {
    const controller = new AbortController();

    async function loadSources() {
      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }
      try {
        const { data, error: fetchError } = await supabase
          .from("sources")
          .select(
            "name, slug, url, tier, country, political_lean_baseline, credibility_notes"
          )
          .order("name");

        if (controller.signal.aborted) return;

        if (fetchError) {
          setError(fetchError.message);
          setIsLoading(false);
          return;
        }

        setSources((data as SpectrumSource[]) || []);
        setIsLoading(false);

        // Deep link: after data loads and Methodology mounts, scroll to hash target.
        // Browser already attempted the scroll before React rendered — retry now.
        requestAnimationFrame(() => {
          const hash = window.location.hash.slice(1);
          if (hash) {
            document.getElementById(hash)?.scrollIntoView({ behavior: "smooth" });
          }
        });
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Failed to load sources"
          );
          setIsLoading(false);
        }
      }
    }

    loadSources();
    return () => controller.abort();
  }, []);

  const filteredSources = useMemo(() => {
    let result = sources;
    const countries = EDITION_COUNTRIES[activeEdition];
    if (countries) result = result.filter((s) => countries.includes(s.country));
    const allowed = LEAN_ALLOWED[activeLean];
    if (allowed) result = result.filter((s) => allowed.includes(normalizeLean(s.political_lean_baseline)));
    return result;
  }, [sources, activeEdition, activeLean]);

  const totalCount = filteredSources.length;

  const handleLeanTap = (lean: LeanFilter) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    setActiveLean(lean === activeLean ? "All" : lean);
  };

  return (
    <div className="page-container">
      {/* ---- Nav header — matches NavBar layout ---- */}
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <div className="nav-left">
            <Link
              href="/"
              aria-label="void --news — home"
              className="nav-logo si-hoverable"
            >
              <span className="nav-logo-desktop">
                <LogoFull height={32} />
              </span>
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>
          </div>

          {/* Edition filter — radiogroup (filters content, not panel switch) */}
          <div
            className="nav-tabs"
            role="radiogroup"
            aria-label="Edition"
            ref={editionGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {EDITIONS.map((edition) => {
              const checked = activeEdition === edition.slug;
              return (
                <button
                  key={edition.slug}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`nav-tab${checked ? " nav-tab--active" : ""}`}
                  onClick={() => setActiveEdition(edition.slug)}
                >
                  <span className="nav-tab__inner">
                    <EditionIcon slug={edition.slug} size={14} />
                    {edition.label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Dateline — desktop only */}
          <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
            {mounted ? `${getEditionTimeOfDay(activeEdition)} Edition` : "Edition"}
            <span className="nav-dateline-inline__sep">&middot;</span>
            {mounted ? formatDateCompact() : ""}
            <span className="nav-dateline-inline__sep">&middot;</span>
            <span className="nav-dateline-inline__time">{mounted ? getEditionTimestamp(activeEdition) : ""}</span>
          </span>

          <div className="nav-right">
            <PageToggle activePage="sources" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      {/* Mobile bottom nav — edition switching */}
      <nav className="nav-bottom" aria-label="Edition navigation">
        {EDITIONS.map((edition) => (
          <button
            key={`mobile-${edition.slug}`}
            aria-current={activeEdition === edition.slug ? "page" : undefined}
            className={`nav-bottom-tab${activeEdition === edition.slug ? " nav-bottom-tab--active" : ""}`}
            onClick={() => setActiveEdition(edition.slug)}
          >
            <span className="nav-tab__inner">
              <EditionIcon slug={edition.slug} size={18} />
              {edition.label}
            </span>
          </button>
        ))}
      </nav>

      <main id="main-content" className="page-main sources-page">
        {/* ---- Toolbar: title + lean filter ---- */}
        <div className="sources-toolbar">
          <div className="sources-toolbar__text">
            <h1 className="sources-toolbar__title" title="void --sources">
              <span className="sources-toolbar__count">{totalCount}</span> Sources
            </h1>
          </div>
          <div
            className="sources-leans"
            role="radiogroup"
            aria-label="Filter by lean"
            ref={leanGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {LEAN_FILTERS.map((lean) => {
              const checked = activeLean === lean;
              return (
                <button
                  key={lean}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`sources-edition-chip${checked ? " sources-edition-chip--active" : ""}`}
                  onClick={() => handleLeanTap(lean)}
                >
                  <span
                    className="filter-chip__dot"
                    style={{ backgroundColor: LEAN_DOT_COLOR[lean] }}
                    aria-hidden="true"
                  />
                  {lean}
                </button>
              );
            })}
          </div>
        </div>

        {/* ---- Loading state ---- */}
        {isLoading && (
          <div className="sources-loading" aria-label="Loading sources">
            <div className="sources-loading__bar skeleton" />
            <div className="sources-loading__logos">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="sources-loading__logo skeleton"
                  style={{ animationDelay: `${i * 60}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ---- Error state ---- */}
        {error && !isLoading && (
          <div className="empty-state">
            <h2 className="text-xl empty-state__title">
              Could not load sources
            </h2>
            <p className="text-base empty-state__body">
              {error}
            </p>
            <button
              className="btn-primary"
              onClick={() => window.location.reload()}
            >
              Try again
            </button>
          </div>
        )}

        {/* ---- Empty state ---- */}
        {!isLoading && !error && sources.length === 0 && (
          <div className="empty-state">
            <LogoIcon size={48} animation="analyzing" />
            <h2 className="text-xl empty-state__title">
              No sources found
            </h2>
            <p className="text-base empty-state__body--no-margin">
              Sources will appear once the pipeline syncs them to the database.
            </p>
          </div>
        )}

        {/* ---- Spectrum visualization ---- */}
        {!isLoading && !error && filteredSources.length > 0 && (
          <>
            <SpectrumChart sources={filteredSources} />
            <div className="meth__skip-link-wrap">
              <a href="#methodology" className="meth__skip-link">
                How we score &darr;
              </a>
            </div>
          </>
        )}

        {!isLoading && !error && filteredSources.length === 0 && sources.length > 0 && (
          <div className="empty-state empty-state--inline">
            <p className="text-base empty-state__body--no-margin">
              No sources match the current filters.
            </p>
            <button
              className="btn-secondary"
              onClick={() => { setActiveEdition("world"); setActiveLean("All"); }}
            >
              Clear filters
            </button>
          </div>
        )}

        {/* ---- Methodology (trust anchor) ---- */}
        {!isLoading && !error && sources.length > 0 && (
          <Methodology sources={sources} />
        )}
      </main>

      <Footer />
    </div>
  );
}

export default function SourcesPage() {
  return (
    <ErrorBoundary>
      <SourcesPageInner />
    </ErrorBoundary>
  );
}
