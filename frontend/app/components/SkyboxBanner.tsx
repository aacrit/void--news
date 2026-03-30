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
   SkyboxBanner — Two-column brief with per-section expand

   Each column has its own subtle "read more". Expanding one side pushes
   the void --onair pill to the other side. Only one side expands at a time.
   OnAir pill is centered and prominent when nothing is expanded.
   --------------------------------------------------------------------------- */

type ExpandedSide = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expandedSide, setExpandedSide] = useState<ExpandedSide>(null);
  const [radioOpen, setRadioOpen] = useState(false);
  const tldrRef = useRef<HTMLDivElement>(null);
  const opinionRef = useRef<HTMLDivElement>(null);
  const radioRef = useRef<HTMLDivElement>(null);
  const [tldrHeight, setTldrHeight] = useState(0);
  const [opinionHeight, setOpinionHeight] = useState(0);
  const [radioHeight, setRadioHeight] = useState(0);

  // Measure expand heights
  useEffect(() => {
    if (!tldrRef.current) return;
    const ro = new ResizeObserver(([e]) => setTldrHeight(e.contentRect.height));
    ro.observe(tldrRef.current);
    return () => ro.disconnect();
  }, [expandedSide]);

  useEffect(() => {
    if (!opinionRef.current) return;
    const ro = new ResizeObserver(([e]) => setOpinionHeight(e.contentRect.height));
    ro.observe(opinionRef.current);
    return () => ro.disconnect();
  }, [expandedSide]);

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

  // Previews — split by sentences, show first 2 as preview, rest as expanded
  const tldrSentences = brief.tldr_text.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");
  const tldrRest = tldrSentences.slice(2).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const opinionSentences = brief.opinion_text
    ? brief.opinion_text.split(/(?<=[.!?])\s+/).filter(Boolean)
    : [];
  const opinionPreview = opinionSentences.slice(0, 2).join(" ");
  const opinionRest = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRest.length > 0;

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

  // OnAir pill renders in the column that is NOT expanded, or centered when neither is
  const onairPill = hasAudio ? (
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
      <span className="skb__onair-label">void --onair</span>
      {durationMin && !isPlaying && !radioOpen && (
        <span className="skb__onair-dur">{durationMin} min</span>
      )}
      {isPlaying && !radioOpen && (
        <span className="skb__onair-dur">{formatTime(currentTime)}</span>
      )}
      {radioOpen && (
        <span className="skb__onair-dur">{isPlaying ? "ON AIR" : "STANDBY"}</span>
      )}
    </button>
  ) : null;

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className={`skb${expandedSide ? ` skb--expand-${expandedSide}` : ""}`} role="complementary" aria-label="Daily Brief">
        {/* Two columns */}
        <div className="skb__columns">
          {/* ── TL;DR column ── */}
          <div className="skb__col skb__col--tldr">
            <div className="skb__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="skb__cmd">void --tl;dr</span>
              {brief.created_at && <span className="skb__time">{timeAgo(brief.created_at)}</span>}
            </div>
            {brief.tldr_headline && (
              <h3 className="skb__hl skb__hl--tldr">{brief.tldr_headline}</h3>
            )}
            <p className="skb__preview skb__preview--tldr">{tldrPreview}</p>

            {/* Inline expand for TL;DR */}
            <div
              className="skb__side-expand"
              style={{
                height: expandedSide === "tldr" ? tldrHeight : 0,
                transition: expandedSide === "tldr"
                  ? "height 350ms var(--spring-snappy)"
                  : "height 200ms var(--ease-out)",
              }}
            >
              <div ref={tldrRef} className="skb__side-expand-inner">
                <div className="skb__expand-text skb__expand-text--tldr">
                  <p>{tldrRest}</p>
                </div>
              </div>
            </div>

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

            {/* OnAir lands here when opinion is expanded */}
            {expandedSide === "opinion" && onairPill && (
              <div className="skb__onair-shifted">{onairPill}</div>
            )}
          </div>

          {/* ── Opinion column ── */}
          {brief.opinion_text && (
            <div className="skb__col skb__col--opinion">
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
              <p className="skb__preview skb__preview--opinion">{opinionPreview}</p>

              {/* Inline expand for Opinion */}
              <div
                className="skb__side-expand"
                style={{
                  height: expandedSide === "opinion" ? opinionHeight : 0,
                  transition: expandedSide === "opinion"
                    ? "height 350ms var(--spring-snappy)"
                    : "height 200ms var(--ease-out)",
                }}
              >
                <div ref={opinionRef} className="skb__side-expand-inner">
                  <div className="skb__expand-text skb__expand-text--opinion">
                    <p>{opinionRest}</p>
                  </div>
                </div>
              </div>

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

              {/* OnAir lands here when tldr is expanded */}
              {expandedSide === "tldr" && onairPill && (
                <div className="skb__onair-shifted">{onairPill}</div>
              )}
            </div>
          )}
        </div>

        {/* Centered OnAir when nothing is expanded */}
        {!expandedSide && onairPill && (
          <div className="skb__onair-center">{onairPill}</div>
        )}

        {/* ═══ Radio Player ═══ */}
        {hasAudio && (
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
                    {isPlaying && <span className="skb__transport-live">LIVE</span>}
                  </div>
                  <div className="skb__transport-voices">
                    <span>Voice A: the facts</span>
                    <span className="skb__transport-dot" aria-hidden="true" />
                    <span>Voice B: the questions</span>
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
                    style={hasOpinion ? { width: `${opinionPct}%` } : { width: "100%" }}>News</button>
                  {hasOpinion && (
                    <button className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                      onClick={() => seekTo(opinionStart)} type="button"
                      style={{ width: `${100 - opinionPct}%` }}>Opinion</button>
                  )}
                </div>
                <div className="skb__radio-bar-wrap">
                  <div className="skb__radio-bar">
                    <div className="skb__radio-fill" style={{ width: `${progress}%` }} />
                    {hasOpinion && <span className="skb__radio-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                  </div>
                  <input type="range" className="skb__radio-input" min={0} max={displayDuration || 100}
                    value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek position" />
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
