import type { Metadata } from "next";
import { MOCK_EVENTS } from "../mockData";
import { HOOKS } from "../hooks";
import {
  getHistoryEntry,
  getHistoryRow,
  getHistoryRows,
  getHistorySlugs,
} from "../../lib/historyCatalog";
import { getHistoryScript } from "../../lib/historyScript";
import { mapRow } from "../data";
import { buildHearing } from "../hearing";
import Hearing from "../components/Hearing";
import { eventMetadata } from "../historyMeta";

/* ===========================================================================
   /history/[slug] — one event, as The Hearing.

   A SERVER component. It used to render EventPageClient, which fetched
   /data/history.json in a useEffect, so the served HTML said "Retrieving
   archival record..." and nothing else: no open, no accounts, no turn. The
   weekly was prerendered in rev 71 for exactly this reason.

   Now the event row and the parsed script are both read at build time and the
   page is markup. Three client islands remain, and each is one because it
   needs browser state that cannot exist at build: the rail (where the reader
   is), the Listen button (the shared player's queue), and the gallery's
   lightbox (an overlay with a focus trap).
   =========================================================================== */

export function generateStaticParams() {
  /* Slugs come from the emitted catalog (data/history/events/*.yaml). Mock
     slugs stay in the union so the redacted/placeholder events still prerender
     when the snapshot is missing. */
  const allSlugs = [...new Set([...MOCK_EVENTS.map((e) => e.slug), ...getHistorySlugs()])];
  return allSlugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  /* Real catalog first; mock data only covers ten of the seventy-eight events,
     so resolving against it alone left most pages with a slug-derived title. */
  const event = getHistoryEntry(slug) ?? MOCK_EVENTS.find((e) => e.slug === slug);
  const title = event?.title || slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description = HOOKS[slug] || event?.subtitle || `One event. Every side. Decide for yourself.`;
  /* Was a bare {title, description}: no canonical, no openGraph, no twitter
     card, so every event page fell back to the root layout's site-wide image.
     `eventMetadata` adds those AND removes the inherited image so the
     per-event `opengraph-image.tsx` beside this file is the one that wins. */
  return eventMetadata({ title, description, slug });
}

export default async function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;

  const row = getHistoryRow(slug);
  const event = row
    ? mapRow(row, getHistoryRows())
    : MOCK_EVENTS.find((e) => e.slug === slug) ?? null;

  if (!event) {
    return (
      <div className="hist-main hist-not-found">
        <h1>Record Not Found</h1>
        <p>This archival record has not been declassified or does not exist.</p>
      </div>
    );
  }

  /* No script exported for this slug yet: the hero and the record still render.
     A missing export should look like a page without a spine, not a failure. */
  const script = getHistoryScript(slug);
  const hearing = script ? buildHearing(script, event) : null;

  /* Chronologically next, for the exit. Read from the same rows, so it does not
     cost a second pass over the catalog. */
  const rows = getHistoryRows();
  const ordered = [...rows].sort((a, b) => (a.date_sort ?? 0) - (b.date_sort ?? 0));
  const at = ordered.findIndex((r) => r.slug === slug);
  const next =
    at >= 0 && at < ordered.length - 1
      ? { slug: String(ordered[at + 1].slug), title: String(ordered[at + 1].title ?? "") }
      : null;

  return <Hearing event={event} hearing={hearing} nextEvent={next} />;
}
