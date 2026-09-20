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

from history.script_format import (  # noqa: E402
    parse_script, validate_script, _overhead_minutes,
)

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
        # The record's own speaker field says these are NOT the admiral's words.
        {"text": "The tables were right and the messengers were slow.",
         "author": "Admiral Rosa Vane (paraphrased)", "work": "Summary", "date": "1962"},
        # Secondhand: the record names who wrote it down, not who said it.
        {"text": "The horizon went white before the sound arrived.",
         "author": "A keeper, as reported by Silvia Vane", "work": "History", "date": "1970"},
        # NOT secondhand: "via" is inside "Silvia", and she is a real witness.
        {"text": "The boats were gone before anyone counted them.",
         "author": "Silvia Vane", "work": "History", "date": "1970"},
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


def pad_to_words(text: str, words: int) -> str:
    """Pad to an exact spoken-word count, for tests that need to straddle a
    threshold. Runtime-targeted padding cannot do that: the filler is added in
    blocks and the block rounding moves the result by tens of words, which is
    more than the gap between two narrators' runtimes."""
    from history.script_format import parse_script
    need = words - parse_script(text, "pad").words
    if need <= 0:
        return text
    filler = "\n".join("N: " + " ".join(["filler"] * 12) for _ in range(need // 12))
    rem = need % 12
    if rem:
        filler += "\nN: " + " ".join(["filler"] * rem)
    return text.replace("## REST\n", "## REST\n\n## SCENE 2 | Filler\n" + filler + "\n", 1)


def pad(text: str, minutes: float = 9.0) -> str:
    """H-07 measures length, so a fixture must be long enough to be legal or
    every other assertion drowns in a length failure."""
    from history.script_format import WPM, _overhead_minutes, parse_script
    # Size against the SAME model the validator uses, including this script's
    # own segment count, and including the one SCENE this function adds below.
    # Sizing against a flat music constant made every length fixture a lie the
    # moment overhead stopped being flat.
    segs = len(parse_script(text, "pad").segments) + 1
    need = int((minutes - _overhead_minutes(segs)) * WPM) - len(text.split())
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

# ---- H-07 measures the episode at the voice that will read it -----------
# One rate for four narrators is a two minute error at episode length, in
# opposite directions: bm_daniel reads a fifth faster than am_michael. A
# script sized against the average renders over the ceiling when the slow
# voice is cast, and nine minutes of rendering is the only other way to find
# out. cast() is deterministic from the event, so the rate is knowable up front.
from history.script_format import estimated_minutes, NARRATOR_WPM

_len = pad(CLEAN, 12.0)
_words = parse_script(_len, "t").words
# cast(): critical + a mass-death category -> am_michael (the slowest read);
# cultural -> bm_daniel (the fastest).
SLOW_EVENT = {"category": "genocide", "severity": "critical"}
FAST_EVENT = {"category": "cultural", "severity": "moderate"}
slow, slow_rate, slow_who = estimated_minutes(parse_script(_len, "t"), SLOW_EVENT)
fast, fast_rate, fast_who = estimated_minutes(parse_script(_len, "t"), FAST_EVENT)
check("the two events really do cast different narrators",
      slow_who == "am_michael" and fast_who == "bm_daniel", f"{slow_who} / {fast_who}")
check("H-07 gives the same script different runtimes for different narrators",
      abs(slow - fast) > 0.4, f"{slow:.2f} vs {fast:.2f}")
check("the slower narrator is the longer runtime", slow > fast, f"{slow:.2f} vs {fast:.2f}")

# The failure this exists for: a script sized to the average that renders over
# the ceiling because the slow voice was cast.
# Straddle deliberately: under the 15.5 audio gate at the catalogue average,
# over it when the slow voice is cast. That gap is ~0.5 min at this length, so
# the word count has to be exact.
long_script = pad_to_words(CLEAN, 2123)
mins_avg, _, _ = estimated_minutes(parse_script(long_script, "t"), None)
check("a script legal at the average rate is caught when the slow voice reads it",
      mins_avg <= 15.5 and "H-07" in fails(long_script, {**EVENT, **SLOW_EVENT}),
      f"avg {mins_avg:.2f} min, findings {fails(long_script, {**EVENT, **SLOW_EVENT})}")
check("the same script passes when the fast voice reads it",
      "H-07" not in fails(long_script, {**EVENT, **FAST_EVENT}),
      str(fails(long_script, {**EVENT, **FAST_EVENT})))

generic, rate, who = estimated_minutes(parse_script(_len, "t"), None)
_n_segs = len(parse_script(_len, "t").segments)
_overhead = _overhead_minutes(_n_segs)
check("estimated_minutes falls back to the catalogue average with no event",
      who == "the cast" and abs(generic - (_words / 145.0 + _overhead)) < 1e-9,
      f"{who} {rate}")
unknown, rate, _ = estimated_minutes(parse_script(_len, "t"), {"category": "x", "severity": "y"})
check("an unmeasured narrator degrades to the average rather than raising",
      rate in set(NARRATOR_WPM.values()) | {145.0}, str(rate))


# ---- H-11 a paraphrase is never read in the document voice --------------
# The failure this exists for reached a finished script: the record carried a
# line marked "(paraphrased)", H-01 was satisfied because the text really is in
# the data, and the episode introduced it with "her own summary was blunt" and
# read it aloud. That puts sentences in a real person's mouth. The rule asks
# only that the hedge be SAID, in the marker or in the narration.
paraphrase_as_speech = pad(CLEAN.replace("""## CLOSE""", """## DOCUMENT | Admiral Rosa Vane | Summary | 1962
N: Admiral Vane put it bluntly.
F: The tables were right and the messengers were slow.

## CLOSE"""))
check("H-11 catches a paraphrase read as the speaker's own words",
      "H-11" in fails(paraphrase_as_speech), str(fails(paraphrase_as_speech)))

spoken_hedge = pad(CLEAN.replace("""## CLOSE""", """## DOCUMENT | Admiral Rosa Vane | Summary | 1962
N: A line attributed to Admiral Vane puts it bluntly.
F: The tables were right and the messengers were slow.

## CLOSE"""))
check("H-11 accepts the same line when the narration says it is attributed",
      "H-11" not in fails(spoken_hedge), str(fails(spoken_hedge)))

marker_hedge = pad(CLEAN.replace("""## CLOSE""", """## DOCUMENT | Admiral Rosa Vane | Attributed summary | 1962
N: Admiral Vane put it bluntly.
F: The tables were right and the messengers were slow.

## CLOSE"""))
check("H-11 accepts the hedge in the DOCUMENT marker",
      "H-11" not in fails(marker_hedge), str(fails(marker_hedge)))

check("H-11 leaves an ordinary sourced quote alone", "H-11" not in fails(pad(CLEAN)),
      str(fails(pad(CLEAN))))

secondhand = pad(CLEAN.replace("""## CLOSE""", """## DOCUMENT | A keeper | History | 1970
N: The keeper said it plainly.
M: The horizon went white before the sound arrived.

## CLOSE"""))
check("H-11 catches a secondhand line read as the speaker's own",
      "H-11" in fails(secondhand), str(fails(secondhand)))

# The trap: matching the hedge as a raw substring makes "via" fire inside
# "Silvia", exactly as "king" once fired inside "striking" for H-04.
silvia = pad(CLEAN.replace("""## CLOSE""", """## DOCUMENT | Silvia Vane | History | 1970
N: Silvia Vane counted them herself.
F: The boats were gone before anyone counted them.

## CLOSE"""))
check("H-11 does not read 'via' inside 'Silvia' as a secondhand marker",
      "H-11" not in fails(silvia), str(fails(silvia)))


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
print(f"PASS  H-01..H-11 against planted defects, and {len(scripts)} committed scripts")


def test_check_script_prints_findings():
    """The checker must PRINT a finding, not crash on it.

    It shipped reading `Finding.message`, a field that does not exist, so it
    raised AttributeError on any script that carried even one finding. The exit
    code was still non-zero, so nothing passed that should not have, but the
    tool went mute exactly when it had something to say and handed a drafter a
    traceback instead of the reason. A drafter caught it, not a test.
    """
    import io, contextlib, subprocess, sys, pathlib
    root = pathlib.Path(__file__).resolve().parents[1]
    # apollo-11 carries a real H-10 warning, so it exercises the print path.
    out = subprocess.run(
        [sys.executable, str(root / "pipeline/history/check_script.py"), "apollo-11-moon-landing"],
        capture_output=True, text=True, cwd=root,
    )
    assert "Traceback" not in out.stderr, f"checker crashed:\n{out.stderr}"
    assert "warn H-10" in out.stdout, f"finding was not printed:\n{out.stdout}"
    print("PASS  check_script prints findings instead of crashing on them")


def test_quote_matches_its_best_source_not_its_first():
    """A weaker match earlier in the event file must not win.

    H-04 looks the speaker up by matching the quote, so taking the first source
    over the 0.6 threshold attributes the line to whoever happens to appear
    first. Both cases below are real, found by drafters on real event data, and
    both scored 1.000 against their true source and 0.667 against an earlier
    unrelated one.
    """
    import sys, pathlib as _p
    sys.path.insert(0, str(_p.Path(__file__).resolve().parents[1] / "pipeline"))
    from history.script_format import _best_source, _norm

    said = _norm("Both sides declared victory over a war that returned them "
                 "to the border where it began")
    sourced = [
        (_norm("War, war until victory."), "Ruhollah Khomeini"),          # earlier, weaker
        (_norm("Both sides declared victory over a war that returned them "
               "to the border where it began"), "Scholarly consensus"),   # later, exact
    ]
    assert _best_source(said, sourced)[1] == "Scholarly consensus"

    said = _norm("To the strongest")
    sourced = [
        (_norm("When Alexander saw the breadth of his domain, he wept, for "
               "there were no more worlds to conquer"), "Plutarch"),      # earlier, weaker
        (_norm("To the strongest."), "Alexander"),                        # later, exact
    ]
    assert _best_source(said, sourced)[1] == "Alexander"

    # And a quote with no real source still finds nothing.
    assert _best_source(_norm("a line nobody ever wrote down"), sourced) is None
    print("PASS  a quote resolves to its best source, not its first")


if __name__ == "__main__":
    test_check_script_prints_findings()
    test_quote_matches_its_best_source_not_its_first()
