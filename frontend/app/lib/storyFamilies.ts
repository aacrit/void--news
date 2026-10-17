/**
 * Same-Story Cluster Family detection.
 *
 * When the clustering engine is conservative (the post-2026-05-18 hardened
 * engine refuses merges that would create mega-clusters > 120 sources),
 * legitimately-related sub-stories about one mega-event can appear as
 * separate top-10 cards. Without this detection, the homepage looks
 * "split" — three angles on the Xi-Putin Beijing summit each take their
 * own slot and a sophisticated reader concludes "void can't detect the
 * same event."
 *
 * This module converts that conservatism into an editorial feature by
 * surfacing the family relationship visually. The detection uses cheap
 * stemmed-title Jaccard (the same signal Phase 3 clustering uses) so
 * there's no new DB dependency.
 */

import type { Story } from "./types";

const TITLE_STOPWORDS = new Set([
  "a", "an", "the", "in", "on", "of", "for", "to", "with", "and", "or",
  "as", "at", "by", "from", "is", "are", "was", "were", "be", "been",
  "have", "has", "had", "will", "would", "could", "should", "may", "can",
  "this", "that", "these", "those", "it", "its", "they", "them", "their",
  "but", "not", "no", "yes", "if", "then", "than", "so", "such",
  "after", "before", "into", "over", "under", "up", "down", "out", "off",
]);

/** Lightweight Porter-style suffix stripper. Matches the spirit of
 *  `_stem_word` in story_cluster.py without bringing in a real stemmer. */
function stem(word: string): string {
  if (word.length <= 4) return word;
  for (const suf of ["ational", "tional", "ization", "ation", "ment",
                     "ness", "ity", "ing", "ies", "ied", "ed", "es", "s"]) {
    if (word.endsWith(suf) && word.length - suf.length >= 3) {
      return word.slice(0, -suf.length);
    }
  }
  return word;
}

function titleStems(title: string): Set<string> {
  const words = title.toLowerCase().match(/[a-z0-9]+/g) ?? [];
  const out = new Set<string>();
  for (const w of words) {
    if (w.length >= 4 && !TITLE_STOPWORDS.has(w)) {
      out.add(stem(w));
    }
  }
  return out;
}

function jaccard(a: Set<string>, b: Set<string>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let inter = 0;
  for (const x of a) if (b.has(x)) inter++;
  return inter / (a.size + b.size - inter);
}

export interface FamilyInfo {
  /** Stable identifier shared by all family members. */
  familyId: string;
  /** Total cluster count in this family (including self). */
  size: number;
  /** Human-readable label, generated from the longest shared-stem
   *  sequence in member titles. e.g. "Beijing summit". */
  label: string;
}

/**
 * Identify same-story families among the top-N stories.
 *
 * Two stories are "family" when their stemmed-title Jaccard meets or
 * exceeds the floor (default 0.30). Single-cluster components (no
 * family relationship) are NOT returned, so callers can treat the
 * result as "show only when present."
 *
 * Cost: O(N²) Jaccard on top-N titles. With N=10 this is 45 comparisons
 * on ≤30-token sets per story. Runs once per feed render in <1ms.
 */
export function computeStoryFamilies(
  stories: Story[],
  opts: { jaccardFloor?: number; topN?: number } = {},
): Map<string, FamilyInfo> {
  const floor = opts.jaccardFloor ?? 0.30;
  const top = stories.slice(0, opts.topN ?? 10);
  if (top.length < 2) return new Map();

  const stems = top.map((s) => titleStems(s.title));

  // Union-find over indices.
  const parent = top.map((_, i) => i);
  const find = (x: number): number => {
    while (parent[x] !== x) {
      parent[x] = parent[parent[x]];
      x = parent[x];
    }
    return x;
  };
  const union = (a: number, b: number): void => {
    const ra = find(a), rb = find(b);
    if (ra !== rb) parent[ra] = rb;
  };

  for (let i = 0; i < top.length; i++) {
    for (let j = i + 1; j < top.length; j++) {
      if (jaccard(stems[i], stems[j]) >= floor) {
        union(i, j);
      }
    }
  }

  // Group indices by root.
  const groups = new Map<number, number[]>();
  for (let i = 0; i < top.length; i++) {
    const r = find(i);
    if (!groups.has(r)) groups.set(r, []);
    groups.get(r)!.push(i);
  }

  // Emit only multi-member families.
  const result = new Map<string, FamilyInfo>();
  for (const [root, members] of groups) {
    if (members.length < 2) continue;

    // Family label = intersection of stems across all members, taking
    // the longest single stem. Falls back to the first cluster's
    // shortest non-trivial stem if no intersection.
    let common = new Set(stems[members[0]]);
    for (let k = 1; k < members.length; k++) {
      common = new Set([...common].filter((s) => stems[members[k]].has(s)));
    }
    const labelStems = [...common].sort((a, b) => b.length - a.length);
    const label = labelStems[0]
      ? labelStems[0]
      : "related event";

    const familyId = `family-${top[root].id.slice(0, 8)}`;
    for (const idx of members) {
      result.set(top[idx].id, {
        familyId,
        size: members.length,
        label,
      });
    }
  }
  return result;
}
