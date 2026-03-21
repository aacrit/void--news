import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import HomeContent from "../components/HomeContent";

export function generateStaticParams() {
  // "world" is handled by the root page.tsx (/) — exclude it here to avoid
  // a duplicate /world route that conflicts with the World tab's href="/".
  return EDITIONS.filter((e) => e.slug !== "world").map((e) => ({ edition: e.slug }));
}

export default async function EditionPage({
  params,
}: {
  params: Promise<{ edition: string }>;
}) {
  const { edition } = await params;

  // Validate — fall back to world if slug is unknown
  const validEdition = EDITIONS.find((e) => e.slug === edition)
    ? (edition as Edition)
    : "world";

  return <HomeContent initialEdition={validEdition} />;
}
