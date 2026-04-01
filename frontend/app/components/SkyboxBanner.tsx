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

/** Truncate text to a single line with ellipsis at ~80 chars */
function truncateLine(text: string, max = 80): string {
  if (text.length <= max) return text;
  return text.slice(0, max).replace(/\s+\S*$/, "") + "\u2026";
}

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
  } = state;

  const [expanded, setExpanded] = useState(false);
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);
  const [radioOpen, setRadioOpen] = useState(false);
  const radioRef = useRef<HTMLDivElement>(null);
  const [radioHeight, setRadioHeight] = useState(0);

  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) => {
      const h = e.borderBoxSize?.[0]?.blockSize ?? e.target.getBoundingClientRect().height;
      setRadioHeight(h);
    });
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + Math.sin(i * 1.3) * 6),
  []);

  if (!brief) return (
    <div className="skb anim-cold-open-skybox skb--collapsed" role="complementary" aria-label="Daily Brief">
      <div className="skb__bar">
        <ScaleIcon size={12} animation="analyzing" />
        <span className="skb__bar-human">Daily Brief</span>
        <span className="skb__bar-cli">void --tl;dr</span>
        <span className="skb__bar-excerpt" style={{ opacity: 0.4 }}>Loading today&rsquo;s brief&hellip;</span>
      </div>
    </div>
  );

  const hasAudio = !!brief.audio_url;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;
  const speedLabel = `${playbackSpeed}x`;

  const opinionStart = brief.opinion_start_seconds ?? null;
  const effectiveOpinionStart = opinionStart ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = opinionStart !== null && displayDuration > 0
    ? (opinionStart / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;

  const tldrFull = brief.tldr_text;
  const tldrHasMore = tldrFull.split(/(?<=[.!?])\s+/).filter(Boolean).length > 2;
  const opinionFull = brief.opinion_text || "";
  const opinionHasMore = opinionFull.split(/(?<=[.!?])\s+/).filter(Boolean).length > 2;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const toggleExpand = () => {
    hapticLight();
    setExpanded((v) => !v);
    if (expanded) setExpandedSide(null);
  };

  const toggleSide = (side: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSide((prev) => prev === side ? null : side);
  };

  // Collapsed bar: single-line summary with listen button
  const barExcerpt = brief.tldr_headline || truncateLine(tldrFull);

  return (
    <>
      {hasAudio && <audio id="void-onair-audio" ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />}

      <div
        className={`skb anim-cold-open-skybox${expanded ? " skb--expanded" : " skb--collapsed"}${expandedSide ? ` skb--expand-${expandedSide}` : ""}`}
        role="complementary"
        aria-label="Daily Brief"
      >
        {/* Collapsed bar — single line */}
        {!expanded && (
          <div className="skb__bar">
            <button
              className="skb__bar-toggle"
              onClick={toggleExpand}
              type="button"
              aria-expanded={false}
              aria-label="Expand daily brief"
            >
              <ScaleIcon size={12} animation="none" />
              <span className="skb__bar-human">Daily Brief</span>
              <span className="skb__bar-cli">void --tl;dr</span>
              {brief.created_at && <span className="skb__bar-time">{timeAgo(brief.created_at)}</span>}
              <span className="skb__bar-sep" aria-hidden="true" />
              <span className="skb__bar-excerpt">{barExcerpt}</span>
              <span className="skb__bar-caret" aria-hidden="true">&#9662;</span>
            </button>

            {/* Listen button — always visible in collapsed bar */}
            {hasAudio && (
              <button
                className={`skb__bar-listen${isPlaying ? " skb__bar-listen--active" : ""}`}
                onClick={(e) => {
                  e.stopPropagation();
                  hapticConfirm();
                  if (!expanded) setExpanded(true);
                  setRadioOpen(true);
                  if (!isPlaying) handlePlayPause();
                }}
                type="button"
                aria-label={isPlaying ? "Now playing" : "Listen to broadcast"}
              >
                {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
                <span className="skb__bar-listen-icon" aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                <span className="skb__bar-listen-label">Listen</span>
                <span className="skb__bar-listen-cli">void --onair</span>
                {isPlaying ? (
                  <span className="skb__bar-listen-dur">{formatTime(currentTime)}</span>
                ) : (
                  durationMin && <span className="skb__bar-listen-dur">{durationMin} min</span>
                )}
              </button>
            )}
          </div>
        )}

        {/* Expanded view — full editorial content */}
        {expanded && (
          <>
            {/* Collapse button */}
            <div className="skb__expanded-header">
              <button className="skb__collapse-btn" onClick={toggleExpand} type="button" aria-expanded={true} aria-label="Collapse daily brief">
                <span className="skb__bar-human">Daily Brief</span>
                <span className="skb__bar-cli">void --tl;dr</span>
                <span className="skb__bar-caret skb__bar-caret--up" aria-hidden="true">&#9652;</span>
              </button>
            </div>

            {/* OnAir pill — left-aligned, above editorial columns */}
            <div className="skb__onair-unit">
              <button
                className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}${radioOpen ? " skb__onair-btn--open" : ""}`}
                onClick={() => {
                  hapticConfirm();
                  if (!hasAudio) return;
                  setRadioOpen((v) => !v);
                  if (!isPlaying && !radioOpen) handlePlayPause();
                }}
                type="button"
                aria-label={radioOpen ? "Close player" : hasAudio ? "Play broadcast" : "Audio unavailable"}
                aria-expanded={radioOpen}
              >
                {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
                <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "none"} />
                <span className="skb__onair-human">Listen</span>
                <span className="skb__onair-label">void --onair</span>
                {audioError ? (
                  <span className="skb__onair-dur skb__onair-dur--error">Unavailable</span>
                ) : hasAudio ? (
                  isPlaying ? (
                    <span className="skb__onair-dur">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</span>
                  ) : (
                    durationMin && <span className="skb__onair-dur">{durationMin} min</span>
                  )
                ) : (
                  <span className="skb__onair-dur">twice daily</span>
                )}
              </button>

              {/* Expanding radio player */}
              {/* eslint-disable-next-line react/no-unknown-property */}
              <div className="skb__radio" inert={!radioOpen ? true : undefined} style={{
                height: radioOpen ? radioHeight : 0,
                transition: radioOpen ? "height 400ms var(--spring-bouncy, ease)" : "height 250ms var(--ease-out, ease)",
              }}>
                <div ref={radioRef} className={`skb__radio-inner${isPlaying ? " skb__radio-inner--live" : ""}`}>
                  <div className="skb__radio-header">
                    <button className="skb__radio-speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                      type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
                  </div>

                  <div className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`} aria-hidden="true">
                    {waveformBars.map((h, i) => (
                      <div key={i} className="skb__waveform-bar" style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
                    ))}
                  </div>

                  <div className="skb__transport">
                    <button className="skb__transport-skip" onClick={() => skipBackward()} type="button" aria-label="Back 15s">-15</button>
                    <button
                      className={`skb__transport-play${isPlaying ? " skb__transport-play--active" : ""}`}
                      onClick={() => { hapticMedium(); handlePlayPause(); }}
                      type="button" aria-label={isPlaying ? "Pause" : "Play"}
                    >
                      <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                    </button>
                    <button className="skb__transport-skip" onClick={() => skipForward()} type="button" aria-label="Forward 15s">+15</button>
                  </div>

                  <div className="skb__dial">
                    <div className="skb__dial-row">
                      <button className={`skb__radio-sec${!inOpinion ? " skb__radio-sec--active" : ""}`}
                        onClick={() => seekTo(0)} type="button">News</button>
                      <div className="skb__radio-bar-wrap">
                        <div className="skb__radio-bar">
                          <div className="skb__radio-buffer" style={{ width: `${buffered}%` }} />
                          <div className="skb__radio-fill" style={{ width: `${progress}%` }} />
                          {hasOpinionSection && <span className="skb__radio-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                        </div>
                        <input type="range" className="skb__radio-input" min={0} max={displayDuration || 100}
                          value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek"
                          aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
                      </div>
                      {hasOpinionSection && (
                        <button className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                          onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                          type="button">Opinion</button>
                      )}
                    </div>
                    <div className="skb__dial-time">
                      <span className="skb__radio-time">{formatTime(currentTime)}</span>
                      <span className="skb__radio-time">{formatTime(displayDuration || 0)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Editorial columns — TL;DR + Opinion */}
            <div className="skb__columns">
              {expandedSide !== "opinion" && (
                <div className={`skb__col skb__col--tldr${expandedSide === "tldr" ? " skb__col--full" : ""}`}>
                  <div className="skb__label">
                    <ScaleIcon size={12} animation="none" />
                    <span className="skb__label-human">Daily Brief</span>
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
                      aria-expanded={expandedSide === "tldr"}>{expandedSide === "tldr" ? "Less" : "Read more"}</button>
                  )}
                </div>
              )}

              {brief.opinion_text && expandedSide !== "tldr" && (
                <div className={`skb__col skb__col--opinion${expandedSide === "opinion" ? " skb__col--full" : ""}`}>
                  <div className="skb__label">
                    <ScaleIcon size={12} animation="none" />
                    <span className="skb__label-human">Editorial</span>
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
                      aria-expanded={expandedSide === "opinion"}>{expandedSide === "opinion" ? "Less" : "Read more"}</button>
                  )}
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
