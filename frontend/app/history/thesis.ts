/* ===========================================================================
   The thesis model: the shape pipeline/history/export_thesis.py writes to
   build-data/history-theses/<slug>.json. Mirrors the exporter field for field;
   the exporter is the one place that decides these names, and the page reads
   them without re-deriving anything (the same rule hearing.ts follows for the
   account an argument belongs to).
   =========================================================================== */

export interface ThesisSentence {
  text: string;
  notes: number[];
  interpretive: boolean;
}

export interface ThesisParaBlock {
  t: "para";
  sentences: ThesisSentence[];
}

export interface ThesisListItem {
  sentences: ThesisSentence[];
  against: string | null;
  againstName: string | null;
  color: string | null;
}

export interface ThesisListBlock {
  t: "list";
  items: ThesisListItem[];
}

export interface ThesisRendering {
  kind: "official-parallel" | "void-translation";
  text: string;
}

export interface ThesisExtractRef {
  source: string;
  locator: string;
  locatorLabel: string;
  short: string;
  producer: string | null;
  text: string;
  language: string;
  rendering: ThesisRendering | null;
  freeCopy: string | null;
  url: string | null;
  exhibit: number | null;
}

export interface ThesisExhibitBlock {
  t: "exhibit";
  n: number;
  id: string;
  kind: "document" | "image" | "map" | string;
  title: string;
  creator: string | null;
  date: string | null;
  repository: string | null;
  accession: string | null;
  licence: string | null;
  url: string | null;
  image: string | null;
  shows: string | null;
  doesNotShow: string | null;
  text: string | null;
  language?: string;
  rendering?: ThesisRendering | null;
  source: string | null;
  locator: string | null;
  locatorLabel?: string;
  producer?: string | null;
  short?: string;
  notes?: string[];
}

export interface ThesisEpisodeBlock {
  t: "episode";
  chapter: number;
  title: string;
  kind: string;
  lines: { speaker: string; text: string }[];
  startTime: number | null;
}

export interface ThesisAdjudication {
  claim: string;
  verdict: "supported" | "contradicted" | "qualified" | "untestable";
  verdictLabel: string;
  basis: "presence" | "absence";
  reasoning: string;
  producers: string[];
  oneSided: boolean;
  restsOn: ThesisExtractRef[];
}

export interface ThesisPositionBlock {
  t: "position";
  id: string;
  name: string;
  color: string;
  holders: string[];
  restsOn: {
    source: string;
    short: string;
    tier: string;
    verified: boolean;
    freeCopy: string | null;
    byHolder: boolean;
  }[];
  claim: string;
  omits: string;
  /** Tier A or B extracts that describe what this position is (§4a); required
   *  when the position rests on a Tier D source. */
  describedBy: ThesisExtractRef[];
  adjudications: ThesisAdjudication[];
}

export interface ThesisContestedRow {
  position: string;
  positionName: string | null;
  color: string;
  holds: string;
  figures: string[];
  source: string;
  short: string;
  locator: string | null;
  freeCopy: string | null;
  note: number;
}

export interface ThesisContestedBlock {
  t: "contested";
  id: string;
  claim: string;
  rows: ThesisContestedRow[];
}

export interface ThesisAnalysisRow {
  cells: Record<string, string | number | null>;
  extract: string;
  note: number;
  short: string;
  locatorLabel: string;
}

export interface ThesisAnalysisBlock {
  t: "analysis";
  id: string;
  title: string;
  method: string;
  finding: string;
  confidence: string;
  against: string | null;
  result: unknown;
  compute: string;
  columns: string[];
  rows: ThesisAnalysisRow[];
  rowCount: number;
}

export type ThesisBlock =
  | ThesisParaBlock
  | ThesisListBlock
  | ThesisExhibitBlock
  | ThesisEpisodeBlock
  | ThesisPositionBlock
  | ThesisContestedBlock
  | ThesisAnalysisBlock;

export interface ThesisSection {
  id: string;
  kind: string;
  level: 2 | 3;
  title: string;
  number: number | null;
  blocks: ThesisBlock[];
}

export interface ThesisNote {
  n: number;
  source: string;
  locator: string | null;
  /** Cited from running text (so the note has a place to return to), as
   *  against a note a table row or a contested block made. */
  inText: boolean;
  locatorLabel: string | null;
  short: string;
  exhibit: number | null;
  freeCopy: string | null;
}

export interface ThesisSourceEntry {
  id: string;
  citation: string;
  kind: string;
  language: string;
  producer: string | null;
  freeCopy: string | null;
  verifiedAt: string | null;
  verifiedBy: string | null;
  pinned: boolean;
  position: string | null;
}

export interface ThesisSourceTier {
  tier: "A" | "B" | "C" | "D";
  name: string;
  entries: ThesisSourceEntry[];
}

export interface ThesisGap {
  entry: string | null;
  short: string | null;
  what: string;
  tried: string[];
  status: string;
}

/** §15: a holistic thesis says which sections carry which strand of the
 *  event, and which position answers each perspective the event record holds.
 *  T-21 checks the map; the page prints it under the question. */
export interface ThesisCoverageStrand {
  sections: string[];
  terms?: string[];
  min?: number;
}

export interface ThesisCoverage {
  causes?: ThesisCoverageStrand;
  course?: ThesisCoverageStrand;
  actors?: ThesisCoverageStrand;
  regions?: ThesisCoverageStrand;
  consequences?: ThesisCoverageStrand;
  legacy?: ThesisCoverageStrand;
  perspectives?: Record<string, { position: string; sections: string[] }>;
}

export interface ThesisDoc {
  /** Present only on a holistic thesis (§15); absent means one question argued. */
  scope?: "holistic";
  coverage?: ThesisCoverage;
  slug: string;
  status: "draft" | "audited" | "published";
  auditedBy: string | null;
  auditedAt: string | null;
  question: string;
  claims: string[];
  regionalSourcesNote: string | null;
  sections: ThesisSection[];
  notes: ThesisNote[];
  exhibits: { n: number; id: string; kind: string; title: string }[];
  sources: ThesisSourceTier[];
  standing: Record<string, number>;
  bar: Record<string, boolean>;
  gaps: ThesisGap[];
  episodeMarks: { chapter: number; where: string; startTime: number | null }[];
  words: number;
}
