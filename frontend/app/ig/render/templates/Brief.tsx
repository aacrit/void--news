import type { BriefSlideSpec, IgPillar } from "../../../lib/supabase-server";
import { LogoMark } from "./LogoMark";

/* ---------------------------------------------------------------------------
   Brief template — three variants:
     • manifesto — the launch opener and other big-type proclamations
     • pullquote — a standout sentence from a daily brief
     • bts — pipeline behind-the-scenes stats grid
   --------------------------------------------------------------------------- */

interface Props {
  spec: BriefSlideSpec;
  slideIndex: number;
  slideCount: number;
  pillar: IgPillar;
}

export function BriefTemplate({ spec, slideIndex, slideCount, pillar }: Props) {
  if (spec.variant === "manifesto") return <Manifesto spec={spec} />;
  if (spec.variant === "bts") return <Bts spec={spec} />;
  return <Pullquote spec={spec} slideIndex={slideIndex} slideCount={slideCount} pillar={pillar} />;
}

function Manifesto({ spec }: { spec: BriefSlideSpec }) {
  return (
    <>
      <LogoMark position="tl" tone="warm" />
      <div className="brief brief--manifesto">
        <h1 className="brief__manifesto-headline">{spec.content}</h1>
        {spec.attribution && <p className="brief__manifesto-sub">{spec.attribution}</p>}
      </div>
    </>
  );
}

function Pullquote({
  spec,
  slideIndex,
  slideCount,
  pillar,
}: {
  spec: BriefSlideSpec;
  slideIndex: number;
  slideCount: number;
  pillar: IgPillar;
}) {
  return (
    <>
      <LogoMark position="tl" tone={pillar === "brief" ? "ink" : "warm"} />
      <div className="brief">
        <p className="brief__variant">
          {slideIndex === 0 ? "from the daily brief" : `${slideIndex + 1} / ${slideCount}`}
        </p>
        <p className="brief__pullquote">{spec.content}</p>
        {spec.attribution && <p className="brief__attribution">{spec.attribution}</p>}
      </div>
    </>
  );
}

function Bts({ spec }: { spec: BriefSlideSpec }) {
  const stats = Object.entries(spec.stats ?? {});
  return (
    <>
      <LogoMark position="tl" tone="ink" />
      <div className="brief brief--bts">
        <p className="brief__variant">what the pipeline saw</p>
        <p className="brief__pullquote" style={{ fontSize: "48px" }}>
          {spec.content}
        </p>
        <div className="brief__bts-grid">
          {stats.map(([label, value]) => (
            <div key={label}>
              <p className="brief__bts-stat-label">{label}</p>
              <p className="brief__bts-stat-value">{String(value)}</p>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
