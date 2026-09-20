/* ---------------------------------------------------------------------------
   weeklyIssues — build-time reader for the weekly back-issue archive.

   Mirrors lib/archive.ts: a SINGLE module-level memoized read that
   generateStaticParams, the page render, generateMetadata and the sitemap all
   share, so prerendering N issues is never an N+1 read.

   WHERE THE ARCHIVE LIVES, AND WHY IT IS A FILE
   ---------------------------------------------
   The weekly job restores the Actions cache and deliberately never saves it
   back: the daily pipeline is usually still running at 12:00 UTC and a save
   would push a pre-run copy under a newer key and lose a day. So each weekly
   row is written into a database discarded when the job ends, and the next
   week's job restores a cache that never contained it. Raising the exporter's
   LIMIT would yield one row forever.

   The deploy tree is therefore the archive of record — exactly as it already
   is on the daily side (printed_stories -> build-data/archive.json ->
   lib/archive.ts -> prerendered /story/<id>).

   Server-only and deterministic: runs at `next build` inside async server
   components. Dates pass through as raw ISO strings and are formatted at the
   render boundary by app/weekly/format.ts.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";
import type { WeeklyDigestData } from "../weekly/types";

let _issues: WeeklyDigestData[] | null = null;

function read(file: string): unknown {
  return JSON.parse(readFileSync(join(process.cwd(), "build-data", file), "utf8"));
}

function isUsable(row: unknown): row is WeeklyDigestData {
  const r = row as Partial<WeeklyDigestData> | null;
  return !!(
    r &&
    typeof r === "object" &&
    typeof r.week_start === "string" &&
    /^\d{4}-\d{2}-\d{2}/.test(r.week_start) &&
    Array.isArray(r.cover_text)
  );
}

/**
 * Every issue, newest first.
 *
 * A MISSING archive returns [] rather than throwing. Unlike the front page, an
 * empty back catalogue is a legitimate cold-start state — a contributor who has
 * never run the pipeline should still be able to `next build`. It means
 * generateStaticParams prerenders zero archive pages, not that the deploy is
 * broken. A row that fails to parse is dropped with a warning for the same
 * reason: prerender fewer pages, never fail the whole deploy over one bad row.
 */
export function getWeeklyIssues(): WeeklyDigestData[] {
  if (_issues) return _issues;
  let rows: unknown;
  try {
    rows = read("weekly-issues.json");
  } catch {
    console.warn("[weekly] no build-data/weekly-issues.json; archive is empty");
    _issues = [];
    return _issues;
  }
  if (!Array.isArray(rows)) {
    console.warn("[weekly] weekly-issues.json is not an array; archive is empty");
    _issues = [];
    return _issues;
  }
  const usable = rows.filter(isUsable);
  if (usable.length !== rows.length) {
    console.warn(`[weekly] dropped ${rows.length - usable.length} unusable issue row(s)`);
  }
  _issues = [...usable].sort((a, b) => b.week_start.localeCompare(a.week_start));
  return _issues;
}

export function getWeeklyIssueByWeek(week: string): WeeklyDigestData | null {
  return getWeeklyIssues().find((i) => i.week_start === week) ?? null;
}

/**
 * The current issue.
 *
 * This one THROWS when it is missing, matching serverFeed's refusal to build a
 * blank front page. /weekly with no issue is a broken deploy, not a cold start,
 * and failing the build is how that gets noticed before it ships.
 */
export function getLatestWeeklyIssue(): WeeklyDigestData {
  const latest = getWeeklyIssues()[0];
  if (!latest) {
    throw new Error(
      "[weekly] no issue in build-data/weekly-issues.json. Refusing to build a " +
        "blank /weekly. Run the weekly digest, or seed the archive with " +
        "`python -m pipeline.briefing.backfill_weekly_archive`."
    );
  }
  return latest;
}

/** The back-issue list shown at the foot of an issue. */
export function getWeeklyArchiveIndex() {
  return getWeeklyIssues().map((i) => ({
    id: i.id,
    issue_number: i.issue_number,
    edition: i.edition,
    week_start: i.week_start,
    week_end: i.week_end,
    cover_headline: i.cover_headline ?? null,
    cover_image_url: i.cover_image_url ?? null,
    audio_url: i.audio_url ?? null,
    audio_duration_seconds: i.audio_duration_seconds ?? null,
    created_at: i.created_at ?? null,
  }));
}
