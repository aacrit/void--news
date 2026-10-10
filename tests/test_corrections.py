#!/usr/bin/env python3
"""Every published correction holds in what is served, and every class of
error that has reached production has a check that catches it.

    python tests/test_corrections.py

Rule 1 (CLAUDE.md): "When a factual error reaches production, the fix is not
complete until a check exists that would have caught it." Until rev 86 that
was a sentence. `corrections.json` recorded what was wrong and nothing tied an
entry to the rule that now stops it, the corrections file could correct a card
and nothing else (the 2026-10-01 TL;DR, Opinion and On Air errors stayed
served), and 146 archived cards still opened a sentence with "Separately,".

Four things are asserted here, against the committed tree:

  THE CORPUS     tests/fixtures/rigor_regressions/ holds one fixture per past
                 error class, from BOTH corrections files. Each names its gate
                 and carries a planted and a clean input. The gate must fail
                 the planted input and pass the clean one; a fixture its gate
                 lets through planted fails this test. A class with no gate is
                 declared below as a known gap, so a gap is a decision someone
                 made, never a silence.
  THE SCHEMA     every entry carries id, product, class, date, gate, reason
                 and notice, its class has a fixture, and the fixture's gate is
                 the gate the entry names.
  APPLIED        no card, brief, opinion, radio or deepdive correction is
                 unapplied in the committed export: a corrected sentence is in
                 no served file, a withdrawn episode is in no feed and no file,
                 a corrected Deep Dive's source_count is its outlet count and
                 its member_count is its member list.
  THE REPAIR     no archived card carries an E-16 opener, and every repaired
                 one is marked auto_corrected and carries its notice.

stdlib only, no key, no network, no database.
"""
from __future__ import annotations

import ast
import copy
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "pipeline"
sys.path.insert(0, str(PIPE))

from editorial import corrections as C  # noqa: E402
from editorial import derived_grounding as dg  # noqa: E402
from editorial import same_event as se  # noqa: E402
from editorial import standard as std  # noqa: E402
from briefing import weekly_parse as wp  # noqa: E402
from utils.bias_aggregation import compute_outlet_lean_histogram  # noqa: E402
from utils.prohibited_terms import find_prohibited  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "rigor_regressions"
BD = ROOT / "frontend" / "build-data"
PUB = ROOT / "frontend" / "public"
WEEKLY_CORR = BD / "weekly-corrections.json"

# Classes that reached production and that NO deterministic check catches yet.
# Adding a class here is a decision: say why in its fixture's `known_gap`.
KNOWN_GAPS = {
    "characterisation-in-void-voice",   # E-07 advisory, term list misses it
    "text-garble",                      # no corrupted-token rule
    "weekly-wrong-speaker",             # E-19 planned (factual-rigor plan gap 5)
}

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


# The two gates that live in other test files are run from their own code, so
# a fixture exercises the real rule and not a copy of it.
_tpg = _load_module("_tpg", ROOT / "tests" / "test_prompt_grounding.py")
sys.path.insert(0, str(ROOT))
from pipeline.validation import rigor as _rigor  # noqa: E402
_lint_src = (ROOT / "tests" / "test_truncation_lint.py").read_text(encoding="utf-8")
_lint_ns: dict = {"__file__": str(ROOT / "tests" / "test_truncation_lint.py"), "__name__": "_lint"}
exec(compile(_lint_src.split("\nchecked = 0")[0], "tests/test_truncation_lint.py", "exec"), _lint_ns)


# ---------------------------------------------------------------------------
# Gates: each returns the findings for one input (empty means it passes)
# ---------------------------------------------------------------------------
def _derived(fn_name: str, x: dict) -> list:
    fn = getattr(dg, fn_name)
    if fn is dg.check_total:
        r = fn(x["sentence"], x.get("prev"))
    else:
        r = fn(x["sentence"], dg.Evidence(x["evidence"]))
    return [r] if r else []


def _copy_literals(x: dict) -> list:
    lits = _tpg.copy_literals(x["source"])
    if x["check"] == "kill-list":
        return [t for _, t in lits if find_prohibited(t)]
    return [t for _, t in lits if _tpg._DASH.search(t)]


