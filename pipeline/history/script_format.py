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

# N narrates. M and F read quoted speech, matched to the SPEAKER'S SEX: a
# woman reading Nehru is jarring, and sex-matched readers are the documentary
# convention the format is modelled on (Ken Burns narrates in one voice and
# casts actors per source). The script declares it rather than the renderer
# guessing from a name, because guessing sex from names fails on exactly the
# cases that matter: Azad, Jucunda, anonymous testimony.
SPEAKERS = ("N", "M", "F")
QUOTE_SPEAKERS = ("M", "F")
KINDS = ("OPEN", "TITLE", "SCENE", "DOCUMENT", "PERSPECTIVE", "ASIDE", "TURN",
         "REST", "CLOSE")
# A REST carries no words. It is a held musical pause, placed by the writer
# where the listener needs somewhere to put what they have just heard: after a
# document that lands hard, before the accounts begin, before the close. A
# documentary that never stops talking gives the audience no room to feel
# anything, and the silence is part of the writing, not a gap in it.
# Segments in which the document voice may speak: a primary source, or a
# perspective quoting its own witness.
QUOTING = ("DOCUMENT", "PERSPECTIVE", "ASIDE")
WPM = 145.0                      # measured on the On Air cast, including pauses
# An event with five substantial perspectives cannot state all five fairly
# inside ten minutes, and stating them fairly is the whole point of the
# catalogue, so the band is wide enough to pay for the moat.
TARGET_MINUTES = (8.0, 15.0)
MUSIC_MINUTES = 1.1              # theme, scene stings, outro


@dataclass
class Line:
    speaker: str          # N | M | F
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
        d_lines = [l for l in seg.lines if l.speaker in QUOTE_SPEAKERS]
        if seg.kind not in QUOTING and d_lines:
            out.append(Finding("H-02", "fail", label, "document voice speaks outside a DOCUMENT segment"))
        if seg.kind in ("DOCUMENT", "PERSPECTIVE", "ASIDE") and d_lines:
            if seg.kind == "DOCUMENT" and not seg.author:
                out.append(Finding("H-03", "fail", label, "DOCUMENT has no author in its marker"))
            # H-04: the narrator must NAME THE SPEAKER before the voice reads.
            # Checking merely that some narration came first is not enough: a
            # perspective states its argument before it quotes, so that test
            # passes even when nobody is named. The speaker's name is looked up
            # from the data by matching the quote, so the rule holds wherever a
            # quote appears and does not depend on the marker being filled in.
            for i, l in enumerate(seg.lines):
                if l.speaker not in QUOTE_SPEAKERS:
                    continue
                said = _norm(l.text)
                speaker = next((who for src, who in sourced
                                if src and (said in src or src in said or _overlap(said, src) > 0.6)), None)
                before = " ".join(_norm(x.text) for x in seg.lines[:i] if x.speaker == "N")
                if not before:
                    out.append(Finding("H-04", "fail", label,
                                       "a quote is read with no narration before it: the listener "
                                       "hears words without knowing whose they are"))
                elif speaker:
                    named = [w for w in _norm(speaker).split() if len(w) > 3 and w != "anonymous"]
                    if named and not any(w in before for w in named):
                        out.append(Finding("H-04", "fail", label,
                                           f"the narration before this quote never names {speaker}"))
            # H-01: the quote must exist in the event's own sources.
            for l in d_lines:
                said = _norm(l.text)
                if not any(said in src or src in said or _overlap(said, src) > 0.6
                           for src, _ in sourced if src):
                    out.append(Finding("H-01", "fail", label,
                                       f"quotation not found in this event's primary sources: "
                                       f"{l.text[:70]!r}"))

    # H-09 is the reason this catalogue is worth making. Void's claim is that
    # it shows every side; an episode that quietly drops one is the single
    # failure that would make the claim false. The data names the sides, so the
    # script cannot silently omit one.
    have = " ".join(_norm(s.title or "") for s in script.segments if s.kind == "PERSPECTIVE")
    for persp in (event.get("perspectives") or []):
        name = persp.get("viewpoint") or ""
        # Compare on word PREFIXES, not whole words: a script may reasonably
        # title the account "the engineers" where the data says "Scientific and
        # Engineering Legacy", and those are plainly the same account. Six
        # characters is enough to keep "engineer" from matching "engine".
        stems = [w[:6] for w in _norm(name).split() if len(w) > 3]
        if stems and not any(st in have for st in stems):
            out.append(Finding("H-09", "fail", "PERSPECTIVE",
                               f"the {name} account is in the data but never heard in the episode"))
    heard = len([s for s in script.segments if s.kind == "PERSPECTIVE"])
    if heard and heard < len(event.get("perspectives") or []):
        out.append(Finding("H-09", "fail", "PERSPECTIVE",
                           f"{heard} of {len(event['perspectives'])} accounts given their own case"))

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
