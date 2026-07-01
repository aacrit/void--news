"""Predicate functions for clustering-suite fixtures.

Each predicate inspects the output of cluster_stories() (and optionally
the per-cluster ranked order) and returns a (grade, message) tuple.

Grading vocabulary mirrors the bias suite (runner.py):
    CORRECT     — predicate fully satisfied
    ACCEPTABLE  — within 1 cluster of the expected target
    WRONG       — predicate violated
    CATASTROPHIC — predicate violated by >50% of the target

Predicate dispatch is by `expectation.type`:
    should_merge        -> all named IDs land in one cluster
    should_split        -> named IDs do NOT all land together
    should_be_present   -> some cluster's title/summary matches a key phrase
                           and lands within top-N when ranked by source_count
    should_dampen       -> wire-share ceiling + rank floor (NOT in top-N)
    should_tag          -> cluster.section / category match expected
    should_have_signal  -> fraction of clusters with non-zero signal >= floor

Helpers:
    grade_predicate(name, ok, deviation, target)   -> Grade
"""
from __future__ import annotations

import re
import statistics
from typing import Any, Iterable

# ---------------------------------------------------------------------------
# Grade vocabulary (matches bias runner)
# ---------------------------------------------------------------------------

GRADE_ORDER = ["CORRECT", "ACCEPTABLE", "WRONG", "CATASTROPHIC"]


def _grade_count_band(actual: int, target_lo: int, target_hi: int) -> str:
    """Grade an integer (e.g., cluster count) against an inclusive range.

    CORRECT      = inside [lo, hi]
    ACCEPTABLE   = within 1 of either bound
    WRONG        = within 50% of target_hi outside the bound
    CATASTROPHIC = beyond 50% of target_hi outside the bound
    """
    if target_lo <= actual <= target_hi:
        return "CORRECT"
    gap = (target_lo - actual) if actual < target_lo else (actual - target_hi)
    if gap <= 1:
        return "ACCEPTABLE"
    # >50% deviation from the larger bound = catastrophic
    target = max(target_hi, 1)
    if gap > target * 0.5:
        return "CATASTROPHIC"
    return "WRONG"


def _worst_grade(grades: Iterable[str]) -> str:
    """Return the worst grade (highest index in GRADE_ORDER)."""
    worst = "CORRECT"
    for g in grades:
        if GRADE_ORDER.index(g) > GRADE_ORDER.index(worst):
            worst = g
    return worst


# ---------------------------------------------------------------------------
# Cluster lookups
# ---------------------------------------------------------------------------

def _cluster_for_article(clusters: list[dict], article_id: str) -> dict | None:
    """Return the cluster dict containing article_id, or None."""
    for c in clusters:
        if article_id in (c.get("article_ids") or []):
            return c
        # Defensive: also scan the embedded `articles` list in case article_ids
        # is missing or empty (singleton clusters built outside the merge path).
        for a in c.get("articles") or []:
            if a.get("id") == article_id:
                return c
    return None


def _cluster_text(cluster: dict) -> str:
    """Concatenated lowercase title + summary for keyword matching."""
    return f"{cluster.get('title', '')} {cluster.get('summary', '')}".lower()


def _key_phrase_words(phrase: str) -> set[str]:
    """Tokenize a key_phrase into a content-word set (>=3 chars, alpha)."""
    words = re.findall(r"[a-z][a-z\-']+", phrase.lower())
    return {w for w in words if len(w) >= 3}


def _match_key_phrase(clusters: list[dict], key_phrase: str,
                      min_overlap: float = 0.5) -> tuple[int, dict | None, float]:
    """Find the cluster whose (title+summary) best matches key_phrase.

    Returns (best_index, best_cluster, overlap_ratio).
    overlap_ratio = (matched_words / total_phrase_words). At least
    `min_overlap` must be matched to count as a hit; otherwise returns
    (-1, None, best_overlap_seen).
    """
    target = _key_phrase_words(key_phrase)
    if not target or not clusters:
        return -1, None, 0.0
    best_idx = -1
    best_cluster: dict | None = None
    best_ratio = 0.0
    for i, c in enumerate(clusters):
        text_words = _key_phrase_words(_cluster_text(c))
        if not text_words:
            continue
        matched = len(target & text_words)
        ratio = matched / len(target)
        if ratio > best_ratio:
            best_ratio = ratio
            best_idx = i
            best_cluster = c
    if best_ratio < min_overlap:
        return -1, None, best_ratio
    return best_idx, best_cluster, best_ratio


