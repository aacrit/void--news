#!/usr/bin/env python3
"""The History thesis gates, T-01..T-20, each against a planted defect.

A rule that has only ever been run against clean copy is a comment, not a
gate (tests/test_history_script.py says the same about H-01..H-11). So this
file builds one small thesis with its ledger that passes every check, asserts
that it does, and then breaks exactly one thing at a time and asserts the
right check fires. Then it runs the real theses under data/history/theses and
the T-14 parity check against the committed export.

The fixture is deliberately at the bar of §4e and not above it, so a check
that quietly stopped counting would show up here as the fixture failing T-13.

Run:  python3 tests/test_history_thesis.py        (also collectable by pytest)
"""
from __future__ import annotations

import copy
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.history.ledger import load_ledger, validate_ledger  # noqa: E402
from pipeline.history.thesis_checks import validate_thesis  # noqa: E402
from pipeline.history.thesis_format import parse_thesis, split_sentences  # noqa: E402

SLUG = "fixture-event"
TODAY = "2026-09-24"

# ----------------------------------------------------------------- fixture

def _entry(i: str, tier: str, kind: str, author: str, title: str, year, producer: str,
           free: str | None, lang="en", region="europe", position=None, rights=None, doi=None):
    return {
        "id": i, "tier": tier, "kind": kind, "author": author, "title": title,
        "container": None, "publisher": "Fixture Press", "place": "The Hague", "year": year,
        "edition": None, "volume": None,
        "identifiers": {"isbn": None, "doi": doi, "archive_org": None, "hathitrust": None, "url": free},
        "access": {"free_copy": free, "verified_at": TODAY,
                   "verified_by": "document-fetch" if tier == "A" else "crossref-title-match",
                   "verified_title": title},
        "language": lang, "region_of_authorship": region, "position": position,
        "producer": producer, "rights": rights,
    }


