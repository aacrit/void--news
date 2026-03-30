"use client";

import { useState, useRef, useEffect } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight, hapticMedium } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   SkyboxBanner — 40px single-line collapsed brief for desktop v2

   "void --tl;dr · 3h — Six nations broke a decade-long...  [Read]  [▶ 4:32]"

   Clicking [Read] opens an overlay with full TL;DR + Opinion + audio player.
   --------------------------------------------------------------------------- */

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Close on Escape
  useEffect(() => {
    if (!expanded) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setExpanded(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [expanded]);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  // Opinion data
  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinion = opinionStart !== null && displayDuration > 0;
  const opinionPct = hasOpinion ? (opinionStart / displayDuration) * 100 : 100;
  const inOpinion = hasOpinion && currentTime >= opinionStart;

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    if (!isPlaying) handlePlayPause();
  };

  // First sentence for the collapsed banner
  const firstSentence = brief.tldr_text.split(/[.!?]\s/)[0]?.trim() || brief.tldr_text.slice(0, 120);
  const firstSentenceText = firstSentence.match(/[.!?]$/) ? firstSentence : firstSentence + "...";

  const paragraphs = brief.tldr_text.split("\n").map((p) => p.trim()).filter(Boolean);

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "mbp-lean--left"
    : brief.opinion_lean === "right" ? "mbp-lean--right"
    : "mbp-lean--center";

  const handleToggle = () => {
    hapticLight();
    setExpanded((prev) => !prev);
  };

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      {/* Collapsed single-line banner */}
      <div className="skb" role="complementary" aria-label="Daily Brief">
        <div className="skb__left">
          <ScaleIcon size={12} animation="idle" />
          <span className="skb__cmd">void --tl;dr</span>
          {brief.created_at && (
            <span className="skb__time">{timeAgo(brief.created_at)}</span>
          )}
          <span className="skb__separator" aria-hidden="true">&mdash;</span>
          <span className="skb__excerpt">{firstSentenceText}</span>
        </div>
        <div className="skb__right">
          <button className="skb__read" onClick={handleToggle} type="button">
            {expanded ? "Close" : "Read"}
          </button>
          {hasAudio && (
            <button
              className={`skb__play${isPlaying ? " skb__play--active" : ""}`}
              onClick={(e) => { e.stopPropagation(); hapticMedium(); handlePlayPause(); }}
              type="button"
              aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
              {durationMin && !isPlaying && (
                <span className="skb__dur">{durationMin}m</span>
              )}
              {isPlaying && (
                <span className="skb__dur">{formatTime(currentTime)}</span>
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expanded overlay */}
      {expanded && (
        <div className="skb-overlay" ref={overlayRef}>
          <div className="skb-overlay__backdrop" onClick={handleToggle} aria-hidden="true" />
          <div className="skb-overlay__panel" ref={contentRef}>
            <div className="skb-overlay__header">
              <div className="skb-overlay__label">
                <ScaleIcon size={14} animation="idle" />
                <span className="skb__cmd">void --tl;dr</span>
                {brief.created_at && <span className="skb__time">{timeAgo(brief.created_at)}</span>}
              </div>
              <button className="skb-overlay__close" onClick={handleToggle} type="button" aria-label="Close brief">
                &times;
              </button>
            </div>

            {/* Full TL;DR */}
            <section className="skb-overlay__section">
              {brief.tldr_headline && (
                <h3 className="skb-overlay__headline skb-overlay__headline--accent">{brief.tldr_headline}</h3>
              )}
              <div className="skb-overlay__text">
                {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
              </div>
            </section>

            {/* Dotted rule */}
            {brief.opinion_text && <hr className="skb-overlay__rule" />}

            {/* Full Opinion */}
            {brief.opinion_text && (
              <section className="skb-overlay__section">
                <div className="skb-overlay__opinion-label">
                  <ScaleIcon size={12} animation="idle" />
                  <span className="skb__cmd">void --opinion</span>
                  {brief.opinion_lean && (
                    <span className={`mbp__lean ${leanMod}`}>{leanLabel}</span>
                  )}
                </div>
                {brief.opinion_headline && (
                  <h3 className="skb-overlay__headline">{brief.opinion_headline}</h3>
                )}
                <div className="skb-overlay__text">
                  <p>{brief.opinion_text}</p>
                </div>
              </section>
            )}

            {/* Audio player */}
            {hasAudio && (
              <div className="skb-overlay__audio">
                <div className="skb-overlay__audio-row">
                  <button
                    className={`mbp__play mbp__play--lg${isPlaying ? " mbp__play--active" : ""}`}
                    onClick={() => { hapticMedium(); handlePlayPause(); }}
                    type="button"
                    aria-label={isPlaying ? "Pause" : "Play"}
                  >
                    <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                  </button>
                  <span className="skb__cmd">void --onair</span>
                  <span className="skb__time">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</span>
                </div>
                <div className="mbp__sections">
                  <button
                    className={`mbp__section-btn${!inOpinion ? " mbp__section-btn--active" : ""}`}
                    onClick={() => seekTo(0)} type="button"
                    style={hasOpinion ? { width: `${opinionPct}%` } : { width: "100%" }}
                  >News</button>
                  {hasOpinion && (
                    <button
                      className={`mbp__section-btn${inOpinion ? " mbp__section-btn--active" : ""}`}
                      onClick={() => seekTo(opinionStart)} type="button"
                      style={{ width: `${100 - opinionPct}%` }}
                    >Opinion</button>
                  )}
                </div>
                <div className="mbp__seek-wrap">
                  <div className="mbp__bar">
                    <div className="mbp__fill" style={{ width: `${progress}%` }} />
                    {hasOpinion && <span className="mbp__section-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                  </div>
                  <input type="range" className="mbp__seek" min={0} max={displayDuration || 100}
                    value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek" />
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
