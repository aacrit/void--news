"""Radio rundown: parser, validators and the spoken-text normaliser. No LLM.

    python tests/test_radio_script.py

Pattern (as tests/test_verify_gate.py): a clean fixture must pass, then one
planted defect per validator must fire exactly that validator id.
"""

from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.radio_script_generator import (  # noqa: E402
    RundownContext, parse_rundown, validate_rundown, build_radio_prompt,
    generate_radio_rundown, SIGN_ON_PREFIX, CLOSE_PREFIX, THROW_LINE,
)
from briefing.spoken_text import (  # noqa: E402
    normalize_for_speech, spoken_numbers, expand_initialisms, apply_say, spoken_date,
    ordinal_words, year_words, has_quotation_marks,
)

FIXTURE = ROOT / "tests" / "fixtures" / "radio_rundown_2026-09-18.txt"
FEED = ROOT / "frontend" / "build-data" / "feed.json"
DATE = datetime.date(2026, 9, 18)

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        failures.append(msg)
        print(f"  FAIL {msg}")


def top20() -> list[dict]:
    if FEED.exists():
        rows = json.loads(FEED.read_text(encoding="utf-8"))["clusters"][:20]
        # The fixture names today's ids; if the committed feed has moved on,
        # pin the four lead ids + kicker id so the test stays deterministic.
    else:
        rows = []
    ids = [
        "d3afa900-ea54-4eb8-b95e-f6ed157317a3", "b4a7fae8-a1cf-44fc-8496-6fa90ec4aa34",
        "e88cab6b-4e17-4e01-b0d5-349eb47f184e", "955f8f75-26de-4c70-9f77-2ee838e2adc1",
    ]
    if not rows or [r["id"] for r in rows[:4]] != ids:
        rows = [{"id": i, "title": f"story {n}", "disaster_severity": 0} for n, i in enumerate(ids, 1)]
        rows += [{"id": f"00000000-0000-0000-0000-0000000000{n:02d}", "title": f"story {n}", "disaster_severity": 0}
                 for n in range(5, 15)]
        rows.append({"id": "72de16f4-806b-4be1-a767-811ee56a6daf", "title": "Hong Kong AI chief", "disaster_severity": 0})
        rows += [{"id": f"00000000-0000-0000-0000-0000000001{n:02d}", "title": f"story {n}", "disaster_severity": 0}
                 for n in range(16, 21)]
    return rows


def ctx(rows=None, **kw) -> RundownContext:
    return RundownContext(top20=rows or top20(), has_editorial=True, date_spoken=spoken_date(DATE), **kw)


def ids_of(report) -> set[str]:
    return {f.id for f in report.findings if f.level == "fail"}


def test_clean_fixture() -> str:
    raw = FIXTURE.read_text(encoding="utf-8")
    r = parse_rundown(raw)
    rep = validate_rundown(r, ctx())
    check(rep.passed, f"clean fixture must pass: {[f.as_dict() for f in rep.failures]}")
    check(len(r.story_segments()) == 4, "four stories")
    check(r.get("FINALLY") is not None, "kicker present on a calm day")
    check(850 <= r.words <= 1150, f"news words in budget ({r.words})")
    check(0.35 <= rep.metrics["speaker_share_a"] <= 0.65, "speaker balance")
    check(r.say.get("Carney") == "KAR-nee", "SAY parsed")
    # round-trip
    r2 = parse_rundown(r.to_text())
    check([s.kind for s in r2.segments] == [s.kind for s in r.segments], "to_text round-trips")
    check(r2.words == r.words, "to_text keeps every word")
    return raw


def test_planted_defects(raw: str) -> None:
    cases = {
        "R-01": raw.replace(f"A: {SIGN_ON_PREFIX}", "A: Good morning, and welcome."),
        "R-02": raw.replace("has called the idea a hostile act", 'called it a "hostile act"'),
        "R-04": raw.replace("issued the order on Thursday", "issued the order at 4 p.m. Thursday"),
        "R-05": raw.replace("A: To South America.", "A: And finally, to South America.") if "A: To South America." in raw
                else raw.replace("B: To South America.", "B: And finally, to South America."),
        "R-08": raw.replace("955f8f75-26de-4c70-9f77-2ee838e2adc1", "e88cab6b-4e17-4e01-b0d5-349eb47f184e"),
        "R-12": raw.replace("B: To the markets.", "A: To the markets."),
    }
    for expect, text in cases.items():
        rep = validate_rundown(parse_rundown(text), ctx())
        fired = ids_of(rep)
        check(expect in fired, f"planted {expect} must fire (fired {sorted(fired)})")
    # R-06 story budget: gut STORY 3 to one line
    gutted = raw.split("## STORY 3")[0] + "## STORY 3 | e88cab6b-4e17-4e01-b0d5-349eb47f184e | X\nA: One line only.\n\n## STORY 4" + raw.split("## STORY 4")[1]
    rep = validate_rundown(parse_rundown(gutted), ctx())
    check("R-06" in ids_of(rep), "gutted story fails the budget")
    # R-09: disaster lead suppresses the kicker
    rows = top20()
    rows[0] = dict(rows[0], disaster_severity=0.9)
    rep = validate_rundown(parse_rundown(raw), ctx(rows))
    check("R-09" in ids_of(rep), "kicker on a disaster day fails R-09")
    # R-10: give every line to A
    lopsided = raw.replace("\nB: ", "\nA: ")
    rep = validate_rundown(parse_rundown(lopsided), ctx())
    check("R-10" in ids_of(rep), "one voice reading everything fails R-10")
    # R-03 numerals are a warning, not a failure
    rep = validate_rundown(parse_rundown(raw.replace("thirty-one tonnes", "31 tonnes")), ctx())
    check(rep.passed and any(f.id == "R-03" for f in rep.findings), "numerals warn but pass")
    # R-07 trailing attribution warns
    rep = validate_rundown(parse_rundown(raw.replace(
        "Carney says closer ties with Europe would stop any single country from controlling Canada's markets or undermining its sovereignty.",
        "Closer ties with Europe would stop any single country from controlling Canada's markets, Carney said.")), ctx())
    check(any(f.id == "R-07" for f in rep.findings), "trailing attribution warns")


