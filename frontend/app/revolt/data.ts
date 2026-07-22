/* ===========================================================================
   void --revolt — Data fetching
   Supabase queries over the revolt_* tables with a 5s mock-race fallback.
   Mock data is already in the frontend (camelCase) shape and passes through;
   only raw DB rows go through mapRevolutionWithRelations (which also converts
   the snake_case JSONB internals the YAML/loader author).
   =========================================================================== */

import { supabase } from '../lib/supabase';
import type {
  Revolution, Grievance, Actor, Tactic, RevoltPhase, SuccessFactor,
  RevoltKeyFigure, RevoltPerspective, RevoltConnection, RevoltMediaItem,
  RevoltEra, RevoltRegion, RevoltType, RevoltStatus, RevoltOutcome,
  ResistanceType, MilitaryDefection, ForeignIntervention, PhaseKey,
  RevoltViewpointType, RevoltConnectionType, LiveQuery, LiveCard,
} from './types';
import { ACTIVE_STATUSES } from './types';
import { MOCK_REVOLUTIONS } from './mockData';
import { assignClustersToRevolts } from '../lib/revoltContext';

/* Wikimedia Commons page URL -> universal direct-file redirect. */
function resolveMediaUrl(url: string): string {
  if (!url) return url;
  const match = url.match(/commons\.wikimedia\.org\/wiki\/File:(.+)$/);
  if (!match) return url;
  const filename = decodeURIComponent(match[1]).replace(/ /g, '_');
  return `https://commons.wikimedia.org/wiki/Special:Redirect/file/${encodeURIComponent(filename)}`;
}

/* ── Public fetchers ── */

export async function fetchRevolutions(): Promise<Revolution[]> {
  if (!supabase) return MOCK_REVOLUTIONS;

  const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 5000));
  const query = supabase
    .from('revolt_events')
    .select('*')
    .eq('is_published', true)
    .order('display_order', { ascending: true })
    .order('date_start', { ascending: true });

  const result = await Promise.race([query, timeout]);
  if (!result) return MOCK_REVOLUTIONS;
  const { data: rows, error } = result;
  if (error || !rows || rows.length === 0) return MOCK_REVOLUTIONS;

  const ids = rows.map((r) => r.id);
  const [{ data: persp }, { data: media }, { data: fwd }, { data: rev }] = await Promise.all([
    supabase.from('revolt_perspectives').select('*').in('revolt_id', ids).order('display_order', { ascending: true }),
    supabase.from('revolt_media').select('*').in('revolt_id', ids).order('display_order', { ascending: true }),
    supabase.from('revolt_connections').select('*, target:revolt_b_id(slug, title)').in('revolt_a_id', ids),
    supabase.from('revolt_connections').select('*, source:revolt_a_id(slug, title)').in('revolt_b_id', ids),
  ]);

  return rows.map((row) => mapRevolutionWithRelations(
    row,
    (persp ?? []).filter((p) => p.revolt_id === row.id),
    (media ?? []).filter((m) => m.revolt_id === row.id),
    [...(fwd ?? []).filter((c) => c.revolt_a_id === row.id), ...(rev ?? []).filter((c) => c.revolt_b_id === row.id)],
    rows,
  ));
}

export async function fetchRevolution(slug: string): Promise<Revolution | null> {
  if (!supabase) return MOCK_REVOLUTIONS.find((r) => r.slug === slug) ?? null;

  const { data: row, error } = await supabase
    .from('revolt_events').select('*').eq('slug', slug).eq('is_published', true).limit(1).single();
  if (error || !row) return MOCK_REVOLUTIONS.find((r) => r.slug === slug) ?? null;

  const [{ data: persp }, { data: media }, { data: fwd }, { data: rev }, { data: all }] = await Promise.all([
    supabase.from('revolt_perspectives').select('*').eq('revolt_id', row.id).order('display_order', { ascending: true }),
    supabase.from('revolt_media').select('*').eq('revolt_id', row.id).order('display_order', { ascending: true }),
    supabase.from('revolt_connections').select('*, target:revolt_b_id(slug, title)').eq('revolt_a_id', row.id),
    supabase.from('revolt_connections').select('*, source:revolt_a_id(slug, title)').eq('revolt_b_id', row.id),
    supabase.from('revolt_events').select('id, slug, title').eq('is_published', true),
  ]);

  return mapRevolutionWithRelations(row, persp ?? [], media ?? [], [...(fwd ?? []), ...(rev ?? [])], all ?? []);
}

