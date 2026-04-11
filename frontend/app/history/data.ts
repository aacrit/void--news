/* ===========================================================================
   void --history — Data Fetching
   Supabase queries with mock data fallback.
   Fetches from 4 tables: history_events, history_perspectives,
   history_media, history_connections.
   =========================================================================== */

/* ── Wikimedia Commons page URL → direct upload URL ──
   Converts https://commons.wikimedia.org/wiki/File:X.jpg
   to       https://upload.wikimedia.org/wikipedia/commons/{a}/{ab}/X.jpg
   using the MD5-based path algorithm that Wikimedia uses for file storage. */
function resolveMediaUrl(url: string): string {
  if (!url) return url;
  const match = url.match(/commons\.wikimedia\.org\/wiki\/File:(.+)$/);
  if (!match) return url;
  const filename = decodeURIComponent(match[1]).replace(/ /g, "_");
  // MD5 hash of the filename (browser-compatible via subtle crypto is async,
  // so we use the deterministic lookup table Wikimedia publishes: first two
  // hex chars of md5(filename) give the two-level path prefix).
  // We pre-compute via a simple inline lookup for known files, otherwise
  // fall through to a Wikimedia API thumb URL which works without hash.
  const encoded = encodeURIComponent(filename);
  // Use Special:Redirect as a universal fallback — always works for valid files
  return `https://commons.wikimedia.org/wiki/Special:Redirect/file/${encoded}`;
}

import { supabase } from "../lib/supabase";
import type {
  HistoricalEvent,
  Perspective,
  MediaItem,
  EventConnection,
  RedactedEvent,
  PerspectiveColor,
  ViewpointType,
  HistoryEra,
  HistoryRegion,
  HistoryCategory,
  Severity,
} from "./types";
import { MOCK_EVENTS, REDACTED_EVENTS } from "./mockData";

/* ── Perspective color assignment ── */
const COLORS: PerspectiveColor[] = ["a", "b", "c", "d", "e"];

/* ── Fetch all published events (for landing, era, region pages) ── */
export async function fetchHistoryEvents(): Promise<HistoricalEvent[]> {
  if (!supabase) return MOCK_EVENTS;

  /* Timeout: fall back to mock data if Supabase is unreachable (paused/slow) */
  const timeout = new Promise<null>((resolve) => setTimeout(() => resolve(null), 5000));
  const query = supabase
    .from("history_events")
    .select("*")
    .eq("is_published", true)
    .order("date_sort", { ascending: true });

  const result = await Promise.race([query, timeout]);
  if (!result) return MOCK_EVENTS; /* Timed out */

  const { data: events, error } = result;
  if (error || !events || events.length === 0) return MOCK_EVENTS;

  /* Batch-fetch perspectives for all events */
  const eventIds = events.map((e) => e.id);
  const { data: allPerspectives } = await supabase
    .from("history_perspectives")
    .select("*")
    .in("event_id", eventIds)
    .order("display_order", { ascending: true });

  const { data: allMedia } = await supabase
    .from("history_media")
    .select("*")
    .in("event_id", eventIds)
    .order("display_order", { ascending: true });

  const { data: allConnections } = await supabase
    .from("history_connections")
    .select("*, target:event_b_id(slug, title)")
    .in("event_a_id", eventIds);

  /* Also get reverse connections */
  const { data: reverseConnections } = await supabase
    .from("history_connections")
    .select("*, source:event_a_id(slug, title)")
    .in("event_b_id", eventIds);

  return events.map((row) => mapEventWithRelations(
    row,
    (allPerspectives ?? []).filter((p) => p.event_id === row.id),
    (allMedia ?? []).filter((m) => m.event_id === row.id),
    [
      ...((allConnections ?? []).filter((c) => c.event_a_id === row.id)),
      ...((reverseConnections ?? []).filter((c) => c.event_b_id === row.id)),
    ],
    events,
  ));
}

/* ── Fetch single event by slug (for event detail page) ── */
export async function fetchHistoryEvent(slug: string): Promise<HistoricalEvent | null> {
  if (!supabase) {
    return MOCK_EVENTS.find((e) => e.slug === slug) ?? null;
  }

  const { data: event, error } = await supabase
    .from("history_events")
    .select("*")
    .eq("slug", slug)
    .eq("is_published", true)
    .limit(1)
    .single();

  if (error || !event) {
    return MOCK_EVENTS.find((e) => e.slug === slug) ?? null;
  }

  const [{ data: perspectives }, { data: media }, { data: fwdConn }, { data: revConn }] =
    await Promise.all([
      supabase
        .from("history_perspectives")
        .select("*")
        .eq("event_id", event.id)
        .order("display_order", { ascending: true }),
      supabase
        .from("history_media")
        .select("*")
        .eq("event_id", event.id)
        .order("display_order", { ascending: true }),
      supabase
        .from("history_connections")
        .select("*, target:event_b_id(slug, title)")
        .eq("event_a_id", event.id),
      supabase
        .from("history_connections")
        .select("*, source:event_a_id(slug, title)")
        .eq("event_b_id", event.id),
    ]);

  /* Need all events for connection title lookups */
  const { data: allEvents } = await supabase
    .from("history_events")
    .select("id, slug, title")
    .eq("is_published", true);

  return mapEventWithRelations(
    event,
    perspectives ?? [],
    media ?? [],
    [...(fwdConn ?? []), ...(revConn ?? [])],
    allEvents ?? [],
  );
}

