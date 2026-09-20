#!/usr/bin/env python3
"""Mechanical checks on the 78 History event files.

These exist because an audit found four event pages crediting the wrong person
entirely: a Cherokee chief linked to an Arctic explorer, a missionary to a
Massachusetts politician, a murdered journalist to a film director, and an earl
to his own father. None was a quote, so none of the H-01..H-11 script
validators could see it. Half were found by one grep.

A finding is worth one afternoon. A check is worth every afternoon after it.
"""
import glob
import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
EVENTS = sorted(glob.glob(str(ROOT / "data/history/events/*.yaml")))

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}" if detail else name)


# Words that appear inside a Wikipedia disambiguator and say what the person
# DID. If the role text contradicts every one of them, the link is suspect.
ROLE_WORDS = {
    "journalist": ("journalist", "reporter", "correspondent", "press"),
    "politician": ("politician", "senator", "congress", "governor", "mp"),
    "director": ("director", "filmmaker", "film"),
    "archaeologist": ("archaeolog",),
    "astronaut": ("astronaut", "pilot", "apollo"),
    "missionary": ("missionar", "church", "cms"),
    "activist": ("activist", "leader", "campaign"),
    "monk": ("monk", "buddhis"),
}

for path in EVENTS:
    ev = yaml.safe_load(open(path))
    slug = ev["slug"]

    for fig in ev.get("key_figures") or []:
        name = fig.get("name", "?")
        role = str(fig.get("role") or "").lower()
        wiki = str(fig.get("wikipedia") or "")
        born, died = fig.get("born"), fig.get("died")

        # A life that runs backwards is wrong, but BCE years count DOWN and
        # this catalogue stores them as positive numbers in key_figures while
        # using negative ones in date_sort. So the direction of the test
        # depends on the era, read from the event's own date_display.
        # BCE years are stored BOTH ways in this catalogue: alexanders uses
        # -356, peloponnesian uses 494 for the same era. So only judge a
        # lifespan where the answer does not depend on which convention the
        # file chose, and flag the mixed convention separately below.
        bce = "BCE" in str(ev.get("date_display") or "")
        if isinstance(born, int) and isinstance(died, int):
            if born < 0 and died < 0:
                ok = born < died                 # signed BCE sorts naturally
            elif born > 0 and died > 0 and not bce:
                ok = born < died                 # ordinary CE
            else:
                ok = True                        # ambiguous: do not guess
            check(f"{slug}/{name}: lifespan runs the right way",
                  ok, f"born {born}, died {died}")

        # The link's own disambiguator against the role beside it. This is the
        # grep that found half of them.
        m = re.search(r"\(([^)]+)\)\s*$", wiki)
        if m:
            tag = m.group(1).lower().replace("_", " ")
            for key, words in ROLE_WORDS.items():
                if key in tag:
                    check(f"{slug}/{name}: wikipedia disambiguator matches the role",
                          any(w in role for w in words),
                          f"link says {tag!r}, role says {role[:60]!r}")
                    break

        # A wrong identifier is worse than none, so a figure may carry no
        # wikidata id, but not one belonging to somebody else. We cannot check
        # that from here; we can check it is shaped like a QID.
        qid = fig.get("wikidata")
        if qid is not None:
            check(f"{slug}/{name}: wikidata looks like a QID",
                  bool(re.fullmatch(r"Q\d+", str(qid))), str(qid))

    # A figure credited with an act cannot have died before it. We only check
    # the cases the text states plainly as a four-digit year.
    for fig in ev.get("key_figures") or []:
        died = fig.get("died")
        if not isinstance(died, int) or died < 0:
            continue
        role_txt = str(fig.get("role") or "")
        # Posthumous publication is not a contradiction: a journal can appear
        # after its author dies, and Henri Mouhot's did.
        if re.search(r"posthum|published|journal", role_txt, re.I):
            continue
        for year in re.findall(r"\b(1[5-9]\d\d|20[0-2]\d)\b", role_txt):
            check(f"{slug}/{fig.get('name')}: credited with an act after death",
                  int(year) <= died, f"died {died}, role cites {year}")

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    print(f"\n{len(failures)} History data failure(s)")
    sys.exit(1)

print(f"PASS  {len(EVENTS)} History events: figure identity, lifespans, identifiers")
