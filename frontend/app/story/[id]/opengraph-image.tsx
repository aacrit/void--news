/* Per-story share card. Before this, every one of the archived Deep Dives
   shared the site-wide brand image: a reader sent a link about a ceasefire and
   the preview said "Void News. See through the void." */
import { getArchiveRowById } from "../../lib/archive";
import { voidCard, SITE_TITLE, SITE_TAGLINE } from "../../lib/ogCard";
import { storyCard, storyCardIds, size, contentType } from "./ogCard";

// Required under `output: export`: without it the image is treated as a
// dynamic route handler and the build refuses to collect it.
export const dynamic = "force-static";
export const dynamicParams = false;
export { size, contentType };
export const alt = "A Void News Deep Dive";

/** A SUBSET of the page's params, on purpose: only the latest edition gets a
 *  card (see ogCard.tsx). The page re-declares the site-wide card for every id
 *  that is not in this set, so no story is left with a broken preview. */
export async function generateStaticParams(): Promise<{ id: string }[]> {
  return [...(await storyCardIds())].map((id) => ({ id }));
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const row = await getArchiveRowById(id);
  // generateStaticParams only emits ids that are in the archive, so this is a
  // type guard rather than a reachable branch.
  if (!row) return voidCard({ title: SITE_TITLE, tagline: SITE_TAGLINE });
  return storyCard(row);
}
