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
