/* ===========================================================================
   Revolt Context — the live-news bridge (inverse of historyContext.ts).
   history: one live story -> one archive link.
   revolt:  one curated movement -> N scored live clusters.

   The DATA (keywords/entities/excludes) rides on each movement's liveQuery;
   the ALGORITHM (lexicon, scorer, argmax single-assignment) lives here.
   Neutral framing: a keyword match is "related coverage", never an endorsed fact.
   =========================================================================== */

import type { LiveCard, Revolution } from '../revolt/types';
import { MOCK_ACTIVE } from '../revolt/mockData';
import { BASE_PATH } from './utils';

/* Shared revolt vocabulary. A bare country name only counts when it co-occurs
   with one of these, so an "Iran nuclear talks" story does not surface under
   "Iran protests". */
export const REVOLT_LEXICON: string[] = [
  'protest', 'protester', 'protesters', 'demonstration', 'demonstrator',
  'uprising', 'revolt', 'revolution', 'revolutionary', 'insurrection',
  'coup', 'junta', 'regime', 'overthrow', 'ouster', 'oust', 'topple',
  'crackdown', 'repression', 'dissident', 'opposition', 'unrest',
  'general strike', 'strike', 'mutiny', 'defect', 'defection',
  'rebel', 'rebellion', 'militia', 'insurgent', 'insurgency', 'civil war',
  'self-immolation', 'tear gas', 'martial law', 'state of emergency',
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function haystackFor(cluster: any): string {
  return `${cluster.title ?? ''} ${cluster.summary ?? ''}`.toLowerCase();
}

function containsAny(haystack: string, terms: string[]): boolean {
  return terms.some((t) => t && haystack.includes(t.toLowerCase()));
}

/**
 * Score one cluster against one movement's live spec.
 *  2 = a strong (unique name/org/leader) term hit
 *  1 = a context (country/city) term hit AND a revolt-lexicon co-occurrence
 *  0 = no match, or an exclude guard fired
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function scoreRevoltMatch(cluster: any, movement: Revolution): number {
  const q = movement.liveQuery;
  if (!q) return 0;
  const hay = haystackFor(cluster);

  if (q.exclude && containsAny(hay, q.exclude)) return 0;
  if (containsAny(hay, q.strong)) return 2;
  if (containsAny(hay, q.context) && containsAny(hay, REVOLT_LEXICON)) return 1;
  return 0;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function toLiveCard(cluster: any, score: number): LiveCard {
  return {
    id: cluster.id,
    title: cluster.title ?? '',
    summary: cluster.summary ?? '',
    category: cluster.category ?? 'conflict',
    lastUpdated: cluster.last_updated ?? cluster.lastUpdated ?? '',
    sourceCount: cluster.source_count ?? cluster.sourceCount ?? undefined,
    score,
  };
}

/**
 * Argmax single-assignment: every cluster lands under at most one movement (the
 * highest-scoring), so a Sudan story never double-renders. Returns a map of
 * slug -> LiveCard[], each sorted by score then rank_world.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function assignClustersToRevolts(clusters: any[], movements: Revolution[]): Record<string, LiveCard[]> {
  const buckets: Record<string, LiveCard[]> = {};
  for (const m of movements) buckets[m.slug] = [];

  for (const cluster of clusters ?? []) {
    let bestSlug: string | null = null;
    let bestScore = 0;
    for (const m of movements) {
      const s = scoreRevoltMatch(cluster, m);
      if (s > bestScore) { bestScore = s; bestSlug = m.slug; }
    }
    if (bestSlug && bestScore > 0) {
      buckets[bestSlug].push(toLiveCard(cluster, bestScore));
    }
  }

  for (const slug of Object.keys(buckets)) {
    buckets[slug].sort((a, b) => b.score - a.score);
  }
  return buckets;
}

/* ── The reverse bridge: one live story -> a tracked active movement ──
   Mirrors findHistoryContext. Scores a feed story against the curated active
   movements and returns the best match for a "Track this movement" chip. */
export interface RevoltMatch {
  slug: string;
  title: string;
  href: string;
}

export function findRevoltContext(title: string, summary: string): RevoltMatch | null {
  const cluster = { title, summary };
  let best: Revolution | null = null;
  let bestScore = 0;
  for (const m of MOCK_ACTIVE) {
    const s = scoreRevoltMatch(cluster, m);
    if (s > bestScore) { bestScore = s; best = m; }
  }
  if (!best || bestScore < 1) return null;
  return { slug: best.slug, title: best.title, href: `${BASE_PATH}/revolt/active/${best.slug}` };
}
