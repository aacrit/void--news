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
    6. Run bias analysis on each article (5 axes + confidence)
    7. Cluster articles into stories
    8. Categorize and rank clusters (v2 — 7 signals + divergence)
    9. Store clusters with enrichment data, finalize pipeline run
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
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
    supabase,
    update_pipeline_run,
)

# Phase 2: Bias analyzers — optional (require spaCy/NLTK)
ANALYSIS_AVAILABLE = False
try:
    from analyzers.political_lean import analyze_political_lean
    from analyzers.sensationalism import analyze_sensationalism
    from analyzers.opinion_detector import analyze_opinion
    from analyzers.factual_rigor import analyze_factual_rigor
    from analyzers.framing import analyze_framing
    from clustering.story_cluster import cluster_stories
    from categorizer.auto_categorize import categorize_article
    from ranker.importance_ranker import rank_importance, compute_coverage_velocity
    ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"[warn] Analysis modules not available ({e}). Running fetch-only mode.")


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


def compute_confidence(article: dict, scores: dict) -> float:
    """
    Compute per-article analysis confidence based on text quality
    and signal strength.

    Factors:
        - Word count: short articles have less signal (30%)
        - Signal variance: scores near defaults = low confidence (40%)
        - Text availability: no full text = very low confidence (30%)
    """
    word_count = article.get("word_count", 0) or 0
    full_text = article.get("full_text", "") or ""

    # Length confidence: articles under 500 words have less reliable analysis
    # 100 words = 0.2, 300 = 0.6, 500+ = 1.0
    length_conf = min(1.0, word_count / 500.0) if word_count > 0 else 0.1

    # Text availability: no full text means analysis ran on title/summary only
    text_conf = 1.0 if len(full_text) > 200 else (0.5 if full_text else 0.1)

    # Signal strength: how many axes deviated from defaults
    defaults = {
        "political_lean": 50, "sensationalism": 10,
        "opinion_fact": 25, "factual_rigor": 50, "framing": 15,
    }
    deviations = 0
    for key, default_val in defaults.items():
        actual = scores.get(key, default_val)
        if abs(actual - default_val) > 5:
            deviations += 1
    # 0 deviations = 0.3 (all defaults), 5 deviations = 1.0 (all fired)
    signal_conf = 0.3 + (deviations / 5.0) * 0.7

    confidence = (length_conf * 0.30) + (text_conf * 0.30) + (signal_conf * 0.40)
    return round(max(0.1, min(1.0, confidence)), 2)


def run_bias_analysis(article: dict, source: dict, cluster_articles: list[dict] | None = None) -> dict:
    """
    Run all 5 bias analyzers on a single article with computed confidence.

    Args:
        article: Article dict with full_text, title, etc.
        source: Source dict with political_lean_baseline, etc.
        cluster_articles: Optional list of other articles in the same cluster,
            passed to the framing analyzer for cross-article omission detection.

    Returns a dict with score keys ready for DB insertion.
    Each analyzer is run independently; failures fall back to defaults.
    Analyzers that return dicts (all 5 axes) have their rationale collected
    into a JSONB-ready rationale field.
    """
    scores = {
        "political_lean": 50,
        "sensationalism": 10,
        "opinion_fact": 25,
        "factual_rigor": 50,
        "framing": 15,
        "confidence": 0.7,
    }
    rationale = {}

    try:
        result = analyze_political_lean(article, source)
        if isinstance(result, dict):
            scores["political_lean"] = result["score"]
            rationale["lean"] = result["rationale"]
        else:
            scores["political_lean"] = result
    except Exception as e:
        print(f"    [warn] Political lean failed: {e}")

    try:
        result = analyze_sensationalism(article)
        if isinstance(result, dict):
            scores["sensationalism"] = result["score"]
            rationale["sensationalism"] = result["rationale"]
        else:
            scores["sensationalism"] = result
    except Exception as e:
        print(f"    [warn] Sensationalism failed: {e}")

    try:
        result = analyze_opinion(article)
        if isinstance(result, dict):
            scores["opinion_fact"] = result["score"]
            rationale["opinion"] = result["rationale"]
        else:
            scores["opinion_fact"] = result
    except Exception as e:
        print(f"    [warn] Opinion detection failed: {e}")

    try:
        result = analyze_factual_rigor(article)
        if isinstance(result, dict):
            scores["factual_rigor"] = result["score"]
            rationale["coverage"] = result["rationale"]
        else:
            scores["factual_rigor"] = result
    except Exception as e:
        print(f"    [warn] Factual rigor failed: {e}")

    try:
        result = analyze_framing(article, cluster_articles=cluster_articles)
        if isinstance(result, dict):
            scores["framing"] = result["score"]
            rationale["framing"] = result["rationale"]
        else:
            scores["framing"] = result
    except Exception as e:
        print(f"    [warn] Framing failed: {e}")

    # Compute real confidence based on text quality and signal strength
    scores["confidence"] = compute_confidence(article, scores)

    # Attach rationale as JSON string for the JSONB column
    if rationale:
        scores["rationale"] = json.dumps(rationale)

    return scores


