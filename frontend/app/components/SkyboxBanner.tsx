"use client";

import { useState, useEffect } from "react";
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
   SkyboxBanner — Two-column brief replacing the old desktop Skybox

   Left:  void --tl;dr (Structural voice — Inter, factual, reporting)
   Right: void --opinion (Editorial voice — Playfair, italic, editorial)
   Footer: [Read full brief] + [▶ void --onair] prominent player

   Canvas-width (no full-bleed). Overlay is void-branded dark space.
   --------------------------------------------------------------------------- */

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState(false);

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

      <div className="skb" role="complementary" aria-label="Daily Brief">
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
          <button className="skb__read-btn" onClick={handleToggle} type="button">
            {expanded ? "Close" : "Read full brief"}
          </button>

          {hasAudio && (
            <div className={`skb__onair${isPlaying ? " skb__onair--playing" : ""}`}>
              <button
                className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}`}
                onClick={() => { hapticMedium(); handlePlayPause(); }}
                type="button"
                aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
              >
                <ScaleIcon size={14} animation={isPlaying ? "analyzing" : "idle"} />
                <span className="skb__onair-icon" aria-hidden="true">
                  {isPlaying ? "\u275A\u275A" : "\u25B6"}
                </span>
                <span className="skb__onair-label">void --onair</span>
                {durationMin && !isPlaying && (
                  <span className="skb__onair-dur">{durationMin} min</span>
                )}
                {isPlaying && (
                  <span className="skb__onair-dur">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</span>
                )}
              </button>

              {/* Seek bar when playing */}
              {(isPlaying || currentTime > 0) && (
                <div className="skb__onair-track">
                  <div className="skb__onair-sections">
                    <button className={`skb__onair-sec${!inOpinion ? " skb__onair-sec--active" : ""}`}
                      onClick={() => seekTo(0)} type="button"
                      style={hasOpinion ? { width: `${opinionPct}%` } : { width: "100%" }}>News</button>
                    {hasOpinion && (
                      <button className={`skb__onair-sec${inOpinion ? " skb__onair-sec--active" : ""}`}
                        onClick={() => seekTo(opinionStart)} type="button"
                        style={{ width: `${100 - opinionPct}%` }}>Opinion</button>
                    )}
                  </div>
                  <div className="skb__onair-bar-wrap">
                    <div className="skb__onair-bar">
                      <div className="skb__onair-fill" style={{ width: `${progress}%` }} />
                      {hasOpinion && <span className="skb__onair-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                    </div>
                    <input type="range" className="skb__onair-seek" min={0} max={displayDuration || 100}
                      value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek" />
                  </div>
                </div>
              )}

              {isPlaying && (
                <div className="skb__onair-eq" aria-hidden="true">
                  <span className="skb__eq-bar" style={{ animationDelay: "0ms" }} />
                  <span className="skb__eq-bar" style={{ animationDelay: "150ms" }} />
                  <span className="skb__eq-bar" style={{ animationDelay: "75ms" }} />
                  <span className="skb__eq-bar" style={{ animationDelay: "200ms" }} />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ═══ Expanded Overlay — void space ═══ */}
      {expanded && (
        <div className="void-overlay">
          <div className="void-overlay__backdrop" onClick={handleToggle} aria-hidden="true" />
          <div className="void-overlay__panel">
            {/* Void header */}
            <div className="void-overlay__header">
              <ScaleIcon size={18} animation="idle" />
              <span className="void-overlay__brand">void --editorial</span>
              <button className="void-overlay__close" onClick={handleToggle} type="button" aria-label="Close">
                &times;
              </button>
            </div>

            <div className="void-overlay__body">
              {/* TL;DR section — Structural voice */}
              <section className="void-overlay__section void-overlay__section--tldr">
                <span className="void-overlay__tag">void --tl;dr</span>
                {brief.tldr_headline && (
                  <h3 className="void-overlay__hl void-overlay__hl--tldr">{brief.tldr_headline}</h3>
                )}
                <div className="void-overlay__text void-overlay__text--tldr">
                  {paragraphs.map((p, i) => <p key={i}>{p}</p>)}
                </div>
              </section>

              {/* Void rule */}
              {brief.opinion_text && <div className="void-overlay__divider" aria-hidden="true" />}

              {/* Opinion section — Editorial voice */}
              {brief.opinion_text && (
                <section className="void-overlay__section void-overlay__section--opinion">
                  <div className="void-overlay__opinion-meta">
                    <span className="void-overlay__tag">void --opinion</span>
                    {brief.opinion_lean && (
                      <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>
                    )}
                  </div>
                  {brief.opinion_headline && (
                    <h3 className="void-overlay__hl void-overlay__hl--opinion">{brief.opinion_headline}</h3>
                  )}
                  <div className="void-overlay__text void-overlay__text--opinion">
                    <p>{brief.opinion_text}</p>
                  </div>
                </section>
              )}

              {/* Audio player */}
              {hasAudio && (
                <div className="void-overlay__audio">
                  <div className="void-overlay__audio-row">
                    <button
                      className={`void-overlay__play${isPlaying ? " void-overlay__play--active" : ""}`}
                      onClick={() => { hapticMedium(); handlePlayPause(); }}
                      type="button" aria-label={isPlaying ? "Pause" : "Play"}
                    >
                      <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                    </button>
                    <span className="void-overlay__audio-label">void --onair</span>
                    <span className="void-overlay__audio-time">
                      {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                    </span>
                  </div>
                  <div className="void-overlay__seek-wrap">
                    <div className="void-overlay__seek-bar">
                      <div className="void-overlay__seek-fill" style={{ width: `${progress}%` }} />
                      {hasOpinion && <span className="void-overlay__seek-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
                    </div>
                    <input type="range" className="void-overlay__seek-input" min={0} max={displayDuration || 100}
                      value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek" />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
