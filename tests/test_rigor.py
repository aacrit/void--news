#!/usr/bin/env python3
"""Rigor: the coverage numbers are honest, and the floors can fail.

Rev 86 WS-G (docs/proposals/FACTUAL-RIGOR-PLAN-2026-10-02.md, section 1 and
gap 8). `pipeline/validation/rigor.py` measures, per product, the share of
published sentences carrying an anchor an enforced deterministic rule checked
against source evidence, and holds the floors a run must clear before its data
commit. INTERNAL ONLY (CEO, 2026-10-03): rigor.json and the series are not
rendered anywhere.

Default mode (auto-merge):
  - the committed rigor.json carries no string over twelve words, and when it
    describes the committed feed its per-product counts and floors recompute
    exactly from the committed outputs (a stale file is a warning here, since
    a branch carries whatever main's last pipeline run wrote);
  - the series row for that feed exists;
  - every floor fails on a planted defect and holds without it:
      F-1  a number in no source, a quotation in no source, a sentence that
           opens on another story, on a card or a point, against a confirmable
           record; and the SAME finding against a format-2 record, a stub
           record or an export-stage record is "cannot confirm", never a
           failure;
      F-2  a shipped card with no record; a fresh card whose record was built
           after truncation;
      F-3  a TL;DR, Opinion or On Air shipped whose grounding did not complete
           and is not labelled, or that carries no flag at all after the flag
           existed (CEO, 2026-10-03: ship labelled, never withhold);
      F-5  a correction with no gate, a gate that is advisory or names no
           file, a correction the export did not apply;
  - verify_production's served-card check fails the planted card and reports
    the stub one;
  - the run counters are a no-op outside a run and keep no prose.

--floors (pipeline.yml, after rigor.py --write, before the data commit):
the same, except the committed rigor.json MUST describe this feed, and the
floors are asserted on this run's data.

    python3 tests/test_rigor.py [--floors]
"""
from __future__ import annotations

import copy
import csv
import io
import json
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from pipeline.editorial import grounding as G  # noqa: E402
from pipeline.validation import rigor  # noqa: E402

FLOORS = "--floors" in sys.argv
failures: list[str] = []
warnings: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'ok' if cond else 'FAIL'}] {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def long_strings(node, path=""):
    if isinstance(node, str):
        if len(node.split()) > rigor.MAX_WORDS:
            yield path, node
    elif isinstance(node, dict):
        for k, v in node.items():
            yield from long_strings(k, f"{path}.<key>")
            yield from long_strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for v in node:
            yield from long_strings(v, f"{path}[]")


# ===================================================================== fixtures
SOURCE = ("Officials said 312 people were evacuated from the valley on Tuesday. "
          "The governor said \"we will rebuild every home that was lost\" at a briefing. "
          "Rescue teams from Operation Safe Harbor moved 312 people by evening.")
CARD_OK = ("Officials said 312 people were evacuated from the valley on Tuesday. "
           "The governor said \"we will rebuild every home that was lost\" at a briefing.")


def article(i: int, full_text: str = SOURCE) -> dict:
    return {"id": f"a{i}", "url": f"https://example.org/{i}", "title": "Valley evacuated",
            "summary": "", "full_text": full_text}


def card(cid: str, summary: str = CARD_OK, points=None, title="Valley Evacuated After Floods") -> dict:
    return {"id": cid, "title": title, "summary": summary, "summary_tier": "flash",
            "source_count": 5, "consensus_points": list(points or []),
            "divergence_points": []}


def tree(cards: list[dict], records: dict[str, dict], built_at="2026-10-03T12:00:00Z",
         run: dict | None = None) -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp(prefix="rigor-"))
    (d / G.DIRNAME).mkdir()
    (d / "feed.json").write_text(json.dumps({"clusters": cards, "builtAt": built_at}))
    for cid, rec in records.items():
        (d / G.DIRNAME / f"{cid}.json").write_text(json.dumps(rec))
    if run is not None:
        (d / rigor.RUN_NAME).write_text(json.dumps(run))
    return d


def pre_record(cid: str, stub: bool = False) -> dict:
    arts = [article(i) for i in range(3)]
    rec = G.build_record(cid, arts, stage=G.STAGE_PRE)
    if stub:
        rec["articles"][0]["stub"] = True
    return rec


def as_format2(rec: dict) -> dict:
    r = copy.deepcopy(rec)
    r["format"] = 2
    r.pop("contexts", None)
    r.pop("junctions", None)
    return r


