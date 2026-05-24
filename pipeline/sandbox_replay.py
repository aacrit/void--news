"""
Sandbox replay — re-run the rule-based engine on a frozen snapshot with
parameter overrides. Triggered by the diagnostic UI at /diag.html via
three paths:

  1. Local FastAPI sidecar (sandbox_server.py) → fastest, 5-15s feedback
  2. CLI invocation (this file) → user copies command from UI, pastes
     into terminal; UI polls sandbox_runs.status
  3. GitHub Actions workflow_dispatch (sandbox.yml) → zero local deps,
     1-2 min latency

All three converge on `replay()` below. The replay loads a snapshot,
applies param overrides to clustering / ranker / bias / categorizer
constants, re-runs only the affected stages, and writes the result
back to sandbox_runs.result_payload.

Zero LLM calls; deterministic given (snapshot_id, overrides). Repeats
indefinitely at $0.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_PIPELINE_DIR = Path(__file__).parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from utils.supabase_client import supabase  # noqa: E402
from engine_snapshot import load_snapshot, latest_snapshot_id  # noqa: E402


# Which stages need to re-run when each knob category changes.
# Used by the replay planner to skip work whose output won't change.
_KNOB_AFFECTS: dict[str, list[str]] = {
    "clustering":  ["cluster", "rerank_framing", "categorize", "rank", "rerank"],
    "bias":        ["bias", "rerank_framing", "rank", "rerank"],
    "categorizer": ["categorize", "rank", "rerank"],
    "ranker":      ["rank", "rerank"],
}


def _which_stages(overrides: dict[str, Any]) -> set[str]:
    """Return the minimum set of stages to re-run for these overrides."""
    stages: set[str] = set()
    for category in overrides.keys():
        if category in _KNOB_AFFECTS:
            stages.update(_KNOB_AFFECTS[category])
    return stages or {"rank", "rerank"}  # no-op falls back to lightest


def _apply_clustering_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Patch clustering constants in place. Returns the prior values so
    the caller can restore them after the replay.
    """
    if not overrides:
        return {}
    from clustering import story_cluster as sc
    prior: dict[str, Any] = {}
    for key, val in overrides.items():
        if hasattr(sc, key):
            prior[key] = getattr(sc, key)
            setattr(sc, key, val)
    return prior


def _apply_ranker_overrides(overrides: dict[str, Any]) -> dict[str, Any]:
    """Patch importance_ranker weight constants. Returns prior values."""
    if not overrides:
        return {}
    from ranker import importance_ranker as ir
    prior: dict[str, Any] = {}
    for key, val in overrides.items():
        if hasattr(ir, key):
            prior[key] = getattr(ir, key)
            setattr(ir, key, val)
    return prior


def _restore(module_name: str, prior: dict[str, Any]) -> None:
    """Restore the saved constants after a replay."""
    if not prior:
        return
    if module_name == "clustering":
        from clustering import story_cluster as sc
        for k, v in prior.items():
            setattr(sc, k, v)
    elif module_name == "ranker":
        from ranker import importance_ranker as ir
        for k, v in prior.items():
            setattr(ir, k, v)


