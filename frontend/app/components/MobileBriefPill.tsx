"use client";

import { useState } from "react";
import type { DailyBriefState } from "./DailyBrief";
import type { EpisodeMeta } from "./AudioProvider";
import { ScaleIcon } from "./ScaleIcon";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";
import { AUDIO_ENABLED } from "../lib/audioGate";

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

  // CEO 2026-05-13: mobile brief starts collapsed so TL;DR pill + Opinion
  // pill + Top Story all fit above the fold on any mobile resolution.
  // Tap the chevron (or any pill row) to expand.
  const [isExpanded, setIsExpanded] = useState(false);
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
  // UAT 2026-05-13 P1-11: show 3 sentences instead of 2 so the TL;DR
  // delivers a full thought before the "read more" hand-off.
  const tldrPreview = tldrSentences.slice(0, 3).join(" ");
  const tldrRest = tldrSentences.slice(3).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const handleOnairClick = () => {
    hapticConfirm();
    setPlayerVisible(true);
    if (!isPlaying) handlePlayPause();
  };

  const pillHeadline = brief.tldr_headline || tldrSentences[0] || "Daily Brief";
  const opinionHeadline = brief.opinion_headline || (brief.opinion_text || "").split(/(?<=[.!?])\s+/)[0] || null;
  const hasOpinion = !!(brief.opinion_text && opinionHeadline);
  // First sentence of the opinion body becomes the collapsed teaser. If the
  // opinion_headline IS the first sentence, fall back to the second to avoid
  // duplicating the headline.
  const opinionSentences = String(brief.opinion_text || "").split(/(?<=[.!?])\s+/).filter(Boolean);
  const firstOpinionSentence = opinionSentences[0] || "";
  const opinionTeaser = firstOpinionSentence && firstOpinionSentence !== opinionHeadline
    ? firstOpinionSentence
    : (opinionSentences[1] || "");
  // Mirror TL;DR: 2-sentence preview + "Read more" reveals the rest.
  const opinionPreviewText = opinionSentences.slice(0, 2).join(" ");
  const opinionRestText = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRestText.length > 0;

  /* Collapsed pill — TL;DR teaser (headline + preview) + Opinion teaser.
     CEO 2026-05-14: filter buried inside topics dropdown, freeing room for
     a richer brief teaser. Tap anywhere to expand into full skybox brief. */
  if (!isExpanded) {
    return (
      <div className={`mbp mbp--teaser${className ? ` ${className}` : ""}`} role="complementary" aria-label="Daily Brief">
        <button
          className="mbp__teaser"
          type="button"
          onClick={() => { hapticLight(); setIsExpanded(true); }}
          aria-expanded={false}
          aria-label="Expand daily brief"
        >
          <div className="mbp__teaser-tldr">
            <span className="mbp__teaser-cmd">void --tl;dr</span>
            <span className="mbp__teaser-hl">{pillHeadline}</span>
            <span className="mbp__teaser-preview">{tldrPreview}</span>
          </div>

          {hasOpinion && (
            <div className={`mbp__teaser-opinion${brief.opinion_lean ? ` mbp__teaser-opinion--${brief.opinion_lean}` : ""}`}>
              <span className="mbp__teaser-cmd mbp__teaser-cmd--opinion">void --opinion</span>
              <span className="mbp__teaser-hl mbp__teaser-hl--opinion">{opinionHeadline}</span>
              {opinionTeaser && <span className="mbp__teaser-preview mbp__teaser-preview--opinion">{opinionTeaser}</span>}
            </div>
          )}

          <span className="mbp__teaser-chevron" aria-hidden="true">&#9662;</span>
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
          {AUDIO_ENABLED && hasAudio && (
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

      {/* Opinion — re-introduced for mobile expanded brief (CEO 2026-05-13).
          User can collapse the whole brief; in expanded state TL;DR + Opinion
          both appear so the editorial moment is one tap away. /opinion route
          still exists for the deeper read. */}
      {hasOpinion && (
        <>
          <hr className="mbp__rule" />
          <div className={`mbp__opinion${brief.opinion_lean ? ` mbp__opinion--${brief.opinion_lean}` : ""}`}>
            <span className="mbp__cmd mbp__cmd--opinion">void --opinion</span>
            {opinionHeadline && <h3 className="mbp__hl mbp__hl--opinion">{opinionHeadline}</h3>}
            <p className="mbp__preview mbp__preview--opinion">{opinionPreviewText}</p>
            <div className={`mbp__expand${opinionExpanded ? " mbp__expand--open" : ""}`}>
              <div className="mbp__expand-inner">
                <p className="mbp__expand-text mbp__expand-text--opinion">{opinionRestText}</p>
              </div>
            </div>
            {opinionHasMore && (
              <button className="mbp__more" onClick={() => { hapticLight(); setOpinionExpanded((v) => !v); }}
                type="button" aria-expanded={opinionExpanded}>{opinionExpanded ? "Less" : "Read more"}</button>
            )}
          </div>
        </>
      )}

      {/* Previous episodes — starts collapsed; tap "Episodes" to reveal.
           Progressive disclosure: OnAir content hidden by default to reduce
           initial cognitive load. Users tap to explore past broadcasts. */}
      {AUDIO_ENABLED && previousEpisodes.length > 1 && (
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
