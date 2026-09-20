"""The History script validators, each against a planted defect.

Every rule here exists because of a failure mode that would reach a listener's
ears. A rule that has only ever been run against clean copy is not a gate, it
is a comment, so each one is asserted twice: silent on a good script, and
firing on a script with exactly one thing wrong with it.

H-04 is the reason this file exists. It was matching the speaker's name as a
RAW SUBSTRING of the preceding narration, and "king" is inside "striking", so
a segment about being beaten without striking back counted as a segment that
had named Martin Luther King. The real script that exposed it passed the gate
while never naming him. The rule now matches on words.

Run: python tests/test_history_script.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from history.script_format import parse_script, validate_script   # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{': ' + detail if detail else ''}")


# A miniature event with everything the validators read: two perspectives by
# name, one sourced quote by a man and one by a woman.
EVENT = {
    "perspectives": [
        {"viewpoint": "Naval Command", "viewpoint_type": "victor"},
        {"viewpoint": "The Fishing Villages", "viewpoint_type": "vanquished"},
    ],
    "primary_source_excerpts": [
        {"text": "The sea was higher than the lighthouse and it did not stop.",
         "author": "Martin Luther King Jr.", "work": "A Letter", "date": "1961"},
        {"text": "We were told the water would never reach the second floor.",
         "author": "Amara Okonjo", "work": "Testimony", "date": "1962"},
    ],
}

CLEAN = """## OPEN
N: One sentence of narration to open on, which carries no claim at all.
N: A second line, because an opening is not one sentence.

## TITLE
N: A Title. Some Date.

## SCENE 1 | The harbour
N: A scene arrives late and leaves early, and this line is the whole of it.
N: A second line of the same scene, so the segment is not a fragment.

## DOCUMENT | Martin Luther King Jr. | A Letter | 1961
N: Martin Luther King wrote it down the same week.
M: The sea was higher than the lighthouse and it did not stop.

## REST

## PERSPECTIVE | Naval Command | victor
N: The first account is the navy's, and it is an argument about warning times.
N: It rests on the tide tables, which were published and which nobody read.

## PERSPECTIVE | The Fishing Villages | vanquished
N: The second account belongs to the people on the shore.
N: Amara Okonjo was in the upper room of a house that no longer exists.
F: We were told the water would never reach the second floor.

## TURN | What each one leaves out
N: The navy's account leaves out who was never told. The villages' account
N: leaves out that the tables were correct.

## CLOSE
N: The lighthouse is still there. The second floor is not.

