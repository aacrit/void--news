"""
Sensationalism detector for the void --news bias engine.

Scores each article on a 0-100 sensationalism spectrum:
    0   = measured, neutral tone
    100 = highly inflammatory, clickbait

Uses rule-based NLP heuristics (no LLM API calls):
    - Headline clickbait pattern detection
    - Superlative/hyperbolic word frequency
    - Emotional word density (TextBlob sentiment extremity)
    - Urgency language
    - Attribution gaps
    - Sentence structure analysis (short punchy sentences)
"""

import re
import string

from textblob import TextBlob

# ---------------------------------------------------------------------------
# Clickbait headline patterns
# ---------------------------------------------------------------------------
CLICKBAIT_PATTERNS: list[tuple[re.Pattern, float]] = [
    # Questions as headlines
    (re.compile(r"^(will|can|could|should|is|are|was|does|did|has|have)\b.+\?$", re.I), 8.0),
    (re.compile(r"\?$"), 5.0),
    # Listicles
    (re.compile(r"^\d+\s+(shocking|surprising|incredible|amazing|stunning|things|reasons|ways|facts|secrets)", re.I), 10.0),
    (re.compile(r"^\d+\s+\w+", re.I), 3.0),
    # "You won't believe" / imperative clickbait
    (re.compile(r"you won'?t believe", re.I), 10.0),
    (re.compile(r"what happens next", re.I), 9.0),
    (re.compile(r"here'?s (what|why|how)", re.I), 4.0),
    (re.compile(r"this is (why|what|how)", re.I), 4.0),
    (re.compile(r"everyone is talking about", re.I), 8.0),
    (re.compile(r"goes (wrong|viral|crazy)", re.I), 8.0),
    (re.compile(r"you need to (know|see|read|hear)", re.I), 7.0),
    (re.compile(r"what (you|we) (need|should) to know", re.I), 5.0),
    # BREAKING / EXCLUSIVE / URGENT prefix patterns
    (re.compile(r"^(BREAKING|EXCLUSIVE|URGENT|ALERT)\s*[:\-\u2014]", re.I), 7.0),
    (re.compile(r"\.\.\.\s*$"), 5.0),
    # All-caps words (2+ uppercase words in a row)
    (re.compile(r"\b[A-Z]{3,}\b"), 3.0),
]

# ---------------------------------------------------------------------------
# Superlatives and hyperbolic words
# ---------------------------------------------------------------------------
SUPERLATIVES: list[str] = [
    "worst", "best", "unprecedented", "shocking", "explosive",
    "stunning", "bombshell", "jaw-dropping", "mind-blowing", "unbelievable",
    "incredible", "outrageous", "horrifying", "terrifying", "devastating",
    "catastrophic", "disastrous", "nightmarish", "apocalyptic",
    "game-changing", "groundbreaking", "earth-shattering", "world-shaking",
    "epic", "legendary", "monumental", "colossal", "mammoth", "enormous",
    "insane", "crazy", "wild", "brutal", "savage", "vicious",
    "slam", "slammed", "slams", "destroyed", "obliterated", "annihilated",
    "eviscerated", "demolished", "crushed", "torched", "blasted",
    "absolute", "total", "complete", "utter", "sheer",
    "historic", "record-breaking", "all-time",
]

# ---------------------------------------------------------------------------
# Urgency language
# ---------------------------------------------------------------------------
URGENCY_WORDS: list[str] = [
    "breaking", "just in", "developing", "urgent", "exclusive",
    "live updates", "happening now", "alert", "flash",
    "breaking news", "this just in", "developing story",
    "emergency", "crisis", "immediate", "right now",
]

# ---------------------------------------------------------------------------
# Hyperbolic modifiers
# ---------------------------------------------------------------------------
HYPERBOLIC_MODIFIERS: list[str] = [
    "massive", "devastating", "incredible", "terrifying", "unbelievable",
    "staggering", "astonishing", "extraordinary", "phenomenal", "miraculous",
    "extremely", "absolutely", "totally", "completely", "utterly",
    "hugely", "enormously", "tremendously", "spectacularly",
    "dramatically", "drastically", "radically", "profoundly",
    "remarkably", "exceptionally", "ridiculously", "outrageously",
    "insanely", "wildly", "breathtakingly", "overwhelmingly",
    "horrifically", "frighteningly", "alarmingly", "disturbingly",
    "shockingly", "stunningly", "astoundingly", "unimaginably",
]

# ---------------------------------------------------------------------------
# Measured / professional indicators (inverse signals)
# ---------------------------------------------------------------------------
MEASURED_PHRASES: list[str] = [
    "according to", "officials said", "the report found",
    "data shows", "the study", "researchers found",
    "analysis suggests", "evidence indicates", "peer-reviewed",
    "the department said", "in a statement", "the spokesperson said",
    "on condition of anonymity", "declined to comment",
    "could not be independently verified", "it remains unclear",
]


