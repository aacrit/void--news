/* ---------------------------------------------------------------------------
   archive — build-time reader for the permanent printed archive.

   The `printed_stories` table (migration 075, PUBLIC read RLS) is a permanent,
   copyright-clean snapshot of each day's displayed top-50: title, summary, bias
   aggregates, and a compact per-source `members` list. Everything needed to
   render a full standalone Deep Dive lives in one row — NO client-side fetch on
   the /story pages.

   This module owns a SINGLE module-level fetch of the whole archive, memoized
   as a promise. generateStaticParams, the page render, generateMetadata, and
   the sitemap all `await getArchiveRows()` and read from that one in-memory
   copy, so prerendering the entire archive never becomes an N+1 Supabase call.

   Server-only + deterministic: runs at `next build` inside async server
   components. No "use client", no React, no Date.now()/new Date() in the mapped
   output (timestamps are passed through as raw ISO strings and formatted at the
   render boundary). Same rows in, same Story out.
   --------------------------------------------------------------------------- */

import { supabase } from "./supabase";
import {
  parseBiasDiversity,
  mapClustersToStories,
} from "./feedMapping";
import type { Story, StorySource, ClaimConsensus } from "./types";
import type { DeepDiveSpectrumSource } from "../components/DeepDiveSpectrum";

/* ── Row shape (subset of printed_stories we render) ───────────────────── */

/** One archived source inside `printed_stories.members`. Written by the
 *  pipeline's print_archive.py step 8f. `lean`/`rigor`/`confidence` may be null
 *  when a member article was never bias-scored. */
export interface PrintedMember {
  source_id?: string | null;
  source_name?: string | null;
  tier?: string | null;
  lean?: number | null;
  rigor?: number | null;
  confidence?: number | null;
  url?: string | null;
  published_at?: string | null;
  is_wire_copy?: boolean | null;
}

export interface PrintedStoryRow {
  id: string;
  printed_on: string;
  edition_position: number;
  source_cluster_id: string;
  title: string;
  summary: string | null;
  category: string | null;
  content_type: string | null;
  story_type: string | null;
  editorial_importance: number | null;
  summary_tier: string | null;
  rank_world: number;
  headline_rank: number | null;
  source_count: number;
  divergence_score: number | null;
  first_published: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  consensus_points: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  divergence_points: any;
  claim_consensus: ClaimConsensus | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  bias_diversity: any;
  mean_lean: number | null;
  polarization: number | null;
  lean_spread: number | null;
  aggregate_confidence: number | null;
  members: PrintedMember[] | null;
  member_count: number;
  story_thread_id: string | null;
  continues_printed_id: string | null;
}

/** Explicit column list — everything the standalone Deep Dive + metadata need.
 *  Ordered newest edition first, strongest position first within a day. */
const ARCHIVE_COLS =
  "id,printed_on,edition_position,source_cluster_id,title,summary,category," +
  "content_type,story_type,editorial_importance,summary_tier,rank_world," +
  "headline_rank,source_count,divergence_score,first_published,consensus_points," +
  "divergence_points,claim_consensus,bias_diversity,mean_lean,polarization," +
  "lean_spread,aggregate_confidence,members,member_count,story_thread_id," +
  "continues_printed_id";

const PAGE = 1000;

/* ── Module-level memoized fetch ───────────────────────────────────────── */

let _rowsPromise: Promise<PrintedStoryRow[]> | null = null;

/**
 * Fetch EVERY printed_stories row exactly once per build process, paginating
 * past PostgREST's 1,000-row response cap. Memoized: repeat callers share the
 * same in-memory array (generateStaticParams / page / metadata / sitemap).
 *
 * An empty or unavailable archive resolves to [] — the /story route then
 * builds zero pages (generateStaticParams returns []). It NEVER throws: an
 * empty archive is a normal pre-first-run state, not a build failure (distinct
 * from the front page's fail-loud, which guards the live feed).
 */
export function getArchiveRows(): Promise<PrintedStoryRow[]> {
  if (_rowsPromise) return _rowsPromise;
  _rowsPromise = (async () => {
    if (!supabase) {
      console.warn(
        "[archive] Supabase client unavailable at build time; no /story pages will be generated.",
      );
      return [];
    }
    const out: PrintedStoryRow[] = [];
    let offset = 0;
    // Hard ceiling so a runaway/unbounded archive can never hang the build.
    const MAX_ROWS = 100000;
    while (offset < MAX_ROWS) {
      const res = await supabase
        .from("printed_stories")
        .select(ARCHIVE_COLS)
        .order("printed_on", { ascending: false })
        .order("edition_position", { ascending: true })
        .range(offset, offset + PAGE - 1);
      if (res.error) {
        console.warn(
          `[archive] printed_stories fetch failed at offset ${offset}: ${res.error.message ?? res.error}. ` +
            `Returning ${out.length} rows collected so far.`,
        );
        break;
      }
      const data = (res.data ?? []) as unknown as PrintedStoryRow[];
      out.push(...data);
      if (data.length < PAGE) break;
      offset += PAGE;
    }
    return out;
  })();
  return _rowsPromise;
}

/** Look up a single archived row by its permalink id (reads the shared cache). */
export async function getArchiveRowById(
  id: string,
): Promise<PrintedStoryRow | null> {
  const rows = await getArchiveRows();
  return rows.find((r) => r.id === id) ?? null;
}