export async function fetchActiveRevolutions(): Promise<Revolution[]> {
  const all = await fetchRevolutions();
  return all.filter((r) => ACTIVE_STATUSES.includes(r.status));
}

export async function fetchConcludedRevolutions(): Promise<Revolution[]> {
  const all = await fetchRevolutions();
  return all.filter((r) => r.status === 'concluded');
}

/* ── The live-news bridge: match story_clusters to an active revolution ── */
const REVOLT_FEED_FIELDS =
  'id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,rank_world';
const FRESH_DAYS = 21;

export async function fetchLiveClustersFor(revolution: Revolution): Promise<LiveCard[]> {
  if (!supabase || !revolution.liveQuery) return [];

  const since = new Date(Date.now() - FRESH_DAYS * 864e5).toISOString();
  const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 5000));
  const query = supabase
    .from('story_clusters')
    .select(REVOLT_FEED_FIELDS)
    .contains('sections', ['world'])
    .in('category', ['conflict', 'politics'])
    .gte('last_updated', since)
    .order('rank_world', { ascending: false })
    .limit(150);

  const result = await Promise.race([query, timeout]);
  if (!result) return [];
  const { data, error } = result;
  if (error || !data) return [];

  const buckets = assignClustersToRevolts(data, [revolution]);
  const mine = buckets[revolution.slug] ?? [];
  return mine.slice(0, 6);
}

