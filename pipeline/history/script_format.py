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
import unicodedata
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


def _fold(s: str) -> str:
    """Strip accents. The event records spell names as the sources do
    (Hernan Cortes is Hernán Cortés there); the scripts spell them for a
    speech synthesiser. They are the same name and must compare equal."""
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", _fold(s).lower())


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
                    # Match on WORDS, not on raw substrings. "king" is inside
                    # "striking", and a segment that happens to use the word
                    # striking is not a segment that named Martin Luther King.
                    # A leading-edge match is still allowed in both directions
                    # so a possessive ("Khomeini's") names Khomeini.
                    words = before.split()
                    def _names(w: str) -> bool:
                        return any(x == w or x.startswith(w) or w.startswith(x)
                                   for x in words if len(x) > 3)
                    if named and not any(_names(w) for w in named):
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

    # H-10: every proper name the script speaks aloud must come from the
    # event's own record. This is the rule that makes DELEGATED drafting
    # safe. H-01 already makes a fabricated quotation impossible, but the
    # likelier failure by far is a confident, checkable, unsourced FACT: a
    # name, a place, an institution that the writer knows from somewhere
    # else and the event data does not contain. I introduced exactly that
    # twice by hand (an East India Company official who deciphered the
    # Ashokan script, and a leaning cathedral in Mexico City), caught both
    # only by grepping the YAML afterwards, and a drafting fleet will make
    # the same move far more often than one writer does.
    #
    # Matching is deliberately loose in the writer's favour: six-character
    # prefixes, case-insensitive, against the whole event document, so
    # "Ottomans" matches "Ottoman" and "Mande" matches "Mande". What it
    # catches is a name with no root anywhere in the record at all.
    haystack = _norm(_event_text(event))
    hay_words = set(haystack.split())
    hay_roots = {w[:6] for w in hay_words if len(w) > 3}
    for seg in script.segments:
        if seg.kind == "SAY":
            continue
        for l in seg.lines:
            for tok in _proper_names(l.text):
                low = _fold(tok).lower()
                if low in _NAME_ALLOWED or low in hay_words:
                    continue
                # A possessive or a hyphenated name is several words to the
                # record: Ben-Gurion is "ben gurion" there, Musa's is "musa".
                # Match on the PARTS, and treat the name as sourced when any
                # part of it is, which is the writer-favouring direction.
                parts = [x for x in re.split(r"[^a-z0-9]+", low) if len(x) > 2]
                if not parts or all(x in _NAME_ALLOWED for x in parts):
                    continue
                if any(x in hay_words or (x[:6] in hay_roots) or
                       any(x[:6] in w for w in hay_words) for x in parts):
                    continue
                out.append(Finding("H-10", "warn", f"{seg.kind}{' ' + seg.title if seg.title else ''}",
                                   f"{tok!r} is spoken in the script and appears nowhere in this "
                                   f"event's data: source it or cut it"))

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


def _event_text(event: dict) -> str:
    """Every word of the event record, flattened, as the sourcing haystack."""
    parts: list[str] = []
    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            parts.append(v)
        elif v is not None:
            parts.append(str(v))
    walk(event)
    return " ".join(parts)


# Words that are capitalised in ordinary prose and are not claims about the
# world: sentence openers, months and weekdays, the house name, and the
# spoken-number vocabulary the format requires (numbers are written as words,
# and a sentence can legitimately open "Twenty thousand men were lost").
_NAME_ALLOWED = {
    "the", "a", "an", "and", "but", "or", "so", "then", "now", "here", "there",
    "this", "that", "these", "those", "it", "its", "he", "she", "they", "them",
    "his", "her", "their", "we", "you", "i", "in", "on", "at", "by", "for",
    "from", "of", "to", "with", "within", "without", "after", "before", "when",
    "what", "which", "who", "whom", "whose", "why", "how", "if", "not", "no",
    "nobody", "none", "nothing", "every", "everything", "all", "both", "each",
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
    "seventeen", "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty",
    "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "million",
    "billion", "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "half", "january", "february",
    "march", "april", "may", "june", "july", "august", "september", "october",
    "november", "december", "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday", "void", "news", "on", "air", "history",
    "read", "listen", "look", "take", "put", "let", "say", "said", "there's",
    "god", "europe", "european", "west", "western", "east", "eastern",
    "north", "northern", "south", "southern",
    # Capitalised only because they open a sentence. Found by running the
    # rule over twenty one hand-written scripts and reading every flag.
    "about", "above", "across", "against", "almost", "along", "already",
    "also", "although", "among", "another", "any", "around", "as", "because",
    "behind", "being", "below", "beside", "besides", "between", "beyond",
    "can", "council", "did", "do", "does", "during", "either", "enough",
    "even", "ever", "everybody", "everyone", "everything", "except", "far",
    "few", "finally", "getting", "given", "going", "had", "has", "have",
    "health", "hold", "instead", "into", "inside", "is", "it's", "just",
    "keep", "kept", "know", "known", "later", "left", "legally", "less",
    "like", "long", "made", "make", "making", "many", "meanwhile", "might",
    "modelled", "more", "most", "much", "must", "near", "nearly", "neither",
    "never", "next", "nine", "nobody's", "once", "only", "other", "others",
    "out", "outside", "over", "own", "people", "perhaps", "property", "put",
    "rather", "read", "reading", "remember", "roughly", "same", "saying",
    "several", "shall", "should", "since", "small", "some", "somebody",
    "someone", "something", "somewhere", "still", "such", "tear", "tell",
    "than", "that's", "their", "think", "those", "though", "through",
    "throughout", "thus", "together", "toward", "towards", "under", "until",
    "up", "upon", "used", "very", "was", "were", "whatever", "whenever",
    "wherever", "whether", "while", "whole", "will", "with", "within",
    "worth", "would", "writers", "yet", "you're",
}

_NAME_RE = re.compile(r"\b([A-Z][a-zA-Z'\u2019-]{2,})")


def _proper_names(text: str) -> list[str]:
    """Capitalised words in a spoken line, as candidate factual claims."""
    return [m.group(1).strip("'\u2019-") for m in _NAME_RE.finditer(text or "")]


def _overlap(a: str, b: str) -> float:
    """Word overlap, so trimming a quote for the ear is allowed but inventing is not."""
    wa, wb = set(a.split()), set(b.split())
    return len(wa & wb) / max(1, min(len(wa), len(wb)))
