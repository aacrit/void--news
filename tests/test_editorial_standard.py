#!/usr/bin/env python3
"""One planted defect per rule in docs/EDITORIAL-STANDARD.md.

A validator that has never rejected anything is not a validator. Each case
below plants exactly ONE defect and asserts the rule with that ID fires, and a
clean control asserts none of them fires on good prose. The clean control is
the half that catches an over-eager regex: E-10's first draft flagged
"Mudslides Kill Dozens" as a headline whose location the summary omitted, which
is why that rule is now model-checked (L-07) instead of a regex.

Run: python tests/test_editorial_standard.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.editorial import standard as std  # noqa: E402

CLEAN_SUMMARY = (
    "The central bank raised its benchmark rate by half a point on Tuesday, the "
    "third increase this quarter. Governor Adeyemi said the decision was "
    "unanimous and that the committee would meet again in November. Mortgage "
    "applications fell 12 percent in the week after the announcement, according "
    "to the national lenders association. Two of the five largest banks passed "
    "the increase to savers within a day."
)
CLEAN_TITLE = "Central Bank Raises Rate Half a Point in Third Increase This Quarter"

# (id, candidate, what was planted)
CASES = [
    ("S-01", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY,
              "href": "/?story=1f4d8c2a-9b31-4e57-8a0d-6c2f5b7e91a4"},
     "archive-miss homepage query link"),
    ("S-02", {"title": CLEAN_TITLE, "summary": "The rate rose. Markets reacted."},
     "two-sentence summary (the satire-as-news shape)"),
    ("S-03", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY.rstrip(".") + " and the"},
     "summary cut off mid-sentence"),
    ("S-04", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + ' Adeyemi called it "a necessary correction.'},
     "unbalanced quotation mark"),
    ("S-05", {"title": "Bank Raises Rate", "summary": "TheThe committee met on Tuesday. " + CLEAN_SUMMARY},
     "doubled capitalized word"),
    ("S-06", {"title": CLEAN_TITLE, "summary": "The U. S. central bank moved first. " + CLEAN_SUMMARY},
     "broken abbreviation spacing"),
    ("E-03", {"title": CLEAN_TITLE, "summary": "The decision affects our borrowers directly. " + CLEAN_SUMMARY},
     "first-person pronoun outside quotes"),
    ("E-04", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY + " although the committee was unanimous."},
     "orphan subordinate clause"),
    ("E-05", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Adeyemi was charged with fraud in 2019."},
     "criminal allegation with no attribution"),
    # The live defect of 2026-09-21: "Defense Department staffers reportedly
    # likened Jennifer to Yoko Ono" satisfied E-05, because "reportedly" was
    # in its attribution cues, while attributing the claim to no one (brand
    # audit F-14). A hedge names nobody. Advisory until the numbers are in.
    ("E-15", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Adeyemi was reportedly charged with fraud in 2019."},
     "a hedge standing in for attribution on a criminal claim"),
    ("E-07", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " The funds were traced to the Iranian terror regime."},
     "contested terminology in Void's voice"),
    ("E-08", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " The committee is described as the most hawkish in a decade."},
     "unattributed passive evaluation"),
    ("E-09", {"title": "Army Base Blasts Leave Two Dead",
              "summary": (
                  "Two people died and 14 are missing after explosions at an army base. "
                  "The exact cause of the explosions remains under investigation. "
                  "Details of the unit involved have not been immediately released. "
                  "The number of dead and missing is based on initial reports from the scene. "
                  "Investigations are ongoing to determine the sequence of events. "
                  "The full extent of the damage is still being evaluated.")},
     "a card that is mostly absence of information"),
    # Verbatim from the 2026-09-10 feed, third report of this shape.
    ("S-07", {"title": "Russia Foils Ukrainian Plot Against British Ambassador",
              "summary": CLEAN_SUMMARY + " The FSB said it had foiled an Ukrainian plot "
                                         "against the ambassador."},
     "\"an\" before a consonant sound"),
    ("E-11", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Adeyemi told the committee to keep your projections conservative."},
     "second-person pronoun outside quotes"),
    # Verbatim from the 2026-09-10 Colombia gun-permit card, where this
    # sentence sat between a Rubio quote and the request for comment.
    # The live defect of 2026-09-20: a headline death toll no source contained.
    # 22 source articles carried 23 mentions of 16, two of 21, and no 31.
    ("E-13", {"title": "Funerals Held After Suicide Attack Kills 31 at Pakistan Mosque",
              "summary": (
                  "Funerals are underway in Kohat, Pakistan, following a suicide attack "
                  "on Friday that killed at least 31 people. A suicide attacker rammed an "
                  "explosives-laden car into a mosque near a police compound as seven "
                  "gunmen attempted to enter the facility. Other reports state at least "
                  "21 people died, while some outlets reported 16 fatalities. Five police "
                  "officers were among those killed. The attack also injured 57 people. "
                  "The incident occurred during Friday prayers, with officers and their "
                  "families inside the mosque near police headquarters."),
              "source_text": (
                  "16 killed in twin suicide attack in NW Pakistan. At least 16 killed in "
                  "Pakistan car bomb attack near mosque. Suicide attack kills 16 near "
                  "mosque in northwest Pakistan police compound. Pakistan mosque bombing "
                  "kills 16, wounds 57. Some outlets put the toll at 21.")},
     "a death toll in the headline that appears in none of the sources"),
    ("E-12", {"title": "Colombian President Lifts Gun Carry Ban",
              "summary": (
                  "Colombian President Abelardo de la Espriella signed an order on Tuesday "
                  "ending regulations that prohibited law-abiding citizens from carrying "
                  "legally-owned firearms. "
                  "The decree reversed a ban set in place in 2015 by then-President Juan "
                  "Manuel Santos and renewed annually by his successors. "
                  "The decree was signed while US Secretary of State Marco Rubio was "
                  "visiting Colombia. "
                  "Rubio stressed the need for security across the region. "
                  "The judge ruled the images could be harmful to minors. "
                  "The Colombian embassy did not respond to a request for comment about "
                  "the gun law change.")},
     "a sentence that belongs to a different story"),
    # L-02 has said "every quotation is verbatim" since the standard was
    # written, but only an LLM ever judged it, and the critique pass is capped
    # at 20 flash requests a day. A quotation is the one thing a reader may
    # treat as literal. E-14 checks it deterministically, at write time.
    ("E-14", {"title": "Minister Rejects Findings of Water Safety Review",
              "summary": (
                  "Environment Minister Dela Whitcombe rejected the review's findings on "
                  "Thursday, telling reporters outside the ministry, \u201cThis report was "
                  "written by people who have never set foot in the catchment and it is "
                  "worthless.\u201d The review found lead concentrations above the national "
                  "limit at 11 of 40 sampling points. The ministry has not said whether it "
                  "will commission a second review, and the minister declined to take "
                  "further questions on the testing programme itself."),
              "source_text": (
                  "Environment Minister Dela Whitcombe dismissed the review on Thursday. "
                  "\u201cI have real questions about the methodology here,\u201d she told "
                  "reporters outside the ministry. The review found lead above the national "
                  "limit at 11 of 40 sampling points.")},
     "a quotation the source never contains"),
    # rev 85, P1-2. A decimal was invisible: "8.3%" read as 8 and 3, both
    # ignored. Run #385 shipped "8.3% of passengers" unexamined.
    ("E-13", {"title": "Airline Delays Rise Across the Network",
              "summary": "Delays affected 8.3% of passengers on the network last month. "
                         + CLEAN_SUMMARY,
              "source_text": "Delays affected 8.1% of passengers on the network last month, "
                             "the regulator said. Mortgage applications fell 12 percent."},
     "a decimal percentage the sources give differently (8.3% for 8.1%)"),
    ("E-13", {"title": "Talarico Leads Paxton in Texas Senate Race",
              "summary": "Talarico led with 47.6% to Paxton's 44.7% in the final count. "
                         + CLEAN_SUMMARY,
              "source_text": "Talarico finished with 46.7% of the vote and Paxton with "
                             "44.7%, the final count showed. Mortgage applications "
                             "fell 12 percent."},
     "\"47.6% to 44.7%\" against a source that says 46.7%"),
    # rev 85, P1-2. The Iraq card of 2026-10-01: the number exists, attached to
    # another war. "the operation" refers back to Operation Inherent Resolve.
    ("E-13", {"title": "US Completes Troop Withdrawal From Iraq",
              "summary": ("The withdrawal marks the end of Operation Inherent Resolve, a "
                          "mission that began in 2014 to combat the Islamic State group. "
                          "The Pentagon reported 4,419 U.S. military deaths during the "
                          "operation. " + CLEAN_SUMMARY),
              "source_text": ("The withdrawal marks the end of Operation Inherent Resolve, "
                              "which began in 2014.\n"
                              "The Pentagon reported 4,419 U.S. military deaths during "
                              "Operation Iraqi Freedom, which began with the 2003 "
                              "invasion.\nMortgage applications fell 12 percent.")},
     "4,419 deaths attached to Operation Inherent Resolve when the source says Operation Iraqi Freedom"),
    # rev 85, P1-3. The Hegseth card of 2026-10-01 turned an ellipsis into a
    # full stop inside a quotation. The words were all there.
    ("E-14", {"title": "Defense Secretary Addresses Officers at Quantico",
              "summary": ("He told the officers that those who “clung to the woke "
                          "department. No longer work here,” and left the stage. "
                          + CLEAN_SUMMARY),
              "source_text": ("He told the officers that those who “clung to the woke "
                              "department... no longer work here.” Mortgage "
                              "applications fell 12 percent.")},
     "a quotation whose ellipsis became a full stop"),
    # rev 85, P1-5. The Putin card of 2026-10-01, verbatim.
    ("E-16", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Separately, two sold-out concerts by Kanye West "
                         "in St. Petersburg, scheduled for October 10 and 11, were "
                         "officially canceled."},
     "a sentence that opens by changing the subject"),
    ("E-17", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY.replace("12 percent", "31 percent"),
              "source_text": "Mortgage applications fell 12 percent. The ferry carried "
                             "31 passengers across the strait."},
     "a sourced number lifted from an unrelated source sentence"),
    ("E-18", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " There are currently 841 active-duty generals "
                                         "and admirals."},
     "a count that goes stale"),
]


S07_MUST_STAY_QUIET = [
    "Turkey is a NATO ally and hosted the talks.",
    "A FIFA spokesperson confirmed the schedule on Monday.",
    "The vote followed a MAGA incumbent's defeat in the primary.",
    "Crews reached the site within an hour of the collapse.",
    "She called it an honest account of what happened.",
    "Protesters carried an umbrella against the rain.",
    "The council approved a unanimous resolution.",
]


def main() -> int:
    ok = True

    # S-07 must stay silent on correct English. An onset-letter rule for
    # letter-named acronyms flagged the first three of these over the archive
    # and caught nothing real, so it was removed rather than tuned.
    for line in S07_MUST_STAY_QUIET:
        found = std.s07_article_agreement(line)
        if found:
            print(f"FAIL: S-07 fired on correct English: {line!r} -> {found}")
            ok = False
    if ok:
        print(f"PASS: S-07 quiet on {len(S07_MUST_STAY_QUIET)} correct constructions")

    # E-15 must stay quiet where the hedge is not the only cover: the same
    # claim attributed to prosecutors is E-05-clean and E-15-clean alike.
    hedged_and_named = std.validate_candidate({
        "title": CLEAN_TITLE,
        "summary": CLEAN_SUMMARY + " Adeyemi was reportedly charged with fraud in 2019, prosecutors said.",
    })
    if any(f.id in ("E-05", "E-15") for f in hedged_and_named):
        print(f"FAIL: E-15 fired beside a real attribution: {[str(f) for f in hedged_and_named]}")
        ok = False
    else:
        print("PASS: E-15 quiet when the claim is also attributed")

    # rev 85: the grounded checks must stay quiet on correct copy, or a cut
    # repair deletes a true sentence.
    quiet = [
        ("decimals that match",
         {"title": "Talarico Leads Paxton in Texas Senate Race",
          "summary": "Talarico led with 47.6% to Paxton's 44.7% in the final count. "
                     + CLEAN_SUMMARY,
          "source_text": "Talarico finished with 47.6 percent of the vote and Paxton "
                         "with 44.7%, the final count showed. Mortgage applications "
                         "fell 12 percent."}),
        ("a number on the operation the source names",
         {"title": "US Completes Troop Withdrawal From Iraq",
          "summary": ("The Pentagon reported 4,419 U.S. military deaths during "
                      "Operation Iraqi Freedom. " + CLEAN_SUMMARY),
          "source_text": ("The Pentagon reported 4,419 U.S. military deaths during "
                          "Operation Iraqi Freedom, which began with the 2003 "
                          "invasion.\nMortgage applications fell 12 percent.")}),
        ("a title on the name in another form",
         {"title": CLEAN_TITLE,
          "summary": "President Donald Trump signed 14 orders on Monday. " + CLEAN_SUMMARY,
          "source_text": "Donald Trump signed 14 orders on Monday, beside President "
                         "Emmanuel Macron. Mortgage applications fell 12 percent."}),
        ("an elided quotation with the ellipsis kept",
         {"title": "Defense Secretary Addresses Officers at Quantico",
          "summary": ("He told the officers that those who “clung to the woke "
                      "department ... no longer work here,” and left the stage. "
                      + CLEAN_SUMMARY),
          "source_text": ("He told the officers that those who “clung to the woke "
                          "department... no longer work here.” Mortgage "
                          "applications fell 12 percent.")}),
        ("a verbatim quotation across a sentence break",
         {"title": CLEAN_TITLE,
          "summary": ("He said, “The clowns are out. The cowboys are in,” to "
                      "applause. " + CLEAN_SUMMARY),
          "source_text": ("He said: “The clowns are out. The cowboys are in.” "
                          "Mortgage applications fell 12 percent.")}),
        ("a dated count", {"title": CLEAN_TITLE,
                           "summary": CLEAN_SUMMARY + " The force had 841 generals and "
                                                      "admirals on September 30."}),
        ("an ordinary 'Meanwhile' that does not leave the story",
         {"title": CLEAN_TITLE,
          "summary": CLEAN_SUMMARY + " Meanwhile, the committee said it would publish "
                                     "its minutes in November."}),
    ]
    for label, cand in quiet:
        found = [f for f in std.validate_candidate(cand)
                 if f.id in ("E-13", "E-14", "E-16", "E-17", "E-18")]
        if found:
            print(f"FAIL: grounded rule fired on {label}: {[str(f) for f in found]}")
            ok = False
        else:
            print(f"PASS: quiet on {label}")

    # Clean control: a good card trips nothing.
    clean = std.validate_candidate({
        "title": CLEAN_TITLE, "summary": CLEAN_SUMMARY,
        "href": "/story/1f4d8c2a-9b31-4e57-8a0d-6c2f5b7e91a4/",
    })
    if clean:
        print(f"FAIL: clean control tripped {[str(f) for f in clean]}")
        ok = False
    else:
        print("PASS: clean control trips no rule")

    for rule_id, candidate, planted in CASES:
        findings = std.validate_candidate(candidate)
        ids = {f.id for f in findings}
        if rule_id not in ids:
            print(f"FAIL: {rule_id} did not fire on {planted}; got {sorted(ids) or 'nothing'}")
            ok = False
        else:
            extra = ids - {rule_id}
            note = f" (also {sorted(extra)})" if extra else ""
            print(f"PASS: {rule_id} fired on {planted}{note}")

    # Feed-level rules.
    dupes = std.f02_duplicate_headlines([
        "Senate Passes Border Funding Bill After Overnight Session",
        "Border Funding Bill Passes Senate in Overnight Session",
        "Wildfire Forces Evacuation of Three Coastal Towns",
    ])
    if not any(f.id == "F-02" for f in dupes):
        print("FAIL: F-02 did not fire on two headlines of the same story")
        ok = False
    else:
        print("PASS: F-02 fired on two headlines of the same story")

    if std.f02_duplicate_headlines([
        "Wildfire Forces Evacuation of Three Coastal Towns",
        "Central Bank Raises Rate Half a Point in Third Increase",
    ]):
        print("FAIL: F-02 fired on two unrelated headlines")
        ok = False
    else:
        print("PASS: F-02 quiet on unrelated headlines")

    counts = std.f04_count_match(header_count=12, rendered=12, expected=20)
    if not any("configured feed size" in f.message for f in counts):
        print("FAIL: F-04 did not fire on a self-consistent short render")
        ok = False
    else:
        print("PASS: F-04 fired on a self-consistent short render")

    # Every ID in the registry must have a case or be model-checked.
    covered = {c[0] for c in CASES} | {"F-02", "F-04"}
    missing = [v.id for v in std.VALIDATORS if v.id not in covered]
    if missing:
        print(f"FAIL: no planted defect for {missing}")
        ok = False
    else:
        print(f"PASS: every one of the {len(std.VALIDATORS)} validators has a planted defect")

    return 0 if ok else 1


def test_e13_catches_a_fabricated_number():
    """A number in the card that no source article contains.

    Taken verbatim from the live feed of 2026-09-20. The card headlined
    "Suicide Attack Kills 31 at Pakistan Mosque"; across its 22 sources there
    were 23 mentions of 16, two of 21, and none of 31. The summary said "Other
    reports state at least 21 people died" one sentence later, so the card knew
    the sources disagreed and asserted a third number anyway.

    Every other rule in the standard reads the card alone. This is the first
    that reads it against what it was written from.
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
    from editorial.standard import validate_candidate

    sources = ("16 killed in twin suicide attack in NW Pakistan. At least 16 killed in "
               "Pakistan car bomb attack near mosque. Pakistan mosque bombing kills 16, "
               "wounds 57. Some reports put the toll at 21.")

    bad = {"title": "Funerals Held After Suicide Attack Kills 31 at Pakistan Mosque",
           "summary": "Funerals are underway in Kohat following an attack that killed at "
                      "least 31 people. Other reports state at least 21 people died, "
                      "while some outlets reported 16 fatalities. " + "Filler. " * 40,
           "source_text": sources}
    ids = [f.id for f in validate_candidate(bad)]
    assert "E-13" in ids, f"fabricated number not caught: {ids}"

    good = dict(bad,
                title="Funerals Held After Suicide Attack at Pakistan Mosque Kills 16",
                summary="Most outlets report 16 killed; some report at least 21. "
                        "Reported injuries reach 57. " + "Filler. " * 40)
    assert "E-13" not in [f.id for f in validate_candidate(good)], "correct card failed"

    # 21 and 57 are in the sources and must not fire; nor may a one-digit number.
    assert "E-13" not in [f.id for f in validate_candidate(
        dict(good, summary="Five officers died; 21 hurt, 57 wounded. " + "Filler. " * 40))]

    # No source text: skip rather than accuse. A rule that cannot see the
    # evidence must not claim the card is wrong.
    assert "E-13" not in [f.id for f in validate_candidate(
        {"title": "Kills 31", "summary": "31 died. " + "Filler. " * 40})]
    print("PASS  E-13 catches a fabricated number and spares a sourced one")


