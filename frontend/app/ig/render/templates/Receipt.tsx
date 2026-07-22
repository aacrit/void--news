import type { ReceiptSlideSpec } from "../../../lib/supabase-server";
import { LogoMark } from "./LogoMark";

/* ---------------------------------------------------------------------------
   Receipt template — same event, multiple outlets, side-by-side scores.

   Voice rules (enforced by ig_caption.py for the caption, but baked in here
   for the on-image text): show, don't tell. Numbers do the work.

   Lean color picks one of 5 bands from --bias-* tokens defined in tokens.css.
   --------------------------------------------------------------------------- */

const LEAN_BANDS = [
  { max: 25, color: "var(--bias-far-left)" },
  { max: 42, color: "var(--bias-left)" },
  { max: 58, color: "var(--bias-center)" },
  { max: 75, color: "var(--bias-right)" },
  { max: 100, color: "var(--bias-far-right)" },
] as const;

function leanColor(score: number): string {
  for (const band of LEAN_BANDS) {
    if (score <= band.max) return band.color;
  }
  return "var(--bias-center)";
}

interface Props {
  spec: ReceiptSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function ReceiptTemplate({ spec, slideIndex, slideCount }: Props) {
  const showFooter = slideIndex === slideCount - 1;
  return (
    <>
      <LogoMark position="tl" />
      <div className="receipt">
        <p className="receipt__topic">{spec.topic}</p>
        <h1 className="receipt__headline">
          {spec.caption ?? `${spec.headlines.length} outlets. Same story.`}
        </h1>
        <div className="receipt__rows">
          {spec.headlines.map((h, i) => (
            <div className="receipt__row" key={`${h.outlet}-${i}`}>
              <div className="receipt__outlet">
                <span
                  className="receipt__lean-dot"
                  style={{ background: leanColor(h.lean_score) }}
                />
                <span>{h.outlet}</span>
              </div>
              <div className="receipt__quote">{h.headline}</div>
              <div className="receipt__score">{h.lean_score}</div>
            </div>
          ))}
        </div>
        {showFooter && (
          <p className="receipt__footer">
            void --news · per article, not per outlet
          </p>
        )}
      </div>
    </>
  );
}
