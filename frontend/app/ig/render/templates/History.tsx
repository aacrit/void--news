import type { HistorySlideSpec } from "../../../lib/supabase-server";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   HISTORY — the Void History carousel (adhoc track). Archival umber identity.

   hook         (dark ink)   dateline + the event title
   perspectives (archival)   the multiple accounts, no winner declared
   cta          (dark ink)   "Read the full record." + URL

   Accent: --ig-umber. Same Sigil-O; the stamp reads "VOID HISTORY".
   --------------------------------------------------------------------------- */

interface Props {
  spec: HistorySlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function HistoryTemplate({ spec }: Props) {
  if (spec.variant === "perspectives") return <Perspectives spec={spec} />;
  if (spec.variant === "cta") return <Cta spec={spec} />;
  return <Hook spec={spec} />;
}

function Hook({ spec }: { spec: HistorySlideSpec }) {
  return (
    <div className="ig-history ig-history--hook">
      {spec.date && <p className="ig-history__dateline">{spec.date}</p>}
      <h1 className="ig-history__title">{spec.headline}</h1>
      <LogoMark position="bl" tone="onDark" accent="umber" word="HISTORY" />
    </div>
  );
}

function Perspectives({ spec }: { spec: HistorySlideSpec }) {
  const rows = spec.perspectives ?? [];
  return (
    <div className="ig-history ig-history--perspectives">
      <p className="ig-kicker ig-kicker--umber">One event. Many accounts.</p>
      <div className="ig-history__voices">
        {rows.map((p, i) => (
          <div className="ig-history__voice" key={`${p.lens}-${i}`}>
            <p className="ig-history__lens">{p.lens}</p>
            <p className="ig-history__quote">{p.voice}</p>
          </div>
        ))}
      </div>
      <p className="ig-history__coda">No winner declared.</p>
      <LogoMark position="br" tone="onLight" accent="umber" word="HISTORY" />
    </div>
  );
}

function Cta({ spec }: { spec: HistorySlideSpec }) {
  return (
    <div className="ig-history ig-history--cta">
      <HeroSigil size={180} accent="umber" />
      <h2 className="ig-cta__line">{spec.headline ?? "Read the full record."}</h2>
      <p className="ig-url ig-url--umber">{spec.url ?? "news.voidvision.org"}</p>
      <LogoMark position="bl" tone="onDark" accent="umber" word="HISTORY" />
    </div>
  );
}
