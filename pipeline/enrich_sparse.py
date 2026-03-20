"""
Targeted enrichment for opinion clusters and single-source stories.

1. Opinion clusters without Gemini summaries → Gemini enrich
2. Single-source clusters without summaries → pull article full_text/summary
3. All single-source clusters → ensure summary = article's best available text

Usage:
    PYTHONUNBUFFERED=1 python3 pipeline/enrich_sparse.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase

# Try to import Gemini summarizer
GEMINI_OK = False
try:
    from summarizer.cluster_summarizer import summarize_cluster
    from summarizer.gemini_client import is_available, calls_remaining
    GEMINI_OK = is_available()
except ImportError:
    pass


def _get_cluster_articles(cluster_id: str) -> list[dict]:
    """Fetch articles for a cluster with their full text and metadata."""
    ca_res = supabase.table("cluster_articles").select(
        "article_id"
    ).eq("cluster_id", cluster_id).execute()
    article_ids = [r["article_id"] for r in (ca_res.data or [])]
    if not article_ids:
        return []

    art_res = supabase.table("articles").select(
        "id,source_id,title,summary,full_text,url,word_count"
    ).in_("id", article_ids).execute()
    articles = art_res.data or []

    # Attach source tier for Gemini prompt
    if articles:
        source_ids = list({a["source_id"] for a in articles if a.get("source_id")})
        if source_ids:
            src_res = supabase.table("sources").select(
                "id,tier"
            ).in_("id", source_ids).execute()
            tier_map = {s["id"]: s["tier"] for s in (src_res.data or [])}
            for art in articles:
                art["tier"] = tier_map.get(art.get("source_id", ""), "")

    return articles


def _best_article_text(articles: list[dict]) -> str:
    """Pick the best available text from articles for single-source clusters."""
    if not articles:
        return ""

    # Sort by text quality: longest full_text first, then longest summary
    best = max(articles, key=lambda a: (
        len(a.get("full_text", "") or ""),
        len(a.get("summary", "") or ""),
    ))

    full = (best.get("full_text") or "").strip()
    summary = (best.get("summary") or "").strip()
    title = (best.get("title") or "").strip()

    # Prefer full_text if substantial (>100 chars), then summary, then title
    if len(full) > 100:
        return full
    if len(summary) > 30:
        return summary
    return title


def main():
    start = time.time()
    print("=" * 60)
    print(f"Sparse cluster enrichment {'(Gemini available)' if GEMINI_OK else '(Gemini unavailable — text fallback only)'}")
    print("=" * 60)

    # Fetch all clusters
    print("\n[1/3] Fetching clusters...")
    all_res = supabase.table("story_clusters").select(
        "id,title,summary,source_count,content_type,section"
    ).execute()
    all_clusters = all_res.data or []

    opinion_clusters = [c for c in all_clusters if c.get("content_type") == "opinion"]
    single_source = [c for c in all_clusters if (c.get("source_count") or 0) <= 1]
    needs_summary = [c for c in all_clusters if not c.get("summary") or len(c.get("summary", "")) < 50]

    print(f"  Total clusters: {len(all_clusters)}")
    print(f"  Opinion: {len(opinion_clusters)}")
    print(f"  Single-source: {len(single_source)}")
    print(f"  Missing summary (<50 chars): {len(needs_summary)}")

    # Phase 1: Gemini-enrich opinion clusters that need it
    opinion_needs_enrich = [c for c in opinion_clusters if not c.get("summary") or len(c.get("summary", "")) < 50]
    print(f"\n[2/3] Opinion clusters needing enrichment: {len(opinion_needs_enrich)}")

    gemini_used = 0
    gemini_cap = 50  # leave room for pipeline runs

    if GEMINI_OK and opinion_needs_enrich:
        remaining = calls_remaining()
        print(f"  Gemini calls remaining: {remaining}")

        for c in opinion_needs_enrich:
            if gemini_used >= gemini_cap:
                print(f"  Hit local cap ({gemini_cap} calls)")
                break
            if calls_remaining() <= 0:
                print("  Gemini daily cap reached")
                break

            articles = _get_cluster_articles(c["id"])
            if not articles:
                continue

            result = summarize_cluster(articles)
            if result:
                try:
                    update = {
                        "title": result["headline"],
                        "summary": result["summary"],
                        "consensus_points": result.get("consensus", []),
                        "divergence_points": result.get("divergence", []),
                    }
                    supabase.table("story_clusters").update(update).eq("id", c["id"]).execute()
                    gemini_used += 1
                    print(f"  Gemini enriched: \"{result['headline'][:50]}\"")
                except Exception as e:
                    print(f"  [err] {c['id'][:8]}: {e}")
            else:
                # Fallback: use article text
                text = _best_article_text(articles)
                if text and len(text) > len(c.get("summary", "") or ""):
                    supabase.table("story_clusters").update(
                        {"summary": text[:2000]}
                    ).eq("id", c["id"]).execute()

    # Phase 2: Single-source clusters — ensure summary = best article text
    print(f"\n[3/3] Enriching single-source clusters...")
    single_needs_text = [
        c for c in single_source
        if not c.get("summary") or len(c.get("summary", "")) < 80
    ]

    # Also try Gemini for single-source opinion clusters that have decent text
    single_opinion = [c for c in single_source if c.get("content_type") == "opinion"]

    enriched = 0
    gemini_single = 0

    # First: Gemini for single-source opinion pieces (they benefit most from synthesis)
    if GEMINI_OK:
        for c in single_opinion:
            if gemini_used >= gemini_cap or calls_remaining() <= 0:
                break
            # Skip if already has a good summary
            if c.get("summary") and len(c.get("summary", "")) >= 100:
                continue

            articles = _get_cluster_articles(c["id"])
            if not articles:
                continue

            # Only worth Gemini if the article has enough text
            best_text = _best_article_text(articles)
            if len(best_text) < 200:
                continue

            result = summarize_cluster(articles)
            if result:
                try:
                    supabase.table("story_clusters").update({
                        "title": result["headline"],
                        "summary": result["summary"],
                    }).eq("id", c["id"]).execute()
                    gemini_used += 1
                    gemini_single += 1
                except Exception:
                    pass

    print(f"  Gemini-enriched {gemini_single} single-source opinion clusters")

    # Second: text fallback for all single-source clusters with weak summaries
    for c in single_needs_text:
        articles = _get_cluster_articles(c["id"])
        if not articles:
            continue

        text = _best_article_text(articles)
        current = c.get("summary", "") or ""

        if text and len(text) > len(current):
            try:
                supabase.table("story_clusters").update(
                    {"summary": text[:2000]}
                ).eq("id", c["id"]).execute()
                enriched += 1
            except Exception:
                pass

        if enriched % 50 == 0 and enriched > 0:
            print(f"  [{enriched}] text-enriched so far...")

    print(f"  Text-enriched {enriched} single-source clusters")

    elapsed = time.time() - start
    print(f"\n  Total Gemini calls used: {gemini_used}")
    print(f"  Done in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
