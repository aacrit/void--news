import type { VisionSlideSpec } from "../../../lib/supabase-server";
import { LogoMark, HeroSigil } from "./LogoMark";

/* ---------------------------------------------------------------------------
   VISION — the evergreen manifesto carousel.

   hook   (dark ink)  a large Playfair provocation about the algorithmic feed
   stance (cream)     the core principle, set as an editorial column
   cta    (dark ink)  the Sigil-O hero mark + sign-off + URL
   --------------------------------------------------------------------------- */

interface Props {
  spec: VisionSlideSpec;
  slideIndex: number;
  slideCount: number;
}

export function VisionTemplate({ spec }: Props) {
  if (spec.variant === "stance") return <Stance spec={spec} />;
  if (spec.variant === "cta") return <Cta spec={spec} />;
  return <Hook spec={spec} />;
}

function Hook({ spec }: { spec: VisionSlideSpec }) {
  return (
    <div className="ig-vision ig-vision--hook">
      <span className="ig-vision__watermark" aria-hidden="true" />
      <p className="ig-kicker ig-kicker--terracotta">{spec.kicker ?? "The Void Manifesto"}</p>
      <h1 className="ig-vision__provocation">{spec.headline}</h1>
      <LogoMark position="bl" tone="onDark" />
    </div>
  );
}

function Stance({ spec }: { spec: VisionSlideSpec }) {
  return (
    <div className="ig-vision ig-vision--stance">
      <p className="ig-kicker ig-kicker--ink">{spec.kicker ?? "Our Stance"}</p>
      {spec.headline && <h2 className="ig-vision__lead">{spec.headline}</h2>}
      <hr className="ig-rule" />
      <p className="ig-vision__body">{spec.body}</p>
      <LogoMark position="br" tone="onLight" />
    </div>
  );
}

function Cta({ spec }: { spec: VisionSlideSpec }) {
  return (
    <div className="ig-vision ig-vision--cta">
      <HeroSigil size={280} accent="terracotta" word="NEWS" />
      <h2 className="ig-cta__line">{spec.headline ?? "See through the void."}</h2>
      <p className="ig-url">{spec.url ?? "void-news.pages.dev"}</p>
    </div>
  );
}
