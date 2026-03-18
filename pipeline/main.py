"""
void --news pipeline orchestrator.

Main entry point for the news ingestion pipeline. Runs as a GitHub Actions
cron job (2x daily) or manually.

Steps:
    1. Load sources from data/sources.json
    2. Create a pipeline run record in Supabase
    3. Fetch articles via RSS feeds (parallel)
    4. Scrape full article text for each fetched article
    5. Store articles in Supabase
    6. Log pipeline run results
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Add pipeline root to path so imports work when run directly
sys.path.insert(0, str(Path(__file__).parent))

from fetchers.rss_fetcher import fetch_from_rss
from fetchers.web_scraper import scrape_article
from utils.supabase_client import (
    create_pipeline_run,
    insert_article,
    update_pipeline_run,
)


# Path to sources.json relative to this file
SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"


def load_sources() -> list[dict]:
    """
    Load the curated source list from data/sources.json.

    Returns:
        List of source dicts with keys like id, name, rss_url, tier, etc.
    """
    if not SOURCES_PATH.exists():
        print(f"[error] Sources file not found: {SOURCES_PATH}")
        print("[info] Create data/sources.json with your curated source list.")
        return []

    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)

    print(f"Loaded {len(sources)} sources from {SOURCES_PATH}")
    return sources


def main():
    """
    Run the full news ingestion pipeline.

    1. Load sources from JSON
    2. Create pipeline run record
    3. Fetch RSS feeds in parallel
    4. Scrape full text for each article
    5. Store articles in Supabase
    6. Update pipeline run with results
    """
    start_time = time.time()
    print("=" * 60)
    print(f"void --news pipeline starting at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/5] Loading sources...")
    sources = load_sources()
    if not sources:
        print("[abort] No sources loaded. Exiting.")
        return

    # Step 2: Create pipeline run record
    print("\n[2/5] Creating pipeline run record...")
    pipeline_run = create_pipeline_run()
    run_id = pipeline_run["id"] if pipeline_run else None
    if run_id:
        print(f"  Pipeline run ID: {run_id}")
    else:
        print("  [warn] Could not create pipeline run record. Continuing without tracking.")

    # Step 3: Fetch articles via RSS
    print("\n[3/5] Fetching RSS feeds...")
    articles_raw, fetch_errors = fetch_from_rss(sources)
    print(f"  Total raw articles: {len(articles_raw)}")
    print(f"  Fetch errors: {len(fetch_errors)}")

    # Step 4: Scrape full text and store articles
    print("\n[4/5] Scraping article text and storing in Supabase...")
    articles_stored = 0
    store_errors = []

    for i, article_data in enumerate(articles_raw):
        url = article_data.get("url", "")
        if not url:
            continue

        # Progress logging every 50 articles
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing article {i + 1}/{len(articles_raw)}...")

        # Scrape full article text
        try:
            scraped = scrape_article(url)
            article_data["full_text"] = scraped.get("full_text", "")
            article_data["word_count"] = scraped.get("word_count", 0)
            article_data["image_url"] = scraped.get("image_url")
        except Exception as e:
            print(f"  [error] Scrape failed for {url}: {e}")
            # Continue with partial data (title + summary from RSS)

        # Store in Supabase
        result = insert_article(article_data)
        if result:
            articles_stored += 1

    print(f"  Articles stored: {articles_stored}/{len(articles_raw)}")

    # Step 5: Update pipeline run
    all_errors = fetch_errors + store_errors
    duration = time.time() - start_time

    print(f"\n[5/5] Finalizing pipeline run...")
    if run_id:
        update_pipeline_run(
            run_id=run_id,
            status="completed",
            articles_fetched=articles_stored,
            articles_analyzed=0,  # Phase 2: bias analysis
            clusters_created=0,   # Phase 2: clustering
            errors=all_errors,
            duration_seconds=round(duration, 2),
        )

    # Summary
    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Sources processed: {len(sources)}")
    print(f"  Articles fetched: {len(articles_raw)}")
    print(f"  Articles stored: {articles_stored}")
    print(f"  Errors: {len(all_errors)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
