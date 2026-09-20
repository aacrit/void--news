import type { Metadata } from "next";
import { MOCK_EVENTS } from "../mockData";
import { HOOKS } from "../hooks";
import { getHistoryEntry, getHistorySlugs } from "../../lib/historyCatalog";
import { eventMetadata } from "../historyMeta";
import EventPageClient from "./EventPageClient";

/* ===========================================================================
   /history/[slug] — Individual event detail page
   generateStaticParams for static export. Client component handles data.
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

export default function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  return <EventPageClient slugPromise={params} />;
}
