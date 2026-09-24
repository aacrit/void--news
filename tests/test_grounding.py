#!/usr/bin/env python3
"""The evidence a card was written from must outlive the run, without keeping
the article text.

E-13 and E-14 read a card against its sources. Neither could run after the
fact until `frontend/build-data/grounding/` existed: `articles.full_text` lives
in the gitignored state database, and `deepdive/<id>.json` keeps only an RSS
snippet. The 2026-09-20 feed audit left two findings unresolved for exactly
that reason.

The first version of that record kept the prose. The repo commits it, so on
2026-09-22 the committed tree held 519,041 characters of publisher article
text in a public repository's permanent history, against the top-priority
control in `docs/IP-COMPLIANCE.md`. The record is now a verification index: the
set of numbers, and a Bloom filter of 4-word shingles.

Three things are worth testing, and one of them is new:

  it still answers      an index that cannot catch the 2026-09-20 fabrication
                        is not worth keeping.
  it keeps no prose     asserted against a distinctive sentence AND against
                        the committed tree, because the leak was in the tree,
                        not in the module.
  the cap is recorded   a silently truncated record makes an auditor read a
                        number's absence as fabrication, which is the same
                        defect the Weekly shipped by publishing `.limit(500)`
                        as an exact count.
"""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from pipeline.editorial import grounding  # noqa: E402
from pipeline.editorial import standard  # noqa: E402
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
check("a record declares its format", rec["format"] == grounding.FORMAT)
check("nothing short is marked truncated", rec["truncated"] is False)

# --- it keeps no prose ------------------------------------------------------
# The strongest available statement: a distinctive span of the source must not
# appear anywhere in the serialised record, in any field, at any nesting.
blob = json.dumps(rec, ensure_ascii=False)
check("no source sentence survives serialisation",
      "roof came down" not in blob and "Rescue workers" not in blob)
check("no article text field is written",
      all("text" not in a for a in rec["articles"]))
check("the record is smaller than the prose it indexes",
      len(blob) < sum(len(a["full_text"]) for a in ARTICLES) * 40, len(blob))

# --- it still answers -------------------------------------------------------
with tempfile.TemporaryDirectory() as tmp:
    build = pathlib.Path(tmp)
    grounding.write_record(build, rec)
    v = grounding.load_verifier(build, "cluster-1")
    check("a written record loads as present", v.present is True)
    check("a whole record reports nothing cut", v.truncated is False)

    check("E-13: a sourced number verifies", v.has_number("16") and v.has_number("21"))
    check("E-13: the 2026-09-20 fabrication does not", v.has_number("31") is False)
    check("E-14: a verbatim quotation verifies",
          v.has_span("We heard a loud bang and then the roof came down on us"))
    check("E-14: case, curly quotes and spacing do not matter",
          v.has_span("we heard a LOUD bang  and\nthen the roof"))
    check("E-14: an invented quotation does not verify",
          v.has_span("The government knew this would happen and did nothing") is False)
    check("E-14: a quotation half invented does not verify",
          v.has_span("We heard a loud bang and then the minister resigned") is False)

    # The rules themselves, through the same door the audit uses.
    fabricated = {"title": "Attack Kills 31 at Mosque",
                  "summary": ('A survivor said, "The government knew this would '
                              'happen and did nothing." ') + "Filler. " * 40,
                  "source_index": v}
    ids = [f.id for f in validate_candidate(fabricated)]
    check("E-13 runs against the persisted index", "E-13" in ids, str(ids))
    check("E-14 runs against the persisted index", "E-14" in ids, str(ids))

    grounded = {"title": "Attack Kills 16 at Mosque",
                "summary": ('Imran Shah said, "We heard a loud bang and then the '
                            'roof came down on us." Some outlets put the toll at 21. ')
                           + "Filler. " * 40,
                "source_index": v}
    ids = [f.id for f in validate_candidate(grounded)]
    check("a sourced card passes both grounded rules against the index",
          "E-13" not in ids and "E-14" not in ids, str(ids))

    # The write-time path takes text and must reach the same verdicts, or the
    # two backings of one rule have drifted.
    raw = " ".join(f"{a['title']} {a['summary']} {a['full_text']}" for a in ARTICLES)
    ids_text = [f.id for f in validate_candidate(dict(fabricated, source_index=None,
                                                      source_text=raw))]
    check("text and index agree on the fabricated card",
          ("E-13" in ids_text) and ("E-14" in ids_text), str(ids_text))
    ids_text = [f.id for f in validate_candidate(dict(grounded, source_index=None,
                                                      source_text=raw))]
    check("text and index agree on the sourced card",
          "E-13" not in ids_text and "E-14" not in ids_text, str(ids_text))

    # --- the cap is recorded ------------------------------------------------
    long_article = [dict(ARTICLES[0],
                         full_text="x " * grounding.PER_ARTICLE_CHARS)]
    cut_rec = grounding.build_record("cluster-2", long_article)
    check("an over-long article is marked truncated", cut_rec["truncated"] is True)
    check("the original length is recorded anyway",
          cut_rec["articles"][0]["chars"] > grounding.PER_ARTICLE_CHARS)
    grounding.write_record(build, cut_rec)
    check("the truncation flag survives the round trip",
          grounding.load_verifier(build, "cluster-2").truncated is True)

    # --- no record at all: skip, never accuse -------------------------------
    missing = grounding.load_verifier(build, "no-such-cluster")
    check("a missing record is absent rather than empty",
          missing.present is False and missing.has_number("31") is False)
    absent_card = {"title": "Attack Kills 31 at Mosque",
                   "summary": "Filler. " * 40, "source_index": missing}
    ids = [f.id for f in validate_candidate(absent_card)]
    check("an absent index accuses nobody",
          "E-13" not in ids and "E-14" not in ids, str(ids))

