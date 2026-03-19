"""
Political lean analyzer for the void --news bias engine.

Scores each article on a 0-100 political lean spectrum:
    0   = strong left
    50  = center
    100 = strong right

Uses rule-based NLP heuristics (no LLM API calls):
    - Partisan keyword lexicons (50+ terms per side)
    - Source baseline blending (0.85 * text + 0.15 * baseline)
    - Entity sentiment via spaCy NER + TextBlob
    - Framing phrase detection
"""

import re
from collections import Counter

from textblob import TextBlob

from utils.nlp_shared import get_nlp


# ---------------------------------------------------------------------------
# Partisan keyword lexicons  (weight = relevance strength 1-3)
# ---------------------------------------------------------------------------
LEFT_KEYWORDS: dict[str, int] = {
    # Social issues
    "progressive": 2, "systemic racism": 3, "systemic oppression": 3,
    "wealth inequality": 3, "income inequality": 3, "reproductive rights": 3,
    "gun control": 3, "climate crisis": 3, "climate emergency": 3,
    "social justice": 3, "marginalized": 2, "undocumented": 2,
    "healthcare access": 2, "universal healthcare": 3, "single payer": 3,
    "living wage": 2, "affordable housing": 2, "racial justice": 3,
    "police reform": 2, "defund the police": 3, "mass incarceration": 3,
    "prison reform": 2, "gender equity": 2, "pay gap": 2,
    "intersectionality": 3, "white privilege": 3, "toxic masculinity": 3,
    "institutional racism": 3, "environmental justice": 2,
    "corporate greed": 3, "billionaire class": 3, "worker exploitation": 3,
    "labor rights": 2, "union busting": 3, "occupy": 2,
    "democratic socialism": 3, "medicare for all": 3,
    "green new deal": 3, "ban assault weapons": 3,
    "disinformation": 1, "voter suppression": 3, "gerrymandering": 2,
    "dark money": 2, "citizens united": 2, "right-wing extremism": 3,
    "authoritarianism": 2, "fascism": 2, "neo-nazi": 3,
    "inclusivity": 1, "diversity": 1, "equity": 1,
    "hate speech": 2, "microaggression": 3, "decolonize": 3,
    "non-binary": 2, "gender-affirming": 3, "trans rights": 3,
    "reparations": 3, "abolish ice": 3, "sanctuary city": 2,
    "community organizing": 2, "grassroots": 1, "solidarity": 1,
}

RIGHT_KEYWORDS: dict[str, int] = {
    # Social issues
    "traditional values": 2, "illegal alien": 3, "illegal immigrant": 2,
    "free market": 2, "second amendment": 3, "pro-life": 3,
    "law and order": 2, "border security": 3, "big government": 3,
    "taxpayer": 1, "patriot": 2, "patriotic": 1,
    "religious liberty": 3, "religious freedom": 2,
    "right to bear arms": 3, "gun rights": 3, "personal responsibility": 2,
    "limited government": 3, "deregulation": 2, "tax cuts": 2,
    "trickle down": 2, "job creators": 3, "small business": 1,
    "national security": 1, "strong military": 2,
    "radical left": 3, "socialist agenda": 3, "socialism": 2,
    "woke": 3, "cancel culture": 3, "virtue signaling": 3,
    "politically correct": 2, "political correctness": 2,
    "deep state": 3, "mainstream media": 2, "liberal bias": 3,
    "traditional family": 3, "family values": 2,
    "school choice": 2, "parental rights": 2,
    "blue lives matter": 3, "back the blue": 3, "thin blue line": 3,
    "stand your ground": 2, "constitutional carry": 3,
    "secure the border": 3, "build the wall": 3, "illegal invasion": 3,
    "election integrity": 2, "voter fraud": 3,
    "states rights": 2, "originalist": 2, "strict constructionist": 2,
    "unborn": 3, "sanctity of life": 3, "abortion on demand": 3,
    "energy independence": 2, "war on coal": 3,
    "radical agenda": 3, "liberal elite": 3, "coastal elite": 3,
    "real americans": 3, "god-fearing": 2, "american exceptionalism": 2,
    "marxist": 3, "communist": 2, "antifa": 3,
}

