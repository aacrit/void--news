"""Feed-size constants: ONE source of truth for Python, TypeScript, shell and CI.

The numbers live in frontend/config/feed.json (inside the Next.js root so the
frontend can import the same file at build time; see frontend/app/lib/
feedConfig.ts). Before 2026-09-06 the displayed size was a literal in eleven
places across two languages (HomeContent.tsx EDITION_FEED_SIZE=50, six
`limit=50` calls in main.py, FEED_CAP_END=50, evals/run_eval.py, the print
archive cap, the export warning floor) kept in sync by comments alone.

Keys:
  displayed      cards on the homepage (the CEO's feed size)
  moreStories    the "More stories" band under the cards: up to this many of
                 the next ranks, as headline links to their printed pages
                 (CEO 2026-10-28, phase 1 of the 30-story evaluation). Never
                 required: a short day shows fewer, minDisplayable is unchanged
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
    for key in ("displayed", "moreStories", "candidates", "pool", "minDisplayable",
                "leadBand", "archiveCap"):
        if not isinstance(cfg.get(key), int) or cfg[key] <= 0:
            raise ValueError(f"feed.json: {key} must be a positive integer")
    if not (cfg["displayed"] <= cfg["candidates"] <= cfg["pool"]):
        raise ValueError("feed.json: require displayed <= candidates <= pool")
    if cfg["minDisplayable"] > cfg["displayed"]:
        raise ValueError("feed.json: minDisplayable must not exceed displayed")
    if cfg["displayed"] + cfg["moreStories"] > cfg["candidates"]:
        raise ValueError("feed.json: displayed + moreStories must fit in the candidates bench")
    if cfg["archiveCap"] < cfg["displayed"] + cfg["moreStories"]:
        # The band links to /story/ pages, which exist only for printed stories.
        raise ValueError("feed.json: archiveCap must print every shipped story "
                         "(displayed + moreStories)")
    if cfg["archiveCap"] > 50:
        raise ValueError("feed.json: archiveCap exceeds the printed_stories CHECK (1..50)")
    return cfg


_CFG = load_feed_config()
DISPLAYED: int = _CFG["displayed"]
MORE_STORIES: int = _CFG["moreStories"]
# Everything a reader can open from the front page: the cards and the band.
# The rigor gate and the cut hold every one of them to the same standard.
SHIPPED: int = DISPLAYED + MORE_STORIES
CANDIDATES: int = _CFG["candidates"]
POOL: int = _CFG["pool"]
MIN_DISPLAYABLE: int = _CFG["minDisplayable"]
LEAD_BAND: int = _CFG["leadBand"]
ARCHIVE_CAP: int = _CFG["archiveCap"]

__all__ = [
    "CONFIG_PATH", "load_feed_config", "DISPLAYED", "MORE_STORIES", "SHIPPED",
    "CANDIDATES", "POOL",
    "MIN_DISPLAYABLE", "LEAD_BAND", "ARCHIVE_CAP",
]
