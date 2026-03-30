"use client";

import { useState, useRef, useEffect, useMemo } from "react";
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
   OnAir pill always centered below the content area.
   --------------------------------------------------------------------------- */

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);
  const [radioOpen, setRadioOpen] = useState(false);
  const radioRef = useRef<HTMLDivElement>(null);
  const [radioHeight, setRadioHeight] = useState(0);

  // Measure radio panel height
  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) => setRadioHeight(e.contentRect.height));
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  // Waveform bar heights
  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + (Math.sin(i * 1.3) * 6)),
  []);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinionTimestamp = opinionStart !== null && displayDuration > 0;
  // Estimate opinion start at 60% if no timestamp but opinion text exists
  const effectiveOpinionStart = opinionStart ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = hasOpinionTimestamp ? (opinionStart / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    if (!isPlaying) handlePlayPause();
  };

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

  // OnAir pill + radio player as a single unit that renders wherever the pill goes
  const onairUnit = hasAudio ? (
    <div className="skb__onair-unit">
      <button
        className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}${radioOpen ? " skb__onair-btn--open" : ""}`}
        onClick={() => { hapticConfirm(); setRadioOpen((v) => !v); if (!isPlaying && !radioOpen) handlePlayPause(); }}
        type="button"
        aria-label={radioOpen ? "Close radio player" : "Open radio player"}
        aria-expanded={radioOpen}
      >
        <span className="skb__radio-waves" aria-hidden="true">
          <span className="skb__radio-wave" />
          <span className="skb__radio-wave" />
          <span className="skb__radio-wave" />
        </span>
        {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
        <span className="skb__onair-label">void --onair</span>
        {durationMin && !isPlaying && (
          <span className="skb__onair-dur">{durationMin} min</span>
        )}
        {isPlaying && (
          <span className="skb__onair-dur">
            {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
          </span>
        )}
      </button>

      {/* Inline seek bar — always visible when audio has progress, even when radio panel closed */}
      {(isPlaying || currentTime > 0) && !radioOpen && (
        <div className="skb__inline-seek">
          <div className="skb__inline-sections">
            <button className={`skb__inline-sec${!inOpinion ? " skb__inline-sec--active" : ""}`}
              onClick={() => seekTo(0)} type="button">News</button>
            {hasOpinionSection && (
              <button className={`skb__inline-sec${inOpinion ? " skb__inline-sec--active" : ""}`}
                onClick={() => effectiveOpinionStart ? seekTo(effectiveOpinionStart) : null} type="button">Opinion</button>
            )}
          </div>
          <div className="skb__inline-bar-wrap">
            <div className="skb__inline-bar">
              <div className="skb__inline-fill" style={{ width: `${progress}%` }} />
              {hasOpinionSection && <span className="skb__inline-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
            </div>
            <input type="range" className="skb__inline-input" min={0} max={displayDuration || 100}
              value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek" />
          </div>
        </div>
      )}

      {/* Radio player expands in place below the pill */}
      <div
        className="skb__radio"
        style={{
          height: radioOpen ? radioHeight : 0,
          transition: radioOpen
            ? "height 400ms var(--spring-bouncy)"
            : "height 250ms var(--ease-out)",
        }}
      >
        <div ref={radioRef} className={`skb__radio-inner${isPlaying ? " skb__radio-inner--live" : ""}`}>
          <div className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`} aria-hidden="true">
            {waveformBars.map((h, i) => (
              <div key={i} className="skb__waveform-bar"
                style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
            ))}
          </div>

          <div className="skb__transport">
            <button
              className={`skb__transport-play${isPlaying ? " skb__transport-play--active" : ""}`}
              onClick={() => { hapticMedium(); handlePlayPause(); }}
              type="button" aria-label={isPlaying ? "Pause" : "Play"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
            </button>
            <div className="skb__transport-info">
              <div className="skb__transport-label">
                <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "idle"} />
                <span className="skb__transport-cmd">void --onair</span>
                {isPlaying && <span className="skb__rec-dot skb__rec-dot--lg" aria-label="Recording" />}
              </div>
              <div className="skb__transport-voices">
                <span>{inOpinion ? "Opinion" : "News"}</span>
                {displayDuration > 0 && (
                  <>
                    <span className="skb__transport-dot" aria-hidden="true" />
                    <span>{Math.round(progress)}%</span>
                  </>
                )}
              </div>
            </div>
            <span className="skb__transport-time">
              {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
            </span>
          </div>

          <div className="skb__radio-seek">
            <div className="skb__radio-sections">
              <button className={`skb__radio-sec${!inOpinion ? " skb__radio-sec--active" : ""}`}
                onClick={() => seekTo(0)} type="button"
                style={{ width: `${opinionPct}%` }}>News</button>
              {hasOpinionSection && (
                <button className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                  onClick={() => effectiveOpinionStart ? seekTo(effectiveOpinionStart) : null} type="button"
                  style={{ width: `${100 - opinionPct}%` }}>Opinion</button>
              )}
            </div>
            <div className="skb__radio-bar-wrap">
              <div className="skb__radio-bar">
                <div className="skb__radio-fill" style={{ width: `${progress}%` }} />
                {hasOpinionSection && <span className="skb__radio-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
              </div>
              <input type="range" className="skb__radio-input" min={0} max={displayDuration || 100}
                value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek position" />
            </div>
          </div>
        </div>
      </div>
    </div>
  ) : null;

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className={`skb${expandedSide ? ` skb--expand-${expandedSide}` : ""}`} role="complementary" aria-label="Daily Brief">
        {/* Columns — two-col preview or single-col expanded */}
        <div className="skb__columns">
          {/* ── TL;DR column (visible when collapsed OR when TL;DR is expanded) ── */}
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
                /* Full text — no line-clamp, full canvas width */
                <div className="skb__expand-text--tldr">
                  {tldrFull.split(/\n\n+/).map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              ) : (
                /* Preview — 2-line clamp */
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

          {/* ── Opinion column (visible when collapsed OR when opinion is expanded) ── */}
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
                /* Full text — no line-clamp, full canvas width */
                <div className="skb__expand-text--opinion">
                  {opinionFull.split(/\n\n+/).map((para, i) => (
                    <p key={i}>{para}</p>
                  ))}
                </div>
              ) : (
                /* Preview — 2-line clamp */
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

        {/* OnAir — always centered below content */}
        {onairUnit && (
          <div className="skb__onair-center">{onairUnit}</div>
        )}
      </div>
    </>
  );
}
