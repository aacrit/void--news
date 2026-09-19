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
}

let _catalog: HistoryCatalogEntry[] | null = null;

/** The whole catalog, ordered as emitted (by date_sort). Empty on a missing
 *  snapshot: the build still succeeds and the routes fall back to mock data. */
export function getHistoryCatalog(): HistoryCatalogEntry[] {
  if (_catalog) return _catalog;
  try {
    const raw = readFileSync(
      join(process.cwd(), "public", "data", "history.json"),
      "utf8",
    );
    const rows = JSON.parse(raw) as Record<string, unknown>[];
    _catalog = rows
      .filter((r) => typeof r.slug === "string" && r.slug)
      .map((r) => ({
        slug: String(r.slug),
        title: String(r.title ?? ""),
        subtitle: String(r.subtitle ?? ""),
        era: String(r.era ?? ""),
        region: String(r.region ?? ""),
      }));
  } catch {
    _catalog = [];
  }
  return _catalog;
}

export function getHistorySlugs(): string[] {
  return getHistoryCatalog().map((e) => e.slug);
}

export function getHistoryEntry(slug: string): HistoryCatalogEntry | undefined {
  return getHistoryCatalog().find((e) => e.slug === slug);
}