def floors_for(build: pathlib.Path, brief=None, corr=None, label_wired=lambda p: True):
    feed = json.loads((build / "feed.json").read_text())
    run = rigor.run_counters(build, feed.get("builtAt"))
    audit = rigor.audit_feed(feed, build, rigor.fresh_ids(run))
    return rigor.floors(audit, run, brief, corr or {"ungated": [], "unapplied": 0},
                        label_wired=label_wired), audit


# ===================================================================== F-1
print("\n-- F-1: confirmed grounded findings on shipped cards and points")
cid = "11111111-0000-0000-0000-000000000001"
fl, audit = floors_for(tree([card(cid)], {cid: pre_record(cid)}))
check("F-1 holds on a clean card against a confirmable record", not fl["F-1"], str(fl["F-1"]))
check("the clean record is confirmable", audit["cards"][0]["state"] == rigor.CONFIRMABLE,
      audit["cards"][0]["state"])

planted_number = CARD_OK + " The flood destroyed 4,419 homes."
fl, _ = floors_for(tree([card(cid, planted_number)], {cid: pre_record(cid)}))
check("F-1 fails a number in no source (E-13)", any("E-13 absent" in x for x in fl["F-1"]), str(fl))

planted_quote = CARD_OK + " The mayor said \"nobody will ever be forgotten here again\" afterwards."
fl, _ = floors_for(tree([card(cid, planted_quote)], {cid: pre_record(cid)}))
check("F-1 fails a quotation in no source (E-14)", any("E-14 absent" in x for x in fl["F-1"]), str(fl))

planted_shift = CARD_OK + " Separately, a concert in the capital was cancelled."
fl, _ = floors_for(tree([card(cid, planted_shift)], {cid: as_format2(pre_record(cid))}))
check("F-1 fails a sentence that opens on another story (E-16), whatever the record",
      any("E-16" in x for x in fl["F-1"]), str(fl))

fl, _ = floors_for(tree([card(cid, points=["Outlets agree 9,999 homes were lost."])],
                        {cid: pre_record(cid)}))
check("F-1 fails a point carrying a number in no source", any("point 0 E-13" in x for x in fl["F-1"]), str(fl))

fl, _ = floors_for(tree([card(cid, points=["Separately, markets fell."])], {cid: pre_record(cid)}))
check("F-1 fails a point that opens on another story", any("point 0 E-16" in x for x in fl["F-1"]), str(fl))

fl, audit = floors_for(tree([card(cid, points=[
    "Sources differ in political framing by 31 points of lean"])], {cid: pre_record(cid)}))
check("a machine-written point (Void's own measurement) is not audited",
      not fl["F-1"] and not audit["cards"][0]["findings"], str(fl))

for label, rec in (("a format-2 record", as_format2(pre_record(cid))),
                   ("a stub record behind a card not written this run", pre_record(cid, stub=True)),
                   ("an export-stage record", G.build_record(cid, [article(i) for i in range(3)],
                                                             stage=G.STAGE_EXPORT))):
    fl, audit = floors_for(tree([card(cid, planted_number)], {cid: rec}))
    st = [f["status"] for f in audit["cards"][0]["findings"]]
    check(f"the same number against {label} is cannot confirm, never a failure",
          not fl["F-1"] and st == ["cannot confirm"], f"{fl['F-1']} {st}")

# A fresh card read the stub it was written from, so a stub row is covered.
run_ok = {"startedAt": "2026-10-03T10:00:00Z", "stage2": {"fresh_ids": [cid]}}
fl, audit = floors_for(tree([card(cid, planted_number)], {cid: pre_record(cid, stub=True)},
                            run=run_ok))
check("a stub row behind a FRESH card is covered, so the finding is confirmed",
      any("E-13 absent" in x for x in fl["F-1"]), f"{fl} {audit['cards'][0]['state']}")

big = article(9, "Officials said 312 people were evacuated. " + "x " * 2000)
big["summary"] = "y " * 900
rec_cap = G.build_record(cid, [big], stage=G.STAGE_PRE)
check("a record whose cap falls short of the writer's window cannot confirm",
      rigor.evidence_state(rec_cap, True) == "index cap below writer window",
      rigor.evidence_state(rec_cap, True))

