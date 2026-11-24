"""A Hearing quotation may not diverge from the source text we hold.

The Hearing prints `primary_source_excerpts` from the event YAML, and the
episode speaks them. Nothing checked those words against the document they
came from, because until the thesis pilot no document text was stored. The
first ledger (Srebrenica, 2026-09-24) found two live quotations that did not
match the record: Erdemovic's words paraphrased and presented as a quotation
(Sentencing Judgement, para. 10), and Resolution 819 with "and others
concerned" silently cut.

For every event that has an evidence ledger, each quotation is compared with
the stored extracts:

- found verbatim (after normalising case, punctuation and quote marks): pass;
- not found, but a stretch of an extract shares most of its words: FAIL, the
  quotation diverges from a source we hold;
- not found and nothing close: reported as unpinned, not failed, because the
  ledger may simply not hold that document yet.

Run: python tests/test_history_quote_ledger.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVENTS = ROOT / "data" / "history" / "events"
EVIDENCE = ROOT / "data" / "history" / "evidence"

# Share of a quotation's words that must recur, in one window of an extract,
# for the quotation to count as a divergent copy of that extract.
NEAR = 0.6


def norm_words(text: str, pdf_z_quote: bool = False) -> list[str]:
    if pdf_z_quote:
        # Some ICTY PDFs print an opening quotation mark as "z"; the extract
        # header records it when it happens.
        text = re.sub(r"\bz(?=[A-Z])", " ", text)
    text = text.lower().replace("’", "'").replace("'", "")
    return re.findall(r"[a-z0-9]+", text)


def load_extracts(slug: str) -> list[list[str]]:
    out = []
    for f in sorted((EVIDENCE / slug / "extracts").glob("*.txt")):
        raw = f.read_text(encoding="utf-8")
        out.append(norm_words(raw, pdf_z_quote="quotation mark as z" in raw))
    return out


def contains(hay: list[str], needle: list[str]) -> bool:
    n = len(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def best_overlap(hay: list[str], needle: list[str]) -> float:
    want = set(needle)
    n = len(needle) + 6
    best = 0.0
    for i in range(0, max(1, len(hay) - n + 1)):
        got = len(want & set(hay[i:i + n])) / len(want)
        best = max(best, got)
    return best


def check(slug: str, quotes: list[dict]) -> tuple[list[str], list[str]]:
    extracts = load_extracts(slug)
    failures, unpinned = [], []
    for q in quotes:
        words = norm_words(q["text"])
        if not words:
            continue
        if any(contains(e, words) for e in extracts):
            continue
        score = max((best_overlap(e, words) for e in extracts), default=0.0)
        label = f"{slug}: {q.get('author', '?')}: {q['text'][:70]}"
        if score >= NEAR:
            failures.append(f"{label} (diverges from a stored extract, overlap {score:.0%})")
        else:
            unpinned.append(label)
    return failures, unpinned


def self_test() -> None:
    """The two defects this check exists for must fail it."""
    extracts_slug = "srebrenica-genocide"
    if not (EVIDENCE / extracts_slug / "extracts").is_dir():
        return
    planted = [
        {"author": "Drazen Erdemovic",
         "text": "They told me that if I felt sorry for them, I should line up with them so they could kill me too."},
        {"author": "United Nations Security Council",
         "text": "Demands that all parties treat Srebrenica and its surroundings as a safe area which should be free from any armed attack or any other hostile act."},
    ]
    failures, _ = check(extracts_slug, planted)
    if len(failures) != len(planted):
        print("FAIL  self-test: a planted divergent quotation passed")
        for line in failures:
            print("   ", line)
        sys.exit(1)


# --------------------------------------------------------------------------
# The withdrawal gate (CEO, 2026-10-03, rev 86 WS-H).
#
# Until an event has a ledger, its quotations are WITHDRAWN from the served
# page, not labelled. An event with a published thesis is held to the T-checks
# instead and is exempt here. Everything else may serve a quotation only if
# its words occur in a stored extract (pipeline/history/quote_ledger.py), and
# that holds for the three places the page reads quotations from: the event
# row's `primary_source_excerpts`, each perspective's `notable_quotes`, and
# the document-voice lines of the exported script the Hearing renders.
# --------------------------------------------------------------------------
sys.path.insert(0, str(ROOT))
from pipeline.history import quote_ledger as QL  # noqa: E402

SERVED = ROOT / "frontend" / "public" / "data" / "history.json"
SERVED_SCRIPTS = ROOT / "frontend" / "build-data" / "history-scripts"
SCRIPTS = ROOT / "data" / "history" / "scripts"


def served_unverified(rows: list[dict], scripts: dict[str, dict]) -> list[str]:
    """Every quotation the served files carry for an event held to the ledger
    that no stored extract carries."""
    bad = []
    for row in rows:
        slug = row.get("slug") or ""
        if not QL.held_to_ledger(slug):
            continue
        for q in row.get("primary_source_excerpts") or []:
            if not QL.verified(slug, q.get("text", "")):
                bad.append(f"{slug}: history.json primary_source_excerpts: {str(q.get('text'))[:60]}")
        for p in row.get("perspectives") or []:
            for q in p.get("notable_quotes") or []:
                if not QL.verified(slug, q.get("text", "")):
                    bad.append(f"{slug}: history.json notable_quotes: {str(q.get('text'))[:60]}")
    for slug, blob in scripts.items():
        if not QL.held_to_ledger(slug):
            continue
        for seg in blob.get("segments") or []:
            for line in seg.get("lines") or []:
                if (line.get("speaker") or "N") != "N" and not QL.verified(slug, line.get("text", "")):
                    bad.append(f"{slug}: history-scripts {seg.get('kind')}: {str(line.get('text'))[:60]}")
    return bad


def withdrawal_self_test() -> list[str]:
    """The gate and the exporter's filter must each be able to fail."""
    out = []
    thesis = next(iter(sorted(QL.published_theses())), None)
    planted_rows = [
        {"slug": "planted-hearing", "primary_source_excerpts": [{"text": "Words nobody holds a copy of."}],
         "perspectives": [{"notable_quotes": [{"text": "Nor these.", "speaker": "X"}]}]},
    ]
    doc = {"kind": "DOCUMENT", "lines": [{"speaker": "N", "text": "She wrote it down."},
                                         {"speaker": "F", "text": "Words nobody holds a copy of."}]}
    got = served_unverified(planted_rows, {"planted-hearing": {"segments": [doc]}})
    if len(got) != 3:
        out.append(f"planted: an unverified excerpt, notable quote and script line must each fail ({got})")
    if thesis:
        exempt = served_unverified([dict(planted_rows[0], slug=thesis)], {thesis: {"segments": [doc]}})
        if exempt:
            out.append(f"planted: a published thesis event is exempt, got {exempt}")
    ex, nq, w = QL.filter_event(dict(planted_rows[0]))
    if ex or any(nq) or len(w) != 2:
        out.append(f"planted: the exporter must withdraw both planted quotations ({ex}, {nq}, {w})")
    segs, q, _lead = QL.filter_script_segments("planted-hearing", [
        doc,
        {"kind": "PERSPECTIVE", "lines": [{"speaker": "N", "text": "The account rests on the tide tables."},
                                          {"speaker": "N", "text": "Its admiral put it this way."},
                                          {"speaker": "M", "text": "Nor these."},
                                          {"speaker": "N", "text": "Nobody read them."}]}])
    texts = [l["text"] for s_ in segs for l in s_["lines"]]
    if [s_["kind"] for s_ in segs] != ["PERSPECTIVE"] or texts != [
            "The account rests on the tide tables.", "Nobody read them."] or q != 2:
        out.append(f"planted: a withdrawn DOCUMENT goes whole and a lead-in goes with its quote ({segs})")
    return out


