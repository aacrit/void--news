/* ===========================================================================
   void --history — Types
   "Archival Cinema" — multi-perspective historical events
   =========================================================================== */

export type HistoryEra = 'ancient' | 'classical' | 'medieval' | 'early-modern' | 'modern' | 'contemporary';
export type HistoryRegion = 'africa' | 'americas' | 'east-asia' | 'south-asia' | 'southeast-asia' | 'middle-east' | 'europe' | 'oceania' | 'central-asia' | 'global';
export type HistoryCategory = 'war' | 'revolution' | 'empire' | 'independence' | 'genocide' | 'disaster' | 'cultural' | 'scientific' | 'economic' | 'political';
export type Severity = 'catastrophic' | 'critical' | 'major';
export type ViewpointType = 'victor' | 'vanquished' | 'bystander' | 'academic' | 'revisionist' | 'indigenous';
export type ConnectionType = 'caused' | 'influenced' | 'response-to' | 'parallel' | 'consequence';
export type PerspectiveColor = 'a' | 'b' | 'c' | 'd' | 'e';

export interface PrimarySource {
  text: string;
  author: string;
  work: string;
  date: string;
}

export interface KeyFigure {
  name: string;
  role: string;
}

export interface MediaItem {
  id: string;
  type: 'image' | 'map' | 'document' | 'artwork' | 'video';
  url: string;
  caption: string;
  attribution: string;
  year?: string;
  /** Internet Archive embed URL — only for type 'video' */
  videoEmbedUrl?: string;
}

export interface EventConnection {
  targetSlug: string;
  targetTitle: string;
  type: ConnectionType;
  description: string;
}

export interface Perspective {
  id: string;
  viewpointName: string;
  viewpointType: ViewpointType;
  color: PerspectiveColor;
  temporalAnchor: string;
  geographicAnchor: string;
  narrative: string;
  keyNarratives: string[];
  omissions: string[];
  disputed: string[];
  primarySources: PrimarySource[];
}

export interface HistoricalEvent {
  id: string;
  slug: string;
  title: string;
  subtitle: string;
  era: HistoryEra;
  regions: HistoryRegion[];
  categories: HistoryCategory[];
  severity: Severity;
  datePrimary: string;
  dateSort: number;
  dateRange: string;
  location: string;
  heroImage?: string;
  heroCaption?: string;
  heroAttribution?: string;
  contextNarrative: string;
  keyFigures: KeyFigure[];
  deathToll?: string;
  displaced?: string;
  duration?: string;
  perspectives: Perspective[];
  media: MediaItem[];
  connections: EventConnection[];
  published: boolean;
}

export interface RedactedEvent {
  id: string;
  slug: string;
  title: string;
  era: HistoryEra;
  regions: HistoryRegion[];
  quoteA: string;
  quoteB: string;
  dateHint: string;
}

/* Era metadata for display */
export interface EraInfo {
  id: HistoryEra;
  label: string;
  dateRange: string;
  description: string;
}

export const ERAS: EraInfo[] = [
  { id: 'ancient', label: 'Ancient', dateRange: '3000 BCE - 500 BCE', description: 'First civilizations, empires, and written law' },
  { id: 'classical', label: 'Classical', dateRange: '500 BCE - 500 CE', description: 'Greece, Rome, Han Dynasty, Maurya Empire' },
  { id: 'medieval', label: 'Medieval', dateRange: '500 - 1500', description: 'Feudalism, Crusades, Mongol expansion, Black Death' },
  { id: 'early-modern', label: 'Early Modern', dateRange: '1500 - 1800', description: 'Colonialism, Reformation, Enlightenment, revolutions' },
  { id: 'modern', label: 'Modern', dateRange: '1800 - 1945', description: 'Industrialization, nationalism, world wars' },
  { id: 'contemporary', label: 'Contemporary', dateRange: '1945 - Present', description: 'Cold War, decolonization, globalization, digital age' },
];

export interface RegionInfo {
  id: HistoryRegion;
  label: string;
}

export const REGIONS: RegionInfo[] = [
  { id: 'africa', label: 'Africa' },
  { id: 'americas', label: 'Americas' },
  { id: 'east-asia', label: 'East Asia' },
  { id: 'south-asia', label: 'South Asia' },
  { id: 'southeast-asia', label: 'Southeast Asia' },
  { id: 'middle-east', label: 'Middle East' },
  { id: 'europe', label: 'Europe' },
  { id: 'oceania', label: 'Oceania' },
  { id: 'central-asia', label: 'Central Asia' },
  { id: 'global', label: 'Global' },
];

/* ===========================================================================
   Long-Arc Topics — Multi-century thematic narratives
   Unlike events (single moments with perspectives), arcs span centuries
   and are structured as sequential chapters, each with its own set of
   perspective narratives. An arc CONTAINS events as nodes along its
   timeline.
   =========================================================================== */

export type ArcTheme =
  | 'economic'
  | 'political'
  | 'social'
  | 'technological'
  | 'cultural'
  | 'military'
  | 'environmental'
  | 'philosophical';