def enrich_cluster(cluster_id: str) -> None:
    """
    Call the Supabase RPC to refresh enrichment data for a cluster.
    Falls back to a manual update if the function doesn't exist.
    """
    try:
        supabase.rpc("refresh_cluster_enrichment", {"p_cluster_id": cluster_id}).execute()
    except Exception as e:
        # RPC not deployed yet — compute client-side as fallback
        if "function" in str(e).lower() or "does not exist" in str(e).lower():
            _enrich_cluster_fallback(cluster_id)
        else:
            print(f"  [warn] Cluster enrichment failed for {cluster_id}: {e}")


def _generate_consensus_divergence(
    count: int,
    pl_values: list, sens_values: list, of_values: list,
    fr_values: list, frm_values: list,
    avg_pl: float, avg_sens: float, avg_of: float,
    avg_fr: float, avg_frm: float,
    lean_spread: float, framing_spread: float, lean_range: float,
    sensationalism_spread: float, opinion_spread: float,
) -> tuple[list[str], list[str]]:
    """
    Generate human-readable consensus and divergence points from bias score
    analysis across articles in a cluster.

    Consensus: axes where sources agree (scores close together).
    Divergence: axes where sources disagree (scores spread widely).

    Returns (consensus_list, divergence_list) as lists of strings.
    """
    if count < 2:
        return (
            ["Single-source coverage — no cross-source comparison available"],
            [],
        )

    consensus = []
    divergence = []

    # --- Political Lean ---
    if lean_range <= 15:
        if avg_pl < 40:
            consensus.append("Sources show similar left-leaning political framing")
        elif avg_pl > 60:
            consensus.append("Sources show similar right-leaning political framing")
        else:
            consensus.append("Sources show similar centrist political framing")
    elif lean_range > 30:
        divergence.append(
            f"Sources show significant differences in political framing "
            f"(lean spread: {int(lean_range)} points)"
        )
    elif lean_spread > 15:
        divergence.append("Sources show moderate differences in political framing")

    # --- Sensationalism ---
    if sensationalism_spread <= 8 and avg_sens < 25:
        consensus.append("Coverage maintains a measured tone across sources")
    elif sensationalism_spread <= 8 and avg_sens >= 25:
        consensus.append("Sources use a similarly elevated tone in their coverage")
    elif sensationalism_spread > 15:
        divergence.append(
            "Some sources use notably more sensational language than others"
        )

    # --- Opinion vs. Fact ---
    if opinion_spread <= 10 and avg_of < 30:
        consensus.append(
            "Coverage is primarily factual reporting across all sources"
        )
    elif opinion_spread <= 10 and avg_of >= 30 and avg_of < 60:
        consensus.append("Sources take a similar analytical approach to this story")
    elif opinion_spread <= 10 and avg_of >= 60:
        consensus.append(
            "Sources consistently present opinion-heavy coverage"
        )
    elif opinion_spread > 15:
        divergence.append(
            "Sources range from straight reporting to opinion-heavy coverage"
        )

    # --- Factual Rigor ---
    if all(v >= 70 for v in fr_values):
        consensus.append("Sources demonstrate strong factual sourcing")
    elif all(v < 40 for v in fr_values):
        consensus.append("Sources show similarly limited factual sourcing")
    elif max(fr_values) - min(fr_values) > 30:
        divergence.append(
            "Sources differ in the depth of their factual sourcing"
        )

    # --- Framing ---
    if framing_spread <= 10:
        if avg_frm < 25:
            consensus.append("Sources use relatively neutral framing")
        else:
            consensus.append("Sources apply similar framing choices")
    elif framing_spread > 15:
        divergence.append(
            "Sources differ in how they frame the story "
            "(emphasis and language choices vary)"
        )

    # Ensure we always have at least one point in each list when there are
    # multiple sources, to avoid empty sections in the UI.
    if not consensus:
        consensus.append(
            "Sources broadly agree on the key facts of this story"
        )
    if not divergence:
        divergence.append(
            "No major divergence detected across sources on this story"
        )

    return consensus, divergence


