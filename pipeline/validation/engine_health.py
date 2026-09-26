"""What the bias engine actually read and did on the latest run. Measured, not claimed.

WHY. Two facts about the engine were true for weeks and visible nowhere:

  1. Half the roster was being scored on a headline. 251 Google News-fed sources
     (4,809 of 11,613 articles on 2026-09-25) arrive with a median of 11 words, and
     `main.py`'s word-count gate sends every article under 150 words straight to
     its outlet's baseline without running the text analyzer at all. Nothing
     counted it. The 2026-09-22 audit found it by hand.
  2. The words move a rated outlet's score very little. On 2026-09-25 the mean
     absolute `text_shift` across 3,635 measured articles from rated outlets was
     1.54 points, and 61.1% moved by exactly zero. `/sources` described the
     architecture ("two things") without the magnitude.

This module computes both from the state DB after a run, `export_static.py` writes
them to `frontend/build-data/engine.json`, `/sources` reads its numbers from that
file rather than from prose (a count written into copy is a future error, Rule 1),
and `tests/test_engine_health.py` fails when the direct-feed body share collapses.

THE FLOOR, set from measurement (state snapshot of run #379): the direct-feed share
of articles with 150+ words was 69.4% and 70.8% on the two healthy runs of
2026-09-24/25, and 45.0% to 47.8% on 2026-09-19..23, when about 2,500 direct
articles a day fell back to their RSS summary (their `word_count` equals the word
count of the stored summary). FULL_SHARE_FLOOR sits between the two regimes.
"""
from __future__ import annotations

import json
import sqlite3
import statistics

# The run's own intake. The pipeline runs once a day and stamps `fetched_at` at
# insert, so everything within this many hours of the newest row is this run.
# Runs are ~24h apart and a fetch spans ~15 minutes; 30 caught two runs.
RUN_WINDOW_HOURS = 20

# The engine's own full-text threshold (`main.py` word-count gate and the lean
# analyzer's `confidence = min(1, words / 150)`).
FULL_BODY_WORDS = 150
HEADLINE_WORDS = 25

FULL_SHARE_FLOOR = 0.55

UNPLACED = ("unrated", "varies")


def feed_class(rss_url: str | None) -> str:
    return "google_news" if rss_url and "news.google.com" in rss_url else "direct"


def _class_stats(rows: list[tuple[int, str]]) -> dict:
    words = [w for w, _ in rows]
    n = len(words)
    return {
        "sources": len({sid for _, sid in rows}),
        "articles": n,
        "median_words": statistics.median(words) if words else 0,
        "full_share": round(sum(w >= FULL_BODY_WORDS for w in words) / n, 4) if n else 0.0,
        "headline_share": round(sum(w <= HEADLINE_WORDS for w in words) / n, 4) if n else 0.0,
    }


def compute(conn: sqlite3.Connection) -> dict:
    newest = conn.execute("select max(fetched_at) from articles").fetchone()[0]
    if not newest:
        return {"run": None}
    rows = conn.execute(
        f"""select coalesce(a.word_count, 0), s.rss_url, s.id,
                   s.political_lean_baseline, b.rationale
              from articles a
              join sources s on s.id = a.source_id
              left join bias_scores b on b.article_id = a.id
             where a.fetched_at >= datetime(?, '-{RUN_WINDOW_HOURS} hours')""",
        (newest,)).fetchall()

    by_class: dict[str, list[tuple[int, str]]] = {"direct": [], "google_news": []}
    shifts: list[float] = []
    outlet_only = text_read = 0
    for words, rss, sid, lean, rationale in rows:
        by_class[feed_class(rss)].append((words, sid))
        if words < FULL_BODY_WORDS:
            outlet_only += 1        # the word-count gate: baseline, no text analyzer
            continue
        text_read += 1
        if lean in UNPLACED or lean is None:
            continue
        if not rationale or not str(rationale).lstrip().startswith("{"):
            continue
        try:
            lr = json.loads(rationale).get("lean")
        except (ValueError, AttributeError):
            continue
        if not isinstance(lr, dict) or lr.get("unscored") or lr.get("text_shift") is None:
            continue
        shifts.append(float(lr["text_shift"]))

    n = len(rows)
    movement = {"articles": len(shifts)}
    if shifts:
        abs_s = [abs(x) for x in shifts]
        movement.update({
            "mean_abs": round(statistics.mean(abs_s), 2),
            "zero_share": round(sum(x == 0 for x in shifts) / len(shifts), 4),
            "min": min(shifts),
            "max": max(shifts),
        })
    return {
        "run": {"newest_fetch": newest, "window_hours": RUN_WINDOW_HOURS, "articles": n},
        "thresholds": {"full_body_words": FULL_BODY_WORDS, "headline_words": HEADLINE_WORDS,
                       "direct_full_share_floor": FULL_SHARE_FLOOR},
        "feeds": {k: _class_stats(v) for k, v in by_class.items()},
        "scoring": {
            "text_read": text_read,
            "outlet_only": outlet_only,
            "outlet_only_share": round(outlet_only / n, 4) if n else 0.0,
        },
        # Rated outlets only: an unplaced outlet has no baseline for the words to
        # move away from, and its articles are handled by the ±24 path instead.
        "text_movement_rated": movement,
    }


def problems(health: dict) -> list[str]:
    """The failures the gate enforces. Empty when healthy."""
    out = []
    d = (health.get("feeds") or {}).get("direct") or {}
    if not d.get("articles"):
        out.append("no direct-feed articles in the latest run")
    elif d["full_share"] < FULL_SHARE_FLOOR:
        out.append(f"direct-feed full-body share {d['full_share']:.1%} is under the "
                   f"{FULL_SHARE_FLOOR:.0%} floor (median {d['median_words']} words): "
                   f"scraping is falling back to RSS summaries")
    m = health.get("text_movement_rated") or {}
    if not m.get("articles"):
        out.append("no rated article carries a measured text_shift")
    return out


def stale(health: dict, db_newest: str | None) -> list[str]:
    """engine.json must describe the newest article in the state DB. A floor
    that reads yesterday's file cannot fail, and on the first run after rev 82
    it did exactly that: the export skipped the section and the check passed."""
    have = ((health or {}).get("run") or {}).get("newest_fetch")
    if not db_newest:
        return []
    if have != db_newest:
        return [f"engine.json describes the run whose newest article is {have}, "
                f"but the state DB's newest is {db_newest}: the export did not "
                f"rewrite it (is `engine` in VOID_EXPORT_ONLY?)"]
    return []


def format_summary(health: dict) -> str:
    f = health.get("feeds", {})
    d, g = f.get("direct", {}), f.get("google_news", {})
    m = health.get("text_movement_rated", {})
    s = health.get("scoring", {})
    return (f"  engine: direct {d.get('articles', 0)} articles / {d.get('sources', 0)} sources, "
            f"median {d.get('median_words')} words, {d.get('full_share', 0):.1%} full; "
            f"google_news {g.get('articles', 0)} / {g.get('sources', 0)}, "
            f"median {g.get('median_words')}; outlet-only {s.get('outlet_only_share', 0):.1%}; "
            f"rated text_shift mean |{m.get('mean_abs')}| over {m.get('articles', 0)}, "
            f"zero {m.get('zero_share', 0):.1%}")
