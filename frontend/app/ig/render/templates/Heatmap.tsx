import type { HeatmapSlideSpec } from "../../../lib/supabase-server";
import { LogoMark } from "./LogoMark";

/* ---------------------------------------------------------------------------
   Heatmap template — sorted-bar visualization of country-level lean on a
   single topic. Renders ≤10 rows (top countries by source count).
   --------------------------------------------------------------------------- */

const LEAN_COLORS = [
  { max: 25, color: "#0E2E70" },
  { max: 42, color: "#1B5298" },
  { max: 58, color: "#2B784A" },
  { max: 75, color: "#9C2C22" },
  { max: 100, color: "#6E1610" },
];

function leanColor(s: number): string {
  for (const b of LEAN_COLORS) if (s <= b.max) return b.color;
  return LEAN_COLORS[2].color;
}

interface Props {
  spec: HeatmapSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function HeatmapTemplate({ spec }: Props) {
  const rows = [...spec.countries].sort((a, b) => b.source_count - a.source_count).slice(0, 10);
  const maxCount = Math.max(...rows.map((r) => r.source_count));
  return (
    <>
      <LogoMark position="tl" />
      <div className="heatmap">
        <h1 className="heatmap__title">{spec.topic}</h1>
        <div className="heatmap__bars">
          {rows.map((r) => (
            <div className="heatmap__bar-row" key={r.code}>
              <span className="heatmap__bar-country">{r.code}</span>
              <div className="heatmap__bar-track">
                <div
                  className="heatmap__bar-fill"
                  style={{
                    width: `${Math.round((r.source_count / maxCount) * 100)}%`,
                    color: leanColor(r.lean),
                  }}
                />
              </div>
              <span className="heatmap__bar-count">{r.source_count}</span>
            </div>
          ))}
        </div>
        <p className="heatmap__footer">
          void --news · 1,016 sources · 158 countries · per-article bias
        </p>
      </div>
    </>
  );
}