cid2 = "11111111-0000-0000-0000-000000000002"
point_rival = "The Operation Weekly says 312 people were moved."
fl, audit = floors_for(tree([card(cid2, points=[point_rival])], {cid2: pre_record(cid2)}))
kinds = {(f["kind"], f["status"]) for f in audit["cards"][0]["findings"]}
check("a point's number beside an outlet name is advisory, not a failure",
      not fl["F-1"] and kinds == {("misattached", "advisory")}, f"{kinds}")
fl, _ = floors_for(tree([card(cid2, CARD_OK + " " + point_rival)], {cid2: pre_record(cid2)}))
check("the same attachment on the CARD is enforced (E-13 contexts)",
      any("E-13 misattached" in x for x in fl["F-1"]), str(fl["F-1"]))

bench = [card(f"22222222-0000-0000-0000-0000000000{i:02d}") for i in range(21)]
bench[20]["summary"] = planted_number
recs = {c["id"]: pre_record(c["id"]) for c in bench}
fl, audit = floors_for(tree(bench, recs))
check("a card past the displayed twenty is reported, never failed",
      not fl["F-1"] and any(f["status"] == "confirmed" for f in audit["cards"][20]["findings"])
      and not audit["cards"][20]["shipped"], str(fl["F-1"]))

# ===================================================================== F-2
print("\n-- F-2: evidence exists for every shipped card")
fl, _ = floors_for(tree([card(cid)], {}))
check("F-2 fails a shipped card with no record", bool(fl["F-2"]), str(fl))
exp = G.build_record(cid, [article(i) for i in range(3)], stage=G.STAGE_EXPORT)
fl, _ = floors_for(tree([card(cid)], {cid: exp}, run=run_ok))
check("F-2 fails a fresh card whose record was built after truncation",
      any("fresh card" in x for x in fl["F-2"]), str(fl))
fl, _ = floors_for(tree([card(cid)], {cid: pre_record(cid)}, run=run_ok))
check("F-2 holds for a fresh card with a pre-truncation record", not fl["F-2"], str(fl))
stale_run = {"startedAt": "2026-09-30T10:00:00Z", "stage2": {"fresh_ids": [cid]}}
fl, _ = floors_for(tree([card(cid)], {cid: exp}, run=stale_run))
check("run counters from another run are not read as this run's", not fl["F-2"], str(fl))

# ===================================================================== F-3
print("\n-- F-3: a derived product that shipped unverified is labelled")
d = tree([card(cid)], {cid: pre_record(cid)})
base = {"tldr_text": "One. Two.", "opinion_text": "Three.", "audio_url": "/a.mp3",
        "audio_script": "## STORY 1 | X\nA: Four.", "created_at": "2026-10-04T10:00:00Z",
        "generator": "gemini-flash"}
ok_brief = dict(base, grounding_ran={"tldr": True, "opinion": True, "onair": True})
fl, _ = floors_for(d, brief=ok_brief)
check("F-3 holds when every pass completed", not fl["F-3"], str(fl["F-3"]))
lab = dict(base, grounding_ran={"tldr": False, "opinion": True, "onair": False})
fl, _ = floors_for(d, brief=lab, label_wired=rigor._label_wired)
check("F-3 holds when an unverified product is labelled (the real frontend wiring)",
      not fl["F-3"], str(fl["F-3"]))
fl, _ = floors_for(d, brief=lab, label_wired=lambda p: False)
check("F-3 fails an unverified product with no label",
      sorted(x.split()[0] for x in fl["F-3"]) == ["onair", "tldr"], str(fl["F-3"]))
fl, _ = floors_for(d, brief=dict(base))
check("F-3 fails a product with no flag after the flag existed", len(fl["F-3"]) == 3, str(fl["F-3"]))
fl, _ = floors_for(d, brief=dict(base, created_at="2026-10-02T21:30:27Z"))
check("a brief written before the flag existed is reported, not failed", not fl["F-3"], str(fl["F-3"]))
fl, _ = floors_for(d, brief=dict(base, generator="stub-on-failure:RuntimeError",
                                 tldr_text="Daily brief unavailable. See top stories."))
check("the stub row (no facts) is not a product", not fl["F-3"], str(fl["F-3"]))
fl, _ = floors_for(d, brief=dict(base, grounding_ran=json.dumps({"tldr": True, "opinion": True,
                                                                  "onair": True})))
check("a flag stored as a JSON string is read", not fl["F-3"], str(fl["F-3"]))
check("the frontend wires the label for every product",
      all(rigor._label_wired(p) for p in rigor.DERIVED))

