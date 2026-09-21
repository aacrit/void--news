#!/usr/bin/env python3
"""Regenerate the BUSIEST list in frontend/test/bench.test.mjs.

The Bench sizes its marks from the busiest lean bucket in a story, so the
packing gate is only worth anything if it runs against the counts the feed
actually produces. This prints them, largest first, in the shape the test file
pastes in.

One entry per SOURCE NAME (the Deep Dive dedupes that way) and `lean_unscored`
rows excluded (the Bench does not seat them), so the numbers here are exactly
what `packBench` is handed in the browser.

    python3 tests/bench_corpus.py
"""
from __future__ import annotations

import collections
import glob
import json
import os
import statistics

# The seven outlet baselines, and the nearest-rung binning with a centre-ward
# tie. Mirrors pipeline/utils/bias_aggregation.py and biasColors.leanToBucket;
# tests/test_bias_bins.py is what holds those two together.
BASELINES = (
    ("far_left", 10), ("left", 20), ("center_left", 35), ("center", 50),
    ("center_right", 65), ("right", 80), ("far_right", 90),
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEEPDIVE = os.path.join(ROOT, "frontend", "public", "data", "deepdive", "*.json")


def bin_of(value: float) -> str:
    best, best_gap, best_pull = "center", float("inf"), float("inf")
    for name, base in BASELINES:
        gap, pull = abs(value - base), abs(base - 50)
        if gap < best_gap - 1e-9 or (abs(gap - best_gap) < 1e-9 and pull < best_pull):
            best, best_gap, best_pull = name, gap, pull
    return best


def busiest_per_cluster() -> list[int]:
    out: list[int] = []
    for path in sorted(glob.glob(DEEPDIVE)):
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        counts: collections.Counter = collections.Counter()
        seen: set[str] = set()
        for row in rows or []:
            article = (row or {}).get("article") or {}
            name = ((article.get("source") or {}).get("name") or "").strip().lower()
            if not name or name in seen:
                continue
            seen.add(name)
            scores = article.get("bias_scores") or []
            if not scores:
                continue
            bias = scores[0]
            if bias.get("lean_unscored"):
                continue
            lean = bias.get("political_lean")
            if not isinstance(lean, (int, float)) or isinstance(lean, bool):
                continue
            counts[bin_of(float(lean))] += 1
        if counts:
            out.append(max(counts.values()))
    return sorted(out, reverse=True)


def main() -> None:
    busiest = busiest_per_cluster()
    if not busiest:
        print("no deepdive exports found under frontend/public/data/deepdive/")
        return
    print(f"clusters: {len(busiest)}")
    print(f"busiest bucket: min {min(busiest)}, median "
          f"{statistics.median(busiest):g}, max {max(busiest)}")
    print("\nconst BUSIEST = [")
    for i in range(0, len(busiest), 18):
        print("  " + ", ".join(str(n) for n in busiest[i:i + 18]) + ",")
    print("];")


if __name__ == "__main__":
    main()