def fixture_ledger() -> dict:
    A = [
        _entry("src-court-tj", "A", "judgment", "The Court", "Trial Judgment in the Harbour Case", 2001,
               "the-court", "https://example.org/court/tj.pdf", rights="public"),
        _entry("src-court-aj", "A", "judgment", "The Court", "Appeal Judgment in the Harbour Case", 2004,
               "the-court", "https://example.org/court/aj.pdf", rights="public"),
        _entry("src-council-res", "A", "resolution", "The Council", "Resolution 100 on the Harbour", 1993,
               "the-council", "https://example.org/council/100.pdf", rights="public"),
        _entry("src-sg-report", "A", "report", "The Secretariat", "Report on the Fall of the Harbour", 1999,
               "the-secretariat", "https://example.org/sg/report.pdf", rights="public"),
        _entry("src-witness", "A", "testimony", "A. Witness", "Testimony before the Court", 1996,
               "the-court", "https://example.org/court/witness.pdf", rights="public"),
        _entry("src-ministry", "A", "report", "The Ministry", "Ministry Report on the Harbour", 2002,
               "the-ministry", "https://example.org/ministry/report.pdf", rights="public"),
    ]
    B = [
        _entry(f"src-scholar-{n}", "B", "journal-article", f"Scholar {n}", f"Study {n} of the Harbour", 2000 + n,
               "scholarship", f"https://example.org/oa/{n}.pdf" if n <= 4 else None,
               lang="en" if n % 2 else "nl", region="europe" if n % 3 else "americas",
               position={1: "court-record", 2: "institutional", 3: "critical"}.get(n),
               doi=f"10.1000/fixture.{n}")
        for n in range(1, 9)
    ]
    D = [_entry("src-partisan", "D", "party-history", "Partisan, P.", "The Harbour Was a Lie", 2010,
                "partisan-press", "https://example.org/partisan.pdf", region="europe", position="critical")]
    return {
        "slug": SLUG,
        "entries": A + B + D,
        "gaps": [{"entry": f"src-scholar-{n}", "what": f"Study {n} of the Harbour",
                  "tried": ["https://example.org/paywall"], "status": "paywalled, no open copy"}
                 for n in range(5, 9)],
        "positions": [
            {"id": "court-record", "name": "The court record", "holders": ["The Court"],
             "rests_on": ["src-court-tj", "src-court-aj", "src-scholar-1"],
             "claim": "The killings were organised executions.", "omits": "What the ministry knew that week.",
             "adjudications": [{"claim": "The killings were organised executions.", "verdict": "supported",
                                "basis": "presence", "rests_on": ["src-court-tj.para84", "src-sg-report.para503"],
                                "reasoning": "Two records, one from the court and one from the secretariat, describe organised executions."}]},
            {"id": "institutional", "name": "The institutional account", "holders": ["The Secretariat"],
             "rests_on": ["src-sg-report", "src-scholar-2"],
             "claim": "The failure ran from the council to the field.", "omits": "The agency of the perpetrators.",
             "adjudications": [{"claim": "The failure ran from the council to the field.", "verdict": "qualified",
                                "basis": "presence", "rests_on": ["src-sg-report.para503"],
                                "reasoning": "One producer, the secretariat, so the verdict is capped at qualified."}]},
            {"id": "critical", "name": "The critical account", "holders": ["Scholar 3", "Partisan, P."],
             "rests_on": ["src-scholar-3", "src-partisan"],
             "claim": "The numbers are inflated.", "omits": "The forensic record.",
             "adjudications": [{"claim": "The numbers are inflated.", "verdict": "contradicted",
                                "basis": "presence", "rests_on": ["src-court-tj.para84", "src-sg-report.para503"],
                                "reasoning": "The court and the secretariat, two producers, both count 7,000 to 8,000."}]},
        ],
        "contested": [
            {"id": "death-toll", "claim": "How many were killed",
             "rows": [
                 {"position": "court-record", "holds": "7,000 to 8,000", "figures": ["7000", "8000"],
                  "source": "src-court-tj", "locator": "para84"},
                 {"position": "critical", "holds": "fewer than 2,000", "figures": ["2000"],
                  "source": "src-partisan", "locator": None},
             ]},
        ],
        "exhibits": [
            {"id": "ex-photo", "kind": "image", "title": "The harbour wall", "creator": "A. Photographer",
             "date": "2009", "repository": "Wikimedia Commons", "accession": "File:Harbour_wall.jpg",
             "licence": "CC BY-SA 3.0", "url": "https://upload.wikimedia.org/x/harbour.jpg",
             "shows": "the wall in 2009", "does_not_show": "1995"},
            {"id": "ex-map", "kind": "map", "title": "The enclave", "creator": "Cartographer",
             "date": "1995", "repository": "Wikimedia Commons", "accession": "File:Enclave.png",
             "licence": "Public domain", "url": "https://upload.wikimedia.org/x/enclave.png",
             "shows": "the enclave", "does_not_show": "the road"},
            {"id": "ex-doc", "kind": "document", "title": "The resolution", "creator": "The Council",
             "date": "1993", "repository": "UN", "accession": "S/RES/100", "licence": "public",
             "url": "https://example.org/council/100.pdf", "source": "src-council-res", "locator": "op1"},
        ],
        "analyses": [
            {"id": "an-crowd", "title": "Four counts of one crowd",
             "method": "Every figure the record gives for the crowd, by document and date.",
             "finding": "The counts run from 17,500 to 25,000.", "confidence": "entailed",
             "against": None, "result": [17500, 25000],
             "derivation": {"compute": "range", "column": "count", "columns": ["document", "count"],
                            "rows": [{"document": "commander's report", "count": 17500, "extract": "src-court-tj.para84"},
                                     {"document": "witness", "count": 25000, "extract": "src-court-tj.para84"}]}},
        ],
    }