# ===================================================================== F-5
print("\n-- F-5: every correction is applied and names its gate")
feed = {"clusters": [card(cid, "A. The wrong sentence. B.")]}
edit = {"field": "summary", "find": "The wrong sentence. ", "replace": ""}
good = [{"cluster": cid, "date": "t", "reason": "r", "gate": "E-13", "edits": [edit]}]
r = rigor.corrections_report({"clusters": [card(cid, "A. B.")]}, [], good)
check("F-5 holds for an applied, gated correction", not r["ungated"] and not r["unapplied"], str(r))
r = rigor.corrections_report(feed, [], good)
check("F-5 fails a correction the export did not apply", r["unapplied"] == 1, str(r))
for label, gate in (("no gate", None), ("an advisory rule", "E-07"),
                    ("a file that does not exist", "tests/test_nothing_here.py"), ("an empty list", [])):
    entry = dict(good[0])
    if gate is None:
        entry.pop("gate")
    else:
        entry["gate"] = gate
    r = rigor.corrections_report({"clusters": []}, [], [entry])
    check(f"F-5 fails a correction naming {label}", r["ungated"] == [0], str(r))
r = rigor.corrections_report({"clusters": []}, [], [dict(good[0], gate=["E-16", "tests/test_rigor.py"])])
check("a gate list resolves when every gate does", not r["ungated"], str(r))
committed = rigor.corrections_report({"clusters": []}, [])
check("every committed correction names a gate that resolves", not committed["ungated"],
      str(committed["ungated"]))

# ===================================================================== coverage
print("\n-- coverage: counted with the checks' own splitters")
summary = ("Officials said 312 people were evacuated. Rain fell all week. "
           "The governor said \"we will rebuild every home that was lost\" at a briefing.")
c = card(cid, summary)
cov = rigor.card_coverage([c], {"cards": [{"id": cid, "state": rigor.CONFIRMABLE}]})
check("card summary: 3 sentences, 2 anchored, 2 checked",
      (cov["card_summary"]["sentences"], cov["card_summary"]["anchored"],
       cov["card_summary"]["checked"]) == (3, 2, 2), str(cov["card_summary"]))
cov = rigor.card_coverage([c], {"cards": [{"id": cid, "state": "stub rows, card not fresh"}]})
check("an unconfirmable card's anchors are anchored, not checked",
      cov["card_summary"]["checked"] == 0 and cov["card_summary"]["anchored"] == 2)
script = ("## OPEN\nA: From Void News, this is On Air. It's Friday, October second.\n\n"
          "## MENU\nA: On the desk today.\n\n## STORY 1 | X\nA: Officials evacuated "
          "three hundred twelve people. Rain fell.\n\n## CLOSE\nA: That's On Air from Void News."
          "\n\n## SAY\nGeffray = zhef-ray")
sents = rigor.onair_sentences(script)
check("On Air: the formulas, OPEN, CLOSE and SAY are not counted",
      sents == ["Officials evacuated three hundred twelve people.", "Rain fell."], str(sents))
dc = rigor.derived_coverage(dict(base, audio_script=script,
                                 grounding_ran={"tldr": True, "opinion": False, "onair": True}))
check("On Air: a spoken number is an anchor, checked when grounding ran",
      (dc["onair"]["anchored"], dc["onair"]["checked"]) == (1, 1), str(dc["onair"]))
check("a product whose grounding did not run has nothing checked",
      dc["opinion"]["checked"] == 0)
check("reason classes are labels, not sentences",
      [rigor.reason_class(x) for x in (
          "E-13 4419 is in no source", "number '20 percent' is not in this story's text",
          "E-16 opens on another story", "names another story that has its own paragraph",
          "a hedge stands in for attribution (E-15)", "weekday 'Friday' is not in this story's text")]
      == ["number", "number", "other story", "other story", "hedge", "date"])

# ===================================================================== hooks
print("\n-- run counters")
os.environ.pop(rigor.RUN_ENV, None)
tmp = pathlib.Path(tempfile.mkdtemp(prefix="rigor-run-"))
before = (rigor.BUILD / rigor.RUN_NAME).read_bytes() if (rigor.BUILD / rigor.RUN_NAME).exists() else None
rigor.note_run("onair", {"grounding_ran": True})
after = (rigor.BUILD / rigor.RUN_NAME).read_bytes() if (rigor.BUILD / rigor.RUN_NAME).exists() else None
check("note_run outside a run writes nothing", before == after)
rigor.start_run(tmp)
rigor.note_run("brief", {"cuts_by_reason": {"number": 2},
                         "why": "a sentence the writer should never have kept in the brief at all"})
