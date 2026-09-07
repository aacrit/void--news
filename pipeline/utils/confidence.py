"""Per-article analysis confidence. One formula, two callers.

main.py and rescore.py each carried a compute_confidence, and rescore's
docstring called itself a "verbatim copy from main.py so rescore stays
consistent". It was not. main.py was recalibrated on 2026-05-13 (saturation
moved 500 to 800 words and 1000 to 1600 chars, the binary per-axis deviation
count replaced with a continuous distance, weights 30/30/40 to 25/25/50, floor
0.30 to 0.20) and the copy in rescore never received any of it. A rescored
article therefore carried a confidence on a different scale from a
pipeline-scored one, in the same column, feeding the same aggregate.

The one thing rescore genuinely needs differently is real: by the time it runs,
step 10 has truncated full_text to 300 characters for IP compliance, so
len(full_text) is no longer a measure of anything. That is what
`text_truncated` is for, and it is a parameter rather than a fork.

Factors:
    word count, saturating at 800 words                      (25%)
    text availability, saturating at 1600 characters         (25%)
    signal magnitude, continuous distance from the defaults  (50%)
"""
from __future__ import annotations

WORD_SATURATION = 800.0
CHAR_SATURATION = 1600.0
# Used only when full_text has been truncated: reconstruct the character term
# from the stored word_count. English news copy runs about 5.5 characters per
# word plus the space, so 1600 characters is roughly 250 words.
CHARS_PER_WORD = 6.4

DEFAULT_SCORES = {
    "political_lean": 50,
    "sensationalism": 10,
    "opinion_fact": 25,
    "factual_rigor": 50,
    "framing": 15,
}


def compute_confidence(article: dict, scores: dict,
                       text_truncated: bool = False) -> float:
    """Confidence in one article's bias scores, 0.05 to 1.0.

    `text_truncated`: the caller knows full_text has been cut down (rescore
    reads rows whose bodies step 10 truncated to 300 characters). The text term
    is then derived from word_count, which is stored pre-truncation, instead of
    from a length that would pin every article to the floor.
    """
    word_count = article.get("word_count", 0) or 0
    full_text = article.get("full_text", "") or ""

    # Length: 100 words = 0.125, 400 = 0.50, 800+ = 1.0
    length_conf = min(1.0, word_count / WORD_SATURATION) if word_count > 0 else 0.05

    if text_truncated and word_count > 0:
        chars = word_count * CHARS_PER_WORD
    else:
        chars = len(full_text)
    text_conf = min(1.0, max(0.05, chars / CHAR_SATURATION)) if chars else 0.05

    # Signal magnitude: continuous per-axis distance from the defaults, each
    # axis clamped at a 25-point deviation. 0 axes off-default = 0.20 (the
    # floor); all five maxed = 1.0.
    total_distance = 0.0
    for key, default_val in DEFAULT_SCORES.items():
        actual = scores.get(key, default_val)
        total_distance += min(1.0, abs(actual - default_val) / 25.0)
    signal_conf = 0.20 + (total_distance / 5.0) * 0.80

    confidence = (length_conf * 0.25) + (text_conf * 0.25) + (signal_conf * 0.50)
    return round(max(0.05, min(1.0, confidence)), 2)
