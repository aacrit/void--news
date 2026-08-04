"use client";

import { useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import LogoIcon from "./LogoIcon";
import { useAudio } from "./AudioProvider";
import { hapticLight, hapticConfirm } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   MobileMiniPlayer — Persistent strip above MobileTabBar when audio is
   playing/paused. Apple Podcasts pattern.
   Shows: logo icon, "void --onair" label, play/pause, thin progress bar.
   Tap anywhere (except play button) expands FloatingPlayer.
   Only visible when audio has ever been started.
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

const PlayIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
    <path d="M3 1.5v11l9-5.5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="currentColor" aria-hidden="true">
    <rect x="2" y="1" width="3" height="12" rx="0.5" />
    <rect x="9" y="1" width="3" height="12" rx="0.5" />
  </svg>
);

export default function MobileMiniPlayer() {
  const {
    brief,
    isPlaying,
    currentTime,
    duration,
    handlePlayPause,
    isExpanded,
    isPlayerVisible,
    contentType,
  } = useAudio();
  const router = useRouter();
  const isWeekly = contentType === "weekly";
  const isHistory = contentType === "history";
  const productLabel = isHistory ? "History" : isWeekly ? "Weekly" : "On Air";

  // Set data-audio-active on body while the mini-player strip is visible —
  // CSS uses this to add bottom padding for the 44px strip. Visibility is now
  // driven by isPlayerVisible (set when the reader taps the On Air tab), so the
  // padding tracks the strip both when it appears and when it is dismissed.
  useEffect(() => {
    if (isPlayerVisible && brief?.audio_url) {
      document.body.setAttribute("data-audio-active", "true");
    } else {
      document.body.removeAttribute("data-audio-active");
    }
  }, [isPlayerVisible, brief?.audio_url]);

  const displayDuration = brief?.audio_duration_seconds || duration;
  const progress =
    displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  // Expanding the mini-player on mobile navigates to the full /onair page
  // rather than opening the in-page expanded sheet.
  const handleExpand = useCallback(() => {
    hapticLight();
    router.push("/onair");
  }, [router]);

  const handlePlayPauseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      hapticConfirm();
      handlePlayPause();
    },
    [handlePlayPause]
  );

  // Only show once the reader has revealed the player (via the On Air tab) and
  // a brief with audio is loaded. Nothing appears on load — the auto-show is
  // suppressed on mobile in AudioProvider.
  // Hide when FloatingPlayer is expanded (they overlap in the same zone).
  if (!isPlayerVisible || !brief?.audio_url) return null;
  if (isExpanded) return null;

  return (
    <div className={`mmp${isWeekly ? " mmp--weekly" : ""}${isHistory ? " mmp--history" : ""}`} onClick={handleExpand} role="complementary" aria-label="Audio mini-player">
      {/* Logo icon */}
      <div className="mmp__icon">
        <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} />
      </div>

      {/* Label */}
      <span className="mmp__label">{productLabel}</span>

      {/* Spacer */}
      <div className="mmp__spacer" />

      {/* Play/Pause button */}
      <button
        type="button"
        className="mmp__play"
        onClick={handlePlayPauseClick}
        aria-label={isPlaying ? "Pause" : "Play"}
      >
        {isPlaying ? <PauseIcon /> : <PlayIcon />}
      </button>

      {/* Progress bar */}
      <div className="mmp__progress" aria-hidden="true">
        <div className="mmp__progress-fill" style={{ width: `${progress}%` }} />
      </div>
    </div>
  );
}
