"""
Signal decomposition for bias engine validation.

Decomposes final scores into per-signal contributions using known weights
from each analyzer. Used to detect dead signals (signals that contribute
negligibly across all test articles).
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Weight constants (must match the analyzers exactly)
# ---------------------------------------------------------------------------

# opinion_detector.py weights (sum = 1.00)
OPINION_WEIGHTS: dict[str, float] = {
    "pronoun":     0.12,
    "subjectivity": 0.18,
    "modal":       0.12,
    "hedging":     0.06,
    "attribution": 0.15,
    "metadata":    0.12,
    "rhetorical":  0.06,
    "value_judg":  0.06,
    "absolutist":  0.13,
}

# factual_rigor.py weights (sum = 1.00 before ref_bonus)
# Named values from the weighted combination formula
RIGOR_WEIGHTS: dict[str, float] = {
    "named_src":   0.22,
    "org_cite":    0.24,
    "data_stats":  0.27,
    "quotes":      0.17,
    "specificity": 0.10,
    # ref_bonus is capped at 8.0 pts flat — not a simple weight*sub-score
    # We track it separately as a flat addition
}
RIGOR_REF_BONUS_MAX = 8.0

# framing.py weights (dynamic: kw_emphasis > 60 shifts weights)
FRAMING_WEIGHTS_NORMAL: dict[str, float] = {
    "connotation": 0.25,
    "keyword_emp": 0.30,
    "omission":    0.20,
    "headline_div": 0.15,
    "passive":     0.10,
}
FRAMING_WEIGHTS_HIGH_KW: dict[str, float] = {
    "connotation": 0.15,
    "keyword_emp": 0.40,
    "omission":    0.20,
    "headline_div": 0.15,
    "passive":     0.10,
}


# ---------------------------------------------------------------------------
# Decomposition functions
# ---------------------------------------------------------------------------

def decompose_lean(rationale: dict, final_score: int) -> dict:
    """
    Decompose political lean score into signal contributions.

    The lean analyzer blends text_score with source_baseline using
    adaptive weights. The rationale does not expose the exact blend
    weights, so we reconstruct approximate contributions from the
    sub-scores that are available.

    Returns a decomposition dict with named signals.
    """
    kw = rationale.get("keyword_score", 50.0)
    framing_shift = rationale.get("framing_shift", 0.0)
    entity_shift = rationale.get("entity_shift", 0.0)
    baseline = rationale.get("source_baseline", 50.0)
    state_affiliated = rationale.get("state_affiliated", False)

    # text_score = keyword + framing + entity (clamped to 0-100)
    raw_text = kw + framing_shift + entity_shift
    text_score = max(0.0, min(100.0, raw_text))

    # Approximate the blend: we know final = text_w * text_score + base_w * baseline
    # Estimate text_weight from the deviation
    if abs(text_score - float(baseline)) < 0.5:
        # Indeterminate; assume equal blend
        estimated_text_w = 0.5
    else:
        estimated_text_w = (float(final_score) - float(baseline)) / (text_score - float(baseline))
        estimated_text_w = max(0.0, min(1.0, estimated_text_w))
    estimated_base_w = 1.0 - estimated_text_w

    # Within the text portion, attribute by relative magnitude
    text_range = abs(raw_text - 50.0) or 1.0
    kw_deviation = abs(kw - 50.0)
    framing_deviation = abs(framing_shift)
    entity_deviation = abs(entity_shift)
    total_deviation = kw_deviation + framing_deviation + entity_deviation or 1.0

    kw_contrib = estimated_text_w * (kw_deviation / total_deviation) * abs(float(final_score) - float(baseline))
    framing_contrib = estimated_text_w * (framing_deviation / total_deviation) * abs(float(final_score) - float(baseline))
    entity_contrib = estimated_text_w * (entity_deviation / total_deviation) * abs(float(final_score) - float(baseline))
    base_contrib = estimated_base_w * abs(float(baseline) - 50.0)

    # Normalise contributions as percentage of final score deviation from 50
    final_dev = abs(float(final_score) - 50.0) or 1.0

    return {
        "keyword_score": {
            "raw_value": float(kw),
            "weight": estimated_text_w * (kw_deviation / total_deviation),
            "contribution": kw_contrib,
            "pct_of_final": round(kw_contrib / final_dev * 100, 1),
        },
        "framing_shift": {
            "raw_value": float(framing_shift),
            "weight": estimated_text_w * (framing_deviation / total_deviation),
            "contribution": framing_contrib,
            "pct_of_final": round(framing_contrib / final_dev * 100, 1),
        },
        "entity_shift": {
            "raw_value": float(entity_shift),
            "weight": estimated_text_w * (entity_deviation / total_deviation),
            "contribution": entity_contrib,
            "pct_of_final": round(entity_contrib / final_dev * 100, 1),
        },
        "source_baseline": {
            "raw_value": float(baseline),
            "weight": estimated_base_w,
            "contribution": base_contrib,
            "pct_of_final": round(base_contrib / final_dev * 100, 1),
        },
    }


def decompose_sensationalism(rationale: dict, final_score: int) -> dict:
    """
    Decompose sensationalism score into signal contributions.

    The sensationalism analyzer combines headline_score and body_score
    at 50/50 and applies a floor-stretch transform. We decompose at the
    pre-stretch level using sub-signal densities from the rationale.
    """
    h_score = rationale.get("headline_score", 0.0)
    b_score = rationale.get("body_score", 0.0)

    # The headline contribution to the combined score
    combined = 0.5 * h_score + 0.5 * b_score
    final_f = float(final_score)

    # Headline and body each have 50% weight in combined
    h_contrib = 0.5 * float(h_score)
    b_contrib = 0.5 * float(b_score)

    # Within body, approximate signal contributions from densities
    sup_density = rationale.get("superlative_density", 0.0)
    urg_density = rationale.get("urgency_density", 0.0)
    hyp_density = rationale.get("hyperbole_density", 0.0)
    meas_density = rationale.get("measured_density", 0.0)
    partisan_density = rationale.get("partisan_attack_density", 0.0)
    clickbait = rationale.get("clickbait_signals", 0)

    # Approximate relative body signal contributions (body is 50% of combined)
    # These are directional only — exact weights are complex within _body_score
    body_signals = {
        "superlative":   sup_density * 5.0,
        "urgency":       urg_density * 8.0,
        "hyperbole":     hyp_density * 5.0,
        "partisan":      partisan_density * 16.0,
        "measured_inv":  meas_density * 4.0,
    }
    body_total = sum(v for k, v in body_signals.items() if k != "measured_inv") or 1.0

    denom = max(combined, 1.0)

    return {
        "headline": {
            "raw_value": float(h_score),
            "weight": 0.5,
            "contribution": h_contrib,
            "pct_of_final": round(h_contrib / denom * 100, 1),
        },
        "body_total": {
            "raw_value": float(b_score),
            "weight": 0.5,
            "contribution": b_contrib,
            "pct_of_final": round(b_contrib / denom * 100, 1),
        },
        "clickbait_signals": {
            "raw_value": float(clickbait),
            "weight": None,
            "contribution": None,
            "pct_of_final": None,
        },
        "superlative": {
            "raw_value": float(sup_density),
            "weight": None,
            "contribution": 0.5 * body_signals["superlative"],
            "pct_of_final": round(0.5 * body_signals["superlative"] / denom * 100, 1),
        },
        "urgency": {
            "raw_value": float(urg_density),
            "weight": None,
            "contribution": 0.5 * body_signals["urgency"],
            "pct_of_final": round(0.5 * body_signals["urgency"] / denom * 100, 1),
        },
        "hyperbole": {
            "raw_value": float(hyp_density),
            "weight": None,
            "contribution": 0.5 * body_signals["hyperbole"],
            "pct_of_final": round(0.5 * body_signals["hyperbole"] / denom * 100, 1),
        },
        "partisan_attack": {
            "raw_value": float(partisan_density),
            "weight": None,
            "contribution": 0.5 * body_signals["partisan"],
            "pct_of_final": round(0.5 * body_signals["partisan"] / denom * 100, 1),
        },
        "measured_inverse": {
            "raw_value": float(meas_density),
            "weight": None,
            "contribution": -0.5 * body_signals["measured_inv"],
            "pct_of_final": round(-0.5 * body_signals["measured_inv"] / denom * 100, 1),
        },
    }


def decompose_opinion(rationale: dict, final_score: int) -> dict:
    """
    Decompose opinion score using known weights:
    pronoun(0.12) + subjectivity(0.18) + modal(0.12) + hedging(0.06)
    + attribution(0.15) + metadata(0.12) + rhetorical(0.06)
    + value_judg(0.06) + absolutist(0.13) = 1.00

    Maps rationale keys to canonical signal names and computes weighted
    contributions. Note: metadata overrides (floor logic) are reflected
    in the final score but not in simple weighted decomposition.
    """
    sub_scores = {
        "pronoun":     rationale.get("pronoun_score", 0.0),
        "subjectivity": rationale.get("subjectivity_score", 0.0),
        "modal":       rationale.get("modal_score", 0.0),
        "hedging":     rationale.get("hedging_score", 0.0),
        "attribution": rationale.get("attribution_score", 0.0),
        "metadata":    rationale.get("metadata_score", 0.0),
        "rhetorical":  rationale.get("rhetorical_score", 0.0),
        "value_judg":  rationale.get("value_judgment_score", 0.0),
        "absolutist":  rationale.get("absolutist_assertion_score", 0.0),
    }

    result = {}
    weighted_sum = 0.0
    for signal, weight in OPINION_WEIGHTS.items():
        raw = float(sub_scores.get(signal, 0.0))
        contribution = raw * weight
        weighted_sum += contribution
        result[signal] = {
            "raw_value": raw,
            "weight": weight,
            "contribution": round(contribution, 2),
            "pct_of_final": round(contribution / max(float(final_score), 1.0) * 100, 1),
        }

    result["_weighted_sum"] = {
        "raw_value": round(weighted_sum, 1),
        "weight": 1.0,
        "contribution": round(weighted_sum, 1),
        "pct_of_final": 100.0,
    }
    return result


def decompose_rigor(rationale: dict, final_score: int) -> dict:
    """
    Decompose factual rigor score using known weights:
    named_src(0.22) + org_cite(0.24) + data_stats(0.27)
    + quotes(0.17) + specificity(0.10)

    Note: ref_bonus and tier blending affect the final score but are
    not directly deducible from the rationale. We reconstruct approximate
    sub-scores from raw counts using analyzer formulas.
    """
    # Reconstruct sub-scores from raw counts using known analyzer formulas
    named_raw = rationale.get("named_sources_count", 0)
    org_raw = rationale.get("org_citations_count", 0)
    data_raw = rationale.get("data_points_count", 0)
    quotes_raw = rationale.get("direct_quotes_count", 0)
    vague_count = rationale.get("vague_sources_count", 0)
    spec_ratio = rationale.get("specificity_ratio", 0.0)

    # Reconstruct sub-scores using analyzer formulas
    named_score = min(100.0, named_raw * 20.0)
    org_score = min(100.0, org_raw * 25.0)
    # data_stats: data_per_100 * 33, but we don't know word count; use raw count / estimate
    # Since we don't have word_count, use a proxy: raw / (raw/3 max logic)
    # Actually just use the counts directly with the formula assuming 100-word doc
    # This is an approximation — the actual score depends on word count
    data_score = min(100.0, data_raw * 33.0 / max(1.0, data_raw / 3.0)) if data_raw > 0 else 0.0
    # Simpler: approximate data_score from raw count (3 data points per 100 words = 100)
    data_score = min(100.0, data_raw * 10.0)  # rough approximation
    quotes_score = min(100.0, quotes_raw * 20.0)  # quotes per 500 words * 20
    spec_score = float(spec_ratio) * 100.0 if spec_ratio else 50.0

    weights = RIGOR_WEIGHTS
    result = {}
    for signal, weight in weights.items():
        sub_score_map = {
            "named_src":   named_score,
            "org_cite":    org_score,
            "data_stats":  data_score,
            "quotes":      quotes_score,
            "specificity": spec_score,
        }
        raw = sub_score_map[signal]
        contribution = raw * weight
        result[signal] = {
            "raw_value": round(raw, 1),
            "weight": weight,
            "contribution": round(contribution, 2),
            "pct_of_final": round(contribution / max(float(final_score), 1.0) * 100, 1),
        }

    # Vague penalty (not a weight — it's a direct deduction)
    vague_penalty = min(15.0, vague_count * 3.0)
    result["vague_penalty"] = {
        "raw_value": float(vague_count),
        "weight": -3.0,
        "contribution": round(-vague_penalty, 2),
        "pct_of_final": round(-vague_penalty / max(float(final_score), 1.0) * 100, 1),
    }

    return result


def decompose_framing(rationale: dict, final_score: int) -> dict:
    """
    Decompose framing score into signal contributions.

    Weights are dynamic: when keyword_emphasis_score > 60, keyword_emp
    weight shifts from 0.25 to 0.35 and connotation from 0.25 to 0.15.
    """
    kw_emp = float(rationale.get("keyword_emphasis_score", 0.0))
    connotation = float(rationale.get("connotation_score", 0.0))
    omission = float(rationale.get("omission_score", 0.0))
    headline_div = float(rationale.get("headline_body_divergence", 0.0))
    passive = float(rationale.get("passive_voice_score", 0.0))
    has_cluster = rationale.get("has_cluster_context", False)

    # Select weight set based on keyword_emphasis_score
    if kw_emp > 60:
        weights = FRAMING_WEIGHTS_HIGH_KW
    else:
        weights = FRAMING_WEIGHTS_NORMAL

    sub_scores = {
        "connotation": connotation,
        "keyword_emp": kw_emp,
        "omission":    omission,
        "headline_div": headline_div,
        "passive":     passive,
    }

    result = {}
    for signal, weight in weights.items():
        raw = sub_scores[signal]
        contribution = raw * weight
        result[signal] = {
            "raw_value": round(raw, 1),
            "weight": weight,
            "contribution": round(contribution, 2),
            "pct_of_final": round(contribution / max(float(final_score), 1.0) * 100, 1),
        }

    result["has_cluster_context"] = {
        "raw_value": float(has_cluster),
        "weight": None,
        "contribution": None,
        "pct_of_final": None,
    }

    return result


def detect_dead_signals(all_decompositions: list[dict]) -> list[str]:
    """
    Flag signals that contribute less than 1% (mean) across all test articles.

    Args:
        all_decompositions: List of decomposition dicts, one per axis per article.
            Each element should be from decompose_lean/sensationalism/opinion/rigor/framing.

    Returns:
        List of signal names where mean absolute pct_of_final < 1.0.
    """
    signal_pcts: dict[str, list[float]] = {}

    for decomp in all_decompositions:
        for signal_name, signal_data in decomp.items():
            if signal_name.startswith("_"):
                continue
            if not isinstance(signal_data, dict):
                continue
            pct = signal_data.get("pct_of_final")
            if pct is not None:
                signal_pcts.setdefault(signal_name, []).append(abs(float(pct)))

    dead_signals = []
    for signal_name, pcts in signal_pcts.items():
        if not pcts:
            continue
        mean_pct = sum(pcts) / len(pcts)
        if mean_pct < 1.0:
            dead_signals.append(f"{signal_name} (mean {mean_pct:.2f}%)")

    return sorted(dead_signals)


def summarize_decomposition(decomp: dict, axis: str) -> str:
    """
    Format a decomposition dict as a compact human-readable summary.

    Returns a string like: "keyword_score=85.2%(37%) framing_shift=-2.1%(5%) ..."
    """
    parts = []
    for signal_name, data in decomp.items():
        if signal_name.startswith("_"):
            continue
        if not isinstance(data, dict):
            continue
        raw = data.get("raw_value")
        pct = data.get("pct_of_final")
        if raw is None:
            continue
        if pct is not None:
            parts.append(f"{signal_name}={raw:.1f}({pct:.0f}%)")
        else:
            parts.append(f"{signal_name}={raw:.1f}")
    return f"[{axis}] " + "  ".join(parts)
