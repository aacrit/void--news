"use client";

import { useMemo } from "react";
import { useAudio, type EpisodeMeta } from "./AudioProvider";
import { hapticLight, hapticMicro } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   OnAirPage — dedicated void --onair broadcast interface (/onair).

   The mobile tab bar routes here instead of toggling the floating player, so
   on-air has a real home: now-playing transport, news/opinion chapter jumps,
   show notes (TL;DR + opinion), and the previous-episodes archive. All state
   comes from the global <AudioProvider> (useAudio) — this is a view, not a
   second player, so playback survives navigation and stays in sync with the
   mini-player.
   --------------------------------------------------------------------------- */

function fmt(s: number): string {
  if (!isFinite(s) || s < 0) s = 0;
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, "0")}`;
}

const LEAN_LABEL: Record<string, string> = {
  left: "Left",
  "center-left": "Center-left",
  center: "Center",
  "center-right": "Center-right",
  right: "Right",
};

function episodeDate(iso: string | null): string {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
    });
  } catch {
    return "";
  }
}

function PlayGlyph({ playing }: { playing: boolean }) {
  return playing ? (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" fill="currentColor">
      <rect x="6" y="5" width="4.5" height="16" rx="1.2" />
      <rect x="15.5" y="5" width="4.5" height="16" rx="1.2" />
    </svg>
  ) : (
    <svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true" fill="currentColor">
      <path d="M8 5.5l12 7.5-12 7.5z" />
    </svg>
  );
}

export default function OnAirPage() {
  const a = useAudio();
  const brief = a.brief;

  const hasAudio = Boolean(brief?.audio_url);
  const opinionStart = brief?.opinion_start_seconds ?? null;
  const opinionPct =
    opinionStart != null && a.duration > 0
      ? Math.min(100, (opinionStart / a.duration) * 100)
      : null;
  const inOpinion = opinionStart != null && a.currentTime >= opinionStart;

  const episodes = a.previousEpisodes;
  const voiceLabel = brief?.audio_voice_label || "Two voices";

  const leanKey = (brief?.opinion_lean || "").toLowerCase();
  const leanLabel = LEAN_LABEL[leanKey] || null;

  const grouped = useMemo(() => {
    const map = new Map<string, EpisodeMeta[]>();
    for (const ep of episodes) {
      const key = episodeDate(ep.created_at) || "Earlier";
      const arr = map.get(key) || [];
      arr.push(ep);
      map.set(key, arr);
    }
    return Array.from(map.entries());
  }, [episodes]);

  return (
    <main className="onair" id="main-content">
      <header className="onair__masthead">
        <span className="onair__kicker">
          <span className={`onair__dot${a.isPlaying ? " onair__dot--live" : ""}`} aria-hidden="true" />
          void --onair
        </span>
        <h1 className="onair__title">The Broadcast</h1>
        <p className="onair__sub">
          Today&apos;s brief, read aloud in two voices. The day in five minutes,
          then the argument worth having.
        </p>
      </header>

      {!hasAudio ? (
        <section className="onair__empty">
          <p>Today&apos;s broadcast is being prepared.</p>
          <span className="onair__empty-sub">Check back after the morning run.</span>
        </section>
      ) : (
        <>
          {/* Now playing */}
          <section className="onair__now" aria-label="Now playing">
            <p className="onair__voices">{voiceLabel}</p>
            {brief?.tldr_headline && (
              <h2 className="onair__np-headline">{brief.tldr_headline}</h2>
            )}

            <div className="onair__seek">
              <input
                className="onair__range"
                type="range"
                min={0}
                max={a.duration || 0}
                step={1}
                value={Math.min(a.currentTime, a.duration || 0)}
                onChange={(e) => a.seekTo(Number(e.target.value))}
                aria-label="Seek"
              />
              {opinionPct != null && (
                <span
                  className="onair__chapter-mark"
                  style={{ left: `${opinionPct}%` }}
                  aria-hidden="true"
                />
              )}
            </div>
            <div className="onair__times">
              <span>{fmt(a.currentTime)}</span>
              <span>{fmt(a.duration)}</span>
            </div>

            {opinionStart != null && (
              <div className="onair__chapters" role="group" aria-label="Chapters">
                <button
                  type="button"
                  className={`onair__chip${!inOpinion ? " onair__chip--on" : ""}`}
                  onClick={() => {
                    hapticMicro();
                    a.seekTo(0);
                  }}
                >
                  News
                </button>
                <button
                  type="button"
                  className={`onair__chip${inOpinion ? " onair__chip--on" : ""}`}
                  onClick={() => {
                    hapticMicro();
                    a.seekTo(opinionStart);
                  }}
                >
                  Opinion
                </button>
              </div>
            )}

            <div className="onair__transport">
              <button
                type="button"
                className="onair__tbtn"
                onClick={() => {
                  hapticMicro();
                  a.skipBackward();
                }}
                aria-label="Back 15 seconds"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M11 4 5 9l6 5" />
                  <path d="M5 9h9a5 5 0 0 1 0 10h-3" />
                </svg>
                <span className="onair__tbtn-n">15</span>
              </button>

              <button
                type="button"
                className="onair__play"
                onClick={() => {
                  hapticLight();
                  a.handlePlayPause();
                }}
                aria-label={a.isPlaying ? "Pause" : "Play"}
              >
                <PlayGlyph playing={a.isPlaying} />
              </button>

              <button
                type="button"
                className="onair__tbtn"
                onClick={() => {
                  hapticMicro();
                  a.skipForward();
                }}
                aria-label="Forward 15 seconds"
              >
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M13 4l6 5-6 5" />
                  <path d="M19 9h-9a5 5 0 0 0 0 10h3" />
                </svg>
                <span className="onair__tbtn-n">15</span>
              </button>

              <button
                type="button"
                className="onair__speed"
                onClick={() => {
                  hapticMicro();
                  a.cycleSpeed();
                }}
                aria-label={`Playback speed ${a.playbackSpeed}x`}
              >
                {a.playbackSpeed}×
              </button>
            </div>
          </section>

          {/* Show notes */}
          <section className="onair__notes" aria-label="Show notes">
            {brief?.tldr_text && (
              <div className="onair__note">
                <h3 className="onair__note-h">In brief</h3>
                {brief.tldr_headline && (
                  <p className="onair__note-lead">{brief.tldr_headline}</p>
                )}
                <p className="onair__note-body">{brief.tldr_text}</p>
              </div>
            )}
            {brief?.opinion_text && (
              <div className="onair__note">
                <h3 className="onair__note-h">
                  Opinion
                  {leanLabel && <span className="onair__lean">{leanLabel}</span>}
                </h3>
                {brief.opinion_headline && (
                  <p className="onair__note-lead">{brief.opinion_headline}</p>
                )}
                <p className="onair__note-body">{brief.opinion_text}</p>
              </div>
            )}
          </section>
        </>
      )}

      {/* Archive */}
      {grouped.length > 0 && (
        <section className="onair__archive" aria-label="Previous broadcasts">
          <h3 className="onair__archive-h">Previous broadcasts</h3>
          {grouped.map(([day, eps]) => (
            <div key={day} className="onair__archive-day">
              <p className="onair__archive-date">{day}</p>
              <ul className="onair__archive-list">
                {eps.map((ep) => {
                  const current = brief?.id === ep.id;
                  return (
                    <li key={ep.id}>
                      <button
                        type="button"
                        className={`onair__ep${current ? " onair__ep--on" : ""}`}
                        onClick={() => {
                          hapticLight();
                          a.loadEpisode(ep);
                        }}
                        disabled={!ep.audio_url}
                      >
                        <span className="onair__ep-play" aria-hidden="true">
                          <PlayGlyph playing={current && a.isPlaying} />
                        </span>
                        <span className="onair__ep-text">
                          <span className="onair__ep-headline">
                            {ep.tldr_headline || "Daily brief"}
                          </span>
                          <span className="onair__ep-meta">
                            {ep.audio_duration_seconds
                              ? `${Math.round(ep.audio_duration_seconds / 60)} min`
                              : ""}
                            {current ? " · Now playing" : ""}
                          </span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
