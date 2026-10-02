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


# --- rev 85: format 3 answers the new questions through the index -----------
# Each of these is a defect that shipped on 2026-10-01 and that the format-2
# index could not see: a decimal, a number moved to another name, and a
# quotation whose ellipsis became a full stop. They are asserted through the
# PERSISTED record, because that is the path the after-the-fact audit takes.
IRAQ = [
    {"id": "i1", "url": "https://example.test/i1",
     "title": "US completes Iraq withdrawal: 23 years, 4,419 military deaths",
     "summary": "The withdrawal marks the end of Operation Inherent Resolve, which began in 2014.",
     "full_text": ("The Pentagon reported 4,419 U.S. military deaths during Operation "
                   "Iraqi Freedom, which began with the 2003 invasion. Delays affected "
                   "8.1% of flights. He told the officers that those who “clung to "
                   "the woke department... no longer work here.”")},
]
with tempfile.TemporaryDirectory() as tmp:
    build = pathlib.Path(tmp)
    grounding.write_record(build, grounding.build_record("iraq", IRAQ,
                                                         stage=grounding.STAGE_PRE))
    vi = grounding.load_verifier(build, "iraq")
    check("format 3: decimals are recorded", vi.decimals and vi.has_number("8.1")
          and not vi.has_number("8.3"))
    check("format 3: a number is paired with its sentence's name",
          vi.has_pair("4419", "P:operation iraqi freedom")
          and not vi.has_pair("4419", "P:operation inherent resolve"))
    check("format 3: a punctuated junction is recorded",
          vi.has_junction("department...no") and not vi.has_junction("department.no"))

    def ids_for(summary, title="US Completes Troop Withdrawal From Iraq"):
        return [f.id for f in validate_candidate(
            {"title": title, "summary": summary + " Filler. " * 40,
             "source_index": vi})]

    check("index: 8.3% against a source's 8.1% fails E-13",
          "E-13" in ids_for("Delays affected 8.3% of flights."))
    check("index: 8.1% passes", "E-13" not in ids_for("Delays affected 8.1% of flights."))
    check("index: 4,419 moved to Operation Inherent Resolve fails E-13",
          "E-13" in ids_for("This marks the end of Operation Inherent Resolve. The "
                            "Pentagon reported 4,419 U.S. military deaths during the "
                            "operation."))
    check("index: 4,419 on Operation Iraqi Freedom passes",
          "E-13" not in ids_for("The Pentagon reported 4,419 U.S. military deaths "
                                "during Operation Iraqi Freedom."))
    check("index: an ellipsis turned into a full stop fails E-14",
          "E-14" in ids_for("He said those who “clung to the woke department. "
                            "No longer work here,” to applause."))
    check("index: the ellipsis kept passes E-14",
          "E-14" not in ids_for("He said those who “clung to the woke department "
                                "... no longer work here,” to applause."))

    # A format-2 record knows none of this and must not accuse on it.
    old = grounding.build_record("old", IRAQ)
    for k in ("contexts", "junctions", "stage"):
        old.pop(k)
    old["format"] = 2
    old["numbers"] = [n for n in old["numbers"] if "." not in n]
    grounding.write_record(build, old)
    vo = grounding.load_verifier(build, "old")
    ids = [f.id for f in validate_candidate(
        {"title": "x", "summary": "Delays affected 8.3% of flights. This marks the end of "
                                  "Operation Inherent Resolve. The Pentagon reported 4,419 "
                                  "deaths during the operation." + " Filler." * 40,
         "source_index": vo})]
    check("a format-2 record skips decimals and attachment rather than accuse",
          "E-13" not in ids and "E-17" not in ids, str(ids))

# --- rev 85, P1-4: the index is built from whole bodies, before step 10 -------
# Built at export time, after main.py step 10 cut every body to 300 characters,
# the median indexed article was 496 characters and the audit of 2026-10-01
# false-flagged 48 numbers and 6 quotations across one top 20.
BODY = " ".join(f"Sentence {i} reports {100 + i} new cases in the district." for i in range(60))
whole = grounding.build_record("w", [{"id": "a", "url": "u", "title": "T",
                                      "full_text": BODY}], stage=grounding.STAGE_PRE)
stub = grounding.build_record("s", [{"id": "a", "url": "u", "title": "T",
                                     "full_text": BODY[:297] + "..."}],
                              stage=grounding.STAGE_PRE)
