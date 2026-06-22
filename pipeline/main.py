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
    from categorizer.auto_categorize import categorize_article, categorize_early, map_to_desk
    from ranker.importance_ranker import rank_importance, compute_coverage_velocity
    from ranker.feed_ranker import apply_feed_ordering
    ANALYSIS_AVAILABLE = True
except ImportError as e:
    print(f"[warn] Analysis modules not available ({e}). Running fetch-only mode.")

# Gemini summarizer — optional (requires google-generativeai + API key)
SUMMARIZER_AVAILABLE = False
try:
    from summarizer.cluster_summarizer import (
        summarize_clusters_batch,
        summarize_cluster,
        summarize_top50_after_rerank,
        _content_hash,
    )
    from summarizer.cluster_summarizer import is_available as llm_is_available
    from summarizer.cluster_summarizer import calls_remaining
    from summarizer.gemini_client import is_available as gemini_is_available
    from summarizer.gemini_client import get_call_count as gemini_get_call_count
    from summarizer.claude_client import is_available as claude_is_available
    from summarizer.claude_client import get_call_count as claude_get_call_count
    SUMMARIZER_AVAILABLE = True
except ImportError:
    pass

# Cluster image cacher — downloads og:images and re-serves from Supabase Storage
IMAGE_CACHER_AVAILABLE = False
try:
    from media.cluster_image_cacher import cache_cluster_images
    IMAGE_CACHER_AVAILABLE = True
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


# News Memory Engine — optional (tracks top story between runs)
MEMORY_AVAILABLE = False
try:
    from memory.memory_orchestrator import update_memory_after_pipeline_run
    MEMORY_AVAILABLE = True
except ImportError:
    pass

# void --verify: Claim Consensus engine — adhoc only (set VOID_VERIFY=1 to enable)
# Historical claims don't change, so extraction runs on-demand, not every pipeline run.
CLAIMS_AVAILABLE = False
if os.environ.get("VOID_VERIFY", "").strip() in ("1", "true", "yes"):
    try:
        from analyzers.claim_extractor import extract_claims_batch
        from analyzers.claim_verifier import verify_all_clusters
        CLAIMS_AVAILABLE = True
        print("[verify] Claim extraction ENABLED (VOID_VERIFY=1)")
    except ImportError as e:
        print(f"[warn] Claim extraction not available ({e}). Skipping void --verify.")