def _truncation(x: dict) -> list:
    src = x["source"]
    out = []
    for fn in ast.walk(ast.parse(src)):
        if isinstance(fn, ast.FunctionDef) and _lint_ns["caps"](fn):
            names = _lint_ns["published_counts"](fn)
            body = ast.get_source_segment(src, fn) or ""
            if names and not any(h in body for h in _lint_ns["HONEST"]):
                out.append(fn.name)
    return out


def _entity(x: dict) -> list:
    idx, _bag = se.entity_outliers([tuple(m) for m in x["members"]], x["cluster_title"])
    return list(idx)


GATES = {
    "E-13": lambda x: [f for f in std.validate_candidate(x) if f.id == "E-13"],
    "E-14": lambda x: [f for f in std.validate_candidate(x) if f.id == "E-14"],
    "E-16": lambda x: std.e16_topic_shift(x["summary"]),
    "pipeline/editorial/derived_grounding.py::check_total": lambda x: _derived("check_total", x),
    "pipeline/editorial/derived_grounding.py::check_numbers": lambda x: _derived("check_numbers", x),
    "pipeline/editorial/derived_grounding.py::check_dates": lambda x: _derived("check_dates", x),
    "pipeline/editorial/derived_grounding.py::check_lifted_quote": lambda x: _derived("check_lifted_quote", x),
    "pipeline/editorial/same_event.py::entity_outliers": _entity,
    "tests/test_prompt_grounding.py::copy_literals": _copy_literals,
    "pipeline/briefing/weekly_parse.py::ground_text": lambda x: wp.ground_text(x["text"], x["source_text"])[1],
    "pipeline/briefing/weekly_parse.py::ground_quotes": lambda x: wp.ground_quotes(x["text"], x["source_text"])[1],
    "tests/test_truncation_lint.py": _truncation,
}


def run_fixture(fx: dict) -> tuple[bool, bool, str]:
    """(fails when planted, passes when clean, detail)."""
    gate = GATES[fx["gate"]]
    planted, clean = gate(fx["planted"]), gate(fx["clean"])
    if fx["gate"] == "pipeline/editorial/same_event.py::entity_outliers":
        caught = sorted(planted) == sorted(fx["planted"]["foreign"])
        return caught, not clean, f"flagged {sorted(planted)}, clean flagged {sorted(clean)}"
    return bool(planted), not clean, f"planted {planted[:1]!r}, clean {clean[:1]!r}"


