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

import { readFileSync, writeFileSync } from "fs";
import { tmpdir } from "os";
import { createHash } from "crypto";
import { join } from "path";
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
  members: PrintedMember[] | null;
  member_count: number;
  story_thread_id: string | null;
  continues_printed_id: string | null;
}

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
    // Static export (2026-08-30 Cloudflare migration): the permanent archive is
    // emitted as build-data/archive.json by the pipeline (was a paginated
    // Supabase read). Read the whole file once; callers share this in-memory
    // copy. An unavailable file resolves to [] (no /story pages), never throws.
    // The archive is either committed (build-data/archive.json) or on R2, with
    // build-data/archive.pointer.json naming where. It is 20 MB rewritten every
    // run, which is the single biggest source of git churn in the repo, so the
    // pointer is the destination; the local file stays supported so a build
    // works either way and during the migration.
    try {
      const raw = readFileSync(
        join(process.cwd(), "build-data", "archive.json"),
        "utf-8",
      );
      const rows = JSON.parse(raw) as PrintedStoryRow[];
      return Array.isArray(rows) ? rows : [];
    } catch {
      // No local file. A pointer means the rows exist and are reachable.
    }

    let pointer: { url?: string; rows?: number } | null = null;
    try {
      pointer = JSON.parse(
        readFileSync(join(process.cwd(), "build-data", "archive.pointer.json"), "utf-8"),
      );
    } catch {
      console.warn(
        "[archive] neither build-data/archive.json nor archive.pointer.json is present; no /story pages will be generated.",
      );
      return [];
    }

    if (!pointer?.url) {
      console.warn("[archive] archive.pointer.json carries no url; no /story pages.");
      return [];
    }

    // A pointer that cannot be fetched THROWS. Returning [] here would silently
    // drop every /story page and every archive url from the sitemap while the
    // build still reported success, which is exactly the class of quiet
    // degradation this codebase keeps getting bitten by. A failed build is
    // recoverable; a deploy that erases 1,500 permalinks is not.
    // Next runs generateStaticParams, generateMetadata and the page render in
    // SEPARATE worker processes, so the module-level promise above memoizes
    // within a worker but not across them: a build fetched this 20 MB file four
    // times. One disk cache per build, keyed by the url, makes it one fetch.
    const cacheFile = join(
      tmpdir(),
      `void-archive-${createHash("sha1").update(pointer.url).digest("hex").slice(0, 16)}.json`,
    );
    try {
      const cached = JSON.parse(readFileSync(cacheFile, "utf-8")) as PrintedStoryRow[];
      if (Array.isArray(cached) && cached.length > 0) {
        return cached;
      }
    } catch {
      // No cache yet in this build; fetch it.
    }

    const res = await fetch(pointer.url, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(
        `[archive] ${pointer.url} returned ${res.status}. The archive is the source of ` +
          `every /story permalink, so the build stops rather than publishing without them.`,
      );
    }
    const rows = (await res.json()) as PrintedStoryRow[];
    if (!Array.isArray(rows)) {
      throw new Error(`[archive] ${pointer.url} did not contain an array of rows.`);
    }
    if (typeof pointer.rows === "number" && rows.length !== pointer.rows) {
      console.warn(
        `[archive] pointer claims ${pointer.rows} rows but ${rows.length} arrived.`,
      );
    }
    try {
      writeFileSync(cacheFile, JSON.stringify(rows));
    } catch {
      // A read-only temp dir just means the other workers fetch it too.
    }
    console.log(`[archive] ${rows.length} rows fetched from ${pointer.url}`);
    return rows;
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

/* ── The story permalink ───────────────────────────────────────────────────
   ONE construction, used by the archive mapper, the sitemap and the standalone
   page. The pipeline writes the same shape into archiveMap.json (export_static)
   and the served-output gate asserts it (S-01), so a change here has to be made
   in exactly two places rather than the six it used to live in.

   getLatestPermalinkMap was deleted 2026-09-07: it built the same map a second
   way, from the archive rows rather than from archiveMap.json, and had no
   caller left after serverFeed moved to the emitted map.                    ── */

export function storyHref(printedStoryId: string): string {
  return `/story/${printedStoryId}/`;
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
  story.permalink = storyHref(row.id);
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