# void --verify Phase 2: Source track record — adhoc only (same gate)
TRACK_RECORD_AVAILABLE = False
if os.environ.get("VOID_VERIFY", "").strip() in ("1", "true", "yes"):
    try:
        from analyzers.source_track_record import update_source_track_record
        TRACK_RECORD_AVAILABLE = True
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Active editions — controls which editions get briefs, ranking, and DB writes.
# Set to ["world"] to disable regional editions and save API calls.
# Set to None or list all to enable all editions.
# Parking Lot: regional editions (us, europe, south-asia) disabled pre-launch.
# ---------------------------------------------------------------------------
# ACTIVE_EDITIONS is the single source of truth defined in
# pipeline.utils.editions so worker modules (cluster_summarizer Pool 2,
# edition_ranker, etc.) can import it without depending on main.py.
from utils.editions import ACTIVE_EDITIONS, ALL_EDITIONS as _ALL_EDITIONS  # noqa: F401,E402

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
    # South Asia edition — India + Pakistan + Bangladesh + Sri Lanka + Nepal + Afghanistan + Maldives + Bhutan
    "IN": "south-asia", "PK": "south-asia", "BD": "south-asia",
    "LK": "south-asia", "NP": "south-asia", "AF": "south-asia",
    "MV": "south-asia", "BT": "south-asia",
    # Europe edition — UK + EU + EEA + Balkans + Caucasus + Ukraine
    "GB": "europe", "UK": "europe",
    "FR": "europe", "DE": "europe", "ES": "europe", "IT": "europe",
    "NL": "europe", "BE": "europe", "PT": "europe", "AT": "europe",
    "CH": "europe", "IE": "europe", "SE": "europe", "DK": "europe",
    "NO": "europe", "FI": "europe", "IS": "europe",
    "PL": "europe", "CZ": "europe", "RO": "europe", "BG": "europe",
    "HR": "europe", "RS": "europe", "GR": "europe", "HU": "europe",
    "EE": "europe", "LV": "europe", "LT": "europe",
    "UA": "europe", "GE": "europe",
    "TR": "europe", "XK": "europe",  # Turkey (NATO/EU candidate), Kosovo
    "AL": "europe", "BA": "europe", "ME": "europe", "MK": "europe",  # Western Balkans
    "SK": "europe", "SI": "europe", "LU": "europe",  # EU members
    "CY": "europe", "MT": "europe", "MD": "europe",  # EU/candidate states
    # Canada routes to world — no dedicated Canada edition.
    # Previously "CA": "canada" made Canadian stories invisible to all editions.
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
        editions: Optional list of edition slugs to filter by (e.g., ["south-asia"]).
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
        - Word count saturation at 800 (25%)
        - Text availability saturation at 1600 chars (25%)
        - Signal magnitude: continuous distance from defaults (50%)

    Recalibration (2026-05-13): production sample (1,984 articles / 24h) showed
    median confidence stuck at 0.70 — almost no variance.  Two causes:
      1. length_conf and text_conf both saturated at 1.0 for any article > 500
         words / 1000 chars, leaving only signal_conf to vary.
      2. signal_conf used a binary >5 threshold per axis, producing only 6
         discrete values (0..5 deviations).

    Fix: raise saturation points (500→800 words, 1000→1600 chars) so typical
    news copy varies through the 0.50-0.85 band; replace the binary threshold
    with a continuous per-axis distance metric.  Floor lowered 0.30→0.20 so
    weak-signal articles land in the 0.40-0.55 band as intended.
    """
    word_count = article.get("word_count", 0) or 0
    full_text = article.get("full_text", "") or ""

    # Length: 100 words = 0.125, 400 = 0.50, 800+ = 1.0
    length_conf = min(1.0, word_count / 800.0) if word_count > 0 else 0.05

    # Text availability: 200 chars = 0.125, 800 = 0.50, 1600+ = 1.0
    text_conf = min(1.0, max(0.05, len(full_text) / 1600.0)) if full_text else 0.05

    # Signal magnitude: continuous per-axis distance from defaults.
    defaults = {
        "political_lean": 50, "sensationalism": 10,
        "opinion_fact": 25, "factual_rigor": 50, "framing": 15,
    }
    total_distance = 0.0
    for key, default_val in defaults.items():
        actual = scores.get(key, default_val)
        # Per-axis contribution clamped at 25-point deviation.
        per_axis = min(1.0, abs(actual - default_val) / 25.0)
        total_distance += per_axis
    # 0 axes off-default = 0.20 (floor); all 5 maxed = 1.0.
    signal_conf = 0.20 + (total_distance / 5.0) * 0.80

    confidence = (length_conf * 0.25) + (text_conf * 0.25) + (signal_conf * 0.50)
    return round(max(0.05, min(1.0, confidence)), 2)


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

    # v6.0.1: Word-count gate — articles with < 150 words of text are
    # scrape failures (stubs, paywalls, redirects). Scoring them produces
    # garbage (3/5 axes compress to floor). Return baseline scores with
    # low confidence so they get minimal weight in cluster aggregation.
    full_text_raw = article.get("full_text", "") or ""
    word_count = len(full_text_raw.split())
    if word_count < 150:
        # Use source baseline for political_lean if available
        baseline = str(source.get("political_lean_baseline", "center")).lower()
        lean_map = {"far-left": 15, "left": 25, "center-left": 38,
                    "center": 50, "center-right": 62, "right": 75,
                    "far-right": 85, "varies": 50}
        scores["political_lean"] = lean_map.get(baseline, 50)
        scores["confidence"] = max(0.15, word_count / 500.0)
        return scores

    # Pre-parse spaCy doc once and share across analyzers that need NER.
    # Saves 2 redundant parses per article (~200-400ms each).
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    combined = f"{title} {full_text}"
    doc = None
    if combined.strip():
        try:
            from utils.nlp_shared import get_nlp
            nlp = get_nlp()
            doc = nlp(combined[:15000])
        except Exception:
            pass  # analyzers fall back to their own parsing

    try:
        result = analyze_political_lean(article, source, topic_lean_data=topic_lean_data, doc=doc)
        if isinstance(result, dict):
            scores["political_lean"] = result["score"]
            rationale["lean"] = result["rationale"]
        else:
            scores["political_lean"] = result
    except Exception as e:
        print(f"    [warn] Political lean failed: {e}")

    try:
        result = analyze_sensationalism(article, source)
        if isinstance(result, dict):
            scores["sensationalism"] = result["score"]
            rationale["sensationalism"] = result["rationale"]
        else:
            scores["sensationalism"] = result
    except Exception as e:
        print(f"    [warn] Sensationalism failed: {e}")

    try:
        result = analyze_opinion(article, source)
        if isinstance(result, dict):
            scores["opinion_fact"] = result["score"]
            rationale["opinion"] = result["rationale"]
        else:
            scores["opinion_fact"] = result
    except Exception as e:
        print(f"    [warn] Opinion detection failed: {e}")

    try:
        result = analyze_factual_rigor(article, source, doc=doc)
        if isinstance(result, dict):
            scores["factual_rigor"] = result["score"]
            rationale["coverage"] = result["rationale"]
        else:
            scores["factual_rigor"] = result
    except Exception as e:
        print(f"    [warn] Factual rigor failed: {e}")

    try:
        result = analyze_framing(article, cluster_articles=cluster_articles, doc=doc, source=source)
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

        # ── Polarization / contestedness ──────────────────────────────────
        # The rigor-weighted MEAN hides bimodal coverage: a story carried by
        # far-left AND far-right sources averages to ~50 and looks "balanced"
        # when it is in fact highly contested. Compute an explicit per-bucket
        # histogram + a polarization index so the frontend can reveal the
        # split the mean conceals (Layer 2). Buckets match biasColors.ts
        # leanToBucket boundaries so the UI and pipeline agree.
        lean_buckets = {
            "far_left": sum(1 for v in pl_values if v <= 20),
            "left": sum(1 for v in pl_values if 20 < v <= 35),
            "center_left": sum(1 for v in pl_values if 35 < v <= 45),
            "center": sum(1 for v in pl_values if 45 < v <= 55),
            "center_right": sum(1 for v in pl_values if 55 < v <= 65),
            "right": sum(1 for v in pl_values if 65 < v <= 80),
            "far_right": sum(1 for v in pl_values if v > 80),
        }
        # 3-segment collapse for the at-a-glance coverage bar.
        lean_left_count = lean_buckets["far_left"] + lean_buckets["left"] + lean_buckets["center_left"]
        lean_center_count = lean_buckets["center"]
        lean_right_count = lean_buckets["center_right"] + lean_buckets["right"] + lean_buckets["far_right"]
        # Polarization: 0 when one-sided / all-center, 100 when a perfect L/R
        # split. minority = the smaller wing; both wings large ⇒ contested.
        polarization = round(100.0 * (2.0 * min(lean_left_count, lean_right_count) / count)) if count else 0

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
            "lean_buckets": lean_buckets,
            "lean_left_count": lean_left_count,
            "lean_center_count": lean_center_count,
            "lean_right_count": lean_right_count,
            "polarization": polarization,
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

    title = article_data.get("title", "") or ""
    rss_summary = article_data.get("summary", "") or ""

    try:
        # Pass title + RSS summary to scraper for quality gates and fallback.
        # The scraper uses title for echo detection (redirect captures) and
        # rss_summary as Tier 3 fallback when scrape produces garbage.
        scraped = scrape_article(url, title=title, rss_summary=rss_summary)
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

    # Final RSS summary fallback: if scraper still got no text (e.g., exception
    # path above), use the RSS summary. A 100-word summary is far better than
    # empty for NLP analysis.
    if not article_data.get("full_text"):
        if rss_summary and len(rss_summary) > 50:
            article_data["full_text"] = f"{title}\n\n{rss_summary}" if title else rss_summary
            article_data["word_count"] = len(article_data["full_text"].split())

    # Section is always "world" (2026-06-02 collapse-editions).
    # The field is kept on the row for defensive frontend / downstream
    # consumers that still filter by section / sections @> ['world'].
    article_data["section"] = "world"

    return article_data


class _ReclusterSkip(Exception):
    """Internal control-flow marker used by --recluster-only fast path.

    Raised from inside try-blocks that wrap fetch/scrape/filter logic so
    the existing except handlers can no-op cleanly when articles came
    from the DB pre-load instead of from RSS.
    """
    pass


def main():
    """Run the full news ingestion + analysis pipeline."""
    import argparse
    parser = argparse.ArgumentParser(description="void --news pipeline")
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="Run only the rule-based engine stage (fetch, cluster, bias, "
             "categorize, rank, rerank). Skip every LLM-bearing editorial "
             "step (cluster summarization, daily brief, weekly digest, "
             "Instagram captions). $0 fresh-run mode for engine testing.",
    )
    parser.add_argument(
        "--recluster-only",
        action="store_true",
        help="Skip fetch + scrape + bias (which already ran). Load existing "
             "articles + bias_scores from DB, then run THE SAME clustering, "
             "ranking, rerank, persist code paths as a fresh production run. "
             "5-10 minutes vs 25-35 for a full pipeline. Use this when a "
             "code change to clustering/ranking needs to take effect today "
             "without re-fetching the corpus. Implies --engine-only.",
    )
    parser.add_argument(
        "--recluster-window-hours",
        type=int,
        default=48,
        help="Article freshness window when --recluster-only is set. Default 48h.",
    )
    args = parser.parse_args()

    editions = None  # 2026-06-02 single-feed — `editions` filter removed; load_sources call sites keep arg for back-compat.
    recluster_only = bool(getattr(args, "recluster_only", False))
    # --recluster-only implies --engine-only (no LLM, no fetch)
    engine_only = bool(getattr(args, "engine_only", False)) or recluster_only
    if engine_only:
        # Hard-disable every LLM call site for this process. The DISABLE_*
        # vars are read by claude_client.is_available(),
        # gemini_client.is_available(), gemini_reasoning, editorial
        # triage, and audio. --engine-only is the umbrella. 2026-05-24
        # added DISABLE_GEMINI for the cluster_summarizer + daily_brief
        # Gemini Flash fallback paths.
        import os as _os
        _os.environ["DISABLE_ANTHROPIC"] = "1"
        _os.environ["DISABLE_GEMINI"] = "1"
        _os.environ["DISABLE_GEMINI_REASONING"] = "1"
        _os.environ["DISABLE_EDITORIAL_TRIAGE"] = "1"
        _os.environ["DISABLE_AUDIO"] = "1"
        print("  [engine-only] All LLM call sites disabled for this run "
              "(DISABLE_ANTHROPIC + DISABLE_GEMINI + reasoning + triage + audio).")
    if recluster_only:
        print(f"  [recluster-only] Skipping fetch/scrape/bias. "
              f"Reusing existing articles in last {args.recluster_window_hours}h.")

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
            # Health columns (migration 051) — used by rss_fetcher to skip
            # sources past the dead-feed quarantine threshold. Silent on
            # missing column (older environments without migration 051).
            slug_to_cff = {
                r["slug"]: (r.get("consecutive_fetch_failures") or 0)
                for r in result.data
            }
            for s in sources:
                slug = s.get("id", "")
                if slug in slug_to_uuid:
                    s["db_id"] = slug_to_uuid[slug]
                if slug in slug_to_cff:
                    s["consecutive_fetch_failures"] = slug_to_cff[slug]
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

    # 2026-05-24 — --recluster-only fast path. Skip fetch + scrape + bias
    # by loading existing articles and bias_scores from the DB. Pipeline
    # continues into step 6 (clustering) with the SAME data structures as
    # a fresh run, so no parallel rerank flow exists to drift from production.
    stored_articles: list[dict] = []
    article_bias_map: dict[str, dict] = {}
    articles_to_scrape: list[dict] = []
    fetch_errors: list = []
    if recluster_only:
        print(f"\n[recluster] Loading articles + bias_scores from DB "
              f"(window: last {args.recluster_window_hours}h)...")
        cutoff_iso = (
            datetime.now(timezone.utc) - timedelta(hours=args.recluster_window_hours)
        ).isoformat()
        # Pull articles WITH PAGINATION — Supabase REST defaults to 1000 rows
        # per request and silently truncates. Today's 48h window has 6,800+
        # articles; without pagination, ~5,800 articles never enter
        # clustering (the orphan bug observed 2026-05-24 recluster).
        _PAGE = 1000
        _offset = 0
        try:
            while True:
                arts_resp = supabase.table("articles").select(
                    "id,source_id,url,title,summary,full_text,author,published_at,"
                    "section,word_count,is_wire_copy,wire_origin_publisher_id"
                ).gte("published_at", cutoff_iso).order(
                    "published_at", desc=True
                ).range(_offset, _offset + _PAGE - 1).execute()
                page = arts_resp.data or []
                if not page:
                    break
                stored_articles.extend(page)
                if len(page) < _PAGE:
                    break
                _offset += _PAGE
                if _offset > 50000:  # safety cap; should never hit in practice
                    print(f"  [warn] preload halted at {len(stored_articles)} articles (cap)")
                    break
        except Exception as _arts_err:
            print(f"  [error] failed to load articles for recluster: {_arts_err}")
        # Attach source_slug + section fallback so analyzers downstream behave
        # as if these came from the live fetcher.
        _src_by_id = {s.get("db_id"): s for s in sources if s.get("db_id")}
        for art in stored_articles:
            src = _src_by_id.get(art.get("source_id"))
            if src:
                art["source_slug"] = src.get("slug", "")
                if not art.get("section"):
                    art["section"] = src.get("section", "world")
        # Pull bias_scores in chunks (URL length limit on IN clause)
        article_ids = [a["id"] for a in stored_articles if a.get("id")]
        bias_chunk = 200
        for i in range(0, len(article_ids), bias_chunk):
            ids_slice = article_ids[i:i + bias_chunk]
            try:
                bs_resp = supabase.table("bias_scores").select("*").in_(
                    "article_id", ids_slice
                ).execute()
                for row in (bs_resp.data or []):
                    art_id = row.pop("article_id", None)
                    if art_id:
                        # Drop DB-only fields that aren't in production map
                        row.pop("id", None)
                        row.pop("created_at", None)
                        row.pop("updated_at", None)
                        article_bias_map[art_id] = row
            except Exception as _bs_err:
                print(f"  [warn] bias_scores chunk {i} failed: {_bs_err}")
        print(f"  Pre-loaded {len(stored_articles)} articles, "
              f"{len(article_bias_map)} bias score rows.")
        # Also: nuke prior clusters so the new run replaces them cleanly.
        # cluster_articles cascade-deletes via FK (verified in Q32 today).
        # 2026-05-24 production diagnostic: today's clusters are full of
        # false-merges from the publisher-name bridge + ratio-blind cap.
        # Replacing them with a fresh recluster is the whole point of this run.
        try:
            print("  Wiping prior clusters before re-cluster...")
            _del_resp = supabase.table("story_clusters").delete().gte(
                "first_published", cutoff_iso
            ).execute()
            print(f"  Deleted {len(_del_resp.data or [])} prior clusters in window.")
        except Exception as _del_err:
            print(f"  [warn] prior cluster wipe failed: {_del_err}")

    # Step 3: Fetch articles via RSS  [skipped if --recluster-only]
    if recluster_only:
        print("\n[3/9] Fetching RSS feeds... SKIPPED (--recluster-only)")
        articles_raw = []
    else:
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
    if recluster_only:
        articles_to_scrape = []
        print("  [recluster-only] skipped.")

    try:
        if recluster_only:
            raise _ReclusterSkip()
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
    except _ReclusterSkip:
        pass  # --recluster-only fast-path: no URL filtering needed.
    except Exception as e:
        print(f"  [warn] URL filter query failed ({e}), scraping all {total_rss_urls} articles")
        articles_to_scrape = articles_raw

    # Step 4: Scrape full text (parallel), then batch-insert articles
    scraped_articles = []
    if recluster_only:
        print(f"\n[4/9] Scraping article text... SKIPPED (--recluster-only)")
    else:
        print(f"\n[4/9] Scraping article text (parallel, 30 workers)...")

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
    # 2026-05-28 — `stored_articles = []` and the insert loop are SKIPPED on
    # --recluster-only. Without this guard, the reset wipes the DB preload
    # populated at lines 1100-1116, causing every recluster run to process
    # zero articles (clustering on empty input → 0 stories).
    if not recluster_only:
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

    if not recluster_only:
        print(f"  Articles stored: {len(stored_articles)}/{len(new_article_rows)} new ({len(existing_urls)} existing skipped)")

    # Step 4b: Wire-aware fingerprinting (Phase 0)
    # Tags syndicated wire copies in place so downstream clustering can
    # collapse them to a single "voice" for source_count math. Articles
    # are NOT removed; the list returned is the same length as the input.
    print(f"\n[4b] Wire-aware fingerprinting on {len(stored_articles)} articles...")
    try:
        from clustering.deduplicator import deduplicate_articles

        # Enrich articles with tier info so the wire-origin picker can
        # prefer canonical wire sources (tier == "wire") when assigning
        # the wire_origin_publisher_id.
        for art in stored_articles:
            src_slug = art.get("source_slug", "") or art.get("source_id", "")
            src_info = source_map.get(src_slug, {})
            art["tier"] = src_info.get("tier", "")
            art["source_name"] = src_info.get("name", "")

        deduplicate_articles(stored_articles)
        wire_copies = sum(1 for a in stored_articles if a.get("is_wire_copy"))
        wire_groups = len({
            a.get("wire_group_id") for a in stored_articles
            if a.get("wire_group_id")
        })
        print(
            f"  Wire fingerprint: {wire_copies} wire copies tagged across "
            f"{wire_groups} syndicate group(s); "
            f"{len(stored_articles)} articles preserved."
        )

        # 2026-05-26 — persist wire flags back to DB. Without this, the
        # in-memory mutations from deduplicate_articles() are lost the
        # moment the pipeline exits: clusters built from the in-memory
        # tags work, but the next recluster preloads from DB where every
        # article shows is_wire_copy=false. Confirmed: zero
        # is_wire_copy=true rows for May 22-26 (4 days of silent
        # persistence failure). Wire-aware source-count collapse has
        # been non-functional across the entire iteration cycle.
        if wire_copies > 0:
            wire_updates = [
                {
                    "id": a["id"],
                    "is_wire_copy": True,
                    "wire_origin_publisher_id": a.get("wire_origin_publisher_id"),
                }
                for a in stored_articles
                if a.get("is_wire_copy") and a.get("id")
            ]
            _wire_updated = 0
            _wire_errors = 0
            for u in wire_updates:
                rid = u.pop("id")
                try:
                    supabase.table("articles").update(u).eq("id", rid).execute()
                    _wire_updated += 1
                except Exception as _wu_err:
                    _wire_errors += 1
                    if _wire_errors <= 3:
                        print(f"  [warn] wire-flag update failed for {rid[:8]}: {_wu_err}")
                u["id"] = rid
            print(
                f"  Wire flags persisted to DB: {_wire_updated} updated, "
                f"{_wire_errors} errors."
            )
    except ImportError:
        print("  [skip] Wire-fingerprint module unavailable (sklearn not installed)")
    except Exception as e:
        print(f"  [warn] Wire-fingerprint pass failed, continuing untagged: {e}")

    # Step 5: Run bias analysis on each article
    articles_analyzed = 0
    clusters_created = 0
    # Collect per-article bias scores keyed by article_id for ranking.
    # 2026-05-24 — preserve preloaded map when --recluster-only is set.
    if not recluster_only:
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
        # 2026-05-24 — when --recluster-only is set, skip the analysis (the
        # article_bias_map was preloaded from DB at the top of main()) and
        # proceed directly into step 6 clustering with the existing scores.
        bias_rows_to_insert: list[dict] = []
        if recluster_only:
            print(f"\n[5/9] Bias analysis SKIPPED (--recluster-only) — "
                  f"using {len(article_bias_map)} preloaded score rows.")
        else:
            print(f"\n[5/9] Running bias analysis on {len(stored_articles)} articles (8 workers)...")
        # 2026-05-24 — recluster-only fast path: bias analysis body is
        # bypassed via a single-iteration loop guarded by recluster_only.
        # `break` jumps past the body without re-indenting the existing
        # ~70 lines of code. Equivalent to "if not recluster_only: ...".
        for _ in range(1):
            if recluster_only:
                articles_analyzed = len(article_bias_map)
                break
            _analysis_lock = __import__("threading").Lock()
            _analyzed_count = [0]

            # Fix 20 (Axis 6 wire-in): Fetch source_topic_lean EMA data so the
            # political lean analyzer can blend in longitudinal per-source-per-topic
            # baselines. Keyed by (source_id, category).
            #
            # 2026-05-21 — Axis 6 was wired but DORMANT for the entire production
            # lifetime: article["category"] was empty at step 5 because the full
            # categorizer runs at step 7. Now categorize_early() (URL+section
            # regex, ~5µs) assigns a best-guess category before bias analysis,
            # populating topic_lean_data for the ~60-70% of articles whose URL
            # path or section metadata is unambiguous. The remaining articles
            # match the prior None behavior. Step 7 still runs the full NLP
            # categorizer to refine and store the final cluster category.
            topic_lean_map: dict[tuple, dict] = {}
            try:
                # Paginated: 1,016 sources x N categories exceeds PostgREST's
                # 1,000-row response cap, which silently truncates a bare
                # select and starves the Axis-6 EMA of most of its rows.
                _tl_PAGE = 1000
                _tl_offset = 0
                while True:
                    topic_lean_result = supabase.table("source_topic_lean").select(
                        "source_id,category,avg_lean"
                    ).range(_tl_offset, _tl_offset + _tl_PAGE - 1).execute()
                    _tl_rows = topic_lean_result.data or []
                    for row in _tl_rows:
                        key = (row["source_id"], row.get("category", ""))
                        topic_lean_map[key] = {"avg_lean": row["avg_lean"]}
                    if len(_tl_rows) < _tl_PAGE:
                        break
                    _tl_offset += _tl_PAGE
            except Exception as _tl_err:
                print(f"    [warn] Could not fetch source_topic_lean: {_tl_err}")

            def _analyze_one(article: dict) -> dict:
                source_slug = article.get("source_slug", "") or article.get("source_id", "")
                source = source_map.get(source_slug, {"political_lean_baseline": "center"})
                # Axis 6: look up topic lean for this article's source + category.
                # Early-categorize via URL+section; stash on the article so step 7
                # can use it as a hint (or override with full NLP categorization).
                source_id = source.get("db_id", "")
                category = article.get("category") or categorize_early(article)
                if category:
                    article["category"] = category  # persist for step 7
                topic_lean_data = topic_lean_map.get((source_id, category)) if source_id and category else None
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
            # 2026-05-24 — paginate 36h lookback (was capped at 1500;
            # under-loaded the corpus for clustering on busy days).
            _recent_PAGE = 1000
            _recent_offset = 0
            _recent_collected: list[dict] = []
            while True:
                recent_res = supabase.table("articles").select(
                    "id,title,summary,full_text,source_id,published_at,fetched_at,word_count,section,"
                    "is_wire_copy,wire_origin_publisher_id"
                ).gte("published_at", cutoff).order(
                    "published_at", desc=True
                ).range(_recent_offset, _recent_offset + _recent_PAGE - 1).execute()
                _page = recent_res.data or []
                if not _page:
                    break
                _recent_collected.extend(_page)
                if len(_page) < _recent_PAGE:
                    break
                _recent_offset += _recent_PAGE
                if _recent_offset > 20000:
                    break
            # Build a shim object with .data for backward compatibility below.
            class _R: pass
            recent_res = _R()
            recent_res.data = _recent_collected
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
        # 2026-05-24 iter 7 — garbage-title + tiny-body filter.
        # The scraper sometimes returns login walls / subscribe redirects /
        # paywall stubs whose .title field looks like "- subscribe.foo.com",
        # "- links.bar.com", or just the bare domain. These cluster together
        # by accident (no real content overlap) and the title generator
        # picks a misleading representative. Observed today: a 26-source
        # "Novinite.com - Sofia News Agency" cluster of 15 garbage-title
        # login pages from Wilmington Star, Inc. Magazine, Morning Brew etc.
        #
        # Drop article when ANY of:
        #   - title is empty / starts with "- " / is just the domain
        #   - title is < 12 chars and word_count < 80
        #   - title contains 'subscribe.', 'login.', 'paywall', 'access.'
        import re as _re_garbage
        _GARBAGE_TITLE_RE = _re_garbage.compile(
            r"^\s*(?:[-_]\s*)?(?:https?://)?[a-z0-9.-]+\.(?:com|net|org|io|co|me|uk)\b",
            _re_garbage.IGNORECASE,
        )
        _GARBAGE_URL_TOKENS = ("subscribe.", "login.", "/paywall", "access.",
                               "/sso/", "/auth/", "?return=", "links.morningbrew.")
        def _is_garbage_article(a: dict) -> bool:
            t = (a.get("title") or "").strip()
            wc = int(a.get("word_count") or 0)
            url = (a.get("url") or "").lower()
            if not t or len(t) < 6:
                return True
            if _GARBAGE_TITLE_RE.match(t):
                return True
            if any(tok in url for tok in _GARBAGE_URL_TOKENS):
                return True
            # short title + tiny body = almost certainly a stub
            if len(t) < 18 and wc < 80:
                return True
            return False
        _pre_garbage_filter = len(all_articles_for_clustering)
        all_articles_for_clustering = [
            a for a in all_articles_for_clustering if not _is_garbage_article(a)
        ]
        _dropped = _pre_garbage_filter - len(all_articles_for_clustering)
        if _dropped:
            print(f"  Garbage-title filter: dropped {_dropped} login/stub articles "
                  f"({len(all_articles_for_clustering)} remain for clustering).")

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
            clusters = cluster_stories(reporting_for_clustering, source_map=source_map)
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
        #
        # An article is an orphan if it was passed into clustering but did not
        # appear in any returned cluster. Causes: empty TF-IDF document
        # (handled in story_cluster.py), AgglomerativeClustering edge cases,
        # or a cluster_stories exception. Wrapping orphans here is the
        # backstop that guarantees every reporting article reaches the
        # frontend feed instead of becoming a database orphan with no
        # cluster_articles row.
        clustered_ids: set = set()
        for c in clusters:
            for aid in c.get("article_ids", []) or []:
                if aid:
                    clustered_ids.add(aid)
        orphans = [
            a for a in reporting_for_clustering
            if a.get("id") and a["id"] not in clustered_ids
        ]
        for a in orphans:
            article_id = a.get("id", "")
            source_id = a.get("source_id", "")
            singleton = {
                "title": a.get("title") or "Developing Story",
                "summary": a.get("summary", "") or (a.get("full_text", "") or "")[:500],
                "article_ids": [article_id],
                "source_ids": [source_id] if source_id else [],
                "source_count": 1 if source_id else 0,
                "section": a.get("section") or "world",
                "first_published": a.get("published_at", "") or "",
                "articles": [a],
            }
            clusters.append(singleton)
        if orphans:
            print(f"  Wrapped {len(orphans)} orphan articles into singleton clusters")

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

                    # Build update row for batch — include ALL bias axes so the
                    # upsert does not null-out columns that aren't in the dict.
                    # (Fix F7: partial upsert was setting 4/5 axes to NULL)
                    existing = article_bias_map.get(art_id, {})
                    update_data: dict = {
                        "article_id": art_id,
                        "political_lean": existing.get("political_lean", 50),
                        "sensationalism": existing.get("sensationalism", 10),
                        "opinion_fact": existing.get("opinion_fact", 25),
                        "factual_rigor": existing.get("factual_rigor", 50),
                        "framing": new_framing,
                        "confidence": existing.get("confidence", 0.7),
                    }
                    # Merge new framing rationale into existing rationale
                    if new_rationale:
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

        # Step 6a: Extract claims (void --verify)
        # Uses spaCy dependency parsing to extract factual claims (SVO triples
        # anchored by named entities or quantitative data patterns).
        all_article_claims: dict[str, list] = {}
        cluster_consensus: dict[str, object] = {}
        if CLAIMS_AVAILABLE and clusters:
            print("\n[6a] Extracting claims (void --verify)...")
            start_6a = time.time()
            try:
                all_article_claims = extract_claims_batch(stored_articles)
                elapsed_6a = time.time() - start_6a
                total_claims = sum(len(v) for v in all_article_claims.values())
                print(f"  Claims: {total_claims} from {len(all_article_claims)} articles ({elapsed_6a:.1f}s)")
            except Exception as e:
                print(f"  [warn] Claim extraction failed: {e}")

            # Step 6a-ii: Verify claims across sources
            # Groups claims by cluster, then uses TF-IDF cosine similarity
            # to find corroborated, single-source, and disputed claims.
            if all_article_claims:
                print("\n[6a-ii] Verifying claims across sources...")
                start_6a2 = time.time()
                try:
                    # Build article_id -> cluster_index mapping
                    article_to_cluster: dict[str, int] = {}
                    for ci, cluster in enumerate(clusters):
                        for art_id in cluster.get("article_ids", []):
                            article_to_cluster[art_id] = ci

                    # Group claims by cluster index
                    claims_by_cluster: dict[str, dict[str, list]] = {}
                    for art_id, claims in all_article_claims.items():
                        ci = article_to_cluster.get(art_id)
                        if ci is not None:
                            ckey = str(ci)
                            claims_by_cluster.setdefault(ckey, {})[art_id] = claims

                    # Build source name lookup
                    source_name_map = {
                        s.get("id", ""): s.get("name", "")
                        for s in source_map.values()
                    }

                    cluster_consensus = verify_all_clusters(
                        claims_by_cluster, source_info=source_name_map
                    )
                    elapsed_6a2 = time.time() - start_6a2
                    total_corr = sum(c.corroborated for c in cluster_consensus.values())
                    total_disp = sum(c.disputed for c in cluster_consensus.values())
                    print(f"  Verified {len(cluster_consensus)} clusters: "
                          f"{total_corr} corroborated, {total_disp} disputed ({elapsed_6a2:.1f}s)")
                except Exception as e:
                    print(f"  [warn] Claim verification failed: {e}")
        elif CLAIMS_AVAILABLE:
            print("\n[6a] Skipping claim extraction (no clusters)")
        else:
            print("\n[6a] Skipping claim extraction (modules not available)")

        # Step 6c: Gemini bias reasoning (contextual score adjustments)
        # Uses a separate call budget (_MAX_REASONING_CALLS = 25) that does
        # not draw from the summarization cap. Prioritises low-confidence,
        # large, and high-divergence clusters. Mutates article_bias_map in
        # place; downstream steps (ranking, storage) pick up the adjustments
        # automatically since they reference the same dict.
        _skip_reasoning = os.environ.get("DISABLE_GEMINI_REASONING", "").strip() in ("1", "true", "yes")
        if GEMINI_REASONING_AVAILABLE and gemini_is_available() and not _skip_reasoning:
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
        elif _skip_reasoning:
            print("\n[6c] Skipping Gemini bias reasoning (DISABLE_GEMINI_REASONING=1)")
        elif GEMINI_REASONING_AVAILABLE:
            print("\n[6c] Skipping Gemini bias reasoning (GEMINI_API_KEY not set)")
        else:
            print("\n[6c] Skipping Gemini bias reasoning (module not available)")

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

            # 2026-06-02 single-feed — sections is always ["world"].
            _rank_sections = ["world"]
            cluster["sections"] = _rank_sections
            cluster["section"] = "world"
            try:
                rank_result = rank_importance(
                    cluster_articles_list, sources, cluster_bias_scores,
                    cluster_confidence=cluster_confidence,
                    category=cluster.get("category"),
                    editorial_importance=cluster.get("editorial_importance"),
                    sections=_rank_sections,
                    mega_capped=bool(cluster.get("mega_cluster_capped", False)),
                    corpus_size=len(stored_articles),  # 2026-05-25 adaptive is_headline
                    cluster=cluster,  # 2026-05-24 v2 — pass cluster so ranker
                                      # can read _cohesion stashed by Phase 5
                )
                cluster["importance_score"] = rank_result["importance_score"]
                cluster["divergence_score"] = rank_result["divergence_score"]
                cluster["coverage_velocity"] = rank_result["coverage_velocity"]
                cluster["headline_rank"] = rank_result["headline_rank"]
                cluster["is_headline"] = bool(rank_result.get("is_headline", False))
                cluster["headline_confidence"] = int(rank_result.get("headline_confidence", 0))
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
        _skip_triage = os.environ.get("DISABLE_EDITORIAL_TRIAGE", "").strip() in ("1", "true", "yes")
        if _skip_triage:
            print("\n[7c] Skipping editorial triage (DISABLE_EDITORIAL_TRIAGE=1)")
        elif SUMMARIZER_AVAILABLE and gemini_is_available():
            try:
                from summarizer.gemini_client import editorial_triage
                print("\n[7c] Running editorial triage (Gemini)...")
                # 2026-06-02 single-feed — one pass on the whole pool.
                pool = sorted(
                    clusters,
                    key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
                    reverse=True,
                )
                top_30 = pool[:30]
                if len(top_30) >= 5:
                    triage_candidates = [
                        {
                            "id": c.get("_db_id", "") or str(id(c)),
                            "title": c.get("title", ""),
                            "summary": c.get("summary", ""),
                            "source_count": c.get("source_count", 0),
                        }
                        for c in top_30
                    ]
                    triage_result = editorial_triage(triage_candidates, "world")
                    if triage_result:
                        incr_flags = set(triage_result.get("incremental_flags", []))
                        for cid in incr_flags:
                            for c in top_30:
                                if (c.get("_db_id", "") or str(id(c))) == cid:
                                    c["story_type"] = c.get("story_type") or "incremental_update"
                                    c["headline_rank"] = round(c.get("headline_rank", 0) * 0.75, 2)
                        if incr_flags:
                            print(f"  Incremental updates flagged: {len(incr_flags)}")
                        dupe_flags = triage_result.get("duplicate_flags", [])
                        if dupe_flags:
                            print(f"  Potential duplicate clusters: {dupe_flags[:3]}")
                        print(f"  Editorial triage applied ({len(incr_flags)} stories adjusted)")
                    else:
                        print("  Triage unavailable, using deterministic ranking")
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

        # 2026-06-02 single-feed — same-event cap runs once on whole pool.
        if len(clusters) > 10:
            event_counts: dict[str, int] = {}
            event_promoted: list[dict] = []
            event_deferred: list[dict] = []
            for c in clusters:
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
                event_last_promoted: dict[str, float] = {}
                for c in event_promoted:
                    t = (c.get("title", "") or "").lower()
                    for ek, kws in _EVENT_KEYWORDS.items():
                        if any(kw in t for kw in kws):
                            event_last_promoted[ek] = c.get("headline_rank", 0)
                            break
                for c in event_deferred:
                    idx = clusters.index(c)
                    t = (c.get("title", "") or "").lower()
                    event = None
                    for ek, kws in _EVENT_KEYWORDS.items():
                        if any(kw in t for kw in kws):
                            event = ek
                            break
                    if event and event in event_last_promoted:
                        floor = event_last_promoted[event] * 0.75
                    elif event_promoted:
                        floor = event_promoted[-1].get("headline_rank", 0) * 0.75
                    else:
                        continue
                    clusters[idx]["headline_rank"] = round(
                        min(c.get("headline_rank", 0), floor), 2
                    )
            clusters.sort(
                key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0), c.get("_db_id", str(id(c)))),
                reverse=True,
            )

        # Step 7b: Summarize clusters with Gemini Flash (runs after ranking so
        # Gemini calls are spent on the clusters that will actually appear on the
        # frontend, not merely the ones with the most raw sources).
        # Gemini generates headlines + summaries for the top 30 clusters only.
        # Clusters that fail Gemini get their rule-based summary cleared so
        # no fallback text reaches the frontend.
        gemini_results: dict[int, dict] = {}
        # Tier label persisted to DB cache. Claude is primary; Gemini fallback
        # only when ANTHROPIC_API_KEY is unset or Claude has a persistent fault.
        _summary_tier_used = "sonnet" if claude_is_available() else (
            "flash" if gemini_is_available() else None
        )
        if SUMMARIZER_AVAILABLE and llm_is_available():
            print(f"\n[7b] Summarizing top 30 clusters (tier={_summary_tier_used})...")
            try:
                # 2026-06-20 cost-cut: top-30 only. The regional/topic fill pools
                # (parked editions + topic desks) burned ~15 LLM calls/day with no
                # homepage consumer; ranks beyond 30 keep rule-based summaries.
                gemini_results, gemini_failed = summarize_clusters_batch(
                    clusters, cluster_consensus=cluster_consensus,
                    top_n=30, regional_fill=0, topic_fill=0,
                )
                for idx, result in gemini_results.items():
                    clusters[idx]["title"] = result["headline"]
                    clusters[idx]["summary"] = result["summary"]
                    clusters[idx]["consensus_points"] = result["consensus"]
                    clusters[idx]["divergence_points"] = result["divergence"]
                    clusters[idx]["_gemini_enriched"] = True
                    # Cache fields persisted at step 8 cluster insert so the
                    # post-rerank top-50 pass can skip unchanged clusters.
                    clusters[idx]["summary_article_hash"] = _content_hash(
                        clusters[idx].get("articles", [])
                    )
                    # Stamp the tier that ACTUALLY answered this cluster, not
                    # the batch-level guess: a mid-batch Claude latch flips
                    # later clusters to Gemini, and mislabeling those "sonnet"
                    # freezes them in the step-8d cache forever.
                    # Map provider -> DB summary_tier (CHECK allows 'sonnet' or
                    # 'flash'). Both $0 providers (Gemini flash, Groq llama) -> 'flash'.
                    _gen = result.get("_generator")
                    clusters[idx]["summary_tier"] = (
                        "sonnet" if _gen == "claude-sonnet" else "flash"
                    )
                    if result.get("editorial_importance") is not None:
                        clusters[idx]["editorial_importance"] = result["editorial_importance"]
                    if result.get("story_type") is not None:
                        clusters[idx]["story_type"] = result["story_type"]
                    if result.get("has_binding_consequences") is not None:
                        clusters[idx]["has_binding_consequences"] = result["has_binding_consequences"]
                    if result.get("claims"):
                        clusters[idx]["_gemini_claims"] = result["claims"]
                    if result.get("consensus_ratio") is not None:
                        clusters[idx]["_gemini_consensus_ratio"] = result["consensus_ratio"]
                    if result.get("consensus_summary"):
                        clusters[idx]["_gemini_consensus_summary"] = result["consensus_summary"]
                if gemini_failed:
                    print(f"  [info] {len(gemini_failed)} pool-1 cluster(s) keeping rule-based summary (LLM failed)")
            except Exception as e:
                print(f"  [warn] LLM summarization failed: {e}")
        elif SUMMARIZER_AVAILABLE:
            print("\n[7b] Skipping LLM summarization (no API key set)")
        else:
            print("\n[7b] Skipping LLM summarization (SDKs not installed)")

        # Topic diversity lives in feed_ranker.apply_feed_ordering() — the
        # in-line copy that used to sit here mutated nothing the consumers
        # read (it only tie-spaced the promoted tier of a local list) and
        # duplicated the partition feed_ranker already does on rank_world.
        # Removed 2026-06-11; feed_ranker is the single owner.

        # Recency gate for top-10 — single pool (2026-06-02).
        recency_cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
        sorted_pool = sorted(
            clusters,
            key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0)),
            reverse=True,
        )
        top_10 = sorted_pool[:10]
        demoted = []
        for c in top_10:
            cluster_arts = c.get("articles", [])
            most_recent = c.get("first_published", "")
            for art in cluster_arts:
                pub = art.get("published_at", "")
                if pub and pub > most_recent:
                    most_recent = pub
            if most_recent and most_recent < recency_cutoff:
                demoted.append(c)
        if demoted:
            floor_rank = sorted_pool[10].get("headline_rank", 0) if len(sorted_pool) > 10 else 0
            for c in demoted:
                c["headline_rank"] = round(
                    min(c.get("headline_rank", 0), floor_rank - 0.01), 2
                )
            print(f"  [feed] Recency gate: demoted {len(demoted)} stale stories from top 10")

        # ── Feed ordering (2026-06-02 single-edition) ──────────────────────
        # Normalized cluster IDs: feed_ranker uses c["id"] for identity.
        for c in clusters:
            if "id" not in c:
                c["id"] = c.get("_db_id", "") or str(id(c))
        apply_feed_ordering(clusters, sources)

        # Top 10 of the single feed for diagnostics.
        pool_sorted = sorted(
            clusters, key=lambda c: c.get("rank_world", 0), reverse=True
        )
        print("\n  --- Top 10 by rank_world ---")
        for j, c in enumerate(pool_sorted[:10]):
            title = (c.get("title", "") or "")[:55]
            print(
                f"  {j+1:2}. [{c.get('rank_world', 0):5.1f}] "
                f"{c.get('source_count', 0):2}src {title}"
            )

        # ── Step 7d: Generate Daily Brief (TL;DR + audio broadcast) ──
        brief_results: dict[str, dict] = {}
        if BRIEFING_AVAILABLE:
            print("\n[7d] Generating Daily Briefs...")
            start_7d = time.time()
            try:
                brief_results = generate_daily_briefs(
                    clusters, source_map,
                    edition_sections=ACTIVE_EDITIONS,
                )

                for edition, brief in brief_results.items():
                    brief_row = {
                        "edition": edition,
                        "pipeline_run_id": run_id,
                        "tldr_headline": brief.get("tldr_headline"),
                        "tldr_text": brief["tldr_text"],
                        "opinion_text": brief.get("opinion_text"),
                        "opinion_headline": brief.get("opinion_headline"),
                        "opinion_lean": brief.get("opinion_lean"),
                        "opinion_cluster_id": brief.get("opinion_cluster_id"),
                        "opinion_audio_script": brief.get("opinion_audio_script"),
                        "audio_script": brief.get("audio_script"),
                        "top_cluster_ids": brief.get("top_cluster_ids", []),
                        "generator": brief.get("generator"),
                    }

                    # Fallback: if this run produced an empty/placeholder brief,
                    # carry forward the previous brief so the frontend always has
                    # real content. "No stories available" is the placeholder text.
                    is_empty_brief = (
                        not brief.get("audio_script")
                        and brief.get("tldr_text", "").startswith("No stories")
                    )
                    if is_empty_brief:
                        try:
                            prev = supabase.table("daily_briefs").select(
                                "tldr_headline,tldr_text,opinion_text,opinion_headline,opinion_lean,opinion_cluster_id,"
                                "audio_script,audio_url,audio_duration_seconds,"
                                "audio_voice_label,audio_voice,audio_file_size,"
                                "opinion_audio_script,top_cluster_ids,opinion_start_seconds"
                            ).eq("edition", edition).order(
                                "created_at", desc=True
                            ).limit(1).execute()
                            if prev.data and prev.data[0].get("tldr_text"):
                                p = prev.data[0]
                                brief_row["tldr_headline"] = p.get("tldr_headline")
                                brief_row["tldr_text"] = p["tldr_text"]
                                brief_row["opinion_text"] = p.get("opinion_text")
                                brief_row["opinion_headline"] = p.get("opinion_headline")
                                brief_row["opinion_lean"] = p.get("opinion_lean")
                                brief_row["opinion_cluster_id"] = p.get("opinion_cluster_id")
                                brief_row["audio_script"] = p.get("audio_script")
                                brief_row["audio_url"] = p.get("audio_url")
                                brief_row["audio_duration_seconds"] = p.get("audio_duration_seconds")
                                brief_row["audio_voice_label"] = p.get("audio_voice_label")
                                brief_row["audio_voice"] = p.get("audio_voice")
                                brief_row["audio_file_size"] = p.get("audio_file_size")
                                brief_row["opinion_start_seconds"] = p.get("opinion_start_seconds")
                                brief_row["top_cluster_ids"] = p.get("top_cluster_ids", [])
                                print(f"  [brief:{edition}] Empty brief — carried forward previous brief")
                        except Exception as e:
                            print(f"  [warn] Could not fetch previous brief for {edition}: {e}")
                        # Skip audio generation — we're using the previous brief's audio
                    else:
                        # Generate two-host audio via Gemini Flash TTS — every run
                        if brief.get("audio_script"):
                            voices = get_voices_for_today(edition)
                            audio_result = produce_audio(
                                brief["audio_script"], voices, edition,
                                opinion_audio_script=brief.get("opinion_audio_script"),
                                opinion_lean=brief.get("opinion_lean"),
                            )
                            if audio_result:
                                brief_row["audio_url"] = audio_result["audio_url"]
                                brief_row["audio_duration_seconds"] = audio_result["duration_seconds"]
                                brief_row["audio_file_size"] = audio_result["file_size"]
                                brief_row["opinion_start_seconds"] = audio_result.get("opinion_start_seconds")
                                has_opinion = bool(brief.get("opinion_audio_script"))
                                brief_row["audio_voice"] = f"{voices['host_a']['id']}+{voices['host_b']['id']}" + (
                                    f"+{voices['opinion']['id']}" if has_opinion else ""
                                )
                                brief_row["audio_voice_label"] = "Three voices" if has_opinion else "Two voices"
                            else:
                                # TTS failed — carry forward previous audio so
                                # frontend always has something to play.
                                try:
                                    prev = supabase.table("daily_briefs").select(
                                        "audio_url,audio_duration_seconds,audio_voice_label,audio_voice,audio_file_size,opinion_start_seconds"
                                    ).eq("edition", edition).order(
                                        "created_at", desc=True
                                    ).limit(1).execute()
                                    if prev.data and prev.data[0].get("audio_url"):
                                        p = prev.data[0]
                                        brief_row["audio_url"] = p["audio_url"]
                                        brief_row["audio_duration_seconds"] = p.get("audio_duration_seconds")
                                        brief_row["audio_voice_label"] = p.get("audio_voice_label")
                                        brief_row["audio_voice"] = p.get("audio_voice")
                                        brief_row["audio_file_size"] = p.get("audio_file_size")
                                        brief_row["opinion_start_seconds"] = p.get("opinion_start_seconds")
                                        print(f"  [brief:{edition}] TTS failed — carried forward previous audio")
                                except Exception as e:
                                    print(f"  [warn] Could not fetch previous audio for {edition}: {e}")
                        else:
                            # No audio script (rule-based fallback) — carry forward
                            # previous audio so frontend always has audio available.
                            try:
                                prev = supabase.table("daily_briefs").select(
                                    "audio_url,audio_duration_seconds,audio_voice_label,audio_script,audio_voice,audio_file_size,opinion_start_seconds"
                                ).eq("edition", edition).order(
                                    "created_at", desc=True
                                ).limit(1).execute()
                                if prev.data and prev.data[0].get("audio_url"):
                                    p = prev.data[0]
                                    brief_row["audio_url"] = p["audio_url"]
                                    brief_row["audio_duration_seconds"] = p.get("audio_duration_seconds")
                                    brief_row["audio_voice_label"] = p.get("audio_voice_label")
                                    brief_row["audio_voice"] = p.get("audio_voice")
                                    brief_row["audio_file_size"] = p.get("audio_file_size")
                                    brief_row["opinion_start_seconds"] = p.get("opinion_start_seconds")
                                    if not brief_row.get("audio_script"):
                                        brief_row["audio_script"] = p.get("audio_script")
                                    print(f"  [brief:{edition}] No audio script — carried forward previous audio")
                            except Exception as e:
                                print(f"  [warn] Could not fetch previous audio for {edition}: {e}")

                    try:
                        supabase.table("daily_briefs").upsert(
                            brief_row, on_conflict="edition,pipeline_run_id"
                        ).execute()
                    except Exception as e:
                        # If the error is a missing column (e.g. opinion_start_seconds
                        # before migration 028), strip the unknown column and retry.
                        err_msg = str(e)
                        if "PGRST204" in err_msg or "does not exist" in err_msg.lower() or "schema cache" in err_msg.lower():
                            # Extract column name from error if possible, or strip known optional cols
                            for optional_col in ("opinion_start_seconds",):
                                brief_row.pop(optional_col, None)
                            try:
                                supabase.table("daily_briefs").upsert(
                                    brief_row, on_conflict="edition,pipeline_run_id"
                                ).execute()
                                print(f"  [brief:{edition}] Stored (stripped missing column)")
                            except Exception as e2:
                                print(f"  [warn] Failed to store brief for {edition} (retry): {e2}")
                        else:
                            print(f"  [warn] Failed to store brief for {edition}: {e}")

                elapsed_7d = time.time() - start_7d
                print(f"  Daily briefs: {len(brief_results)} editions (with audio, {elapsed_7d:.1f}s)")

                # Generate podcast RSS feeds (only when audio is enabled)
                if not os.environ.get("DISABLE_AUDIO", "").strip() in ("1", "true", "yes"):
                    try:
                        from briefing.podcast_feed_generator import generate_podcast_feeds
                        feed_results = generate_podcast_feeds(ACTIVE_EDITIONS)
                        if feed_results:
                            print(f"  Podcast feeds: {', '.join(feed_results.keys())}")
                    except Exception as e:
                        print(f"  [warn] Podcast feed generation failed: {e}")
            except Exception as e:
                print(f"  [warn] Daily brief generation failed: {e}")
                # P0 fix (UAT 2026-05-13): on total generator failure we MUST
                # still write a stub row per edition so the homepage doesn't
                # serve yesterday's audio indefinitely. tldr_text is a safe
                # placeholder; frontend already handles null audio_url.
                for edition in ACTIVE_EDITIONS:
                    try:
                        stub_row = {
                            "edition": edition,
                            "pipeline_run_id": run_id,
                            "tldr_headline": None,
                            "tldr_text": "Daily brief unavailable — see top stories.",
                            "opinion_text": None,
                            "opinion_headline": None,
                            "opinion_lean": None,
                            "opinion_cluster_id": None,
                            "opinion_audio_script": None,
                            "audio_script": None,
                            "audio_url": None,
                            "top_cluster_ids": [],
                            "generator": f"stub-on-failure:{type(e).__name__}",
                        }
                        supabase.table("daily_briefs").upsert(
                            stub_row, on_conflict="edition,pipeline_run_id"
                        ).execute()
                        print(f"  [brief:{edition}] >>> WROTE STUB ROW (generator crash) <<<")
                    except Exception as e2:
                        print(f"  [warn] Failed to write stub brief for {edition}: {e2}")
        else:
            print("\n[7d] Skipping daily briefs (modules not installed)")

        # Step 8: Store clusters with enrichment data
        print("\n[8/9] Storing clusters with enrichment data...")
        all_cluster_article_links: list[dict] = []  # batch insert
        cluster_ids_to_enrich: list[str] = []
        gemini_enriched_ids: set[str] = set()  # clusters with Gemini text
        # 2026-05-24 fix 5 — surface aggregate insert failures.
        # Previously insert_cluster() returned None on exception with only
        # a print line. If schema drift caused every row to fail, the loop
        # silently produced clusters_created=0 (May 18-20 mystery: 7000+
        # articles analyzed, 0 clusters persisted, 0 errors logged). Now
        # we track the count + sample message so it shows up in summary
        # and gets attached to pipeline_runs.errors at finalize.
        cluster_insert_failures = 0
        cluster_insert_sample_err: str = ""

        for ci, cluster in enumerate(clusters):
            cluster_articles_list = cluster.get("articles", [])

            # Determine cluster section (edition) from its articles.
            # Strategy: majority vote — whichever edition has the most
            # 2026-06-02 single-feed — section / sections frozen to world.
            cluster_section = "world"
            all_sections = ["world"]
            _is_international = True  # kept for legacy column; no longer used for routing

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
                "rank_world": round(cluster.get("rank_world", cluster.get("headline_rank", 0.0)), 2),
                "is_international": _is_international,
                "mega_cluster_capped": bool(cluster.get("mega_cluster_capped", False)),
                # 2026-05-24 v2 — first-class headline signal (migration 059)
                "is_headline": bool(cluster.get("is_headline", False)),
                "headline_confidence": int(cluster.get("headline_confidence", 0)),
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

            # Summary cache fields — populated by step 7b for clusters that
            # received an LLM summary; consumed by step 8d (post-rerank pass)
            # to skip clusters whose article membership hasn't changed.
            if cluster.get("summary_article_hash"):
                cluster_row["summary_article_hash"] = cluster["summary_article_hash"]
            if cluster.get("summary_tier"):
                cluster_row["summary_tier"] = cluster["summary_tier"]

            # void --verify: claim_consensus JSONB
            # Prefer Gemini-deduplicated claims; fall back to NLP-only
            ci_key = str(ci)
            nlp_consensus = cluster_consensus.get(ci_key)
            if cluster.get("_gemini_claims") or nlp_consensus:
                cc_data: dict = {}
                if nlp_consensus:
                    cc_data = {
                        "total_claims": nlp_consensus.total_claims,
                        "corroborated": nlp_consensus.corroborated,
                        "single_source": nlp_consensus.single_source,
                        "disputed": nlp_consensus.disputed,
                        "consensus_ratio": nlp_consensus.consensus_ratio,
                    }
                # Overlay Gemini deduplication if available
                if cluster.get("_gemini_claims"):
                    cc_data["highlighted_claims"] = cluster["_gemini_claims"]
                elif nlp_consensus and nlp_consensus.claims:
                    cc_data["highlighted_claims"] = [
                        {
                            "text": vc.claim_text,
                            "status": vc.status,
                            "source_count": vc.source_count,
                            "sources": vc.source_names,
                            "highlight": vc.highlight,
                        }
                        for vc in nlp_consensus.claims
                        if vc.highlight or vc.status == "disputed"
                    ][:10]
                if cluster.get("_gemini_consensus_ratio") is not None:
                    cc_data["consensus_ratio"] = cluster["_gemini_consensus_ratio"]
                if cluster.get("_gemini_consensus_summary"):
                    cc_data["consensus_summary"] = cluster["_gemini_consensus_summary"]
                elif nlp_consensus and nlp_consensus.disputed_details:
                    cc_data["consensus_summary"] = (
                        f"{nlp_consensus.corroborated} claims corroborated, "
                        f"{nlp_consensus.disputed} disputed across sources"
                    )
                if nlp_consensus and nlp_consensus.disputed_details:
                    cc_data["disputed_details"] = [
                        {
                            "topic": dd.topic,
                            "version_a": dd.version_a,
                            "version_a_sources": dd.version_a_sources,
                            "version_b": dd.version_b,
                            "version_b_sources": dd.version_b_sources,
                            "contradiction_type": dd.contradiction_type,
                        }
                        for dd in nlp_consensus.disputed_details
                    ][:5]
                if cc_data:
                    cluster_row["claim_consensus"] = cc_data

            try:
                result = insert_cluster(cluster_row)
            except Exception as _ins_e:
                cluster_insert_failures += 1
                if not cluster_insert_sample_err:
                    cluster_insert_sample_err = f"{type(_ins_e).__name__}: {str(_ins_e)[:200]}"
                continue
            if result:
                clusters_created += 1
                cluster_id = result.get("id", "")
                # Write the DB UUID back onto the in-memory cluster. Image
                # caching (step 8e), the step-8d summary sync, title dedup,
                # brief linkage, and the memory engine all key on this; the
                # str(id(c)) placeholder set before feed ordering satisfies
                # none of them.
                cluster["_db_id"] = cluster_id
                cluster["id"] = cluster_id
                cluster_ids_to_enrich.append(cluster_id)
                if has_gemini:
                    gemini_enriched_ids.add(cluster_id)
                for article_id in cluster.get("article_ids", []):
                    if article_id:
                        all_cluster_article_links.append({
                            "cluster_id": cluster_id,
                            "article_id": article_id,
                        })
            else:
                cluster_insert_failures += 1
                if not cluster_insert_sample_err:
                    cluster_insert_sample_err = "insert returned None (see prior insert error logs)"

        # 2026-05-24 fix 5 — emit aggregate summary so silent regressions
        # (May 18-20 clusters_created=0 mystery) surface in CI logs.
        if cluster_insert_failures:
            print(
                f"  [warn] cluster_insert_failures={cluster_insert_failures} "
                f"clusters_created={clusters_created} — sample: "
                f"{cluster_insert_sample_err}"
            )
            try:
                # Attach to pipeline_runs.errors so monitoring can alarm.
                # Appends (does not overwrite) so claude_client latch
                # markers written earlier in the run survive.
                from utils.supabase_client import append_pipeline_run_errors
                append_pipeline_run_errors(run_id, [{
                    "error": (
                        f"cluster_insert_failures={cluster_insert_failures}, "
                        f"sample={cluster_insert_sample_err}"
                    ),
                    "source": "step_8_store_clusters",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }])
            except Exception:
                pass

        # Brief linkage backfill — step 7d runs BEFORE these inserts, so the
        # generator saw no _db_id and persisted top_cluster_ids=[] and a NULL
        # opinion_cluster_id. The generator keeps references to the cluster
        # dicts it used (_top_cluster_refs / _opinion_cluster_ref); those
        # same dicts now carry _db_id, so patch the stored rows.
        if brief_results and run_id:
            for _bf_edition, _bf_brief in brief_results.items():
                _bf_patch: dict = {}
                # TL;DR linkage only when the text was generated from THIS
                # run's clusters (a carried-forward brief describes a
                # previous run's stories).
                if not _bf_brief.get("_carried"):
                    _bf_top_ids = [
                        c.get("_db_id")
                        for c in (_bf_brief.get("_top_cluster_refs") or [])
                        if c.get("_db_id")
                    ]
                    if _bf_top_ids:
                        _bf_patch["top_cluster_ids"] = _bf_top_ids
                else:
                    _bf_top_ids = []
                # Opinion linkage whenever THIS run generated the opinion
                # (a carried brief can still receive a fresh opinion).
                _bf_op_ref = _bf_brief.get("_opinion_cluster_ref")
                _bf_op_id = (_bf_op_ref or {}).get("_db_id")
                if _bf_op_id and _bf_brief.get("_fresh_opinion"):
                    _bf_patch["opinion_cluster_id"] = _bf_op_id
                if not _bf_patch:
                    continue
                try:
                    supabase.table("daily_briefs").update(_bf_patch).eq(
                        "edition", _bf_edition
                    ).eq("pipeline_run_id", run_id).execute()
                    print(
                        f"  [brief:{_bf_edition}] Linkage backfilled: "
                        f"{len(_bf_top_ids)} top clusters"
                        + (", opinion" if _bf_patch.get("opinion_cluster_id") else "")
                    )
                except Exception as _bf_e:
                    print(f"  [warn] Brief linkage backfill failed ({_bf_edition}): {_bf_e}")

        # Batch-insert cluster_articles links (instead of one per article)
        if all_cluster_article_links:
            print(f"  Batch-linking {len(all_cluster_article_links)} article-cluster pairs...")
            _batch_upsert(
                "cluster_articles", all_cluster_article_links, chunk_size=200,
                on_conflict="cluster_id,article_id",
            )

        # void --verify: Batch-insert article_claims to Supabase
        if CLAIMS_AVAILABLE and all_article_claims and cluster_ids_to_enrich:
            print("  Storing article claims (void --verify)...")
            try:
                # Map article -> cluster via the _db_id written back at
                # insert time. The old index-zip against
                # cluster_ids_to_enrich misaligned the moment any insert
                # failed (the failure `continue` skips the id append but
                # not the cluster), attaching claims to the wrong clusters.
                ci_to_db_id: dict[int, str] = {}
                article_to_ci: dict[str, int] = {}
                for ci_idx, cluster in enumerate(clusters):
                    db_id = cluster.get("_db_id")
                    if not db_id:
                        continue
                    ci_to_db_id[ci_idx] = db_id
                    for art_id in cluster.get("article_ids", []):
                        article_to_ci[art_id] = ci_idx

                claim_rows: list[dict] = []
                for art_id, claims in all_article_claims.items():
                    ci_idx = article_to_ci.get(art_id)
                    db_cluster_id = ci_to_db_id.get(ci_idx) if ci_idx is not None else None

                    # Get verification status from cluster_consensus
                    ci_key = str(ci_idx) if ci_idx is not None else None
                    nlp_cons = cluster_consensus.get(ci_key) if ci_key else None
                    verified_statuses: dict[str, str] = {}
                    if nlp_cons:
                        for vc in nlp_cons.claims:
                            verified_statuses[vc.claim_text] = vc.status

                    for claim in claims:
                        status = verified_statuses.get(claim.claim_text, "unverified")
                        claim_rows.append({
                            "article_id": art_id,
                            "cluster_id": db_cluster_id,
                            "claim_text": claim.claim_text[:2000],
                            "source_sentence": (claim.source_sentence or "")[:2000],
                            "subject_entity": claim.subject_entity or None,
                            "subject_entity_type": claim.subject_entity_type or None,
                            "claim_type": claim.claim_type,
                            "has_quantitative": claim.has_quantitative,
                            "status": status,
                            "corroboration_count": 0,
                            "corroborating_sources": [claim.source_slug] if claim.source_slug else [],
                        })

                if claim_rows:
                    # Replace, don't accumulate: rows carry no `id`, so the
                    # old on_conflict="id" never fired and re-runs over the
                    # same articles duplicated every claim. Claims are
                    # regenerated per run; delete the affected articles'
                    # claims first, then plain-insert.
                    _claim_art_ids = sorted({r["article_id"] for r in claim_rows})
                    for _del_i in range(0, len(_claim_art_ids), 200):
                        try:
                            supabase.table("article_claims").delete().in_(
                                "article_id", _claim_art_ids[_del_i:_del_i + 200]
                            ).execute()
                        except Exception as _del_e:
                            print(f"  [warn] claim pre-delete failed: {_del_e}")
                            break
                    inserted = _batch_upsert(
                        "article_claims", claim_rows, chunk_size=200,
                    )
                    print(f"  Article claims stored: {inserted}")
            except Exception as e:
                print(f"  [warn] Article claims storage failed: {e}")

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

    # Step 8b (deferred): Deduplicate clusters — runs AFTER enrichment so old
    # clusters remain visible to the frontend until new ones are fully ready.
    # This prevents the "Presses Are Warming Up" empty state during pipeline runs.
    new_cluster_ids = set(cluster_ids_to_enrich)
    if new_cluster_ids:
        print(f"\n[8b] Deduplicating clusters (deferred — new clusters already enriched)...")
        new_cluster_articles: dict[str, set[str]] = {}
        for link in all_cluster_article_links:
            cid = link["cluster_id"]
            aid = link["article_id"]
            new_cluster_articles.setdefault(cid, set()).add(aid)

        all_new_article_ids = set()
        for aids in new_cluster_articles.values():
            all_new_article_ids.update(aids)

        old_cluster_articles: dict[str, set[str]] = {}
        all_new_article_list = list(all_new_article_ids)
        for i in range(0, len(all_new_article_list), 500):
            batch = all_new_article_list[i:i + 500]
            try:
                # Paginated: one article can sit in multiple clusters, so a
                # 500-id batch can exceed PostgREST's 1,000-row response cap.
                _dq_offset = 0
                while True:
                    res = supabase.table("cluster_articles").select(
                        "cluster_id,article_id"
                    ).in_("article_id", batch).range(
                        _dq_offset, _dq_offset + 999
                    ).execute()
                    _dq_rows = res.data or []
                    for row in _dq_rows:
                        cid = row["cluster_id"]
                        if cid not in new_cluster_ids:
                            old_cluster_articles.setdefault(cid, set()).add(
                                row["article_id"]
                            )
                    if len(_dq_rows) < 1000:
                        break
                    _dq_offset += 1000
            except Exception as e:
                print(f"  [warn] dedup query failed: {e}")

        # Only delete old clusters with >30% article overlap with a new cluster.
        # This prevents aggressive deletion of clusters that share only 1-2 articles.
        stale_ids: list[str] = []
        for old_cid, old_aids in old_cluster_articles.items():
            # Check overlap with ANY new cluster
            for new_cid, new_aids in new_cluster_articles.items():
                overlap = len(old_aids & new_aids)
                if len(old_aids) > 0 and overlap / len(old_aids) > 0.3:
                    stale_ids.append(old_cid)
                    break

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
            print(f"  Deduplicated: removed {len(stale_ids)} old clusters (>30% article overlap)")
        else:
            print(f"  No duplicate clusters found")

        # Title-based cross-run dedup: catch old clusters covering the same
        # story as new clusters but with ZERO article overlap (different RSS
        # fetch batches). The article-overlap check above misses these entirely.
        try:
            from clustering.story_cluster import _title_words
            # Fetch titles of old clusters in DB (recent 48h).
            # Paginated to avoid payload size limits on large cluster sets.
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
            old_titles: dict[str, tuple[set[str], int]] = {}
            _page_size = 500
            _offset = 0
            while True:
                old_res = supabase.table("story_clusters").select(
                    "id,title,source_count"
                ).gte("created_at", cutoff).range(
                    _offset, _offset + _page_size - 1
                ).execute()
                if not old_res.data:
                    break
                for r in old_res.data:
                    rid = r.get("id", "")
                    if rid and rid not in new_cluster_ids and r.get("title"):
                        old_titles[rid] = (_title_words(r["title"]), r.get("source_count", 0))
                if len(old_res.data) < _page_size:
                    break
                _offset += _page_size

            # Build title word sets for new clusters
            new_titles: dict[str, set[str]] = {}
            for cid in new_cluster_ids:
                # Find title from the stored clusters (was `all_clusters`, an
                # undefined name whose NameError the outer try swallowed
                # every run, leaving this dedup permanently inert)
                for c in clusters:
                    db_id = c.get("_db_id", "")
                    if db_id == cid:
                        new_titles[cid] = _title_words(c.get("title", ""))
                        break

            title_stale: list[str] = []
            for old_cid, (old_words, old_src) in old_titles.items():
                if old_cid in stale_ids or not old_words:
                    continue
                for new_cid, new_words in new_titles.items():
                    if not new_words:
                        continue
                    intersection = len(old_words & new_words)
                    union = len(old_words | new_words)
                    if union > 0 and intersection / union >= 0.40:
                        title_stale.append(old_cid)
                        break

            if title_stale:
                for i in range(0, len(title_stale), 100):
                    batch = title_stale[i:i + 100]
                    try:
                        supabase.table("cluster_articles").delete().in_(
                            "cluster_id", batch
                        ).execute()
                        supabase.table("story_clusters").delete().in_(
                            "id", batch
                        ).execute()
                    except Exception as e:
                        print(f"  [warn] title dedup delete failed: {e}")
                print(f"  Title dedup: removed {len(title_stale)} old clusters (>=40% title overlap with new)")
        except Exception as e:
            print(f"  [warn] Title-based dedup failed: {e}")

    # Step 8c: Holistic re-rank — re-score ALL clusters in DB with the
    # current ranking engine so old and new clusters compete on equal footing.
    # Without this, old clusters keep stale scores from previous pipeline runs
    # while new clusters are scored with the current engine, causing rank drift.
    if ANALYSIS_AVAILABLE:
        print("\n[8c] Holistic re-rank (all clusters, v6.0 engine)...")
        try:
            import sys as _sys
            from pathlib import Path as _Path
            _pipeline_dir = str(_Path(__file__).parent)
            if _pipeline_dir not in _sys.path:
                _sys.path.insert(0, _pipeline_dir)
            from rerank import rerank_all_clusters
            rerank_all_clusters(sources)
        except Exception as e:
            import traceback
            print(f"  [warn] Holistic re-rank failed: {e}")
            traceback.print_exc()

    # Step 8c.5 REMOVED (2026-06-02 collapse-editions). World-tag
    # reconciliation was only needed when /world was a separate overflow
    # surface filtered by `sections @> ['world']`. With the single feed
    # all clusters carry sections=['world'] at write time, so no post-rerank
    # reconciliation is required.

    # Step 8c.6 — Engine snapshot writer REMOVED (2026-06-01 egress fix).
    # The diagnostic lab at /diag.html and the supporting sandbox stack
    # (engine_snapshot.py, sandbox_replay.py, sandbox_server.py,
    # sandbox.yml) were deleted to stop multi-MB JSONB payloads from
    # contributing to Supabase egress. The engine_runs / engine_snapshots /
    # sandbox_runs tables (migrations 057-058) remain in the schema —
    # cleanup_diagnostic_tables RPC prunes them on every run.

    # --engine-only short-circuit: skip every LLM-bearing step
    # (summarization, daily brief, weekly, IG). $0 fresh-run mode.
    if engine_only:
        elapsed = time.time() - start_time
        # 2026-05-24 iter 6 fix — finalize pipeline_runs BEFORE the early
        # return. Previously engine_only/recluster_only runs left the run
        # row at status="running" + clusters_created=0 forever, breaking
        # downstream monitoring (the diag.html cost panel, the engine_runs
        # snapshot, the "did the pipeline succeed?" question).
        if run_id:
            try:
                update_pipeline_run(
                    run_id=run_id,
                    status="completed",
                    articles_fetched=len(stored_articles),
                    articles_analyzed=len(article_bias_map) if recluster_only else articles_analyzed,
                    clusters_created=clusters_created,
                    errors=(fetch_errors or [])[:50],
                    duration_seconds=round(elapsed, 2),
                )
            except Exception as _fin_e:
                print(f"  [warn] finalize pipeline_run failed: {_fin_e}")
        print(f"\n[engine-only] Done in {elapsed/60:.1f} minutes. "
              f"Skipping LLM editorial steps (8d, brief, weekly).")
        return

    # Step 8d: Post-rerank single-pass top-50 Sonnet summarization with cache.
    # Reads final top-50 by rank_world from DB. For each cluster:
    #   - hash its current article membership
    #   - if hash matches stored summary_article_hash AND tier='sonnet' → skip
    #   - else → call Claude (Gemini fallback), write summary + hash + tier
    # Op-eds (content_type='opinion') and clusters with <3 articles skipped.
    # Updates the in-memory `clusters` list so the daily brief regen below
    # reads fresh top-15 summaries.
    summary_metrics = {"summarized": 0, "cached": 0, "skipped": 0, "failed": 0}
    if SUMMARIZER_AVAILABLE and llm_is_available() and calls_remaining() > 0:
        print("\n[8d] Post-rerank top-10 Gemini upgrade (premium slots)...")
        try:
            # 2026-06-20 split: 7b summarized the top 30 on Groq (llama). Here we
            # upgrade only the VISIBLE top 10 (post-rerank) to Gemini quality.
            # That keeps Gemini at ~10 calls/run (+2 for the brief), under its
            # 20/day free cap. Ranks 11-30 keep their Groq summaries; 31-50 stay
            # rule-based. prefer_provider="gemini" (Groq fallback if Gemini out).
            # Quality hierarchy: top-5 highest-impact stories → gemini-2.5-flash
            # (premium), ranks 6-10 → gemini-2.5-flash-lite. Groq fallback for
            # both. See summarize_top50_after_rerank / migration 063.
            summary_metrics = summarize_top50_after_rerank(
                supabase, edition="world", limit=10, prefer_provider="gemini",
                flash_top_n=5)
            print(
                f"  Top-10: {summary_metrics['summarized']} summarized, "
                f"{summary_metrics['cached']} cache hits, "
                f"{summary_metrics['skipped']} skipped (op-ed / <3 sources), "
                f"{summary_metrics['failed']} failed"
            )
            # Sync in-memory clusters with the freshly written summaries so any
            # downstream consumer (brief regen, audio) sees the post-rerank text.
            id_to_idx = {c.get("id"): i for i, c in enumerate(clusters) if c.get("id")}
            for cid, result in summary_metrics.get("updated_summaries", {}).items():
                idx = id_to_idx.get(cid)
                if idx is None:
                    continue
                clusters[idx]["title"] = result["headline"]
                clusters[idx]["summary"] = result["summary"]
                if result.get("consensus"):
                    clusters[idx]["consensus_points"] = result["consensus"]
                if result.get("divergence"):
                    clusters[idx]["divergence_points"] = result["divergence"]
                clusters[idx]["_gemini_enriched"] = True
        except Exception as e:
            print(f"  [warn] Post-rerank summarization failed: {e}")

    # Step 8e: Cache cluster images to Supabase Storage (bypasses CDN hotlink protection)
    # Downloads og:images server-side on GitHub Actions (neutral IP = no Referer block),
    # re-serves from Supabase CDN. Top 15 clusters get guaranteed image availability —
    # buffer for the 50/50 lead split (rank 0) + headroom if rank 0 image fetch fails
    # (rank 1 promotes seamlessly).
    if IMAGE_CACHER_AVAILABLE:
        print("\n[8e] Caching cluster images to Supabase Storage...")
        try:
            cache_cluster_images(clusters, supabase, top_n=15)
        except Exception as e:
            print(f"  [warn] Image caching failed: {e}")
    else:
        print("\n[8e] Skipping image cache (cluster_image_cacher not available)")

    # Step 9a: Update memory engine with new top story
    if MEMORY_AVAILABLE and cluster_ids_to_enrich and ANALYSIS_AVAILABLE:
        print("\n[9a] Updating news memory engine...")
        try:
            # Pass only successfully-stored clusters, ordered by the final
            # display signal (rank_world), so the recorded "top story"
            # matches the homepage #1. The old (clusters,
            # cluster_ids_to_enrich) index-zip misaligned on any insert
            # failure and followed pre-feed-ordering list order.
            _mem_clusters = sorted(
                (c for c in clusters if c.get("_db_id")),
                key=lambda c: c.get("rank_world", 0),
                reverse=True,
            )
            memory_result = update_memory_after_pipeline_run(
                pipeline_run_id=run_id,
                clusters=_mem_clusters,
                cluster_ids=[c["_db_id"] for c in _mem_clusters],
            )
            print(f"  Memory engine: {memory_result.get('status', 'unknown')}"
                  f" — {memory_result.get('top_story', 'n/a')}"
                  f" ({memory_result.get('source_count', 0)} sources)")
        except Exception as e:
            print(f"  [warn] Memory engine update failed: {e}")
    elif not MEMORY_AVAILABLE:
        print("\n[9a] Skipping memory engine (not installed)")

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

    # Step 9d: Update source track record (void --verify Phase 2)
    # Longitudinal tracking: how often a source's single-source claims get
    # confirmed or contradicted by other sources in subsequent runs.
    if TRACK_RECORD_AVAILABLE:
        print("\n[9d] Updating source track record (void --verify)...")
        try:
            track_stats = update_source_track_record(supabase)
            print(f"  Track record: {track_stats}")
        except Exception as e:
            print(f"  [warn] Source track record update failed: {e}")
    else:
        print("\n[9d] Skipping source track record (module not available)")

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

    # Clean old daily briefs — keep 8 days for weekly digest signal
    # The weekly generator uses daily TL;DR headlines and top_cluster_ids
    # to determine which stories dominated the week.
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        editions_list = ["world", "us", "europe", "uk", "south-asia", "canada"]
        old = supabase.table("daily_briefs").select("id, edition").in_(
            "edition", editions_list
        ).lt("created_at", cutoff).execute()
        if old.data:
            ids = [b["id"] for b in old.data]
            supabase.table("daily_briefs").delete().in_("id", ids).execute()
            per_ed: dict[str, int] = {}
            for b in old.data:
                per_ed[b["edition"]] = per_ed.get(b["edition"], 0) + 1
            for ed, n in per_ed.items():
                print(f"  Cleaned {n} old briefs for {ed}")
    except Exception as e:
        print(f"  [warn] Daily brief cleanup failed: {e}")

    # Retention: archive then delete clusters older than 2 days,
    # delete orphaned articles older than 7 days (CASCADE cleans
    # bias_scores + article_categories), prune archive after 30 days.
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

        # Delete empty clusters (no articles linked)
        empty = supabase.rpc("cleanup_stale_clusters").execute()

        # Fix NULL first_published clusters (never caught by retention)
        supabase.table("story_clusters").update(
            {"first_published": datetime.now(timezone.utc).isoformat()}
        ).is_("first_published", "null").execute()

    except Exception as e:
        print(f"  [warn] cluster retention failed: {e}")

    # Article retention via RPC (migration 050). Atomic, indexed, cascades
    # through FKs from migration 046. Falls back to the legacy paginated
    # SELECT/DELETE block below if the RPC is missing (e.g., migration 050
    # not yet applied to this environment).
    try:
        # 2026-06-01 egress fix — tightened 8 → 7 days. Weekly digest needs
        # exactly 7 full days of articles to compute its picks; 8 was a
        # one-day buffer that no longer earns its keep given the Free-Plan
        # cap pressure.
        result = supabase.rpc('cleanup_stale_articles', {'days': 7}).execute()
        pruned = result.data if (result and result.data is not None) else 0
        print(f"  Article retention RPC: pruned {pruned} stale articles (>7 days)")
    except Exception as e:
        err_msg = str(e).lower()
        if "does not exist" in err_msg or "function" in err_msg and "not" in err_msg:
            print(f"  [info] cleanup_stale_articles RPC not yet applied — using legacy path")
        else:
            print(f"  [warn] cleanup_stale_articles RPC failed: {e} — using legacy path")

    # Diagnostic-table retention via cleanup_diagnostic_tables RPC (migration 060).
    # Prunes engine_snapshots (3 days), engine_runs (14 days), sandbox_runs
    # (7 days) in one call. Critical for Free-Plan projects with a 0.5 GB cap.
    # The 2026-06-01 outage was caused by engine_snapshots accumulating ~100 MB
    # of JSONB payloads with no retention policy. Non-fatal: pipeline continues
    # if the RPC is missing (migration 060 not yet applied).
    try:
        diag_result = supabase.rpc('cleanup_diagnostic_tables', {}).execute()
        d = diag_result.data if (diag_result and diag_result.data is not None) else {}
        if isinstance(d, dict):
            _snap = d.get('engine_snapshots_pruned', 0)
            _runs = d.get('engine_runs_pruned', 0)
            _sand = d.get('sandbox_runs_pruned', 0)
            _size = d.get('db_size_mb', 0)
            print(
                f"  Diagnostic retention RPC: pruned {_snap} snapshot(s), "
                f"{_runs} engine run(s), {_sand} sandbox run(s); "
                f"DB size now {_size} MB"
            )
            # Warn at 80% of Free-Plan cap (500 MB).
            try:
                if float(_size) > 400.0:
                    print(
                        f"  [WARN] DB size {_size} MB is above 80% of the 500 MB "
                        f"Free-Plan cap. Either upgrade to Pro or tighten retention."
                    )
            except (TypeError, ValueError):
                pass
        else:
            print(f"  Diagnostic retention RPC returned: {d}")
    except Exception as e:
        err_msg = str(e).lower()
        if "does not exist" in err_msg or ("function" in err_msg and "not" in err_msg):
            print(f"  [info] cleanup_diagnostic_tables RPC not yet applied (migration 060)")
        else:
            print(f"  [warn] cleanup_diagnostic_tables RPC failed: {e}")

    # Legacy article retention: delete articles older than 7 days (kept as
    # a defensive fallback in case the RPC above is missing or partial).
    # 7 days ensures the weekly digest's Sunday run has the full week of
    # data. ON DELETE CASCADE removes bias_scores, cluster_articles, and
    # article_categories. Daily briefs are PERMANENT.
    try:
        article_cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        old_article_ids: list[str] = []
        offset = 0
        while True:
            page = supabase.table("articles").select("id").lt(
                "published_at", article_cutoff
            ).range(offset, offset + 999).execute()
            if not page.data:
                break
            old_article_ids.extend(a["id"] for a in page.data)
            if len(page.data) < 1000:
                break
            offset += 1000

        if old_article_ids:
            for i in range(0, len(old_article_ids), 100):
                batch = old_article_ids[i:i + 100]
                supabase.table("articles").delete().in_("id", batch).execute()
            print(f"  Retention: removed {len(old_article_ids)} articles older than 7 days"
                  f" (+ cascaded bias_scores, article_categories)")
        else:
            print(f"  Retention: no articles older than 7 days")
    except Exception as e:
        print(f"  [warn] article retention failed: {e}")

    # Archive retention: prune entries older than 10 days (buffer past Sunday weekly digest)
    try:
        archive_cutoff = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        result = supabase.table("cluster_archive").delete().lt(
            "first_published", archive_cutoff
        ).execute()
        pruned = len(result.data) if result.data else 0
        if pruned:
            print(f"  Retention: pruned {pruned} archive entries older than 30 days")
    except Exception as e:
        print(f"  [warn] archive retention failed: {e}")

    # Finalize
    duration = time.time() - start_time

    # LLM telemetry — written to pipeline_runs.llm_metrics for ops visibility.
    # Cost estimate uses Sonnet 4.6 list price ($3 in / $15 out per MTok) with
    # rough avg token counts per call type. Treats every Claude call as Sonnet
    # since this build does not split tiers. Gemini fallback calls priced at $0.
    try:
        _claude_calls = claude_get_call_count()
    except Exception:
        _claude_calls = 0
    try:
        _gemini_calls = gemini_get_call_count()
    except Exception:
        _gemini_calls = 0
    _AVG_TOKENS_PER_CALL_USD = 0.0225  # ~3500 in × $3/M + 800 out × $15/M
    estimated_cost_usd = round(_claude_calls * _AVG_TOKENS_PER_CALL_USD, 4)
    cache_hit_rate = 0.0
    if summary_metrics["summarized"] + summary_metrics["cached"] > 0:
        cache_hit_rate = round(
            summary_metrics["cached"]
            / (summary_metrics["summarized"] + summary_metrics["cached"]),
            3,
        )
    llm_metrics = {
        "summaries_total": summary_metrics["summarized"],
        "cached_skips": summary_metrics["cached"],
        "skipped_other": summary_metrics["skipped"],
        "summary_failures": summary_metrics["failed"],
        "cache_hit_rate": cache_hit_rate,
        "llm_calls_claude": _claude_calls,
        "llm_calls_gemini": _gemini_calls,
        "llm_calls_total": _claude_calls + _gemini_calls,
        "estimated_cost_usd": estimated_cost_usd,
        "top50_coverage_pct": round(
            100 * (summary_metrics["summarized"] + summary_metrics["cached"]) / 50, 1
        ),
    }

    if run_id:
        update_pipeline_run(
            run_id=run_id,
            status="completed",
            articles_fetched=len(stored_articles),
            articles_analyzed=articles_analyzed,
            clusters_created=clusters_created,
            errors=fetch_errors[:50],
            duration_seconds=round(duration, 2),
            llm_metrics=llm_metrics,
        )

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Sources: {len(sources)} | Articles: {len(stored_articles)} "
          f"| Analyzed: {articles_analyzed} | Clusters: {clusters_created}")
    print(
        f"  LLM: {llm_metrics['llm_calls_total']} calls "
        f"(claude={_claude_calls}, gemini={_gemini_calls}) | "
        f"top50: {llm_metrics['top50_coverage_pct']}% covered "
        f"({llm_metrics['summaries_total']} new, {llm_metrics['cached_skips']} cached) | "
        f"~${estimated_cost_usd:.2f}"
    )
    print(f"  Errors: {len(fetch_errors)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
