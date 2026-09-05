"""
News Memory Engine — Live Poller

Lightweight daemon that runs every 30 minutes via GitHub Actions.
Polls the top 2 stories' sources for new articles, generates wire-style
one-liner summaries via Gemini, and inserts them into live_updates.

Usage:
    python pipeline/memory/live_poller.py [--json] [--verbose]
"""

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import supabase

# Gemini calls split across all tracked stories
MAX_GEMINI_CALLS_TOTAL = 10

# Max articles per story per run
MAX_ARTICLES_PER_STORY = 8


def live_poll(verbose: bool = False) -> dict:
    """
    Main entry point. Polls all active top stories' sources for new articles.

    Returns:
        Summary dict with status and per-story results.
    """
    start = time.time()

    # 1. Get all active top stories
    top_stories = _get_active_top_stories()
    if not top_stories:
        return {"status": "skip", "reason": "no active top stories"}

    if verbose:
        print(f"[poll] Tracking {len(top_stories)} stories")

    # Split Gemini budget evenly across stories
    gemini_per_story = MAX_GEMINI_CALLS_TOTAL // max(1, len(top_stories))

    results = []
    for story in top_stories:
        result = _poll_single_story(story, gemini_per_story, verbose)
        results.append(result)

    elapsed = round(time.time() - start, 1)

    return {
        "status": "ok",
        "stories_polled": len(results),
        "results": results,
        "duration_s": elapsed,
    }


def _poll_single_story(
    story: dict, gemini_budget: int, verbose: bool = False
) -> dict:
    """Poll a single story's sources for new articles."""
    memory_id = story["id"]
    headline = story["headline"]
    rank = story.get("rank", 1)
    source_slugs = story.get("source_slugs", [])

    if verbose:
        print(f"\n[poll] Story #{rank}: {headline[:80]}")
        print(f"[poll]   Sources: {', '.join(source_slugs[:5])}{'...' if len(source_slugs) > 5 else ''}")

    if not source_slugs:
        return {"rank": rank, "headline": headline[:80], "status": "skip", "reason": "no sources"}

    # Look up source details
    sources = _get_sources_by_slug(source_slugs)
    if not sources:
        return {"rank": rank, "headline": headline[:80], "status": "skip", "reason": "no RSS URLs"}

    # Fetch new articles from RSS
    new_articles = _fetch_new_articles(sources, memory_id, verbose)

    if verbose:
        print(f"[poll]   Found {len(new_articles)} new articles")

    if not new_articles:
        _update_polled_timestamp(memory_id)
        return {
            "rank": rank,
            "headline": headline[:80],
            "new_articles": 0,
        }

    # Limit per story
    new_articles = new_articles[:MAX_ARTICLES_PER_STORY]

    # Generate one-liner summaries via Gemini
    gemini_count = _summarize_articles(new_articles, headline, gemini_budget, verbose)

    # Insert into live_updates
    inserted = _insert_live_updates(new_articles, memory_id)

    # Update counts
    _update_memory_counts(memory_id, inserted)

    # Denormalize onto cluster
    cluster_id = story.get("cluster_id")
    if cluster_id:
        _denormalize_live_updates(cluster_id, memory_id)

    return {
        "rank": rank,
        "headline": headline[:80],
        "new_articles": inserted,
        "gemini_summaries": gemini_count,
    }


def _get_active_top_stories() -> list[dict]:
    """Fetch all active top stories from story_memory, ordered by rank."""
    try:
        result = supabase.table("story_memory").select("*").eq(
            "is_active", True
        ).order("rank").limit(2).execute()
        return result.data or []
    except Exception as e:
        print(f"[poll] Error fetching top stories: {e}")
        return []


def _get_sources_by_slug(slugs: list[str]) -> list[dict]:
    """Look up source details by slug."""
    try:
        result = supabase.table("sources").select(
            "id,slug,name,rss_url"
        ).in_("slug", slugs).execute()
        return [s for s in (result.data or []) if s.get("rss_url")]
    except Exception as e:
        print(f"[poll] Error fetching sources: {e}")
        return []


def _fetch_new_articles(
    sources: list[dict],
    memory_id: str,
    verbose: bool = False,
) -> list[dict]:
    """
    Fetch RSS from tracked sources, filter to only new articles not already
    in live_updates or the main articles table.
    """
    existing_urls = _get_existing_urls(memory_id)

    all_new = []

    def _fetch_source(source: dict) -> list[dict]:
        rss_url = source.get("rss_url")
        if not rss_url:
            return []
        try:
            import requests
            import feedparser
            resp = requests.get(
                rss_url,
                headers={"User-Agent": "void-news-live-poller/1.0"},
                timeout=15,
                allow_redirects=True,
            )
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
            if not feed.entries:
                return []

            articles = []
            for entry in feed.entries[:10]:
                url = entry.get("link", "")
                title = entry.get("title", "")
                if not url or not title or len(title.strip()) < 10:
                    continue
                if url in existing_urls:
                    continue
                summary = entry.get("summary") or entry.get("description") or ""
                if "<" in summary:
                    from bs4 import BeautifulSoup
                    summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)
                if len(summary) > 500:
                    summary = summary[:497] + "..."

                articles.append({
                    "article_url": url,
                    "title": title.strip(),
                    "summary": summary,
                    "source_slug": source.get("slug", ""),
                    "source_name": source.get("name", ""),
                    "published_at": _extract_pub_date(entry),
                })
            return articles
        except Exception as e:
            if verbose:
                print(f"[poll]   RSS error for {source.get('name', '?')}: {e}")
            return []

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_fetch_source, s): s for s in sources}
        for future in as_completed(futures):
            try:
                all_new.extend(future.result())
            except Exception:
                pass

    return all_new


