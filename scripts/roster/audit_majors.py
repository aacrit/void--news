#!/usr/bin/env python3
"""Audit the roster against scripts/roster/majors_target.py.

Reports, per market: which target outlets we have and how healthy their feed
is, which we are missing, and whether the HEALTHY subset covers both sides.
The last column is the one that matters, because a market covered from one side
publishes a lean and looks measured.

Matching is exact on a normalised name, plus an explicit alias table. The first
version of this audit used fuzzy substring matching and produced false
positives on shared mastheads (the UK Daily Telegraph matched the Australian
one, The Observer matched The Observer Uganda, India's The Wire matched The Wire
China). Aliases are listed in the open so a wrong match is visible rather than
silent.

    python3 scripts/roster/audit_majors.py            summary per market
    python3 scripts/roster/audit_majors.py --detail    plus every outlet
"""
from __future__ import annotations
import json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from majors_target import MAJORS  # noqa: E402

# target name -> exact roster name, where the two legitimately differ
ALIAS = {
    "Sueddeutsche Zeitung": "Süddeutsche Zeitung",
    "Hurriyet Daily News": "Hürriyet Daily News",
    "Frankfurter Allgemeine": "Frankfurter Allgemeine Zeitung",
    "Xinhua": "Xinhua (English)",
    "ANSA": "ANSA (English)",
    "Kyodo News": "Kyodo News",
    "The National (UAE)": "The National",
    "La Nacion (AR)": "La Nacion",
    "El Universal (MX)": "El Universal (English)",
    "Publico (Portugal)": "Publico",
    "The Daily Star (Bangladesh)": "The Daily Star",
    "The Daily Star (Lebanon)": "The Daily Star (Lebanon)",
    "The Standard (Kenya)": "The Standard",
    "BusinessDay (SA)": "BusinessDay",
    "Focus Taiwan": "Focus Taiwan (CNA)",
    "Al Arabiya": "Al Arabiya English",
    "The Korea Herald": "Korea Herald",
    "Caixin": "Caixin Global",
    "Tempo": "Tempo (English)",
    "Ukrainska Pravda": "Ukrainska Pravda (English)",
    "Kyiv Independent": "The Kyiv Independent",
    "Der Spiegel": "Der Spiegel (English)",
    "SWI Swissinfo.ch": "SWI Swissinfo.ch",
    "Aftenposten": "Aftenposten (English)",
    "Helsingin Sanomat": "Helsingin Sanomat (English)",
    "Corriere della Sera": "Corriere della Sera (English)",
    "Prothom Alo": "Prothom Alo (English)",
    "Daily Mirror (Sri Lanka)": "Daily Mirror Sri Lanka",
    "The Island (Sri Lanka)": "The Island (Sri Lanka)",
    "The EastAfrican": "The East African",
    "The Telegraph India": "The Telegraph (India)",
    "ABC News (Australia)": "ABC News (Australia)",
    "Novaya Gazeta Europe": "Novaya Gazeta Europe",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main() -> int:
    detail = "--detail" in sys.argv
    with open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8") as fh:
        srcs = json.load(fh)
    tiers_path = os.path.join(ROOT, "data", "roster", "tiers-2026-09-22.json")
    with open(tiers_path, encoding="utf-8") as fh:
        tiers = json.load(fh)
    tier_of = {r["name"]: k for k, v in tiers.items() for r in v}
    exact = {norm(s["name"]): s["name"] for s in srcs}

    def find(target: str):
        a = ALIAS.get(target, target)
        return exact.get(norm(a))

    tot = have = missing = 0
    print(f"{'market':36s} {'tgt':>4} {'have':>5} {'A':>3} {'C':>3} {'D':>3} {'E':>3} {'gone':>5}  healthy sides")
    gaps = []
    for market, entries in MAJORS.items():
        got = []
        miss = []
        for name, side in entries:
            r = find(name)
            (got if r else miss).append((name, side, r))
        cnt = collections.Counter(tier_of.get(r, "?") for _, _, r in got)
        hsides = {side for _, side, r in got if tier_of.get(r) == "A"}
        verdict = "".join(s for s in "LCR" if s in hsides) or "NONE"
        flag = ""
        if "L" not in hsides and "R" not in hsides:
            flag = "  <-- NO WING HEALTHY"
            gaps.append((market, "both wings"))
        elif "L" not in hsides:
            flag = "  <-- right only"
            gaps.append((market, "no left"))
        elif "R" not in hsides:
            flag = "  <-- left only"
            gaps.append((market, "no right"))
        print(f"{market:36s} {len(entries):>4} {len(got):>5} {cnt['A']:>3} {cnt['C']:>3} "
              f"{cnt['D']:>3} {cnt['E']:>3} {len(miss):>5}  {verdict:<4}{flag}")
        tot += len(entries); have += len(got); missing += len(miss)
        if detail:
            for name, side, r in got:
                print(f"      [{side}] {tier_of.get(r,'?')}  {name}")
            for name, side, _ in miss:
                print(f"      [{side}] --  {name}   MISSING")
    print(f"\ntargets {tot}, on the roster {have}, absent {missing}")
    print(f"markets whose HEALTHY subset is one-sided or empty: {len(gaps)} of {len(MAJORS)}")
    for m, why in gaps:
        print(f"    {m:36s} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
