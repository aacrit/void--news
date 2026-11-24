#!/usr/bin/env python3
"""The http-only allowlist for History source links holds exactly the hosts it
names, each with a reason and a checked date, and every consumer reads it.

TH-04 (scripts/verify_sections.py), the headless source-mark check
(frontend/scripts/verify-headless.mjs) and ThesisSourceLink.tsx all require
https on a source link, with one documented exception: a host verified to
serve the page only over http. The first was www.armenocide.de (2026-09-25),
the Gust edition of the German Foreign Office files, whose https resets and
whose .net mirror answers 404 on the document paths. A second host may not
slip in without its reason, and a ledger entry may cite http only on a host
in this list.

Run: python tests/test_insecure_origins.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "frontend/config/insecure-origins.json"
ALLOWED = {"www.armenocide.de"}
CONSUMERS = [
    ROOT / "scripts/verify_sections.py",
    ROOT / "frontend/scripts/verify-headless.mjs",
    ROOT / "frontend/app/history/components/ThesisSourceLink.tsx",
]


def main() -> int:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    hosts = cfg.get("hosts") or []
    fails = []
    names = {str(h.get("host")) for h in hosts}
    if names != ALLOWED:
        fails.append(f"allowlist holds {sorted(names)}; it may hold only {sorted(ALLOWED)}")
    for h in hosts:
        if len(str(h.get("reason") or "").split()) < 8:
            fails.append(f"{h.get('host')}: no reason of substance")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(h.get("checked") or "")):
            fails.append(f"{h.get('host')}: no checked date")
    for c in CONSUMERS:
        if "insecure-origins.json" not in c.read_text(encoding="utf-8"):
            fails.append(f"{c.relative_to(ROOT)} does not read the allowlist")
    # Every http free copy in every ledger is on an allowed host.
    for led in (ROOT / "data/history/evidence").glob("*/ledger.yaml"):
        for e in (yaml.safe_load(led.read_text(encoding="utf-8")) or {}).get("entries") or []:
            u = str((e.get("access") or {}).get("free_copy") or "")
            if u.startswith("http://") and u.split("/")[2] not in names:
                fails.append(f"{led.parent.name}/{e.get('id')}: http free copy on {u.split('/')[2]}, not in the allowlist")
    for f in fails:
        print("FAIL ", f)
    if fails:
        return 1
    print(f"PASS  insecure-origin allowlist: {sorted(names)}, each with a reason and a date; {len(CONSUMERS)} consumers read it; no ledger cites http elsewhere")
    return 0


if __name__ == "__main__":
    sys.exit(main())
