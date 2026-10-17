"""Rigor: how much of what Void published was checked, and the floors a run must clear.

Rule 1 is a claim about published sentences, so it is measured in sentences
(docs/proposals/FACTUAL-RIGOR-PLAN-2026-10-02.md, section 1). INTERNAL ONLY
(CEO, 2026-10-03): nothing here is rendered on a page; the numbers live in
`frontend/build-data/rigor.json` and `docs/data/rigor-series.csv`.

COVERAGE, per product (card headline, card summary, consensus and divergence
points, TL;DR, Opinion, On Air). The share of published sentences carrying at
least one anchor that an ENFORCED deterministic rule checked against source
evidence. An anchor is a number in E-13 scope, a quotation of four words or
more, a multi-word proper name, or a date or interval. Which anchors count
depends on what the product's rules read:

  card headline, card summary, points   number, quote (E-13, E-14)
  TL;DR, Opinion, On Air                number, name, date, quote
                                        (editorial/derived_grounding.py)

"Checked" is stricter than "anchored". A card's anchors count as checked only
when its evidence can confirm or refute them (`evidence_state` below): a
pre-truncation index whose rows cover what the writer read. A derived
product's anchors count only when its grounding pass completed
(`daily_briefs.grounding_ran`). Every split uses the same sentence splitter as
the check that reads that product.

Machine-written points ("Sources differ in political framing by 31 points of
lean") are Void's own measurement from the bias engine, not a claim about the
story, and are left out of the points count and of the audit.

THE AUDIT (`audit_feed`) runs E-13, E-14 and E-16 over every shipped card and
every consensus and divergence point, against the committed index
(`editorial.grounding.load_verifier`). A finding is CONFIRMED only when the
evidence can carry it: E-16 reads the text alone and is always confirmable;
an absence (a number or a quotation in no source) is confirmable only on a
format-3, pre-truncation record whose rows the writer could not have read
past. Anything else is "cannot confirm", reported every run and never a
failure: an index of 300-character stubs proves nothing absent.

FLOORS (`floors`), run by `tests/test_rigor.py --floors` before the data
commit:

  F-1  a confirmed E-13, E-14 or E-16 finding on a shipped card or point
  F-2  a fresh card (written this run) with no pre-truncation record, or any
       shipped card with no record at all
  F-3  a TL;DR, Opinion or On Air shipped whose grounding pass did not
       complete AND that is not labelled "Not yet verified" (CEO, 2026-10-03:
       ship with the label rather than withhold)
  F-5  a published correction unapplied in the export, or naming no gate

RUN COUNTERS. Stage 2 and the brief generators write counts into
`build-data/rigor-run.json` through `start_run` and `note_run`: fresh card
ids, critique cards read and unread, sentences cut by reason, cards dropped,
cards kept with an enforced finding. Counts and ids only.

Nothing written here carries a string over twelve words (MAX_WORDS); the test
asserts it.

    python3 pipeline/validation/rigor.py            # print
    python3 pipeline/validation/rigor.py --write    # rigor.json + series row
"""
from __future__ import annotations

import csv
import datetime as _dt
import io
import json
import os
import pathlib
import re
import sys
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BUILD = ROOT / "frontend" / "build-data"
PUBLIC = ROOT / "frontend" / "public" / "data"
FEED_CONFIG = ROOT / "frontend" / "config" / "feed.json"
SERIES = ROOT / "docs" / "data" / "rigor-series.csv"
OUT_NAME = "rigor.json"
RUN_NAME = "rigor-run.json"

#: No string in rigor.json or rigor-run.json may run longer than this.
MAX_WORDS = 12
#: `cluster_summarizer._ARTICLE_BODY_MAX_CHARS`: the most of one body the card
#: writer reads. A record whose index covers this much of every body covers
#: everything the card can have been written from.
SUMMARIZER_WINDOW = 2200
#: `tests/test_feed_buildable.MIN_SOURCES`, the front page's own floor.
MIN_SOURCES = 3
#: Brief rows created on or after this date must say whether grounding ran.
#: Older rows predate the flag and are reported, not failed.
F3_SINCE = "2026-10-03"
#: The run counters describe this feed only when its builtAt falls inside
#: this many hours after the run started.
RUN_WINDOW_HOURS = 8

