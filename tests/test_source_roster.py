#!/usr/bin/env python3
"""The roster must not disagree with itself about an outlet.

Written 2026-09-21, after the CEO asked why so many articles come back
"unscored" and the answer turned out to be partly a roster inconsistency
rather than a limit of the engine.

`political_lean.py` marks an article unscored only when the OUTLET has no
left/right placement AND the article's own words carry no signal. So an outlet
left at `unrated` silently removes every article it publishes from the lean
aggregate and from the Deep Dive spectrum. That is the right outcome for an
outlet nobody can place on a US-shaped axis. It is the wrong outcome for one
this roster has already placed 46 of its siblings on.

Measured when this file was written: Tagesschau (Germany, ARD, public
broadcaster) carried `center` + `state_affiliated`, while Deutsche Welle
(Germany, federal-tax-funded public international broadcaster) carried
`unrated` and no flag. Likewise NRK against Swissinfo, RTP against Radio
Prague, SVT against France 24, and Ghana News Agency against two Ghanaian
state-owned dailies in the same country. Seven rows, all of one class, none of
them a new editorial judgement: the convention was already written down 46
times and these rows had missed it.

WHAT THIS DOES NOT DO. It never demands a placement for an outlet whose
politics does not run on a left/right axis. 287 rows are still `unrated` after
the fix and they are meant to be: a Kenyan daily, an Indian paper, a Pakistani
broadsheet. Inventing a position for those would fabricate the measurement
this product exists to report honestly. The check is only that an outlet
DESCRIBED IN ITS OWN NOTES as state-owned or a public broadcaster is treated
the way this roster treats that class.

Stdlib only. No DB, no pipeline imports, no VOID_SQLITE_PATH.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "sources.json"

UNPLACED = {"unrated", "varies", ""}

#: Phrases in an outlet's OWN credibility_notes that put it in the class this
#: roster already rates: state or public ownership, or a national wire. Kept
#: narrow on purpose. "Government-critical" or "covers state policy" must not
#: match, so the pattern requires the ownership or the broadcaster itself.
PUBLIC_OWNERSHIP = re.compile(
    r"state[- ](?:owned|funded|run|controlled)"
    r"|publicly funded"
    r"|public (?:broadcast|service broadcast)"
    r"|national (?:broadcaster|news agency)"
    r"|state (?:news agency|wire)"
    r"|government[- ](?:owned|funded)"
    r"|broadcasting corporation"
    r"|international broadcaster"
    r"|\bczech radio\b",
    re.I,
)

#: An outlet may be described in these terms and still legitimately carry no
#: placement, with the reason. Empty today: every match is rated. A future
#: entry needs a sentence saying why the axis does not apply to it.
EXEMPT: dict[str, str] = {}


def load() -> list:
    return json.loads(ROSTER.read_text())


def check_public_outlets_are_placed(rows) -> list:
    """An outlet whose notes say state-owned/public must not sit at `unrated`."""
    out = []
    for s in rows:
        note = s.get("credibility_notes") or ""
        if not PUBLIC_OWNERSHIP.search(note):
            continue
        name = s.get("name", "?")
        if name in EXEMPT:
            continue
        baseline = str(s.get("political_lean_baseline") or "").lower().strip()
        if baseline in UNPLACED:
            out.append(
                f"{name} ({s.get('country','??')}) is described as "
                f"state-owned or a public broadcaster but carries "
                f"political_lean_baseline={s.get('political_lean_baseline')!r}. "
                f"Every article it publishes is therefore dropped from the lean "
                f"aggregate and the spectrum. This roster rates 46 outlets of "
                f"that class; place it, or add it to EXEMPT with the reason."
            )
    return out


def report_state_affiliated_spread(rows) -> list:
    """REPORTS, never fails. The roster is not consistent here and this is not
    the file that settles it.

    Written as an assertion first, which was a mistake worth recording. It
    flagged 25 outlets as missing `state_affiliated`, among them the BBC, CBC,
    NPR, Yle, AFP and Voice of America, and "fixing" them would have changed
    how the BBC is scored on an inference nobody had checked.

    The roster's dominant convention, read off the rows rather than guessed:
    state-FUNDED but editorially independent gets a real baseline and NO flag
    (Voice of America, "US federal government international broadcaster
    operated by USAGM", is center with no flag; so are BBC, CBC, Yle, NPR,
    AFP, DPA). The flag is for state media whose alignment is the dominant
    editorial signal (RT, CGTN, Xinhua, TASS, Gulf state press) plus a handful
    of democratic public broadcasters (SVT, NRK, RTP, Tagesschau, SABC,
    Agencia Brasil) which sit on the wrong side of that line.

    Which reading is right changes the score of ~25 major outlets, because
    `_delta_max_for` gives a flagged outlet a delta of 8 instead of the
    default. That is an editorial decision about what Void asserts, so it is
    in docs/OPEN-ITEMS.md for the CEO, and this function only prints the
    population so the number cannot quietly drift.
    """
    funded_unflagged = []
    for s in rows:
        note = s.get("credibility_notes") or ""
        if PUBLIC_OWNERSHIP.search(note) and not s.get("state_affiliated"):
            funded_unflagged.append(s.get("name", "?"))
    flagged = [s.get("name", "?") for s in rows if s.get("state_affiliated")]
    print(f"       {len(flagged)} outlets carry state_affiliated; "
          f"{len(funded_unflagged)} more are described as publicly funded and "
          f"do not. Which is correct is an open CEO question, not a defect: "
          f"see docs/OPEN-ITEMS.md.")
    return []


def check_flagged_outlets_are_placed(rows) -> list:
    """The converse: nothing carries state_affiliated AND no placement.

    The flag exists to anchor a score. On a row with no baseline it anchors
    nothing, and the analyzer's `unscored` rule explicitly excludes a
    state-affiliated outlet, so such a row would be neither placed nor
    honestly withheld.
    """
    out = []
    for s in rows:
        if not s.get("state_affiliated"):
            continue
        baseline = str(s.get("political_lean_baseline") or "").lower().strip()
        if baseline in UNPLACED:
            out.append(
                f"{s.get('name','?')} carries state_affiliated but "
                f"political_lean_baseline={s.get('political_lean_baseline')!r}: "
                f"it can be neither scored nor honestly withheld."
            )
    return out


def check_baselines_are_on_the_ladder(rows) -> list:
    """Every baseline is a rung political_lean.py's BASELINE_MAP knows.

    A typo resolves to 50 through BASELINE_MAP's default, which is
    indistinguishable on the page from an outlet assessed as centrist.
    """
    LADDER = {"far-left", "left", "center-left", "center", "center-right",
              "right", "far-right", "unrated", "varies"}
    out = []
    for s in rows:
        b = s.get("political_lean_baseline")
        if b is None:
            out.append(f"{s.get('name','?')} has no political_lean_baseline "
                       f"at all; BASELINE_MAP would resolve it to 50.")
        elif str(b).lower().strip() not in LADDER:
            out.append(f"{s.get('name','?')} has baseline {b!r}, not a rung of "
                       f"the ladder; BASELINE_MAP resolves it to 50 silently.")
    return out


def check_the_unrated_tail_is_deliberate(rows) -> list:
    """The remaining unrated rows are the axis's edge, not a backlog.

    Asserted as behaviour rather than a count: no outlet in a country whose
    national politics runs on the same left/right axis the roster measures may
    be left unplaced. Every anglosphere outlet was already placed when this
    was written (0 unrated, on a roster of 1,016 at the time), and that is
    the property worth keeping. The count is the date's, not today's; the
    assertion below reads the roster.
    """
    SAME_AXIS = {"US", "GB", "UK", "CA", "AU", "NZ", "IE"}
    out = []
    for s in rows:
        if s.get("country") not in SAME_AXIS:
            continue
        baseline = str(s.get("political_lean_baseline") or "").lower().strip()
        if baseline in UNPLACED:
            out.append(
                f"{s.get('name','?')} ({s.get('country')}) is unplaced, but its "
                f"country's politics runs on the axis this roster measures. "
                f"Unrated is for an outlet the axis does not fit, not for one "
                f"nobody has got to yet."
            )
    return out


CHECKS = (
    ("public outlets are placed", check_public_outlets_are_placed),
    ("state_affiliated spread (report only)", report_state_affiliated_spread),
    ("flagged outlets are placed", check_flagged_outlets_are_placed),
    ("baselines are on the ladder", check_baselines_are_on_the_ladder),
    ("the unrated tail is the axis's edge", check_the_unrated_tail_is_deliberate),
)


def main() -> int:
    rows = load()
    failures = []
    for name, fn in CHECKS:
        problems = fn(rows)
        if problems:
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"    - {p}")
            failures.extend(problems)
        else:
            print(f"[ ok ] {name}")

    unrated = sum(
        1 for s in rows
        if str(s.get("political_lean_baseline") or "").lower().strip() in UNPLACED
    )
    flagged = sum(1 for s in rows if s.get("state_affiliated"))
    if failures:
        print(f"\nFAILED: {len(failures)} roster inconsistency(ies)")
        return 1
    print(f"\nOK: {len(rows)} outlets, {flagged} state-affiliated, "
          f"{unrated} deliberately unplaced ({100 * unrated / len(rows):.1f}%, "
          f"none of them on the axis the roster measures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
