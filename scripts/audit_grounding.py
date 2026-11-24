#!/usr/bin/env python3
"""Read every exported card and point against the index it was written from.

Gap 8 of docs/proposals/FACTUAL-RIGOR-PLAN-2026-10-02.md: the grounding index
(`frontend/build-data/grounding/`) was stored every run and read by nothing
outside a test. This runs after the export and before the data commit, and
puts every `feed.json` card (headline and summary) and every consensus and
divergence point through E-13, E-14 and E-16, against the record
`editorial.grounding.load_verifier` returns for its cluster.

What fails (exit 1):

  F-1  a CONFIRMED E-13, E-14 or E-16 finding on a shipped card or point.
       E-16 reads the text alone, so it is always confirmed. An absence (a
       number or a quotation in no source) is confirmed only against a
       format-3, pre-truncation record whose rows cover what the writer read
       (`pipeline/validation/rigor.evidence_state`).
  F-2  a fresh card (written this run, per the Stage 2 run counters) whose
       record was not built before truncation, or a shipped card with no
       record at all.

What never fails: a finding against a format-2 record, an export-stage
record, or a record holding 300-character stubs for a card not written this
run. Those print as "cannot confirm", because an index of stubs proves
nothing absent. A number a point puts beside an outlet's name is printed as
advisory: outlets do not name themselves in their own sentences.

Cards past the displayed twenty (the rest of the bench) are audited and
reported, never failed: nobody reads them.

    python3 scripts/audit_grounding.py [--build-data DIR] [--quiet]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.validation import rigor  # noqa: E402


def run(build: pathlib.Path, quiet: bool = False) -> int:
    feed_path = build / "feed.json"
    if not feed_path.exists():
        print(f"FAIL  no feed at {feed_path}")
        return 1
    feed = json.loads(feed_path.read_text(encoding="utf-8"))
    run_counters = rigor.run_counters(build, feed.get("builtAt"))
    fresh = rigor.fresh_ids(run_counters)
    audit = rigor.audit_feed(feed, build, fresh)
    print(f"audit_grounding: feed builtAt {feed.get('builtAt')}, "
          f"{len(audit['cards'])} cards, fresh ids "
          f"{'unknown (no run counters for this feed)' if fresh is None else len(fresh)}")
    tallies: dict[str, int] = {}
    for r in audit["cards"]:
        scope = "shipped" if r["shipped"] else "bench"
        if not quiet or r["findings"]:
            print(f"  {r['id'][:8]} [{scope}] evidence: {r['state']}"
                  f" (format {r['format']}, stage {r['stage']})")
        for f in r["findings"]:
            key = f"{scope} {f['status']}"
            tallies[key] = tallies.get(key, 0) + 1
            mark = {"confirmed": "FAIL" if r["shipped"] else "bench",
                    "cannot confirm": "cannot confirm",
                    "advisory": "advisory"}[f["status"]]
            print(f"      [{mark}] {f['where']} {f['rule']}: {f['message'][:160]}")
    fl = rigor.floors(audit, run_counters, None,
                      {"ungated": [], "unapplied": 0}, label_wired=lambda p: True)
    print("  tallies: " + (", ".join(f"{k} {v}" for k, v in sorted(tallies.items()))
                           or "no findings"))
    bad = fl["F-1"] + fl["F-2"]
    for floor in ("F-1", "F-2"):
        print(f"  {floor}: {'pass' if not fl[floor] else 'FAIL'}")
        for line in fl[floor]:
            print(f"      {line}")
    if bad:
        print(f"\nFAIL  {len(bad)} grounding failure(s) on shipped cards")
        return 1
    print("\nPASS  no confirmed grounding finding on a shipped card or point")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="E-13/E-14/E-16 over the exported feed")
    ap.add_argument("--build-data", default=str(rigor.build_dir()))
    ap.add_argument("--quiet", action="store_true", help="print only cards with findings")
    a = ap.parse_args(argv)
    return run(pathlib.Path(a.build_data), a.quiet)


if __name__ == "__main__":
    raise SystemExit(main())