def _ranked_order(clusters: list[dict]) -> list[dict]:
    """Rank clusters by source_count desc, then article_count desc.

    The clustering suite intentionally does NOT exercise importance_ranker
    (that gets its own suite later). Source count is the cheapest, most
    deterministic stand-in for "rank" inside this suite.
    """
    def _key(c: dict) -> tuple[int, int]:
        return (c.get("source_count", 0), len(c.get("articles") or []))
    return sorted(clusters, key=_key, reverse=True)


def _wire_share(cluster: dict) -> float:
    """Estimate the fraction of cluster articles that are wire copies.

    A "wire" article is one whose `tier` field equals "wire" OR whose
    source slug is in the canonical wire set. Articles produced by the
    same wire byline appearing in many outlets all count.
    """
    arts = cluster.get("articles") or []
    if not arts:
        return 0.0
    wire_slugs = {"ap", "ap-news", "reuters", "afp", "dpa", "kyodo",
                  "bloomberg-wire", "upi", "pa-media", "anadolu", "tass",
                  "xinhua", "ians", "pti", "epa-efe"}
    wire = 0
    for a in arts:
        tier = (a.get("tier") or "").lower()
        slug = (a.get("source_id") or "").lower()
        if tier in ("wire", "wire-service") or slug in wire_slugs:
            wire += 1
    return wire / len(arts)


# ---------------------------------------------------------------------------
# Predicate: should_merge
# ---------------------------------------------------------------------------

def should_merge(
    clusters: list[dict],
    expected_member_ids: list[str],
    min_clusters: int = 1,
    max_clusters: int = 1,
    min_source_count: int = 1,
) -> tuple[str, str]:
    """All named IDs must land in the same cluster.

    Args:
        clusters: cluster_stories() output
        expected_member_ids: article IDs that should co-cluster
        min_clusters/max_clusters: bounds on the total cluster count for the
            ID set (1/1 = strict merge to one)
        min_source_count: minimum unique source_count for the merged cluster

    Grading:
        CORRECT      = all IDs in one cluster, count in [lo,hi], src >= floor
        ACCEPTABLE   = IDs in 2 clusters when 1 was expected (close miss)
        WRONG        = IDs split across 3+ clusters
        CATASTROPHIC = IDs split across more clusters than half of expected_member_ids
    """
    if not expected_member_ids:
        return "CORRECT", "no expected IDs supplied"

    # Map each expected ID to the cluster index it lands in
    found_clusters: dict[int, list[str]] = {}
    missing: list[str] = []
    for aid in expected_member_ids:
        c = _cluster_for_article(clusters, aid)
        if c is None:
            missing.append(aid)
            continue
        idx = clusters.index(c)
        found_clusters.setdefault(idx, []).append(aid)

    if missing:
        # Missing IDs always count as WRONG (article was dropped entirely)
        return "WRONG", (
            f"missing article IDs: {missing} "
            f"(found {len(found_clusters)} clusters for the rest)"
        )

    n_clusters = len(found_clusters)
    grade_count = _grade_count_band(n_clusters, min_clusters, max_clusters)

    # Source count check on the cluster holding the most expected IDs
    grade_src = "CORRECT"
    src_msg = ""
    if found_clusters:
        primary_idx = max(found_clusters, key=lambda i: len(found_clusters[i]))
        primary = clusters[primary_idx]
        src = primary.get("source_count", 0)
        if src < min_source_count:
            gap = min_source_count - src
            if gap == 1:
                grade_src = "ACCEPTABLE"
            elif gap >= max(2, int(min_source_count * 0.5)):
                grade_src = "WRONG"
            else:
                grade_src = "ACCEPTABLE"
            src_msg = f" | source_count={src} (need >={min_source_count})"

    grade = _worst_grade([grade_count, grade_src])
    msg = (
        f"IDs landed in {n_clusters} cluster(s) "
        f"(expected {min_clusters}-{max_clusters}){src_msg}"
    )
    return grade, msg