EXTRACTS = {
    "src-court-tj.para84.txt": ("src-court-tj", "para84", "https://example.org/court/tj.pdf",
                                "The Trial Chamber finds that 7,000 to 8,000 men were executed between 13 July 1995 and 19 July 1995, "
                                "after a crowd counted at 17,500 by the commander and 25,000 by a witness had gathered."),
    "src-court-aj.para37.txt": ("src-court-aj", "para37", "https://example.org/court/aj.pdf",
                                "The Appeals Chamber calls the massacre by its proper name: genocide."),
    "src-council-res.op1.txt": ("src-council-res", "op1", "https://example.org/council/100.pdf",
                                "Adopted on 16 April 1993. Demands that all parties treat the harbour as a safe area which should be free from any armed attack."),
    "src-sg-report.para503.txt": ("src-sg-report", "para503", "https://example.org/sg/report.pdf",
                                  "Through error and misjudgement we failed to do our part; 7,000 to 8,000 men were murdered."),
    "src-witness.p9.txt": ("src-witness", "p9", "https://example.org/court/witness.pdf",
                           "If you are sorry for them, line up with them."),
    "src-ministry.p12.txt": ("src-ministry", "p12", "https://example.org/ministry/report.pdf",
                             "The battalion numbered 600 and held 3 observation posts."),
    "src-scholar-1.p10.txt": ("src-scholar-1", "p10", "https://example.org/oa/1.pdf",
                              "The judgment settled the count at 7,000 to 8,000."),
    "src-scholar-2.p20.txt": ("src-scholar-2", "p20", "https://example.org/oa/2.pdf",
                              "Het rapport telde 600 soldaten in Potočari."),
    "src-scholar-3.p30.txt": ("src-scholar-3", "p30", "https://example.org/oa/3.pdf",
                              "The critical school holds the count inflated."),
    "src-scholar-4.p40.txt": ("src-scholar-4", "p40", "https://example.org/oa/4.pdf",
                              "The battalion's 3 posts fell in 2 days."),
}
RENDERINGS = {
    "src-scholar-2.p20.en.txt": "rendering: void-translation\nof: src-scholar-2.p20\nnames: Potočari=Potočari\n\n"
                                "The report counted 600 soldiers in Potočari.",
}

THESIS = """---
slug: fixture-event
status: published
audited_by: historiographic-auditor
audited_at: 2026-09-24
question: Did the safe area fail because it was never held?
claims:
  - The council declared a safe area and sent 600 men.
  - The killings were organised.
  - The count is a range.
episode_marks: []
---
## The question

The council declared the harbour a safe area in 1993.[^src-council-res op1] This thesis asks whether the area was ever held.

## The record

The record holds the trial judgment whole.[^src-court-tj para84] What it does not hold is said below.{i}

## The argument

### 1. The declaration

The resolution demanded that the harbour be “free from any armed attack”.[^src-council-res op1] The battalion numbered 600 men at 3 observation posts.[^src-ministry p12] A resolution is a sentence and a battalion is a number, and neither is a wall.{i}

::: exhibit src-council-res op1

::: episode chapter=0

### 2. The count

The Trial Chamber put the dead at 7,000 to 8,000.[^src-court-tj para84] The Appeals Chamber called it “by its proper name: genocide”.[^src-court-aj para37] The Dutch study counted the same battalion.[^src-scholar-2 p20]

::: analysis an-crowd

::: exhibit ex-photo

::: exhibit ex-map

## The historiography

::: position court-record

::: position institutional

::: position critical

### Where the record disagrees

::: contested death-toll

## What the record omits

- No source in this record was written by a member of the battalion. {against=institutional}
- No source in this record dates the order to move the graves. {against=court-record}
"""

SCRIPT = {"slug": SLUG, "words": 20, "segments": [
    {"kind": "OPEN", "lines": [{"speaker": "N", "text": "A safe area, the council called it."},
                               {"speaker": "N", "text": "Six hundred men held it."}]},
    {"kind": "SCENE", "title": "The harbour", "lines": [{"speaker": "N", "text": "The town fell in two days."}]},
    {"kind": "CLOSE", "lines": [{"speaker": "N", "text": "The wall still stands."}]},
], "say": {}}
EPISODE = {"url": "/audio/history/fixture.mp3", "durationSeconds": 60.0, "chapters": [
    {"startTime": 0.0, "title": "Opening", "kind": "segment"},
    {"startTime": 20.0, "title": "The harbour", "kind": "segment"},
    {"startTime": 40.0, "title": "Legacy", "kind": "segment"},
]}
EVENT = {"slug": SLUG, "title": "The Harbour", "region": "europe",
         "hero_image_url": "https://upload.wikimedia.org/x/hero.jpg", "media": []}