def withdrawal_gate() -> int:
    fails = withdrawal_self_test()
    rows = json.loads(SERVED.read_text(encoding="utf-8")) if SERVED.exists() else []
    rows = rows if isinstance(rows, list) else rows.get("events", [])
    scripts = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted(SERVED_SCRIPTS.glob("*.json"))}
    fails += served_unverified(rows, scripts)
    held = [r for r in rows if QL.held_to_ledger(r.get("slug") or "")]
    yaml_quotes = 0
    for r in held:
        ev = yaml.safe_load((EVENTS / f"{r['slug']}.yaml").read_text(encoding="utf-8"))
        yaml_quotes += len(ev.get("primary_source_excerpts") or []) + sum(
            len(p.get("notable_quotes") or []) for p in ev.get("perspectives") or [])
    served_quotes = sum(len(r.get("primary_source_excerpts") or []) + sum(
        len(p.get("notable_quotes") or []) for p in r.get("perspectives") or []) for r in held)
    speaking = QL.scripts_speaking_withdrawn(SCRIPTS, EVENTS)
    if fails:
        for f in fails:
            print("FAIL ", f)
        return 1
    print(f"PASS  {len(held)} events without a published thesis serve no unverified quotation "
          f"({yaml_quotes - served_quotes} of {yaml_quotes} in the record withdrawn, {served_quotes} served)")
    if speaking:
        print(f"note  {len(speaking)} episode(s) still SPEAK {sum(speaking.values())} withdrawn "
              f"quotation line(s), awaiting a re-render: " + ", ".join(sorted(speaking)))
    return 0


def main() -> int:
    self_test()
    if withdrawal_gate():
        return 1
    failures, unpinned, checked = [], [], 0
    for ledger_dir in sorted(p for p in EVIDENCE.glob("*") if (p / "extracts").is_dir()):
        slug = ledger_dir.name
        event = EVENTS / f"{slug}.yaml"
        if not event.exists():
            continue
        data = yaml.safe_load(event.read_text(encoding="utf-8"))
        quotes = data.get("primary_source_excerpts") or []
        checked += len(quotes)
        f, u = check(slug, quotes)
        failures += f
        unpinned += u
    for line in unpinned:
        print("  unpinned:", line)
    if failures:
        for line in failures:
            print("FAIL ", line)
        return 1
    print(f"PASS  {checked} Hearing quotations checked against the ledger extracts; "
          f"none diverges from a source we hold ({len(unpinned)} unpinned)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
