"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { CaretRight } from "@phosphor-icons/react";
import { useAudio } from "./AudioProvider";
import ScaleIcon from "./ScaleIcon";
import VuMeter from "./broadcast/VuMeter";
import { hapticConfirm, hapticLight, hapticMedium } from "../lib/haptics";
import { splitBriefParagraphs } from "../lib/briefText";
import {
  chapterKindLabel,
  chapterMarks,
  findOpinionIndex,
  formatChapterTime,
} from "../lib/chapters";

/* ---------------------------------------------------------------------------
   OnAirPanel: the player opens where the reader is.

   Pressing On Air used to take the page away. A reader three screens into a
   story, or halfway down the Weekly, lost their place to reach a transport
   that was already on screen as a pill. This panel is the same console, opened
   beside the page instead of in place of it: right-anchored from 1024px,
   a bottom sheet below that, full screen on a phone.

   /onair is still a real page with its own URL, metadata and <h1>. The panel
   is chrome; the page is a destination. What they show differs on purpose:
   the PAGE's subject is today's broadcast whoever owns the element, and the
   PANEL's subject is whatever is playing. A page that renamed itself after a
   documentary would be the same lie this whole change removed.

   A dialog, not a div: aria-modal, Escape, a Tab trap, focus restored to
   whatever opened it, and a throwaway history entry so the back gesture
   closes the panel instead of leaving the route. The mechanics are
   MobileSidePanel's, including the reason its close goes through
   history.back() rather than calling onClose directly.
   --------------------------------------------------------------------------- */

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

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "long", day: "numeric", year: "numeric",
  });
}

function formatEpisodeTime(dateStr: string): string {
  return new Date(dateStr).toLocaleTimeString("en-US", {
    hour: "numeric", minute: "2-digit", hour12: true,
  });
}

