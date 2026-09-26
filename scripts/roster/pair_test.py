#!/usr/bin/env python3
"""The pair test: can the engine tell two outlets that disagree apart, on the SAME event?

WHY. `docs/proposals/OUTLET-BASELINE-PROGRAMME-2026-09-22.md` section 1 names this
as the decisive experiment before any work on deriving our own outlet baselines,
and the CEO authorised it on 2026-09-26. If the instrument cannot separate two
outlets that loathe each other writing about the same event, no corpus size fixes
that, and the programme stops.

WHAT IT MEASURES. For each matched pair of articles (one from each outlet, same
event), the engine's TEXT-ONLY score: `political_lean`'s `text_score`, which is
computed from the words alone and never sees the outlet (the outlet enters only
afterwards, as the baseline the bounded shift is added to). Then

    AUC = P(text_score(right-rated article) > text_score(left-rated article)),
          ties counted as one half.

    AUC >= 0.75   proceed: build one market end to end
    AUC <  0.65   stop deriving our own baselines; keep the roster label as a label
    in between    inconclusive; say so

THE AUTOMATED HALF ONLY (CEO, 2026-09-26: no human raters for now). The ground
truth is the roster's own labels (which member of a pair is rated further right),
not blind human judgement. That is weaker evidence in one specific way: it cannot
catch a mislabelled outlet, and it assumes every article from the right-rated
member leans right of its counterpart on every event, which is false for some
events. So a LOW AUC is informative (the instrument does not separate outlets
the roster calls opposed), while a HIGH one is capped at "agrees with our labels".

THE PAIRS (CEO, 2026-09-26). Chosen for being outside US partisan vocabulary, the
lexicon's known blind spot, and on direct feeds that deliver full text.

WHAT IS STORED. `collect` writes matched pairs as URL + headline + match score,
never article text, to `data/roster/pair-test/`. `score` re-fetches each body
through the pipeline's own scraper (robots.txt decides every fetch), scores it,
and drops it; only the scores are written. Same argument as `phrase_counts.py`
and `harvest_phrase_counts.py`: a derived number, never the prose.

MATCHING reuses `anchor_pairs.similarity` (proper nouns and numbers weighted
double, greedy best-first, one article per pair). Its bar of 18 was measured at
100% precision on 11 of 11 cross-language pairs. Same-language pairs share more
topic words, and the first collection (2026-09-26) matched 3 of 4 correctly: the
miss scored 20 and paired "Turkish officials hit back at Israeli minister" with
"Turkey shelters Emirati Brotherhood figures", the shared-topic, different-subject
failure anchor_pairs documents. Every pair is stored with its score, so
`score --min-score` raises the bar without re-collecting; check a sample of the
stored headlines before trusting the default.

    python3 scripts/roster/pair_test.py collect            (cron, twice a day)
    python3 scripts/roster/pair_test.py score [--min-score N] [--out FILE]
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import html
import json
import os
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "roster"))
OUT_DIR = ROOT / "data" / "roster" / "pair-test"

import anchor_pairs  # noqa: E402

# (pair id, right-rated member, left-rated member), by roster id. "Right" means
# the higher roster baseline, whatever the market calls it.
PAIRS = [
    ("uk-tabloids", "daily-mail", "the-mirror"),
    ("israel", "jerusalem-post", "haaretz"),
    ("india", "india-today", "the-hindu"),
    ("turkey", "daily-sabah", "nordic-monitor"),
]

MIN_SCORE = anchor_pairs.MIN_SCORE
MIN_BODY_WORDS = 150        # the engine's full-text threshold
PROCEED_AUC = 0.75
STOP_AUC = 0.65


def roster() -> dict:
    rows = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    rows = rows if isinstance(rows, list) else rows["sources"]
    return {r["id"]: r for r in rows}


# --------------------------------------------------------------------------- collect

def collect() -> int:
    ros = roster()
    now = dt.datetime.now(dt.timezone.utc)
    out = {"collected_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "min_score": MIN_SCORE,
           "pairs": {}}
    total = 0
    for pid, right, left in PAIRS:
        rec = {"right": right, "left": left, "matches": [], "error": None}
        try:
            r_items = anchor_pairs.fetch(ros[right]["rss_url"])
            l_items = anchor_pairs.fetch(ros[left]["rss_url"])
            rec["feed_items"] = {"right": len(r_items), "left": len(l_items)}
            for m in anchor_pairs.pair_up(r_items, l_items, MIN_SCORE):
                # URL and headline only: the summary is publisher prose and is
                # used for matching, never stored.
                rec["matches"].append({
                    "score": m["score"],
                    "right": {"url": m["a"]["link"], "title": html.unescape(m["a"]["title"]),
                              "published": m["a"]["published"]},
                    "left": {"url": m["b"]["link"], "title": html.unescape(m["b"]["title"]),
                             "published": m["b"]["published"]},
                })
        except Exception as e:  # a dead feed is a finding, not a crash
            rec["error"] = f"{type(e).__name__}: {e}"[:200]
        total += len(rec["matches"])
        out["pairs"][pid] = rec
        print(f"  {pid:12} {right} x {left}: {len(rec['matches'])} matched"
              + (f"  ERROR {rec['error']}" if rec["error"] else
                 f"  (feeds {rec['feed_items']['right']}/{rec['feed_items']['left']})"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"{now.strftime('%Y-%m-%dT%H%MZ')}.json"
    path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)}: {total} matched pairs")
    return 0


# --------------------------------------------------------------------------- score

def load_matches(min_score: int) -> dict[str, list[dict]]:
    """Every stored match at or above the bar, de-duplicated by URL pair: the
    feeds overlap between collections, so the same pair is seen repeatedly."""
    seen = set()
    out: dict[str, list[dict]] = {pid: [] for pid, _, _ in PAIRS}
    for path in sorted(glob.glob(str(OUT_DIR / "*.json"))):
        doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        for pid, rec in doc.get("pairs", {}).items():
            for m in rec.get("matches", []):
                key = (m["right"]["url"], m["left"]["url"])
                if m["score"] < min_score or key in seen or pid not in out:
                    continue
                seen.add(key)
                out[pid].append(m)
    return out


def auc(pairs: list[tuple[float, float]]) -> float | None:
    """P(right > left) over matched pairs, ties as one half."""
    if not pairs:
        return None
    return sum(1.0 if r > l else 0.5 if r == l else 0.0 for r, l in pairs) / len(pairs)


def bootstrap_ci(pairs, n=2000, seed=11):
    if len(pairs) < 5:
        return None
    rng = random.Random(seed)
    vals = sorted(auc([rng.choice(pairs) for _ in pairs]) for _ in range(n))
    return round(vals[int(0.025 * n)], 3), round(vals[int(0.975 * n)], 3)


def verdict(a: float | None, n: int) -> str:
    if a is None or n < 20:
        return "insufficient pairs"
    if a >= PROCEED_AUC:
        return "proceed"
    if a < STOP_AUC:
        return "stop"
    return "inconclusive"


def text_score_of(url: str, title: str) -> tuple[float | None, int, str]:
    """(text_score, words, why). The body is scored and dropped here."""
    from fetchers.web_scraper import _check_robots_txt, scrape_article
    from analyzers.political_lean import analyze_political_lean
    if not _check_robots_txt(url):
        return None, 0, "robots"
    got = scrape_article(url, title=title) or {}
    body = got.get("full_text") or ""
    words = len(body.split())
    if words < MIN_BODY_WORDS:
        return None, words, "short"
    res = analyze_political_lean(
        {"title": title, "summary": "", "full_text": body},
        {"political_lean_baseline": "unrated"})
    rat = res.get("rationale") or {}
    ts = rat.get("text_score")
    return (float(ts) if ts is not None else None), words, "ok"


def score(min_score: int, out_path: str | None) -> int:
    # The analyzer imports the Supabase switch, which needs a state path. Nothing
    # here reads or writes it; a throwaway file satisfies the import.
    os.environ.setdefault("VOID_SQLITE_PATH", str(ROOT / ".pair_test_scratch.db"))
    sys.path.insert(0, str(ROOT / "pipeline"))
    matches = load_matches(min_score)
    report = {"scored_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "min_score": min_score, "thresholds": {"proceed": PROCEED_AUC, "stop": STOP_AUC},
              "pairs": {}}
    pooled: list[tuple[float, float]] = []
    for pid, right, left in PAIRS:
        rows, skipped = [], {"robots": 0, "short": 0, "error": 0, "no_score": 0}
        for m in matches[pid]:
            try:
                r, rw, rwhy = text_score_of(m["right"]["url"], m["right"]["title"])
                time.sleep(0.5)
                l, lw, lwhy = text_score_of(m["left"]["url"], m["left"]["title"])
                time.sleep(0.5)
            except Exception:
                skipped["error"] += 1
                continue
            if rwhy != "ok" or lwhy != "ok":
                skipped[rwhy if rwhy != "ok" else lwhy] += 1
                continue
            if r is None or l is None:
                skipped["no_score"] += 1
                continue
            rows.append({"score": m["score"], "right": r, "left": l,
                         "right_url": m["right"]["url"], "left_url": m["left"]["url"]})
        sp = [(x["right"], x["left"]) for x in rows]
        pooled += sp
        a = auc(sp)
        both_null = sum(1 for r, l in sp if r == 50.0 and l == 50.0)
        report["pairs"][pid] = {
            "right": right, "left": left, "matched": len(matches[pid]), "scored": len(sp),
            "skipped": skipped, "auc": None if a is None else round(a, 3),
            "ci95": bootstrap_ci(sp), "both_at_50": both_null,
            "verdict": verdict(a, len(sp)), "rows": rows,
        }
        print(f"  {pid:12} matched {len(matches[pid]):4} scored {len(sp):4} "
              f"AUC {a if a is None else round(a, 3)} ci {bootstrap_ci(sp)} "
              f"both-at-50 {both_null}  -> {verdict(a, len(sp))}  skipped {skipped}")
    a = auc(pooled)
    report["pooled"] = {"scored": len(pooled), "auc": None if a is None else round(a, 3),
                        "ci95": bootstrap_ci(pooled), "verdict": verdict(a, len(pooled))}
    print(f"  POOLED       scored {len(pooled):4} AUC {report['pooled']['auc']} "
          f"ci {report['pooled']['ci95']} -> {report['pooled']['verdict']}")
    if out_path:
        pathlib.Path(out_path).write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
        print(f"wrote {out_path}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("collect")
    sp = sub.add_parser("score")
    sp.add_argument("--min-score", type=int, default=MIN_SCORE)
    sp.add_argument("--out")
    args = ap.parse_args()
    return collect() if args.cmd == "collect" else score(args.min_score, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
