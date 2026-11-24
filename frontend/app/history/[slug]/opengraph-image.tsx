/* Per-event share card. Before this, all 78 event pages shared the site-wide
   image: a reader sent a link about Partition and saw the Void News logo. */
import { MOCK_EVENTS } from "../mockData";
import { getHistorySlugs, getHistoryEntry } from "../../lib/historyCatalog";
import { eventCard, size, contentType } from "../ogCard";

export const dynamic = "force-static";
export { size, contentType };
export const alt = "A Void History event";

/** Must mirror the page's own params, or a card is emitted for a route that
 *  does not exist (or worse, missed for one that does). */
export function generateStaticParams() {
  // MIRRORS page.tsx EXACTLY, mock slugs included. A card route that
  // prerenders a different set than its page either emits an image for a page
  // that does not exist or, worse, misses one that does, and `dynamicParams`
  // is false so there is no runtime fallback to cover the gap.
  const all = [...new Set([...MOCK_EVENTS.map((e) => e.slug), ...getHistorySlugs()])];
  return all.map((slug) => ({ slug }));
}

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const e = getHistoryEntry(slug);
  return eventCard({
    title: e?.title || slug.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
    date: e?.dateDisplay,
    region: e?.region,
  });
}
