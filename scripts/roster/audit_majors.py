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
    # "Sueddeutsche Zeitung": "Süddeutsche Zeitung" was aspirational: no such
    # row exists. The roster name it WOULD get now lives in
    # data/roster/majors-metadata-2026-09-22.json, which is read directly.
    "Hurriyet Daily News": "Hürriyet Daily News",
    "Frankfurter Allgemeine": "Frankfurter Allgemeine Zeitung",
    "Xinhua": "Xinhua (English)",
    "ANSA": "ANSA (English)",
    "Kyodo News": "Kyodo News",
    "The National (UAE)": "The National",
    "La Nacion (AR)": "La Nacion",
    "El Universal (MX)": "El Universal (English)",
    # "Publico (Portugal)": "Publico" pointed at a row that does not exist.
    "The Daily Star (Bangladesh)": "The Daily Star",
    # An identity alias for a row that does not exist. "The Daily Star" on
    # the roster is Bangladesh's, which is why Lebanon's is a real absence.
    "The Standard (Kenya)": "The Standard",
    # "BusinessDay (SA)": "BusinessDay" was here and pointed at a row that
    # does not exist. Once add_sources wrote the real row as
    # "BusinessDay (South Africa)", this hand entry overrode the correct
    # mapping and the audit went on reporting the outlet absent. A stale alias
    # is worse than a missing one: it wins over the file that knows.
    # tests/test_roster_config.py fails on a contradiction now.
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
    # "The Telegraph India": "The Telegraph (India)" was WORSE than dangling:
    # the roster row is named "The Telegraph India" exactly, so the alias
    # redirected a match that already worked to a name that does not exist,
    # and the audit reported an outlet it already had as absent. Found by
    # tests/test_roster_config.py the day that gate was written.
    "ABC News (Australia)": "ABC News (Australia)",
    "Novaya Gazeta Europe": "Novaya Gazeta Europe",

    # Found 2026-09-22 by checking each target's homepage HOST against the
    # roster's, which is a stronger signal than either name matching or my
    # memory: 20 targets the name audit called absent were already on the
    # roster under a different masthead spelling. Adding them as new rows would
    # have created 20 duplicate outlets, each double-counting its own copy on
    # the Bench. Listed here in the open so a wrong equivalence is arguable.
    "The Daily Telegraph": "The Telegraph",
    "Handelsblatt": "Handelsblatt Global",
    "Balkan Insight": "Balkan Insight (BIRN)",
    "Ekathimerini": "Kathimerini English",
    "The Wire": "The Wire (India)",
    "Republic World": "Republic TV",
    "Yomiuri Shimbun": "The Japan News (Yomiuri Shimbun)",
    "Global Times": "Global Times (China)",
    "VnExpress": "VnExpress International",
    "The Times of Israel": "Times of Israel",
    "IOL": "IOL (South Africa)",
    "Premium Times": "Premium Times Nigeria",
    "The Punch": "Punch Nigeria",
    "Vanguard": "Vanguard Nigeria",
    "Daily Nation": "Nation Africa",
    "Folha de S.Paulo": "Folha de Sao Paulo (English)",
    "Brazilian Report": "The Brazilian Report",
    "ABC News (Australia)": "ABC Australia",
    "RNZ": "RNZ News",
    # Found by an accent-folded substring scan run to FLAG possible
    # duplicates before adding rows, not to match automatically. Three
    # flags, one real: the roster carries the Chosun Ilbo already.
    # ("The Daily Star" on the roster is Bangladesh's, so Lebanon's is a
    # genuine absence; L'Express against Financial Express was noise.)
    "Chosun Ilbo": "The Chosun Ilbo (English)",
    # The Observer is a distinct Sunday title, and it publishes on
    # theguardian.com under Guardian feeds. A separate row would put the same
    # copy on the Bench twice under two mastheads, which is the syndication
    # double-count this roster work exists to remove. Counted as covered.
    "The Observer": "The Guardian",
}


def norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def metadata_aliases() -> dict:
    """target name -> roster name, read from every majors-metadata-*.json.

    `add_sources.py` deliberately disambiguates a generic masthead when it
    writes a row: the target "ABC" becomes "ABC (Spain)", "Focus" becomes
    "Focus (Germany)", "Stuff" becomes "Stuff (NZ)". Those names are how the
    roster avoids colliding with itself later, and they are also why the first
    run of this audit after the 2026-09-22 additions reported 31 absent while
    12 of the 31 had just been added under their disambiguated names. That is
    the same false-negative class as the 20 shared mastheads above, and it
    would have had someone add them a second time.

    So the mapping is READ from the file that created it rather than
    hand-copied into ALIAS. One file to update on the next round, not two.
    """
    out = {}
    folder = os.path.join(ROOT, "data", "roster")
    if not os.path.isdir(folder):
        return out
    for name in sorted(os.listdir(folder)):
        if not (name.startswith("majors-metadata-") and name.endswith(".json")):
            continue
        with open(os.path.join(folder, name), encoding="utf-8") as fh:
            doc = json.load(fh)
        for target, row in (doc.get("outlets") or {}).items():
            roster_name = row.get("roster_name")
            if roster_name and roster_name != target:
                out[target] = roster_name
    return out


