"use client";

import { useEffect, useMemo, useState } from "react";
import { useAudio, type EpisodeMeta } from "./AudioProvider";
import { hapticLight, hapticMicro } from "../lib/haptics";
import { splitBriefParagraphs } from "../lib/briefText";
import {
  chapterKindLabel,
  chapterMarks,
  findOpinionIndex,
  formatChapterTime,
} from "../lib/chapters";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   OnAirPage — dedicated On Air broadcast interface (/onair).

   The hero is the teal broadcast PORTAL: the same console-surface visual
   language as the desktop FloatingPlayer broadcast view (dark console gradient,
   amber filament warmth, VU arc motif, teal signal, big transport, News/Opinion
   section seek with the opinion chapter mark). Below it sit tighter secondary
   blocks: the show notes (In brief / Opinion) and the previous-broadcasts
   archive.

   All state comes from the global <AudioProvider> (useAudio) — this is a view,
   not a second player, so playback survives navigation and stays in sync with
   the mini-player and FloatingPlayer.
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

function fullDate(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
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

const VU_BARS = 16;

export default function OnAirPage() {
  const a = useAudio();
  const brief = a.brief;

  const hasAudio = Boolean(brief?.audio_url);

  // Prefer the stored episode duration (stable) over the <audio> element's
  // reported duration so the portal readouts settle immediately.
  const displayDuration = brief?.audio_duration_seconds || a.duration || 0;
  const progress = displayDuration > 0 ? (a.currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  const opinionStart = brief?.opinion_start_seconds ?? null;
  const hasOpinion = Boolean(brief?.opinion_text);
  const opinionPct =
    opinionStart != null && displayDuration > 0
      ? Math.min(100, (opinionStart / displayDuration) * 100)
      : null;
  const inOpinion = opinionStart != null && a.currentTime >= opinionStart;

  const episodes = a.previousEpisodes;
  // The stored label is the truth about who read the episode; "Two voices" is
  // only the fallback for a row that predates the field. Hosts are no longer
  // named, so the count is all the dateline carries.
  const voiceLabel = brief?.audio_voice_label || "Two voices";

  const editionLabel = brief?.edition
    ? brief.edition.charAt(0).toUpperCase() + brief.edition.slice(1)
    : "World";
  const dateLabel = fullDate(brief?.created_at ?? null);

  const leanKey = (brief?.opinion_lean || "").toLowerCase();
  const leanLabel = LEAN_LABEL[leanKey] || null;

  /* ---- Chapter rail ----
     A chaptered episode replaces the two-tab News / Opinion group with the
     show's real running order. Legacy episodes (and weekly / history) carry no
     chapters and keep the original tabs untouched. */
  const chapters = a.chapters;
  const hasChapters = chapters.length > 0;
  const chapIndex = a.currentChapterIndex;
  const currentChapter = chapIndex >= 0 ? chapters[chapIndex] : null;
  const marks = useMemo(
    () => chapterMarks(chapters, displayDuration),
    [chapters, displayDuration]
  );
  const opinionIndex = useMemo(() => findOpinionIndex(chapters), [chapters]);

  const vuBars = useMemo(() => Array.from({ length: VU_BARS }, (_, i) => i), []);

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
    <div className="page-container">
      {/* Site masthead — the Void News Sigil-wordmark navbar flows across the top
          of /onair exactly as it does on Home. Search is omitted here: the
          SearchOverlay searches the loaded story feed, which /onair does not
          carry. NavBar renders fine without onSearchClick. */}

      <main className="onair" id="main-content">
        <header className="onair__masthead">
          <span className="onair__kicker">
            <span className={`onair__dot${a.isPlaying ? " onair__dot--live" : ""}`} aria-hidden="true" />
            On Air
          </span>
          <h1 className="onair__title">The Broadcast</h1>
          {/* Explanatory sub-callout removed (CEO 2026-08-09): the portal itself
              is the moat. The dateline, headline, and live transport below say
              what this is without a paragraph describing it. */}
        </header>

        {!hasAudio ? (
          <section className="onair__empty">
            <p>Today&apos;s broadcast is being prepared.</p>
            <span className="onair__empty-sub">Check back after the morning run.</span>
          </section>
        ) : (
          <>
            {/* ── Broadcast portal (hero) ── */}
            <section
              className={`onair__portal${a.isPlaying ? " onair__portal--live" : ""}`}
              aria-label="Now playing"
            >
              {/* VU arc motif — decorative broadcast gauge behind header */}
              <svg className="onair__arc" viewBox="0 0 200 60" aria-hidden="true">
                <path d="M30 55 A70 70 0 0 1 170 55" fill="none" stroke="currentColor" strokeWidth="1.5" />
                <path d="M45 55 A55 55 0 0 1 155 55" fill="none" stroke="currentColor" strokeWidth="0.75" opacity="0.5" />
                {Array.from({ length: 9 }, (_, i) => {
                  const angle = Math.PI - (Math.PI * (i + 1)) / 10;
                  const cx = 100 + 70 * Math.cos(angle);
                  const cy = 55 - 70 * Math.sin(angle);
                  const len = i === 0 || i === 4 || i === 8 ? 6 : 4;
                  const dx = len * Math.cos(angle);
                  const dy = -len * Math.sin(angle);
                  return <line key={i} x1={cx} y1={cy} x2={cx + dx} y2={cy + dy} stroke="currentColor" strokeWidth="1" />;
                })}
              </svg>

              {/* Header — brand + live status + speed */}
              <div className="onair__phead">
                <div className="onair__pbrand">
                  <ScaleIcon size={22} animation={a.isPlaying ? "broadcast" : "idle"} />
                  <span className="onair__pbrand-void">Void</span>
                  <span className="onair__pbrand-cmd">On Air</span>
                  <span className={`onair__status${a.isPlaying ? " onair__status--live" : ""}`}>
                    <span className="onair__status-dot" aria-hidden="true" />
                    <span className="onair__status-label">{a.isPlaying ? "ON AIR" : "On demand"}</span>
                  </span>
                </div>
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

              {/* Dateline */}
              <div className="onair__dateline">
                <span className="onair__dateline-edition">{editionLabel} Edition</span>
                {dateLabel && <span className="onair__dateline-date">{dateLabel}</span>}
                <span className="onair__dateline-voices">{voiceLabel}</span>
                {durationMin && <span className="onair__dateline-duration">{durationMin} min</span>}
              </div>

              {brief?.tldr_headline && (
                <h2 className="onair__np-headline">{brief.tldr_headline}</h2>
              )}

              {/* Hero VU meter — teal phosphor bars, CSS-animated when playing */}
              <div className={`onair__vu${a.isPlaying ? " onair__vu--active" : ""}`} aria-hidden="true">
                {vuBars.map((i) => (
                  <span key={i} className="onair__vu-bar" style={{ animationDelay: `${i * 60}ms` }} />
                ))}
              </div>

              {/* Transport */}
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
                  className={`onair__play${a.isPlaying ? " onair__play--on" : ""}`}
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
              </div>

              {/* Seek — the running order when the episode is chaptered, the
                  legacy News / Opinion pair when it is not. */}
              <div className="onair__seekwrap">
                {hasChapters ? (
                  <div className="onair__rail">
                    <span className="onair__rail-now" title={currentChapter?.title || undefined}>
                      {currentChapter ? (
                        <>
                          {chapterKindLabel(currentChapter) && (
                            <span className="onair__rail-kind">
                              {chapterKindLabel(currentChapter)}
                            </span>
                          )}
                          <span className="onair__rail-title">{currentChapter.title}</span>
                        </>
                      ) : (
                        <span className="onair__rail-title onair__rail-title--between">
                          On air
                        </span>
                      )}
                    </span>
                    <span className="onair__rail-count" aria-label={`Chapter ${chapIndex + 1} of ${chapters.length}`}>
                      {chapIndex >= 0 ? chapIndex + 1 : "\u2013"} / {chapters.length}
                    </span>
                    {opinionIndex >= 0 && (
                      <button
                        type="button"
                        className={`onair__rail-jump${chapIndex === opinionIndex ? " onair__rail-jump--on" : ""}`}
                        onClick={() => {
                          hapticMicro();
                          a.seekToChapter(opinionIndex);
                        }}
                      >
                        Editorial
                      </button>
                    )}
                  </div>
                ) : (
                  opinionStart != null && (
                    <div className="onair__sections" role="group" aria-label="Chapters">
                      <button
                        type="button"
                        className={`onair__section${!inOpinion ? " onair__section--on" : ""}`}
                        onClick={() => {
                          hapticMicro();
                          a.seekTo(0);
                        }}
                      >
                        News
                      </button>
                      <button
                        type="button"
                        className={`onair__section${inOpinion ? " onair__section--on" : ""}`}
                        onClick={() => {
                          hapticMicro();
                          a.seekTo(opinionStart);
                        }}
                      >
                        Opinion
                      </button>
                    </div>
                  )
                )}

                <div className="onair__seek">
                  <div className="onair__seek-bar" aria-hidden="true">
                    <div className="onair__seek-fill" style={{ width: `${progress}%` }} />
                    {hasChapters
                      ? marks.map((m) => (
                          <span
                            key={m.index}
                            className={`onair__seek-mark${m.index === chapIndex ? " onair__seek-mark--on" : ""}${(m.chapter.kind === "opinion" || m.chapter.kind === "editorial") ? " onair__seek-mark--ed" : ""}`}
                            style={{ left: `${m.pct}%` }}
                          />
                        ))
                      : opinionPct != null && (
                          <span className="onair__seek-mark" style={{ left: `${opinionPct}%` }} />
                        )}
                  </div>
                  <input
                    className="onair__seek-input"
                    type="range"
                    min={0}
                    max={displayDuration || 0}
                    step={1}
                    value={Math.min(a.currentTime, displayDuration || 0)}
                    onChange={(e) => a.seekTo(Number(e.target.value))}
                    aria-label="Seek"
                    aria-valuetext={`${fmt(a.currentTime)} of ${fmt(displayDuration)}`}
                  />
                </div>
                <div className="onair__times">
                  <span>{fmt(a.currentTime)}</span>
                  <span>{fmt(displayDuration)}</span>
                </div>
              </div>
            </section>

            {/* Running order — the show's chapters, in play order. Clicking a
                row seeks; a story that has been archived carries a small
                secondary link to its Deep Dive so the row itself stays a seek
                control rather than becoming a navigation trap. */}
            {hasChapters && (
              <section className="onair__runorder" aria-label="Running order">
                <h3 className="onair__runorder-h">Running order</h3>
                <ol className="onair__chaps">
                  {chapters.map((c, i) => {
                    const on = i === chapIndex;
                    const kind = chapterKindLabel(c);
                    return (
                      <li
                        key={`${c.startTime}-${i}`}
                        className={`onair__chap${on ? " onair__chap--on" : ""}`}
                      >
                        <button
                          type="button"
                          className="onair__chap-seek"
                          onClick={() => {
                            hapticMicro();
                            a.seekToChapter(i);
                          }}
                          aria-current={on ? "true" : undefined}
                        >
                          <span className="onair__chap-time">
                            {formatChapterTime(c.startTime)}
                          </span>
                          <span className="onair__chap-body">
                            <span className="onair__chap-title">{c.title}</span>
                            {c.subtitle && (
                              <span className="onair__chap-sub">{c.subtitle}</span>
                            )}
                          </span>
                          {kind && <span className="onair__chap-kind">{kind}</span>}
                        </button>
                        {c.url && (
                          <a className="onair__chap-link" href={c.url}>
                            Read
                            <span className="sr-only"> the full story: {c.title}</span>
                          </a>
                        )}
                      </li>
                    );
                  })}
                </ol>
              </section>
            )}

            {/* Show notes */}
            <section className="onair__notes" aria-label="Show notes">
              {brief?.tldr_text && (
                <div className="onair__note">
                  <h3 className="onair__note-h">In brief</h3>
                  {brief.tldr_headline && (
                    <p className="onair__note-lead">{brief.tldr_headline}</p>
                  )}
                  <div className="onair__note-body">
                    {splitBriefParagraphs(brief.tldr_text).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
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
                  <div className="onair__note-body">
                    {splitBriefParagraphs(brief.opinion_text).map((para, i) => <p key={i}>{para}</p>)}
                  </div>
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
    </div>
  );
}
