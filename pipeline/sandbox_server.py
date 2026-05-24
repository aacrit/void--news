"""
Sandbox server — local FastAPI sidecar for the diagnostic UI's "Re-run
(sidecar)" trigger. Start with:

    python -m pipeline.sandbox_server

Listens on localhost:8888. Accepts POST /replay with JSON body:
    {snapshot_id?: str, overrides: {clustering?: {...}, ranker?: {...}}}
Returns the sandbox_runs row id; UI polls the table for status.

Only loaded when the user wants the fastest feedback loop (5-15s vs
1-2min for the GH Actions trigger). CORS allowed for any localhost
origin so the standalone diag.html (file:// or hosted) can call in.

Requires: pip install fastapi uvicorn (added to requirements.txt for
local dev only; not required by production pipeline).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PIPELINE_DIR = Path(__file__).parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print(
        "[sandbox_server] requires `pip install fastapi uvicorn`.\n"
        "  Run: pip install fastapi uvicorn  (dev dependency only)"
    )
    sys.exit(1)

from sandbox_replay import replay  # noqa: E402
from engine_snapshot import latest_snapshot_id  # noqa: E402


app = FastAPI(title="void --news sandbox", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class ReplayRequest(BaseModel):
    snapshot_id: str | None = None
    overrides: dict = {}
    sandbox_run_id: str | None = None


@app.get("/health")
def health():
    return {"ok": True, "service": "void-sandbox-sidecar"}


@app.get("/latest-snapshot")
def latest():
    sid = latest_snapshot_id("production")
    if not sid:
        raise HTTPException(404, "no production engine_snapshot found")
    return {"snapshot_id": sid}


@app.post("/replay")
def trigger_replay(req: ReplayRequest):
    """Synchronously run a replay and return the result. The diag UI
    can either await this directly (5-15s typical) or kick it and poll
    sandbox_runs by id.
    """
    try:
        result = replay(
            snapshot_id=req.snapshot_id,
            overrides=req.overrides,
            triggered_via="sidecar",
            sandbox_run_id=req.sandbox_run_id,
        )
        return result
    except Exception as e:
        raise HTTPException(500, f"replay failed: {e}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="void sandbox sidecar")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8888)
    args = parser.parse_args()
    print(f"void --news sandbox sidecar starting on http://{args.host}:{args.port}")
    print("  POST /replay        — trigger a sandbox replay")
    print("  GET  /latest-snapshot — current production snapshot id")
    print("  GET  /health        — liveness probe")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