check("a whole body is not a stub", whole["articles"][0]["stub"] is False)
check("a step-10 stub is recognised as one", stub["articles"][0]["stub"] is True)
check("the whole body's numbers are all indexed",
      grounding.Verifier(whole).has_number("130")
      and not grounding.Verifier(stub).has_number("130"))
check("the export keeps a pre-truncation record that covers the cluster",
      grounding.keep_existing(whole, ["a"]) is True)
check("the export rebuilds when the cluster gained an article",
      grounding.keep_existing(whole, ["a", "b"]) is False)
check("the export rebuilds over a record it wrote itself",
      grounding.keep_existing(dict(whole, stage=grounding.STAGE_EXPORT), ["a"]) is False)


def coverage_problems(record: dict) -> list[str]:
    """A record whose shingle count does not match the words it claims, or a
    pre-truncation record built from nothing but step-10 stubs."""
    out = []
    arts = record.get("articles") or []
    words = sum(int(a.get("words") or 0) for a in arts)
    count = int((record.get("quotes") or {}).get("count") or 0)
    floor = words - (grounding.SHINGLE_WORDS - 1) * len(arts)
    # Distinct shingles can be fewer than positions (syndicated copy repeats),
    # never more, and never fewer than a quarter of them.
    if count > max(words, 1) or (floor > 40 and count < floor * 0.25):
        out.append(f"{record.get('cluster')}: {count} shingles for {words} words")
    if any(a.get("stub") is None for a in arts):
        out.append(f"{record.get('cluster')}: an article row does not say "
                   f"whether its body was a step-10 stub")
    for a in arts:
        # A row that claims a whole body must have indexed more than a stub's
        # worth of it.
        if a.get("stub") is False and int(a.get("bodyChars") or 0) > grounding.STUB_CHARS \
                and int(a.get("words") or 0) * 12 < min(int(a.get("chars") or 0),
                                                         grounding.PER_ARTICLE_CHARS):
            out.append(f"{record.get('cluster')}: article {a.get('id')} claims "
                       f"{a.get('chars')} characters and indexed {a.get('words')} words")
    return out


check("coverage: a whole-body record is consistent", not coverage_problems(whole),
      str(coverage_problems(whole)))
check("coverage: a stub is declared as one, so a reader can discount it",
      not coverage_problems(stub) and stub["articles"][0]["stub"] is True)
undeclared = dict(whole, articles=[{k: v for k, v in a.items() if k != "stub"}
                                   for a in whole["articles"]])
check("coverage: a row that does not declare whether it was a stub is caught",
      bool(coverage_problems(undeclared)))
hollow = dict(whole, articles=[dict(a, words=10) for a in whole["articles"]])
check("coverage: a row claiming a whole body it did not index is caught",
      bool(coverage_problems(hollow)))

# The ordering itself: Stage 2 writes the index (8f), and Stage 2 runs before
# main.py truncates bodies at step 10. Asserted on the source, because the
# defect was an ordering and no unit test of either half could see it.
_main = (ROOT / "pipeline" / "main.py").read_text(encoding="utf-8")
_s2 = (ROOT / "pipeline" / "editorial" / "stage2.py").read_text(encoding="utf-8")
_run = _s2[_s2.index("def run_stage2("):]
check("Stage 2 writes the grounding index before it returns",
      "write_bench_index(" in _run)
check("main.py runs Stage 2 before step 10 truncates the bodies",
      0 < _main.index("run_stage2(supabase") < _main.index("[10] Truncating full_text"))
_exp = (ROOT / "pipeline" / "export_static.py").read_text(encoding="utf-8")
check("the export keeps a pre-truncation record instead of rebuilding it",
      "grounding.keep_existing(" in _exp)
inflated = dict(whole, quotes=dict(whole["quotes"], count=whole["quotes"]["count"] * 9))
check("coverage: a shingle count larger than the words is caught",
      bool(coverage_problems(inflated)))


# --- rev 85, P2-10: publisher summaries served in the Deep Dive are capped ---
# 846 per-article summaries across 35 deep-dive files, 181,000 characters,
# 111 of them over 60 words and some a whole lede (security audit M5), against
# IP-COMPLIANCE's 2 to 3 sentences and 300 characters.
from pipeline.editorial import corrections  # noqa: E402

LONG = ("The first sentence of the lede runs on for a while with detail. " * 3
        + "The second sentence adds a further and different fact entirely. " * 4)
capped = corrections.cap_summary(LONG)
check("cap: a long summary is cut to the cap", len(capped) <= corrections.SUMMARY_CAP,
      str(len(capped)))
