import type { Edition } from "../../lib/types";
import { EDITIONS } from "../../lib/types";
import WeeklyDigest from "../../components/WeeklyDigest";

export function generateStaticParams() {
  // "world" is handled by /weekly/page.tsx — exclude it here
  return EDITIONS.filter((e) => e.slug !== "world").map((e) => ({
    edition: e.slug,
  }));
}

export default async function WeeklyEditionPage({
  params,
}: {
  params: Promise<{ edition: string }>;
}) {
  const { edition } = await params;

  const validEdition = EDITIONS.find((e) => e.slug === edition)
    ? (edition as Edition)
    : "world";

  return <WeeklyDigest edition={validEdition} />;
}
