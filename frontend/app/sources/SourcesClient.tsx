"use client";

// Route-scoped CSS — sources page is the only consumer of spectrum.css.
// Moving the import here removes ~80KB gzipped from globals/homepage bundle.
import "../styles/spectrum.css";

import { useState, useEffect, useMemo, useCallback } from "react";
import Link from "next/link";
import { supabase, supabaseError, fetchMethodologyArticles, fetchLastPipelineRun } from "../lib/supabase";
import {
  leanLabel,
  senseLabel,
  rigorLabel,
} from "../lib/biasColors";
import SpectrumChart, { type SpectrumSource, normalizeLean } from "../components/SpectrumChart";
import NavBar from "../components/NavBar";
import LogoIcon from "../components/LogoIcon";
import Footer from "../components/Footer";
// Canonical curated-source total (data/sources.json — verified). Single source
// of truth so the /sources header, the finale hero, and the About page can't
// drift apart (F9). Live DB row count can include inactive/duplicate rows.
import { SOURCE_TIERS } from "../film/data";
import ErrorBoundary from "../components/ErrorBoundary";
import { useInView } from "../lib/sharedObserver";

/* ---------------------------------------------------------------------------
   Sources Page — /sources
   Visualizes all curated news sources on a political lean spectrum.
   Desktop: horizontal spectrum bar with logos above/below.
   Mobile: horizontal swipeable card strip with scroll-snap.
   --------------------------------------------------------------------------- */

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
    range: "0 to 100",
    low: "Far Left",
    high: "Far Right",
    what: "Where an article falls on the left-right spectrum, read from two things: the outlet\u2019s track record and the article\u2019s own words. On a short item the record weighs more; on a full article the words weigh more.",
    signals: [
      "Keyword frequency against curated left/right phrase lists",
      "Positive or negative tone around named political figures",
      "Framing phrases that signal ideological perspective",
      "Length-adaptive scoring blended with each outlet\u2019s historical baseline",
    ],
  },
  {
    id: "sensationalism",
    name: "Sensationalism",
    range: "0 to 100",
    low: "Measured",
    high: "Inflammatory",
    what: "How much the article inflates urgency, emotion, or outrage beyond what the facts warrant.",
    signals: [
      "Clickbait headline patterns (questions, listicles, superlatives)",
      "Superlative density across the text",
      "Emotional extremity score",
      "Partisan attack density (capped at 30 points)",
    ],
  },
  {
    id: "opinion",
    name: "Opinion vs Reporting",
    range: "0 to 100",
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
    range: "0 to 100",
    low: "Unsourced",
    high: "Well-sourced",
    what: "How thoroughly an article cites named sources, data, and direct quotes.",
    signals: [
      "Named sources identified through attribution verbs",
      "Organizational citations (agencies, institutions)",
      "Data patterns (percentages, dollar figures, dates)",
      "Direct quotes count; vague-source penalty (\u201cofficials say\u201d)",
    ],
  },
  {
    id: "framing",
    name: "Framing",
    range: "0 to 100",
    low: "Neutral",
    high: "Heavy Framing",
    what: "Whether word choices, omissions, or structural decisions nudge the reader toward a conclusion.",
    signals: [
      "Charged synonym detection (50+ curated word pairs)",
      "Cluster-aware omission analysis (what peers cover that this article skips)",
      "Headline-body divergence score",
      "Passive voice frequency (capped at 30 points)",
    ],
  },
  {
    id: "tracking",
    name: "Outlet Tracking",
    range: "Adaptive",
    low: "New outlet",
    high: "Established",
    what: "Tracks how each outlet covers each topic over time, weighting recent articles more heavily.",
    signals: [
      "Newer outlets weighted more toward recent articles; established outlets draw on deeper history",
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
    { axis: "Outlet Tracking", score: null, color: "var(--fg-muted)", label: "EMA: 47.2", detail: "For example, an outlet\u2019s economy coverage might average 47.2 (center) across the articles tracked on that topic." },
  ],
};

/* ---------------------------------------------------------------------------
   Axis Glyph SVGs — inline, 40x40 viewBox, stroke-based
   Scaled up for the cinematic infographic stamps.
   --------------------------------------------------------------------------- */

