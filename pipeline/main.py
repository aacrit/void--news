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
    7b. Summarize clusters with Gemini Flash (headline, summary, consensus/divergence)
    8. Categorize and rank clusters (v2 — 7 signals + divergence)
    9. Store clusters with enrichment data, finalize pipeline run
"""

import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
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
    from categorizer.auto_categorize import categorize_article, map_to_desk
    from ranker.importance_ranker import rank_importance, compute_coverage_velocity
    ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"[warn] Analysis modules not available ({e}). Running fetch-only mode.")

# Gemini summarizer — optional (requires google-generativeai + API key)
SUMMARIZER_AVAILABLE = False
try:
    from summarizer.cluster_summarizer import summarize_clusters_batch
    from summarizer.gemini_client import is_available as gemini_is_available
    SUMMARIZER_AVAILABLE = True
except ImportError:
    pass

# Gemini bias reasoning — optional (requires gemini_reasoning module + API key)
GEMINI_REASONING_AVAILABLE = False
try:
    from analyzers.gemini_reasoning import (
        reason_clusters_batch,
        apply_reasoning_to_bias_map,
        blend_score,
    )
    GEMINI_REASONING_AVAILABLE = True
except ImportError:
    pass

# Daily Brief generator — optional (requires google-genai + pydub)
BRIEFING_AVAILABLE = False
try:
    from briefing.daily_brief_generator import generate_daily_briefs
    from briefing.audio_producer import produce_audio
    from briefing.voice_rotation import get_voice_for_today, get_voices_for_today
    BRIEFING_AVAILABLE = True
except ImportError as e:
    print(f"[warn] Briefing modules not available ({e}). Skipping daily brief.")


SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"

# ---------------------------------------------------------------------------
# US domestic content signal patterns (UAT-004)
# Used to detect stories about US domestic politics/events even when the
# source is not tier us_major (e.g., international outlet covering US story).
# ---------------------------------------------------------------------------
_US_STATE_NAMES = (
    "alabama|alaska|arizona|arkansas|california|colorado|connecticut|delaware"
    "|florida|georgia|hawaii|idaho|illinois|indiana|iowa|kansas|kentucky"
    "|louisiana|maine|maryland|massachusetts|michigan|minnesota|mississippi"
    "|missouri|montana|nebraska|nevada|new hampshire|new jersey|new mexico"
    "|new york|north carolina|north dakota|ohio|oklahoma|oregon|pennsylvania"
    "|rhode island|south carolina|south dakota|tennessee|texas|utah|vermont"
    "|virginia|washington|west virginia|wisconsin|wyoming"
)
_US_DOMESTIC_PATTERN = re.compile(
    r"\b("
    + _US_STATE_NAMES
    + r"|congress|senate|house of representatives|supreme court"
    r"|white house|pentagon|u\.s\. congress|u\.s\. senate|u\.s\. house"
    r"|federal reserve|fbi|cia|dhs|doj|department of justice"
    r"|republican party|democratic party|gop|dnc|rnc"
    r"|u\.s\. dollar|u\.s\. economy|u\.s\. government|u\.s\. president"
    r"|u\.s\. troops|u\.s\. military|u\.s\. officials"
    r"|aipac|nra|aclu|planned parenthood|irs"
    r"|mid-?term|u\.s\. immigration|border patrol|ice detain"
    r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Country-to-edition mapping for multi-edition support
# Sources from these countries are routed to their respective editions.
# All other countries route to "world" edition.
# ---------------------------------------------------------------------------
_COUNTRY_EDITION_MAP: dict[str, str] = {
    "US": "us",
    "IN": "india",
    "GB": "uk",
    "UK": "uk",  # Non-standard code in some sources; normalize to GB
    "CA": "canada",
}


def _has_us_domestic_signal(article_data: dict) -> bool:
    """
    Return True if the article's title + summary contains clear US domestic
    content signals (state names, US institutions, US political entities).
    Used as a content-based override for section assignment.
    """
    title = article_data.get("title", "") or ""
    summary = article_data.get("summary", "") or ""
    text = f"{title} {summary}"
    return bool(_US_DOMESTIC_PATTERN.search(text))


def load_sources(editions: list[str] | None = None) -> list[dict]:
    """Load the curated source list from data/sources.json.

    Args:
        editions: Optional list of edition slugs to filter by (e.g., ["india"]).
                  If None or empty, loads all sources.
    """
    if not SOURCES_PATH.exists():
        print(f"[error] Sources file not found: {SOURCES_PATH}")
        return []
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)
    total = len(sources)

    if editions:
        # Build set of country codes for requested editions
        # Reverse lookup: edition -> country codes
        edition_to_countries: dict[str, list[str]] = {}
        for country, edition in _COUNTRY_EDITION_MAP.items():
            edition_to_countries.setdefault(edition, []).append(country)
        # "world" = all countries NOT in any specific edition
        mapped_countries = set(_COUNTRY_EDITION_MAP.keys())

        allowed_countries: set[str] = set()
        include_world = False
        for ed in editions:
            if ed == "world":
                include_world = True
            elif ed in edition_to_countries:
                allowed_countries.update(edition_to_countries[ed])

        sources = [
            s for s in sources
            if s.get("country", "") in allowed_countries
            or (include_world and s.get("country", "") not in mapped_countries)
        ]
        print(f"Loaded {len(sources)}/{total} sources for editions: {', '.join(editions)}")
    else:
        print(f"Loaded {total} sources from {SOURCES_PATH}")

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

    # Text availability: smooth ramp instead of a binary cliff.
    # Old formula (1.0 / 0.5 / 0.1) created a confidence step-function that
    # undervalued 201-999-char articles and overvalued 200-char ones equally.
    # New formula: confidence scales linearly from 0.1 (no text) to 1.0 at
    # 1000+ chars, giving proportional credit to summaries and partial text.
    # (Priority 5 fix)
    text_conf = min(1.0, max(0.1, len(full_text) / 1000.0)) if full_text else 0.1

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


def run_bias_analysis(
    article: dict,
    source: dict,
    cluster_articles: list[dict] | None = None,
    topic_lean_data: dict | None = None,
) -> dict:
    """
    Run all 5 bias analyzers on a single article with computed confidence.

    Performance optimization: parses spaCy doc once and passes it to
    analyzers that need NER/dependency parsing (factual_rigor, framing),
    avoiding 2-3 redundant spaCy parses per article.

    Args:
        article: Article dict with full_text, title, etc.
        source: Source dict with political_lean_baseline, etc.
        cluster_articles: Optional list of other articles in the same cluster,
            passed to the framing analyzer for cross-article omission detection.
        topic_lean_data: Optional Axis 6 EMA data for this source+topic pair
            (e.g. {"avg_lean": 42.0}). Passed to analyze_political_lean so it
            can blend longitudinal per-source-per-topic lean into the score.

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
        result = analyze_political_lean(article, source, topic_lean_data=topic_lean_data)
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
        result = analyze_factual_rigor(article, source)
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


def _batch_upsert(table: str, rows: list[dict], chunk_size: int = 200,
                  on_conflict: str | None = None) -> int:
    """
    Batch upsert rows to a Supabase table in chunks.
    Returns the number of rows successfully upserted.
    """
    total = 0
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        try:
            if on_conflict:
                supabase.table(table).upsert(
                    chunk, on_conflict=on_conflict
                ).execute()
            else:
                supabase.table(table).upsert(chunk).execute()
            total += len(chunk)
        except Exception as e:
            print(f"  [warn] Batch {table} upsert failed (chunk {i}): {e}")
            # Fall back to individual upserts for this chunk
            for row in chunk:
                try:
                    if on_conflict:
                        supabase.table(table).upsert(
                            row, on_conflict=on_conflict
                        ).execute()
                    else:
                        supabase.table(table).upsert(row).execute()
                    total += 1
                except Exception:
                    pass  # skip duplicates/errors silently
    return total


