/* ===========================================================================
   void --revolt — Types
   "Barricade Press" — the comparative anatomy of revolutions.
   Frontend remapped shapes (camelCase), assembled from the revolt_* tables
   (or mockData) by data.ts::mapRevolutionWithRelations.
   =========================================================================== */

export type RevoltEra =
  | 'classical'
  | 'atlantic'
  | 'springtime'
  | 'modern-nationalist'
  | 'anticolonial'
  | 'people-power'
  | 'color-revolutions'
  | 'square-revolutions';

export type RevoltRegion =
  | 'africa' | 'americas' | 'east-asia' | 'south-asia' | 'southeast-asia'
  | 'middle-east' | 'europe' | 'oceania' | 'central-asia' | 'global';

export type RevoltType =
  | 'social' | 'political' | 'anticolonial' | 'nationalist-secessionist'
  | 'democratic-uprising' | 'communist' | 'religious-theocratic'
  | 'peasant-agrarian' | 'coup-from-above' | 'velvet-negotiated';

export type RevoltStatus =
  | 'concluded' | 'active' | 'consolidating' | 'dormant' | 'watchlist';

export type RevoltOutcome =
  | 'independence' | 'consolidated-democracy' | 'consolidated-autocracy'
  | 'restored-old-regime' | 'failed-suppressed' | 'civil-war'
  | 'ongoing-unresolved' | 'intra-regime-purge' | 'secession-partition';

export type ResistanceType = 'nonviolent' | 'armed' | 'hybrid';
export type MilitaryDefection = 'none' | 'partial' | 'full' | 'unknown';
export type ForeignIntervention = 'none' | 'diplomatic' | 'material' | 'direct-military' | 'unknown';

export type PhaseKey =
  | 'old-regime-crisis' | 'intellectual-desertion' | 'the-spark' | 'moderate-phase'
  | 'dual-power' | 'radical-phase' | 'terror-virtue' | 'thermidor' | 'consolidation';

export type RevoltViewpointType =
  | 'revolutionary' | 'movement' | 'regime' | 'counter-revolutionary'
  | 'moderate' | 'radical' | 'military' | 'academic' | 'diaspora' | 'indigenous';

export type RevoltConnectionType =
  | 'inspired' | 'provided-model' | 'triggered-contagion' | 'provoked-backlash'
  | 'shared-repertoire' | 'parallel' | 'counter-example';

export type FactorDirection = 'favors-movement' | 'favors-regime' | 'indeterminate';

/* ── Sub-objects ── */

export interface Grievance {
  kind: string;
  /** 0-100 pressure gauge fill */
  intensity: number;
  evidence: string;
}

export interface Actor {
  actorType: string;
  name: string;
  description: string;
  roleInArc: string;
  defected: boolean;
}

export interface Tactic {
  tacticType: string;
  description: string;
  prominence: string;
}

export interface RevoltPhase {
  phase: PhaseKey;
  label: string;
  dateStart?: string;
  /** Pre-normalized position on the shared [0,1] arc skeleton */
  tStart: number;
  tEnd: number;
  /** 0-100 y-height for the phase-arc chart */
  intensity: number;
  /** false = this revolution never reached this phase; the curve truncates */
  reached: boolean;
  summary: string;
  keyEvents: string[];
}

export interface SuccessFactor {
  factorKey: string;
  label: string;
  framework: string;
  /** This movement's dated, cited status — never a verdict */
  status: string;
  direction: FactorDirection;
  /** The cited scholarly base rate, quoted */
  baseRate: string;
  rationale: string;
  sources: string[];
  asOf?: string;
  confidence?: string;
}

export interface RevoltKeyFigure {
  name: string;
  role: string;
  born?: number;
  died?: number;
  wikipedia?: string;
}

export interface RevoltPerspective {
  id: string;
  viewpoint: string;
  viewpointType: RevoltViewpointType;
  regionOrigin: string;
  narrative: string;
  keyArguments: string[];
  emphasized: string[];
  omitted: string[];
  notableQuotes: { text: string; speaker: string; context: string }[];
}

export interface RevoltConnection {
  targetSlug: string;
  targetTitle: string;
  type: RevoltConnectionType;
  description: string;
}

export interface RevoltMediaItem {
  id: string;
  type: 'image' | 'photograph' | 'painting' | 'artwork' | 'map' | 'poster' | 'document' | 'video';
  url: string;
  caption: string;
  attribution: string;
  year?: string;
}

