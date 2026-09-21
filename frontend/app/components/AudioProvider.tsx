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
import type { AudioChapter, DailyBriefData } from "../lib/types";
import { findChapterIndex } from "../lib/chapters";
import {
  type Episode,
  type HistoryAudioPayload,
  type ProgrammeKind,
  decidePress,
  editionLabelFor,
  episodeFromBrief,
  episodeFromHistory,
  episodeFromWeekly,
  mayTakeOver,
  sameEpisode,
} from "../lib/episode";
import { fetchDailyBrief, fetchPreviousEpisodes } from "../lib/supabase";
import { hapticLight, hapticTick } from "../lib/haptics";
import { AUDIO_ENABLED } from "../lib/audioGate";

/* ---------------------------------------------------------------------------
   AudioProvider — the one audio state for Void News.
   Wraps layout.tsx so <audio> survives page navigation.

   TWO SLOTS, and the difference is the whole design (2026-09-21):

   - `dailyBrief` is today's edition. The daily fetch owns it and NO programme
     may write it, so every surface that means "today" (the skybox, the mobile
     brief pill, /onair's edition dateline) is always right.
   - `nowPlaying` is an Episode: what is in the element, whoever made it. The
     transport labels, the chapter rail and the <audio> src all read it.

   Before the split there was one `brief` slot that three programmes wrote
   into, and it produced every one of these, each measured in a browser:
   /onair announced a History documentary as "World Edition · ON AIR"; opening
   the Weekly issue paused a playing brief and swapped the source with no
   gesture; returning home detached a playing documentary; a tab resume put
   the daily brief under a player still labelled Weekly; and a pause that came
   from outside React (a call, a Bluetooth drop) left every live dot lit,
   because isPlaying was an optimistic guess rather than the element's truth.

   Two rules follow, and the gates in scripts/verify-headless.mjs hold them:
   1. ONE PRESS RULE. `play(ep)` toggles when it already owns that episode and
      loads then plays when it does not, so every play button in the product
      behaves the same (see decidePress in lib/episode.ts).
   2. A NAVIGATION NEVER STOPS PLAYBACK. `load(ep)` reveals without autoplay
      and refuses to interrupt something that is playing (mayTakeOver), so a
      page that merely renders can offer its programme but never seize it.
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

/* Re-exported so the history surfaces keep importing it from here. */
export type { HistoryAudioPayload, Episode, ProgrammeKind };

