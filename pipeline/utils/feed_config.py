"""Feed-size constants: ONE source of truth for Python, TypeScript, shell and CI.

The numbers live in frontend/config/feed.json (inside the Next.js root so the
frontend can import the same file at build time; see frontend/app/lib/
feedConfig.ts). Before 2026-09-06 the displayed size was a literal in eleven
places across two languages (HomeContent.tsx EDITION_FEED_SIZE=50, six
`limit=50` calls in main.py, FEED_CAP_END=50, evals/run_eval.py, the print
archive cap, the export warning floor) kept in sync by comments alone.

Keys:
  displayed      cards on the homepage (the CEO's feed size)
  candidates     Stage 2 bench: clusters that get summaries, critique and
                 validation; the displayed set is a subset of the survivors
  pool           rows fetched by rank before the display filter (headroom for
                 the near-dup guard and the source_count >= 3 filter)
  minDisplayable build fails below this many displayable rows
  leadBand       the top-N band the diversity partition and lead gates govern
  archiveCap     stories printed per edition (printed_stories CHECK allows 1..50)
"""
from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
CONFIG_PATH = _REPO / "frontend" / "config" / "feed.json"


def load_feed_config(path: Path = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    for key in ("displayed", "candidates", "pool", "minDisplayable", "leadBand", "archiveCap"):
        if not isinstance(cfg.get(key), int) or cfg[key] <= 0:
            raise ValueError(f"feed.json: {key} must be a positive integer")
    if not (cfg["displayed"] <= cfg["candidates"] <= cfg["pool"]):
        raise ValueError("feed.json: require displayed <= candidates <= pool")
    if cfg["minDisplayable"] > cfg["displayed"]:
        raise ValueError("feed.json: minDisplayable must not exceed displayed")
    if cfg["archiveCap"] > 50:
        raise ValueError("feed.json: archiveCap exceeds the printed_stories CHECK (1..50)")
    return cfg


_CFG = load_feed_config()
DISPLAYED: int = _CFG["displayed"]
CANDIDATES: int = _CFG["candidates"]
POOL: int = _CFG["pool"]
MIN_DISPLAYABLE: int = _CFG["minDisplayable"]
LEAD_BAND: int = _CFG["leadBand"]
ARCHIVE_CAP: int = _CFG["archiveCap"]

__all__ = [
    "CONFIG_PATH", "load_feed_config", "DISPLAYED", "CANDIDATES", "POOL",
    "MIN_DISPLAYABLE", "LEAD_BAND", "ARCHIVE_CAP",
]
