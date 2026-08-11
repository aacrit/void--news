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

import { supabase } from "./supabase";
import {
  mapClustersToStories,
  FEED_ENRICHED_FIELDS,
  FEED_BASE_FIELDS,
} from "./feedMapping";
import { getLatestPermalinkMap } from "./archive";
import type { Story } from "./types";

const FETCH_LIMIT = 100;
const ACTIVE_EDITION = "world" as const;

/** Minimum displayable stories (>=3 sources) for a valid front page. */
const MIN_STORIES = 20;

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
  if (!supabase) {
    throw new Error(
      "[serverFeed] Supabase client unavailable at build time. " +
        "NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY must be set in the build env.",
    );
  }

  // Tiered field fallback, mirroring the client: enriched -> enriched-minus-
  // is_international (older schema) -> base.
  let usingEnriched = true;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  let res: any = await supabase
    .from("story_clusters")
    .select(FEED_ENRICHED_FIELDS)
    .contains("sections", [ACTIVE_EDITION])
    .order("rank_world", { ascending: false })
    .limit(FETCH_LIMIT);

  if (res.error) {
    res = await supabase
      .from("story_clusters")
      .select(FEED_ENRICHED_FIELDS.replace(",is_international", ""))
      .contains("sections", [ACTIVE_EDITION])
      .order("rank_world", { ascending: false })
      .limit(FETCH_LIMIT);
  }
  if (res.error) {
    usingEnriched = false;
    res = await supabase
      .from("story_clusters")
      .select(FEED_BASE_FIELDS)
      .contains("sections", [ACTIVE_EDITION])
      .order("first_published", { ascending: false })
      .limit(FETCH_LIMIT);
  }

  if (res.error) {
    throw new Error(
      `[serverFeed] Feed query failed at build time: ${res.error.message ?? res.error}`,
    );
  }

  let clusters = res.data ?? [];

  // Ghost-cluster guard (cheap, batched — NOT per-cluster): a cluster whose
  // stale source_count still ranks it into the feed but whose cluster_articles
  // links were all cascade-dropped by article retention renders as a real card
  // with an empty Deep Dive. The pipeline cleanup sweep removes these on its
  // next run; this guard keeps one from reaching the prerender in the meantime.
  // Cost is a SINGLE .in_() query over the already-fetched top-100 ids (paged
  // for the 1000-row cap), not one query per cluster. Fail-open: any error, or
  // an empty result set, leaves the feed untouched so a transient read problem
  // can never blank the front page.
  try {
    const ids = clusters
      .map((c: { id?: string }) => c.id)
      .filter((id: string | undefined): id is string => !!id);
    if (ids.length > 0) {
      const withArticles = new Set<string>();
      let from = 0;
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { data, error } = await supabase
          .from("cluster_articles")
          .select("cluster_id")
          .in("cluster_id", ids)
          .range(from, from + 999);
        if (error || !data || data.length === 0) break;
        for (const row of data as { cluster_id?: string }[]) {
          if (row.cluster_id) withArticles.add(row.cluster_id);
        }
        if (data.length < 1000) break;
        from += 1000;
      }
      // Only filter when we actually found links; an empty set means the read
      // failed or the table is empty, and we must not drop the whole feed.
      if (withArticles.size > 0) {
        const before = clusters.length;
        clusters = clusters.filter((c: { id?: string }) => c.id && withArticles.has(c.id));
        const dropped = before - clusters.length;
        if (dropped > 0) {
          console.warn(`[serverFeed] dropped ${dropped} ghost cluster(s) with zero cluster_articles`);
        }
      }
    }
  } catch (e) {
    console.warn(`[serverFeed] ghost-cluster guard skipped: ${e}`);
  }

  const stories = mapClustersToStories(clusters, usingEnriched);

  // Attach shareable permalinks from the latest printed edition. Today's
  // displayed clusters are archived at pipeline step 8f BEFORE this deploy, so
  // today's feed maps 1:1 to the newest printed_stories rows (keyed by
  // source_cluster_id == cluster.id == Story.id). An archive miss simply leaves
  // permalink undefined and the card falls back to the button behavior.
  try {
    const permalinkMap = await getLatestPermalinkMap();
    if (permalinkMap.size > 0) {
      for (const s of stories) {
        const link = permalinkMap.get(s.id);
        if (link) s.permalink = link;
      }
    }
  } catch (e) {
    // Never fail the front-page build on the archive lookup — permalinks are a
    // progressive enhancement, not a requirement for the feed to render.
    console.warn(`[serverFeed] permalink map unavailable: ${e}`);
  }

  // Fail loud: the displayed feed applies a >=3-source quality floor. Count
  // only stories that would actually render; a short/empty page must not ship.
  const displayable = stories.filter(
    (s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3,
  ).length;
  if (displayable < MIN_STORIES) {
    throw new Error(
      `[serverFeed] Only ${displayable} displayable stories (>=3 sources) returned; ` +
        `expected at least ${MIN_STORIES}. Refusing to build an empty front page. ` +
        `Total clusters fetched: ${clusters.length}.`,
    );
  }

  // Edition build time — the latest completed pipeline run.
  let builtAt: string | null = null;
  const { data: run } = await supabase
    .from("pipeline_runs")
    .select("completed_at")
    .eq("status", "completed")
    .order("completed_at", { ascending: false })
    .limit(1)
    .single();
  if (run?.completed_at) builtAt = run.completed_at as string;

  return {
    stories,
    builtAt,
    editionDateline: formatDatelineUTC(builtAt),
  };
}
