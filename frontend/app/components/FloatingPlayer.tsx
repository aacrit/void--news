"use client";

import { useState, useRef, useEffect, useMemo, useCallback, Fragment } from "react";
import type { DailyBriefState } from "./DailyBrief";
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

type PlayerView = "compact" | "expanded" | "broadcast";

export default function FloatingPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible,
  } = state;

  const [view, setView] = useState<PlayerView>("compact");
  const [closing, setClosing] = useState(false);

  // On mobile, skip compact pill (hidden via CSS) — open expanded directly
  useEffect(() => {
    if (!isPlayerVisible) return;
    const isMobile = window.matchMedia("(max-width: 767px)").matches;
    if (isMobile && view === "compact") {
      setView("expanded");
    }
  }, [isPlayerVisible, view]);
  const playerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rafRef = useRef<number>(0);
  const timeDomainRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const freqDataRef = useRef<Uint8Array<ArrayBuffer> | null>(null);
  const trailRef = useRef<number[]>([]);
  const peakRef = useRef<{ level: number; time: number }>({ level: 0, time: 0 });
  const colorsRef = useRef<{
    bg: string; trace: string; grid: string; accent: string; hot: string; isDark: boolean;
  } | null>(null);

  /* ---- Broadcast Monitor: frequency band + phosphor trace + signal meter ---- */
  const drawBroadcastMonitor = useCallback(() => {
    const canvas = canvasRef.current;
    const analyser = state.analyserRef?.current;
    if (!canvas || !analyser) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // HiDPI scaling
    const rect = canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.scale(dpr, dpr);
      colorsRef.current = null;
    }

    const w = rect.width;
    const h = rect.height;

    // Cache CSS colors
    if (!colorsRef.current) {
      const s = getComputedStyle(canvas);
      const bg = s.getPropertyValue("--console-bg").trim() || "#EBE5D6";
      const isDark = bg.startsWith("#1") || bg.startsWith("#0") || bg.startsWith("#2");
      colorsRef.current = {
        bg,
        trace: isDark ? (s.getPropertyValue("--voice-accent").trim() || "#4DAFA0") : (s.getPropertyValue("--accent-warm").trim() || "#946B15"),
        grid: isDark ? "rgba(237,232,224,0.06)" : "rgba(42,37,32,0.07)",
        accent: s.getPropertyValue("--accent-warm").trim() || "#946B15",
        hot: s.getPropertyValue("--indicator-broadcast").trim() || "#c0392b",
        isDark,
      };
    }
    const { bg, trace, grid, accent, hot, isDark } = colorsRef.current;

    // Zone layout
    const eqH = 24;          // frequency band
    const meterH = 32;       // signal meter
    const traceY = eqH + 2;  // phosphor trace start
    const traceH = h - eqH - meterH - 4; // remaining space
    const meterY = h - meterH;

    // Get audio data
    if (!timeDomainRef.current || timeDomainRef.current.length !== analyser.fftSize) {
      timeDomainRef.current = new Uint8Array(analyser.fftSize);
    }
    const freqBins = analyser.frequencyBinCount;
    if (!freqDataRef.current || freqDataRef.current.length !== freqBins) {
      freqDataRef.current = new Uint8Array(freqBins);
    }
    analyser.getByteTimeDomainData(timeDomainRef.current);
    analyser.getByteFrequencyData(freqDataRef.current);

    // RMS amplitude for signal meter
    let rmsSum = 0;
    const td = timeDomainRef.current;
    for (let i = 0; i < td.length; i++) {
      const v = (td[i] - 128) / 128;
      rmsSum += v * v;
    }
    const rms = Math.sqrt(rmsSum / td.length);
    const rmsNorm = Math.min(1, rms * 3.5); // scale up for visual range

    // Trail amplitude (center 64 samples)
    const mid = Math.floor(td.length / 2);
    let ampSum = 0;
    for (let i = mid - 32; i < mid + 32; i++) ampSum += td[i];
    const amplitude = (ampSum / 64) / 255;

    // Trail buffer
    const trailLen = Math.floor(w - 20); // leave room for dB scale
    if (trailRef.current.length !== trailLen) {
      trailRef.current = new Array(trailLen).fill(0.5);
    }
    trailRef.current.shift();
    trailRef.current.push(amplitude);

    // Peak hold (1.5s decay)
    const now = performance.now();
    if (rmsNorm >= peakRef.current.level) {
      peakRef.current = { level: rmsNorm, time: now };
    } else if (now - peakRef.current.time > 1500) {
      peakRef.current.level = Math.max(rmsNorm, peakRef.current.level - 0.02);
    }

    // ══════════════════════════════════════════════
    // CLEAR
    // ══════════════════════════════════════════════
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, w, h);

    // ══════════════════════════════════════════════
    // ZONE 1: FREQUENCY BAND (top 24px)
    // ══════════════════════════════════════════════
    const numBars = 24;
    const barGap = 2;
    const barW = (w - (numBars - 1) * barGap) / numBars;
    const fd = freqDataRef.current;
    const binsPerBar = Math.floor(freqBins / numBars);

    for (let b = 0; b < numBars; b++) {
      // Average frequency bins for this bar (logarithmic-ish: weight lower frequencies)
      let barSum = 0;
      const startBin = Math.floor(b * b * freqBins / (numBars * numBars)); // quadratic mapping
      const endBin = Math.floor((b + 1) * (b + 1) * freqBins / (numBars * numBars));
      const count = Math.max(1, endBin - startBin);
      for (let i = startBin; i < endBin && i < freqBins; i++) barSum += fd[i];
      const barNorm = (barSum / count) / 255;

      const barHeight = barNorm * (eqH - 4);
      const bx = b * (barW + barGap);
      const by = eqH - 2 - barHeight;

      ctx.fillStyle = trace;
      ctx.globalAlpha = 0.6 + barNorm * 0.3;
      ctx.beginPath();
      ctx.roundRect(bx, by, barW, barHeight, 1);
      ctx.fill();
    }
    ctx.globalAlpha = 1;

    // Separator line
    ctx.strokeStyle = grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, eqH);
    ctx.lineTo(w, eqH);
    ctx.stroke();

    // ══════════════════════════════════════════════
    // ZONE 2: PHOSPHOR TRACE (middle)
    // ══════════════════════════════════════════════
    const pad = 8;
    const traceLeft = 18; // room for dB labels

    // Grid lines
    ctx.strokeStyle = grid;
    ctx.lineWidth = 0.5;
    ctx.setLineDash([2, 3]);
    for (let i = 1; i <= 4; i++) {
      const gy = traceY + (traceH * i) / 5;
      ctx.beginPath();
      ctx.moveTo(traceLeft, gy);
      ctx.lineTo(w, gy);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    // dB scale labels (left edge)
    ctx.fillStyle = trace;
    ctx.globalAlpha = 0.3;
    ctx.font = "7px 'IBM Plex Mono', monospace";
    ctx.textAlign = "right";
    const dbLabels = ["+3", "0", "-6", "-20"];
    for (let i = 0; i < dbLabels.length; i++) {
      const ly = traceY + pad + (i / (dbLabels.length - 1)) * (traceH - pad * 2);
      ctx.fillText(dbLabels[i], traceLeft - 3, ly + 3);
    }
    ctx.globalAlpha = 1;

    // Phosphor trace with persistence decay
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    const trail = trailRef.current;
    const fadeStart = Math.floor(trail.length * 0.4); // oldest 40% fades

    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (let i = 0; i < trail.length; i++) {
      const x = traceLeft + (i / trail.length) * (w - traceLeft);
      const y = traceY + pad + trail[i] * (traceH - pad * 2);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    // Persistence: draw segments with fading alpha
    ctx.strokeStyle = trace;
    ctx.globalAlpha = 0.7;
    ctx.stroke();

    // Glow on the newest 30% of trail
    ctx.save();
    ctx.beginPath();
    const glowStart = Math.floor(trail.length * 0.7);
    for (let i = glowStart; i < trail.length; i++) {
      const x = traceLeft + (i / trail.length) * (w - traceLeft);
      const y = traceY + pad + trail[i] * (traceH - pad * 2);
      if (i === glowStart) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = trace;
    ctx.globalAlpha = 0.15;
    ctx.lineWidth = 5;
    ctx.filter = "blur(3px)";
    ctx.stroke();
    ctx.filter = "none";
    ctx.restore();
    ctx.globalAlpha = 1;

    // Cursor dot at write position
    const cursorX = traceLeft + ((trail.length - 1) / trail.length) * (w - traceLeft);
    const cursorY = traceY + pad + amplitude * (traceH - pad * 2);
    ctx.fillStyle = trace;
    ctx.globalAlpha = 0.9;
    ctx.beginPath();
    ctx.arc(cursorX, cursorY, 3, 0, Math.PI * 2);
    ctx.fill();
    // Cursor glow
    ctx.globalAlpha = 0.3;
    ctx.beginPath();
    ctx.arc(cursorX, cursorY, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalAlpha = 1;

    // Separator
    ctx.strokeStyle = grid;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, meterY - 2);
    ctx.lineTo(w, meterY - 2);
    ctx.stroke();

    // ══════════════════════════════════════════════
    // ZONE 3: SIGNAL METER (bottom 32px)
    // ══════════════════════════════════════════════
    const meterPad = 4;
    const meterLeft = 18;
    const meterRight = w - 4;
    const meterW = meterRight - meterLeft;
    const numBlocks = 30;
    const blockGap = 1.5;
    const blockW = (meterW - (numBlocks - 1) * blockGap) / numBlocks;
    const blockH = meterH - meterPad * 2 - 8; // leave room for labels
    const blockY = meterY + meterPad;
    const threshold = Math.floor(numBlocks * 0.8); // -6dB at 80%

    for (let b = 0; b < numBlocks; b++) {
      const bx = meterLeft + b * (blockW + blockGap);
      const filled = (b + 1) / numBlocks <= rmsNorm;
      const isHot = b >= threshold;

      if (filled) {
        ctx.fillStyle = isHot ? hot : accent;
        ctx.globalAlpha = 0.8;
      } else {
        ctx.fillStyle = isHot ? hot : accent;
        ctx.globalAlpha = 0.08;
      }
      ctx.fillRect(bx, blockY, blockW, blockH);
    }

    // Peak hold ghost
    const peakBlock = Math.min(numBlocks - 1, Math.floor(peakRef.current.level * numBlocks));
    if (peakBlock > 0) {
      const px = meterLeft + peakBlock * (blockW + blockGap);
      ctx.fillStyle = peakBlock >= threshold ? hot : accent;
      ctx.globalAlpha = 0.5;
      ctx.fillRect(px, blockY, blockW, blockH);
    }
    ctx.globalAlpha = 1;

    // -6dB threshold mark
    const threshX = meterLeft + threshold * (blockW + blockGap) - blockGap / 2;
    ctx.strokeStyle = hot;
    ctx.globalAlpha = 0.25;
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);
    ctx.beginPath();
    ctx.moveTo(threshX, blockY - 1);
    ctx.lineTo(threshX, blockY + blockH + 1);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;

    // Meter labels
    ctx.fillStyle = trace;
    ctx.globalAlpha = 0.3;
    ctx.font = "7px 'IBM Plex Mono', monospace";
    ctx.textAlign = "left";
    ctx.fillText("-20", meterLeft, meterY + meterH - 3);
    ctx.textAlign = "center";
    ctx.fillText("-6", threshX, meterY + meterH - 3);
    ctx.textAlign = "right";
    ctx.fillText("+3", meterRight, meterY + meterH - 3);
    ctx.globalAlpha = 1;
  }, [state.analyserRef]);

  useEffect(() => {
    if (!isPlaying) {
      cancelAnimationFrame(rafRef.current);
      // Draw powered-down state: dark canvas with faint grid
      const canvas = canvasRef.current;
      if (canvas) {
        const ctx = canvas.getContext("2d");
        if (ctx) {
          const rect = canvas.getBoundingClientRect();
          const dpr = window.devicePixelRatio || 1;
          if (canvas.width !== rect.width * dpr || canvas.height !== rect.height * dpr) {
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            ctx.scale(dpr, dpr);
          }
          const s = getComputedStyle(canvas);
          const bg = s.getPropertyValue("--console-bg").trim() || "#EBE5D6";
          ctx.fillStyle = bg;
          ctx.fillRect(0, 0, rect.width, rect.height);
        }
      }
      return;
    }

    const prefersReduced = typeof window !== "undefined"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    let lastFrame = 0;
    const loop = (timestamp: number) => {
      if (timestamp - lastFrame > 33) {
        lastFrame = timestamp;
        drawBroadcastMonitor();
      }
      rafRef.current = requestAnimationFrame(loop);
    };
    rafRef.current = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(rafRef.current);
  }, [isPlaying, drawBroadcastMonitor]);

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

          {/* Oscilloscope — real-time audio waveform */}
          <canvas ref={canvasRef} className="fp__oscilloscope" aria-hidden="true" />

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

          {/* VU arc motif — decorative 120° arc behind header */}
          <svg className="fp__vu-arc" viewBox="0 0 200 60" aria-hidden="true">
            <path d="M30 55 A70 70 0 0 1 170 55" fill="none" stroke="currentColor" strokeWidth="1.5" />
            {/* Frequency hash marks */}
            {Array.from({ length: 9 }, (_, i) => {
              const angle = Math.PI - (Math.PI * (i + 1)) / 10;
              const cx = 100 + 70 * Math.cos(angle);
              const cy = 55 - 70 * Math.sin(angle);
              const dx = 4 * Math.cos(angle);
              const dy = -4 * Math.sin(angle);
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

          {/* Oscilloscope — hero element in broadcast pane */}
          <canvas ref={canvasRef} className="fp__oscilloscope fp__oscilloscope--hero" aria-hidden="true" />

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
        </div>
      )}
    </div>
  );
}
