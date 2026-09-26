"""The rigor controls on a History thesis: T-01..T-21 (proposal §9, CEO rules
of 2026-09-24). Each returns Findings; `validate_thesis` runs them all, the
ledger's own L-xx checks included, because a thesis is only as sound as the
ledger it cites.

  T-01  a marker whose id is not in the ledger, or whose locator names no
        stored extract when the sentence holds a quote or a number
  T-02  a sentence in The record, The argument, The historiography or Omits
        with no marker and no {i}; an {i} sentence carrying a numeral or a
        quotation; a paragraph that is all {i}
  T-03  a numeral in a cited sentence absent from every cited extract
  T-04  a quoted span not a substring, under _norm, of a cited extract or of
        an OFFICIAL parallel rendering of one; a Void translation never
        satisfies a quotation (CEO, non-English sources)
  T-05  a cited entry not verified, a verified_title that is another work, a
        pinned locator on an entry with no free copy
  T-06  a spelled-out year or a cardinal from ten up outside a quotation; an
        em or en dash; a straight double quote; a kill-list word; the
        time-relative and hedge shapes test_history_copy.py gates
  T-07  fewer than 3 positions; a position with no verified source by a
        holder; a position over twice the words of the shortest; every Tier B
        source from one region; every position resting on one language
  T-08  a contested claim with fewer than 2 positions, or two positions
        sharing a source; a contested figure stated alone in the body
  T-09  an exhibit missing provenance; a stock domain anywhere in the media
  T-10  an episode mark whose chapter is not in the script or the manifest, or
        whose lines are not the script's; a section that is only an episode
  T-11  an Omits statement that names an entry or an author the ledger holds
  T-12  an entry from an excluded host or kind; a Tier C or D entry cited on a
        number or a quote
  T-13  `published` below the bar of §4e (plus at least one analysis)
  T-14  the served JSON differing from the thesis (tests/test_history_thesis.py)
  T-15  a position with no adjudication resting on a Tier A extract
  T-16  an analysis whose derivation does not resolve or recompute (L-10, L-11)
  T-17  a verdict of `contradicted` on one producer's record (L-13, RULE A)
  T-18  absence of evidence read as contradiction, or a gap left unsaid
        (L-12, L-14, RULE B)
  T-19  a rendering that loses a number or a name of its original (L-15)
  T-20  a Void translation presented as a published quotation (in T-04)
  T-21  a holistic thesis (front matter `scope: holistic`, §15) whose
        coverage map does not hold: a required strand (causes, course,
        actors, regions, consequences, legacy) missing, a strand with no
        section in The event, a strand below its floor of sourced sentences,
        a listed section that contributes none, an actor or region the
        strand names that no sourced sentence in its sections carries, an
        event-YAML perspective with no entry, a perspective whose position
        is not on the page or whose own sources are heard fewer than twice in
        its sections, an event section no strand claims, too few event
        sections or contested questions, an unknown scope
"""
from __future__ import annotations

import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.history.ledger import (  # noqa: E402
    EXCLUDED_HOSTS, EXCLUDED_KINDS, STOCK_HOSTS, Finding, Ledger, _numbers,
    _title_match, entry_is_verified, norm, standing, validate_ledger,
)
from pipeline.history.thesis_format import (  # noqa: E402
    Directive, Paragraph, Section, Thesis, chapter_segments, segment_chapters, slugify, strip_inline,
)
from pipeline.history.copy_rules import (  # noqa: E402
    EM, EN, hedge_hits, outside_quotations, time_relative_hits,
)
from pipeline.utils.prohibited_terms import find_prohibited  # noqa: E402

CITED_KINDS = ("event", "event-section", "record", "argument-section", "historiography", "contested", "other")
BODY_KINDS = ("question", "event", "event-section", "record", "argument-section")

