#!/usr/bin/env python3
"""Parsed History scripts, for the page to read at build time.

The Hearing renders the episode's own structure: the OPEN, the scenes and their
documents, each account arguing its case uninterrupted, then the turn. That
structure already exists, in `data/history/scripts/*.txt`, and until now only
the synthesiser ever read it.

This exports it as JSON into `frontend/build-data/history-scripts/`, so a
server component can render it with no client fetch and no "Retrieving archival
record..." for a reader with JavaScript off.

The one piece of real work is mapping each PERSPECTIVE segment in the script to
its account in the YAML. The script titles accounts for the ear ("the
engineers"); the data names them for the record ("Scientific and Engineering
Legacy"). H-09 already reconciles the two with a six-character stem rule, and
this reuses it rather than inventing a second answer: two rules that disagree
about which account is which would put words in the wrong mouth, which is the
whole thing the History section exists not to do.

Run: python3 -m pipeline.history.export_scripts
"""
from __future__ import annotations

import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.history.script_format import (  # noqa: E402
    Script, _norm, parse_script,
)

SCRIPTS = ROOT / "data/history/scripts"
EVENTS = ROOT / "data/history/events"
OUT = ROOT / "frontend/build-data/history-scripts"


def resolve_accounts(script: Script, event: dict) -> list[int | None]:
    """For each PERSPECTIVE segment, the index of the account it argues.

    Same rule as H-09, and it has to be the same rule rather than a similar
    one: two rules that disagree about which account is which would put an
    argument in the wrong mouth. H-09 asks whether a six-character stem of the
    account's name occurs ANYWHERE in the script's titles, as a substring, so
    "cuban" is found inside "cubans". Scoring these as sets of equal-length
    prefixes instead leaves "The Cubans" unmatched to "Cuban" and "The Whites"
    unmatched to "White Russian / Monarchist", which is exactly what the first
    draft of this function did.

    Best overlap wins. Segments are resolved in script order, and whatever is
    left over is assigned by elimination only once every confident match has
    been made, since an account claimed early by elimination is an account
    taken from the segment that actually names it.
    """
    perspectives = event.get("perspectives") or []
    stems: list[list[str]] = []
    for p in perspectives:
        name = _norm(p.get("viewpoint") or "")
        stems.append([w[:6] for w in name.split() if len(w) > 3])

    segments = [s for s in script.segments if s.kind == "PERSPECTIVE"]
    titles = [_norm(seg.title or "") for seg in segments]

    out: list[int | None] = [None] * len(segments)
    taken: set[int] = set()

    # Pass one: every segment that names its account, strongest match first, so
    # a weak overlap cannot claim an account that another segment names outright.
    # Score by how much of the ACCOUNT's name the title accounts for, not by a
    # bare count of matching stems. "The Mexica" matches one stem of both
    # "Aztec / Mexica" and "Modern Mexican Identity", and a count alone leaves
    # the winner to whichever index sorts higher, which handed the Mexica's
    # case to Modern Mexican Identity and left "Modern Mexico" holding the
    # Aztec account. One stem of a two-word name is a stronger claim than one
    # stem of a three-word name, and that is what breaks the tie correctly
    # here, in congo-free-state and in congo-wars.
    scored = []
    for si, title in enumerate(titles):
        for ai, st in enumerate(stems):
            if not st:
                continue
            hits = sum(1 for stem in st if stem and stem in title)
            if hits:
                scored.append((hits, hits / len(st), -si, si, ai))
    for _, _, _, si, ai in sorted(scored, reverse=True):
        if out[si] is None and ai not in taken:
            out[si] = ai
            taken.add(ai)

    # Pass two: elimination, and only where it is forced.
    for si in range(len(segments)):
        if out[si] is not None:
            continue
        free = [i for i in range(len(perspectives)) if i not in taken]
        if len(free) == 1:
            out[si] = free[0]
            taken.add(free[0])
    return out


def export(script: Script, event: dict) -> dict:
    accounts = resolve_accounts(script, event)
    seen_perspective = 0
    segments = []
    for seg in script.segments:
        row: dict = {
            "kind": seg.kind,
            "lines": [{"speaker": l.speaker, "text": l.text} for l in seg.lines],
        }
        if seg.title:
            row["title"] = seg.title
        if seg.kind == "DOCUMENT":
            row["author"] = seg.author
            row["work"] = seg.work
            row["date"] = seg.date
        if seg.kind == "PERSPECTIVE":
            row["account"] = accounts[seen_perspective]
            seen_perspective += 1
        segments.append(row)
    return {
        "slug": script.slug,
        "words": script.words,
        "segments": segments,
        "say": script.say,
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    written = 0
    problems: list[str] = []
    for path in sorted(SCRIPTS.glob("*.txt")):
        slug = path.stem
        ev_path = EVENTS / f"{slug}.yaml"
        if not ev_path.exists():
            problems.append(f"{slug}: script with no event record")
            continue
        event = yaml.safe_load(ev_path.read_text(encoding="utf-8"))
        script = parse_script(path.read_text(encoding="utf-8"), slug)
        blob = export(script, event)
        unresolved = [i for i, s in enumerate(blob["segments"])
                      if s["kind"] == "PERSPECTIVE" and s.get("account") is None]
        if unresolved:
            problems.append(f"{slug}: {len(unresolved)} account(s) unresolved")
        (OUT / f"{slug}.json").write_text(
            json.dumps(blob, ensure_ascii=False), encoding="utf-8")
        written += 1

    print(f"history-scripts/: {written} files")
    for p in problems:
        print(f"  [warn] {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
