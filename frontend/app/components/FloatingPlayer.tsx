"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import ScaleIcon from "./ScaleIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";

const PlayIcon = () => (
  <svg width="11" height="13" viewBox="0 0 11 13" fill="currentColor" aria-hidden="true">
    <path d="M1 1.5v10l9-5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="2.5" height="10" rx="0.5" />
    <rect x="6.5" y="1" width="2.5" height="10" rx="0.5" />
  </svg>
);

/* ---- Host lookup: maps Gemini voice IDs to newsroom personas ---- */
const HOSTS: Record<string, { name: string; trait: string }> = {
  Charon:      { name: "The Correspondent",  trait: "Measured authority, lets facts land" },
  Kore:        { name: "The Structuralist",   trait: "Sees systems, connects policy to outcome" },
  Gacrux:      { name: "The Pragmatist",      trait: "Institutional memory, fiscal instinct" },
  Orus:        { name: "The Investigator",    trait: "Follows the money, the paper trail" },
  Achernar:    { name: "The Realist",         trait: "Challenges consensus with data" },
  Sadaltager:  { name: "The Editor",          trait: "Synthesizes, contextualizes, finds the arc" },
};

function parseHosts(audioVoice: string | null | undefined): { name: string; trait: string }[] {
  if (!audioVoice) return [];
  return audioVoice.split("+").map(id => HOSTS[id.trim()]).filter(Boolean);
}

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

type PlayerView = "compact" | "expanded" | "broadcast";

