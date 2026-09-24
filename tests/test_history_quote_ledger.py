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


def main() -> int:
    self_test()
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
