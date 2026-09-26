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
  /** Contestedness 0-100: 0 = one-sided / all-center, 100 = perfect L/R split.
   *  Reveals the bimodal coverage that the mean lean conceals. */
  polarization?: number;
  /** Source counts collapsed to 3 segments for the coverage bar. */
  /** The seven bucket counts, far-left first; sums to leanMeasuredCount. */
  leanBuckets?: readonly number[];
  leanLeftCount?: number;
  leanCenterCount?: number;
  leanRightCount?: number;
  /** How many of this story's analyzed articles actually carried a lean
   *  measurement, and how many were analyzed in total. An article from an
   *  outlet not placed on the left/right axis, writing copy with no partisan
   *  signal, is full coverage but not a lean reading, so it is excluded from
   *  the mean (migration 078). These let the UI say how much of the coverage
   *  the lean is measured from instead of implying the whole roster voted. */
  leanMeasuredCount?: number;
  leanTotalCount?: number;
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
  /** Raw analysis confidence 0-1 from pipeline (optional) */
  confidence?: number;
  /** Article title from source (for ComparativeView) */
  articleTitle?: string;
  /** Article summary/excerpt from source (for ComparativeView) */
  articleSummary?: string;
  /** The engine did not measure this article's political lean. Its stored
   *  value is the 50 default, so no surface may plot or average it. */
  leanUnscored?: boolean;
}

/* ---------------------------------------------------------------------------
   void --verify types — cross-source factual verification
   --------------------------------------------------------------------------- */

export interface ClaimConsensus {
  total_claims: number;
  corroborated: number;
  single_source: number;
  disputed: number;
  consensus_ratio: number;
  consensus_summary: string;
  highlighted_claims: VerifiedClaim[];
  disputed_details: DisputedClaim[];
}

export interface VerifiedClaim {
  text: string;
  status: 'corroborated' | 'single_source' | 'disputed';
  source_count: number;
  sources: string[];
  highlight: boolean;
}

export interface DisputedClaim {
  topic: string;
  version_a: string;
  version_a_sources: string[];
  version_b: string;
  version_b_sources: string[];
  contradiction_type: 'negation' | 'numeric' | 'entity_swap';
}

export interface SourceAccuracy {
  source_slug: string;
  source_name: string;
  total_unique_claims: number;
  later_corroborated: number;
  later_contradicted: number;
  still_unverified: number;
  accuracy_rate: number;
  accuracy_30d: number | null;
  accuracy_90d: number | null;
  trend: 'improving' | 'stable' | 'declining';
}

export interface DeepDiveData {
  consensus: string[];
  divergence: string[];
  sources: StorySource[];
  claimConsensus?: ClaimConsensus;
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
  /** Claim consensus: corroborated count (from void --verify) */
  consensusCorroborated?: number;
  /** Claim consensus: total claims checked */
  consensusTotal?: number;
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
  /** Best available og:image URL from cluster articles (highest-tier source) */
  imageUrl?: string | null;
  /** Supabase Storage URL — pipeline-cached image, no hotlink protection */
  cachedImageUrl?: string | null;
  /** Site-absolute permalink to this story's standalone Deep Dive page
   *  (e.g. "/story/<uuid>/"). Present when the cluster was archived into
   *  printed_stories (today's feed always is); absent on an archive miss.
   *  Crawlable + shareable; the in-app click still opens the inline/full-page
   *  Deep Dive via preventDefault on plain left-click. */
  permalink?: string;
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

/** One chapter of the On Air daily broadcast.
 *
 *  The brief is produced as a radio show: ident and sign-on, a headlines menu,
 *  one chapter per story, the "also today" briefs, the closer, the editorial.
 *  The pipeline emits their marks so the player can present a rail instead of
 *  a single undifferentiated hour. Legacy episodes, weekly issues and history
 *  accounts carry no chapters (see `audio_chapters: null`). */
export interface AudioChapter {
  /** Seconds from the start of the MP3. */
  startTime: number;
  /** Seconds. Omitted when the chapter runs to the next one. */
  endTime?: number;
  /** e.g. "Fed raises rates" / "Headlines" / "Also today" / "Opinion" */
  title: string;
  /** "segment" is a History documentary chapter: it carries a title and
   *  nothing else, so the rail draws no kind badge beside it. */
  /* On Air: headlines / story / briefs / finally / opinion (legacy: editorial).
     History: segment. The Sunday weekly edition, "The Argument", adds its own
     movements — the rail renders any kind and already guards an empty label,
     which is exactly what lets a new format arrive without a player change. */
  kind:
    | "headlines" | "story" | "briefs" | "finally" | "opinion" | "editorial"
    | "segment"
    | "promo"
    | "open" | "contents" | "cover" | "topic" | "second" | "department"
    | "numbers" | "close";
  /** story_clusters.id when kind is "story" or "finally" */
  cluster_id?: string;
  /** Feed rank when kind is "story" */
  rank?: number;
  /** Editorial: the opinion headline */
  subtitle?: string;
  /** Permalink to /story/<uuid>/ when the story is archived */
  url?: string;
}

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
  /** Radio-show chapter marks. null on legacy episodes, weekly and history. */
  audio_chapters: AudioChapter[] | null;
  /** Where STORY 1 begins, after the ident, sign-on and menu. null when unknown. */
  news_start_seconds: number | null;
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

// Parking Lot: regional editions (us, europe, south-asia) disabled pre-launch.
// To re-enable, move entries from _ALL_EDITIONS back into EDITIONS.
export const EDITIONS: EditionMeta[] = [
  { slug: "world", label: "World", country: "Global", sourceCount: "200+ sources", description: "International coverage" },
];

export const _ALL_EDITIONS: EditionMeta[] = [
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
export type ShipStatus = 'submitted' | 'triaged' | 'building' | 'shipped' | 'wontship' | 'deferred' | 'not_feasible';
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
  Left: { min: 0, max: 46 },
  Balanced: { min: 38, max: 62 },
  Right: { min: 54, max: 100 },
};

/* ---------------------------------------------------------------------------
   Weekly Digest types — void --weekly

   These live in app/weekly/types.ts now, alongside the section that owns them
   (mirroring app/history/). Re-exported here so AudioProvider and DailyBrief
   keep importing them from the shared module.
   --------------------------------------------------------------------------- */

export type {
  WeeklyCoverStory,
  WeeklyTimelineDay,
  WeeklyCoverNumber,
  WeeklyRecapStory,
  WeeklyOpinion,
  WeeklyDepartment,
  WeeklyBiasReportData,
  WeeklyDigestData,
  WeeklyIssueSummary,
} from "../weekly/types";