/* ── Latest-edition permalink map (for feed cards) ─────────────────────── */

/**
 * Build `{ source_cluster_id -> "/story/<id>/" }` for the LATEST printed
 * edition (max printed_on). Today's displayed clusters are archived at step 8f
 * before the deploy, so today's feed cards get permalinks. Reads the shared
 * cache — no extra query.
 */
export async function getLatestPermalinkMap(): Promise<Map<string, string>> {
  const rows = await getArchiveRows();
  const map = new Map<string, string>();
  if (rows.length === 0) return map;
  // Rows are ordered printed_on DESC already; the first row's date is latest.
  const latest = rows[0].printed_on;
  for (const r of rows) {
    if (r.printed_on !== latest) break; // ordered DESC — done once the date drops
    if (r.source_cluster_id && r.id) {
      // First write wins (strongest edition_position, since ordered ASC within a day).
      if (!map.has(r.source_cluster_id)) {
        map.set(r.source_cluster_id, `/story/${r.id}/`);
      }
    }
  }
  return map;
}

/* ── Row -> Story mapping (reuses the shared feed mapping) ─────────────── */

const TIER_VALUES = new Set(["us_major", "international", "independent"]);

function normalizeTier(tier: string | null | undefined): StorySource["tier"] {
  return tier && TIER_VALUES.has(tier)
    ? (tier as StorySource["tier"])
    : "independent"; // never fabricate a higher tier — unknown -> Independent
}

/**
 * Map a printed_stories row to the `Story` the Deep Dive content components
 * expect. Reuses `mapClustersToStories` by shaping the archive row into the
 * synthetic story_clusters row that mapping already understands (bias_diversity
 * JSONB, consensus/divergence points, claim_consensus). The Story.id is the
 * PERMANENT permalink id, so Sigil rotation seeds + keys are stable.
 */
export function archiveRowToStory(row: PrintedStoryRow): Story {
  // Shape a synthetic story_clusters row for the shared mapper. Every field the
  // enriched mapping reads is present on the archive row (or safely absent).
  const syntheticCluster = {
    id: row.id,
    title: row.title,
    summary: row.summary,
    category: row.category,
    section: "world",
    sections: ["world"],
    importance_score: row.rank_world,
    source_count: row.source_count,
    first_published: row.first_published,
    last_updated: row.first_published,
    divergence_score: row.divergence_score,
    headline_rank: row.headline_rank,
    coverage_velocity: 0,
    bias_diversity: row.bias_diversity,
    consensus_points: row.consensus_points,
    divergence_points: row.divergence_points,
    rank_world: row.rank_world,
    claim_consensus: row.claim_consensus,
    cached_image_url: null,
    is_international: false,
  };
  const [story] = mapClustersToStories([syntheticCluster], true);
  story.permalink = `/story/${row.id}/`;
  return story;
}

/**
 * Build the `DeepDiveSpectrumSource[]` the spectrum + source columns render,
 * from the archive `members` list. Only members that carry a real bias lean are
 * plotted (the spectrum positions by lean). Deterministic order: as stored.
 */
export function archiveMembersToSpectrumSources(
  members: PrintedMember[] | null,
): DeepDiveSpectrumSource[] {
  if (!Array.isArray(members)) return [];
  const seen = new Set<string>();
  const out: DeepDiveSpectrumSource[] = [];
  for (const m of members) {
    if (typeof m.lean !== "number" || Number.isNaN(m.lean)) continue;
    const name = (m.source_name || "").trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue; // one entry per source (mirrors the live Deep Dive dedupe)
    seen.add(key);
    const url = m.url || "#";
    out.push({
      name,
      articleUrl: url,
      sourceUrl: url,
      tier: normalizeTier(m.tier),
      politicalLean: m.lean,
      factualRigor: typeof m.rigor === "number" ? m.rigor : undefined,
      confidence: typeof m.confidence === "number" ? m.confidence : undefined,
    });
  }
  return out;
}

/**
 * Build `StorySource[]` from the archive members. Same source-lean data as the
 * spectrum, in the shape the shared source components (ComparativeView) consume.
 */
export function archiveMembersToStorySources(
  members: PrintedMember[] | null,
): StorySource[] {
  if (!Array.isArray(members)) return [];
  const seen = new Set<string>();
  const out: StorySource[] = [];
  for (const m of members) {
    const name = (m.source_name || "").trim();
    if (!name) continue;
    const key = name.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const lean = typeof m.lean === "number" && !Number.isNaN(m.lean) ? m.lean : 50;
    const rigor = typeof m.rigor === "number" ? m.rigor : 75;
    out.push({
      name,
      url: m.url || "#",
      tier: normalizeTier(m.tier),
      biasScores: {
        politicalLean: lean,
        sensationalism: 30,
        opinionFact: 25,
        factualRigor: rigor,
        framing: 40,
      },
      confidence: typeof m.confidence === "number" ? m.confidence : undefined,
    });
  }
  return out;
}

/** Runtime guard: does this row carry any real bias diversity data? Drives
 *  whether the Spread section (Sigil + spectrum) renders. */
export function rowHasBiasData(row: PrintedStoryRow): boolean {
  const bd = parseBiasDiversity(row.bias_diversity);
  return !!(bd && bd["avg_political_lean"] != null);
}