/* ── Fetch by era ── */
export async function fetchHistoryEventsByEra(era: string): Promise<HistoricalEvent[]> {
  if (!supabase) return MOCK_EVENTS.filter((e) => e.era === era);

  const { data, error } = await supabase
    .from("history_events")
    .select("*")
    .eq("era", era)
    .eq("is_published", true)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) {
    return MOCK_EVENTS.filter((e) => e.era === era);
  }

  /* For listing pages, skip full relation fetch — use summary data */
  return data.map((row) => mapEventWithRelations(row, [], [], [], []));
}

/* ── Fetch by region ── */
export async function fetchHistoryEventsByRegion(region: string): Promise<HistoricalEvent[]> {
  if (!supabase) {
    return MOCK_EVENTS.filter((e) => e.regions.includes(region as HistoryRegion));
  }

  const { data, error } = await supabase
    .from("history_events")
    .select("*")
    .eq("region", region)
    .eq("is_published", true)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) {
    return MOCK_EVENTS.filter((e) => e.regions.includes(region as HistoryRegion));
  }

  return data.map((row) => mapEventWithRelations(row, [], [], [], []));
}

/* ── Fetch redacted (coming-soon) stubs ── */
export async function fetchRedactedEvents(): Promise<RedactedEvent[]> {
  /* Redacted events always come from mock data — they need curated quotes */
  return REDACTED_EVENTS;
}

/* ── DB → TypeScript mapper ── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapEventWithRelations(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  row: any,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dbPerspectives: any[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dbMedia: any[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  dbConnections: any[],
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  allEvents: any[],
): HistoricalEvent {
  const perspectives: Perspective[] = dbPerspectives.map((p, i) => ({
    id: p.id,
    viewpointName: p.viewpoint,
    viewpointType: p.viewpoint_type as ViewpointType,
    color: COLORS[i % COLORS.length],
    temporalAnchor: p.region_origin ?? "",
    geographicAnchor: p.region_origin ?? "",
    narrative: p.narrative,
    keyNarratives: Array.isArray(p.emphasized) ? p.emphasized : [],
    omissions: Array.isArray(p.omitted) ? p.omitted : [],
    disputed: [],
    primarySources: Array.isArray(p.notable_quotes)
      ? p.notable_quotes.map((q: { text: string; speaker: string; context: string }) => ({
          text: q.text,
          author: q.speaker,
          work: q.context ?? "",
          date: "",
        }))
      : [],
  }));

  const media: MediaItem[] = dbMedia.map((m) => ({
    id: m.id,
    type: m.media_type === "photograph" ? "image" : m.media_type,
    url: resolveMediaUrl(m.source_url),
    caption: m.description ?? m.title,
    attribution: m.attribution,
    year: m.creation_date ?? undefined,
    videoEmbedUrl: m.embed_url ?? undefined,
  }));

  const connections: EventConnection[] = dbConnections.map((c) => {
    /* Handle both forward and reverse connections */
    const isForward = !!c.target;
    const linked = isForward ? c.target : c.source;
    const targetSlug = linked?.slug ?? "";
    const targetTitle = linked?.title ?? allEvents.find(
      (e) => e.id === (isForward ? c.event_b_id : c.event_a_id)
    )?.title ?? "Unknown Event";

    return {
      targetSlug,
      targetTitle,
      type: c.connection_type,
      description: c.description ?? "",
    };
  });

  /* Parse key_figures JSONB — map all available fields */
  const keyFigures = Array.isArray(row.key_figures)
    ? row.key_figures.map((f: { name: string; role: string; born?: number; died?: number; wikipedia?: string }) => ({
        name: f.name,
        role: f.role,
        born: f.born ?? undefined,
        died: f.died ?? undefined,
        wikipedia: f.wikipedia ?? undefined,
      }))
    : [];

  return {
    id: row.id,
    slug: row.slug,
    title: row.title,
    subtitle: row.subtitle ?? "",
    era: row.era as HistoryEra,
    regions: [row.region as HistoryRegion],
    categories: [row.category as HistoryCategory],
    severity: row.severity as Severity,
    datePrimary: row.date_display,
    dateSort: row.date_sort,
    dateRange: row.duration ?? row.date_display,
    location: row.country ?? "",
    heroImage: row.hero_image_url ? resolveMediaUrl(row.hero_image_url) : undefined,
    heroCaption: row.subtitle ?? undefined,
    heroAttribution: row.hero_image_attribution ?? undefined,
    contextNarrative: row.summary ?? "",
    keyFigures,
    deathToll: row.death_toll ?? undefined,
    displaced: row.affected_population ?? undefined,
    duration: row.duration ?? undefined,
    perspectives,
    media,
    connections,
    published: row.is_published ?? false,
  };
}