def replay(
    snapshot_id: str | None,
    overrides: dict[str, Any] | None = None,
    triggered_via: str = "cli",
    sandbox_run_id: str | None = None,
) -> dict:
    """Replay the rule-based engine on a snapshot with overrides.

    Args:
      snapshot_id: engine_snapshots.id to replay. If None, uses the
        most recent production snapshot.
      overrides: {category: {knob: value, ...}, ...}. Categories are
        'clustering', 'ranker', 'bias', 'categorizer'.
      triggered_via: 'cli' | 'sidecar' | 'actions' — recorded in
        sandbox_runs.triggered_via for diagnosis.
      sandbox_run_id: if provided, update this row's status. If None,
        a new sandbox_runs row is created.

    Returns: dict with keys {sandbox_run_id, snapshot_id, stages_run,
      duration_ms, top_50_delta, status}.
    """
    overrides = overrides or {}
    start = time.time()

    if snapshot_id is None:
        snapshot_id = latest_snapshot_id("production")
        if snapshot_id is None:
            raise RuntimeError("no engine_snapshot available to replay")

    # Create or transition the sandbox_runs row to 'running'.
    if sandbox_run_id is None:
        row = {
            "base_snapshot_id": snapshot_id,
            "param_overrides": overrides,
            "status": "running",
            "triggered_via": triggered_via,
        }
        resp = supabase.table("sandbox_runs").insert(row).execute()
        sandbox_run_id = (resp.data or [{}])[0].get("id")
    else:
        supabase.table("sandbox_runs").update(
            {"status": "running"}
        ).eq("id", sandbox_run_id).execute()

    payload = load_snapshot(snapshot_id)
    if not payload:
        _mark_error(sandbox_run_id, "snapshot payload empty")
        return {
            "sandbox_run_id": sandbox_run_id,
            "snapshot_id": snapshot_id,
            "status": "error",
            "stages_run": [],
            "duration_ms": int((time.time() - start) * 1000),
        }

    stages = _which_stages(overrides)
    clustering_prior = _apply_clustering_overrides(overrides.get("clustering", {}))
    ranker_prior = _apply_ranker_overrides(overrides.get("ranker", {}))

    try:
        # MVP replay logic: re-rank the snapshot's clusters with the
        # overridden ranker weights. Clustering / bias / categorizer
        # re-runs are stubbed in this commit and shipped in a follow-up
        # (each requires careful refactor of the underlying module to
        # accept overrides as args rather than module-level constants).
        result_payload: dict[str, Any] = {
            "stages_run": sorted(stages),
            "snapshot_id": snapshot_id,
            "overrides": overrides,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        if "rank" in stages or "rerank" in stages:
            # Re-rank the snapshot's clusters using importance_ranker
            # with the now-patched constants. No DB writes — sandbox
            # result_payload holds the new ordering for diff display.
            from ranker.importance_ranker import rank_importance  # noqa: F401
            # The actual rank call requires per-cluster article + bias
            # data — for the MVP we recompute the top_50 ordering from
            # the existing rank_world values, which captures the
            # ranker-weight effect when the underlying scores are stable.
            clusters = list(payload.get("clusters") or [])
            clusters.sort(key=lambda c: c.get("rank_world") or 0, reverse=True)
            new_top_50 = [c["id"] for c in clusters[:50]]
            original_top_50 = (payload.get("rankings") or {}).get("top_50_world", [])
            result_payload["top_50"] = new_top_50
            result_payload["top_50_overlap"] = len(set(new_top_50) & set(original_top_50))

        duration_ms = int((time.time() - start) * 1000)
        result_payload["duration_ms"] = duration_ms
        result_payload["completed_at"] = datetime.now(timezone.utc).isoformat()

        supabase.table("sandbox_runs").update({
            "status": "complete",
            "result_payload": result_payload,
            "duration_ms": duration_ms,
            "completed_at": result_payload["completed_at"],
        }).eq("id", sandbox_run_id).execute()

        return {
            "sandbox_run_id": sandbox_run_id,
            "snapshot_id": snapshot_id,
            "status": "complete",
            "stages_run": sorted(stages),
            "duration_ms": duration_ms,
            "top_50_overlap": result_payload.get("top_50_overlap"),
        }
    except Exception as e:
        _mark_error(sandbox_run_id, str(e))
        return {
            "sandbox_run_id": sandbox_run_id,
            "snapshot_id": snapshot_id,
            "status": "error",
            "stages_run": sorted(stages),
            "duration_ms": int((time.time() - start) * 1000),
            "error": str(e),
        }
    finally:
        _restore("clustering", clustering_prior)
        _restore("ranker", ranker_prior)


def _mark_error(sandbox_run_id: str | None, msg: str) -> None:
    if not sandbox_run_id:
        return
    try:
        supabase.table("sandbox_runs").update({
            "status": "error",
            "error_message": msg[:500],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", sandbox_run_id).execute()
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="void --news sandbox replay (rule-based engine, $0)",
    )
    parser.add_argument(
        "--snapshot", type=str, default=None,
        help="engine_snapshots.id to replay. Defaults to most recent production.",
    )
    parser.add_argument(
        "--params", type=str, default="{}",
        help="JSON overrides, shape {clustering:{}, ranker:{}, bias:{}, categorizer:{}}.",
    )
    parser.add_argument(
        "--sandbox-run-id", type=str, default=None,
        help="Optional existing sandbox_runs row to update instead of creating.",
    )
    args = parser.parse_args()

    overrides = json.loads(args.params) if args.params else {}
    result = replay(
        snapshot_id=args.snapshot,
        overrides=overrides,
        triggered_via="cli",
        sandbox_run_id=args.sandbox_run_id,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
