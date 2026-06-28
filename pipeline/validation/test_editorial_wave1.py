"""Regression tests for the Wave 1 editorial-quality fixes (2026-06-28).

Covers the dependency-light, subtle-logic pieces:
  O5 — sanitize_editorial_text: em-dash -> comma, significance-word removal,
       and the negation guard that must NOT strip load-bearing phrases.
  O7 — feed_ranker editorial gates: opinion detection (with the "opinion poll"
       false-positive guard) and the entertainment/opinion multipliers.

The clustering validation suite (pipeline.validation.clustering.runner) covers
O6 title cleaning and O10 categorization end-to-end; this file isolates the
rules that are easy to silently regress.

Run: python -m pipeline.validation.test_editorial_wave1   (or via pytest)
"""

from utils.prohibited_terms import sanitize_editorial_text as sanitize
from ranker.feed_ranker import (
    _is_opinion,
    STORY_TYPE_GATES,
    OPINION_GATE,
)


def test_em_and_en_dash_become_comma():
    assert sanitize("Rates rose Tuesday — the third move.") == "Rates rose Tuesday, the third move."
    assert "–" not in sanitize("America Is 250 Years Young – WSJ")
    assert "—" not in sanitize("Exclusive—Dinesh D'Souza")


def test_compound_hyphens_untouched():
    assert sanitize("fact-check the twenty-four-hour claim") == "Fact-check the twenty-four-hour claim"


def test_significance_words_removed():
    assert "significant" not in sanitize("a significant weapon in the arsenal").lower()
    assert "significantly" not in sanitize("Rates rose significantly in June.").lower()
    assert "notably" not in sanitize("It was, notably, the third strike.").lower()


def test_negation_guard_preserves_meaning():
    # Dropping "significant" here would invert the factual claim — must be kept.
    assert "significant" in sanitize("Officials reported no significant damage.").lower()
    assert "notable" in sanitize("There were not notable casualties.").lower()


def test_sentence_recapitalized_after_lead_deletion():
    assert sanitize("Significant escalation followed.") == "Escalation followed."


def test_sanitize_safe_on_empty_and_none():
    assert sanitize("") == ""
    assert sanitize(None) is None


def test_opinion_detected_from_label():
    assert _is_opinion({"title": "Opinion | Harvey Mansfield: America Is 250 Years Young"})
    assert _is_opinion({"title": "Analysis | Opinion: why it matters"})
    assert _is_opinion({"content_type": "opinion", "title": "A straight news headline"})


def test_opinion_poll_is_not_opinion():
    # "Opinion poll" / "opinion of" must NOT trip the gate (no separator).
    assert not _is_opinion({"title": "Opinion poll shows Labour ahead by 5 points"})
    assert not _is_opinion({"title": "Court weighs the opinion of three justices"})


def test_entertainment_and_opinion_gates_present():
    assert STORY_TYPE_GATES.get("entertainment") == 0.78
    assert 0.0 < OPINION_GATE < 1.0


def test_same_event_cap_never_decays_canonical():
    # O8: the most-sourced ("canonical") cluster of an event must survive the
    # same-event cap even when a narrower framing outranks it.
    from ranker.feed_ranker import apply_feed_ordering
    clusters = [
        {"title": f"Filler story {i}", "headline_rank": 80 - i, "source_count": 5}
        for i in range(15)
    ]
    # Three Iran-event clusters: a narrow high-rank framing and the rich canonical.
    narrow = {"title": "UAE condemns Iran strikes", "headline_rank": 72, "source_count": 24}
    third = {"title": "Iran halts talks after Tehran strikes", "headline_rank": 61, "source_count": 18}
    canonical = {"title": "Iran-US war live: Tehran strikes bases", "headline_rank": 57, "source_count": 75}
    clusters += [narrow, third, canonical]
    apply_feed_ordering(clusters)
    # canonical keeps full headline_rank (not multiplied by EVENT_DECAY=0.80);
    # the third Iran cluster is the one decayed.
    assert canonical["rank_world"] >= 57 * 0.95
    assert third["rank_world"] <= 61 * 0.85


def test_coherence_factor_separates_legit_from_bag():
    # O9: a coherent cluster scores ~1.0; an over-merged bag scores ~0.
    from ranker.importance_ranker import _coherence_factor
    title = "Iran strikes Bahrain and Kuwait after US attack"
    legit = [{"title": t} for t in [
        "Iran attacks Bahrain military base", "Kuwait condemns Iranian strikes",
        "Bahrain reports Iranian drone strike", "US base in Kuwait hit by Iran",
    ]]
    bag = [{"title": t} for t in [
        "England wins the World Cup match", "New study on a shingles vaccine",
        "Local tree service expands hours", "Pop star collapses on a stage",
    ]]
    assert _coherence_factor(title, legit) >= 0.9
    assert _coherence_factor(title, bag) <= 0.1
    assert _coherence_factor("", legit) == 1.0  # no title -> no discount


def test_coverage_discount_deflates_bag_not_legit():
    # O9: lower coherence -> lower coverage credit; coherence 1.0 is the baseline.
    from ranker.importance_ranker import _source_coverage_score
    arts = [{"title": "x", "source_id": f"s{i}"} for i in range(20)]
    sm = {f"s{i}": {"tier": "international", "country": "GB"} for i in range(20)}
    legit_cov = _source_coverage_score(arts, sm, None, coherence=1.0)
    bag_cov = _source_coverage_score(arts, sm, None, coherence=0.1)
    assert legit_cov > 0
    assert bag_cov < legit_cov


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  [PASS] {fn.__name__}")
    print(f"\n{passed}/{len(fns)} editorial Wave-1 tests passed")


if __name__ == "__main__":
    _run()
