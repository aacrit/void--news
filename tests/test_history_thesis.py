#!/usr/bin/env python3
"""The History thesis gates, T-01..T-21, each against a planted defect.

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
             "described_by": ["src-scholar-3.p30"],
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
            {"id": "an-crowd", "title": "Two counts of one crowd",
             "method": "Every figure the record gives for the crowd, by document and date.",
             "finding": "The counts run from 17,500 to 25,000.",
             "confidence": "high: both figures are in one court extract",
             "against": "none found in the six primary documents held", "result": [17500, 25000],
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


# ------------------------------------------------ the holistic fixture (§15, T-21)
#
# The same event argued whole: a `## The event` narrative in five numbered
# sections before the record, the argument titled "The contested questions",
# and a coverage map that says which sections carry which strand and which
# perspective. It is clean; each T-21 test below breaks one thing.

EVENT_H = {**EVENT, "perspectives": [{"viewpoint": "The Court"}, {"viewpoint": "The Institutions"},
                                     {"viewpoint": "The Critics"}]}

COVERAGE_H = """scope: holistic
coverage:
  causes: {sections: [event-1, event-2]}
  course: {sections: [event-2, event-3]}
  actors: {sections: [event-1, event-3, event-4], terms: [council, secretariat, court]}
  regions: {sections: [event-1, event-3], terms: [harbour, posts, attack]}
  consequences: {sections: [event-4, event-5]}
  legacy: {sections: [event-4, event-5]}
  perspectives:
    the-court: {position: court-record, sections: [event-4]}
    the-institutions: {position: institutional, sections: [event-1, event-5]}
    the-critics: {position: critical, sections: [event-5]}
"""

EVENT_SECTIONS_H = """## The event

### 1. The council

The council declared the harbour a safe area.[^src-council-res op1] It demanded that all parties treat the area as free from attack.[^src-council-res op1] The secretariat later reported on the fall of the harbour.[^src-sg-report para503]

### 2. The battalion

The ministry reported on the battalion it sent.[^src-ministry p12] The battalion held observation posts.[^src-ministry p12] A Dutch study counted the same battalion.[^src-scholar-2 p20]

### 3. The fall

The posts fell.[^src-scholar-4 p40] The court found that men were executed after the fall.[^src-court-tj para84] A witness testified before the court.[^src-witness p9]

### 4. The judgments

The trial chamber gave judgment.[^src-court-tj para84] The appeals chamber named the crime.[^src-court-aj para37] A scholar wrote that the judgment settled the count.[^src-scholar-1 p10]

### 5. What followed

The critical school holds the count inflated.[^src-scholar-3 p30] Its account is set out in a study of the school.[^src-scholar-3 p30] The secretariat wrote that it had failed to do its part.[^src-sg-report para503]

