"""The Orpheus word check: transcriber spellings pass, misreads still fail.

pipeline/briefing/asr_words.py judges every rendered History unit against
its script line (tts_orpheus_worker.judge). On 2026-10-06 units failed all
six takes on spellings of the transcriber, not misreads of the voice:

  names       edmond/edmund, aldwin/aldwyn, rolph/ralph, "la bouchere" for
              Labouchere: a capitalised mid-sentence script token heard one
              vowel off, or split, goes to the ear log
  spelling    recognising/recognizing folds (British -ising)
  numbers     "1.5 million" is "one and a half million"; "Charles X" and
              "Charles the 10th" are "Charles the Tenth"; "World War II" is
              "World War Two"

and these MUST still fail (Rule 1):

  brand       void/voigt, although Void is capitalised
  meaning     is/as, an inserted "thousand", a lowercase common word one
              vowel off, a sentence-initial capitalised word
  values      1.4 million against one and a half million, Charles IX
              against Charles the Tenth, a number word one letter off

Run: python tests/test_asr_words.py
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
warnings.filterwarnings("ignore")

from briefing.asr_words import align, judge_ops, norm_words, same_when_joined  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{': ' + detail if detail else ''}")


def judge(script: str, heard: str, names=()) -> tuple[set, set]:
    """One decode, judged exactly as the worker judges it."""
    ref, hyp = norm_words(script), norm_words(heard)
    if same_when_joined(ref, hyp):
        return set(), set()
    return judge_ops(script, align(ref, hyp), names)


def passes(name: str, script: str, heard: str, *, ear: bool = False) -> None:
    wrong, heard_names = judge(script, heard)
    check(f"{name} passes", not wrong, f"{script!r} heard {heard!r}: wrong={sorted(wrong, key=str)}")
    if ear:
        check(f"{name} is logged for the ear", bool(heard_names), f"{script!r} heard {heard!r}")


def fails(name: str, script: str, heard: str, expect: tuple | None = None) -> None:
    wrong, _ = judge(script, heard)
    check(f"{name} FAILS", bool(wrong), f"{script!r} heard {heard!r} was waved through")
    if expect is not None:
        check(f"{name} names its defect", expect in wrong, f"{expect} not in {sorted(wrong, key=str)}")


# -- proper-name spellings: to the ear, not failed --------------------------

def test_name_vowel_variants() -> None:
    passes("edmond/edmund", "The order went to Edmond Barton that night.",
           "The order went to Edmund Barton that night.", ear=True)
    passes("aldwin/aldwyn", "It was signed by Aldwin and two clerks.",
           "It was signed by Aldwyn and two clerks.", ear=True)
    passes("rolph/ralph", "The letter reached Rolph in March.",
           "The letter reached Ralph in March.", ear=True)


def test_name_split() -> None:
    # Beside another variant, so the whole-line join does not hide the split.
    passes("labouchere split", "The amendment was moved by Labouchere and Aldwin.",
           "The amendment was moved by La bouchere and Aldwyn.", ear=True)
    # The 2026-10-06 log: the name on the cast list, the split-off "la" failed.
    wrong, ear = judge("The amendment was moved by Labouchere and Aldwin.",
                       "The amendment was moved by La bouchere and Aldwyn.", names=["labouchere"])
    check("cast-listed name split: the inserted 'la' is not a defect", not wrong and ("I", None, "la") in ear,
          f"wrong={sorted(wrong, key=str)} ear={sorted(ear, key=str)}")


def test_name_join() -> None:
    passes("two-token name joined", "He sailed with De Witt and Rolph.",
           "He sailed with Dewitt and Ralph.", ear=True)


def test_british_ising() -> None:
    passes("recognising", "Nobody was recognising the border.", "Nobody was recognizing the border.")


def test_british_ence() -> None:
    # 2026-10-07 Cuban Missile Crisis render: "defence" heard "defense" on every take.
    passes("defence", "Its arms in Cuba were for defence only.", "Its arms in Cuba were for defense only.")


def test_british_doubled_l_and_titles() -> None:
    # 2026-10-07 Cuban Missile Crisis render.
    passes("signalling", "The destroyers were signalling to the submarine.", "The destroyers were signaling to the submarine.")
    passes("Mister", "Mister Khrushchev wrote again.", "Mr. Khrushchev wrote again.")
    fails("filling is not filing", "They were filling the forms.", "They were filing the forms.")
    fails("drop is not dropped", "The ships drop their speed.", "The ships dropped their speed.")


def test_hundreds_and_labourers() -> None:
    # 2026-10-09 Hiroshima render.
    passes("nineteen hundred feet", "It bursts at nineteen hundred feet.", "It bursts at 1,900 feet.")
    fails("eighteen hundred is not 1,900", "It bursts at eighteen hundred feet.", "It bursts at 1,900 feet.")
    passes("labourers", "Forced labourers were never counted.", "Forced laborers were never counted.")


def test_designators() -> None:
    # 2026-10-07: "a U two" heard "a U-2" on every take. Same value only.
    passes("U two", "Photographs from a U two, a reconnaissance plane.", "Photographs from a U-2, a reconnaissance plane.")
    passes("R twelve", "The R twelve warheads were on the ship.", "The R-12 warheads were on the ship.")
    fails("U three is not U two", "Photographs from a U two.", "Photographs from a U-3.")


# -- number formatting: same value, folded ----------------------------------

def test_fraction_formats() -> None:
    passes("1.5 million", "Some one and a half million people crossed.", "Some 1.5 million people crossed.")
    passes("2.25 thousand", "Two and a quarter thousand rifles.", "2.25 thousand rifles.")
    passes("hour and a half untouched", "It took an hour and a half.", "It took an hour and a half.")
    check("hour and a half stays words", norm_words("an hour and a half") == ["an", "hour", "and", "a", "half"],
          str(norm_words("an hour and a half")))


def test_regnal_formats() -> None:
    passes("Charles X", "The crown passed to Charles the Tenth.", "The crown passed to Charles X.")
    passes("Charles the 10th", "The crown passed to Charles the Tenth.", "The crown passed to Charles the 10th.")
    passes("Louis XIV", "Then came Louis the Fourteenth.", "Then came Louis XIV.")
    passes("World War II", "Before World War Two the line held.", "Before World War II the line held.")
    check("MD stays letters", norm_words("MD and CD") == ["md", "and", "cd"], str(norm_words("MD and CD")))


# -- must still fail --------------------------------------------------------

def test_brand_still_fails() -> None:
    fails("void/voigt", "This is Void News, History.", "This is Voigt News, History.", ("S", "void", "voigt"))


def test_meaning_still_fails() -> None:
    fails("is/as", "The toll is thirty five to a hundred thousand.",
          "The toll as thirty five to a hundred thousand.", ("S", "is", "as"))
    fails("inserted thousand", "Between thirty five to a hundred thousand died.",
          "Between thirty five thousand to a hundred thousand died.", ("I", None, "thousand"))
    fails("common word one vowel off", "They burned the mill at dawn.", "They burned the mall at dawn.",
          ("S", "mill", "mall"))
    fails("sentence-initial capital", "Rolph was not there. Nobody came.", "Ralph was not there. Nobody came.",
          ("S", "rolph", "ralph"))
    fails("name, two letters off", "The letter reached Rolph in March.", "The letter reached Rudolph in March.")
    fails("name split into a different word", "The amendment was moved by Labouchere.",
          "The amendment was moved by La butcher.")


def test_values_still_fail() -> None:
    fails("1.4 vs one and a half", "Some one and a half million people crossed.",
          "Some 1.4 million people crossed.", ("S", "five", "four"))
    fails("Charles IX vs the Tenth", "The crown passed to Charles the Tenth.", "The crown passed to Charles IX.")
    fails("Henry VII vs the Eighth", "Then came Henry the Eighth.", "Then came Henry VII.")
    fails("a capitalised number word", "They waited for Seven days.", "They waited for Seven dues.")
    fails("number word, vowel off", "It lasted ten weeks.", "It lasted tin weeks.")


def test_listed_names_unchanged() -> None:
    # The episode cast list still sends its tokens to the ear, as before.
    wrong, ear = judge("the man called orwell spoke", "the man called orwel spoke", names=["orwell"])
    check("cast-list name to the ear", not wrong and ear, f"wrong={wrong} ear={ear}")


def main() -> int:
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    if failures:
        for f in failures:
            print(f"FAIL {f}")
        print(f"{len(failures)} failure(s)")
        return 1
    print("test_asr_words: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
