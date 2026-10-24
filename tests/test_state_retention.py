#!/usr/bin/env python3
"""Rows the date retention can never reach are swept, and nothing else is (P2-3).

Every retention rule in `main.py` compares a date column to an ISO cutoff. An
article whose `published_at` is NULL, not ISO ("Sep 23, 2026 2:34pm") or in the
future fails that comparison forever: on the 2026-10-01 state snapshot that was
5,136 articles, the oldest fetched 2026-03-22, and 154 clusters.
`main.sweep_unretainable_rows` deletes them on the date the pipeline itself wrote
(fetched_at, created_at, archived_at) with the existing windows.

This runs the sweep on a throwaway SQLite DB built from the real schema
(`migration/schema_pipeline.sql`) and asserts what goes, what stays, that the
dependants go with their article, that a same-day 'YYYY-MM-DD HH:MM:SS' value is
not read as older than an ISO cutoff, and that printed_stories is never touched.
No network, no VOID_SQLITE_PATH.
"""
from __future__ import annotations

import ast
import pathlib
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


MAIN = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")
fn = next(n for n in ast.parse(MAIN).body
          if isinstance(n, ast.FunctionDef) and n.name == "sweep_unretainable_rows")
ns: dict = {"datetime": datetime, "timezone": timezone}
exec(compile(ast.Module(body=[fn], type_ignores=[]), "main.py", "exec"), ns)
sweep = ns["sweep_unretainable_rows"]

NOW = datetime(2026, 10, 2, 12, 0, 0, tzinfo=timezone.utc)


def sp(d: datetime) -> str:          # what CURRENT_TIMESTAMP writes
    return d.strftime("%Y-%m-%d %H:%M:%S")


def iso(d: datetime) -> str:         # what the pipeline writes
    return d.isoformat()


c = sqlite3.connect(":memory:")
c.executescript((ROOT / "migration" / "schema_pipeline.sql").read_text(encoding="utf-8"))
c.execute("insert into sources(id, slug, name, url, tier, country, type) "
          "values ('s1','s1','S','https://s.example','independent','US','commercial')")
CAT = c.execute("select id from categories limit 1").fetchone()[0]

ARTS = {
    # id: (published_at, fetched_at, expected to survive the sweep)
    "fresh":        (iso(NOW - timedelta(hours=5)), sp(NOW - timedelta(hours=4)), True),
    "null_old":     (None, sp(NOW - timedelta(days=10)), False),
    "null_recent":  (None, sp(NOW - timedelta(days=2)), True),
    "junk_old":     ("Sep 23, 2026 2:34pm", sp(NOW - timedelta(days=9)), False),
    "undefined":    ("undefined", sp(NOW - timedelta(days=30)), False),
    "future_old":   (iso(NOW + timedelta(days=20)), sp(NOW - timedelta(days=8)), False),
    # Valid and old: the normal published_at rule owns it, not this sweep.
    "valid_old":    (iso(NOW - timedelta(days=10)), sp(NOW - timedelta(days=10)), True),
    # Same day as the cutoff, two hours INSIDE the window, space-form: a string
    # compare against an ISO cutoff ('2026-09-25 14:00' < '2026-09-25T12:00')
    # would delete it.
    "edge_inside":  (None, sp(NOW - timedelta(days=7) + timedelta(hours=2)), True),
}
for i, (aid, (pub, fetched, _)) in enumerate(ARTS.items()):
    c.execute("insert into articles(id, source_id, url, title, published_at, fetched_at) "
              "values (?,?,?,?,?,?)", (aid, "s1", f"https://s.example/{i}", aid, pub, fetched))
    c.execute("insert into bias_scores(id, article_id) values (?,?)", (f"b-{aid}", aid))
    c.execute("insert into article_categories values (?, ?)", (aid, CAT))