"""

THESIS_H = (THESIS
            .replace("episode_marks: []\n", "episode_marks: []\n" + COVERAGE_H)
            .replace("## The record\n", EVENT_SECTIONS_H + "## The record\n")
            .replace("## The argument\n", "## The contested questions\n")
            .replace("## The historiography\n", "### 3. The posts\n\nThe battalion's posts fell.[^src-scholar-4 p40]\n\n## The historiography\n"))


def ids_h(tmp, thesis: str | None = None, event: dict | None = None, **kw) -> list[str]:
    th, led = build(tmp, thesis=thesis or THESIS_H, **kw)
    return sorted({f.id for f in validate_thesis(th, led, event or EVENT_H, SCRIPT, EPISODE) if f.level == "fail"})


def details_h(tmp, thesis: str) -> list[str]:
    th, led = build(tmp, thesis=thesis)
    return [f"{f.where}: {f.detail}" for f in validate_thesis(th, led, EVENT_H, SCRIPT, EPISODE) if f.id == "T-21"]


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
        # ... but a position speaking in its own words in the historiography is what Tier D is for
        spoken = THESIS.replace("::: position critical\n", "::: position critical\n\nThe critical account holds that the count is “inflated”.[^src-partisan p5]\n")
        found = ids(pathlib.Path(t), thesis=spoken, extracts={**EXTRACTS, "src-partisan.p5.txt": ("src-partisan", "p5", "https://example.org/partisan.pdf", "The count is inflated, the critics hold.")})
        assert "T-12" not in found, found


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
        def no_against(d):
            d["analyses"][0]["against"] = None
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(no_against))
        def entailed_is_no_waiver(d):
            d["analyses"][0]["against"] = None
            d["analyses"][0]["confidence"] = "entailed"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(entailed_is_no_waiver))
        def none_found_nowhere(d):
            d["analyses"][0]["against"] = "none found"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(none_found_nowhere))
        def bare_confidence(d):
            d["analyses"][0]["confidence"] = "high"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(bare_confidence))
        def off_scale(d):
            d["analyses"][0]["confidence"] = "likely, because the rows agree"
        assert "L-10" in ids(pathlib.Path(t), ledger=mutated(off_scale))
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


def test_l16_tier_d_position_described_by_a_or_b():
    """§4a: a Tier D position enters only when a Tier A or B source is cited
    for what the position is."""
    with tempfile.TemporaryDirectory() as t:
        def undescribed(d):
            d["positions"][2].pop("described_by")
        assert "L-16" in ids(pathlib.Path(t), ledger=mutated(undescribed))
        def described_by_itself(d):
            d["positions"][2]["described_by"] = ["src-partisan.p1"]
        assert "L-16" in ids(pathlib.Path(t), ledger=mutated(described_by_itself))
        def dangling(d):
            d["positions"][2]["described_by"] = ["src-scholar-3.p99"]
        assert "L-16" in ids(pathlib.Path(t), ledger=mutated(dangling))
        # a position with no Tier D source needs no description
        def no_d(d):
            d["positions"][0].pop("described_by", None)
        assert "L-16" not in ids(pathlib.Path(t), ledger=mutated(no_d))


def test_l17_analysis_counts_its_own_rows():
    with tempfile.TemporaryDirectory() as t:
        def six(d):
            d["analyses"][0]["title"] = "One crowd, six counts"
        assert "L-17" in ids(pathlib.Path(t), ledger=mutated(six))
        def nine(d):
            d["analyses"][0]["confidence"] = "high: the extreme of nine figures held"
        assert "L-17" in ids(pathlib.Path(t), ledger=mutated(nine))
        def right(d):
            d["analyses"][0]["title"] = "One crowd, two counts"
        assert "L-17" not in ids(pathlib.Path(t), ledger=mutated(right))


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


def test_holistic_fixture_is_clean():
    with tempfile.TemporaryDirectory() as t:
        th, _ = build(pathlib.Path(t), thesis=THESIS_H)
        assert th.scope == "holistic" and [s.id for s in th.event_sections()] == [f"event-{n}" for n in range(1, 6)]
        assert th.section("argument").title == "The contested questions"
        found = ids_h(pathlib.Path(t))
        assert found == [], (found, details_h(pathlib.Path(t), THESIS_H))


def test_t21_coverage():
    with tempfile.TemporaryDirectory() as t:
        tp = pathlib.Path(t)
        # a required strand dropped from the map
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("  legacy: {sections: [event-4, event-5]}\n", ""))
        # a strand naming a section the thesis does not have
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("causes: {sections: [event-1, event-2]}", "causes: {sections: [event-1, event-9]}"))
        # a strand argued only in the questions, never narrated
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("legacy: {sections: [event-4, event-5]}", "legacy: {sections: [argument-1, argument-2]}"))
        # a strand below the floor of sourced sentences
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("legacy: {sections: [event-4, event-5]}", "legacy: {sections: [event-5]}"))
        # ... and a floor may be raised, never lowered
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("legacy: {sections: [event-4, event-5]}", "legacy: {sections: [event-5], min: 3}"))
        # a listed section that says nothing: its sentences are all the historian's own
        padded = THESIS_H.replace("The posts fell.[^src-scholar-4 p40] The court found that men were executed after the fall.[^src-court-tj para84] A witness testified before the court.[^src-witness p9]",
                                  "The posts fell.[^src-scholar-4 p40]")
        assert any("carries no sourced sentence" in d or "floor" in d for d in details_h(tp, padded.replace("The posts fell.[^src-scholar-4 p40]", "Nothing held.{i} The posts fell.[^src-scholar-4 p40]")))
        # an actor the strand names and no sourced sentence carries
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("terms: [council, secretariat, court]", "terms: [council, secretariat, court, admiral]"))
        # actors and regions must name at least three
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("terms: [harbour, posts, attack]", "terms: [harbour]"))
        # a perspective the event record holds and the map does not answer
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("    the-critics: {position: critical, sections: [event-5]}\n", ""))
        # a perspective answered by a position the page does not render
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("::: position critical\n", ""))
        # a perspective whose own sources are heard fewer than twice in its sections
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("the-court: {position: court-record, sections: [event-4]}", "the-court: {position: court-record, sections: [event-1]}"))
        # an event section no strand claims
        orphan = THESIS_H.replace("## The record\n", "### 6. Aftermath\n\nThe trial chamber gave judgment.[^src-court-tj para84]\n\n## The record\n")
        assert any("no strand claims" in d for d in details_h(tp, orphan))
        # too few event sections, and too few contested questions
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("### 5. What followed\n", ""))
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("### 3. The posts\n\nThe battalion's posts fell.[^src-scholar-4 p40]\n\n", ""))
        # holistic with no event narrative at all
        no_event = THESIS_H.replace(EVENT_SECTIONS_H, "")
        assert "T-21" in ids_h(tp, thesis=no_event)
        # a scope the rule does not know
        assert "T-21" in ids_h(tp, thesis=THESIS_H.replace("scope: holistic", "scope: sweeping"))
        # the pilot model is untouched: no scope, no T-21
        assert "T-21" not in ids(tp)


def test_draft_overlay():
    """§15e: a draft thesis reads the ledger plus its draft overlay; the
    published reading of the same ledger never sees the overlay."""
    from pipeline.history.ledger import load_ledger as _load
    with tempfile.TemporaryDirectory() as t:
        tp = pathlib.Path(t)
        build(tp)
        d = tp / SLUG / "draft"
        (d / "extracts").mkdir(parents=True)
        new = _entry("src-new-doc", "A", "report", "The Registry", "Registry Report", 2003,
                     "the-registry", "https://example.org/registry.pdf", rights="public")
        changed = copy.deepcopy(entry(fixture_ledger(), "src-ministry"))
        changed["title"] = "Ministry Report on the Harbour, revised"
        changed["access"]["verified_title"] = changed["title"]
        (d / "ledger.yaml").write_text(yaml.safe_dump({
            "entries": [new, changed],
            "gaps": [{"what": "The registry's annex", "tried": ["https://example.org/annex"], "status": "not found"}],
        }, sort_keys=False), encoding="utf-8")
        (d / "extracts" / "src-new-doc.p1.txt").write_text(
            f"source: src-new-doc\nlocator: p1\nurl: https://example.org/registry.pdf\nread: {TODAY}\n\nThe registry counted 12 files.\n",
            encoding="utf-8")
        base = _load(SLUG, evidence_dir=tp)
        over = _load(SLUG, evidence_dir=tp, draft=True)
        assert "src-new-doc" not in base.entries and base.extract("src-new-doc", "p1") is None
        assert "src-new-doc" in over.entries and over.extract("src-new-doc", "p1") is not None
        assert over.entries["src-ministry"]["title"].endswith("revised")
        assert base.entries["src-ministry"]["title"] == "Ministry Report on the Harbour"
        assert any(g.get("what") == "The registry's annex" for g in over.gaps)
        assert validate_ledger(over) == [], validate_ledger(over)
        # a gap retired by the overlay while the source is still unread is caught (RULE B)
        delta = yaml.safe_load((d / "ledger.yaml").read_text(encoding="utf-8"))
        delta["drop_gaps"] = ["src-scholar-5"]
        (d / "ledger.yaml").write_text(yaml.safe_dump(delta, sort_keys=False), encoding="utf-8")
        dropped = _load(SLUG, evidence_dir=tp, draft=True)
        assert not any(g.get("entry") == "src-scholar-5" for g in dropped.gaps)
        assert "L-14" in {f.id for f in validate_ledger(dropped)}
        # an overlay extract for an entry neither ledger holds is caught
        (d / "extracts" / "src-ghost.p1.txt").write_text(
            f"source: src-ghost\nlocator: p1\nurl: https://example.org/ghost.pdf\nread: {TODAY}\n\nNothing.\n", encoding="utf-8")
        assert "L-03" in {f.id for f in validate_ledger(_load(SLUG, evidence_dir=tp, draft=True))}


def test_draft_overlays_validate():
    """Every committed draft overlay (§15e) passes the ledger's own checks
    merged with its base, whether or not its draft thesis exists yet."""
    from pipeline.history.ledger import EVIDENCE, load_ledger as _load
    for d in sorted(EVIDENCE.glob("*/draft/ledger.yaml")):
        slug = d.parent.parent.name
        fails = [f for f in validate_ledger(_load(slug, draft=True)) if f.level == "fail"]
        assert not fails, f"{slug}/draft: " + "; ".join(f"{f.id} {f.where}: {f.detail}" for f in fails[:12])


def test_drafts_are_drafts():
    """A drafts file is never published from the drafts path: it is promoted by
    moving it over the published file, in the commit that folds its ledger
    overlay into the base. The exporter refuses a --draft run without an
    explicit build directory, so a preview cannot land in the committed tree."""
    drafts = ROOT / "data/history/theses/drafts"
    for path in sorted(drafts.glob("*.md")) if drafts.exists() else []:
        front = parse_thesis(path.read_text(encoding="utf-8"), path.stem).front
        assert str(front.get("status") or "draft") != "published", f"{path.name} is published from the drafts path"
    env = {k: v for k, v in os.environ.items() if k != "VOID_EXPORT_BUILD_DIR"}
    run = subprocess.run([sys.executable, "-m", "pipeline.history.export_thesis", "fixture-event", "--draft"],
                         cwd=ROOT, env=env, capture_output=True, text=True)
    assert run.returncode == 2 and "VOID_EXPORT_BUILD_DIR" in run.stdout, run.stdout + run.stderr


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
    # A draft that will replace a published thesis (§15e) is gated the same
    # way, against the ledger with its draft overlay.
    for path in sorted((ROOT / "data/history/theses/drafts").glob("*.md")):
        event, ledger, thesis, script, episode = load_inputs(path.stem, draft=True)
        fails = [f for f in validate_thesis(thesis, ledger, event, script, episode) if f.level == "fail"]
        assert not fails, f"drafts/{path.stem}: " + "; ".join(f"{f.id} {f.where}: {f.detail}" for f in fails[:12])


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


# ------------------------------------------------ producer labels
# A verdict prints the bodies whose documents it rests on, and an analysis may
# print a producer column. The ledger names a body by an id (`uk-government`),
# and until 2026-09-26 the page printed that id raw wherever a hand-written
# table in Thesis.tsx had no entry for it: 20 verdict lines on the Partition
# draft read "Rests on documents from: boundary-commission-chairman;
# commission-member-congress; ...". The labels are data now
# (data/history/producers.yaml), each taken from the author or publisher of a
# named ledger entry that carries the id.

def _is_id(v: str) -> bool:
    import re as _re
    return bool(_re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", v))


def producer_label_problems(labels: dict, ledgers: list) -> list[str]:
    """`labels` is producers.yaml's `producers` map; `ledgers` the loaded
    ledgers. Returns every way the page could print a raw id, or a label with
    no provenance."""
    probs: list[str] = []
    used: dict[str, str] = {}
    carriers: dict[str, set] = {}
    for name, led in ledgers:
        for e in led.entries.values():
            pid = e.get("producer")
            if pid:
                used.setdefault(str(pid), f"{name} {e['id']}")
                carriers.setdefault(str(e["id"]), set()).add(str(pid))
        entry_ids = {str(e.get("producer")) for e in led.entries.values() if e.get("producer")}
        for aid, a in led.analyses.items():
            for r in (a.get("derivation") or {}).get("rows") or []:
                v = r.get("producer")
                if isinstance(v, str) and (v in entry_ids or _is_id(v)):
                    used.setdefault(v, f"{name} analysis {aid}")
    for pid, where in sorted(used.items()):
        v = labels.get(pid)
        if not isinstance(v, dict) or not str(v.get("label") or "").strip():
            probs.append(f"producer `{pid}` ({where}) has no label in data/history/producers.yaml")
            continue
        lab = str(v["label"])
        if lab == pid or _is_id(lab):
            probs.append(f"producer `{pid}`: the label is the id")
        if "\u2014" in lab or "\u2013" in lab:
            probs.append(f"producer `{pid}`: a dash in the label")
        src = str(v.get("from") or "")
        if pid not in carriers.get(src, set()):
            probs.append(f"producer `{pid}`: `from: {src or '(none)'}` is not a ledger entry carrying that producer")
    for pid in sorted(set(labels) - set(used)):
        probs.append(f"producer `{pid}` is labelled but no ledger uses it")
    return probs


def _all_ledgers() -> list:
    from pipeline.history.ledger import EVIDENCE, has_draft, load_ledger as _load
    out = []
    for d in sorted(EVIDENCE.glob("*/ledger.yaml")):
        slug = d.parent.name
        out.append((slug, _load(slug)))
        if has_draft(slug):
            out.append((f"{slug}/draft", _load(slug, draft=True)))
    return out


def test_producer_labels():
    """Every producer id any committed ledger or draft overlay uses has a
    readable label with provenance, and the export carries it to the page."""
    labels = (yaml.safe_load((ROOT / "data/history/producers.yaml").read_text(encoding="utf-8")) or {})["producers"]
    ledgers = _all_ledgers()
    probs = producer_label_problems(labels, ledgers)
    assert not probs, "; ".join(probs[:12])
    # Planted: an id with no label, a label with no provenance, an orphan.
    missing = {k: v for k, v in labels.items() if k != "uk-government"}
    assert any("`uk-government`" in p and "no label" in p for p in producer_label_problems(missing, ledgers))
    unsourced = dict(labels, **{"uk-government": {"label": "UK government", "from": "src-no-such-entry"}})
    assert any("`uk-government`" in p and "from:" in p for p in producer_label_problems(unsourced, ledgers))
    orphan = dict(labels, **{"no-such-body": {"label": "Nobody", "from": "src-x"}})
    assert any("`no-such-body`" in p and "no ledger" in p for p in producer_label_problems(orphan, ledgers))
    # The committed export names every producer its page prints.
    for path in sorted((ROOT / "frontend/build-data/history-theses").glob("*.json")):
        blob = json.loads(path.read_text(encoding="utf-8"))
        have = blob.get("producerLabels") or {}
        for sec in blob["sections"]:
            for b in sec["blocks"]:
                ids = []
                if b["t"] == "position":
                    ids = [p for a in b["adjudications"] for p in a["producers"]]
                elif b["t"] == "analysis":
                    ids = [str(r["cells"]["producer"]) for r in b["rows"]
                           if isinstance(r["cells"].get("producer"), str) and r["cells"]["producer"] in labels]
                for pid in ids:
                    assert pid in have, f"{path.name}: `{pid}` is printed with no label in producerLabels"


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
