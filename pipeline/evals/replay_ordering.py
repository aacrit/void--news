#!/usr/bin/env python3
"""Offline replay of apply_feed_ordering over committed feed snapshots.

Every ranking change since rev 56 has been justified by "replay the real rows"
(docs/PHASE2-CHANGES-2026-08-10.md: "reproduces stored rank_world exactly
through rank 31"), but the harness was rebuilt by hand each time and never
committed. This is that harness.

It reads `frontend/build-data/feed.json` (and `archive.json` for content_type)
straight out of git history, runs the REAL `feed_ranker.apply_feed_ordering`
over the snapshot, and reports which stories the gates and caps moved. No DB,
no network, no LLM, $0.

THE SILENT-NO-OP TRAP. `feed_ranker._dup_title_stems_fn()` returns None when
`clustering.story_cluster` cannot import (it needs numpy and spaCy), and stages
3.6 (near-duplicate removal) and 3.7 (dynamic same-event cap) then skip with no
warning. An offline replay without a stemmer produces a different, entirely
plausible order and misses exactly the mechanism most ranking bugs live in. So
this harness INJECTS `evals.checks._title_stems` (Porter when nltk is present,
a local stripper otherwise) and refuses to run if the injection did not take.

Usage:
    python -m pipeline.evals.replay_ordering                  # last 6 snapshots
    python -m pipeline.evals.replay_ordering --commits 10
    python -m pipeline.evals.replay_ordering --displayed 50   # what the old cap did
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

_PIPELINE_DIR = Path(__file__).resolve().parent.parent
if str(_PIPELINE_DIR) not in sys.path:
    sys.path.insert(0, str(_PIPELINE_DIR))

from evals import checks as _checks  # noqa: E402
from ranker import feed_ranker as fr  # noqa: E402
from utils.display_window import is_displayable  # noqa: E402
from utils.feed_config import DISPLAYED  # noqa: E402

FEED_PATH = "frontend/build-data/feed.json"
ARCHIVE_PATH = "frontend/build-data/archive.json"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True,
                                   stderr=subprocess.DEVNULL)


def snapshot_commits(limit: int) -> list[tuple[str, str]]:
    """(commit, date) for the most recent commits that touched feed.json."""
    out = _git("log", f"-{limit}", "--format=%h %ad", "--date=short",
               "--", FEED_PATH).strip().splitlines()
    return [tuple(line.split(None, 1)) for line in out if line.strip()]


def load_snapshot(commit: str) -> tuple[list[dict], dict]:
    feed = json.loads(_git("show", f"{commit}:{FEED_PATH}"))["clusters"]
    content_types: dict[str, str] = {}
    try:
        archive = json.loads(_git("show", f"{commit}:{ARCHIVE_PATH}"))
        latest = max(r["printed_on"] for r in archive)
        for row in archive:
            if row.get("printed_on") == latest and row.get("source_cluster_id"):
                content_types[row["source_cluster_id"]] = row.get("content_type") or "reporting"
    except Exception:
        pass
    return feed, content_types


# `disaster_severity` is not in older snapshots (export_static started emitting
# it 2026-09-06). Recompute it from the title, which is what the ranker does
# whenever the title alone fires: importance_ranker._breaking_disaster_score
# returns the title score when the title carries a hazard noun or a toll.
def _title_disaster_severity(title: str) -> float:
    try:
        from ranker.importance_ranker import _score_disaster_text
    except Exception:
        return 0.0
    try:
        score, _ = _score_disaster_text(title or "")
        return float(score or 0.0)
    except Exception:
        return 0.0


def prepare(feed: list[dict], content_types: dict) -> list[dict]:
    rows = []
    for c in feed:
        r = dict(c)
        r.setdefault("content_type", content_types.get(c["id"], "reporting"))
        if r.get("disaster_severity") in (None, ""):
            r["disaster_severity"] = _title_disaster_severity(r.get("title", ""))
        r["rank_world"] = r.get("headline_rank") or 0
        rows.append(r)
    return rows


def order(rows: list[dict], displayed: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Return (base, pre_partition, final) displayable orderings."""
    work = [dict(r) for r in rows]
    fr.apply_feed_ordering(work, None)
    base = [r for r in sorted(work, key=lambda r: -(r.get("headline_rank") or 0))
            if is_displayable(r)]
    pre = [r for r in sorted(work, key=lambda r: -r.get("_base_rank", r["rank_world"]))
           if is_displayable(r)]
    final = [r for r in sorted(work, key=lambda r: -r["rank_world"]) if is_displayable(r)]
    return base[:displayed * 3], pre, final


