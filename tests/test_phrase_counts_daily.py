#!/usr/bin/env python3
"""The daily phrase-count path stays bounded, and bounded by the right rules.

`phrase_counts.record_daily` runs every day inside the pipeline (step 9e). The
harvest entry point it replaced would have kept every phrase from a daily run,
because a day's one to five articles per outlet never reaches the band's
denominator: replayed at the measured direct-feed volume that was 765,142 rows
after one day and 18.3M after thirty. So the gate asserts the three rules that
bound it and the alarm behind them, each against a planted case:

  - a headline is not an article (short bodies are skipped, not counted)
  - only phrases the derivation can score are stored
  - a phrase seen once today is kept (it may be seen again tomorrow), which is
    exactly what the harvest band would have thrown away
  - a phrase that never spread is pruned by age; one still in use never is
  - past the ceiling nothing is recorded, and nothing is pruned to fit
  - the table still holds no article identifier and no row over three words

Runs with no network, no state DB and no VOID_SQLITE_PATH.
"""
from __future__ import annotations

import importlib.util
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))


def load(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "pipeline" / "analyzers" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


pc = load("phrase_counts")
ld = load("lexicon_derive")

failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


FILLER = ("Officials met on Tuesday to review the proposal and discuss funding for "
          "regional transport projects across several districts. ") * 12
BODY = FILLER + " the wealth tax debate continued in parliament. "
assert len(BODY.split()) >= pc.DAILY_MIN_BODY_WORDS


def fresh():
    conn = sqlite3.connect(":memory:")
    return conn


# Sections 1-6 test the rules behind the gate, so the gate is opened for them
# (admit on first sighting). Section 8 tests the gate itself at its real setting.
REAL_GATE = pc.GATE_SIGHTINGS
pc.GATE_SIGHTINGS = 1


def phrases_for(conn, sid):
    return {p: c for p, c in conn.execute(
        "select phrase, count from outlet_phrase_counts where source_id=?", (sid,))}


# --- 1. A headline is not an article ---------------------------------------
conn = fresh()
rep = pc.record_daily(conn, [
    {"source_id": "a", "full_text": "Wealth tax debate continues"},     # headline only
    {"source_id": "a", "full_text": BODY},
], "2026-09-01T11:00:00Z")
arts = dict(conn.execute("select source_id, articles from outlet_phrase_articles"))
check("a headline-only row is skipped, not counted", rep["skipped_short"] == 1, str(rep))
check("the denominator counts only full bodies", arts.get("a") == 1, str(arts))

# --- 2. Only phrases the derivation can score -------------------------------
stored = set(phrases_for(conn, "a"))
emittable = set(ld.phrases(BODY))
check("every stored phrase is one lexicon_derive.phrases() can emit",
      stored <= emittable, str(sorted(stored - emittable)[:5]))
check("stop-bracketed furniture is not stored", "of the" not in stored and "in the" not in stored)
check("a stop unigram is not stored", "the" not in stored)
check("the planted phrase is stored", "wealth tax" in stored)

# --- 3. A phrase seen once today survives, and the cap is fixed by URL -------
conn = fresh()
pc.record_daily(conn, [{"source_id": "o", "url": "u0", "full_text": FILLER + " rare phrase sighting here"}],
                "2026-09-01T11:00:00Z")
check("a once-today phrase is kept for tomorrow",
      phrases_for(conn, "o").get("rare phrase sighting") == 1)
pc.record_daily(conn, [{"source_id": "o", "url": "u1", "full_text": FILLER + " rare phrase sighting again"}],
                "2026-09-02T11:00:00Z")
check("and it accumulates across days",
      phrases_for(conn, "o").get("rare phrase sighting") == 2)

import hashlib  # noqa: E402
import random  # noqa: E402
busy = [{"source_id": "busy", "url": f"https://x.example/{i}",
         "full_text": FILLER + f" marker{chr(97 + i)} words"} for i in range(25)]
kept_urls = sorted(busy, key=lambda r: hashlib.sha1(r["url"].encode()).hexdigest())[:pc.DAILY_PER_OUTLET_CAP]
expect = {f"marker{r['full_text'].split('marker')[1][0]}" for r in kept_urls}


def run_cap(rows):
    c = fresh()
    rep = pc.record_daily(c, rows, "2026-09-01T11:00:00Z")
    got = {p for p in phrases_for(c, "busy") if p.startswith("marker") and " " not in p}
    arts = dict(c.execute("select source_id, articles from outlet_phrase_articles"))
    return rep, got, arts


rep, got, arts = run_cap(busy)
check("a busy outlet is capped at DAILY_PER_OUTLET_CAP bodies a day",
      arts.get("busy") == pc.DAILY_PER_OUTLET_CAP and rep["capped"] == 25 - pc.DAILY_PER_OUTLET_CAP,
      f"{arts} {rep['capped']}")
check("the kept bodies are the lowest URL hashes, not the first in the feed",
      got == expect, f"{sorted(got)} vs {sorted(expect)}")
shuffled = busy[:]
random.Random(7).shuffle(shuffled)
check("feed order does not change which bodies are kept", run_cap(shuffled)[1] == expect)

# --- 4. Retention by spread and age -----------------------------------------
conn = fresh()
day0 = "2026-09-01T11:00:00Z"
pc.record_daily(conn, [{"source_id": "solo", "full_text": FILLER + " sacramento county ordinance"}], day0)
for sid in ("x1", "x2", "x3"):
    pc.record_daily(conn, [{"source_id": sid, "full_text": FILLER + " border funding vote"}], day0)
# 15 days later, nothing new mentions either phrase.
pc.record_daily(conn, [], "2026-09-16T11:00:00Z")
solo = phrases_for(conn, "solo")
check("a phrase at one outlet is pruned after the early window",
      "sacramento county ordinance" not in solo, str(sorted(solo)[:5]))
check("a phrase at three outlets survives the early window",
      "border funding vote" in phrases_for(conn, "x1"))
# Still used by one outlet on day 15: its newest row is fresh, so it is not old.
conn2 = fresh()
pc.record_daily(conn2, [{"source_id": "solo", "full_text": FILLER + " harbour dredging levy"}], day0)
pc.record_daily(conn2, [{"source_id": "solo", "full_text": FILLER + " harbour dredging levy"}],
                "2026-09-15T11:00:00Z")
pc.record_daily(conn2, [], "2026-09-16T11:00:00Z")
check("a phrase still in use is never aged out",
      "harbour dredging levy" in phrases_for(conn2, "solo"))
# 57 days on, three outlets is not enough.
pc.record_daily(conn, [], "2026-10-28T11:00:00Z")
check("a phrase that never reached eight outlets is pruned after the late window",
      "border funding vote" not in phrases_for(conn, "x1"))

# --- 5. The ceiling halts, it does not prune to fit -------------------------
conn = fresh()
pc.record_daily(conn, [{"source_id": "a", "full_text": BODY}], day0)
before = conn.execute("select count(*) from outlet_phrase_counts").fetchone()[0]
saved = pc.DAILY_MAX_ROWS
pc.DAILY_MAX_ROWS = before - 1
try:
    rep = pc.record_daily(conn, [{"source_id": "b", "full_text": BODY}], "2026-09-02T11:00:00Z")
finally:
    pc.DAILY_MAX_ROWS = saved
after = conn.execute("select count(*) from outlet_phrase_counts").fetchone()[0]
check("past the ceiling the run records nothing", rep["halted"] and not phrases_for(conn, "b"))
check("and prunes nothing to fit", after == before, f"{before} -> {after}")

# --- 6. The IP invariant holds on the daily path ----------------------------
conn = fresh()
pc.record_daily(conn, [{"source_id": "a", "full_text": BODY + " " + BODY}], day0)
widest = conn.execute("select max(words) from outlet_phrase_counts").fetchone()[0]
check("no stored phrase exceeds the width bound", widest <= pc.MAX_PHRASE_WORDS, str(widest))
cols = {r[1] for r in conn.execute("pragma table_info(outlet_phrase_counts)")}
check("the table stores no article identifier",
      not (cols & {"article_id", "url", "text", "body", "full_text"}), str(sorted(cols)))

# --- 8. The admission gate ------------------------------------------------
pc.GATE_SIGHTINGS = REAL_GATE
check("the gate is on at three sightings in production", REAL_GATE == 3)
conn = fresh()
art = FILLER + " levy on harbour dredging"
rep1 = pc.record_daily(conn, [{"source_id": "g1", "full_text": art}], "2026-09-01T11:00:00Z")
pc.record_daily(conn, [{"source_id": "g2", "full_text": art}], "2026-09-02T11:00:00Z")
check("a phrase seen twice holds no row", not any(
    "harbour dredging" in p for p in list(phrases_for(conn, "g1")) + list(phrases_for(conn, "g2"))))
rep = pc.record_daily(conn, [{"source_id": "g3", "full_text": art}], "2026-09-03T11:00:00Z")
check("its third sighting is admitted and counted once",
      phrases_for(conn, "g3").get("harbour dredging") == 1, str(rep))
check("gated sightings are reported, not silent",
      rep1["gated"] > 0 and rep1["written"] == 0, str(rep1))
pc.record_daily(conn, [{"source_id": "g1", "full_text": art}], "2026-09-04T11:00:00Z")
check("once a phrase holds a row, every later sighting counts",
      phrases_for(conn, "g1").get("harbour dredging") == 1)
cols = {r[1] for r in conn.execute("pragma table_info(phrase_gate)")}
check("the gate stores bit arrays, never phrase text",
      cols == {"name", "started_at", "bits", "hashes", "array"}, str(sorted(cols)))

# Generations: remembered across one rotation, forgotten after two.
conn = fresh()
once = FILLER + " quarry permit dispute"
pc.record_daily(conn, [{"source_id": "r1", "full_text": once}], "2026-09-01T11:00:00Z")
pc.record_daily(conn, [{"source_id": "r2", "full_text": once}], "2026-09-16T11:00:00Z")  # rotated
pc.record_daily(conn, [{"source_id": "r3", "full_text": once}], "2026-09-17T11:00:00Z")
check("a first sighting survives one rotation (window is one to two generations)",
      phrases_for(conn, "r3").get("quarry permit dispute") == 1)
conn = fresh()
pc.record_daily(conn, [{"source_id": "r1", "full_text": once}], "2026-09-01T11:00:00Z")
pc.record_daily(conn, [{"source_id": "r2", "full_text": once}], "2026-09-16T11:00:00Z")
pc.record_daily(conn, [], "2026-10-01T11:00:00Z")                       # second rotation
pc.record_daily(conn, [{"source_id": "r3", "full_text": once}], "2026-10-16T11:00:00Z")
check("sightings older than two generations are forgotten",
      "quarry permit dispute" not in phrases_for(conn, "r3"))

# --- 7. The pipeline wires it before truncation, to its own file ------------
main_src = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")
i_rec = main_src.find("_pc.record_daily(")
i_trunc = main_src.find("# Step 10: Truncate full_text")
check("main.py calls record_daily before the step-10 truncation", 0 < i_rec < i_trunc)
check("main.py writes to VOID_PHRASE_DB, not the state DB",
      'os.environ.get("VOID_PHRASE_DB")' in main_src)
wf = (ROOT / ".github" / "workflows" / "pipeline.yml").read_text(encoding="utf-8")
check("the pipeline workflow sets VOID_PHRASE_DB and persists the file",
      "VOID_PHRASE_DB: phrase_counts.db" in wf and "void-phrase-snapshot" in wf
      and "void-phrases-v1-" in wf)

if failures:
    print(f"\nFAIL  {len(failures)} daily phrase-count check(s)")
    sys.exit(1)
print("\nPASS  the daily phrase counts are bounded by what the derivation can use")