def build(tmp: pathlib.Path, ledger: dict | None = None, thesis: str | None = None,
          extracts: dict | None = None, renderings: dict | None = None):
    base = tmp / SLUG
    (base / "extracts").mkdir(parents=True, exist_ok=True)
    (base / "ledger.yaml").write_text(yaml.safe_dump(ledger or fixture_ledger(), sort_keys=False,
                                                     allow_unicode=True), encoding="utf-8")
    for name, (src, loc, url, text) in (extracts or EXTRACTS).items():
        (base / "extracts" / name).write_text(
            f"source: {src}\nlocator: {loc}\nurl: {url}\nread: {TODAY}\n\n{text}\n", encoding="utf-8")
    for name, text in (renderings or RENDERINGS).items():
        (base / "extracts" / name).write_text(text, encoding="utf-8")
    led = load_ledger(SLUG, evidence_dir=tmp)
    th = parse_thesis(thesis or THESIS, SLUG)
    return th, led


def ids(tmp, **kw) -> list[str]:
    th, led = build(tmp, **kw)
    return sorted({f.id for f in validate_thesis(th, led, EVENT, SCRIPT, EPISODE) if f.level == "fail"})


def mutated(fn) -> dict:
    d = copy.deepcopy(fixture_ledger())
    fn(d)
    return d


def entry(d: dict, i: str) -> dict:
    return next(e for e in d["entries"] if e["id"] == i)


# ------------------------------------------------------------------ tests

def test_sentence_splitter():
    s = split_sentences("He said “It ends here. Now.” and left.[^src-a p1] The count was 8,372 in 2.5 days.{i} Dr. Who saw p. 9.[^src-b p9]")
    assert [x.text for x in s] == ["He said “It ends here. Now.” and left.", "The count was 8,372 in 2.5 days.", "Dr. Who saw p. 9."], [x.text for x in s]
    assert s[0].markers == [("src-a", "p1")] and s[1].interpretive and s[2].markers == [("src-b", "p9")]
    assert s[1].numerals == ["8,372", "2.5"]


def test_fixture_is_clean():
    with tempfile.TemporaryDirectory() as t:
        found = ids(pathlib.Path(t))
        assert found == [], found


def test_t01_marker_to_nowhere():
    with tempfile.TemporaryDirectory() as t:
        assert "T-01" in ids(pathlib.Path(t), thesis=THESIS.replace("[^src-ministry p12]", "[^src-nobody p12]"))
        assert "T-01" in ids(pathlib.Path(t), thesis=THESIS.replace("[^src-ministry p12]", "[^src-ministry p99]"))
        # a number with a bare entry marker and no extract
        assert "T-01" in ids(pathlib.Path(t), thesis=THESIS.replace("[^src-ministry p12]", "[^src-ministry]"))


def test_t02_unsourced_and_interpretive():
    with tempfile.TemporaryDirectory() as t:
        assert "T-02" in ids(pathlib.Path(t), thesis=THESIS.replace("[^src-ministry p12]", ""))
        assert "T-02" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "neither is a wall in 1995.{i}"))
        allinterp = THESIS.replace("The resolution demanded that the harbour be “free from any armed attack”.[^src-council-res op1] The battalion numbered 600 men at 3 observation posts.[^src-ministry p12] ", "")
        assert "T-02" in ids(pathlib.Path(t), thesis=allinterp)


def test_t03_number_not_in_extract():
    with tempfile.TemporaryDirectory() as t:
        assert "T-03" in ids(pathlib.Path(t), thesis=THESIS.replace("numbered 600 men", "numbered 650 men"))
        # a range: each end is checked
        assert "T-03" in ids(pathlib.Path(t), thesis=THESIS.replace("7,000 to 8,000.[^src-court-tj", "7,000 to 9,000.[^src-court-tj"))


def test_t04_invented_quotation():
    with tempfile.TemporaryDirectory() as t:
        assert "T-04" in ids(pathlib.Path(t), thesis=THESIS.replace("“free from any armed attack”", "“free from every armed attack”"))


def test_t05_unverified_or_unfree():
    with tempfile.TemporaryDirectory() as t:
        def unverify(d):
            entry(d, "src-ministry")["access"]["verified_by"] = None
        assert "T-05" in ids(pathlib.Path(t), ledger=mutated(unverify))
        def other_work(d):
            entry(d, "src-ministry")["access"]["verified_title"] = "A Guide to Tulip Growing"
        assert "T-05" in ids(pathlib.Path(t), ledger=mutated(other_work))
        def unfree(d):
            entry(d, "src-ministry")["access"]["free_copy"] = None
            d["gaps"].append({"entry": "src-ministry", "what": "x", "status": "blocked"})
        assert "T-05" in ids(pathlib.Path(t), ledger=mutated(unfree))


