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
  "alexanders-conquests",
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
  "cyrus-cylinder",
  "creation-of-israel-nakba",
  "cuban-missile-crisis",
  "fall-of-berlin-wall",
  "fall-of-rome",
  "fall-of-tenochtitlan",
  "french-revolution",
  "gutenberg-printing-press",
  "haitian-revolution",
  "hiroshima-nagasaki",
  "holodomor",
  "indian-independence-movement",
  "mali-empire-mansa-musa",
  "meiji-restoration",
  "mongol-conquest-baghdad",
  "mongol-empire",
  "opium-wars",
  "partition-of-india",
  "peloponnesian-war",
  "russian-revolution",
  "rwandan-genocide",
  "scramble-for-africa",
  "september-11-attacks",
  "silk-road",
  "the-crusades",
  "the-holocaust",
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

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const event = MOCK_EVENTS.find((e) => e.slug === slug);
  const title = event?.title ?? slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const description = HOOKS[slug] ?? event?.subtitle ?? `One event. Every side. Decide for yourself.`;
  return {
    title: `${title} — void --history`,
    description,
  };
}

export default function EventPage({ params }: { params: Promise<{ slug: string }> }) {
  return <EventPageClient slugPromise={params} />;
}