## SAY
lighthouse = LITE-house
"""


def fails(script_text: str, event=None) -> set[str]:
    sc = parse_script(script_text, "test")
    return {f.id for f in validate_script(sc, event or EVENT) if f.level == "fail"}


def pad(text: str, minutes: float = 9.0) -> str:
    """H-07 measures length, so a fixture must be long enough to be legal or
    every other assertion drowns in a length failure."""
    from history.script_format import WPM, MUSIC_MINUTES
    need = int((minutes - MUSIC_MINUTES) * WPM) - len(text.split())
    if need <= 0:
        return text
    filler = "\n".join("N: " + " ".join(["filler"] * 12) for _ in range(need // 12 + 1))
    return text.replace("## REST\n", "## REST\n\n## SCENE 2 | Filler\n" + filler + "\n", 1)


CLEAN_LEGAL = pad(CLEAN)

# ---- the clean fixture is silent ---------------------------------------
check("clean fixture passes every rule", fails(CLEAN_LEGAL) == set(),
      str(fails(CLEAN_LEGAL)))

# ---- H-01 a quote that is not in the sources ----------------------------
invented = CLEAN_LEGAL.replace(
    "M: The sea was higher than the lighthouse and it did not stop.",
    "M: History will absolve the men who built the harbour wall.")
check("H-01 catches an invented quotation", "H-01" in fails(invented), str(fails(invented)))

# A quote TRIMMED for the ear is allowed: that is the whole reason the rule
# is word overlap rather than string equality.
trimmed = CLEAN_LEGAL.replace(
    "M: The sea was higher than the lighthouse and it did not stop.",
    "M: The sea was higher than the lighthouse.")
check("H-01 allows a quote trimmed for the ear", "H-01" not in fails(trimmed),
      str(fails(trimmed)))

# ---- H-02 the document voice outside a quoting segment ------------------
stray = CLEAN_LEGAL.replace(
    "## CLOSE\nN: The lighthouse is still there.",
    "## CLOSE\nM: The lighthouse is still there.")
check("H-02 catches the document voice in a CLOSE", "H-02" in fails(stray), str(fails(stray)))

# ---- H-04 the narration must NAME the speaker ---------------------------
unnamed = CLEAN_LEGAL.replace("N: Martin Luther King wrote it down the same week.",
                              "N: A witness wrote it down the same week.")
check("H-04 catches a quote whose speaker is never named",
      "H-04" in fails(unnamed), str(fails(unnamed)))

# THE REGRESSION. "king" is a substring of "striking". Narration that merely
# contains such a word has not named anybody, and the rule must say so.
substring = CLEAN_LEGAL.replace(
    "N: Martin Luther King wrote it down the same week.",
    "N: The crews were trained to take a beating without striking back.")
check("H-04 is not fooled by king inside striking",
      "H-04" in fails(substring), str(fails(substring)))

# A possessive still names the speaker, in either direction.
possessive = CLEAN_LEGAL.replace(
    "N: Martin Luther King wrote it down the same week.",
    "N: Martin Luther King's own account was written the same week.")
check("H-04 accepts a possessive form", "H-04" not in fails(possessive), str(fails(possessive)))

# Crediting the WRONG person is the same failure: the rule looks the speaker
# up from the data by matching the quote, so it catches a misattribution.
miscredit = CLEAN_LEGAL.replace(
    "N: Martin Luther King wrote it down the same week.",
    "N: Amara Okonjo wrote it down the same week.")
check("H-04 catches a quote credited to the wrong person",
      "H-04" in fails(miscredit), str(fails(miscredit)))

# ---- H-05 / H-06 structure ----------------------------------------------
no_close = CLEAN_LEGAL.replace("## CLOSE\n", "## ASIDE\n")
check("H-05 catches a missing CLOSE", "H-05" in fails(no_close), str(fails(no_close)))
no_turn = CLEAN_LEGAL.replace("## TURN | What each one leaves out", "## ASIDE")
check("H-06 catches an episode with no TURN", "H-06" in fails(no_turn), str(fails(no_turn)))

# ---- H-07 length ---------------------------------------------------------
check("H-07 catches a script that is too short", "H-07" in fails(CLEAN), str(fails(CLEAN)))

# ---- H-09 every account gets its own case -------------------------------
dropped = CLEAN_LEGAL.replace("## PERSPECTIVE | The Fishing Villages | vanquished",
                              "## ASIDE")
check("H-09 catches an account that is silently dropped",
      "H-09" in fails(dropped), str(fails(dropped)))

# A script may retitle an account in plainer words and still be giving it its
# own case: the rule compares word PREFIXES for exactly this reason, so a
# shortened title keeps passing.
retitled = CLEAN_LEGAL.replace("## PERSPECTIVE | The Fishing Villages | vanquished",
                               "## PERSPECTIVE | The villages | vanquished")
check("H-09 accepts a shortened title for the same account",
      "H-09" not in fails(retitled), str(fails(retitled)))

# And the documented edge, recorded here rather than wished away: the prefix
# is six characters, so a retitle that shares only a shorter root DOES fire.
# "fishermen" and "Fishing Villages" have four characters in common and the
# rule will not accept it. That is the conservative direction to fail in (the
# writer renames the segment, nobody ships an episode missing an account), and
# it is the same six-character floor that stops "engineer" matching "engine".
reworded = CLEAN_LEGAL.replace("## PERSPECTIVE | The Fishing Villages | vanquished",
                               "## PERSPECTIVE | The fishermen | vanquished")
check("H-09 is conservative about a title sharing only a short root",
      "H-09" in fails(reworded), str(fails(reworded)))

# ---- every committed script still passes --------------------------------
import yaml   # noqa: E402

scripts = sorted((ROOT / "data" / "history" / "scripts").glob("*.txt"))
check("there are committed scripts to check", len(scripts) > 0)
for f in scripts:
    event_file = ROOT / "data" / "history" / "events" / f"{f.stem}.yaml"
    check(f"{f.stem}: has an event", event_file.exists())
    if not event_file.exists():
        continue
    sc = parse_script(f.read_text(), f.stem)
    found = [x for x in validate_script(sc, yaml.safe_load(event_file.read_text()))
             if x.level == "fail"]
    check(f"{f.stem}: passes every rule", not found,
          "; ".join(f"{x.id} {x.detail}" for x in found))

if failures:
    print("\n".join(f"FAIL  {f}" for f in failures))
    print(f"\n{len(failures)} History script failure(s)")
    raise SystemExit(1)
print(f"PASS  H-01..H-09 against planted defects, and {len(scripts)} committed scripts")
