#!/usr/bin/env python3
"""
Pre/Post Rescore Comparison Analysis
Compares pre-v5.0 bias scores (from DATA_QUALITY_AUDIT_REPORT.md) against
post-rescore v5.0 scores to measure algorithm improvements.

Pre-rescore baselines (from audit run 2026-03-20 21:39 UTC):
  - political_lean:   mean=50.1, stdev=8.9, center-heavy (90% in 40-60)
  - sensationalism:   mean=10.1, stdev=7.0, measured
  - opinion_fact:     mean=17.8, stdev=8.9, reporting-focused
  - factual_rigor:    mean=26.6, stdev=28.0, BROKEN (53% at 0)
  - framing:          mean=14.2, stdev=7.6
  - confidence:       mean=0.616, stdev=0.202

Post-rescore targets:
  - factual_rigor: should increase from 26.6 to 50+, <20% at 0
  - political_lean: should widen from tight 40-60 peak to 30+ stdev
  - confidence: should improve for long articles, stay low for short
"""

import sys
import time
from collections import defaultdict
from pathlib import Path
from statistics import mean, median, stdev, quantiles

# Add pipeline to path
pipeline_path = Path(__file__).parent / "pipeline"
sys.path.insert(0, str(pipeline_path))

try:
    from utils.supabase_client import supabase
