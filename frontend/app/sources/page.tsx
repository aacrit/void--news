import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Metadata } from "next";
import type { SpectrumSource } from "../components/SpectrumChart";
import { pageMetadata } from "../lib/siteMeta";
import SourcesClient from "./SourcesClient";
import { SOURCE_TIERS } from "../film/data";

/* ---------------------------------------------------------------------------
   /sources — PRERENDERED source list (static export).

   This route wrapper is a Server Component so it can (1) export per-route
   metadata and (2) read data/sources.json at BUILD time and seed the client
   list, so the served HTML ships all curated sources (names in the spectrum
   logos' aria-labels + fallbacks) instead of an empty shell that fills in via
   a client fetch. The client component keeps all filtering / hover / search
   interactivity and revalidates from Supabase after mount.

   Read via fs (cwd = frontend/ at build) rather than a JSON import so the
   repo-root data file resolves cleanly and never lands in a client bundle.
   --------------------------------------------------------------------------- */

export const metadata: Metadata = pageMetadata({
  title: `${SOURCE_TIERS.total.toLocaleString()} Sources | Void News`,
  description:
    "Every outlet Void News reads, plotted on a seven-zone political lean spectrum. 1,016 hand-curated sources across three tiers and 158 countries, with the scoring methodology in full.",
  path: "/sources/",
});

interface RawSource {
  id: string;
  name: string;
  url: string;
  tier: string;
  country: string;
  political_lean_baseline: string | null;
}

/** Read + shape the curated source list at build time. */
function loadSources(): SpectrumSource[] {
  try {
    const raw = readFileSync(join(process.cwd(), "..", "data", "sources.json"), "utf-8");
    const parsed = JSON.parse(raw) as RawSource[];
    return parsed
      .map((s) => ({
        name: s.name,
        slug: s.id,
        url: s.url,
        tier: s.tier as SpectrumSource["tier"],
        country: s.country,
        political_lean_baseline: s.political_lean_baseline ?? null,
        // credibility_notes (long, tooltip-only) is NOT baked into the
        // prerender to keep the HTML lean; the client revalidation from
        // Supabase fills it in after mount.
        credibility_notes: null,
      }))
      .sort((a, b) => a.name.localeCompare(b.name));
  } catch {
    // Fail soft: an unreadable data file yields an empty seed; the client
    // fetch still populates the list. The home feed is the fail-loud surface.
    return [];
  }
}

export default function SourcesPage() {
  return <SourcesClient initialSources={loadSources()} />;
}
