#!/usr/bin/env python3
"""Regenerate frontend/config/roster.json from data/sources.json.

WHY THIS EXISTS. The roster's size was hand-written in nine frontend files
plus the served manifest, four docs, two pipeline modules and two tests. Rule 1
in CLAUDE.md calls a number that goes stale a future error wherever a durable
formulation exists, and one already existed for the feed size:
`frontend/config/feed.json`, read through `frontend/app/lib/feedConfig.ts`,
whose header says in as many words "never restate these numbers as literals in
a component". The source count restated them anyway, in fifteen places, which
is the same defect the Weekly shipped when the site said "50 stories" for two
weeks after the feed became 20.

Two integers, not the roster itself: `data/sources.json` is over a megabyte and
importing it into a client component would ship the whole roster to every
reader to print one number.

`tests/test_roster_config.py` asserts this file agrees with the roster, because
a generated file nobody checks is just a sixteenth place to be wrong.

    python3 scripts/roster/emit_roster_config.py            write it
    python3 scripts/roster/emit_roster_config.py --check     exit 1 if stale
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
ROSTER = ROOT / "data" / "sources.json"
OUT = ROOT / "frontend" / "config" / "roster.json"


# The three tiers, rendered as exact counts on /about and /sources. They were
# literals too (43 / 373 / 600), and adding 47 international outlets would have
# left three served pages asserting 373 while the roster held 420. A breakdown
# that does not sum to its own total is the kind of error a reader can check.
TIERS = ("us_major", "international", "independent")


def counts() -> dict[str, int]:
    rows = json.loads(ROSTER.read_text(encoding="utf-8"))
    out = {
        "sources": len(rows),
        "countries": len({r["country"] for r in rows if r.get("country")}),
    }
    for tier in TIERS:
        out[tier] = sum(1 for r in rows
                        if str(r.get("tier") or "").lower() == tier)
    # A row in no known tier would make the breakdown quietly not add up.
    placed = sum(out[t] for t in TIERS)
    if placed != out["sources"]:
        raise SystemExit(
            f"{out['sources'] - placed} roster row(s) carry a tier outside "
            f"{TIERS}; the breakdown would not sum to the total")
    return out


def main() -> int:
    live = counts()
    if "--check" in sys.argv:
        try:
            on_disk = json.loads(OUT.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"FAIL  {OUT.relative_to(ROOT)}: {type(exc).__name__}")
            return 1
        stale = {k: (on_disk.get(k), v) for k, v in live.items()
                 if on_disk.get(k) != v}
        if stale:
            for k, (was, now) in stale.items():
                print(f"FAIL  {k}: config says {was}, the roster holds {now}")
            return 1
        print(f"PASS  roster config matches: {live['sources']} sources, "
              f"{live['countries']} countries")
        return 0

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(live, indent=2) + "\n", encoding="utf-8")
    # The SERVED manifest carries the same sentence and is not a component, so
    # nothing imports the config into it. It is mechanical JSON, so it is
    # rewritten here rather than left to be remembered: the count a browser
    # installs the app with was never checked at all until 2026-09-22.
    man = ROOT / "frontend" / "public" / "manifest.json"
    if man.exists():
        text = man.read_text(encoding="utf-8")
        fixed = re.sub(r"\b\d{1,2},?\d{3}(?= sources\b)",
                       f"{live['sources']:,}", text)
        if fixed != text:
            man.write_text(fixed, encoding="utf-8")
            print(f"updated {man.relative_to(ROOT)}")
    print(f"wrote {OUT.relative_to(ROOT)}: {live['sources']} sources, "
          f"{live['countries']} countries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
