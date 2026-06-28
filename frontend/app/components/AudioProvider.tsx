"use client";

import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  type ReactNode,
} from "react";
import type { DailyBriefData, Edition } from "../lib/types";
import { fetchDailyBrief, fetchPreviousEpisodes } from "../lib/supabase";
import { hapticLight, hapticTick } from "../lib/haptics";
import { AUDIO_ENABLED } from "../lib/audioGate";

/* ---------------------------------------------------------------------------
   AudioProvider — Global audio context for void --onair.
   Wraps layout.tsx so <audio> survives page navigation.
   Any component can consume playback state via useAudio().

   Design:
   - The <audio> element lives here, not in any page component.
   - Brief data fetching also lives here (coupled to edition).
   - Navigator.mediaSession for iOS lock screen / notification controls.
   --------------------------------------------------------------------------- */

/** Episode metadata for the "Previous Episodes" playlist */
export interface EpisodeMeta {
  id: string;
  edition: string;
  tldr_headline: string | null;
  tldr_text: string | null;
  opinion_headline: string | null;
  opinion_text: string | null;
  opinion_lean: string | null;
  audio_url: string | null;
  audio_duration_seconds: number | null;
  opinion_start_seconds: number | null;
  audio_voice_label: string | null;
  audio_voice: string | null;
  created_at: string;
}

export interface AudioState {
  brief: DailyBriefData | null;
  edition: string;
  setEdition: (ed: string) => void;
  /** Which product currently owns the player — drives accent theming + labels */
  contentType: "daily" | "weekly";
  /** Load a weekly digest (+ optional archive playlist) into the shared player */
  playWeekly: (
    digest: import("../lib/types").WeeklyDigestData,
    archiveIssues?: EpisodeMeta[]
  ) => void;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  buffered: number;
  audioError: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  handlePlayPause: () => void;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
  playbackSpeed: number;
  cycleSpeed: () => void;
  skipForward: () => void;
  skipBackward: () => void;
  seekTo: (seconds: number) => void;
  isPlayerVisible: boolean;
  setPlayerVisible: (v: boolean) => void;
  isExpanded: boolean;
  setExpanded: (v: boolean) => void;
  analyserRef: React.RefObject<AnalyserNode | null>;
  /** Lazily connect Web Audio API analyser — call when viz becomes visible */
  connectAnalyser: () => void;
  /** Whether audio has ever been started (for mini-player visibility) */
  hasEverPlayed: boolean;
  /** Previous episodes (last 3 days) for current edition */
  previousEpisodes: EpisodeMeta[];
  /** Load and play a specific episode by its audio URL */
  loadEpisode: (episode: EpisodeMeta) => void;
}

const AudioContext = createContext<AudioState | null>(null);

export function useAudio(): AudioState {
  const ctx = useContext(AudioContext);
  if (!ctx) throw new Error("useAudio must be used inside <AudioProvider>");
  return ctx;
}

