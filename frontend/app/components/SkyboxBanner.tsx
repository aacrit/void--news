"use client";

import { useState, useRef, useEffect, useMemo, useCallback } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

type ExpandedSection = null | "tldr" | "opinion";

export default function SkyboxBanner({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
  } = state;

  const [expandedSection, setExpandedSection] = useState<ExpandedSection>(null);
  const [onairExpanded, setOnairExpanded] = useState(false);
  const [announcement, setAnnouncement] = useState("");
  const radioRef = useRef<HTMLDivElement>(null);
  const [radioHeight, setRadioHeight] = useState(0);

  // Focus management refs
  const collapseRef = useRef<HTMLButtonElement>(null);
  const expandTldrRef = useRef<HTMLButtonElement>(null);
  const expandOpinionRef = useRef<HTMLButtonElement>(null);
  const prevSectionRef = useRef<ExpandedSection>(null);

  useEffect(() => {
    if (!radioRef.current) return;
    const ro = new ResizeObserver(([e]) => {
      const h = e.borderBoxSize?.[0]?.blockSize ?? e.target.getBoundingClientRect().height;
      setRadioHeight(h);
    });
    ro.observe(radioRef.current);
    return () => ro.disconnect();
  }, [onairExpanded]);

  useEffect(() => {
    const main = document.querySelector('.page-main');
    if (!main) return;
    if (isPlaying) {
      main.classList.add('page-main--audio-playing');
    } else {
      main.classList.remove('page-main--audio-playing');
    }
    return () => main.classList.remove('page-main--audio-playing');
  }, [isPlaying]);

  useEffect(() => {
    const prev = prevSectionRef.current;
    if (expandedSection && !prev) {
      requestAnimationFrame(() => collapseRef.current?.focus());
    } else if (!expandedSection && prev) {
      requestAnimationFrame(() => {
        if (prev === "tldr") expandTldrRef.current?.focus();
        else expandOpinionRef.current?.focus();
      });
    }
    prevSectionRef.current = expandedSection;
  }, [expandedSection]);

  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => Math.min(32, 10 + Math.sin(i * 0.55) * 16 + Math.sin(i * 1.3) * 6)),
  []);

  if (!brief) return (
    <div className="skb skb--compact anim-cold-open-skybox" role="complementary" aria-label="Daily Brief">
      <div className="skb__compact">
        <div className="skb__compact-header">
          <div className="skb__compact-cols">
            <div className="skb__compact-col">
              <div className="skb__compact-label">
                <LogoIcon size={16} animation="analyzing" />
                <span className="skb__compact-human">News Brief</span>
                <span className="skb__compact-cmd">void --tl;dr</span>
              </div>
              <span className="skb__compact-loading">Loading today&rsquo;s brief&hellip;</span>
            </div>
          </div>
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

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative" : "Pragmatic";
  const leanMod = brief.opinion_lean === "left" ? "skb-lean--left"
    : brief.opinion_lean === "right" ? "skb-lean--right" : "skb-lean--center";

  const isCompact = expandedSection === null;

  const toggleSection = useCallback((section: "tldr" | "opinion") => {
    hapticLight();
    setExpandedSection(prev => {
      const next = prev === section ? null : section;
      if (next) {
        setAnnouncement(`Daily brief expanded, showing ${next === "tldr" ? "news brief" : "editorial opinion"}.`);
      } else {
        setAnnouncement("Daily brief collapsed.");
      }
      return next;
    });
  }, []);

  const collapseAll = useCallback(() => {
    hapticLight();
    setExpandedSection(null);
    setAnnouncement("Daily brief collapsed.");
  }, []);

  const toggleOnair = useCallback(() => {
    hapticConfirm();
    setOnairExpanded(v => !v);
  }, []);

  // ── Radio Player ──
  const radioPlayer = (
    <div className="skb__radio" inert={!onairExpanded ? true : undefined} style={{
      height: onairExpanded ? radioHeight : 0,
      transition: onairExpanded
        ? "height 450ms var(--ease-unfold, ease)"
        : "height 220ms var(--ease-refold, ease)",
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
  );

  // ── OnAir pill ──
  const onairPill = (
    <button
      className={`skb__onair-pill${isPlaying ? " skb__onair-pill--active" : ""}${onairExpanded ? " skb__onair-pill--open" : ""}`}
      onClick={toggleOnair}
      type="button"
      aria-label={onairExpanded ? "Close audio player" : "Open audio player"}
      aria-expanded={onairExpanded}
    >
      {isPlaying && <span className="skb__rec-dot" aria-hidden="true" />}
      <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "none"} />
      <span className="skb__onair-cmd">void --onair</span>
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
      <span className={`skb__onair-caret${onairExpanded ? " skb__onair-caret--up" : ""}`} aria-hidden="true">&#9662;</span>
    </button>
  );

  const rootClass = [
    "skb",
    "anim-cold-open-skybox",
    isCompact ? "skb--compact" : "skb--section-open",
    expandedSection ? `skb--show-${expandedSection}` : "",
    onairExpanded ? "skb--onair-open" : "",
  ].filter(Boolean).join(" ");

  return (
    <>
      {hasAudio && <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />}
      <div aria-live="polite" className="sr-only">{announcement}</div>

      <div className={rootClass} role="complementary" aria-label="Daily Brief">

        {/* ── COMPACT MODE ── */}
        {isCompact && (
          <div className="skb__compact">
            {/* Header row: columns + OnAir pill (top-right) */}
            <div className="skb__compact-header">
              <div className={`skb__compact-cols${!brief.opinion_text ? " skb__compact-cols--single" : ""}`}>
                {/* TL;DR column */}
                <div className="skb__compact-col skb__compact-col--tldr">
                  <div className="skb__compact-label">
                    <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                    <span className="skb__compact-human">News Brief</span>
                    <span className="skb__compact-cmd">void --tl;dr</span>
                    {brief.created_at && <span className="skb__compact-time">{timeAgo(brief.created_at)}</span>}
                  </div>
                  {brief.tldr_headline && <h3 className="skb__compact-hl skb__compact-hl--tldr">{brief.tldr_headline}</h3>}
                  <p className="skb__compact-preview skb__compact-preview--tldr">{brief.tldr_text}</p>
                  <button
                    ref={expandTldrRef}
                    className="skb__compact-expand"
                    onClick={() => toggleSection("tldr")}
                    type="button"
                    aria-label="Expand news brief"
                  >
                    <span aria-hidden="true">&#9662;</span>
                  </button>
                </div>

                {/* Opinion column */}
                {brief.opinion_text && (
                  <div className="skb__compact-col skb__compact-col--opinion">
                    <div className="skb__compact-label">
                      <LogoIcon size={16} animation="idle" className="skb__compact-logo" />
                      <span className="skb__compact-human">Editorial</span>
                      <span className="skb__compact-cmd">void --opinion</span>
                      {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                    </div>
                    {brief.opinion_headline && <h3 className="skb__compact-hl skb__compact-hl--opinion">{brief.opinion_headline}</h3>}
                    <p className="skb__compact-preview skb__compact-preview--opinion">{brief.opinion_text}</p>
                    <button
                      ref={expandOpinionRef}
                      className="skb__compact-expand"
                      onClick={() => toggleSection("opinion")}
                      type="button"
                      aria-label="Expand editorial opinion"
                    >
                      <span aria-hidden="true">&#9662;</span>
                    </button>
                  </div>
                )}
              </div>

              {/* OnAir pill — top right */}
              <div className="skb__compact-onair">
                {onairPill}
              </div>
            </div>

            {/* OnAir expanded radio (pushes content below) */}
            {radioPlayer}
          </div>
        )}

        {/* ── EXPANDED MODE ── */}
        {!isCompact && (
          <>
            {/* Top bar: OnAir pill (left) + other section chip (right) + collapse */}
            <div className="skb__topbar">
              <div className="skb__topbar-left">
                {onairPill}
              </div>

              <div className="skb__topbar-right">
                {expandedSection === "tldr" && brief.opinion_text && (
                  <button
                    className="skb__topbar-chip"
                    onClick={() => toggleSection("opinion")}
                    type="button"
                    aria-label="Switch to editorial"
                  >
                    <LogoIcon size={12} animation="none" className="skb__topbar-chip-logo" />
                    <span className="skb__topbar-chip-human">Editorial</span>
                    <span className="skb__topbar-chip-cmd">void --opinion</span>
                    {brief.opinion_lean && <span className={`skb__lean-badge skb__lean-badge--sm ${leanMod}`}>{leanLabel}</span>}
                    <span className="skb__topbar-chip-caret" aria-hidden="true">&#9662;</span>
                  </button>
                )}
                {expandedSection === "opinion" && (
                  <button
                    className="skb__topbar-chip"
                    onClick={() => toggleSection("tldr")}
                    type="button"
                    aria-label="Switch to news brief"
                  >
                    <LogoIcon size={12} animation="none" className="skb__topbar-chip-logo" />
                    <span className="skb__topbar-chip-human">News Brief</span>
                    <span className="skb__topbar-chip-cmd">void --tl;dr</span>
                    <span className="skb__topbar-chip-caret" aria-hidden="true">&#9662;</span>
                  </button>
                )}

                <button
                  ref={collapseRef}
                  className="skb__topbar-collapse"
                  onClick={collapseAll}
                  type="button"
                  aria-label="Collapse daily brief"
                >
                  <span aria-hidden="true">&#9652;</span>
                </button>
              </div>
            </div>

            {/* OnAir expanded radio */}
            {radioPlayer}

            {/* Expanded section content */}
            <div className="skb__section-content">
              {expandedSection === "tldr" && (
                <div className="skb__section skb__section--tldr">
                  <div className="skb__section-label">
                    <LogoIcon size={18} animation="idle" />
                    <span className="skb__section-label-human">News Brief</span>
                    <span className="skb__section-label-cmd">void --tl;dr</span>
                    {brief.created_at && <span className="skb__section-label-time">{timeAgo(brief.created_at)}</span>}
                  </div>
                  {brief.tldr_headline && <h3 className="skb__section-hl skb__section-hl--tldr">{brief.tldr_headline}</h3>}
                  <div className="skb__section-body skb__section-body--tldr">
                    {brief.tldr_text.split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
                </div>
              )}

              {expandedSection === "opinion" && (
                <div className="skb__section skb__section--opinion">
                  <div className="skb__section-label">
                    <LogoIcon size={18} animation="idle" />
                    <span className="skb__section-label-human">Editorial</span>
                    <span className="skb__section-label-cmd">void --opinion</span>
                    {brief.opinion_lean && <span className={`skb__lean-badge ${leanMod}`}>{leanLabel}</span>}
                  </div>
                  {brief.opinion_headline && <h3 className="skb__section-hl skb__section-hl--opinion">{brief.opinion_headline}</h3>}
                  <div className="skb__section-body skb__section-body--opinion">
                    {(brief.opinion_text || "").split(/\n\n+/).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </>
  );
}
