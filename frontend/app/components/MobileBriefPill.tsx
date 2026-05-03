"use client";

import { useState } from "react";
import type { DailyBriefState } from "./DailyBrief";
import type { EpisodeMeta } from "./AudioProvider";
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

function formatMobileEpTime(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - d.getTime()) / (1000 * 60 * 60 * 24));
  const time = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
  if (diffDays === 0) return time;
  if (diffDays === 1) return `Yesterday ${time}`;
  return d.toLocaleDateString("en-US", { weekday: "short" }) + " " + time;
}

export default function MobileBriefPill({ state, className }: { state: DailyBriefState; className?: string }) {
  const {
    brief, isPlaying, handlePlayPause,
    isPlayerVisible, setPlayerVisible,
    previousEpisodes, loadEpisode,
  } = state;

  // Phase 2 redesign: Always expanded on mobile (no collapsed pill state)
  const [isExpanded, setIsExpanded] = useState(true);
  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);
  const [episodesExpanded, setEpisodesExpanded] = useState(false);

  if (!brief) return (
    <div className={`mbp${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
      <button
        className="mbp__pill"
        type="button"
        aria-expanded={false}
        disabled
      >
        <span className="mbp__pill-cmd">void --tl;dr</span>
        <span className="mbp__pill-sep" aria-hidden="true">/</span>
        <span className="mbp__pill-label mbp__pill-label--loading">Loading&hellip;</span>
      </button>
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

  const pillHeadline = brief.tldr_headline || tldrSentences[0] || "Daily Brief";

  /* Collapsed pill — tap to expand */
  if (!isExpanded) {
    return (
      <div className={`mbp${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
        <button
          className="mbp__pill"
          type="button"
          onClick={() => { hapticLight(); setIsExpanded(true); }}
          aria-expanded={false}
          aria-label="Expand daily brief"
        >
          <span className="mbp__pill-cmd">void --tl;dr</span>
          <span className="mbp__pill-sep" aria-hidden="true">/</span>
          <span className="mbp__pill-label">{pillHeadline}</span>
          <span className="mbp__pill-chevron" aria-hidden="true">&#9662;</span>
        </button>
      </div>
    );
  }

  return (
    <div className={`mbp mbp--skybox${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
      {/* Header row: branding + OnAir button */}
      <div className="mbp__header">
        <LogoIcon size={14} animation="idle" />
        <span className="mbp__cmd">void --tl;dr</span>
        {brief.created_at && <span className="mbp__time">{timeAgo(brief.created_at)}</span>}
        <div className="mbp__header-actions">
          <button
            className="mbp__pill-chevron-btn"
            type="button"
            onClick={() => { hapticLight(); setIsExpanded(false); }}
            aria-label="Collapse daily brief"
          >
            <span className="mbp__pill-chevron mbp__pill--open" aria-hidden="true">&#9662;</span>
          </button>
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

      {/* Previous episodes — starts collapsed; tap "Episodes" to reveal.
           Progressive disclosure: OnAir content hidden by default to reduce
           initial cognitive load. Users tap to explore past broadcasts. */}
      {previousEpisodes.length > 1 && (
        <>
          <hr className="mbp__rule" />
          <button
            className="mbp__prev-toggle"
            onClick={() => { hapticLight(); setEpisodesExpanded(v => !v); }}
            type="button"
            aria-expanded={episodesExpanded}
            aria-label={episodesExpanded ? "Hide episodes" : "Show episodes"}
          >
            <span className="mbp__prev-label">Episodes ({previousEpisodes.length - 1})</span>
            <span className={`mbp__prev-arrow${episodesExpanded ? " mbp__prev-arrow--open" : ""}`}>&#9656;</span>
          </button>
          <div className={`mbp__expand${episodesExpanded ? " mbp__expand--open" : ""}`}>
            <div className="mbp__expand-inner">
              <div className="mbp__episodes">
                {previousEpisodes.filter(ep => ep.audio_url).map((ep) => {
                  const isCurrent = brief?.audio_url === ep.audio_url;
                  const dur = ep.audio_duration_seconds ? Math.ceil(ep.audio_duration_seconds / 60) : null;
                  return (
                    <button
                      key={ep.id}
                      className={`mbp__ep${isCurrent ? " mbp__ep--current" : ""}`}
                      onClick={() => { if (!isCurrent) { hapticConfirm(); loadEpisode(ep); } }}
                      type="button"
                      disabled={isCurrent}
                    >
                      <span className="mbp__ep-time">{formatMobileEpTime(ep.created_at)}</span>
                      <span className="mbp__ep-hl">{ep.tldr_headline || "Daily Brief"}</span>
                      {dur && <span className="mbp__ep-dur">{dur}m</span>}
                      {isCurrent && <span className="mbp__ep-badge">Now</span>}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
