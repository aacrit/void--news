"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { DailyBriefData } from "../lib/types";
import { fetchDailyBrief } from "../lib/supabase";
import { hapticLight, hapticTick } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   Shared state — call once in HomeContent, pass to DailyBriefText + OnAirButton.
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
}

export function useDailyBrief(edition: string): DailyBriefState {
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const [buffered, setBuffered] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(() => {
    if (typeof window === "undefined") return 1;
    try { const s = localStorage.getItem("void-onair-speed"); return s ? Number(s) : 1; } catch { return 1; }
  });
  const [isPlayerVisible, setPlayerVisible] = useState(false);
  const [isExpanded, setExpanded] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Pause and detach audio before switching briefs to prevent a race
    // where audio.play() is still pending when src changes.
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.src = "";
      audio.load();
    }

    setBrief(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setAudioError(false);
    setBuffered(0);
    // Fetch edition-specific brief (pipeline generates distinct content per edition)
    fetchDailyBrief(edition).then((data) => {
      if (!cancelled) setBrief(data);
    });
    return () => { cancelled = true; };
  }, [edition]);

  // Callback ref — attaches listeners the instant <audio> mounts in the DOM,
  // regardless of whether brief loaded before or after DailyBriefText renders.
  const listenerCleanupRef = useRef<(() => void) | null>(null);

  const audioCallbackRef = useCallback((el: HTMLAudioElement | null) => {
    if (listenerCleanupRef.current) {
      listenerCleanupRef.current();
      listenerCleanupRef.current = null;
    }
    audioRef.current = el;
    if (!el) return;

    const onTime = () => setCurrentTime(el.currentTime);
    const onMeta = () => {
      if (el.duration && isFinite(el.duration)) setDuration(el.duration);
    };
    const onEnd = () => setIsPlaying(false);
    const onError = () => { setAudioError(true); setIsPlaying(false); };
    const onProgress = () => {
      if (el.buffered.length > 0 && el.duration > 0) {
        setBuffered((el.buffered.end(el.buffered.length - 1) / el.duration) * 100);
      }
    };

    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("durationchange", onMeta);
    el.addEventListener("ended", onEnd);
    el.addEventListener("error", onError);
    el.addEventListener("progress", onProgress);
    if (el.duration && isFinite(el.duration)) setDuration(el.duration);

    listenerCleanupRef.current = () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("durationchange", onMeta);
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("error", onError);
      el.removeEventListener("progress", onProgress);
    };
  }, []);

  // F08: Rely solely on callback ref — no getElementById fallback (avoids duplicate id issues)
  const getAudio = useCallback((): HTMLAudioElement | null => {
    return audioRef.current;
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    // No haptic here — callers provide their own (hapticConfirm on pill, hapticMedium on transport)
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      if (audioError) {
        setAudioError(false);
        audio.load();
      }
      audio.play().catch(() => {
        setAudioError(true);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    }
  }, [isPlaying, audioError, getAudio]);

  const lastSeekTick = useRef(0);
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = getAudio();
    if (!audio) return;
    const t = Number(e.target.value);
    const tick = Math.floor(t / 5);
    if (tick !== lastSeekTick.current) {
      lastSeekTick.current = tick;
      hapticTick();
    }
    audio.currentTime = t;
    setCurrentTime(t);
  }, [getAudio]);

  const SPEEDS = [1, 1.25, 1.5, 2] as const;
  const cycleSpeed = useCallback(() => {
    setPlaybackSpeed((prev) => {
      const idx = SPEEDS.indexOf(prev as typeof SPEEDS[number]);
      const next = SPEEDS[(idx + 1) % SPEEDS.length];
      const audio = audioRef.current;
      if (audio) audio.playbackRate = next;
      try { localStorage.setItem("void-onair-speed", String(next)); } catch {}
      return next;
    });
  }, []);

  // Apply saved speed when audio loads
  useEffect(() => {
    const audio = audioRef.current;
    if (audio && playbackSpeed !== 1) audio.playbackRate = playbackSpeed;
  }, [brief, playbackSpeed]);

  const skipForward = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticTick();
    audio.currentTime = Math.min(audio.currentTime + 15, audio.duration || Infinity);
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const skipBackward = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticTick();
    audio.currentTime = Math.max(audio.currentTime - 15, 0);
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const seekTo = useCallback((seconds: number) => {
    const audio = getAudio();
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    setCurrentTime(seconds);
    if (!isPlaying) {
      if (audioError) { setAudioError(false); audio.load(); }
      audio.play().catch(() => { setAudioError(true); setIsPlaying(false); });
      setIsPlaying(true);
    }
  }, [isPlaying, audioError]);

  // Auto-show player when brief has audio
  useEffect(() => {
    if (brief?.audio_url) setPlayerVisible(true);
  }, [brief]);

  return {
    brief, isPlaying, currentTime, duration, buffered, audioError, audioRef, audioCallbackRef,
    handlePlayPause, handleSeek, playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible, isExpanded, setExpanded,
  };
}

/* F07: DailyBriefText, OnAirButton, and default export removed.
   Desktop uses SkyboxBanner. Mobile uses MobileBriefPill.
   Only useDailyBrief hook and DailyBriefState type are retained. */