def _enrich_cluster_fallback(cluster_id: str) -> None:
    """
    Client-side fallback for cluster enrichment when the DB function
    hasn't been deployed yet.
    """
    try:
        # Fetch bias scores for this cluster's articles
        result = (
            supabase.table("cluster_articles")
            .select("article_id")
            .eq("cluster_id", cluster_id)
            .execute()
        )
        if not result.data:
            return

        article_ids = [r["article_id"] for r in result.data]

        scores_result = (
            supabase.table("bias_scores")
            .select("political_lean,sensationalism,opinion_fact,factual_rigor,framing")
            .in_("article_id", article_ids)
            .execute()
        )
        if not scores_result.data:
            return

        scores = scores_result.data
        count = len(scores)

        import math

        def _stddev(vals):
            if len(vals) < 2:
                return 0.0
            mean = sum(vals) / len(vals)
            return math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))

        pl_values = [s["political_lean"] for s in scores]
        sens_values = [s["sensationalism"] for s in scores]
        of_values = [s["opinion_fact"] for s in scores]
        fr_values = [s["factual_rigor"] for s in scores]
        frm_values = [s["framing"] for s in scores]

        # Weighted average political lean (weight by factual rigor, matching the view)
        total_rigor = sum(fr_values)
        if total_rigor > 0:
            avg_pl = round(sum(p * r for p, r in zip(pl_values, fr_values)) / total_rigor)
        else:
            avg_pl = round(sum(pl_values) / count) if count else 50

        avg_sens = round(sum(sens_values) / count) if count else 30
        avg_of = round(sum(of_values) / count) if count else 25
        avg_fr = round(sum(fr_values) / count) if count else 50
        avg_frm = round(sum(frm_values) / count) if count else 40

        # Compute all spread metrics (matching the view)
        lean_spread = round(_stddev(pl_values), 1)
        framing_spread = round(_stddev(frm_values), 1)
        lean_range = max(pl_values) - min(pl_values) if pl_values else 0
        sensationalism_spread = round(_stddev(sens_values), 1)
        opinion_spread = round(_stddev(of_values), 1)

        # Divergence score
        divergence = min(100.0,
            (min(lean_range / 60.0, 1.0) * 40.0) +
            (min(lean_spread / 20.0, 1.0) * 30.0) +
            (min(framing_spread / 25.0, 1.0) * 30.0)
        )

        # Compute tier breakdown for 3-lens coverage score
        tier_breakdown = {"us_major": 0, "international": 0, "independent": 0}
        try:
            arts_result = (
                supabase.table("cluster_articles")
                .select("article_id")
                .eq("cluster_id", cluster_id)
                .execute()
            )
            if arts_result.data:
                art_ids = [r["article_id"] for r in arts_result.data]
                src_result = (
                    supabase.table("articles")
                    .select("source_id")
                    .in_("id", art_ids)
                    .execute()
                )
                if src_result.data:
                    source_ids = list({r["source_id"] for r in src_result.data if r.get("source_id")})
                    if source_ids:
                        tier_result = (
                            supabase.table("sources")
                            .select("tier")
                            .in_("id", source_ids)
                            .execute()
                        )
                        if tier_result.data:
                            for r in tier_result.data:
                                t = r.get("tier", "")
                                if t in tier_breakdown:
                                    tier_breakdown[t] += 1
        except Exception:
            pass  # tier breakdown is best-effort

        tier_count = len([v for v in tier_breakdown.values() if v > 0])
        source_count_val = sum(tier_breakdown.values()) or count
        agg_confidence = min(1.0, count / 5.0)

        # Coverage score: composite of source breadth, tier diversity, confidence, rigor
        coverage_score = round(
            (min(1.0, source_count_val / 10.0) * 35.0)
            + (tier_count / 3.0 * 20.0)
            + (agg_confidence * 20.0)
            + (avg_fr / 100.0 * 25.0),
            1,
        )

        # Opinion label
        if avg_of <= 25:
            opinion_label = "Reporting"
        elif avg_of <= 50:
            opinion_label = "Analysis"
        elif avg_of <= 75:
            opinion_label = "Opinion"
        else:
            opinion_label = "Editorial"

        bias_diversity = {
            "avg_political_lean": avg_pl,
            "avg_sensationalism": avg_sens,
            "avg_opinion_fact": avg_of,
            "avg_factual_rigor": avg_fr,
            "avg_framing": avg_frm,
            "lean_spread": lean_spread,
            "framing_spread": framing_spread,
            "lean_range": lean_range,
            "sensationalism_spread": sensationalism_spread,
            "opinion_spread": opinion_spread,
            "aggregate_confidence": agg_confidence,
            "analyzed_count": count,
            "coverage_score": coverage_score,
            "tier_breakdown": tier_breakdown,
            "avg_opinion_label": opinion_label,
        }

        # Generate consensus/divergence text from bias score analysis
        consensus_pts, divergence_pts = _generate_consensus_divergence(
            count, pl_values, sens_values, of_values, fr_values, frm_values,
            avg_pl, avg_sens, avg_of, avg_fr, avg_frm,
            lean_spread, framing_spread, lean_range,
            sensationalism_spread, opinion_spread,
        )

        supabase.table("story_clusters").update({
            "divergence_score": round(divergence, 2),
            "bias_diversity": json.dumps(bias_diversity),
            "consensus_points": json.dumps(consensus_pts),
            "divergence_points": json.dumps(divergence_pts),
        }).eq("id", cluster_id).execute()

    except Exception as e:
        print(f"  [warn] Fallback enrichment failed for {cluster_id}: {e}")


