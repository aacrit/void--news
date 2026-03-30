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
   MobileBriefPill — Mobile-optimized skybox with TL;DR, Opinion, OnAir

   Single-column stacked layout. Each section has independent "read more"
   expand/collapse. OnAir pill uses the retro radio aesthetic from desktop.
   Radio player expands below the pill with 20 waveform bars.
   Spring-snappy for section expand, spring-bouncy for radio expand.
   --------------------------------------------------------------------------- */

export default function MobileBriefPill({ state }: { state: DailyBriefState }) {
  const {
    brief,
    isPlaying,
    currentTime,
    duration,
    audioError,
    audioRef,
    audioCallbackRef,
    handlePlayPause,
    handleSeek,
  } = state;

  // Top-level collapsed state: single-line pill by default to save fold space
  const [pillExpanded, setPillExpanded] = useState(false);
  const pillContentRef = useRef<HTMLDivElement>(null);
  const [pillContentHeight, setPillContentHeight] = useState(0);

  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);
  const [radioOpen, setRadioOpen] = useState(false);

  // Refs for measuring expand heights
  const tldrRef = useRef<HTMLDivElement>(null);
  const opinionRef = useRef<HTMLDivElement>(null);
  const radioRef = useRef<HTMLDivElement>(null);

  const [tldrHeight, setTldrHeight] = useState(0);
  const [opinionHeight, setOpinionHeight] = useState(0);
  const [radioHeight, setRadioHeight] = useState(0);

  // ResizeObservers for smooth expand/collapse
  useEffect(() => {
    if (!tldrRef.current) return;
    const ro = new ResizeObserver(([e]) => setTldrHeight(e.contentRect.height));
    ro.observe(tldrRef.current);
    return () => ro.disconnect();
  }, [tldrExpanded]);

  useEffect(() => {
    if (!opinionRef.current) return;
    const ro = new ResizeObserver(([e]) =>
      setOpinionHeight(e.contentRect.height),
    );
    ro.observe(opinionRef.current);
    return () => ro.disconnect();
  }, [opinionExpanded]);

  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) =>
      setRadioHeight(e.contentRect.height),
    );
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [radioOpen]);

  // Measure pill content for smooth expand/collapse
  useEffect(() => {
    if (!pillContentRef.current) return;
    const ro = new ResizeObserver(([e]) =>
      setPillContentHeight(e.contentRect.height),
    );
    ro.observe(pillContentRef.current);
    return () => ro.disconnect();
  }, [pillExpanded, tldrExpanded, opinionExpanded, radioOpen]);

  // 20 waveform bars for narrower mobile viewport
  const waveformBars = useMemo(
    () =>
      Array.from(
        { length: 20 },
        (_, i) => 8 + Math.sin(i * 0.65) * 14 + Math.sin(i * 1.3) * 5,
      ),
    [],
  );

  if (!brief) return null;

  const hasAudio = !!brief.audio_url;
  const displayDuration =
    (hasAudio && brief.audio_duration_seconds) || duration;
  const progress =
    displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinion = opinionStart !== null && displayDuration > 0;
  const opinionPct = hasOpinion
    ? (opinionStart / displayDuration) * 100
    : 100;
  const inOpinion = hasOpinion && currentTime >= opinionStart;

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    if (!isPlaying) handlePlayPause();
  };

  // Split sentences for per-section preview/expand
  const tldrSentences = brief.tldr_text
    .split(/(?<=[.!?])\s+/)
    .filter(Boolean);
  const tldrPreview = tldrSentences.slice(0, 2).join(" ");
  const tldrRest = tldrSentences.slice(2).join(" ");
  const tldrHasMore = tldrRest.length > 0;

  const opinionSentences = brief.opinion_text
    ? brief.opinion_text.split(/(?<=[.!?])\s+/).filter(Boolean)
    : [];
  const opinionPreview = opinionSentences.slice(0, 2).join(" ");
  const opinionRest = opinionSentences.slice(2).join(" ");
  const opinionHasMore = opinionRest.length > 0;

  const leanLabel =
    brief.opinion_lean === "left"
      ? "Progressive"
      : brief.opinion_lean === "right"
        ? "Conservative"
        : "Pragmatic";

  const leanMod =
    brief.opinion_lean === "left"
      ? "skb-lean--left"
      : brief.opinion_lean === "right"
        ? "skb-lean--right"
        : "skb-lean--center";

  // Collapsed pill label: headline or fallback
  const pillLabel = brief.tldr_headline || "Today\u2019s brief";

  return (
    <div className="mbp" role="complementary" aria-label="Daily Brief">
      {hasAudio && (
        <audio
          ref={audioCallbackRef}
          src={brief.audio_url!}
          preload="metadata"
        />
      )}

      {/* ── Collapsed single-line pill (default) ── */}
      <button
        className={`mbp__pill${pillExpanded ? " mbp__pill--open" : ""}`}
        onClick={() => {
          hapticLight();
          setPillExpanded((v) => !v);
        }}
        type="button"
        aria-expanded={pillExpanded}
        aria-controls="mbp-content"
      >
        <ScaleIcon size={12} animation="idle" />
        <span className="mbp__pill-cmd">void --tl;dr</span>
        <span className="mbp__pill-sep" aria-hidden="true">&middot;</span>
        <span className="mbp__pill-label">{pillLabel}</span>
        <span className="mbp__pill-chevron" aria-hidden="true">&#9662;</span>
      </button>

      {/* ── Expandable content ── */}
      <div
        id="mbp-content"
        className="mbp__content"
        style={{
          height: pillExpanded ? pillContentHeight : 0,
          transition: pillExpanded
            ? "height 350ms var(--spring-snappy)"
            : "height 250ms var(--ease-out)",
        }}
      >
        <div ref={pillContentRef} className="mbp__content-inner">
          {/* ── TL;DR Section ── */}
          <section className="mbp__section" aria-label="void --tl;dr">
            <div className="mbp__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="mbp__cmd">void --tl;dr</span>
              {brief.created_at && (
                <span className="mbp__time">{timeAgo(brief.created_at)}</span>
              )}
            </div>

            {brief.tldr_headline && (
              <h3 className="mbp__hl mbp__hl--tldr">{brief.tldr_headline}</h3>
            )}

            <p className="mbp__preview mbp__preview--tldr">{tldrPreview}</p>

            {/* Inline expand */}
            <div
              className="mbp__expand"
              style={{
                height: tldrExpanded ? tldrHeight : 0,
                transition: tldrExpanded
                  ? "height 350ms var(--spring-snappy)"
                  : "height 200ms var(--ease-out)",
              }}
            >
              <div ref={tldrRef} className="mbp__expand-inner">
                <p className="mbp__expand-text mbp__expand-text--tldr">
                  {tldrRest}
                </p>
              </div>
            </div>

            {tldrHasMore && (
              <button
                className="mbp__more"
                onClick={() => {
                  hapticLight();
                  setTldrExpanded((v) => !v);
                }}
                type="button"
                aria-expanded={tldrExpanded}
              >
                {tldrExpanded ? "less" : "read more"}
              </button>
            )}
          </section>

          {/* ── Dotted rule ── */}
          {brief.opinion_text && <hr className="mbp__rule" />}

          {/* ── Opinion Section ── */}
          {brief.opinion_text && (
            <section className="mbp__section" aria-label="void --opinion">
              <div className="mbp__label">
                <ScaleIcon size={12} animation="idle" />
                <span className="mbp__cmd">void --opinion</span>
                {brief.opinion_lean && (
                  <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>
                )}
              </div>

              {brief.opinion_headline && (
                <h3 className="mbp__hl mbp__hl--opinion">
                  {brief.opinion_headline}
                </h3>
              )}

              <p className="mbp__preview mbp__preview--opinion">
                {opinionPreview}
              </p>

              {/* Inline expand */}
              <div
                className="mbp__expand"
                style={{
                  height: opinionExpanded ? opinionHeight : 0,
                  transition: opinionExpanded
                    ? "height 350ms var(--spring-snappy)"
                    : "height 200ms var(--ease-out)",
                }}
              >
                <div ref={opinionRef} className="mbp__expand-inner">
                  <p className="mbp__expand-text mbp__expand-text--opinion">
                    {opinionRest}
                  </p>
                </div>
              </div>

              {opinionHasMore && (
                <button
                  className="mbp__more"
                  onClick={() => {
                    hapticLight();
                    setOpinionExpanded((v) => !v);
                  }}
                  type="button"
                  aria-expanded={opinionExpanded}
                >
                  {opinionExpanded ? "less" : "read more"}
                </button>
              )}
            </section>
          )}

          {/* ── OnAir Pill + Radio Player ── */}
          {hasAudio && (
            <div className="mbp__onair-zone">
              <hr className="mbp__rule" />

              <div className="mbp__onair-center">
                <button
                  className={`skb__onair-btn${isPlaying ? " skb__onair-btn--active" : ""}${radioOpen ? " skb__onair-btn--open" : ""}`}
                  onClick={() => {
                    hapticConfirm();
                    setRadioOpen((v) => !v);
                    if (!isPlaying && !radioOpen) handlePlayPause();
                  }}
                  type="button"
                  aria-label={radioOpen ? "Close radio player" : "Open radio player"}
                  aria-expanded={radioOpen}
                >
                  <span className="skb__radio-waves" aria-hidden="true">
                    <span className="skb__radio-wave" />
                    <span className="skb__radio-wave" />
                    <span className="skb__radio-wave" />
                  </span>
                  {isPlaying && (
                    <span className="skb__rec-dot" aria-hidden="true" />
                  )}
                  <span className="skb__onair-label">void --onair</span>
                  {durationMin && !isPlaying && (
                    <span className="skb__onair-dur">{durationMin} min</span>
                  )}
                  {isPlaying && (
                    <span className="skb__onair-dur">
                      {formatTime(currentTime)} /{" "}
                      {formatTime(displayDuration || 0)}
                    </span>
                  )}
                </button>
              </div>

              {/* Radio player expands below the pill */}
              <div
                className="skb__radio"
                style={{
                  height: radioOpen ? radioHeight : 0,
                  transition: radioOpen
                    ? "height 400ms var(--spring-bouncy)"
                    : "height 250ms var(--ease-out)",
                }}
              >
                <div
                  ref={radioRef}
                  className={`skb__radio-inner${isPlaying ? " skb__radio-inner--live" : ""}`}
                >
                  {/* Waveform — 20 bars for mobile */}
                  <div
                    className={`skb__waveform${isPlaying ? " skb__waveform--active" : ""}`}
                    aria-hidden="true"
                  >
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
                      onClick={() => {
                        hapticMedium();
                        handlePlayPause();
                      }}
                      type="button"
                      aria-label={isPlaying ? "Pause" : "Play"}
                    >
                      <span aria-hidden="true">
                        {isPlaying ? "\u275A\u275A" : "\u25B6"}
                      </span>
                    </button>
                    <div className="skb__transport-info">
                      <div className="skb__transport-label">
                        <ScaleIcon
                          size={12}
                          animation={isPlaying ? "analyzing" : "idle"}
                        />
                        <span className="skb__transport-cmd">void --onair</span>
                        {isPlaying && (
                          <span
                            className="skb__rec-dot skb__rec-dot--lg"
                            aria-label="Recording"
                          />
                        )}
                      </div>
                      <div className="skb__transport-voices">
                        <span>Voice A: the facts</span>
                        <span
                          className="skb__transport-dot"
                          aria-hidden="true"
                        />
                        <span>Voice B: the questions</span>
                      </div>
                    </div>
                    <span className="skb__transport-time">
                      {formatTime(currentTime)} /{" "}
                      {formatTime(displayDuration || 0)}
                    </span>
                  </div>

                  {/* Seek bar with section skip */}
                  <div className="skb__radio-seek">
                    <div className="skb__radio-sections">
                      <button
                        className={`skb__radio-sec${!inOpinion ? " skb__radio-sec--active" : ""}`}
                        onClick={() => seekTo(0)}
                        type="button"
                        style={
                          hasOpinion
                            ? { width: `${opinionPct}%` }
                            : { width: "100%" }
                        }
                      >
                        News
                      </button>
                      {hasOpinion && (
                        <button
                          className={`skb__radio-sec${inOpinion ? " skb__radio-sec--active" : ""}`}
                          onClick={() => seekTo(opinionStart)}
                          type="button"
                          style={{ width: `${100 - opinionPct}%` }}
                        >
                          Opinion
                        </button>
                      )}
                    </div>
                    <div className="skb__radio-bar-wrap">
                      <div className="skb__radio-bar">
                        <div
                          className="skb__radio-fill"
                          style={{ width: `${progress}%` }}
                        />
                        {hasOpinion && (
                          <span
                            className="skb__radio-mark"
                            style={{ left: `${opinionPct}%` }}
                            aria-hidden="true"
                          />
                        )}
                      </div>
                      <input
                        type="range"
                        className="skb__radio-input"
                        min={0}
                        max={displayDuration || 100}
                        value={currentTime}
                        step={0.5}
                        onChange={handleSeek}
                        aria-label="Seek position"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
