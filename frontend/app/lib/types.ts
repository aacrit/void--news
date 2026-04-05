export interface BiasScores {
  /** 0 = far left, 50 = center, 100 = far right */
  politicalLean: number;
  /** 0 = measured, 100 = inflammatory */
  sensationalism: number;
  /** 0 = hard reporting, 50 = analysis, 100 = opinion */
  opinionFact: number;
  /** 0 = unsourced, 100 = well-sourced */
  factualRigor: number;
  /** 0 = neutral framing, 100 = heavy framing */
  framing: number;
}

/** Spread metrics showing how much sources diverge on each axis */
export interface BiasSpread {
  leanSpread: number;
  framingSpread: number;
  leanRange: number;
  sensationalismSpread: number;
  opinionSpread: number;
  aggregateConfidence: number;
  analyzedCount: number;
}

export interface Source {
  name: string;
  count: number;
}

/** Rationale for political lean scoring */
export interface LeanRationale {
  keywordScore: number;
  framingShift: number;
  entityShift: number;
  sourceBaseline: number;
  topLeftKeywords: string[];
  topRightKeywords: string[];
  framingPhrasesFound: string[];
  entitySentiments: Record<string, number>;
}

/** Rationale for opinion vs reporting classification */
export interface OpinionRationale {
  pronounScore: number;
  subjectivityScore: number;
  modalScore: number;
  hedgingScore: number;
  attributionScore: number;
  metadataScore: number;
  rhetoricalScore: number;
  valueJudgmentScore: number;
  classification: "Reporting" | "Analysis" | "Opinion" | "Editorial";
  dominantSignals: string[];
}

/** Rationale for coverage/confidence scoring */
export interface CoverageRationale {
  factualRigor: number;
  namedSourcesCount: number;
  orgCitationsCount: number;
  dataPointsCount: number;
  directQuotesCount: number;
  vagueSourcesCount: number;
  specificityRatio: number;
}

/** Rationale for sensationalism scoring */
export interface SensationalismRationale {
  headlineScore: number;
  bodyScore: number;
  clickbaitSignals: number;
  superlativeDensity: number;
  urgencyDensity: number;
  hyperboleDensity: number;
  measuredDensity: number;
}

/** Rationale for framing analysis scoring */
export interface FramingRationale {
  connotationScore: number;
  keywordEmphasisScore: number;
  omissionScore: number;
  headlineBodyDivergence: number;
  passiveVoiceScore: number;
  hasClusterContext: boolean;
}

/** Gemini LLM reasoning text per bias axis — stored under rationale.gemini_reasoning */
export interface GeminiReasoning {
  political_lean?: string;
  sensationalism?: string;
  opinion_fact?: string;
  factual_rigor?: string;
  framing?: string;
}

/** Three-lens data model for bias visualization */
export interface ThreeLensData {
  /** Political lean: 0=far left, 50=center, 100=far right */
  lean: number;
  leanRationale?: LeanRationale;
  /** Coverage/confidence composite: 0=weak, 100=strong */
  coverage: number;
  coverageRationale?: CoverageRationale;
  sourceCount: number;
  tierBreakdown?: Record<string, number>;
  /** Opinion vs reporting: 0=reporting, 100=opinion */
  opinion: number;
  opinionLabel: "Reporting" | "Analysis" | "Opinion" | "Editorial";
  opinionRationale?: OpinionRationale;
  /** Sensationalism rationale — populated from bias_scores.rationale.sensationalism */
  sensationalismRationale?: SensationalismRationale;
  /** Framing rationale — populated from bias_scores.rationale.framing */
  framingRationale?: FramingRationale;
  /** Gemini LLM reasoning — populated from bias_scores.rationale.gemini_reasoning */
  geminiReasoning?: GeminiReasoning;
  /** True when bias scores are fallback placeholders, not real analysis data */
  pending?: boolean;
}

export type OpinionLabel = ThreeLensData["opinionLabel"];

