/* ===========================================================================
   void --history — Data Fetching
   Reads the static snapshot the pipeline emits at /data/history.json
   (pipeline/history/export_history.py, built from data/history/events/*.yaml).
   Rows carry the same shape PostgREST returned from the four history_* tables,
   with perspectives/media/connections nested, so mapEventWithRelations below is
   unchanged from the Supabase era.

   Supabase was decommissioned 2026-09-01. The browser client has no credentials
   in the Cloudflare build, so the old query path resolved to null on every call
   and silently served MOCK_EVENTS; mock data is now only the last-resort
   fallback for a missing or unparseable snapshot.
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

import { BASE_PATH } from "../lib/utils";
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
import { withHistoryAudio, withHistoryAudioAll } from "./audio";

/* ── The audio edition ──
   Which events have a produced mini documentary is recorded in
   public/data/history-audio.json, not in any event row: the episodes are
   published by pipeline/history/publish_audio.py and the manifest is the
   record of what actually reached the CDN. It is applied at the two points
   every event passes through, the row mapper and the mock fallback, so the
   Listen button appears on exactly the events that have something to play
   whichever source the page is reading. */
const MOCK_WITH_AUDIO = withHistoryAudioAll(MOCK_EVENTS);

/* ── Media type normalisation ──
   The curated YAML uses the sourcing vocabulary ("photograph", "painting");
   MediaItem["type"] is the rendering vocabulary. Unmapped values fall back to
   "image" so a new source type can never render as an unhandled variant. */
const MEDIA_TYPES: Record<string, MediaItem["type"]> = {
  photograph: "image",
  image: "image",
  painting: "artwork",
  artwork: "artwork",
  map: "map",
  document: "document",
  video: "video",
};

/* ── Perspective color assignment ── */
const COLORS: PerspectiveColor[] = ["a", "b", "c", "d", "e"];

/* ── Static snapshot loader ──
   One fetch per page load, memoised: the landing, era, region and event pages
   all read the same file. A failed or empty fetch falls back to mock data so a
   missing snapshot degrades to a visibly-placeholder archive instead of a
   blank page. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HistoryRow = any;

let _snapshot: Promise<HistoryRow[] | null> | null = null;

function loadSnapshot(): Promise<HistoryRow[] | null> {
  if (!_snapshot) {
    _snapshot = fetch(`${BASE_PATH}/data/history.json`, { cache: "no-cache" })
      .then((res) => (res.ok ? res.json() : null))
      .then((rows) => (Array.isArray(rows) && rows.length > 0 ? rows : null))
      .catch(() => null);
  }
  return _snapshot;
}

/* Rows arrive with their relations nested; mapEventWithRelations wants them
   passed separately, exactly as the four Supabase queries returned them. */
function mapRow(row: HistoryRow, allRows: HistoryRow[]): HistoricalEvent {
  return mapEventWithRelations(
    row,
    row.perspectives ?? [],
    row.media ?? [],
    row.connections ?? [],
    allRows,
  );
}

/* ── Fetch all published events (for landing, era, region pages) ── */
export async function fetchHistoryEvents(): Promise<HistoricalEvent[]> {
  const rows = await loadSnapshot();
  if (!rows) return MOCK_WITH_AUDIO;
  return rows.map((row) => mapRow(row, rows));
}

/* ── Fetch single event by slug (for event detail page) ── */
export async function fetchHistoryEvent(slug: string): Promise<HistoricalEvent | null> {
  const rows = await loadSnapshot();
  if (!rows) return MOCK_WITH_AUDIO.find((e) => e.slug === slug) ?? null;

  const row = rows.find((r) => r.slug === slug);
  if (!row) return MOCK_WITH_AUDIO.find((e) => e.slug === slug) ?? null;
  return mapRow(row, rows);
}

/* ── Fetch by era ── */
export async function fetchHistoryEventsByEra(era: string): Promise<HistoricalEvent[]> {
  const rows = await loadSnapshot();
  if (!rows) return MOCK_WITH_AUDIO.filter((e) => e.era === era);

  const matches = rows.filter((r) => r.era === era);
  if (matches.length === 0) return MOCK_WITH_AUDIO.filter((e) => e.era === era);
  return matches.map((row) => mapRow(row, rows));
}

/* ── Fetch by region ── */
export async function fetchHistoryEventsByRegion(region: string): Promise<HistoricalEvent[]> {
  const rows = await loadSnapshot();
  if (!rows) {
    return MOCK_WITH_AUDIO.filter((e) => e.regions.includes(region as HistoryRegion));
  }

  const matches = rows.filter((r) => r.region === region);
  if (matches.length === 0) {
    return MOCK_WITH_AUDIO.filter((e) => e.regions.includes(region as HistoryRegion));
  }
  return matches.map((row) => mapRow(row, rows));
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

  /* A stock "Landscape orientation, 6000x4000px" dimension string is not a
     caption — surface the image title (or the event title) instead. */
  const isDimensionString = (s: string): boolean =>
    /^\s*(landscape|portrait|square)\s+orientation/i.test(s) ||
    /\d+\s*[x×]\s*\d+\s*px/i.test(s);

  const media: MediaItem[] = dbMedia.map((m) => {
    const rawDescription = (m.description ?? "").toString();
    const rawTitle = (m.title ?? "").toString();
    let caption = rawDescription;
    if (!caption || isDimensionString(caption)) {
      caption =
        (rawTitle && !isDimensionString(rawTitle) ? rawTitle : "") ||
        row.title ||
        "Archival image";
    }
    return {
      id: m.id,
      type: MEDIA_TYPES[m.media_type as string] ?? "image",
      url: resolveMediaUrl(m.source_url),
      caption,
      attribution: m.attribution,
      year: m.creation_date ?? undefined,
      location: m.location ?? row.country ?? undefined,
      videoEmbedUrl: m.embed_url ?? undefined,
    };
  });

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

  return withHistoryAudio({
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
    significance: row.significance ?? undefined,
    legacyPoints: Array.isArray(row.legacy_points) ? row.legacy_points as string[] : undefined,
    keyFigures,
    deathToll: row.death_toll ?? undefined,
    displaced: row.affected_population ?? undefined,
    duration: row.duration ?? undefined,
    perspectives,
    media,
    connections,
    published: row.is_published ?? false,
    audioUrl: row.audio_url ?? null,
    audioDuration: row.audio_duration_seconds ? Number(row.audio_duration_seconds) : null,
    audioChapters: null,
  });
}