CONFIRMABLE = "confirmable"
PRODUCTS = ("card_headline", "card_summary", "points", "tldr", "opinion", "onair")
DERIVED = ("tldr", "opinion", "onair")
CARD_ANCHORS = ("number", "quote")
DERIVED_ANCHORS = ("number", "name", "date", "quote")
#: Where the frontend renders the "Not yet verified" label (F-3 checks the
#: wiring as well as the flag).
LABEL_SOURCES = {
    "tldr": ("frontend/app/components/SkyboxBanner.tsx",
             "frontend/app/components/MobileBriefPill.tsx",
             "frontend/app/components/OnAirPage.tsx"),
    "opinion": ("frontend/app/components/SkyboxBanner.tsx",
                "frontend/app/components/MobileBriefPill.tsx",
                "frontend/app/components/OnAirPage.tsx"),
    "onair": ("frontend/app/components/OnAirPage.tsx",),
}
LABEL_LIB = "frontend/app/lib/verification.ts"

# Points the bias engine writes (pipeline/main.py _generate_consensus_divergence):
# Void's measurement of the coverage, not a claim about the event.
MACHINE_POINT_RE = re.compile(
    r"^(?:Sources (?:differ|show|use|take|demonstrate|apply)\b|"
    r"Coverage maintains\b|Single-source coverage\b|Some sources use\b)")

# On Air segments the grounding pass does not read: fixed formulas and the
# pronunciation table.
ONAIR_UNREAD = ("OPEN", "CLOSE", "SAY")


def build_dir() -> pathlib.Path:
    env = os.environ.get("VOID_EXPORT_BUILD_DIR")
    return pathlib.Path(env) if env else BUILD


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


# --------------------------------------------------------------------------
# Run counters (the pipeline hooks). Import-light and never raise: a counter
# must not cost the edition anything.
# --------------------------------------------------------------------------

def _clip(v: Any) -> Any:
    """Strings cut to MAX_WORDS words; containers walked."""
    if isinstance(v, str):
        w = v.split()
        return " ".join(w[:MAX_WORDS]) if len(w) > MAX_WORDS else v
    if isinstance(v, dict):
        return {str(_clip(k)): _clip(x) for k, x in v.items()}
    if isinstance(v, (list, tuple, set)):
        return [_clip(x) for x in v]
    return v


#: Set by start_run in THIS process. note_run writes only under it, so a test
#: that calls a generator directly can never touch the committed counters.
RUN_ENV = "VOID_RIGOR_RUN_FILE"


def start_run(build: pathlib.Path | None = None) -> None:
    """Reset the run counters. Called once, at the start of Stage 2."""
    try:
        p = pathlib.Path(build or build_dir()) / RUN_NAME
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({"startedAt": _now()}, indent=1), encoding="utf-8")
        os.environ[RUN_ENV] = str(p)
    except Exception as e:  # pragma: no cover - a counter never costs the run
        print(f"  [rigor] [warn] could not reset run counters: {e}")


def note_run(section: str, data: dict, build: pathlib.Path | None = None) -> None:
    """Merge `data` into the run counters under `section`. Counts and ids only.

    A no-op unless start_run ran in this process (or `build` is given).
    """
    try:
        if build is None and not os.environ.get(RUN_ENV):
            return
        p = pathlib.Path(build) / RUN_NAME if build else pathlib.Path(os.environ[RUN_ENV])
        cur = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        cur.setdefault(section, {}).update(_clip(data))
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cur, indent=1, sort_keys=True), encoding="utf-8")
    except Exception as e:  # pragma: no cover
        print(f"  [rigor] [warn] could not record {section} counters: {e}")


