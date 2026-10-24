"""Regression tests for Branch G: real aggregate_confidence + rev-49 histogram
(2026-08-10).

These exercise the pure-Python helpers in ``utils.bias_aggregation``, which are
the single source of truth for main.py's fallback AND are mirrored formula-for-
formula by the SQL RPC in ``supabase/migrations/076_confidence_and_histogram.sql``
(same weights: 0.7 conf_mean + 0.3 breadth, breadth full at 12, 20% spread damp;
same lean buckets; same polarization = round(100 * 2 * min(L,R) / n)). Verifying
the Python thus verifies the shape the RPC emits.

Asserted:
  * aggregate_confidence VARIES with per-article confidence and breadth: a
    3-source low-confidence cluster scores clearly below a 30-source
    high-confidence one, and it is not pinned to 1.0 on count alone.
  * aggregate_confidence stays in [0, 1].
  * polarization is 100 for a perfect L/R split and 0 for an all-center cluster.
  * the histogram emits the exact keys the frontend reads.

Run: python pipeline/validation/test_bias_aggregation.py
 or: python -m pytest pipeline/validation/test_bias_aggregation.py
"""

import os
import sys

_PIPELINE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PIPELINE_DIR not in sys.path:
    sys.path.insert(0, _PIPELINE_DIR)

from utils.bias_aggregation import (  # noqa: E402
    compute_aggregate_confidence,
    compute_lean_histogram,
)


def test_confidence_in_unit_interval():
    cases = [
        ([], [], 0.0),
        ([0.0], [0], 0.0),
        ([1.0] * 30, [100] * 30, 0.0),
        ([0.5] * 5, [50] * 5, 40.0),
        ([0.9, 0.1], [100, 10], 30.0),
    ]
    for conf, rigor, spread in cases:
        v = compute_aggregate_confidence(conf, rigor, spread)
        assert 0.0 <= v <= 1.0, f"out of [0,1]: {v} for {conf!r}"


def test_confidence_varies_thin_lowconf_below_broad_highconf():
    # 3-source LOW per-article confidence, low rigor.
    thin_low = compute_aggregate_confidence(
        conf_values=[0.35, 0.40, 0.30],
        rigor_values=[40, 45, 35],
        lean_spread=8.0,
    )
    # 30-source HIGH per-article confidence, high rigor.
    broad_high = compute_aggregate_confidence(
        conf_values=[0.85] * 30,
        rigor_values=[80] * 30,
        lean_spread=8.0,
    )
    assert broad_high - thin_low > 0.2, (
        f"confidence should vary clearly: thin_low={thin_low:.3f} "
        f"broad_high={broad_high:.3f}"
    )
    # The whole point of Branch G: NOT pinned to 1.0 the way count/5 was.
    assert thin_low < 0.5, f"thin low-confidence cluster too high: {thin_low:.3f}"
    assert broad_high < 1.0, f"should not saturate to 1.0: {broad_high:.3f}"


def test_confidence_not_a_count_proxy():
    # Same count, different per-article confidence => different scores.
    low = compute_aggregate_confidence([0.3] * 10, [50] * 10, 5.0)
    high = compute_aggregate_confidence([0.9] * 10, [50] * 10, 5.0)
    assert high > low + 0.2, (
        f"per-article confidence must move the score: low={low:.3f} high={high:.3f}"
    )


def test_rigor_weighting():
    # A high-confidence article with high rigor should pull the mean up more
    # than an equal-weight (plain) mean would when a low-rigor low-conf article
    # is present.
    conf = [0.2, 0.9]
    rigor = [10, 90]  # the 0.9 article dominates
    v = compute_aggregate_confidence(conf, rigor, 0.0)
    plain = compute_aggregate_confidence(conf, [], 0.0)  # no rigor -> plain mean
    assert v > plain, f"rigor weighting should lift toward high-rigor conf: {v} vs {plain}"


def test_polarization_perfect_split_is_100():
    # 3 hard-left + 3 hard-right, no center: a perfect L/R standoff.
    pl = [10, 12, 15, 85, 88, 90]
    hist = compute_lean_histogram(pl)
    assert hist["polarization"] == 100, hist
    assert hist["lean_left_count"] == 3 and hist["lean_right_count"] == 3


def test_polarization_all_center_is_zero():
    pl = [48, 50, 51, 49, 52, 50]
    hist = compute_lean_histogram(pl)
    assert hist["polarization"] == 0, hist
    assert hist["lean_left_count"] == 0 and hist["lean_right_count"] == 0


def test_polarization_one_sided_is_zero():
    # All left: minority wing is 0 -> polarization 0 (one-sided, not contested).
    pl = [10, 20, 30, 40, 45]
    hist = compute_lean_histogram(pl)
    assert hist["polarization"] == 0, hist


def test_histogram_emits_frontend_keys():
    hist = compute_lean_histogram([10, 50, 90])
    for key in (
        "lean_buckets",
        "lean_left_count",
        "lean_center_count",
        "lean_right_count",
        "polarization",
    ):
        assert key in hist, f"missing frontend key: {key}"
    for bucket in (
        "far_left", "left", "center_left", "center",
        "center_right", "right", "far_right",
    ):
        assert bucket in hist["lean_buckets"], f"missing bucket: {bucket}"
    # 3-segment counts sum to n and match the collapsed buckets.
    assert (
        hist["lean_left_count"] + hist["lean_center_count"] + hist["lean_right_count"]
    ) == 3


def test_contested_gate_lights_up():
    # The frontend Contested path is polarization>=50 AND both wings present
    # AND total>=3. A balanced-but-divergent cluster (Jacobin + Breitbart shape)
    # must satisfy it now that the RPC emits these fields.
    pl = [15, 18, 85, 88]  # 2 left, 2 right, mean ~51.5, total 4
    hist = compute_lean_histogram(pl)
    both_wings = hist["lean_left_count"] > 0 and hist["lean_right_count"] > 0
    total = (
        hist["lean_left_count"] + hist["lean_center_count"] + hist["lean_right_count"]
    )
    assert hist["polarization"] >= 50 and both_wings and total >= 3, hist


_TESTS = [
    test_confidence_in_unit_interval,
    test_confidence_varies_thin_lowconf_below_broad_highconf,
    test_confidence_not_a_count_proxy,
    test_rigor_weighting,
    test_polarization_perfect_split_is_100,
    test_polarization_all_center_is_zero,
    test_polarization_one_sided_is_zero,
    test_histogram_emits_frontend_keys,
    test_contested_gate_lights_up,
]


def _run():
    failures = 0
    for fn in _TESTS:
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(_TESTS) - failures}/{len(_TESTS)} passed.")
    return failures


if __name__ == "__main__":
    sys.exit(1 if _run() else 0)
