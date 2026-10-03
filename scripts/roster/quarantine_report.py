#!/usr/bin/env python3
"""Why each quarantined feed is quarantined, counted by cause. Read only.

A feed is skipped once `consecutive_fetch_failures` reaches
`rss_fetcher.QUARANTINE_THRESHOLD`, and nothing un-quarantines it: a skipped feed
is never fetched, so it never succeeds. On 2026-10-01 that was 260 of 1,061
sources, 214 of them last tried on 2026-09-06, and the recorded causes could not
tell a rate limit from a dead URL (P2-6, rev 85). The fetcher now records the
cause on every failure (`rss_fetcher.FAILURE_CAUSES`, `http_<code>`); rows
quarantined before that carry the old coarse statuses, which this report names
as legacy rather than guessing what they were.

    VOID_SQLITE_PATH=pipeline_state.db python3 scripts/roster/quarantine_report.py
    python3 scripts/roster/quarantine_report.py --db pipeline_state.db --list
    python3 scripts/roster/quarantine_report.py --db pipeline_state.db --json

It changes nothing. Releasing a feed is a decision per feed (retry it from a
different hour, fix its URL in data/sources.json, or drop it), made by a person.
Exit status is 1 when any quarantined row carries no recognisable cause, which
is the invariant tests/test_quarantine_causes.py holds.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

# The fetcher's constants, read from its source so this script needs none of the
# fetcher's dependencies (feedparser, defusedxml) to run.
_SRC = (ROOT / "pipeline" / "fetchers" / "rss_fetcher.py").read_text(encoding="utf-8")


def _const(name: str):
    import ast
    for node in ast.parse(_SRC).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(name)


THRESHOLD = _const("QUARANTINE_THRESHOLD")
FAILURE_CAUSES = _const("FAILURE_CAUSES")
LEGACY = {"http_4xx": "legacy: http 4xx, code not recorded",
          "http_5xx": "legacy: http 5xx, code not recorded"}


def cause_of(status: str | None) -> str:
    """The cause label for a stored last_fetch_status; 'unrecorded' when none."""
    if not status:
        return "unrecorded"
    if status in LEGACY:
        return LEGACY[status]
    if status.startswith("http_") and status[5:].isdigit() and len(status) == 8:
        return status
    if status in FAILURE_CAUSES:
        return status
    return "unrecorded"


def feed_class(rss_url: str | None) -> str:
    return "google_news" if rss_url and "news.google.com" in rss_url else "direct"


def report(conn: sqlite3.Connection, roster: list[dict] | None = None) -> dict:
    rows = conn.execute(
        """select slug, name, rss_url, consecutive_fetch_failures, last_fetch_at,
                  last_fetch_status
             from sources
            where coalesce(consecutive_fetch_failures, 0) >= ?
            order by slug""", (THRESHOLD,)).fetchall()
    total = conn.execute("select count(*) from sources").fetchone()[0]
    by_slug = {s.get("id"): s for s in (roster or [])}
    entries = []
    for slug, name, rss, cff, last_at, status in rows:
        r = by_slug.get(slug) or {}
        entries.append({
            "slug": slug, "name": name, "cause": cause_of(status), "status": status,
            "failures": cff, "last_tried": (last_at or "")[:10], "feed": feed_class(rss),
            # The roster's URL moved since the failures were counted: the counter
            # describes a feed that is no longer configured.
            "url_changed": bool(r.get("rss_url")) and r.get("rss_url") != rss,
            "on_roster": bool(r) if roster else None,
        })
    causes = collections.Counter(e["cause"] for e in entries)
    return {
        "threshold": THRESHOLD,
        "sources": total,
        "quarantined": len(entries),
        "by_cause": dict(causes.most_common()),
        "by_feed_class": dict(collections.Counter(e["feed"] for e in entries)),
        "by_last_tried": dict(sorted(collections.Counter(e["last_tried"] for e in entries).items())),
        "url_changed_since": [e["slug"] for e in entries if e["url_changed"]],
        "off_roster": [e["slug"] for e in entries if e["on_roster"] is False],
        "unrecorded": [e["slug"] for e in entries if e["cause"] == "unrecorded"],
        "entries": entries,
    }


def _roster() -> list[dict]:
    path = Path(os.environ.get("VOID_ROSTER_DATA") or ROOT / "data") / "sources.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return data if isinstance(data, list) else data.get("sources", [])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.environ.get("VOID_SQLITE_PATH"))
    ap.add_argument("--list", action="store_true", help="print every quarantined feed")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not a.db or not Path(a.db).exists():
        print("error: pass --db or set VOID_SQLITE_PATH to the state DB", file=sys.stderr)
        return 2
    rep = report(sqlite3.connect(a.db), _roster())
    if a.json:
        print(json.dumps(rep, indent=2))
    else:
        print(f"{rep['quarantined']} of {rep['sources']} sources quarantined "
              f"(>= {rep['threshold']} consecutive failures)\n")
        print("by cause:")
        for k, v in rep["by_cause"].items():
            print(f"  {v:5d}  {k}")
        print("\nby feed class: " + ", ".join(f"{k} {v}" for k, v in rep["by_feed_class"].items()))
        print("last tried:    " + ", ".join(f"{k or 'never'} {v}" for k, v in rep["by_last_tried"].items()))
        if rep["off_roster"]:
            print(f"\n{len(rep['off_roster'])} quarantined row(s) are no longer on the roster "
                  f"(retired; the fetcher never reads them)")
        if rep["url_changed_since"]:
            print(f"\n{len(rep['url_changed_since'])} quarantined feed(s) whose roster URL has "
                  f"changed since: " + ", ".join(rep["url_changed_since"][:20]))
        if a.list:
            print()
            for e in rep["entries"]:
                print(f"  {e['slug']:40s} {e['cause']:38s} {e['feed']:11s} "
                      f"x{e['failures']:<3} last {e['last_tried']}")
    if rep["unrecorded"]:
        print(f"\nFAIL  {len(rep['unrecorded'])} quarantined feed(s) carry no cause: "
              + ", ".join(rep["unrecorded"][:20]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
