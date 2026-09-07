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

from editorial.same_event import should_merge  # noqa: E402

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
    print(f"\n{len(CASES) - failed}/{len(CASES)} merge fixtures correct")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
