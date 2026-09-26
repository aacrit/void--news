"""Radio rundown: parser, validators and the spoken-text normaliser. No LLM.

    python tests/test_radio_script.py

Pattern (as tests/test_verify_gate.py): a clean fixture must pass, then one
planted defect per validator must fire exactly that validator id.
"""

from __future__ import annotations

import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.radio_script_generator import (  # noqa: E402
    RundownContext, parse_rundown, validate_rundown, build_radio_prompt,
    generate_radio_rundown, SIGN_ON_PREFIX, CLOSE_PREFIX, WORD_BUDGETS, TOTAL_BUDGET,
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
        rows.append({"id": "72de16f4-806b-4be1-a767-811ee56a6daf", "title": "Hong Kong to recruit AI chief by mid-2027", "disaster_severity": 0})
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
    check(r.say.get("Kohat") == "ko-haht", "SAY parsed")
    # round-trip
    r2 = parse_rundown(r.to_text())
    check([s.kind for s in r2.segments] == [s.kind for s in r.segments], "to_text round-trips")
    check(r2.words == r.words, "to_text keeps every word")
    return raw


def test_planted_defects(raw: str) -> None:
    cases = {
        "R-01": raw.replace(f"A: {SIGN_ON_PREFIX}", "A: Good morning, and welcome."),
        "R-04": raw.replace("issued the order on Thursday", "issued the order at 4 p.m. Thursday"),
        "R-05": raw.replace("A: To South America.", "A: And finally, to South America.") if "A: To South America." in raw
                else raw.replace("B: To South America.", "B: And finally, to South America."),
        "R-08": raw.replace("## FINALLY | 15 |", "## FINALLY | 2 |"),
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
    # R-02 quotation marks are a hard fail since 2026-09-21. They warned, the
    # engine stripped them anyway, and the served script carried four; a
    # finding that changes nothing is not a rule (brand audit F-02).
    rep = validate_rundown(parse_rundown(raw.replace("has called the idea a hostile act", 'called it a "hostile act"')), ctx())
    check("R-02" in ids_of(rep), "quote marks fail R-02")
    # R-05 the significance family. "This attack marks a significant
    # escalation" reached the air because the sanitizer that deletes these
    # words is skipped for audio (brand audit F-13).
    for word in ("a significant increase", "a notable increase", "importantly, an increase"):
        rep = validate_rundown(parse_rundown(raw.replace("It is the first increase in three years.", f"It is {word}, the first in three years.")), ctx())
        check("R-05" in ids_of(rep), f"{word!r} fails R-05")
    rep = validate_rundown(parse_rundown(raw.replace("It is the first increase in three years.", "It marks a shift, the first in three years.")), ctx())
    check("R-05" in ids_of(rep), "'marks a' fails R-05")
    # R-08: ids are bound by rank, so a mis-copied uuid in a STORY marker is harmless
    legacy = raw.replace("## STORY 2 | The Fed raises rates", "## STORY 2 | b4a7fae8-a1cf-44fc-8496-6fa90ec4ea34 | The Fed raises rates")
    r_leg = parse_rundown(legacy)
    rep = validate_rundown(r_leg, ctx())
    check(rep.passed and r_leg.story_segments()[1].cluster_id == "b4a7fae8-a1cf-44fc-8496-6fa90ec4aa34",
          "mis-copied story uuid is re-bound to the rank's real id")
    near = raw.replace("## FINALLY | 15 |", "## FINALLY | 72de16f4-806b-4be1-a767-811ee56a6dbf |")
    r_near = parse_rundown(near)
    rep = validate_rundown(r_near, ctx())
    check(rep.passed and r_near.get("FINALLY").cluster_id == "72de16f4-806b-4be1-a767-811ee56a6daf", "near-miss kicker uuid resolves")
    r_no = parse_rundown(raw.replace("## FINALLY | 15 |", "## FINALLY |"))
    rep = validate_rundown(r_no, ctx())
    check(rep.passed and r_no.get("FINALLY").cluster_id == "72de16f4-806b-4be1-a767-811ee56a6daf", "kicker resolves by title words when no rank is given")
    # R-08: the kicker must not be the editorial's own story
    rep = validate_rundown(parse_rundown(raw), ctx(editorial_cluster_id="72de16f4-806b-4be1-a767-811ee56a6daf"))
    check("R-08" in ids_of(rep), "kicker == editorial story fails R-08")
    # R-03 numerals are a warning, not a failure
    rep = validate_rundown(parse_rundown(raw.replace("thirty-one tonnes", "31 tonnes")), ctx())
    check(rep.passed and any(f.id == "R-03" for f in rep.findings), "numerals warn but pass")
    # R-07 trailing attribution warns
    rep = validate_rundown(parse_rundown(raw.replace(
        "Carney says closer ties with Europe would stop any single country from controlling Canada's markets or undermining its sovereignty.",
        "Closer ties with Europe would stop any single country from controlling Canada's markets, Carney said.")), ctx())
    check(any(f.id == "R-07" for f in rep.findings), "trailing attribution warns")


# The served pair of 2026-09-21 (brand audit F-02), verbatim: the summary the
# rundown was cut from, and the two lines it became.
WALTZ_SUMMARY = (
    "U.N. Ambassador Mike Waltz has barred two outlets from the mission's briefings. "
    "Waltz argues the Supreme Court has protected the right to publish, but not access "
    "to any government facility."
)


def test_grounded_attribution(raw: str) -> None:
    rows = top20()
    rows[0] = dict(rows[0], title="Waltz bars two outlets", summary=WALTZ_SUMMARY)
    head, rest = raw.split("## STORY 1 | Canada turns toward Europe")
    tail = rest[rest.index("## STORY 2"):]

    def with_story1(*lines: str) -> str:
        return head + "## STORY 1 | Waltz bars two outlets\n" + "\n".join(lines) + "\n\n" + tail

    bad = with_story1(
        "A: U-N Ambassador Mike Waltz has barred two outlets from the mission's briefings.",
        "A: Ambassador Waltz argues the Supreme Court has protected such actions.",
        "A: The Supreme Court has previously protected the government's right to limit access to facilities. "
        "This protection applies to journalists.",
    )
    fired = ids_of(validate_rundown(parse_rundown(bad), ctx(rows)))
    check("R-14" in fired, f"'such actions' for 'the right to publish' fails R-14 (fired {sorted(fired)})")
    check("R-15" in fired, f"the court stated in Void's own voice fails R-15 (fired {sorted(fired)})")

    good = with_story1(
        "A: U-N Ambassador Mike Waltz has barred two outlets from the mission's briefings.",
        "A: Waltz argues the Supreme Court has protected the right to publish, but not access to any "
        "government facility. He says the same court has never protected access to a government building.",
    )
    fired = ids_of(validate_rundown(parse_rundown(good), ctx(rows)))
    check("R-14" not in fired and "R-15" not in fired, f"the faithful cut passes R-14 and R-15 (fired {sorted(fired)})")

    # Cutting is the job: a clause that keeps only the first half of the
    # claim, adding nothing, is grounded.
    cut = with_story1(
        "A: U-N Ambassador Mike Waltz has barred two outlets from the mission's briefings.",
        "A: Waltz argues the Supreme Court has protected the right to publish.",
    )
    fired = ids_of(validate_rundown(parse_rundown(cut), ctx(rows)))
    check("R-14" not in fired, f"a shorter cut of the same claim passes R-14 (fired {sorted(fired)})")

    # A statement of law after an attribution IN THE SAME TURN is reported speech.
    same_turn = with_story1(
        "A: Ambassador Waltz argues the Supreme Court has protected the right to publish. "
        "The Supreme Court has protected only that right, he says. The court has protected nothing else.",
    )
    fired = ids_of(validate_rundown(parse_rundown(same_turn), ctx(rows)))
    check("R-15" not in fired, f"a legal sentence following an attribution in the same turn passes R-15 (fired {sorted(fired)})")

    # A speaker the stories never name is not grounded.
    invented = with_story1(
        "A: U-N Ambassador Mike Waltz has barred two outlets from the mission's briefings.",
        "A: Press Secretary Dana Ortiz says the outlets were warned twice.",
    )
    fired = ids_of(validate_rundown(parse_rundown(invented), ctx(rows)))
    check("R-14" in fired, f"a speaker absent from the stories fails R-14 (fired {sorted(fired)})")

    # No summary to judge against: R-14 abstains rather than accuses; R-15
    # needs no summary.
    fired = ids_of(validate_rundown(parse_rundown(bad), ctx(top20())))
    check("R-14" not in fired and "R-15" in fired, f"without summaries R-14 abstains and R-15 still fires (fired {sorted(fired)})")


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
    check(st.cluster_id == "d3afa900-ea54-4eb8-b95e-f6ed157317a3" and st.title == "Canada turns", "uuid and title found whatever the field order")
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
        'staff call her "Yoko Ono," a spokesperson says': "staff call her Yoko Ono, a spokesperson says",
        "the ‘big night’ remark and Carney's plan isn't done": "the big night remark and Carney's plan isn't done",
    }
    for src, want in cases.items():
        got = normalize_for_speech(src)
        check(got == want, f"{src!r} -> {got!r} (want {want!r})")
    check(apply_say("Kohat police", {"Kohat": "ko-haht"}) == "ko-haht police", "SAY substitution")
    check(apply_say("Mark Carney and Pete Hegseth", {"Carney": "KAR-nee", "Hegseth": "HEG-seth"}) == "Mark kar-nee and Pete heg-seth",
          "capitalised respellings are lowercased (capitals are read as initials)")
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
    # The prompt's word budgets and the validator's must be the SAME numbers.
    # They were typed separately and had already drifted: the model was asked
    # for one length and then marked against another.
    for label in ("STORY1", "STORY", "FINALLY"):
        lo, hi = WORD_BUDGETS[label]
        check(f"{lo}-{hi}" in user, f"prompt states the {label} budget {lo}-{hi}")
    check(f"{TOTAL_BUDGET[0]:,} to {TOTAL_BUDGET[1]:,}" in user, "prompt states the total budget")
    check(not re.findall(r"\{[A-Z_]+\}", user), "every prompt placeholder is filled")

    clean = FIXTURE.read_text(encoding="utf-8")
    calls = []

    def fake(system: str, user: str) -> str:
        calls.append(user)
        # first attempt broken (a clock time), second attempt clean
        return clean.replace("issued the order on Thursday", "issued the order at 4 p.m. Thursday") if len(calls) == 1 else clean

    r, rep, label = generate_radio_rundown(rows, date=datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc),
                                           generate_fn=fake)
    check(r is not None and rep.passed and label == "gemini-flash", "retry recovers a fixable script")
    check(len(calls) == 2 and "R-04" in calls[1], "retry prompt names the failed rule")

    r, rep, label = generate_radio_rundown(rows, date=datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc),
                                           generate_fn=lambda s, u: "nonsense with no markers")
    check(r is None and label == "gemini-flash-rejected", "unfixable output returns None for the fallback")

    # R-02 spends the retry; if the retry still carries quotation marks they
    # are stripped and the script re-validated, so punctuation alone never
    # costs the show.
    quoted = clean.replace("has called the idea a hostile act", 'called it a "hostile act"')
    qcalls = []

    def fake_quoted(system: str, user: str) -> str:
        qcalls.append(user)
        return quoted

    r, rep, label = generate_radio_rundown(rows, date=datetime.datetime(2026, 9, 18, tzinfo=datetime.timezone.utc),
                                           generate_fn=fake_quoted)
    check(r is not None and label == "gemini-flash" and len(qcalls) == 2 and "R-02" in qcalls[1],
          "quotation marks: the retry is spent naming R-02, then the marks are stripped and the script accepted")
    check(r is not None and not any(has_quotation_marks(t.text) for s in r.segments for t in s.turns),
          "no quotation mark survives the strip")


if __name__ == "__main__":
    raw = test_clean_fixture()
    test_planted_defects(raw)
    test_grounded_attribution(raw)
    test_parser_tolerance()
    test_spoken_text()
    test_prompt_and_generation()
    if failures:
        print(f"\n{len(failures)} FAILED")
        sys.exit(1)
    print("\ntest_radio_script: all checks passed")
