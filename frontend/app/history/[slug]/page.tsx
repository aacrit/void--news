import { MOCK_EVENTS } from "../mockData";
import EventPageClient from "./EventPageClient";

/* ===========================================================================
   /history/[slug] — Individual event detail page
   generateStaticParams for static export. Client component handles data.
   =========================================================================== */

/* All known event slugs — mock data + YAML/Supabase canonical slugs */
const YAML_SLUGS = [
  "armenian-genocide",
  "ashoka-maurya-empire",
  "bolivarian-revolutions",
  "cambodian-genocide",
  "congo-free-state",
  "creation-of-israel-nakba",
  "fall-of-berlin-wall",
  "fall-of-rome",
  "french-revolution",
  "haitian-revolution",
  "hiroshima-nagasaki",
  "holodomor",
  "mali-empire-mansa-musa",
  "meiji-restoration",
  "mongol-conquest-baghdad",
  "opium-wars",
  "partition-of-india",
  "peloponnesian-war",
  "rwandan-genocide",
  "scramble-for-africa",
  "the-crusades",
  "tiananmen-square",
  "trail-of-tears",
  "transatlantic-slave-trade",
  "treaty-of-waitangi",
];

export function generateStaticParams() {
  const mockSlugs = MOCK_EVENTS.map((e) => e.slug);
  const allSlugs = [...new Set([...mockSlugs, ...YAML_SLUGS])];
  return allSlugs.map((slug) => ({ slug }));
}

export default function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  return <EventPageClient slugPromise={params} />;
}