def test_e13_appositive_age_is_attached_to_its_name() -> None:
    """`Name, 47,` gives the number to Name; a party in the same sentence is no rival.

    Served 2026-10-03 and failed verify-production: "Kulbergs, 47, of the
    centrist United List party". The sources put 47 beside Kulbergs; one of
    them also mentioned another "United ..." beside 47, and the rival test
    read the party as what 47 counted. The Iraq shape must still fail.
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "pipeline"))
    from editorial.standard import validate_candidate

    filler = " The vote closes on Saturday evening. " + "Filler. " * 40
    src = ("Kulbergs, 47, a former businessman, studied in the United States.\n"
           "His United List party is polling at around 20 percent.")
    card = {"title": "Latvians Vote for New Parliament",
            "summary": "Kulbergs, 47, of the centrist United List party, then led a "
                       "four-party coalition." + filler,
            "source_text": src}
    assert "E-13" not in [f.id for f in validate_candidate(card)], \
        [f.message for f in validate_candidate(card) if f.id == "E-13"]

    # The appositive must be sourced beside THAT name: an age the sources give
    # to someone else is not rescued.
    other = dict(card, summary="Silina, 47, of the centrist United List party, then led "
                               "a four-party coalition." + filler)
    other_ids = [f.id for f in validate_candidate(other)]
    assert "E-13" in other_ids or "E-17" in other_ids, other_ids
    print("PASS  E-13 reads an appositive age as its name's, and still refuses another's")


def test_e14_catches_an_invented_quotation() -> None:
    """A quotation must be in the sources; scare quotes and elisions must not fire."""
    from pipeline.editorial.standard import validate_candidate
    sources = (
        "Environment Minister Dela Whitcombe dismissed the review on Thursday. "
        "\u201cI have real questions about the methodology here, and I have said so to "
        "the department,\u201d she told reporters outside the ministry. She called the "
        "sampling regime a \u201cwork in progress\u201d."
    )
    filler = "Filler sentence for length. " * 20

    bad = {"title": "Minister Rejects Water Review",
           "summary": ('She said, "This report was written by people who have never set '
                       'foot in the catchment." ') + filler,
           "source_text": sources}
    assert "E-14" in [f.id for f in validate_candidate(bad)], "invented quotation not caught"

    # Verbatim, with the curly quotes the summarizer straightens on the way out.
    good = dict(bad, summary=('She said, "I have real questions about the methodology '
                              'here, and I have said so to the department." ') + filler)
    assert "E-14" not in [f.id for f in validate_candidate(good)], "verbatim quote failed"

    # An elided quote is checked around the ellipsis, which no source contains.
    assert "E-14" not in [f.id for f in validate_candidate(
        dict(bad, summary='She said, "I have real questions about the methodology ... '
                          'I have said so to the department." ' + filler))]

    # Three words or fewer is a scare quote or a title, not a quotation.
    assert "E-14" not in [f.id for f in validate_candidate(
        dict(bad, summary='She called it a "work in progress" and left. ' + filler))]

    # No source text: skip rather than accuse, exactly as E-13 does.
    assert "E-14" not in [f.id for f in validate_candidate(
        {"title": "Minister Rejects Water Review",
         "summary": 'She said, "Nobody in this ministry believes that number." ' + filler})]
    print("PASS  E-14 catches an invented quotation and spares a verbatim one")


# ---------------------------------------------------------------------------
# rev 86 (factual rigor plan, gaps 1 and 3). Run by `python` in CI as well as
# by pytest: until rev 86 the two tests above sat after a `sys.exit(main())`
# and only pytest ever reached them, while CI runs this file with `python`.
# ---------------------------------------------------------------------------
POINT_SOURCES = (
    "The central bank raised its benchmark rate by half a point on Tuesday. "
    "Governor Adeyemi said the decision was unanimous. Mortgage applications "
    "fell 12 percent in the week after the announcement.\n"
    "“We will not hesitate to act again if inflation persists,” Adeyemi "
    "told reporters at the central bank."
)


def test_points_are_checked_and_a_failing_point_is_dropped() -> None:
    """Gap 1: E-13, E-14, E-16 on each consensus or divergence point."""
    good = "Outlets agree mortgage applications fell 12 percent after the rise."
    unsourced = "Outlets agree the bank closed 37 regional branches."
    invented = ("Adeyemi said “the bank has lost control of prices "
                "entirely” on Tuesday.")
    verbatim = ("Adeyemi said “we will not hesitate to act again if inflation "
                "persists.”")
    shift = "Separately, a court in Lagos fined a telecom operator."
    kept, dropped = std.check_points(
        [good, unsourced, invented, verbatim, shift], POINT_SOURCES)
    assert kept == [good, verbatim], f"wrong points kept: {kept}"
    why = {text: found[0].id for text, found in dropped}
    assert why == {unsourced: "E-13", invented: "E-14", shift: "E-16"}, why

    # Precision: no evidence is "cannot confirm". E-13 and E-14 skip, E-16
    # (which reads the point alone) still runs.
    kept, dropped = std.check_points([good, unsourced, invented, shift], None)
    assert kept == [good, unsourced, invented], kept
    assert [d[0] for d in dropped] == [shift]

    # An index with no record behind it is not evidence either.
    from pipeline.editorial import grounding as G
    kept, _ = std.check_points([unsourced], G.Verifier(None))
    assert kept == [unsourced], "an absent index accused a point"

    # The same question against the persisted index as against the text.
    rec = G.build_record("c", [{"id": "a1", "title": "Bank raises rate",
                                "full_text": POINT_SOURCES}], stage=G.STAGE_PRE)
    kept, dropped = std.check_points([good, unsourced], G.Verifier(rec))
    assert kept == [good] and dropped[0][0] == unsourced

    # Precision: a divergence point attributes a figure to an OUTLET, which no
    # article names beside it. On the committed feed of 2026-10-02, "The Daily
    # Beast and The Hill emphasize ... the 2028 presidential nomination" read
    # as 2028 moved onto "Daily Beast" because a source put 2028 beside
    # another "Daily ..." name. The cluster's outlet names are not counted.
    src = "Vance is weighing a 2028 presidential run, Daily Wire Editor Ben Shapiro said."
    point = "The Daily Beast emphasizes Vance's 2028 presidential ambitions."
    assert std.check_points([point], src)[1], "control: the attachment half fires"
    kept, _ = std.check_points([point], src, outlets=["The Daily Beast", "The Hill"])
    assert kept == [point], "an outlet name was read as what a number counts"
    print("PASS  points: an unsourced number, an invented quotation and a "
          "topic shift are dropped; evidence that is absent drops nothing")


# --- a minimal Stage 2 harness: an in-memory table store and a stub model ---

class _Q:
    def __init__(self, db, name):
        self.db, self.name, self.filters, self.payload = db, name, [], None

    def select(self, _cols):
        return self

    def in_(self, col, vals):
        vals = set(vals)
        self.filters.append(lambda r: r.get(col) in vals)
        return self

    def eq(self, col, val):
        self.filters.append(lambda r: r.get(col) == val)
        return self

    def update(self, payload):
        self.payload = payload
        return self

    def execute(self):
        rows = [r for r in self.db.tables.setdefault(self.name, [])
                if all(f(r) for f in self.filters)]
        if self.payload is not None:
            if self.db.fail_updates:
                raise RuntimeError("write refused")
            for r in rows:
                r.update(self.payload)
            self.db.writes.append((self.name, dict(self.payload)))
        return type("R", (), {"data": [dict(r) for r in rows]})()


class _DB:
    def __init__(self):
        self.tables: dict = {}
        self.writes: list = []
        self.fail_updates = False

    def table(self, name):
        return _Q(self, name)

    def row(self, table, rid):
        return next(r for r in self.tables[table] if r["id"] == rid)


_SUMMARIZER = "summarizer.cluster_summarizer"


def _restores_summarizer(fn):
    """Put the real summarizer module back after a test that stubbed it, so a
    pytest session running other files in this process never sees the stub."""
    import functools

    @functools.wraps(fn)
    def wrapper(*a, **k):
        had = _SUMMARIZER in sys.modules
        saved = sys.modules.get(_SUMMARIZER)
        try:
            return fn(*a, **k)
        finally:
            if had:
                sys.modules[_SUMMARIZER] = saved
            else:
                sys.modules.pop(_SUMMARIZER, None)
    return wrapper


def _stage2(llm: bool):
    """editorial.stage2 with the summarizer replaced by a stub that spends
    nothing: no model is called, and `llm` is what is_available() answers.
    Call only inside a test wrapped by @_restores_summarizer."""
    import types
    pipeline = str(ROOT / "pipeline")
    if pipeline not in sys.path:
        sys.path.insert(0, pipeline)
    fake = types.ModuleType("summarizer.cluster_summarizer")
    fake._content_hash = lambda arts: "h:" + "|".join(sorted(a["id"] for a in arts))
    fake._store_cluster_summary = lambda *a, **k: None
    fake.critique_cards = lambda recs, **k: {}
    fake.summarize_cluster = lambda *a, **k: None
    fake.is_available = lambda: llm
    import summarizer  # noqa: F401  the real (light) package
    sys.modules["summarizer.cluster_summarizer"] = fake
    from editorial import stage2
    return stage2


BODY = (
    "The central bank raised its benchmark rate by half a point on Tuesday, the "
    "third increase this quarter. Governor Adeyemi said the decision was "
    "unanimous and that the committee would meet again in November. Mortgage "
    "applications fell 12 percent in the week after the announcement, according "
    "to the national lenders association. Two of the five largest banks passed "
    "the increase to savers within a day. " * 2
)


def _cluster(db, cid, n_articles, *, title, summary, stub=False, points=None,
             tier="flash"):
    arts = []
    for i in range(n_articles):
        aid = f"{cid}-a{i}"
        body = (BODY[:297] + "...") if stub else BODY
        a = {"id": aid, "title": f"Central bank raises rate ({i})",
             "summary": "", "full_text": body, "source_id": "s1",
             "published_at": "2026-10-02T10:00", "url": f"https://x.test/{aid}"}
        db.tables.setdefault("articles", []).append(a)
        db.tables.setdefault("cluster_articles", []).append(
            {"cluster_id": cid, "article_id": aid})
        arts.append(a)
    db.tables.setdefault("sources", [{"id": "s1", "name": "Wire",
                                      "tier": "international",
                                      "political_lean_baseline": "center"}])
    row = {"id": cid, "title": title, "summary": summary, "summary_tier": tier,
           "source_count": n_articles, "content_type": "reporting",
           "summary_article_hash": "h:" + "|".join(sorted(a["id"] for a in arts))}
    row.update(points or {})
    db.tables.setdefault("story_clusters", []).append(row)
    return arts


def _write_index(build_dir, cid, arts, **over):
    from editorial import grounding as G
    rec = G.build_record(cid, arts, stage=over.pop("stage", G.STAGE_PRE))
    rec.update(over)
    G.write_record(build_dir, rec)


@_restores_summarizer
def test_cached_card_is_judged_against_its_stored_index() -> None:
    """Gap 3: a cached card is checked against its pre-truncation record."""
    import tempfile
    stage2 = _stage2(llm=False)
    build = Path(tempfile.mkdtemp(prefix="void-rigor-"))
    db = _DB()
    bad = " The bank said it would close 73 regional branches by March."
    arts = _cluster(db, "cached", 3, title=CLEAN_TITLE, summary=CLEAN_SUMMARY + bad)
    _write_index(build, "cached", arts)
    out = stage2.review_bench(db, ["cached"], run_critique=False,
                              fresh_ids=set(), build_dir=build)
    card = db.row("story_clusters", "cached")
    assert "73" not in card["summary"], "the unsourced sentence shipped"
    assert card["summary"].startswith("The central bank raised"), card["summary"]
    assert out["survivors"] == ["cached"], out
    r = out["rigor"]
    assert (r["cached_cards"], r["cached_cards_checked"], r["cached_cards_cut"],
            r["cached_sentences_cut"]) == (1, 1, 1, 1), r
    print("PASS  a cached card's number its stored index lacks is cut")


@_restores_summarizer
def test_stub_or_format2_record_cannot_confirm() -> None:
    """Precision: an index the card was not written from never cuts."""
    import tempfile
    from editorial import grounding as G
    stage2 = _stage2(llm=False)
    bad = " The bank said it would close 73 regional branches by March."
    cases = [
        ("stub", dict(stub=True), {}),
        ("format", {}, {"format": 2}),
        ("not-pre-truncation", {}, {"stage": G.STAGE_EXPORT}),
        ("no-record", {}, None),
    ]
    for reason, kw, over in cases:
        build = Path(tempfile.mkdtemp(prefix="void-rigor-"))
        db = _DB()
        arts = _cluster(db, "c1", 3, title=CLEAN_TITLE,
                        summary=CLEAN_SUMMARY + bad, **kw)
        if over is not None:
            _write_index(build, "c1", arts, **over)
        out = stage2.review_bench(db, ["c1"], run_critique=False,
                                  fresh_ids=set(), build_dir=build)
        card = db.row("story_clusters", "c1")
        assert "73" in card["summary"], f"{reason}: a stub-backed absence cut a sentence"
        assert out["survivors"] == ["c1"], f"{reason}: {out}"
        assert out["rigor"]["cached_cards_cannot_confirm"] == {reason: 1}, out["rigor"]

    # A card written from another membership is not judged by this one's index.
    assert stage2.cached_evidence_status(
        {"stage": G.STAGE_PRE, "format": 3, "articles": [{"id": "a"}]},
        ["a"], written_from_members=False) == "membership-changed"
    # An index that does not hold every member cannot clear or accuse.
    assert stage2.cached_evidence_status(
        {"stage": G.STAGE_PRE, "format": 3, "articles": [{"id": "a"}]},
        ["a", "b"], written_from_members=True) == "uncovered"
    # An index cut short of the 2,200 body characters the summarizer read.
    assert stage2.cached_evidence_status(
        {"stage": G.STAGE_PRE, "format": 3, "articles": [
            {"id": "a", "truncated": True, "chars": 5200, "bodyChars": 4000}]},
        ["a"], written_from_members=True) == "short-index"
    assert stage2.cached_evidence_status(
        {"stage": G.STAGE_PRE, "format": 3, "articles": [
            {"id": "a", "truncated": True, "chars": 4200, "bodyChars": 4000}]},
        ["a"], written_from_members=True) == "ok"
    print("PASS  stub, format-2, export-stage and missing records cannot "
          "confirm, and cut nothing")


@_restores_summarizer
def test_factual_failure_on_a_thin_cluster_is_dropped_not_kept() -> None:
    """Gap 3: an enforced grounded finding after repair never ships."""
    import tempfile
    stage2 = _stage2(llm=False)
    build = Path(tempfile.mkdtemp(prefix="void-rigor-"))
    db = _DB()
    # A headline cannot be repaired by a cut. Two articles, no model.
    arts = _cluster(db, "thin", 2, title="Central Bank Raise Costs 31 Branches",
                    summary=CLEAN_SUMMARY)
    _write_index(build, "thin", arts)
    # Control: a STYLE failure on the same thin cluster is still kept.
    arts2 = _cluster(db, "style", 2, title=CLEAN_TITLE,
                     summary=CLEAN_SUMMARY + " although the committee was unanimous.")
    _write_index(build, "style", arts2)
    out = stage2.review_bench(db, ["thin", "style"], run_critique=False,
                              fresh_ids=set(), build_dir=build)
    assert "thin" in out["dropped"] and "thin" not in out["survivors"], out
    assert "style" in out["survivors"], "a style-only failure was dropped"
    r = out["rigor"]
    assert r["factual_drops"] == 1 and r["factual_drops_by_rule"] == {"E-13": 1}, r
    assert r["factual_drops_kept_before_rev86"] == 1, r

    # The same headline on a FRESH card, judged against this run's text.
    db2 = _DB()
    _cluster(db2, "fresh", 2, title="Central Bank Raise Costs 31 Branches",
             summary=CLEAN_SUMMARY)
    out = stage2.review_bench(db2, ["fresh"], run_critique=False,
                              fresh_ids={"fresh"}, build_dir=build)
    assert out["dropped"] == ["fresh"], out
    print("PASS  a headline E-13 failure on a 2-article cluster is dropped; "
          "a style failure there is kept")


@_restores_summarizer
def test_failing_point_is_dropped_and_the_card_kept() -> None:
    """Gap 1 at 8d.3: the stored points lose the failure, the card ships."""
    import tempfile
    stage2 = _stage2(llm=False)
    build = Path(tempfile.mkdtemp(prefix="void-rigor-"))
    db = _DB()
    good = "Outlets agree mortgage applications fell 12 percent after the rise."
    bad = "Outlets agree the bank closed 37 regional branches."
    arts = _cluster(db, "pts", 3, title=CLEAN_TITLE, summary=CLEAN_SUMMARY,
                    points={"consensus_points": [good, bad],
                            "divergence_points": ["Separately, a court fined "
                                                  "a telecom operator."]})
    _write_index(build, "pts", arts)
    out = stage2.review_bench(db, ["pts"], run_critique=False,
                              fresh_ids=set(), build_dir=build)
    row = db.row("story_clusters", "pts")
    assert row["consensus_points"] == [good], row["consensus_points"]
    assert row["divergence_points"] == [], row["divergence_points"]
    assert out["survivors"] == ["pts"], out
    r = out["rigor"]
    assert (r["points_checked"], r["points_dropped"]) == (3, 2), r
    assert r["points_dropped_by_rule"] == {"E-13": 1, "E-16": 1}, r

    # A card whose filtered points cannot be written does not ship them.
    db2 = _DB()
    arts = _cluster(db2, "nowrite", 3, title=CLEAN_TITLE, summary=CLEAN_SUMMARY,
                    points={"consensus_points": [bad]})
    _write_index(build, "nowrite", arts)
    db2.fail_updates = True
    out = stage2.review_bench(db2, ["nowrite"], run_critique=False,
                              fresh_ids=set(), build_dir=build)
    assert out["dropped"] == ["nowrite"], out
    assert out["rigor"]["points_write_failed_drops"] == 1
    print("PASS  a point with an unsourced number is dropped from the stored "
          "card, which ships")


@_restores_summarizer
def test_bench_index_keeps_whole_bodies_over_stubs() -> None:
    """8f must not overwrite a whole-body index with the same articles' stubs."""
    import tempfile
    from editorial import grounding as G
    stage2 = _stage2(llm=False)
    build = Path(tempfile.mkdtemp(prefix="void-rigor-"))
    db = _DB()
    arts = _cluster(db, "k", 3, title=CLEAN_TITLE, summary=CLEAN_SUMMARY)
    _write_index(build, "k", arts)                     # yesterday, whole bodies
    for a in db.tables["articles"]:                    # step 10 since
        a["full_text"] = a["full_text"][:297] + "..."
    stage2.write_bench_index(db, ["k"], build_dir=str(build))
    rec = json.loads((build / G.DIRNAME / "k.json").read_text())
    assert not any(a["stub"] for a in rec["articles"]), "stubs replaced bodies"
    # A new member means a new record.
    _cluster(db, "k", 1, title=CLEAN_TITLE, summary=CLEAN_SUMMARY)
    db.tables["cluster_articles"][-1]["article_id"] = "k-new"
    db.tables["articles"][-1]["id"] = "k-new"
    stage2.write_bench_index(db, ["k"], build_dir=str(build))
    rec = json.loads((build / G.DIRNAME / "k.json").read_text())
    assert "k-new" in {a["id"] for a in rec["articles"]}
    print("PASS  8f keeps a whole-body index over the same articles' stubs")


ALL_TESTS = (
    test_e13_catches_a_fabricated_number,
    test_e13_appositive_age_is_attached_to_its_name,
    test_e14_catches_an_invented_quotation,
    test_points_are_checked_and_a_failing_point_is_dropped,
    test_cached_card_is_judged_against_its_stored_index,
    test_stub_or_format2_record_cannot_confirm,
    test_factual_failure_on_a_thin_cluster_is_dropped_not_kept,
    test_failing_point_is_dropped_and_the_card_kept,
    test_bench_index_keeps_whole_bodies_over_stubs,
)


def _run_all() -> int:
    rc = main()
    for fn in ALL_TESTS:
        try:
            fn()
        except AssertionError as e:
            print(f"FAIL  {fn.__name__}: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(_run_all())
