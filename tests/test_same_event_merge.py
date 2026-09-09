#!/usr/bin/env python3
"""Hand-labelled fixtures for the Stage 2 same-event merge gate.

Every case is a real pair from the live feed, labelled by reading the two
stories. The positives are the duplicates the 2026-09-06 feed shipped; the
negatives are the pairs the disabled Phase 7 merge actually fused, which is the
failure this gate exists not to repeat.

topic_coherence is deliberately absent: it scores any shared word as on topic
and reported 1.00 on the Assam cluster at a true precision of 0.25.

Run: python tests/test_same_event_merge.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from editorial.same_event import (  # noqa: E402
    MODAL_MIN_STEMS,
    incoherent_members,
    should_merge,
)

T0 = "2026-09-05T02:00:00+00:00"
T1 = "2026-09-05T05:00:00+00:00"
NYT = {"new", "york", "time"}

# (name, title a, title b, ts a, ts b, mastheads, should merge)
CASES = [
    # ---- the duplicates the 09-06 feed shipped -------------------------------
    ("nepal rescue 46/9",
     "Rescuers Pull Two People Alive From Nepal Debris 10 Days After Flash Floods",
     "Nepali Woman Found Alive in Collapsed Home Days After Mourning Began",
     "2026-09-05T08:19:18+00:00", "2026-09-05T07:55:59+00:00",
     NYT | {"newsmax", "haven", "regist"}, True),
    ("pentagon polygraph 12/8",
     "Pentagon Orders Polygraph Tests for 50 Officials in Classified Leak Investigation",
     "Defense Secretary Hegseth Faces Scrutiny Amid Pentagon Purges, Leak Hunt",
     "2026-09-05T02:55:58+00:00", "2026-09-05T10:00:00+00:00",
     NYT | {"cbs", "news", "express", "tribun"}, True),
    ("scotus retelling",
     "Supreme Court Rules on Transgender Care Ban in 6-3 Decision",
     "Supreme Court Upholds Tennessee Law Restricting Care for Minors",
     T0, T1, set(), True),

    # ---- what the disabled Phase 7 pass actually fused -----------------------
    ("tesla probe vs us open",
     "Federal Regulators Open Probe Into Tesla Cybercab Autonomous Driving",
     "Alcaraz, Sabalenka into US Open last 16", T0, T1, set(), False),
    ("idf lebanon vs russian drones",
     "IDF Strikes Hezbollah Targets in Southern Lebanon",
     "Russian Drone Strikes Hit Ukraine's SBU Headquarters", T0, T1, set(), False),
    ("iran war vs gas prices",
     "Iran War Day 189: Tehran Signals Talks",
     "US Gas Prices Fall for Fifth Straight Week", T0, T1, set(), False),
    ("putin pause vs judge order",
     "Putin Suspends Kyiv Strikes for 72 Hours as US Envoys Meet for Talks",
     "Judge Orders Trump Administration to Restore Foreign Aid Payments",
     T0, T1, set(), False),

    # ---- two mass-casualty stories on one day are still two stories ----------
    ("greek jet vs cape verde bus",
     "Greek Air Force F-4 Phantom Jet Crashes at Athens Airshow, Killing Two",
     "Cape Verde Bus Crash Kills 25, Most of Them Students", T0, T1, set(), False),

    # ---- same country, different event --------------------------------------
    ("nepal rescue vs singapore posts",
     "Rescuers Pull Two People Alive From Nepal Debris 10 Days After Flash Floods",
     "Singapore Probes 'Shameful' Xenophobic Posts on Nepal-Tibet Flood, Air India",
     T0, T1, set(), False),

    # ---- the masthead trap: shared entities that are an outlet name ----------
    ("masthead-only overlap",
     "New York Times Wins Pulitzer for Investigation",
     "New York Prosecutors Charge Two in Subway Assault", T0, T1, NYT, False),

    # ---- the temporal conjunct ----------------------------------------------
    ("same story, four days apart",
     "Pentagon Orders Polygraph Tests for 50 Officials in Classified Leak Investigation",
     "Pentagon Orders More Polygraph Tests in Classified Leak Inquiry",
     "2026-09-01T02:00:00+00:00", "2026-09-05T02:00:00+00:00", set(), False),
]


# Coherence fixtures. Each is a real cluster from the 09-06 feed, with its
# member headlines, and the members a reader would say do not belong.
# `want` is the set of member indices that must be flagged.
COHERENCE = [
    ("arctic tanker", [
        "Russia's giant Vostok Oil loads first crude on Arctic tanker",
        "KONGSBERG StrikeMaster Deploys to Jan Mayen for NATO Arctic Exercise",
        "Can the EU find its energy independence in the Arctic?",
        "Russia's Giant Vostok Oil Loads First Crude on Arctic Tanker - Bloomberg.com",
        "Who will control the Arctic? Growing power struggle between Russia, China and the US",
        "China-Russia first Arctic on-site sea-ice observation sheds light on climate change",
    ], {1, 2, 4, 5}),
    ("pickaxe mountain", [
        "Trump Says US May Hit Iran's Pickaxe Mountain Soon - NTD News",
        "Trump's war in Iran is driving the worst wave of pirate attacks in decades",
        "Iran war latest: Iranian oil tanker targeted in US strike, says state media",
        "'Small potatoes for us': Trump plays down Iran conflict, threatens to hit Pickaxe Mountain",
        "Iran War Day 190: Trump Calls Iran War 'Small Potatoes,' Suggests U.S. May Attack Pickaxe Mountain",
        "Amid Iran war stalemate Trump says may hit Pickaxe Mountain 'very soon'",
        "Morning recap",
    ], {6}),
    # Ten reports of one death, differently worded, are one story. A rule that
    # compares each member to the cluster TITLE flags the four that say "halt"
    # where the title says "suspends"; comparing to the cluster's own modal
    # vocabulary keeps them.
    ("putin ceasefire, differently worded", [
        "Putin Suspends Kyiv Strikes for 72 Hours as US Envoys Meet for Talks",
        "War in Ukraine: Putin, Zelensky order pause in strikes",
        "Putin orders three-day halt to strikes on Kiev",
        "Putin orders three-day pause to strikes on Ukraine as US delegation arrives in Moscow",
        "Putin pauses strikes on Kiev",
        "Kremlin confirms 72-hour pause in strikes on Kyiv",
    ], set()),
    # Every member is the same subject; nothing should be flagged.
    ("gloria steinem", [
        "Gloria Steinem was a fierce Trump critic: What she said about the president",
        "Gloria Steinem's Life Between Art and Activism",
        "My Friend Gloria Steinem. Plus. . .",
        "Extended interview: Gloria Steinem",
        "Gloria Steinem Was the Godmother of Neoliberal Feminism - TheWire.in",
        "Look back: Gloria Steinem on the founding of Ms. Magazine",
    ], set()),
    # ---- the 2026-09-09 production over-trim ---------------------------------
    # A big cluster's modal vocabulary SHRINKS as it grows: 62 members of the
    # Iran strike cluster produced exactly three modal stems, so every report
    # phrased differently read as foreign. The cluster HEADLINE does not shrink,
    # which is why removal now needs both signals. Each member below was really
    # deleted from the live feed that day.
    ("iran strike, real over-trim", [
        "US Destroys Five Iranian Tankers in Strait of Hormuz",
        "Oil surges as US destroys five Iranian tankers",
        "Tankers ablaze after US strike, oil markets react",
        "Five tankers destroyed in US strike on Iranian oil fleet",
        "Oil above $100 after tankers destroyed in Hormuz strike",
        "US strike destroys Iranian tankers, oil jumps",
        # These four were really deleted from this cluster on 2026-09-09.
        # Each is the same story in different words, and each shares a stem
        # with the cluster headline even though it shares none of the three
        # modal stems the 62-member cluster produced.
        "US Targets Iranian Ships Near Kharg Island in Response to Attack",
        "War in the Middle East: Iran attacks US base in Jordan, 10 wounded",
        "U.S. denies claims Iran struck two American vessels in retaliation",
        "Iran's retaliatory missiles: sound and fury, signifying nothing",
        # Genuine contamination: must still go.
        "Makinde: Blockade of Obi's convoy confirms APC's desperation",
        "Tuesday's Final Word",
    ], {10, 11}, "US Destroys Five Iranian Tankers; Iran Strikes Jordan, Oil Surges"),

    # "Trump hails 'really big night' for populists in German elections" was
    # deleted from a cluster titled "Trump hails AfD win in Germany's
    # Saxony-Anhalt". They are the same sentence twice.
    ("afd win, real over-trim", [
        "Trump hails AfD win in Germany's Saxony-Anhalt election",
        "Trump hails 'really big night' for populists in German elections",
        "German economy frets about Saxony-Anhalt election results",
        "German Establishment Responds To Its Ballot Box Drubbing",
        "AfD sweeps Saxony-Anhalt in historic state election win",
        "Far-right AfD takes Saxony-Anhalt, Merz under pressure",
        "Liam Rooney gives an instant reaction to FSU's 27-24 loss",
    ], {6}, "Trump hails AfD win in Germany's Saxony-Anhalt"),

    # The guard must not resurrect genuine contamination: a plane-crash cluster
    # keeps its own coverage and still sheds a college football recap.
    ("amazon crash keeps its own, sheds the rest", [
        "Amazon Cargo Jet Crashes on Approach to Miami",
        "Miami crash: NTSB opens investigation into Amazon cargo jet",
        "Amazon cargo plane down near Miami, three crew aboard",
        "Cargo jet crash in Miami kills three, Amazon confirms",
        "Amazon cargo jet crash: what we know about the Miami disaster",
        "Investigators comb Miami site of Amazon cargo jet crash",
        # Really deleted from this cluster on 2026-09-09, and really the
        # same story.
        "Amazon freighter in crash was transporting contact lenses",
        "Pilot of Amazon cargo jet told wife his career was over",
        # Genuine contamination: must still go.
        "Liam Rooney gives an instant reaction to FSU's 27-24 loss",
        "Green groups file complaint over EU water protection review",
    ], {8, 9}, "Amazon Cargo Jet Pilot Reportedly Told Wife Career Over After Miami Crash"),

    # A hyphen must not make a near-identical headline read as foreign.
    ("hyphen artifact", [
        "Germany's Far-Right AfD Poised for Historic State Election Victory",
        "Germany's Far Right Heads for Historic State Win - Bloomberg.com",
        "AfD leads Saxony-Anhalt election polls ahead of historic state vote",
        "Far-right AfD on course for first state election win in Saxony-Anhalt",
    ], set()),
]


def check_coherence() -> int:
    failed = 0
    for case in COHERENCE:
        name, titles, want = case[0], case[1], case[2]
        head = case[3] if len(case) > 3 else ""
        idx, vocab = incoherent_members(titles, head)
        got = set(idx)
        if len(vocab) < MODAL_MIN_STEMS:
            got = set()
        mark = "ok  " if got == want else "FAIL"
        if got != want:
            failed += 1
        print(f"  [{mark}] {name:<32} want {sorted(want)} got {sorted(got)} "
              f"vocab={sorted(vocab)[:5]}")
    print(f"\n{len(COHERENCE) - failed}/{len(COHERENCE)} coherence fixtures correct")
    return failed


def main() -> int:
    failed = 0
    for name, a, b, ta, tb, mast, want in CASES:
        got, why = should_merge(
            {"title": a, "first_published": ta, "mastheads": set(mast)},
            {"title": b, "first_published": tb, "mastheads": set(mast)})
        mark = "ok  " if got == want else "FAIL"
        if got != want:
            failed += 1
        verb = "merge" if want else "keep apart"
        print(f"  [{mark}] {name:<32} want {verb:<10} got "
              f"{'merge' if got else 'keep apart':<10} {why}")
    print(f"\n{len(CASES) - failed}/{len(CASES)} merge fixtures correct\n")
    failed += check_coherence()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
