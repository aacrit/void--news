"use client";

import {
  createContext,
  useContext,
  useState,
  useRef,
  useCallback,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import type { AudioChapter, DailyBriefData, Edition } from "../lib/types";
import { findChapterIndex } from "../lib/chapters";
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
  /** Radio-show chapter marks. null on legacy episodes (and on weekly/history). */
  audio_chapters: AudioChapter[] | null;
  /** Where STORY 1 begins, after the ident, sign-on and menu. */
  news_start_seconds: number | null;
  created_at: string;
}

/** Minimal void --history event audio payload for the shared player.
 *  History audio is a single narrated account (no opinion firewall, no host
 *  personas), so only the fields the shared transport needs are threaded in. */
export interface HistoryAudioPayload {
  id: string;
  title: string;
  subtitle?: string | null;
  audioUrl: string;
  durationSeconds: number;
}

export interface AudioState {
  brief: DailyBriefData | null;
  edition: string;
  setEdition: (ed: string) => void;
  /** Which product currently owns the player — drives accent theming + labels */
  contentType: "daily" | "weekly" | "history";
  /** Load a weekly digest (+ optional archive playlist) into the shared player */
  playWeekly: (
    digest: import("../lib/types").WeeklyDigestData,
    archiveIssues?: EpisodeMeta[]
  ) => void;
  /** Load a void --history event's companion audio into the shared player */
  playHistory: (payload: HistoryAudioPayload) => void;
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
  /* ---- Chapter rail (radio-show episodes) ----
     Empty on legacy episodes, weekly issues and history accounts: every
     consumer treats an empty rail as "keep the old News / Opinion transport". */
  chapters: AudioChapter[];
  /** Index into `chapters` for the current playhead, or -1 when between chapters. */
  currentChapterIndex: number;
  /** Seek to the start of chapter i (no-op when out of range). */
  seekToChapter: (i: number) => void;
  /** Jump to the next chapter. */
  nextChapter: () => void;
  /** Restart the current chapter, or step back when already near its start. */
  prevChapter: () => void;
}

const AudioContext = createContext<AudioState | null>(null);

export function useAudio(): AudioState {
  const ctx = useContext(AudioContext);
  if (!ctx) throw new Error("useAudio must be used inside <AudioProvider>");
  return ctx;
}

