import type { Metadata } from "next";
import { MOCK_EVENTS } from "../mockData";
import { HOOKS } from "../hooks";
import EventPageClient from "./EventPageClient";

/* ===========================================================================
   /history/[slug] — Individual event detail page
   generateStaticParams for static export. Client component handles data.
   =========================================================================== */

/* All known event slugs — mock data + YAML/Supabase canonical slugs */
const YAML_SLUGS = [
  "apollo-11-moon-landing",
  "global-financial-crisis-2008",
  "great-depression",
  "nanjing-massacre",
  "six-day-war",
  "soviet-union-collapse",
  "spanish-flu-1918",
  "srebrenica-genocide",
  "sykes-picot-agreement",
  "world-war-i",
  "alexanders-conquests",
  "angkor-khmer-empire",
  "apartheid",
  "armenian-genocide",
  "ashoka-maurya-empire",
  "assassination-of-caesar",
  "black-death",
  "bolivarian-revolutions",
  "cambodian-genocide",
  "chinese-cultural-revolution",
  "civil-rights-movement",
  "congo-free-state",
  "creation-of-israel-nakba",
  "cuban-missile-crisis",
  "cyrus-cylinder",
  "fall-of-berlin-wall",
  "fall-of-constantinople",
  "fall-of-rome",
  "fall-of-tenochtitlan",
  "french-revolution",
  "gutenberg-printing-press",
  "haitian-revolution",
  "hiroshima-nagasaki",
  "holodomor",
  "inca-conquest-peru",
  "indian-independence-movement",
  "kingdom-of-kongo",
  "mali-empire-mansa-musa",
  "meiji-restoration",
  "mongol-conquest-baghdad",
  "mongol-empire",
  "mughal-empire",
  "opium-wars",
  "partition-of-india",
  "peloponnesian-war",
  "rise-of-islam",
  "russian-revolution",
  "rwandan-genocide",
  "scramble-for-africa",
  "september-11-attacks",
  "silk-road",
  "taiping-rebellion",
  "the-crusades",
  "the-holocaust",
  "tiananmen-square",
  "trail-of-tears",
  "transatlantic-slave-trade",
  "treaty-of-waitangi",
  // Batch 2 — 10 new events (2026-04-10)
  "arab-spring",
  "bandung-conference",
  "columbian-exchange",
  "congo-wars",
  "industrial-revolution",
  "iranian-revolution",
  "korean-war",
  "ottoman-empire",
  "vietnam-war",
  "womens-suffrage",
  // Batch 3 — 10 new events (2026-08-05)
  "algerian-war",
  "chernobyl-disaster",
  "chinese-civil-war",
  "cuban-revolution",
  "great-leap-forward",
  "iran-iraq-war",
  "spanish-civil-war",
  "suez-crisis",
  "the-reformation",
  "watergate",
];

export function generateStaticParams() {
  const mockSlugs = MOCK_EVENTS.map((e) => e.slug);
  const allSlugs = [...new Set([...mockSlugs, ...YAML_SLUGS])];
  return allSlugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const event = MOCK_EVENTS.find((e) => e.slug === slug);
  const title = event?.title ?? slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description = HOOKS[slug] ?? event?.subtitle ?? `One event. Every side. Decide for yourself.`;
  return {
    title: `${title} | History`,
    description,
  };
}

export default function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  return <EventPageClient slugPromise={params} />;
}
