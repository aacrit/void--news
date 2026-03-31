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

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
  } = state;
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);
  const [radioOpen, setRadioOpen] = useState(false);
  const radioRef = useRef<HTMLDivElement>(null);
  const [radioHeight, setRadioHeight] = useState(0);

  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) => setRadioHeight(e.contentRect.height));
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + Math.sin(i * 1.3) * 6),
  []);

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

  const toggleSide = (side: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSide((prev) => prev === side ? null : side);
  };

  return (
    <>
      {hasAudio && <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />}

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
                  aria-expanded={expandedSide === "tldr"}>{expandedSide === "tldr" ? "Less" : "Read more"}</button>
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
                  aria-expanded={expandedSide === "opinion"}>{expandedSide === "opinion" ? "Less" : "Read more"}</button>
              )}
            </div>
          )}
        </div>

        {/* ── OnAir Pill + Expanding Player ── */}
        <div className="skb__onair-center">
          <div className="skb__onair-unit">
            <button
              className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}${radioOpen ? " skb__onair-btn--open" : ""}`}
              onClick={() => {
                hapticConfirm();
                setRadioOpen((v) => !v);
                if (!isPlaying && !radioOpen && hasAudio) handlePlayPause();
              }}
              type="button"
              aria-label={radioOpen ? "Close player" : hasAudio ? "Play broadcast" : "Audio unavailable"}
              aria-expanded={radioOpen}
            >
              {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
              <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "idle"} />
              <span className="skb__onair-label">void --onair</span>
              {hasAudio ? (
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
            <div className="skb__radio" style={{
              height: radioOpen ? radioHeight : 0,
              transition: radioOpen ? "height 400ms var(--spring-bouncy, ease)" : "height 250ms var(--ease-out, ease)",
            }}>
              <div ref={radioRef} className={`skb__radio-inner${isPlaying ? " skb__radio-inner--live" : ""}`}>
                {/* Waveform */}
                <div className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`} aria-hidden="true">
                  {waveformBars.map((h, i) => (
                    <div key={i} className="skb__waveform-bar" style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
                  ))}
                </div>

                {/* Transport: skip back, play/pause, skip forward */}
                <div className="skb__transport">
                  <button className="skb__transport-skip" onClick={() => skipBackward()} type="button" aria-label="Back 15s">
                    -15
                  </button>
                  <button
                    className={`skb__transport-play${isPlaying ? " skb__transport-play--active" : ""}`}
                    onClick={() => { hapticMedium(); handlePlayPause(); }}
                    type="button" aria-label={isPlaying ? "Pause" : "Play"}
                  >
                    <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                  </button>
                  <button className="skb__transport-skip" onClick={() => skipForward()} type="button" aria-label="Forward 15s">
                    +15
                  </button>
                </div>

                {/* Section nav + speed */}
                <div className="skb__radio-controls">
                  <div className="skb__radio-sections">
                    <button className={`skb__radio-sec${!inOpinion ? " skb__radio-sec--active" : ""}`}
                      onClick={() => seekTo(0)} type="button">News</button>
                    {hasOpinionSection && (
                      <button className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                        onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                        type="button">Opinion</button>
                    )}
                  </div>
                  <button className="skb__radio-speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                    type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
                </div>

                {/* Seek bar */}
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

                {/* Time */}
                <div className="skb__radio-time">
                  {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
