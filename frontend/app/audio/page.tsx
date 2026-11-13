import type { Metadata } from "next";
import Link from "next/link";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { pageMetadata, SITE_URL } from "../lib/siteMeta";
import { getWeeklyIssues, getWeeklyCorrections } from "../lib/weeklyIssues";
import { audioWithdrawal } from "../lib/weeklyAudio";
import { issueLabel } from "../weekly/format";
import type { AudioChapter } from "../lib/types";
import CopyButton from "../press/CopyButton";
import AudioPortal from "./AudioPortal";
import { isNewRecording } from "../history/edition";
import "../styles/prose-page.css";
import "./audio.css";

/* ---------------------------------------------------------------------------
   /audio: the player, with a switch between programmes (CEO 2026-10-03:
   "the user should land directly on the same audio portal as the sidebar").
   The console is OnAirPanel's own, inline (AudioPortal). What follows is the
   page's history; the listing it describes is now the switch's three panels.

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
  edition?: string;
  audio_withdrawn?: boolean;
}

function readJson<T>(rel: string): T | null {
  try {
    return JSON.parse(readFileSync(join(process.cwd(), rel), "utf8")) as T;
  } catch {
    return null;
  }
}

/* Whole seconds, truncated: the rule the player, the History pages and the
   podcast feeds (`_itunes_duration`) all use, so one episode never reads
   11:41 here and 11:40 in a podcast app. tests/test_podcast_feed.py runs
   this function against the feed's on the same durations. */
function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/* A UTC date, spelled out. Everything here is a published date, so the
   viewer's clock never enters it. */
function dateUTC(iso: string): string {
  const d = new Date(iso.length === 10 ? `${iso}T00:00:00Z` : iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

/* How many episodes a committed feed carries. A feed with none is an address
   a podcast app would subscribe to and find empty, so it is not offered. Read
   at build from the same public/ file the CDN serves. */
function feedItems(file: string): number {
  try {
    return (readFileSync(join(process.cwd(), "public", file), "utf8").match(/<item[\s>]/g) ?? []).length;
  } catch {
    return 0;
  }
}

const FEEDS = [
  { key: "onair", title: "On Air", cadence: "Daily", file: "podcast-world.xml" },
  { key: "argument", title: "The Argument", cadence: "Sundays", file: "podcast-weekly.xml" },
  { key: "history", title: "History", cadence: "One event per episode", file: "podcast-history.xml" },
] as const;

export default function AudioPage() {
  const brief = readJson<BriefRow>("public/data/brief.json");
  const dailyDuration = brief?.audio_duration_seconds != null ? Number(brief.audio_duration_seconds) : 0;
  const daily = brief?.audio_url && dailyDuration > 0
    ? {
        headline: brief.tldr_headline,
        dateline: brief.created_at ? dateUTC(brief.created_at) : "",
        clock: clock(dailyDuration),
      }
    : null;

  const all = getWeeklyIssues();
  const issues = all
    .filter((i) => i.audio_url)
    .map((i) => ({
      issue: i,
      label: issueLabel(i.issue_number),
      dateline: `Week of ${dateUTC(i.week_start)}`,
      clock: i.audio_duration_seconds ? clock(Number(i.audio_duration_seconds)) : null,
    }));
  /* The latest issue's recording, if a correction withdrew it. Read from the
     corrections file, never written here by hand. */
  const latest = all[0] ?? null;
  const withdrawn = latest && !latest.audio_url
    ? audioWithdrawal(getWeeklyCorrections(latest.week_start), latest.week_start)
    : null;
  const withdrawnLabel = withdrawn && latest
    ? issueLabel(latest.issue_number).replace(/^Pilot issue$/, "the pilot issue")
    : null;
  const feeds = FEEDS
    .filter((f) => feedItems(f.file) > 0)
    .map((f) => ({ ...f, feed: `${SITE_URL}/${f.file}` }));

  const manifest = readJson<{ episodes: Record<string, HistoryEpisode> }>("public/data/history-audio.json");
  // A withdrawn episode (its script was corrected after the render) is not
  // offered here, as on its own page and in the feed.
  const history = Object.entries(manifest?.episodes ?? {})
    .filter(([, e]) => e && e.url && e.durationSeconds > 0 && !e.audio_withdrawn)
    .sort((a, b) => (b[1].publishedAt ?? "").localeCompare(a[1].publishedAt ?? ""))
    .map(([slug, e]) => ({
      slug,
      id: slug,
      title: e.title,
      subtitle: null,
      audioUrl: e.url,
      durationSeconds: e.durationSeconds,
      chapters: e.chapters ?? null,
      publishedAt: e.publishedAt ?? null,
      chapterCount: e.chapters?.length ?? 0,
      clock: clock(e.durationSeconds),
      newRecording: isNewRecording(e.edition),
    }));

  return (
    <div className="audio-page">
      <main id="main-content" className="audio-hub">
        <header className="audio-hub__head">
          <h1 className="audio-hub__title">Audio</h1>
          <p className="audio-hub__lede">
            Three programmes, one player. Switch programmes above it; the player follows you round the site.
          </p>
        </header>

        <AudioPortal daily={daily} issues={issues} withdrawnLabel={withdrawnLabel} history={history} />

        <p className="audio-hub__elsewhere">
          <Link href="/onair" className="audio-prog__open">On Air page</Link>
          <Link href="/weekly" className="audio-prog__open">This week&rsquo;s issue</Link>
          <Link href="/history" className="audio-prog__open">Every History event</Link>
        </p>

        <section className="audio-feeds" aria-labelledby="audio-feeds-h">
          <h2 id="audio-feeds-h" className="audio-feeds__title">Subscribe</h2>
          <p className="audio-feeds__lede">Paste a feed address into any podcast app.</p>
          <ul className="audio-feeds__list">
            {feeds.map((f) => (
              <li key={f.key} className="audio-feed">
                <span className="audio-feed__name">
                  {f.title} <span className="audio-feed__cadence">{f.cadence}</span>
                </span>
                <span className="audio-feed__row">
                  <code className="audio-feed__url">{f.feed}</code>
                  <CopyButton text={f.feed} label={`Copy the feed address for ${f.title}`} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      </main>
    </div>
  );
}
