import { notFound } from "next/navigation";
import { IgSlideClient } from "../IgSlideClient";

/* ---------------------------------------------------------------------------
   /ig/render/[postId] — 1080×1350 canvas rendered for Playwright.

   Reads the ig_posts row, hands the slide_specs to <IgSlideClient>, which picks
   the slide N from the `?slide=N` query and routes to the per-pillar template.

   This route is intentionally NOT part of the production static export
   (generateStaticParams emits only a placeholder). Post IDs are generated at
   runtime and cannot be known at build time. Playwright runs against
   `next dev` during the capture step, where output:export is dropped (see
   next.config.ts) so the route renders any post ID on demand.
   --------------------------------------------------------------------------- */

export async function generateStaticParams() {
  // Production static export: only the placeholder. Post IDs aren't known at
  // build time and this route is never served in prod.
  if (process.env.IG_RENDER_DYNAMIC !== "1") {
    return [{ postId: "placeholder" }];
  }
  // Dev capture (`next dev`, output:export dropped): enumerate the posts that
  // need rendering so they are valid params despite dynamicParams=false.
  try {
    const { listRenderablePostIds } = await import("../../../lib/supabase-server");
    const ids = await listRenderablePostIds();
    return [{ postId: "placeholder" }, ...ids.map((postId) => ({ postId }))];
  } catch {
    return [{ postId: "placeholder" }];
  }
}

// Must stay a static literal `false` — output:export rejects dynamicParams=true.
// Dev capture still renders real post IDs because generateStaticParams above
// enumerates them when IG_RENDER_DYNAMIC=1 (and output:export is dropped under
// `next dev` — see next.config.ts).
export const dynamicParams = false;

interface PageProps {
  params: Promise<{ postId: string }>;
}

export default async function IgRenderPage({ params }: PageProps) {
  const { postId } = await params;

  // Build-time placeholder render (output:export pre-bakes one HTML).
  if (postId === "placeholder") {
    return <div className="ig-canvas" data-placeholder="true" />;
  }

  // Dynamic import keeps the server-only Supabase client out of the static
  // analyzer's reach for the build-time placeholder pass; the import only
  // resolves under `next dev` where this branch is hit.
  const { fetchIgPost } = await import("../../../lib/supabase-server");
  const row = await fetchIgPost(postId);
  if (!row) notFound();

  const slides = Array.isArray(row.slide_specs) ? row.slide_specs : [];
  if (!slides.length) notFound();

  return <IgSlideClient slides={slides} pillar={row.pillar} />;
}
