import { notFound } from "next/navigation";
import type { SlideSpec, IgPostRow } from "../../../lib/supabase-server";
import { ReceiptTemplate } from "../templates/Receipt";
import { MethodTemplate } from "../templates/Method";
import { HistoryTemplate } from "../templates/History";
import { BriefTemplate } from "../templates/Brief";
import { HeatmapTemplate } from "../templates/Heatmap";

/* ---------------------------------------------------------------------------
   /ig/render/[postId] — 1080×1350 canvas rendered for Playwright.

   Reads the ig_posts row, picks the slide N from `slide_specs` via the
   `?slide=N` query (default 0), routes to the per-pillar template.

   This route is intentionally NOT included in the static export
   (generateStaticParams returns []). Post IDs are generated at runtime and
   cannot be known at build time. Playwright runs against `npm run dev`
   during the capture step, which still serves dynamic routes in dev mode.
   The production CF Pages build emits no /ig/render/[postId] pages.
   --------------------------------------------------------------------------- */

// Next.js 16 + output:"export" rejects (a) empty generateStaticParams as
// "missing" and (b) `searchParams` in any statically-exported page.
// We ship a single placeholder static page at build time and read the
// slide index client-side via URLSearchParams. The real Playwright capture
// flow runs against `npm run dev` (dynamic routes from Supabase per request)
// — the placeholder is never visited in production.
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
  // `npm run dev` overrides per-request with real data because dev mode
  // ignores dynamicParams=false.
  if (postId === "placeholder") {
    return <div className="ig-canvas" data-placeholder="true" />;
  }

  // Dynamic import keeps the server-only Supabase client out of the static
  // analyzer's reach for the build-time placeholder pass; the import only
  // resolves under `npm run dev` where this branch is hit.
  const { fetchIgPost } = await import("../../../lib/supabase-server");
  const row = await fetchIgPost(postId);
  if (!row) notFound();

  const slides = Array.isArray(row.slide_specs) ? row.slide_specs : [];
  // Slide index moved to client-side URLSearchParams (?slide=N) — see
  // <IgSlideClient> below — because Next 16 forbids `searchParams` in
  // statically-exported pages.
  const spec = slides[0];
  if (!spec) notFound();

  return (
    <IgSlideClient slides={slides} pillar={row.pillar} row={row} />
  );
}

// Placed inline so the page file remains the single import surface.
// The wrapper reads `?slide=N` from window.location and renders the right
// slide via the shared renderSlide() helper.
function IgSlideClient(props: {
  slides: SlideSpec[];
  pillar: IgPostRow["pillar"];
  row: IgPostRow;
}) {
  if (typeof window === "undefined") {
    // SSR pass at dev-time: render slide 0; client effect will swap.
    const spec = props.slides[0];
    if (!spec) return null;
    return (
      <div
        className="ig-canvas"
        data-pillar={props.pillar}
        data-variant={spec.kind === "brief" ? spec.variant : undefined}
        data-slide-index={0}
        data-slide-count={props.slides.length}
      >
        {renderSlide(spec, props.row, 0, props.slides.length)}
      </div>
    );
  }
  const sp = new URLSearchParams(window.location.search);
  const slideIndex = Math.max(0, parseInt(sp.get("slide") ?? "0", 10) || 0);
  const spec = props.slides[slideIndex];
  if (!spec) return null;
  return (
    <div
      className="ig-canvas"
      data-pillar={props.pillar}
      data-variant={spec.kind === "brief" ? spec.variant : undefined}
      data-slide-index={slideIndex}
      data-slide-count={props.slides.length}
    >
      {renderSlide(spec, props.row, slideIndex, props.slides.length)}
    </div>
  );
}

function renderSlide(
  spec: SlideSpec,
  row: IgPostRow,
  index: number,
  count: number,
) {
  switch (spec.kind) {
    case "receipt":
      return <ReceiptTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "method":
      return <MethodTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "history":
      return <HistoryTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "brief":
      return <BriefTemplate spec={spec} slideIndex={index} slideCount={count} pillar={row.pillar} />;
    case "heatmap":
      return <HeatmapTemplate spec={spec} slideIndex={index} slideCount={count} />;
    default: {
      const _exhaustive: never = spec;
      void _exhaustive;
      return null;
    }
  }
}
