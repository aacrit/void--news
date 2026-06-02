"use client";

import { useCallback, useEffect } from "react";
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
    hasEverPlayed,
    isExpanded,
    isPlayerVisible,
    setExpanded,
    setPlayerVisible,
  } = useAudio();

  // Set data-audio-active on body when mini-player becomes visible —
  // CSS uses this to add bottom padding for the 44px mini-player strip.
  useEffect(() => {
    if (hasEverPlayed && brief?.audio_url) {
      document.body.setAttribute("data-audio-active", "true");
    }
  }, [hasEverPlayed, brief?.audio_url]);

  const displayDuration = brief?.audio_duration_seconds || duration;
  const progress =
    displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const handleExpand = useCallback(() => {
    hapticLight();
    setPlayerVisible(true);
    setExpanded(true);
  }, [setPlayerVisible, setExpanded]);

  const handlePlayPauseClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      hapticConfirm();
      handlePlayPause();
    },
    [handlePlayPause]
  );

  // Only show when audio has been started and brief has audio.
  // Hide when FloatingPlayer is expanded (they overlap in the same zone).
  if (!hasEverPlayed || !brief?.audio_url) return null;
  if (isPlayerVisible && isExpanded) return null;

  return (
    <div className="mmp" onClick={handleExpand} role="complementary" aria-label="Audio mini-player">
      {/* Logo icon */}
      <div className="mmp__icon">
        <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} />
      </div>

      {/* Label */}
      <span className="mmp__label">void --onair</span>

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
