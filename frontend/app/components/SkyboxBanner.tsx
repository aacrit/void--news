"use client";

import { useState } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

/* ---------------------------------------------------------------------------
   SkyboxBanner — Two-column brief (TL;DR | Opinion)

   Audio player is handled exclusively by AudioPlayer bottom bar.
   No audio controls or OnAir CTAs here.
   --------------------------------------------------------------------------- */

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief } = state;
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);

  if (!brief) return (
    <div className="skb" role="complementary" aria-label="Daily Brief">
      <div className="skb__columns">
        <div className="skb__col skb__col--tldr">
          <div className="skb__label">
            <ScaleIcon size={12} animation="analyzing" />
            <span className="skb__cmd">void --tl;dr</span>
          </div>
          <p className="skb__preview skb__preview--tldr" style={{ opacity: 0.4 }}>Loading today&rsquo;s brief&hellip;</p>
        </div>
      </div>
    </div>
  );

  const tldrFull = brief.tldr_text;
  const tldrSentences = tldrFull.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrHasMore = tldrSentences.length > 2;

  const opinionFull = brief.opinion_text || "";
  const opinionSentences = opinionFull.split(/(?<=[.!?])\s+/).filter(Boolean);
  const opinionHasMore = opinionSentences.length > 2;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const toggleSide = (side: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSide((prev) => prev === side ? null : side);
  };

  return (
    <div className={`skb${expandedSide ? ` skb--expand-${expandedSide}` : ""}`} role="complementary" aria-label="Daily Brief">
      <div className="skb__columns">
        {expandedSide !== "opinion" && (
          <div className={`skb__col skb__col--tldr${expandedSide === "tldr" ? " skb__col--full" : ""}`}>
            <div className="skb__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="skb__cmd">void --tl;dr</span>
              {brief.created_at && <span className="skb__time">{timeAgo(brief.created_at)}</span>}
            </div>
            {brief.tldr_headline && <h3 className="skb__hl skb__hl--tldr">{brief.tldr_headline}</h3>}
            {expandedSide === "tldr" ? (
              <div className="skb__expand-text--tldr">
                {tldrFull.split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
              </div>
            ) : (
              <p className="skb__preview skb__preview--tldr">{tldrFull}</p>
            )}
            {tldrHasMore && (
              <button className="skb__more" onClick={() => toggleSide("tldr")} type="button"
                aria-expanded={expandedSide === "tldr"}>{expandedSide === "tldr" ? "less" : "read more"}</button>
            )}
          </div>
        )}

        {brief.opinion_text && expandedSide !== "tldr" && (
          <div className={`skb__col skb__col--opinion${expandedSide === "opinion" ? " skb__col--full" : ""}`}>
            <div className="skb__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="skb__cmd">void --opinion</span>
              {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
            </div>
            {brief.opinion_headline && <h3 className="skb__hl skb__hl--opinion">{brief.opinion_headline}</h3>}
            {expandedSide === "opinion" ? (
              <div className="skb__expand-text--opinion">
                {opinionFull.split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
              </div>
            ) : (
              <p className="skb__preview skb__preview--opinion">{opinionFull}</p>
            )}
            {opinionHasMore && (
              <button className="skb__more" onClick={() => toggleSide("opinion")} type="button"
                aria-expanded={expandedSide === "opinion"}>{expandedSide === "opinion" ? "less" : "read more"}</button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
