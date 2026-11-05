import type { Metadata } from "next";
import { ERAS } from "../../types";
import { eraMetadata } from "../../historyMeta";
import EraPageClient from "./EraPageClient";

/* ===========================================================================
   /history/era/[era] — Era browser page.

   A thin server page that owns the metadata; the client tree below keeps the
   data fetch and the era nav. Until this pass the route exported no metadata
   at all, so all six served pages carried the root layout's title and the
   site-wide card.
   =========================================================================== */

export function generateStaticParams() {
  return ERAS.map((e) => ({ era: e.id }));
}

export async function generateMetadata(
  { params }: { params: Promise<{ era: string }> },
): Promise<Metadata> {
  const { era } = await params;
  const info = ERAS.find((e) => e.id === era);
  if (!info) return { title: "History | Void News" };
  return eraMetadata({
    label: info.label,
    dateRange: info.dateRange,
    description: info.description,
    era: info.id,
  });
}

export default function EraPage({ params }: { params: Promise<{ era: string }> }) {
  return <EraPageClient eraPromise={params} />;
}
