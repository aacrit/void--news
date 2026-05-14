import type { MethodSlideSpec } from "../../../lib/supabase-server";
import { LogoMark } from "./LogoMark";

/* ---------------------------------------------------------------------------
   Method template — single bias-axis explainer with a real sample sentence.
   Highlight ranges turn into <mark> spans (matches the about-page treatment).
   --------------------------------------------------------------------------- */

interface Props {
  spec: MethodSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function MethodTemplate({ spec, slideIndex, slideCount }: Props) {
  return (
    <>
      <LogoMark position="tl" />
      <div className="method">
        <p className="method__axis-num">
          axis {slideIndex + 1} / {slideCount}
        </p>
        <h1 className="method__name">{spec.axis_name}</h1>
        <p className="method__brief">{spec.brief}</p>
        {spec.sample && (
          <>
            <p className="method__sample-label">Sample</p>
            <p
              className="method__sample"
              dangerouslySetInnerHTML={{
                __html: highlightSample(spec.sample.text, spec.sample.highlights ?? []),
              }}
            />
          </>
        )}
        {spec.principle && <p className="method__principle">{spec.principle}</p>}
      </div>
    </>
  );
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