function AxisGlyph({ id, size = 40 }: { id: string; size?: number }) {
  const props = { width: size, height: size, viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.6, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true as const, className: "meth-dot__glyph" };

  switch (id) {
    case "lean":
      return (<svg {...props}><line x1="3" y1="8" x2="17" y2="8" /><polygon points="10,18 7,13 13,13" fill="none" /></svg>);
    case "sensationalism":
      return (<svg {...props}><rect x="8" y="3" width="4" height="14" rx="2" /><line x1="10" y1="12" x2="10" y2="10" strokeWidth="2.5" /></svg>);
    case "opinion":
      return (<svg {...props}><rect x="3" y="3" width="14" height="14" rx="1" /><line x1="10" y1="4" x2="10" y2="16" strokeDasharray="2 2" /><line x1="5" y1="7" x2="8" y2="7" /><line x1="5" y1="10" x2="8" y2="10" /><path d="M12 7 Q13 6 14 7 Q15 8 16 7" /></svg>);
    case "rigor":
      return (<svg {...props}><path d="M6 3 L4 3 L4 17 L6 17" /><line x1="7" y1="7" x2="14" y2="7" /><line x1="7" y1="10" x2="16" y2="10" /><line x1="7" y1="13" x2="12" y2="13" /></svg>);
    case "framing":
      return (<svg {...props}><circle cx="9" cy="9" r="5" /><line x1="13" y1="13" x2="17" y2="17" /><path d="M6 9 Q7.5 7 9 9 Q10.5 11 12 9" strokeWidth="1.4" /></svg>);
    case "tracking":
      return (<svg {...props}><polyline points="3,14 6,8 9,11 13,5 17,9" /></svg>);
    default:
      return null;
  }
}

/* Detail panel glyph (smaller, used in expanded detail) */
function AxisGlyphSmall({ id }: { id: string }) {
  const props = { width: 20, height: 20, viewBox: "0 0 20 20", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true as const, className: "meth-dot-detail__glyph" };

  switch (id) {
    case "lean":
      return (<svg {...props}><line x1="3" y1="8" x2="17" y2="8" /><polygon points="10,18 7,13 13,13" fill="none" /></svg>);
    case "sensationalism":
      return (<svg {...props}><rect x="8" y="3" width="4" height="14" rx="2" /><line x1="10" y1="12" x2="10" y2="10" strokeWidth="2.5" /></svg>);
    case "opinion":
      return (<svg {...props}><rect x="3" y="3" width="14" height="14" rx="1" /><line x1="10" y1="4" x2="10" y2="16" strokeDasharray="2 2" /><line x1="5" y1="7" x2="8" y2="7" /><line x1="5" y1="10" x2="8" y2="10" /><path d="M12 7 Q13 6 14 7 Q15 8 16 7" /></svg>);
    case "rigor":
      return (<svg {...props}><path d="M6 3 L4 3 L4 17 L6 17" /><line x1="7" y1="7" x2="14" y2="7" /><line x1="7" y1="10" x2="16" y2="10" /><line x1="7" y1="13" x2="12" y2="13" /></svg>);
    case "framing":
      return (<svg {...props}><circle cx="9" cy="9" r="5" /><line x1="13" y1="13" x2="17" y2="17" /><path d="M6 9 Q7.5 7 9 9 Q10.5 11 12 9" strokeWidth="1.4" /></svg>);
    case "tracking":
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
    case "tracking": return "\u2014";
    default: return "";
  }
}



/* ---------------------------------------------------------------------------
   AxisDotGrid — 3x2 cluster of large ink-stamp axis cards.
   Glyph centered inside each stamp. Click to expand detail below.
   Rack-focus: when one is active, siblings dim and blur.
   --------------------------------------------------------------------------- */

