"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import type { EpisodeMeta } from "./AudioProvider";
import { CaretRight } from "@phosphor-icons/react";
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

function formatEpisodeDate(dateStr: string): string {
  const d = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatEpisodeTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true });
}

type PlayerView = "compact" | "expanded" | "broadcast";

export default function FloatingPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible,
    previousEpisodes, loadEpisode,
  } = state;

  const [view, setView] = useState<PlayerView>("compact");
  const [closing, setClosing] = useState(false);

  // Memoize episode grouping — avoids re-running date formatting on every
  // currentTime tick (~4/s) since previousEpisodes only changes on edition switch.
  const groupedEpisodes = useMemo(() => {
    if (previousEpisodes.length <= 1) return null;
    const grouped = new Map<string, typeof previousEpisodes>();
    for (const ep of previousEpisodes) {
      const dayKey = new Date(ep.created_at).toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
      if (!grouped.has(dayKey)) grouped.set(dayKey, []);
      grouped.get(dayKey)!.push(ep);
    }
    return grouped;
  }, [previousEpisodes]);

  // On mobile, skip compact pill (hidden via CSS) — open expanded directly
  useEffect(() => {
    if (!isPlayerVisible) return;
    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    if (isMobile && view === "compact") {
      setView("expanded");
    }
  }, [isPlayerVisible, view]);
  const playerRef = useRef<HTMLDivElement>(null);

  /* ---- VU Meter: 16 bars, CSS-driven, scales via height ---- */
  const VU_BARS = 16;
  const vuBars = useMemo(() => Array.from({ length: VU_BARS }, (_, i) => i), []);

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

  /* ---- Escape key dismisses expanded/broadcast views ---- */
  useEffect(() => {
    if (view === "compact") return;
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        if (view === "broadcast") {
          const isDesktop = window.matchMedia("(min-width: 1024px)").matches;
          if (isDesktop) {
            setClosing(true);
            setTimeout(() => { setClosing(false); setView("compact"); }, 300);
          } else {
            setView("compact");
          }
        } else {
          const isMobile = window.matchMedia("(max-width: 767px)").matches;
          if (isMobile) setPlayerVisible(false);
          else setView("compact");
        }
      }
    };
    document.addEventListener("keydown", handleEsc);
    return () => document.removeEventListener("keydown", handleEsc);
  }, [view, setPlayerVisible]);

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

  /* Flow: pill → pane (direct). Floating is an option from pane. */
  const openPane = () => {
    hapticLight();
    setView("broadcast");
  };

  const closePane = () => {
    hapticLight();
    const isDesktop = typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;
    if (isDesktop) {
      setClosing(true);
      setTimeout(() => { setClosing(false); setView("compact"); }, 300);
    } else {
      setView("compact");
    }
  };

  const detachToFloating = () => {
    hapticLight();
    const isDesktop = typeof window !== "undefined" && window.matchMedia("(min-width: 1024px)").matches;
    if (isDesktop) {
      setClosing(true);
      setTimeout(() => { setClosing(false); setView("expanded"); }, 300);
    } else {
      setView("expanded");
    }
  };

  const closeFloating = () => {
    hapticLight();
    const isMobile = typeof window !== "undefined" && window.matchMedia("(max-width: 767px)").matches;
    if (isMobile) {
      // On mobile, compact is hidden — dismiss player entirely
      setPlayerVisible(false);
    } else {
      setView("compact");
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
      if (view === "broadcast") {
        setView("expanded");
      } else {
        // On mobile, dismiss entirely; on desktop, go to compact
        const isMobile = window.matchMedia("(max-width: 767px)").matches;
        if (isMobile) {
          setPlayerVisible(false);
        } else {
          setView("compact");
        }
      }
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
        <div className="fp__pill" onClick={openPane} role="button" tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openPane(); } }}>
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
              <span className={`fp__status${isPlaying ? " fp__status--live" : ""}`}>
                <span className="fp__status-dot" />
                <span className="fp__status-label">{isPlaying ? "ON AIR" : "OFFLINE"}</span>
              </span>
              {audioError && <span className="fp__bar-error">Unavailable</span>}
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__minimize" onClick={closeFloating} type="button" aria-label="Minimize player">
                <CaretRight size={14} weight="bold" className="fp__caret fp__caret--down" />
              </button>
              <button className="fp__dismiss" onClick={dismiss} type="button" aria-label="Close player">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          {/* VU meter — CSS-driven audio visualization */}
          <div className={`fp__vu${isPlaying ? " fp__vu--active" : ""}`} aria-hidden="true">
            {vuBars.map(i => <span key={i} className="fp__vu-bar" style={{ animationDelay: `${i * 60}ms` }} />)}
          </div>

          {renderTransport()}
          {renderSeek()}
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

          {/* VU arc motif — decorative broadcast gauge behind header */}
          <svg className="fp__vu-arc" viewBox="0 0 200 60" aria-hidden="true">
            <path d="M30 55 A70 70 0 0 1 170 55" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M45 55 A55 55 0 0 1 155 55" fill="none" stroke="currentColor" strokeWidth="0.75" opacity="0.5" />
            {/* Graduated hash marks — longer at extremes and center */}
            {Array.from({ length: 9 }, (_, i) => {
              const angle = Math.PI - (Math.PI * (i + 1)) / 10;
              const cx = 100 + 70 * Math.cos(angle);
              const cy = 55 - 70 * Math.sin(angle);
              const len = (i === 0 || i === 4 || i === 8) ? 6 : 4;
              const dx = len * Math.cos(angle);
              const dy = -len * Math.sin(angle);
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
              <span className={`fp__status${isPlaying ? " fp__status--live" : ""}`}>
                <span className="fp__status-dot" />
                <span className="fp__status-label">{isPlaying ? "ON AIR" : "OFFLINE"}</span>
              </span>
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__detach" onClick={detachToFloating} type="button" aria-label="Detach to floating player"
                title="Floating player">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" aria-hidden="true">
                  <rect x="1" y="5" width="8" height="8" rx="1.5" />
                  <path d="M5 5V3a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4a2 2 0 0 1-2 2H9" />
                </svg>
              </button>
              <button className="fp__minimize" onClick={closePane} type="button" aria-label="Minimize to pill">
                <CaretRight size={14} weight="bold" className="fp__caret fp__caret--down" />
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

          {/* VU meter — hero element in broadcast pane */}
          <div className={`fp__vu fp__vu--hero${isPlaying ? " fp__vu--active" : ""}`} aria-hidden="true">
            {vuBars.map(i => <span key={i} className="fp__vu-bar" style={{ animationDelay: `${i * 60}ms` }} />)}
          </div>

          {renderTransport()}
          {renderSeek()}

          {/* Episode notes — collapsed by default, "Read more" disclosure */}
          <details className="fp__bcast-details">
            <summary className="fp__bcast-summary">
              <span>Episode notes</span>
              <CaretRight size={12} weight="bold" className="fp__caret fp__bcast-summary-arrow" />
            </summary>
            <div className="fp__bcast-content">
              <div className="fp__bcast-section">
                <span className="fp__bcast-section-label">Summary</span>
                <p className="fp__bcast-text">{brief.tldr_text}</p>
              </div>

              {brief.opinion_text && (
                <>
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
          </details>

          {/* Previous Episodes — playlist with news/opinion separation */}
          {groupedEpisodes && (
              <details className="fp__bcast-details fp__playlist">
                <summary className="fp__bcast-summary">
                  <span>Previous episodes</span>
                  <CaretRight size={12} weight="bold" className="fp__caret fp__bcast-summary-arrow" />
                </summary>
                <div className="fp__playlist-wrap">
                  {(() => { let ti = 0; return Array.from(groupedEpisodes.entries()).map(([dayLabel, eps]) => (
                    <div key={dayLabel} className="fp__playlist-day">
                      <div className="fp__playlist-day-label" style={{ '--fp-track-i': ti++ } as React.CSSProperties}>{dayLabel}</div>
                      {eps.map((ep) => {
                        const isCurrent = brief.audio_url === ep.audio_url;
                        const epDuration = ep.audio_duration_seconds ? Math.ceil(ep.audio_duration_seconds / 60) : null;
                        const epHosts = parseHosts(ep.audio_voice);
                        const timeStr = formatEpisodeTime(ep.created_at);
                        const hasOpinion = !!ep.opinion_text;
                        return (
                          <button
                            key={ep.id}
                            className={`fp__track${isCurrent ? " fp__track--current" : ""}`}
                            style={{ '--fp-track-i': ti++ } as React.CSSProperties}
                            onClick={() => { if (!isCurrent) { hapticConfirm(); loadEpisode(ep); } }}
                            type="button"
                            aria-current={isCurrent ? "true" : undefined}
                            disabled={isCurrent}
                          >
                            <div className="fp__track-num" aria-hidden="true">
                              {isCurrent && isPlaying ? (
                                <span className="fp__track-eq">
                                  <span /><span /><span />
                                </span>
                              ) : (
                                <PlayIcon />
                              )}
                            </div>
                            <div className="fp__track-body">
                              <div className="fp__track-row">
                                <span className="fp__track-label">News</span>
                                <span className="fp__track-hl">
                                  {ep.tldr_headline || "Daily Brief"}
                                </span>
                              </div>
                              {hasOpinion && (
                                <div className="fp__track-row fp__track-row--opinion">
                                  <span className="fp__track-label">Opinion</span>
                                  <span className="fp__track-hl">
                                    {ep.opinion_headline || "Editorial"}
                                  </span>
                                  {ep.opinion_lean && (
                                    <span className={`fp__track-lean fp__track-lean--${ep.opinion_lean}`}>
                                      {ep.opinion_lean[0].toUpperCase()}
                                    </span>
                                  )}
                                </div>
                              )}
                              <div className="fp__track-sub">
                                <span>{timeStr}</span>
                                {epDuration && <span>{epDuration} min</span>}
                                {epHosts.length > 0 && (
                                  <span>{epHosts.map(h => h.name).join(" & ")}</span>
                                )}
                              </div>
                            </div>
                            {isCurrent && <span className="fp__track-badge">Now playing</span>}
                          </button>
                        );
                      })}
                    </div>
                  )); })()}
                </div>
              </details>
          )}
        </div>
      )}
    </div>
  );
}