export default function AudioProvider({
  children,
  initialBrief = null,
}: {
  children: ReactNode;
  /** Build-time prerendered daily brief (from the root layout). Seeds the
   *  first paint so The Brief renders real text server-side, and suppresses the
   *  first-mount refetch that would otherwise flash "Loading" / risk #418. */
  initialBrief?: DailyBriefData | null;
}) {
  const [edition, setEditionState] = useState<string>("world");
  const [brief, setBrief] = useState<DailyBriefData | null>(initialBrief);
  // Timestamp of the last successful brief fetch — drives the resume-refetch
  // staleness check (see the visibilitychange effect below).
  const briefFetchedAtRef = useRef<number>(0);
  // True until the seeded brief has satisfied the first edition-fetch effect
  // run, so we keep the build-time brief instead of clearing + refetching it.
  const seededRef = useRef<boolean>(initialBrief != null);
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
  // bail when a weekly issue or history account is loaded, without re-running on
  // contentType change.
  const [contentType, setContentType] = useState<"daily" | "weekly" | "history">("daily");
  const contentTypeRef = useRef<"daily" | "weekly" | "history">("daily");
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
    // A weekly issue or a history account currently owns the player — do NOT
    // overwrite it with the daily brief. (Read the ref for the live value:
    // playWeekly / playHistory set the ref synchronously, so even if this
    // effect fires from the contentType state change it sees the non-daily
    // owner and bails.)
    if (contentTypeRef.current !== "daily") return;

    let cancelled = false;

    // First mount with a build-time seeded brief: keep it. Refetching here would
    // clear the brief to null (flashing "Loading today's brief…") and could
    // produce a hydration-time first paint that differs from the server render
    // (React #418). We still load the audio playlist. Any later edition change
    // (or return from a weekly/history load) falls through to a normal refetch.
    if (seededRef.current) {
      seededRef.current = false;
      if (AUDIO_ENABLED) {
        fetchPreviousEpisodes(edition).then((data) => {
          if (!cancelled) setPreviousEpisodes(data);
        });
      }
      return () => {
        cancelled = true;
      };
    }

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
      if (!cancelled) {
        setBrief(data);
        briefFetchedAtRef.current = Date.now();
      }
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

  /* ---- Stale-brief self-heal on resume (2026-08-11) ----
     The brief is fetched once on mount, but installed PWAs / background tabs
     are resumed from memory for hours or days without a remount — observed
     live: a reader resumed a yesterday session and saw yesterday's TL;DR
     under today's dateline. On visibility resume, if the last brief fetch is
     older than 15 minutes, refetch. Data-only; playback state untouched. */
  useEffect(() => {
    const BRIEF_STALE_MS = 15 * 60 * 1000;
    const handleResumeRefetch = () => {
      if (document.visibilityState !== "visible") return;
      if (Date.now() - briefFetchedAtRef.current < BRIEF_STALE_MS) return;
      briefFetchedAtRef.current = Date.now(); // debounce concurrent resumes
      fetchDailyBrief(edition).then((data) => {
        if (data) setBrief(data);
      });
    };
    document.addEventListener("visibilitychange", handleResumeRefetch);
    return () => document.removeEventListener("visibilitychange", handleResumeRefetch);
  }, [edition]);

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

  /* ---- Chapter rail ----------------------------------------------------
     The daily brief is a radio show with real chapters; weekly, history and
     every legacy episode are one continuous read. `chapters` is empty in that
     case and every surface falls back to the News / Opinion transport, so the
     null guard lives here once rather than in each player view. */
  const chapters = useMemo<AudioChapter[]>(
    () => brief?.audio_chapters ?? [],
    [brief?.audio_chapters]
  );

  const currentChapterIndex = useMemo(
    () => findChapterIndex(chapters, currentTime),
    [chapters, currentTime]
  );

  const seekToChapter = useCallback(
    (i: number) => {
      if (i < 0 || i >= chapters.length) return;
      seekTo(chapters[i].startTime);
    },
    [chapters, seekTo]
  );

  // Next / previous work off the PLAYHEAD, not off currentChapterIndex, so
  // they still do the obvious thing while the reader is in the ident, in the
  // sign-off, or anywhere else that sits between two chapters.
  const nextChapter = useCallback(() => {
    if (chapters.length === 0) return;
    let target = -1;
    let bestStart = Infinity;
    for (let i = 0; i < chapters.length; i++) {
      const st = chapters[i].startTime;
      if (st > currentTime + 0.25 && st < bestStart) {
        bestStart = st;
        target = i;
      }
    }
    if (target >= 0) seekTo(chapters[target].startTime);
  }, [chapters, currentTime, seekTo]);

  /** Podcast convention: restart the chapter, unless we only just entered it. */
  const RESTART_WINDOW = 3;
  const prevChapter = useCallback(() => {
    if (chapters.length === 0) return;
    const idx = findChapterIndex(chapters, currentTime);
    if (idx >= 0 && currentTime - chapters[idx].startTime > RESTART_WINDOW) {
      seekTo(chapters[idx].startTime);
      return;
    }
    const ref = idx >= 0 ? chapters[idx].startTime : currentTime;
    let target = -1;
    let bestStart = -Infinity;
    for (let i = 0; i < chapters.length; i++) {
      const st = chapters[i].startTime;
      if (st < ref - 0.25 && st > bestStart) {
        bestStart = st;
        target = i;
      }
    }
    seekTo(target >= 0 ? chapters[target].startTime : 0);
  }, [chapters, currentTime, seekTo]);

  // Auto-show player when brief has audio — DESKTOP ONLY. On mobile (<768px)
  // the auto-show is suppressed so nothing audio-related appears until the
  // reader taps the On Air tab. The brief TEXT (TL;DR / Opinion pill) still
  // loads and renders independently of this (see the fetch effect above).
  useEffect(() => {
    if (!brief?.audio_url) return;
    const isMobile =
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 767px)").matches;
    if (isMobile) return;
    setPlayerVisible(true);
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
      audio_chapters: episode.audio_chapters ?? null,
      news_start_seconds: episode.news_start_seconds ?? null,
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
        // Weekly is one continuous read: no chapter rail, so the player keeps
        // the original News / Opinion transport.
        audio_chapters: null,
        news_start_seconds: null,
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

  /** Load a void --history event's companion audio into the shared player.
   *  Mirrors playWeekly: maps the event onto the DailyBriefData shape the player
   *  consumes (history has no opinion firewall or host personas, so those are
   *  null → the transport renders a single "Account" section). Does NOT auto-play
   *  — it reveals the player ready to start, matching the daily/weekly behaviour.
   *  Taking ownership here also pauses any daily brief that was playing, so the
   *  news broadcast never continues on a history route. */
  const playHistory = useCallback((payload: HistoryAudioPayload) => {
    if (!payload.audioUrl) return;
    contentTypeRef.current = "history";
    setContentType("history");

    const audio = audioRef.current;
    if (audio) audio.pause();

    setBrief({
      id: payload.id,
      edition: "world" as DailyBriefData["edition"],
      tldr_text: payload.subtitle ?? "",
      tldr_headline: payload.title,
      opinion_text: null,
      opinion_headline: null,
      opinion_lean: null,
      opinion_cluster_id: null,
      audio_url: payload.audioUrl,
      audio_duration_seconds: payload.durationSeconds,
      opinion_start_seconds: null,
      audio_voice_label: null,
      audio_voice: null,
      audio_script: null,
      // History is a single narrated account: unchaptered.
      audio_chapters: null,
      news_start_seconds: null,
      top_cluster_ids: null,
      created_at: new Date().toISOString(),
    });
    setPreviousEpisodes([]);
    setCurrentTime(0);
    setDuration(payload.durationSeconds || 0);
    setBuffered(0);
    setAudioError(false);
    setIsPlaying(false);
    setPlayerVisible(true);
  }, []);

  /* Chapter navigation changes identity on every timeupdate (it reads the
     playhead), so the Media Session effect must NOT depend on it: rebuilding
     MediaMetadata four times a second flickers the lock screen and is pure
     waste. The handlers call through this ref instead. */
  const chapterNavRef = useRef({ next: nextChapter, prev: prevChapter });
  useEffect(() => {
    chapterNavRef.current = { next: nextChapter, prev: prevChapter };
  }, [nextChapter, prevChapter]);

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

    // On a chaptered episode the lock screen reads like a radio show: the
    // chapter is the track, the edition and date are the album. Between
    // chapters (ident, sign-off) it falls back to the show name rather than
    // freezing on whichever chapter ran last.
    const chapter =
      currentChapterIndex >= 0 ? chapters[currentChapterIndex] : null;
    const dateLabel = brief?.created_at
      ? new Date(brief.created_at).toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        })
      : "";

    navigator.mediaSession.metadata = new MediaMetadata(
      chapters.length > 0
        ? {
            title: chapter?.title || "On Air",
            artist: "Void News \u00b7 On Air",
            album: dateLabel
              ? `${editionLabel} Edition \u00b7 ${dateLabel}`
              : `${editionLabel} Edition`,
          }
        : {
            title: "On Air",
            artist: "Void News",
            album: editionLabel + " Edition",
          }
    );

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

    // Track skip = chapter skip, but only on a chaptered episode. Registering
    // a no-op handler would put dead next/previous buttons on the lock screen
    // of every legacy episode, so unchaptered audio clears them instead.
    if (chapters.length > 0) {
      try {
        navigator.mediaSession.setActionHandler("nexttrack", () => {
          chapterNavRef.current.next();
        });
        navigator.mediaSession.setActionHandler("previoustrack", () => {
          chapterNavRef.current.prev();
        });
      } catch {
        // Browser does not support track actions.
      }
    } else {
      try {
        navigator.mediaSession.setActionHandler("nexttrack", null);
        navigator.mediaSession.setActionHandler("previoustrack", null);
      } catch {}
    }

    return () => {
      try {
        navigator.mediaSession.setActionHandler("play", null);
        navigator.mediaSession.setActionHandler("pause", null);
        navigator.mediaSession.setActionHandler("seekbackward", null);
        navigator.mediaSession.setActionHandler("seekforward", null);
        navigator.mediaSession.setActionHandler("nexttrack", null);
        navigator.mediaSession.setActionHandler("previoustrack", null);
      } catch {}
    };
    // Deliberately NOT depending on nextChapter / prevChapter: see chapterNavRef.
  }, [
    edition,
    isPlaying,
    handlePlayPause,
    skipForward,
    skipBackward,
    chapters,
    currentChapterIndex,
    brief?.created_at,
  ]);

  /* ---- Media Session position state ----
     Throttled to ~1/s: currentTime updates about four times a second and
     setPositionState is not free. Guarded for browsers without it. */
  const lastPositionPush = useRef(0);
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
    if (typeof navigator.mediaSession.setPositionState !== "function") return;
    const total = brief?.audio_duration_seconds || duration;
    if (!total || !isFinite(total) || total <= 0) return;
    const now = Date.now();
    if (now - lastPositionPush.current < 1000) return;
    lastPositionPush.current = now;
    try {
      navigator.mediaSession.setPositionState({
        duration: total,
        playbackRate: playbackSpeed,
        position: Math.min(Math.max(currentTime, 0), total),
      });
    } catch {
      // Safari throws when position exceeds duration mid-load.
    }
  }, [currentTime, duration, playbackSpeed, brief?.audio_duration_seconds]);

  const value: AudioState = {
    brief,
    edition,
    setEdition,
    contentType,
    playWeekly,
    playHistory,
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
    chapters,
    currentChapterIndex,
    seekToChapter,
    nextChapter,
    prevChapter,
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
          /* Defer the MP3 fetch until the reader actually plays. "metadata"
             (the old value) fetched the file's header bytes on every home load
             even though the player auto-shows without interaction. "none" until
             first play means zero audio bytes on the initial render; the browser
             loads on demand when play() is called, then keeps metadata for the
             scrubber on subsequent renders. */
          preload={hasEverPlayed ? "metadata" : "none"}
          crossOrigin="anonymous"
          hidden
        />
      )}
    </AudioContext.Provider>
  );
}