export default function OnAirPanel() {
  const {
    brief, nowPlaying, isPlaying, currentTime, duration, buffered, audioError,
    handlePlayPause, handleSeek, seekTo, skipForward, skipBackward,
    playbackSpeed, cycleSpeed,
    isPanelOpen, setPanelOpen, setPlayerVisible,
    previousEpisodes, loadEpisode,
    chapters, currentChapterIndex, seekToChapter,
  } = useAudio();

  const panelRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const wasOpenRef = useRef(false);
  const historyPushedRef = useRef(false);
  const dragRef = useRef<{ startY: number; current: number } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

  const open = isPanelOpen && !!nowPlaying;

  /* Two forms, and they are not equally modal. Below 1024px the panel covers
     the page: a scrim dims it, body scroll is locked, Tab stays inside and
     aria-modal is true. At 1024px and up it is a pane BESIDE the page, which
     stays scrollable and readable, so none of that applies. Claiming
     aria-modal there would tell a screen reader the article had gone away
     while a sighted reader can still see and scroll it. */
  const [isSheet, setIsSheet] = useState(true);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const sync = () => setIsSheet(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);

  /* Close from inside (backdrop, the close button, a swipe). While we still
     own the pushed entry, unwind it so the back button is not left pointing at
     a state that no longer exists; the popstate handler then does the one
     close. Calling setPanelOpen(false) directly here would leave the entry. */
  const requestClose = useCallback(() => {
    if (historyPushedRef.current) {
      historyPushedRef.current = false;
      window.history.back();
    } else {
      setPanelOpen(false);
    }
  }, [setPanelOpen]);

  /* Escape closes. */
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        requestClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, requestClose]);

  /* Back closes the panel rather than leaving the route. */
  useEffect(() => {
    if (!open) return;
    window.history.pushState({ onAirPanel: true }, "");
    historyPushedRef.current = true;
    const onPop = () => {
      historyPushedRef.current = false;
      setPanelOpen(false);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [open, setPanelOpen]);

  /* Focus in on open, back where it came from on close.

     The opener is usually the pill, and this panel suppresses the pill while
     it is open. That button is therefore already gone by the time this effect
     reads document.activeElement, which then reports <body> and gives the
     restore nothing to aim at: measured, a keyboard reader who pressed Escape
     landed on <body> and had to Tab in from the top of the document.

     So the rule is the outcome, not the mechanism: focus lands on a control.
     The remembered node is used when it is still a connected element other
     than <body>, and otherwise the restore waits a frame for the pill or the
     On Air tab to come back and focuses that. */
  useEffect(() => {
    if (open) {
      wasOpenRef.current = true;
      openerRef.current = (document.activeElement as HTMLElement) ?? null;
      panelRef.current
        ?.querySelector<HTMLElement>("button, a, [tabindex]:not([tabindex='-1'])")
        ?.focus();
      return;
    }
    /* Only ever restore after a close. Without this the effect's first run on
       every page load would focus the pill, stealing focus from the document
       before the reader had touched anything. */
    if (!wasOpenRef.current) return;
    wasOpenRef.current = false;
    const opener = openerRef.current;
    openerRef.current = null;
    const raf = requestAnimationFrame(() => {
      if (opener && opener.isConnected && opener !== document.body) {
        opener.focus();
        return;
      }
      document
        .querySelector<HTMLElement>(".fp__info, .mtb__tab--onair")
        ?.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [open]);

  /* Body scroll lock, saved and restored, for the sheet only: the desktop
     pane pushes the canvas rather than covering it, so the page behind is
     still the reader's to scroll. Locking it there would freeze the article
     they opened the transport to listen along with. */
  useEffect(() => {
    if (!open || !isSheet) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = previous; };
  }, [open, isSheet]);

  /* The desktop canvas shifts to make room. */
  useEffect(() => {
    const root = document.documentElement;
    if (open) root.setAttribute("data-onair-pane", "");
    else root.removeAttribute("data-onair-pane");
    return () => root.removeAttribute("data-onair-pane");
  }, [open]);

  /* Tab stays inside the sheet. In the pane form the reader must be able to
     Tab back out to the page they are reading. */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== "Tab" || !panelRef.current || !isSheet) return;
    const focusables = Array.from(
      panelRef.current.querySelectorAll<HTMLElement>(
        "a, button, input, summary, [tabindex]:not([tabindex='-1'])"
      )
    ).filter((el) => !el.hasAttribute("disabled"));
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }, [isSheet]);

  /* A chapter's Read link leaves the site's SPA for the story page. The
     throwaway history entry this panel pushed would survive that navigation
     and cost the reader a second press of Back to get anywhere. Release it and
     close the panel; the link then navigates normally. The same reasoning as
     MobileSidePanel's link-click case, for the same reason. */
  const releaseForLink = useCallback(() => {
    historyPushedRef.current = false;
    setPanelOpen(false);
  }, [setPanelOpen]);

  /* Swipe down to dismiss (the sheet and the phone panel). */
  const onTouchStart = (e: React.TouchEvent) => {
    dragRef.current = { startY: e.touches[0].clientY, current: 0 };
  };
  const onTouchMove = (e: React.TouchEvent) => {
    if (!dragRef.current) return;
    const dy = e.touches[0].clientY - dragRef.current.startY;
    if (dy > 0) {
      dragRef.current.current = dy;
      setDragOffset(dy * 0.6);
    }
  };
  const onTouchEnd = () => {
    if (!dragRef.current) return;
    const dy = dragRef.current.current;
    dragRef.current = null;
    setDragOffset(0);
    if (dy > 80) {
      hapticLight();
      requestClose();
    }
  };

  const groupedEpisodes = useMemo(() => {
    if (previousEpisodes.length <= 1) return null;
    const grouped = new Map<string, typeof previousEpisodes>();
    for (const ep of previousEpisodes) {
      const key = new Date(ep.created_at).toLocaleDateString("en-US", {
        weekday: "short", month: "short", day: "numeric",
      });
      if (!grouped.has(key)) grouped.set(key, []);
      grouped.get(key)!.push(ep);
    }
    return grouped;
  }, [previousEpisodes]);

  const opinionIndex = useMemo(() => findOpinionIndex(chapters), [chapters]);

  if (!open || !nowPlaying) return null;

  const displayDuration = nowPlaying.durationSeconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;
  const marks = chapterMarks(chapters, displayDuration);

  /* Everything the panel says comes off the loaded episode. Only the daily
     programme has an edition; the Argument used to be datelined "World
     Edition" because it was written into the daily slot. */
  const ownsDaily = nowPlaying.kind === "daily";
  const editionLabel = nowPlaying.editionLabel;
  const episodeDate = nowPlaying.publishedAt ? formatDate(nowPlaying.publishedAt) : "";
  const voiceLabel = nowPlaying.voiceLabel;

  const opinionStart = nowPlaying.opinionStartSeconds;
  const hasOpinionSection = ownsDaily && brief?.opinion_text != null && opinionStart !== null;
  const opinionPct = opinionStart !== null && displayDuration > 0
    ? (opinionStart / displayDuration) * 100
    : null;
  const inOpinion = opinionStart !== null && currentTime >= opinionStart;

  const hasChapters = chapters.length > 0;
  const currentChapter = currentChapterIndex >= 0 ? chapters[currentChapterIndex] : null;
  const speedLabel = `${playbackSpeed}x`;

  const dismiss = () => {
    hapticLight();
    setPlayerVisible(false);
    requestClose();
  };

  return (
    <>
      {isSheet && (
        <div className="oap__scrim" onClick={requestClose} aria-hidden="true" />
      )}
      <div
        ref={panelRef}
        /* fp fp--broadcast: the console's own geometry and skin, which this
           panel inherits rather than restating. `oap` adds only what a dialog
           needs on top of it. */
        className={[
          "fp", "fp--broadcast", "oap",
          isPlaying ? "fp--playing" : "",
          nowPlaying.kind === "weekly" ? "fp--weekly" : "",
          nowPlaying.kind === "history" ? "fp--history" : "",
        ].filter(Boolean).join(" ")}
        style={dragOffset > 0 ? { transform: `translateY(${dragOffset}px)`, transition: "none" } : undefined}
        role="dialog"
        aria-modal={isSheet ? "true" : undefined}
        aria-label={`${nowPlaying.programmeLabel}: ${nowPlaying.title}`}
        onKeyDown={handleKeyDown}
      >
        <div
          className="fp__broadcast oap__body"
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
        >
          <div className="fp__drag-indicator" aria-hidden="true" />

          {/* VU arc motif — decorative broadcast gauge behind the header */}
          <svg className="fp__vu-arc" viewBox="0 0 200 60" aria-hidden="true">
            <path d="M30 55 A70 70 0 0 1 170 55" fill="none" stroke="currentColor" strokeWidth="1.5" />
            <path d="M45 55 A55 55 0 0 1 155 55" fill="none" stroke="currentColor" strokeWidth="0.75" opacity="0.5" />
            {Array.from({ length: 9 }, (_, i) => {
              const angle = Math.PI - (Math.PI * (i + 1)) / 10;
              const cx = 100 + 70 * Math.cos(angle);
              const cy = 55 - 70 * Math.sin(angle);
              const len = (i === 0 || i === 4 || i === 8) ? 6 : 4;
              return (
                <line
                  key={i}
                  x1={cx} y1={cy}
                  x2={cx + len * Math.cos(angle)} y2={cy - len * Math.sin(angle)}
                  stroke="currentColor" strokeWidth="1"
                />
              );
            })}
          </svg>

          <div className="fp__bcast-header">
            <div className="fp__bcast-brand">
              <ScaleIcon size={22} animation={isPlaying ? "broadcast" : "idle"} />
              <div className="fp__bcast-title-group">
                <span className="fp__bcast-void">Void</span>
                <span className="fp__bcast-cmd">{nowPlaying.programmeLabel}</span>
              </div>
              <span className={`fp__status${isPlaying ? " fp__status--live" : ""}`}>
                <span className="fp__status-dot" />
                <span className="fp__status-label">{isPlaying ? "ON AIR" : "On demand"}</span>
              </span>
              {audioError && <span className="fp__bar-error">Unavailable</span>}
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" type="button"
                onClick={() => { hapticLight(); cycleSpeed(); }}
                aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__minimize" type="button"
                onClick={() => { hapticLight(); requestClose(); }}
                aria-label="Close the player panel">
                <CaretRight size={14} weight="bold" className="fp__caret fp__caret--down" />
              </button>
              <button className="fp__dismiss" type="button" onClick={dismiss}
                aria-label="Stop and dismiss the player">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          {/* Dateline. A programme without an edition leads with its own title
              instead, so the panel reads like a plate rather than borrowing
              the daily grammar. */}
          <div className="fp__bcast-dateline">
            <span className="fp__bcast-edition">
              {editionLabel ? `${editionLabel} Edition` : nowPlaying.title}
            </span>
            {episodeDate && <span className="fp__bcast-date">{episodeDate}</span>}
            {voiceLabel && <span className="fp__bcast-voices">{voiceLabel}</span>}
            {durationMin && <span className="fp__bcast-duration">{durationMin} min</span>}
          </div>

          <VuMeter
            className={`fp__vu fp__vu--hero${isPlaying ? " fp__vu--active" : ""}`}
            barClassName="fp__vu-bar"
            liveClassName="fp__vu--live"
            active={isPlaying}
          />

          <div className="fp__transport">
            <button className="fp__skip" type="button"
              onClick={() => skipBackward()} aria-label="Back 15s">-15</button>
            <button
              className={`fp__play-lg${isPlaying ? " fp__play-lg--active" : ""}`}
              type="button"
              onClick={() => { hapticMedium(); handlePlayPause(); }}
              aria-label={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>
            <button className="fp__skip" type="button"
              onClick={() => skipForward()} aria-label="Forward 15s">+15</button>
          </div>

          <div className="fp__seek">
            {hasChapters ? (
              <div className="fp__rail">
                <span className="fp__rail-now">{currentChapter ? currentChapter.title : "On air"}</span>
                <span className="fp__rail-count"
                  aria-label={`Chapter ${currentChapterIndex + 1} of ${chapters.length}`}>
                  {/* Between chapters the readout names the length of the running
                order rather than drawing a dash for the missing index. The old
                placeholder was a literal en dash written as a \u escape, which
                slipped the kill list while still printing a banned dash to the
                reader. */}
            {currentChapterIndex >= 0
              ? `${currentChapterIndex + 1} / ${chapters.length}`
              : `${chapters.length} chapters`}
                </span>
                {opinionIndex >= 0 && (
                  <button
                    className={`fp__rail-jump${currentChapterIndex === opinionIndex ? " fp__rail-jump--active" : ""}`}
                    type="button"
                    onClick={() => seekToChapter(opinionIndex)}
                  >
                    Editorial
                  </button>
                )}
              </div>
            ) : (
              <div className="fp__seek-sections">
                <button
                  className={`fp__seek-sec${!inOpinion ? " fp__seek-sec--active" : ""}`}
                  type="button" onClick={() => seekTo(0)}
                >
                  {nowPlaying.kind === "history" ? "Account" : "News"}
                </button>
                {hasOpinionSection && opinionStart !== null && (
                  <button
                    className={`fp__seek-sec${inOpinion ? " fp__seek-sec--active" : ""}`}
                    type="button" onClick={() => seekTo(opinionStart)}
                  >
                    Opinion
                  </button>
                )}
              </div>
            )}
            <div className="fp__seek-bar-wrap">
              <div className="fp__seek-bar">
                <div className="fp__seek-buffer" style={{ transform: `scaleX(${buffered / 100})` }} />
                <div className="fp__seek-fill" style={{ width: `${progress}%` }} />
                {hasChapters
                  ? marks.map((m) => (
                      <span
                        key={m.index}
                        className={`fp__seek-mark${m.index === currentChapterIndex ? " fp__seek-mark--active" : ""}${(m.chapter.kind === "opinion" || m.chapter.kind === "editorial") ? " fp__seek-mark--ed" : ""}`}
                        style={{ left: `${m.pct}%` }}
                        aria-hidden="true"
                      />
                    ))
                  : opinionPct !== null && (
                      <span className="fp__seek-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
                    )}
              </div>
              <input
                type="range" className="fp__seek-input" min={0} max={displayDuration || 100}
                value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek"
                aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`}
              />
            </div>
            <div className="fp__seek-time">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(displayDuration || 0)}</span>
            </div>
          </div>

          {/* Running order. The ROW seeks; an archived story carries a separate
              small link, so a tap never navigates the reader away mid-broadcast. */}
          {hasChapters && (
            <ol className="fp__chaps" aria-label="Running order">
              {chapters.map((c, i) => {
                const on = i === currentChapterIndex;
                const kind = chapterKindLabel(c);
                return (
                  <li key={`${c.startTime}-${i}`} className={`fp__chap${on ? " fp__chap--on" : ""}`}>
                    <button
                      className="fp__chap-seek" type="button"
                      onClick={() => { hapticLight(); seekToChapter(i); }}
                      aria-current={on ? "true" : undefined}
                    >
                      <span className="fp__chap-time">{formatChapterTime(c.startTime)}</span>
                      <span className="fp__chap-body">
                        <span className="fp__chap-title">{c.title}</span>
                        {c.subtitle && <span className="fp__chap-sub">{c.subtitle}</span>}
                      </span>
                      {kind && <span className="fp__chap-kind">{kind}</span>}
                    </button>
                    {c.url && (
                      <a className="fp__chap-link" href={c.url} onClick={releaseForLink}>
                        Read
                        <span className="sr-only"> the full story: {c.title}</span>
                      </a>
                    )}
                  </li>
                );
              })}
            </ol>
          )}

          {/* Episode notes: the DAILY brief's own text. Rendered only while the
              daily programme is loaded; it used to print today's TL;DR under a
              History documentary. */}
          {ownsDaily && brief && (
            <details className="fp__bcast-details">
              <summary className="fp__bcast-summary">
                <span>Episode notes</span>
                <CaretRight size={12} weight="bold" className="fp__caret fp__bcast-summary-arrow" />
              </summary>
              <div className="fp__bcast-content">
                <div className="fp__bcast-section">
                  <span className="fp__bcast-section-label">Summary</span>
                  <div className="fp__bcast-text">
                    {splitBriefParagraphs(brief.tldr_text).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
                </div>
                {brief.opinion_text && (
                  <>
                    <div className="fp__bcast-firewall" aria-hidden="true" />
                    <div className="fp__bcast-section">
                      <div className="fp__bcast-section-head">
                        <span className="fp__bcast-section-label">Opinion</span>
                        {brief.opinion_lean && (
                          <span className={`fp__bcast-lean fp__bcast-lean--${brief.opinion_lean}`}>
                            {brief.opinion_lean}
                          </span>
                        )}
                      </div>
                      <div className="fp__bcast-text">
                        {splitBriefParagraphs(brief.opinion_text).map((para, i) => <p key={i}>{para}</p>)}
                      </div>
                    </div>
                  </>
                )}
              </div>
            </details>
          )}

          {groupedEpisodes && (
            <details className="fp__bcast-details fp__playlist">
              <summary className="fp__bcast-summary">
                <span>{nowPlaying.kind === "weekly" ? "Previous issues" : "Previous episodes"}</span>
                <CaretRight size={12} weight="bold" className="fp__caret fp__bcast-summary-arrow" />
              </summary>
              <div className="fp__playlist-wrap">
                {(() => { let ti = 0; return Array.from(groupedEpisodes.entries()).map(([dayLabel, eps]) => (
                  <div key={dayLabel} className="fp__playlist-day">
                    <div className="fp__playlist-day-label" style={{ "--fp-track-i": ti++ } as React.CSSProperties}>{dayLabel}</div>
                    {eps.map((ep) => {
                      /* Against the LOADED episode, not the daily brief: the
                         row that is playing must be the one marked. */
                      const isCurrent = !!ep.audio_url && nowPlaying.audioUrl === ep.audio_url;
                      const epDuration = ep.audio_duration_seconds ? Math.ceil(ep.audio_duration_seconds / 60) : null;
                      return (
                        <button
                          key={ep.id}
                          className={`fp__track${isCurrent ? " fp__track--current" : ""}`}
                          style={{ "--fp-track-i": ti++ } as React.CSSProperties}
                          onClick={() => { if (!isCurrent) { hapticConfirm(); loadEpisode(ep); } }}
                          type="button"
                          aria-current={isCurrent ? "true" : undefined}
                          disabled={isCurrent}
                        >
                          <div className="fp__track-num" aria-hidden="true">
                            {isCurrent && isPlaying
                              ? <span className="fp__track-eq"><span /><span /><span /></span>
                              : <PlayIcon />}
                          </div>
                          <div className="fp__track-body">
                            <div className="fp__track-row">
                              <span className="fp__track-label">News</span>
                              <span className="fp__track-hl">{ep.tldr_headline || "Daily Brief"}</span>
                            </div>
                            {ep.opinion_text && (
                              <div className="fp__track-row fp__track-row--opinion">
                                <span className="fp__track-label">Opinion</span>
                                <span className="fp__track-hl">{ep.opinion_headline || "Opinion"}</span>
                                {ep.opinion_lean && (
                                  <span className={`fp__track-lean fp__track-lean--${ep.opinion_lean}`}>
                                    {ep.opinion_lean[0].toUpperCase()}
                                  </span>
                                )}
                              </div>
                            )}
                            <div className="fp__track-sub">
                              <span>{formatEpisodeTime(ep.created_at)}</span>
                              {epDuration && <span>{epDuration} min</span>}
                              {ep.audio_voice_label && <span>{ep.audio_voice_label}</span>}
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
      </div>
    </>
  );
}
