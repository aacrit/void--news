/* ==========================================================================
   film/data.ts — Canonical content constants for "The Film"

   Single source of truth for all demo/onboarding/about-page content.
   Both the prologue (onboarding carousel) and manifesto (about page)
   import from here. Change once, both surfaces update.
   ========================================================================== */

/* ── Divergent Headlines — Scene I: "The Void" ── */

export interface DivergentHeadline {
  outlet: string;
  lean: string;
  leanScore: number;
  color: string;
  headline: string;
}

export const DIVERGENT_HEADLINES: DivergentHeadline[] = [
  {
    outlet: "Reuters",
    lean: "Center",
    leanScore: 48,
    color: "var(--bias-center)",
    headline: "\u201CUS and China resume trade talks amid tariff tensions\u201D",
  },
  {
    outlet: "Fox News",
    lean: "Right",
    leanScore: 72,
    color: "var(--bias-right)",
    headline: "\u201CTrump administration takes hard line as China trade talks restart\u201D",
  },
  {
    outlet: "The Guardian",
    lean: "Center-Left",
    leanScore: 38,
    color: "var(--bias-left)",
    headline: "\u201CTrade war uncertainty looms as US-China negotiations resume\u201D",
  },
  {
    outlet: "Al Jazeera",
    lean: "Center-Left",
    leanScore: 35,
    color: "var(--bias-left)",
    headline: "\u201CGlobal markets brace as superpowers return to negotiating table\u201D",
  },
  {
    outlet: "New York Post",
    lean: "Right",
    leanScore: 74,
    color: "var(--bias-right)",
    headline: "\u201CBiden caves to China pressure, agrees to new round of trade talks\u201D",
  },
];

/* ── Six Axes — Scene II extension (manifesto) ── */

export interface BiasAxis {
  name: string;
  brief: string;
  score: number;
  signals: string;
  sample: string;
}

export const SIX_AXES: BiasAxis[] = [
  {
    name: "Political Lean",
    brief: "Where the article falls on the spectrum.",
    score: 42,
    signals: "Keyword lexicons, entity sentiment (NER + TextBlob), framing phrases, length-adaptive + sparsity-weighted source baseline blending.",
    sample: "The <mark>administration</mark> defended the <mark>crackdown</mark> as necessary to <mark>restore order</mark>.",
  },
  {
    name: "Sensationalism",
    brief: "How much urgency is inflated beyond the facts.",
    score: 28,
    signals: "Clickbait patterns, superlative density, TextBlob extremity, partisan attack density (capped 30 pts).",
    sample: "The <mark>unprecedented</mark> move sent <mark>shockwaves</mark> through the <mark>entire</mark> industry.",
  },
  {
    name: "Opinion vs. Reporting",
    brief: "Whether it reports facts or argues a position.",
    score: 15,
    signals: "First-person pronouns, subjectivity score, attribution density (24 investigative patterns), value judgments, rhetorical questions.",
    sample: "<mark>I believe</mark> the decision <mark>should have been</mark> made earlier. <mark>Don\u2019t you agree?</mark>",
  },
  {
    name: "Factual Rigor",
    brief: "How thoroughly it cites named sources and data.",
    score: 78,
    signals: "Named sources via NER + attribution verbs, org citations, data patterns, direct quotes, vague-source penalty.",
    sample: "<mark>Treasury Secretary Janet Yellen</mark> told reporters at the <mark>G7 summit</mark> that <mark>2.3% GDP growth</mark> was expected.",
  },
  {
    name: "Framing",
    brief: "Whether word choices nudge the reader.",
    score: 31,
    signals: "50+ charged synonym pairs, cluster-aware omission detection, headline-body divergence, passive voice (capped 30).",
    sample: "Protestors <mark>clashed with</mark> police vs. Police <mark>dispersed</mark> the crowd.",
  },
  {
    name: "Outlet Tracking",
    brief: "How each outlet covers each topic over time.",
    score: 55,
    signals: "Per-topic per-outlet EMA with adaptive alpha (0.3 new / 0.15 established). Stored across pipeline runs.",
    sample: "Fox News on immigration: <mark>lean 68 avg</mark> over 30 days (12 articles). CNN: <mark>lean 35 avg</mark>.",
  },
];

/* ── Ranking Signals — Scene III: "The Engine" ── */

export interface RankingSignal {
  name: string;
  weight: number;
}

export const RANKING_SIGNALS: RankingSignal[] = [
  { name: "Source Breadth", weight: 20 },
  { name: "Maturity", weight: 16 },
  { name: "Tier Diversity", weight: 13 },
  { name: "Consequentiality", weight: 10 },
  { name: "Institutional Authority", weight: 8 },
];

/* ── Competitive Landscape — Scene IV extension (manifesto) ── */

export interface LandscapePair {
  them: string;
  us: string;
}

export const LANDSCAPE: LandscapePair[] = [
  { them: "They rate the outlet.", us: "We read the article." },
  { them: "They track who owns the source.", us: "We analyze what the source wrote." },
  { them: "They score once and move on.", us: "We score every article, every run, every day." },
];

/* ── Comparison Morph — Scene IV: "The Difference" ── */

