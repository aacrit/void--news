#!/usr/bin/env python3
"""
Database Quality Audit - void --news Supabase instance
Audits bias scores, articles, clusters, and data quality across 8 domains.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
from statistics import mean, stdev

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def histogram(values: list, buckets: int = 10, min_val: int = 0, max_val: int = 100) -> dict:
    """Create a histogram of values."""
    bucket_size = (max_val - min_val) / buckets
    hist = defaultdict(int)
    for v in values:
        if v is None:
            hist["NULL"] += 1
        else:
            bucket = int((v - min_val) / bucket_size)
            bucket = min(bucket, buckets - 1)
            range_label = f"{int(min_val + bucket * bucket_size)}-{int(min_val + (bucket + 1) * bucket_size)}"
            hist[range_label] += 1
    return dict(hist)

def audit_1_source_coverage():
    """Domain 1: Source Coverage - verify all 90 sources exist with valid config."""
    print("\n" + "="*70)
    print("DOMAIN 1: SOURCE COVERAGE")
    print("="*70)

    # Load sources.json
    with open('/home/aacrit/projects/void-news/data/sources.json', 'r') as f:
        sources_config = json.load(f)

    expected_count = len(sources_config)
    print(f"Expected sources: {expected_count}")

    # Get all sources from DB
    result = supabase.table("sources").select("*").execute()
    db_sources = result.data or []

    print(f"Sources in DB: {len(db_sources)}")

    # Verify tier distribution
    tier_counts = defaultdict(int)
    for src in db_sources:
        tier_counts[src['tier']] += 1

    print(f"Tier distribution:")
    for tier, count in sorted(tier_counts.items()):
        print(f"  {tier}: {count}")

    # Check for missing rss_url
    missing_rss = sum(1 for src in db_sources if not src.get('rss_url'))
    print(f"Sources without rss_url: {missing_rss}")

    # Check for missing political_lean_baseline
    missing_lean = sum(1 for src in db_sources if not src.get('political_lean_baseline'))
    print(f"Sources without political_lean_baseline: {missing_lean}")

    # Count active sources
    active_sources = sum(1 for src in db_sources if src.get('is_active', False))
    print(f"Active sources: {active_sources}")

    return {
        "expected": expected_count,
        "actual": len(db_sources),
        "tier_distribution": dict(tier_counts),
        "missing_rss_url": missing_rss,
        "missing_lean": missing_lean,
        "active": active_sources,
    }

def audit_2_article_quality():
    """Domain 2: Article Quality - check NULL rates, word count distribution, duplicates."""
    print("\n" + "="*70)
    print("DOMAIN 2: ARTICLE QUALITY")
    print("="*70)

    # Get all articles
    result = supabase.table("articles").select("*").execute()
    articles = result.data or []

    total_articles = len(articles)
    print(f"Total articles: {total_articles}")

    # NULL text count
    null_full_text = sum(1 for a in articles if not a.get('full_text'))
    null_published_at = sum(1 for a in articles if not a.get('published_at'))
    null_summary = sum(1 for a in articles if not a.get('summary'))

    print(f"NULL full_text: {null_full_text} ({100*null_full_text/total_articles:.1f}%)")
    print(f"NULL published_at: {null_published_at} ({100*null_published_at/total_articles:.1f}%)")
    print(f"NULL summary: {null_summary} ({100*null_summary/total_articles:.1f}%)")

    # Word count distribution
    word_counts = [a.get('word_count', 0) for a in articles if a.get('word_count')]
    suspicious_low = 0
    if word_counts:
        suspicious_low = sum(1 for wc in word_counts if wc < 100)
        print(f"Articles with word_count < 100: {suspicious_low} ({100*suspicious_low/len(word_counts):.1f}%)")
        print(f"Word count range: {min(word_counts)} - {max(word_counts)}")
        print(f"Word count mean: {mean(word_counts):.0f}")
        if len(word_counts) > 1:
            print(f"Word count stdev: {stdev(word_counts):.0f}")

    # Section distribution
    sections = defaultdict(int)
    for a in articles:
        sections[a.get('section', 'other')] += 1

    print(f"Section distribution:")
    for section, count in sorted(sections.items()):
        print(f"  {section}: {count} ({100*count/total_articles:.1f}%)")

    # Check for duplicate URLs
    urls = [a['url'] for a in articles]
    unique_urls = len(set(urls))
    duplicates = total_articles - unique_urls
    print(f"Duplicate URLs: {duplicates}")

    return {
        "total": total_articles,
        "null_full_text": null_full_text,
        "null_published_at": null_published_at,
        "null_summary": null_summary,
        "suspicious_low_wc": suspicious_low,
        "sections": dict(sections),
        "duplicate_urls": duplicates,
    }

def audit_3_bias_score_quality():
    """Domain 3: Bias Score Quality - distributions, defaults, confidence, outliers."""
    print("\n" + "="*70)
    print("DOMAIN 3: BIAS SCORE QUALITY")
    print("="*70)

    result = supabase.table("bias_scores").select("*").execute()
    bias_scores = result.data or []
    total_scores = len(bias_scores)

    print(f"Total bias scores: {total_scores}")

    # Get articles for coverage calc
    result_articles = supabase.table("articles").select("id").execute()
    articles = result_articles.data or []
    total_articles = len(articles)

    coverage = 100 * total_scores / total_articles if total_articles else 0
    print(f"Coverage: {coverage:.1f}% ({total_scores}/{total_articles} articles)")

    # Check for default score pattern (50/10/25/50/15 or similar)
    default_pattern = sum(1 for bs in bias_scores
                         if (bs.get('political_lean') == 50 and
                             bs.get('sensationalism') == 10 and
                             bs.get('opinion_fact') == 25 and
                             bs.get('factual_rigor') == 50))

    print(f"Scores matching default pattern (50/10/25/50): {default_pattern} ({100*default_pattern/total_scores:.1f}%)")

    # Distribution analysis per axis
    axes = {
        'political_lean': [bs.get('political_lean') for bs in bias_scores if bs.get('political_lean') is not None],
        'sensationalism': [bs.get('sensationalism') for bs in bias_scores if bs.get('sensationalism') is not None],
        'opinion_fact': [bs.get('opinion_fact') for bs in bias_scores if bs.get('opinion_fact') is not None],
        'factual_rigor': [bs.get('factual_rigor') for bs in bias_scores if bs.get('factual_rigor') is not None],
        'framing': [bs.get('framing') for bs in bias_scores if bs.get('framing') is not None],
    }

    for axis_name, axis_values in axes.items():
        if not axis_values:
            print(f"{axis_name}: NO DATA")
            continue

        print(f"\n{axis_name}:")
        print(f"  Mean: {mean(axis_values):.1f}")
        if len(axis_values) > 1:
            print(f"  Stdev: {stdev(axis_values):.1f}")
        print(f"  Range: {min(axis_values)} - {max(axis_values)}")
        print(f"  Histogram: {histogram(axis_values, buckets=5)}")

        # Check for outliers
        at_0 = sum(1 for v in axis_values if v == 0)
        at_100 = sum(1 for v in axis_values if v == 100)
        if at_0 + at_100 > 0:
            print(f"  Outliers: {at_0} at 0, {at_100} at 100")

    # Confidence distribution
    confidences = [bs.get('confidence', 0) for bs in bias_scores if bs.get('confidence') is not None]
    if confidences:
        low_conf = sum(1 for c in confidences if c < 0.3)
        print(f"\nConfidence:")
        print(f"  Mean: {mean(confidences):.3f}")
        if len(confidences) > 1:
            print(f"  Stdev: {stdev(confidences):.3f}")
        print(f"  Range: {min(confidences):.3f} - {max(confidences):.3f}")
        print(f"  Low confidence (<0.3): {low_conf} ({100*low_conf/len(confidences):.1f}%)")

    # Rationale column check
    rationale_filled = sum(1 for bs in bias_scores if bs.get('rationale'))
    print(f"\nRationale JSONB populated: {rationale_filled}/{total_scores} ({100*rationale_filled/total_scores:.1f}%)")

    return {
        "total": total_scores,
        "coverage": coverage,
        "default_pattern": default_pattern,
        "axes_stats": {
            axis_name: {
                "mean": mean(vals) if vals else None,
                "stdev": stdev(vals) if len(vals) > 1 else None,
                "min": min(vals) if vals else None,
                "max": max(vals) if vals else None,
                "count": len(vals),
            }
            for axis_name, vals in axes.items()
        },
        "confidence_mean": mean(confidences) if confidences else None,
        "rationale_populated": rationale_filled,
    }

def audit_4_cluster_quality():
    """Domain 4: Cluster Quality - size distribution, orphans, divergence, summaries."""
    print("\n" + "="*70)
    print("DOMAIN 4: CLUSTER QUALITY")
    print("="*70)

    result = supabase.table("story_clusters").select("*").execute()
    clusters = result.data or []
    total_clusters = len(clusters)

    print(f"Total clusters: {total_clusters}")

    # Get cluster_articles to count articles per cluster
    result_ca = supabase.table("cluster_articles").select("cluster_id, article_id").execute()
    cluster_articles = result_ca.data or []

    articles_per_cluster = defaultdict(int)
    for ca in cluster_articles:
        articles_per_cluster[ca['cluster_id']] += 1

    cluster_sizes = list(articles_per_cluster.values())
    single_article_clusters = 0
    if cluster_sizes:
        avg_size = mean(cluster_sizes)
        single_article_clusters = sum(1 for size in cluster_sizes if size == 1)

        print(f"Average articles per cluster: {avg_size:.1f}")
        print(f"Single-article clusters: {single_article_clusters} ({100*single_article_clusters/len(cluster_sizes):.1f}%)")
        print(f"Cluster size range: {min(cluster_sizes)} - {max(cluster_sizes)}")
        print(f"Cluster size histogram: {histogram(cluster_sizes, buckets=6)}")

    # Check for orphaned clusters (0 articles)
    orphaned = sum(1 for c in clusters if articles_per_cluster.get(c['id'], 0) == 0)
    print(f"Orphaned clusters (0 articles): {orphaned}")

    # Check for missing summaries
    missing_summary = sum(1 for c in clusters if not c.get('summary'))
    print(f"Clusters without summary: {missing_summary}")

    # Check for "Untitled Story" titles
    untitled = sum(1 for c in clusters if c.get('title', '').strip() == 'Untitled Story')
    print(f"Clusters with 'Untitled Story' title: {untitled}")

    # Divergence score distribution
    divergence_scores = [c.get('divergence_score', 0) for c in clusters if c.get('divergence_score') is not None]
    if divergence_scores:
        print(f"\nDivergence score:")
        print(f"  Mean: {mean(divergence_scores):.1f}")
        if len(divergence_scores) > 1:
            print(f"  Stdev: {stdev(divergence_scores):.1f}")
        print(f"  Range: {min(divergence_scores):.1f} - {max(divergence_scores):.1f}")

    # Headline rank distribution
    headline_ranks = [c.get('headline_rank', 0) for c in clusters if c.get('headline_rank') is not None]
    if headline_ranks:
        print(f"\nHeadline rank:")
        print(f"  Mean: {mean(headline_ranks):.1f}")
        if len(headline_ranks) > 1:
            print(f"  Stdev: {stdev(headline_ranks):.1f}")
        print(f"  Range: {min(headline_ranks):.1f} - {max(headline_ranks):.1f}")

    # Bias diversity populated
    bias_diversity_filled = sum(1 for c in clusters if c.get('bias_diversity'))
    print(f"\nbias_diversity JSONB populated: {bias_diversity_filled}/{total_clusters} ({100*bias_diversity_filled/total_clusters:.1f}%)")

    return {
        "total": total_clusters,
        "avg_articles_per_cluster": mean(cluster_sizes) if cluster_sizes else 0,
        "single_article_clusters": single_article_clusters,
        "orphaned": orphaned,
        "missing_summary": missing_summary,
        "untitled": untitled,
        "bias_diversity_filled": bias_diversity_filled,
    }

def audit_5_enrichment_quality():
    """Domain 5: Enrichment Quality - bias_diversity, divergence, headline_rank, coverage_velocity."""
    print("\n" + "="*70)
    print("DOMAIN 5: ENRICHMENT QUALITY")
    print("="*70)

    result = supabase.table("story_clusters").select("*").execute()
    clusters = result.data or []

    # bias_diversity
    bd_filled = sum(1 for c in clusters if c.get('bias_diversity') and len(c['bias_diversity']) > 0)
    print(f"bias_diversity populated: {bd_filled}/{len(clusters)} ({100*bd_filled/len(clusters):.1f}%)")

    # divergence_score
    div_filled = sum(1 for c in clusters if c.get('divergence_score') and c['divergence_score'] != 0)
    div_zero = sum(1 for c in clusters if c.get('divergence_score') == 0 or not c.get('divergence_score'))
    print(f"divergence_score non-zero: {div_filled}/{len(clusters)} ({100*div_filled/len(clusters):.1f}%)")
    print(f"divergence_score zero/null: {div_zero}/{len(clusters)} ({100*div_zero/len(clusters):.1f}%)")

    # headline_rank variance
    headline_ranks = [c.get('headline_rank', 0) for c in clusters if c.get('headline_rank') is not None]
    hr_stdev = 0
    if headline_ranks:
        unique_ranks = len(set(headline_ranks))
        print(f"headline_rank unique values: {unique_ranks}/{len(headline_ranks)}")
        if len(headline_ranks) > 1:
            hr_stdev = stdev(headline_ranks)
            print(f"headline_rank variance: {hr_stdev:.2f}")

    # coverage_velocity
    cv_filled = sum(1 for c in clusters if c.get('coverage_velocity'))
    print(f"coverage_velocity populated: {cv_filled}/{len(clusters)} ({100*cv_filled/len(clusters):.1f}%)")

    return {
        "bias_diversity_filled": bd_filled,
        "divergence_nonzero": div_filled,
        "headline_rank_variance": hr_stdev,
        "coverage_velocity_filled": cv_filled,
    }

def audit_6_temporal_freshness():
    """Domain 6: Temporal Freshness - article dates, pipeline runs, age distribution."""
    print("\n" + "="*70)
    print("DOMAIN 6: TEMPORAL FRESHNESS")
    print("="*70)

    result = supabase.table("articles").select("published_at").execute()
    articles = result.data or []

    published_dates = [a['published_at'] for a in articles if a.get('published_at')]

    if published_dates:
        recent = max(published_dates)
        oldest = min(published_dates)
        print(f"Most recent article: {recent}")
        print(f"Oldest article: {oldest}")

        # Age distribution
        now = datetime.now(datetime.fromisoformat(recent).tzinfo) if recent else datetime.now()
        ages = []
        for date_str in published_dates:
            if date_str:
                date = datetime.fromisoformat(date_str)
                age_days = (now - date).days
                ages.append(age_days)

        if ages:
            over_7_days = sum(1 for age in ages if age > 7)
            print(f"Articles > 7 days old: {over_7_days}/{len(ages)} ({100*over_7_days/len(ages):.1f}%)")

    # Pipeline runs
    result_runs = supabase.table("pipeline_runs").select("completed_at, status").execute()
    runs = result_runs.data or []
    completed_runs = [r for r in runs if r.get('status') == 'completed']

    print(f"\nTotal pipeline runs: {len(runs)}")
    print(f"Completed runs: {len(completed_runs)}")

    if completed_runs:
        last_run = completed_runs[0].get('completed_at') if completed_runs else None
        if last_run:
            print(f"Last pipeline run: {last_run}")

    return {
        "articles_count": len(articles),
        "articles_with_date": len(published_dates),
        "pipeline_runs": len(runs),
        "completed_runs": len(completed_runs),
    }

def audit_7_referential_integrity():
    """Domain 7: Referential Integrity - orphaned articles/clusters, dangling refs."""
    print("\n" + "="*70)
    print("DOMAIN 7: REFERENTIAL INTEGRITY")
    print("="*70)

    # Get all articles and clusters
    result_articles = supabase.table("articles").select("id").execute()
    articles = result_articles.data or []
    article_ids = set(a['id'] for a in articles)

    result_clusters = supabase.table("story_clusters").select("id").execute()
    clusters = result_clusters.data or []
    cluster_ids = set(c['id'] for c in clusters)

    # Get all cluster_articles refs
    result_ca = supabase.table("cluster_articles").select("cluster_id, article_id").execute()
    cluster_articles = result_ca.data or []

    # Check for orphaned articles (not in any cluster)
    clustered_articles = set(ca['article_id'] for ca in cluster_articles)
    orphaned_articles = article_ids - clustered_articles

    print(f"Total articles: {len(articles)}")
    print(f"Articles in clusters: {len(clustered_articles)}")
    print(f"Orphaned articles (not in any cluster): {len(orphaned_articles)}")

    # Check for invalid cluster_articles refs
    invalid_cluster_refs = sum(1 for ca in cluster_articles if ca['cluster_id'] not in cluster_ids)
    invalid_article_refs = sum(1 for ca in cluster_articles if ca['article_id'] not in article_ids)

    print(f"Invalid cluster_articles refs (bad cluster_id): {invalid_cluster_refs}")
    print(f"Invalid cluster_articles refs (bad article_id): {invalid_article_refs}")

    # Check for orphaned bias_scores
    result_bias = supabase.table("bias_scores").select("article_id").execute()
    bias_scores = result_bias.data or []
    bias_article_ids = set(bs['article_id'] for bs in bias_scores)

    invalid_bias_refs = len(bias_article_ids - article_ids)
    print(f"Invalid bias_scores refs (article doesn't exist): {invalid_bias_refs}")

    return {
        "total_articles": len(articles),
        "orphaned_articles": len(orphaned_articles),
        "invalid_cluster_refs": invalid_cluster_refs,
        "invalid_article_refs": invalid_article_refs,
        "invalid_bias_refs": invalid_bias_refs,
    }

def audit_8_cross_field_consistency():
    """Domain 8: Cross-Field Consistency - lean baselines vs articles, tier patterns."""
    print("\n" + "="*70)
    print("DOMAIN 8: CROSS-FIELD CONSISTENCY")
    print("="*70)

    # Load sources
    result = supabase.table("sources").select("*").execute()
    sources = result.data or []
    source_map = {s['id']: s for s in sources}

    # Get articles with bias scores
    result_articles = supabase.table("articles").select("source_id").execute()
    articles = result_articles.data or []

    result_bias = supabase.table("bias_scores").select("article_id, political_lean, factual_rigor, opinion_fact").execute()
    bias_scores = result_bias.data or []

    # Get article->source mapping
    result_articles_full = supabase.table("articles").select("id, source_id").execute()
    article_source_map = {a['id']: a['source_id'] for a in (result_articles_full.data or [])}

    # Analyze per-source patterns
    source_leans = defaultdict(list)
    source_rigor = defaultdict(list)
    source_opinion = defaultdict(list)

    for bs in bias_scores:
        article_id = bs['article_id']
        source_id = article_source_map.get(article_id)
        if source_id and source_id in source_map:
            source_leans[source_id].append(bs.get('political_lean'))
            source_rigor[source_id].append(bs.get('factual_rigor'))
            source_opinion[source_id].append(bs.get('opinion_fact'))

    # Check center sources (should have avg lean 40-60)
    center_sources = [s for s in sources if s.get('political_lean_baseline') == 'center']
    center_consistency = 0
    for src in center_sources:
        if src['id'] in source_leans:
            leans = source_leans[src['id']]
            avg_lean = mean(leans)
            if 40 <= avg_lean <= 60:
                center_consistency += 1

    if center_sources:
        print(f"Center-baseline sources with avg lean 40-60: {center_consistency}/{len(center_sources)}")

    # Per-tier averages
    tier_leans = defaultdict(list)
    tier_rigor = defaultdict(list)

    for src in sources:
        if src['id'] in source_leans:
            tier_leans[src['tier']].extend(source_leans[src['id']])
            tier_rigor[src['tier']].extend(source_rigor[src['id']])

    print(f"\nPer-tier average political lean:")
    for tier in ['us_major', 'international', 'independent']:
        if tier_leans[tier]:
            print(f"  {tier}: {mean(tier_leans[tier]):.1f}")

    print(f"\nPer-tier average factual rigor:")
    for tier in ['us_major', 'international', 'independent']:
        if tier_rigor[tier]:
            print(f"  {tier}: {mean(tier_rigor[tier]):.1f}")

    # Check a few key outlets
    key_outlets = ['ap-news', 'reuters', 'nyt', 'washington-post', 'fox-news', 'breitbart']
    print(f"\nKey outlet patterns:")
    for outlet_slug in key_outlets:
        outlet = next((s for s in sources if s.get('slug') == outlet_slug), None)
        if outlet and outlet['id'] in source_leans:
            leans = [l for l in source_leans[outlet['id']] if l is not None]
            rigor = [r for r in source_rigor[outlet['id']] if r is not None]
            if leans:
                print(f"  {outlet_slug}: lean={mean(leans):.1f}, rigor={mean(rigor):.1f}, articles={len(leans)}")

    return {
        "center_sources_consistent": center_consistency,
        "tier_patterns": {
            tier: {
                "avg_lean": mean(tier_leans[tier]) if tier_leans[tier] else None,
                "avg_rigor": mean(tier_rigor[tier]) if tier_rigor[tier] else None,
            }
            for tier in ['us_major', 'international', 'independent']
        }
    }

def main():
    print("\n")
    print("▪" * 70)
    print("DATA QUALITY AUDIT — void --news")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("▪" * 70)

    results = {}

    try:
        results['1_source_coverage'] = audit_1_source_coverage()
    except Exception as e:
        print(f"ERROR in Domain 1: {e}")

    try:
        results['2_article_quality'] = audit_2_article_quality()
    except Exception as e:
        print(f"ERROR in Domain 2: {e}")

    try:
        results['3_bias_score_quality'] = audit_3_bias_score_quality()
    except Exception as e:
        print(f"ERROR in Domain 3: {e}")

    try:
        results['4_cluster_quality'] = audit_4_cluster_quality()
    except Exception as e:
        print(f"ERROR in Domain 4: {e}")

    try:
        results['5_enrichment_quality'] = audit_5_enrichment_quality()
    except Exception as e:
        print(f"ERROR in Domain 5: {e}")

    try:
        results['6_temporal_freshness'] = audit_6_temporal_freshness()
    except Exception as e:
        print(f"ERROR in Domain 6: {e}")

    try:
        results['7_referential_integrity'] = audit_7_referential_integrity()
    except Exception as e:
        print(f"ERROR in Domain 7: {e}")

    try:
        results['8_cross_field_consistency'] = audit_8_cross_field_consistency()
    except Exception as e:
        print(f"ERROR in Domain 8: {e}")

    # Summary
    print("\n" + "="*70)
    print("AUDIT SUMMARY")
    print("="*70)
    print(json.dumps(results, indent=2, default=str))

    return results

if __name__ == '__main__':
    main()
