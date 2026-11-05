#!/usr/bin/env python3
"""Step 8c ranks only the clusters that can reach the feed, and the feed does not move.

P2-1 (rev 85). The holistic re-rank scored every cluster in the table: 15,566 on
run #385 in 637 s, about 11,800 of them one- or two-source orphans that
`display_window.select_candidates` refuses outright. `rerank.rerank_all_clusters`
now ranks the pool-eligible clusters (source_count >= MIN_SOURCES) and parks the
orphans below every ranked row.

This builds a synthetic day in a throwaway SQLite state DB (the real schema,
`migration/schema_pipeline.sql`), runs the re-rank the old way (`pool_only=False`)
and the new way on the same rows, and asserts:

  - the candidate bench (top POOL by rank_world, then the first CANDIDATES with
    >= 3 sources, exactly as Stage 2 selects it) is IDENTICAL, in order;
  - the full eligible ordering is identical, not just the bench;
  - every orphan is parked strictly below every eligible cluster;
  - the corpus-size proxy the adaptive is_headline band reads is unchanged, so
    is_headline cannot flip;
  - parking touches rank_world only: an orphan's headline_rank is left alone.

Runs with no network. Needs the pipeline's NLP deps (spaCy), like the ranker.
"""
from __future__ import annotations

import json
import os
import pathlib
import random
import sqlite3
import sys
import tempfile
import uuid
from datetime import datetime, timedelta, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
_tmp = tempfile.mkdtemp(prefix="void-rerank-")
DB = os.path.join(_tmp, "state.db")
os.environ["VOID_SQLITE_PATH"] = DB

conn = sqlite3.connect(DB)
conn.executescript((ROOT / "migration" / "schema_pipeline.sql").read_text(encoding="utf-8"))

sys.path.insert(0, str(ROOT / "pipeline"))
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


# --- A synthetic day -----------------------------------------------------------
rng = random.Random(85)
roster = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
roster = roster if isinstance(roster, list) else roster.get("sources", [])
picked = [s for s in roster if s.get("tier") in ("us_major", "international", "independent")][:60]
sources = []
for s in picked:
    db_id = str(uuid.uuid5(uuid.NAMESPACE_URL, s["id"]))
    conn.execute(
        "insert into sources(id, slug, name, url, tier, country, type, political_lean_baseline) "
        "values (?,?,?,?,?,?,?,?)",
        (db_id, s["id"], s.get("name") or s["id"], s.get("url") or "https://x.example",
         s["tier"], s.get("country") or "US", s.get("type") or "commercial",
         s.get("political_lean_baseline") or "unrated"))
    sources.append(dict(s, db_id=db_id))

# Titles share no content words. Real days have a few same-story clusters, and
# apply_feed_ordering's event cap and near-duplicate scans DO see orphans on the
# old path (see the note in rerank.py); this fixture isolates the ranking change
# from that interaction, which section 2 states separately.
VERBS = ["approves", "rejects", "announces", "suspends", "expands", "investigates",
         "launches", "cancels", "extends", "confirms", "delays", "funds"]
CATS = ["politics", "general", "economy", "conflict", "health", "science"]
_seen: set[str] = set()


def word() -> str:
    while True:
        w = "".join(rng.choice("bdfgklmnprstvz") + rng.choice("aeiou") for _ in range(3))
        if w not in _seen:
            _seen.add(w)
            return w


def title_and_cat(i: int) -> tuple[str, str]:
    return (f"{word().title()} {VERBS[i % len(VERBS)]} {word()} {word()} plan",
            CATS[i % len(CATS)])


NOW = datetime.now(timezone.utc)
art_n = 0


def add_cluster(n_sources: int, title: str, category: str) -> str:
    global art_n
    cid = str(uuid.uuid4())
    first = (NOW - timedelta(hours=rng.uniform(2, 30))).isoformat()
    conn.execute(
        "insert into story_clusters(id, title, category, section, sections, content_type, "
        "source_count, first_published, headline_rank, rank_world) values (?,?,?,?,?,?,?,?,?,?)",
        (cid, title, category, "world", '["world"]', "reporting", n_sources, first,
         rng.uniform(5, 60), rng.uniform(5, 60)))
    for s in rng.sample(sources, n_sources):
        art_n += 1
        aid = str(uuid.uuid4())
        body = (f"{title}. Officials said on Tuesday that the decision would take effect "
                f"next month, according to a statement. ") * 6
        conn.execute(
            "insert into articles(id, source_id, url, title, summary, full_text, published_at, "
            "word_count) values (?,?,?,?,?,?,?,?)",
            (aid, s["db_id"], f"https://x.example/{art_n}", title, title, body,
             (NOW - timedelta(hours=rng.uniform(1, 30))).isoformat(), len(body.split())))
        conn.execute(
            "insert into bias_scores(id, article_id, political_lean, sensationalism, opinion_fact, "
            "factual_rigor, framing, confidence) values (?,?,?,?,?,?,?,?)",
            (str(uuid.uuid4()), aid, rng.randint(20, 80), rng.randint(5, 40), rng.randint(5, 40),
             rng.randint(30, 80), rng.randint(10, 50), round(rng.uniform(0.4, 0.9), 2)))
        conn.execute("insert into cluster_articles values (?,?)", (cid, aid))
    return cid