def test_t06_register():
    with tempfile.TemporaryDirectory() as t:
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "neither is a wall — ever.{i}"))
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "neither is twenty walls.{i}"))
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "neither is a wall, which is notable.{i}"))
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "neither is a wall to this day.{i}"))
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("neither is a wall.{i}", "many analysts argue neither is a wall.{i}"))
        assert "T-06" in ids(pathlib.Path(t), thesis=THESIS.replace("“free from any armed attack”", '"free from any armed attack"'))


def test_t07_positions():
    with tempfile.TemporaryDirectory() as t:
        assert "T-07" in ids(pathlib.Path(t), thesis=THESIS.replace("::: position critical\n", ""))
        def no_holder(d):
            entry(d, "src-scholar-3")["position"] = None
            entry(d, "src-partisan")["position"] = None
        assert "T-07" in ids(pathlib.Path(t), ledger=mutated(no_holder))
        def bloated(d):
            d["positions"][0]["claim"] = " ".join(["word"] * 80)
        assert "T-07" in ids(pathlib.Path(t), ledger=mutated(bloated))
        def one_region(d):
            for e in d["entries"]:
                e["region_of_authorship"] = "europe"
        assert "T-07" in ids(pathlib.Path(t), ledger=mutated(one_region))
        def one_language(d):
            for e in d["entries"]:
                e["language"] = "en"
        assert "T-07" in ids(pathlib.Path(t), ledger=mutated(one_language))


def test_t08_contested():
    with tempfile.TemporaryDirectory() as t:
        def one_row(d):
            d["contested"][0]["rows"] = d["contested"][0]["rows"][:1]
        assert "T-08" in ids(pathlib.Path(t), ledger=mutated(one_row))
        def shared(d):
            d["contested"][0]["rows"][1]["source"] = "src-court-tj"
            d["contested"][0]["rows"][1]["locator"] = "para84"
        assert "T-08" in ids(pathlib.Path(t), ledger=mutated(shared))
        # a contested figure stated alone in the body
        assert "T-08" in ids(pathlib.Path(t), thesis=THESIS.replace("put the dead at 7,000 to 8,000.", "put the dead at 8,000."))


def test_t09_exhibits():
    with tempfile.TemporaryDirectory() as t:
        def no_creator(d):
            d["exhibits"][0]["creator"] = None
        assert "T-09" in ids(pathlib.Path(t), ledger=mutated(no_creator))
        def stock(d):
            d["exhibits"][0]["url"] = "https://images.unsplash.com/photo-1"
        assert "T-09" in ids(pathlib.Path(t), ledger=mutated(stock))
        assert "T-09" in ids(pathlib.Path(t), thesis=THESIS.replace("::: exhibit src-council-res op1", "::: exhibit src-council-res op9"))


def test_t10_episode():
    with tempfile.TemporaryDirectory() as t:
        assert "T-10" in ids(pathlib.Path(t), thesis=THESIS.replace("chapter=0", "chapter=7"))
        assert "T-10" in ids(pathlib.Path(t), thesis=THESIS.replace("chapter=0", "chapter=0 lines=1-9"))
        only = THESIS.replace("### 2. The count\n", "### 2. The count\n\n::: episode chapter=1\n\n### 3. More\n")
        assert "T-10" in ids(pathlib.Path(t), thesis=only)
        # the manifest disagrees with the script about a chapter's title
        th, led = build(pathlib.Path(t))
        bad = copy.deepcopy(EPISODE)
        bad["chapters"][0]["title"] = "Something else"
        bad_script = copy.deepcopy(SCRIPT)
        bad_script["segments"][0]["title"] = "Opening"
        found = {f.id for f in validate_thesis(th, led, EVENT, bad_script, bad)}
        assert "T-10" in found, found


def test_t11_omits():
    with tempfile.TemporaryDirectory() as t:
        assert "T-11" in ids(pathlib.Path(t), thesis=THESIS.replace("by a member of the battalion.", "by The Ministry."))
        assert "T-11" in ids(pathlib.Path(t), thesis=THESIS.replace(" {against=institutional}", ""))