# ---------------------------------------------------------------------------
# Predicate: should_split
# ---------------------------------------------------------------------------

def should_split(
    clusters: list[dict],
    member_ids: list[str],
    min_clusters: int = 2,
) -> tuple[str, str]:
    """Named IDs must NOT all land in the same cluster.

    Args:
        clusters: cluster_stories() output
        member_ids: article IDs that should be split apart
        min_clusters: minimum number of distinct clusters the IDs should
            be distributed across (default 2)

    Grading:
        CORRECT      = IDs distributed across >= min_clusters
        ACCEPTABLE   = within 1 of min_clusters
        WRONG        = distributed across fewer
        CATASTROPHIC = all IDs in one cluster when min_clusters >= 4
    """
    if not member_ids:
        return "CORRECT", "no member IDs supplied"

    found_clusters: dict[int, list[str]] = {}
    missing: list[str] = []
    for aid in member_ids:
        c = _cluster_for_article(clusters, aid)
        if c is None:
            missing.append(aid)
            continue
        idx = clusters.index(c)
        found_clusters.setdefault(idx, []).append(aid)

    if missing:
        return "WRONG", f"missing article IDs: {missing}"

    n_clusters = len(found_clusters)

    if n_clusters >= min_clusters:
        return "CORRECT", (
            f"split into {n_clusters} clusters (>= {min_clusters} expected)"
        )

    gap = min_clusters - n_clusters
    if gap == 1:
        grade = "ACCEPTABLE"
    elif n_clusters == 1 and min_clusters >= 4:
        grade = "CATASTROPHIC"
    else:
        grade = "WRONG"
    return grade, f"only {n_clusters} cluster(s) (expected >= {min_clusters})"


# ---------------------------------------------------------------------------
# Predicate: should_be_present
# ---------------------------------------------------------------------------

def should_be_present(
    clusters: list[dict],
    key_phrase: str,
    in_top_n: int = 50,
    min_overlap: float = 0.5,
) -> tuple[str, str]:
    """At least one cluster matches key_phrase semantically and lands in top N.

    "Top N" is computed via _ranked_order(): source_count desc, article_count
    desc. We deliberately don't run the full importance_ranker — the
    clustering suite tests clustering, not ranking.

    Grading:
        CORRECT      = matched cluster found in top in_top_n
        ACCEPTABLE   = matched cluster present but ranks just outside (within 50%)
        WRONG        = matched cluster present but ranks far below (>50% beyond)
        CATASTROPHIC = no matched cluster at all (story missing)
    """
    ranked = _ranked_order(clusters)
    idx, match, ratio = _match_key_phrase(ranked, key_phrase, min_overlap=min_overlap)
    if match is None:
        return "CATASTROPHIC", (
            f"no cluster matched key_phrase '{key_phrase}' "
            f"(best overlap {ratio:.0%})"
        )
    rank = idx + 1  # 1-indexed
    if rank <= in_top_n:
        return "CORRECT", (
            f"matched '{match.get('title', '')[:60]}' at rank {rank}/{len(ranked)} "
            f"(overlap {ratio:.0%})"
        )
    # Outside top N
    overflow = rank - in_top_n
    if overflow <= int(in_top_n * 0.5):
        grade = "ACCEPTABLE"
    else:
        grade = "WRONG"
    return grade, (
        f"matched '{match.get('title', '')[:60]}' at rank {rank} "
        f"(expected top {in_top_n}, overflow {overflow})"
    )


# ---------------------------------------------------------------------------
# Predicate: should_dampen
# ---------------------------------------------------------------------------