def _headline_score(title: str) -> float:
    """Score headline sensationalism from 0-100."""
    if not title or not title.strip():
        return 0.0

    score = 0.0

    # Clickbait patterns
    for pattern, weight in CLICKBAIT_PATTERNS:
        if pattern.search(title):
            score += weight

    # Exclamation marks
    excl_count = title.count("!")
    score += min(excl_count * 5.0, 15.0)

    # Multiple punctuation (!! or ?! or ??)
    multi_punct = len(re.findall(r"[!?]{2,}", title))
    score += multi_punct * 5.0

    # All-caps words count
    words = title.split()
    if len(words) > 0:
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
        caps_ratio = caps_words / len(words)
        score += caps_ratio * 20.0

    # Check superlatives in title
    title_lower = title.lower()
    for word in SUPERLATIVES:
        if word in title_lower:
            score += 3.0

    # Very short headlines (< 5 words) can be sensational
    if 0 < len(words) < 5:
        score += 3.0

    # TextBlob sentiment extremity on headline
    blob = TextBlob(title)
    sentiment_extremity = abs(blob.sentiment.polarity)
    score += sentiment_extremity * 10.0

    return min(100.0, score)


def _body_score(text: str) -> float:
    """Score body text sensationalism from 0-100."""
    if not text or not text.strip():
        return 0.0

    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)
    if word_count == 0:
        return 0.0

    score = 0.0

    # --- Emotional word density (TextBlob) ---
    blob = TextBlob(text[:50000])  # limit for performance
    # Very positive or very negative = more sensational
    polarity_extremity = abs(blob.sentiment.polarity)
    subjectivity = blob.sentiment.subjectivity
    score += polarity_extremity * 15.0  # up to 15 pts
    score += subjectivity * 10.0  # up to 10 pts

    # --- Urgency language density ---
    urgency_count = 0
    for phrase in URGENCY_WORDS:
        urgency_count += text_lower.count(phrase)
    urgency_density = urgency_count / max(word_count / 100, 1)
    score += min(urgency_density * 5.0, 15.0)

    # --- Superlative density ---
    sup_count = 0
    for word in SUPERLATIVES:
        sup_count += text_lower.count(word)
    sup_density = sup_count / max(word_count / 100, 1)
    score += min(sup_density * 3.0, 15.0)

    # --- Hyperbolic modifier density ---
    hyp_count = 0
    for mod in HYPERBOLIC_MODIFIERS:
        hyp_count += text_lower.count(mod)
    hyp_density = hyp_count / max(word_count / 100, 1)
    score += min(hyp_density * 3.0, 10.0)

    # --- Exclamation mark density ---
    excl_count = text.count("!")
    excl_per_100 = excl_count / max(word_count / 100, 1)
    score += min(excl_per_100 * 3.0, 10.0)

    # --- Short punchy sentence ratio ---
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        short_count = sum(1 for s in sentences if len(s.split()) <= 6)
        short_ratio = short_count / len(sentences)
        # More than 40% short sentences is sensational-leaning
        if short_ratio > 0.4:
            score += (short_ratio - 0.4) * 30.0

    # --- Attribution gaps (inverse: measured articles have more attribution) ---
    measured_count = 0
    for phrase in MEASURED_PHRASES:
        measured_count += text_lower.count(phrase)
    measured_density = measured_count / max(word_count / 100, 1)
    # High attribution = less sensational, apply negative weight
    score -= min(measured_density * 3.0, 15.0)

    return max(0.0, min(100.0, score))


def analyze_sensationalism(article: dict) -> dict:
    """
    Score the sensationalism level of an article.

    Args:
        article: Dict with keys: full_text, title, summary.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with sub-scores).
    """
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""

    # If no text at all, return low default
    if not title.strip() and not full_text.strip():
        return {
            "score": 10,
            "rationale": {
                "headline_score": 0, "body_score": 0,
                "clickbait_signals": 0, "superlative_density": 0,
                "urgency_density": 0, "hyperbole_density": 0,
                "measured_density": 0,
            },
        }

    h_score = _headline_score(title)
    b_score = _body_score(full_text)

    # Weighted combination: 40% headline, 60% body
    combined = 0.4 * h_score + 0.6 * b_score
    score = max(0, min(100, int(round(combined))))

    # Compute sub-signal rationale
    text_lower = (full_text or "").lower()
    words = text_lower.split()
    word_count = len(words)
    per_100 = max(word_count / 100, 1)

    clickbait_signals = sum(1 for p, _ in CLICKBAIT_PATTERNS if p.search(title))
    sup_count = sum(text_lower.count(w) for w in SUPERLATIVES)
    urg_count = sum(text_lower.count(p) for p in URGENCY_WORDS)
    hyp_count = sum(text_lower.count(m) for m in HYPERBOLIC_MODIFIERS)
    meas_count = sum(text_lower.count(p) for p in MEASURED_PHRASES)

    return {
        "score": score,
        "rationale": {
            "headline_score": round(h_score, 1),
            "body_score": round(b_score, 1),
            "clickbait_signals": clickbait_signals,
            "superlative_density": round(sup_count / per_100, 2),
            "urgency_density": round(urg_count / per_100, 2),
            "hyperbole_density": round(hyp_count / per_100, 2),
            "measured_density": round(meas_count / per_100, 2),
        },
    }
