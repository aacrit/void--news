#!/usr/bin/env python3
"""
Pre/Post Bias Engine v5.0 Rescore Comparison Analysis

Compares the current (post-rescore) bias scores against known PRE-rescore baselines
to measure improvement across all 5 axes and per-tier/per-outlet patterns.
"""

import os
import sys
import json
import statistics
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, '/home/aacrit/projects/void-news/pipeline')

from utils.supabase_client import supabase

# PRE-rescore baselines from earlier audit
PRE_BASELINES = {
    "political_lean": {"mean": 50.1, "note": "perfectly neutral, maybe too flat"},
    "sensationalism": {"mean": 10.1, "note": "91% measured"},
    "opinion_fact": {"mean": 17.8, "note": "65% reporting-only"},
    "factual_rigor": {"mean": 26.6, "note": "53% at zero — THIS WAS THE BROKEN ONE"},
    "framing": {"mean": 15.0, "note": "estimate"},
    "confidence": {"mean": 0.65, "note": "estimate"},
}

AXES = ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing"]
CONFIDENCE = "confidence"

def fetch_all_scores(limit=10000):
    """Fetch all bias scores from the database with article and source info."""
    print(f"[*] Fetching up to {limit} bias scores with source metadata...")
    try:
        # Fetch bias scores with linked article info
        result = supabase.table("bias_scores").select(
            "article_id, political_lean, sensationalism, opinion_fact, factual_rigor, framing, confidence, articles(word_count, full_text, source_id, section, published_at)"
        ).limit(limit).execute()

        scores = result.data
        print(f"[✓] Fetched {len(scores)} scores")

        # Extract source_ids
        source_ids = []
        for score in scores:
            article = score.get("articles")
            if article and isinstance(article, dict):
                source_id = article.get("source_id")
                if source_id:
                    source_ids.append(source_id)

        source_ids = list(set(source_ids))
        print(f"[*] Found {len(source_ids)} unique sources, fetching metadata...")

        # Fetch sources in batches
        sources_by_id = {}
        if source_ids:
            sources_result = supabase.table("sources").select("id, slug, tier, name").in_("id", source_ids).execute()
            sources_by_id = {s["id"]: s for s in sources_result.data}
            print(f"[✓] Fetched {len(sources_by_id)} source records")

        # Inject source info into each score
        for score in scores:
            article = score.get("articles")
            if article and isinstance(article, dict):
                source_id = article.get("source_id")
                if source_id in sources_by_id:
                    score["source"] = sources_by_id[source_id]

        return scores
    except Exception as e:
        print(f"[error] Failed to fetch scores: {e}")
        import traceback
        traceback.print_exc()
        return []

