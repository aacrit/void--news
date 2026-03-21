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
# Common institutional acronyms — excluded from ALL-CAPS sensationalism check.
# These are proper nouns, not clickbait; treating them as hyperbole inflates
# scores on wire-service and policy articles. (Priority 1 fix)
# ---------------------------------------------------------------------------
COMMON_ACRONYMS: frozenset[str] = frozenset({
    # US government / agencies
    "CIA", "FBI", "NSA", "DHS", "DOJ", "DOD", "DOE", "HHS", "EPA",
    "IRS", "SEC", "FTC", "FEC", "FCC", "FEMA", "CDC", "FDA", "NIH",
    "NASA", "USDA", "OMB", "CBO", "GAO", "ICE", "DEA", "ATF",
    # Legislative / judicial
    "GOP", "DNC", "RNC", "SCOTUS",
    # International bodies
    "UN", "EU", "NATO", "WHO", "IMF", "WTO", "IAEA", "OPEC",
    # News / wire services
    "AP", "AFP", "UPI", "PBS", "NPR", "BBC", "CNN", "ABC", "CBS", "NBC",
    # Economic / finance
    "GDP", "CPI", "IMF", "FED",
    # Misc institutional
    "UK", "US", "UAE", "NGO", "CEO", "CFO", "COO", "CTO",
})

# ---------------------------------------------------------------------------
# Clickbait headline patterns
# ---------------------------------------------------------------------------
CLICKBAIT_PATTERNS: list[tuple[re.Pattern, float]] = [
    # Questions as headlines.
    # Pattern 0: interrogative-led question (e.g. "Will Trump win?") — strongest
    # clickbait signal because the question IS the whole content structure.
    (re.compile(r"^(will|can|could|should|is|are|was|does|did|has|have)\b.+\?$", re.I), 8.0),
    # Pattern 1: any other question ending (e.g. "Trump wins — or does he?").
    # Weight reduced 5.0 → 2.0: a bare terminal ? on a non-interrogative headline
    # is a much weaker signal than a full question headline.  Previously, a
    # headline matching pattern 0 also always matched pattern 1, creating an
    # undifferentiated 13-point cliff vs a 5-point plain-question score.
    # With 8+2=10 vs 2, the gap is narrower and proportional.
    (re.compile(r"\?$"), 2.0),
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
    # NOTE: bare \b[A-Z]{3,}\b removed — replaced by _caps_score() which
    # excludes COMMON_ACRONYMS (CIA, FBI, NATO, GOP, etc.) to avoid false
    # positives on institutional acronyms in wire-service headlines. (Priority 1)
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
    # Partisan / ideological charged language not previously captured.
    # These appear routinely in attack-style editorial and opinion pieces
    # but are absent from measured wire reporting. Added to lift sensationalism
    # scores for Fox/Breitbart opinion pieces that use charged framing but
    # avoid traditional clickbait patterns. (bias-auditor Wave-3 fix)
    #
    # Excluded from this list (regression analysis 2026-03-20):
    #   "crisis"    — already in URGENCY_WORDS; also appears neutrally in
    #                 "crisis-level fire danger", "housing crisis", DHS briefings
    #   "dangerous" — extremely common in neutral disaster/safety reporting
    #                 ("dangerous conditions", "dangerous levels", "dangerous driving")
    #   "flooding"  — standard meteorological term in disaster/weather coverage
    #   "invasion"  — too common in geo-political/military neutral reporting
    #   "rampage"   — narrow use case, captured by "massacre"/"riot" already
    #
    # Words below only appear in genuinely inflammatory editorial framing,
    # not in standard wire/policy/disaster reporting:
    "catastrophe", "chaos", "extremism", "extremist",
    "takeover", "radical", "socialist", "destroying",
]

