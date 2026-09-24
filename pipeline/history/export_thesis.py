"""Export a History thesis to the JSON the event page reads at build time.

    python3 -m pipeline.history.export_thesis [slug ...] [--include-drafts]

Reads `data/history/theses/<slug>.md` and `data/history/evidence/<slug>/`,
resolves every marker, numbers the notes and the exhibits, pulls episode
chapters from the script export, and writes
`frontend/build-data/history-theses/<slug>.json`. A thesis whose front
matter is not `published` is not exported (the route renders the Hearing)
unless `--include-drafts` is passed for a local preview; the frontend reader
renders a draft only when NEXT_PUBLIC_HISTORY_DRAFTS is set, so a preview
export cannot reach the served site by accident.

The exporter validates first and refuses to write a thesis with a failing
check. The served JSON is therefore never ahead of the gates.

Honours VOID_EXPORT_BUILD_DIR, as tests/test_history_export_parity.py expects
of the script exporter.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.history.ledger import (  # noqa: E402
    EVENTS, EVIDENCE, THESES, Ledger, compute_analysis, entry_is_verified,
    load_ledger, locator_label, standing,
)
from pipeline.history.thesis_format import (  # noqa: E402
    Directive, Paragraph, Thesis, chapter_segments, parse_thesis,
)
from pipeline.history.thesis_checks import validate_thesis  # noqa: E402

BUILD_DIR = pathlib.Path(os.environ.get("VOID_EXPORT_BUILD_DIR") or (ROOT / "frontend/build-data"))
OUT = BUILD_DIR / "history-theses"
PUBLIC_DIR = pathlib.Path(os.environ.get("VOID_EXPORT_PUBLIC_DIR") or (ROOT / "frontend/public/data"))
SCRIPTS = ROOT / "frontend/build-data/history-scripts"
MANIFEST = ROOT / "frontend/public/data/history-audio.json"

POSITION_COLORS = ["a", "b", "c", "d", "e", "f"]
TIER_NAMES = {"A": "Primary record", "B": "Peer-reviewed scholarship",
              "C": "Reference", "D": "Positional"}
VERDICT_LABEL = {"supported": "Supported", "contradicted": "Contradicted",
                 "qualified": "Qualified", "untestable": "Cannot be tested from the free record"}


def load_inputs(slug: str):
    event = yaml.safe_load((EVENTS / f"{slug}.yaml").read_text(encoding="utf-8"))
    ledger = load_ledger(slug)
    thesis = parse_thesis((THESES / f"{slug}.md").read_text(encoding="utf-8"), slug)
    script = None
    sp = SCRIPTS / f"{slug}.json"
    if sp.exists():
        script = json.loads(sp.read_text(encoding="utf-8"))
    episode = None
    if MANIFEST.exists():
        episode = (json.loads(MANIFEST.read_text(encoding="utf-8")).get("episodes") or {}).get(slug)
    return event, ledger, thesis, script, episode


# --------------------------------------------------------------- citations

def _authors_short(e: dict) -> str:
    a = str(e.get("author") or "")
    return a


def short_cite(e: dict) -> str:
    """The note form: author, short title, year."""
    title = str(e.get("title") or "")
    short = title.split(":")[0].strip()
    if len(short) > 60:
        short = short[:57].rsplit(" ", 1)[0] + "..."
    year = str(e.get("year") or "")
    # "Resolution 819 (1993)" already carries its year; do not print it twice.
    if year and year in short:
        return f"{_authors_short(e)}, {short}"
    return f"{_authors_short(e)}, {short} ({year})"


def full_cite(e: dict) -> str:
    parts = [str(e.get("author") or ""), str(e.get("title") or "")]
    if e.get("container"):
        parts.append(f"in {e['container']}")
    if e.get("volume"):
        parts.append(f"vol. {e['volume']}")
    if e.get("edition"):
        parts.append(str(e["edition"]))
    place_pub = ", ".join(str(x) for x in (e.get("place"), e.get("publisher")) if x)
    if place_pub:
        parts.append(place_pub)
    if e.get("year"):
        parts.append(str(e["year"]))
    if e.get("document_number"):
        parts.append(str(e["document_number"]))
    return ". ".join(p.strip().rstrip(".") for p in parts if p) + "."


# ------------------------------------------------------------------ export

class Exporter:
    def __init__(self, slug: str, event: dict, ledger: Ledger, thesis: Thesis,
                 script: dict | None, episode: dict | None):
        self.slug = slug
        self.event = event
        self.ledger = ledger
        self.thesis = thesis
        self.script = script
        self.episode = episode
        self.notes: list[dict] = []
        self.exhibits: list[dict] = []
        self.exhibit_by_key: dict[str, int] = {}
        self.position_color: dict[str, str] = {}
        for i, pid in enumerate(ledger.positions):
            self.position_color[pid] = POSITION_COLORS[i % len(POSITION_COLORS)]

    # -- notes
    def note(self, src: str, loc: str) -> int:
        e = self.ledger.entries[src]
        n = len(self.notes) + 1
        key = f"{src}.{loc}" if loc else src
        self.notes.append({
            "n": n, "source": src, "locator": loc or None, "inText": self._in_text,
            "locatorLabel": locator_label(loc) if loc else None,
            "short": short_cite(e) + (f", {locator_label(loc)}" if loc else ""),
            "exhibit": self.exhibit_by_key.get(key),
            "freeCopy": (e.get("access") or {}).get("free_copy"),
        })
        return n

    _in_text = False

    def sentence(self, sen) -> dict:
        self._in_text = True
        try:
            return {
                "text": sen.text,
                "notes": [self.note(src, loc) for src, loc in sen.markers],
                "interpretive": sen.interpretive,
            }
        finally:
            self._in_text = False

    # -- extracts
    def extract_ref(self, ref: str) -> dict:
        src, _, loc = ref.partition(".")
        e = self.ledger.entries[src]
        ex = self.ledger.extract(src, loc)
        r = self.ledger.rendering(src, loc)
        return {
            "source": src, "locator": loc, "locatorLabel": locator_label(loc),
            "short": short_cite(e), "producer": e.get("producer"),
            "text": ex.text if ex else "", "language": e.get("language") or "en",
            "rendering": ({"kind": r.kind, "text": r.text} if r else None),
            "freeCopy": (e.get("access") or {}).get("free_copy"),
            "url": ex.url if ex else None,
            "exhibit": self.exhibit_by_key.get(ref),
        }

    # -- blocks
    def exhibit_block(self, d: Directive) -> dict:
        ref = d.args["ref"]
        n = len(self.exhibits) + 1
        if ref in self.ledger.exhibits:
            x = self.ledger.exhibits[ref]
            blk = {
                "t": "exhibit", "n": n, "id": ref, "kind": x.get("kind"), "title": x.get("title"),
                "creator": x.get("creator"), "date": x.get("date"), "repository": x.get("repository"),
                "accession": x.get("accession"), "licence": x.get("licence"), "url": x.get("url"),
                "image": x.get("image") or None, "shows": x.get("shows"), "doesNotShow": x.get("does_not_show"),
                "text": None, "source": x.get("source"), "locator": x.get("locator"),
            }
            if x.get("kind") == "document" and x.get("source"):
                blk.update(self.extract_ref(f"{x['source']}.{x['locator']}"))
                blk["t"] = "exhibit"
                blk["n"] = n
            self.exhibit_by_key[ref] = n
        else:
            loc = d.args["locator"]
            e = self.ledger.entries[ref]
            ex = self.ledger.extract(ref, loc)
            r = self.ledger.rendering(ref, loc)
            blk = {
                "t": "exhibit", "n": n, "id": f"{ref}.{loc}", "kind": "document",
                "title": str(e.get("title")), "creator": str(e.get("author")), "date": str(e.get("year")),
                "repository": e.get("repository") or e.get("publisher") or e.get("producer"),
                "accession": e.get("document_number") or (e.get("identifiers") or {}).get("url") or "",
                "licence": e.get("rights") or "", "url": (e.get("access") or {}).get("free_copy"),
                "image": None, "shows": None, "doesNotShow": None,
                "text": ex.text if ex else "", "language": e.get("language") or "en",
                "rendering": ({"kind": r.kind, "text": r.text} if r else None),
                "source": ref, "locator": loc, "locatorLabel": locator_label(loc),
                "producer": e.get("producer"), "short": short_cite(e),
                "notes": ex.notes if ex else [],
            }
            self.exhibit_by_key[f"{ref}.{loc}"] = n
        self.exhibits.append({k: blk[k] for k in ("n", "id", "kind", "title") if k in blk})
        return blk

    def episode_block(self, d: Directive) -> dict:
        n = d.args["chapter"]
        chapters = chapter_segments(self.script) if self.script else []
        seg = chapters[n]
        lines = [l for l in seg.get("lines") or [] if (l.get("text") or "").strip()]
        a, b = d.args.get("lines", (1, len(lines)))
        chosen = lines[a - 1:b]
        manifest = (self.episode or {}).get("chapters") or []
        start = manifest[n]["startTime"] if n < len(manifest) else None
        title = seg.get("title") or {"OPEN": "Opening", "TURN": "The disagreement",
                                     "CLOSE": "Legacy"}.get(seg.get("kind"), "")
        return {
            "t": "episode", "chapter": n, "title": title, "kind": str(seg.get("kind")).lower(),
            "lines": [{"speaker": l.get("speaker") or "N", "text": l.get("text")} for l in chosen],
            "startTime": start,
        }

    def position_block(self, d: Directive) -> dict:
        pid = d.args["id"]
        pos = self.ledger.positions[pid]
        rests = []
        for src in pos.get("rests_on") or []:
            e = self.ledger.entries.get(src) or {}
            rests.append({"source": src, "short": short_cite(e), "tier": e.get("tier"),
                          "verified": entry_is_verified(e),
                          "freeCopy": (e.get("access") or {}).get("free_copy"),
                          "byHolder": str(e.get("position") or "") == pid})
        adjs = []
        for a in pos.get("adjudications") or []:
            producers = sorted(self.ledger.producers_of(a.get("rests_on") or []))
            adjs.append({
                "claim": a.get("claim"), "verdict": a.get("verdict"),
                "verdictLabel": VERDICT_LABEL.get(a.get("verdict"), a.get("verdict")),
                "basis": a.get("basis"), "reasoning": a.get("reasoning"),
                "producers": producers,
                "oneSided": len(producers) < 2,
                "restsOn": [self.extract_ref(r) for r in (a.get("rests_on") or [])],
            })
        return {
            "t": "position", "id": pid, "name": pos.get("name"),
            "color": self.position_color.get(pid, "a"),
            "holders": list(pos.get("holders") or []), "restsOn": rests,
            "claim": pos.get("claim"), "omits": pos.get("omits"),
            "adjudications": adjs,
        }

    def contested_block(self, d: Directive) -> dict:
        cid = d.args["id"]
        c = self.ledger.contested[cid]
        rows = []
        for r in c.get("rows") or []:
            src = str(r.get("source"))
            e = self.ledger.entries.get(src) or {}
            loc = str(r.get("locator") or "")
            rows.append({
                "position": r.get("position"),
                "positionName": (self.ledger.positions.get(r.get("position")) or {}).get("name"),
                "color": self.position_color.get(r.get("position"), "a"),
                "holds": r.get("holds"), "figures": [str(f) for f in (r.get("figures") or [])],
                "source": src, "short": short_cite(e) + (f", {locator_label(loc)}" if loc else ""),
                "locator": loc or None, "freeCopy": (e.get("access") or {}).get("free_copy"),
                "note": self.note(src, loc),
            })
        return {"t": "contested", "id": cid, "claim": c.get("claim"), "rows": rows}

    def analysis_block(self, d: Directive) -> dict:
        aid = d.args["id"]
        a = self.ledger.analyses[aid]
        got, how = compute_analysis(a)
        der = a.get("derivation") or {}
        cols = list(der.get("columns") or [])
        rows = []
        for r in der.get("rows") or []:
            ref = str(r.get("extract"))
            rows.append({
                "cells": {k: r.get(k) for k in r if k != "extract"},
                "extract": ref, "note": self.note(*ref.partition(".")[::2]),
                "short": short_cite(self.ledger.entries[ref.partition(".")[0]]),
                "locatorLabel": locator_label(ref.partition(".")[2]),
            })
        if not cols and rows:
            cols = [k for k in rows[0]["cells"]]
        return {
            "t": "analysis", "id": aid, "title": a.get("title"), "method": a.get("method"),
            "finding": a.get("finding"), "confidence": a.get("confidence"),
            "against": a.get("against"), "result": a.get("result"),
            "compute": how, "columns": cols, "rows": rows,
        }

    def section(self, sec) -> dict:
        blocks = []
        for b in sec.blocks:
            if isinstance(b, Paragraph):
                if b.kind == "list-item":
                    if blocks and blocks[-1]["t"] == "list":
                        target = blocks[-1]
                    else:
                        target = {"t": "list", "items": []}
                        blocks.append(target)
                    target["items"].append({
                        "sentences": [self.sentence(s) for s in b.sentences],
                        "against": b.against,
                        "againstName": (self.ledger.positions.get(b.against) or {}).get("name") if b.against else None,
                        "color": self.position_color.get(b.against) if b.against else None,
                    })
                else:
                    blocks.append({"t": "para", "sentences": [self.sentence(s) for s in b.sentences]})
            elif isinstance(b, Directive):
                blocks.append({
                    "exhibit": self.exhibit_block, "episode": self.episode_block,
                    "position": self.position_block, "contested": self.contested_block,
                    "analysis": self.analysis_block,
                }[b.kind](b))
        return {"id": sec.id, "kind": sec.kind, "level": sec.level, "title": sec.title,
                "number": sec.number, "blocks": blocks}

    def sources(self) -> list[dict]:
        out = []
        for tier in ("A", "B", "C", "D"):
            entries = [e for e in self.ledger.entries.values()
                       if e.get("tier") == tier and entry_is_verified(e)]
            if not entries:
                continue
            out.append({
                "tier": tier, "name": TIER_NAMES[tier],
                "entries": [{
                    "id": e["id"], "citation": full_cite(e), "kind": e.get("kind"),
                    "language": e.get("language"), "producer": e.get("producer"),
                    "freeCopy": (e.get("access") or {}).get("free_copy"),
                    "verifiedAt": (e.get("access") or {}).get("verified_at"),
                    "verifiedBy": (e.get("access") or {}).get("verified_by"),
                    "pinned": bool(self.ledger.extracts_of(e["id"])),
                    "position": e.get("position"),
                } for e in sorted(entries, key=lambda e: str(e.get("author") or ""))],
            })
        return out

    def run(self) -> dict:
        th = self.thesis
        # Exhibits are numbered in document order, and a note must know its
        # exhibit's number, so the exhibits are placed before the notes are.
        counter = 0
        for sec in th.sections:
            for d in sec.directives:
                if d.kind == "exhibit":
                    ref = d.args["ref"]
                    key = ref if ref in self.ledger.exhibits else f"{ref}.{d.args.get('locator')}"
                    if key not in self.exhibit_by_key:
                        counter += 1
                        self.exhibit_by_key[key] = counter
                    x = self.ledger.exhibits.get(ref)
                    if x and x.get("kind") == "document" and x.get("source"):
                        # A note on the same passage links to the exhibit; the
                        # alias shares the number rather than taking one.
                        self.exhibit_by_key.setdefault(f"{x['source']}.{x['locator']}", self.exhibit_by_key[key])
        self.exhibits = []
        sections = [self.section(s) for s in th.sections]
        st = standing(self.ledger, self.event)
        gaps = []
        for g in self.ledger.gaps:
            e = self.ledger.entries.get(str(g.get("entry")) or "") or {}
            gaps.append({"entry": g.get("entry"), "short": short_cite(e) if e else None,
                         "what": g.get("what"), "tried": list(g.get("tried") or []),
                         "status": g.get("status")})
        marks = []
        for sec in sections:
            for b in sec["blocks"]:
                if b["t"] == "episode":
                    marks.append({"chapter": b["chapter"], "where": sec["id"], "startTime": b["startTime"]})
        return {
            "slug": self.slug,
            "status": th.status,
            "auditedBy": th.front.get("audited_by"),
            "auditedAt": str(th.front.get("audited_at") or "") or None,
            "question": th.front.get("question"),
            "claims": list(th.front.get("claims") or []),
            "regionalSourcesNote": th.front.get("regional_sources_note"),
            "sections": sections,
            "notes": self.notes,
            "exhibits": self.exhibits,
            "sources": self.sources(),
            "standing": {k: v for k, v in st.items() if k != "bar"},
            "bar": st["bar"],
            "gaps": gaps,
            "episodeMarks": marks,
            "words": sum(len(sen.text.split()) for _, _, sen in th.all_sentences),
        }


def export(slug: str) -> tuple[dict, list]:
    event, ledger, thesis, script, episode = load_inputs(slug)
    findings = [f for f in validate_thesis(thesis, ledger, event, script, episode) if f.level == "fail"]
    blob = Exporter(slug, event, ledger, thesis, script, episode).run()
    return blob, findings


def main(argv: list[str]) -> int:
    include_drafts = "--include-drafts" in argv
    slugs = [a for a in argv if not a.startswith("--")] or sorted(p.stem for p in THESES.glob("*.md"))
    OUT.mkdir(parents=True, exist_ok=True)
    rc = 0
    written = 0
    for slug in slugs:
        blob, findings = export(slug)
        if findings:
            print(f"{slug}: {len(findings)} failing check(s); not exported")
            for f in findings[:40]:
                print(f"  {f.id} {f.where}: {f.detail}")
            rc = 1
            continue
        if blob["status"] != "published" and not include_drafts:
            print(f"{slug}: status {blob['status']}; not exported (the route renders the Hearing)")
            stale = OUT / f"{slug}.json"
            if stale.exists():
                stale.unlink()
                print(f"  removed stale {stale}")
            continue
        # YAML hands dates back as date objects; the page wants the ISO string.
        (OUT / f"{slug}.json").write_text(json.dumps(blob, ensure_ascii=False, default=str), encoding="utf-8")
        written += 1
        print(f"{slug}: {blob['status']}, {len(blob['notes'])} notes, {len(blob['exhibits'])} exhibits, "
              f"{blob['words']} words -> {OUT / (slug + '.json')}")
    # The served index: which events are theses, with the counts the served
    # gates (scripts/verify_sections.py TH-01..TH-04) check the page against.
    index = []
    for p in sorted(OUT.glob("*.json")):
        blob = json.loads(p.read_text(encoding="utf-8"))
        if blob.get("status") != "published":
            continue
        index.append({"slug": blob["slug"], "notes": len(blob.get("notes") or []),
                      "exhibits": len(blob.get("exhibits") or []),
                      "question": blob.get("question"), "auditedAt": blob.get("auditedAt")})
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    (PUBLIC_DIR / "history-theses.json").write_text(
        json.dumps({"count": len(index), "theses": index}, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"history-theses/: {written} file(s); index lists {len(index)} published")
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
