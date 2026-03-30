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
   SkyboxBanner — Two-column brief replacing the old desktop Skybox

   Left:  void --tl;dr (Structural voice — Inter, factual, reporting)
   Right: void --opinion (Editorial voice — Playfair, italic, editorial)
   Footer: [Read full brief] + [▶ void --onair] retro radio player

   Canvas-width (no full-bleed). Inline expand — no overlay.
   --------------------------------------------------------------------------- */

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState(false);
  const [radioOpen, setRadioOpen] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const radioRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);
  const [radioHeight, setRadioHeight] = useState(0);

  // Measure expanded content height for smooth spring animation
  useEffect(() => {
    if (!contentRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setContentHeight(entry.contentRect.height);
    });
    ro.observe(contentRef.current);
    return () => ro.disconnect();
  }, [expanded]);

  // Measure radio panel height
  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setRadioHeight(entry.contentRect.height);
    });
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  // Generate stable waveform bar heights (24 bars, sin wave pattern)
  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + (Math.sin(i * 1.3) * 6)),
  []);

  // Escape key to collapse
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

  // TL;DR preview: first 2 sentences
  const tldrSentences = brief.tldr_text.split(/(?<=[.!?])\s+/).filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");

  // Opinion preview: first 2 sentences
  const opinionPreview = brief.opinion_text
    ? brief.opinion_text.split(/(?<=[.!?])\s+/).slice(0, 2).join(" ")
    : "";

  const paragraphs = brief.tldr_text.split("\n").map((p) => p.trim()).filter(Boolean);

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right"
    : "skb-lean--center";

  const handleToggle = () => {
    hapticLight();
    setExpanded((prev) => !prev);
  };

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className={`skb${expanded ? " skb--expanded" : ""}`} role="complementary" aria-label="Daily Brief">
        {/* Two preview columns — different type voices */}
        <div className="skb__columns">
          {/* TL;DR — Structural voice (Inter, factual) */}
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
          </div>

          {/* Opinion — Editorial voice (Playfair, italic) */}
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
            </div>
          )}
        </div>

        {/* Action row: Read + OnAir */}
        <div className="skb__actions">
          <button
            className="skb__read-btn"
            onClick={handleToggle}
            type="button"
            aria-expanded={expanded}
          >
            {expanded ? "Close brief" : "Read full brief"}
          </button>

          {hasAudio && (
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
          )}
        </div>

        {/* ═══ Radio Player — expands in place with waveform visualization ═══ */}
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
              {/* Waveform visualization — 32 bars, animated when playing */}
              <div className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`} aria-hidden="true">
                {waveformBars.map((h, i) => (
                  <div
                    key={i}
                    className="skb__waveform-bar"
                    style={{
                      height: `${h}px`,
                      animationDelay: `${i * 55}ms`,
                    }}
                  />
                ))}
              </div>

              {/* Transport controls */}
              <div className="skb__transport">
                <button
                  className={`skb__transport-play${isPlaying ? " skb__transport-play--active" : ""}`}
                  onClick={() => { hapticMedium(); handlePlayPause(); }}
                  type="button"
                  aria-label={isPlaying ? "Pause" : "Play"}
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

              {/* Seek bar with section markers */}
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

        {/* ═══ Inline expanded content — spring snap-expand ═══ */}
        <div
          className="skb__expand"
          style={{
            height: expanded ? contentHeight : 0,
            transition: expanded
              ? "height 400ms var(--spring-bouncy)"
              : "height 250ms var(--ease-out)",
          }}
        >
          <div ref={contentRef} className="skb__expand-inner">
            <div className="skb__expand-columns">
              {/* TL;DR full — Structural voice, warm accent headline */}
              <section className="skb__expand-col skb__expand-col--tldr" aria-label="Full TL;DR">
                <span className="skb__expand-tag">void --tl;dr</span>
                {brief.tldr_headline && (
                  <h3 className="skb__expand-hl skb__expand-hl--tldr">{brief.tldr_headline}</h3>
                )}
                <div className="skb__expand-text skb__expand-text--tldr">
                  {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
                </div>
              </section>

              {/* Opinion full — Editorial voice, Playfair italic */}
              {brief.opinion_text && (
                <section className="skb__expand-col skb__expand-col--opinion" aria-label="Editorial Opinion">
                  <div className="skb__expand-opinion-meta">
                    <span className="skb__expand-tag">void --opinion</span>
                    {brief.opinion_lean && (
                      <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>
                    )}
                  </div>
                  {brief.opinion_headline && (
                    <h3 className="skb__expand-hl skb__expand-hl--opinion">{brief.opinion_headline}</h3>
                  )}
                  <div className="skb__expand-text skb__expand-text--opinion">
                    <p>{brief.opinion_text}</p>
                  </div>
                </section>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