/**
 * A perspective that runs across the entire arc.
 * Unlike event perspectives (tied to a moment), arc perspectives
 * represent ideological or analytical traditions that persist and
 * evolve across centuries. Each has a "throughline" — the core
 * argument this perspective makes about the arc's entire trajectory.
 */
export interface ArcPerspective {
  id: string;
  slug: string;
  name: string;
  /** Short label for the tradition (e.g., "Marxist", "Free Market") */
  ideology: string;
  /** CSS color token suffix — maps to --hist-arc-perspective-{color} */
  color: PerspectiveColor;
  /** The core argument this perspective makes across ALL chapters (2-4 sentences) */
  throughline: string;
  /** Key thinkers associated with this perspective across the arc's timespan */
  keyThinkers: ArcThinker[];
  /** Canonical texts that define this perspective */
  canonicalWorks: ArcSource[];
}

export interface ArcThinker {
  name: string;
  role: string;
  activeYears: string;
}

export interface ArcSource {
  title: string;
  author: string;
  year: string;
  type: 'book' | 'essay' | 'speech' | 'report' | 'data';
}

/**
 * A single data point in a statistical time series.
 * Rendered as line/area charts to show trends across the arc's timespan.
 */
export interface StatisticalDataPoint {
  year: number;
  value: number;
  /** Optional label for annotation (e.g., "Bretton Woods", "2008 crash") */
  label?: string;
}

/**
 * A time series of data associated with the arc.
 * Examples: GDP per capita, Gini coefficient, labor share of income,
 * union membership rates, trade volume.
 */
export interface StatisticalSeries {
  id: string;
  label: string;
  /** What is being measured */
  description: string;
  unit: string;
  /** Attribution for the data (e.g., "World Bank", "Maddison Project") */
  source: string;
  sourceUrl?: string;
  dataPoints: StatisticalDataPoint[];
  /** Which chapters this series is most relevant to (for filtering) */
  relevantChapters?: number[];
}

/**
 * A chapter within a long-arc topic.
 * Represents a distinct phase or era in the arc's trajectory.
 * Each chapter has its own date range, narrative, and per-perspective
 * analysis. Chapters are sequential — chapter 1 precedes chapter 2.
 */
export interface ArcChapter {
  id: string;
  chapterNumber: number;
  title: string;
  subtitle: string;
  dateRange: string;
  /** Year for timeline positioning (start of chapter) */
  dateStart: number;
  /** Year for timeline positioning (end of chapter) */
  dateEnd: number;
  /** The factual narrative of this period (neutral framing, 300-600 words) */
  narrative: string;
  /** Key events/turning points within this chapter */
  keyMoments: ArcKeyMoment[];
  /** Per-perspective narratives for this chapter */
  chapterPerspectives: ArcChapterPerspective[];
  /** Slugs of existing history_events that fall within this chapter */
  connectedEventSlugs: string[];
  /** Primary sources specific to this chapter */
  primarySources: PrimarySource[];
  /** Statistical series IDs most relevant to this chapter */
  relevantStatistics?: string[];
  /** Hero image for the chapter */
  heroImage?: string;
  heroCaption?: string;
  heroAttribution?: string;
}

/**
 * A key moment or turning point within a chapter.
 * Smaller than a full HistoricalEvent, but marks a specific
 * date/event that shaped the chapter's trajectory.
 */
export interface ArcKeyMoment {
  year: number;
  title: string;
  description: string;
  /** If this moment IS an existing void --history event, link to it */
  eventSlug?: string;
}

/**
 * How a specific perspective interprets a specific chapter.
 * This is the intersection of perspective (row) and chapter (column).
 */
export interface ArcChapterPerspective {
  perspectiveId: string;
  /** This perspective's reading of this chapter (200-500 words) */
  narrative: string;
  /** Core arguments this perspective makes about this period */
  keyArguments: string[];
  /** What this perspective highlights that others downplay */
  emphasized: string[];
  /** What this perspective minimizes or ignores */
  omitted: string[];
  /** Sources specific to this perspective in this chapter */
  sources: ArcSource[];
  /** Notable quotes from this perspective's thinkers in this period */
  notableQuotes: { text: string; speaker: string; context: string }[];
}

/**
 * The top-level long-arc topic.
 * Contains everything needed to render a multi-century thematic narrative.
 */
export interface LongArcTopic {
  id: string;
  slug: string;
  title: string;
  subtitle: string;
  /** The central question this arc examines */
  centralQuestion: string;
  dateRange: string;
  dateStart: number;
  dateEnd: number;
  theme: ArcTheme;
  regions: HistoryRegion[];
  /** Introductory narrative (500-800 words, neutral framing) */
  introduction: string;
  /** Arc-level perspectives (the ideological/analytical traditions) */
  perspectives: ArcPerspective[];
  /** Sequential chapters */
  chapters: ArcChapter[];
  /** Statistical time series for the arc */
  statistics: StatisticalSeries[];
  /** Connections to existing void --history events */
  connectedEventSlugs: string[];
  heroImage?: string;
  heroCaption?: string;
  heroAttribution?: string;
  published: boolean;
}