def main() -> int:
    detail = "--detail" in sys.argv
    with open(os.path.join(ROOT, "data", "sources.json"), encoding="utf-8") as fh:
        srcs = json.load(fh)
    tiers_path = os.path.join(ROOT, "data", "roster", "tiers-2026-09-22.json")
    with open(tiers_path, encoding="utf-8") as fh:
        tiers = json.load(fh)
    tier_of = {r["name"]: k for k, v in tiers.items() for r in v}
    # A roster row absent from the tiers snapshot is NEW, not unknown. The
    # snapshot is built from the 41-day archive, and an outlet added today has
    # published nothing into it. Calling that "?" let the table report "no
    # right" for France after Le Point was added with a verified direct feed,
    # and calling it healthy would claim an archive record that does not exist.
    NEW = "N"
    exact = {norm(s["name"]): s["name"] for s in srcs}

    # The roster names a foreign-language outlet's English edition with a
    # suffix ("Le Monde (English)", "Al Arabiya English"). Trying those two
    # suffixes is a RULE, not a guess, and it cannot reproduce the
    # shared-masthead false positives the fuzzy version produced, because the
    # comparison is still exact after normalisation. Without it the audit
    # reported Le Monde, El Pais and eight others absent while they were on the
    # roster, which is a false negative that would have had me add duplicates.
    SUFFIXES = ("", " (English)", " English")

    # ALIAS wins: it holds the hand-checked equivalences, including the ones
    # that say "this target is covered by a row under another masthead". The
    # metadata mapping only fills in names this project itself created.
    lookup = dict(metadata_aliases())
    lookup.update(ALIAS)

    def find(target: str):
        a = lookup.get(target, target)
        for suffix in SUFFIXES:
            hit = exact.get(norm(a + suffix))
            if hit:
                return hit
        return None

    tot = have = missing = 0
    print(f"{'market':36s} {'tgt':>4} {'have':>5} {'A':>3} {'N':>3} {'C':>3} "
          f"{'D':>3} {'E':>3} {'gone':>5}  healthy sides")
    print("   A healthy in the 41-day archive · N added 2026-09-22, direct feed "
          "verified, no archive history yet · C/D/E thinner · gone absent")
    gaps = []
    for market, entries in MAJORS.items():
        got = []
        miss = []
        for name, side in entries:
            r = find(name)
            (got if r else miss).append((name, side, r))
        cnt = collections.Counter(tier_of.get(r, NEW) for _, _, r in got)
        hsides = {side for _, side, r in got if tier_of.get(r) == "A"}
        # A side whose only evidence is a row added today: real feeds, no
        # archive record. Reported as pending, never folded into healthy.
        psides = {side for _, side, r in got
                  if tier_of.get(r, NEW) == NEW} - hsides
        verdict = "".join(s for s in "LCR" if s in hsides) or "NONE"
        if psides:
            verdict += "+" + "".join(s for s in "LCR" if s in psides)
        flag = ""
        missing_wings = [w for w in ("L", "R") if w not in hsides]
        if missing_wings:
            pending = [w for w in missing_wings if w in psides]
            still = [w for w in missing_wings if w not in psides]
            if still and len(still) == 2:
                flag = "  <-- NO WING HEALTHY"
                gaps.append((market, "both wings"))
            elif still:
                flag = f"  <-- no {'left' if still[0] == 'L' else 'right'}"
                gaps.append((market, f"no {'left' if still[0] == 'L' else 'right'}"))
            if pending:
                sides = "/".join("left" if w == "L" else "right" for w in pending)
                flag += f"  ({sides} pending: added today, no archive yet)"
        print(f"{market:36s} {len(entries):>4} {len(got):>5} {cnt['A']:>3} "
              f"{cnt[NEW]:>3} {cnt['C']:>3} {cnt['D']:>3} {cnt['E']:>3} "
              f"{len(miss):>5}  {verdict:<6}{flag}")
        tot += len(entries); have += len(got); missing += len(miss)
        if detail:
            for name, side, r in got:
                print(f"      [{side}] {tier_of.get(r, NEW)}  {name}")
            for name, side, _ in miss:
                print(f"      [{side}] --  {name}   MISSING")
    print(f"\ntargets {tot}, on the roster {have}, absent {missing}")
    newly = sum(1 for _, v in tiers.items() for _ in v) and sum(
        1 for s in srcs if s["name"] not in tier_of)
    print(f"{newly} roster row(s) are newer than the tiers snapshot and count "
          f"as N, not as healthy: rebuild the tiers file to resolve them")
    print(f"markets whose HEALTHY subset is one-sided or empty, counting only "
          f"archive evidence: {len(gaps)} of {len(MAJORS)}")
    for m, why in gaps:
        print(f"    {m:36s} {why}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
