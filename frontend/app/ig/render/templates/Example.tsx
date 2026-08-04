import type { ExampleSlideSpec, OutletHeadline } from "../../../lib/supabase-server";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   EXAMPLE — the dynamic, real-top-story carousel (the proof).

   hook     (dark ink)  the event + "N outlets. One event. See where they land."
   spectrum (cream)     THE money slide: every outlet plotted on a left/center/
                        right lean axis, then a colour-keyed headline breakdown
   cta      (dark ink)  "The full breakdown is on the front page." + URL

   Lean colours come from the --bias-* tokens only (never terracotta).
   --------------------------------------------------------------------------- */

const LEAN_BANDS = [
  { max: 21, color: "var(--bias-far-left)" },
  { max: 40, color: "var(--bias-left)" },
  { max: 47, color: "var(--bias-center-left)" },
  { max: 53, color: "var(--bias-center)" },
  { max: 60, color: "var(--bias-center-right)" },
  { max: 79, color: "var(--bias-right)" },
  { max: 100, color: "var(--bias-far-right)" },
] as const;

function leanColor(score: number): string {
  for (const b of LEAN_BANDS) if (score <= b.max) return b.color;
  return "var(--bias-center)";
}

function clampPct(n: number): number {
  return Math.max(4, Math.min(96, n));
}

interface Props {
  spec: ExampleSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function ExampleTemplate({ spec }: Props) {
  if (spec.variant === "spectrum") return <Spectrum spec={spec} />;
  if (spec.variant === "cta") return <Cta spec={spec} />;
  return <Hook spec={spec} />;
}

function Hook({ spec }: { spec: ExampleSlideSpec }) {
  const n = spec.outlet_count ?? spec.headlines?.length ?? 0;
  return (
    <div className="ig-example ig-example--hook">
      <p className="ig-kicker ig-kicker--terracotta">{spec.topic ?? "Today's front page"}</p>
      <h1 className="ig-example__event">{spec.headline}</h1>
      <div className="ig-example__count">
        <span className="ig-example__count-n">{n}</span>
        <span className="ig-example__count-word">outlets. One event.</span>
        <span className="ig-example__count-sub">See where they land.</span>
      </div>
      <LogoMark position="bl" tone="onDark" />
    </div>
  );
}

function Spectrum({ spec }: { spec: ExampleSlideSpec }) {
  const outlets: OutletHeadline[] = (spec.headlines ?? []).slice(0, 6);
  return (
    <div className="ig-example ig-example--spectrum">
      <p className="ig-kicker ig-kicker--ink">{spec.topic ?? "The spread"}</p>
      <h2 className="ig-example__spectrum-title">One event. Where the coverage landed.</h2>

      <div className="ig-spectrum">
        <div className="ig-spectrum__track" aria-hidden="true" />
        {outlets.map((o, i) => {
          const color = leanColor(o.lean_score);
          return (
            <div
              className="ig-spectrum__pin"
              key={`${o.outlet}-${i}`}
              data-side={i % 2 === 0 ? "above" : "below"}
              style={{ left: `${clampPct(o.lean_score)}%` }}
            >
              <span className="ig-spectrum__flag" style={{ color }}>
                {o.outlet}
              </span>
              <span className="ig-spectrum__stem" style={{ background: color }} />
              <span className="ig-spectrum__dot" style={{ background: color, borderColor: color }} />
            </div>
          );
        })}
      </div>
      <div className="ig-spectrum__axis" aria-hidden="true">
        <span>Left</span>
        <span>Center</span>
        <span>Right</span>
      </div>

      <div className="ig-example__list">
        {outlets.map((o, i) => {
          const color = leanColor(o.lean_score);
          return (
            <div className="ig-example__item" key={`row-${o.outlet}-${i}`}>
              <span className="ig-example__item-dot" style={{ background: color }} />
              <div className="ig-example__item-head">
                <span className="ig-example__item-outlet">{o.outlet}</span>
                <span className="ig-example__item-score" style={{ color }}>
                  {o.lean_score}
                </span>
              </div>
              <p className="ig-example__item-quote">{o.headline}</p>
            </div>
          );
        })}
      </div>
      <LogoMark position="br" tone="onLight" />
    </div>
  );
}

function Cta({ spec }: { spec: ExampleSlideSpec }) {
  return (
    <div className="ig-example ig-example--cta">
      <HeroSigil size={180} accent="terracotta" />
      <h2 className="ig-cta__line">
        {spec.headline ?? "The full breakdown is on the front page."}
      </h2>
      <p className="ig-url">{spec.url ?? "void-news.pages.dev"}</p>
      <LogoMark position="bl" tone="onDark" />
    </div>
  );
}
