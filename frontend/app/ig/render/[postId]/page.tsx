import { notFound } from "next/navigation";
import {
  fetchIgPost,
  type SlideSpec,
  type IgPostRow,
} from "../../../lib/supabase-server";
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

export function generateStaticParams() {
  return [];
}

// Required by Next.js 16 + output:"export" when generateStaticParams returns
// an empty list — tells the static exporter that no params are valid,
// otherwise the build rejects the route as missing static params.
export const dynamicParams = false;

interface PageProps {
  params: Promise<{ postId: string }>;
  searchParams: Promise<{ slide?: string }>;
}

export default async function IgRenderPage({ params, searchParams }: PageProps) {
  const { postId } = await params;
  const { slide } = await searchParams;

  const row = await fetchIgPost(postId);
  if (!row) notFound();

  const slideIndex = Math.max(0, parseInt(slide ?? "0", 10) || 0);
  const slides = Array.isArray(row.slide_specs) ? row.slide_specs : [];
  const spec = slides[slideIndex];
  if (!spec) notFound();

  return (
    <div
      className="ig-canvas"
      data-pillar={row.pillar}
      data-variant={spec.kind === "brief" ? spec.variant : undefined}
      data-slide-index={slideIndex}
      data-slide-count={slides.length}
    >
      {renderSlide(spec, row, slideIndex, slides.length)}
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