def should_dampen(
    clusters: list[dict],
    key_phrase: str,
    wire_share_max: float = 0.6,
    rank_floor: int = 10,
    min_overlap: float = 0.4,
) -> tuple[str, str]:
    """Wire-amplification dampener.

    The matched cluster:
      (a) has wire_share <= wire_share_max
      (b) does NOT rank in top (rank_floor - 1) -- its rank must be >= rank_floor

    Used for fixtures like `004-hantavirus-wire-amplification.yaml` where
    33 articles are mostly AP/Reuters reprints — the cluster should exist
    but should not displace independently-reported stories.

    Grading:
        CORRECT      = wire_share <= max AND rank >= floor
        ACCEPTABLE   = misses one bound by <=10% (wire) or 1-2 ranks (rank)
        WRONG        = misses one bound by more
        CATASTROPHIC = matched cluster is rank #1 with wire_share > 0.7
    """
    ranked = _ranked_order(clusters)
    idx, match, ratio = _match_key_phrase(ranked, key_phrase, min_overlap=min_overlap)
    if match is None:
        return "WRONG", f"no cluster matched key_phrase '{key_phrase}'"
    rank = idx + 1
    wshare = _wire_share(match)

    issues: list[str] = []
    grades: list[str] = ["CORRECT"]

    # Wire-share check
    if wshare > wire_share_max:
        excess = wshare - wire_share_max
        if excess <= 0.10:
            grades.append("ACCEPTABLE")
        elif excess >= 0.30:
            grades.append("WRONG")
        else:
            grades.append("WRONG")
        issues.append(f"wire_share={wshare:.0%} > {wire_share_max:.0%}")

    # Rank floor: cluster must sit at rank >= rank_floor (i.e., NOT too high)
    if rank < rank_floor:
        deficit = rank_floor - rank
        if deficit <= 2:
            grades.append("ACCEPTABLE")
        else:
            grades.append("WRONG")
        issues.append(f"rank={rank} < floor {rank_floor}")

    # Catastrophic override
    if rank == 1 and wshare > 0.7:
        grades.append("CATASTROPHIC")
        issues.append("rank #1 wire-amplified cluster")

    grade = _worst_grade(grades)
    if not issues:
        return grade, (
            f"matched '{match.get('title', '')[:60]}' rank={rank} "
            f"wire_share={wshare:.0%} (within bounds)"
        )
    return grade, "; ".join(issues) + (
        f" | matched '{match.get('title', '')[:60]}'"
    )


# ---------------------------------------------------------------------------
# Predicate: should_tag
# ---------------------------------------------------------------------------

def should_tag(
    clusters: list[dict],
    key_phrase: str,
    expected_section: str | None = None,
    expected_category: str | None = None,
    min_overlap: float = 0.4,
) -> tuple[str, str]:
    """Cluster's section (and optionally category) must match expected.

    Section comes directly from cluster_stories() output (`section` key).
    Category is computed via pipeline.categorizer.auto_categorize on the
    cluster's anchor article when expected_category is supplied.

    Grading:
        CORRECT      = both section and category match
        ACCEPTABLE   = section matches but category in secondary list
        WRONG        = section mismatch (e.g., expected world, got us)
        CATASTROPHIC = section AND category both wildly wrong
    """
    ranked = _ranked_order(clusters)
    idx, match, ratio = _match_key_phrase(ranked, key_phrase, min_overlap=min_overlap)
    if match is None:
        return "WRONG", f"no cluster matched key_phrase '{key_phrase}'"

    actual_section = (match.get("section") or "").lower()
    issues: list[str] = []
    grades: list[str] = ["CORRECT"]

    if expected_section is not None:
        if actual_section != expected_section.lower():
            issues.append(
                f"section: got '{actual_section}', expected '{expected_section}'"
            )
            grades.append("WRONG")

    if expected_category is not None:
        # Lazy import — categorizer pulls in spaCy and is slow at module load.
        try:
            from categorizer.auto_categorize import categorize_article, map_to_desk
            anchor = (match.get("articles") or [None])[0]
            if anchor is None:
                grades.append("WRONG")
                issues.append("cluster has no articles for category check")
            else:
                cats = categorize_article(anchor)
                desks = [map_to_desk(c) for c in cats]
                if expected_category in cats or expected_category in desks:
                    pass  # CORRECT
                else:
                    # ACCEPTABLE if expected appears in secondary list
                    grades.append("WRONG")
                    issues.append(
                        f"category: got {cats[:2]}, expected '{expected_category}'"
                    )
        except Exception as e:
            grades.append("WRONG")
            issues.append(f"category check failed: {e}")

    # Catastrophic override: when both section and category are wrong
    if expected_section is not None and expected_category is not None:
        if (issues and any("section" in i for i in issues)
                and any("category" in i for i in issues)):
            grades.append("CATASTROPHIC")

    grade = _worst_grade(grades)
    if not issues:
        return grade, (
            f"section='{actual_section}'"
            + (f" + category check passed" if expected_category else "")
        )
    return grade, "; ".join(issues)