export const COMPARISON_SCORES = [
  { name: "Lean", value: 42 },
  { name: "Rigor", value: 78 },
  { name: "Tone", value: 18 },
  { name: "Framing", value: 31 },
];

/* ── Product Family — Scene V: "The Worlds" ── */

export interface ProductWorld {
  cli: string;
  name: string;
  desc: string;
  href: string;
  palette: string;
}

export const PRODUCT_FAMILY: ProductWorld[] = [
  { cli: "void --news", name: "The Feed", desc: "Importance-ranked, bias-analyzed", href: "/", palette: "feed" },
  { cli: "void --weekly", name: "The Magazine", desc: "Economist-style weekly digest", href: "/weekly", palette: "weekly" },
  { cli: "void --paper", name: "The Broadsheet", desc: "E-paper front page", href: "/paper", palette: "paper" },
  { cli: "void --sources", name: "The Spectrum", desc: "1,013 sources on one axis", href: "/sources", palette: "sources" },
  { cli: "void --onair", name: "The Studio", desc: "Two-host audio broadcast", href: "/", palette: "onair" },
  { cli: "void --ship", name: "The Forge", desc: "Feature request board", href: "/ship", palette: "ship" },
  { cli: "void --history", name: "The Archive", desc: "Multi-perspective historical events", href: "/history", palette: "archive" },
];

/* ── Key Numbers — Scene VI: "The Verdict" ── */

export const NUMBERS = [
  { value: "1,013", label: "sources" },
  { value: "6", label: "axes" },
  { value: "4", label: "editions" },
  { value: "$0", label: "cost" },
  { value: "4\u00D7", label: "daily" },
  { value: "0", label: "accounts required" },
];

/* ── First Principles (manifesto extension after Scene I) ── */

export const FIRST_PRINCIPLES = [
  "Every reader sees the same stories in the same order.",
  "Every score traces to specific words in the text.",
  "Every feature is free. There is no premium tier. There never will be.",
];

/* ── Sigil Component Labels (Scene II breakdown) ── */

export const SIGIL_PARTS = [
  { id: "circle", name: "Coverage Lens", desc: "Sources reporting on this story" },
  { id: "beam", name: "Lean Spectrum", desc: "Political lean, per article" },
  { id: "ticks", name: "Confidence", desc: "Weight of analytical signal" },
  { id: "post", name: "Grounding", desc: "Anchored to methodology" },
  { id: "base", name: "Stability", desc: "Foundation of consistent scoring" },
];

/* ── Beam Sweep Data (Scene II animation) ── */

export const SWEEP_POSITIONS = [
  { lean: 10, color: "var(--bias-far-left)", label: "Far Left" },
  { lean: 30, color: "var(--bias-left)", label: "Left" },
  { lean: 50, color: "var(--bias-center)", label: "Center" },
  { lean: 70, color: "var(--bias-right)", label: "Right" },
  { lean: 90, color: "var(--bias-far-right)", label: "Far Right" },
  { lean: 50, color: "var(--bias-center)", label: "Center" },
];

/* ── Chapter Definitions ── */

export interface Chapter {
  id: string;
  roman: string;
  headline: string;
  subtitle?: string;
  prologueBody: string;
  manifestoLead?: string;
  duration: number;
}

export const CHAPTERS: Chapter[] = [
  {
    id: "the-void",
    roman: "I",
    headline: "The Void",
    prologueBody: "One event. Five outlets. Five different realities. One calls it a crackdown. Another calls it restoring order. A third buries it on page six.",
    manifestoLead: "Not the absence of information. The opposite. A flood of it, shaped by incentive, refracted through ideology, optimized for the click that keeps you inside the bubble you didn\u2019t choose.",
    duration: 15_000,
  },
  {
    id: "the-instrument",
    roman: "II",
    headline: "The Instrument",
    subtitle: "Every story, measured",
    prologueBody: "Six axes. Zero black boxes. The beam tilts with coverage lean \u2014 per story, not per outlet. The ring fills as sources weigh in. Sparse signal? Honest uncertainty over false precision.",
    duration: 20_000,
  },
  {
    id: "the-engine",
    roman: "III",
    headline: "The Engine",
    subtitle: "Importance, not popularity",
    prologueBody: "1,013 sources. 158 countries. 11 ranking signals. Zero engagement metrics. The algorithm decides what matters \u2014 not what gets clicked.",
    duration: 15_000,
  },
  {
    id: "the-difference",
    roman: "IV",
    headline: "The Difference",
    prologueBody: "They rate the outlet. We read the article. An outlet labeled \u201CLeft\u201D published this article with center-right lean, high rigor, and minimal framing. The label would have told you to distrust it. The article earned that trust back.",
    manifestoLead: "Per article. Not per outlet. That is the difference.",
    duration: 15_000,
  },
  {
    id: "the-worlds",
    roman: "V",
    headline: "The Worlds",
    subtitle: "One platform, six experiences",
    prologueBody: "Each built for a different way of reading the news.",
    duration: 15_000,
  },
  {
    id: "the-verdict",
    roman: "VI",
    headline: "Read with clarity.",
    prologueBody: "Broad coverage from across the spectrum, grounded in named sources. That\u2019s where confidence lives. Thin coverage from one corner? Scrutinize more.",
    duration: 10_000,
  },
];
