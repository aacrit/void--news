"""The evidence ledger: one directory per History event, canonical over
everything the event may publish (docs/proposals/HISTORY-THESIS-PAGE.md §3, §4c, §8).

    data/history/evidence/<slug>/
      ledger.yaml            entries[], positions[], contested[], exhibits[], analyses[]
      extracts/<src-id>.<locator>.txt

An ENTRY is a source the event may cite. It carries the citation record of
§4c and an `access` block that says where its cited passages were READ and how
it was verified. An entry with no `access.free_copy` may be listed in the
historiography; it may not carry a pinned claim (T-05).

An EXTRACT is a verbatim passage, one file per pinned locator, with a header:

    source: src-icty-krstic-tj
    locator: para84
    url: https://www.icty.org/x/cases/krstic/tjug/en/krs-tj010802e.pdf
    read: 2026-09-24
    <blank line>
    <the passage as printed>

The header may carry `note:` lines (a glyph substitution in a PDF text layer,
for instance). Nothing else. A copyrighted work is held only as the passages
cited: at most 150 words per extract and 5 extracts per work (CEO decision 3).
Public-domain and official documents (`rights: public`) may be held whole.

Locators are short, filename-safe and rendered for the reader by
`locator_label`: `para84` -> "¶ 84", `p12` -> "p. 12", `p12-13` -> "pp. 12-13",
`op1` -> "op. para. 1", `pre3` -> "preambular para. 3", `fn2` -> "n. 2",
`sec2` -> "§ 2", `art2` -> "art. 2", `t04m12s` -> "4:12", `item3` -> "item 3",
`abstract` -> "abstract", `whole` -> "whole document".

`bootstrap` seeds a ledger from the event YAML (Stage 0 of §5) and `report`
writes docs/data/history-ledger.csv, the standing register of every event
against the bar of §4e. Both resolve identifiers LIVE (doi.org plus a Crossref
title match, the archive.org metadata API, Open Library) when the network is
allowed, and stamp `unverified` otherwise. Nothing here writes to the event
YAML: it is read-only input.

Run:
    python3 -m pipeline.history.ledger validate <slug>
    python3 -m pipeline.history.ledger bootstrap <slug> [--no-resolve]
    python3 -m pipeline.history.ledger report [--no-resolve] [--out docs/data/history-ledger.csv]
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data/history/events"
EVIDENCE = ROOT / "data/history/evidence"
THESES = ROOT / "data/history/theses"
REPORT = ROOT / "docs/data/history-ledger.csv"

TIERS = ("A", "B", "C", "D")
KINDS = (
    "primary-document", "judgment", "testimony", "resolution", "report",
    "treaty", "edict", "chronicle", "letter", "dataset", "monograph",
    "journal-article", "chapter", "edition", "edited-documents", "reference",
    "memoir", "party-history", "state-history", "advocacy", "image", "map",
)
VERIFIED_BY = (
    "crossref-title-match", "archive-item-fetch", "repository-record",
    "manual-page-read", "document-fetch", "openlibrary-record",
)
VERDICTS = ("supported", "contradicted", "qualified", "untestable")
BASES = ("presence", "absence")          # RULE B: what the verdict rests on
RENDERING_KINDS = ("official-parallel", "void-translation")
# Where a citation may never point (§4a, T-12).
EXCLUDED_HOSTS = (
    "wikipedia.org", "wikimedia.org/wiki/", "wikiquote.org", "wikisource.org",
    "fandom.com", "wikia.", "blogspot.", "wordpress.com", "medium.com",
    "substack.com", "quora.com", "reddit.com", "tumblr.com", "facebook.com",
    "x.com", "twitter.com", "youtube.com",
)
EXCLUDED_KINDS = ("review", "book-review", "wiki", "blog", "ai-output",
                  "lecture-notes")
STOCK_HOSTS = ("unsplash.com", "pexels.com", "pixabay.com", "shutterstock.com",
               "gettyimages.com", "istockphoto.com")

# The bar of §4e.
BAR_TIER_A = 6
BAR_TIER_B = 8
BAR_TIER_B_PINNED = 4
BAR_POSITIONS = 3
BAR_REGIONAL = 2
BAR_EXHIBITS = 3
BAR_ANALYSES = 1      # CEO 2026-09-24: no thesis publishes without a finding of its own

EXTRACT_MAX_WORDS = 150
EXTRACTS_PER_WORK = 5

_LOCATOR_RE = re.compile(
    r"^(?:para\d+[a-z]?(?:-\d+[a-z]?)?|p\d+(?:-\d+)?|op\d+|pre\d+|fn\d+|sec[a-z0-9]+|"
    r"art\d+[a-z]?|t\d{2}m\d{2}s|item\d+|abstract|whole|toc|dispositif|caption)$")
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ----------------------------------------------------------------------- model

@dataclass
class Finding:
    id: str
    level: str          # "fail" | "warn"
    where: str
    detail: str


@dataclass
class Extract:
    source: str
    locator: str
    url: str
    read: str
    text: str
    notes: list[str] = field(default_factory=list)
    path: pathlib.Path | None = None

    @property
    def key(self) -> str:
        return f"{self.source}.{self.locator}"

    @property
    def words(self) -> int:
        return len(self.text.split())


@dataclass
class Rendering:
    """An English rendering of a non-English extract, one file per extract:
    `extracts/<src>.<locator>.en.txt`. `kind` is `official-parallel` (a
    published parallel text, read at `url`) or `void-translation` (made here,
    at $0, never presented as a published quotation). `names` pairs each name
    as the original prints it with its rendering, so parity is checkable
    across scripts."""
    of: str
    kind: str
    text: str
    names: list[tuple[str, str]]
    url: str = ""
    read: str = ""
    checked_against: str = ""
    path: pathlib.Path | None = None


@dataclass
class Ledger:
    slug: str
    entries: dict[str, dict]
    positions: dict[str, dict]
    contested: dict[str, dict]
    exhibits: dict[str, dict]
    analyses: dict[str, dict]
    extracts: dict[str, Extract]
    raw: dict
    renderings: dict[str, Rendering] = field(default_factory=dict)
    gaps: list[dict] = field(default_factory=list)

    def entry(self, src: str) -> dict | None:
        return self.entries.get(src)

    def extract(self, src: str, locator: str) -> Extract | None:
        return self.extracts.get(f"{src}.{locator}")

    def extracts_of(self, src: str) -> list[Extract]:
        return [e for e in self.extracts.values() if e.source == src]

    def rendering(self, src: str, locator: str) -> Rendering | None:
        return self.renderings.get(f"{src}.{locator}")

    def producers_of(self, refs) -> set[str]:
        """Who produced the documents behind a list of `<src>.<locator>` refs."""
        out = set()
        for ref in refs or []:
            src = str(ref).partition(".")[0]
            e = self.entries.get(src) or {}
            if e.get("producer"):
                out.add(str(e["producer"]))
        return out


# --------------------------------------------------------------------- helpers

def locator_label(loc: str) -> str:
    """The reader-facing form of a locator."""
    m = re.match(r"^para(\d+[a-z]?)(?:-(\d+[a-z]?))?$", loc)
    if m:
        return f"¶ {m.group(1)}" + (f" to {m.group(2)}" if m.group(2) else "")
    m = re.match(r"^p(\d+)(?:-(\d+))?$", loc)
    if m:
        return f"pp. {m.group(1)} to {m.group(2)}" if m.group(2) else f"p. {m.group(1)}"
    m = re.match(r"^op(\d+)$", loc)
    if m:
        return f"operative para. {m.group(1)}"
    m = re.match(r"^pre(\d+)$", loc)
    if m:
        return f"preambular para. {m.group(1)}"
    m = re.match(r"^fn(\d+)$", loc)
    if m:
        return f"n. {m.group(1)}"
    m = re.match(r"^sec([a-z0-9]+)$", loc)
    if m:
        return f"§ {m.group(1)}"
    m = re.match(r"^art(\d+[a-z]?)$", loc)
    if m:
        return f"art. {m.group(1)}"
    m = re.match(r"^t(\d{2})m(\d{2})s$", loc)
    if m:
        return f"{int(m.group(1))}:{m.group(2)}"
    m = re.match(r"^item(\d+)$", loc)
    if m:
        return f"item {m.group(1)}"
    return {"abstract": "abstract", "whole": "whole document", "toc": "table of contents",
            "dispositif": "disposition", "caption": "caption"}.get(loc, loc)


_NUM_RE = re.compile(r"(?<![\w.])\d[\d,.]*\d|(?<![\w.])\d(?![\w])")


def _numbers(text: str) -> list[str]:
    """Digit strings in a text, commas and spaces removed, in order. A dot used
    as a thousands separator ("8.000", as Serbian and Dutch print it) is
    removed too, so 8.000 and 8,000 are the same number and 2.5 stays 2.5."""
    out = []
    for m in _NUM_RE.finditer(text or ""):
        s = re.sub(r"[,\s]", "", m.group(0)).rstrip(".")
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
            s = s.replace(".", "")
        out.append(s)
        # A footnote number glued to a figure by a PDF text layer ("2028.165"
        # for 2028 with note 165): the figure is carried too. Only when the
        # tail is three or more digits, so 2.5 never yields 2.
        mm = re.fullmatch(r"(\d+)\.(\d{3,})", s)
        if mm and not re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):
            out.append(mm.group(1))
        # The same glue on a year ("1995.54" for 1995 with note 54): a year
        # has no decimal part, so the integer is the figure.
        my = re.fullmatch(r"(1\d{3}|20\d{2})\.(\d{1,4})", s)
        if my:
            out.append(my.group(1))
    return out


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def norm(s: str) -> str:
    """The same normalisation H-01 uses (script_format._norm), so a quotation
    that passes here passes there."""
    return re.sub(r"[^a-z0-9 ]+", " ", fold(s).lower())


def read_extract(path: pathlib.Path) -> Extract:
    raw = path.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n\n")
    fields: dict[str, str] = {}
    notes: list[str] = []
    for line in head.splitlines():
        k, _, v = line.partition(":")
        k = k.strip().lower()
        v = v.strip()
        if k == "note":
            notes.append(v)
        elif k in ("source", "locator", "url", "read"):
            fields[k] = v
        else:
            raise ValueError(f"{path.name}: unknown header line {line!r}")
    for k in ("source", "locator", "url", "read"):
        if not fields.get(k):
            raise ValueError(f"{path.name}: header lacks {k}")
    return Extract(source=fields["source"], locator=fields["locator"],
                   url=fields["url"], read=fields["read"], text=body.strip(),
                   notes=notes, path=path)


def read_rendering(path: pathlib.Path) -> Rendering:
    raw = path.read_text(encoding="utf-8")
    head, _, body = raw.partition("\n\n")
    fields: dict[str, str] = {}
    for line in head.splitlines():
        k, _, v = line.partition(":")
        k = k.strip().lower()
        if k not in ("rendering", "of", "names", "url", "read", "checked_against"):
            raise ValueError(f"{path.name}: unknown header line {line!r}")
        fields[k] = v.strip()
    if not fields.get("rendering") or not fields.get("of"):
        raise ValueError(f"{path.name}: a rendering needs `rendering:` and `of:`")
    names = []
    for pair in [p.strip() for p in fields.get("names", "").split(";") if p.strip()]:
        a, _, b = pair.partition("=")
        names.append((a.strip(), b.strip()))
    return Rendering(of=fields["of"], kind=fields["rendering"], text=body.strip(), names=names,
                     url=fields.get("url", ""), read=fields.get("read", ""),
                     checked_against=fields.get("checked_against", ""), path=path)


def load_ledger(slug: str, evidence_dir: pathlib.Path | None = None) -> Ledger:
    base = (evidence_dir or EVIDENCE) / slug
    raw = yaml.safe_load((base / "ledger.yaml").read_text(encoding="utf-8")) or {}

    def keyed(items, what):
        out: dict[str, dict] = {}
        for it in items or []:
            if not isinstance(it, dict) or not it.get("id"):
                raise ValueError(f"{slug}: a {what} row has no id: {it!r}"[:200])
            out[str(it["id"])] = it
        return out

    extracts: dict[str, Extract] = {}
    renderings: dict[str, Rendering] = {}
    exdir = base / "extracts"
    if exdir.exists():
        for p in sorted(exdir.glob("*.txt")):
            if p.name.endswith(".en.txt"):
                r = read_rendering(p)
                renderings[r.of] = r
            else:
                ex = read_extract(p)
                extracts[ex.key] = ex
    return Ledger(
        slug=str(raw.get("slug") or slug),
        entries=keyed(raw.get("entries"), "entry"),
        positions=keyed(raw.get("positions"), "position"),
        contested=keyed(raw.get("contested"), "contested"),
        exhibits=keyed(raw.get("exhibits"), "exhibit"),
        analyses=keyed(raw.get("analyses"), "analysis"),
        extracts=extracts,
        raw=raw,
        renderings=renderings,
        gaps=[g for g in (raw.get("gaps") or []) if isinstance(g, dict)],
    )


def entry_is_verified(e: dict) -> bool:
    acc = e.get("access") or {}
    return bool(acc.get("verified_by")) and acc["verified_by"] in VERIFIED_BY \
        and bool(acc.get("verified_at")) and bool(acc.get("verified_title"))


def entry_is_pinned(ledger: Ledger, src: str) -> bool:
    e = ledger.entries.get(src) or {}
    return bool((e.get("access") or {}).get("free_copy")) and bool(ledger.extracts_of(src))


def is_public(e: dict) -> bool:
    return str(e.get("rights") or "").lower() in ("public", "public-domain", "official")


# ------------------------------------------------------------- derivations

def compute_analysis(analysis: dict) -> tuple[object, str]:
    """Recompute an analysis's stated result from its derivation rows.

    Returns (value, description). The `derivation` block is:
        compute: count | sum | min | max | range | distinct | ratio | share
        column: <row field>            (sum/min/max/range/distinct/ratio/share)
        over: <row field>              (ratio: numerator column / over column, rows summed)
        of: <value>                    (share: rows whose column == of, over all rows)
        rows: [{..., extract: <src>.<locator>}, ...]
    """
    d = analysis.get("derivation") or {}
    rows = [r for r in (d.get("rows") or []) if isinstance(r, dict)]
    how = str(d.get("compute") or "").lower()
    col = d.get("column")

    def num(v):
        if isinstance(v, (int, float)):
            return float(v)
        s = str(v).replace(",", "")
        return float(s)

    if how == "count":
        return len(rows), f"count of rows = {len(rows)}"
    if how == "distinct":
        vals = {str(r.get(col)) for r in rows}
        return len(vals), f"distinct {col} = {len(vals)}"
    if how in ("sum", "min", "max", "range"):
        vals = [num(r.get(col)) for r in rows]
        if not vals:
            return None, "no rows"
        if how == "sum":
            return sum(vals), f"sum of {col} = {sum(vals):g}"
        if how == "min":
            return min(vals), f"min of {col} = {min(vals):g}"
        if how == "max":
            return max(vals), f"max of {col} = {max(vals):g}"
        return [min(vals), max(vals)], f"range of {col} = {min(vals):g} to {max(vals):g}"
    if how == "ratio":
        over = d.get("over")
        a = sum(num(r.get(col)) for r in rows)
        b = sum(num(r.get(over)) for r in rows)
        return (a / b if b else None), f"sum {col} / sum {over} = {a:g}/{b:g}"
    if how == "share":
        of = d.get("of")
        n = sum(1 for r in rows if str(r.get(col)) == str(of))
        return (n / len(rows) if rows else None), f"rows with {col} = {of!r}: {n} of {len(rows)}"
    return None, f"unknown compute {how!r}"


def result_matches(expected, got) -> bool:
    if got is None:
        return False
    if isinstance(expected, list) and isinstance(got, list):
        return len(expected) == len(got) and all(result_matches(a, b) for a, b in zip(expected, got))
    try:
        return abs(float(str(expected).replace(",", "")) - float(got)) < 1e-6 or \
            (abs(float(str(expected).replace(",", "")) - float(got)) / max(abs(float(got)), 1e-9) < 0.005)
    except (TypeError, ValueError):
        return str(expected) == str(got)


# ----------------------------------------------------------------- validate

def validate_ledger(ledger: Ledger) -> list[Finding]:
    """L-01..L-12: the ledger agrees with itself and with §4c."""
    out: list[Finding] = []

    def fail(code, where, detail):
        out.append(Finding(code, "fail", where, detail))

    # L-01 entries carry the citation record.
    for src, e in ledger.entries.items():
        if not _ID_RE.match(src):
            fail("L-01", src, "id is not lower-case kebab")
        if e.get("tier") not in TIERS:
            fail("L-01", src, f"tier {e.get('tier')!r} not in {TIERS}")
        if e.get("kind") not in KINDS:
            fail("L-01", src, f"kind {e.get('kind')!r} not in KINDS")
        for k in ("author", "title", "year", "language", "region_of_authorship", "producer"):
            if not e.get(k):
                fail("L-01", src, f"missing {k}")
        acc = e.get("access")
        if not isinstance(acc, dict):
            fail("L-01", src, "missing access block")
            continue
        vb = acc.get("verified_by")
        if vb and vb not in VERIFIED_BY:
            fail("L-01", src, f"verified_by {vb!r} not in {VERIFIED_BY}")
        if vb and not _DATE_RE.match(str(acc.get("verified_at") or "")):
            fail("L-01", src, "verified_at is not YYYY-MM-DD")
        if vb and not acc.get("verified_title"):
            fail("L-01", src, "verified but verified_title is empty")
        if e.get("tier") == "D" and not e.get("position"):
            fail("L-01", src, "a Tier D entry must name the position it holds")
        ids = e.get("identifiers") or {}
        url = str(ids.get("url") or acc.get("free_copy") or "")
        if any(h in url for h in EXCLUDED_HOSTS):
            fail("L-02", src, f"excluded host in {url}")
        if str(e.get("kind")) in EXCLUDED_KINDS:
            fail("L-02", src, f"excluded kind {e.get('kind')}")

    # L-03 extracts: header agrees with the file name, the entry exists, the
    # locator parses, the read url is the entry's free copy.
    per_work: dict[str, int] = {}
    for key, ex in ledger.extracts.items():
        p = ex.path.name if ex.path else key
        if ex.path and ex.path.stem != key:
            fail("L-03", p, f"file name disagrees with header ({key})")
        if ex.source not in ledger.entries:
            fail("L-03", p, f"extract for unknown entry {ex.source}")
            continue
        if not _LOCATOR_RE.match(ex.locator):
            fail("L-03", p, f"locator {ex.locator!r} does not parse")
        if not _DATE_RE.match(ex.read):
            fail("L-03", p, "read date is not YYYY-MM-DD")
        if not ex.text:
            fail("L-03", p, "empty extract")
        e = ledger.entries[ex.source]
        free = (e.get("access") or {}).get("free_copy")
        if not free:
            fail("L-04", p, "extract for an entry with no access.free_copy")
        elif ex.url != free and ex.url != str((e.get("identifiers") or {}).get("url") or ""):
            fail("L-04", p, f"extract url {ex.url} is not the entry's free_copy")
        if not is_public(e):
            per_work[ex.source] = per_work.get(ex.source, 0) + 1
            if ex.words > EXTRACT_MAX_WORDS:
                fail("L-05", p, f"{ex.words} words in an extract of a copyrighted work (cap {EXTRACT_MAX_WORDS})")
    for src, n in per_work.items():
        if n > EXTRACTS_PER_WORK:
            fail("L-05", src, f"{n} extracts of a copyrighted work (cap {EXTRACTS_PER_WORK})")

    # L-06 positions.
    for pid, pos in ledger.positions.items():
        for k in ("name", "holders", "rests_on", "claim", "omits"):
            if not pos.get(k):
                fail("L-06", pid, f"position lacks {k}")
        for src in pos.get("rests_on") or []:
            if src not in ledger.entries:
                fail("L-06", pid, f"rests on unknown entry {src}")
        for adj in pos.get("adjudications") or []:
            if adj.get("verdict") not in VERDICTS:
                fail("L-07", pid, f"verdict {adj.get('verdict')!r} not in {VERDICTS}")
            if not adj.get("claim"):
                fail("L-07", pid, "adjudication with no claim")
            if adj.get("basis") not in BASES:
                fail("L-07", pid, f"adjudication basis {adj.get('basis')!r} not in {BASES}")
            if not adj.get("reasoning"):
                fail("L-07", pid, "adjudication with no reasoning")
            for ref in adj.get("rests_on") or []:
                src, _, loc = str(ref).partition(".")
                if src not in ledger.entries:
                    fail("L-07", pid, f"adjudication rests on unknown entry {src}")
                elif not loc or not ledger.extract(src, loc):
                    fail("L-07", pid, f"adjudication rests on no stored extract {ref}")
            # RULE B (CEO 2026-09-24): absence of evidence never contradicts.
            if adj.get("basis") == "absence" and adj.get("verdict") in ("contradicted", "supported"):
                fail("L-12", pid, f"a verdict resting on absence may not be {adj.get('verdict')}")
            # RULE A: every verdict names whose record it rests on, and a
            # record from one side caps the verdict at qualified.
            producers = ledger.producers_of(adj.get("rests_on") or [])
            if adj.get("verdict") in ("contradicted", "supported") and not producers:
                fail("L-13", pid, "verdict rests on documents with no named producer")
            if adj.get("verdict") in ("contradicted", "supported") and len(producers) < 2:
                fail("L-13", pid, f"{adj.get('verdict')} on one side's record alone ({', '.join(sorted(producers)) or 'none'}); cap is qualified")

    # L-08 contested.
    for cid, c in ledger.contested.items():
        rows = c.get("rows") or []
        if not c.get("claim"):
            fail("L-08", cid, "contested claim has no claim text")
        for r in rows:
            if r.get("position") not in ledger.positions:
                fail("L-08", cid, f"row names unknown position {r.get('position')}")
            src = str(r.get("source") or "")
            if src not in ledger.entries:
                fail("L-08", cid, f"row cites unknown entry {src}")
            loc = r.get("locator")
            if loc and not ledger.extract(src, str(loc)):
                fail("L-08", cid, f"row locator {src}.{loc} has no stored extract")

    # L-09 exhibits.
    for xid, x in ledger.exhibits.items():
        for k in ("kind", "title", "creator", "date", "repository", "accession", "licence", "url"):
            if not x.get(k):
                fail("L-09", xid, f"exhibit lacks {k}")
        if x.get("kind") in ("image", "map") and not (x.get("shows") and x.get("does_not_show")):
            fail("L-09", xid, "an image or map needs shows and does_not_show")
        if any(h in str(x.get("url") or "") for h in STOCK_HOSTS):
            fail("L-09", xid, "stock photograph")
        if x.get("kind") == "document":
            src = str(x.get("source") or "")
            if src not in ledger.entries or not x.get("locator") or not ledger.extract(src, str(x["locator"])):
                fail("L-09", xid, "document exhibit does not point at a stored extract")

    # L-14 gaps: a Tier A or B entry the record could not read free is published
    # as a gap, by entry id, with what was tried (RULE B).
    gap_entries = {str(g.get("entry")) for g in ledger.gaps if g.get("entry")}
    for g in ledger.gaps:
        for k in ("what", "status"):
            if not g.get(k):
                fail("L-14", str(g.get("entry") or g.get("what")), f"gap lacks {k}")
        if g.get("entry") and g["entry"] not in ledger.entries:
            fail("L-14", str(g["entry"]), "gap names an unknown entry")
    for src, e in ledger.entries.items():
        if e.get("tier") in ("A", "B") and not (e.get("access") or {}).get("free_copy") \
                and src not in gap_entries:
            fail("L-14", src, "a Tier A/B entry with no free copy must be listed under gaps")

    # L-15 renderings: original stays, the rendering keeps every number and
    # every declared name, an official parallel is read at a url, and a Void
    # translation checked against a parallel agrees with it on numbers.
    for key, r in ledger.renderings.items():
        p = r.path.name if r.path else key
        if r.kind not in RENDERING_KINDS:
            fail("L-15", p, f"rendering kind {r.kind!r} not in {RENDERING_KINDS}")
        ex = ledger.extracts.get(r.of)
        if ex is None:
            fail("L-15", p, f"rendering of a missing extract {r.of}")
            continue
        if r.kind == "official-parallel" and not (r.url and r.read):
            fail("L-15", p, "an official parallel must say where and when it was read")
        missing = [n for n in _numbers(ex.text) if n not in _numbers(r.text)]
        if missing:
            fail("L-15", p, f"numbers in the original are missing from the rendering: {missing[:6]}")
        if r.kind == "void-translation" and not r.names:
            fail("L-15", p, "a Void translation must declare its name pairs")
        for orig, rend in r.names:
            if orig not in ex.text:
                fail("L-15", p, f"declared name {orig!r} is not in the original")
            if rend not in r.text:
                fail("L-15", p, f"rendered name {rend!r} is not in the rendering")
        if r.checked_against:
            src, _, loc = r.checked_against.partition(".")
            par = ledger.extract(src, loc)
            if par is None:
                fail("L-15", p, f"checked_against names no stored extract {r.checked_against}")
            else:
                diff = [n for n in _numbers(par.text) if n not in _numbers(r.text)]
                if diff:
                    fail("L-15", p, f"the official parallel carries numbers the Void translation lacks: {diff[:6]}")
                for _, rend in r.names:
                    if rend not in par.text:
                        fail("L-15", p, f"rendered name {rend!r} is not in the official parallel")

    # L-10 analyses: method, derivation rows traced to extracts, result recomputes.
    for aid, a in ledger.analyses.items():
        for k in ("title", "method", "finding", "confidence", "derivation", "result"):
            if not a.get(k) and a.get(k) != 0:
                fail("L-10", aid, f"analysis lacks {k}")
        d = a.get("derivation") or {}
        rows = d.get("rows") or []
        if not rows:
            fail("L-10", aid, "derivation has no rows")
        for i, r in enumerate(rows):
            ref = str(r.get("extract") or "")
            src, _, loc = ref.partition(".")
            if not ref or src not in ledger.entries or not ledger.extract(src, loc):
                fail("L-10", aid, f"row {i} does not resolve to a stored extract ({ref!r})")
            elif ledger.entries[src].get("tier") not in ("A", "B"):
                fail("L-10", aid, f"row {i} rests on a Tier {ledger.entries[src].get('tier')} entry")
        got, how = compute_analysis(a)
        if not result_matches(a.get("result"), got):
            fail("L-11", aid, f"stated result {a.get('result')!r} does not recompute: {how}")
        if not a.get("against") and str(a.get("confidence")).lower() != "entailed":
            fail("L-10", aid, "an inference that is not entailed must state the evidence against it")

    return out


# ------------------------------------------------------------ the bar (§4e)

def standing(ledger: Ledger, event: dict | None = None) -> dict:
    """Counts against the bar. Used by T-13 and the register."""
    A = [s for s, e in ledger.entries.items() if e.get("tier") == "A"]
    B = [s for s, e in ledger.entries.items() if e.get("tier") == "B"]
    a_with_extract = [s for s in A if ledger.extracts_of(s)]
    b_verified = [s for s in B if entry_is_verified(ledger.entries[s])]
    b_pinned = [s for s in b_verified if entry_is_pinned(ledger, s)]
    region = str((event or {}).get("region") or "")
    regional = [s for s, e in ledger.entries.items()
                if entry_is_verified(e) and (
                    (region and str(e.get("region_of_authorship")) == region)
                    or str(e.get("language") or "en") != "en")]
    positions_ok = [pid for pid, p in ledger.positions.items()
                    if any(entry_is_verified(ledger.entries.get(s) or {})
                           and str((ledger.entries.get(s) or {}).get("position") or "") == pid
                           for s in (p.get("rests_on") or []))]
    exhibits_ok = [x for x, v in ledger.exhibits.items()
                   if all(v.get(k) for k in ("creator", "date", "repository", "accession", "licence", "url"))]
    return {
        "tier_a": len(A), "tier_a_with_extract": len(a_with_extract),
        "tier_b": len(B), "tier_b_verified": len(b_verified), "tier_b_pinned": len(b_pinned),
        "positions": len(ledger.positions), "positions_with_holder_source": len(positions_ok),
        "regional": len(regional), "exhibits": len(exhibits_ok),
        "analyses": len(ledger.analyses),
        "extracts": len(ledger.extracts),
        "bar": {
            "tier_a": len(a_with_extract) >= BAR_TIER_A,
            "tier_b": len(b_verified) >= BAR_TIER_B and len(b_pinned) >= BAR_TIER_B_PINNED,
            "positions": len(positions_ok) >= BAR_POSITIONS and len(ledger.positions) >= BAR_POSITIONS,
            "regional": len(regional) >= BAR_REGIONAL,
            "exhibits": len(exhibits_ok) >= BAR_EXHIBITS,
            "analyses": len(ledger.analyses) >= BAR_ANALYSES,
        },
    }


# ------------------------------------------------------------- resolvers

_UA = "void-history-ledger/0.1 (+https://news.voidvision.org; aacrit@gmail.com)"
_cache: dict[str, dict] = {}


def _get_json(url: str, timeout: int = 30) -> dict | list | None:
    if url in _cache:
        return _cache[url]
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, TimeoutError, OSError):
        data = None
    _cache[url] = data
    return data


def _title_match(a: str, b: str) -> float:
    """Token overlap between a claimed title and a resolved one, 0..1."""
    ta = {w for w in norm(a).split() if len(w) > 2}
    tb = {w for w in norm(b).split() if len(w) > 2}
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta)


def resolve_doi(doi: str, claimed_title: str) -> dict:
    doi = doi.strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    data = _get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto=aacrit@gmail.com")
    if not isinstance(data, dict) or data.get("status") != "ok":
        return {"resolves": False, "title": "", "match": 0.0, "type": ""}
    msg = data.get("message") or {}
    title = (msg.get("title") or [""])[0]
    if not title and msg.get("container-title"):
        title = (msg.get("container-title") or [""])[0]
    return {"resolves": True, "title": title, "match": _title_match(claimed_title, title),
            "type": str(msg.get("type") or "")}


def resolve_archive(url: str, claimed_title: str) -> dict:
    m = re.search(r"archive\.org/(?:details|stream|download)/([^/?#]+)", url or "")
    if not m:
        return {"live": False, "title": "", "match": 0.0}
    data = _get_json(f"https://archive.org/metadata/{m.group(1)}")
    if not isinstance(data, dict) or not data.get("metadata"):
        return {"live": False, "title": "", "match": 0.0}
    title = data["metadata"].get("title") or ""
    if isinstance(title, list):
        title = title[0] if title else ""
    return {"live": True, "title": str(title), "match": _title_match(claimed_title, str(title))}


def resolve_openlibrary(olid: str, claimed_title: str) -> dict:
    olid = olid.strip()
    kind = "books" if olid.endswith("M") else "works"
    data = _get_json(f"https://openlibrary.org/{kind}/{olid}.json")
    if not isinstance(data, dict) or not data.get("title"):
        return {"live": False, "title": "", "match": 0.0}
    return {"live": True, "title": str(data["title"]), "match": _title_match(claimed_title, str(data["title"]))}


TIER_GUESS = {
    "legal": "A", "document": "A", "archive": "A", "primary-source": "A", "primary": "A",
    "report": "A", "government-document": "A", "speech": "A", "collection": "A",
    "book": "B", "journal": "B", "chapter": "B", "study": "B", "investigation": "B",
    "encyclopedia": "C", "reference": "C",
    "ngo-report": "D", "article": "D", "film": "D", "documentary": "D", "other": "D",
}


def _slugify(s: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", fold(s).lower()).strip("-")
    return s[:n].rstrip("-") or "x"


def bootstrap(slug: str, resolve: bool = True, pause: float = 0.2) -> dict:
    """A first ledger.yaml from the event YAML: one entry per source and per
    excerpt, tier guessed from `type`, identifiers resolved live."""
    ev = yaml.safe_load((EVENTS / f"{slug}.yaml").read_text(encoding="utf-8"))
    today = dt.date.today().isoformat()
    entries: list[dict] = []
    seen: set[str] = set()
    for p in ev.get("perspectives") or []:
        for s in p.get("sources") or []:
            title = str(s.get("title") or "")
            author = str(s.get("author") or "")
            key = norm(title)
            if key in seen:
                continue
            seen.add(key)
            sid = f"src-{_slugify(author.split(',')[0].split()[-1] if author else 'anon', 14)}-{_slugify(title, 24)}"
            ids = {"isbn": None, "doi": s.get("doi"), "archive_org": None,
                   "hathitrust": None, "url": None}
            arch = s.get("archive_url")
            m = re.search(r"archive\.org/(?:details|stream)/([^/?#]+)", arch or "")
            if m:
                ids["archive_org"] = m.group(1)
            if s.get("openlibrary"):
                ids["openlibrary"] = s["openlibrary"]
            access = {"free_copy": None, "verified_at": None, "verified_by": None,
                      "verified_title": None, "status": "unverified"}
            if resolve:
                if s.get("doi"):
                    r = resolve_doi(str(s["doi"]), title)
                    if r["resolves"] and r["match"] >= 0.6:
                        access.update(verified_at=today, verified_by="crossref-title-match",
                                      verified_title=r["title"], status="verified")
                    elif r["resolves"]:
                        access["status"] = f"doi points at a different work: {r['title'][:80]}"
                    else:
                        access["status"] = "doi does not resolve"
                    time.sleep(pause)
                if access["status"] == "unverified" and arch:
                    r = resolve_archive(arch, title)
                    if r["live"] and r["match"] >= 0.5:
                        access.update(free_copy=arch, verified_at=today, verified_by="archive-item-fetch",
                                      verified_title=r["title"], status="verified")
                    elif r["live"]:
                        access["status"] = f"archive item is a different work: {r['title'][:80]}"
                    else:
                        access["status"] = "archive item is dead"
                    time.sleep(pause)
                if access["status"] == "unverified" and s.get("openlibrary"):
                    r = resolve_openlibrary(str(s["openlibrary"]), title)
                    if r["live"] and r["match"] >= 0.6:
                        access.update(verified_at=today, verified_by="openlibrary-record",
                                      verified_title=r["title"], status="verified")
                    time.sleep(pause)
            entries.append({
                "id": sid, "tier": TIER_GUESS.get(str(s.get("type")), "D"),
                "kind": "monograph" if s.get("type") == "book" else "primary-document",
                "author": author, "title": title, "container": None, "publisher": None,
                "place": None, "year": s.get("year"), "edition": None, "volume": None,
                "identifiers": ids, "access": access,
                "language": "en", "region_of_authorship": p.get("region_origin") or "global",
                "position": None,
                "from_yaml": f"perspectives[{(ev.get('perspectives') or []).index(p)}].sources",
            })
    for i, x in enumerate(ev.get("primary_source_excerpts") or []):
        entries.append({
            "id": f"src-excerpt-{i + 1}-{_slugify(str(x.get('work') or ''), 24)}",
            "tier": "A", "kind": "primary-document",
            "author": x.get("author"), "title": x.get("work"), "container": None,
            "publisher": None, "place": None, "year": x.get("date"), "edition": None,
            "volume": None,
            "identifiers": {"isbn": None, "doi": None, "archive_org": None, "hathitrust": None,
                            "url": x.get("url")},
            "access": {"free_copy": None, "verified_at": None, "verified_by": None,
                       "verified_title": None, "status": "unverified"},
            "language": "en", "region_of_authorship": "global", "position": None,
            "from_yaml": f"primary_source_excerpts[{i}]",
            "yaml_text": x.get("text"),
        })
    return {"slug": slug, "bootstrapped": today, "entries": entries,
            "positions": [], "contested": [], "exhibits": [], "analyses": []}


# ----------------------------------------------------------------- report

REPORT_COLUMNS = [
    "Event", "Slug", "Sources", "Kind A", "Kind B", "Kind C", "Kind D",
    "With identifier", "DOIs", "DOI resolves", "DOI title matches", "DOI other work",
    "Archive links", "Archive live", "Broken identifiers", "Verifiable",
    "Excerpts", "Excerpts with URL", "Media", "Stock media",
    "Ledger", "Ledger entries", "Tier A pinned", "Tier B verified", "Tier B pinned",
    "Positions", "Regional", "Exhibits", "Analyses", "Extracts",
    "Bar A", "Bar B", "Bar positions", "Bar regional", "Bar exhibits", "Bar analyses",
    "Thesis", "Report date",
]


def event_row(slug: str, resolve: bool, pause: float = 0.2) -> dict:
    ev = yaml.safe_load((EVENTS / f"{slug}.yaml").read_text(encoding="utf-8"))
    sources = [s for p in (ev.get("perspectives") or []) for s in (p.get("sources") or [])]
    kinds = {t: 0 for t in TIERS}
    for s in sources:
        kinds[TIER_GUESS.get(str(s.get("type")), "D")] += 1
    with_id = sum(1 for s in sources if s.get("doi") or s.get("archive_url") or s.get("openlibrary"))
    dois = [s for s in sources if s.get("doi")]
    arch = [s for s in sources if s.get("archive_url")]
    doi_res = doi_match = doi_other = arch_live = 0
    verifiable = 0
    if resolve:
        for s in sources:
            ok = False
            if s.get("doi"):
                r = resolve_doi(str(s["doi"]), str(s.get("title") or ""))
                if r["resolves"]:
                    doi_res += 1
                    if r["match"] >= 0.6:
                        doi_match += 1
                        ok = True
                    else:
                        doi_other += 1
                time.sleep(pause)
            if s.get("archive_url"):
                r = resolve_archive(str(s["archive_url"]), str(s.get("title") or ""))
                if r["live"]:
                    arch_live += 1
                    ok = True
                time.sleep(pause)
            verifiable += 1 if ok else 0
    broken = (len(dois) - doi_match) + (len(arch) - arch_live) if resolve else ""
    excerpts = ev.get("primary_source_excerpts") or []
    media = ev.get("media") or []
    stock = sum(1 for m in media if any(h in str(m.get("source_url") or "") for h in STOCK_HOSTS))

    row = {
        "Event": ev.get("title") or slug, "Slug": slug, "Sources": len(sources),
        "Kind A": kinds["A"], "Kind B": kinds["B"], "Kind C": kinds["C"], "Kind D": kinds["D"],
        "With identifier": with_id, "DOIs": len(dois),
        "DOI resolves": doi_res if resolve else "", "DOI title matches": doi_match if resolve else "",
        "DOI other work": doi_other if resolve else "",
        "Archive links": len(arch), "Archive live": arch_live if resolve else "",
        "Broken identifiers": broken, "Verifiable": verifiable if resolve else "",
        "Excerpts": len(excerpts), "Excerpts with URL": sum(1 for x in excerpts if x.get("url")),
        "Media": len(media), "Stock media": stock,
        "Ledger": "none", "Ledger entries": 0, "Tier A pinned": 0, "Tier B verified": 0,
        "Tier B pinned": 0, "Positions": 0, "Regional": 0, "Exhibits": 0, "Analyses": 0,
        "Extracts": 0, "Bar A": "", "Bar B": "", "Bar positions": "", "Bar regional": "",
        "Bar exhibits": "", "Bar analyses": "", "Thesis": "none",
        "Report date": dt.date.today().isoformat(),
    }
    if (EVIDENCE / slug / "ledger.yaml").exists():
        led = load_ledger(slug)
        st = standing(led, ev)
        row.update({
            "Ledger": "yes", "Ledger entries": len(led.entries),
            "Tier A pinned": st["tier_a_with_extract"], "Tier B verified": st["tier_b_verified"],
            "Tier B pinned": st["tier_b_pinned"], "Positions": st["positions"],
            "Regional": st["regional"], "Exhibits": st["exhibits"], "Analyses": st["analyses"],
            "Extracts": st["extracts"],
            "Bar A": "ok" if st["bar"]["tier_a"] else "below",
            "Bar B": "ok" if st["bar"]["tier_b"] else "below",
            "Bar positions": "ok" if st["bar"]["positions"] else "below",
            "Bar regional": "ok" if st["bar"]["regional"] else "below",
            "Bar exhibits": "ok" if st["bar"]["exhibits"] else "below",
            "Bar analyses": "ok" if st["bar"]["analyses"] else "below",
        })
    tp = THESES / f"{slug}.md"
    if tp.exists():
        m = re.search(r"^status:\s*(\w+)", tp.read_text(encoding="utf-8"), re.M)
        row["Thesis"] = m.group(1) if m else "unknown"
    return row


def write_report(resolve: bool, out: pathlib.Path = REPORT, pause: float = 0.2) -> list[dict]:
    rows = []
    for p in sorted(EVENTS.glob("*.yaml")):
        rows.append(event_row(p.stem, resolve, pause))
        print(f"  {p.stem}: {rows[-1]['Sources']} sources, verifiable {rows[-1]['Verifiable']}",
              file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=REPORT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return rows


# --------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    cmd, rest = argv[0], argv[1:]
    resolve = "--no-resolve" not in rest
    rest = [a for a in rest if a != "--no-resolve"]
    if cmd == "validate":
        led = load_ledger(rest[0])
        findings = validate_ledger(led)
        ev = yaml.safe_load((EVENTS / f"{rest[0]}.yaml").read_text(encoding="utf-8"))
        st = standing(led, ev)
        for f in findings:
            print(f"{f.level.upper():4} {f.id} {f.where}: {f.detail}")
        print(json.dumps(st, indent=1))
        return 1 if any(f.level == "fail" for f in findings) else 0
    if cmd == "bootstrap":
        slug = rest[0]
        led = bootstrap(slug, resolve=resolve)
        outdir = EVIDENCE / slug
        outdir.mkdir(parents=True, exist_ok=True)
        target = outdir / "ledger.yaml"
        if target.exists():
            target = outdir / "ledger.bootstrap.yaml"
        target.write_text(yaml.safe_dump(led, sort_keys=False, allow_unicode=True), encoding="utf-8")
        ver = sum(1 for e in led["entries"] if e["access"].get("status") == "verified")
        print(f"{target}: {len(led['entries'])} entries, {ver} verified")
        return 0
    if cmd == "report":
        out = REPORT
        if "--out" in rest:
            out = pathlib.Path(rest[rest.index("--out") + 1])
        rows = write_report(resolve, out)
        print(f"{out}: {len(rows)} events")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