# ---------------------------------------------------------------------------
# Predicate: should_have_signal
# ---------------------------------------------------------------------------

def should_have_signal(
    clusters: list[dict],
    signal_name: str,
    nonzero_min_fraction: float = 0.30,
    top_n: int = 10,
) -> tuple[str, str]:
    """Cohort signal-health check.

    Looks at the top_n clusters (by _ranked_order) and computes the
    fraction with a non-zero value for `signal_name`. Two interpretations
    supported:

    - signal_name == "bias_diversity": computed as max(lean) - min(lean)
      over a cluster's per-article `bias_score.political_lean` values.
      Non-zero = spread > 0.
    - any other name: looked up directly on each cluster dict; non-zero =
      truthy value.

    Grading:
        CORRECT      = fraction >= nonzero_min_fraction
        ACCEPTABLE   = within 10pp of floor
        WRONG        = within 25pp of floor
        CATASTROPHIC = fraction == 0
    """
    if not clusters:
        return "CATASTROPHIC", "no clusters produced"
    ranked = _ranked_order(clusters)[:top_n]
    if not ranked:
        return "WRONG", "no top clusters to inspect"

    nonzero = 0
    for c in ranked:
        if signal_name == "bias_diversity":
            leans: list[float] = []
            for a in c.get("articles") or []:
                bs = a.get("bias_score") or {}
                if isinstance(bs, dict) and "political_lean" in bs:
                    try:
                        leans.append(float(bs["political_lean"]))
                    except (TypeError, ValueError):
                        continue
            if len(leans) >= 2 and (max(leans) - min(leans)) > 0:
                nonzero += 1
        else:
            v = c.get(signal_name)
            if v:
                nonzero += 1

    fraction = nonzero / len(ranked)
    if fraction >= nonzero_min_fraction:
        return "CORRECT", (
            f"{nonzero}/{len(ranked)} clusters have non-zero {signal_name} "
            f"({fraction:.0%} >= {nonzero_min_fraction:.0%})"
        )
    gap = nonzero_min_fraction - fraction
    if fraction == 0:
        grade = "CATASTROPHIC"
    elif gap <= 0.10:
        grade = "ACCEPTABLE"
    elif gap <= 0.25:
        grade = "WRONG"
    else:
        grade = "WRONG"
    return grade, (
        f"only {nonzero}/{len(ranked)} have non-zero {signal_name} "
        f"({fraction:.0%}, need {nonzero_min_fraction:.0%})"
    )


# ---------------------------------------------------------------------------
# Predicate: should_tag_each
# ---------------------------------------------------------------------------

