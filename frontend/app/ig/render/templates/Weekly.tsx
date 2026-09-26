import type { WeeklySlideSpec } from "../../../lib/supabase-server";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   WEEKLY — the Void Weekly carousel (adhoc track). Red magazine identity.

   hook    (dark ink)   "Void Weekly · Issue #N" + the cover headline / deck
   stories (weekly paper) the week's key / most-contested stories
   cta     (dark ink)   "Read the edition." + URL

   Accent: --ig-red. Same Sigil-O; the stamp reads "VOID WEEKLY".
   --------------------------------------------------------------------------- */

interface Props {
  spec: WeeklySlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function WeeklyTemplate({ spec }: Props) {
  if (spec.variant === "stories") return <Stories spec={spec} />;
  if (spec.variant === "cta") return <Cta spec={spec} />;
  return <Hook spec={spec} />;
}

function issueLabel(n?: number): string {
  return n ? `Issue #${n}` : "This week";
}

function Hook({ spec }: { spec: WeeklySlideSpec }) {
  return (
    <div className="ig-weekly ig-weekly--hook">
      <p className="ig-kicker ig-kicker--red">Void Weekly · {issueLabel(spec.issue_number)}</p>
      <h1 className="ig-weekly__cover">{spec.headline}</h1>
      {spec.deck && <p className="ig-weekly__deck">{spec.deck}</p>}
      <LogoMark position="bl" tone="onDark" accent="red" word="WEEKLY" />
    </div>
  );
}

function Stories({ spec }: { spec: WeeklySlideSpec }) {
  const rows = spec.stories ?? [];
  return (
    <div className="ig-weekly ig-weekly--stories">
      <p className="ig-kicker ig-kicker--red-ink">The week in full</p>
      <ol className="ig-weekly__list">
        {rows.map((s, i) => (
          <li className="ig-weekly__item" key={`${s.headline}-${i}`}>
            <span className="ig-weekly__num">{String(i + 1).padStart(2, "0")}</span>
            <div className="ig-weekly__item-body">
              <p className="ig-weekly__item-headline">{s.headline}</p>
              {s.tag && <p className="ig-weekly__item-tag">{s.tag}</p>}
            </div>
          </li>
        ))}
      </ol>
      <LogoMark position="br" tone="onLight" accent="red" word="WEEKLY" />
    </div>
  );
}

function Cta({ spec }: { spec: WeeklySlideSpec }) {
  return (
    <div className="ig-weekly ig-weekly--cta">
      <HeroSigil size={180} accent="red" />
      <h2 className="ig-cta__line">{spec.headline ?? "Read the edition."}</h2>
      <p className="ig-url ig-url--red">{spec.url ?? "news.voidvision.org"}</p>
      <LogoMark position="bl" tone="onDark" accent="red" word="WEEKLY" />
    </div>
  );
}
