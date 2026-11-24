/* ---------------------------------------------------------------------------
   historyCatalog — build-time reader for the History event catalog.

   The browser reads /data/history.json at runtime (app/history/data.ts). The
   BUILD also needs the catalog, for three things that must run on the server:
   generateStaticParams (which slugs to prerender), generateMetadata (per-event
   title + description), and the sitemap.

   Those three previously read a hand-maintained YAML_SLUGS array in
   history/[slug]/page.tsx plus MOCK_EVENTS. That list had to be edited by hand
   with every content batch, and metadata resolved against MOCK_EVENTS only, so
   68 of the 78 real events prerendered with a title derived from the slug and a
   generic description. Reading the emitted snapshot makes the YAML the single
   source for slugs and metadata alike.

   Server-only + deterministic: one memoized read, no network, no dates.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";

export interface HistoryCatalogEntry {
  slug: string;
  title: string;
  subtitle: string;
  era: string;
  region: string;
  /** "539 BCE", "1948". The event's own dateline, as the page sets it. The
   *  share card places the event in time with it. */
  dateDisplay: string;
}

/* The emitted row, relations nested, exactly as export_history.py writes it.
   Shape is asserted by nothing here on purpose: data.ts already owns the row →
   HistoricalEvent mapping and is the one place that knows the field names. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type HistoryRow = Record<string, any>;

let _catalog: HistoryCatalogEntry[] | null = null;
let _rows: HistoryRow[] | null = null;

/** The whole catalog, ordered as emitted (by date_sort). Empty on a missing
 *  snapshot: the build still succeeds and the routes fall back to mock data. */
export function getHistoryCatalog(): HistoryCatalogEntry[] {
  if (_catalog) return _catalog;
  const rows = getHistoryRows();
  _catalog = rows
    .filter((r) => typeof r.slug === "string" && r.slug)
    .map((r) => ({
      slug: String(r.slug),
      title: String(r.title ?? ""),
      subtitle: String(r.subtitle ?? ""),
      era: String(r.era ?? ""),
      region: String(r.region ?? ""),
      dateDisplay: String(r.date_display ?? ""),
    }));
  return _catalog;
}

/** Every emitted row with its relations nested, ordered as emitted.
 *
 *  The event page prerenders from this rather than fetching /data/history.json
 *  in the browser, so the spine, the five accounts and the turn are in the
 *  served HTML. A missing snapshot returns [] and the route falls back to mock
 *  data, exactly as the catalog does: a contributor who has never run the
 *  pipeline can still `next build`. */
export function getHistoryRows(): HistoryRow[] {
  if (_rows) return _rows;
  try {
    const raw = readFileSync(
      join(process.cwd(), "public", "data", "history.json"),
      "utf8",
    );
    const parsed = JSON.parse(raw) as HistoryRow[];
    _rows = Array.isArray(parsed) ? parsed : [];
  } catch {
    _rows = [];
  }
  return _rows;
}

/** One emitted row by slug, or null when the snapshot has no such event. */
export function getHistoryRow(slug: string): HistoryRow | null {
  return getHistoryRows().find((r) => r.slug === slug) ?? null;
}

export function getHistorySlugs(): string[] {
  return getHistoryCatalog().map((e) => e.slug);
}

export function getHistoryEntry(slug: string): HistoryCatalogEntry | undefined {
  return getHistoryCatalog().find((e) => e.slug === slug);
}
