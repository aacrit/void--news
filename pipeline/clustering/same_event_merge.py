"""Late-stage same-event cluster merge (2026-08-22).

Two disjoint clusters of ONE real-world event ship as two feed cards with
independently-corrupted source_count, summary, and bias label. On 2026-08-21
four such pairs shipped; the West Bank pair landed 13 lean points apart (55 vs
42), straddling center, so one card read "Flat" and the other "Left" for the
same event.

ROOT CAUSE (confirmed against fixture 005 + the live pairs): the Phase-2 entity
merge that SHOULD coalesce these declines because the pairs' strongest shared
entity is a geopolitical common noun (Israel / Russia / Iran) that lives in
`_LOW_SPECIFICITY_ENTITIES` and is therefore barred from being a Phase-2 anchor.
That blacklist is CORRECT at 2,196 clusters (where "Russia" is everywhere) and
wrong at 50 (where two same-day clusters both centered on "Russia" that also
share title stems are obviously one story).

So this is NOT a Phase 1/2/3 threshold change (those stay untouched, per the
contamination-safety constraint). It is a NEW pass that runs LAST, over only the
top-N clusters by source_count, and merges on a CONJUNCTIVE, high-precision gate:

    shared salient entity  (INCLUDING the low-specificity ones, safe at N=50)
      AND temporal proximity  (<= MERGE_TEMPORAL_HOURS)
      AND ( >= MERGE_MIN_SHARED_STEMS shared title stems
            OR both assert the same numeric metric type )

Cosine was DROPPED from the gate deliberately: max cross-cluster article cosine
is saturated at ~1.0 by shared wire reprints, and centroid cosine does not
separate same-event from different-event pairs cleanly (a Harry-lawsuit vs
Harry-UK-visit pair scored 0.34, among true positives). The conjunctive gate
above rejects that false positive (1 shared stem, no shared metric) while still
catching the West Bank / Kyiv / Russia-UK pairs.

Bias is NOT averaged: the merge unions the disjoint article lists and lets the
downstream bias aggregation re-score the combined set (55 and 42 over 27 real
articles, never (55+42)/2). Every merge is logged (both titles, source counts,
pre-merge leans, merged size, gate branch) so a bad merge surfaces in week one.
A per-root ceiling caps how many sub-clusters one merge can absorb, so this can
never manufacture a mega-cluster. P0-2 removal stays as the downstream backstop
for what this misses (e.g. a 1-shared-stem, no-numeric pair like Iran).
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from .story_cluster import (
    _extract_cluster_entities,
    _expand_entities_with_tokens,
    _parse_first_pub,
    _title_word_stems,
)

# ---------------------------------------------------------------------------
# Tunables. Deliberately conservative: contamination (a wrong merge) is worse
# than duplication (a missed merge), so every gate is on the strict side.
# ---------------------------------------------------------------------------
MERGE_TOP_N = 50               # candidate set = top-N clusters by source_count
MERGE_TEMPORAL_HOURS = 48      # same-event coverage clusters within ~2 days
MERGE_MIN_SHARED_STEMS = 2     # the loosest branch (Russia-UK cleared here)
MERGE_MIN_SHARED_ENTITIES = 1  # >= 1 shared salient entity (incl. blacklisted)
MERGE_CEILING = 6              # a single merged cluster may absorb at most this
                               # many sub-clusters (mega-merge guard)

# A shared numeric-metric branch: both clusters assert the SAME metric TYPE
# (a casualty count / money figure). Values need not match; fragmentation is
# exactly what makes them differ (17 vs 12 dead). The entity + temporal
# conjunction anchors it so two unrelated death tolls do not merge.
_METRIC_RE = re.compile(
    r"\b(?:killed|dead|deaths?|death\s+toll|fatalities|injured|wounded|"
    r"casualties|magnitude)\b",
    re.IGNORECASE,
)


def _cluster_blob(cluster: dict) -> str:
    """Title + a few members' text, for the numeric-metric test."""
    parts = [cluster.get("title", "") or ""]
    for art in (cluster.get("articles", []) or [])[:6]:
        parts.append(((art.get("title") or "") + " " + (art.get("summary") or "")).strip())
    return " ".join(parts)


def _article_key(art: dict) -> str:
    """Stable identity for de-duping articles across a merge."""
    return str(art.get("id") or art.get("url") or art.get("title") or id(art))


def _distinct_source_count(articles: list[dict]) -> int:
    """Recompute source_count from the merged article set (never a sum of the
    two cluster counts, which would double-count a source present in both)."""
    src = set()
    for a in articles or []:
        s = a.get("source_id") or a.get("source_slug") or a.get("source") or a.get("source_name")
        if isinstance(s, dict):
            s = s.get("slug") or s.get("id") or s.get("name")
        src.add(s if s is not None else _article_key(a))
    return len(src)


