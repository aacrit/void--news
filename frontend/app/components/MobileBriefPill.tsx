"use client";

import { useState } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

const PlayIcon = () => (
  <svg width="11" height="13" viewBox="0 0 11 13" fill="currentColor" aria-hidden="true">
    <path d="M1 1.5v10l9-5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="2.5" height="10" rx="0.5" />
    <rect x="6.5" y="1" width="2.5" height="10" rx="0.5" />
  </svg>
);

/* ---------------------------------------------------------------------------
   MobileBriefPill — Mobile skybox brief

   Promoted to skybox position (above hero). Shows TL;DR preview visible
   by default — no collapsed pill. Tap "Read more" to expand full text.
   OnAir play button integrated directly.
   --------------------------------------------------------------------------- */

export default function MobileBriefPill({ state, className }: { state: DailyBriefState; className?: string }) {
  const {
    brief, isPlaying, handlePlayPause,
    isPlayerVisible, setPlayerVisible,
  } = state;

  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);

  if (!brief) return (
    <div className={`mbp mbp--skybox${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
      <div className="mbp__header">
        <ScaleIcon size={16} animation="analyzing" />
        <span className="mbp__cmd">void --tl;dr</span>
        <span className="mbp__pill-label mbp__pill-label--loading">Loading&hellip;</span>
      </div>
    </div>
  );

  const hasAudio = !!brief.audio_url;

  const tldrSentences = String(brief.tldr_text).split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");
  const tldrRest = tldrSentences.slice(2).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const opinionSentences = brief.opinion_text ? String(brief.opinion_text).split(/(?<=[.!?])\s+/).filter(Boolean) : [];
  const opinionPreview = opinionSentences.slice(0, 2).join(" ");
  const opinionRest = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRest.length > 0;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const handleOnairClick = () => {
    hapticConfirm();
    setPlayerVisible(true);
    if (!isPlaying) handlePlayPause();
  };

  return (
    <div className={`mbp mbp--skybox${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
      {/* Header row: branding + OnAir button */}
      <div className="mbp__header">
        <LogoIcon size={14} animation="idle" />
        <span className="mbp__cmd">void --tl;dr</span>
        {brief.created_at && <span className="mbp__time">{timeAgo(brief.created_at)}</span>}
        <div className="mbp__header-actions">
          {hasAudio && (
            <button
              className={`mbp__play${isPlaying ? " mbp__play--active" : ""}`}
              onClick={handleOnairClick}
              type="button"
              aria-label={isPlaying ? "Now playing" : "Play broadcast"}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
              <span className="mbp__play-label">{isPlaying ? "Playing" : "Listen"}</span>
            </button>
          )}
        </div>
      </div>

      {/* TL;DR — first 2 sentences always visible */}
      {brief.tldr_headline && <h3 className="mbp__hl mbp__hl--tldr">{brief.tldr_headline}</h3>}
      <p className="mbp__preview mbp__preview--tldr">{tldrPreview}</p>
      <div className={`mbp__expand${tldrExpanded ? " mbp__expand--open" : ""}`}>
        <div className="mbp__expand-inner">
          <p className="mbp__expand-text mbp__expand-text--tldr">{tldrRest}</p>
        </div>
      </div>
      {tldrHasMore && (
        <button className="mbp__more" onClick={() => { hapticLight(); setTldrExpanded((v) => !v); }}
          type="button" aria-expanded={tldrExpanded}>{tldrExpanded ? "Less" : "Read more"}</button>
      )}

      {/* Opinion — behind dotted firewall */}
      {brief.opinion_text && <hr className="mbp__rule" />}

      {brief.opinion_text && (
        <section className="mbp__section" aria-label="void --opinion">
          <div className="mbp__label">
            <LogoIcon size={14} animation="idle" />
            <span className="mbp__label-human">Editorial</span>
            <span className="mbp__cmd">void --opinion</span>
            {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
          </div>
          {brief.opinion_headline && <h3 className="mbp__hl mbp__hl--opinion">{brief.opinion_headline}</h3>}
          <p className="mbp__preview mbp__preview--opinion">{opinionPreview}</p>
          <div className={`mbp__expand${opinionExpanded ? " mbp__expand--open" : ""}`}>
            <div className="mbp__expand-inner">
              <p className="mbp__expand-text mbp__expand-text--opinion">{opinionRest}</p>
            </div>
          </div>
          {opinionHasMore && (
            <button className="mbp__more" onClick={() => { hapticLight(); setOpinionExpanded((v) => !v); }}
              type="button" aria-expanded={opinionExpanded}>{opinionExpanded ? "Less" : "Read more"}</button>
          )}
        </section>
      )}
    </div>
  );
}
