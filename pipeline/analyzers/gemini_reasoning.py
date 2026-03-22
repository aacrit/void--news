"""
Gemini bias reasoning module for the void --news pipeline.

Adds LLM contextual reasoning to deterministic bias scores. Runs per-cluster,
reviewing rule-based scores and providing bounded adjustments + human-readable
reasoning for the cases where pattern matching missed context.

Design constraints:
    - Never adjusts scores based on outlet identity (source names are anonymized)
    - Max delta per axis: ±20 points
    - Per-axis blend weights: lean=0.35, framing=0.40, opinion=0.30,
      sensationalism=0.20, rigor=0.15
    - Separate call budget from summarization: _MAX_REASONING_CALLS = 25
    - Uses count_call=False (does not draw from summarization's 25-call cap)
    - At 6 runs/day: 150 RPD = 10% of the 1500 RPD free limit

Architecture mirrors cluster_summarizer.py:
    - Module-level system instruction (set once per API call)
    - Per-cluster prompt built from article context + deterministic scores
    - _validate_reasoning() enforces response shape and delta clamps
    - Falls back gracefully (returns empty dict) on any failure
"""

from summarizer.gemini_client import generate_json, is_available


# ---------------------------------------------------------------------------
# Per-axis blend weights — how much Gemini's delta shifts the final score.
# Lower weights = Gemini is a minor corrective signal, not a replacement.
# Framing (0.40) is the highest: framing is most context-dependent and
# hardest for rule-based pattern matching to calibrate correctly.
# Rigor (0.15) is lowest: NER counts and data patterns are objective signals
# that rarely benefit from LLM reinterpretation.
# ---------------------------------------------------------------------------
_BLEND_WEIGHTS: dict[str, float] = {
    "political_lean": 0.35,
    "framing": 0.40,
    "opinion_fact": 0.30,
    "sensationalism": 0.20,
    "factual_rigor": 0.15,
}

# Maximum absolute delta Gemini may propose per axis.
# Hard-clamped in _validate_reasoning; protects against hallucinated extremes.
_MAX_DELTA: int = 20

# Minimum cluster size to qualify for reasoning (must have at least 2 articles
# to make cross-article coherence analysis meaningful).
_MIN_ARTICLES: int = 2

# Maximum articles included in the reasoning prompt per cluster.
# Keeping this at 8 (same as summarizer's max_articles default) ensures
# the prompt stays well within Gemini Flash's context window.
_MAX_PROMPT_ARTICLES: int = 8

# Separate call budget from summarization.
_MAX_REASONING_CALLS: int = 25
_reasoning_call_count: int = 0

# Tier label map — mirrors cluster_summarizer._build_articles_block() exactly.
_TIER_LABEL_MAP: dict[str, str] = {
    "us_major": "US Source",
    "international": "International Source",
    "independent": "Independent Source",
}


# ---------------------------------------------------------------------------
# System instruction — defines the reasoning role.
# Passed as the system turn so it is persistent across the prompt.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are a media bias analyst at void --news, a neutral news intelligence service.
You review rule-based NLP bias scores and provide contextual corrections and reasoning.
You have no political perspective. You analyze journalistic technique, not partisan alignment.

Your role:
1. Review deterministic bias scores for articles in a news cluster.
2. Identify cases where pattern-matching missed context (e.g., neutral use of \
politically-coded terms, a technical report that triggers sensationalism patterns \
due to statistical language, an academic framing mistaken for opinion).
3. Provide score adjustments (delta: integer from -20 to +20) per axis. Use 0 \
when the deterministic score is accurate — most scores need no adjustment.
4. Generate concise reasoning (one sentence) for each axis explaining whether \
the score is accepted or why it is being adjusted.
5. Assess cross-axis coherence in one sentence.

Constraints:
- You NEVER adjust scores based on the outlet's identity.
- Source names are anonymized as tier labels (US Source, International Source, \
Independent Source) — do not attempt to infer outlet identity.
- A delta of 0 is valid and expected for most axes. Only adjust when there is a \
clear, articulable reason the pattern-matching score is wrong.
- Adjustments must be proportionate: reserve large deltas (|delta| > 10) for \
clear, systematic miscalibration, not minor nuance.\
"""


# ---------------------------------------------------------------------------
# User prompt template — injected per cluster.
# {context_line} and {articles_block} are replaced at call time.
# ---------------------------------------------------------------------------
_PROMPT_TEMPLATE = """\
Review the following news cluster's deterministic bias scores and return a JSON \
object with two top-level fields: "articles" and "cluster_coherence".

