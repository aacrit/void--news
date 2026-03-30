"use client";

import { useState } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   SkyboxBanner — Two-column brief with full-width expand

   Default: two columns (TL;DR | Opinion) with 2-line previews.
   Expanding either side: full canvas width, other column hides.
   OnAir pill triggers the persistent AudioPlayer (rendered in HomeContent).
   --------------------------------------------------------------------------- */

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration,
    handlePlayPause, setExpanded, setPlayerVisible,
  } = state;
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  // Full text — line-clamp truncates when collapsed, full when expanded
  const tldrFull = brief.tldr_text;
  const tldrSentences = tldrFull.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrHasMore = tldrSentences.length > 2;

  const opinionFull = brief.opinion_text || "";
  const opinionSentences = opinionFull.split(/(?<=[.!?])\s+/).filter(Boolean);
  const opinionHasMore = opinionSentences.length > 2;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right"
    : "skb-lean--center";

  const toggleSide = (side: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSide((prev) => prev === side ? null : side);
  };

  // OnAir pill — prominent CTA with radio waves that triggers the bottom player
  const onairPill = (
    <div className="skb__onair-unit">
      <button
        className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}`}
        onClick={() => {
          hapticConfirm();
          if (hasAudio) {
            setPlayerVisible(true);
            if (!isPlaying) handlePlayPause();
            setExpanded(true);
          }
        }}
        type="button"
        disabled={!hasAudio}
        aria-label={
          !hasAudio ? "Audio broadcast unavailable"
            : isPlaying ? "Open audio player" : "Play broadcast"
        }
        title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
      >
        <span className="skb__radio-waves" aria-hidden="true">
          <span className="skb__radio-wave" />
          <span className="skb__radio-wave" />
          <span className="skb__radio-wave" />
        </span>
        {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
        <span className="skb__onair-label">void --onair</span>
        {hasAudio ? (
          isPlaying ? (
            <span className="skb__onair-dur">
              {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
            </span>
          ) : (
            durationMin && <span className="skb__onair-dur">{durationMin} min</span>
          )
        ) : (
          <span className="skb__onair-dur">twice daily</span>
        )}
      </button>
    </div>
  );

  return (
    <div className={`skb${expandedSide ? ` skb--expand-${expandedSide}` : ""}`} role="complementary" aria-label="Daily Brief">
      {/* Columns — two-col preview or single-col expanded */}
      <div className="skb__columns">
        {/* TL;DR column */}
        {expandedSide !== "opinion" && (
          <div className={`skb__col skb__col--tldr${expandedSide === "tldr" ? " skb__col--full" : ""}`}>
            <div className="skb__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="skb__cmd">void --tl;dr</span>
              {brief.created_at && <span className="skb__time">{timeAgo(brief.created_at)}</span>}
            </div>
            {brief.tldr_headline && (
              <h3 className="skb__hl skb__hl--tldr">{brief.tldr_headline}</h3>
            )}

            {expandedSide === "tldr" ? (
              <div className="skb__expand-text--tldr">
                {tldrFull.split(/\n\n+/).map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            ) : (
              <p className="skb__preview skb__preview--tldr">
                {tldrFull}
              </p>
            )}

            {tldrHasMore && (
              <button
                className="skb__more"
                onClick={() => toggleSide("tldr")}
                type="button"
                aria-expanded={expandedSide === "tldr"}
              >
                {expandedSide === "tldr" ? "less" : "read more"}
              </button>
            )}
          </div>
        )}

        {/* Opinion column */}
        {brief.opinion_text && expandedSide !== "tldr" && (
          <div className={`skb__col skb__col--opinion${expandedSide === "opinion" ? " skb__col--full" : ""}`}>
            <div className="skb__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="skb__cmd">void --opinion</span>
              {brief.opinion_lean && (
                <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>
              )}
            </div>
            {brief.opinion_headline && (
              <h3 className="skb__hl skb__hl--opinion">{brief.opinion_headline}</h3>
            )}

            {expandedSide === "opinion" ? (
              <div className="skb__expand-text--opinion">
                {opinionFull.split(/\n\n+/).map((para, i) => (
                  <p key={i}>{para}</p>
                ))}
              </div>
            ) : (
              <p className="skb__preview skb__preview--opinion">
                {opinionFull}
              </p>
            )}

            {opinionHasMore && (
              <button
                className="skb__more"
                onClick={() => toggleSide("opinion")}
                type="button"
                aria-expanded={expandedSide === "opinion"}
              >
                {expandedSide === "opinion" ? "less" : "read more"}
              </button>
            )}
          </div>
        )}
      </div>

      {/* OnAir pill — always visible, centered below content */}
      <div className="skb__onair-center">{onairPill}</div>
    </div>
  );
}
