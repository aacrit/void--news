"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { useAudio } from "./AudioProvider";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticConfirm } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";

/* ---------------------------------------------------------------------------
   FloatingPlayer: the pill.

   This file used to carry three tiers: the pill, a compact bar, and the full
   broadcast console. The console duplicated OnAirPage's portal almost line
   for line (onair.css:5 admitted it: "mirrors .fp__broadcast"), so at 1440px
   both were on screen at once showing one episode through two
   implementations. The console is OnAirPanel now, and with it gone the
   middle tier had neither a way in nor a purpose: the pill IS the compact
   state and the panel IS the full one.

   What is left is the smallest honest piece of chrome: what is playing, how
   far in, a play control, and a press that opens the console. Everything it
   says comes off the loaded episode, so it cannot print today's headline over
   a Weekly issue.

   It stands down where a fuller transport already has the reader: on /onair,
   whose page carries its own portal, and while the panel is open.
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

export default function FloatingPlayer() {
  const {
    isPlaying, currentTime, duration,
    handlePlayPause,
    isPlayerVisible,
    isPanelOpen, setPanelOpen,
    contentType, nowPlaying,
    chapters, currentChapterIndex,
  } = useAudio();

  const pathname = usePathname();
  const route = pathname.replace(BASE_PATH, "") || "/";
  const isWeekly = contentType === "weekly";
  const isHistory = contentType === "history";
  /* The programme in the element, never a constant: the pill read "Weekly",
     the section, whichever programme had last been written into the old
     single slot. */
  const productLabel = nowPlaying?.programmeLabel ?? "On Air";

  const onOnAirRoute = route === "/onair" || route.startsWith("/onair/");
  const suppressed = onOnAirRoute || isPanelOpen;

  // Desktop: reserve a bottom gutter so the fixed pill never covers the end of
  // page content (/ship, /about, /sources — F10). floating-player.css consumes
  // html[data-fp-pill] to pad the document body on >=768px.
  useEffect(() => {
    const showPill = isPlayerVisible && !suppressed && !!nowPlaying;
    const root = document.documentElement;
    if (showPill) root.setAttribute("data-fp-pill", "");
    else root.removeAttribute("data-fp-pill");
    return () => root.removeAttribute("data-fp-pill");
  }, [isPlayerVisible, suppressed, nowPlaying]);

  if (!nowPlaying || !isPlayerVisible || suppressed) return null;

  const displayDuration = nowPlaying.durationSeconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  /* The opinion firewall belongs to the daily programme. A null start means no
     label: the old code guessed the editorial began at 60% of the episode and
     labelled a moment nobody had measured. */
  const opinionStart = nowPlaying.opinionStartSeconds;
  const inOpinion = opinionStart !== null && currentTime >= opinionStart;

  const hasChapters = chapters.length > 0;
  const currentChapter = currentChapterIndex >= 0 ? chapters[currentChapterIndex] : null;

  /* The press opens the panel, not a route: the reader keeps their place. */
  const openPanel = () => {
    hapticLight();
    setPanelOpen(true);
  };

  return (
    <div
      className={[
        "fp", "fp--compact",
        isPlaying ? "fp--playing" : "",
        isWeekly ? "fp--weekly" : "",
        isHistory ? "fp--history" : "",
      ].filter(Boolean).join(" ")}
      role="region"
      aria-label="Audio player"
    >
      <div className="fp__pill" onClick={openPanel}>
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

        <button type="button" className="fp__info" title="Open the player"
          onClick={(e) => { e.stopPropagation(); openPanel(); }}>
          {isPlaying && <span className="fp__rec-dot" aria-hidden="true" />}
          <span className="fp__title">{productLabel}</span>
          <span
            className={`fp__section${hasChapters ? " fp__section--chapter" : ""}`}
            title={hasChapters && currentChapter ? currentChapter.title : undefined}
          >
            {hasChapters
              ? currentChapter?.title ?? "On air"
              : isHistory ? "Account" : isWeekly ? "Issue" : inOpinion ? "Opinion" : "News"}
          </span>
        </button>

        <span className="fp__time">
          {isPlaying || currentTime > 0 ? formatTime(currentTime) : durationMin ? `${durationMin}m` : ""}
        </span>

        <div className="fp__mini-progress" aria-hidden="true">
          <div className="fp__mini-progress-fill" style={{ transform: `scaleX(${progress / 100})` }} />
        </div>
      </div>
    </div>
  );
}