# ---------------------------------------------------------------------------
# Framing phrases  (shift_direction: negative = left shift, positive = right)
# ---------------------------------------------------------------------------
FRAMING_PHRASES: list[tuple[str, float]] = [
    # Left-leaning framing
    ("advocates argue", -0.3), ("critics of the administration", -0.3),
    # Right-leaning framing
    ("critics say", 0.3), ("some argue", 0.1), ("many believe", 0.1),
    ("radical", 0.5), ("far-left", 0.8), ("extremist left", 0.8),
    ("so-called experts", 0.6), ("government overreach", 0.5),
    ("mainstream media", 0.5), ("liberal media", 0.8),
    # Left-associated framing of the right
    ("far-right", -0.5), ("extremist", -0.3), ("white nationalist", -0.5),
    ("hard-line conservative", -0.3), ("ultra-conservative", -0.3),
]

# ---------------------------------------------------------------------------
# Politically coded entities (used for entity-sentiment scoring)
# ---------------------------------------------------------------------------
LEFT_CODED_ENTITIES = {
    "democrat", "democrats", "democratic party", "dnc", "aclu",
    "planned parenthood", "naacp", "sierra club", "greenpeace",
    "progressive caucus", "labor union", "afl-cio",
}

RIGHT_CODED_ENTITIES = {
    "republican", "republicans", "gop", "rnc", "nra",
    "heritage foundation", "federalist society", "fox news",
    "conservative caucus", "freedom caucus", "tea party",
    "turning point usa", "breitbart",
}

# ---------------------------------------------------------------------------
# Source baseline mapping
# ---------------------------------------------------------------------------
BASELINE_MAP: dict[str, int] = {
    "far-left": 10, "left": 20, "center-left": 35,
    "center": 50,
    "center-right": 65, "right": 80, "far-right": 90,
    "varies": 50,
}


def _keyword_score(text: str) -> tuple[float, list[str], list[str]]:
    """Compute keyword-based lean score from 0-100. 50 = neutral.
    Returns (score, top_left_keywords, top_right_keywords)."""
    text_lower = text.lower()
    left_total = 0
    right_total = 0
    left_hits: dict[str, float] = {}
    right_hits: dict[str, float] = {}

    for phrase, weight in LEFT_KEYWORDS.items():
        if " " not in phrase:
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
        else:
            count = text_lower.count(phrase)
        if count > 0:
            left_total += count * weight
            left_hits[phrase] = count * weight

    for phrase, weight in RIGHT_KEYWORDS.items():
        if " " not in phrase:
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
        else:
            count = text_lower.count(phrase)
        if count > 0:
            right_total += count * weight
            right_hits[phrase] = count * weight

    # Normalize by article length (per 500 words)
    word_count = max(len(text_lower.split()) / 500, 1)
    left_total = left_total / word_count
    right_total = right_total / word_count

    # Top keywords by impact
    top_left = sorted(left_hits, key=left_hits.get, reverse=True)[:5]
    top_right = sorted(right_hits, key=right_hits.get, reverse=True)[:5]

    total = left_total + right_total
    if total == 0:
        return 50.0, top_left, top_right

    if total < 4:
        right_ratio = right_total / total
        return 50.0 + (right_ratio - 0.5) * (total / 4.0) * 100.0, top_left, top_right

    right_ratio = right_total / total
    return right_ratio * 100.0, top_left, top_right


def _framing_score(text: str) -> tuple[float, list[str]]:
    """Detect framing phrases and return (lean_shift, phrases_found)."""
    text_lower = text.lower()
    shift = 0.0
    count = 0
    phrases_found: list[str] = []

    for phrase, direction in FRAMING_PHRASES:
        occurrences = text_lower.count(phrase)
        if occurrences > 0:
            shift += direction * occurrences
            count += occurrences
            phrases_found.append(phrase)

    if count == 0:
        return 0.0, phrases_found

    return max(-15.0, min(15.0, shift * 3.0)), phrases_found