export interface AudioState {
  /** TODAY'S EDITION. Never another programme's episode: read this for "the
   *  brief", and `nowPlaying` for "what is playing". */
  brief: DailyBriefData | null;
  /** What is loaded in the element, whoever made it. null when nothing is. */
  nowPlaying: Episode | null;
  edition: string;
  setEdition: (ed: string) => void;
  /** Which programme owns the player. Derived from `nowPlaying`, so it can no
   *  longer disagree with what is actually loaded. */
  contentType: ProgrammeKind;
  /** THE one press: toggles when it owns this episode, loads and plays when
   *  it does not. Every play button in the product calls this. `startAt` lets
   *  a chapter or a section start an episode that is not loaded yet. */
  play: (ep: Episode, opts?: { startAt?: number }) => void;
  /** Reveal an episode without autoplay. Refuses to interrupt playback, so a
   *  page may offer its programme on mount without seizing the player. Pass
   *  `interrupt` only for a deliberate press. */
  load: (ep: Episode, opts?: { interrupt?: boolean }) => void;
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
  /* ---- Chapter rail ----
     Read off `nowPlaying`, so the rail always belongs to the audio in the
     element. Empty on a legacy episode: every consumer treats an empty rail as
     "keep the old News / Opinion transport", so the null guard lives here once
     rather than in each player view. */
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

const SPEEDS = [1, 1.25, 1.5, 2] as const;

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
  /* TODAY'S EDITION. Only the daily fetch writes this. */
  const [dailyBrief, setDailyBrief] = useState<DailyBriefData | null>(initialBrief);
  /* WHAT IS PLAYING. Seeded from the daily brief when the player is idle. */
  const [nowPlaying, setNowPlaying] = useState<Episode | null>(() =>
    AUDIO_ENABLED ? episodeFromBrief(initialBrief) : null
  );
  // Timestamp of the last successful brief fetch — drives the resume-refetch
  // staleness check (see the visibilitychange effect below). Seeded to "now"
  // when the build handed us a brief: at 0 the very first resume always
  // refetched, whoever owned the player.
  const briefFetchedAtRef = useRef<number>(0);
  /* Seeded on mount rather than during render (Date.now() is impure): at 0
     the very first tab resume always refetched, whoever owned the player. */
  useEffect(() => {
    if (initialBrief != null && briefFetchedAtRef.current === 0) {
      briefFetchedAtRef.current = Date.now();
    }
  }, [initialBrief]);
  // True until the seeded brief has satisfied the first edition-fetch effect
  // run, so we keep the build-time brief instead of clearing + refetching it.
  const seededRef = useRef<boolean>(initialBrief != null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const [buffered, setBuffered] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(() => {
    if (typeof window === "undefined") return 1;
    try {
      // Validated against the ladder: an unparseable or hand-edited value used
      // to reach audio.playbackRate as NaN and silence the element.
      const stored = Number(localStorage.getItem("void-onair-speed"));
      return (SPEEDS as readonly number[]).includes(stored) ? stored : 1;
    } catch {
      return 1;
    }
  });
  const [isPlayerVisible, setPlayerVisible] = useState(false);
  const [isExpanded, setExpanded] = useState(false);
  const [hasEverPlayed, setHasEverPlayed] = useState(false);
  const [previousEpisodes, setPreviousEpisodes] = useState<EpisodeMeta[]>([]);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  /* Ownership is DERIVED, not stored. The old `contentType` state plus its ref
     mirror could disagree with the audio in the element; this cannot. */
  const contentType: ProgrammeKind = nowPlaying?.kind ?? "daily";

  /* The live episode, for callbacks that must not re-subscribe on every
     change (the element listeners, the press rule, the Media Session). */
  const nowPlayingRef = useRef<Episode | null>(nowPlaying);
  useEffect(() => {
    nowPlayingRef.current = nowPlaying;
  }, [nowPlaying]);
  const isPlayingRef = useRef(false);
  useEffect(() => {
    isPlayingRef.current = isPlaying;
  }, [isPlaying]);

  /* May today's broadcast take the player? Only when the player is EMPTY, or
     when it already holds a daily episode the reader is not listening to (the
     stale-brief self-heal, which exists to replace yesterday's edition with
     today's). A paused episode of another programme is a reader's place in it,
     not an idle player: swapping it out would lose their position. */
  const maySeed = useCallback(
    (ep: Episode) => {
      const cur = nowPlayingRef.current;
      if (!cur) return true;
      if (sameEpisode(cur, ep)) return false;
      return cur.kind === "daily" && !isPlayingRef.current;
    },
    []
  );
  const maySeedRef = useRef(maySeed);
  useEffect(() => {
    maySeedRef.current = maySeed;
  }, [maySeed]);

  /* Public setEdition: sets the edition and nothing else. It used to claim
     ownership of the player for the daily programme, which is why merely
     opening the front page detached a playing documentary. */
  const setEdition = useCallback((ed: string) => {
    setEditionState(ed);
  }, []);

  /* ---- Web Audio API: real-time analyser for oscilloscope ---- */
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const connectedElements = useRef<WeakSet<HTMLAudioElement>>(new WeakSet());

  /* ---- Fetch today's edition when the edition changes ----
     This writes `dailyBrief` ONLY. It never touches the element and never
     touches `nowPlaying`, so a refetch cannot swap the source under a reader
     who is listening to something else. When the player is idle it seeds
     `nowPlaying` with today's broadcast, so the pill still comes up ready. */
  useEffect(() => {
    let cancelled = false;

    // First mount with a build-time seeded brief: keep it. Refetching here would
    // clear the brief to null (flashing "Loading today's brief…") and could
    // produce a hydration-time first paint that differs from the server render
    // (React #418). We still load the audio playlist. Any later edition change
    // falls through to a normal refetch.
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

    // TL;DR + opinion are editorial TEXT, not audio: they must load even when
    // the void --onair kill switch is on. Only the audio playback layer
    // (previous-episode list + <audio> mount) is gated by AUDIO_ENABLED.
    // Coupling this fetch to the kill switch left SkyboxBanner / MobileBriefPill
    // stuck on "Loading today's brief…" whenever audio was disabled.
    fetchDailyBrief(edition).then((data) => {
      if (cancelled) return;
      setDailyBrief(data);
      briefFetchedAtRef.current = Date.now();
      const ep = AUDIO_ENABLED ? episodeFromBrief(data) : null;
      if (ep && maySeedRef.current(ep)) setNowPlaying(ep);
    });

    if (AUDIO_ENABLED) {
      fetchPreviousEpisodes(edition).then((data) => {
        if (!cancelled) setPreviousEpisodes(data);
      });
    }
    return () => {
      cancelled = true;
    };
  }, [edition]);

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
    /* THE ELEMENT IS THE TRUTH about whether sound is coming out. `play`,
       `pause` and `ended` are the only writers of isPlaying. Without them a
       pause from outside React — an incoming call, a Bluetooth disconnect, an
       autoplay rejection, the OS — left the pill showing a pause icon, the tab
       bar's live dot lit and the wordmark beam rocking over silence, and the
       next press then paused an element that was already paused. */
    const onPlay = () => {
      setIsPlaying(true);
      setHasEverPlayed(true);
      setAudioError(false);
    };
    const onPause = () => setIsPlaying(false);
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
    el.addEventListener("play", onPlay);
    el.addEventListener("playing", onPlay);
    el.addEventListener("pause", onPause);
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
      el.removeEventListener("play", onPlay);
      el.removeEventListener("playing", onPlay);
      el.removeEventListener("pause", onPause);
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
     older than 15 minutes, refetch.

     It writes `dailyBrief` and NOTHING else. It used to write the single
     `brief` slot: backgrounding the tab on /weekly and returning swapped the
     element's source back to the daily MP3 and stopped it, while every
     surface still said Weekly, playing (measured 2026-09-21). */
  useEffect(() => {
    const BRIEF_STALE_MS = 15 * 60 * 1000;
    const handleResumeRefetch = () => {
      if (document.visibilityState !== "visible") return;
      if (Date.now() - briefFetchedAtRef.current < BRIEF_STALE_MS) return;
      briefFetchedAtRef.current = Date.now(); // debounce concurrent resumes
      fetchDailyBrief(edition).then((data) => {
        if (!data) return;
        setDailyBrief(data);
        const ep = AUDIO_ENABLED ? episodeFromBrief(data) : null;
        if (ep && maySeedRef.current(ep)) setNowPlaying(ep);
      });
    };
    document.addEventListener("visibilitychange", handleResumeRefetch);
    return () => document.removeEventListener("visibilitychange", handleResumeRefetch);
  }, [edition]);

  /* ---- Transport ------------------------------------------------------- */

  /** Start the element. isPlaying is not set here: the `play` listener does
   *  that, so the UI only ever claims to play once the element really does. */
  const startPlayback = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (audioError) {
      setAudioError(false);
      audio.load();
    }
    // Resume AudioContext for iOS Safari
    if (audioContextRef.current?.state === "suspended") {
      audioContextRef.current.resume();
    }
    audio.play().catch(() => {
      setAudioError(true);
      setIsPlaying(false);
    });
  }, [audioError]);

  const handlePlayPause = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    if (isPlaying) audio.pause();
    else startPlayback();
  }, [isPlaying, getAudio, startPlayback]);

  /* Set when a press asks for playback on an episode that is not in the
     element yet: React swaps the <audio> src on the next commit, and this
     effect plays it once the new source is attached. Setting src imperatively
     instead would fire a second request for a file we are about to mount. */
  const playOnLoadRef = useRef<{ url: string; startAt: number } | null>(null);
  /* `seekTo` is declared below (it needs startPlayback), so `play` reaches it
     through a ref rather than being reordered around it. */
  const seekToRef = useRef<(seconds: number) => void>(() => {});

  /** Reveal an episode. Never autoplays; refuses to interrupt live audio
   *  unless the caller says this came from a press. */
  const load = useCallback((ep: Episode, opts?: { interrupt?: boolean }) => {
    if (!ep.audioUrl) return;
    if (sameEpisode(nowPlayingRef.current, ep)) {
      setPlayerVisible(true);
      return;
    }
    if (!opts?.interrupt && !mayTakeOver(nowPlayingRef.current, isPlayingRef.current, ep)) {
      return;
    }
    const audio = audioRef.current;
    if (audio) audio.pause();
    nowPlayingRef.current = ep;
    setNowPlaying(ep);
    setCurrentTime(0);
    setDuration(ep.durationSeconds || 0);
    setBuffered(0);
    setAudioError(false);
    setIsPlaying(false);
    setPlayerVisible(true);
  }, []);

  /** THE one press. Toggles when it already owns this episode, loads and
   *  plays when it does not. Before this rule, the same button played an
   *  already-loaded issue and merely loaded a History episode, so "Play"
   *  produced silence (measured 2026-09-21). */
  const play = useCallback(
    (ep: Episode, opts?: { startAt?: number }) => {
      if (!ep.audioUrl) return;
      if (decidePress(nowPlayingRef.current, ep) === "toggle") {
        if (opts?.startAt != null) {
          seekToRef.current(opts.startAt);
          return;
        }
        handlePlayPause();
        return;
      }
      hapticLight();
      playOnLoadRef.current = { url: ep.audioUrl, startAt: opts?.startAt ?? 0 };
      load(ep, { interrupt: true });
    },
    [handlePlayPause, load]
  );

  /* Play the episode a press asked for, once its source is in the element. */
  useEffect(() => {
    const wanted = playOnLoadRef.current;
    if (!wanted || !nowPlaying || nowPlaying.audioUrl !== wanted.url) return;
    playOnLoadRef.current = null;
    const audio = audioRef.current;
    if (!audio) return;
    if (wanted.startAt > 0) {
      /* The element has the new src but no metadata yet; currentTime only
         sticks once it is seekable, so set it on loadedmetadata when needed. */
      /* No setState here: seeking fires `timeupdate`, and the element's own
         listener is the one writer of currentTime. */
      const seek = () => {
        try { audio.currentTime = wanted.startAt; } catch {}
      };
      if (audio.readyState >= 1) seek();
      else audio.addEventListener("loadedmetadata", seek, { once: true });
    }
    startPlayback();
  }, [nowPlaying, startPlayback]);

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

  // Apply saved speed when the loaded episode changes
  useEffect(() => {
    const audio = audioRef.current;
    if (audio && playbackSpeed !== 1) audio.playbackRate = playbackSpeed;
  }, [nowPlaying, playbackSpeed]);

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
      if (!isPlaying) startPlayback();
    },
    [isPlaying, getAudio, startPlayback]
  );

  useEffect(() => {
    seekToRef.current = seekTo;
  }, [seekTo]);

  /* ---- Chapter rail ----
     Off `nowPlaying`, so the rail belongs to the audio in the element. It used
     to come off the single brief slot, which is how /onair showed the daily
     broadcast's eight chapters over a Weekly issue's eleven movements. */
  const chapters = useMemo<AudioChapter[]>(
    () => nowPlaying?.chapters ?? [],
    [nowPlaying]
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

  // Auto-show the player once something is loaded — DESKTOP ONLY. On mobile
  // (<768px) the auto-show is suppressed so nothing audio-related appears
  // until the reader asks for it. The brief TEXT (TL;DR / Opinion pill) still
  // loads and renders independently of this (see the fetch effect above).
  useEffect(() => {
    if (!nowPlaying) return;
    const isMobile =
      typeof window !== "undefined" &&
      window.matchMedia("(max-width: 767px)").matches;
    if (isMobile) return;
    setPlayerVisible(true);
  }, [nowPlaying]);

  /** Load a previous episode from an archive row. A press, so it plays. */
  const loadEpisode = useCallback(
    (episode: EpisodeMeta) => {
      if (!episode.audio_url) return;
      play({
        kind: "daily",
        id: episode.id,
        title: episode.tldr_headline ?? "Broadcast",
        subtitle: null,
        audioUrl: episode.audio_url,
        durationSeconds: Number(episode.audio_duration_seconds) || 0,
        chapters: episode.audio_chapters ?? [],
        publishedAt: episode.created_at ?? null,
        programmeLabel: "On Air",
        editionLabel: editionLabelFor(episode.edition),
        voiceLabel: episode.audio_voice_label ?? null,
        opinionStartSeconds: episode.opinion_start_seconds ?? null,
      });
    },
    [play]
  );

  /** Offer a weekly issue to the player. Called from the issue page on mount,
   *  so it must NOT seize: `load` leaves live audio alone. The optional
   *  archiveIssues become the "Previous issues" playlist. */
  const playWeekly = useCallback(
    (
      digest: import("../lib/types").WeeklyDigestData,
      archiveIssues?: EpisodeMeta[]
    ) => {
      const ep = episodeFromWeekly(digest);
      if (!ep) return;
      if (archiveIssues && archiveIssues.length > 0) setPreviousEpisodes(archiveIssues);
      load(ep);
    },
    [load]
  );

  /** A History event's Listen control: a press, so it plays and a second
   *  press pauses instead of restarting the documentary from zero. */
  const playHistory = useCallback(
    (payload: HistoryAudioPayload) => {
      const ep = episodeFromHistory(payload);
      if (!ep) return;
      play(ep);
    },
    [play]
  );

  /* Chapter navigation changes identity on every timeupdate (it reads the
     playhead), so the Media Session effect must NOT depend on it: rebuilding
     MediaMetadata four times a second flickers the lock screen and is pure
     waste. The handlers call through this ref instead. */
  const chapterNavRef = useRef({ next: nextChapter, prev: prevChapter });
  useEffect(() => {
    chapterNavRef.current = { next: nextChapter, prev: prevChapter };
  }, [nextChapter, prevChapter]);

  /* ---- Media Session API — iOS lock screen + notification controls ----
     Off `nowPlaying`, so the lock screen names the programme that is playing.
     It used to hardcode "Void News · On Air" and an edition label for every
     programme, and date a 1258 documentary today. */
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator))
      return;
    if (!nowPlaying) return;

    // On a chaptered episode the lock screen reads like a radio show: the
    // chapter is the track, the programme and date are the album. Between
    // chapters (ident, sign-off) it falls back to the episode title rather
    // than freezing on whichever chapter ran last.
    const chapter =
      currentChapterIndex >= 0 ? chapters[currentChapterIndex] : null;
    const dateLabel = nowPlaying.publishedAt
      ? new Date(nowPlaying.publishedAt).toLocaleDateString("en-US", {
          month: "long",
          day: "numeric",
          year: "numeric",
        })
      : "";
    const album = [
      nowPlaying.editionLabel ? `${nowPlaying.editionLabel} Edition` : nowPlaying.programmeLabel,
      dateLabel,
    ]
      .filter(Boolean)
      .join(" · ");

    navigator.mediaSession.metadata = new MediaMetadata({
      title: chapters.length > 0 ? chapter?.title || nowPlaying.title : nowPlaying.title,
      artist: `Void News · ${nowPlaying.programmeLabel}`,
      album,
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
    nowPlaying,
    isPlaying,
    handlePlayPause,
    skipForward,
    skipBackward,
    chapters,
    currentChapterIndex,
  ]);

  /* ---- Media Session position state ----
     Throttled to ~1/s: currentTime updates about four times a second and
     setPositionState is not free. Guarded for browsers without it. */
  const lastPositionPush = useRef(0);
  useEffect(() => {
    if (typeof navigator === "undefined" || !("mediaSession" in navigator)) return;
    if (typeof navigator.mediaSession.setPositionState !== "function") return;
    const total = nowPlaying?.durationSeconds || duration;
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
  }, [currentTime, duration, playbackSpeed, nowPlaying]);

  /* Memoized: the value object used to be rebuilt on every render, so every
     useAudio() consumer — including NavBar, MobileTabBar and MobileNav, which
     each need one boolean — re-rendered four times a second on timeupdate. */
  const value = useMemo<AudioState>(
    () => ({
      brief: dailyBrief,
      nowPlaying,
      edition,
      setEdition,
      contentType,
      play,
      load,
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
    }),
    [
      dailyBrief, nowPlaying, edition, setEdition, contentType, play, load,
      playWeekly, playHistory, isPlaying, currentTime, duration, buffered,
      audioError, handlePlayPause, handleSeek, playbackSpeed, cycleSpeed,
      skipForward, skipBackward, seekTo, isPlayerVisible, isExpanded,
      connectAnalyser, hasEverPlayed, previousEpisodes, loadEpisode, chapters,
      currentChapterIndex, seekToChapter, nextChapter, prevChapter,
    ]
  );

  return (
    <AudioContext.Provider value={value}>
      {children}
      {/* The one <audio> element — survives page navigation. Its src is the
          LOADED EPISODE, not the daily brief, so refreshing today's edition
          can never swap the file under a reader listening to something else.
          Gated by the audio kill switch (void --onair parked): when audio is
          disabled the element is never rendered and no .mp3 is requested. */}
      {AUDIO_ENABLED && nowPlaying?.audioUrl && (
        <audio
          ref={audioCallbackRef}
          src={nowPlaying.audioUrl}
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
