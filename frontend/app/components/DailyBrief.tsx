"use client";

import { useEffect, useRef, useCallback } from "react";
import type { DailyBriefData } from "../lib/types";
import { useAudio, type AudioState } from "./AudioProvider";

/* ---------------------------------------------------------------------------
   DailyBriefState — backward-compatible API surface.
   useDailyBrief(edition) now delegates to the global AudioProvider.
   All consumers (HomeContent, FloatingPlayer, SkyboxBanner, etc.) continue
   to work without modification.
   --------------------------------------------------------------------------- */

export interface DailyBriefState {
  brief: DailyBriefData | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  buffered: number;
  audioError: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  audioCallbackRef: (el: HTMLAudioElement | null) => void;
  handlePlayPause: () => void;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Current playback speed (1, 1.25, 1.5, 2) */
  playbackSpeed: number;
  /** Cycle to next speed */
  cycleSpeed: () => void;
  /** Skip forward 15 seconds */
  skipForward: () => void;
  /** SkipBackward 15 seconds */
  skipBackward: () => void;
  /** Direct seek to a time in seconds */
  seekTo: (seconds: number) => void;
  /** Whether the persistent bottom player is visible */
  isPlayerVisible: boolean;
  setPlayerVisible: (v: boolean) => void;
  /** Whether the player is expanded (full panel) */
  isExpanded: boolean;
  setExpanded: (v: boolean) => void;
  /** Web Audio API analyser for real-time waveform visualization */
  analyserRef: React.RefObject<AnalyserNode | null>;
}

/**
 * Thin bridge hook: syncs edition to the global AudioProvider and returns
 * the global state shaped as DailyBriefState (backward-compatible).
 * The <audio> element now lives in AudioProvider (layout.tsx), so playback
 * persists across page navigation.
 */
export function useDailyBrief(edition: string): DailyBriefState {
  const audio = useAudio();

  // Sync edition to global provider when it changes (edition tabs, URL nav)
  useEffect(() => {
    audio.setEdition(edition);
  }, [edition]); // eslint-disable-line react-hooks/exhaustive-deps

  // No-op callback ref — <audio> is managed by AudioProvider, not here.
  // Kept in the interface for backward compatibility; existing consumers that
  // pass audioCallbackRef to an <audio> element will harmlessly no-op.
  const noopCallbackRef = useCallback((_el: HTMLAudioElement | null) => {}, []);

  return {
    brief: audio.brief,
    isPlaying: audio.isPlaying,
    currentTime: audio.currentTime,
    duration: audio.duration,
    buffered: audio.buffered,
    audioError: audio.audioError,
    audioRef: audio.audioRef,
    audioCallbackRef: noopCallbackRef,
    handlePlayPause: audio.handlePlayPause,
    handleSeek: audio.handleSeek,
    playbackSpeed: audio.playbackSpeed,
    cycleSpeed: audio.cycleSpeed,
    skipForward: audio.skipForward,
    skipBackward: audio.skipBackward,
    seekTo: audio.seekTo,
    isPlayerVisible: audio.isPlayerVisible,
    setPlayerVisible: audio.setPlayerVisible,
    isExpanded: audio.isExpanded,
    setExpanded: audio.setExpanded,
    analyserRef: audio.analyserRef,
  };
}

/* F07: DailyBriefText, OnAirButton, and default export removed.
   Desktop uses SkyboxBanner. Mobile uses MobileBriefPill.
   Only useDailyBrief hook and DailyBriefState type are retained. */