def _entity_sentiment_score(text: str) -> tuple[float, dict[str, float]]:
    """
    Use spaCy NER + TextBlob to gauge sentiment toward politically coded entities.
    Returns (lean_shift, entity_sentiments_dict).
    """
    nlp = get_nlp()
    doc = nlp(text[:15000])

    left_sentiment = 0.0
    right_sentiment = 0.0
    left_count = 0
    right_count = 0
    entity_sentiments: dict[str, list[float]] = {}

    for sent in doc.sents:
        sent_lower = sent.text.lower()
        blob = None

        for ent_name in LEFT_CODED_ENTITIES:
            if ent_name in sent_lower:
                if blob is None:
                    blob = TextBlob(sent.text)
                left_sentiment += blob.sentiment.polarity
                left_count += 1
                entity_sentiments.setdefault(ent_name, []).append(blob.sentiment.polarity)

        for ent_name in RIGHT_CODED_ENTITIES:
            if ent_name in sent_lower:
                if blob is None:
                    blob = TextBlob(sent.text)
                right_sentiment += blob.sentiment.polarity
                right_count += 1
                entity_sentiments.setdefault(ent_name, []).append(blob.sentiment.polarity)

    shift = 0.0
    if left_count > 0:
        avg_left = left_sentiment / left_count
        shift -= avg_left * 10
    if right_count > 0:
        avg_right = right_sentiment / right_count
        shift += avg_right * 10

    # Average sentiments per entity for rationale
    avg_sentiments = {
        k: round(sum(v) / len(v), 2) for k, v in entity_sentiments.items()
    }

    return max(-15.0, min(15.0, shift)), avg_sentiments


def _get_source_baseline(source: dict) -> int:
    """Extract numeric baseline from source dict."""
    baseline_str = source.get("political_lean_baseline", "center")
    if isinstance(baseline_str, (int, float)):
        return int(baseline_str)
    return BASELINE_MAP.get(str(baseline_str).lower().strip(), 50)


def analyze_political_lean(article: dict, source: dict) -> dict:
    """
    Score the political lean of an article.

    Args:
        article: Dict with keys: full_text, title, summary, source_id.
        source: Dict with keys: political_lean_baseline, tier, name.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with evidence).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    combined = f"{title} {full_text}"
    source_baseline = _get_source_baseline(source)

    if not combined.strip():
        return {
            "score": source_baseline,
            "rationale": {"keyword_score": 50, "framing_shift": 0, "entity_shift": 0,
                          "source_baseline": source_baseline, "top_left_keywords": [],
                          "top_right_keywords": [], "framing_phrases_found": [],
                          "entity_sentiments": {}},
        }

    # 1. Keyword-based score (0-100) + top keywords
    kw_score, top_left, top_right = _keyword_score(combined)

    # 2. Framing shift (-15 to +15) + phrases found
    framing_shift, framing_phrases = _framing_score(combined)

    # 3. Entity sentiment shift (-15 to +15) + sentiments
    entity_shift, entity_sentiments = _entity_sentiment_score(combined)

    # Combine text-based score
    text_score = kw_score + framing_shift + entity_shift
    text_score = max(0.0, min(100.0, text_score))

    # 4. Blend with source baseline (0.85 text + 0.15 baseline)
    final_score = 0.85 * text_score + 0.15 * source_baseline
    score = max(0, min(100, int(round(final_score))))

    return {
        "score": score,
        "rationale": {
            "keyword_score": round(kw_score, 1),
            "framing_shift": round(framing_shift, 1),
            "entity_shift": round(entity_shift, 1),
            "source_baseline": source_baseline,
            "top_left_keywords": top_left,
            "top_right_keywords": top_right,
            "framing_phrases_found": framing_phrases,
            "entity_sentiments": entity_sentiments,
        },
    }