export interface StorySource {
  name: string;
  url: string;
  tier: "us_major" | "international" | "independent";
  biasScores: BiasScores;
  lensData?: ThreeLensData;
  /** Raw analysis confidence 0–1 from pipeline (optional, for BiasInspector) */
  confidence?: number;
  /** Article title from source (for ComparativeView) */
  articleTitle?: string;
  /** Article summary/excerpt from source (for ComparativeView) */
  articleSummary?: string;
}

export interface DeepDiveData {
  consensus: string[];
  divergence: string[];
  sources: StorySource[];
}

/** Data model for the Sigil — unified 6-axis bias indicator */
export interface SigilData {
  /** Political lean: 0=far left, 50=center, 100=far right */
  politicalLean: number;
  /** Sensationalism: 0=measured, 100=inflammatory */
  sensationalism: number;
  /** Opinion vs reporting: 0=reporting, 50=analysis, 100=opinion */
  opinionFact: number;
  /** Factual rigor: 0=unsourced, 100=well-sourced (inverted: high=good) */
  factualRigor: number;
  /** Framing: 0=neutral, 100=heavy framing */
  framing: number;
  /** Source agreement: 0=unanimous, 100=high disagreement */
  agreement: number;
  /** Number of sources covering this story */
  sourceCount: number;
  /** Tier breakdown for coverage context */
  tierBreakdown?: Record<string, number>;
  /** Spread metrics per axis (when available from cluster data) */
  biasSpread?: BiasSpread;
  /** True when bias scores are fallback placeholders */
  pending?: boolean;
  /** True when lean is in balanced range but lacks analytical signal */
  unscored?: boolean;
  /** Opinion classification label */
  opinionLabel: OpinionLabel;
  /** Percentile-based divergence flag: "divergent" (top 10%), "consensus" (bottom 10%), or null */
  divergenceFlag?: "divergent" | "consensus" | null;
}

export interface OpinionArticle {
  id: string;
  title: string;
  summary: string;
  author: string | null;
  url: string;
  publishedAt: string;
  sourceName: string;
  sourceSlug: string;
  sourceTier: "us_major" | "international" | "independent";
  section: "world" | "us";
  politicalLean: number;
  sensationalism: number;
  confidence: number;
}

export interface Story {
  id: string;
  title: string;
  summary: string;
  source: Source;
  category: Category;
  publishedAt: string;
  biasScores: BiasScores;
  biasSpread?: BiasSpread;
  lensData: ThreeLensData;
  sigilData: SigilData;
  section: Edition;
  sections: Edition[];
  importance: number;
  divergenceScore: number;
  headlineRank: number;
  coverageVelocity: number;
  deepDive?: DeepDiveData;
  articleUrl?: string;
}

export type Category =
  | "Politics"
  | "Conflict"
  | "Economy"
  | "Science"
  | "Health"
  | "Environment"
  | "Culture";

export type Edition = "world" | "us" | "europe" | "south-asia";

// Keep Section as alias for backward compat
export type Section = Edition;

/** Editorial lean for the opinion piece — rotates daily */
export type OpinionLean = "left" | "center" | "right";

/** Daily Brief data from Supabase */
export interface DailyBriefData {
  id: string;
  edition: Edition;
  tldr_text: string;
  tldr_headline: string | null;
  opinion_text: string | null;
  opinion_headline: string | null;
  opinion_lean: OpinionLean | null;
  opinion_cluster_id: string | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  opinion_start_seconds: number | null;
  audio_voice_label: string | null;
  audio_voice: string | null;
  audio_script: string | null;
  top_cluster_ids: string[] | null;
  created_at: string;
}

export interface EditionMeta {
  slug: Edition;
  label: string;
  country: string;
  sourceCount: string;
  description: string;
}

export const EDITIONS: EditionMeta[] = [
  { slug: "world", label: "World", country: "Global", sourceCount: "200+ sources", description: "International coverage" },
  { slug: "us", label: "US", country: "United States", sourceCount: "170+ sources", description: "United States coverage" },
  { slug: "europe", label: "Europe", country: "UK & Europe", sourceCount: "110+ sources", description: "UK and European coverage" },
  { slug: "south-asia", label: "South Asia", country: "India & South Asia", sourceCount: "70+ sources", description: "India, Pakistan, Bangladesh, Sri Lanka, Nepal, Afghanistan" },
];

