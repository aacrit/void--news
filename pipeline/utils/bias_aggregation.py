"""Pure per-cluster bias aggregation helpers (Branch G, 2026-08-10).

Single source of truth for two cluster-level bias signals that used to be a
count proxy or a Python-fallback-only feature:

  1. aggregate_confidence: a real [0,1] confidence derived from the mean of the
     per-article ``bias_scores.confidence`` (rigor-weighted), lifted a little by
     coverage breadth and damped a little by cross-source lean disagreement. The
     old ``LEAST(1.0, count/5.0)`` pinned to 1.0 at 5+ articles and ignored the
     per-article confidence entirely, so it never varied across top stories and
     deadened the frontend display-position confidence damping.

  2. lean_histogram: the rev-49 7-bucket lean histogram, 3-segment L/C/R counts,
     and the polarization index (0 = one-sided/all-center, 100 = a perfect L/R
     split). These reveal the split a rigor-weighted MEAN conceals so the
     "Contested" marker (LeanCoverageBar) can light up.

The bucket boundaries match ``frontend/app/lib/biasColors.ts`` leanToBucket, and
the SQL RPC in ``supabase/migrations/076_confidence_and_histogram.sql`` mirrors
BOTH formulas exactly so the primary (RPC) and fallback (Python) paths agree.

Pure functions only: no I/O, no DB, no numpy. Cheap to unit-test offline.
"""

from __future__ import annotations

import math
from typing import Sequence

# --- aggregate_confidence weights (mirrored verbatim in migration 076) -------
# Per-article confidence is the PRIMARY driver; breadth is a secondary lift so a
# 30-source cluster edges above a 3-source cluster of equal per-article
# confidence; lean disagreement is a mild damp.
CONF_WEIGHT = 0.7          # weight on the rigor-weighted mean per-article confidence
BREADTH_WEIGHT = 0.3       # weight on the coverage-breadth term
BREADTH_FULL_AT = 12.0     # source count at which the breadth term saturates to 1.0
SPREAD_DAMP_MAX = 0.20     # at lean_spread >= 20 the estimate is damped by up to 20%
SPREAD_DAMP_SCALE = 100.0  # lean_spread is on the 0..100 political_lean scale


def compute_aggregate_confidence(
    conf_values: Sequence[float],
    rigor_values: Sequence[float],
    lean_spread: float,
) -> float:
    """Real cluster confidence in [0, 1].

    aggregate_confidence =
        clamp(
            (CONF_WEIGHT * rigor_weighted_mean(confidence)
             + BREADTH_WEIGHT * min(1, count / BREADTH_FULL_AT))
            * (1 - min(SPREAD_DAMP_MAX, lean_spread / SPREAD_DAMP_SCALE)),
            0, 1)

    Varies with BOTH the mean per-article confidence and coverage breadth, so a
    3-source low-confidence cluster scores clearly below a 30-source
    high-confidence one. Never pins to 1.0 on article count alone.
    """
    count = len(conf_values)
    if count == 0:
        return 0.0

    total_rigor = sum(rigor_values) if rigor_values else 0.0
    if total_rigor > 0 and len(rigor_values) == count:
        conf_mean = sum(c * r for c, r in zip(conf_values, rigor_values)) / total_rigor
    else:
        conf_mean = sum(conf_values) / count

    breadth = min(1.0, count / BREADTH_FULL_AT)
    raw = CONF_WEIGHT * conf_mean + BREADTH_WEIGHT * breadth
    spread_damp = 1.0 - min(SPREAD_DAMP_MAX, max(0.0, lean_spread) / SPREAD_DAMP_SCALE)
    value = raw * spread_damp
    return max(0.0, min(1.0, value))


