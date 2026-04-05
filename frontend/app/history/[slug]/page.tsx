import { MOCK_EVENTS } from "../mockData";
import EventPageClient from "./EventPageClient";

/* ===========================================================================
   /history/[slug] — Individual event detail page
   generateStaticParams for static export. Client component handles data.
   =========================================================================== */

/* All known event slugs — mock data + YAML/Supabase canonical slugs */
const YAML_SLUGS = [
  "partition-of-india",
  "hiroshima-nagasaki",
  "rwandan-genocide",
  "creation-of-israel-nakba",
  "fall-of-berlin-wall",
  "french-revolution",
  "opium-wars",
  "scramble-for-africa",
  "trail-of-tears",
  "transatlantic-slave-trade",
];

export function generateStaticParams() {
  const mockSlugs = MOCK_EVENTS.map((e) => e.slug);
  const allSlugs = [...new Set([...mockSlugs, ...YAML_SLUGS])];
  return allSlugs.map((slug) => ({ slug }));
}

export default function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  return <EventPageClient slugPromise={params} />;
}