# §15, the holistic scope (CEO 2026-09-25). The numbers are floors, not
# targets: a strand that clears six sourced sentences in two sections is
# covered; one that names a section to look covered and says nothing there
# is not.
SCOPES = ("question", "holistic")
HOLISTIC_STRANDS = ("causes", "course", "actors", "regions", "consequences", "legacy")
TERM_STRANDS = ("actors", "regions")
COVERAGE_MIN_SENTENCES = 6
COVERAGE_MIN_TERMS = 3
PERSPECTIVE_MIN_SENTENCES = 2
HOLISTIC_MIN_EVENT_SECTIONS = 5
HOLISTIC_MIN_QUESTIONS = 3
WORD_CEILING = 8000
WORD_CEILING_HOLISTIC = 12000

_WORD_NUMBER = re.compile(
    r"\b(?:ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|"
    r"million|billion|dozen)\b", re.I)
_MAX_POSITION_RATIO = 2.0


def _fail(out: list[Finding], code: str, where: str, detail: str) -> None:
    out.append(Finding(code, "fail", where, detail))


def _where(sec: Section, sen=None) -> str:
    base = sec.id
    return f"{base} line {sen.line}" if sen is not None else base


def _cited_texts(ledger: Ledger, markers) -> tuple[list[str], list[str], list[str]]:
    """(extract texts, official parallel texts, void translation texts) behind
    a sentence's markers."""
    ex, official, void = [], [], []
    for src, loc in markers:
        if not loc:
            continue
        e = ledger.extract(src, loc)
        if e is None:
            continue
        ex.append(e.text)
        r = ledger.rendering(src, loc)
        if r is not None:
            (official if r.kind == "official-parallel" else void).append(r.text)
    return ex, official, void


# ------------------------------------------------------------------ checks