def _scrape_single(article_data, source_map):
    """Scrape a single article (for parallel execution)."""
    url = article_data.get("url", "")
    if not url:
        return None
    try:
        scraped = scrape_article(url)
        article_data["full_text"] = scraped.get("full_text", "")
        article_data["word_count"] = scraped.get("word_count", 0)
        article_data["image_url"] = scraped.get("image_url")
    except Exception:
        pass  # Article proceeds with empty full_text

    # RSS summary fallback: if scraper got no text, use the RSS summary
    # A 200-word summary is far better than empty for NLP analysis
    if not article_data.get("full_text"):
        summary = article_data.get("summary", "") or ""
        title = article_data.get("title", "") or ""
        if summary and len(summary) > 50:
            article_data["full_text"] = f"{title}\n\n{summary}"
            article_data["word_count"] = len(article_data["full_text"].split())

    # Determine section
    source_id_slug = article_data.get("source_id", "")
    source_info = source_map.get(source_id_slug, {})
    source_tier = source_info.get("tier", "")
    source_country = source_info.get("country", "")
    if source_tier == "us_major":
        article_data["section"] = "us"
    elif source_country == "US" and source_tier == "independent":
        article_data["section"] = "us"
    else:
        article_data["section"] = "world"

    return article_data


def main():
    """Run the full news ingestion + analysis pipeline."""
    start_time = time.time()
    print("=" * 60)
    print(f"void --news pipeline starting at {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/9] Loading sources...")
    sources = load_sources()
    if not sources:
        print("[abort] No sources loaded. Exiting.")
        return

    # Seed/sync sources into Supabase via batch upsert (replaces N+1 per-source queries)
    print("\n  Syncing sources to Supabase...")
    source_map = {}  # slug -> source dict with UUID
    source_rows = [{
        "slug": s.get("id", ""),
        "name": s.get("name", ""),
        "url": s.get("url", ""),
        "rss_url": s.get("rss_url"),
        "tier": s.get("tier", "independent"),
        "country": s.get("country", "US"),
        "type": s.get("type", "digital"),
        "political_lean_baseline": s.get("political_lean_baseline"),
        "credibility_notes": s.get("credibility_notes"),
    } for s in sources]

    try:
        result = supabase.table("sources").upsert(
            source_rows, on_conflict="slug"
        ).execute()
        # Map slugs to DB UUIDs
        if result.data:
            slug_to_uuid = {r["slug"]: r["id"] for r in result.data}
            for s in sources:
                slug = s.get("id", "")
                if slug in slug_to_uuid:
                    s["db_id"] = slug_to_uuid[slug]
    except Exception as e:
        print(f"  [warn] Batch source upsert failed, falling back to individual sync: {e}")
        # Fallback: individual source sync
        for s in sources:
            slug = s.get("id", "")
            try:
                existing = supabase.table("sources").select("id").eq("slug", slug).limit(1).execute()
                if existing.data:
                    s["db_id"] = existing.data[0]["id"]
            except Exception as ex:
                if "duplicate" not in str(ex).lower():
                    print(f"  [warn] Source sync failed for {slug}: {ex}")

    for s in sources:
        source_map[s.get("id", "")] = s

    sources_with_ids = [s for s in sources if s.get("db_id")]
    print(f"  {len(sources_with_ids)} sources synced to Supabase")

    # Step 2: Create pipeline run record
    print("\n[2/9] Creating pipeline run record...")
    pipeline_run = create_pipeline_run()
    run_id = pipeline_run["id"] if pipeline_run else None
    if run_id:
        print(f"  Pipeline run ID: {run_id}")
    else:
        print("  [warn] Could not create pipeline run record.")

    # Step 3: Fetch articles via RSS
    print("\n[3/9] Fetching RSS feeds...")
    articles_raw, fetch_errors = fetch_from_rss(sources)
    print(f"  Total raw articles: {len(articles_raw)}")
    print(f"  Fetch errors: {len(fetch_errors)}")

    # Step 4: Scrape full text and store articles (parallel)
    print("\n[4/9] Scraping article text (parallel, 15 workers)...")
    stored_articles = []

    with ThreadPoolExecutor(max_workers=15) as executor:
        futures = {
            executor.submit(_scrape_single, article_data, source_map): article_data
            for article_data in articles_raw
        }
        for i, future in enumerate(as_completed(futures)):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"  Scraped {i + 1}/{len(articles_raw)}...")
            result = future.result()
            if result:
                db_result = insert_article(result)
                if db_result:
                    result["id"] = db_result["id"]
                    stored_articles.append(result)

    print(f"  Articles stored: {len(stored_articles)}/{len(articles_raw)}")

    # Step 4b: Content-based deduplication
    # Removes near-duplicate articles (syndicated/wire content with different URLs)
    # before analysis to avoid wasting compute on duplicate text.
    print(f"\n[4b] Content-based deduplication on {len(stored_articles)} articles...")
    try:
        from clustering.deduplicator import deduplicate_articles

        # Enrich articles with tier info so deduplicator can prefer higher-tier sources
        for art in stored_articles:
            src_slug = art.get("source_id", "")
            src_info = source_map.get(src_slug, {})
            art["tier"] = src_info.get("tier", "")

        articles_before_dedup = len(stored_articles)
        stored_articles = deduplicate_articles(stored_articles)
        articles_after_dedup = len(stored_articles)
        print(f"  Deduplication: {articles_before_dedup} -> {articles_after_dedup} "
              f"({articles_before_dedup - articles_after_dedup} duplicates removed)")
    except ImportError:
        print("  [skip] Deduplicator not available (sklearn not installed)")
    except Exception as e:
        print(f"  [warn] Deduplication failed, continuing with all articles: {e}")

    # Step 5: Run bias analysis on each article
    articles_analyzed = 0
    clusters_created = 0
    # Collect per-article bias scores keyed by article_id for ranking
    article_bias_map: dict[str, dict] = {}
    # Collect article-to-categories mapping for junction table
    article_categories_map: dict[str, list[str]] = {}

    if not ANALYSIS_AVAILABLE:
        print("\n[5-9] Skipping analysis/clustering (NLP deps not installed). Fetch-only mode.")
    else:
        # Step 5: Bias analysis with computed confidence
        print(f"\n[5/9] Running bias analysis on {len(stored_articles)} articles...")
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
                # Store for ranking
                article_bias_map[article.get("id", "")] = {
                    k: v for k, v in bias_scores.items() if k != "article_id"
                }
        print(f"  Articles analyzed: {articles_analyzed}/{len(stored_articles)}")

        # Step 6: Cluster articles
        print(f"\n[6/9] Clustering {len(stored_articles)} articles into stories...")
        clusters = []
        try:
            clusters = cluster_stories(stored_articles)
            print(f"  Clusters formed: {len(clusters)}")
        except Exception as e:
            print(f"  [error] Clustering failed: {e}")

        # Step 6b: Re-run framing analysis with cluster context
        # Framing's omission detection benefits from knowing what other
        # articles in the same cluster mention. Initial analysis (step 5)
        # ran without cluster context. Now re-score framing for multi-article
        # clusters and update the stored bias scores.
        print("\n[6b] Re-scoring framing with cluster context...")
        framing_updated = 0
        for cluster in clusters:
            cluster_articles_list = cluster.get("articles", [])
            if len(cluster_articles_list) < 2:
                continue  # single-article clusters gain nothing
            for art in cluster_articles_list:
                art_id = art.get("id", "")
                if not art_id:
                    continue
                try:
                    result = analyze_framing(art, cluster_articles=cluster_articles_list)
                    new_framing = result["score"] if isinstance(result, dict) else result
                    new_rationale = result.get("rationale") if isinstance(result, dict) else None

                    # Update in-memory bias map
                    if art_id in article_bias_map:
                        article_bias_map[art_id]["framing"] = new_framing

                    # Update DB: bias_scores row
                    update_data: dict = {"framing": new_framing}
                    # Merge new framing rationale into existing rationale
                    if new_rationale:
                        existing = article_bias_map.get(art_id, {})
                        existing_rationale_str = existing.get("rationale")
                        if existing_rationale_str and isinstance(existing_rationale_str, str):
                            try:
                                existing_rationale = json.loads(existing_rationale_str)
                            except (json.JSONDecodeError, TypeError):
                                existing_rationale = {}
                        elif isinstance(existing_rationale_str, dict):
                            existing_rationale = existing_rationale_str
                        else:
                            existing_rationale = {}
                        existing_rationale["framing"] = new_rationale
                        update_data["rationale"] = json.dumps(existing_rationale)

                    supabase.table("bias_scores").update(
                        update_data
                    ).eq("article_id", art_id).execute()
                    framing_updated += 1
                except Exception as e:
                    print(f"    [warn] Framing re-score failed for {art_id}: {e}")
        print(f"  Framing re-scored: {framing_updated} articles in multi-article clusters")

        # Step 7: Categorize and rank with v2 engine
        print("\n[7/9] Categorizing and ranking clusters (v2 engine)...")
        for cluster in clusters:
            cluster_articles_list = cluster.get("articles", [])

            # Categorize
            try:
                categories = categorize_article(cluster_articles_list[0]) if cluster_articles_list else ["politics"]
                cluster["category"] = categories[0] if categories else "politics"
                # Store all categories for each article in the cluster
                for art in cluster_articles_list:
                    art_id = art.get("id", "")
                    if art_id:
                        article_categories_map[art_id] = categories
            except Exception:
                cluster["category"] = "politics"

            # Gather bias scores for articles in this cluster
            cluster_bias_scores = []
            for art in cluster_articles_list:
                art_id = art.get("id", "")
                if art_id in article_bias_map:
                    cluster_bias_scores.append(article_bias_map[art_id])

            # Rank with v2 engine (7 signals + divergence)
            try:
                rank_result = rank_importance(
                    cluster_articles_list, sources, cluster_bias_scores
                )
                cluster["importance_score"] = rank_result["importance_score"]
                cluster["divergence_score"] = rank_result["divergence_score"]
                cluster["coverage_velocity"] = rank_result["coverage_velocity"]
                cluster["headline_rank"] = rank_result["headline_rank"]
            except Exception as e:
                print(f"  [warn] Ranking failed: {e}")
                cluster["importance_score"] = 20.0
                cluster["divergence_score"] = 0.0
                cluster["coverage_velocity"] = 0
                cluster["headline_rank"] = 20.0

        clusters.sort(key=lambda c: c.get("headline_rank", 0), reverse=True)

        # Step 8: Store clusters with enrichment data
        print("\n[8/9] Storing clusters with enrichment data...")
        for cluster in clusters:
            cluster_articles_list = cluster.get("articles", [])

            # Determine cluster section from its articles
            section_counts: dict[str, int] = {}
            for art in cluster_articles_list:
                sec = art.get("section", "world")
                section_counts[sec] = section_counts.get(sec, 0) + 1
            cluster_section = max(section_counts, key=section_counts.get) if section_counts else "world"

            # Populate cluster summary from first article
            cluster_summary = ""
            if cluster_articles_list:
                first_art = cluster_articles_list[0]
                cluster_summary = first_art.get("summary", "") or ""
                if not cluster_summary:
                    cluster_summary = (first_art.get("title", "") or "")[:200]

            result = insert_cluster({
                "title": cluster.get("title", "Untitled Story")[:500],
                "summary": cluster_summary,
                "category": cluster.get("category", "politics"),
                "section": cluster_section,
                "importance_score": round(cluster.get("importance_score", 0.0), 2),
                "source_count": cluster.get("source_count", 0),
                "first_published": cluster.get("first_published", ""),
                "divergence_score": round(cluster.get("divergence_score", 0.0), 2),
                "headline_rank": round(cluster.get("headline_rank", 0.0), 2),
                "coverage_velocity": cluster.get("coverage_velocity", 0),
            })
            if result:
                clusters_created += 1
                cluster_id = result.get("id", "")
                for article_id in cluster.get("article_ids", []):
                    if article_id:
                        link_article_to_cluster(cluster_id, article_id)

                # Step 9: Enrich cluster with aggregated bias data
                enrich_cluster(cluster_id)

    print(f"  Clusters stored: {clusters_created}/{len(clusters) if ANALYSIS_AVAILABLE else 0}")

    # Step 9b: Populate article_categories junction table
    if ANALYSIS_AVAILABLE and article_categories_map:
        print("\n[9b] Populating article_categories junction table...")
        # Fetch category slug -> UUID mapping
        category_slug_map: dict[str, str] = {}
        try:
            cat_result = supabase.table("categories").select("id,slug").execute()
            if cat_result.data:
                category_slug_map = {r["slug"]: r["id"] for r in cat_result.data}
        except Exception as e:
            print(f"  [warn] Failed to fetch categories: {e}")

        if category_slug_map:
            ac_inserted = 0
            ac_rows = []
            for art_id, cat_slugs in article_categories_map.items():
                for slug in cat_slugs:
                    cat_id = category_slug_map.get(slug)
                    if cat_id:
                        ac_rows.append({
                            "article_id": art_id,
                            "category_id": cat_id,
                        })
            # Batch upsert to avoid duplicates
            if ac_rows:
                try:
                    # Upsert in chunks of 200 to avoid payload limits
                    for i in range(0, len(ac_rows), 200):
                        chunk = ac_rows[i:i + 200]
                        supabase.table("article_categories").upsert(
                            chunk, on_conflict="article_id,category_id"
                        ).execute()
                        ac_inserted += len(chunk)
                    print(f"  article_categories rows inserted: {ac_inserted}")
                except Exception as e:
                    print(f"  [warn] article_categories batch insert failed: {e}")
                    # Fallback: insert one by one
                    for row in ac_rows:
                        try:
                            supabase.table("article_categories").upsert(
                                row, on_conflict="article_id,category_id"
                            ).execute()
                        except Exception:
                            pass  # skip duplicates silently
        else:
            print("  [warn] No categories found in DB; skipping article_categories")

    # Step 9c: Update per-source per-topic tracking (Axis 6)
    if ANALYSIS_AVAILABLE and clusters:
        print("\n[9c] Updating per-source per-topic tracking...")
        try:
            from analyzers.topic_outlet_tracker import update_source_topic_lean

            tracking_articles = []
            for cluster in clusters:
                for ca in cluster.get("articles", []):
                    art_id = ca.get("id", "")
                    if art_id and art_id in article_bias_map and cluster.get("category"):
                        scores = article_bias_map[art_id]
                        # Resolve source_id slug to DB UUID
                        src_slug = ca.get("source_id", "")
                        src_info = source_map.get(src_slug, {})
                        db_source_id = src_info.get("db_id")
                        if db_source_id:
                            tracking_articles.append({
                                "source_id": db_source_id,
                                "category": cluster["category"],
                                "political_lean": scores.get("political_lean", 50),
                                "sensationalism": scores.get("sensationalism", 10),
                                "opinion_fact": scores.get("opinion_fact", 25),
                            })
            if tracking_articles:
                stats = update_source_topic_lean(tracking_articles, supabase)
                print(f"  Updated source-topic tracking: {stats}")
            else:
                print("  No articles with scores + categories to track")
        except Exception as e:
            print(f"  [warn] Source-topic tracking failed: {e}")

    # Step 10: Truncate full_text for IP compliance
    # Full article text is used only for NLP analysis (transformative use).
    # After analysis, truncate to a short excerpt to avoid storing copyrighted
    # content long-term. Bias scores (the derived, transformative output) are
    # retained. See docs/IP-COMPLIANCE.md — AP v. Meltwater precedent.
    print("\n[10] Truncating full_text for IP compliance...")
    try:
        truncated = 0
        for article in stored_articles:
            art_id = article.get("id", "")
            if art_id:
                full = article.get("full_text", "") or ""
                if len(full) > 300:
                    excerpt = full[:297] + "..."
                    supabase.table("articles").update({
                        "full_text": excerpt,
                    }).eq("id", art_id).execute()
                    truncated += 1
        print(f"  Truncated {truncated} articles to 300-char excerpts")
    except Exception as e:
        print(f"  [warn] Full-text truncation failed: {e}")

    # Cleanup: remove stale clusters and stuck pipeline runs
    print("\n[cleanup] Running database cleanup RPCs...")
    try:
        result = supabase.rpc("cleanup_stale_clusters").execute()
        cleaned = result.data if result.data else 0
        print(f"  Stale clusters cleaned: {cleaned}")
    except Exception as e:
        print(f"  [warn] cleanup_stale_clusters failed: {e}")

    try:
        result = supabase.rpc("cleanup_stuck_pipeline_runs").execute()
        cleaned = result.data if result.data else 0
        print(f"  Stuck pipeline runs cleaned: {cleaned}")
    except Exception as e:
        print(f"  [warn] cleanup_stuck_pipeline_runs failed: {e}")

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
