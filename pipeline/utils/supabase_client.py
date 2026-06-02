"""
Supabase client and helper functions for the void --news pipeline.

Loads credentials from environment variables and provides convenience
functions for common database operations.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError(
        "SUPABASE_URL and SUPABASE_KEY must be set in the environment. "
        "Create a .env file or set them as GitHub Actions secrets."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def insert_article(article: dict) -> dict | None:
    """
    Insert an article into the articles table.

    Args:
        article: Dict with keys matching the articles table columns:
            source_id, url, title, summary, full_text, author,
            published_at, section, image_url, word_count

    Returns:
        The inserted row as a dict, or None if the insert failed
        (e.g., duplicate URL).
    """
    try:
        result = supabase.table("articles").insert(article).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        # Duplicate URL or other constraint violation
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            print(f"  [skip] Duplicate article: {article.get('url', 'unknown')}")
        else:
            print(f"  [error] Failed to insert article: {e}")
    return None


def insert_bias_scores(scores: dict) -> dict | None:
    """
    Insert bias scores for an article.

    Args:
        scores: Dict with keys: article_id, political_lean, sensationalism,
            opinion_fact, factual_rigor, framing, confidence

    Returns:
        The inserted row as a dict, or None on failure.
    """
    try:
        result = supabase.table("bias_scores").insert(scores).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"  [error] Failed to insert bias scores: {e}")
    return None


def insert_cluster(cluster: dict) -> dict | None:
    """
    Insert a story cluster.

    Args:
        cluster: Dict with keys: title, summary, consensus_points,
            divergence_points, category, section, importance_score,
            source_count, first_published

    Returns:
        The inserted row as a dict, or None on failure.
    """
    try:
        result = supabase.table("story_clusters").insert(cluster).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"  [error] Failed to insert cluster: {e}")
    return None


def link_article_to_cluster(cluster_id: str, article_id: str) -> bool:
    """
    Link an article to a story cluster via the junction table.

    Returns:
        True if successful, False otherwise.
    """
    try:
        supabase.table("cluster_articles").insert({
            "cluster_id": cluster_id,
            "article_id": article_id,
        }).execute()
        return True
    except Exception as e:
        print(f"  [error] Failed to link article to cluster: {e}")
        return False


def create_pipeline_run() -> dict | None:
    """
    Create a new pipeline run record with status 'running'.

    Returns:
        The inserted row as a dict, or None on failure.
    """
    try:
        result = supabase.table("pipeline_runs").insert({
            "status": "running",
        }).execute()
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"  [error] Failed to create pipeline run: {e}")
    return None


def update_pipeline_run(
    run_id: str,
    status: str = "completed",
    articles_fetched: int = 0,
    articles_analyzed: int = 0,
    clusters_created: int = 0,
    errors: list | None = None,
    duration_seconds: float | None = None,
    llm_metrics: dict | None = None,
) -> dict | None:
    """
    Update a pipeline run record with final results.

    Args:
        run_id: UUID of the pipeline run to update.
        status: 'completed' or 'failed'.
        articles_fetched: Total articles fetched this run.
        articles_analyzed: Total articles with bias scores.
        clusters_created: Total story clusters formed.
        errors: List of error dicts [{source, error, timestamp}].
        duration_seconds: Total pipeline duration.
        llm_metrics: Optional dict with per-run LLM telemetry (call counts,
            cache hits, cost estimate). Persisted to pipeline_runs.llm_metrics.

    Returns:
        The updated row as a dict, or None on failure.
    """
    update_data = {
        "status": status,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "articles_fetched": articles_fetched,
        "articles_analyzed": articles_analyzed,
        "clusters_created": clusters_created,
        "errors": errors or [],
    }
    if duration_seconds is not None:
        update_data["duration_seconds"] = duration_seconds
    if llm_metrics is not None:
        update_data["llm_metrics"] = llm_metrics

    try:
        result = (
            supabase.table("pipeline_runs")
            .update(update_data)
            .eq("id", run_id)
            .execute()
        )
        if result.data:
            return result.data[0]
    except Exception as e:
        print(f"  [error] Failed to update pipeline run: {e}")
    return None


def get_active_sources() -> list[dict]:
    """
    Fetch all active sources from the database.

    Returns:
        List of source dicts.
    """
    try:
        result = (
            supabase.table("sources")
            .select("*")
            .eq("is_active", True)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"  [error] Failed to fetch sources: {e}")
        return []
