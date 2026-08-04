import type { ExampleSlideSpec, OutletHeadline } from "../../../lib/supabase-server";
import {
  computeKDE,
  robustBandwidth,
  normalizeKDE,
  kdeToCubicPath,
  getYOnCurve,
} from "../../../lib/kde";
import { leanLabelAbbr } from "../../../lib/biasColors";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   EXAMPLE — the dynamic, real-top-story carousel (the proof).

   hook     (dark ink)  the event + "N outlets. One event. See where they land."
   spectrum (cream)     THE money slide: a STATIC render of the real product's
                        KDE ridge — the same ink-wash distribution + chromatic
                        stroke + mean plumb-line users see in the Deep Dive —
                        followed by the colour-keyed outlet breakdown.
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

/* Spectrum gradient stops — identical hues to the in-app DeepDiveSpectrum so the
   ridge reads as the same visualization. Referenced via --bias-* tokens. */
const RIDGE_STOPS: Array<{ offset: string; color: string }> = [
  { offset: "0%", color: "var(--bias-far-left)" },
  { offset: "16%", color: "var(--bias-left)" },
  { offset: "32%", color: "var(--bias-center-left)" },
  { offset: "50%", color: "var(--bias-center)" },
  { offset: "68%", color: "var(--bias-center-right)" },
  { offset: "84%", color: "var(--bias-right)" },
  { offset: "100%", color: "var(--bias-far-right)" },
];

/* Ridge geometry (viewBox units). The SVG scales to full slide width; height
   follows the viewBox ratio so no layout math is needed at render time. */
const RIDGE_W = 400;
const RIDGE_H = 110;
const RIDGE_PAD = 14; // baseline padding
const RIDGE_PEAK = 86; // curve peak height above baseline

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

/* ── Static KDE ridge ──────────────────────────────────────────────────────
   A screenshot-safe reduction of DeepDiveSpectrum's SpectrumView: it reuses the
   exact kde math (computeKDE / robustBandwidth / normalizeKDE / kdeToCubicPath /
   getYOnCurve) and the same ink-wash fill + chromatic-stroke + amber mean
   plumb-line, but renders the FINAL settled state directly — no localStorage,
   no useEffect / rAF entrance beats, no favicon fetches, no hover fan-out.
   Purely presentational, so it renders identically server-side or client-side. */
function SpectrumRidge({
  leanValues,
  outlets,
}: {
  leanValues: number[];
  outlets: OutletHeadline[];
}) {
  const leans = leanValues
    .filter((v) => typeof v === "number" && Number.isFinite(v))
    .map((v) => Math.max(0, Math.min(100, v)));

  if (leans.length === 0) return null;

  // Mirror the app: n<=7 uses a tight fixed bandwidth so small samples don't
  // smear into one hump; larger samples use the IQR-corrected robust rule.
  const bw = leans.length <= 7 ? 6 : robustBandwidth(leans);
  const densities = normalizeKDE(computeKDE(leans, bw, 100));
  const scaled = densities.map((d) => d * (RIDGE_PEAK / (RIDGE_H - RIDGE_PAD)));
  const { fillPath, strokePath } = kdeToCubicPath(scaled, RIDGE_H, RIDGE_W, RIDGE_PAD);

  const mean = leans.reduce((s, v) => s + v, 0) / leans.length;
  const meanX = (mean / 100) * RIDGE_W;

  const pins = outlets
    .filter((o) => typeof o.lean_score === "number" && Number.isFinite(o.lean_score))
    .map((o) => {
      const lean = Math.max(0, Math.min(100, o.lean_score));
      return {
        x: (lean / 100) * RIDGE_W,
        y: getYOnCurve(lean, scaled, RIDGE_H, RIDGE_PAD),
        color: leanColor(lean),
      };
    });

  return (
    <div className="ig-example__ridge">
      <svg
        className="ig-example__ridge-svg"
        viewBox={`0 0 ${RIDGE_W} ${RIDGE_H}`}
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="ig-ridge-fill" x1="0" y1="0" x2="1" y2="0">
            {RIDGE_STOPS.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.42" />
            ))}
          </linearGradient>
          <linearGradient id="ig-ridge-stroke" x1="0" y1="0" x2="1" y2="0">
            {RIDGE_STOPS.map((s) => (
              <stop key={`s-${s.offset}`} offset={s.offset} stopColor={s.color} stopOpacity="0.95" />
            ))}
          </linearGradient>
          {/* Ink-wash: the same feTurbulence displacement the app applies to the
              fill so the distribution reads hand-pressed, not vector-clean. */}
          <filter id="ig-ridge-wash" x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence
              type="turbulence"
              baseFrequency="0.012 0.025"
              numOctaves="1"
              seed="42"
              result="turb"
            />
            <feDisplacementMap in="SourceGraphic" in2="turb" scale="2.2" />
          </filter>
        </defs>

        {/* Ink-wash distribution fill */}
        <path d={fillPath} fill="url(#ig-ridge-fill)" filter="url(#ig-ridge-wash)" />

        {/* Chromatic ridge stroke — blue → green → red across the lean axis */}
        <path
          d={strokePath}
          fill="none"
          stroke="url(#ig-ridge-stroke)"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Amber mean plumb-line — the weighted-centre tilt indicator */}
        <line
          x1={meanX}
          y1={5}
          x2={meanX}
          y2={RIDGE_H - 4}
          stroke="var(--cin-amber)"
          strokeWidth="1.4"
          strokeDasharray="5 3"
        />

        {/* Shown outlets, plotted on the ridge at their exact lean, --bias-coloured */}
        {pins.map((p, i) => (
          <g key={`ridge-pin-${i}`}>
            <circle cx={p.x} cy={p.y} r="5.5" fill="var(--ig-cream)" />
            <circle cx={p.x} cy={p.y} r="5.5" fill="none" stroke={p.color} strokeWidth="2.6" />
          </g>
        ))}
      </svg>

      {/* Mean tilt caption — mirrors the app's TiltRow readout */}
      <div className="ig-example__ridge-tilt" aria-hidden="true">
        <span
          className="ig-example__ridge-tilt-needle"
          style={{ left: `${mean}%`, background: leanColor(mean) }}
        />
        <span
          className="ig-example__ridge-tilt-label"
          style={{ left: `clamp(40px, ${mean}%, calc(100% - 40px))` }}
        >
          {leanLabelAbbr(mean)} · {Math.round(mean)}
        </span>
      </div>
    </div>
  );
}

function Spectrum({ spec }: { spec: ExampleSlideSpec }) {
  const outlets: OutletHeadline[] = (spec.headlines ?? []).slice(0, 6);
  // Prefer the full per-article distribution; fall back to the shown outlets.
  const leanValues =
    spec.lean_values && spec.lean_values.length > 0
      ? spec.lean_values
      : outlets.map((o) => o.lean_score);

  return (
    <div className="ig-example ig-example--spectrum">
      <p className="ig-kicker ig-kicker--ink">{spec.topic ?? "The spread"}</p>
      <h2 className="ig-example__spectrum-title">One event. Where the coverage landed.</h2>

      <SpectrumRidge leanValues={leanValues} outlets={outlets} />

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
