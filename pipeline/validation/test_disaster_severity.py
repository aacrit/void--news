#!/usr/bin/env python3
"""The mass-casualty signal, including the epidemics it used to be blind to.

_DISASTER_NOUNS listed 40 hazard nouns and not one disease term, so a slow
mass-casualty event scored nothing: "Bangladesh Measles Outbreak Kills Over
1,000 Children Since March" scored disaster_severity 0.0 on the 2026-09-09
production feed, got no lift, and landed at slot 14, below a story about a
television network denying a cancellation rumour.

The keep-list is the point of this file. A disease noun is far more likely to
appear in a metaphor than an earthquake is ("outbreak of optimism", "viral
video"), so the co-occurrence requirement with a casualty cue has to hold.

Run: python pipeline/validation/test_disaster_severity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ranker.importance_ranker import _score_disaster_text  # noqa: E402


def _sev(text: str) -> float:
    r = _score_disaster_text(text)
    return float(r[0] if isinstance(r, tuple) else r)


# Real mass-casualty events that must score.
_SCORES = [
    "Bangladesh Measles Outbreak Kills Over 1,000 Children Since March",
    "Cholera epidemic kills 240 in Sudan camps",
    "Ebola outbreak has killed 1,200 in eastern provinces",
    "Famine in Sudan has killed an estimated 30,000 since January",
    # The gap in the death-toll pattern was 25 characters, shorter than real
    # wire phrasing. NPR's line needs 31.
    "The death toll among children just surpassed 1,000",
    # The hazards that already worked must keep working.
    "Landslide kills 45 in Nepal's Sindhupalchowk district",
    "Earthquake death toll rises to 300 in Herat province",
]

# A disease noun with no casualty cue, or used as a metaphor. None may score.
_QUIET = [
    "Outbreak of optimism lifts European shares",
    "Viral video sparks debate over school policy",
    "Measles vaccine rollout reaches 18 million children",
    "Famine warning issued as rains fail across the Horn",
    "WHO monitors dengue outbreak in northern districts",
    "Pandemic-era rules on remote work are quietly expiring",
    # Cases are not deaths, and the signal is right to stay quiet on them.
    "DR Congo Ebola Outbreak Surpasses 5,000 Cases; WHO Declares Global Emergency",
]


def test_mass_casualty_events_score():
    for t in _SCORES:
        assert _sev(t) > 0, f"should score: {t!r}"


def test_metaphors_and_non_casualty_stay_quiet():
    for t in _QUIET:
        assert _sev(t) == 0, f"should NOT score: {t!r} (got {_sev(t)})"


def test_known_gap_spelled_out_numbers():
    # Documented, not fixed here: the death-toll patterns require a digit, so a
    # headline that spells the number out scores nothing. Widening this needs
    # its own false-positive sweep ("kills two birds with one stone"), so it is
    # recorded as a gap rather than papered over.
    assert _sev("Greek Air Force Jet Crashes at Athens Airshow, Kills Two") == 0


def _run() -> int:
    failures = 0
    for fn in (test_mass_casualty_events_score,
               test_metaphors_and_non_casualty_stay_quiet,
               test_known_gap_spelled_out_numbers):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run())
