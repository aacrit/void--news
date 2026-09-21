#!/usr/bin/env python3
"""The evidence a card was written from must survive the run that wrote it.

E-13 and E-14 read a card against its sources. Neither could run after the fact
until now: `articles.full_text` lives in the gitignored state database, and
`deepdive/<id>.json` keeps only an RSS snippet. The 2026-09-20 feed audit left
two findings unresolved for exactly this reason.

The cap is the part worth testing. A silently truncated record would make an
auditor read a number's absence as fabrication, which is the same defect the
Weekly shipped by publishing `.limit(500)` as an exact count.
"""
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from pipeline.editorial import grounding  # noqa: E402
from pipeline.editorial.standard import validate_candidate  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


ARTICLES = [
    {"id": "a1", "url": "https://example.test/1",
     "title": "Sixteen killed in mosque attack",
     "summary": "At least 16 died.",
     "full_text": 'Rescue workers recovered 16 bodies. "We heard a loud bang and '
                  'then the roof came down on us," said Imran Shah.'},
    {"id": "a2", "url": "https://example.test/2",
     "title": "Toll disputed", "summary": "Some outlets put the toll at 21.",
     "full_text": "Officials would not confirm a figure."},
]

rec = grounding.build_record("cluster-1", ARTICLES)
check("a record names its cluster and every article", 
      rec["cluster"] == "cluster-1" and len(rec["articles"]) == 2)
check("nothing short is marked truncated", rec["truncated"] is False)

with tempfile.TemporaryDirectory() as tmp:
    build = pathlib.Path(tmp)
    grounding.write_record(build, rec)
    blob, cut = grounding.load_source_text(build, "cluster-1")

    check("the round trip keeps the full text",
          "roof came down on us" in blob and "16 bodies" in blob)
    check("a whole record reports nothing cut", cut is False)

    # The point of keeping it: the grounded rules can now run after the run.
    fabricated = {"title": "Attack Kills 31 at Mosque",
                  "summary": ('A survivor said, "The government knew this would '
                              'happen and did nothing." ') + "Filler. " * 40,
                  "source_text": blob}
    ids = [f.id for f in validate_candidate(fabricated)]
    check("E-13 runs against the persisted text", "E-13" in ids, str(ids))
    check("E-14 runs against the persisted text", "E-14" in ids, str(ids))

    grounded = {"title": "Attack Kills 16 at Mosque",
                "summary": ('Imran Shah said, "We heard a loud bang and then the '
                            'roof came down on us." Some outlets put the toll at 21. ')
                           + "Filler. " * 40,
                "source_text": blob}
    ids = [f.id for f in validate_candidate(grounded)]
    check("a sourced card passes both grounded rules",
          "E-13" not in ids and "E-14" not in ids, str(ids))

    # A cut record must say so, or absence reads as fabrication.
    long_article = [dict(ARTICLES[0],
                         full_text="x " * grounding.PER_ARTICLE_CHARS)]
    cut_rec = grounding.build_record("cluster-2", long_article)
    check("an over-long article is marked truncated", cut_rec["truncated"] is True)
    check("the cap is actually applied",
          len(cut_rec["articles"][0]["text"]) == grounding.PER_ARTICLE_CHARS)
    check("the original length is recorded anyway",
          cut_rec["articles"][0]["chars"] > grounding.PER_ARTICLE_CHARS)

    grounding.write_record(build, cut_rec)
    _, cut2 = grounding.load_source_text(build, "cluster-2")
    check("the truncation flag survives the round trip", cut2 is True)

    # No record at all: skip, never accuse.
    blob3, cut3 = grounding.load_source_text(build, "no-such-cluster")
    check("a missing record returns empty rather than raising",
          blob3 == "" and cut3 is False)

if failures:
    print(f"\nFAIL  {len(failures)} grounding check(s)")
    sys.exit(1)
print("\nPASS  grounding survives the run that wrote it")