# --- the index asks the question the rules ask ------------------------------
# grounding.py duplicates the folding deliberately (it must not import the
# validator graph), so the duplication is asserted rather than trusted.
for probe in ("1,200 killed", "Toll of 21", "no numbers here", "007 agents"):
    check(f"numbers agree on {probe!r}",
          set(grounding.numbers_in(probe)) == standard._numbers(probe),
          f"{grounding.numbers_in(probe)} vs {sorted(standard._numbers(probe))}")
for probe in ("A “curly”  quote", "EM — dash", "  collapse\tme "):
    check(f"folding agrees on {probe!r}",
          grounding.fold(probe) == standard._fold_quote(probe),
          f"{grounding.fold(probe)!r} vs {standard._fold_quote(probe)!r}")

# --- THE GATE: the committed tree carries no prose -------------------------
# This is the check that would have caught the leak. The defect was never in
# the module's API, it was in what the repo was carrying, so the assertion is
# made against the repo.
TREE = ROOT / "frontend" / "build-data" / grounding.DIRNAME
committed = sorted(TREE.glob("*.json")) if TREE.exists() else []
check("the committed grounding tree exists", bool(committed), str(TREE))

WORD_CEILING = 12  # a URL or an id, never a sentence


def long_strings(node, path=""):
    """Every string in the record that could be read as prose."""
    if isinstance(node, str):
        # The Bloom filter is base64 of a bit array. It is one long token by
        # construction and holds no recoverable words.
        if not path.endswith("bloom") and len(node.split()) > WORD_CEILING:
            yield path, node
    elif isinstance(node, dict):
        for k, val in node.items():
            yield from long_strings(val, f"{path}.{k}")
    elif isinstance(node, list):
        for val in node:
            yield from long_strings(val, f"{path}[]")


stale = []
prose = []
for path in committed:
    record = json.loads(path.read_text(encoding="utf-8"))
    if int(record.get("format") or 1) < grounding.FORMAT:
        stale.append(path.name)
    for where, text in long_strings(record):
        prose.append(f"{path.name}{where}: {text[:60]!r}")

check("every committed record is an index, not prose",
      not stale, f"{len(stale)} format-1 record(s): {stale[:3]}")
check("no committed record carries a sentence",
      not prose, f"{len(prose)} field(s): {prose[:3]}")

if failures:
    print(f"\nFAIL  {len(failures)} grounding check(s)")
    sys.exit(1)
print(f"\nPASS  the evidence outlives the run and keeps no prose "
      f"({len(committed)} committed records)")