# ---------------------------------------------------------------------------
# Urgency language
#
# NOTE: compound phrases are listed in LONGEST-FIRST order so that a phrase
# like "breaking news" is counted once as a unit rather than twice via its
# constituent "breaking" + "breaking news".  The bare single-word forms
# "breaking" and "developing" were removed because they triggered double-
# counting with their compound forms ("breaking news", "developing story")
# and because the single words produce false positives in body text
# ("breaking records", "developing countries").  The compound forms are
# the true urgency signal. (Priority C2 fix — urgency double-count)
# ---------------------------------------------------------------------------
URGENCY_WORDS: list[str] = [
    # Compound phrases first (most specific — prevent substring double-count)
    "breaking news", "this just in", "developing story", "live updates",
    "happening now",
    # Single-word urgency terms with no compound risk
    "just in", "urgent", "exclusive", "alert", "flash",
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
# Partisan attack / demonization language
#
# These are concentrated ideological attack phrases that appear in editorial
# content aimed at demonizing the opposing side rather than describing policy.
# Distinct from LEFT_KEYWORDS/RIGHT_KEYWORDS in political_lean.py (which score
# *direction*) — these score *inflammatory intensity* regardless of which side.
#
# Design constraints for regression safety:
#   - Phrase-level matching only (no bare single words like "radical" or
#     "socialist" that appear in neutral reporting contexts such as
#     "radical surgery", "socialist party of X country").
#   - Scored by DENSITY per 100 words: one isolated phrase in a 500-word
#     AP analysis piece contributes 0.2/100 = negligible.  A 40-word
#     attack paragraph with 4 phrases contributes 10/100 = meaningful.
#   - Capped so even a pure attack paragraph contributes at most 25 pts
#     to body_score before the weighted 15% blend.
# ---------------------------------------------------------------------------
PARTISAN_ATTACK_PHRASES: list[str] = [
    # Attack + demonization framing — right-wing editorial registers
    # (phrases specific enough that they cannot appear in neutral wire reporting)
    "radical left", "the radical left",
    "destroying america", "destroy america",
    "dangerous agenda", "radical agenda", "socialist agenda",
    "socialist takeover", "communist takeover", "radical takeover",
    "open border agenda", "open borders agenda",
    "before it's too late", "before its too late",
    "wake up america", "save america", "take back america",
    "the end of america", "end of our freedom",
    # Demonization patterns: paired accusation structures
    "refuses to enforce the law", "refuses to protect our",
    "radical democrats", "democrat mob", "democrat agenda",
    "liberal mob", "leftist mob", "woke mob",
    "illegal aliens flooding", "flooding our communities",
    # Alarmist / end-times framing (only specific compound forms)
    "threat to our way of life", "america is dying",
    "america is under attack", "freedom is under attack",
    "our children will inherit", "our children are being",
    # Cross-ideological: left-wing attack equivalents
    # (comparably specific — cannot appear in neutral science/economics reporting)
    "fascist agenda", "white supremacist agenda",
    "billionaire takeover", "oligarch takeover",
    "genocide agenda", "climate genocide",
    "fascist takeover", "nazi agenda",
    "destroy our democracy", "destroying our democracy",
    "corporate coup", "billionaire coup",
    # State-media propaganda phrases (RT, CGTN, Sputnik, Global Times, TRT World)
    # These are inflammatory in the geopolitical register the same way "radical
    # left" is in the Western register: concentrated demonization language that
    # goes well beyond neutral wire-service description of the same events.
    # Phrase-level only — cannot appear in neutral reporting by construction.
    "denazification of ukraine", "puppet regime in kiev", "puppet regime in kyiv",
    "collective west's proxy war", "nato's proxy war", "western proxy war",
    "collective west refuses", "collective west continues",
    "anti-china forces in", "hostile forces in", "separatist forces",
    "century of humiliation", "historical inevitability of",
    "western aggression against", "nato aggression",
    "hegemonism and power politics", "cold war mentality",
    "interference in china's internal affairs", "interference in russia's",
    "the so-called", "so-called human rights",
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


def _partisan_attack_score(text_lower: str, word_count: int) -> float:
    """
    Score concentrated partisan attack / demonization language.

    Returns 0-25 contribution to body_score.

    Fires on DENSITY of PARTISAN_ATTACK_PHRASES per 100 words, not mere
    presence. This ensures a single phrase in a long AP analysis article
    contributes < 1 pt, while a short attack-editorial paragraph dense with
    demonization language contributes up to 25 pts.

    The 15% weight in _body_score() then caps the actual contribution to
    ~3.75 pts at max, but more practically delivers the ~8-12 pt body_score
    lift needed to push calm-but-ideological content from ~29 to 40+.
    """
    if word_count == 0:
        return 0.0

    hit_count = 0
    for phrase in PARTISAN_ATTACK_PHRASES:
        hit_count += text_lower.count(phrase)

    if hit_count == 0:
        return 0.0

    # Density: hits per 100 words
    density = hit_count / max(word_count / 100, 1)
    # Each density unit contributes 8 pts; cap at 25
    return min(density * 8.0, 25.0)


def _caps_score(title: str, words: list[str]) -> float:
    """
    Score ALL-CAPS word usage in a headline, excluding COMMON_ACRONYMS.

    Standard institutional acronyms (CIA, FBI, NATO, GOP, UN, GDP, PBS, etc.)
    are common in straight news and should not signal sensationalism. Only
    non-acronym all-caps words (e.g. "SHOCKING", "EXPOSED", "DESTROYED")
    indicate hyperbolic editorial tone. (Priority 1 fix)

    Returns 0-20 contribution to the headline score.
    """
    if not words:
        return 0.0
    # Count caps words that are NOT in the common-acronym whitelist
    caps_words = sum(
        1 for w in words
        if w.isupper() and len(w) > 2 and w.strip(".,!?;:'\"()") not in COMMON_ACRONYMS
    )
    caps_ratio = caps_words / len(words)
    return caps_ratio * 20.0


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

    # All-caps words (excluding institutional acronyms — Priority 1 fix)
    words = title.split()
    score += _caps_score(title, words)

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
    score += polarity_extremity * 20.0  # up to 20 pts
    score += subjectivity * 15.0  # up to 15 pts

    # --- Urgency language density ---
    urgency_count = 0
    for phrase in URGENCY_WORDS:
        urgency_count += text_lower.count(phrase)
    urgency_density = urgency_count / max(word_count / 100, 1)
    score += min(urgency_density * 8.0, 20.0)

    # --- Superlative density ---
    sup_count = 0
    for word in SUPERLATIVES:
        sup_count += text_lower.count(word)
    sup_density = sup_count / max(word_count / 100, 1)
    score += min(sup_density * 5.0, 20.0)

    # --- Hyperbolic modifier density ---
    hyp_count = 0
    for mod in HYPERBOLIC_MODIFIERS:
        hyp_count += text_lower.count(mod)
    hyp_density = hyp_count / max(word_count / 100, 1)
    score += min(hyp_density * 5.0, 15.0)

    # --- Exclamation mark density ---
    excl_count = text.count("!")
    excl_per_100 = excl_count / max(word_count / 100, 1)
    score += min(excl_per_100 * 5.0, 15.0)

    # --- Short punchy sentence ratio ---
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        short_count = sum(1 for s in sentences if len(s.split()) <= 6)
        short_ratio = short_count / len(sentences)
        # More than 30% short sentences is sensational-leaning
        if short_ratio > 0.3:
            score += (short_ratio - 0.3) * 40.0

    # --- Partisan attack / demonization density ---
    # Detects concentrated ideological attack language (e.g. "radical left's
    # dangerous agenda", "socialist takeover", "before it's too late") that
    # signals inflammatory editorial tone even when traditional clickbait
    # patterns (ALL-CAPS, urgency words, exclamation marks) are absent.
    #
    # The raw score (0-25) is added directly to the body_score at a 2x
    # multiplier, capping at 50 pts contribution. This yields:
    #   - 1 isolated phrase in 500-word AP article: density=0.2 → raw=1.6 → +3.2 pts
    #   - 3 phrases in 200-word editorial: density=1.5 → raw=12 → +24 pts
    #   - Dense 60-word attack paragraph (10+ phrases): density=16+ → raw=25 → +50 pts
    # The measured_density inverse signal partially offsets low-density cases
    # where AP articles quote partisan language in a well-attributed context.
    partisan_raw = _partisan_attack_score(text_lower, word_count)
    score += min(partisan_raw * 2.0, 50.0)

    # --- Attribution gaps (inverse: measured articles have more attribution) ---
    measured_count = 0
    for phrase in MEASURED_PHRASES:
        measured_count += text_lower.count(phrase)
    measured_density = measured_count / max(word_count / 100, 1)
    # High attribution = less sensational, apply negative weight
    score -= min(measured_density * 4.0, 20.0)

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

    # Weighted combination: 50% headline, 50% body
    # Headline is the strongest discriminator between wire copy and tabloid
    combined = 0.5 * h_score + 0.5 * b_score

    # Apply a mild floor-stretch to spread the compressed 4-7 range wider.
    # Stretch the 0-30 raw range into 0-50 and preserve 30-100 into 50-100.
    # This makes AP wire copy score ~10-20 and tabloid headlines score 50-80.
    if combined <= 30:
        stretched = combined * (50.0 / 30.0)
    else:
        stretched = 50.0 + (combined - 30.0) * (50.0 / 70.0)

    # Minimum floor for articles with actual text content.
    # Heavy attribution-language in wire copy pushes body_score to 0 via the
    # measured_density inverse signal, which correctly reduces the body score
    # but can produce a combined=0 → stretched=0 → score=0 outcome.  A score
    # of 0 is unreachable by any real journalism — even the most neutral wire
    # story carries some baseline subjectivity.  Floor of 8 preserves the
    # intent (AP ≈ 10-20, tabloid ≈ 50-80) without clamping genuine low-end
    # reporting to zero. (Priority H2 fix — sensationalism floor for real text)
    has_content = bool(title.strip() or full_text.strip())
    floor = 8 if has_content else 0
    score = max(floor, min(100, int(round(stretched))))

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
    partisan_attack_count = sum(text_lower.count(p) for p in PARTISAN_ATTACK_PHRASES)

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
            "partisan_attack_density": round(partisan_attack_count / per_100, 2),
        },
    }