def test_t12_excluded_and_wrong_tier():
    with tempfile.TemporaryDirectory() as t:
        def wiki(d):
            entry(d, "src-ministry")["identifiers"]["url"] = "https://en.wikipedia.org/wiki/Harbour"
        assert "T-12" in ids(pathlib.Path(t), ledger=mutated(wiki))
        assert "T-12" in ids(pathlib.Path(t), thesis=THESIS.replace("[^src-ministry p12]", "[^src-partisan]") .replace("numbered 600 men at 3 observation posts", "numbered 600 men"))


def test_t13_bar():
    with tempfile.TemporaryDirectory() as t:
        def thin(d):
            d["entries"] = [e for e in d["entries"] if e["id"] != "src-witness"]
        assert "T-13" in ids(pathlib.Path(t), ledger=mutated(thin))
        assert "T-13" in ids(pathlib.Path(t), thesis=THESIS.replace("::: analysis an-crowd\n", ""))
        assert "T-13" in ids(pathlib.Path(t), thesis=THESIS.replace("audited_by: historiographic-auditor\n", ""))
        # a draft below the bar is allowed to exist
        found = ids(pathlib.Path(t), ledger=mutated(thin), thesis=THESIS.replace("status: published", "status: draft"))
        assert "T-13" not in found, found


def test_t15_adjudication():
    with tempfile.TemporaryDirectory() as t:
        def none(d):
            d["positions"][1]["adjudications"] = []
        assert "T-15" in ids(pathlib.Path(t), ledger=mutated(none))
        def tier_b_only(d):
            d["positions"][1]["adjudications"][0]["rests_on"] = ["src-scholar-1.p10"]
        assert "T-15" in ids(pathlib.Path(t), ledger=mutated(tier_b_only))


def test_t16_analysis():
    with tempfile.TemporaryDirectory() as t:
        def wrong_result(d):
            d["analyses"][0]["result"] = [17500, 26000]
        assert "L-11" in ids(pathlib.Path(t), ledger=mutated(wrong_result))
        def dangling(d):
            d["analyses"][0]["derivation"]["rows"][0]["extract"] = "src-court-tj.para1"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(dangling))
        def no_method(d):
            d["analyses"][0]["method"] = None
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(no_method))
        def unentailed_without_against(d):
            d["analyses"][0]["confidence"] = "likely"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(unentailed_without_against))
        assert "T-16" in ids(pathlib.Path(t), thesis=THESIS.replace("::: analysis an-crowd", "::: analysis an-nothing"))


def test_t17_rule_a_one_sided_verdict():
    with tempfile.TemporaryDirectory() as t:
        def one_side(d):
            d["positions"][2]["adjudications"][0]["rests_on"] = ["src-court-tj.para84", "src-court-aj.para37"]
        assert "L-13" in ids(pathlib.Path(t), ledger=mutated(one_side))
        # "capped at qualified" means supported is out of reach on one side's record too
        def one_side_supported(d):
            d["positions"][0]["adjudications"][0]["rests_on"] = ["src-court-tj.para84", "src-court-aj.para37"]
        assert "L-13" in ids(pathlib.Path(t), ledger=mutated(one_side_supported))
        def no_producer(d):
            for e in d["entries"]:
                if e["id"] in ("src-court-tj", "src-sg-report"):
                    e["producer"] = None
        found = ids(pathlib.Path(t), ledger=mutated(no_producer))
        assert "L-01" in found and "L-13" in found, found


def test_t18_rule_b_absence_and_gaps():
    with tempfile.TemporaryDirectory() as t:
        def absence(d):
            d["positions"][2]["adjudications"][0]["basis"] = "absence"
        assert "L-12" in ids(pathlib.Path(t), ledger=mutated(absence))
        def unsaid_gap(d):
            d["gaps"] = d["gaps"][1:]
        assert "L-14" in ids(pathlib.Path(t), ledger=mutated(unsaid_gap))