def merge_same_event_clusters(
    clusters: list[dict],
    top_n: int = MERGE_TOP_N,
    log_fn: Optional[Callable[[str], None]] = None,
) -> list[dict]:
    """Merge same-event fragments among the top-N clusters by source_count.

    Unions the (disjoint) article lists into the higher-sourced cluster and
    drops the absorbed clusters; downstream bias aggregation then re-scores the
    combined article set. Returns the reduced cluster list. Never raises; on any
    unexpected error it logs and returns the input unchanged."""
    log = log_fn or (lambda m: print(m))
    # DISABLED 2026-08-23: the conjunctive gate over-merged unrelated events on
    # live data (Sweden sword attack + Congo Ebola + Texas court fused into one
    # 73-source cluster via the too-loose shared-entity + numeric-metric branch).
    # Contamination corrupts the bias distribution, so the pass is OFF until the
    # gate is tightened and validated on real 50-cluster feeds, not just fixtures.
    return clusters
    if not clusters or len(clusters) < 2:  # pragma: no cover (unreachable while disabled)
        return clusters
    try:
        order = sorted(
            range(len(clusters)),
            key=lambda i: clusters[i].get("source_count", 0) or 0,
            reverse=True,
        )[:top_n]
        ents = [
            set(_expand_entities_with_tokens(_extract_cluster_entities(clusters[i].get("articles", []) or [])))
            for i in order
        ]
        stems = [_title_word_stems(clusters[i].get("title", "") or "") for i in order]
        ts = [_parse_first_pub(clusters[i]) for i in order]
        metric = [bool(_METRIC_RE.search(_cluster_blob(clusters[i]))) for i in order]

        # Union-find over positions in `order`.
        parent = list(range(len(order)))
        load = [1] * len(order)

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        merge_log: list[tuple] = []
        for a in range(len(order)):
            for b in range(a + 1, len(order)):
                ra, rb = find(a), find(b)
                if ra == rb:
                    continue
                if load[ra] + load[rb] > MERGE_CEILING:
                    continue  # mega-merge guard
                shared_ent = ents[a] & ents[b]
                if len(shared_ent) < MERGE_MIN_SHARED_ENTITIES:
                    continue
                if ts[a] and ts[b] and abs((ts[a] - ts[b]).total_seconds()) > MERGE_TEMPORAL_HOURS * 3600:
                    continue
                shared_stems = len(stems[a] & stems[b])
                branch = None
                if shared_stems >= MERGE_MIN_SHARED_STEMS:
                    branch = f"stems({shared_stems})"
                elif metric[a] and metric[b]:
                    branch = "numeric"
                if not branch:
                    continue
                parent[rb] = ra
                load[ra] += load[rb]
                merge_log.append((order[a], order[b], branch, sorted(shared_ent)[:4]))

        if not merge_log:
            return clusters

        # Group candidate positions by union-find root.
        groups: dict[int, list[int]] = {}
        for pos in range(len(order)):
            groups.setdefault(find(pos), []).append(order[pos])

        removed: set[int] = set()
        for _root, cluster_idxs in groups.items():
            if len(cluster_idxs) < 2:
                continue
            # Survivor = highest source_count in the group; keeps its title.
            survivor = max(cluster_idxs, key=lambda i: clusters[i].get("source_count", 0) or 0)
            surv = clusters[survivor]
            merged_articles = list(surv.get("articles", []) or [])
            seen = {_article_key(a) for a in merged_articles}
            pre_lean = (surv.get("bias_diversity") or {}).get("avg_political_lean")
            absorbed_titles = []
            for idx in cluster_idxs:
                if idx == survivor:
                    continue
                other = clusters[idx]
                absorbed_titles.append(
                    (other.get("title", "")[:48], other.get("source_count", 0),
                     (other.get("bias_diversity") or {}).get("avg_political_lean"))
                )
                for a in (other.get("articles", []) or []):
                    if _article_key(a) not in seen:
                        seen.add(_article_key(a))
                        merged_articles.append(a)
                removed.add(idx)
            surv["articles"] = merged_articles
            new_sc = _distinct_source_count(merged_articles)
            surv["source_count"] = new_sc
            # Bias is intentionally NOT set here: downstream aggregation re-scores
            # `articles`. Clear a stale cached lean so a later guard can't read it.
            if isinstance(surv.get("bias_diversity"), dict):
                surv["bias_diversity"]["_merged_from_count"] = 1 + len(absorbed_titles)
            surv["_same_event_merged"] = True
            for at, asc, al in absorbed_titles:
                log(
                    f"  [same-event-merge] KEEP[{surv.get('source_count')}src, "
                    f"lean={pre_lean}] '{surv.get('title','')[:48]}' <- "
                    f"ABSORB[{asc}src, lean={al}] '{at}' "
                    f"(now {new_sc} sources; bias re-aggregated downstream)"
                )
        if removed:
            log(f"  [same-event-merge] merged {len(removed)} fragment cluster(s) into "
                f"{len({find(p) for p in range(len(order)) if len(groups.get(find(p),[]))>1})} event(s)")
        return [c for i, c in enumerate(clusters) if i not in removed]
    except Exception as e:  # never break the pipeline on a merge bug
        log(f"  [warn][same-event-merge] skipped ({type(e).__name__}: {e})")
        return clusters
