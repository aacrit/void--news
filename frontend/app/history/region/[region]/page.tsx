import type { Metadata } from "next";
import { REGIONS } from "../../types";
import { regionMetadata } from "../../historyMeta";
import RegionPageClient from "./RegionPageClient";

/* ===========================================================================
   /history/region/[region] — Region explorer page.

   A thin server page that owns the metadata; the client tree below keeps the
   data fetch and the region nav. Until this pass the route exported no
   metadata at all, so all nine served pages carried the root layout's title
   and the site-wide card.
   =========================================================================== */

export function generateStaticParams() {
  return REGIONS.filter((r) => r.id !== "global").map((r) => ({ region: r.id }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ region: string }> },
): Promise<Metadata> {
  const { region } = await params;
  const info = REGIONS.find((r) => r.id === region);
  if (!info) return { title: "History | Void News" };
  return regionMetadata({ label: info.label, region: info.id });
}

export default function RegionPage({ params }: { params: Promise<{ region: string }> }) {
  return <RegionPageClient regionPromise={params} />;
}
