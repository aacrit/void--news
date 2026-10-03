"""Published corrections, applied at export so the database cannot undo them.

A printed card is permanent: `printed_stories` feeds `build-data/archive.json`,
which prerenders `/story/<id>/`, and the same text sits in `feed.json` until the
next run replaces the feed. Before this file there was no way to correct one.
Editing the committed JSON by hand lasts until the next export, which rewrites
`archive.json` from the state database, and the database still holds the error.

So a correction lives here, in `corrections.json`, and `export_static.py`
applies it to every row it writes, from any database, on every run.

THE ENTRY (schema 2, rev 86 WS-R). Every entry carries:

  id        stable slug, cited by the regression corpus
  product   card | brief | opinion | radio | deepdive
  class     the error class (tests/fixtures/rigor_regressions/<class>.json)
  date      the day the correction was made (the reader's notice prints it)
  gate      the rule or test that now catches this class, or "none" when no
            deterministic check does yet (a declared gap, listed in
            tests/test_corrections.py, never a silent one)
  reason    internal: what was wrong and the evidence (never served)
  notice    the short public reason, or null for a wording change that
            corrects no fact. Rendered as "Corrected <date>: <notice>."

and its target and action, by product:

  card      "cluster": a source cluster id, or "*" for every card.
            "edits": find/replace (a literal substring), remove (a list item
            containing the text), regex/replace (a pattern)
  brief     "brief": a daily_briefs id. "edits" on tldr_text
  opinion   "brief": a daily_briefs id. "edits" on opinion_text
  radio     "brief": a daily_briefs id. "audio": "withdrawn" (the flag the
            Weekly's corrections use) and "audio_paths", the files the
            episode was served at. The audio is never edited: the episode is
            withdrawn until it is re-rendered, and the brief row is stamped
            `audio_withdrawn` (the flag History's manifest uses)
  deepdive  "cluster": a source cluster id. "remove_members": article URLs
            that are another story's. The member list, `source_count`,
            `member_count` and the one-vote-per-outlet lean histogram are
            recomputed from what remains

An edit whose text is no longer present is skipped: the card may have been
regenerated, and a correction must never write text of its own into a card it
cannot find.

THE ARCHIVE REPAIR (rev 86, CEO decision 3 of the factual-rigor plan). An
archived card whose summary carries an E-16 topic-shift opener ("Separately,")
had a sentence from another story in it. `repair_archive` removes that
sentence, and the sentences that follow it until one returns to the card's own
names (the write-time repair's rule, `derived_grounding.repair_card`, run on
`standard.py`'s own sentence splitter so the result can be re-checked by E-16
and pass). The row is stamped `auto_corrected` with the repair's date and
carries a notice. Deterministic and idempotent: the state database still holds
the old text, so every export repairs it again, the same way, on the same date.

Pure, stdlib plus the editorial modules, no I/O beyond reading the file.
`tests/test_corrections.py` and `tests/test_grounding.py` assert the committed
tree carries every correction.
"""
from __future__ import annotations

import copy
import json
import pathlib
import re
from typing import Any, Iterable

PATH = pathlib.Path(__file__).with_name("corrections.json")

PRODUCTS = ("card", "brief", "opinion", "radio", "deepdive")
REQUIRED = ("id", "product", "class", "date", "gate", "reason")
# The fields of a brief row each product may edit.
BRIEF_FIELDS = {"brief": ("tldr_text", "tldr_headline"),
                "opinion": ("opinion_text", "opinion_headline")}
# What a withdrawn episode stops serving. The scripts go too: they speak the
# error, and a page that shows a transcript would print it.
AUDIO_FIELDS = ("audio_url", "audio_duration_seconds", "audio_file_size",
                "audio_chapters", "news_start_seconds", "opinion_start_seconds",
                "audio_script", "opinion_audio_script")