export default function AudioProvider({ children }: { children: ReactNode }) {
  const [edition, setEditionState] = useState<string>("world");
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const [buffered, setBuffered] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(() => {
    if (typeof window === "undefined") return 1;
    try {
      const s = localStorage.getItem("void-onair-speed");
      return s ? Number(s) : 1;
    } catch {
      return 1;
    }
  });
  const [isPlayerVisible, setPlayerVisible] = useState(false);
  const [isExpanded, setExpanded] = useState(false);
  const [hasEverPlayed, setHasEverPlayed] = useState(false);
  const [previousEpisodes, setPreviousEpisodes] = useState<EpisodeMeta[]>([]);
  // Which product owns the player. A ref mirror lets the edition-fetch effect
  // bail when a weekly issue is loaded, without re-running on contentType change.
  const [contentType, setContentType] = useState<"daily" | "weekly">("daily");
  const contentTypeRef = useRef<"daily" | "weekly">("daily");
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Public setEdition: the daily flow (useDailyBrief) is the only caller, so
  // any setEdition means we are back on a daily surface — flip ownership to
  // 'daily' BEFORE the edition-fetch effect re-runs so its clobber guard lets
  // the daily brief load. (Ref is updated synchronously; state for rendering.)
  const setEdition = useCallback((ed: string) => {
    contentTypeRef.current = "daily";
    setContentType("daily");
    setEditionState(ed);
  }, []);

  /* ---- Web Audio API: real-time analyser for oscilloscope ---- */
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const connectedElements = useRef<WeakSet<HTMLAudioElement>>(new WeakSet());

  /* ---- Fetch brief when edition changes (or when returning to the daily surface) ---- */
  useEffect(() => {
    // A weekly issue currently owns the player — do NOT overwrite it with the
    // daily brief. (Read the ref for the live value: playWeekly sets the ref
    // synchronously, so even if this effect fires from the contentType state
    // change it sees 'weekly' and bails.)
    if (contentTypeRef.current === "weekly") return;

    let cancelled = false;

    // Pause and detach audio before switching briefs. No-ops when audio is
    // parked (the <audio> element is never mounted, so audioRef is null).
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
    setPreviousEpisodes([]);

    // TL;DR + opinion are editorial TEXT, not audio: they must load even when
    // the void --onair kill switch is on. Only the audio playback layer
    // (previous-episode list + <audio> mount) is gated by AUDIO_ENABLED.
    // Coupling this fetch to the kill switch left SkyboxBanner / MobileBriefPill
    // stuck on "Loading today's brief…" whenever audio was disabled.
    fetchDailyBrief(edition).then((data) => {
      if (!cancelled) setBrief(data);
    });

    if (AUDIO_ENABLED) {
      fetchPreviousEpisodes(edition).then((data) => {
        if (!cancelled) setPreviousEpisodes(data);
      });
    }
    return () => {
      cancelled = true;
    };
    // contentType is a dep so returning from a weekly issue to the daily surface
    // reloads the brief even when the edition string is unchanged. The ref guard
    // above prevents a weekly load from triggering a stray daily fetch.
  }, [edition, contentType]);

  /* ---- Callback ref — attaches listeners when <audio> mounts ---- */
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
    const onError = () => {
      setAudioError(true);
      setIsPlaying(false);
    };
    const onProgress = () => {
      if (el.buffered.length > 0 && el.duration > 0) {
        setBuffered(
          (el.buffered.end(el.buffered.length - 1) / el.duration) * 100
        );
      }
    };

    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("durationchange", onMeta);
    el.addEventListener("ended", onEnd);
    el.addEventListener("error", onError);
    el.addEventListener("progress", onProgress);
    if (el.duration && isFinite(el.duration)) setDuration(el.duration);

    // Web Audio API analyser: LAZY connection — only when visualization is
    // first needed. Connecting immediately causes iOS to route audio through
    // AudioContext, which gets suspended in background and kills playback.
    // The analyser is connected on first play when isExpanded/broadcast is open.

    listenerCleanupRef.current = () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("durationchange", onMeta);
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("error", onError);
      el.removeEventListener("progress", onProgress);
    };
  }, []);

  const getAudio = useCallback((): HTMLAudioElement | null => {
    return audioRef.current;
  }, []);

  /* ---- Lazy analyser connection — called from FloatingPlayer when viz opens ---- */
  const connectAnalyser = useCallback(() => {
    const el = audioRef.current;
    if (!el || connectedElements.current.has(el)) return;
    try {
      const ctx =
        audioContextRef.current ||
        new (window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof window.AudioContext })
            .webkitAudioContext)();
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 2048;
      analyser.smoothingTimeConstant = 0.82;
      const source = ctx.createMediaElementSource(el);
      source.connect(analyser);
      analyser.connect(ctx.destination);
      audioContextRef.current = ctx;
      analyserRef.current = analyser;
      connectedElements.current.add(el);
    } catch {
      // Web Audio API unavailable or CORS blocked
    }
  }, []);

  /* ---- Resume AudioContext when returning from background (iOS) ---- */
  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === "visible" && audioContextRef.current?.state === "suspended") {
        audioContextRef.current.resume();
      }
    };
    document.addEventListener("visibilitychange", handleVisibility);
    return () => document.removeEventListener("visibilitychange", handleVisibility);
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      if (audioError) {
        setAudioError(false);
        audio.load();
      }
      // Resume AudioContext for iOS Safari
      if (audioContextRef.current?.state === "suspended") {
        audioContextRef.current.resume();
      }
      audio
        .play()
        .catch(() => {
          setAudioError(true);
          setIsPlaying(false);
        });
      setIsPlaying(true);
      setHasEverPlayed(true);
    }
  }, [isPlaying, audioError, getAudio]);

  const lastSeekTick = useRef(0);
  const handleSeek = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
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
    },
    [getAudio]
  );

  const SPEEDS = [1, 1.25, 1.5, 2] as const;
  const cycleSpeed = useCallback(() => {
    setPlaybackSpeed((prev) => {
      const idx = SPEEDS.indexOf(prev as (typeof SPEEDS)[number]);
      const next = SPEEDS[(idx + 1) % SPEEDS.length];
      const audio = audioRef.current;
      if (audio) audio.playbackRate = next;
      try {
        localStorage.setItem("void-onair-speed", String(next));
      } catch {}
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
    audio.currentTime = Math.min(
      audio.currentTime + 15,
      audio.duration || Infinity
    );
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const skipBackward = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticTick();
    audio.currentTime = Math.max(audio.currentTime - 15, 0);
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const seekTo = useCallback(
    (seconds: number) => {
      const audio = getAudio();
      if (!audio) return;
      hapticLight();
      audio.currentTime = seconds;
      setCurrentTime(seconds);
      if (!isPlaying) {
        if (audioError) {
          setAudioError(false);
          audio.load();
        }
        audio.play().catch(() => {
          setAudioError(true);
          setIsPlaying(false);
        });
        setIsPlaying(true);
        setHasEverPlayed(true);
      }
    },
    [isPlaying, audioError]
  );

  // Auto-show player when brief has audio
  useEffect(() => {
    if (brief?.audio_url) setPlayerVisible(true);
  }, [brief]);

  /** Load a previous episode — swap audio source and reset playback state.
   *  We only pause the current element here; the actual source swap happens
   *  when React reconciles the <audio> element with the new brief.audio_url.
   *  Setting audio.src imperatively would trigger a wasted HTTP request on
   *  the old element that gets unmounted moments later. */
  const loadEpisode = useCallback((episode: EpisodeMeta) => {
    if (!episode.audio_url) return;
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
    }
    // Create DailyBriefData from episode metadata
    setBrief((prev) => ({
      ...(prev || {} as DailyBriefData),
      id: episode.id,
      edition: episode.edition as DailyBriefData["edition"],
      tldr_headline: episode.tldr_headline,
      tldr_text: episode.tldr_text || "",
      opinion_headline: episode.opinion_headline,
      opinion_text: episode.opinion_text || null,
      opinion_lean: episode.opinion_lean as DailyBriefData["opinion_lean"],
      audio_url: episode.audio_url,
      audio_duration_seconds: episode.audio_duration_seconds,
      opinion_start_seconds: episode.opinion_start_seconds,
      audio_voice_label: episode.audio_voice_label,
      audio_voice: episode.audio_voice,
      created_at: episode.created_at,
    }));
    setCurrentTime(0);
    setDuration(episode.audio_duration_seconds || 0);
    setAudioError(false);
    setBuffered(0);
    setIsPlaying(false);
    setPlayerVisible(true);
    hapticLight();
  }, []);

  /** Load a weekly issue into the shared player. Maps WeeklyDigestData onto the
   *  DailyBriefData shape the player consumes (weekly lacks opinion sections /
   *  voice metadata, so those are null). Does NOT auto-play — it reveals the
   *  player ready to start, mirroring the daily brief's load behaviour. The
   *  optional archiveIssues become the "Previous issues" playlist. */
  const playWeekly = useCallback(
    (
      digest: import("../lib/types").WeeklyDigestData,
      archiveIssues?: EpisodeMeta[]
    ) => {
      if (!digest.audio_url) return;
      contentTypeRef.current = "weekly";
      setContentType("weekly");

      const audio = audioRef.current;
      if (audio) audio.pause();

      // cover_text is a structured WeeklyCoverStory[]; take the lead story's body.
      const coverText =
        Array.isArray(digest.cover_text) && digest.cover_text.length > 0
          ? digest.cover_text[0]?.text ?? ""
          : "";

      setBrief({
        id: digest.id,
        edition: (digest.edition ?? "world") as DailyBriefData["edition"],
        tldr_text: coverText,
        tldr_headline: digest.cover_headline ?? null,
        opinion_text: digest.opinion_text ?? null,
        opinion_headline: digest.opinion_headline ?? null,
        opinion_lean: digest.opinion_lean ?? null,
        opinion_cluster_id: null,
        audio_url: digest.audio_url,
        audio_duration_seconds: digest.audio_duration_seconds,
        opinion_start_seconds: digest.opinion_start_seconds ?? null,
        audio_voice_label: digest.audio_voice_label ?? null,
        audio_voice: digest.audio_voice ?? null,
        audio_script: null,
        top_cluster_ids: null,
        created_at: digest.created_at,
      });
      setPreviousEpisodes(archiveIssues ?? []);
      setCurrentTime(0);
      setDuration(digest.audio_duration_seconds ?? 0);
      setBuffered(0);
      setAudioError(false);
      setIsPlaying(false);
      setPlayerVisible(true);
    },
    []
  );

  /* ---- Media Session API — iOS lock screen + notification controls ---- */
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator))
      return;

    const editionLabels: Record<string, string> = {
      world: "World",
      us: "US",
      europe: "Europe",
      "south-asia": "South Asia",
    };
    const editionLabel = editionLabels[edition] || "World";

    navigator.mediaSession.metadata = new MediaMetadata({
      title: "void --onair",
      artist: "void --news",
      album: editionLabel + " Edition",
    });

    navigator.mediaSession.setActionHandler("play", () => {
      if (!isPlaying) handlePlayPause();
    });
    navigator.mediaSession.setActionHandler("pause", () => {
      if (isPlaying) handlePlayPause();
    });
    navigator.mediaSession.setActionHandler("seekbackward", () => {
      skipBackward();
    });
    navigator.mediaSession.setActionHandler("seekforward", () => {
      skipForward();
    });

    return () => {
      try {
        navigator.mediaSession.setActionHandler("play", null);
        navigator.mediaSession.setActionHandler("pause", null);
        navigator.mediaSession.setActionHandler("seekbackward", null);
        navigator.mediaSession.setActionHandler("seekforward", null);
      } catch {}
    };
  }, [edition, isPlaying, handlePlayPause, skipForward, skipBackward]);

  const value: AudioState = {
    brief,
    edition,
    setEdition,
    contentType,
    playWeekly,
    isPlaying,
    currentTime,
    duration,
    buffered,
    audioError,
    audioRef,
    handlePlayPause,
    handleSeek,
    playbackSpeed,
    cycleSpeed,
    skipForward,
    skipBackward,
    seekTo,
    isPlayerVisible,
    setPlayerVisible,
    isExpanded,
    setExpanded,
    analyserRef,
    connectAnalyser,
    hasEverPlayed,
    previousEpisodes,
    loadEpisode,
  };

  return (
    <AudioContext.Provider value={value}>
      {children}
      {/* Global <audio> element — survives page navigation.
          Gated by the audio kill switch (void --onair parked): when audio is
          disabled the element is never rendered and no .mp3 is requested. */}
      {AUDIO_ENABLED && brief?.audio_url && (
        <audio
          ref={audioCallbackRef}
          src={brief.audio_url}
          preload="metadata"
          crossOrigin="anonymous"
          hidden
        />
      )}
    </AudioContext.Provider>
  );
}
