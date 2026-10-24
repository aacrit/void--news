"""Which History quotations are verified against a source text we hold.

A quotation is VERIFIED when its words occur, in order, in a stored ledger
extract for its event (`data/history/evidence/<slug>/extracts/*.txt`), after
normalising case, punctuation and quotation marks. That is the only evidence
the repository holds that the words were said: the event YAML is a record
someone wrote, and H-01 checking a script against it is the YAML agreeing
with itself.

CEO decision, 2026-10-03 (rev 86 WS-H): until an event has a ledger, its
quotations are WITHDRAWN from the served page, not labelled. So:

- an event with a PUBLISHED thesis is held to the thesis checks (T-01..T-22)
  and is left exactly as it is;
- every other event has each `primary_source_excerpts` entry, each
  perspective's `notable_quotes`, and each line its script reads in the
  document voice, kept only when verified. With no ledger, nothing is.

The audio is not touched: an episode that speaks a withdrawn quotation is
listed by `scripts_speaking_withdrawn()` and re-rendered by a person, never
silently.

`tests/test_history_quote_ledger.py` uses the same matching, and fails when
the served `history.json` or a served script carries an unverified quotation
for an event without a published thesis.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "data" / "history" / "evidence"
THESES = ROOT / "data" / "history" / "theses"


def norm_words(text: str, pdf_z_quote: bool = False) -> list[str]:
    if pdf_z_quote:
        # Some ICTY PDFs print an opening quotation mark as "z"; the extract
        # header records it when it happens.
        text = re.sub(r"\bz(?=[A-Z])", " ", text)
    text = text.lower().replace("’", "'").replace("'", "")
    return re.findall(r"[a-z0-9]+", text)


@lru_cache(maxsize=None)
def load_extracts(slug: str) -> tuple[tuple[str, ...], ...]:
    out = []
    for f in sorted((EVIDENCE / slug / "extracts").glob("*.txt")):
        raw = f.read_text(encoding="utf-8")
        out.append(tuple(norm_words(raw, pdf_z_quote="quotation mark as z" in raw)))
    return tuple(out)


def contains(hay, needle) -> bool:
    n = len(needle)
    hay = list(hay)
    needle = list(needle)
    return any(hay[i:i + n] == needle for i in range(len(hay) - n + 1))


def verified(slug: str, text: str) -> bool:
    """True when the quotation's words occur, in order, in a stored extract."""
    words = norm_words(text or "")
    if not words:
        return False
    return any(contains(e, words) for e in load_extracts(slug))


@lru_cache(maxsize=None)
def published_theses() -> frozenset[str]:
    """Slugs whose thesis front matter says `status: published`."""
    out = set()
    for f in THESES.glob("*.md"):
        raw = f.read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---", raw, re.S)
        if not m:
            continue
        try:
            front = yaml.safe_load(m.group(1)) or {}
        except yaml.YAMLError:
            continue
        if front.get("status") == "published":
            out.add(f.stem)
    return frozenset(out)


def held_to_ledger(slug: str) -> bool:
    """True for an event whose quotations must be verified to be served."""
    return slug not in published_theses()


def filter_event(doc: dict) -> tuple[list[dict], list[list[dict]], list[str]]:
    """(excerpts kept, notable_quotes kept per perspective, withdrawn labels)."""
    slug = doc.get("slug") or ""
    excerpts = doc.get("primary_source_excerpts") or []
    persp = [p.get("notable_quotes") or [] for p in doc.get("perspectives") or []]
    if not held_to_ledger(slug):
        return list(excerpts), [list(q) for q in persp], []
    withdrawn: list[str] = []
    kept_ex = []
    for q in excerpts:
        if verified(slug, q.get("text", "")):
            kept_ex.append(q)
        else:
            withdrawn.append(f"primary_source_excerpts: {q.get('author', '?')}: {str(q.get('text'))[:60]}")
    kept_p = []
    for qs in persp:
        keep = []
        for q in qs:
            if verified(slug, q.get("text", "")):
                keep.append(q)
            else:
                withdrawn.append(f"notable_quotes: {q.get('speaker', '?')}: {str(q.get('text'))[:60]}")
        kept_p.append(keep)
    return kept_ex, kept_p, withdrawn


# A narration line that exists only to hand over to the quotation after it:
# "Mandela put the argument this way, in nineteen ninety four." With the
# quotation gone it would introduce nothing, so it goes with it.
_LEAD_IN = re.compile(
    r"(\bthis\b|\bthese words\b|\bthis way\b|\bas follows\b|\bplainly\b|\bin full\b"
    r"|\bown words\b|\bone line\b|\bone sentence\b|\bthree words\b|\bin two words\b|:)"
    r"[^.]{0,60}[.:]?\s*$|^here (?:is|he is|she is|it is)\b", re.I)


def is_lead_in(line: str) -> bool:
    return bool(_LEAD_IN.search((line or "").strip()))


def filter_script_segments(slug: str, segments: list[dict]) -> tuple[list[dict], int, int]:
    """The exported script's segments with unverified document-voice lines
    withdrawn: (segments, quote lines withdrawn, lead-in lines withdrawn).

    A DOCUMENT segment exists to present its document, so one whose every
    quotation is withdrawn is withdrawn whole, narration and all. In an
    account or an aside only the quotation goes, and the narrator's line
    directly before it when that line is nothing but a hand-over to it.
    """
    if not held_to_ledger(slug):
        return segments, 0, 0
    out: list[dict] = []
    gone_q = gone_lead = 0
    for seg in segments:
        lines = seg.get("lines") or []
        quoted = [i for i, l in enumerate(lines) if (l.get("speaker") or "N") != "N"]
        if not quoted:
            out.append(seg)
            continue
        drop = {i for i in quoted if not verified(slug, lines[i].get("text", ""))}
        if not drop:
            out.append(seg)
            continue
        gone_q += len(drop)
        if seg.get("kind") == "DOCUMENT" and drop == set(quoted):
            gone_lead += sum(1 for l in lines if (l.get("speaker") or "N") == "N")
            continue
        for i in sorted(drop):
            j = i - 1
            if j >= 0 and j not in drop and (lines[j].get("speaker") or "N") == "N" \
                    and is_lead_in(lines[j].get("text", "")):
                drop.add(j)
                gone_lead += 1
        out.append(dict(seg, lines=[l for i, l in enumerate(lines) if i not in drop]))
    return out, gone_q, gone_lead


def scripts_speaking_withdrawn(scripts_dir: Path, events_dir: Path) -> dict[str, int]:
    """slug -> number of document-voice lines its episode speaks that the
    page no longer prints. These episodes are flagged, not re-rendered."""
    import sys
    sys.path.insert(0, str(ROOT / "pipeline"))
    from history.script_format import parse_script  # noqa: E402
    out: dict[str, int] = {}
    for path in sorted(scripts_dir.glob("*.txt")):
        slug = path.stem
        if not held_to_ledger(slug) or not (events_dir / f"{slug}.yaml").exists():
            continue
        sc = parse_script(path.read_text(encoding="utf-8"), slug)
        n = sum(1 for seg in sc.segments for l in seg.lines
                if l.speaker != "N" and not verified(slug, l.text))
        if n:
            out[slug] = n
    return out
