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
    6. Run bias analysis on each article (6 axes)
    7. Cluster stories and rank by importance
    8. Log pipeline run results
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
    supabase,
)

# Import analyzers
from analyzers.political_lean import analyze_political_lean
from analyzers.sensationalism import analyze_sensationalism
from analyzers.opinion_detector import analyze_opinion
from analyzers.factual_rigor import analyze_factual_rigor
from analyzers.framing import analyze_framing

# Import clustering, categorization, ranking
from clustering.story_cluster import cluster_stories
from categorizer.auto_categorize import categorize_article
from ranker.importance_ranker import rank_importance


SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"

LEAN_MAP = {
    "left": 15,
    "center-left": 35,
    "center": 50,
    "center-right": 65,
    "right": 85,
    "varies": 50,
}


def load_sources() -> list[dict]:
    """Load the curated source list from data/sources.json."""
    if not SOURCES_PATH.exists():
        print(f"[error] Sources file not found: {SOURCES_PATH}")
        return []
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)
    print(f"Loaded {len(sources)} sources from {SOURCES_PATH}")
    return sources


def analyze_article(article_id: str, title: str, text: str, source_baseline: int = 50) -> dict | None:
    """Run all 5 bias analyzers on a single article."""
    if not text and not title:
        return None
    content = text or title
    try:
        scores = {
            "article_id": article_id,
            "political_lean": max(0, min(100, int(analyze_political_lean(content, title=title, source_baseline=source_baseline)))),
            "sensationalism": max(0, min(100, int(analyze_sensationalism(content, title=title)))),
            "opinion_fact": max(0, min(100, int(analyze_opinion(content, title=title)))),
            "factual_rigor": max(0, min(100, int(analyze_factual_rigor(content, title=title)))),
            "framing": max(0, min(100, int(analyze_framing(content, title=title)))),
            "confidence": 0.7,
        }
        return scores
    except Exception as e:
        print(f"  [error] Bias analysis failed for article {article_id}: {e}")
        return None


def run_clustering_and_ranking(stored_articles: list[dict], sources: list[dict]) -> int:
    """Cluster stored articles into stories, categorize, and rank by importance."""
    if len(stored_articles) < 2:
        print("  Not enough articles to cluster.")
        return 0

    texts = []
    for a in stored_articles:
        text = a.get("title", "")
        full_text = a.get("full_text", "") or a.get("summary", "")
        if full_text:
            text += " " + " ".join(full_text.split()[:200])
        texts.append(text)

    print("  Running story clustering...")
    try:
        cluster_labels = cluster_stories(texts)
    except Exception as e:
        print(f"  [error] Clustering failed: {e}")
        return 0

    clusters_map = {}
    for idx, label in enumerate(cluster_labels):
        if label == -1:
            continue
        clusters_map.setdefault(label, []).append(stored_articles[idx])

    print(f"  Found {len(clusters_map)} story clusters from {len(stored_articles)} articles")

    source_lookup = {s.get("id", s.get("slug", "")): s for s in sources}
    clusters_created = 0

    for label, articles in clusters_map.items():
        if len(articles) < 1:
            continue

        cluster_title = articles[0].get("title", "Untitled Story")
        combined_text = " ".join(a.get("title", "") + " " + (a.get("summary", "") or "") for a in articles)
        category = categorize_article(combined_text)

        sections = [a.get("section", "world") for a in articles]
        section = max(set(sections), key=sections.count) if sections else "world"

        unique_sources = set(a.get("source_id", "") for a in articles)
        source_count = len(unique_sources)

        try:
            cluster_sources = [source_lookup.get(sid, {}) for sid in unique_sources]
            importance = rank_importance(articles, cluster_sources)
        except Exception as e:
            print(f"  [warn] Importance ranking failed: {e}")
            importance = source_count * 10

        timestamps = [a.get("published_at") for a in articles if a.get("published_at")]
        first_published = min(timestamps) if timestamps else datetime.now(timezone.utc).isoformat()

        cluster_row = insert_cluster({
            "title": cluster_title[:500],
            "summary": articles[0].get("summary", "")[:1000],
            "category": category,
            "section": section,
            "importance_score": round(importance, 2),
            "source_count": source_count,
            "first_published": first_published,
        })

        if cluster_row:
            clusters_created += 1
            cluster_id = cluster_row["id"]
            for article in articles:
                link_article_to_cluster(cluster_id, article["id"])
            try:
                cat_result = supabase.table("categories").select("id").eq("slug", category.lower()).limit(1).execute()
                if cat_result.data:
                    cat_id = cat_result.data[0]["id"]
                    for article in articles:
                        try:
                            supabase.table("article_categories").insert({
                                "article_id": article["id"],
                                "category_id": cat_id,
                            }).execute()
                        except Exception:
                            pass
            except Exception:
                pass

    return clusters_created


def main():
    """Run the full news ingestion + analysis pipeline."""
    start_time = time.time()
    print("=" * 60)
    print(f"void --news pipeline starting at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/7] Loading sources...")
    sources = load_sources()
    if not sources:
        print("[abort] No sources loaded. Exiting.")
        return

    source_slug_map = {s.get("id", s.get("slug", "")): s for s in sources}

    # Step 2: Create pipeline run record
    print("\n[2/7] Creating pipeline run record...")
    pipeline_run = create_pipeline_run()
    run_id = pipeline_run["id"] if pipeline_run else None
    if run_id:
        print(f"  Pipeline run ID: {run_id}")
    else:
        print("  [warn] Could not create pipeline run record.")

    # Step 3: Fetch articles via RSS
    print("\n[3/7] Fetching RSS feeds...")
    articles_raw, fetch_errors = fetch_from_rss(sources)
    print(f"  Total raw articles: {len(articles_raw)}")
    print(f"  Fetch errors: {len(fetch_errors)}")

    # Step 4: Scrape full text and store articles
    print("\n[4/7] Scraping article text and storing in Supabase...")
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

    # Step 5: Run bias analysis
    print(f"\n[5/7] Running bias analysis on {len(stored_articles)} articles...")
    articles_analyzed = 0

    for i, article in enumerate(stored_articles):
        if (i + 1) % 25 == 0 or i == 0:
            print(f"  Analyzing article {i + 1}/{len(stored_articles)}...")

        source = source_slug_map.get(article.get("source_id", ""), {})
        baseline_lean = LEAN_MAP.get(source.get("political_lean_baseline", "center"), 50)

        text = article.get("full_text", "") or article.get("summary", "") or ""
        title = article.get("title", "")
        scores = analyze_article(article["id"], title, text, source_baseline=baseline_lean)

        if scores:
            result = insert_bias_scores(scores)
            if result:
                articles_analyzed += 1

    print(f"  Articles analyzed: {articles_analyzed}/{len(stored_articles)}")

    # Step 6: Cluster stories and rank importance
    print(f"\n[6/7] Clustering stories and ranking importance...")
    clusters_created = run_clustering_and_ranking(stored_articles, sources)
    print(f"  Clusters created: {clusters_created}")

    # Step 7: Update pipeline run
    duration = time.time() - start_time
    print(f"\n[7/7] Finalizing pipeline run...")
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
    print(f"  Sources: {len(sources)} | Articles: {len(stored_articles)} | Analyzed: {articles_analyzed} | Clusters: {clusters_created}")
    print(f"  Errors: {len(fetch_errors)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