def test_t19_rendering_parity():
    with tempfile.TemporaryDirectory() as t:
        r = {"src-scholar-2.p20.en.txt": RENDERINGS["src-scholar-2.p20.en.txt"].replace("600", "60")}
        assert "L-15" in ids(pathlib.Path(t), renderings=r)
        r = {"src-scholar-2.p20.en.txt": RENDERINGS["src-scholar-2.p20.en.txt"].replace("names: Potočari=Potočari", "names: Potočari=Potocari")}
        assert "L-15" in ids(pathlib.Path(t), renderings=r)


def test_t20_void_translation_is_not_a_quotation():
    with tempfile.TemporaryDirectory() as t:
        assert "T-20" in ids(pathlib.Path(t), thesis=THESIS.replace("The Dutch study counted the same battalion.[^src-scholar-2 p20]",
                                                                    "The Dutch study “counted 600 soldiers in Potočari”.[^src-scholar-2 p20]"))


def test_real_theses():
    """Every committed thesis passes every check, draft or not: a draft that
    fails is still a draft with a known defect, and it is fixed before it is
    audited, not after."""
    from pipeline.history.export_thesis import load_inputs
    theses = sorted((ROOT / "data/history/theses").glob("*.md"))
    for path in theses:
        event, ledger, thesis, script, episode = load_inputs(path.stem)
        fails = [f for f in validate_thesis(thesis, ledger, event, script, episode) if f.level == "fail"]
        assert not fails, f"{path.stem}: " + "; ".join(f"{f.id} {f.where}: {f.detail}" for f in fails[:12])


def test_t14_served_json_matches_the_thesis():
    """A port of tests/test_history_export_parity.py: the committed export is
    what a fresh export writes, and it carries nothing that is not published."""
    committed = ROOT / "frontend/build-data/history-theses"
    committed_index = ROOT / "frontend/public/data/history-theses.json"
    with tempfile.TemporaryDirectory() as t:
        env = dict(os.environ)
        env["VOID_EXPORT_BUILD_DIR"] = t
        env["VOID_EXPORT_PUBLIC_DIR"] = str(pathlib.Path(t) / "public")
        run = subprocess.run([sys.executable, "-m", "pipeline.history.export_thesis"],
                             cwd=ROOT, env=env, capture_output=True, text=True)
        assert run.returncode == 0, run.stdout[-1500:] + run.stderr[-800:]
        fresh = {p.name: json.loads(p.read_text(encoding="utf-8"))
                 for p in (pathlib.Path(t) / "history-theses").glob("*.json")} \
            if (pathlib.Path(t) / "history-theses").exists() else {}
        fresh_index = json.loads((pathlib.Path(t) / "public" / "history-theses.json").read_text(encoding="utf-8"))
    # The served index (which events are theses, with the counts TH-02 checks
    # against) is committed too, and must be the fresh one.
    assert committed_index.exists(), "frontend/public/data/history-theses.json is not committed; run python3 -m pipeline.history.export_thesis"
    have_index = json.loads(committed_index.read_text(encoding="utf-8"))
    assert json.dumps(have_index, sort_keys=True) == json.dumps(fresh_index, sort_keys=True), \
        "public/data/history-theses.json has drifted; run python3 -m pipeline.history.export_thesis"
    have = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in committed.glob("*.json")} \
        if committed.exists() else {}
    for name, blob in have.items():
        assert blob.get("status") == "published", f"{name} is committed with status {blob.get('status')}"
    canon = lambda o: json.dumps(o, sort_keys=True, ensure_ascii=False)  # noqa: E731
    assert set(fresh) == set(have), f"fresh {sorted(fresh)} vs committed {sorted(have)}; run python3 -m pipeline.history.export_thesis"
    for name in fresh:
        assert canon(fresh[name]) == canon(have[name]), f"{name} has drifted; run python3 -m pipeline.history.export_thesis"


TESTS = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]

if __name__ == "__main__":
    failures = []
    for fn in TESTS:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as exc:
            failures.append(fn.__name__)
            print(f"FAIL  {fn.__name__}: {exc}")
        except Exception as exc:  # noqa: BLE001
            failures.append(fn.__name__)
            print(f"FAIL  {fn.__name__}: {type(exc).__name__}: {exc}")
    if failures:
        print(f"\nFAIL  {len(failures)} of {len(TESTS)} thesis gate test(s)")
        sys.exit(1)
    print(f"\nPASS  {len(TESTS)} thesis gate tests: every T-check fires on its planted defect and every committed thesis is clean")