def main() -> int:
    corr = C.load()
    weekly = json.loads(WEEKLY_CORR.read_text(encoding="utf-8"))
    fixtures = {}
    for p in sorted(FIX.glob("*.json")):
        fx = json.loads(p.read_text(encoding="utf-8"))
        check(f"fixture {p.name}: its file is named for its class", p.stem == fx.get("class"))
        fixtures[fx["class"]] = fx

    # --- THE CORPUS -----------------------------------------------------------
    print("\nthe regression corpus")
    for cls, fx in sorted(fixtures.items()):
        for k in ("gate", "product", "covers", "planted", "clean"):
            check(f"{cls}: carries {k}", k in fx)
        if fx["gate"] == "none":
            check(f"{cls}: a class with no gate is a declared gap",
                  cls in KNOWN_GAPS and bool(fx.get("known_gap")),
                  "add it to KNOWN_GAPS with its reason, or give it a gate")
            continue
        check(f"{cls}: its gate {fx['gate']!r} is one this test can run", fx["gate"] in GATES)
        if fx["gate"] not in GATES:
            continue
        fails_planted, passes_clean, detail = run_fixture(fx)
        check(f"{cls}: {fx['gate']} fails the planted defect", fails_planted, detail)
        check(f"{cls}: {fx['gate']} passes the clean twin", passes_clean, detail)
    check("every declared gap has its fixture", KNOWN_GAPS <= set(fixtures),
          str(sorted(KNOWN_GAPS - set(fixtures))))

    # --- THE SCHEMA -----------------------------------------------------------
    print("\nthe corrections files")
    probs = C.schema_problems(corr)
    check("corrections.json: every entry carries id, product, class, date, gate, "
          "reason, notice and a target", not probs, "; ".join(probs[:5]))
    for c in corr:
        fx = fixtures.get(c.get("class"))
        check(f"{c.get('id')}: class {c.get('class')!r} has a regression fixture", fx is not None)
        if fx:
            check(f"{c.get('id')}: names the gate its fixture runs ({fx['gate']})",
                  c.get("gate") == fx["gate"], f"entry says {c.get('gate')!r}")
        n = c.get("notice")
        if n:
            check(f"{c.get('id')}: the notice carries no dash and no kill-list word",
                  not re.search("[\u2014\u2013]", n) and not find_prohibited(n), n)
    for i, w in enumerate(weekly):
        classes = w.get("classes") or []
        check(f"weekly-corrections #{i} ({w.get('corrected_on')} {w.get('section')}): "
              f"names its classes", bool(classes))
        for cls in classes:
            fx = fixtures.get(cls)
            check(f"weekly-corrections #{i}: class {cls!r} has a Weekly fixture",
                  fx is not None and fx.get("product") == "weekly")
    for c in corr:
        for gap in c.get("gap_classes") or []:
            check(f"{c.get('id')}: gap class {gap!r} is a declared gap with its fixture",
                  gap in KNOWN_GAPS and gap in fixtures)
        # F-5's own resolver (pipeline/validation/rigor.py): an ENFORCED rule
        # id, or a file that exists; with path::name, the function must exist.
        g = c.get("gate") or ""
        ok = _rigor.gate_resolves(g)
        if ok and "::" in g:
            path, name = g.split("::", 1)
            ok = re.search(rf"^\s*def {re.escape(name)}\b",
                           (ROOT / path).read_text(encoding="utf-8"), re.M) is not None
        check(f"{c.get('id')}: its gate {g!r} resolves (rule, file, named function)", ok)
    used = ({c.get("class") for c in corr}
            | {gap for c in corr for gap in c.get("gap_classes") or []}
            | {cls for w in weekly for cls in w.get("classes") or []})
    used.add(C.ARCHIVE_REPAIR_CLASS)
    check("every fixture is a class some correction records", set(fixtures) <= used,
          str(sorted(set(fixtures) - used)))

    # --- PLANTED: the export functions do what they say ----------------------
    print("\nthe export's correction functions, planted")
    bid = "b-1"
    plant = [
        {"id": "t-brief", "product": "brief", "class": "stacked-total", "date": "2026-10-03",
         "gate": "x", "reason": "r", "notice": "a sentence was removed", "brief": bid,
         "edits": [{"field": "tldr_text", "find": "This follows 10 percent cuts, totaling 20 percent. ",
                    "replace": ""}]},
        {"id": "t-radio", "product": "radio", "class": "lifted-quote", "date": "2026-10-03",
         "gate": "x", "reason": "r", "notice": "the recording is withdrawn", "brief": bid,
         "audio": "withdrawn", "audio_paths": ["/audio/world/x.mp3"]},
        {"id": "t-dd", "product": "deepdive", "class": "membership-contamination",
         "date": "2026-10-03", "gate": "x", "reason": "r", "notice": "members removed",
         "cluster": "c-1", "remove_members": ["https://x.test/foreign"]},
    ]
    brief = {"id": bid, "tldr_text": "Cuts of 20 percent. This follows 10 percent cuts, totaling 20 percent. "
                                     "The end.", "audio_url": "/audio/world/x.mp3?v=1",
             "audio_script": "A: words", "audio_chapters": [{"t": 0}]}
    check("an unapplied brief correction is found (text and audio)",
          len(C.unapplied_brief(brief, plant)) == 2, str(C.unapplied_brief(brief, plant)))
    C.apply_brief(brief, plant)
    check("applying removes the sentence", "totaling" not in brief["tldr_text"]
          and brief["tldr_text"] == "Cuts of 20 percent. The end.", brief["tldr_text"])
    check("a radio correction withdraws the episode: no audio field survives",
          brief["audio_withdrawn"] is True and not brief["audio_url"]
          and not brief["audio_script"] and not brief["audio_chapters"])
    check("the corrected brief carries both notices",
          [n["notice"] for n in brief.get("corrections", [])] ==
          ["a sentence was removed", "the recording is withdrawn"], str(brief.get("corrections")))
    check("a corrected brief is clean", not C.unapplied_brief(brief, plant))
    check("another day's brief is untouched",
          C.apply_brief({"id": "b-2", "tldr_text": "This follows 10 percent cuts, totaling 20 percent. "},
                        plant) == [])

    members = [
        {"source_id": "s1", "source_name": "Left Daily", "tier": "us_major", "lean": 20, "rigor": 60,
         "url": "https://x.test/1"},
        {"source_id": "s2", "source_name": "Centre Wire", "tier": "international", "lean": 50,
         "rigor": 50, "url": "https://x.test/2"},
        {"source_id": "s2", "source_name": "Centre Wire", "tier": "international", "lean": 52,
         "rigor": 50, "url": "https://x.test/3"},
        {"source_id": "s3", "source_name": "Right Post", "tier": "independent", "lean": 80,
         "rigor": 40, "url": "https://x.test/foreign"},
    ]
    meas = [m for m in members]
    votes = [{"outlet": m["source_name"], "name": m["source_name"], "lean": m["lean"],
              "state_affiliated": False} for m in meas]
    h0 = compute_outlet_lean_histogram(votes)
    bd = {"avg_political_lean": round(sum(m["lean"] for m in meas) / 4),
          "lean_total_count": 4, "tier_breakdown": {"us_major": 1, "international": 1, "independent": 1},
          "aggregate_confidence": 0.77, **h0}
    row = {"source_cluster_id": "c-1", "members": copy.deepcopy(members), "member_count": 4,
           "source_count": 3, "bias_diversity": bd}
    check("an unapplied membership correction is found", bool(C.unapplied_members([row], corrections=plant)))
    C.apply_members([row], corrections=plant)
    want = compute_outlet_lean_histogram(votes[:3])
    check("the foreign member is gone, and member_count is the member list",
          len(row["members"]) == 3 and row["member_count"] == 3)
    check("source_count is the distinct outlets that remain", row["source_count"] == 2)
    check("the histogram is recounted one vote per outlet",
          row["bias_diversity"]["lean_buckets"] == want["lean_buckets"]
          and row["bias_diversity"]["lean_outlet_count"] == 2, str(row["bias_diversity"]))
    check("a derived field that recomputes is recomputed, one that does not is left",
          row["bias_diversity"]["avg_political_lean"] == 41
          and row["bias_diversity"]["tier_breakdown"] == {"us_major": 1, "international": 1}
          and row["bias_diversity"]["aggregate_confidence"] == 0.77, str(row["bias_diversity"]))
    check("a corrected membership is clean", not C.unapplied_members([row], corrections=plant))

    arow = {"id": "p-1", "printed_on": "2026-09-20", "title": "Minister Resigns Over Budget Row",
            "summary": ("The finance minister resigned on Monday over the budget. "
                        "Separately, the city zoo welcomed two pandas. "
                        "The animals arrived from Chengdu. "
                        "Her deputy will act until the Budget Committee meets.")}
    log = C.repair_archive([arow])
    check("the archive repair removes the opener and its continuation, and keeps the "
          "sentence that returns to the story",
          arow["summary"] == ("The finance minister resigned on Monday over the budget. "
                              "Her deputy will act until the Budget Committee meets."),
          arow["summary"])
    check("the repaired row is marked auto_corrected with the repair's date",
          arow.get("auto_corrected") == C.ARCHIVE_REPAIR_DATE and len(log) == 1)
    check("the repaired row carries the notice",
          (arow.get("corrections") or [{}])[0].get("notice") == C.ARCHIVE_REPAIR_NOTICE)
    check("the repair is idempotent", C.repair_archive([arow]) == [])
    qrow = {"id": "p-3", "title": "Court Quashes Case Against Opposition Leader",
            "summary": ('The court cautioned him about "freedom fighters." Separately, a '
                        'comedian was cleared in another case. The court sits again in May.')}
    C.repair_archive([qrow])
    check("an opener after a closing quotation is found, where standard.sentences "
          "runs the two sentences together",
          "Separately" not in qrow["summary"] and qrow.get("auto_corrected"), qrow["summary"])
    untouched = {"id": "p-2", "summary": "Meanwhile the vote was delayed.\n\nNo shift here."}
    check("a summary with no E-16 opener is returned exactly as given",
          C.repair_archive([untouched]) == [] and untouched["summary"].startswith("Meanwhile the vote"))

    exp = (PIPE / "export_static.py").read_text(encoding="utf-8")
    for call in ("corrections.apply_brief(brief)", "corrections.apply_members(archive",
                 "corrections.repair_archive(archive)", "corrections.removed_members(cid)",
                 'corrections.apply_all(clusters, key="id")',
                 'corrections.apply_all(archive, key="source_cluster_id")'):
        check(f"the export calls {call}", call in exp)
    pod = (PIPE / "briefing" / "podcast_feed_generator.py").read_text(encoding="utf-8")
    check("the podcast feed reads every daily row through apply_brief", "apply_brief(_row)" in pod)

    # --- APPLIED, in the committed tree ---------------------------------------
    print("\nthe committed tree")
    feed = json.loads((BD / "feed.json").read_text(encoding="utf-8"))["clusters"]
    arch = json.loads((BD / "archive.json").read_text(encoding="utf-8"))
    brief_live = json.loads((PUB / "data" / "brief.json").read_text(encoding="utf-8"))
    podcast = (PUB / "podcast-world.xml").read_text(encoding="utf-8")

    left = C.unapplied(feed, "id") + C.unapplied(arch, "source_cluster_id")
    check("no card correction is unapplied in feed.json or archive.json", not left, str(left[:3]))
    left = C.unapplied_members(arch)
    check("no deepdive correction is unapplied in archive.json (members, member_count, "
          "source_count)", not left, str(left[:3]))
    check("no brief, opinion or radio correction is unapplied in brief.json",
          not C.unapplied_brief(brief_live), str(C.unapplied_brief(brief_live)))
    served = brief_live and json.dumps(brief_live, ensure_ascii=False) or ""
    for cid, text in C.corrected_texts():
        check(f"{cid}: the corrected sentence is in neither brief.json nor podcast-world.xml",
              text not in served and text not in podcast)
    for path in C.withdrawn_audio():
        check(f"withdrawn {path}: not in the deploy tree", not (PUB / path.lstrip("/")).exists())
        check(f"withdrawn {path}: no podcast item points at it", path not in podcast)
    for bid in C.withdrawn_brief_ids():
        check(f"withdrawn brief {bid[:8]}: no podcast item carries its guid", bid not in podcast)

    for c in corr:
        if C.product_of(c) != "deepdive":
            continue
        rows = [r for r in arch if r.get("source_cluster_id") == c["cluster"]]
        for r in rows:
            check(f"{c['id']}: archive row {r['id'][:8]} source_count equals its outlets "
                  f"and member_count its members",
                  r["source_count"] == C.outlet_count(r["members"])
                  and r["member_count"] == len(r["members"]),
                  f"{r['source_count']}/{C.outlet_count(r['members'])}, "
                  f"{r['member_count']}/{len(r['members'])}")
            check(f"{c['id']}: archive row {r['id'][:8]} carries the notice",
                  any(n.get("notice") == c["notice"] for n in r.get("corrections") or []))
        f = PUB / "data" / "deepdive" / f"{c['cluster']}.json"
        if f.exists():
            dd = json.loads(f.read_text(encoding="utf-8"))
            urls = {x["article"]["url"] for x in dd}
            card = next((d for d in feed if d["id"] == c["cluster"]), None)
            check(f"{c['id']}: the deepdive file lists no removed member",
                  not (urls & set(c["remove_members"])))
            if card:
                n = len({(x["article"].get("source") or {}).get("name") or x["article"]["id"] for x in dd})
                check(f"{c['id']}: the card's source_count is its deepdive file's outlets",
                      card["source_count"] == n, f"{card['source_count']} != {n}")

    # --- THE REPAIR -----------------------------------------------------------
    print("\nthe archive repair")
    still = [r["id"][:8] for r in arch if std.e16_topic_shift(r.get("summary") or "")
             or C.topic_shift_openers(r.get("summary") or "")]
    check("A-01 (in tree): no archived card carries an E-16 topic-shift opener", not still,
          f"{len(still)}: {still[:5]}")
    repaired = [r for r in arch if r.get("auto_corrected")]
    print(f"      {len(repaired)} archived card(s) repaired and marked auto_corrected")
    check("the repair has run on the committed archive", bool(repaired))
    check("every repaired card carries its notice and its date",
          all(any(n.get("notice") == C.ARCHIVE_REPAIR_NOTICE and n.get("date") == r["auto_corrected"]
                  for n in r.get("corrections") or []) for r in repaired))
    check("every repaired card still has a summary", all((r.get("summary") or "").strip() for r in repaired))
    stray = [r["id"][:8] for r in arch for n in r.get("corrections") or []
             if re.search("[\u2014\u2013]", str(n.get("notice")))]
    check("no notice on any card carries a dash", not stray, str(stray[:3]))

    if failures:
        print(f"\n{len(failures)} FAILED")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\ntest_corrections: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
