"""Unit assertions for the deterministic breaking-disaster ranking signal.

Run: python pipeline/ranker/test_disaster_signal.py
$0, no LLM, no network. Guards the two properties the signal must hold:
  (1) a real mass-casualty disaster ("Earthquake kills 111") gets a boost;
  (2) a routine policy headline and a metaphorical "killer deal" / "dead heat"
      get NO boost (multiplier == 1.0).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ranker.importance_ranker import (  # noqa: E402
    DISASTER_MAX_LIFT,
    _breaking_disaster_multiplier,
    _score_disaster_text,
)


def _sev(text: str):
    return _score_disaster_text(text)


def test_deadly_earthquake_gets_boost():
    sev, meta = _sev("Earthquake kills 111 in Afghanistan, hundreds hurt")
    assert sev > 0.0, "a deadly earthquake must score > 0"
    assert meta["has_noun"] and meta["has_casualty"]
    assert meta["death_toll"] == 111
    # Realistic path: the cluster's canonical title IS the disaster headline,
    # so the corroboration (A) branch fires from the title.
    mult, msev, _ = _breaking_disaster_multiplier(
        [{"title": "Earthquake kills 111 in Afghanistan", "summary": ""}],
        canonical_title="Earthquake kills 111 in Afghanistan",
    )
    assert mult > 1.0, "the boost must lift headline_rank"
    assert mult <= 1.0 + DISASTER_MAX_LIFT + 1e-9, "the lift must stay clamped"


def test_overmerge_bag_is_not_hijacked():
    # A non-disaster primary bag that swept in ONE stray disaster wire item
    # (1 of many members) must NOT get the boost: the title is not a disaster
    # and a single member cannot corroborate.
    members = [{"title": "Abdul El-Sayed Faces Scrutiny After Michigan Primary Win", "summary": ""}]
    members += [{"title": f"El-Sayed campaign reaction number {i}", "summary": ""} for i in range(9)]
    members += [{"title": "Helicopter fighting a wildfire crashes, pilots dead", "summary": ""}]
    mult, sev, _ = _breaking_disaster_multiplier(
        members, canonical_title="Abdul El-Sayed Faces Scrutiny After Michigan Primary Win"
    )
    assert mult == 1.0, "one stray disaster member must not hijack the cluster"


def test_corroborated_disaster_without_title_number_fires():
    # A genuine disaster whose canonical title lacks an explicit toll still
    # fires when a real share of members report casualties.
    members = [{"title": f"Boat capsizes near the harbor, {n}", "summary": "two dead after the boat capsized"} for n in range(6)]
    mult, sev, _ = _breaking_disaster_multiplier(
        members, canonical_title="Ferry Disaster in the Bay"
    )
    assert mult > 1.0, "a corroborated multi-member disaster must fire"


def test_typhoon_and_flood_toll_variants_fire():
    # toll bound to a fatal word after the noun, and death-toll phrasing.
    assert _sev("Typhoon leaves 34 dead in the Philippines")[0] > 0.0
    assert _sev("Flood death toll rises to 72 in Ceuta")[0] > 0.0
    # standalone mass-casualty (no named natural-disaster noun) still fires.
    assert _sev("Bombing kills 40 at a crowded market")[0] > 0.0


def test_routine_policy_headline_no_boost():
    sev, _ = _sev("Senate passes routine spending bill after a long debate")
    assert sev == 0.0, "a policy headline must not trigger the disaster signal"
    mult, _, _ = _breaking_disaster_multiplier(
        [{"title": "Senate passes spending bill", "summary": ""}]
    )
    assert mult == 1.0, "no disaster cue => no lift"


def test_metaphors_do_not_trigger():
    # "killer deal", "dead heat", metaphorical "earthquake", and a bare
    # non-casualty number must all score zero (no keyword hijack).
    for neg in (
        "This is a killer deal on laptops this weekend",
        "Dead heat in the polls as the two candidates tie",
        "A political earthquake shakes the ruling party",
        "Population explosion strains the city budget",
        "Group of 20 leaders meet in Rome for the summit",
    ):
        sev, _ = _sev(neg)
        assert sev == 0.0, f"false positive on: {neg!r}"
        mult, _, _ = _breaking_disaster_multiplier([{"title": neg, "summary": ""}])
        assert mult == 1.0, f"false-positive lift on: {neg!r}"


def test_severity_scales_with_toll():
    # A larger death toll should not score lower than a smaller one.
    low, _ = _sev("Landslide kills 12 in Peru")
    high, _ = _sev("Landslide kills 900 in Peru")
    assert high >= low


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(fns)} disaster-signal assertions passed.")