def why(row: dict) -> str:
    bits = []
    if row.get("_near_dup_removed"):
        bits.append(f'near-dup of "{(row.get("_near_dup_of") or "")[:40]}"')
    if row.get("_same_event_anchor"):
        bits.append(f'dynamic same-event cap [{row["_same_event_anchor"]}]')
    ev = fr._detect_event((row.get("title") or "").lower())
    if ev:
        bits.append(f"static event group [{ev}]")
    if fr._is_opinion(row):
        bits.append("opinion gate")
    if row.get("_coverage_guard_kept"):
        bits.append("coverage guard")
    if row.get("_mass_casualty_floor"):
        bits.append("mass-casualty floor")
    return "; ".join(bits) or "category cap / diversity partition"


def replay(commit: str, date: str, displayed: int) -> dict:
    feed, content_types = load_snapshot(commit)
    rows = prepare(feed, content_types)
    base, pre, final = order(rows, displayed)
    bpos = {r["id"]: i + 1 for i, r in enumerate(base)}
    ppos = {r["id"]: i + 1 for i, r in enumerate(pre)}
    fpos = {r["id"]: i + 1 for i, r in enumerate(final)}

    gate_out, cap_out = [], []
    for r in final:
        if bpos.get(r["id"], 999) > displayed:
            continue
        if fpos[r["id"]] <= displayed:
            continue
        (gate_out if ppos.get(r["id"], 999) > displayed else cap_out).append(r)

    print("=" * 96)
    print(f"{date}  {commit}   {len(feed)} clusters, {len(final)} displayable, "
          f"showing top {displayed}")
    print(f"  categories in the displayed feed: "
          f"{dict(Counter(r['category'] for r in final[:displayed]))}")
    srcs = [r.get("source_count", 0) for r in final[:displayed]]
    if srcs:
        print(f"  source_count in the displayed feed: min {min(srcs)}, "
              f"median {sorted(srcs)[len(srcs)//2]}, max {max(srcs)}")
    print(f"  base-top-{displayed} stories pushed out by GATES: {len(gate_out)}")
    for r in gate_out:
        print(f"    base#{bpos[r['id']]:<3} -> #{fpos[r['id']]:<3} "
              f"src={r.get('source_count', 0):<3} {r['title'][:58]!r}")
        print(f"        {why(r)}")
    print(f"  base-top-{displayed} stories pushed out by the CATEGORY CAP: {len(cap_out)}")
    for r in cap_out:
        print(f"    base#{bpos[r['id']]:<3} -> #{fpos[r['id']]:<3} "
              f"src={r.get('source_count', 0):<3} cat={r.get('category')} "
              f"{r['title'][:52]!r}")
    return {"date": date, "commit": commit, "gate_out": len(gate_out),
            "cap_out": len(cap_out), "displayable": len(final)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commits", type=int, default=6,
                    help="how many committed feed.json snapshots to replay")
    ap.add_argument("--displayed", type=int, default=DISPLAYED,
                    help="feed size to replay at (default: frontend/config/feed.json)")
    args = ap.parse_args()

    # Guard the silent no-op: without a stemmer, stages 3.6 and 3.7 skip.
    fr._DUP_STEMS_CACHED = _checks._title_stems
    if fr._dup_title_stems_fn() is None:
        print("FATAL: no title stemmer; stages 3.6 and 3.7 would silently skip.")
        return 2
    probe = fr._dup_title_stems_fn()("Rescuers Pull Two People Alive From Nepal Debris")
    if len(probe) < 4:
        print(f"FATAL: stemmer returned {probe}; refusing to replay on a broken tokenizer.")
        return 2
    print(f"stemmer: {fr._dup_title_stems_fn().__module__}.{fr._dup_title_stems_fn().__name__} "
          f"({len(probe)} stems on the probe title)")

    commits = snapshot_commits(args.commits)
    if not commits:
        print(f"No commits touch {FEED_PATH}")
        return 1
    results = [replay(c, d, args.displayed) for c, d in commits]
    print("=" * 96)
    print(f"TOTAL over {len(results)} snapshots at {args.displayed} slots: "
          f"{sum(r['gate_out'] for r in results)} gate displacements, "
          f"{sum(r['cap_out'] for r in results)} category-cap displacements")
    return 0


if __name__ == "__main__":
    sys.exit(main())
