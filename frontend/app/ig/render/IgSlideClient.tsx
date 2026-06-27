"use client";

import { useEffect, useState } from "react";
import type { SlideSpec, IgPillar } from "../../lib/supabase-server";
import { ReceiptTemplate } from "./templates/Receipt";
import { MethodTemplate } from "./templates/Method";
import { HistoryTemplate } from "./templates/History";
import { BriefTemplate } from "./templates/Brief";
import { HeatmapTemplate } from "./templates/Heatmap";

/* ---------------------------------------------------------------------------
   Client-side slide selector for the IG render route.

   This MUST be a real client component ("use client"): the Playwright capture
   requests one URL per slide (?slide=N), and the slide index is read from the
   URL at runtime. When this logic lived inline in the server component it only
   ever ran the server branch (window undefined) and rendered slide 0 for every
   request, so multi-slide carousels (e.g. history's 5 slides) captured slide 0
   five times. Reading ?slide in a useEffect after hydration fixes that — the
   capture waits for networkidle + fonts + 250ms, by which point the correct
   slide has rendered.
   --------------------------------------------------------------------------- */

function renderSlide(
  spec: SlideSpec,
  pillar: IgPillar,
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
      return <BriefTemplate spec={spec} slideIndex={index} slideCount={count} pillar={pillar} />;
    case "heatmap":
      return <HeatmapTemplate spec={spec} slideIndex={index} slideCount={count} />;
    default: {
      const _exhaustive: never = spec;
      void _exhaustive;
      return null;
    }
  }
}

export function IgSlideClient({
  slides,
  pillar,
}: {
  slides: SlideSpec[];
  pillar: IgPillar;
}) {
  // SSR + first paint render slide 0; the effect swaps to ?slide=N after mount.
  const [slideIndex, setSlideIndex] = useState(0);
  useEffect(() => {
    const raw = new URLSearchParams(window.location.search).get("slide");
    const n = parseInt(raw ?? "0", 10);
    setSlideIndex(Number.isFinite(n) && n > 0 && n < slides.length ? n : 0);
  }, [slides.length]);

  const spec = slides[slideIndex];
  if (!spec) return null;

  return (
    <div
      className="ig-canvas"
      data-pillar={pillar}
      data-variant={spec.kind === "brief" ? spec.variant : undefined}
      data-slide-index={slideIndex}
      data-slide-count={slides.length}
    >
      {renderSlide(spec, pillar, slideIndex, slides.length)}
    </div>
  );
}