def enrich_cluster(cluster_id: str, skip_text: bool = False) -> None:
    """
    Call the Supabase RPC to refresh enrichment data for a cluster,
    then run client-side consensus/divergence generation unless skip_text
    is True (indicates Gemini already generated the text).

    The RPC handles divergence_score, bias_diversity, coverage_score,
    and tier_breakdown, but does NOT generate consensus_points or
    divergence_points text.

    Args:
        cluster_id: UUID of the cluster to enrich.
        skip_text: If True, skip rule-based consensus/divergence generation
            (used when Gemini has already provided these).
    """
    rpc_succeeded = False
    try:
        supabase.rpc("refresh_cluster_enrichment", {"p_cluster_id": cluster_id}).execute()
        rpc_succeeded = True
    except Exception as e:
        # RPC not deployed yet — compute client-side as fallback
        if "function" in str(e).lower() or "does not exist" in str(e).lower():
            _enrich_cluster_fallback(cluster_id, skip_text=skip_text)
            return  # fallback already generates consensus/divergence
        else:
            print(f"  [warn] Cluster enrichment failed for {cluster_id}: {e}")

    # RPC succeeded but omits consensus/divergence text — generate unless Gemini handled it
    if rpc_succeeded and not skip_text:
        _generate_cluster_consensus_divergence(cluster_id)


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