_REASONS = (
    ("removed", "removed member"), ("e-16", "other story"),
    ("names another story", "other story"), ("e-13", "number"),
    ("e-14", "quotation"), ("number", "number"), ("weekday", "date"),
    ("date", "date"), ("interval", "date"), ("name", "name"),
    ("quotation", "quotation"), ("total", "total"),
    ("reported speech", "lifted quote"), ("hedge", "hedge"),
)


def reason_class(reason: str) -> str:
    """A cut's reason as a short class label, never the sentence."""
    low = (reason or "").lower()
    for key, cls in _REASONS:
        if low.startswith(key) or key in low[:40]:
            return cls
    return "other"


def count_reasons(cuts: Iterable[Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for c in cuts or ():
        r = c.get("reason") if isinstance(c, dict) else getattr(c, "reason", "")
        k = reason_class(r or "")
        out[k] = out.get(k, 0) + 1
    return out


# --------------------------------------------------------------------------
# The checks this module reads with (lazy, so the hooks above stay light)
# --------------------------------------------------------------------------

def _mods():
    from pipeline.editorial import derived_grounding as dg
    from pipeline.editorial import grounding as G
    from pipeline.editorial import standard as std
    return G, std, dg


def _load(path: pathlib.Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def displayable(c: dict) -> bool:
    """`tests/test_feed_buildable.displayable`, the front page's predicate."""
    return (c.get("source_count") or 0) >= MIN_SOURCES and bool(
        (c.get("summary_tier") or "").strip())


def shipped_cards(feed: dict) -> list[dict]:
    """The cards the front page renders: the first `displayed` displayable."""
    cfg = _load(FEED_CONFIG, {}) or {}
    n = int(cfg.get("displayed") or 20)
    return [c for c in (feed.get("clusters") or []) if displayable(c)][:n]


def points_of(c: dict) -> list[str]:
    out = []
    for k in ("consensus_points", "divergence_points"):
        v = c.get(k) or []
        if isinstance(v, str):
            v = [v]
        out.extend(str(p) for p in v if str(p).strip())
    return out


def is_machine_point(p: str) -> bool:
    return bool(MACHINE_POINT_RE.match((p or "").strip()))


# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------

def load_record(build: pathlib.Path, cid: str) -> dict | None:
    G, _, _ = _mods()
    return _load(pathlib.Path(build) / G.DIRNAME / f"{cid}.json")


def evidence_state(record: dict | None, fresh: bool | None) -> str:
    """Whether this record can confirm an absence, or why not (a short label)."""
    G, _, _ = _mods()
    if not record:
        return "no record"
    if int(record.get("format") or 0) < 3:
        return "format 2 index"
    if record.get("stage") != G.STAGE_PRE:
        return "built after truncation"
    for a in record.get("articles") or []:
        body = int(a.get("bodyChars") or 0)
        if a.get("stub") and not fresh:
            # Cut to 300 characters by an EARLIER run. A card written this run
            # read the same stub, so its index covers it; a cached card was
            # written from the whole body, which nobody kept.
            return "stub rows, card not fresh"
        nonbody = max(0, int(a.get("chars") or 0) - body)
        if body and G.PER_ARTICLE_CHARS - nonbody < min(body, SUMMARIZER_WINDOW):
            return "index cap below writer window"
    return CONFIRMABLE


# --------------------------------------------------------------------------
# The audit: E-13, E-14, E-16 against the committed index
# --------------------------------------------------------------------------

def _kind(f) -> str:
    m = f.message
    if f.id == "E-16":
        return "shift"
    if f.id == "E-13":
        return "misattached" if " puts " in f" {m}" else "absent"
    if f.id == "E-14":
        return "punctuation" if "punctuation no source" in m else "absent"
    return "other"


def audit_text(title: str, summary: str, verifier, *, where: str,
               state: str, point: bool = False) -> list[dict]:
    """Findings for one card or one point, each classed.

    `status` is "confirmed" (fails F-1), "cannot confirm" (reported) or
    "advisory" (reported: a point's number beside an outlet name, which no
    source sentence carries because outlets do not name themselves).
    """
    _, std, _ = _mods()
    found = list(std.e16_topic_shift(summary))
    if verifier is not None and getattr(verifier, "present", False):
        found += std.e13_numbers_are_sourced(title, summary, verifier)
        found += std.e14_quotes_are_verbatim(title, summary, verifier)
    out = []
    for f in found:
        kind = _kind(f)
        if f.id == "E-16":
            status = "confirmed"
        elif point and kind == "misattached":
            status = "advisory"
        elif state == CONFIRMABLE:
            status = "confirmed"
        else:
            status = "cannot confirm"
        out.append({"rule": f.id, "kind": kind, "where": where,
                    "status": status, "message": f.message})
    return out


def audit_cluster(c: dict, build: pathlib.Path, fresh: bool | None) -> dict:
    G, _, _ = _mods()
    cid = str(c.get("id") or "")
    rec = load_record(build, cid)
    state = evidence_state(rec, fresh)
    v = G.Verifier(rec) if rec else None
    findings = audit_text(c.get("title") or "", c.get("summary") or "", v,
                          where="card", state=state)
    for i, p in enumerate(points_of(c)):
        if is_machine_point(p):
            continue
        findings += audit_text("", p, v, where=f"point {i}", state=state, point=True)
    return {"id": cid, "state": state, "stage": (rec or {}).get("stage"),
            "format": (rec or {}).get("format"), "findings": findings}


def run_counters(build: pathlib.Path, built_at: str | None) -> dict | None:
    """The run counters, when they describe the run that built this feed."""
    run = _load(pathlib.Path(build) / RUN_NAME)
    if not run or not run.get("startedAt") or not built_at:
        return None
    try:
        start = _dt.datetime.fromisoformat(run["startedAt"].replace("Z", "+00:00"))
        built = _dt.datetime.fromisoformat(built_at.replace("Z", "+00:00"))
        if built.tzinfo is None:
            built = built.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return None
    if not (start <= built <= start + _dt.timedelta(hours=RUN_WINDOW_HOURS)):
        return None
    return run


def fresh_ids(run: dict | None) -> set[str] | None:
    if not run:
        return None
    ids = (run.get("stage2") or {}).get("fresh_ids")
    return set(ids) if isinstance(ids, list) else None


def audit_feed(feed: dict, build: pathlib.Path | None = None,
               fresh: set[str] | None = None) -> dict:
    """Every shipped card and point, then the rest of the bench (report only)."""
    build = pathlib.Path(build or build_dir())
    shipped = shipped_cards(feed)
    ship_ids = {c.get("id") for c in shipped}
    cards = []
    for c in feed.get("clusters") or []:
        f = None if fresh is None else (c.get("id") in fresh)
        r = audit_cluster(c, build, f)
        r["shipped"] = c.get("id") in ship_ids
        r["fresh"] = f
        cards.append(r)
    return {"cards": cards, "freshKnown": fresh is not None}


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------

def anchors(sent: str, spoken: bool = False) -> set[str]:
    """The anchor types a sentence carries."""
    G, std, dg = _mods()
    a: set[str] = set()
    if (dg.values_of(sent) if spoken else G.numbers_in(sent)):
        a.add("number")
    if any(len(q.split()) >= 4 for q in std._QUOTE_RE.findall(sent)):
        a.add("quote")
    for nm in G.proper_names(dg._collapse_spelled(sent)):
        toks = [t for t in dg._norm_names(nm).split() if t not in ("mr", "mrs", "ms", "dr")]
        if len(toks) >= 2 and not all(t in dg._TITLE_WORDS for t in toks):
            a.add("name")
            break
    if dg._WEEKDAY.search(sent) or dg._MONTH_DAY.search(sent) or dg._INTERVAL.search(sent):
        a.add("date")
    return a


def derived_sentences(text: str) -> list[str]:
    """`derived_grounding.ground_text`'s own walk: paragraph, line, sentence."""
    _, _, dg = _mods()
    out = []
    for para in re.split(r"\n\s*\n", text or ""):
        for line in para.split("\n"):
            out.extend(s for s in dg._sentences(line) if s.strip())
    return out


def onair_sentences(script: str) -> list[str]:
    """The rundown's turns, minus the segments grounding does not read and
    the programme's own formulas."""
    try:
        from pipeline.briefing.radio_script_generator import (
            BRIEFS_LEAD, KICKER_LEADS, MENU_LEAD)
        formulas = (MENU_LEAD, BRIEFS_LEAD) + tuple(KICKER_LEADS)
    except Exception:  # pragma: no cover
        formulas = ()
    out: list[str] = []
    kind = None
    for line in (script or "").split("\n"):
        h = re.match(r"^##\s+([A-Z]+)", line)
        if h:
            kind = h.group(1)
            continue
        if kind in ONAIR_UNREAD:
            continue
        m = re.match(r"^\s*[AB]:\s*(.*)$", line)
        if not m:
            continue
        for s in derived_sentences(m.group(1)):
            for f in formulas:
                if f and s.startswith(f):
                    s = s[len(f):].strip()
            if s:
                out.append(s)
    return out


def _tally(sents: list[str], types: tuple[str, ...], spoken: bool,
           checked: bool) -> dict:
    n = anch = chk = 0
    by: dict[str, int] = {}
    for s in sents:
        n += 1
        a = anchors(s, spoken) & set(types)
        if a:
            anch += 1
            if checked:
                chk += 1
            for t in a:
                by[t] = by.get(t, 0) + 1
    return {"sentences": n, "anchored": anch, "checked": chk,
            "coverage": round(100.0 * chk / n, 1) if n else None,
            "anchorTypes": list(types), "byAnchor": dict(sorted(by.items()))}


def _add(a: dict, b: dict) -> dict:
    for k in ("sentences", "anchored", "checked"):
        a[k] = a.get(k, 0) + b[k]
    for t, n in b["byAnchor"].items():
        a.setdefault("byAnchor", {})[t] = a.get("byAnchor", {}).get(t, 0) + n
    a["anchorTypes"] = b["anchorTypes"]
    return a


def _finish(a: dict) -> dict:
    n = a.get("sentences", 0)
    a["coverage"] = round(100.0 * a.get("checked", 0) / n, 1) if n else None
    a.setdefault("byAnchor", {})
    a["byAnchor"] = dict(sorted(a["byAnchor"].items()))
    return a


def card_coverage(shipped: list[dict], audit: dict) -> dict[str, dict]:
    _, std, _ = _mods()
    state = {r["id"]: r["state"] for r in audit["cards"]}
    out = {"card_headline": {"sentences": 0, "anchored": 0, "checked": 0},
           "card_summary": {"sentences": 0, "anchored": 0, "checked": 0},
           "points": {"sentences": 0, "anchored": 0, "checked": 0}}
    machine = 0
    for c in shipped:
        ok = state.get(c.get("id")) == CONFIRMABLE
        _add(out["card_headline"], _tally([c.get("title") or ""], CARD_ANCHORS, False, ok))
        _add(out["card_summary"], _tally(std.sentences(c.get("summary") or ""),
                                         CARD_ANCHORS, False, ok))
        for p in points_of(c):
            if is_machine_point(p):
                machine += 1
                continue
            _add(out["points"], _tally(std.sentences(p), CARD_ANCHORS, False, ok))
    for k in out:
        _finish(out[k])
        out[k]["anchorTypes"] = list(CARD_ANCHORS)
    out["points"]["machinePointsExcluded"] = machine
    return out


def grounding_flags(brief: dict | None) -> dict | None:
    if not brief:
        return None
    g = brief.get("grounding_ran")
    if isinstance(g, str):
        try:
            g = json.loads(g)
        except ValueError:
            g = None
    return g if isinstance(g, dict) else None


def shipped_derived(brief: dict | None) -> dict[str, str]:
    """product -> the text that shipped, for each derived product that did."""
    if not brief or str(brief.get("generator") or "").startswith("stub-on-failure"):
        return {}
    out = {}
    if (brief.get("tldr_text") or "").strip():
        out["tldr"] = brief["tldr_text"]
    if (brief.get("opinion_text") or "").strip():
        out["opinion"] = brief["opinion_text"]
    if brief.get("audio_url") and (brief.get("audio_script") or "").strip():
        out["onair"] = brief["audio_script"]
    return out


def derived_coverage(brief: dict | None) -> dict[str, dict]:
    flags = grounding_flags(brief) or {}
    texts = shipped_derived(brief)
    out = {}
    for p in DERIVED:
        text = texts.get(p)
        sents = (onair_sentences(text) if p == "onair" else derived_sentences(text)) if text else []
        ran = flags.get(p)
        t = _tally(sents, DERIVED_ANCHORS, True, ran is True)
        t["groundingRan"] = ran if isinstance(ran, bool) else None
        t["shipped"] = bool(text)
        out[p] = t
    return out


# --------------------------------------------------------------------------
# Corrections (F-5)
# --------------------------------------------------------------------------

def gate_resolves(gate: str) -> bool:
    """A gate is an ENFORCED rule id in editorial.standard, or a file that exists."""
    _, std, _ = _mods()
    g = (gate or "").strip()
    if not g:
        return False
    v = std.VALIDATORS_BY_ID.get(g)
    if v is not None:
        return v.status == std.ENFORCED
    return (ROOT / g.split("::")[0]).exists()


def corrections_report(feed: dict, archive: list | None,
                       entries: list[dict] | None = None) -> dict:
    from pipeline.editorial import corrections as C
    corr = C.load() if entries is None else entries
    ungated = []
    for i, c in enumerate(corr):
        gates = c.get("gate")
        gates = [gates] if isinstance(gates, str) else list(gates or [])
        if not gates or not all(gate_resolves(g) for g in gates):
            ungated.append(i)
    unapplied = C.unapplied(feed.get("clusters") or [], "id", corr)
    if archive:
        unapplied += C.unapplied(archive, "source_cluster_id", corr)
    by_surface: dict[str, int] = {}
    for c in corr:
        s = str(c.get("product") or "card")
        by_surface[s] = by_surface.get(s, 0) + 1
    return {"entries": len(corr), "ungated": ungated, "unapplied": len(unapplied),
            "unappliedDetail": unapplied, "bySurface": by_surface}


# --------------------------------------------------------------------------
# Floors
# --------------------------------------------------------------------------

def _label_wired(product: str) -> bool:
    lib = ROOT / LABEL_LIB
    if not lib.exists() or "grounding_ran" not in lib.read_text(encoding="utf-8"):
        return False
    for rel in LABEL_SOURCES[product]:
        p = ROOT / rel
        if not p.exists():
            return False
        src = p.read_text(encoding="utf-8")
        if f'isUnverified(brief, "{product}") && <UnverifiedLabel />' not in src:
            return False
    return True


def floors(audit: dict, run: dict | None, brief: dict | None,
           corr: dict, label_wired=_label_wired) -> dict[str, list[str]]:
    """Floor -> failure lines (empty means it holds). Short lines, ids only."""
    out: dict[str, list[str]] = {"F-1": [], "F-2": [], "F-3": [], "F-5": []}
    fresh = fresh_ids(run)
    for r in audit["cards"]:
        if not r["shipped"]:
            continue
        for f in r["findings"]:
            if f["status"] == "confirmed":
                out["F-1"].append(f"{r['id'][:8]} {f['where']} {f['rule']} {f['kind']}")
        if r["state"] == "no record":
            out["F-2"].append(f"{r['id'][:8]} shipped with no grounding record")
        elif fresh is not None and r["id"] in fresh and r["stage"] != "pre-truncation":
            out["F-2"].append(f"{r['id'][:8]} fresh card, record stage {r['stage']}")
    flags = grounding_flags(brief)
    created = str((brief or {}).get("created_at") or "")[:10]
    for p in shipped_derived(brief):
        ran = (flags or {}).get(p)
        if ran is True:
            continue
        if ran is False:
            if not label_wired(p):
                out["F-3"].append(f"{p} grounding did not complete and no label renders")
            continue
        if created >= F3_SINCE:
            out["F-3"].append(f"{p} shipped with no grounding flag")
    for i in corr["ungated"]:
        out["F-5"].append(f"correction {i} names no gate that resolves")
    if corr["unapplied"]:
        out["F-5"].append(f"{corr['unapplied']} correction edit(s) unapplied in the export")
    return out


# --------------------------------------------------------------------------
# Compute, write
# --------------------------------------------------------------------------

def _counts(audit: dict, shipped_only: bool) -> dict:
    by: dict[str, dict[str, int]] = {}
    for r in audit["cards"]:
        if r["shipped"] != shipped_only:
            continue
        for f in r["findings"]:
            d = by.setdefault(f["status"], {})
            k = f"{f['rule']} {f['kind']}"
            d[k] = d.get(k, 0) + 1
    return {s: dict(sorted(d.items())) for s, d in sorted(by.items())}


def compute(build: pathlib.Path | None = None, public: pathlib.Path | None = None,
            entries: list[dict] | None = None) -> dict:
    """Everything rigor.json holds, from the committed outputs."""
    build = pathlib.Path(build or build_dir())
    public = pathlib.Path(public or PUBLIC)
    feed = _load(build / "feed.json", {}) or {}
    archive = _load(build / "archive.json", []) or []
    brief = _load(public / "brief.json")
    built_at = feed.get("builtAt")
    run = run_counters(build, built_at)
    fresh = fresh_ids(run)
    audit = audit_feed(feed, build, fresh)
    shipped = shipped_cards(feed)
    products = card_coverage(shipped, audit)
    products.update(derived_coverage(brief))
    states: dict[str, int] = {}
    for r in audit["cards"]:
        if r["shipped"]:
            states[r["state"]] = states.get(r["state"], 0) + 1
    corr = corrections_report(feed, archive, entries)
    fl = floors(audit, run, brief, corr)
    run_view = None
    if run:
        run_view = {k: v for k, v in run.items() if k != "stage2"}
        s2 = dict(run.get("stage2") or {})
        if "fresh_ids" in s2:
            s2["fresh"] = len(s2.pop("fresh_ids") or [])
        run_view["stage2"] = s2
    return {
        "builtAt": built_at,
        "briefCreatedAt": (brief or {}).get("created_at"),
        "products": {p: products[p] for p in PRODUCTS},
        "evidence": {
            "shipped": len(shipped),
            "freshKnown": fresh is not None,
            "fresh": None if fresh is None else sum(1 for c in shipped if c.get("id") in fresh),
            "states": dict(sorted(states.items())),
        },
        "audit": {"shipped": _counts(audit, True), "bench": _counts(audit, False)},
        "run": run_view,
        "corrections": {k: v for k, v in corr.items() if k != "unappliedDetail"},
        "floors": {k: ("pass" if not v else f"fail {len(v)}") for k, v in fl.items()},
        "floorDetail": {k: v for k, v in fl.items() if v},
    }


SERIES_COLUMNS = (
    ["built_at", "computed_at"]
    + [f"{p}_{k}" for p in PRODUCTS for k in ("sentences", "anchored", "checked")]
    + ["shipped_cards", "confirmable_cards", "fresh_cards",
       "audit_confirmed", "audit_cannot_confirm", "audit_advisory",
       "critique_read", "critique_unread", "cards_cut_sentences",
       "cards_dropped", "cards_kept_failing", "derived_cut_sentences",
       "tldr_grounded", "opinion_grounded", "onair_grounded",
       "corrections", "floors_failed"])


def series_row(r: dict, computed_at: str) -> dict:
    row: dict[str, Any] = {"built_at": r["builtAt"], "computed_at": computed_at}
    for p in PRODUCTS:
        for k in ("sentences", "anchored", "checked"):
            row[f"{p}_{k}"] = r["products"][p].get(k, 0)
    ev = r["evidence"]
    row["shipped_cards"] = ev["shipped"]
    row["confirmable_cards"] = ev["states"].get(CONFIRMABLE, 0)
    row["fresh_cards"] = "" if ev["fresh"] is None else ev["fresh"]
    sh = r["audit"]["shipped"]
    for st, col in (("confirmed", "audit_confirmed"), ("cannot confirm", "audit_cannot_confirm"),
                    ("advisory", "audit_advisory")):
        row[col] = sum((sh.get(st) or {}).values())
    run = r.get("run") or {}
    s2 = run.get("stage2") or {}
    row["critique_read"] = s2.get("critique_read", "")
    row["critique_unread"] = s2.get("critique_unread", "")
    row["cards_cut_sentences"] = s2.get("cut_sentences", "")
    row["cards_dropped"] = s2.get("dropped", "")
    row["cards_kept_failing"] = s2.get("kept_failing", "")
    derived_cuts = [sum((run.get(k) or {}).get("cuts_by_reason", {}).values())
                    for k in ("brief", "onair") if run.get(k)]
    row["derived_cut_sentences"] = sum(derived_cuts) if derived_cuts else ""
    for p in DERIVED:
        g = r["products"][p].get("groundingRan")
        row[f"{p}_grounded"] = "" if g is None else int(g)
    row["corrections"] = r["corrections"]["entries"]
    row["floors_failed"] = " ".join(k for k, v in r["floors"].items() if v != "pass")
    return row


def append_series(r: dict, path: pathlib.Path = SERIES, computed_at: str | None = None) -> dict:
    """One row per run, keyed by builtAt: a rerun replaces its own row."""
    row = series_row(r, computed_at or _now())
    rows: list[dict] = []
    if path.exists():
        rows = [x for x in csv.DictReader(io.StringIO(path.read_text(encoding="utf-8")))]
    rows = [x for x in rows if x.get("built_at") != str(row["built_at"])]
    rows.append({k: row.get(k, "") for k in SERIES_COLUMNS})
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(SERIES_COLUMNS), lineterminator="\n")
    w.writeheader()
    for x in rows:
        w.writerow({k: x.get(k, "") for k in SERIES_COLUMNS})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(buf.getvalue(), encoding="utf-8")
    return row


def write(build: pathlib.Path | None = None, series: pathlib.Path | None = SERIES) -> dict:
    r = compute(build)
    r["computedAt"] = _now()
    out = pathlib.Path(build or build_dir()) / OUT_NAME
    out.write_text(json.dumps(_clip(r), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if series is not None:
        append_series(r, series, r["computedAt"])
    return r


def format_summary(r: dict) -> str:
    lines = [f"rigor: feed builtAt {r['builtAt']}"]
    for p in PRODUCTS:
        x = r["products"][p]
        extra = ""
        if p in DERIVED:
            extra = f", grounding ran: {x.get('groundingRan')}"
        lines.append(f"  {p:14s} {x['sentences']:4d} sentences, {x['anchored']:4d} anchored, "
                     f"{x['checked']:4d} checked, coverage {x['coverage']}%{extra}")
    ev = r["evidence"]
    lines.append(f"  evidence: {ev['shipped']} shipped cards, states {ev['states']}, "
                 f"fresh {'unknown' if not ev['freshKnown'] else ev['fresh']}")
    lines.append(f"  audit (shipped): {r['audit']['shipped'] or 'no findings'}")
    lines.append(f"  floors: {r['floors']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write", action="store_true",
                    help="write build-data/rigor.json and the series row")
    ap.add_argument("--no-series", action="store_true")
    a = ap.parse_args(argv)
    if a.write:
        r = write(series=None if a.no_series else SERIES)
    else:
        r = compute()
    print(format_summary(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