export default function FloatingPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible,
  } = state;

  const [view, setView] = useState<PlayerView>("compact");
  const [closing, setClosing] = useState(false);
  const playerRef = useRef<HTMLDivElement>(null);

  const waveformBars = useMemo(() =>
    Array.from({ length: 24 }, (_, i) => Math.min(28, 8 + Math.sin(i * 0.6) * 14 + Math.sin(i * 1.4) * 5)),
  []);

  /* ---- Swipe-down gesture ---- */
  const dragYRef = useRef<{ startY: number; current: number } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  /* ---- Derived host/episode metadata ---- */
  const hosts = useMemo(() => parseHosts(brief?.audio_voice), [brief?.audio_voice]);
  const editionLabel = brief?.edition ? brief.edition.charAt(0).toUpperCase() + brief.edition.slice(1) : "World";
  const episodeDate = brief?.created_at ? formatDate(brief.created_at) : "";

  /* ---- Desktop left-pane: push page canvas right when broadcast is open ---- */
  useEffect(() => {
    if (view === "broadcast" && !closing) {
      document.documentElement.setAttribute("data-onair-pane", "");
    } else {
      document.documentElement.removeAttribute("data-onair-pane");
    }
    return () => document.documentElement.removeAttribute("data-onair-pane");
  }, [view, closing]);

  if (!brief || !brief.audio_url || !isPlayerVisible) return null;

  const displayDuration = brief.audio_duration_seconds || duration;
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

  const toggleExpand = () => {
    hapticLight();
    setView(v => v === "compact" ? "expanded" : "compact");
  };

  const openBroadcast = () => {
    hapticLight();
    setView("broadcast");
  };

  const closeBroadcast = () => {
    hapticLight();
    const isDesktop = typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;
    if (isDesktop) {
      setClosing(true);
      setTimeout(() => { setClosing(false); setView("compact"); }, 300);
    } else {
      setView("expanded");
    }
  };

  const dismiss = () => {
    hapticLight();
    const isDesktop = typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;
    if (view === "broadcast" && isDesktop) {
      setClosing(true);
      setTimeout(() => { setClosing(false); setView("compact"); setPlayerVisible(false); }, 300);
    } else {
      setPlayerVisible(false);
      setView("compact");
    }
  };

  const handleBarTouchStart = (e: React.TouchEvent) => {
    dragYRef.current = { startY: e.touches[0].clientY, current: 0 };
  };

  const handleBarTouchMove = (e: React.TouchEvent) => {
    if (!dragYRef.current) return;
    const dy = e.touches[0].clientY - dragYRef.current.startY;
    if (dy > 0) {
      dragYRef.current.current = dy;
      setDragOffset(dy * 0.6);
    }
  };

  const handleBarTouchEnd = () => {
    if (!dragYRef.current) return;
    const dy = dragYRef.current.current;
    dragYRef.current = null;
    setDragOffset(0);
    if (dy > 80) {
      hapticLight();
      if (view === "broadcast") setView("expanded");
      else setView("compact");
    }
  };

  /* ---- Shared transport controls ---- */
  const renderTransport = () => (
    <div className="fp__transport">
      <button className="fp__skip" onClick={() => skipBackward()} type="button" aria-label="Back 15s">-15</button>
      <button
        className={`fp__play-lg${isPlaying ? " fp__play-lg--active" : ""}`}
        onClick={() => { hapticMedium(); handlePlayPause(); }}
        type="button" aria-label={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? <PauseIcon /> : <PlayIcon />}
      </button>
      <button className="fp__skip" onClick={() => skipForward()} type="button" aria-label="Forward 15s">+15</button>
    </div>
  );

  /* ---- Shared seek bar ---- */
  const renderSeek = () => (
    <div className="fp__seek">
      <div className="fp__seek-sections">
        <button className={`fp__seek-sec${!inOpinion ? " fp__seek-sec--active" : ""}`}
          onClick={() => seekTo(0)} type="button">News</button>
        {hasOpinionSection && (
          <button className={`fp__seek-sec${inOpinion ? " fp__seek-sec--active" : ""}`}
            onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
            type="button">Opinion</button>
        )}
      </div>
      <div className="fp__seek-bar-wrap">
        <div className="fp__seek-bar">
          <div className="fp__seek-buffer" style={{ width: `${buffered}%` }} />
          <div className="fp__seek-fill" style={{ width: `${progress}%` }} />
          {hasOpinionSection && <span className="fp__seek-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
        </div>
        <input type="range" className="fp__seek-input" min={0} max={displayDuration || 100}
          value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek"
          aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
      </div>
      <div className="fp__seek-time">
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(displayDuration || 0)}</span>
      </div>
    </div>
  );

  return (
    <div
      ref={playerRef}
      className={[
        "fp",
        view === "compact" ? "fp--compact" : view === "expanded" ? "fp--expanded" : "fp--broadcast",
        isPlaying ? "fp--playing" : "",
        closing ? "fp--closing" : "",
      ].filter(Boolean).join(" ")}
      style={dragOffset > 0 ? { transform: `translateY(${dragOffset}px)`, transition: "none" } : undefined}
      role="region"
      aria-label="Audio player"
    >
      {/* ── COMPACT PILL ── */}
      {view === "compact" && (
        <div className="fp__pill" onClick={toggleExpand} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); toggleExpand(); } }}>
          <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} className="fp__logo" />

          {isPlaying && (
            <div className="fp__pill-eq" aria-hidden="true">
              <div className="fp__pill-eq-bar" style={{ height: 10 }} />
              <div className="fp__pill-eq-bar" style={{ height: 14 }} />
              <div className="fp__pill-eq-bar" style={{ height: 8 }} />
              <div className="fp__pill-eq-bar" style={{ height: 12 }} />
            </div>
          )}

          <button
            className={`fp__play${isPlaying ? " fp__play--active" : ""}`}
            onClick={(e) => { e.stopPropagation(); hapticConfirm(); handlePlayPause(); }}
            type="button"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
          </button>

          <div className="fp__info">
            {isPlaying && <span className="fp__rec-dot" aria-hidden="true" />}
            <span className="fp__title">void --onair</span>
            <span className="fp__section">{inOpinion ? "Opinion" : "News"}</span>
          </div>

          <span className="fp__time">
            {isPlaying || currentTime > 0 ? formatTime(currentTime) : durationMin ? `${durationMin}m` : ""}
          </span>

          <div className="fp__mini-progress" aria-hidden="true">
            <div className="fp__mini-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* ── EXPANDED CONSOLE ── */}
      {view === "expanded" && (
        <div
          className="fp__bar"
          onTouchStart={handleBarTouchStart}
          onTouchMove={handleBarTouchMove}
          onTouchEnd={handleBarTouchEnd}
        >
          <div className="fp__drag-indicator" aria-hidden="true" />

          <div className="fp__bar-header">
            <div className="fp__bar-brand">
              <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} />
              <span className="fp__bar-title">void --onair</span>
              {audioError && <span className="fp__bar-error">Unavailable</span>}
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__minimize" onClick={toggleExpand} type="button" aria-label="Minimize player">
                <span aria-hidden="true">&#9662;</span>
              </button>
              <button className="fp__dismiss" onClick={dismiss} type="button" aria-label="Close player">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          {/* Metadata row */}
          <div className="fp__meta">
            {hosts.length > 0 && (
              <span className="fp__meta-hosts">{hosts.slice(0, 2).map(h => h.name).join(" + ")}</span>
            )}
            <span className="fp__meta-sep" aria-hidden="true" />
            <span className="fp__meta-edition">{editionLabel}</span>
            {durationMin && <span className="fp__meta-duration">{durationMin} min</span>}
          </div>

          {/* Waveform */}
          <div className={`fp__waveform${isPlaying ? " fp__waveform--active" : ""}`} aria-hidden="true">
            {waveformBars.map((h, i) => (
              <div key={i} className="fp__waveform-bar" style={{ height: `${h}px`, animationDelay: `${i * 50}ms` }} />
            ))}
          </div>

          {renderTransport()}
          {renderSeek()}

          {/* Episode details trigger */}
          <button className="fp__episode-btn" onClick={openBroadcast} type="button">
            <span>Episode details</span>
            <span className="fp__episode-btn-arrow" aria-hidden="true">&#9652;</span>
          </button>
        </div>
      )}

      {/* ── BROADCAST PANEL ── */}
      {view === "broadcast" && (
        <div
          className="fp__broadcast"
          onTouchStart={handleBarTouchStart}
          onTouchMove={handleBarTouchMove}
          onTouchEnd={handleBarTouchEnd}
        >
          <div className="fp__drag-indicator" aria-hidden="true" />

          {/* VU arc motif — decorative 120° arc behind header */}
          <svg className="fp__vu-arc" viewBox="0 0 200 60" aria-hidden="true">
            <path d="M30 55 A70 70 0 0 1 170 55" fill="none" stroke="currentColor" strokeWidth="1.5" />
            {/* Frequency hash marks */}
            {Array.from({ length: 9 }, (_, i) => {
              const angle = Math.PI - (Math.PI * (i + 1)) / 10;
              const cx = 100 + 70 * Math.cos(angle);
              const cy = 55 - 70 * Math.sin(angle);
              const dx = 4 * Math.cos(angle);
              const dy = -4 * Math.sin(angle);
              return <line key={i} x1={cx} y1={cy} x2={cx + dx} y2={cy + dy} stroke="currentColor" strokeWidth="1" />;
            })}
          </svg>

          {/* Broadcast header */}
          <div className="fp__bcast-header">
            <div className="fp__bcast-brand">
              <ScaleIcon size={22} animation={isPlaying ? "broadcast" : "idle"} />
              <div className="fp__bcast-title-group">
                <span className="fp__bcast-void">void</span>
                <span className="fp__bcast-cmd">--onair</span>
              </div>
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__minimize" onClick={closeBroadcast} type="button" aria-label="Collapse to console">
                <span aria-hidden="true">&#9662;</span>
              </button>
              <button className="fp__dismiss" onClick={dismiss} type="button" aria-label="Close player">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          {/* Episode dateline */}
          <div className="fp__bcast-dateline">
            <span className="fp__bcast-edition">{editionLabel} Edition</span>
            {episodeDate && <span className="fp__bcast-date">{episodeDate}</span>}
            {durationMin && <span className="fp__bcast-duration">{durationMin} min</span>}
          </div>

          {/* Host pair card */}
          {hosts.length > 0 && (
            <div className="fp__bcast-hosts">
              {hosts.slice(0, 2).map((host, i) => (
                <div key={i} className="fp__bcast-host">
                  <span className="fp__bcast-host-tag">{i === 0 ? "A" : "B"}</span>
                  <div className="fp__bcast-host-info">
                    <span className="fp__bcast-host-name">{host.name}</span>
                    <span className="fp__bcast-host-trait">{host.trait}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {renderTransport()}
          {renderSeek()}

          {/* Episode content */}
          <div className="fp__bcast-content">
            <div className="fp__bcast-section">
              <span className="fp__bcast-section-label">Episode Summary</span>
              <p className="fp__bcast-text">{brief.tldr_text}</p>
            </div>

            {brief.opinion_text && (
              <>
                {/* Dotted firewall — same convention as SkyboxBanner */}
                <div className="fp__bcast-firewall" aria-hidden="true" />
                <div className="fp__bcast-section">
                  <div className="fp__bcast-section-head">
                    <span className="fp__bcast-section-label">Editorial</span>
                    {brief.opinion_lean && (
                      <span className={`fp__bcast-lean fp__bcast-lean--${brief.opinion_lean}`}>
                        {brief.opinion_lean}
                      </span>
                    )}
                  </div>
                  <p className="fp__bcast-text">{brief.opinion_text}</p>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
