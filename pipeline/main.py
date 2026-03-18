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
    6. Run bias analysis on each article (5 axes)
    7. Cluster articles into stories
    8. Categorize and rank clusters
    9. Store clusters and linkages, finalize pipeline run
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
    insert_bias_scores,
    insert_cluster,
    link_article_to_cluster,
    update_pipeline_run,
)

# Phase 2: Bias analyzers
from analyzers.political_lean import analyze_political_lean
from analyzers.sensationalism import analyze_sensationalism
from analyzers.opinion_detector import analyze_opinion
from analyzers.factual_rigor import analyze_factual_rigor
from analyzers.framing import analyze_framing

# Phase 2: Clustering, categorization, ranking
from clustering.story_cluster import cluster_stories
from categorizer.auto_categorize import categorize_article
from ranker.importance_ranker import rank_importance


SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"


def load_sources() -> list[dict]:
    """Load the curated source list from data/sources.json."""
    if not SOURCES_PATH.exists():
        print(f"[error] Sources file not found: {SOURCES_PATH}")
        return []
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} sources from {SOURCES_PATH}")
    return sources


def run_bias_analysis(article: dict, source: dict) -> dict:
    """
    Run all 5 bias analyzers on a single article.

    Returns a dict with score keys ready for DB insertion.
    Each analyzer is run independently; failures fall back to defaults.
    """
    scores = {
        "political_lean": 50,
        "sensationalism": 10,
        "opinion_fact": 25,
        "factual_rigor": 50,
        "framing": 15,
    }

    try:
        scores["political_lean"] = analyze_political_lean(article, source)
    except Exception as e:
        print(f"    [warn] Political lean failed: {e}")

    try:
        scores["sensationalism"] = analyze_sensationalism(article)
    except Exception as e:
        print(f"    [warn] Sensationalism failed: {e}")

    try:
        scores["opinion_fact"] = analyze_opinion(article)
    except Exception as e:
        print(f"    [warn] Opinion detection failed: {e}")

    try:
        scores["factual_rigor"] = analyze_factual_rigor(article)
    except Exception as e:
        print(f"    [warn] Factual rigor failed: {e}")

    try:
        scores["framing"] = analyze_framing(article)
    except Exception as e:
        print(f"    [warn] Framing failed: {e}")

    return scores


def main():
    """Run the full news ingestion + analysis pipeline."""
    start_time = time.time()
    print("=" * 60)
    print(f"void --news pipeline starting at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/8] Loading sources...")
    sources = load_sources()
    if not sources:
        print("[abort] No sources loaded. Exiting.")
        return

    source_map = {s.get("id", ""): s for s in sources}

    # Step 2: Create pipeline run record
    print("\n[2/8] Creating pipeline run record...")
    pipeline_run = create_pipeline_run()
    run_id = pipeline_run["id"] if pipeline_run else None
    if run_id:
        print(f"  Pipeline run ID: {run_id}")
    else:
        print("  [warn] Could not create pipeline run record.")

    # Step 3: Fetch articles via RSS
    print("\n[3/8] Fetching RSS feeds...")
    articles_raw, fetch_errors = fetch_from_rss(sources)
    print(f"  Total raw articles: {len(articles_raw)}")
    print(f"  Fetch errors: {len(fetch_errors)}")

    # Step 4: Scrape full text and store articles
    print("\n[4/8] Scraping article text and storing in Supabase...")
    stored_articles = []

    for i, article_data in enumerate(articles_raw):
        url = article_data.get("url", "")
        if not url:
            continue
        if (i + 1) % 50 == 0 or i == 0:
            print(f"  Processing article {i + 1}/{len(articles_raw)}...")

        try:
            scraped = scrape_article(url)
            article_data["full_text"] = scraped.get("full_text", "")
            article_data["word_count"] = scraped.get("word_count", 0)
            article_data["image_url"] = scraped.get("image_url")
        except Exception as e:
            print(f"  [error] Scrape failed for {url}: {e}")

        result = insert_article(article_data)
        if result:
            article_data["id"] = result["id"]
            stored_articles.append(article_data)

    print(f"  Articles stored: {len(stored_articles)}/{len(articles_raw)}")

    # Step 5: Run bias analysis on each article
    print(f"\n[5/8] Running bias analysis on {len(stored_articles)} articles...")
    articles_analyzed = 0

    for i, article in enumerate(stored_articles):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Analyzing article {i + 1}/{len(stored_articles)}...")

        source_id = article.get("source_id", "")
        source = source_map.get(source_id, {"political_lean_baseline": "center"})

        bias_scores = run_bias_analysis(article, source)
        bias_scores["article_id"] = article.get("id", "")

        result = insert_bias_scores(bias_scores)
        if result:
            articles_analyzed += 1

    print(f"  Articles analyzed: {articles_analyzed}/{len(stored_articles)}")

    # Step 6: Cluster articles into stories
    print(f"\n[6/8] Clustering {len(stored_articles)} articles into stories...")
    clusters = []
    try:
        clusters = cluster_stories(stored_articles)
        print(f"  Clusters formed: {len(clusters)}")
    except Exception as e:
        print(f"  [error] Clustering failed: {e}")

    # Step 7: Categorize and rank each cluster
    print("\n[7/8] Categorizing and ranking clusters...")
    for cluster in clusters:
        cluster_articles_list = cluster.get("articles", [])

        # Categorize using the first article
        try:
            categories = categorize_article(cluster_articles_list[0]) if cluster_articles_list else ["politics"]
            cluster["categories"] = categories
            cluster["category"] = categories[0] if categories else "politics"
        except Exception as e:
            print(f"  [warn] Categorization failed: {e}")
            cluster["categories"] = ["politics"]
            cluster["category"] = "politics"

        # Rank importance
        try:
            importance = rank_importance(cluster_articles_list, sources)
            cluster["importance_score"] = importance
        except Exception as e:
            print(f"  [warn] Ranking failed: {e}")
            cluster["importance_score"] = 20.0

    clusters.sort(key=lambda c: c.get("importance_score", 0), reverse=True)

    # Step 8: Store clusters and linkages in Supabase
    print("\n[8/8] Storing clusters and finalizing...")
    clusters_created = 0
    for cluster in clusters:
        cluster_record = {
            "title": cluster.get("title", "Untitled Story")[:500],
            "category": cluster.get("category", "politics"),
            "section": cluster.get("section", "world"),
            "importance_score": round(cluster.get("importance_score", 0.0), 2),
            "source_count": cluster.get("source_count", 0),
            "first_published": cluster.get("first_published", ""),
        }

        result = insert_cluster(cluster_record)
        if result:
            cluster_id = result.get("id", "")
            clusters_created += 1
            for article_id in cluster.get("article_ids", []):
                if article_id:
                    link_article_to_cluster(cluster_id, article_id)

    print(f"  Clusters stored: {clusters_created}/{len(clusters)}")

    # Finalize
    duration = time.time() - start_time
    if run_id:
        update_pipeline_run(
            run_id=run_id,
            status="completed",
            articles_fetched=len(stored_articles),
            articles_analyzed=articles_analyzed,
            clusters_created=clusters_created,
            errors=fetch_errors[:50],
            duration_seconds=round(duration, 2),
        )

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Sources: {len(sources)} | Articles: {len(stored_articles)} "
          f"| Analyzed: {articles_analyzed} | Clusters: {clusters_created}")
    print(f"  Errors: {len(fetch_errors)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
