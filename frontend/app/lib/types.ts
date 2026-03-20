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
  /** Opinion classification label */
  opinionLabel: OpinionLabel;
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
  | "Economy"
  | "Tech"
  | "Health"
  | "Environment"
  | "Conflict"
  | "Science"
  | "Culture"
  | "Sports";

export type Edition = "world" | "us" | "india";

// Keep Section as alias for backward compat
export type Section = Edition;

export interface EditionMeta {
  slug: Edition;
  label: string;
  country: string;
  sourceCount: string;
  description: string;
}

export const EDITIONS: EditionMeta[] = [
  { slug: "world", label: "World", country: "Global", sourceCount: "130+ sources", description: "International coverage" },
  { slug: "us", label: "US", country: "United States", sourceCount: "130+ sources", description: "United States coverage" },
  { slug: "india", label: "India", country: "India", sourceCount: "19 sources", description: "Indian news in English" },
];