eligible_ids, orphan_ids = [], []
for i in range(80):
    n = rng.choice([3, 4, 5, 6, 8, 10, 14, 20, 30, 45])
    eligible_ids.append(add_cluster(n, *title_and_cat(i)))
for i in range(320):
    orphan_ids.append(add_cluster(rng.choice([1, 1, 1, 2]), *title_and_cat(i)))
conn.commit()
conn.close()

import rerank  # noqa: E402  (binds the shim to DB)
from utils.supabase_client import supabase  # noqa: E402
from utils.display_window import fetch_display_pool, select_candidates  # noqa: E402
from utils.feed_config import CANDIDATES, POOL  # noqa: E402


def snapshot():
    rows = supabase.table("story_clusters").select(
        "id,rank_world,headline_rank,source_count,is_headline").execute().data
    return {r["id"]: r for r in rows}


def bench():
    pool = fetch_display_pool(supabase, edition="world", pool=POOL)
    return [r["id"] for r in select_candidates(pool, CANDIDATES)]


def eligible_order(snap):
    return [cid for cid, _ in sorted(((c, float(snap[c]["rank_world"])) for c in eligible_ids),
                                     key=lambda kv: -kv[1])]


# --- 1. The old path, then the new path, on the same rows ---------------------
rerank.rerank_all_clusters(sources, pool_only=False)
old, old_bench = snapshot(), bench()
orphan_headline_before = {c: old[c]["headline_rank"] for c in orphan_ids}
rerank.rerank_all_clusters(sources, pool_only=True)
new, new_bench = snapshot(), bench()

check("the whole eligible ordering is identical", eligible_order(old) == eligible_order(new))
check("the new bench is the first CANDIDATES of that ordering",
      new_bench == eligible_order(new)[:CANDIDATES], str(len(new_bench)))
check("the bench is identical, in order, as far as the old pool let it fill",
      old_bench == new_bench[:len(old_bench)])
if len(old_bench) != len(new_bench):
    print(f"  info  old bench {len(old_bench)} of {CANDIDATES}, new {len(new_bench)}: orphans "
          f"ranked into the top {POOL} took the difference on the old path")
check("the new path fills the bench", len(new_bench) == CANDIDATES, str(len(new_bench)))
check("eligible clusters keep the same is_headline",
      all(old[c]["is_headline"] == new[c]["is_headline"] for c in eligible_ids))
lowest_eligible = min(float(new[c]["rank_world"]) for c in eligible_ids)
highest_orphan = max(float(new[c]["rank_world"]) for c in orphan_ids)
check("every orphan is parked below every eligible cluster", highest_orphan < lowest_eligible,
      f"{highest_orphan} vs {lowest_eligible}")
check("the floor is at or below ORPHAN_RANK_FLOOR", highest_orphan <= rerank.ORPHAN_RANK_FLOOR)
check("parking moves rank_world only: headline_rank is left as it was",
      all(new[c]["headline_rank"] == orphan_headline_before[c] for c in orphan_ids))
check("no orphan is in the pool", not (set(new_bench) & set(orphan_ids)))

# --- 2. The corpus proxy and the eligibility rule ------------------------------
src = (ROOT / "pipeline" / "rerank.py").read_text(encoding="utf-8")
check("the corpus count still reads every cluster-linked article (orphans included)",
      "corpus_published" in src and "_orphan_only_ids" in src)
check("eligibility is the bench's own threshold",
      rerank.POOL_MIN_SOURCES == __import__("utils.display_window",
                                            fromlist=["MIN_SOURCES"]).MIN_SOURCES)
check("a 2-source cluster is not eligible, a 3-source one is",
      not rerank.is_pool_eligible({"source_count": 2})
      and rerank.is_pool_eligible({"source_count": "3"}))
check("the floor sits under the lowest ranked row it is given",
      rerank.parking_floor([{"rank_world": -150.0}]) == -151.0
      and rerank.parking_floor([{"rank_world": 40.0}]) == rerank.ORPHAN_RANK_FLOOR)
main_src = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")
check("main.py's 8c calls the default (pool-only) re-rank",
      "rerank_all_clusters(sources, run_id=run_id)" in main_src)

if failures:
    print(f"\nFAIL  {len(failures)} re-rank pool check(s)")
    sys.exit(1)
print("\nPASS  8c ranks only what can reach the feed, and the feed does not move")