/** The keyword/entity spec used by the live-news bridge (revoltContext.ts). */
export interface LiveQuery {
  /** Unique names/orgs/leaders — a single hit qualifies */
  strong: string[];
  /** Country/city names — must co-occur with a revolt lexicon term */
  context: string[];
  /** Disambiguation guards — presence kills the match */
  exclude?: string[];
}

export interface Revolution {
  id: string;
  slug: string;
  title: string;
  subtitle: string;
  era: RevoltEra;
  region: RevoltRegion;
  country: string;
  revoltType: RevoltType;
  status: RevoltStatus;

  dateDisplay: string;
  dateStart: number;
  dateEnd?: number;

  summary: string;
  significance: string;
  analyticalOutlook?: string;

  grievances: Grievance[];
  structuralPressures?: Record<string, { score: number; note: string }>;
  repressionLevel?: string;

  actors: Actor[];
  tactics: Tactic[];
  resistanceType?: ResistanceType;

  phases: RevoltPhase[];
  ateItsChildren?: boolean;

  outcome?: RevoltOutcome;
  peakParticipationPct?: number | null;
  peakParticipationDisplay?: string;
  crossedParticipationThreshold?: boolean | null;
  militaryDefection?: MilitaryDefection;
  foreignIntervention?: ForeignIntervention;
  durationDays?: number | null;
  deathToll?: string;
  deathTollLow?: number | null;
  deathTollHigh?: number | null;
  regimeBefore?: string;
  regimeAfter?: string;
  democratizationDelta?: number | null;

  successFactors: SuccessFactor[];

  keyFigures: RevoltKeyFigure[];
  legacyPoints: string[];
  perspectives: RevoltPerspective[];
  connections: RevoltConnection[];
  media: RevoltMediaItem[];

  heroImage?: string;
  heroAttribution?: string;

  relatedRevoltSlugs: string[];
  relatedHistorySlugs: string[];

  liveQuery?: LiveQuery;
  analysisReviewedAt?: string;
  predictionConfidence?: string;

  published: boolean;
}

/** A live-news cluster matched to an active revolution by revoltContext.ts. */
export interface LiveCard {
  id: string;
  title: string;
  summary: string;
  category: string;
  lastUpdated: string;
  sourceCount?: number;
  /** Bridge match score, 1 or 2 */
  score: number;
}

/* ── Era / status display metadata ── */

export interface RevoltEraInfo {
  id: RevoltEra;
  label: string;
  dateRange: string;
  description: string;
}

export const REVOLT_ERAS: RevoltEraInfo[] = [
  { id: 'classical', label: 'Classical Upheavals', dateRange: 'to 1600', description: 'Peasant revolts and dynastic overthrows before the modern nation' },
  { id: 'atlantic', label: 'The Atlantic Wave', dateRange: '1640 - 1830', description: 'English, American, French and Haitian revolutions remake sovereignty' },
  { id: 'springtime', label: 'Springtime of Nations', dateRange: '1848 - 1871', description: 'Liberal and national uprisings sweep Europe' },
  { id: 'modern-nationalist', label: 'Modern Nationalist', dateRange: '1900 - 1945', description: 'Mexican, Russian and nationalist revolutions of the industrial age' },
  { id: 'anticolonial', label: 'Anticolonial', dateRange: '1945 - 1975', description: 'Empires fall as colonies win independence' },
  { id: 'people-power', label: 'People Power', dateRange: '1979 - 1991', description: 'Iran, the Philippines and the fall of communism' },
  { id: 'color-revolutions', label: 'Color Revolutions', dateRange: '2000 - 2010', description: 'Electoral uprisings across the post-Soviet space' },
  { id: 'square-revolutions', label: 'The Square', dateRange: '2011 - present', description: 'Arab Spring and the age of the occupied plaza' },
];

export interface RevoltRegionInfo { id: RevoltRegion; label: string }

export const REVOLT_REGIONS: RevoltRegionInfo[] = [
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

export const ACTIVE_STATUSES: RevoltStatus[] = ['active', 'consolidating', 'dormant', 'watchlist'];

export function isActiveStatus(s: RevoltStatus): boolean {
  return ACTIVE_STATUSES.includes(s);
}