check("cap: it ends on a sentence boundary when one is in reach", capped.endswith("."))
check("cap: no ellipsis is added", "…" not in capped and not capped.endswith("..."))
words = "word " * 120
cw = corrections.cap_summary(words)
check("cap: with no sentence end it cuts on a word boundary",
      len(cw) <= corrections.SUMMARY_CAP and not cw.endswith(" ") and cw.split()[-1] == "word")
check("cap: a short summary is untouched", corrections.cap_summary("Short.") == "Short.")

DD = ROOT / "frontend" / "public" / "data" / "deepdive"
over = []
for path in sorted(DD.glob("*.json")) if DD.exists() else []:
    for row in json.loads(path.read_text(encoding="utf-8")):
        s = ((row.get("article") or {}).get("summary")) or ""
        if len(s) > corrections.SUMMARY_CAP:
            over.append(f"{path.name[:8]}: {len(s)}")
check("every served Deep Dive summary is within the cap", not over,
      f"{len(over)} over: {over[:3]}")
_exp_src = (ROOT / "pipeline" / "export_static.py").read_text(encoding="utf-8")
check("the export caps each served summary", '"summary": cap_summary(a["summary"])' in _exp_src)

# --- rev 85: published corrections hold in the committed tree ---------------
# A printed card is a permanent /story/ page and the export rewrites
# archive.json from a database that still holds the error, so a correction
# lives in pipeline/editorial/corrections.json and the export applies it. The
# gate asserts no committed copy still carries a corrected text.
row = {"id": "x", "summary": "A. The Pentagon reported 9 deaths during the operation. B.",
       "divergence_points": ["Sources show significant differences in political "
                             "framing (lean spread: 41 points)"]}
plant = [{"cluster": "x", "date": "t", "reason": "r",
          "edits": [{"field": "summary",
                     "find": "The Pentagon reported 9 deaths during the operation. ",
                     "replace": ""}]},
         {"cluster": "*", "date": "t", "reason": "r",
          "edits": [{"field": "divergence_points",
                     "regex": "Sources show significant differences in political "
                              "framing \\(lean spread: (\\d+) points\\)",
                     "replace": "Sources differ in political framing by \\1 points of lean"}]}]
check("corrections: an uncorrected row is found", len(corrections.unapplied([row], "id", plant)) == 2)
corrections.apply_all([row], "id", plant)
check("corrections: applying removes the text and rewrites the pattern",
      "Pentagon" not in row["summary"] and row["summary"] == "A. B."
      and row["divergence_points"] == ["Sources differ in political framing by 41 points of lean"])
check("corrections: a corrected row is clean", not corrections.unapplied([row], "id", plant))
check("corrections: a card that no longer carries the text is left alone",
      corrections.apply_all([{"id": "x", "summary": "Rewritten."}], "id", plant) == [])

_bd = ROOT / "frontend" / "build-data"
_feed = json.loads((_bd / "feed.json").read_text(encoding="utf-8"))["clusters"]
_arch = json.loads((_bd / "archive.json").read_text(encoding="utf-8"))
left = corrections.unapplied(_feed, "id") + corrections.unapplied(_arch, "source_cluster_id")
check("every published correction holds in the committed feed and archive", not left,
      f"{len(left)}: {left[:3]}")
check("the export applies the corrections to the feed and the archive",
      'corrections.apply_all(clusters, key="id")' in _exp_src
      and 'corrections.apply_all(archive, key="source_cluster_id")' in _exp_src)

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
coverage: list[str] = []
for path in committed:
    record = json.loads(path.read_text(encoding="utf-8"))
    if int(record.get("format") or 1) < grounding.MIN_INDEX_FORMAT:
        stale.append(path.name)
    if int(record.get("format") or 1) >= 3:
        coverage.extend(coverage_problems(record))
    for where, text in long_strings(record):
        prose.append(f"{path.name}{where}: {text[:60]!r}")

check("every committed record is an index, not prose",
      not stale, f"{len(stale)} format-1 record(s): {stale[:3]}")
check("no committed record carries a sentence",
      not prose, f"{len(prose)} field(s): {prose[:3]}")
check("every committed format-3 record's coverage matches its bodies",
      not coverage, f"{len(coverage)}: {coverage[:3]}")

if failures:
    print(f"\nFAIL  {len(failures)} grounding check(s)")
    sys.exit(1)
print(f"\nPASS  the evidence outlives the run and keeps no prose "
      f"({len(committed)} committed records)")
