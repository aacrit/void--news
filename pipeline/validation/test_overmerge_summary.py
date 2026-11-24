"""Regression tests for the summary-must-match-dominant-topic fix (2026-08-07).

Layer 3 of the CEO-directed over-merge fix set: even when an over-merged bag
slips the clustering gates, the shipped summary must describe the cluster's
DOMINANT (title) topic, never a minority member. These isolate the
deterministic on-topic input filter (`_filter_ontopic_articles`) that all four
LLM summary passes funnel through.

Run: python -m pipeline.validation.test_overmerge_summary   (or via pytest)
"""

from summarizer.cluster_summarizer import (
    _filter_ontopic_articles,
    _build_dominant_topic_line,
)


def _art(aid, title, text=""):
    return {"id": aid, "title": title, "summary": title, "full_text": text or title}


def test_bag_summary_anchors_on_title_not_larger_member():
    # Title is topic A (axis military cooperation); 3 of 4 members are topic B
    # (veteran benefits) bridged only by the generic word "military". The summary
    # input must keep the TITLE story and drop the (larger) veteran sub-pile.
    bag = [
        _art("axis", "Axis of Aggressors Deepen Military Cooperation",
             "Russia China Iran North Korea axis deepen military cooperation treaty"),
        _art("vet1", "Military Times: Veterans Fight Congress Over Benefits Cuts"),
        _art("vet2", "Veterans Groups Press Congress on Benefits Backlog at VA"),
        _art("vet3", "Congress Stalls on Veterans Benefits as VA Backlog Grows"),
    ]
    kept = {a["id"] for a in _filter_ontopic_articles(
        bag, cluster_title="Axis of Aggressors Deepen Military Cooperation")}
    assert "axis" in kept
    assert not (kept & {"vet1", "vet2", "vet3"})


def test_generic_supreme_court_bridge_does_not_keep_off_topic_member():
    # Title = an Indian Supreme Court case; majority = US SCOTUS. They share only
    # the generic "Supreme Court". The summary must follow the TITLE (Indian).
    sc = [
        _art("in", "Supreme Court Stays Arrest of Banerjee Aide in Bengal"),
        _art("us1", "Supreme Court Weighs Louisiana Voting Map"),
        _art("us2", "Supreme Court Hears Louisiana Redistricting Case"),
        _art("us3", "Supreme Court Reviews Louisiana Gerrymander Challenge"),
    ]
    kept = {a["id"] for a in _filter_ontopic_articles(
        sc, cluster_title="Supreme Court Stays Arrest of Banerjee Aide in Bengal")}
    assert "in" in kept
    assert not (kept & {"us1", "us2", "us3"})


def test_coherent_cluster_is_left_whole():
    # One real story, varied headline vocabulary — every member must survive.
    coh = [
        _art("c1", "Typhoon Rai Slams Philippines, Dozens Dead in Cebu"),
        _art("c2", "Rai Death Toll Climbs as Cebu and Bohol Reel"),
        _art("c3", "Philippines Declares Emergency After Typhoon Rai"),
        _art("c4", "Aid Rushes to Cebu as Typhoon Rai Aftermath Grips Region"),
    ]
    kept = _filter_ontopic_articles(
        coh, cluster_title="Typhoon Rai Slams Philippines, Dozens Dead in Cebu")
    assert len(kept) == 4


def test_small_cluster_is_noop():
    # < 4 members: the filter must never touch the input.
    small = [_art("a", "Some Story"), _art("b", "Another Story")]
    assert _filter_ontopic_articles(small, cluster_title="Some Story") is small


def test_anchor_matching_nothing_falls_back_to_full_membership():
    # A title that shares nothing with any member must NOT blank the summary.
    arts = [
        _art("m1", "City Council Approves Budget"),
        _art("m2", "City Council Debates Zoning"),
        _art("m3", "City Council Hires Auditor"),
        _art("m4", "City Council Sets Meeting"),
    ]
    kept = _filter_ontopic_articles(arts, cluster_title="Distant Volcano Erupts Overnight")
    assert len(kept) == 4


def test_dominant_topic_line_prefers_specific_terms():
    bag = [
        _art("axis", "Axis of Aggressors Deepen Military Cooperation"),
        _art("vet1", "Military Times: Veterans Fight Congress Over Benefits"),
        _art("vet2", "Veterans Groups Press Congress on Benefits Backlog"),
        _art("vet3", "Congress Stalls on Veterans Benefits at VA"),
    ]
    line = _build_dominant_topic_line(
        bag, "Axis of Aggressors Deepen Military Cooperation").lower()
    # Title's specific terms lead; the generic bridge word must not dominate.
    assert "axis" in line or "aggressors" in line


def _run():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"PASS {fn.__name__}")
    print(f"\nAll {len(fns)} tests passed.")


if __name__ == "__main__":
    _run()
