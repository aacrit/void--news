#!/usr/bin/env python3
"""
Scraper Health Check — Identify sources with highest full_text failure rates
Useful for debugging web scraper issues source-by-source.
"""

import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def main():
    # Fetch all articles with source metadata
    print("\nFetching article-source mapping...")
    articles = supabase.table("articles").select("id, source_id, url, full_text, title, published_at").order("published_at", desc=True).execute().data or []

    # Fetch sources
    sources = supabase.table("sources").select("id, name, slug, tier").execute().data or []
    sources_by_id = {s["id"]: s for s in sources}

    # Count by source
    source_stats = {}
    for article in articles:
        source_id = article.get("source_id")
        if not source_id:
            continue

        if source_id not in source_stats:
            source = sources_by_id.get(source_id, {})
            source_stats[source_id] = {
                "name": source.get("name", "Unknown"),
                "slug": source.get("slug", "unknown"),
                "tier": source.get("tier", "unknown"),
                "total": 0,
                "with_full_text": 0,
                "without_full_text": 0,
                "sample_urls": [],
            }

        source_stats[source_id]["total"] += 1

        full_text = (article.get("full_text") or "").strip()
        if full_text:
            source_stats[source_id]["with_full_text"] += 1
        else:
            source_stats[source_id]["without_full_text"] += 1
            # Collect sample failing URLs
            if len(source_stats[source_id]["sample_urls"]) < 2:
                source_stats[source_id]["sample_urls"].append(article.get("url", "no-url"))

    # Calculate percentages and sort by failure rate
    stats_with_pct = []
    for source_id, stats in source_stats.items():
        failure_rate = 100 * stats["without_full_text"] / stats["total"] if stats["total"] > 0 else 0
        stats["failure_rate"] = failure_rate
        stats["source_id"] = source_id
        stats_with_pct.append(stats)

    # Sort by failure rate (descending)
    stats_with_pct.sort(key=lambda x: x["failure_rate"], reverse=True)

    # Print results
    print("\n" + "="*100)
    print("SCRAPER HEALTH CHECK — Sources by Full_Text Capture Rate")
    print("="*100)
    print()

    print("TOP 20 SOURCES WITH HIGHEST FAILURE RATES:")
    print("-" * 100)
    print(f"{'#':<3} {'Source Name':<40} {'Tier':<15} {'Fail%':<8} {'With':<5} {'Without':<7} {'Total':<6}")
    print("-" * 100)

    for i, stats in enumerate(stats_with_pct[:20], 1):
        name = stats["name"][:39]  # Truncate long names
        tier = stats["tier"][:14]
        failure = f"{stats['failure_rate']:.1f}%"
        print(f"{i:<3} {name:<40} {tier:<15} {failure:<8} {stats['with_full_text']:<5} {stats['without_full_text']:<7} {stats['total']:<6}")

    print()
    print("="*100)
    print("TOP 20 SOURCES WITH BEST CAPTURE RATES:")
    print("="*100)
    print()

    print(f"{'#':<3} {'Source Name':<40} {'Tier':<15} {'Success%':<10} {'With':<5} {'Total':<6}")
    print("-" * 100)

    for i, stats in enumerate(reversed(stats_with_pct[-20:]), 1):
        name = stats["name"][:39]
        tier = stats["tier"][:14]
        success = f"{100 - stats['failure_rate']:.1f}%"
        print(f"{i:<3} {name:<40} {tier:<15} {success:<10} {stats['with_full_text']:<5} {stats['total']:<6}")

    # Summary
    print()
    print("="*100)
    print("SUMMARY STATISTICS")
    print("="*100)

    total_articles = sum(s["total"] for s in stats_with_pct)
    total_with_text = sum(s["with_full_text"] for s in stats_with_pct)
    total_without_text = sum(s["without_full_text"] for s in stats_with_pct)
    overall_success = 100 * total_with_text / total_articles if total_articles > 0 else 0

    print(f"\nOverall success rate: {overall_success:.1f}% ({total_with_text}/{total_articles})")
    print(f"Overall failure rate: {100 - overall_success:.1f}% ({total_without_text}/{total_articles})")
    print(f"Sources tracked: {len(stats_with_pct)}")

    # Tier-based breakdown
    print("\nBy Tier:")
    for tier in ["us_major", "international", "independent"]:
        tier_stats = [s for s in stats_with_pct if s["tier"] == tier]
        if tier_stats:
            tier_total = sum(s["total"] for s in tier_stats)
            tier_with = sum(s["with_full_text"] for s in tier_stats)
            tier_rate = 100 * tier_with / tier_total if tier_total > 0 else 0
            print(f"  {tier:<20}: {tier_rate:.1f}% success ({tier_with}/{tier_total} articles)")

    # Identify critical sources (>50% failure)
    print("\n" + "="*100)
    print("CRITICAL SOURCES (>50% Failure Rate) — Need Investigation")
    print("="*100)

    critical = [s for s in stats_with_pct if s["failure_rate"] > 50]
    if critical:
        print(f"\nFound {len(critical)} sources with >50% failure rate:\n")
        for stats in critical[:10]:
            print(f"  {stats['name']:<45} ({stats['tier']})")
            print(f"    Failure rate: {stats['failure_rate']:.1f}%")
            print(f"    Total articles: {stats['total']}")
            if stats["sample_urls"]:
                print(f"    Sample failing URL: {stats['sample_urls'][0]}")
            print()
    else:
        print("\nNo sources with >50% failure rate — scraper is generally healthy.")

    print()
    print("RECOMMENDATIONS:")
    print("-" * 100)
    print("1. For critical sources (>50% failure):")
    print("   - Test the sample URLs manually to see what HTML structure is returned")
    print("   - Update CSS selectors in pipeline/fetchers/web_scraper.py for that source")
    print("   - Check if the source uses JavaScript rendering (requires headless browser)")
    print("   - Verify robots.txt doesn't block the scraper")
    print()
    print("2. For moderate sources (20-50% failure):")
    print("   - Investigate intermittent issues (rate limiting, timeout)")
    print("   - Add retry logic with exponential backoff")
    print("   - Consider domain-specific scraper handlers")
    print()
    print("3. General improvements:")
    print("   - Use scrapy-splash or playwright for JavaScript-heavy sites")
    print("   - Implement proxy rotation to avoid blocking")
    print("   - Add logging for each failed scrape (URL, error type, HTML size)")
    print()

if __name__ == "__main__":
    main()