def analyze_distributions(scores, axis_name):
    """Compute mean, median, stdev, min, max, percentiles, and histogram."""
    values = [s[axis_name] for s in scores if s.get(axis_name) is not None]

    if not values:
        return None

    values_sorted = sorted(values)
    n = len(values)

    result = {
        "count": n,
        "mean": round(statistics.mean(values), 2),
        "median": round(statistics.median(values), 2),
        "stdev": round(statistics.stdev(values), 2) if n > 1 else 0,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "p10": round(values_sorted[n // 10], 2),
        "p25": round(values_sorted[n // 4], 2),
        "p50": round(values_sorted[n // 2], 2),
        "p75": round(values_sorted[3 * n // 4], 2),
        "p90": round(values_sorted[9 * n // 10], 2),
    }

    # Histogram: 10 buckets (0-9, 10-19, ..., 90-100) + one for 100
    buckets = [0] * 11
    for v in values:
        bucket = min(int(v / 10), 10)
        buckets[bucket] += 1
    result["distribution"] = buckets

    return result

def compute_comparison(pre_mean, post_mean):
    """Compute change metrics."""
    if pre_mean is None or post_mean is None:
        return {"change": None, "pct_change": None}

    change = round(post_mean - pre_mean, 2)
    pct_change = round((change / pre_mean * 100), 1) if pre_mean != 0 else None
    return {"change": change, "pct_change": pct_change}

def per_tier_analysis(scores):
    """Compute average scores per source tier."""
    tier_scores = defaultdict(list)

    for score_record in scores:
        source = score_record.get("source")
        if not source:
            continue
        tier = source.get("tier", "unknown")

        for axis in AXES:
            if score_record.get(axis) is not None:
                tier_scores[tier].append((axis, score_record[axis]))

    # Aggregate by tier and axis
    tier_stats = {}
    for tier in sorted(tier_scores.keys()):
        tier_stats[tier] = {}
        for axis in AXES:
            values = [v for a, v in tier_scores[tier] if a == axis]
            if values:
                tier_stats[tier][axis] = {
                    "mean": round(statistics.mean(values), 2),
                    "count": len(values),
                    "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                }
            else:
                tier_stats[tier][axis] = {"mean": None, "count": 0}

    return tier_stats

def outlet_spot_checks(scores):
    """Compute average scores for key outlets."""
    outlet_scores = defaultdict(list)

    for score_record in scores:
        source = score_record.get("source")
        if not source:
            continue
        slug = source.get("slug", "unknown")

        for axis in AXES:
            if score_record.get(axis) is not None:
                outlet_scores[slug].append((axis, score_record[axis]))

        if CONFIDENCE in score_record and score_record[CONFIDENCE] is not None:
            outlet_scores[slug].append((CONFIDENCE, score_record[CONFIDENCE]))

    # Key outlets to check
    key_outlets = [
        "ap-news", "reuters", "fox-news", "breitbart",
        "cnn", "msnbc", "the-intercept", "common-dreams",
        "rt", "cgtn",  "heritage-foundation", "bbc-news",
        "al-jazeera", "npr"
    ]

    outlet_stats = {}
    for slug in key_outlets:
        if slug in outlet_scores:
            outlet_stats[slug] = {}
            for axis in AXES + [CONFIDENCE]:
                values = [v for a, v in outlet_scores[slug] if a == axis]
                if values:
                    outlet_stats[slug][axis] = {
                        "mean": round(statistics.mean(values), 2),
                        "count": len(values),
                        "stdev": round(statistics.stdev(values), 2) if len(values) > 1 else 0,
                    }
                else:
                    outlet_stats[slug][axis] = {"mean": None, "count": 0}
        else:
            outlet_stats[slug] = {axis: {"mean": None, "count": 0} for axis in AXES + [CONFIDENCE]}

    return outlet_stats

def main():
    """Run the full comparison analysis."""
    print("\n" + "=" * 80)
    print("PRE/POST BIAS ENGINE v5.0 RESCORE COMPARISON ANALYSIS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().isoformat()}\n")

    # 1. Fetch all current scores
    scores = fetch_all_scores(limit=10000)
    if not scores:
        print("[fatal] No scores found in database")
        return

    # 2. Overall distribution analysis
    print("\n" + "-" * 80)
    print("OVERALL SCORE DISTRIBUTIONS (POST-RESCORE v5.0)")
    print("-" * 80)

    comparison_data = {}
    for axis in AXES + [CONFIDENCE]:
        post_dist = analyze_distributions(scores, axis)
        if post_dist:
            pre_mean = PRE_BASELINES.get(axis, {}).get("mean")
            post_mean = post_dist["mean"]
            comp = compute_comparison(pre_mean, post_mean)

            comparison_data[axis] = {
                "pre": pre_mean,
                "post": post_mean,
                "change": comp["change"],
                "pct_change": comp["pct_change"],
                "post_dist": post_dist,
            }

            print(f"\n{axis.upper()}:")
            print(f"  PRE (old):  mean={pre_mean}")
            print(f"  POST (v5):  mean={post_mean:.2f}  stdev={post_dist['stdev']:.2f}  n={post_dist['count']}")
            if comp["change"] is not None:
                print(f"  CHANGE:     {comp['change']:+.2f} ({comp['pct_change']:+.1f}%)")
            print(f"  [p10={post_dist['p10']}, p25={post_dist['p25']}, p50={post_dist['p50']}, p75={post_dist['p75']}, p90={post_dist['p90']}]")
            print(f"  Distribution (0-9, 10-19, ..., 90-100): {post_dist['distribution']}")

    # 3. Per-tier analysis
    print("\n" + "-" * 80)
    print("PER-TIER AVERAGE SCORES (POST-RESCORE)")
    print("-" * 80)

    tier_stats = per_tier_analysis(scores)
    for tier in sorted(tier_stats.keys()):
        print(f"\n{tier.upper()}:")
        for axis in AXES:
            stats = tier_stats[tier][axis]
            if stats["mean"] is not None:
                print(f"  {axis:20s}: mean={stats['mean']:6.2f}  stdev={stats['stdev']:6.2f}  n={stats['count']:5d}")
            else:
                print(f"  {axis:20s}: NO DATA")

    # 4. Key outlet spot-checks
    print("\n" + "-" * 80)
    print("KEY OUTLET SPOT-CHECKS (POST-RESCORE)")
    print("-" * 80)

    outlet_stats = outlet_spot_checks(scores)

    print(f"\n{'OUTLET':<25} {'LEAN':>8} {'SENS':>8} {'OPIN':>8} {'FACT':>8} {'FRAM':>8} {'CONF':>8}")
    print("-" * 100)

    for slug in sorted(outlet_stats.keys()):
        stats = outlet_stats[slug]
        name = slug.replace("-", " ").title()
        lean = stats.get("political_lean", {}).get("mean", "—")
        sens = stats.get("sensationalism", {}).get("mean", "—")
        opin = stats.get("opinion_fact", {}).get("mean", "—")
        fact = stats.get("factual_rigor", {}).get("mean", "—")
        fram = stats.get("framing", {}).get("mean", "—")
        conf = stats.get("confidence", {}).get("mean", "—")

        print(f"{name:<25} {lean!s:>8} {sens!s:>8} {opin!s:>8} {fact!s:>8} {fram!s:>8} {conf!s:>8}")

    # 5. Summary table
    print("\n" + "-" * 80)
    print("SUMMARY: PRE vs POST COMPARISON")
    print("-" * 80)
    print(f"\n{'AXIS':<25} {'PRE (old)':<15} {'POST (v5.0)':<15} {'CHANGE':<12} {'ASSESSMENT':<30}")
    print("-" * 97)

    for axis in AXES + [CONFIDENCE]:
        if axis in comparison_data:
            data = comparison_data[axis]
            pre = data["pre"]
            post = data["post"]
            change = data["change"]
            pct = data["pct_change"]

            if change is None:
                assess = "NO PRE-DATA"
            elif abs(change) < 0.5:
                assess = "No significant change"
            elif axis == "factual_rigor" and change > 0:
                assess = "IMPROVED (less zeros!)"
            elif axis == "sensationalism" and change < 0:
                assess = "IMPROVED (more measured)"
            elif axis == "political_lean" and abs(change) < 1:
                assess = "Stable (good)"
            else:
                assess = f"Changed {change:+.1f}"

            print(f"{axis:<25} {pre!s:<15} {post:<15.2f} {change:+.2f} ({pct:+.1f}%) {assess:<30}")

    # 6. Key findings
    print("\n" + "-" * 80)
    print("KEY FINDINGS")
    print("-" * 80)

    # Check for critical improvements
    fact_change = comparison_data.get("factual_rigor", {}).get("change", 0)
    if fact_change > 5:
        print("\n[CRITICAL] Factual Rigor IMPROVED significantly (>5 points!)")
        post_fact = comparison_data.get("factual_rigor", {}).get("post_dist", {}).get("distribution", [])
        if post_fact and len(post_fact) > 0:
            zero_bucket = post_fact[0]
            total = sum(post_fact)
            pct_zero = (zero_bucket / total * 100) if total > 0 else 0
            print(f"  Articles with factual_rigor=0-9: {zero_bucket} ({pct_zero:.1f}% of {total})")

    sens_change = comparison_data.get("sensationalism", {}).get("change", 0)
    if sens_change < -2:
        print(f"\n[NOTE] Sensationalism DECREASED by {-sens_change:.1f} points (articles more measured)")

    lean_change = comparison_data.get("political_lean", {}).get("change", 0)
    if abs(lean_change) > 2:
        print(f"\n[NOTE] Political Lean SHIFTED by {lean_change:+.1f} points")
    elif abs(lean_change) < 1:
        print(f"\n[GOOD] Political Lean stable at {comparison_data.get('political_lean', {}).get('post'):.1f} (centered)")

    # Check outlier outlets
    print("\n[OUTLETS] Notable patterns:")
    found_patterns = False
    for slug, stats in sorted(outlet_stats.items()):
        lean = stats.get("political_lean", {}).get("mean")
        fact = stats.get("factual_rigor", {}).get("mean")

        if "ap-news" in slug or "reuters" in slug:
            if lean and (lean < 45 or lean > 55):
                print(f"  WARNING: {slug} lean={lean} (expected ~50)")
                found_patterns = True
        if "breitbart" in slug or "fox-news" in slug:
            if lean and lean < 60:
                print(f"  WARNING: {slug} lean={lean} (expected >65 for right-leaning)")
                found_patterns = True
        if fact and fact < 20:
            print(f"  CRITICAL: {slug} factual_rigor={fact} (very low)")
            found_patterns = True

    if not found_patterns:
        print("  All major outlets show expected patterns")

    print("\n" + "=" * 80 + "\n")

if __name__ == "__main__":
    main()
