/* ===========================================================================
   void --history — Data Fetching
   Supabase queries with mock data fallback.
   =========================================================================== */

import { supabase } from "../lib/supabase";
import type { HistoricalEvent, RedactedEvent } from "./types";
import { MOCK_EVENTS, REDACTED_EVENTS } from "./mockData";

/**
 * Fetch all published historical events.
 * Falls back to mock data when Supabase is unavailable or empty.
 */
export async function fetchHistoryEvents(): Promise<HistoricalEvent[]> {
  if (!supabase) return MOCK_EVENTS;

  const { data, error } = await supabase
    .from("historical_events")
    .select("*")
    .eq("published", true)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) return MOCK_EVENTS;

  return data.map(mapDbEventToType);
}

/**
 * Fetch a single historical event by slug.
 * Falls back to mock data when Supabase is unavailable or not found.
 */
export async function fetchHistoryEvent(slug: string): Promise<HistoricalEvent | null> {
  if (!supabase) {
    return MOCK_EVENTS.find((e) => e.slug === slug) ?? null;
  }

  const { data, error } = await supabase
    .from("historical_events")
    .select("*")
    .eq("slug", slug)
    .eq("published", true)
    .limit(1)
    .single();

  if (error || !data) {
    return MOCK_EVENTS.find((e) => e.slug === slug) ?? null;
  }

  return mapDbEventToType(data);
}

/**
 * Fetch historical events filtered by era.
 * Falls back to mock data filtered by era.
 */
export async function fetchHistoryEventsByEra(era: string): Promise<HistoricalEvent[]> {
  if (!supabase) {
    return MOCK_EVENTS.filter((e) => e.era === era);
  }

  const { data, error } = await supabase
    .from("historical_events")
    .select("*")
    .eq("era", era)
    .eq("published", true)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) {
    return MOCK_EVENTS.filter((e) => e.era === era);
  }

  return data.map(mapDbEventToType);
}

/**
 * Fetch historical events filtered by region.
 * Falls back to mock data filtered by region.
 */
export async function fetchHistoryEventsByRegion(region: string): Promise<HistoricalEvent[]> {
  if (!supabase) {
    return MOCK_EVENTS.filter((e) => e.regions.includes(region as HistoricalEvent["regions"][number]));
  }

  const { data, error } = await supabase
    .from("historical_events")
    .select("*")
    .contains("regions", [region])
    .eq("published", true)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) {
    return MOCK_EVENTS.filter((e) => e.regions.includes(region as HistoricalEvent["regions"][number]));
  }

  return data.map(mapDbEventToType);
}

/**
 * Fetch redacted (coming-soon) event stubs.
 */
export async function fetchRedactedEvents(): Promise<RedactedEvent[]> {
  if (!supabase) return REDACTED_EVENTS;

  const { data, error } = await supabase
    .from("historical_events")
    .select("id, slug, title, era, regions, date_hint")
    .eq("published", false)
    .order("date_sort", { ascending: true });

  if (error || !data || data.length === 0) return REDACTED_EVENTS;

  /* Map unpublished events to redacted stubs (quotes are in mock data only) */
  return data.map((row) => {
    const mock = REDACTED_EVENTS.find((r) => r.slug === row.slug);
    return {
      id: row.id,
      slug: row.slug,
      title: row.title,
      era: row.era,
      regions: row.regions ?? [],
      quoteA: mock?.quoteA ?? "",
      quoteB: mock?.quoteB ?? "",
      dateHint: row.date_hint ?? "",
    };
  });
}

/* ── DB Row → TypeScript type mapper ── */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function mapDbEventToType(row: any): HistoricalEvent {
  return {
    id: row.id,
    slug: row.slug,
    title: row.title,
    subtitle: row.subtitle ?? "",
    era: row.era,
    regions: row.regions ?? [],
    categories: row.categories ?? [],
    severity: row.severity ?? "major",
    datePrimary: row.date_primary ?? "",
    dateSort: row.date_sort ?? 0,
    dateRange: row.date_range ?? "",
    location: row.location ?? "",
    heroImage: row.hero_image ?? undefined,
    heroCaption: row.hero_caption ?? undefined,
    heroAttribution: row.hero_attribution ?? undefined,
    contextNarrative: row.context_narrative ?? "",
    keyFigures: row.key_figures ?? [],
    deathToll: row.death_toll ?? undefined,
    displaced: row.displaced ?? undefined,
    duration: row.duration ?? undefined,
    perspectives: row.perspectives ?? [],
    media: row.media ?? [],
    connections: row.connections ?? [],
    published: row.published ?? false,
  };
}
