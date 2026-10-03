"""Regression tests for the academic-journal artifact ingestion filter (2026-08-10).

Branch E (source hygiene): three Nature "Author Correction" / "Publisher
Correction" / "Editorial Expression of Concern" journal errata were ingested as
news in the 2026-08-10 run and landed in a story cluster. `newsworthiness` now
drops journal corrections / errata / retraction notices matched as TITLE
PREFIXES, while a real news story that merely CONTAINS "correction"/"retraction"
mid-title (Retraction Watch, wire corrections about statements) survives.

Run: python pipeline/validation/test_academic_artifact_filter.py
 or: python -m pytest pipeline/validation/test_academic_artifact_filter.py
"""

import os
import sys

# Make `categorizer.newsworthiness` importable whether run from repo root, the
# pipeline/ dir, or via pytest.
_PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PIPELINE_DIR not in sys.path:
    sys.path.insert(0, _PIPELINE_DIR)

from categorizer.newsworthiness import (  # noqa: E402
    is_evergreen_junk,
    newsworthiness,
)


# --- titles that MUST be dropped (real Nature 2026-08-10 leak + siblings) ----
_DROP_TITLES = [
    "Author Correction: Nucleolar URB1 ensures 3' ETS rRNA removal to prevent exosome surveillance",
    "Author Correction: Cooperation conflicts with equality when allocating public goods",
    "Author Correction: Casdatifan shows durable response linked to HIF-2a biology in kidney cancer",
    "Publisher Correction: Progressive plasticity during colorectal cancer metastasis",
    "Editorial Expression of Concern: Tumour exosome integrins determine organotropic metastasis",
    "Expression of Concern: Some study title here",
    "Erratum: A prior article's title",
    "Erratum to: A prior article's title",
    "Corrigendum: Another study",
    "Corrigenda: Another study",
    "Retraction: The fabricated results paper",
    "Retraction of: The fabricated results paper",
    "Retraction Note: The fabricated results paper",
    "Retracted Article: The fabricated results paper",
    "Author response to: Reviewer comments on our method",
    "Reviewer acknowledgements 2026",
    "Reviewer acknowledgement 2026",
    "Matters Arising: Reassessing the reported effect",
    "Correction: The figure in our earlier paper was mislabelled",
    # bracketed / quoted lead-in still drops
    "[Author Correction] Some paper title",
    "  Publisher Correction: leading whitespace paper",
]

# --- titles that MUST be kept (contain the words, but not as a prefix) -------
_KEEP_TITLES = [
    # Retraction Watch journalism (the source that also appears in the window)
    "High-profile anesthesiologists earning retractions for data, image problems",
    "Clarivate removes hold on mega-journal Heliyon after internal audit, 650+ retractions",
    "Weekend reads: Second gene editing death in China reported; a resignation; retractions",
    # real news that contains "correction" mid-title
    "Police issue correction to earlier statement on suspect count",
    "Reuters issues a correction to jobs-report story",
    "Government forced to make a correction after data error",
    "JU forms probe body over research paper retractions",
    # words appearing but clearly hard news
    "Erratum-free reporting pledged as newsroom overhauls fact-checking",
    "Concern grows over expression of dissent in new law",
]


def test_academic_artifacts_are_dropped():
    for t in _DROP_TITLES:
        v = newsworthiness({"title": t})
        assert v["is_junk"] is True, f"should DROP but kept: {t!r}"
        assert v.get("academic_artifact") is True, f"artifact flag missing: {t!r}"
        assert is_evergreen_junk({"title": t}) is True


def test_real_news_with_correction_words_is_kept():
    for t in _KEEP_TITLES:
        v = newsworthiness({"title": t})
        assert v["is_junk"] is False, f"should KEEP but dropped: {t!r}"
        assert v.get("academic_artifact") is not True, (
            f"false artifact flag on: {t!r}")


def test_artifact_drop_is_veto_proof():
    # A correction whose title also carries a hard news verb ("shows") must
    # still drop; the academic-artifact check runs before the news-event veto.
    t = "Author Correction: Casdatifan shows durable response in kidney cancer"
    assert newsworthiness({"title": t})["is_junk"] is True


def test_missing_title_fails_open():
    assert is_evergreen_junk({"title": ""}) is False
    assert is_evergreen_junk({}) is False


def _run():
    failures = 0
    for fn in (test_academic_artifacts_are_dropped,
               test_real_news_with_correction_words_is_kept,
               test_artifact_drop_is_veto_proof,
               test_missing_title_fails_open):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{4 - failures}/4 passed.")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
