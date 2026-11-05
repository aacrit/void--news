#!/usr/bin/env python3
"""Rule 1, cut and publish: the export cuts what the gate would confirm.

CEO 2026-10-04, after run #389 held the whole edition back for two wrong
lines (a date the card's own points contradicted, and an "18,000 feet" no
source carries). pipeline/editorial/cut_confirmed.py runs at the end of the
export, before the gate. Planted here, against the real grounding index:

  - a summary sentence with a number no source carries is cut from feed.json,
    the latest archive row and both database tables; the other sentences are
    kept word for word and nothing is written in the cut line's place;
  - a point with a number no source carries is cut from every copy;
  - after the cuts, the gate's own audit confirms nothing (F-1 passes);
  - a card whose HEAD carries the finding cannot be fixed by a cut, and a
    card is never pulled from the feed (that would move an unprinted story,
    with no /story/ page, into the twenty): it is left as it is, reported, and
    the gate still holds the edition, as before;
  - a "cannot confirm" card (a stub record) is never cut: absence of evidence
    is not evidence of absence;
  - a clean card is untouched;
  - cuts.json records each cut, and holds no publisher prose.

    python3 tests/test_cut_confirmed.py
"""
from __future__ import annotations

import json
import pathlib
import sqlite3
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.editorial import cut_confirmed  # noqa: E402
from pipeline.editorial import grounding as G  # noqa: E402
from pipeline.validation import rigor  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'ok' if cond else 'FAIL'}] {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


SOURCE = ("Officials said 312 people were evacuated from the valley on Tuesday. "
          "The governor said the state would rebuild every home that was lost. "
          "Rescue teams from Operation Safe Harbor moved 312 people by evening. "
          "The river crested at 9 metres before dawn.")
GOOD_1 = "Officials said 312 people were evacuated from the valley on Tuesday."
GOOD_2 = "The river crested at 9 metres before dawn."
BAD = "The flood destroyed 4,700 homes across the region."
POINT_OK = "Outlets agree that 312 people were evacuated."
POINT_BAD = "Some sources report the river crested at 14 metres."


def article(cid: str, i: int, text: str = SOURCE) -> dict:
    return {"id": f"{cid}-a{i}", "url": f"https://example.org/{cid}/{i}",
            "title": "Valley evacuated", "summary": "", "full_text": text}


def card(cid: str, summary: str, title="Valley Evacuated After Floods",
         cons=None, div=None) -> dict:
    return {"id": cid, "title": title, "summary": summary, "summary_tier": "flash",
            "source_count": 5, "consensus_points": list(cons or []),
            "divergence_points": list(div or [])}


BAD_CARD = "c-bad"
HEAD_CARD = "c-head"
STUB_CARD = "c-stub"
CLEAN_CARD = "c-clean"
BUILT = "2026-10-04T16:42:33Z"


def build_tree(with_head: bool = True) -> tuple[pathlib.Path, str]:
    d = pathlib.Path(tempfile.mkdtemp(prefix="cut-"))
    (d / G.DIRNAME).mkdir()
    cards = [
        card(BAD_CARD, f"{GOOD_1} {BAD} {GOOD_2}", cons=[POINT_OK], div=[POINT_BAD]),
        card(HEAD_CARD, f"{GOOD_1} {GOOD_2}", title="Flood Destroys 4,700 Homes"),
        card(STUB_CARD, f"{GOOD_1} {BAD}"),
        card(CLEAN_CARD, f"{GOOD_1} {GOOD_2}", cons=[POINT_OK]),
    ]
    if not with_head:
        cards = [c for c in cards if c["id"] != HEAD_CARD]
    (d / "feed.json").write_text(json.dumps({"clusters": cards, "builtAt": BUILT}))
    for cid in (BAD_CARD, HEAD_CARD, STUB_CARD, CLEAN_CARD):
        rec = G.build_record(cid, [article(cid, i) for i in range(3)], stage=G.STAGE_PRE)
        if cid == STUB_CARD:
            for a in rec["articles"]:
                a["stub"] = True
        (d / G.DIRNAME / f"{cid}.json").write_text(json.dumps(rec))
    run = {"startedAt": "2026-10-04T15:00:00Z",
           "stage2": {"fresh_ids": [BAD_CARD, HEAD_CARD, CLEAN_CARD]}}
    (d / rigor.RUN_NAME).write_text(json.dumps(run))
    archive = [dict(c, source_cluster_id=c["id"], printed_on="2026-10-04") for c in cards]
    archive.append(dict(card(BAD_CARD, f"{GOOD_1} {BAD}"), source_cluster_id=BAD_CARD,
                        printed_on="2026-10-03"))
    (d / "archive.json").write_text(json.dumps(archive))

    db = str(d / "state.db")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE story_clusters (id TEXT, title TEXT, summary TEXT, "
                "consensus_points TEXT, divergence_points TEXT)")
    con.execute("CREATE TABLE printed_stories (id TEXT, source_cluster_id TEXT, printed_on TEXT, "
                "title TEXT, summary TEXT, consensus_points TEXT, divergence_points TEXT)")
    for c in cards:
        con.execute("INSERT INTO story_clusters VALUES (?,?,?,?,?)",
                    [c["id"], c["title"], c["summary"], json.dumps(c["consensus_points"]),
                     json.dumps(c["divergence_points"])])
        con.execute("INSERT INTO printed_stories VALUES (?,?,?,?,?,?,?)",
                    [f"p-{c['id']}", c["id"], "2026-10-04", c["title"], c["summary"],
                     json.dumps(c["consensus_points"]), json.dumps(c["divergence_points"])])
    con.commit()
    con.close()
    return d, db


def main() -> int:
    d, db = build_tree()
    clean_before = next(c for c in json.loads((d / "feed.json").read_text())["clusters"]
                        if c["id"] == CLEAN_CARD)

    # The gate fails the planted tree before the cut.
    feed0 = json.loads((d / "feed.json").read_text())
    audit0 = rigor.audit_feed(feed0, d, rigor.fresh_ids(rigor.run_counters(d, BUILT)))
    confirmed0 = [c["id"] for c in audit0["cards"]
                  if any(f["status"] == "confirmed" for f in c["findings"])]
    check("the planted tree fails the gate before the cut",
          set(confirmed0) == {BAD_CARD, HEAD_CARD}, str(confirmed0))

    done = cut_confirmed.run(d, db)

    feed = json.loads((d / "feed.json").read_text())
    by = {c["id"]: c for c in feed["clusters"]}
    bad = by.get(BAD_CARD)
    check("a wrong summary sentence is cut from the feed",
          bad is not None and BAD not in bad["summary"], bad and bad["summary"])
    check("the card's other sentences are kept word for word, nothing written in",
          bad is not None and bad["summary"] == f"{GOOD_1} {GOOD_2}", bad and bad["summary"])
    check("a wrong point is cut", bad is not None and POINT_BAD not in bad["divergence_points"]
          and bad["consensus_points"] == [POINT_OK], bad and json.dumps(bad))
    check("a card whose head is wrong is left in place, never pulled from the feed",
          by.get(HEAD_CARD, {}).get("title") == "Flood Destroys 4,700 Homes"
          and [c["id"] for c in feed["clusters"]] == [BAD_CARD, HEAD_CARD, STUB_CARD, CLEAN_CARD]
          and done.get("left") == 1, str(done))
    check("a cannot-confirm card is never cut",
          by.get(STUB_CARD, {}).get("summary") == f"{GOOD_1} {BAD}", json.dumps(by.get(STUB_CARD)))
    check("a clean card is untouched", by.get(CLEAN_CARD) == clean_before)

    arch = json.loads((d / "archive.json").read_text())
    today = {r["source_cluster_id"]: r for r in arch if r["printed_on"] == "2026-10-04"}
    check("the latest archive row is cut the same way",
          today.get(BAD_CARD, {}).get("summary") == f"{GOOD_1} {GOOD_2}"
          and POINT_BAD not in today.get(BAD_CARD, {}).get("divergence_points", []))
    check("the head card's archive row is left as it was", HEAD_CARD in today)
    older = [r for r in arch if r["printed_on"] == "2026-10-03"]
    check("an earlier day's archive row is left as printed (a correction's job, not this)",
          older and BAD in older[0]["summary"])

    con = sqlite3.connect(db)
    sc = dict(con.execute("SELECT id, summary FROM story_clusters").fetchall())
    ps = dict(con.execute("SELECT id, summary FROM story_clusters").fetchall())
    pts = con.execute("SELECT divergence_points FROM story_clusters WHERE id=?", [BAD_CARD]).fetchone()[0]
    printed = [r[0] for r in con.execute("SELECT source_cluster_id FROM printed_stories")]
    printed_bad = con.execute("SELECT summary FROM printed_stories WHERE source_cluster_id=?",
                              [BAD_CARD]).fetchone()[0]
    con.close()
    check("the state database is cut, so the next export cannot put it back",
          sc[BAD_CARD] == f"{GOOD_1} {GOOD_2}" and printed_bad == f"{GOOD_1} {GOOD_2}"
          and POINT_BAD not in json.loads(pts), f"{sc[BAD_CARD]!r} / {printed_bad!r}")
    check("no printed row is deleted", sorted(printed) == sorted([BAD_CARD, HEAD_CARD, STUB_CARD, CLEAN_CARD])
          and HEAD_CARD in ps)

    audit = rigor.audit_feed(feed, d, rigor.fresh_ids(rigor.run_counters(d, BUILT)))
    left = [(c["id"], f["message"]) for c in audit["cards"]
            for f in c["findings"] if f["status"] == "confirmed"]
    check("what a cut cannot fix still fails the gate (the edition is held, as before)",
          left and all(cid == HEAD_CARD for cid, _ in left), str(left))

    d2, db2 = build_tree(with_head=False)
    cut_confirmed.run(d2, db2)
    feed2 = json.loads((d2 / "feed.json").read_text())
    audit2 = rigor.audit_feed(feed2, d2, rigor.fresh_ids(rigor.run_counters(d2, BUILT)))
    left2 = [(c["id"], f["message"]) for c in audit2["cards"]
             for f in c["findings"] if f["status"] == "confirmed"]
    check("with only cuttable errors, after the cut the gate confirms nothing (F-1 passes)",
          not left2, str(left2))

    cuts = json.loads((d / cut_confirmed.CUTS_NAME).read_text())
    rec = {c["id"]: c for c in cuts["cards"]}
    check("cuts.json records each cut, and what could not be cut",
          rec.get(BAD_CARD, {}).get("sentences", [{}])[0].get("text") == BAD
          and rec.get(BAD_CARD, {}).get("points", [{}])[0].get("text") == POINT_BAD
          and bool(rec.get(HEAD_CARD, {}).get("left")), json.dumps(cuts)[:300])
    check("cuts.json carries no publisher prose (only the card's own lines)",
          SOURCE not in json.dumps(cuts))

    # Idempotent: a second pass over the cut tree changes nothing.
    before = (d / "feed.json").read_text()
    again = cut_confirmed.run(d, db)
    check("a second pass cuts nothing", (d / "feed.json").read_text() == before
          and not again.get("sentences") and not again.get("points"), str(again))

    # A summary with paragraph breaks keeps them.
    check("a paragraph break survives a cut",
          cut_confirmed.remove_sentence(f"{GOOD_1}\n\n{BAD} {GOOD_2}", BAD) == f"{GOOD_1}\n\n{GOOD_2}")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1
    print("\nPASS  rule 1 cut and publish: wrong lines cut from every copy, the rest ships, the gate passes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
