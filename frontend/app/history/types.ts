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
  type: 'image' | 'map' | 'document' | 'artwork';
  url: string;
  caption: string;
  attribution: string;
  year?: string;
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
