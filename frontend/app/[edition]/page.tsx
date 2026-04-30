import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import HomeContent from "../components/HomeContent";

export function generateStaticParams() {
  // Return all edition slugs for static generation.
  // The root page.tsx (/) also handles "world" to provide a canonical / route.
  // This route supports /world, /us, /europe, /south-asia for direct access.
  return EDITIONS.map((e) => ({ edition: e.slug }));
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