def _extract_pub_date(entry: dict) -> str | None:
    """Try to extract publication date from RSS entry."""
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass
    return None


def _get_existing_urls(memory_id: str) -> set[str]:
    """Get URLs already in live_updates for this story + recent articles table."""
    urls = set()
    try:
        result = supabase.table("live_updates").select("article_url").eq(
            "story_memory_id", memory_id
        ).execute()
        if result.data:
            urls.update(r["article_url"] for r in result.data)

        from datetime import timedelta
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        result = supabase.table("articles").select("url").gt(
            "created_at", cutoff
        ).execute()
        if result.data:
            urls.update(r["url"] for r in result.data)
    except Exception as e:
        print(f"[poll] Warning: URL dedup check failed: {e}")
    return urls


def _summarize_articles(
    articles: list[dict],
    story_headline: str,
    max_calls: int,
    verbose: bool = False,
) -> int:
    """
    Generate wire-style one-liner summaries for new articles using Gemini.
    Returns number of articles summarized.
    """
    try:
        from summarizer.gemini_client import generate_json, is_available
        if not is_available():
            if verbose:
                print("[poll]   Gemini not available, skipping summaries")
            return 0
    except ImportError:
        return 0

    summarized = 0
    for article in articles[:max_calls]:
        try:
            prompt = (
                f"You are a wire editor. Write ONE sentence (max 25 words) "
                f"capturing the single newest fact from this article.\n\n"
                f"Story context: {story_headline}\n"
                f"Article: \"{article['title']}\" by {article['source_name']}\n"
                f"Summary: {article.get('summary', '')[:500]}\n\n"
                f"Rules:\n"
                f"- One sentence only, max 25 words\n"
                f"- Lead with the new fact, not context\n"
                f"- Use specific numbers, names, actions\n"
                f"- No editorializing — just the fact\n\n"
                f'Return JSON: {{"update_summary": "your one sentence"}}'
            )
            result = generate_json(prompt, count_call=False)
            if result and result.get("update_summary"):
                article["update_summary"] = result["update_summary"].strip()
                article["summarized_at"] = datetime.now(timezone.utc).isoformat()
                summarized += 1
        except Exception as e:
            if verbose:
                print(f"[poll]   Gemini summary failed for {article['title'][:50]}: {e}")
    return summarized


def _insert_live_updates(articles: list[dict], memory_id: str) -> int:
    """Insert new articles into live_updates table. Returns count inserted."""
    inserted = 0
    for article in articles:
        try:
            row = {
                "story_memory_id": memory_id,
                "article_url": article["article_url"],
                "title": article["title"],
                "summary": article.get("summary"),
                "source_slug": article["source_slug"],
                "source_name": article["source_name"],
                "published_at": article.get("published_at"),
                "update_summary": article.get("update_summary"),
                "summarized_at": article.get("summarized_at"),
            }
            supabase.table("live_updates").insert(row).execute()
            inserted += 1
        except Exception as e:
            if "duplicate" not in str(e).lower() and "unique" not in str(e).lower():
                print(f"[poll] Insert error: {e}")
    return inserted


def _update_polled_timestamp(memory_id: str) -> None:
    """Update last_polled_at on story_memory."""
    try:
        supabase.table("story_memory").update({
            "last_polled_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", memory_id).execute()
    except Exception:
        pass


def _update_memory_counts(memory_id: str, new_count: int) -> None:
    """Update polling timestamp and live update count on story_memory."""
    try:
        current = supabase.table("story_memory").select(
            "live_update_count"
        ).eq("id", memory_id).single().execute()
        existing = current.data.get("live_update_count", 0) if current.data else 0

        supabase.table("story_memory").update({
            "last_polled_at": datetime.now(timezone.utc).isoformat(),
            "last_live_update_at": datetime.now(timezone.utc).isoformat(),
            "live_update_count": existing + new_count,
        }).eq("id", memory_id).execute()
    except Exception as e:
        print(f"[poll] Warning: failed to update memory counts: {e}")


def _denormalize_live_updates(cluster_id: str, memory_id: str) -> None:
    """Sync live_update_count and last_live_update_at to the cluster row."""
    try:
        result = supabase.table("live_updates").select(
            "id", count="exact"
        ).eq("story_memory_id", memory_id).is_(
            "merged_into_cluster_id", "null"
        ).execute()
        count = result.count if result.count is not None else 0

        supabase.table("story_clusters").update({
            "live_update_count": count,
            "last_live_update_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", cluster_id).execute()
    except Exception as e:
        print(f"[poll] Warning: failed to denormalize live updates: {e}")


# Legacy alias for backward compatibility
live_poll_for_top_story = live_poll


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="void --news live poller")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    result = live_poll(verbose=args.verbose or not args.json)

    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"\n{'=' * 40}")
        print(f"Live Poll: {result.get('status', 'unknown')}")
        for r in result.get("results", []):
            print(f"  #{r.get('rank', '?')} {r.get('headline', '?')}")
            print(f"     New articles: {r.get('new_articles', 0)}, Gemini: {r.get('gemini_summaries', 0)}")
        if result.get("duration_s"):
            print(f"  Duration: {result['duration_s']}s")
        print(f"{'=' * 40}")
