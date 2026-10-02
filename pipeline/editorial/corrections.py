"""Published corrections, applied at export so the database cannot undo them.

A printed card is permanent: `printed_stories` feeds `build-data/archive.json`,
which prerenders `/story/<id>/`, and the same text sits in `feed.json` until the
next run replaces the feed. Before this file there was no way to correct one.
Editing the committed JSON by hand lasts until the next export, which rewrites
`archive.json` from the state database, and the database still holds the error.

So a correction lives here, in `corrections.json`, and `export_static.py`
applies it to every row it writes, from any database, on every run. Each entry
names the card (its source cluster id), the date, the reason, and edits of
three kinds:

  find / replace   a literal substring of one field, replaced (or removed)
  remove           a list field's item, dropped when it contains this text
  regex / replace  a pattern, for a correction that applies to every card
                   ("cluster": "*"), such as a retired fallback string

An edit whose text is no longer present is skipped and said so: the card may
have been regenerated, and a correction must never write text of its own
into a card it cannot find. Pure, stdlib, no I/O beyond reading the file.
`tests/test_grounding.py` asserts the committed tree carries every correction.
"""
from __future__ import annotations

import json
import pathlib
import re
from typing import Any, Iterable

PATH = pathlib.Path(__file__).with_name("corrections.json")


def load(path: pathlib.Path | None = None) -> list[dict[str, Any]]:
    p = pathlib.Path(path or PATH)
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8")).get("corrections") or []


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


def apply_all(rows: Iterable[dict[str, Any]], key: str = "id",
              corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Apply every correction to the rows it names. Returns a log line per edit."""
    corr = load() if corrections is None else corrections
    if not corr:
        return []
    log: list[str] = []
    for row in rows:
        rid = str(row.get(key) or "")
        for c in corr:
            target = c.get("cluster") or ""
            if target != "*" and target != rid:
                continue
            for edit in c.get("edits") or []:
                done = _apply_edit(row, edit)
                if done:
                    log.append(f"{rid[:8]} {done} ({c.get('date')}: {c.get('reason', '')[:60]})")
    return log


def unapplied(rows: Iterable[dict[str, Any]], key: str = "id",
              corrections: list[dict[str, Any]] | None = None) -> list[str]:
    """Corrections whose wrong text is still present in `rows` (for the gate)."""
    corr = load() if corrections is None else corrections
    out: list[str] = []
    for row in rows:
        rid = str(row.get(key) or "")
        for c in corr:
            target = c.get("cluster") or ""
            if target != "*" and target != rid:
                continue
            for edit in c.get("edits") or []:
                probe = dict(row)
                if _apply_edit(probe, edit):
                    out.append(f"{rid[:8]} {edit.get('field', 'summary')}: "
                               f"{(edit.get('find') or edit.get('remove') or edit.get('regex'))[:50]!r}")
    return out


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
