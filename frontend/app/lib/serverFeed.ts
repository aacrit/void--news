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

   Determinism: all date formatting here is UTC and computed ONCE at build,
   then passed to the client as preformatted strings. Never call new Date()
   during React render on either server or client for the initial paint.
   --------------------------------------------------------------------------- */

import { supabase } from "./supabase";
import {
  mapClustersToStories,
  FEED_ENRICHED_FIELDS,
  FEED_BASE_FIELDS,
} from "./feedMapping";
import type { Story } from "./types";

const FETCH_LIMIT = 100;
const ACTIVE_EDITION = "world" as const;

/** Minimum displayable stories (>=3 sources) for a valid front page. */
const MIN_STORIES = 20;

export interface InitialFeed {
  stories: Story[];
  /** Pipeline completed_at ISO string (edition build time), or null. */
  builtAt: string | null;
  /** Build-time-formatted, UTC, deterministic masthead strings. */
  editionDateline: string; // e.g. "Aug 9, 2026"
  editionTimestamp: string; // e.g. "11:00 UTC"
}

const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** UTC dateline, deterministic: "Aug 9, 2026". */
function formatDatelineUTC(iso: string | null): string {
  const d = iso ? new Date(iso) : new Date();
  if (isNaN(d.getTime())) return "";
  return `${MONTHS[d.getUTCMonth()]} ${d.getUTCDate()}, ${d.getUTCFullYear()}`;
}

/** UTC edition time, rounded to the nearest hour: "11:00 UTC".
 *  Signals a once-a-day edition rather than a live clock. */
function formatTimestampUTC(iso: string | null): string {
  const src = iso ? new Date(iso) : new Date();
  if (isNaN(src.getTime())) return "";
  let hour = src.getUTCHours();
  if (src.getUTCMinutes() >= 30) hour = (hour + 1) % 24;
  return `${String(hour).padStart(2, "0")}:00 UTC`;
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

  const clusters = res.data ?? [];
  const stories = mapClustersToStories(clusters, usingEnriched);

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
    editionTimestamp: formatTimestampUTC(builtAt),
  };
}