def _enrich_cluster_fallback(cluster_id: str, skip_text: bool = False) -> None:
    """
    Client-side fallback for cluster enrichment when the DB function
    hasn't been deployed yet.

    Args:
        cluster_id: UUID of the cluster to enrich.
        skip_text: If True, skip rule-based consensus/divergence generation
            (used when Gemini has already provided these).
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

        # Classify as reporting vs opinion based on avg opinion score
        content_type = "opinion" if avg_of > 50 else "reporting"

        # Build the update payload — always include numeric aggregates
        update_payload = {
            "divergence_score": round(divergence, 2),
            "bias_diversity": bias_diversity,
            "content_type": content_type,
        }

        # Generate consensus/divergence text unless Gemini already provided it
        if not skip_text:
            consensus_pts, divergence_pts = _generate_consensus_divergence(
                count, pl_values, sens_values, of_values, fr_values, frm_values,
                avg_pl, avg_sens, avg_of, avg_fr, avg_frm,
                lean_spread, framing_spread, lean_range,
                sensationalism_spread, opinion_spread,
            )
            update_payload["consensus_points"] = consensus_pts
            update_payload["divergence_points"] = divergence_pts

        # Pass raw Python objects — Supabase client handles JSONB
        # serialization automatically. Using json.dumps() here would
        # double-serialize, storing escaped JSON strings instead of arrays.
        supabase.table("story_clusters").update(
            update_payload
        ).eq("id", cluster_id).execute()

    except Exception as e:
        print(f"  [warn] Fallback enrichment failed for {cluster_id}: {e}")


def _generate_cluster_consensus_divergence(cluster_id: str) -> None:
    """
    Generate and store consensus/divergence text for a cluster.

    Called after the RPC enrichment succeeds (RPC handles numeric
    aggregates but not the human-readable text). Fetches bias scores,
    computes spreads, generates text via _generate_consensus_divergence,
    and writes just the two JSONB columns.
    """
    try:
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

        total_rigor = sum(fr_values)
        if total_rigor > 0:
            avg_pl = round(sum(p * r for p, r in zip(pl_values, fr_values)) / total_rigor)
        else:
            avg_pl = round(sum(pl_values) / count) if count else 50

        avg_sens = round(sum(sens_values) / count) if count else 30
        avg_of = round(sum(of_values) / count) if count else 25
        avg_fr = round(sum(fr_values) / count) if count else 50
        avg_frm = round(sum(frm_values) / count) if count else 40

        lean_spread = round(_stddev(pl_values), 1)
        framing_spread = round(_stddev(frm_values), 1)
        lean_range = max(pl_values) - min(pl_values) if pl_values else 0
        sensationalism_spread = round(_stddev(sens_values), 1)
        opinion_spread = round(_stddev(of_values), 1)

        consensus_pts, divergence_pts = _generate_consensus_divergence(
            count, pl_values, sens_values, of_values, fr_values, frm_values,
            avg_pl, avg_sens, avg_of, avg_fr, avg_frm,
            lean_spread, framing_spread, lean_range,
            sensationalism_spread, opinion_spread,
        )

        # Pass raw Python lists — Supabase client handles JSONB serialization
        supabase.table("story_clusters").update({
            "consensus_points": consensus_pts,
            "divergence_points": divergence_pts,
        }).eq("id", cluster_id).execute()

    except Exception as e:
        print(f"  [warn] Consensus/divergence generation failed for {cluster_id}: {e}")


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
        # Use canonical URL (final URL after redirects) when available.
        # Google News RSS entries link to news.google.com/rss/articles/CBMi...
        # which redirect to the real article. Storing the canonical URL ensures
        # deduplication works correctly across pipeline runs.
        canonical = scraped.get("canonical_url", "")
        if canonical and canonical != url:
            article_data["url"] = canonical
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

    # Determine section (edition) — route by source country first,
    # then fall back to content-based detection for US stories.
    source_slug = article_data.get("source_slug", "") or article_data.get("source_id", "")
    source_info = source_map.get(source_slug, {})
    source_country = source_info.get("country", "")

    if source_country in _COUNTRY_EDITION_MAP:
        # Country-specific edition: US, India
        article_data["section"] = _COUNTRY_EDITION_MAP[source_country]
    elif _has_us_domestic_signal(article_data):
        # Content-based override: international sources covering clearly
        # US domestic stories should appear in the US edition.
        article_data["section"] = "us"
    else:
        article_data["section"] = "world"

    return article_data


def main():
    """Run the full news ingestion + analysis pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="void --news pipeline")
    parser.add_argument(
        "--editions",
        type=str,
        default="",
        help="Comma-separated edition slugs to process (e.g., 'india'). "
             "Empty = all sources.",
    )
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",") if e.strip()] if args.editions else None

    start_time = time.time()
    print("=" * 60)
    edition_label = ", ".join(editions) if editions else "all"
    print(f"void --news pipeline starting at {datetime.now(timezone.utc).isoformat()}")
    print(f"  Editions: {edition_label}")
    print("=" * 60)

    # Step 1: Load sources
    print("\n[1/9] Loading sources...")
    sources = load_sources(editions=editions)
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

    # Step 3b: Filter out URLs already in the database
    # This avoids scraping ~3,800+ articles that already exist, reducing
    # scrape time from ~7 minutes to seconds on typical runs.
    print("\n[3b] Filtering known URLs...")
    total_rss_urls = len(articles_raw)
    articles_to_scrape = articles_raw  # default: scrape everything (first run / error fallback)

    try:
        rss_urls = {a["url"] for a in articles_raw if a.get("url")}

        if rss_urls:
            # Fetch only recently-published URLs (within 48h) from DB.
            # RSS feeds never surface articles older than 36h, so a full-table
            # scan of all-time URLs is wasteful — a 48h window catches all
            # possible duplicates while reading far fewer rows.
            existing_urls: set[str] = set()
            url_cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            page_size = 1000
            offset = 0
            while True:
                result = (
                    supabase.table("articles")
                    .select("url")
                    .gte("published_at", url_cutoff)
                    .range(offset, offset + page_size - 1)
                    .execute()
                )
                if not result.data:
                    break
                existing_urls.update(r["url"] for r in result.data if r.get("url"))
                if len(result.data) < page_size:
                    break
                offset += page_size

            # Keep articles whose URL is new (not in DB) or has no URL
            articles_to_scrape = [
                a for a in articles_raw
                if not a.get("url") or a["url"] not in existing_urls
            ]

            existing_count = len(rss_urls & existing_urls)
            new_count = len(articles_to_scrape)
            print(f"  URLs from RSS: {total_rss_urls}")
            print(f"  Already in DB: {existing_count} (of {len(existing_urls)} total)")
            print(f"  New to scrape: {new_count}")
        else:
            print(f"  URLs from RSS: {total_rss_urls} (none valid)")
    except Exception as e:
        print(f"  [warn] URL filter query failed ({e}), scraping all {total_rss_urls} articles")
        articles_to_scrape = articles_raw

    # Step 4: Scrape full text (parallel), then batch-insert articles
    print(f"\n[4/9] Scraping article text (parallel, 30 workers)...")
    scraped_articles = []

    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = {
            executor.submit(_scrape_single, article_data, source_map): article_data
            for article_data in articles_to_scrape
        }
        for i, future in enumerate(as_completed(futures)):
            if (i + 1) % 50 == 0 or i == 0:
                print(f"  Scraped {i + 1}/{len(articles_to_scrape)}...")
            result = future.result()
            if result:
                scraped_articles.append(result)

    # Resolve source slugs to DB UUIDs and build clean article rows
    # The raw article dicts from _scrape_single have source_id set to the
    # slug string (e.g., "ap-news") or the UUID depending on when db_id was
    # available. We must ensure every article row has the proper UUID before
    # sending to Supabase, and include only columns that exist in the
    # articles table to avoid PostgREST rejecting the payload.
    article_rows = []
    skipped_no_source = 0
    for art in scraped_articles:
        # Resolve source_id to DB UUID using source_slug (always the slug string).
        # The source_slug field was added by _parse_entry and is always the
        # original source "id" from sources.json (e.g., "ap-news").
        # source_id may be the UUID (if db_id was set) or the slug (if not).
        src_slug = art.get("source_slug", "") or art.get("source_id", "")
        src_info = source_map.get(src_slug, {})
        db_source_id = src_info.get("db_id")
        if not db_source_id:
            # source_id might already be a UUID (set by _parse_entry from db_id).
            # Check if any source has this as its db_id.
            raw_source_id = art.get("source_id", "")
            for s in source_map.values():
                if s.get("db_id") == raw_source_id:
                    db_source_id = raw_source_id
                    break
        if not db_source_id:
            skipped_no_source += 1
            continue

        row = {
            "source_id": db_source_id,
            "url": art.get("url", ""),
            "title": art.get("title", "Untitled"),
            "summary": art.get("summary"),
            "full_text": art.get("full_text"),
            "author": art.get("author"),
            "published_at": art.get("published_at"),
            "section": art.get("section", "world"),
            "image_url": art.get("image_url"),
            "word_count": art.get("word_count", 0),
        }
        # Skip rows missing required NOT NULL fields
        if not row["url"] or not row["title"]:
            skipped_no_source += 1
            continue
        # Keep reference to original dict for later enrichment (dedup, analysis)
        art["_row"] = row
        article_rows.append((row, art))

    if skipped_no_source:
        print(f"  Skipped {skipped_no_source} articles (missing source UUID or required fields)")

    # Deduplicate URLs within this batch (RSS feeds can return overlapping entries)
    seen_urls: set[str] = set()
    unique_article_rows: list[tuple[dict, dict]] = []
    for row, art in article_rows:
        url = row["url"]
        if url not in seen_urls:
            seen_urls.add(url)
            unique_article_rows.append((row, art))
    if len(article_rows) != len(unique_article_rows):
        print(f"  Deduplicated within batch: {len(article_rows)} -> {len(unique_article_rows)}")

    # Filter out URLs that already exist in the DB (avoid re-processing
    # articles from previous pipeline runs, which inflated article count
    # from ~596 to 3,436 when using UPSERT)
    existing_urls: set[str] = set()
    all_urls = [row["url"] for row, _ in unique_article_rows]
    for i in range(0, len(all_urls), 500):
        url_chunk = all_urls[i:i + 500]
        try:
            result = supabase.table("articles").select("url").in_("url", url_chunk).execute()
            if result.data:
                for r in result.data:
                    existing_urls.add(r["url"])
        except Exception as e:
            print(f"  [warn] URL existence check failed, proceeding without dedup: {e}")
            existing_urls.clear()
            break

    new_article_rows: list[tuple[dict, dict]] = []
    for row, art in unique_article_rows:
        if row["url"] not in existing_urls:
            new_article_rows.append((row, art))

    if existing_urls:
        print(f"  Filtered existing URLs: {len(unique_article_rows)} -> {len(new_article_rows)} new articles")

    # Batch-insert only NEW articles to Supabase (200 per chunk)
    print(f"  Batch-inserting {len(new_article_rows)} new articles...")
    stored_articles = []
    for i in range(0, len(new_article_rows), 200):
        chunk_pairs = new_article_rows[i:i + 200]
        chunk_rows = [row for row, _ in chunk_pairs]
        try:
            result = supabase.table("articles").insert(chunk_rows).execute()
            if result.data:
                # Map returned IDs back to original article dicts
                url_to_id = {r["url"]: r["id"] for r in result.data if r.get("url")}
                for row, art in chunk_pairs:
                    art_url = row["url"]
                    if art_url in url_to_id:
                        art["id"] = url_to_id[art_url]
                        stored_articles.append(art)
        except Exception as e:
            print(f"  [warn] Batch article insert failed (chunk {i}), falling back: {e}")
            # Fallback: individual inserts for this chunk
            for row, art in chunk_pairs:
                try:
                    result = supabase.table("articles").insert(row).execute()
                    if result.data:
                        art["id"] = result.data[0]["id"]
                        stored_articles.append(art)
                except Exception:
                    pass  # skip duplicates/errors silently

    print(f"  Articles stored: {len(stored_articles)}/{len(new_article_rows)} new ({len(existing_urls)} existing skipped)")

    # Step 4b: Content-based deduplication
    # Removes near-duplicate articles (syndicated/wire content with different URLs)
    # before analysis to avoid wasting compute on duplicate text.
    print(f"\n[4b] Content-based deduplication on {len(stored_articles)} articles...")
    try:
        from clustering.deduplicator import deduplicate_articles

        # Enrich articles with tier info so deduplicator can prefer higher-tier sources
        for art in stored_articles:
            src_slug = art.get("source_slug", "") or art.get("source_id", "")
            src_info = source_map.get(src_slug, {})
            art["tier"] = src_info.get("tier", "")
            art["source_name"] = src_info.get("name", "")

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
        # Step 5: Bias analysis with computed confidence + batch DB insert
        # Parallelised with 4 workers — spaCy releases the GIL during C-extension
        # parsing, so concurrent threads provide real throughput gains.
        # 4 workers balances CPU throughput against memory (each thread holds a
        # full spaCy parse + 5 analyzer passes per article).
        print(f"\n[5/9] Running bias analysis on {len(stored_articles)} articles (8 workers)...")
        bias_rows_to_insert: list[dict] = []
        _analysis_lock = __import__("threading").Lock()
        _analyzed_count = [0]

        # Fix 20 (Axis 6 wire-in): Fetch source_topic_lean EMA data so the
        # political lean analyzer can blend in longitudinal per-source-per-topic
        # baselines. Keyed by (source_id, category). Note: article categories
        # are assigned at step 7, so topic_lean_data will be None for all
        # articles in this run's first pass. The parameter wiring is in place
        # for when categorization is moved earlier in a future refactor.
        topic_lean_map: dict[tuple, dict] = {}
        try:
            topic_lean_result = supabase.table("source_topic_lean").select(
                "source_id,category,avg_lean"
            ).execute()
            for row in (topic_lean_result.data or []):
                key = (row["source_id"], row.get("category", ""))
                topic_lean_map[key] = {"avg_lean": row["avg_lean"]}
        except Exception as _tl_err:
            print(f"    [warn] Could not fetch source_topic_lean: {_tl_err}")

        def _analyze_one(article: dict) -> dict:
            source_slug = article.get("source_slug", "") or article.get("source_id", "")
            source = source_map.get(source_slug, {"political_lean_baseline": "center"})
            # Axis 6: look up topic lean for this article's source + category.
            # Category is not yet assigned at step 5 (assigned at step 7), so
            # this will resolve to None until categorization is moved earlier.
            source_id = source.get("db_id", "")
            category = article.get("category", "")
            topic_lean_data = topic_lean_map.get((source_id, category)) if source_id else None
            bias_scores = run_bias_analysis(article, source, topic_lean_data=topic_lean_data)
            bias_scores["article_id"] = article.get("id", "")
            with _analysis_lock:
                _analyzed_count[0] += 1
                if _analyzed_count[0] % 50 == 0 or _analyzed_count[0] == 1:
                    print(f"  Analyzed {_analyzed_count[0]}/{len(stored_articles)}...")
            return bias_scores

        with ThreadPoolExecutor(max_workers=8) as analysis_executor:
            analysis_futures = {
                analysis_executor.submit(_analyze_one, article): article
                for article in stored_articles
            }
            for future in as_completed(analysis_futures):
                try:
                    bias_scores = future.result()
                    art_id = bias_scores.get("article_id", "")
                    article_bias_map[art_id] = {
                        k: v for k, v in bias_scores.items() if k != "article_id"
                    }
                    bias_rows_to_insert.append(bias_scores)
                except Exception as e:
                    print(f"  [warn] Bias analysis task failed: {e}")

        # Batch-insert bias scores (200 per chunk vs N individual HTTP calls)
        print(f"  Batch-inserting {len(bias_rows_to_insert)} bias score rows...")
        articles_analyzed = _batch_upsert(
            "bias_scores", bias_rows_to_insert, chunk_size=200,
            on_conflict="article_id",
        )
        print(f"  Articles analyzed: {articles_analyzed}/{len(stored_articles)}")

        # Step 6: Cluster articles
        # Include recent articles from the last 36h so stories that span
        # multiple pipeline runs can cluster together (cross-run continuity).
        print(f"\n[6/9] Clustering articles into stories...")
        recent_articles = []
        try:
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=36)).isoformat()
            current_ids = {a.get("id", "") for a in stored_articles}
            recent_res = supabase.table("articles").select(
                "id,title,summary,full_text,source_id,published_at,fetched_at,word_count,section"
            ).gte("published_at", cutoff).limit(1500).execute()
            # Only add articles NOT in the current batch (avoid duplicates)
            # Also enrich with tier/source_name so Gemini prompts can attribute correctly
            db_id_to_source = {s.get("db_id"): s for s in source_map.values() if s.get("db_id")}
            for art in (recent_res.data or []):
                if art["id"] not in current_ids:
                    # Preserve stored section (already computed at scrape time)
                    art["section"] = art.get("section") or "world"
                    # Backfill tier, source_slug, source_name from source_map
                    src_info = db_id_to_source.get(art.get("source_id", ""), {})
                    art["tier"] = src_info.get("tier", "")
                    art["source_slug"] = src_info.get("id", "")
                    art["source_name"] = src_info.get("name", "")
                    recent_articles.append(art)
            print(f"  Current batch: {len(stored_articles)}, 36h lookback: {len(recent_articles)}")
        except Exception as e:
            print(f"  [warn] 36h lookback fetch failed, clustering current batch only: {e}")

        all_articles_for_clustering = stored_articles + recent_articles

        # Separate opinion articles — they should NOT be clustered with reporting.
        # Opinion/op-ed content (opinion_fact > 50) is wrapped as single-article
        # clusters later so each piece stands alone rather than being merged with
        # news coverage of the same topic.
        opinion_article_ids = {
            aid for aid, scores in article_bias_map.items()
            if scores.get("opinion_fact", 0) > 50
        }
        reporting_for_clustering = [
            a for a in all_articles_for_clustering
            if a.get("id", "") not in opinion_article_ids
        ]
        opinion_articles_list = [
            a for a in all_articles_for_clustering
            if a.get("id", "") in opinion_article_ids
        ]
        print(f"  Total for clustering: {len(reporting_for_clustering)} reporting + {len(opinion_articles_list)} opinion (separate)")

        clusters = []
        try:
            clusters = cluster_stories(reporting_for_clustering)
            print(f"  Clusters formed: {len(clusters)}")
        except Exception as e:
            print(f"  [error] Clustering failed: {e}")

        # Step 6 post-process: orphan wrapping.
        # Articles that didn't cluster with any other source get kept as
        # single-article clusters so they appear in the frontend feed.
        # They receive a reduced importance score at ranking time (source_count=1
        # means coverage breadth and tier diversity signals are minimal).
        # Single-article clusters are only excluded for the lead gate (top-10
        # positions require 3+ sources, per the ranker's lead eligibility gate).
        single_source_count = sum(
            1 for c in clusters
            if c.get("source_count", len(c.get("article_ids", []))) < 2
        )
        if single_source_count:
            print(f"  Orphan wrapping: {single_source_count} single-source clusters kept for feed")

        # Wrap opinion articles as single-article clusters (never clustered).
        # Each op-ed stands alone: original title and summary are preserved,
        # Gemini summarization is skipped naturally (source_count=1 < _MIN_SOURCES=3),
        # and content_type="opinion" is pre-set so the classifier below won't
        # overwrite it.
        for art in opinion_articles_list:
            art_id = art.get("id", "")
            if not art_id:
                continue
            opinion_cluster = {
                "title": art.get("title", ""),
                "summary": art.get("summary", "") or art.get("full_text", "")[:500] or "",
                "articles": [art],
                "article_ids": [art_id],
                "source_count": 1,
                "first_published": art.get("published_at"),
                "content_type": "opinion",
                "_is_opinion": True,
            }
            # Include author only when genuinely known
            author = (art.get("author") or "").strip()
            if author and author.lower() not in ("unknown", "n/a", ""):
                opinion_cluster["author"] = author
            # Resolve source name from source_map
            src_slug = art.get("source_slug", "") or art.get("source_id", "")
            src_info = source_map.get(src_slug, {})
            source_name = src_info.get("name", "")
            if source_name:
                opinion_cluster["source_name"] = source_name
            clusters.append(opinion_cluster)

        if opinion_articles_list:
            print(f"  Opinion articles: {len(opinion_articles_list)} wrapped as single-source clusters (no clustering)")

        # Step 6b: Re-run framing analysis with cluster context
        # Framing's omission detection benefits from knowing what other
        # articles in the same cluster mention. Initial analysis (step 5)
        # ran without cluster context. Now re-score framing for multi-article
        # clusters and update the stored bias scores.
        #
        # Performance optimization: pre-compute cluster entity cache once per
        # cluster (instead of re-parsing all articles for each article in the
        # cluster). This reduces spaCy calls from O(N*M) to O(N+M).
        print("\n[6b] Re-scoring framing with cluster context...")
        framing_updated = 0
        framing_update_rows: list[dict] = []  # batch DB updates

        try:
            from utils.nlp_shared import get_nlp
            _nlp = get_nlp()
        except Exception:
            _nlp = None

        for cluster in clusters:
            cluster_articles_list = cluster.get("articles", [])
            if len(cluster_articles_list) < 2:
                continue  # single-article clusters gain nothing

            # Pre-compute per-article entity sets: parse each article ONCE,
            # then build per-article caches that EXCLUDE the article's own
            # entities. This prevents self-inclusion bias in omission scoring
            # where an article is penalised for "omitting" its own entities.
            # (Fix 9: cluster_entity_cache self-inclusion bug)
            all_cluster_entities: set[str] = set()
            per_article_entities: dict[str, set[str]] = {}
            article_docs: dict[str, object] = {}  # art_id -> spaCy doc
            if _nlp is not None:
                for art in cluster_articles_list[:10]:
                    art_text = art.get("full_text", "") or ""
                    art_id = art.get("id", "")
                    if art_text and art_id:
                        doc = _nlp(art_text[:15000])
                        article_docs[art_id] = doc
                        art_ents = {
                            ent.text.lower()
                            for ent in doc.ents
                            if ent.label_ in ("PERSON", "ORG", "GPE")
                        }
                        per_article_entities[art_id] = art_ents
                        all_cluster_entities.update(art_ents)

            for art in cluster_articles_list:
                art_id = art.get("id", "")
                if not art_id:
                    continue
                try:
                    # Build entity cache for this article: all cluster entities
                    # minus this article's own entities (self-exclusion guard)
                    self_ents = per_article_entities.get(art_id, set())
                    cache_without_self = all_cluster_entities - self_ents
                    article_entity_cache = cache_without_self if cache_without_self else None

                    # Reuse pre-computed spaCy doc if available
                    cached_doc = article_docs.get(art_id)
                    result = analyze_framing(
                        art, cluster_articles=cluster_articles_list,
                        doc=cached_doc,
                        cluster_entity_cache=article_entity_cache,
                    )
                    new_framing = result["score"] if isinstance(result, dict) else result
                    new_rationale = result.get("rationale") if isinstance(result, dict) else None

                    # Update in-memory bias map
                    if art_id in article_bias_map:
                        article_bias_map[art_id]["framing"] = new_framing

                    # Build update row for batch
                    update_data: dict = {"article_id": art_id, "framing": new_framing}
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

                    framing_update_rows.append(update_data)
                    framing_updated += 1
                except Exception as e:
                    print(f"    [warn] Framing re-score failed for {art_id}: {e}")

        # Batch-upsert framing updates (instead of one UPDATE per article)
        if framing_update_rows:
            upserted = _batch_upsert(
                "bias_scores", framing_update_rows, chunk_size=200,
                on_conflict="article_id",
            )
            print(f"  Framing re-scored: {framing_updated} articles "
                  f"({upserted} DB rows updated in batches)")
        else:
            print(f"  Framing re-scored: {framing_updated} articles in multi-article clusters")

        # Step 6c: Gemini bias reasoning (contextual score adjustments)
        # Uses a separate call budget (_MAX_REASONING_CALLS = 25) that does
        # not draw from the summarization cap. Prioritises low-confidence,
        # large, and high-divergence clusters. Mutates article_bias_map in
        # place; downstream steps (ranking, storage) pick up the adjustments
        # automatically since they reference the same dict.
        if GEMINI_REASONING_AVAILABLE and gemini_is_available():
            print("\n[6c] Running Gemini bias reasoning...")
            start_6c = time.time()
            try:
                reasoning_results = reason_clusters_batch(
                    clusters, article_bias_map, source_map
                )
                adjusted_count = apply_reasoning_to_bias_map(
                    clusters, article_bias_map, reasoning_results
                )
                elapsed_6c = time.time() - start_6c
                print(
                    f"  Gemini reasoning: {len(reasoning_results)} clusters processed, "
                    f"{adjusted_count} axis-scores adjusted ({elapsed_6c:.1f}s)"
                )
            except Exception as e:
                print(f"  [warn] Gemini reasoning failed: {e}")
        elif GEMINI_REASONING_AVAILABLE:
            print("\n[6c] Skipping Gemini bias reasoning (GEMINI_API_KEY not set)")
        else:
            print("\n[6c] Skipping Gemini bias reasoning (module not available)")

        # Step 7b: Summarize clusters with Gemini Flash
        # Generates polished headlines, summaries, and consensus/divergence.
        # Falls back to rule-based generation (already set by cluster_stories)
        # when Gemini is unavailable or fails for a given cluster.
        gemini_results: dict[int, dict] = {}
        if SUMMARIZER_AVAILABLE and gemini_is_available():
            print("\n[7b] Summarizing clusters with Gemini Flash...")
            try:
                gemini_results = summarize_clusters_batch(clusters)
                for idx, result in gemini_results.items():
                    clusters[idx]["title"] = result["headline"]
                    clusters[idx]["summary"] = result["summary"]
                    clusters[idx]["consensus_points"] = result["consensus"]
                    clusters[idx]["divergence_points"] = result["divergence"]
                    clusters[idx]["_gemini_enriched"] = True
                    # v5.0: editorial intelligence fields
                    if result.get("editorial_importance") is not None:
                        clusters[idx]["editorial_importance"] = result["editorial_importance"]
                    if result.get("story_type") is not None:
                        clusters[idx]["story_type"] = result["story_type"]
                    if result.get("has_binding_consequences") is not None:
                        clusters[idx]["has_binding_consequences"] = result["has_binding_consequences"]
            except Exception as e:
                print(f"  [warn] Gemini summarization failed: {e}")
        elif SUMMARIZER_AVAILABLE:
            print("\n[7b] Skipping Gemini summarization (GEMINI_API_KEY not set)")
        else:
            print("\n[7b] Skipping Gemini summarization (google-generativeai not installed)")

        # Step 7: Categorize and rank with v2 engine
        print("\n[7/9] Categorizing and ranking clusters (v2 engine)...")
        for cluster in clusters:
            cluster_articles_list = cluster.get("articles", [])

            # Categorize — use up to 3 articles for more reliable classification.
            # The old approach used only the first article, which could be a
            # brief wire bulletin that miscategorizes the whole cluster.
            try:
                cat_votes: dict[str, int] = {}
                sample = cluster_articles_list[:3] if cluster_articles_list else []
                all_categories: list[str] = []
                for art in sample:
                    cats = categorize_article(art)
                    for cat in cats:
                        cat_votes[cat] = cat_votes.get(cat, 0) + 1
                    if not all_categories:
                        all_categories = cats
                # Pick the category with the most votes across sampled articles,
                # then map to merged desk slug for display.
                if cat_votes:
                    best_cat = max(cat_votes, key=cat_votes.get)
                    cluster["category"] = map_to_desk(best_cat)
                    if best_cat not in all_categories:
                        all_categories.insert(0, best_cat)
                else:
                    cluster["category"] = "politics"
                    all_categories = ["politics"]
                # Store fine-grained categories for article_categories table
                for art in cluster_articles_list:
                    art_id = art.get("id", "")
                    if art_id:
                        article_categories_map[art_id] = all_categories
            except Exception:
                cluster["category"] = "politics"

            # Gather bias scores for articles in this cluster
            cluster_bias_scores = []
            for art in cluster_articles_list:
                art_id = art.get("id", "")
                if art_id in article_bias_map:
                    cluster_bias_scores.append(article_bias_map[art_id])

            # Classify as reporting vs opinion based on avg opinion score.
            # Skip if already set — opinion articles are pre-classified in step 6
            # (_is_opinion=True) and must not be overwritten here.
            if not cluster.get("_is_opinion"):
                if cluster_bias_scores:
                    avg_opinion = sum(
                        bs.get("opinion_fact", 25) for bs in cluster_bias_scores
                    ) / len(cluster_bias_scores)
                else:
                    avg_opinion = 25.0
                cluster["content_type"] = "opinion" if avg_opinion > 50 else "reporting"

            # Compute cluster confidence: 25th-percentile confidence across
            # articles. Using p25 instead of min() so one bad article doesn't
            # tank an otherwise well-analyzed cluster.
            cluster_confidence = 1.0
            if cluster_bias_scores:
                conf_values = sorted(
                    bs.get("confidence", 0.5) for bs in cluster_bias_scores
                )
                if conf_values:
                    p25_idx = max(0, len(conf_values) // 4)
                    cluster_confidence = conf_values[p25_idx]

            # Rank with v5.1 engine (10 signals + Gemini editorial + gates)
            # Pre-compute sections so the US-only divergence damper and
            # cross-spectrum bonus can be applied correctly at scoring time.
            # (The authoritative sections[] written to DB is computed in step 8;
            # this early read gives the same result since both use article.section.)
            _rank_sections = sorted(
                {a.get("section", "world") for a in cluster_articles_list}
            ) or ["world"]
            try:
                rank_result = rank_importance(
                    cluster_articles_list, sources, cluster_bias_scores,
                    cluster_confidence=cluster_confidence,
                    category=cluster.get("category"),
                    editorial_importance=cluster.get("editorial_importance"),
                    sections=_rank_sections,
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

        # Rank separately within each content_type so opinion #1 doesn't
        # compete with facts #1 for headline_rank position.
        #
        # IMPORTANT: We no longer collapse ranks linearly to 0-100. The old
        # approach mapped position 1 → 100, last position → 0 regardless of
        # raw score, destroying inter-run comparability (a weak news day and
        # a strong news day would both produce a "100" lead story).
        #
        # New approach: sort by raw score, then apply a soft floor so the
        # worst story in a pool never falls below 5, while the top story
        # retains its raw score. This preserves absolute score meaning and
        # allows downstream comparison across runs.
        #
        #   floor = 5.0
        #   rescaled = floor + raw_score * (100 - floor) / 100
        #           = 5 + raw_score * 0.95
        #
        # A raw score of 70 → 71.5 (nearly unchanged at the top).
        # A raw score of 20 → 24.0 (floor lifted slightly).
        # The ordering is preserved; the spread is preserved.
        for ctype in ("reporting", "opinion"):
            pool = [c for c in clusters if c.get("content_type") == ctype]
            pool.sort(
                key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), str(id(c))),
                reverse=True,
            )
            for c in pool:
                raw = max(0.0, min(100.0, c.get("headline_rank", 0)))
                c["headline_rank"] = round(5.0 + raw * 0.95, 2)

        # Story-type gates (v5.0): demote incremental updates and ceremonial stories
        for cluster in clusters:
            st = cluster.get("story_type")
            if st == "incremental_update":
                cluster["headline_rank"] = round(cluster.get("headline_rank", 0) * 0.75, 2)
            elif st == "ceremonial":
                cluster["headline_rank"] = round(cluster.get("headline_rank", 0) * 0.82, 2)

        # v5.2: deterministic sort — tiebreak on source_count (more sources = higher
        # priority), then cluster _db_id or object id as final tiebreaker to ensure
        # identical headline_rank values always sort the same way across runs.
        clusters.sort(
            key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
            reverse=True,
        )

        # Step 7c: Editorial triage (Gemini) — reorder top 10 per section
        # Uses 1 API call per section (3 total). Falls back to deterministic
        # ranking if Gemini is unavailable.
        if SUMMARIZER_AVAILABLE and gemini_is_available():
            try:
                from summarizer.gemini_client import editorial_triage
                print("\n[7c] Running editorial triage (Gemini)...")
                for section_val in ("world", "us", "india"):
                    pool = [c for c in clusters
                            if section_val in (c.get("sections") or [c.get("section", "world")])]
                    pool.sort(
                        key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
                        reverse=True,
                    )
                    top_30 = pool[:30]
                    if len(top_30) < 5:
                        continue

                    # Build candidate list with IDs
                    triage_candidates = []
                    for c in top_30:
                        triage_candidates.append({
                            "id": c.get("_db_id", "") or str(id(c)),
                            "title": c.get("title", ""),
                            "summary": c.get("summary", ""),
                            "source_count": c.get("source_count", 0),
                        })

                    triage_result = editorial_triage(triage_candidates, section_val)
                    if not triage_result:
                        print(f"  [{section_val}] Triage unavailable, using deterministic ranking")
                        continue

                    # Flag incremental updates
                    incr_flags = set(triage_result.get("incremental_flags", []))
                    for cid in incr_flags:
                        for c in top_30:
                            if (c.get("_db_id", "") or str(id(c))) == cid:
                                c["story_type"] = c.get("story_type") or "incremental_update"
                                c["headline_rank"] = round(c.get("headline_rank", 0) * 0.75, 2)
                    if incr_flags:
                        print(f"  [{section_val}] Incremental updates flagged: {len(incr_flags)}")

                    # Log duplicate flags
                    dupe_flags = triage_result.get("duplicate_flags", [])
                    if dupe_flags:
                        print(f"  [{section_val}] Potential duplicate clusters: {dupe_flags[:3]}")

                    applied = len(incr_flags)
                    print(f"  [{section_val}] Editorial triage applied ({applied} stories adjusted)")
            except Exception as e:
                print(f"  [warn] Editorial triage failed, using deterministic ranking: {e}")

        clusters.sort(
            key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
            reverse=True,
        )

        # Same-event cap (v5.1): max 3 stories about the same major event.
        # Without this, 11/20 top stories can be Iran war variants.
        _EVENT_KEYWORDS = {
            "iran": {"iran", "iranian", "tehran", "hormuz", "persian gulf", "irgc", "hegseth"},
            "ukraine": {"ukraine", "ukrainian", "kyiv", "zelenskyy", "zelensky"},
            "israel_palestine": {"gaza", "hamas", "west bank", "netanyahu", "idf"},
            "china_taiwan": {"taiwan", "taipei", "strait", "xi jinping", "pla"},
        }
        MAX_SAME_EVENT = 3

        for section_val in ("world", "us", "india"):
            pool = [c for c in clusters if section_val in (c.get("sections") or [c.get("section", "world")])]
            if len(pool) <= 10:
                continue

            event_counts: dict[str, int] = {}
            event_promoted: list[dict] = []
            event_deferred: list[dict] = []
            for c in pool:
                title_lower = (c.get("title", "") or "").lower()
                event = None
                for ek, kws in _EVENT_KEYWORDS.items():
                    if any(kw in title_lower for kw in kws):
                        event = ek
                        break
                if event and event_counts.get(event, 0) >= MAX_SAME_EVENT:
                    event_deferred.append(c)
                else:
                    event_promoted.append(c)
                    if event:
                        event_counts[event] = event_counts.get(event, 0) + 1
            if event_deferred:
                # Replace pool in-place for this section
                for c in event_deferred:
                    idx = clusters.index(c)
                    # Nudge headline_rank down so it sorts below promoted
                    if event_promoted:
                        floor = event_promoted[-1].get("headline_rank", 0) - 0.1
                        clusters[idx]["headline_rank"] = round(min(c.get("headline_rank", 0), floor), 2)

            clusters.sort(
                key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
                reverse=True,
            )

        # Topic diversity re-ranking: prevent any single category from
        # dominating the top of the feed. Within each section pool (world/us),
        # demote stories that would put >2 of the same category in the top 10.
        for section_val in ("world", "us", "india"):
            pool = [c for c in clusters if section_val in (c.get("sections") or [c.get("section", "world")])]
            if len(pool) <= 10:
                continue
            # v4.0: soft-news desk "culture" (merges culture+sports) gets
            # MAX_SAME_CAT=1 (max 1 slot in top 10). All other desks get 2.
            _SOFT_CATS = {"culture"}
            MAX_SAME_CAT_DEFAULT = 2
            MAX_SAME_CAT_SOFT = 1
            TOP_N = 10
            promoted: list[dict] = []
            deferred: list[dict] = []
            cat_counts: dict[str, int] = {}

            for c in pool:
                if len(promoted) >= TOP_N:
                    deferred.append(c)
                    continue
                cat = c.get("category", "general")
                cat_limit = MAX_SAME_CAT_SOFT if cat in _SOFT_CATS else MAX_SAME_CAT_DEFAULT
                if cat_counts.get(cat, 0) < cat_limit:
                    promoted.append(c)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                else:
                    deferred.append(c)

            # If we couldn't fill TOP_N due to all categories being capped,
            # pull from deferred in original rank order.
            while len(promoted) < TOP_N and deferred:
                promoted.append(deferred.pop(0))

            # Write back headline_rank to reflect diversity-adjusted order.
            # Preserve raw scores but ensure monotonic ordering so DB sort
            # matches our diversity-adjusted order.
            final_order = promoted + deferred
            if final_order and len(promoted) >= 2:
                for j in range(1, len(promoted)):
                    if promoted[j].get("headline_rank", 0) >= promoted[j-1].get("headline_rank", 0):
                        promoted[j]["headline_rank"] = round(
                            promoted[j-1].get("headline_rank", 0) - 0.01, 2
                        )

        # Recency gate for top-10: ensure the front page shows today's news.
        # After topic diversity re-rank, demote any cluster whose most recent
        # article is older than 24h below position 10 within each section pool.
        recency_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        for section_val in ("world", "us", "india"):
            pool = [c for c in clusters if section_val in (c.get("sections") or [c.get("section", "world")])]
            pool.sort(key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0)), reverse=True)

            top_10 = pool[:10]
            demoted = []
            kept = []
            for c in top_10:
                # Determine the most recent article timestamp in this cluster
                cluster_arts = c.get("articles", [])
                most_recent = c.get("first_published", "")
                for art in cluster_arts:
                    pub = art.get("published_at", "")
                    if pub and pub > most_recent:
                        most_recent = pub

                if most_recent and most_recent < recency_cutoff:
                    demoted.append(c)
                else:
                    kept.append(c)

            if demoted:
                floor_rank = pool[10].get("headline_rank", 0) if len(pool) > 10 else 0
                for c in demoted:
                    c["headline_rank"] = round(min(c.get("headline_rank", 0), floor_rank - 0.01), 2)
                print(f"  [{section_val}] Recency gate: demoted {len(demoted)} stale stories from top 10")

        # ── Step 7d: Generate Daily Brief (TL;DR + audio broadcast) ──
        if BRIEFING_AVAILABLE:
            print("\n[7d] Generating Daily Briefs...")
            start_7d = time.time()
            try:
                brief_results = generate_daily_briefs(
                    clusters, source_map,
                    edition_sections=["world"],
                )

                # Determine if this is an audio run (2x/day: morning + evening)
                utc_hour = datetime.now(timezone.utc).hour
                should_generate_audio = True  # TODO: restore time window after testing

                for edition, brief in brief_results.items():
                    brief_row = {
                        "edition": edition,
                        "pipeline_run_id": run_id,
                        "tldr_text": brief["tldr_text"],
                        "audio_script": brief.get("audio_script"),
                        "top_cluster_ids": brief.get("top_cluster_ids", []),
                    }

                    # Generate two-host audio via Gemini Flash TTS
                    if should_generate_audio and brief.get("audio_script"):
                        voices = get_voices_for_today(edition)
                        audio_result = produce_audio(
                            brief["audio_script"], voices, edition,
                        )
                        if audio_result:
                            brief_row["audio_url"] = audio_result["audio_url"]
                            brief_row["audio_duration_seconds"] = audio_result["duration_seconds"]
                            brief_row["audio_file_size"] = audio_result["file_size"]
                            brief_row["audio_voice"] = f"{voices['host_a']['id']}+{voices['host_b']['id']}"
                            brief_row["audio_voice_label"] = "Two voices"

                    try:
                        supabase.table("daily_briefs").upsert(
                            brief_row, on_conflict="edition,pipeline_run_id"
                        ).execute()
                    except Exception as e:
                        print(f"  [warn] Failed to store brief for {edition}: {e}")

                elapsed_7d = time.time() - start_7d
                audio_status = "with audio" if should_generate_audio else "text only"
                print(f"  Daily briefs: {len(brief_results)} editions ({audio_status}, {elapsed_7d:.1f}s)")
            except Exception as e:
                print(f"  [warn] Daily brief generation failed: {e}")
        else:
            print("\n[7d] Skipping daily briefs (modules not installed)")

        # Step 8: Store clusters with enrichment data
        print("\n[8/9] Storing clusters with enrichment data...")
        all_cluster_article_links: list[dict] = []  # batch insert
        cluster_ids_to_enrich: list[str] = []
        gemini_enriched_ids: set[str] = set()  # clusters with Gemini text

        for ci, cluster in enumerate(clusters):
            cluster_articles_list = cluster.get("articles", [])

            # Determine cluster section (edition) from its articles.
            # Strategy: majority vote — whichever edition has the most
            # articles in this cluster determines the cluster's edition.
            # This works fairly across all 3 editions (world/us/india).
            section_counts: dict[str, int] = {}
            for art in cluster_articles_list:
                sec = art.get("section", "world")
                section_counts[sec] = section_counts.get(sec, 0) + 1
            cluster_section = max(section_counts, key=section_counts.get) if section_counts else "world"

            # Multi-section: list ALL editions that have articles in this cluster.
            # This allows cross-listing — e.g., a global Iran war cluster with
            # 3 India-source articles appears in both "world" and "india" feeds.
            all_sections = sorted(section_counts.keys()) if section_counts else ["world"]

            # Use pre-generated summary from clustering or Gemini step
            cluster_summary = cluster.get("summary", "") or ""
            if not cluster_summary and cluster_articles_list:
                first_art = cluster_articles_list[0]
                cluster_summary = (first_art.get("summary", "") or
                                   first_art.get("title", "") or "")

            cluster_row = {
                "title": cluster.get("title", "Developing Story")[:500],
                "summary": cluster_summary,
                "category": cluster.get("category", "politics"),
                "section": cluster_section,
                "sections": all_sections,
                "content_type": cluster.get("content_type", "reporting"),
                "importance_score": round(cluster.get("importance_score", 0.0), 2),
                "source_count": cluster.get("source_count", 0),
                "first_published": cluster.get("first_published") or None,
                "divergence_score": round(cluster.get("divergence_score", 0.0), 2),
                "headline_rank": round(cluster.get("headline_rank", 0.0), 2),
                "coverage_velocity": cluster.get("coverage_velocity", 0),
            }

            # v5.0: editorial intelligence columns (nullable — NULL = no Gemini)
            if cluster.get("editorial_importance") is not None:
                cluster_row["editorial_importance"] = cluster["editorial_importance"]
            if cluster.get("story_type") is not None:
                cluster_row["story_type"] = cluster["story_type"]
            if cluster.get("has_binding_consequences") is not None:
                cluster_row["has_binding_consequences"] = cluster["has_binding_consequences"]

            # Include Gemini-generated consensus/divergence in the initial insert
            has_gemini = cluster.get("_gemini_enriched", False)
            if has_gemini:
                cluster_row["consensus_points"] = cluster.get("consensus_points", [])
                cluster_row["divergence_points"] = cluster.get("divergence_points", [])

            result = insert_cluster(cluster_row)
            if result:
                clusters_created += 1
                cluster_id = result.get("id", "")
                cluster_ids_to_enrich.append(cluster_id)
                if has_gemini:
                    gemini_enriched_ids.add(cluster_id)
                for article_id in cluster.get("article_ids", []):
                    if article_id:
                        all_cluster_article_links.append({
                            "cluster_id": cluster_id,
                            "article_id": article_id,
                        })

        # Batch-insert cluster_articles links (instead of one per article)
        if all_cluster_article_links:
            print(f"  Batch-linking {len(all_cluster_article_links)} article-cluster pairs...")
            _batch_upsert(
                "cluster_articles", all_cluster_article_links, chunk_size=200,
                on_conflict="cluster_id,article_id",
            )

        # Step 8b: Deduplicate clusters — delete old clusters superseded by this run.
        # Each pipeline run re-clusters the last 48h of articles from scratch, so
        # previous runs' clusters covering the same articles are stale duplicates.
        # Strategy: for each new cluster, find older clusters sharing >50% of
        # their articles (Jaccard overlap). Delete the old ones — the new run has
        # fresher summaries, updated bias scores, and any new articles.
        new_cluster_ids = set(cluster_ids_to_enrich)
        if new_cluster_ids:
            print(f"\n[8b] Deduplicating clusters (removing old duplicates)...")
            # Build article→new_cluster map from the links we just inserted
            new_cluster_articles: dict[str, set[str]] = {}
            for link in all_cluster_article_links:
                cid = link["cluster_id"]
                aid = link["article_id"]
                new_cluster_articles.setdefault(cid, set()).add(aid)

            # Collect all article IDs from this run's clusters
            all_new_article_ids = set()
            for aids in new_cluster_articles.values():
                all_new_article_ids.update(aids)

            # Find old clusters that share articles with our new clusters.
            # Query cluster_articles for our article IDs, excluding new cluster IDs.
            old_cluster_articles: dict[str, set[str]] = {}
            all_new_article_list = list(all_new_article_ids)
            for i in range(0, len(all_new_article_list), 500):
                batch = all_new_article_list[i:i + 500]
                try:
                    res = supabase.table("cluster_articles").select(
                        "cluster_id,article_id"
                    ).in_("article_id", batch).execute()
                    if res.data:
                        for row in res.data:
                            cid = row["cluster_id"]
                            if cid not in new_cluster_ids:
                                old_cluster_articles.setdefault(cid, set()).add(
                                    row["article_id"]
                                )
                except Exception as e:
                    print(f"  [warn] dedup query failed: {e}")

            # Any article overlap means the old cluster is superseded by the
            # new run (which re-clusters the same 48h article window with
            # fresher summaries and scores). Delete the old one.
            stale_ids: list[str] = list(old_cluster_articles.keys())

            if stale_ids:
                for i in range(0, len(stale_ids), 100):
                    batch = stale_ids[i:i + 100]
                    try:
                        supabase.table("cluster_articles").delete().in_(
                            "cluster_id", batch
                        ).execute()
                        supabase.table("story_clusters").delete().in_(
                            "id", batch
                        ).execute()
                    except Exception as e:
                        print(f"  [warn] dedup delete failed: {e}")
                print(f"  Deduplicated: removed {len(stale_ids)} old clusters superseded by this run")
            else:
                print(f"  No duplicate clusters found")

        # Enrich clusters with aggregated bias data (Step 9)
        # For Gemini-enriched clusters, only run numeric aggregation (RPC),
        # skip rule-based consensus/divergence text generation.
        # Run enrichment in parallel (8 workers) — each call is an independent
        # Supabase RPC + optional text generation with no shared state.
        # This reduces N*~150ms sequential RPCs to ceil(N/8)*~150ms.
        if cluster_ids_to_enrich:
            print(f"  Enriching {len(cluster_ids_to_enrich)} clusters (parallel, 8 workers)...")
            with ThreadPoolExecutor(max_workers=8) as enrich_executor:
                enrich_futures = {
                    enrich_executor.submit(
                        enrich_cluster,
                        cluster_id,
                        cluster_id in gemini_enriched_ids,
                    ): cluster_id
                    for cluster_id in cluster_ids_to_enrich
                }
                for future in as_completed(enrich_futures):
                    try:
                        future.result()
                    except Exception as enrich_err:
                        cid = enrich_futures[future]
                        print(f"  [warn] Enrichment failed for {cid}: {enrich_err}")

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
                        # Resolve source slug to DB UUID
                        src_slug = ca.get("source_slug", "") or ca.get("source_id", "")
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
    #
    # EXCEPTION: Opinion articles (opinion_fact > 50) keep their full text.
    # Opinion/editorial content is authored commentary — the full text is the
    # value proposition for the Op-Ed page. Cluster summaries also keep full
    # text since they're already short (Gemini 150-250 words or article excerpt).
    print("\n[10] Truncating full_text for IP compliance (skipping opinion articles)...")
    try:
        # Build set of opinion article IDs to preserve
        opinion_article_ids: set[str] = set()
        for art_id, scores in article_bias_map.items():
            if scores.get("opinion_fact", 0) > 50:
                opinion_article_ids.add(art_id)

        truncation_rows: list[dict] = []
        skipped_opinion = 0
        for article in stored_articles:
            art_id = article.get("id", "")
            if art_id:
                if art_id in opinion_article_ids:
                    skipped_opinion += 1
                    continue  # Preserve full text for opinion articles
                full = article.get("full_text", "") or ""
                if len(full) > 300:
                    excerpt = full[:297] + "..."
                    truncation_rows.append({
                        "id": art_id,
                        "full_text": excerpt,
                    })
        if truncation_rows:
            # Batch-update full_text in 200-row chunks (each chunk = 1 HTTP call).
            # Previously used N individual UPDATE calls (one per article), which
            # generated ~3,000 sequential HTTP requests for a typical run.
            # The articles table has a partial unique index on id, so we can use
            # UPDATE ... WHERE id IN (...) chunked via the Supabase Python client.
            # We issue individual UPDATE calls inside a ThreadPoolExecutor so
            # the batching stays compatible with PostgREST's update-by-filter API.
            truncated_count = 0
            failed_count = 0

            def _truncate_chunk(chunk: list[dict]) -> int:
                """Update a batch of articles' full_text, returns count updated."""
                ok = 0
                for row in chunk:
                    try:
                        supabase.table("articles").update(
                            {"full_text": row["full_text"]}
                        ).eq("id", row["id"]).execute()
                        ok += 1
                    except Exception:
                        pass
                return ok

            # Split into 50-row chunks; dispatch 16 workers (each chunk is
            # sequential internally, but chunks run concurrently).
            TRUNC_CHUNK = 50
            chunks = [
                truncation_rows[i:i + TRUNC_CHUNK]
                for i in range(0, len(truncation_rows), TRUNC_CHUNK)
            ]
            with ThreadPoolExecutor(max_workers=16) as trunc_executor:
                trunc_futures = [
                    trunc_executor.submit(_truncate_chunk, chunk)
                    for chunk in chunks
                ]
                for future in as_completed(trunc_futures):
                    try:
                        truncated_count += future.result()
                    except Exception:
                        failed_count += TRUNC_CHUNK

            print(f"  Truncated {truncated_count} articles to 300-char excerpts"
                  + (f" ({failed_count} failed)" if failed_count else "")
                  + f", preserved {skipped_opinion} opinion articles")
        else:
            print("  No articles needed truncation")
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

    # Clean old daily briefs (keep only latest per edition)
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        for ed in ("world", "us", "india"):
            old = supabase.table("daily_briefs").select("id").eq(
                "edition", ed
            ).lt("created_at", cutoff).execute()
            if old.data:
                ids = [b["id"] for b in old.data]
                supabase.table("daily_briefs").delete().in_("id", ids).execute()
                print(f"  Cleaned {len(ids)} old briefs for {ed}")
    except Exception as e:
        print(f"  [warn] Daily brief cleanup failed: {e}")

    # Retention: archive then delete clusters older than 2 days.
    # Articles >36h are rejected at ingestion, so clusters >2d are frozen.
    # Articles + bias_scores persist (not deleted) for historical analysis.
    # Only cluster shells + links are pruned to keep the DB lean.
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        # Paginate to get all old cluster IDs
        old_ids: list[str] = []
        offset = 0
        while True:
            page = supabase.table("story_clusters").select("id").lt(
                "first_published", cutoff
            ).range(offset, offset + 999).execute()
            if not page.data:
                break
            old_ids.extend(c["id"] for c in page.data)
            if len(page.data) < 1000:
                break
            offset += 1000

        if old_ids:
            # Archive: copy key fields to cluster_archive before deletion
            # (preserves Gemini summaries for weekly/monthly trend reports)
            for i in range(0, len(old_ids), 100):
                batch = old_ids[i:i + 100]
                # Fetch full cluster data for archive
                to_archive = supabase.table("story_clusters").select(
                    "id,title,summary,section,sections,category,source_count,"
                    "first_published,headline_rank,divergence_score,bias_diversity,"
                    "consensus_points,divergence_points"
                ).in_("id", batch).execute()
                if to_archive.data:
                    # Upsert into archive table (created by migration 016)
                    try:
                        supabase.table("cluster_archive").upsert(
                            to_archive.data, on_conflict="id"
                        ).execute()
                    except Exception:
                        pass  # Archive table may not exist yet — still delete

                supabase.table("cluster_articles").delete().in_(
                    "cluster_id", batch
                ).execute()
                supabase.table("story_clusters").delete().in_(
                    "id", batch
                ).execute()
            print(f"  Retention: archived + removed {len(old_ids)} clusters older than 2 days")
        else:
            print(f"  Retention: no clusters older than 2 days")
    except Exception as e:
        print(f"  [warn] retention cleanup failed: {e}")

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