/* ---------------------------------------------------------------------------
   Tilt filter types — used by NavBar, MobileBottomNav, HomeContent, etc.
   "Tilt" = story/cluster-level measurement. Source-level uses "lean."
   --------------------------------------------------------------------------- */

export type LeanChip = "All" | "Left" | "Balanced" | "Right";

/** Lean chip boundaries — used by HomeContent to filter stories by political lean */
/* ---------------------------------------------------------------------------
   void --ship types
   --------------------------------------------------------------------------- */

export type ShipCategory = 'bug' | 'feature' | 'enhancement';
export type ShipArea = 'frontend' | 'pipeline' | 'bias' | 'audio' | 'design' | 'other';
export type ShipStatus = 'submitted' | 'triaged' | 'building' | 'shipped' | 'wontship';
export type ShipPriority = 'p0' | 'p1' | 'p2' | 'p3';

export interface ShipRequest {
  id: string;
  title: string;
  description: string;
  category: ShipCategory;
  area: ShipArea;
  edition_context: Edition | null;
  status: ShipStatus;
  priority: ShipPriority | null;
  votes: number;
  ceo_response: string | null;
  claude_branch: string | null;
  shipped_commit: string | null;
  device_info: string | null;
  ip_hash: string | null;
  created_at: string;
  triaged_at: string | null;
  shipped_at: string | null;
  updated_at: string;
  shipped_diff_summary: string | null;
}

export interface ShipReply {
  id: string;
  request_id: string;
  body: string;
  fingerprint: string;
  created_at: string;
}

/** Tilt filter boundaries — data-driven from production score distribution.
 *  Overlapping ranges so edge cases appear in both adjacent filters. */
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 43 },
  Balanced: { min: 34, max: 66 },
  Right: { min: 57, max: 100 },
};

/* ---------------------------------------------------------------------------
   Weekly Digest types — void --weekly
   --------------------------------------------------------------------------- */

export interface WeeklyCoverStory {
  headline: string;
  text: string;
  timeline?: WeeklyTimelineDay[];
  numbers?: WeeklyCoverNumber[];
}

export interface WeeklyTimelineDay {
  day?: string;      // legacy: "Monday"
  date?: string;     // new: "Mon Mar 31"
  note?: string;     // legacy
  event?: string;    // new: concrete event description
  development?: string;  // legacy from Gemini v1
}

export interface WeeklyCoverNumber {
  value: string;
  label: string;
}

export interface WeeklyRecapStory {
  headline: string;
  summary: string;
  section?: string;
}

export interface WeeklyOpinion {
  headline: string;
  text: string;
  lean: string;
  topic?: string;
}

export interface WeeklyBiasReportData {
  most_polarized?: Array<{
    headline: string;
    lean_spread: number;
    avg_lean: number;
  }>;
  aggregate?: {
    avg_lean: number;
    avg_rigor: number;
    avg_sensationalism: number;
    total_articles: number;
  };
}

export interface WeeklyDigestData {
  id: string;
  edition: string;
  week_start: string;
  week_end: string;
  issue_number: number;
  cover_headline: string;
  cover_image_url: string | null;
  cover_image_attribution: string | null;
  cover_text: WeeklyCoverStory[];
  cover_numbers: WeeklyCoverNumber[] | null;
  recap_stories: WeeklyRecapStory[];
  opinion_left: WeeklyOpinion[] | null;
  opinion_center: WeeklyOpinion[] | null;
  opinion_right: WeeklyOpinion[] | null;
  opinion_headlines: string[] | null;
  opinion_topic: string | null;
  bias_report_text: string | null;
  bias_report_data: WeeklyBiasReportData | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  total_articles: number | null;
  total_clusters: number | null;
  created_at: string;
}