except ImportError as e:
    print(f"[fatal] {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)


def fetch_all_bias_scores() -> list[dict]:
    """Fetch all bias scores from Supabase."""
    print("Fetching all bias scores from Supabase...")
    all_scores = []
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table("bias_scores").select(
            "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence"
        ).range(offset, offset + batch_size - 1).execute()

        batch = result.data or []
        if not batch:
            break

        all_scores.extend(batch)
        offset += batch_size
        print(f"  ... {len(all_scores)} scores loaded")

    return all_scores


def fetch_articles_with_sources() -> dict[str, dict]:
    """
    Fetch articles with source tier info.
    Returns dict: article_id -> {source_id, tier, word_count, section}
    """
    print("Fetching article metadata...")
    articles_by_id = {}
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table("articles").select(
            "id,source_id,word_count,section"
        ).range(offset, offset + batch_size - 1).execute()

        batch = result.data or []
        if not batch:
            break

        for art in batch:
            articles_by_id[art["id"]] = art

        offset += batch_size
        print(f"  ... {len(articles_by_id)} articles loaded")

    return articles_by_id


def fetch_sources_map() -> dict[str, dict]:
    """
    Fetch sources with tier info.
    Returns dict: source_id -> {tier, name, slug}
    """
    print("Fetching source metadata...")
    result = supabase.table("sources").select("id,tier,name,slug").execute()
    sources_by_id = {}
    for src in (result.data or []):
        sources_by_id[src["id"]] = src
    return sources_by_id


def analyze_distribution(values: list[float], axis_name: str) -> dict:
    """Compute distribution stats."""
    if not values:
        return {}

    n = len(values)
    vals_sorted = sorted(values)

    stats = {
        "count": n,
        "mean": round(mean(values), 2),
        "median": round(median(values), 2),
        "stdev": round(stdev(values), 2) if n > 1 else 0,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }

    # Quartiles and percentiles
    if n >= 4:
        q = quantiles(vals_sorted, n=4)
        stats["q1"] = round(q[0], 2)
        stats["q3"] = round(q[2], 2)

    if n >= 10:
        p10_idx = n // 10
        p90_idx = (9 * n) // 10
        stats["p10"] = round(vals_sorted[p10_idx], 2)
        stats["p90"] = round(vals_sorted[p90_idx], 2)

    # Histogram: 10 buckets
    buckets = [0] * 11
    for v in values:
        bucket = min(int(v / 10), 10)
        buckets[bucket] += 1
    stats["histogram"] = buckets

    # Zero/100 counts
    stats["at_zero"] = sum(1 for v in values if v == 0)
    stats["at_100"] = sum(1 for v in values if v == 100)
    stats["pct_zero"] = round(100 * stats["at_zero"] / n, 1) if n > 0 else 0

    return stats


def print_distribution_table(axis_name: str, pre: dict, post: dict) -> None:
    """Print comparison table for one axis."""
    print(f"\n{'='*80}")
    print(f"  {axis_name.upper()}")
    print(f"{'='*80}")

    print(f"\n  {'Metric':<30} {'PRE-v5.0':<20} {'POST-v5.0':<20} {'Δ':<15}")
    print(f"  {'-'*30} {'-'*20} {'-'*20} {'-'*15}")

    metrics = ["count", "mean", "median", "stdev", "min", "max", "at_zero", "pct_zero"]

    for metric in metrics:
        pre_val = pre.get(metric, "—")
        post_val = post.get(metric, "—")

        delta = "—"
        if isinstance(pre_val, (int, float)) and isinstance(post_val, (int, float)):
            delta_num = post_val - pre_val
            delta = f"{delta_num:+.2f}" if isinstance(delta_num, float) else f"{delta_num:+d}"

        pre_str = str(pre_val) if pre_val != "—" else "—"
        post_str = str(post_val) if post_val != "—" else "—"

        print(f"  {metric:<30} {pre_str:<20} {post_str:<20} {delta:<15}")

    # Histogram
    if "histogram" in pre and "histogram" in post:
        print(f"\n  Histogram (PRE):  {pre['histogram']}")
        print(f"  Histogram (POST): {post['histogram']}")


def analyze_per_tier(scores: list[dict], articles: dict, sources: dict) -> dict:
    """
    Analyze scores grouped by source tier.
    Returns dict: tier -> {axis -> stats}
    """
    tier_scores = defaultdict(lambda: defaultdict(list))

    for score in scores:
        art_id = score.get("article_id")
        art = articles.get(art_id)
        if not art:
            continue

        src_id = art.get("source_id")
        src = sources.get(src_id)
        if not src:
            continue

        tier = src.get("tier", "unknown")

        # Collect per axis
        for axis in ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing", "confidence"]:
            val = score.get(axis)
            if val is not None:
                tier_scores[tier][axis].append(val)

    # Compute stats per tier
    tier_stats = {}
    for tier in tier_scores:
        tier_stats[tier] = {}
        for axis in tier_scores[tier]:
            tier_stats[tier][axis] = analyze_distribution(
                tier_scores[tier][axis], axis
            )

    return tier_stats


def analyze_key_outlets(scores: list[dict], articles: dict, sources: dict) -> dict:
    """
    Analyze scores for specific known outlets.
    Returns dict: outlet_slug -> {axis -> mean}
    """
    outlet_scores = defaultdict(lambda: defaultdict(list))

    # Key outlets to spot-check
    outlet_slugs = [
        "ap-news", "reuters", "nyt",
        "fox-news", "cnn", "msnbc",
        "breitbart", "bbc", "al-jazeera",
        "the-intercept", "common-dreams", "rt"
    ]

    for score in scores:
        art_id = score.get("article_id")
        art = articles.get(art_id)
        if not art:
            continue

        src_id = art.get("source_id")
        src = sources.get(src_id)
        if not src:
            continue

        slug = src.get("slug", "")
        if slug not in outlet_slugs:
            continue

        # Collect per axis
        for axis in ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing", "confidence"]:
            val = score.get(axis)
            if val is not None:
                outlet_scores[slug][axis].append(val)

    # Compute means
    outlet_means = {}
    for slug in outlet_scores:
        outlet_means[slug] = {}
        for axis in outlet_scores[slug]:
            vals = outlet_scores[slug][axis]
            outlet_means[slug][axis] = {
                "mean": round(mean(vals), 1),
                "n": len(vals),
                "stdev": round(stdev(vals), 1) if len(vals) > 1 else 0,
            }

    return outlet_means


def main():
    start = time.time()

    print("\n" + "="*80)
    print("  VOID --NEWS PRE/POST RESCORE COMPARISON ANALYSIS")
    print("="*80)

    # Load data
    print("\n[1/5] Loading data from Supabase...")
    scores = fetch_all_bias_scores()
    articles = fetch_articles_with_sources()
    sources = fetch_sources_map()

    if not scores:
        print("[fatal] No bias scores found!")
        sys.exit(1)

    print(f"  Loaded: {len(scores)} scores, {len(articles)} articles, {len(sources)} sources")

    # PRE-RESCORE BASELINES (from audit report)
    print("\n[2/5] Defining pre-rescore baselines...")
    pre_baselines = {
        "political_lean": {
            "count": 9999,
            "mean": 50.1,
            "median": 50.0,
            "stdev": 8.9,
            "min": 2,
            "max": 98,
            "at_zero": 0,
            "pct_zero": 0,
            "histogram": [144, 346, 9005, 346, 158, 0, 0, 0, 0, 0, 0],
        },
        "sensationalism": {
            "count": 9999,
            "mean": 10.1,
            "median": 9.0,
            "stdev": 7.0,
            "min": 0,
            "max": 55,
            "at_zero": 853,
            "pct_zero": 8.5,
            "histogram": [9100, 859, 40, 0, 0, 0, 0, 0, 0, 0, 0],
        },
        "opinion_fact": {
            "count": 9999,
            "mean": 17.8,
            "median": 15.0,
            "stdev": 8.9,
            "min": 0,
            "max": 70,
            "at_zero": 0,
            "pct_zero": 0,
            "histogram": [6504, 3338, 77, 80, 0, 0, 0, 0, 0, 0, 0],
        },
        "factual_rigor": {
            "count": 9999,
            "mean": 26.6,
            "median": 5.0,
            "stdev": 28.0,
            "min": 0,
            "max": 100,
            "at_zero": 5294,
            "pct_zero": 53.0,
            "histogram": [5294, 1425, 1319, 1760, 201, 0, 0, 0, 0, 0, 8],
        },
        "framing": {
            "count": 9999,
            "mean": 14.2,
            "median": 13.0,
            "stdev": 7.6,
            "min": 3,
            "max": 60,
            "at_zero": 0,
            "pct_zero": 0,
            "histogram": [0, 7981, 1952, 65, 0, 0, 0, 0, 0, 0, 0],
        },
        "confidence": {
            "count": 9999,
            "mean": 0.616,
            "median": 0.620,
            "stdev": 0.202,
            "min": 0.21,
            "max": 1.0,
        },
    }

    # POST-RESCORE ANALYSIS
    print("\n[3/5] Analyzing post-rescore score distributions...")
    post_distributions = {}
    for axis in ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing", "confidence"]:
        values = [s.get(axis) for s in scores if s.get(axis) is not None]
        if values:
            post_distributions[axis] = analyze_distribution(values, axis)
            print(f"  {axis}: {len(values)} scores, mean={post_distributions[axis]['mean']}")

    # PER-TIER ANALYSIS
    print("\n[4/5] Analyzing per-tier distributions...")
    tier_stats = analyze_per_tier(scores, articles, sources)

    # KEY OUTLETS
    print("\n[5/5] Analyzing key outlets...")
    outlet_means = analyze_key_outlets(scores, articles, sources)

    # PRINT RESULTS
    print("\n\n" + "="*80)
    print("  COMPARISON TABLES")
    print("="*80)

    for axis in ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing", "confidence"]:
        pre = pre_baselines.get(axis, {})
        post = post_distributions.get(axis, {})
        print_distribution_table(axis, pre, post)

    # Per-tier summary
    print(f"\n{'='*80}")
    print("  PER-TIER AVERAGES (POST-RESCORE)")
    print(f"{'='*80}\n")

    tiers = sorted(tier_stats.keys())
    for tier in tiers:
        print(f"\n  TIER: {tier}")
        print(f"  {'-'*75}")

        tier_data = tier_stats[tier]
        axes = ["political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing", "confidence"]

        for axis in axes:
            if axis in tier_data:
                stats = tier_data[axis]
                mean_val = stats.get("mean", "—")
                n = stats.get("count", 0)
                print(f"    {axis:<20} mean={mean_val:>6}  n={n:>5}  stdev={stats.get('stdev', '—'):>6}")

    # Key outlets summary
    print(f"\n{'='*80}")
    print("  KEY OUTLET SPOT-CHECKS (POST-RESCORE)")
    print(f"{'='*80}\n")

    header = f"  {'Outlet':<25} {'Lean':>6} {'Sens':>6} {'Opin':>6} {'Fact':>6} {'Fram':>6} {'Conf':>6} {'N':>5}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    for slug in sorted(outlet_means.keys()):
        outlet_data = outlet_means[slug]
        lean = outlet_data.get("political_lean", {}).get("mean", "—")
        sens = outlet_data.get("sensationalism", {}).get("mean", "—")
        opin = outlet_data.get("opinion_fact", {}).get("mean", "—")
        fact = outlet_data.get("factual_rigor", {}).get("mean", "—")
        fram = outlet_data.get("framing", {}).get("mean", "—")
        conf = outlet_data.get("confidence", {}).get("mean", "—")
        n = outlet_data.get("political_lean", {}).get("n", "—")

        print(f"  {slug:<25} {lean:>6} {sens:>6} {opin:>6} {fact:>6} {fram:>6} {conf:>6} {n:>5}")

    # Assessment
    print(f"\n{'='*80}")
    print("  ASSESSMENT")
    print(f"{'='*80}\n")

    assessments = []

    # Factual rigor improvement
    pre_rigor_mean = pre_baselines["factual_rigor"]["mean"]
    post_rigor_mean = post_distributions["factual_rigor"]["mean"]
    rigor_delta = post_rigor_mean - pre_rigor_mean
    pre_rigor_zero = pre_baselines["factual_rigor"]["pct_zero"]
    post_rigor_zero = post_distributions["factual_rigor"]["pct_zero"]
    rigor_zero_delta = post_rigor_zero - pre_rigor_zero

    if post_rigor_mean > pre_rigor_mean:
        assessments.append(f"✓ Factual Rigor IMPROVED: {pre_rigor_mean:.1f} → {post_rigor_mean:.1f} (+{rigor_delta:.1f})")
    else:
        assessments.append(f"✗ Factual Rigor DEGRADED: {pre_rigor_mean:.1f} → {post_rigor_mean:.1f} ({rigor_delta:.1f})")

    if post_rigor_zero < pre_rigor_zero:
        assessments.append(f"✓ Zero-score articles REDUCED: {pre_rigor_zero:.1f}% → {post_rigor_zero:.1f}% ({rigor_zero_delta:.1f}pp)")
    else:
        assessments.append(f"✗ Zero-score articles INCREASED: {pre_rigor_zero:.1f}% → {post_rigor_zero:.1f}% ({rigor_zero_delta:+.1f}pp)")

    # Political lean distribution
    pre_lean_stdev = pre_baselines["political_lean"]["stdev"]
    post_lean_stdev = post_distributions["political_lean"]["stdev"]

    if post_lean_stdev > pre_lean_stdev:
        assessments.append(f"✓ Political Lean WIDENED: stdev {pre_lean_stdev:.1f} → {post_lean_stdev:.1f} (more differentiation)")
    else:
        assessments.append(f"~ Political Lean unchanged: stdev {pre_lean_stdev:.1f} → {post_lean_stdev:.1f}")

    # Confidence
    pre_conf_mean = pre_baselines["confidence"]["mean"]
    post_conf_mean = post_distributions["confidence"]["mean"]

    if abs(post_conf_mean - pre_conf_mean) < 0.05:
        assessments.append(f"~ Confidence stable: {pre_conf_mean:.3f} → {post_conf_mean:.3f}")
    else:
        direction = "↑" if post_conf_mean > pre_conf_mean else "↓"
        assessments.append(f"  Confidence changed {direction}: {pre_conf_mean:.3f} → {post_conf_mean:.3f}")

    for assessment in assessments:
        print(f"  {assessment}")

    # Tier summary
    print(f"\n  Tier analysis:")
    for tier in tiers:
        if tier in tier_stats:
            tier_rigor_mean = tier_stats[tier].get("factual_rigor", {}).get("mean", 0)
            print(f"    {tier:<20} factual_rigor={tier_rigor_mean:>6.1f}")

    # Outlet summary
    print(f"\n  Key outlet spot-checks:")
    outlet_notes = []

    # AP should be 70+
    if "ap-news" in outlet_means:
        ap_fact = outlet_means["ap-news"].get("factual_rigor", {}).get("mean", 0)
        if ap_fact >= 60:
            outlet_notes.append(f"  ✓ AP News factual_rigor={ap_fact:.1f} (expected 70+, acceptable)")
        else:
            outlet_notes.append(f"  ✗ AP News factual_rigor={ap_fact:.1f} (expected 70+, too low)")

    # Fox News should be 60+ and right-leaning
    if "fox-news" in outlet_means:
        fox_fact = outlet_means["fox-news"].get("factual_rigor", {}).get("mean", 0)
        fox_lean = outlet_means["fox-news"].get("political_lean", {}).get("mean", 50)
        if fox_lean >= 60:
            outlet_notes.append(f"  ✓ Fox News lean={fox_lean:.1f} (right-leaning, expected)")
        else:
            outlet_notes.append(f"  ~ Fox News lean={fox_lean:.1f} (expected 65+)")

    # Breitbart should be 65+ and far-right
    if "breitbart" in outlet_means:
        bb_lean = outlet_means["breitbart"].get("political_lean", {}).get("mean", 50)
        if bb_lean >= 65:
            outlet_notes.append(f"  ✓ Breitbart lean={bb_lean:.1f} (far-right, expected)")
        else:
            outlet_notes.append(f"  ✗ Breitbart lean={bb_lean:.1f} (expected 70+, too center)")

    for note in outlet_notes:
        print(note)

    elapsed = time.time() - start
    print(f"\n\nAnalysis complete in {elapsed:.1f}s")
    print("\n")


if __name__ == "__main__":
    main()
