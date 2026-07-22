'use client';

import { useRef, useState } from 'react';

function fmt(s: number): string {
  if (!isFinite(s) || s < 0) s = 0;
  const m = Math.floor(s / 60);
  const ss = Math.floor(s % 60);
  return `${m}:${String(ss).padStart(2, '0')}`;
}

const PlayIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M7 5v14l11-7z" fill="currentColor" /></svg>
);
const PauseIcon = () => (
  <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path d="M6 5h4v14H6zM14 5h4v14h-4z" fill="currentColor" /></svg>
);

/* Self-contained narrated-anatomy player (local <audio>, like HistoryAudioCue).
   The section-wide "onair" floating player is for the daily brief only. */
export default function RevoltAudioCue({
  audioUrl,
  durationSeconds,
  title,
}: {
  audioUrl: string;
  durationSeconds: number;
  title: string;
}) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [cur, setCur] = useState(0);
  const [dur, setDur] = useState(durationSeconds || 0);

  const toggle = () => {
    const a = audioRef.current;
    if (!a) return;
    if (playing) a.pause();
    else a.play().catch(() => {});
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const a = audioRef.current;
    if (!a || !dur) return;
    const rect = e.currentTarget.getBoundingClientRect();
    a.currentTime = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)) * dur;
  };

  return (
    <div className="rev-audio">
      <audio
        ref={audioRef}
        src={audioUrl}
        preload="metadata"
        crossOrigin="anonymous"
        hidden
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
        onTimeUpdate={() => setCur(audioRef.current?.currentTime ?? 0)}
        onLoadedMetadata={() => setDur(audioRef.current?.duration || durationSeconds || 0)}
      />
      <button
        type="button"
        className="rev-audio__btn"
        onClick={toggle}
        aria-label={playing ? `Pause ${title}` : `Listen to ${title}`}
      >
        {playing ? <PauseIcon /> : <PlayIcon />}
      </button>
      <div className="rev-audio__body">
        <div className="rev-audio__label">void --onair &middot; narrated anatomy</div>
        <div className="rev-audio__track" onClick={seek} role="progressbar" aria-valuenow={Math.round(cur)} aria-valuemax={Math.round(dur)}>
          <span className="rev-audio__fill" style={{ width: dur ? `${(cur / dur) * 100}%` : '0%' }} />
        </div>
      </div>
      <div className="rev-audio__time">{fmt(cur)} / {fmt(dur)}</div>
    </div>
  );
}
