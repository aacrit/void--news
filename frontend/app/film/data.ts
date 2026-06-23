/* ==========================================================================
   film/data.ts — Canonical content for the unified About + onboarding
   experience (app/components/about/*).

   Single source of truth for the interactive beats. Numbers here are kept
   in lockstep with the real codebase (sources.json, importance_ranker).
   ========================================================================== */

/* ── Canonical source counts (data/sources.json — verified) ───────────────
   Use these everywhere instead of hard-coding, so the figures can't drift. */
export const SOURCE_TIERS = {
  usMajor: 43,
  international: 373,
  independent: 600,
  total: 1016,
  countries: 158,
} as const;

/* ── Beat 1 — "Same story, five headlines" ──────────────────────────────── */

export interface DivergentHeadline {
  outlet: string;
  lean: string;
  /** True text lean 0-100 (drives the chip's spectrum position + color). */
  leanScore: number;
  headline: string;
}

// Illustrative — one real-world-shaped event, five framings. Kept internally
// consistent (same administration throughout).
export const DIVERGENT_HEADLINES: DivergentHeadline[] = [
  {
    outlet: "Reuters",
    lean: "Center",
    leanScore: 50,
    headline: "US and China resume trade talks amid tariff tensions",
  },
  {
    outlet: "The Guardian",
    lean: "Center-Left",
    leanScore: 38,
    headline: "Trade-war uncertainty looms as US-China negotiations resume",
  },
  {
    outlet: "Al Jazeera",
    lean: "Center-Left",
    leanScore: 35,
    headline: "Global markets brace as superpowers return to the table",
  },
  {
    outlet: "Fox News",
    lean: "Right",
    leanScore: 72,
    headline: "Administration takes hard line as China trade talks restart",
  },
  {
    outlet: "New York Post",
    lean: "Right",
    leanScore: 74,
    headline: "China comes crawling back to the negotiating table",
  },
];

/* ── Beat 2 — "The mark that shows the bias" (Learn more) ─────────────────
   Source for the optional methodology disclosure. Matches the real engine. */

export interface BiasAxis {
  name: string;
  brief: string;
  signals: string;
}

export const SIX_AXES: BiasAxis[] = [
  {
    name: "Political Lean",
    brief: "Where the article's language falls, left to right.",
    signals: "Keyword lexicons, entity sentiment (NER + TextBlob), framing phrases, length-adaptive source-baseline blending.",
  },
  {
    name: "Sensationalism",
    brief: "How much urgency is inflated beyond the facts.",
    signals: "Clickbait patterns, superlative density, TextBlob extremity, partisan-attack density.",
  },
  {
    name: "Opinion vs. Reporting",
    brief: "Whether it reports facts or argues a position.",
    signals: "First-person pronouns, subjectivity, attribution density, value judgments, rhetorical questions.",
  },
  {
    name: "Factual Rigor",
    brief: "How thoroughly it cites named sources and data.",
    signals: "Named sources via NER + attribution verbs, org citations, data patterns, direct quotes.",
  },
  {
    name: "Framing",
    brief: "Whether word choices nudge the reader.",
    signals: "50+ charged synonym pairs, omission detection, headline-body divergence, passive voice.",
  },
  {
    name: "Outlet Tracking",
    brief: "How each outlet covers each topic over time.",
    signals: "Per-topic per-outlet EMA with adaptive alpha, stored across pipeline runs.",
  },
];

/* ── Beat 3 — "We rank by importance, not clicks" ─────────────────────────
   The real ranker (pipeline/ranker/importance_ranker.py) uses 10 signals:
   nine weighted contributors below + a soft-news category gate (0.78x
   multiplier) as the tenth. Bias-blind by design. */

export interface RankingSignal {
  name: string;
  weight: number;
}

export const RANKING_SIGNALS: RankingSignal[] = [
  { name: "Source breadth", weight: 20 },
  { name: "Story maturity", weight: 16 },
  { name: "Tier diversity", weight: 13 },
  { name: "Consequentiality", weight: 10 },
  { name: "Institutional authority", weight: 8 },
  { name: "Factual density", weight: 8 },
  { name: "Divergence", weight: 7 },
  { name: "Perspective diversity", weight: 6 },
  { name: "Geographic impact", weight: 6 },
];

/** Tenth signal is a gate, not a positive weight. */
export const RANKING_GATE = "Soft-news category gate (0.78×)";
export const RANKING_SIGNAL_COUNT = 10;

/* ── Beat 4 — "Read with clarity" ────────────────────────────────────────
   Headline numbers (verified against the live codebase). */

export const NUMBERS = [
  { value: "1,016", label: "sources" },
  { value: "158", label: "countries" },
  { value: "6", label: "bias axes" },
  { value: "$0", label: "to read" },
  { value: "0", label: "accounts" },
  { value: "0", label: "tracking" },
];

/* ── Product family (page-only footer, not shown in the overlay) ──────────
   Production-available products only. Weekly / Paper / OnAir / Games are
   parked (not production-ready) and intentionally omitted. */

export interface ProductWorld {
  cli: string;
  name: string;
  desc: string;
  href: string;
}

export const PRODUCT_FAMILY: ProductWorld[] = [
  { cli: "void --news", name: "The Feed", desc: "One daily feed. Top 50 stories, ranked once.", href: "/" },
  { cli: "void --sources", name: "The Spectrum", desc: "Every source we read, on one axis.", href: "/sources" },
  { cli: "void --history", name: "The Archive", desc: "Historical events, told from every side.", href: "/history" },
  { cli: "void --ship", name: "The Forge", desc: "Tell us what to build next.", href: "/ship" },
];

/* ── First principles (page-only footer) ─────────────────────────────────── */

export const FIRST_PRINCIPLES = [
  "Every reader sees the same stories in the same order.",
  "Every score traces to specific words in the text.",
  "Every feature is free. There is no premium tier. There never will be.",
];

/* ── Beats — the 4 chapters of the unified experience ─────────────────────
   Plain, user-focused copy. Deeper detail lives behind each beat's
   "Learn more" disclosure, not in the headline layer. */

export interface Beat {
  id: "void" | "sigil" | "engine" | "verdict";
  headline: string;
  body: string;
}

export const BEATS: Beat[] = [
  {
    id: "void",
    headline: "One story. Five versions.",
    body: "The same event becomes five different stories depending on who tells it. Drag each headline to where its language actually lands.",
  },
  {
    id: "sigil",
    headline: "One mark reads the bias.",
    body: "Every story carries this mark. The beam is the lean. The ring is how many sources cover it. When sources disagree, it splits. Try it.",
  },
  {
    id: "engine",
    headline: "Ranked by what matters.",
    body: "1,016 sources across 158 countries. We order the feed by importance, never by what gets the most clicks.",
  },
  {
    id: "verdict",
    headline: "Read with clarity.",
    body: "Broad coverage from across the spectrum, grounded in named sources, is where confidence lives. Thin coverage from one corner? Read it with more scrutiny.",
  },
];