blob = json.loads((tmp / rigor.RUN_NAME).read_text())
check("start_run then note_run records the section", blob["brief"]["cuts_by_reason"] == {"number": 2})
check("the counters keep no string over twelve words", not list(long_strings(blob)), str(blob))
os.environ.pop(rigor.RUN_ENV, None)

# ===================================================================== served
print("\n-- verify_production: the served cards against the committed index")
import verify_production as vp  # noqa: E402

page = vp.Page(
    '<span class="story-card__headline-text">Valley Evacuated After Floods</span>'
    f'<p class="story-card__summary">{planted_number}</p>')
vp.GROUNDING_REPORT.clear()
out = vp.check_served_grounding(page, tree([card(cid, planted_number)], {cid: pre_record(cid)}))
check("a served card carrying a number in no source fails the served gate",
      any("E-13" in x for x in out), str(out))
vp.GROUNDING_REPORT.clear()
out = vp.check_served_grounding(page, tree([card(cid, planted_number)],
                                           {cid: pre_record(cid, stub=True)}))
check("against a stub record it is reported, never failed",
      not out and any("cannot confirm" in x for x in vp.GROUNDING_REPORT), str(vp.GROUNDING_REPORT))
vp.GROUNDING_REPORT.clear()

# ===================================================================== committed
print("\n-- the committed rigor.json and series")
OUT = rigor.BUILD / rigor.OUT_NAME
check("frontend/build-data/rigor.json exists", OUT.exists())
if OUT.exists():
    committed_r = json.loads(OUT.read_text(encoding="utf-8"))
    prose = list(long_strings(committed_r))
    check("rigor.json carries no string over twelve words", not prose, str(prose[:2]))
    feed_now = json.loads((rigor.BUILD / "feed.json").read_text(encoding="utf-8"))
    fresh_r = rigor.compute()
    same_feed = committed_r.get("builtAt") == feed_now.get("builtAt")
    if FLOORS:
        check("rigor.json describes this run's feed (run rigor.py --write first)", same_feed,
              f"{committed_r.get('builtAt')} vs {feed_now.get('builtAt')}")
    elif not same_feed:
        warnings.append(f"rigor.json describes {committed_r.get('builtAt')}, the feed is "
                        f"{feed_now.get('builtAt')}: the next pipeline run rewrites it")
    if same_feed:
        for p in rigor.PRODUCTS:
            a, b = committed_r["products"][p], fresh_r["products"][p]
            check(f"{p} counts recompute from the committed outputs",
                  all(a.get(k) == b.get(k) for k in ("sentences", "anchored", "checked")),
                  f"committed {a.get('sentences')}/{a.get('anchored')}/{a.get('checked')}, "
                  f"recomputed {b.get('sentences')}/{b.get('anchored')}/{b.get('checked')}")
        check("the committed floors are the recomputed floors",
              committed_r.get("floors") == fresh_r["floors"], f"{committed_r.get('floors')}")
        rows = list(csv.DictReader(io.StringIO(rigor.SERIES.read_text(encoding="utf-8")))) \
            if rigor.SERIES.exists() else []
        check("docs/data/rigor-series.csv has this run's row",
              any(r.get("built_at") == str(feed_now.get("builtAt")) for r in rows))
        check("the series header is the declared one",
              rigor.SERIES.exists() and rigor.SERIES.read_text().splitlines()[0]
              == ",".join(rigor.SERIES_COLUMNS))
    run_file = rigor.BUILD / rigor.RUN_NAME
    if run_file.exists():
        check("rigor-run.json keeps no string over twelve words",
              not list(long_strings(json.loads(run_file.read_text()))))

# ===================================================================== this run
print("\n-- the floors on the committed data")
real = rigor.compute()
print(rigor.format_summary(real))
for floor, lines in sorted(real["floorDetail"].items()):
    for line in lines:
        print(f"      {floor}: {line}")
for floor in ("F-1", "F-2", "F-3", "F-5"):
    check(f"{floor} holds on the committed data", real["floors"][floor] == "pass",
          real["floors"][floor])

for w in warnings:
    print(f"[warn] {w}")
if failures:
    print(f"\nFAIL  {len(failures)} rigor check(s): {failures[:5]}")
    sys.exit(1)
print(f"\nPASS  rigor{' floors' if FLOORS else ''}: the numbers recompute and every floor "
      f"can fail")
