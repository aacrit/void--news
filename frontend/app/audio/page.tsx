import type { Metadata } from "next";
import Link from "next/link";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pageMetadata, SITE_URL } from "../lib/siteMeta";
import { getWeeklyIssues } from "../lib/weeklyIssues";
import type { AudioChapter } from "../lib/types";
import CopyButton from "../press/CopyButton";
import AudioPlay from "./AudioPlay";
import "../styles/prose-page.css";
import "./audio.css";

/* ---------------------------------------------------------------------------
   /audio: every programme, one place.

   Until 2026-09-21 the masthead carried On Air (the daily programme's page)
   and Listen (a page of three RSS addresses) as two unrelated links, and
   the three programmes had no single home. This is the horizontal channel:
   today's On Air, this week's Argument, the latest History episodes, each
   playable here through the shared player, and the feeds for anyone who
   would rather subscribe. On Air keeps its own page under this section.

   A server component: the data is the deploy tree's (brief.json, the weekly
   archive, the History audio manifest), read at build time. The play
   buttons are the one client island. Rule 1: nothing here is written by
   hand; every title, date and duration comes from the row that produced it.
   --------------------------------------------------------------------------- */

export const metadata: Metadata = pageMetadata({
  title: "Audio | Void News",
  description:
    "Every programme Void News makes, in one place: On Air every day, The Argument on Sundays, History one event at a time. Play here, or take the feeds to any podcast app.",
  path: "/audio/",
});

interface BriefRow {
  id: string;
  tldr_headline: string | null;
  audio_url: string | null;
  audio_duration_seconds: number | string | null;
  created_at: string | null;
}

interface HistoryEpisode {
  url: string;
  title: string;
  durationSeconds: number;
  publishedAt?: string | null;
  chapters?: AudioChapter[] | null;
}

function readJson<T>(rel: string): T | null {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), rel), "utf8")) as T;
  } catch {
    return null;
  }
}

function clock(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/* A UTC date, spelled out. Everything here is a published date, so the
   viewer's clock never enters it. */
function dateUTC(iso: string): string {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

const FEEDS = [
  { key: "onair", title: "On Air", cadence: "Daily", feed: `${SITE_URL}/podcast-world.xml` },
  { key: "argument", title: "The Argument", cadence: "Sundays", feed: `${SITE_URL}/podcast-weekly.xml` },
  { key: "history", title: "History", cadence: "One event per episode", feed: `${SITE_URL}/podcast-history.xml` },
] as const;

export default function AudioPage() {
  const brief = readJson<BriefRow>("public/data/brief.json");
  const dailyDuration = brief?.audio_duration_seconds != null ? Number(brief.audio_duration_seconds) : 0;
  const daily = brief?.audio_url && dailyDuration > 0 ? brief : null;

  const weekly = getWeeklyIssues().find((i) => i.audio_url) ?? null;

  const manifest = readJson<{ episodes: Record<string, HistoryEpisode> }>("public/data/history-audio.json");
  const episodes = Object.entries(manifest?.episodes ?? {})
    .filter(([, e]) => e && e.url && e.durationSeconds > 0)
    .sort((a, b) => (b[1].publishedAt ?? "").localeCompare(a[1].publishedAt ?? ""))
    .slice(0, 6);
  const historyCount = Object.keys(manifest?.episodes ?? {}).length;

  return (
    <div className="audio-page">
      <main id="main-content" className="audio-hub">
        <header className="audio-hub__head">
          <h1 className="audio-hub__title">Audio</h1>
          <p className="audio-hub__lede">
            Three programmes. Play them here, or take the feeds to any podcast app.
          </p>
        </header>

        <section className="audio-prog audio-prog--onair" aria-labelledby="audio-onair-h">
          <p className="audio-prog__kicker">
            <span className="audio-prog__n">01</span> Daily
          </p>
          <h2 id="audio-onair-h" className="audio-prog__title">On Air</h2>
          {daily ? (
            <>
              <p className="audio-prog__line">{daily.tldr_headline}</p>
              <p className="audio-prog__meta">
                {daily.created_at ? <span>{dateUTC(daily.created_at)}</span> : null}
                <span>{clock(dailyDuration)}</span>
              </p>
              <div className="audio-prog__actions">
                <AudioPlay kind="daily" label="Play today's programme" />
                <Link href="/onair" className="audio-prog__open">Open On Air</Link>
              </div>
            </>
          ) : (
            <p className="audio-prog__line">No programme has been published yet.</p>
          )}
        </section>

        <section className="audio-prog audio-prog--argument" aria-labelledby="audio-argument-h">
          <p className="audio-prog__kicker">
            <span className="audio-prog__n">02</span> Sundays
          </p>
          <h2 id="audio-argument-h" className="audio-prog__title">The Argument</h2>
          {weekly ? (
            <>
              <p className="audio-prog__line">{weekly.cover_headline}</p>
              <p className="audio-prog__meta">
                <span>Week of {dateUTC(weekly.week_start)}</span>
                {weekly.audio_duration_seconds ? <span>{clock(Number(weekly.audio_duration_seconds))}</span> : null}
              </p>
              <div className="audio-prog__actions">
                <AudioPlay kind="weekly" label="Play this week's Argument" issue={weekly} />
                <Link href="/weekly" className="audio-prog__open">Open the issue</Link>
              </div>
            </>
          ) : (
            <p className="audio-prog__line">No issue has been recorded yet.</p>
          )}
        </section>

        <section className="audio-prog audio-prog--history" aria-labelledby="audio-history-h">
          <p className="audio-prog__kicker">
            <span className="audio-prog__n">03</span> One event per episode
          </p>
          <h2 id="audio-history-h" className="audio-prog__title">History</h2>
          <p className="audio-prog__line">
            {historyCount} episodes. The latest six:
          </p>
          <ol className="audio-episodes">
            {episodes.map(([slug, e]) => (
              <li key={slug} className="audio-episode">
                <div className="audio-episode__text">
                  <Link href={`/history/${slug}`} className="audio-episode__title">{e.title}</Link>
                  <span className="audio-episode__meta">
                    {clock(e.durationSeconds)}
                    {e.chapters?.length ? ` · ${e.chapters.length} chapters` : ""}
                  </span>
                </div>
                <AudioPlay
                  kind="history"
                  label={`Play ${e.title}`}
                  compact
                  payload={{ id: slug, title: e.title, subtitle: null, audioUrl: e.url, durationSeconds: e.durationSeconds, chapters: e.chapters ?? null, publishedAt: e.publishedAt ?? null }}
                />
              </li>
            ))}
          </ol>
          <p className="audio-prog__actions">
            <Link href="/history" className="audio-prog__open">Every event</Link>
          </p>
        </section>

        <section className="audio-feeds" aria-labelledby="audio-feeds-h">
          <h2 id="audio-feeds-h" className="audio-feeds__title">Subscribe</h2>
          <p className="audio-feeds__lede">Paste a feed address into any podcast app.</p>
          <ul className="audio-feeds__list">
            {FEEDS.map((f) => (
              <li key={f.key} className="audio-feed">
                <span className="audio-feed__name">
                  {f.title} <span className="audio-feed__cadence">{f.cadence}</span>
                </span>
                <span className="audio-feed__row">
                  <code className="audio-feed__url">{f.feed}</code>
                  <CopyButton text={f.feed} label={`Copy the ${f.title} feed address`} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
