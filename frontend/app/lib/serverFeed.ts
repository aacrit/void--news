/* ---------------------------------------------------------------------------
   serverFeed — build-time front-page feed fetch (static export).

   Runs ONCE at `next build` inside the async server component (app/page.tsx).
   Queries the SAME top-50 feed the client renders and returns fully-mapped
   Story[] plus the edition build time, so the prerendered index.html ships the
   real feed instead of an empty shell.

   Static-export safe: this is a plain async function invoked during the
   server render of a statically-exported page. No SSR at request time, no
   route handler, no middleware. Supabase creds come from the build env
   (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY).

   Determinism: the edition DATE is formatted in UTC ONCE at build and passed
   to the client as a preformatted string. The edition TIME is deliberately
   NOT baked here: it is rendered in the viewer's LOCAL zone, computed on the
   client after mount from the raw builtAt ISO (NavBar), so the build box's
   timezone never leaks into the HTML. Never call new Date() for a rendered
   value during React render on either server or client for the initial paint.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";
import {
  mapClustersToStories,
  clusterHasRealSummary,
} from "./feedMapping";
import type { Story } from "./types";

/** Minimum displayable, REAL-SUMMARY stories (>=3 sources) for a valid front
 *  page. mapClustersToStories drops every unsummarized cluster (raw scraped
 *  text) before we get here, so this count is of genuinely-summarized cards.
 *  Below this we fail the build loudly rather than ship a raw or gutted feed
 *  (P0, 2026-08-11). If a healthy run genuinely cannot cover this many, that is
 *  a signal to lower the displayed feed size deliberately, not to pad with raw
 *  excerpts. */
const MIN_STORIES = 30;

export interface InitialFeed {
  stories: Story[];
  /** Pipeline completed_at ISO string (edition build time), or null. This raw
   *  ISO is what the client uses to render the masthead "as of" TIME in the
   *  viewer's LOCAL zone after mount. */
  builtAt: string | null;
  /** Build-time-formatted, UTC, deterministic edition DATE (e.g. "Aug 9, 2026").
   *  The masthead TIME is NOT baked here: it is machine-local and computed
   *  client-side after mount from builtAt (see NavBar), so nothing that would
   *  mismatch the reader's zone ever lands in the prerendered HTML. */
  editionDateline: string;
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** UTC dateline, deterministic: "Aug 9, 2026". Safe to bake into the
 *  prerendered HTML because it never depends on the viewer's timezone. The
 *  edition TIME is intentionally NOT formatted here: local time is computed
 *  on the client after mount (NavBar) so no zone-specific string is baked. */
function formatDatelineUTC(iso: string | null): string {
  const d = iso ? new Date(iso) : new Date();
  if (isNaN(d.getTime())) return "";
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

/**
 * Fetch + map the top-50 feed at build time.
 * Throws (failing `next build`) when fewer than MIN_STORIES displayable
 * stories come back so a blank / short front page can never deploy.
 */
export async function fetchInitialFeed(): Promise<InitialFeed> {
  // Static export (2026-08-30 Cloudflare migration): the front-page feed is
  // emitted as build-data/feed.json by the pipeline (was a build-time Supabase
  // read). The file carries the same story_clusters rows the enriched query
  // returned (summary_tier + bias_diversity + consensus/divergence points), plus
  // the edition builtAt. The pipeline emits a clean, summarized set, so the old
  // ghost-cluster guard and null-tier filter that needed live Supabase reads are
  // gone; clusterHasRealSummary still runs as a belt-and-suspenders text check.
  let clusters: Record<string, unknown>[] = [];
  let builtAt: string | null = null;
  try {
    const raw = readFileSync(
      join(process.cwd(), "build-data", "feed.json"),
      "utf-8",
    );
    const parsed = JSON.parse(raw) as {
      clusters?: Record<string, unknown>[];
      builtAt?: string | null;
    };
    clusters = Array.isArray(parsed.clusters) ? parsed.clusters : [];
    builtAt = parsed.builtAt ?? null;
  } catch (e) {
    throw new Error(
      `[serverFeed] build-data/feed.json unavailable at build time (${e}). ` +
        `The pipeline emits it each run; refusing to build a blank front page.`,
    );
  }

  // Belt-and-suspenders: never render a raw-excerpt/unsummarized cluster.
  clusters = clusters.filter((c) => clusterHasRealSummary(c, true));

  const stories = mapClustersToStories(clusters, true);

  // Attach shareable permalinks from the latest printed edition (build-data/
  // archiveMap.json: { source_cluster_id -> "/story/<id>/" }). An archive miss
  // falls back to the in-app deep link ?story=<id>, so no card is ever link-less.
  try {
    const rawMap = readFileSync(
      join(process.cwd(), "build-data", "archiveMap.json"),
      "utf-8",
    );
    const map = JSON.parse(rawMap) as Record<string, string>;
    for (const s of stories) {
      const link = map[s.id];
      if (link) s.permalink = link;
    }
  } catch (e) {
    console.warn(`[serverFeed] permalink map unavailable: ${e}`);
  }
  for (const s of stories) {
    if (!s.permalink && s.id) s.permalink = `/?story=${s.id}`;
  }

  // Fail loud: too few real-summary, >=3-source stories means an upstream
  // coverage failure. Refuse to ship a raw or gutted front page.
  const displayable = stories.filter(
    (s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3,
  ).length;
  if (displayable < MIN_STORIES) {
    throw new Error(
      `[serverFeed] Only ${displayable} displayable stories (>=3 sources, real ` +
        `summary) in build-data/feed.json; expected at least ${MIN_STORIES}. ` +
        `${clusters.length} clusters were emitted, so the gap is a coverage failure.`,
    );
  }

  return {
    stories,
    builtAt,
    editionDateline: formatDatelineUTC(builtAt),
  };
}
