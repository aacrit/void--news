"""
Engine snapshot — frozen rule-based-engine output, the contract between
Stage A (engine: free, deterministic, infinitely re-runnable) and Stage B
(editorial: LLM, costly, opaque).

A snapshot captures the complete output of:
  • Fetched + scraped articles (corpus)
  • Per-article bias scores (6 axes + rationale)
  • Clusters with their member article ids
  • Per-edition rankings (rank_world, rank_us, ...)
  • Phase traces (which phase merged what, which Phase 5 caps fired)

It is written to engine_snapshots.payload (jsonb) at the end of the
rule-based stage. The editorial layer (cluster summarizer, daily brief,
weekly digest) reads from this snapshot only; never touches the engine
state directly. The sandbox at frontend/public/diag.html replays this
snapshot with parameter overrides at $0 cost.

Reuses utils/supabase_client.supabase. No LLM imports; no Anthropic SDK.
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Path setup so this can be imported from pipeline.main or from sandbox
# server with the same syntax.
_PIPELINE_DIR = Path(__file__).parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from utils.supabase_client import supabase  # noqa: E402


def build_payload(
    articles: list[dict],
    clusters: list[dict],
    rankings: dict[str, Any] | None = None,
    phase_traces: dict[str, Any] | None = None,
) -> dict:
    """Assemble the snapshot payload. Pure function over its inputs.

    The shape is the contract — change carefully. Sandbox replay and
    editorial layer both read from this exact structure.
    """
    return {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "articles": articles,
        "clusters": clusters,
        "rankings": rankings or {},
        "phase_traces": phase_traces or {},
    }


def write_snapshot(
    payload: dict,
    pipeline_run_id: str | None = None,
    source: str = "production",
    params: dict | None = None,
    step_timings: dict | None = None,
    step_errors: dict | None = None,
    sonnet_calls: int = 0,
    gemini_calls: int = 0,
) -> tuple[str | None, str | None]:
    """Insert a row into engine_runs + engine_snapshots. Returns
    (engine_run_id, engine_snapshot_id) or (None, None) on failure.

    Idempotent on retry — a new run row is created on each call. If the
    engine_runs / engine_snapshots tables don't exist yet (migration 057
    not applied), this logs a warning and returns (None, None) so the
    pipeline keeps running.
    """
    run_payload = {
        "source": source,
        "params": params or {},
        "step_timings": step_timings or {},
        "step_errors": step_errors or {},
        "cluster_count": len(payload.get("clusters") or []),
        "article_count": len(payload.get("articles") or []),
        "sonnet_calls": sonnet_calls,
        "gemini_calls": gemini_calls,
    }
    if pipeline_run_id:
        run_payload["pipeline_run_id"] = pipeline_run_id

    try:
        run_resp = supabase.table("engine_runs").insert(run_payload).execute()
        engine_run_id = (run_resp.data or [{}])[0].get("id")
    except Exception as e:
        print(f"  [warn] engine_runs insert failed: {e}")
        return None, None

    if not engine_run_id:
        print("  [warn] engine_runs insert returned no id")
        return None, None

    # Payload size for budget tracking. Cap at ~25 MB jsonb to avoid
    # Supabase REST timeouts; if exceeded, drop the per-article bias
    # rationale (kept in articles[i].bias_metadata) and rely on the DB
    # for fetches.
    payload_str = json.dumps(payload, default=str)
    payload_size = len(payload_str.encode("utf-8"))
    MAX_BYTES = 25 * 1024 * 1024
    if payload_size > MAX_BYTES:
        print(
            f"  [warn] payload size {payload_size:,}B exceeds {MAX_BYTES:,}B; "
            f"dropping per-article rationale to fit"
        )
        slim_articles = [
            {k: v for k, v in art.items() if k != "bias_metadata"}
            for art in (payload.get("articles") or [])
        ]
        payload = {**payload, "articles": slim_articles, "rationale_slim": True}
        payload_str = json.dumps(payload, default=str)
        payload_size = len(payload_str.encode("utf-8"))

    snapshot_row = {
        "engine_run_id": engine_run_id,
        "payload": payload,
        "payload_size_bytes": payload_size,
    }
    try:
        snap_resp = supabase.table("engine_snapshots").insert(snapshot_row).execute()
        snapshot_id = (snap_resp.data or [{}])[0].get("id")
        print(
            f"  Engine snapshot {snapshot_id[:8] if snapshot_id else '?'} written "
            f"({payload_size:,}B, {run_payload['article_count']} articles, "
            f"{run_payload['cluster_count']} clusters)"
        )
        return engine_run_id, snapshot_id
    except Exception as e:
        print(f"  [warn] engine_snapshots insert failed: {e}")
        return engine_run_id, None


def load_snapshot(snapshot_id: str) -> dict | None:
    """Fetch a snapshot payload by id. Returns None on missing/error."""
    try:
        resp = (
            supabase.table("engine_snapshots")
            .select("payload")
            .eq("id", snapshot_id)
            .single()
            .execute()
        )
        return (resp.data or {}).get("payload")
    except Exception as e:
        print(f"  [warn] load_snapshot({snapshot_id[:8]}) failed: {e}")
        return None


def latest_snapshot_id(source: str = "production") -> str | None:
    """Return the id of the most recent engine_snapshot for a given source.
    Used by the sandbox UI to pick a default baseline to replay against.
    """
    try:
        resp = (
            supabase.table("engine_runs")
            .select("id")
            .eq("source", source)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return None
        engine_run_id = rows[0]["id"]
        snap_resp = (
            supabase.table("engine_snapshots")
            .select("id")
            .eq("engine_run_id", engine_run_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        snap_rows = snap_resp.data or []
        return snap_rows[0]["id"] if snap_rows else None
    except Exception as e:
        print(f"  [warn] latest_snapshot_id failed: {e}")
        return None
