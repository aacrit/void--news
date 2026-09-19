"""The History audio script format: parser and validators.

A History script is authored by hand and committed as data (see
docs/HISTORY-AUDIO.md for why it is not generated). This module is the
contract between that prose and the renderer.

    ## OPEN | TITLE | SCENE n | <title> | ASIDE | TURN | CLOSE
    ## DOCUMENT | <author> | <work> | <date>
    N: narrator line
    D: document line (only inside a DOCUMENT segment)
    ## SAY
    Radcliffe = RAD-kliff

The validators exist because one failure in a history programme is
unrecoverable: a quotation the source never said. H-01 makes that
structurally impossible by checking every D: line against the event's own
`primary_source_excerpts`. A script that invents a quote does not render.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

SPEAKERS = ("N", "D")
KINDS = ("OPEN", "TITLE", "SCENE", "DOCUMENT", "ASIDE", "TURN", "CLOSE")
WPM = 145.0                      # measured on the On Air cast, including pauses
TARGET_MINUTES = (8.0, 12.0)
MUSIC_MINUTES = 1.1              # theme, scene stings, outro


@dataclass
class Line:
    speaker: str
    text: str


@dataclass
class Segment:
    kind: str
    title: str | None = None
    author: str | None = None
    work: str | None = None
    date: str | None = None
    lines: list[Line] = field(default_factory=list)

    @property
    def words(self) -> int:
        return sum(len(l.text.split()) for l in self.lines)


@dataclass
class Script:
    slug: str
    segments: list[Segment] = field(default_factory=list)
    say: dict[str, str] = field(default_factory=dict)

    @property
    def words(self) -> int:
        return sum(s.words for s in self.segments)

    @property
    def minutes(self) -> float:
        return self.words / WPM + MUSIC_MINUTES


@dataclass
class Finding:
    id: str
    level: str          # "fail" | "warn"
    segment: str
    detail: str


def parse_script(raw: str, slug: str = "") -> Script:
    """Never raises: a malformed script becomes findings, not a traceback."""
    script = Script(slug=slug)
    cur: Segment | None = None
    in_say = False
    for line in raw.splitlines():
        line = line.rstrip()
        if line.startswith("## "):
            head = [p.strip() for p in line[3:].split("|")]
            kind = head[0].split()[0].upper() if head[0] else ""
            if kind == "SAY":
                in_say = True
                cur = None
                continue
            in_say = False
            cur = Segment(kind=kind)
            if kind == "DOCUMENT":
                cur.author = head[1] if len(head) > 1 else None
                cur.work = head[2] if len(head) > 2 else None
                cur.date = head[3] if len(head) > 3 else None
            elif len(head) > 1:
                cur.title = head[1]
            script.segments.append(cur)
            continue
        if in_say and "=" in line:
            k, v = line.split("=", 1)
            script.say[k.strip()] = v.strip()
            continue
        if not line or ":" not in line:
            continue
        sp, text = line.split(":", 1)
        if sp.strip() in SPEAKERS and cur is not None:
            cur.lines.append(Line(sp.strip(), text.strip()))
    return script


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", (s or "").lower())


def validate_script(script: Script, event: dict) -> list[Finding]:
    """Check a script against the EVENT DATA it was written from."""
    out: list[Finding] = []
    excerpts = event.get("primary_source_excerpts") or []
    quotes = [q for p in (event.get("perspectives") or [])
              for q in (p.get("notable_quotes") or [])]
    sourced = [(_norm(e.get("text", "")), e.get("author", "")) for e in excerpts]
    sourced += [(_norm(q.get("text", "")), q.get("speaker", "")) for q in quotes]

    kinds = [s.kind for s in script.segments]
    for required in ("OPEN", "CLOSE"):
        if required not in kinds:
            out.append(Finding("H-05", "fail", required, f"no {required} segment"))
    if "TURN" not in kinds:
        out.append(Finding("H-06", "fail", "TURN", "no TURN: the episode never shows the disagreement"))

    for seg in script.segments:
        label = f"{seg.kind}{' ' + seg.title if seg.title else ''}"
        d_lines = [l for l in seg.lines if l.speaker == "D"]
        if seg.kind != "DOCUMENT" and d_lines:
            out.append(Finding("H-02", "fail", label, "document voice speaks outside a DOCUMENT segment"))
        if seg.kind == "DOCUMENT":
            if not seg.author:
                out.append(Finding("H-03", "fail", label, "DOCUMENT has no author in its marker"))
            # H-04: the narrator must say who it is BEFORE the document reads.
            first_d = next((i for i, l in enumerate(seg.lines) if l.speaker == "D"), None)
            before = [l for l in seg.lines[:first_d or 0] if l.speaker == "N"]
            if first_d is None:
                out.append(Finding("H-03", "fail", label, "DOCUMENT segment with nothing read"))
            elif not before:
                out.append(Finding("H-04", "fail", label,
                                   "no attribution spoken before the read: the listener hears a quote "
                                   "without knowing whose it is"))
            elif seg.author:
                surname = seg.author.split()[-1].lower()
                if surname not in " ".join(_norm(l.text) for l in before):
                    out.append(Finding("H-04", "warn", label,
                                       f"attribution line does not name {seg.author}"))
            # H-01: the quote must exist in the event's own sources.
            for l in d_lines:
                said = _norm(l.text)
                if not any(said in src or src in said or _overlap(said, src) > 0.6
                           for src, _ in sourced if src):
                    out.append(Finding("H-01", "fail", label,
                                       f"quotation not found in this event's primary sources: "
                                       f"{l.text[:70]!r}"))

    lo, hi = TARGET_MINUTES
    if not (lo <= script.minutes <= hi):
        out.append(Finding("H-07", "fail", "TOTAL",
                           f"{script.words} words is {script.minutes:.1f} min, outside {lo:.0f}-{hi:.0f}"))
    for seg in script.segments:
        for l in seg.lines:
            if "—" in l.text or "–" in l.text:
                out.append(Finding("H-08", "warn", seg.kind, "dash in spoken copy"))
                break
    return out


def _overlap(a: str, b: str) -> float:
    """Word overlap, so trimming a quote for the ear is allowed but inventing is not."""
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / max(1, min(len(wa), len(wb)))