# The archive repair. Its date is fixed, so the notice a reader sees does not
# move every time the export runs; a row printed after it is dated by its own
# edition.
ARCHIVE_REPAIR_DATE = "2026-10-03"
ARCHIVE_REPAIR_CLASS = "cluster-contamination"
ARCHIVE_REPAIR_NOTICE = "a sentence from another story was removed"


def load(path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    p = pathlib.Path(path or PATH)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("corrections") or []


def product_of(c: dict[str, Any]) -> str:
    return c.get("product") or "card"


def schema_problems(corr: list[dict[str, Any]]) -> list[str]:
    """Every entry that is missing a field, names an unknown product, or
    has no target for its product."""
    out: list[str] = []
    seen: set[str] = set()
    for i, c in enumerate(corr):
        tag = c.get("id") or f"#{i}"
        for k in REQUIRED:
            if not c.get(k):
                out.append(f"{tag}: no {k}")
        if "notice" not in c:
            out.append(f"{tag}: no notice (null is allowed, absent is not)")
        p = c.get("product")
        if p not in PRODUCTS:
            out.append(f"{tag}: product {p!r} is not one of {PRODUCTS}")
        if c.get("id") in seen:
            out.append(f"{tag}: duplicate id")
        seen.add(c.get("id"))
        if p in ("card", "deepdive") and not c.get("cluster"):
            out.append(f"{tag}: a {p} correction names no cluster")
        if p in ("brief", "opinion", "radio") and not c.get("brief"):
            out.append(f"{tag}: a {p} correction names no brief")
        if p == "deepdive" and not c.get("remove_members"):
            out.append(f"{tag}: a deepdive correction removes no member")
        if p == "radio" and c.get("audio") != "withdrawn":
            out.append(f"{tag}: a radio correction must withdraw the episode")
        if p in ("brief", "opinion"):
            allowed = BRIEF_FIELDS[p]
            for e in c.get("edits") or []:
                if e.get("field") not in allowed:
                    out.append(f"{tag}: a {p} correction edits {e.get('field')!r}, "
                               f"not one of {allowed}")
        notice = c.get("notice")
        if isinstance(notice, str) and re.search("[\u2014\u2013]", notice):
            out.append(f"{tag}: the notice carries a dash")
    return out


def _notice(c: dict[str, Any]) -> dict[str, Any] | None:
    if not c.get("notice"):
        return None
    return {"date": c.get("date"), "product": product_of(c), "notice": c["notice"]}


def _add_notice(row: dict[str, Any], note: dict[str, Any] | None) -> None:
    if not note:
        return
    notes = row.get("corrections")
    if not isinstance(notes, list):
        notes = []
    if note not in notes:
        notes.append(note)
    row["corrections"] = notes


# ---------------------------------------------------------------------------
# Edits, shared by every text product
# ---------------------------------------------------------------------------
def _apply_edit(row: dict[str, Any], edit: dict[str, Any]) -> str | None:
    field = edit.get("field") or "summary"
    val = row.get(field)
    if val is None:
        return None
    if "remove" in edit and isinstance(val, list):
        keep = [x for x in val if edit["remove"] not in str(x)]
        if len(keep) != len(val):
            row[field] = keep
            return f"{field}: removed {len(val) - len(keep)} item(s)"
        return None
    if "regex" in edit:
        rx = re.compile(edit["regex"])
        if isinstance(val, list):
            new = [rx.sub(edit.get("replace", ""), str(x)) if isinstance(x, str) else x
                   for x in val]
        elif isinstance(val, str):
            new = rx.sub(edit.get("replace", ""), val)
        else:
            return None
        if new != val:
            row[field] = new
            return f"{field}: pattern replaced"
        return None
    if "find" in edit:
        find, repl = edit["find"], edit.get("replace", "")
        if isinstance(val, str) and find in val:
            row[field] = re.sub(r"  +", " ", val.replace(find, repl)).strip()
            return f"{field}: corrected"
        if isinstance(val, list):
            new = [x.replace(find, repl) if isinstance(x, str) else x for x in val]
            if new != val:
                row[field] = new
                return f"{field}: corrected"
    return None


# ---------------------------------------------------------------------------
# Cards (feed rows and archive rows)
# ---------------------------------------------------------------------------
def _card_entries(corr: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [c for c in corr if product_of(c) == "card"]


def apply_all(rows: Iterable[dict[str, Any]], key: str = "id",
              corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Apply every card correction to the rows it names. Returns a log line per
    edit. A row a correction changed carries its notice under `corrections`."""
    corr = _card_entries(load() if corrections is None else corrections)
    if not corr:
        return []
    log: list[str] = []
    for row in rows:
        rid = str(row.get(key) or "")
        for c in corr:
            target = c.get("cluster") or ""
            if target != "*" and target != rid:
                continue
            changed = False
            for edit in c.get("edits") or []:
                done = _apply_edit(row, edit)
                if done:
                    changed = True
                    log.append(f"{rid[:8]} {done} ({c.get('date')}: {c.get('reason', '')[:60]})")
            # The notice is the record that the page differs from what was
            # printed. The database keeps the printed text, so every export
            # changes the row again and stamps it again; a card that was
            # regenerated without the error is not marked corrected.
            if target != "*" and changed:
                _add_notice(row, _notice(c))
    return log


def unapplied(rows: Iterable[dict[str, Any]], key: str = "id",
              corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Card corrections whose wrong text is still present in `rows` (for the gate)."""
    corr = _card_entries(load() if corrections is None else corrections)
    out: list[str] = []
    for row in rows:
        rid = str(row.get(key) or "")
        for c in corr:
            target = c.get("cluster") or ""
            if target != "*" and target != rid:
                continue
            for edit in c.get("edits") or []:
                probe = copy.deepcopy(row)
                if _apply_edit(probe, edit):
                    out.append(f"{rid[:8]} {edit.get('field', 'summary')}: "
                               f"{(edit.get('find') or edit.get('remove') or edit.get('regex'))[:50]!r}")
    return out


# ---------------------------------------------------------------------------
# The brief: TL;DR, Opinion, and the radio episode
# ---------------------------------------------------------------------------
def _brief_entries(corr: list[dict[str, Any]], brief_id: str) -> list[dict[str, Any]]:
    return [c for c in corr if product_of(c) in ("brief", "opinion", "radio")
            and str(c.get("brief") or "") == brief_id]


def apply_brief(brief: dict[str, Any] | None,
                corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Apply the brief, opinion and radio corrections that name this brief row.

    Text products are edited in place. A radio correction withdraws the
    episode: every audio field is cleared, so no player, page or podcast feed
    can offer it, and the row is stamped `audio_withdrawn`.
    """
    if not brief:
        return []
    corr = load() if corrections is None else corrections
    bid = str(brief.get("id") or "")
    log: list[str] = []
    for c in _brief_entries(corr, bid):
        if product_of(c) == "radio":
            if c.get("audio") == "withdrawn":
                if not brief.get("audio_withdrawn") or brief.get("audio_url"):
                    log.append(f"{bid[:8]} radio: episode withdrawn ({c.get('date')})")
                for k in AUDIO_FIELDS:
                    if k in brief:
                        brief[k] = None
                brief["audio_withdrawn"] = True
                _add_notice(brief, _notice(c))
            continue
        for edit in c.get("edits") or []:
            done = _apply_edit(brief, edit)
            if done:
                log.append(f"{bid[:8]} {product_of(c)} {done} ({c.get('date')})")
        _add_notice(brief, _notice(c))
    return log


def unapplied_brief(brief: dict[str, Any] | None,
                    corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Brief corrections whose wrong text (or withdrawn audio) is still served."""
    if not brief:
        return []
    corr = load() if corrections is None else corrections
    bid = str(brief.get("id") or "")
    out: list[str] = []
    for c in _brief_entries(corr, bid):
        if product_of(c) == "radio":
            if any(brief.get(k) for k in AUDIO_FIELDS) or not brief.get("audio_withdrawn"):
                out.append(f"{c.get('id')}: the withdrawn episode is still offered")
            continue
        for edit in c.get("edits") or []:
            probe = copy.deepcopy(brief)
            if _apply_edit(probe, edit):
                out.append(f"{c.get('id')}: {edit.get('field')}: "
                           f"{(edit.get('find') or edit.get('regex'))[:50]!r}")
    return out


def corrected_texts(corrections: list[dict[str, Any]] | None = None,
                    products: Iterable[str] = ("brief", "opinion")) -> list[tuple[str, str]]:
    """(correction id, removed text) for every literal a text correction took
    out, so a gate can assert no served file still carries it."""
    corr = load() if corrections is None else corrections
    out = []
    for c in corr:
        if product_of(c) not in tuple(products):
            continue
        for e in c.get("edits") or []:
            if e.get("find"):
                out.append((c.get("id"), e["find"].strip()))
    return out


def withdrawn_audio(corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Every served path a radio correction withdrew (verify_production 404s them)."""
    corr = load() if corrections is None else corrections
    out: list[str] = []
    for c in corr:
        if product_of(c) == "radio" and c.get("audio") == "withdrawn":
            out.extend(str(p) for p in c.get("audio_paths") or [])
    return out


def withdrawn_brief_ids(corrections: list[dict[str, Any]] | None = None) -> set[str]:
    corr = load() if corrections is None else corrections
    return {str(c.get("brief")) for c in corr
            if product_of(c) == "radio" and c.get("audio") == "withdrawn"}


# ---------------------------------------------------------------------------
# Deep Dive membership
# ---------------------------------------------------------------------------
def removed_members(cluster_id: str,
                    corrections: list[dict[str, Any]] | None = None) -> set[str]:
    """The article URLs a deepdive correction took off this cluster."""
    corr = load() if corrections is None else corrections
    out: set[str] = set()
    for c in corr:
        if product_of(c) == "deepdive" and str(c.get("cluster") or "") == str(cluster_id):
            out.update(str(u) for u in c.get("remove_members") or [])
    return out


def _deepdive_entries(corr, cluster_id):
    return [c for c in corr if product_of(c) == "deepdive"
            and str(c.get("cluster") or "") == str(cluster_id)]


def _round_mean(vals):
    return round(sum(vals) / len(vals)) if vals else None


def _spread(vals):
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return round((sum((v - m) ** 2 for v in vals) / len(vals)) ** 0.5, 1)


def _tiers(members):
    seen: dict[str, str] = {}
    for m in members:
        sid = m.get("source_id") or m.get("source_name")
        if sid and sid not in seen:
            seen[sid] = m.get("tier") or ""
    out: dict[str, int] = {}
    for t in seen.values():
        if t:
            out[t] = out.get(t, 0) + 1
    return out


def _measured(members):
    return [m for m in members if not m.get("lean_unscored") and m.get("lean") is not None]


# Derived fields of `bias_diversity` an archive row carries, each with the
# function that recomputes it from the member list. A field is rewritten only
# when recomputing it from the ORIGINAL members reproduces the stored value:
# the convention is checked before it is applied, so a field the run computed
# some other way (weighted, capped) is left alone and said so, never guessed.
_DERIVED = {
    "avg_political_lean": lambda ms: _round_mean([m["lean"] for m in _measured(ms)]),
    "avg_factual_rigor": lambda ms: _round_mean([m["rigor"] for m in ms if m.get("rigor") is not None]),
    "lean_spread": lambda ms: _spread([m["lean"] for m in _measured(ms)]),
    "lean_range": lambda ms: (round(max(v) - min(v)) if (v := [m["lean"] for m in _measured(ms)]) else 0),
    "tier_breakdown": _tiers,
    "analyzed_count": len,
    "lean_total_count": len,
    "lean_measured_count": lambda ms: len(_measured(ms)),
}


def outlet_count(members: list[dict[str, Any]]) -> int:
    """`source_count`'s convention: distinct outlets among the members
    (verified on the committed archive: it holds on every row whose members
    are not capped)."""
    return len({m.get("source_id") or m.get("source_name") for m in members
                if m.get("source_id") or m.get("source_name")})


def recount_members(row: dict[str, Any], before: list[dict[str, Any]],
                    state_names: frozenset | set = frozenset()) -> list[str]:
    """Recompute everything an archive row derives from its members, after a
    removal. `before` is the member list as it was, for the convention check."""
    from utils.bias_aggregation import compute_outlet_lean_histogram  # lazy: pure module
    members = row.get("members") or []
    log: list[str] = []
    row["member_count"] = len(members)
    row["source_count"] = outlet_count(members)
    bd = row.get("bias_diversity")
    if isinstance(bd, dict):
        for k, fn in _DERIVED.items():
            if k not in bd:
                continue
            try:
                if fn(before) == bd[k]:
                    bd[k] = fn(members)
                else:
                    log.append(f"{k} left as stored (not recomputable from members)")
            except (TypeError, ValueError, KeyError):
                log.append(f"{k} left as stored")
        meas = _measured(members) or members
        votes = [{"outlet": m.get("source_name") or m.get("source_id") or m.get("url"),
                  "name": m.get("source_name") or m.get("source_id"),
                  "lean": m["lean"],
                  "state_affiliated": str(m.get("source_name") or "").strip().lower() in state_names}
                 for m in meas if m.get("lean") is not None]
        if votes:
            h = compute_outlet_lean_histogram(votes)
            if row.get("polarization") is not None and row.get("polarization") == bd.get("polarization"):
                row["polarization"] = h["polarization"]
            bd.update(h)
    return log


def apply_members(rows: Iterable[dict[str, Any]], key: str = "source_cluster_id",
                  corrections: list[dict[str, Any]] | None = None,
                  state_names: frozenset | set = frozenset()) -> list[str]:
    """Apply every deepdive correction to the archive rows it names."""
    corr = load() if corrections is None else corrections
    log: list[str] = []
    for row in rows:
        cid = str(row.get(key) or "")
        entries = _deepdive_entries(corr, cid)
        if not entries:
            continue
        drop = set().union(*(set(c.get("remove_members") or []) for c in entries))
        before = list(row.get("members") or [])
        after = [m for m in before if m.get("url") not in drop]
        if len(after) != len(before):
            row["members"] = after
            notes = recount_members(row, before, state_names)
            log.append(f"{cid[:8]} deepdive: {len(before) - len(after)} member(s) removed, "
                       f"source_count {row['source_count']}, member_count {row['member_count']}"
                       + (f" ({'; '.join(notes)})" if notes else ""))
        for c in entries:
            _add_notice(row, _notice(c))
    return log


def unapplied_members(rows: Iterable[dict[str, Any]], key: str = "source_cluster_id",
                      corrections: list[dict[str, Any]] | None = None) -> list[str]:
    corr = load() if corrections is None else corrections
    out: list[str] = []
    for row in rows:
        cid = str(row.get(key) or "")
        drop = removed_members(cid, corr)
        if not drop:
            continue
        left = [m.get("url") for m in row.get("members") or [] if m.get("url") in drop]
        if left:
            out.append(f"{cid[:8]}: {len(left)} removed member(s) still listed")
        if row.get("member_count") != len(row.get("members") or []):
            out.append(f"{cid[:8]}: member_count {row.get('member_count')} != "
                       f"{len(row.get('members') or [])} members")
        if row.get("source_count") != outlet_count(row.get("members") or []):
            out.append(f"{cid[:8]}: source_count {row.get('source_count')} != "
                       f"{outlet_count(row.get('members') or [])} outlets")
    return out


# ---------------------------------------------------------------------------
# The archive repair (E-16)
# ---------------------------------------------------------------------------
# `standard.sentences` splits only where the stop is the last character before
# the space, so a sentence ending inside a quotation ('... "freedom
# fighters." Separately, the court ...') runs into the next one and E-16 never
# sees the opener. The page splits there (the Deep Dive renders it as its own
# sentence), so the repair does too: three archived cards carried an opener
# only in that position. The E-16 rule itself is unchanged here.
_AFTER_QUOTE = re.compile("(?<=[.!?][\"\u201d\u2019'])\\s+(?=[A-Z\u201c\"])")


def _repair_sentences(para: str) -> list[str]:
    from editorial import standard as std
    out: list[str] = []
    for s in std.sentences(para):
        out.extend(x for x in _AFTER_QUOTE.split(s) if x.strip())
    return out


def topic_shift_openers(summary: str) -> list[str]:
    """Every sentence of `summary` that opens on another story (E-16's
    pattern, on the finer split above)."""
    from editorial import standard as std
    return [s for para in re.split(r"\n\s*\n", summary or "")
            for s in _repair_sentences(para) if std.TOPIC_SHIFT_RE.match(s)]


def repair_topic_shift(summary: str, title: str = "") -> tuple[str, list[tuple[str, str]]]:
    """`summary` with every E-16 topic-shift sentence removed, and the
    sentences after it that never return to the card's own names.

    Returns (new_summary, [(sentence, why), ...]). Paragraph breaks are kept;
    an untouched summary is returned exactly as given.
    """
    from editorial import standard as std
    from editorial import derived_grounding as dg
    if not summary or not topic_shift_openers(summary):
        return summary, []
    before = dg._entities(title or "")
    cuts: list[tuple[str, str]] = []
    paras_out: list[str] = []
    for para in re.split(r"\n\s*\n", summary):
        kept: list[str] = []
        shifted = False
        for sent in _repair_sentences(para):
            if std.TOPIC_SHIFT_RE.match(sent):
                cuts.append((sent, "E-16 opens on another story"))
                shifted = True
                continue
            if shifted:
                if dg._entities(sent) & before:
                    shifted = False
                else:
                    cuts.append((sent, "E-16 continues the other story"))
                    continue
            kept.append(sent)
            before |= dg._entities(sent)
        if kept:
            paras_out.append(" ".join(kept))
    if not cuts:
        return summary, []
    return "\n\n".join(paras_out), cuts


def repair_archive(rows: Iterable[dict[str, Any]],
                   repair_date: str = ARCHIVE_REPAIR_DATE) -> list[str]:
    """Remove E-16 contamination from every archive row that carries it."""
    log: list[str] = []
    for row in rows:
        s = row.get("summary")
        if not isinstance(s, str):
            continue
        new, cuts = repair_topic_shift(s, row.get("title") or "")
        if not cuts:
            continue
        row["summary"] = new
        date = max(repair_date, str(row.get("printed_on") or "")[:10])
        row["auto_corrected"] = date
        _add_notice(row, {"date": date, "product": "card", "notice": ARCHIVE_REPAIR_NOTICE})
        log.append(f"{str(row.get('id') or '')[:8]} archive repair: {len(cuts)} sentence(s) "
                   f"({', '.join(sorted({w for _, w in cuts}))})")
    return log


# ---------------------------------------------------------------------------
# Publisher text the export serves (P2-10, security audit M5)
# ---------------------------------------------------------------------------
SUMMARY_CAP = 300


def cap_summary(text, cap: int = SUMMARY_CAP):
    """A served per-article summary, at most `cap` characters.

    Cut at the last sentence end inside the cap, else the last word boundary,
    and never with an ellipsis glyph: the reader sees fewer of the publisher's
    words, not a mark announcing the cut (and a "..." or an ellipsis character
    would be Void's punctuation inside someone else's sentence).
    """
    if not isinstance(text, str):
        return text
    t = " ".join(text.split())
    if len(t) <= cap:
        return t
    head = t[:cap]
    ends = [head.rfind(m) for m in (". ", "! ", "? ")]
    end = max(ends)
    if end >= cap // 3:
        return head[:end + 1]
    cut = head.rsplit(" ", 1)[0] if " " in head else head
    return cut.rstrip(" ,;:-\u2014\u2013.\u2026")