def check_markers(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-01, T-05, T-12."""
    for sec, _, sen in th.all_sentences:
        loaded = sen.quotes or sen.numerals
        has_extract = False
        for src, loc in sen.markers:
            e = ledger.entries.get(src)
            if e is None:
                _fail(out, "T-01", _where(sec, sen), f"marker cites unknown entry {src}")
                continue
            if loc:
                if ledger.extract(src, loc) is None:
                    _fail(out, "T-01", _where(sec, sen), f"locator {src}.{loc} names no stored extract")
                else:
                    has_extract = True
                if not (e.get("access") or {}).get("free_copy"):
                    _fail(out, "T-05", _where(sec, sen), f"pinned locator on {src}, which has no free copy")
            if not entry_is_verified(e):
                _fail(out, "T-05", _where(sec, sen), f"{src} is cited but not verified")
            else:
                vt = str((e.get("access") or {}).get("verified_title") or "")
                if _title_match(str(e.get("title") or ""), vt) < 0.5 and _title_match(vt, str(e.get("title") or "")) < 0.5:
                    _fail(out, "T-05", _where(sec, sen), f"{src}: verified_title {vt[:60]!r} is not its title")
            ids = e.get("identifiers") or {}
            url = str(ids.get("url") or (e.get("access") or {}).get("free_copy") or "")
            if any(h in url for h in EXCLUDED_HOSTS) or str(e.get("kind")) in EXCLUDED_KINDS:
                _fail(out, "T-12", _where(sec, sen), f"{src} is an excluded source ({e.get('kind')}, {url[:50]})")
            # A Tier C or D entry may carry a number or a quotation only in
            # the historiography, where it is a labelled position speaking in
            # its own words (§4a); in the record or the argument it would be
            # a fact, and it may not be one.
            if loaded and e.get("tier") in ("C", "D") and sec.kind != "historiography":
                _fail(out, "T-12", _where(sec, sen), f"Tier {e.get('tier')} entry {src} cited on a number or a quote outside the historiography")
        if loaded and sen.markers and not has_extract:
            _fail(out, "T-01", _where(sec, sen), "a sentence with a quote or a number cites no stored extract")


def check_sentences(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-02, T-03, T-04 (with T-20)."""
    for sec in th.sections:
        for para in sec.paragraphs:
            if sec.kind == "omits" and para.kind == "list-item":
                continue   # T-11 governs statements about the ledger
            if sec.kind in CITED_KINDS and para.sentences and all(s.interpretive for s in para.sentences):
                _fail(out, "T-02", _where(sec, para.sentences[0]), "a paragraph that is all interpretation")
            for sen in para.sentences:
                if sec.kind in CITED_KINDS and not sen.markers and not sen.interpretive:
                    _fail(out, "T-02", _where(sec, sen), f"no marker and no {{i}}: {sen.text[:70]!r}")
                if sen.interpretive and (sen.numerals or sen.quotes):
                    _fail(out, "T-02", _where(sec, sen), f"an {{i}} sentence carrying a number or a quotation: {sen.text[:70]!r}")
                if not sen.markers:
                    continue
                ex, official, void = _cited_texts(ledger, sen.markers)
                have = set()
                for t in ex + official:
                    have.update(_numbers(t))
                for n in sen.numerals:
                    key = re.sub(r"[,\s%]", "", n)
                    if key not in have:
                        _fail(out, "T-03", _where(sec, sen), f"{n!r} is in no cited extract")
                for q in sen.quotes:
                    nq = norm(strip_inline(q)).strip()
                    if any(nq in norm(t) for t in ex + official):
                        continue
                    if any(nq in norm(t) for t in void):
                        _fail(out, "T-20", _where(sec, sen), f"a Void translation presented as a quotation: {q[:60]!r}")
                    else:
                        _fail(out, "T-04", _where(sec, sen), f"quotation not in any cited extract: {q[:60]!r}")


def check_register(th: Thesis, out: list[Finding]) -> None:
    """T-06 on every paragraph and list item; directives carry no prose."""
    for sec in th.sections:
        for para in sec.paragraphs:
            raw = strip_inline(re.sub(r"\[\^[^\]]+\]|\{i\}", "", para.raw))
            if '"' in raw:
                _fail(out, "T-06", _where(sec, para.sentences[0] if para.sentences else None),
                      "a straight double quote; quotations use curly quotes")
            prose = outside_quotations(raw)
            if EM in prose or EN in prose:
                _fail(out, "T-06", _where(sec), f"a dash in prose: {prose[:70]!r}")
            m = _WORD_NUMBER.search(prose)
            if m:
                _fail(out, "T-06", _where(sec), f"a spelled-out number {m.group(0)!r} outside a quotation")
            for hit in find_prohibited(prose):
                _fail(out, "T-06", _where(sec), f"kill-list term {hit!r}")
            for label, snip in time_relative_hits(prose):
                _fail(out, "T-06", _where(sec), f"{label}: ...{snip}...")
            for hit in hedge_hits(prose):
                _fail(out, "T-06", _where(sec), f"hedge in place of attribution: {hit!r}")
    for k in ("question", "claims"):
        v = th.front.get(k)
        texts = v if isinstance(v, list) else [v]
        for t in texts:
            t = str(t or "")
            if EM in t or EN in t:
                _fail(out, "T-06", f"front matter {k}", "a dash")
            if _WORD_NUMBER.search(outside_quotations(t)):
                _fail(out, "T-06", f"front matter {k}", "a spelled-out number")


def check_positions(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-07, T-15."""
    used = [d.args["id"] for s in th.sections for d in s.directives if d.kind == "position"]
    if len(used) < 3:
        _fail(out, "T-07", "historiography", f"{len(used)} position block(s); the floor is 3")
    lengths: dict[str, int] = {}
    languages: set[str] = set()
    for pid in used:
        pos = ledger.positions.get(pid)
        if pos is None:
            _fail(out, "T-07", pid, "position block names no ledger position")
            continue
        holders_src = [s for s in (pos.get("rests_on") or [])
                       if str((ledger.entries.get(s) or {}).get("position") or "") == pid
                       and entry_is_verified(ledger.entries.get(s) or {})]
        if not holders_src:
            _fail(out, "T-07", pid, "no verified source by a holder of this position")
        for s in pos.get("rests_on") or []:
            languages.add(str((ledger.entries.get(s) or {}).get("language") or "en"))
        text = " ".join(str(pos.get(k) or "") for k in ("claim", "omits")) + " " + " ".join(map(str, pos.get("holders") or []))
        lengths[pid] = len(text.split())
        adjs = [a for a in (pos.get("adjudications") or [])
                if any(str((ledger.entries.get(str(r).partition(".")[0]) or {}).get("tier")) == "A"
                       and ledger.extract(*str(r).partition(".")[::2]) is not None
                       for r in (a.get("rests_on") or []))]
        if not adjs:
            _fail(out, "T-15", pid, "no adjudication resting on a Tier A extract")
    if lengths and max(lengths.values()) > _MAX_POSITION_RATIO * min(lengths.values()):
        longest = max(lengths, key=lengths.get)
        shortest = min(lengths, key=lengths.get)
        _fail(out, "T-07", longest, f"{lengths[longest]} words against {shortest}'s {lengths[shortest]}: over twice")
    tier_b = [e for e in ledger.entries.values() if e.get("tier") == "B"]
    regions = {str(e.get("region_of_authorship")) for e in tier_b}
    if len(tier_b) >= 2 and len(regions) < 2:
        _fail(out, "T-07", "ledger", f"every Tier B source is from one region ({regions.pop()})")
    if used and len(languages) < 2:
        _fail(out, "T-07", "ledger", f"every position rests on one language ({languages or {'en'}})")


def check_contested(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-08."""
    used = [d.args["id"] for s in th.sections for d in s.directives if d.kind == "contested"]
    body = [sen for sec, _, sen in th.all_sentences if sec.kind in BODY_KINDS]
    for cid in used:
        c = ledger.contested.get(cid)
        if c is None:
            _fail(out, "T-08", cid, "contested block names no ledger record")
            continue
        rows = c.get("rows") or []
        if len({r.get("position") for r in rows}) < 2:
            _fail(out, "T-08", cid, "fewer than 2 positions")
        seen: dict[str, str] = {}
        for r in rows:
            src = str(r.get("source"))
            if src in seen and seen[src] != r.get("position"):
                _fail(out, "T-08", cid, f"two positions share the source {src}")
            seen[src] = str(r.get("position"))
        figures = {re.sub(r"[,\s]", "", str(f)) for r in rows for f in (r.get("figures") or []) if f}
        if not figures:
            continue
        for sen in body:
            present = {re.sub(r"[,\s%]", "", n) for n in sen.numerals} & figures
            if len(present) == 1:
                _fail(out, "T-08", f"body line {sen.line}", f"contested figure {present.pop()} stated alone; point at the disagreement")


def check_exhibits(th: Thesis, ledger: Ledger, event: dict, out: list[Finding]) -> None:
    """T-09."""
    for sec in th.sections:
        for d in sec.directives:
            if d.kind != "exhibit":
                continue
            ref = d.args["ref"]
            if ref in ledger.exhibits:
                x = ledger.exhibits[ref]
                for k in ("creator", "date", "repository", "accession", "licence", "url"):
                    if not x.get(k):
                        _fail(out, "T-09", ref, f"exhibit lacks {k}")
                if x.get("kind") in ("image", "map") and not (x.get("shows") and x.get("does_not_show")):
                    _fail(out, "T-09", ref, "image exhibit lacks shows / does_not_show")
            elif ref in ledger.entries:
                loc = d.args.get("locator")
                if not loc or ledger.extract(ref, loc) is None:
                    _fail(out, "T-09", ref, f"document exhibit names no stored extract ({loc})")
            else:
                _fail(out, "T-09", ref, "exhibit names neither an entry nor an exhibit record")
    urls = [str(x.get("url") or "") for x in ledger.exhibits.values()]
    urls.append(str(event.get("hero_image_url") or ""))
    urls += [str(m.get("source_url") or "") for m in (event.get("media") or [])]
    for u in urls:
        if any(h in u for h in STOCK_HOSTS):
            _fail(out, "T-09", "media", f"stock photograph: {u[:70]}")


def check_episode(th: Thesis, script: dict | None, episode: dict | None, out: list[Finding]) -> None:
    """T-10."""
    chapters = chapter_segments(script) if script else []
    manifest = segment_chapters(episode)
    for sec in th.sections:
        ds = sec.directives
        if ds and all(d.kind == "episode" for d in ds) and not sec.paragraphs:
            _fail(out, "T-10", sec.id, "a section whose only content is an episode block")
        for d in ds:
            if d.kind != "episode":
                continue
            n = d.args["chapter"]
            if not script:
                _fail(out, "T-10", sec.id, "episode mark with no exported script")
                continue
            if n >= len(chapters):
                _fail(out, "T-10", sec.id, f"chapter {n} is not in the script ({len(chapters)} chapters)")
                continue
            lines = [l for l in chapters[n].get("lines") or [] if (l.get("text") or "").strip()]
            a, b = d.args.get("lines", (1, len(lines)))
            if a < 1 or b > len(lines) or a > b:
                _fail(out, "T-10", sec.id, f"lines {a}-{b} are not in chapter {n} ({len(lines)} lines)")
            if manifest:
                if n >= len(manifest):
                    _fail(out, "T-10", sec.id, f"chapter {n} is not in the served manifest ({len(manifest)} chapters)")
                else:
                    want = (chapters[n].get("title") or "").strip()
                    got = str(manifest[n].get("title") or "").strip()
                    if want and got and norm(want) != norm(got):
                        _fail(out, "T-10", sec.id, f"chapter {n} is {want!r} in the script and {got!r} in the manifest")


def check_omits(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-11."""
    sec = th.section("omits")
    if sec is None:
        return
    authors = [str(e.get("author") or "") for e in ledger.entries.values()]
    for para in sec.paragraphs:
        text = para.raw
        for src in ledger.entries:
            if src in text:
                _fail(out, "T-11", f"omits line {para.line}", f"names the ledger entry {src}")
        for a in authors:
            if len(a) > 3 and a in text:
                _fail(out, "T-11", f"omits line {para.line}", f"names an author the ledger holds: {a[:40]!r}")
        if para.against and para.against not in ledger.positions:
            _fail(out, "T-11", f"omits line {para.line}", f"against unknown position {para.against}")
        if not para.against:
            _fail(out, "T-11", f"omits line {para.line}", "an omission not attached to the position it cuts against")


def check_analyses(th: Thesis, ledger: Ledger, out: list[Finding]) -> None:
    """T-16: every analysis block resolves; validate_ledger checks the derivation."""
    for sec in th.sections:
        for d in sec.directives:
            if d.kind == "analysis" and d.args["id"] not in ledger.analyses:
                _fail(out, "T-16", d.args["id"], "analysis block names no ledger analysis")


def check_bar(th: Thesis, ledger: Ledger, event: dict, out: list[Finding]) -> None:
    """T-13."""
    if th.status != "published":
        return
    st = standing(ledger, event)
    for k, ok in st["bar"].items():
        if not ok:
            _fail(out, "T-13", th.slug, f"published below the bar: {k} ({ {x: st[x] for x in st if x != 'bar'} })")
    if st["regional"] < 2 and not th.front.get("regional_sources_note"):
        _fail(out, "T-13", th.slug, "fewer than 2 regional sources and no regional_sources_note")
    used = [d for s in th.sections for d in s.directives if d.kind == "analysis"]
    if not used:
        _fail(out, "T-13", th.slug, "published with no analysis block of its own")
    if not th.front.get("audited_by") or not th.front.get("audited_at"):
        _fail(out, "T-13", th.slug, "published without an audit record in the front matter")
    for kind in ("question", "record", "argument", "historiography", "contested", "omits"):
        if th.section(kind) is None:
            _fail(out, "T-13", th.slug, f"published without a {kind} section")
    if not th.argument_sections():
        _fail(out, "T-13", th.slug, "published with no argument sections")
    if th.scope == "holistic" and th.section("event") is None:
        _fail(out, "T-13", th.slug, "published holistic without an event section")
    words = sum(len(sen.text.split()) for _, _, sen in th.all_sentences)
    ceiling = WORD_CEILING_HOLISTIC if th.scope == "holistic" else WORD_CEILING
    if words > ceiling:
        _fail(out, "T-13", th.slug, f"{words} words; the ceiling is {ceiling:,}")


def _sourced(sen) -> bool:
    """A sentence that carries a fact: at least one marker, and not the
    historian's own reading. The coverage rule counts only these."""
    return bool(sen.markers) and not sen.interpretive


def check_coverage(th: Thesis, ledger: Ledger, event: dict, out: list[Finding]) -> None:
    """T-21: a holistic thesis covers the whole event, and says where (§15).

    The front matter's `coverage` map names, for each required strand, the
    sections that carry it; for each perspective the event YAML holds, the
    ledger position that answers it and the sections where its own sources
    are heard. The check counts sourced sentences, so a strand cannot be
    covered by a heading, an {i} sentence or a section that says nothing."""
    scope = th.front.get("scope")
    if scope is None:
        return                      # the pilot model: one question, T-21 silent
    if scope not in SCOPES:
        _fail(out, "T-21", th.slug, f"scope {scope!r} is not one of {SCOPES}")
        return
    if scope != "holistic":
        return
    cov = th.front.get("coverage")
    if not isinstance(cov, dict):
        _fail(out, "T-21", th.slug, "scope holistic with no coverage map in the front matter")
        return
    by_id = {s.id: s for s in th.sections}
    event_ids = {s.id for s in th.sections if s.kind in ("event", "event-section")}
    ev_secs = th.event_sections()
    if th.section("event") is None:
        _fail(out, "T-21", th.slug, "scope holistic with no `## The event` section")
    if len(ev_secs) < HOLISTIC_MIN_EVENT_SECTIONS:
        _fail(out, "T-21", "event", f"{len(ev_secs)} numbered event section(s); the floor is {HOLISTIC_MIN_EVENT_SECTIONS}")
    if len(th.argument_sections()) < HOLISTIC_MIN_QUESTIONS:
        _fail(out, "T-21", "argument", f"{len(th.argument_sections())} contested question(s); the floor is {HOLISTIC_MIN_QUESTIONS}")

    def sourced_in(sid: str) -> list:
        sec = by_id.get(sid)
        return [sen for p in (sec.paragraphs if sec else []) for sen in p.sentences if _sourced(sen)]

    claimed: set[str] = set()
    for strand in HOLISTIC_STRANDS:
        spec = cov.get(strand)
        where = f"coverage.{strand}"
        if not isinstance(spec, dict) or not spec.get("sections"):
            _fail(out, "T-21", where, "a required strand with no sections")
            continue
        sids = [str(x) for x in spec.get("sections") or []]
        unknown = [x for x in sids if x not in by_id]
        for x in unknown:
            _fail(out, "T-21", where, f"names section {x!r}, which the thesis does not have")
        sids = [x for x in sids if x in by_id]
        claimed.update(sids)
        if not any(x in event_ids for x in sids):
            _fail(out, "T-21", where, "no section in The event carries it; a strand argued only in the questions is not narrated")
        floor = spec.get("min", COVERAGE_MIN_SENTENCES)
        if not isinstance(floor, int) or floor < COVERAGE_MIN_SENTENCES:
            _fail(out, "T-21", where, f"min {floor!r} is below the floor of {COVERAGE_MIN_SENTENCES}")
            floor = COVERAGE_MIN_SENTENCES
        sents = []
        for x in sids:
            here = sourced_in(x)
            if not here:
                _fail(out, "T-21", where, f"section {x} is listed and carries no sourced sentence")
            sents.extend(here)
        if len(sents) < floor:
            _fail(out, "T-21", where, f"{len(sents)} sourced sentence(s) across {sids}; the floor is {floor}")
        terms = [str(t) for t in spec.get("terms") or []]
        if strand in TERM_STRANDS and len(terms) < COVERAGE_MIN_TERMS:
            _fail(out, "T-21", where, f"{len(terms)} term(s); {strand} must name at least {COVERAGE_MIN_TERMS}")
        for t in terms:
            rx = re.compile(r"(?<!\w)" + re.escape(t) + r"(?!\w)")
            if not any(rx.search(sen.text) for sen in sents):
                _fail(out, "T-21", where, f"{t!r} is named and no sourced sentence in {sids} carries it")
    extra = [k for k in cov if k not in HOLISTIC_STRANDS and k != "perspectives"]
    for k in extra:
        _fail(out, "T-21", f"coverage.{k}", "not a strand this rule knows; §15 lists them")

    persp = cov.get("perspectives") or {}
    if not isinstance(persp, dict):
        _fail(out, "T-21", "coverage.perspectives", "must map each event-YAML perspective to a position and sections")
        persp = {}
    rendered = {d.args["id"] for s in th.sections for d in s.directives if d.kind == "position"}
    wanted = [slugify(str(p.get("viewpoint") or p.get("name") or "")) for p in (event or {}).get("perspectives") or []]
    for key in wanted:
        spec = persp.get(key)
        where = f"coverage.perspectives.{key}"
        if not isinstance(spec, dict):
            _fail(out, "T-21", where, "a perspective the event record holds is not answered")
            continue
        pid = str(spec.get("position") or "")
        pos = ledger.positions.get(pid)
        if pos is None:
            _fail(out, "T-21", where, f"position {pid!r} is not in the ledger")
            continue
        if pid not in rendered:
            _fail(out, "T-21", where, f"position {pid} has no `::: position` block on the page")
        own = set(pos.get("rests_on") or []) | {src for src, e in ledger.entries.items()
                                                 if str(e.get("position") or "") == pid}
        sids = [str(x) for x in spec.get("sections") or []]
        for x in sids:
            if x not in by_id:
                _fail(out, "T-21", where, f"names section {x!r}, which the thesis does not have")
        heard = [sen for x in sids for sen in sourced_in(x) if any(src in own for src, _ in sen.markers)]
        if len(heard) < PERSPECTIVE_MIN_SENTENCES:
            _fail(out, "T-21", where, f"its own sources are cited in {len(heard)} sourced sentence(s) of {sids}; the floor is {PERSPECTIVE_MIN_SENTENCES}")
    for key in persp:
        if key not in wanted:
            _fail(out, "T-21", f"coverage.perspectives.{key}", "names a perspective the event record does not hold")
    for s in ev_secs:
        if s.id not in claimed:
            _fail(out, "T-21", s.id, "an event section no strand claims")


def validate_thesis(th: Thesis, ledger: Ledger, event: dict,
                    script: dict | None = None, episode: dict | None = None) -> list[Finding]:
    out: list[Finding] = []
    for p in th.problems:
        _fail(out, "T-00", th.slug, p)
    out.extend(validate_ledger(ledger))
    check_markers(th, ledger, out)
    check_sentences(th, ledger, out)
    check_register(th, out)
    check_positions(th, ledger, out)
    check_contested(th, ledger, out)
    check_exhibits(th, ledger, event, out)
    check_episode(th, script, episode, out)
    check_omits(th, ledger, out)
    check_analyses(th, ledger, out)
    check_bar(th, ledger, event, out)
    check_coverage(th, ledger, event, out)
    return out
