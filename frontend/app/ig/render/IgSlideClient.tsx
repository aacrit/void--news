"use client";

import { useEffect, useState } from "react";
import type { SlideSpec, IgPillar } from "../../lib/supabase-server";
import { VisionTemplate } from "./templates/Vision";
import { MethodTemplate } from "./templates/Method";
import { ExampleTemplate } from "./templates/Example";
import { HistoryTemplate } from "./templates/History";
import { WeeklyTemplate } from "./templates/Weekly";

/* ---------------------------------------------------------------------------
   Client-side slide selector for the IG render route.

   This MUST be a real client component ("use client"): the Playwright capture
   requests one URL per slide (?slide=N), and the slide index is read from the
   URL at runtime. When this logic lived inline in the server component it only
   ever ran the server branch (window undefined) and rendered slide 0 for every
   request. Reading ?slide in a useEffect after hydration fixes that — the
   capture waits for networkidle + fonts + 250ms, by which point the correct
   slide has rendered.

   Three pillars, each a 3-slide carousel (hook -> substance -> cta):
     vision  -> VisionTemplate    (Void News, terracotta)
     method  -> MethodTemplate    (Void News, terracotta)
     example -> ExampleTemplate   (Void News, terracotta)
     history -> HistoryTemplate   (Void History, umber)
     weekly  -> WeeklyTemplate    (Void Weekly, red)
   --------------------------------------------------------------------------- */

function renderSlide(spec: SlideSpec, index: number, count: number) {
  switch (spec.kind) {
    case "vision":
      return <VisionTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "method":
      return <MethodTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "example":
      return <ExampleTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "history":
      return <HistoryTemplate spec={spec} slideIndex={index} slideCount={count} />;
    case "weekly":
      return <WeeklyTemplate spec={spec} slideIndex={index} slideCount={count} />;
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
      data-variant={spec.variant}
      data-slide-index={slideIndex}
      data-slide-count={slides.length}
    >
      {renderSlide(spec, slideIndex, slides.length)}
    </div>
  );
}