{context_line}
ARTICLES WITH DETERMINISTIC SCORES:
{articles_block}

---

RESPONSE SCHEMA:
Return a JSON object with this exact structure:
{{
  "articles": [
    {{
      "index": 0,
      "adjustments": {{
        "political_lean": {{"delta": 0, "reasoning": "one sentence"}},
        "sensationalism": {{"delta": 0, "reasoning": "one sentence"}},
        "opinion_fact": {{"delta": 0, "reasoning": "one sentence"}},
        "factual_rigor": {{"delta": 0, "reasoning": "one sentence"}},
        "framing": {{"delta": 0, "reasoning": "one sentence"}}
      }},
      "confidence_boost": 0.0
    }}
  ],
  "cluster_coherence": "One sentence overall assessment of bias patterns across sources."
}}

Rules:
- "index" matches the article number in the list above (0-based).
- Each "delta" is an integer in [-20, 20]. Use 0 when the score is accurate.
- "reasoning" is one concise sentence per axis (required even when delta is 0).
- "confidence_boost" is a float in [-0.1, 0.1] — boost if text was richer than \
word count suggests, reduce if the article was thin despite length.
- "cluster_coherence" is exactly one sentence.
- Return JSON only. No markdown fences. No text outside the JSON object.\
"""


def blend_score(deterministic: float, delta: int, weight: float) -> int:
    """
    Apply a Gemini reasoning delta to a deterministic bias score.

    The final score is a weighted blend: the deterministic score shifts by
    (delta * weight). This keeps Gemini as a corrective signal rather than
    a replacement for the rule-based engine.

    Args:
        deterministic: The original rule-based score (0-100).
        delta: Gemini's proposed adjustment (-20 to +20).
        weight: Per-axis blend weight (0.0 to 1.0).

    Returns:
        Adjusted score clamped to [0, 100].
    """
    adjusted = deterministic + delta * weight
    return max(0, min(100, int(round(adjusted))))


def _reasoning_calls_remaining() -> int:
    """Return how many reasoning calls are left in this pipeline run."""
    return max(0, _MAX_REASONING_CALLS - _reasoning_call_count)


def _prioritize_clusters(
    clusters: list[dict],
    article_bias_map: dict[str, dict],
) -> list[tuple[int, float]]:
    """
    Sort clusters by reasoning priority, returning (original_index, priority_score) pairs.

    Priority formula (out of 100):
        (1 - avg_confidence) * 40     — low-confidence clusters benefit most
        + min(source_count / 10, 1) * 35  — larger clusters have more cross-article signal
        + min(lean_range / 60, 1) * 25    — high lean divergence = more correction value

    Only clusters with at least _MIN_ARTICLES articles are included.
    """
    scored: list[tuple[int, float]] = []

    for i, cluster in enumerate(clusters):
        articles = cluster.get("articles", [])
        if len(articles) < _MIN_ARTICLES:
            continue

        art_ids = [a.get("id", "") for a in articles]
        bias_entries = [article_bias_map.get(aid) for aid in art_ids if aid in article_bias_map]

        if not bias_entries:
            continue

        # Average confidence across articles in cluster
        confidences = [b.get("confidence", 0.5) for b in bias_entries if b]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

        # Source count (use explicit field, fall back to article count)
        source_count = cluster.get("source_count", len(articles))

        # Lean range across articles
        lean_scores = [b.get("political_lean", 50) for b in bias_entries if b]
        lean_range = (max(lean_scores) - min(lean_scores)) if len(lean_scores) >= 2 else 0.0

        priority = (
            (1.0 - avg_confidence) * 40.0
            + min(source_count / 10.0, 1.0) * 35.0
            + min(lean_range / 60.0, 1.0) * 25.0
        )
        scored.append((i, priority))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def _extract_rationale_signals(bias_entry: dict) -> dict[str, list[str]]:
    """
    Extract the top 2-3 rationale signals per axis from a bias scores entry.

    Rationale fields are stored as JSON strings or dicts in the bias_scores
    map. This function normalises them and pulls out the most informative
    signals for inclusion in the reasoning prompt.

    Returns a dict keyed by axis name with a list of human-readable signal strings.
    """
    import json

    signals: dict[str, list[str]] = {}
    raw_rationale = bias_entry.get("rationale")

    if raw_rationale is None:
        return signals

    # Rationale may be a JSON string (as stored in Supabase) or already a dict.
    if isinstance(raw_rationale, str):
        try:
            raw_rationale = json.loads(raw_rationale)
        except (json.JSONDecodeError, ValueError):
            return signals

    if not isinstance(raw_rationale, dict):
        return signals

    # Political lean signals
    lean_signals: list[str] = []
    top_left = raw_rationale.get("top_left_keywords", [])
    top_right = raw_rationale.get("top_right_keywords", [])
    if top_left:
        lean_signals.append(f"left keywords: {', '.join(top_left[:2])}")
    if top_right:
        lean_signals.append(f"right keywords: {', '.join(top_right[:2])}")
    framing_phrases = raw_rationale.get("framing_phrases_found", [])
    if framing_phrases:
        lean_signals.append(f"framing: {', '.join(framing_phrases[:2])}")
    if lean_signals:
        signals["political_lean"] = lean_signals[:3]

    # Sensationalism signals
    sens_signals: list[str] = []
    clickbait = raw_rationale.get("clickbait_signals", [])
    if clickbait:
        sens_signals.append(f"clickbait: {', '.join(str(c) for c in clickbait[:2])}")
    headline_score = raw_rationale.get("headline_score")
    if headline_score is not None:
        sens_signals.append(f"headline score: {headline_score}")
    urgency_density = raw_rationale.get("urgency_density")
    if urgency_density is not None:
        sens_signals.append(f"urgency density: {urgency_density}")
    if sens_signals:
        signals["sensationalism"] = sens_signals[:3]

    # Opinion/fact signals
    opinion_signals: list[str] = []
    dominant = raw_rationale.get("dominant_signals", [])
    if dominant:
        opinion_signals.append(f"dominant: {', '.join(dominant[:2])}")
    subjectivity = raw_rationale.get("subjectivity_score")
    if subjectivity is not None:
        opinion_signals.append(f"subjectivity: {subjectivity}")
    pronoun_density = raw_rationale.get("pronoun_density")
    if pronoun_density is not None:
        opinion_signals.append(f"pronoun density: {pronoun_density}")
    if opinion_signals:
        signals["opinion_fact"] = opinion_signals[:3]

    # Factual rigor signals
    rigor_signals: list[str] = []
    named_count = raw_rationale.get("named_sources_count")
    if named_count is not None:
        rigor_signals.append(f"named sources: {named_count}")
    data_count = raw_rationale.get("data_points_count")
    if data_count is not None:
        rigor_signals.append(f"data points: {data_count}")
    vague_count = raw_rationale.get("vague_sources_count")
    if vague_count is not None:
        rigor_signals.append(f"vague sources: {vague_count}")
    if rigor_signals:
        signals["factual_rigor"] = rigor_signals[:3]

    # Framing signals
    framing_signals: list[str] = []
    charged_synonyms = raw_rationale.get("charged_synonyms_found", [])
    if charged_synonyms:
        framing_signals.append(f"charged synonyms: {', '.join(str(s) for s in charged_synonyms[:2])}")
    passive_score = raw_rationale.get("passive_voice_score")
    if passive_score is not None:
        framing_signals.append(f"passive voice: {passive_score}")
    headline_divergence = raw_rationale.get("headline_body_divergence")
    if headline_divergence is not None:
        framing_signals.append(f"headline divergence: {headline_divergence}")
    if framing_signals:
        signals["framing"] = framing_signals[:3]

    return signals


def _build_context_line(articles: list[dict]) -> str:
    """
    Build a one-line cluster metadata header for the reasoning prompt.

    Mirrors cluster_summarizer._build_context_line() format so Gemini
    receives consistent context structure across both prompt types.
    """
    total = len(articles)
    tier_counts: dict[str, int] = {}
    for art in articles:
        tier = (art.get("tier", "") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    parts = []
    if tier_counts.get("us_major"):
        parts.append(f"{tier_counts['us_major']} US major")
    if tier_counts.get("international"):
        parts.append(f"{tier_counts['international']} international")
    if tier_counts.get("independent"):
        parts.append(f"{tier_counts['independent']} independent")

    distribution = ", ".join(parts) if parts else "mixed sources"
    return f"Cluster: {total} articles from {distribution} outlets.\n"


def _build_reasoning_prompt(
    articles: list[dict],
    article_bias_map: dict[str, dict],
) -> str:
    """
    Build the per-cluster reasoning prompt.

    Each article block includes:
    - Tier-anonymized source label (same anonymization as cluster_summarizer)
    - Title + summary (400 char cap, same as summarizer)
    - Deterministic scores for all 5 axes + confidence
    - Top 2-3 rationale signals per axis (from bias_scores rationale dict)

    Args:
        articles: List of article dicts with id, title, summary, tier keys.
        article_bias_map: Dict mapping article_id -> bias scores dict.

    Returns:
        Formatted prompt string ready for generate_json().
    """
    context_line = _build_context_line(articles)

    lines: list[str] = []
    for i, art in enumerate(articles[:_MAX_PROMPT_ARTICLES]):
        art_id = art.get("id", "")
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()
        if len(summary) > 400:
            summary = summary[:397] + "..."

        tier = (art.get("tier", "") or "").strip()
        source_label = _TIER_LABEL_MAP.get(tier, f"Source {i + 1}")

        bias = article_bias_map.get(art_id, {})
        lean = bias.get("political_lean", "N/A")
        sens = bias.get("sensationalism", "N/A")
        opinion = bias.get("opinion_fact", "N/A")
        rigor = bias.get("factual_rigor", "N/A")
        framing = bias.get("framing", "N/A")
        confidence = bias.get("confidence", "N/A")

        # Format scores line
        scores_line = (
            f"lean={lean} sens={sens} opinion={opinion} "
            f"rigor={rigor} framing={framing} conf={confidence}"
        )

        # Extract rationale signals
        rationale_signals = _extract_rationale_signals(bias)
        signal_parts: list[str] = []
        for axis in ("political_lean", "sensationalism", "opinion_fact", "factual_rigor", "framing"):
            sigs = rationale_signals.get(axis, [])
            if sigs:
                short_axis = {
                    "political_lean": "lean",
                    "sensationalism": "sens",
                    "opinion_fact": "opinion",
                    "factual_rigor": "rigor",
                    "framing": "framing",
                }[axis]
                signal_parts.append(f"{short_axis}: [{'; '.join(sigs)}]")

        lines.append(f"[{i}] {source_label}: {title}")
        if summary:
            lines.append(f"    {summary}")
        lines.append(f"    Scores: {scores_line}")
        if signal_parts:
            lines.append(f"    Signals: {' | '.join(signal_parts)}")
        lines.append("")

    articles_block = "\n".join(lines)

    return _PROMPT_TEMPLATE.format(
        context_line=context_line,
        articles_block=articles_block,
    )


def _validate_reasoning(result: dict, cluster_idx: int = 0) -> dict | None:
    """
    Validate the Gemini response shape and enforce delta clamps.

    Checks:
    - Top-level keys "articles" and "cluster_coherence" are present
    - Each article entry has "index" and "adjustments"
    - Each axis has "delta" (int, clamped to ±_MAX_DELTA) and "reasoning" (str)
    - confidence_boost is clamped to [-0.1, 0.1]

    Returns the validated + clamped result dict, or None if shape is invalid.
    """
    if not isinstance(result, dict):
        return None

    articles_raw = result.get("articles")
    coherence = result.get("cluster_coherence", "")

    if not isinstance(articles_raw, list):
        return None
    if not isinstance(coherence, str):
        coherence = ""

    _VALID_AXES = frozenset(_BLEND_WEIGHTS.keys())
    validated_articles: list[dict] = []

    for entry in articles_raw:
        if not isinstance(entry, dict):
            continue

        idx = entry.get("index")
        if not isinstance(idx, int):
            try:
                idx = int(idx)
            except (TypeError, ValueError):
                continue

        adjustments_raw = entry.get("adjustments", {})
        if not isinstance(adjustments_raw, dict):
            continue

        validated_adjustments: dict[str, dict] = {}
        for axis in _VALID_AXES:
            axis_data = adjustments_raw.get(axis)
            if not isinstance(axis_data, dict):
                # Tolerate missing axes — treat as delta=0
                validated_adjustments[axis] = {"delta": 0, "reasoning": ""}
                continue

            raw_delta = axis_data.get("delta", 0)
            try:
                delta = int(raw_delta)
            except (TypeError, ValueError):
                delta = 0
            # Hard clamp
            delta = max(-_MAX_DELTA, min(_MAX_DELTA, delta))

            # Cap reasoning at 300 chars to prevent memory bloat from verbose
            # or hallucinated responses. One concise sentence fits in ~150 chars.
            reasoning = str(axis_data.get("reasoning", "")).strip()[:300]

            validated_adjustments[axis] = {"delta": delta, "reasoning": reasoning}

        # Confidence boost
        raw_boost = entry.get("confidence_boost", 0.0)
        try:
            boost = float(raw_boost)
        except (TypeError, ValueError):
            boost = 0.0
        boost = max(-0.1, min(0.1, boost))

        validated_articles.append({
            "index": idx,
            "adjustments": validated_adjustments,
            "confidence_boost": boost,
        })

    if not validated_articles:
        return None

    return {
        "articles": validated_articles,
        "cluster_coherence": coherence.strip()[:500],
    }


def reason_cluster(
    articles: list[dict],
    article_bias_map: dict[str, dict],
    source_map: dict | None = None,
) -> dict | None:
    """
    Run Gemini reasoning on a single cluster.

    Builds the prompt, calls generate_json with count_call=False (uses the
    separate reasoning budget, not the summarization cap), validates the
    response, and returns the validated result.

    Args:
        articles: List of article dicts in the cluster.
        article_bias_map: Dict mapping article_id -> bias scores dict.
        source_map: Unused (reserved for future source context). Kept for
            API symmetry with reason_clusters_batch.

    Returns:
        Validated reasoning dict, or None on failure.
    """
    global _reasoning_call_count

    if not is_available():
        return None

    if len(articles) < _MIN_ARTICLES:
        return None

    if _reasoning_calls_remaining() <= 0:
        return None

    prompt = _build_reasoning_prompt(articles, article_bias_map)

    _reasoning_call_count += 1
    raw = generate_json(prompt, system_instruction=_SYSTEM_INSTRUCTION, count_call=False)

    if raw is None:
        return None

    return _validate_reasoning(raw)


def reason_clusters_batch(
    clusters: list[dict],
    article_bias_map: dict[str, dict],
    source_map: dict | None = None,
) -> dict[int, dict]:
    """
    Run Gemini reasoning on a batch of clusters, subject to budget cap.

    Clusters are prioritised by:
        (1 - avg_confidence) * 40
        + min(source_count / 10, 1) * 35
        + min(lean_range / 60, 1) * 25

    High-priority clusters (low confidence + large + divergent) are processed
    first. Processing stops when _MAX_REASONING_CALLS is reached.

    Args:
        clusters: List of cluster dicts, each with "articles" key.
        article_bias_map: Dict mapping article_id -> bias scores dict.
        source_map: Optional source metadata map (passed to reason_cluster).

    Returns:
        Dict mapping cluster index -> validated reasoning result.
        Missing indices = no reasoning available (rule-based scores unchanged).
    """
    if not is_available():
        return {}

    priority_list = _prioritize_clusters(clusters, article_bias_map)

    results: dict[int, dict] = {}
    processed = 0
    adjusted_articles = 0

    for cluster_idx, _priority in priority_list:
        if _reasoning_calls_remaining() <= 0:
            remaining_count = len(priority_list) - processed
            print(
                f"  [reasoning] Call cap reached after {processed} clusters "
                f"({remaining_count} remaining will use unmodified scores)"
            )
            break

        cluster = clusters[cluster_idx]
        articles = cluster.get("articles", [])

        result = reason_cluster(articles, article_bias_map, source_map)
        if result is None:
            continue

        results[cluster_idx] = result
        processed += 1

        # Count how many articles actually received non-zero adjustments
        for art_entry in result.get("articles", []):
            adjs = art_entry.get("adjustments", {})
            if any(a.get("delta", 0) != 0 for a in adjs.values()):
                adjusted_articles += 1

    skipped = len(priority_list) - processed
    print(
        f"  Gemini reasoning: {processed} clusters processed, "
        f"{adjusted_articles} articles adjusted "
        f"({skipped} clusters skipped — cap or below minimum)"
    )

    return results


def apply_reasoning_to_bias_map(
    clusters: list[dict],
    article_bias_map: dict[str, dict],
    reasoning_results: dict[int, dict],
) -> int:
    """
    Apply validated Gemini reasoning deltas to the in-memory article_bias_map.

    Mutates article_bias_map in place. Returns the count of individual axis
    values that were adjusted (delta != 0).

    This is a pure post-processing step — it does not make any API calls.
    Called after reason_clusters_batch() returns results.

    Args:
        clusters: List of cluster dicts with "articles" key.
        article_bias_map: The pipeline's in-memory bias scores dict (mutated).
        reasoning_results: Output of reason_clusters_batch().

    Returns:
        Total number of axis-score adjustments applied.
    """
    total_adjustments = 0

    for cluster_idx, reasoning in reasoning_results.items():
        cluster = clusters[cluster_idx]
        articles = cluster.get("articles", [])
        capped = articles[:_MAX_PROMPT_ARTICLES]

        for art_entry in reasoning.get("articles", []):
            prompt_idx = art_entry.get("index")
            if not isinstance(prompt_idx, int) or prompt_idx >= len(capped):
                continue

            art = capped[prompt_idx]
            art_id = art.get("id", "")
            if not art_id or art_id not in article_bias_map:
                continue

            bias = article_bias_map[art_id]
            adjs = art_entry.get("adjustments", {})

            # Political lean
            lean_adj = adjs.get("political_lean", {})
            lean_delta = lean_adj.get("delta", 0)
            if lean_delta != 0:
                orig = bias.get("political_lean", 50)
                bias["political_lean"] = blend_score(orig, lean_delta, _BLEND_WEIGHTS["political_lean"])
                total_adjustments += 1

            # Sensationalism
            sens_adj = adjs.get("sensationalism", {})
            sens_delta = sens_adj.get("delta", 0)
            if sens_delta != 0:
                orig = bias.get("sensationalism", 50)
                bias["sensationalism"] = blend_score(orig, sens_delta, _BLEND_WEIGHTS["sensationalism"])
                total_adjustments += 1

            # Opinion/fact
            opinion_adj = adjs.get("opinion_fact", {})
            opinion_delta = opinion_adj.get("delta", 0)
            if opinion_delta != 0:
                orig = bias.get("opinion_fact", 50)
                bias["opinion_fact"] = blend_score(orig, opinion_delta, _BLEND_WEIGHTS["opinion_fact"])
                total_adjustments += 1

            # Factual rigor
            rigor_adj = adjs.get("factual_rigor", {})
            rigor_delta = rigor_adj.get("delta", 0)
            if rigor_delta != 0:
                orig = bias.get("factual_rigor", 50)
                bias["factual_rigor"] = blend_score(orig, rigor_delta, _BLEND_WEIGHTS["factual_rigor"])
                total_adjustments += 1

            # Framing
            framing_adj = adjs.get("framing", {})
            framing_delta = framing_adj.get("delta", 0)
            if framing_delta != 0:
                orig = bias.get("framing", 50)
                bias["framing"] = blend_score(orig, framing_delta, _BLEND_WEIGHTS["framing"])
                total_adjustments += 1

            # Confidence boost
            boost = art_entry.get("confidence_boost", 0.0)
            if boost != 0.0:
                orig_conf = bias.get("confidence", 0.5)
                bias["confidence"] = max(0.0, min(1.0, orig_conf + boost))

    return total_adjustments


def get_reasoning_call_count() -> int:
    """Return the number of Gemini reasoning calls made this pipeline run."""
    return _reasoning_call_count
