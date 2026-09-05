import type { Edition } from "../../lib/types";
import { EDITIONS } from "../../lib/types";
import PaperContent from "../PaperContent";

export function generateStaticParams() {
  // "world" is handled by /paper/page.tsx — exclude it here.
  // When only "world" is active (pre-launch), return a placeholder to satisfy
  // Turbopack's requirement that dynamic routes have at least one param.
  const editions = EDITIONS.filter((e) => e.slug !== "world").map((e) => ({
    edition: e.slug,
  }));
  return editions.length > 0 ? editions : [{ edition: "world" }];
}

export default async function PaperEditionPage({
  params,
}: {
  params: Promise<{ edition: string }>;
}) {
  const { edition } = await params;

  const validEdition = EDITIONS.find((e) => e.slug === edition)
    ? (edition as Edition)
    : "world";

  return <PaperContent edition={validEdition} />;
}
