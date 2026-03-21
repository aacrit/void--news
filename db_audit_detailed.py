#!/usr/bin/env python3
"""Detailed analysis of key data quality issues."""

import os
import json
from collections import defaultdict
from statistics import mean

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def analyze_orphaned_articles():
    """Deep dive into orphaned articles."""
    print("\n" + "="*70)
    print("DETAILED ISSUE 1: ORPHANED ARTICLES (4553 total)")
    print("="*70)

    # Get articles not in any cluster
    result = supabase.table("cluster_articles").select("article_id").execute()
    clustered_ids = set(ca['article_id'] for ca in (result.data or []))

    result = supabase.table("articles").select("id, source_id, published_at, word_count").execute()
    all_articles = result.data or []

    orphaned = [a for a in all_articles if a['id'] not in clustered_ids]
    print(f"Total orphaned: {len(orphaned)}")

    # Get sources for context
    result = supabase.table("sources").select("id, slug, tier").execute()
    sources = {s['id']: s for s in (result.data or [])}

    # Analyze by tier
    tier_counts = defaultdict(int)
    wc_counts = defaultdict(int)
    for article in orphaned[:100]:  # Sample
        src = sources.get(article['source_id'], {})
        tier = src.get('tier', 'unknown')
        tier_counts[tier] += 1
        wc = article.get('word_count', 0)
        if wc < 100:
            wc_counts['<100'] += 1
        elif wc < 500:
            wc_counts['100-500'] += 1
        else:
            wc_counts['500+'] += 1

    print(f"Orphaned by tier (sample of 100):")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    print(f"Orphaned by word count (sample of 100):")
    for wc_range, count in sorted(wc_counts.items()):
        print(f"  {wc_range}: {count}")

def analyze_factual_rigor_outliers():
    """Why is factual_rigor so low? 53% at 0."""
    print("\n" + "="*70)
    print("DETAILED ISSUE 2: FACTUAL RIGOR DISTRIBUTION")
    print("="*70)

    result = supabase.table("bias_scores").select("factual_rigor, rationale").execute()
    scores = result.data or []

    at_0 = [s for s in scores if s['factual_rigor'] == 0]
    at_high = [s for s in scores if s['factual_rigor'] > 80]

    print(f"Scores at 0: {len(at_0)} ({100*len(at_0)/len(scores):.1f}%)")
    print(f"Scores >80: {len(at_high)} ({100*len(at_high)/len(scores):.1f}%)")

    # Sample some rationales
    print(f"\nSample rationales for factual_rigor=0:")
    for s in at_0[:3]:
        rat = s.get('rationale', {})
        if isinstance(rat, str):
            rat = json.loads(rat)
        factual = rat.get('factual_rigor_analysis', {})
        print(f"  named_sources: {factual.get('named_sources_count')}, "
              f"data_points: {factual.get('data_points_count')}, "
              f"quotes: {factual.get('direct_quotes_count')}")

    print(f"\nSample rationales for factual_rigor>80:")
    for s in at_high[:3]:
        rat = s.get('rationale', {})
        if isinstance(rat, str):
            rat = json.loads(rat)
        factual = rat.get('factual_rigor_analysis', {})
        print(f"  named_sources: {factual.get('named_sources_count')}, "
              f"data_points: {factual.get('data_points_count')}, "
              f"quotes: {factual.get('direct_quotes_count')}")

def analyze_low_divergence():
    """Why 54.8% of clusters have divergence_score = 0."""
    print("\n" + "="*70)
    print("DETAILED ISSUE 3: LOW DIVERGENCE SCORES")
    print("="*70)

    result = supabase.table("story_clusters").select("divergence_score, bias_diversity").execute()
    clusters = result.data or []

    at_0 = [c for c in clusters if c.get('divergence_score', 0) == 0]
    print(f"Clusters with divergence_score=0: {len(at_0)} ({100*len(at_0)/len(clusters):.1f}%)")

    # Check bias_diversity for these clusters
    lean_spreads = []
    framing_spreads = []

    for cluster in at_0[:100]:
        bd = cluster.get('bias_diversity', {})
        if isinstance(bd, str):
            bd = json.loads(bd)
        lean_spreads.append(bd.get('lean_spread', 0))
        framing_spreads.append(bd.get('framing_spread', 0))

    if lean_spreads:
        print(f"Average lean_spread for divergence=0 clusters: {mean(lean_spreads):.2f}")
    if framing_spreads:
        print(f"Average framing_spread for divergence=0 clusters: {mean(framing_spreads):.2f}")

    # High divergence for comparison
    high_div = [c for c in clusters if c.get('divergence_score', 0) > 50]
    print(f"\nClusters with divergence_score>50: {len(high_div)} ({100*len(high_div)/len(clusters):.1f}%)")

    if high_div:
        lean_spreads_high = []
        for cluster in high_div[:100]:
            bd = cluster.get('bias_diversity', {})
            if isinstance(bd, str):
                bd = json.loads(bd)
            lean_spreads_high.append(bd.get('lean_spread', 0))

        if lean_spreads_high:
            print(f"Average lean_spread for divergence>50 clusters: {mean(lean_spreads_high):.2f}")

def analyze_invalid_refs():
    """Investigate 614 invalid article_ids in cluster_articles."""
    print("\n" + "="*70)
    print("DETAILED ISSUE 4: INVALID CLUSTER_ARTICLES REFS (614)")
    print("="*70)

    result = supabase.table("cluster_articles").select("cluster_id, article_id").execute()
    cluster_articles = result.data or []

    result = supabase.table("articles").select("id").execute()
    valid_ids = set(a['id'] for a in (result.data or []))

    invalid = [ca for ca in cluster_articles if ca['article_id'] not in valid_ids]
    print(f"Total invalid refs: {len(invalid)}")

    # Sample invalid cluster_ids
    invalid_cluster_ids = set(ca['cluster_id'] for ca in invalid[:10])
    print(f"Sample invalid cluster IDs: {list(invalid_cluster_ids)[:3]}")

def main():
    print("\n▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪")
    print("DETAILED DATA QUALITY ANALYSIS")
    print("▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪▪")

    try:
        analyze_orphaned_articles()
    except Exception as e:
        print(f"ERROR: {e}")

    try:
        analyze_factual_rigor_outliers()
    except Exception as e:
        print(f"ERROR: {e}")

    try:
        analyze_low_divergence()
    except Exception as e:
        print(f"ERROR: {e}")

    try:
        analyze_invalid_refs()
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == '__main__':
    main()
