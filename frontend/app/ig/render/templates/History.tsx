import type { HistorySlideSpec } from "../../../lib/supabase-server";
import { LogoMark } from "./LogoMark";

/* ---------------------------------------------------------------------------
   History template — burnt-umber archival aesthetic.
   First slide leads with a fact. Subsequent slides carry one perspective each.
   No assertions of significance. Show, don't tell.
   --------------------------------------------------------------------------- */

interface Props {
  spec: HistorySlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function HistoryTemplate({ spec, slideIndex, slideCount }: Props) {
  const isLast = slideIndex === slideCount - 1;
  return (
    <>
      <LogoMark position="br" />
      <div className="history">
        <p className="history__dateline">{spec.date}</p>
        {spec.lead_fact && <p className="history__lead-fact">{spec.lead_fact}</p>}
        {spec.perspective && (
          <>
            <p className="history__perspective-lens">{spec.perspective.lens}</p>
            <p className="history__voice">{spec.perspective.voice}</p>
          </>
        )}
        {isLast && (
          <p className="history__cta">
            void --history · multiple perspectives, no winner declared
          </p>
        )}
      </div>
    </>
  );
}