function AxisDotGrid({
  axes,
  scores,
  visible,
}: {
  axes: typeof AXES_DATA;
  scores: (number | null)[];
  visible: boolean;
}) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedAxis = axes.find(a => a.id === selectedId);
  const selectedScore = selectedId ? scores[axes.findIndex(a => a.id === selectedId)] : null;

  return (
    <>
      <div className={`meth-dot-grid${selectedId ? " meth-dot-grid--has-active" : ""}`} role="group" aria-label="Six-axis bias scores">
        {axes.map((axis, i) => {
          const isTracking = axis.id === "tracking";
          const displayScore = scores[i] !== null ? scores[i] : (isTracking ? null : 50);
          const dotCount = displayScore !== null ? Math.max(1, Math.round(((displayScore as number) / 100) * 5)) : 0;
          const isActive = selectedId === axis.id;

          return (
            <button
              key={axis.id}
              className={`meth-dot${isActive ? " meth-dot--active" : ""}${visible ? " meth-dot--visible" : ""}`}
              style={{ "--dot-delay": `${i * 60}ms` } as React.CSSProperties}
              onClick={() => setSelectedId(isActive ? null : axis.id)}
              aria-expanded={isActive}
              aria-controls={`meth-dot-detail-${axis.id}`}
            >
              <span className="meth-dot__glyph-wrap">
                <AxisGlyph id={axis.id} />
              </span>
              <span className="meth-dot__name">{axis.name}</span>
              <span className="meth-dot__dots" aria-label={`${displayScore ?? 0} out of 100`}>
                {Array.from({ length: 5 }, (_, di) => (
                  <span key={di} className={`meth-dot__pip${di < dotCount ? " meth-dot__pip--filled" : ""}`} />
                ))}
              </span>
              <span className="meth-dot__label">{getAxisLabel(axis.id, displayScore)}</span>
            </button>
          );
        })}
      </div>

      {/* Shared detail panel below grid */}
      <div
        className={`meth-dot-detail${selectedId ? " meth-dot-detail--open" : ""}`}
        id={selectedId ? `meth-dot-detail-${selectedId}` : undefined}
        role="region"
        aria-label={selectedAxis ? `${selectedAxis.name} details` : undefined}
        aria-hidden={!selectedId}
      >
        {selectedAxis && (
          <div className="meth-dot-detail__inner">
            <div className="meth-dot-detail__head">
              <AxisGlyphSmall id={selectedAxis.id} />
              <span className="meth-dot-detail__name">{selectedAxis.name}</span>
              {selectedScore !== null && (
                <span className="meth-dot-detail__score">{selectedScore}</span>
              )}
            </div>
            <p className="meth-axis__what">{selectedAxis.what}</p>
            <ul className="meth-axis__signals">
              {selectedAxis.signals.map((s, si) => (
                <li key={si} className="meth-axis__signal">{s}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------
   InfographicScene — scroll-revealed scene for the cinematic infographic.
   Alternating L/R callout+viz layout. Parallax stagger: visualizations
   enter with a slightly later delay than text callouts.
   --------------------------------------------------------------------------- */

function InfographicScene({
  layout = "lr",
  children,
}: {
  layout?: "lr" | "rl" | "full";
  children: React.ReactNode;
}) {
  const [ref, visible] = useInView<HTMLDivElement>();
  return (
    <div
      ref={ref}
      className={`meth-scene meth-scene--${layout}${visible ? " meth-scene--visible" : ""}`}
    >
      {children}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Validation + Sources — compact inline stats, no progress bars
   --------------------------------------------------------------------------- */

/* ---------------------------------------------------------------------------
   ArticlePicker — live article selection for the autopsy
   --------------------------------------------------------------------------- */

interface MethodologyArticle {
  id: string;
  title: string;
  published_at: string;
  summary: string | null;
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

function getFaviconUrlMeth(_sourceUrl: string): string {
  // Privacy: never call an external favicon service. Fetching a third-party
  // favicon would leak the reader's IP and which publisher they are viewing to
  // that host. The self-contained letter monogram fallback renders instead.
  return "";
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
    <div className="meth-rationale-signals">
      {signals.map((s) => (
        <div key={s.label} className="meth-rationale-signals__row">
          <span className="meth-rationale-signals__label">{s.label}</span>
          <span className="meth-rationale-signals__value">{s.value}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Methodology — "The Scoring Stage"
   --------------------------------------------------------------------------- */

function Methodology({ sources }: { sources: SpectrumSource[] }) {
  /* Scene 1: Dot grid state */
  const [dotRef, dotVisible] = useInView<HTMLDivElement>();

  /* Scene 2: Live articles */
  const [articles, setArticles] = useState<MethodologyArticle[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  /* Neutral initial scores for dot grid (before article selection) */
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

  /* Handle article selection */
  const handleSelectArticle = useCallback((idx: number) => {
    setSelectedIdx(idx);
  }, []);

  /* Active rationale for tree decomposition */
  const activeRationale = useMemo(() => {
    if (selectedIdx === null || !articles[selectedIdx]) return null;
    return articles[selectedIdx].bias_scores?.[0]?.rationale ?? null;
  }, [selectedIdx, articles]);

  /* Tier data for source bar visualization */
  const tierCounts = useMemo(() => {
    const tiers = [
      { tier: "us_major", label: "US Major", count: 0, total: SOURCE_TIERS.usMajor, sources: [] as SpectrumSource[] },
      { tier: "international", label: "International", count: 0, total: SOURCE_TIERS.international, sources: [] as SpectrumSource[] },
      { tier: "independent", label: "Independent", count: 0, total: SOURCE_TIERS.independent, sources: [] as SpectrumSource[] },
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

  /* L:R ratio computed from source lean baselines */
  const lrRatio = useMemo(() => {
    const LEFT_LEANS = new Set(["far-left", "left", "center-left"]);
    const RIGHT_LEANS = new Set(["far-right", "right", "center-right"]);
    let left = 0, right = 0;
    for (const s of sources) {
      const lean = s.political_lean_baseline;
      if (lean && LEFT_LEANS.has(lean)) left++;
      else if (lean && RIGHT_LEANS.has(lean)) right++;
    }
    return right > 0 ? (left / right).toFixed(2) : "1.20";
  }, [sources]);

  /* Collect all source favicons for the river (up to 60).
     Gated behind `mounted`: the Math.random() shuffle is non-deterministic, so
     running it during the build-time server render and again at client
     hydration would produce different orders and a React #418 mismatch. Before
     mount it yields [] on BOTH sides (identical markup); the shuffle runs
     client-only after hydration. */
  const [riverMounted, setRiverMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setRiverMounted(true); }, []);
  const riverSources = useMemo(() => {
    if (!riverMounted) return [];
    const shuffled = [...sources].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 60);
  }, [sources, riverMounted]);

  return (
    <section id="methodology" className="meth meth-infographic" aria-label="Scoring methodology">
      <h2 className="sr-only">Scoring Methodology</h2>

      {/* ================================================================
          Scene 1: "Every Article, Six Lenses"
          Text LEFT, Visualization RIGHT (giant ink stamps)
          ================================================================ */}
      <InfographicScene layout="lr">
        <div className="meth-scene__callout">
          <h3 className="meth-scene__heading">Two Things, Six Lenses</h3>
          <p className="meth__body">
            Most bias tools assign one fixed score to an entire outlet, as if
            every article from it leaned the same way. Void News looks at two
            things instead: what the outlet has published before, and what this
            specific article actually says. Both, across six axes, by rule-based
            NLP. No LLM calls. The same text always produces the same scores.
            On a short wire item there is little text to read, so the outlet&rsquo;s
            track record carries more of the score. On a full article, the words
            carry more. Sensationalism, opinion, and framing are read from the
            words of a full article. Every score discloses how it was reached.
          </p>
        </div>
        <div className="meth-scene__viz" ref={dotRef}>
          <AxisDotGrid axes={AXES_DATA} scores={activeScores} visible={dotVisible} />
        </div>
      </InfographicScene>

      {/* ================================================================
          Scene 2: "Live Autopsy"
          Visualization LEFT (picker + rationale), Text RIGHT
          ================================================================ */}
      <InfographicScene layout="rl">
        <div className="meth-scene__callout">
          <h3 className="meth-scene__heading">Live Autopsy</h3>
          <p className="meth__body">
            Pick any article. Watch the scores populate in real time.
            Every number traces back to a signal decomposition: keyword
            counts, entity sentiments, attribution density. Every score shows its work.
          </p>
        </div>
        <div className="meth-scene__viz">
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
                        <>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={favicon}
                            alt=""
                            width={16}
                            height={16}
                            loading="lazy"
                            className="meth-picker__favicon"
                            onError={(e) => {
                              // Silent, graceful swap to the letter monogram.
                              // No console.log — the error event is handled here
                              // so it never surfaces as an uncaught error (F7).
                              const t = e.currentTarget;
                              t.style.display = "none";
                              const fb = t.nextElementSibling as HTMLElement | null;
                              if (fb) fb.style.display = "flex";
                            }}
                          />
                          <span className="meth-picker__fallback" style={{ display: "none" }}>
                            {article.source?.name?.charAt(0) ?? "?"}
                          </span>
                        </>
                      ) : (
                        <span className="meth-picker__fallback">{article.source?.name?.charAt(0) ?? "?"}</span>
                      )}
                    </span>
                    <span className="meth-picker__source">{article.source?.name ?? "Unknown"}</span>
                    <span className="meth-picker__headline">{article.title}</span>
                  </button>
                );
              })
            ) : (
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
                <span className="meth-picker__headline">{WORKED_EXAMPLE.headline}</span>
              </button>
            )}
          </div>

          {/* Rationale grid */}
          {selectedIdx !== null && activeRationale && (
            <div className="meth-rationale-grid">
              {AXES_DATA.filter(a => a.id !== "tracking").map((axis, i) => {
                const score = activeScores[i];
                return (
                  <div key={axis.id} className="meth-rationale-card">
                    <span className="meth-rationale-card__name">{axis.name}</span>
                    <span className="meth-rationale-card__score">{score ?? "\u2014"}</span>
                    <RationaleTree axisId={axis.id} rationale={activeRationale} />
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </InfographicScene>

      {/* ================================================================
          Scene 3: "Validated. Tested. Proven."
          Text LEFT, Visualization RIGHT (ink stamp numbers)
          ================================================================ */}
      <InfographicScene layout="lr">
        <div className="meth-scene__callout">
          <h3 className="meth-scene__heading">42 articles, scored blind, checked by hand.</h3>
          <p className="meth__body">
            42 ground-truth articles across 9 categories. Each scored by the engine,
            then verified by hand against editorial consensus. A cross-axis correlation
            gate ensures no two axes are secretly measuring the same thing.
          </p>
        </div>
        <div className="meth-scene__viz">
          <div className="meth-stats-strip" role="list" aria-label="Validation statistics">
            <div className="meth-stats-strip__item" role="listitem">
              <span className="meth-stats-strip__number">42</span>
              <span className="meth-stats-strip__label">ground truth</span>
            </div>
            <div className="meth-stats-strip__item" role="listitem">
              <span className="meth-stats-strip__number">9</span>
              <span className="meth-stats-strip__label">categories</span>
            </div>
            <div className="meth-stats-strip__item" role="listitem">
              <span className="meth-stats-strip__number meth-stats-strip__number--formula">r{"\u2009<\u2009"}0.70</span>
              <span className="meth-stats-strip__label">cross-axis</span>
            </div>
          </div>
        </div>
      </InfographicScene>

      {/* ================================================================
          Scene 4: "Hand-Curated." — Full-width grand finale
          Big number, source favicon river, tier stamps, closing line
          ================================================================ */}
      <InfographicScene layout="full">
        <div className="meth-finale">
          {/* Hero count — giant ink circle around source number */}
          <div className="meth-finale__hero">
            <span className="meth-finale__count">{SOURCE_TIERS.total.toLocaleString()}</span>
            <span className="meth-finale__subtitle">Hand-Curated Sources</span>
          </div>

          {/* Favicon river — flowing wrap of source logos */}
          <div className="meth-river" aria-label="Source logos">
            <div className="meth-river__flow">
              {riverSources.map((s, i) => {
                const fav = s.url ? getFaviconUrlMeth(s.url) : "";
                const yOffset = [0, -2, 1, -1, 2, 0, -2, 1, 2, -1][i % 10];
                return (
                  <span
                    key={s.slug}
                    className="meth-river__fav"
                    title={s.name}
                    style={{ "--river-y": `${yOffset}px`, "--river-delay": `${i * 20}ms` } as React.CSSProperties}
                  >
                    {fav ? (
                      <>
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={fav}
                          alt=""
                          width={18}
                          height={18}
                          loading="lazy"
                          className="meth-river__fav-img"
                          onError={(e) => {
                            // Silent, graceful swap to the letter monogram (F7).
                            const t = e.currentTarget;
                            t.style.display = "none";
                            const fb = t.nextElementSibling as HTMLElement | null;
                            if (fb) fb.style.display = "flex";
                          }}
                        />
                        <span className="meth-river__fav-letter" style={{ display: "none" }}>
                          {s.name.charAt(0)}
                        </span>
                      </>
                    ) : (
                      <span className="meth-river__fav-letter">{s.name.charAt(0)}</span>
                    )}
                  </span>
                );
              })}
            </div>
          </div>

          {/* Tier stamps among the flow */}
          <div className="meth-tier-stamps">
            {tierCounts.map((tier) => (
              <div key={tier.tier} className="meth-tier-stamp">
                <span className="meth-tier-stamp__label">{tier.label}</span>
                <span className="meth-tier-stamp__count">{tier.count || tier.total}</span>
              </div>
            ))}
          </div>

          {/* Closing line */}
          <p className="meth__body meth-finale__closing">
            7 lean zones. L:R ratio <strong>{lrRatio}:1</strong>.
            Every score is deterministic. Same text, same result.
            Every score includes a structured rationale.
            If a score looks wrong, the rationale tells you why.
          </p>
        </div>
      </InfographicScene>
    </section>
  );
}

function SourcesPageInner({ initialSources }: { initialSources: SpectrumSource[] }) {
  // Seed from the build-time list (data/sources.json) so the served HTML ships
  // the full source list for SEO + instant paint. The effect below still
  // revalidates from Supabase (live credibility notes / claim accuracy) but
  // never blanks the prerendered list on failure.
  const hasInitial = initialSources.length > 0;
  const [sources, setSources] = useState<SpectrumSource[]>(initialSources);
  const [isLoading, setIsLoading] = useState(!hasInitial);
  const [error, setError] = useState<string | null>(null);

  // Edition build time (pipeline completed_at) — drives the NavBar masthead
  // "as of" dateline so it shows the same edition time as the home feed. NavBar
  // formats the DATE in UTC and the TIME in the viewer's LOCAL zone after mount
  // (getEditionTimestampLocal), so every surface agrees on the same instant.
  const [editionBuiltAt, setEditionBuiltAt] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    fetchLastPipelineRun().then((run) => {
      if (alive && run?.completed_at) setEditionBuiltAt(run.completed_at as string);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSources() {
      if (!supabase) {
        // Keep the prerendered list rather than surfacing a connect error.
        if (!hasInitial) setError(supabaseError ?? "Unable to connect to data source.");
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
          if (!hasInitial) setError(fetchError.message);
          setIsLoading(false);
          return;
        }

        // Only replace the seeded list when the DB actually returns rows;
        // an empty response keeps the prerendered list on screen.
        const rows = (data as SpectrumSource[]) || [];
        if (rows.length > 0) setSources(rows);
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
          if (!hasInitial) {
            setError(
              err instanceof Error ? err.message : "Failed to load sources"
            );
          }
          setIsLoading(false);
        }
      }
    }

    loadSources();
    return () => controller.abort();
  }, [hasInitial]);

  return (
    <div className="page-container">
      {/* PWA back nav — visible on mobile */}
      <Link href="/" className="pwa-back" aria-label="Back to news feed">
        <span aria-hidden="true">&larr;</span> News Feed
      </Link>
      {/* Shared masthead — identical top chrome to the home feed (tagline,
          edition timestamp, experimental badge, page links, theme toggle). */}
      <NavBar editionBuiltAt={editionBuiltAt} />

      <main id="main-content" className="page-main sources-page">
        {/* ---- Toolbar: title ---- */}
        <div className="sources-toolbar">
          <div className="sources-toolbar__text">
            <h1 className="sources-toolbar__title" title="Sources">
              <span className="sources-toolbar__count">{SOURCE_TIERS.total.toLocaleString()}</span> Sources
            </h1>
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
        {!isLoading && !error && sources.length > 0 && (
          <>
            <SpectrumChart sources={sources} />
            <div className="meth__skip-link-wrap">
              <a href="#methodology" className="meth__skip-link">
                How we score &rarr;
              </a>
            </div>
          </>
        )}

        {/* Scoring methodology — anchor target for #methodology deep links
            (DeepDive "How we score" + the in-page skip link above).
            Rendered UNCONDITIONALLY: gating it behind !isLoading excluded
            id="methodology" from the SSG prerender (isLoading starts true),
            so cold deep links and crawlers found no anchor in the static
            HTML. The component takes sources for its live examples
            but its prose + anchor must exist before any fetch resolves. */}
        <Methodology sources={sources} />
      </main>

      <Footer />
    </div>
  );
}

export default function SourcesClient({ initialSources }: { initialSources: SpectrumSource[] }) {
  return (
    <ErrorBoundary>
      <SourcesPageInner initialSources={initialSources} />
    </ErrorBoundary>
  );
}