/* ── DB -> TS mapper (only for raw Supabase rows) ── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function arr(v: any): any[] { return Array.isArray(v) ? v : []; }

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapRevolutionWithRelations(row: any, dbPersp: any[], dbMedia: any[], dbConn: any[], allRows: any[]): Revolution {
  const grievances: Grievance[] = arr(row.grievances).map((g) => ({
    kind: g.kind, intensity: Number(g.intensity) || 0, evidence: g.evidence ?? '',
  }));

  const actors: Actor[] = arr(row.actors).map((a) => ({
    actorType: a.actor_type ?? a.actorType ?? 'masses',
    name: a.name, description: a.description ?? '',
    roleInArc: a.role_in_arc ?? a.roleInArc ?? '',
    defected: !!a.defected,
  }));

  const tactics: Tactic[] = arr(row.tactics).map((t) => ({
    tacticType: t.tactic_type ?? t.tacticType ?? 'mass-demonstration',
    description: t.description ?? '', prominence: t.prominence ?? 'medium',
  }));

  const phases: RevoltPhase[] = arr(row.phases).map((p) => ({
    phase: (p.phase) as PhaseKey,
    label: p.label ?? '',
    dateStart: p.date_start ?? p.dateStart,
    tStart: Number(p.t_start ?? p.tStart) || 0,
    tEnd: Number(p.t_end ?? p.tEnd) || 0,
    intensity: Number(p.intensity) || 0,
    reached: p.reached !== false,
    summary: p.summary ?? '',
    keyEvents: arr(p.key_events ?? p.keyEvents),
  }));

  const successFactors: SuccessFactor[] = arr(row.success_factors).map((f) => ({
    factorKey: f.factor_key ?? f.factorKey ?? '',
    label: f.label ?? '', framework: f.framework ?? '',
    status: f.status ?? '', direction: f.direction ?? 'indeterminate',
    baseRate: f.base_rate ?? f.baseRate ?? '', rationale: f.rationale ?? '',
    sources: arr(f.sources), asOf: f.as_of ?? f.asOf, confidence: f.confidence,
  }));

  const keyFigures: RevoltKeyFigure[] = arr(row.key_figures).map((f) => ({
    name: f.name, role: f.role, born: f.born ?? undefined, died: f.died ?? undefined, wikipedia: f.wikipedia ?? undefined,
  }));

  const perspectives: RevoltPerspective[] = dbPersp.map((p) => ({
    id: p.id,
    viewpoint: p.viewpoint,
    viewpointType: p.viewpoint_type as RevoltViewpointType,
    regionOrigin: p.region_origin ?? '',
    narrative: p.narrative ?? '',
    keyArguments: arr(p.key_arguments),
    emphasized: arr(p.emphasized),
    omitted: arr(p.omitted),
    notableQuotes: arr(p.notable_quotes).map((q) => ({ text: q.text, speaker: q.speaker, context: q.context ?? '' })),
  }));

  const media: RevoltMediaItem[] = dbMedia.map((m) => ({
    id: m.id,
    type: m.media_type === 'footage' ? 'video' : m.media_type,
    url: resolveMediaUrl(m.source_url),
    caption: m.description ?? m.title,
    attribution: m.attribution,
    year: m.creation_date ?? undefined,
  }));

  const connections: RevoltConnection[] = dbConn.map((c) => {
    const isForward = !!c.target;
    const linked = isForward ? c.target : c.source;
    const targetTitle = linked?.title
      ?? allRows.find((r) => r.id === (isForward ? c.revolt_b_id : c.revolt_a_id))?.title
      ?? 'Unknown';
    return {
      targetSlug: linked?.slug ?? '',
      targetTitle,
      type: c.connection_type as RevoltConnectionType,
      description: c.description ?? '',
    };
  });

  const liveQuery: LiveQuery | undefined = row.live_query
    ? {
        strong: arr(row.live_query.strong),
        context: arr(row.live_query.context),
        exclude: arr(row.live_query.exclude),
      }
    : undefined;

  return {
    id: row.id, slug: row.slug, title: row.title, subtitle: row.subtitle ?? '',
    era: row.era as RevoltEra, region: row.region as RevoltRegion, country: row.country ?? '',
    revoltType: row.revolt_type as RevoltType, status: row.status as RevoltStatus,
    dateDisplay: row.date_display, dateStart: row.date_start, dateEnd: row.date_end ?? undefined,
    summary: row.summary ?? '', significance: row.significance ?? '', analyticalOutlook: row.analytical_outlook ?? undefined,
    grievances,
    structuralPressures: row.structural_pressures && typeof row.structural_pressures === 'object' ? row.structural_pressures : undefined,
    repressionLevel: row.repression_level ?? undefined,
    actors, tactics, resistanceType: (row.resistance_type ?? undefined) as ResistanceType | undefined,
    phases, ateItsChildren: row.ate_its_children ?? undefined,
    outcome: (row.outcome ?? undefined) as RevoltOutcome | undefined,
    peakParticipationPct: row.peak_participation_pct ?? null,
    peakParticipationDisplay: row.peak_participation_display ?? undefined,
    crossedParticipationThreshold: row.crossed_participation_threshold ?? null,
    militaryDefection: (row.military_defection ?? undefined) as MilitaryDefection | undefined,
    foreignIntervention: (row.foreign_intervention ?? undefined) as ForeignIntervention | undefined,
    durationDays: row.duration_days ?? null,
    deathToll: row.death_toll ?? undefined,
    deathTollLow: row.death_toll_low ?? null,
    deathTollHigh: row.death_toll_high ?? null,
    regimeBefore: row.regime_before ?? undefined,
    regimeAfter: row.regime_after ?? undefined,
    democratizationDelta: row.democratization_delta ?? null,
    successFactors,
    keyFigures,
    legacyPoints: arr(row.legacy_points),
    perspectives, connections, media,
    heroImage: row.hero_image_url ? resolveMediaUrl(row.hero_image_url) : undefined,
    heroAttribution: row.hero_image_attribution ?? undefined,
    relatedRevoltSlugs: arr(row.related_revolt_slugs),
    relatedHistorySlugs: arr(row.related_history_slugs),
    liveQuery,
    analysisReviewedAt: row.analysis_reviewed_at ?? undefined,
    predictionConfidence: row.prediction_confidence ?? undefined,
    published: row.is_published ?? false,
  };
}
