#!/usr/bin/env python3
"""Can the outlet baselines be derived from our own data? Measure, don't guess.

THE TRAP THIS AVOIDS. The published `political_lean` is `baseline + shift`, so
deriving a baseline from it would read the engine's own output back into its
own prior. That loop was cut on 2026-09-22 (`tests/test_lean_prior_is_not_self_fed.py`)
and must not be reopened by the very work meant to fix the baselines.

The only non-circular signal stored per article is `rationale.lean.keyword_score`:
the lexicon's reading of the text alone, with no knowledge of the outlet. This
script measures that signal and nothing else.

WHAT IT MEASURES, and why each number decides something:

  usable rows          an article the scorer could actually read: 150+ words
                       (the full-confidence threshold), its outlet placed on
                       the left/right axis, and not marked `lean_unscored`.
  signal-bearing rows  of those, the ones where the lexicon fired at all.
                       `keyword_score` is exactly 50.0 when zero terms match,
                       and that is most of them. This is the real sample size,
                       and confusing it with the usable count is what made an
                       earlier estimate of this work too optimistic.
  rho                  Spearman rank correlation between an outlet's mean text
                       score and its label's numeric baseline. This is the
                       question "is the signal real?", and it is a RANK
                       correlation because the magnitudes are known to differ.
  ranges               the text scores' spread against the label ladder's. This
                       is the question "is the signal strong enough to publish
                       as a number?", which is a different question from
                       whether it is real.

Run it against a state snapshot, which is the only place the article rows live
(`pipeline_state.db` is gitignored and dies with its container; the durable copy
is the `void-state-snapshot` Actions artifact):

    python3 scripts/roster/measure_lean_signal.py /path/to/pipeline_state.db
"""
from __future__ import annotations

import collections
import json
import math
import sqlite3
import statistics
import sys

BASELINE = {"far-left": 10, "left": 20, "center-left": 35, "center": 50,
            "center-right": 65, "right": 80, "far-right": 90}

# The word count at which the engine grants full text authority
# (`_LENGTH_FULL_CONFIDENCE` in pipeline/analyzers/political_lean.py). Below it
# the text is discounted, so an article under it is not evidence about its
# outlet even when the lexicon fires.
FULL_CONFIDENCE_WORDS = 150

# `keyword_score` is exactly this when no lexicon term matched. Compared with a
# tolerance rather than `== 50` because it arrives as a float through JSON.
NO_SIGNAL = 50.0
EPS = 1e-9


def spearman(xs: list[float], ys: list[float]) -> float:
    """Rank correlation, ties averaged. No scipy in this environment."""
    def ranks(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        out = [0.0] * len(v)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out
    rx, ry = ranks(xs), ranks(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx)
                    * sum((b - my) ** 2 for b in ry))
    return num / den if den else float("nan")


def keyword_score(raw: str | None):
    """`rationale.lean.keyword_score`, through the double encoding it arrives in."""
    if not raw:
        return None
    try:
        doc = json.loads(raw)
        if isinstance(doc, str):        # stored as a JSON string of JSON
            doc = json.loads(doc)
        return (doc.get("lean") or {}).get("keyword_score")
    except Exception:
        return None


def load(db_path: str) -> tuple[list[dict], dict]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = []
    q = """select s.slug, s.name, s.country, s.tier,
                  s.political_lean_baseline lab, a.word_count wc,
                  b.political_lean published, b.lean_unscored unscored,
                  b.rationale rat
           from articles a
           join bias_scores b on b.article_id = a.id
           join sources s on s.id = a.source_id"""
    total = 0
    for r in conn.execute(q):
        total += 1
        rows.append({"slug": r["slug"], "name": r["name"],
                     "country": r["country"], "tier": r["tier"],
                     "lab": (r["lab"] or "").lower(), "wc": r["wc"] or 0,
                     "published": r["published"], "unscored": r["unscored"],
                     "kw": keyword_score(r["rat"])})
    return rows, {"total": total}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    rows, meta = load(sys.argv[1])
    print(f"article rows with a bias score: {meta['total']:,}")

    usable = [r for r in rows
              if r["lab"] in BASELINE and r["wc"] >= FULL_CONFIDENCE_WORDS
              and not r["unscored"]]
    print(f"  usable (placed, {FULL_CONFIDENCE_WORDS}+ words, scored): "
          f"{len(usable):,} ({len(usable) / max(meta['total'], 1) * 100:.1f}%)")
    scored = [r for r in usable if r["kw"] is not None]
    signal = [r for r in scored if abs(r["kw"] - NO_SIGNAL) >= EPS]
    print(f"  of those, carrying a stored keyword score: {len(scored):,}")
    print(f"  of those, the lexicon fired at all: {len(signal):,} "
          f"({len(signal) / max(len(scored), 1) * 100:.1f}%)")
    print(f"  so {len(scored) - len(signal):,} usable articles "
          f"({(len(scored) - len(signal)) / max(len(scored), 1) * 100:.1f}%) "
          f"contribute NOTHING about their outlet")

    by = collections.defaultdict(lambda: {"sig": [], "lab": "", "name": "",
                                          "country": ""})
    for r in signal:
        e = by[r["slug"]]
        e["lab"], e["name"], e["country"] = r["lab"], r["name"], r["country"]
        e["sig"].append(r["kw"])
    ns = sorted(len(v["sig"]) for v in by.values())
    print(f"\noutlets with any signal: {len(by)}, "
          f"median signal-bearing articles {ns[len(ns) // 2] if ns else 0}")
    for floor in (5, 10, 25, 30, 50, 100):
        print(f"  n >= {floor:3d}: {sum(1 for x in ns if x >= floor):>4} outlets")

    print("\nis the signal real? (Spearman against the label's own baseline)")
    for floor in (5, 10, 25):
        ok = {k: v for k, v in by.items() if len(v["sig"]) >= floor}
        if len(ok) < 5:
            continue
        lab = [BASELINE[v["lab"]] for v in ok.values()]
        txt = [statistics.mean(v["sig"]) for v in ok.values()]
        us = [v for v in ok.values() if v["country"] == "US"]
        non = [v for v in ok.values() if v["country"] != "US"]
        def rho_of(group):
            if len(group) < 5:
                return float("nan")
            return spearman([BASELINE[v["lab"]] for v in group],
                            [statistics.mean(v["sig"]) for v in group])
        print(f"  n>={floor:2d}: {len(ok):3d} outlets  rho={spearman(lab, txt):+.3f}"
              f"   US({len(us)}) {rho_of(us):+.3f}"
              f"   non-US({len(non)}) {rho_of(non):+.3f}")
        print(f"         text spread {min(txt):.1f}-{max(txt):.1f} "
              f"({max(txt) - min(txt):.1f} pts) against the ladder's "
              f"{min(lab)}-{max(lab)} ({max(lab) - min(lab)} pts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
