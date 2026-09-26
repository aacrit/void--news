#!/usr/bin/env python3
"""The engine's input is measured, and a collapse in it cannot pass silently.

For weeks half the roster was scored on a headline and nothing counted it
(`docs/proposals/OUTLET-BASELINE-PROGRAMME-2026-09-22.md` section 0). And on
2026-09-19..23 about 2,500 direct-feed articles a day fell back to their RSS
summary, the direct full-body share sat at 45-48% against 69-71% on healthy
runs, and nothing noticed that either. `validation/engine_health.py` measures
both; `export_static.py` writes them to `frontend/build-data/engine.json`.

Two modes:

  python tests/test_engine_health.py            (auto-merge CI)
      The measurement is right on a planted fixture, the gate fires on a planted
      collapse, and the committed engine.json is well formed and consistent.
      Deliberately does NOT fail on the data's floor here: a bad scraping day
      must not freeze every code branch (CLAUDE.md, "main is production").

  python tests/test_engine_health.py --floors   (pipeline.yml, AFTER the data commit)
      Fails the run when the committed engine.json is under the floor. The paper
      still ships; the run goes red, which is the alarm.

Runs with no network and no VOID_SQLITE_PATH.
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from validation import engine_health as eh  # noqa: E402

ENGINE_JSON = ROOT / "frontend" / "build-data" / "engine.json"
failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


if "--floors" in sys.argv:
    health = json.loads(ENGINE_JSON.read_text(encoding="utf-8"))
    print(eh.format_summary(health))
    probs = eh.problems(health)
    for p in probs:
        print(f"  FAIL  {p}")
    sys.exit(1 if probs else 0)


# --- 1. The measurement, on a planted fixture --------------------------------
def fixture(direct_full: int, direct_short: int) -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.executescript("""
        create table sources (id text primary key, rss_url text, political_lean_baseline text);
        create table articles (id text primary key, source_id text, word_count integer,
                               fetched_at text);
        create table bias_scores (article_id text, rationale text);
    """)
    c.execute("insert into sources values ('d1', 'https://outlet.example/rss', 'left')")
    c.execute("insert into sources values ('d2', 'https://other.example/feed', 'unrated')")
    c.execute("insert into sources values ('g1', "
              "'https://news.google.com/rss/search?q=site:x.example', 'right')")
    n = 0

    def art(sid, words, rationale=None, when="2026-09-25 16:00:00"):
        nonlocal n
        n += 1
        c.execute("insert into articles values (?,?,?,?)", (f"a{n}", sid, words, when))
        if rationale is not None:
            c.execute("insert into bias_scores values (?,?)", (f"a{n}", json.dumps(rationale)))

    for i in range(direct_full):
        art("d1", 400, {"lean": {"text_shift": [0.0, 2.0, -4.0][i % 3], "unscored": False}})
    for _ in range(direct_short):
        art("d1", 40, {"framing": {}})
    art("d2", 500, {"lean": {"text_shift": 9.0, "unscored": False}})    # unplaced: excluded
    art("d1", 500, {"lean": {"text_shift": 50.0, "unscored": True}})    # unscored: excluded
    for _ in range(4):
        art("g1", 11, {"framing": {}})                                   # headline only
    art("d1", 900, {"lean": {"text_shift": 7.0}}, when="2026-09-23 16:00:00")  # older run
    return c


h = eh.compute(fixture(direct_full=6, direct_short=2))
check("an article from an older run is outside the window", h["run"]["articles"] == 14,
      str(h["run"]))
check("a Google News feed is classed as google_news",
      h["feeds"]["google_news"]["articles"] == 4 and h["feeds"]["google_news"]["full_share"] == 0)
check("direct full share counts 150+ words over all direct articles",
      h["feeds"]["direct"]["full_share"] == round(8 / 10, 4), str(h["feeds"]["direct"]))
check("everything under 150 words is scored on the outlet alone",
      h["scoring"]["outlet_only"] == 6 and h["scoring"]["text_read"] == 8, str(h["scoring"]))
m = h["text_movement_rated"]
check("text movement uses rated, measured rows only (unplaced and unscored excluded)",
      m["articles"] == 6, str(m))
check("mean |text_shift| is the mean of the absolute shifts", m["mean_abs"] == 2.0, str(m))
check("the share that did not move is reported", m["zero_share"] == round(2 / 6, 4), str(m))

# --- 2. The gate fires on a planted collapse, and only then ------------------
check("a healthy run has no problems", eh.problems(h) == [], str(eh.problems(h)))
collapsed = eh.compute(fixture(direct_full=4, direct_short=6))      # 5/11 = 45%
probs = eh.problems(collapsed)
check("a direct full-body share of 45% (the 2026-09-19..23 regime) fails",
      any("floor" in p for p in probs), str(probs))
check("the floor sits between the measured regimes (45-48% bad, 69-71% healthy)",
      0.48 < eh.FULL_SHARE_FLOOR < 0.69)
empty = {"feeds": {"direct": {"articles": 0}}, "text_movement_rated": {"articles": 0}}
check("a run with no direct articles or no measured shift fails", len(eh.problems(empty)) == 2)

# --- 3. The committed export ---------------------------------------------------
check("frontend/build-data/engine.json is committed", ENGINE_JSON.exists())
if ENGINE_JSON.exists():
    e = json.loads(ENGINE_JSON.read_text(encoding="utf-8"))
    for key in ("run", "thresholds", "feeds", "scoring", "text_movement_rated"):
        check(f"engine.json carries '{key}'", key in e)
    check("its thresholds are the module's",
          e.get("thresholds") == {"full_body_words": eh.FULL_BODY_WORDS,
                                  "headline_words": eh.HEADLINE_WORDS,
                                  "direct_full_share_floor": eh.FULL_SHARE_FLOOR},
          str(e.get("thresholds")))
    s, r = e.get("scoring", {}), e.get("run", {})
    check("text_read + outlet_only = the run's articles",
          s.get("text_read", -1) + s.get("outlet_only", -1) == r.get("articles"))
    f = e.get("feeds", {})
    check("the feed classes sum to the run's articles",
          f.get("direct", {}).get("articles", 0) + f.get("google_news", {}).get("articles", 0)
          == r.get("articles"))

# --- 4. Copy quotes the engine, not a memory of it ----------------------------
import re  # noqa: E402

bounds = (ROOT / "frontend" / "app" / "lib" / "leanBounds.ts").read_text(encoding="utf-8")
lean_src = (ROOT / "pipeline" / "analyzers" / "political_lean.py").read_text(encoding="utf-8")
main_src = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")


def ts_const(name):
    m = re.search(rf"export const {name} = (\d+);", bounds)
    return int(m.group(1)) if m else None


def py_const(name):
    m = re.search(rf"^{name} = (\d+)", lean_src, re.M)
    return int(m.group(1)) if m else None


check("leanBounds RATED_DELTA_MAX is political_lean._TEXT_DELTA_MAX",
      ts_const("RATED_DELTA_MAX") == py_const("_TEXT_DELTA_MAX") is not None,
      f"{ts_const('RATED_DELTA_MAX')} vs {py_const('_TEXT_DELTA_MAX')}")
check("leanBounds UNRATED_DELTA_MAX is political_lean._CENTER_TEXT_DELTA_MAX",
      ts_const("UNRATED_DELTA_MAX") == py_const("_CENTER_TEXT_DELTA_MAX") is not None)
gate = re.search(r"if word_count < (\d+):", main_src)
check("leanBounds FULL_TEXT_WORDS is main.py's word-count gate and engine_health's",
      gate and ts_const("FULL_TEXT_WORDS") == int(gate.group(1)) == eh.FULL_BODY_WORDS,
      f"{ts_const('FULL_TEXT_WORDS')} vs {gate and gate.group(1)} vs {eh.FULL_BODY_WORDS}")

src_client = (ROOT / "frontend" / "app" / "sources" / "SourcesClient.tsx").read_text(encoding="utf-8")
check("/sources prints the measured movement from engine.json",
      "engine.text_movement_rated.mean_abs" in src_client
      and "engine.scoring.outlet_only_share" in src_client)
check("/sources restates no measured movement as a literal",
      not re.search(r"\d+(\.\d+)?\s+points on average", src_client))
retired = {
    "frontend/app/components/about/AboutPipeline.tsx": "a full article leans on its words",
    "frontend/app/components/about/beats/BeatSigil.tsx": "so its words carry more",
    "frontend/app/sources/SourcesClient.tsx": "never overrides one that reads against type",
}
for path, phrase in retired.items():
    check(f"retired claim is gone: '{phrase}'",
          phrase not in (ROOT / path).read_text(encoding="utf-8"))

# --- 5. The pipeline runs the floor after it commits, not before ---------------
wf = (ROOT / ".github" / "workflows" / "pipeline.yml").read_text(encoding="utf-8")
i_commit = wf.find("- name: Commit refreshed static data to main")
i_floor = wf.find("tests/test_engine_health.py --floors")
check("pipeline.yml runs the floor check", i_floor > 0)
check("and runs it after the data commit, so a bad day still ships the paper",
      i_commit > 0 and i_floor > i_commit)

if failures:
    print(f"\nFAIL  {len(failures)} engine-health check(s)")
    sys.exit(1)
print("\nPASS  the engine's input is measured, and a collapse in it cannot pass silently")
