"""The History thesis format: parser (docs/proposals/HISTORY-THESIS-PAGE.md §8).

A thesis is Markdown with a strict front matter and five extensions:

    ---
    slug: srebrenica-genocide
    status: draft | audited | published
    ...
    ---
    ## The question
    ## The record
    ## The argument
    ### 1. The safe area
    The Council declared Srebrenica a safe area on April 16, 1993.[^src-un-sres-819 op1]
    The record carries no order from Zagreb that day.{i}
    ::: exhibit src-un-sres-819 op1
    ::: episode chapter=4
    ::: analysis an-crowd-counts
    ## The historiography
    ::: position bosniak-legal
    ### Where the record disagrees
    ::: contested death-toll
    ## What the record omits
    - No source in this record is by a Dutchbat soldier. {against=un-dutch}

`[^id locator]` is the citation marker and sits AFTER the sentence's final
punctuation. `{i}` marks an interpretive sentence, the historian's own. A
directive line (`::: `) pulls a ledger record, an extract, a script chapter or
an analysis into the page. Quotations use curly quotes only, so the parser can
tell a quotation from an apostrophe and never splits a sentence inside one.

The parser never raises on prose: a malformed line becomes a Finding in
thesis_checks, not a traceback. It raises only on a front matter that is not
YAML, because nothing downstream can proceed without the slug and the status.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import yaml

MARKER_RE = re.compile(r"\[\^([a-z0-9][a-z0-9-]*)(?:\s+([a-z0-9][a-z0-9.-]*))?\]")
INTERP = "{i}"
NUMERAL_RE = re.compile(r"(?<![\w.])\d(?:[\d,]*\d)?(?:\.\d+)?%?(?![\w])")
QUOTE_RE = re.compile(r"“([^“”]{1,1200})”")
DIRECTIVE_RE = re.compile(r"^:::\s+(exhibit|episode|position|contested|analysis)\b\s*(.*)$")
# Abbreviations whose full stop does not end a sentence.
_ABBREV = {"mr", "mrs", "ms", "dr", "prof", "gen", "col", "lt", "st", "no", "vol",
           "para", "paras", "p", "pp", "art", "cf", "eg", "ie", "vs", "op", "ch", "fig",
           "jr", "sr", "ed", "eds", "trans", "n", "nn", "sec", "res", "doc", "u", "s", "a"}

SECTION_KINDS = {
    "the question": "question",
    "the record": "record",
    "the argument": "argument",
    "the historiography": "historiography",
    "where the record disagrees": "contested",
    "what the record omits": "omits",
}


@dataclass
class Sentence:
    text: str                      # the sentence with markers and {i} removed
    markers: list[tuple[str, str]]  # (source id, locator or "")
    interpretive: bool
    line: int

    @property
    def quotes(self) -> list[str]:
        return [m.group(1) for m in QUOTE_RE.finditer(self.text)]

    @property
    def numerals(self) -> list[str]:
        return [m.group(0) for m in NUMERAL_RE.finditer(self.text)]


@dataclass
class Paragraph:
    kind: str = "paragraph"        # paragraph | list-item
    sentences: list[Sentence] = field(default_factory=list)
    raw: str = ""
    line: int = 0
    against: str | None = None     # list-item in Omits: the position it cuts against


@dataclass
class Directive:
    kind: str                      # exhibit | episode | position | contested | analysis
    args: dict
    raw: str
    line: int


Block = Paragraph | Directive


@dataclass
class Section:
    level: int                     # 2 or 3
    title: str
    kind: str                      # question | record | argument | historiography | contested | omits | argument-section | other
    number: int | None
    blocks: list[Block] = field(default_factory=list)
    line: int = 0
    parent: "Section | None" = None

    @property
    def id(self) -> str:
        if self.kind == "argument-section" and self.number is not None:
            return f"argument-{self.number}"
        return {"question": "question", "record": "record", "argument": "argument",
                "historiography": "historiography", "contested": "disagreements",
                "omits": "omits"}.get(self.kind, slugify(self.title))

    @property
    def paragraphs(self) -> list[Paragraph]:
        return [b for b in self.blocks if isinstance(b, Paragraph)]

    @property
    def directives(self) -> list[Directive]:
        return [b for b in self.blocks if isinstance(b, Directive)]


@dataclass
class Thesis:
    slug: str
    front: dict
    sections: list[Section]
    problems: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return str(self.front.get("status") or "draft")

    def section(self, kind: str) -> Section | None:
        return next((s for s in self.sections if s.kind == kind), None)

    def argument_sections(self) -> list[Section]:
        return [s for s in self.sections if s.kind == "argument-section"]

    @property
    def all_sentences(self) -> list[tuple[Section, Paragraph, Sentence]]:
        out = []
        for s in self.sections:
            for p in s.paragraphs:
                for sen in p.sentences:
                    out.append((s, p, sen))
        return out

    @property
    def all_markers(self) -> list[tuple[str, str]]:
        return [m for _, _, sen in self.all_sentences for m in sen.markers]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-") or "section"


# ------------------------------------------------------------- sentences

def _is_abbrev(text: str, i: int) -> bool:
    """`i` is the index of a full stop; is the word before it an abbreviation?"""
    j = i - 1
    while j >= 0 and (text[j].isalnum()):
        j -= 1
    word = text[j + 1:i].lower()
    return word in _ABBREV or (len(word) == 1 and word.isalpha() and word.isupper())


def split_sentences(text: str, line: int = 0) -> list[Sentence]:
    """Sentences of one paragraph. A terminator is `.`, `!` or `?` outside a
    curly-quoted span, not after an abbreviation, not inside a number, and
    followed by whitespace or the end. Markers and `{i}` that follow the
    terminator belong to the sentence that just closed."""
    out: list[Sentence] = []
    n = len(text)
    i = 0
    start = 0
    in_quote = False
    while i < n:
        c = text[i]
        if c == "“":
            in_quote = True
        elif c == "”":
            in_quote = False
        elif c in ".!?" and not in_quote:
            if c == "." and (
                (i + 1 < n and text[i + 1].isdigit() and i > 0 and text[i - 1].isdigit())
                or _is_abbrev(text, i)
            ):
                i += 1
                continue
            # consume the tail: more punctuation, closing quotes/brackets, markers, {i}
            j = i + 1
            while j < n and text[j] in ".!?”’)\"'":
                j += 1
            while True:
                m = MARKER_RE.match(text, j) if j < n else None
                if m:
                    j = m.end()
                    continue
                if text.startswith(INTERP, j):
                    j += len(INTERP)
                    continue
                if j < n and text[j] == " " and (MARKER_RE.match(text, j + 1) or text.startswith(INTERP, j + 1)):
                    j += 1
                    continue
                break
            if j >= n or text[j].isspace():
                out.append(_make_sentence(text[start:j], line))
                i = j
                while i < n and text[i].isspace():
                    i += 1
                start = i
                continue
        i += 1
    tail = text[start:].strip()
    if tail:
        out.append(_make_sentence(tail, line))
    return out


def _make_sentence(raw: str, line: int) -> Sentence:
    markers = [(m.group(1), m.group(2) or "") for m in MARKER_RE.finditer(raw)]
    interpretive = INTERP in raw
    text = MARKER_RE.sub("", raw).replace(INTERP, "")
    text = re.sub(r"\s+", " ", text).strip()
    return Sentence(text=text, markers=markers, interpretive=interpretive, line=line)


# ----------------------------------------------------------------- parse

def _parse_directive(line: str, lineno: int, problems: list[str]) -> Directive | None:
    m = DIRECTIVE_RE.match(line.strip())
    if not m:
        problems.append(f"line {lineno}: malformed directive {line.strip()!r}")
        return None
    kind, rest = m.group(1), m.group(2).strip()
    args: dict = {}
    parts = rest.split()
    if kind == "exhibit":
        if not parts:
            problems.append(f"line {lineno}: exhibit directive names nothing")
            return None
        args["ref"] = parts[0]
        if len(parts) > 1:
            args["locator"] = parts[1]
    elif kind in ("position", "contested", "analysis"):
        if not parts:
            problems.append(f"line {lineno}: {kind} directive names nothing")
            return None
        args["id"] = parts[0]
    elif kind == "episode":
        for p in parts:
            k, _, v = p.partition("=")
            args[k] = v
        if not str(args.get("chapter", "")).isdigit():
            problems.append(f"line {lineno}: episode directive needs chapter=<n>")
            return None
        args["chapter"] = int(args["chapter"])
        if "lines" in args:
            mm = re.match(r"^(\d+)-(\d+)$", args["lines"])
            if not mm:
                problems.append(f"line {lineno}: episode lines must be a-b")
                return None
            args["lines"] = (int(mm.group(1)), int(mm.group(2)))
    return Directive(kind=kind, args=args, raw=line.strip(), line=lineno)


def parse_thesis(raw: str, slug: str = "") -> Thesis:
    lines = raw.splitlines()
    problems: list[str] = []
    front: dict = {}
    body_start = 0
    if lines and lines[0].strip() == "---":
        try:
            end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        except StopIteration:
            raise ValueError(f"{slug}: front matter never closes")
        front = yaml.safe_load("\n".join(lines[1:end])) or {}
        if not isinstance(front, dict):
            raise ValueError(f"{slug}: front matter is not a mapping")
        body_start = end + 1
    else:
        problems.append("no front matter")

    sections: list[Section] = []
    current: Section | None = None
    parent_h2: Section | None = None
    para_lines: list[tuple[int, str]] = []

    def flush():
        nonlocal para_lines
        if not para_lines:
            return
        text = " ".join(t.strip() for _, t in para_lines)
        first = para_lines[0][0]
        if current is None:
            problems.append(f"line {first}: prose before the first section heading")
        else:
            current.blocks.append(Paragraph(kind="paragraph", sentences=split_sentences(text, first),
                                            raw=text, line=first))
        para_lines = []

    for idx in range(body_start, len(lines)):
        lineno = idx + 1
        line = lines[idx]
        stripped = line.strip()
        if not stripped:
            flush()
            continue
        if stripped.startswith("#"):
            flush()
            m = re.match(r"^(#{2,3})\s+(.*)$", stripped)
            if not m:
                problems.append(f"line {lineno}: heading must be ## or ###")
                continue
            level = len(m.group(1))
            title = m.group(2).strip()
            key = re.sub(r"^\d+\.\s*", "", title).strip().lower()
            number = None
            if level == 2:
                kind = SECTION_KINDS.get(key, "other")
                sec = Section(level=2, title=title, kind=kind, number=None, line=lineno)
                parent_h2 = sec
            else:
                if parent_h2 is None:
                    problems.append(f"line {lineno}: ### before any ##")
                mm = re.match(r"^(\d+)\.\s+(.*)$", title)
                if key in SECTION_KINDS and SECTION_KINDS[key] == "contested":
                    kind = "contested"
                elif parent_h2 is not None and parent_h2.kind == "argument" and mm:
                    kind = "argument-section"
                    number = int(mm.group(1))
                    title = title
                else:
                    kind = "other"
                sec = Section(level=3, title=title, kind=kind, number=number, line=lineno, parent=parent_h2)
            sections.append(sec)
            current = sec
            continue
        if stripped.startswith("::: ") or stripped == ":::":
            flush()
            d = _parse_directive(stripped, lineno, problems)
            if d is not None:
                if current is None:
                    problems.append(f"line {lineno}: directive before the first section heading")
                else:
                    current.blocks.append(d)
            continue
        if stripped.startswith("- "):
            flush()
            text = stripped[2:].strip()
            against = None
            m = re.search(r"\{against=([a-z0-9-]+)\}\s*$", text)
            if m:
                against = m.group(1)
                text = text[:m.start()].rstrip()
            if current is None:
                problems.append(f"line {lineno}: list item before the first section heading")
            else:
                current.blocks.append(Paragraph(kind="list-item", sentences=split_sentences(text, lineno),
                                                raw=text, line=lineno, against=against))
            continue
        para_lines.append((lineno, stripped))
    flush()

    return Thesis(slug=str(front.get("slug") or slug), front=front, sections=sections, problems=problems)


def strip_inline(text: str) -> str:
    """Plain text for the checks: `**x**` and `*x*` markup removed."""
    return re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)


def chapter_segments(script: dict) -> list[dict]:
    """The script export's segments that are chapters, in chapter order: the
    same rule history_producer.chapters() applies (no ASIDE, DOCUMENT, TITLE,
    and a REST has no lines to cue), so chapter n here is chapter n in the
    served manifest."""
    return [s for s in script.get("segments") or []
            if s.get("kind") in ("OPEN", "SCENE", "PERSPECTIVE", "TURN", "CLOSE")]
