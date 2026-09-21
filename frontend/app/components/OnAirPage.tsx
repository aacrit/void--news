"use client";

import { useMemo } from "react";
import { useAudio, type EpisodeMeta } from "./AudioProvider";
import { episodeFromBrief, sameEpisode } from "../lib/episode";
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

  /* THE PAGE'S SUBJECT IS TODAY'S BROADCAST, always. `brief` is the daily
     edition and no other programme can write it, so this page can no longer
     announce someone else's episode as its own: it used to print
     "ON AIR · World Edition · 23 min" over the Weekly's cover headline, and
     "15 min" over "The Fall of Constantinople" (measured 2026-09-21).

     The transport below is the SHARED one. It is live while today's broadcast
     is the loaded episode; when another programme owns the player the same
     controls start today's broadcast instead, and a line above the portal
     names what is playing. */
  const episode = useMemo(() => episodeFromBrief(brief), [brief]);
  const owns = sameEpisode(a.nowPlaying, episode);
  const playing = owns && a.isPlaying;
  const elsewhere = !owns && a.nowPlaying ? a.nowPlaying : null;

  const hasAudio = Boolean(episode);

  /** Today's broadcast, from this chapter. Universal: it toggles when the
   *  daily programme is already loaded and starts it when it is not. */
  const start = (at?: number) => {
    if (!episode) return;
    if (at == null) {
      if (owns) a.handlePlayPause();
      else a.play(episode);
      return;
    }
    if (owns) a.seekTo(at);
    else a.play(episode, { startAt: at });
  };

  // Prefer the stored episode duration (stable) over the <audio> element's
  // reported duration so the portal readouts settle immediately.
  const displayDuration = episode?.durationSeconds || (owns ? a.duration : 0) || 0;
  /* The playhead belongs to the loaded episode: showing a Weekly issue's
     position on today's seek bar would be a second kind of lie. */
  const currentTime = owns ? a.currentTime : 0;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  const opinionStart = brief?.opinion_start_seconds ?? null;
  const opinionPct =
    opinionStart != null && displayDuration > 0
      ? Math.min(100, (opinionStart / displayDuration) * 100)
      : null;
  const inOpinion = opinionStart != null && currentTime >= opinionStart;

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
  /* Today's running order, off the daily brief, so the page lists its own
     chapters whoever owns the player. Memoized: it feeds two useMemo deps. */
  const chapters = useMemo(() => episode?.chapters ?? [], [episode]);
  const hasChapters = chapters.length > 0;
  const chapIndex = owns ? a.currentChapterIndex : -1;
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
            <span className={`onair__dot${playing ? " onair__dot--live" : ""}`} aria-hidden="true" />
            On Air
          </span>
          <h1 className="onair__title">The Broadcast</h1>
          {/* Explanatory sub-callout removed (CEO 2026-08-09): the portal itself
              is the moat. The dateline, headline, and live transport below say
              what this is without a paragraph describing it. */}
        </header>

        {/* Another programme owns the player. The page says so rather than
            presenting someone else's episode as today's edition, and the
            transport below starts today's broadcast on a press. */}
        {elsewhere && (
          <p className="onair__elsewhere" role="status">
            <span className="onair__elsewhere-label">{elsewhere.programmeLabel} is loaded</span>
            <span className="onair__elsewhere-title">{elsewhere.title}</span>
          </p>
        )}

        {!hasAudio ? (
          <section className="onair__empty">
            <p>Today&apos;s broadcast is being prepared.</p>
            <span className="onair__empty-sub">Check back after the morning run.</span>
          </section>
        ) : (
          <>
            {/* ── Broadcast portal (hero) ── */}
            <section
              className={`onair__portal${playing ? " onair__portal--live" : ""}`}
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
                  <ScaleIcon size={22} animation={playing ? "broadcast" : "idle"} />
                  <span className="onair__pbrand-void">Void</span>
                  <span className="onair__pbrand-cmd">On Air</span>
                  <span className={`onair__status${playing ? " onair__status--live" : ""}`}>
                    <span className="onair__status-dot" aria-hidden="true" />
                    <span className="onair__status-label">{playing ? "ON AIR" : "On demand"}</span>
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
              <div className={`onair__vu${playing ? " onair__vu--active" : ""}`} aria-hidden="true">
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
                    if (owns) a.skipBackward(); else start(0);
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
                  className={`onair__play${playing ? " onair__play--on" : ""}`}
                  onClick={() => {
                    hapticLight();
                    start();
                  }}
                  aria-label={playing ? "Pause" : "Play"}
                >
                  <PlayGlyph playing={playing} />
                </button>

                <button
                  type="button"
                  className="onair__tbtn"
                  onClick={() => {
                    hapticMicro();
                    if (owns) a.skipForward(); else start(0);
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
                          start(chapters[opinionIndex]?.startTime ?? 0);
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
                          start(0);
                        }}
                      >
                        News
                      </button>
                      <button
                        type="button"
                        className={`onair__section${inOpinion ? " onair__section--on" : ""}`}
                        onClick={() => {
                          hapticMicro();
                          start(opinionStart);
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
                    value={Math.min(currentTime, displayDuration || 0)}
                    onChange={(e) => start(Number(e.target.value))}
                    aria-label="Seek"
                    aria-valuetext={`${fmt(currentTime)} of ${fmt(displayDuration)}`}
                  />
                </div>
                <div className="onair__times">
                  <span>{fmt(currentTime)}</span>
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
                            start(chapters[i]?.startTime ?? 0);
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
                    /* The row that is really in the element, not the row
                       whose id matches today's brief. */
                    const current = !!ep.audio_url && a.nowPlaying?.audioUrl === ep.audio_url;
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
