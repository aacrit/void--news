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
  { value: "50", label: "top stories" },
  { value: "1×", label: "a day" },
  { value: "6", label: "bias axes" },
  { value: "$0", label: "to read" },
  { value: "0", label: "accounts" },
  { value: "0", label: "tracking" },
];

/* ── Product family (page-only footer, not shown in the overlay) ──────────
   The live void suite. Paper and Games are still parked (hidden from nav,
   not production-ready) and intentionally omitted here. */

export interface ProductWorld {
  /** Plain newspaper name — the card heading (e.g. "Void News", "Weekly"). */
  name: string;
  /** Poetic subtitle, rendered italic beneath the name (e.g. "The Front Page"). */
  subtitle: string;
  desc: string;
  href: string;
  /** Brand accent for light mode ("Morning Edition"). */
  accentLight: string;
  /** Brand accent for dark mode ("Evening Edition"). */
  accentDark: string;
  /** When true, the card shows a small "Coming soon" chip. */
  comingSoon?: boolean;
  /** Tooltip text for the coming-soon chip. */
  soonNote?: string;
}

// Each product carries its own brand accent, chosen to read on both the light
// card background (~#F5F0E4) and the dark card background (~#333028).

// The products — the things you read and listen to.
export const PRODUCT_FAMILY: ProductWorld[] = [
  { name: "Void News", subtitle: "The Front Page", desc: "One daily front page. The 50 stories that matter, ranked once.", href: "/", accentLight: "#6B4423", accentDark: "#C9A88A" },
  { name: "Weekly", subtitle: "The Magazine", desc: "The week, read like a magazine. Covers, essays, an editorial.", href: "/weekly", accentLight: "#B23A2A", accentDark: "#E0705C" },
  { name: "History", subtitle: "The Archive", desc: "Consequential events, told from every side.", href: "/history", accentLight: "#8A6410", accentDark: "#D4A574" },
  { name: "Revolt", subtitle: "The Anatomy", desc: "Every revolution on one arc, past and unfolding.", href: "/revolt", accentLight: "#1E40AF", accentDark: "#6AA0FF" },
  { name: "On Air", subtitle: "The Broadcast", desc: "The daily brief, read aloud.", href: "/onair", accentLight: "#2E8B7D", accentDark: "#4DAFA0" },
];

// Transparency and feedback tools — how the work stays honest and open, not
// products in their own right.
export const TRANSPARENCY_TOOLS: ProductWorld[] = [
  { name: "Sources", subtitle: "The Spectrum", desc: "All 1,016 sources we read, placed on one axis.", href: "/sources", accentLight: "#3F7A5A", accentDark: "#77B994" },
  { name: "Ship", subtitle: "The Forge", desc: "Request it, vote, watch it ship. Deferred and not-feasible requests are tracked honestly.", href: "/ship", accentLight: "#BE4326", accentDark: "#D2593A" },
];

/* ── First principles (page-only footer) ─────────────────────────────────── */

export const FIRST_PRINCIPLES = [
  "A front page, not a feed. The same 50 stories, in the same order, for every reader.",
  "Every bias score traces to specific words in the text. No black box, no opinion.",
  "Free, forever. No account, no tracking, no premium tier. There never will be.",
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
    body: "The same event becomes five different stories depending on who tells it. That spin is usually invisible. Drag each headline to where its language actually lands, and watch the bias appear.",
  },
  {
    id: "sigil",
    headline: "One mark reads the bias.",
    body: "Every story on Void carries this mark, measured from the words themselves, not from who published it. The beam is the lean. The ring is how many sources cover it. When they disagree, it splits. Try it.",
  },
  {
    id: "engine",
    headline: "A front page, not a feed.",
    body: "A newspaper prints one front page, the same for everyone. So do we: the 50 stories that matter most each day, chosen once by importance, never by what you click. No endless scroll, no feed tuned to you. Here is what decides the order.",
  },
  {
    id: "verdict",
    headline: "Read with clarity.",
    body: "Broad coverage from across the spectrum, grounded in named sources, is where confidence lives. Thin coverage from one corner deserves more scrutiny. Void gives you the whole picture, measured, so you decide what to trust.",
  },
];