def test_parser_tolerance() -> None:
    messy = """Some preamble the model added.
### OPEN:
**A:** From Void News, this is On Air. It's Friday, September eighteenth.
## STORY 1 | Canada turns | d3afa900-ea54-4eb8-b95e-f6ed157317a3
A: First line
that wraps onto a second line.
B - one fact.
## SAY
Carney = KAR-nee
junk line
"""
    r = parse_rundown(messy)
    check([s.kind for s in r.segments] == ["OPEN", "STORY"], f"kinds {[s.kind for s in r.segments]}")
    check(r.segments[0].turns[0].text.startswith(SIGN_ON_PREFIX), "bold A: tag parsed")
    st = r.segments[1]
    check(st.cluster_id == "d3afa900-ea54-4eb8-b95e-f6ed157317a3", "uuid found even when fields are swapped")
    check(st.turns[0].text == "First line that wraps onto a second line.", f"wrapped line joined: {st.turns[0].text!r}")
    check(st.turns[1].speaker == "B" and st.turns[1].text == "one fact.", "B - dash tag parsed")
    check(r.say == {"Carney": "KAR-nee"}, "SAY junk ignored")
    check(parse_rundown("").segments == [], "empty input never raises")


def test_spoken_text() -> None:
    cases = {
        "rates to 3.75% to 4%": "rates to three point seven five percent to four percent",
        "$4 billion in gold, 31 tonnes": "four billion dollars in gold, thirty-one tonnes",
        "cost $1.50 and £2.2bn": "cost one dollar fifty and two point two billion pounds",
        "the 17th of the month": "the seventeenth of the month",
        "began in 2018, ended in 2026": "began in twenty eighteen, ended in twenty twenty-six",
        "2,000 people and 1,500 troops": "two thousand people and one thousand five hundred troops",
        "the US and the EU, NATO and the FBI": "the U-S and the E-U, NATO and the F-B-I",
        "Mr. Smith at 11:00 GMT": "Mister Smith at eleven o'clock G-M-T",
        "a pause — then more": "a pause, then more",
    }
    for src, want in cases.items():
        got = normalize_for_speech(src)
        check(got == want, f"{src!r} -> {got!r} (want {want!r})")
    check(apply_say("Kohat police", {"Kohat": "ko-HAHT"}) == "ko-HAHT police", "SAY substitution")
    check(spoken_date(DATE) == "Friday, September eighteenth", "spoken date")
    check(ordinal_words(21) == "twenty-first" and ordinal_words(12) == "twelfth", "ordinals")
    check(year_words(1979) == "nineteen seventy-nine" and year_words(2005) == "two thousand five", "years")
    check(has_quotation_marks('a "hostile act"') and not has_quotation_marks("Carney's plan isn't"), "quote detection")
    check(expand_initialisms("the WHO says") == "the W-H-O says", "WHO as an org")


def test_prompt_and_generation() -> None:
    rows = top20()
    system, user = build_radio_prompt(rows, spoken_date(DATE), has_editorial=True)
    check(SIGN_ON_PREFIX in user and CLOSE_PREFIX in user, "prompt carries the sign-on and sign-off")
    check("## FINALLY" in user, "calm day asks for a kicker")
    rows2 = [dict(rows[0], disaster_severity=0.9)] + rows[1:]
    _, user2 = build_radio_prompt(rows2, spoken_date(DATE))
    check("No FINALLY segment today" in user2, "disaster day suppresses the kicker in the prompt")
    for bad in ("Up First", "Here's what we're covering", "First the headlines", "Stay with us"):
        # The only place a borrowed line may appear is the ban list itself.
        check(bad.lower() not in system.lower() and user.lower().count(bad.lower()) == 1 and "Never these phrases" in user,
              f"prompt never suggests {bad!r}")
    check(THROW_LINE not in user, "throw line is a code constant, not model output")

    clean = FIXTURE.read_text(encoding="utf-8")
    calls = []

    def fake(system: str, user: str) -> str:
        calls.append(user)
        # first attempt broken (a quote), second attempt clean
        return clean.replace("has called the idea a hostile act", 'called it a "hostile act"') if len(calls) == 1 else clean

    r, rep, label = generate_radio_rundown(rows, date=datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc),
                                           generate_fn=fake)
    check(r is not None and rep.passed and label == "gemini-flash", "retry recovers a fixable script")
    check(len(calls) == 2 and "R-02" in calls[1], "retry prompt names the failed rule")

    r, rep, label = generate_radio_rundown(rows, date=datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc),
                                           generate_fn=lambda s, u: "nonsense with no markers")
    check(r is None and label == "gemini-flash-rejected", "unfixable output returns None for the fallback")


if __name__ == "__main__":
    raw = test_clean_fixture()
    test_planted_defects(raw)
    test_parser_tolerance()
    test_spoken_text()
    test_prompt_and_generation()
    if failures:
        print(f"\n{len(failures)} FAILED")
        sys.exit(1)
    print("\ntest_radio_script: all checks passed")