CLUSTERS = {
    "c_junk_old":     ("Sep 23, 2026 2:34pm", iso(NOW - timedelta(days=3)), False),
    "c_future_old":   (iso(NOW + timedelta(days=19)), iso(NOW - timedelta(days=3)), False),
    "c_future_new":   (iso(NOW + timedelta(days=19)), iso(NOW - timedelta(hours=20)), True),
    "c_valid_old":    (iso(NOW - timedelta(days=4)), iso(NOW - timedelta(days=4)), True),
    "c_fresh":        (iso(NOW - timedelta(hours=6)), iso(NOW - timedelta(hours=6)), True),
}
for cid, (fp, created, _) in CLUSTERS.items():
    c.execute("insert into story_clusters(id, title, first_published, created_at) values (?,?,?,?)",
              (cid, cid, fp, created))
c.execute("insert into cluster_articles values ('c_junk_old', 'fresh')")
c.execute("insert into cluster_articles values ('c_fresh', 'null_old')")
c.execute("insert into cluster_articles values ('c_fresh', 'fresh')")

ARCHIVE = {
    "a_junk_old":  ("undefined", iso(NOW - timedelta(days=11)), False),
    "a_junk_new":  ("undefined", iso(NOW - timedelta(days=3)), True),
    "a_valid_old": (iso(NOW - timedelta(days=12)), iso(NOW - timedelta(days=11)), True),
}
for aid, (fp, archived, _) in ARCHIVE.items():
    c.execute("insert into cluster_archive(id, title, first_published, archived_at) values (?,?,?,?)",
              (aid, aid, fp, archived))

c.execute("insert into printed_days(printed_on) values ('2026-03-01')")
c.execute("insert into printed_stories(id, printed_on, edition_position, source_cluster_id, title, "
          "rank_world, story_thread_id) values ('p1', '2026-03-01', 1, 'gone', 't', 50, 'th')")
c.commit()

out = sweep(c, now_iso=sp(NOW))


def ids(table):
    return {r[0] for r in c.execute(f"select id from {table}")}


arts = ids("articles")
for aid, (_, _, keep) in ARTS.items():
    check(f"article '{aid}' {'stays' if keep else 'is swept'}", (aid in arts) == keep)
check("the report counts the swept articles", out["articles"] == sum(not k for *_, k in ARTS.values()),
      str(out))
gone = {a for a, (*_, k) in ARTS.items() if not k}
check("a swept article's bias row goes with it",
      not gone & {r[0] for r in c.execute("select article_id from bias_scores")})
check("and its categories", not gone & {r[0] for r in c.execute("select article_id from article_categories")})
check("and its cluster links",
      not gone & {r[0] for r in c.execute("select article_id from cluster_articles")})
cls = ids("story_clusters")
for cid, (*_, keep) in CLUSTERS.items():
    check(f"cluster '{cid}' {'stays' if keep else 'is swept'}", (cid in cls) == keep)
check("a swept cluster's links go with it",
      "c_junk_old" not in {r[0] for r in c.execute("select cluster_id from cluster_articles")})
arc = ids("cluster_archive")
for aid, (*_, keep) in ARCHIVE.items():
    check(f"archive row '{aid}' {'stays' if keep else 'is swept'}", (aid in arc) == keep)
check("printed_stories is permanent", ids("printed_stories") == {"p1"})
check("a second sweep finds nothing", sweep(c, now_iso=sp(NOW)) == {"articles": 0, "clusters": 0, "archive": 0})

# --- The pipeline wiring -------------------------------------------------------
i_sweep = MAIN.find("_swept = sweep_unretainable_rows(")
i_ghost = MAIN.find("    # Ghost-cluster sweep: remove story_clusters that have ZERO cluster_articles.")
i_art = MAIN.find("cleanup_stale_articles', {'days': 7}")
check("run_retention calls the sweep after article retention and before the ghost sweep",
      0 < i_art < i_sweep < i_ghost)
check("the sweep never names printed_stories or printed_days",
      "printed_" not in "".join(ast.unparse(n) for n in fn.body[1:]))   # body past the docstring
check("only clusters that could have been shown are archived",
      'if int(float(r.get("source_count") or 0)) >= 3]' in MAIN
      and "_arch, on_conflict=\"id\"" in MAIN)

if failures:
    print(f"\nFAIL  {len(failures)} retention check(s)")
    sys.exit(1)
print("\nPASS  undated rows are swept on the date we wrote, and the permanent archive is untouched")
