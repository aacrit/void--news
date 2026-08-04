import type { MethodSlideSpec } from "../../../lib/supabase-server";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   METHOD — the evergreen "how bias scoring works" carousel.

   hook   (dark ink)  "Bias isn't the outlet. It's the words."
   sample (cream)     a real sentence, charged words highlighted in terracotta,
                      a lean chip on the --bias-* scale, axis name + principle
   cta    (dark ink)  "Rule based. Traceable. Every score shows its math." + URL
   --------------------------------------------------------------------------- */

/* Lean-band colour from the --bias-* tokens (never terracotta). Score 0..100. */
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

interface Props {
  spec: MethodSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function MethodTemplate({ spec }: Props) {
  if (spec.variant === "sample") return <Sample spec={spec} />;
  if (spec.variant === "cta") return <Cta spec={spec} />;
  return <Hook spec={spec} />;
}

function Hook({ spec }: { spec: MethodSlideSpec }) {
  return (
    <div className="ig-method ig-method--hook">
      <p className="ig-kicker ig-kicker--terracotta">{spec.kicker ?? "How we score bias"}</p>
      <h1 className="ig-method__headline">{spec.headline ?? "Bias isn't the outlet. It's the words."}</h1>
      <LogoMark position="bl" tone="onDark" />
    </div>
  );
}

function Sample({ spec }: { spec: MethodSlideSpec }) {
  const score = spec.score ?? 50;
  const color = leanColor(score);
  return (
    <div className="ig-method ig-method--sample">
      <p className="ig-kicker ig-kicker--ink">{spec.axis_name ?? "Political Lean"}</p>
      {spec.sample && (
        <p
          className="ig-method__sample"
          dangerouslySetInnerHTML={{
            __html: highlightSample(spec.sample.text, spec.sample.highlights ?? []),
          }}
        />
      )}
      <div className="ig-chip" role="img" aria-label={`Lean score ${score}`}>
        <div className="ig-chip__track">
          <span
            className="ig-chip__dot"
            style={{ left: `${clamp(score)}%`, background: color, borderColor: color }}
          />
        </div>
        <div className="ig-chip__meta">
          <span className="ig-chip__ends">Left</span>
          <span className="ig-chip__label" style={{ color }}>
            {spec.lean_label ?? "Center"} · {score}
          </span>
          <span className="ig-chip__ends">Right</span>
        </div>
      </div>
      {spec.principle && <p className="ig-method__principle">{spec.principle}</p>}
      <LogoMark position="br" tone="onLight" />
    </div>
  );
}

function Cta({ spec }: { spec: MethodSlideSpec }) {
  return (
    <div className="ig-method ig-method--cta">
      <HeroSigil size={180} accent="terracotta" />
      <h2 className="ig-cta__line">
        {spec.headline ?? "Rule based. Traceable. Every score shows its math."}
      </h2>
      <p className="ig-url">{spec.url ?? "void-news.pages.dev"}</p>
      <LogoMark position="bl" tone="onDark" />
    </div>
  );
}

function clamp(n: number): number {
  return Math.max(3, Math.min(97, n));
}

function highlightSample(
  text: string,
  highlights: Array<{ start: number; end: number }>,
): string {
  if (highlights.length === 0) return escapeHtml(text);
  const sorted = [...highlights].sort((a, b) => a.start - b.start);
  const parts: string[] = [];
  let cursor = 0;
  for (const h of sorted) {
    if (h.start > cursor) parts.push(escapeHtml(text.slice(cursor, h.start)));
    parts.push(`<mark>${escapeHtml(text.slice(h.start, h.end))}</mark>`);
    cursor = h.end;
  }
  if (cursor < text.length) parts.push(escapeHtml(text.slice(cursor)));
  return parts.join("");
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