def should_tag_each(
    clusters: list[dict],
    cases: list[dict],
    min_overlap: float = 0.4,
) -> tuple[str, str]:
    """Composite tagging predicate: assert section/category for many clusters.

    `cases` is a list of dicts each with keys:
        key_phrase: str — phrase to match a cluster on
        expected_section: optional — "us", "world", etc.
        expected_category: optional — "politics", "science", etc.

    Used by 021-overflow-classification.yaml to assert that the same
    cluster_stories() run correctly tags 5 us-domestic, 5 international,
    5 mixed (international by edition policy).

    Grading:
        CORRECT      = every case satisfied
        ACCEPTABLE   = at most 1 case fails
        WRONG        = 2-3 cases fail
        CATASTROPHIC = >3 cases fail (or all fail)
    """
    if not cases:
        return "CORRECT", "no cases supplied"
    n = len(cases)
    failures: list[str] = []
    for i, case in enumerate(cases, 1):
        key_phrase = case.get("key_phrase", "")
        exp_sec = case.get("expected_section")
        exp_cat = case.get("expected_category")
        grade, msg = should_tag(
            clusters,
            key_phrase=key_phrase,
            expected_section=exp_sec,
            expected_category=exp_cat,
            min_overlap=min_overlap,
        )
        if grade != "CORRECT":
            failures.append(f"case {i} ({key_phrase[:30]}): {msg}")

    if not failures:
        return "CORRECT", f"all {n} tagging cases satisfied"

    n_fail = len(failures)
    if n_fail == 1:
        grade = "ACCEPTABLE"
    elif n_fail <= 3:
        grade = "WRONG"
    elif n_fail > n // 2:
        grade = "CATASTROPHIC"
    else:
        grade = "WRONG"
    return grade, f"{n_fail}/{n} cases failed: " + " | ".join(failures[:3])


# ---------------------------------------------------------------------------
# Size-distribution predicates
# ---------------------------------------------------------------------------

def should_have_capped_source_count(
    clusters: list[dict],
    max_allowed: int = 75,
    **_: Any,
) -> tuple[str, str]:
    """No cluster's stored source_count exceeds max_allowed.

    This is the post-mortem guard for the 217-source mega-cluster
    regression. Phase 5's soft cap is supposed to bring stored
    source_count down to MEGA_CLUSTER_THRESHOLD (75) when a force-split
    can't cleanly recover an over-merge. If any cluster's source_count
    is above max_allowed, the cap was bypassed (rerank overwrite, missing
    flag, etc.) OR a merge phase pushed past it without Phase 5 catching.

    CORRECT      — all clusters at or below max_allowed
    ACCEPTABLE   — at most one cluster is over by <=5
    WRONG        — one cluster over by >5, OR two clusters over
    CATASTROPHIC — one cluster over by >max_allowed (e.g. 150 when cap=75)
    """
    if not clusters:
        return "CORRECT", "no clusters in output"

    over = [
        (c.get("title", "")[:60], c.get("source_count", 0))
        for c in clusters
        if (c.get("source_count", 0) or 0) > max_allowed
    ]
    if not over:
        return "CORRECT", (
            f"all {len(clusters)} clusters at or below "
            f"max_allowed={max_allowed}"
        )

    worst = max(sc for _, sc in over)
    gap = worst - max_allowed
    examples = ", ".join(f"{t!r}={sc}" for t, sc in over[:3])

    if gap > max_allowed:
        grade = "CATASTROPHIC"
    elif len(over) == 1 and gap <= 5:
        grade = "ACCEPTABLE"
    elif len(over) == 1:
        grade = "WRONG"
    else:
        grade = "WRONG"

    return grade, (
        f"{len(over)} cluster(s) above max_allowed={max_allowed} "
        f"(worst={worst}, gap={gap}): {examples}"
    )


# ---------------------------------------------------------------------------
# Predicate dispatch
# ---------------------------------------------------------------------------

PREDICATES = {
    "should_merge": should_merge,
    "should_split": should_split,
    "should_be_present": should_be_present,
    "should_dampen": should_dampen,
    "should_tag": should_tag,
    "should_tag_each": should_tag_each,
    "should_have_signal": should_have_signal,
    "should_have_capped_source_count": should_have_capped_source_count,
}


def evaluate(
    clusters: list[dict],
    expectation: dict,
) -> tuple[str, str]:
    """Dispatch on `expectation.type` and run the matching predicate.

    Returns (grade, message). Unknown types return ("WRONG", "...").
    """
    ptype = expectation.get("type")
    fn = PREDICATES.get(ptype)
    if fn is None:
        return "WRONG", f"unknown predicate type '{ptype}'"

    # Build kwargs by stripping 'type' and passing the rest through
    kwargs = {k: v for k, v in expectation.items() if k != "type"}
    try:
        return fn(clusters, **kwargs)
    except TypeError as e:
        return "WRONG", f"predicate signature error: {e}"
    except Exception as e:
        return "WRONG", f"predicate raised: {type(e).__name__}: {e}"