def compute_lean_histogram(pl_values: Sequence[float]) -> dict:
    """rev-49 lean histogram, 3-segment counts, and polarization.

    Buckets match biasColors.ts leanToBucket boundaries. Returns the exact JSON
    shape the frontend already reads out of ``bias_diversity``:
        lean_buckets, lean_left_count, lean_center_count, lean_right_count,
        polarization.
    """
    count = len(pl_values)
    # Bins centred on the seven outlet baselines from
    # `analyzers/political_lean.py` BASELINE_MAP, boundaries at the midpoints
    # between them (15, 27.5, 42.5, 57.5, 72.5, 85). A score on a boundary
    # takes the rung nearer the centre.
    #
    # These were `<=20, <=35, <=45, <=55, <=65, <=80` until 2026-09-21, which
    # put the `left` baseline (20) in FAR LEFT and the `center-left` baseline
    # (35) in LEFT while the right-hand rungs landed correctly, so a
    # left-leaning outlet publishing unremarkable copy was binned one rung
    # more extreme than the roster rates it and a right-leaning one was not.
    # Mirrored EXACTLY by `leanToBucket` in frontend/app/lib/biasColors.ts;
    # tests/test_bias_bins.py asserts the two agree on every score 0..100.
    _BASELINES = (("far_left", 10), ("left", 20), ("center_left", 35),
                  ("center", 50), ("center_right", 65), ("right", 80),
                  ("far_right", 90))

    def _bin(v):
        best, best_gap, best_pull = "center", float("inf"), float("inf")
        for name, base in _BASELINES:
            gap, pull = abs(v - base), abs(base - 50)
            if gap < best_gap - 1e-9 or (abs(gap - best_gap) < 1e-9 and pull < best_pull):
                best, best_gap, best_pull = name, gap, pull
        return best

    lean_buckets = {name: 0 for name, _ in _BASELINES}
    for v in pl_values:
        lean_buckets[_bin(v)] += 1
    lean_left_count = (
        lean_buckets["far_left"] + lean_buckets["left"] + lean_buckets["center_left"]
    )
    lean_center_count = lean_buckets["center"]
    lean_right_count = (
        lean_buckets["center_right"] + lean_buckets["right"] + lean_buckets["far_right"]
    )
    polarization = (
        round(100.0 * (2.0 * min(lean_left_count, lean_right_count) / count))
        if count
        else 0
    )
    return {
        "lean_buckets": lean_buckets,
        "lean_left_count": lean_left_count,
        "lean_center_count": lean_center_count,
        "lean_right_count": lean_right_count,
        "polarization": polarization,
    }


def outlet_positions(rows: Sequence[dict]) -> list[dict]:
    """Collapse measured article rows to one position per OUTLET.

    ``rows``: dicts with ``outlet`` (any stable key; the export uses the
    source name), ``lean`` (0..100) and optionally ``name`` and
    ``state_affiliated``. Rows are assumed to be MEASURED already: the
    caller drops ``lean_unscored`` rows first, exactly as it always has.

    An outlet's position is the plain mean of its measured articles' leans in
    this cluster. One vote per outlet, because ten RT articles are one view,
    not ten (CEO decision 3, 2026-10-02). The Deep Dive Bench draws one mark
    per outlet at this same mean (`frontend/app/lib/outletVotes.ts`), which is
    what lets the card's word and the Bench's word be asserted equal.

    Returned in first-seen order, so the output is deterministic for a given
    row order.
    """
    order: list[str] = []
    acc: dict[str, dict] = {}
    for r in rows:
        key = str(r.get("outlet") or "").strip().lower()
        if not key:
            continue
        if key not in acc:
            order.append(key)
            acc[key] = {"name": r.get("name") or r.get("outlet"), "sum": 0.0,
                        "n": 0, "state_affiliated": bool(r.get("state_affiliated"))}
        acc[key]["sum"] += float(r["lean"])
        acc[key]["n"] += 1
        acc[key]["state_affiliated"] = acc[key]["state_affiliated"] or bool(r.get("state_affiliated"))
    return [
        {"outlet": k, "name": acc[k]["name"], "lean": acc[k]["sum"] / acc[k]["n"],
         "articles": acc[k]["n"], "state_affiliated": acc[k]["state_affiliated"]}
        for k in order
    ]


def compute_outlet_lean_histogram(rows: Sequence[dict]) -> dict:
    """The lean histogram the product prints: one vote per OUTLET.

    ``compute_lean_histogram`` counts whatever it is handed. Until 2026-10-02
    it was handed one value per ARTICLE, while the Deep Dive Bench drew one
    mark per outlet, so on the 2026-10-01 feed 3 of the 20 cards printed a
    different word from their own Deep Dive (417 article votes from 347
    outlets). This wraps it so there is one counting rule and it is computed
    here, once, for both.

    Adds to the dict ``compute_lean_histogram`` returns:
        lean_vote            "outlet", so a reader of the payload can tell a
                             per-outlet histogram from a pre-2026-10-02 one.
        lean_outlet_count    outlets in the seven buckets (the "N placed").
        lean_article_count   measured articles behind them.
    """
    outlets = outlet_positions(rows)
    placed = outlets
    hist = compute_lean_histogram([o["lean"] for o in placed])
    hist.update({
        "lean_vote": "outlet",
        "lean_outlet_count": len(placed),
        "lean_article_count": sum(o["articles"] for o in outlets),
    })
    return hist


def stddev(vals: Sequence[float]) -> float:
    """Population standard deviation (matches the pipeline's fallback helper)."""
    if len(vals) < 2:
        return 0.0
    mean = sum(vals) / len(vals)
    return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
