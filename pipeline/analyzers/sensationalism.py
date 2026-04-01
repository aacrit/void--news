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
    # Pattern 0 catches sensational-modifier listicles ("10 shocking things") at 10.0.
    # The bare numeric-prefix pattern (^\d+\s+\w+) was removed because it fired on
    # legitimate hard-news headlines: "5 killed in Gaza strike", "14 senators voted
    # against the bill", "2024 election results finalized", "100 days since ceasefire".
    # Body counts, vote tallies, year-dates, and day-counts all matched and added 3 pts
    # unfairly to straight wire headlines. Real listicles are fully covered by Pattern 0.
    (re.compile(r"^\d+\s+(shocking|surprising|incredible|amazing|stunning|things|reasons|ways|facts|secrets)", re.I), 10.0),
    # "You won't believe" / imperative clickbait
    (re.compile(r"you won'?t believe", re.I), 10.0),
    (re.compile(r"what happens next", re.I), 9.0),
    (re.compile(r"here'?s (what|why|how)", re.I), 4.0),
    (re.compile(r"this is (why|what|how)", re.I), 4.0),
    (re.compile(r"everyone is talking about", re.I), 8.0),
    (re.compile(r"goes (wrong|viral|crazy)", re.I), 8.0),
    (re.compile(r"you need to (know|see|read|hear)", re.I), 7.0),
    # "what you need to know" / "what you should know"
    # Previous regex used "(need|should) to know" — "should to know" is ungrammatical
    # and unreachable in real text. Fixed to capture both grammatical constructions.
    (re.compile(r"what (you|we) (need to know|should know)", re.I), 5.0),
    # BREAKING / EXCLUSIVE / URGENT prefix patterns
    (re.compile(r"^(BREAKING|EXCLUSIVE|URGENT|ALERT)\s*[:\-\u2014]", re.I), 7.0),
    (re.compile(r"\.\.\.\s*$"), 5.0),
    # NOTE: bare \b[A-Z]{3,}\b removed — replaced by _caps_score() which
    # excludes COMMON_ACRONYMS (CIA, FBI, NATO, GOP, etc.) to avoid false
    # positives on institutional acronyms in wire-service headlines. (Priority 1)
]

# ---------------------------------------------------------------------------
# Superlatives and hyperbolic words
#
# NOTE: matching uses _SUPERLATIVE_PATTERN (compiled word-boundary regex,
# defined immediately after this list) rather than str.count(), to avoid
# substring false-positives: "total" firing on "totally", "complete" on
# "completely", "slam" on "slammed", "ultimate" on "ultimately".
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
    # NOTE: "historic" removed — used routinely in factual AP/Reuters contexts
    # ("historic vote", "historic agreement", "historic low"). Not tabloid language.
    # (Cycle 3 fix)
    "record-breaking", "all-time",
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
    # NOTE: "extremism" and "extremist" removed — these are factual law-enforcement
    # and policy category labels used neutrally across wire services (AP, Reuters,
    # DHS briefings). Not tabloid hyperbole. (bias-auditor fix)
    # NOTE: "radical" removed — as hyperbole it is rare in journalism; phrase-scoped
    # forms ("radical left", "radical agenda") already captured in political_lean.py
    # and PARTISAN_ATTACK_PHRASES. (bias-auditor fix)
    # NOTE: "socialist" removed — this is a government/party designation used in
    # factual political reporting worldwide ("socialist party", "socialist government",
    # "socialist candidate"). Phrase-scoped form ("socialist agenda", "socialist
    # takeover") already captured in PARTISAN_ATTACK_PHRASES. (bias-auditor fix)
    # NOTE: "takeover" removed — used neutrally in M&A/business reporting
    # ("hostile takeover", "corporate takeover"). Sensational compound forms
    # ("socialist takeover", "communist takeover") remain in PARTISAN_ATTACK_PHRASES.
    # (Cycle 3 fix)
    "catastrophe", "chaos", "destroying",
]

# Compiled word-boundary pattern for SUPERLATIVES.
# Using re.IGNORECASE so we can match against already-lowercased text (the flag
# is harmless there) and also against mixed-case headline text directly.
_SUPERLATIVE_PATTERN: re.Pattern = re.compile(
    r'\b(' + '|'.join(re.escape(s) for s in SUPERLATIVES) + r')\b',
    re.IGNORECASE,
)

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
    # Single-word urgency terms with no compound risk.
    #
    # REMOVED "just in" — it is a substring of "this just in" (listed above).
    # str.count() on a text containing "this just in" fires on BOTH entries,
    # inflating urgency_count by 1 for every occurrence of the compound phrase.
    # "just in:" as a standalone news prefix is the same journalistic construct
    # as "this just in" and is fully covered by the compound form.
    #
    # REMOVED "immediate" — str.count("immediate") fires on "immediately", which
    # is one of the most common adverbs in straight wire copy
    # ("officials responded immediately", "the law takes effect immediately").
    # A single body sentence with "immediately" registered as an urgency hit,
    # adding up to 8 pts to body_score on neutral AP/Reuters articles.
    # Genuine urgency framing ("requires immediate evacuation", "immediate danger")
    # is already captured by "emergency" and "urgent".
    "urgent", "exclusive", "alert", "flash",
    "emergency", "crisis", "right now",
]

# ---------------------------------------------------------------------------
# Hyperbolic modifiers
# ---------------------------------------------------------------------------
HYPERBOLIC_MODIFIERS: list[str] = [
    # NOTE: "devastating", "incredible", "terrifying", "unbelievable", "horrifying"
    # removed — these appear in SUPERLATIVES and counting them here too caused
    # double-counting in _body_score(). They remain in SUPERLATIVES only. (Cycle 3 fix)
    "massive",
    "staggering", "astonishing", "extraordinary", "phenomenal", "miraculous",
    "extremely", "absolutely", "totally", "completely", "utterly",
    "hugely", "enormously", "tremendously", "spectacularly",
    "dramatically", "drastically", "radically", "profoundly",
    "remarkably", "exceptionally", "ridiculously", "outrageously",
    "insanely", "wildly", "breathtakingly", "overwhelmingly",
    "horrifically", "frighteningly", "alarmingly", "disturbingly",
    "shockingly", "stunningly", "astoundingly", "unimaginably",
    # Additional hyperbolic modifiers (revive dead signal — 0.95% contribution)
    "jaw-dropping", "mind-blowing", "earth-shattering", "ground-breaking",
    "monumental", "colossal", "explosive", "seismic",
]

# Compiled word-boundary pattern for HYPERBOLIC_MODIFIERS.
# Using regex prevents substring false positives: "radically" in
# "radicalization", "massive" in "massively" (both forms are listed so
# this prevents double-count rather than missed detection).
_HYPERBOLIC_PATTERN: re.Pattern = re.compile(
    r'\b(' + '|'.join(re.escape(m) for m in HYPERBOLIC_MODIFIERS) + r')\b',
    re.IGNORECASE,
)

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

    Returns a raw density score (0-15) that _body_score() multiplies by 2.0
    and caps at 30.0 pts — the single largest potential contributor to
    body_score. This makes it the dominant signal for pure attack editorials.

    Fires on DENSITY of PARTISAN_ATTACK_PHRASES per 100 words, not mere
    presence. This ensures a single phrase in a long AP analysis article
    contributes negligibly, while a short attack-editorial paragraph dense
    with demonization language contributes meaningfully:

        1 phrase in 500-word AP article: density=0.2 → raw=1.6 → +3.2 pts
        3 phrases in 200-word editorial: density=1.5 → raw=12 → +24 pts
        Dense 60-word attack paragraph (10+ phrases): → raw capped at 15 → +30 pts

    Max contribution to body_score: 30 pts (via min(raw * 2.0, 30.0)).
    Each matching phrase contributes 8 pts raw (×2.0 = 16 pts per phrase),
    but the 30-pt ceiling prevents a single dense attack paragraph from
    consuming more than 30% of the body_score capacity on its own.
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
    # Each density unit contributes 8 pts; raw cap at 15 (×2.0 in _body_score = 30 pts max)
    return min(density * 8.0, 15.0)


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

    # Check superlatives in title using word-boundary regex to avoid substring
    # hits ("total" → "totally", "complete" → "completely", etc.).
    title_lower = title.lower()
    score += len(_SUPERLATIVE_PATTERN.findall(title_lower)) * 3.0

    # Urgency and hyperbolic modifiers in headlines.
    # Previously only checked in _body_score(), leaving headlines like
    # "We Must Ban Assault Weapons Now" (urgency: "now" is not in
    # URGENCY_WORDS, but "crisis" and "emergency" are) and "Big Oil's
    # Climate Genocide Is Killing Frontline Communities" scoring 0.
    # Adding these checks widens the sensationalism range for articles
    # with urgent/hyperbolic headlines that lack traditional clickbait
    # patterns.  Weight per-hit is lower than body (2.0 vs 8.0) because
    # a single urgency word in a headline is a weaker signal than
    # sustained urgency throughout body text.
    # (nlp-engineer — sensationalism distribution spread)
    for phrase in URGENCY_WORDS:
        if phrase in title_lower:
            score += 2.0
    score += len(_HYPERBOLIC_PATTERN.findall(title_lower)) * 2.0

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
    blob = TextBlob(text[:5000])  # limit for performance — sentiment signal saturates within first ~1000 words; 50000 was 10x too large
    # Very positive or very negative = more sensational
    polarity_extremity = abs(blob.sentiment.polarity)
    subjectivity = blob.sentiment.subjectivity
    score += polarity_extremity * 20.0  # up to 20 pts
    # Subjectivity multiplier increased from 15 to 20 to widen the dynamic
    # range.  Wire articles (subjectivity ~0.20-0.30) get +4-6 pts; opinion
    # pieces (subjectivity ~0.45-0.60) get +9-12 pts.  The 5-point increase
    # creates more separation between neutral reporting and subjective
    # editorial content, helping break the low-range clustering.
    # (nlp-engineer — sensationalism distribution spread)
    score += subjectivity * 20.0  # up to 20 pts (was 15.0)

    # --- Urgency language density ---
    urgency_count = 0
    for phrase in URGENCY_WORDS:
        urgency_count += text_lower.count(phrase)
    urgency_density = urgency_count / max(word_count / 100, 1)
    score += min(urgency_density * 8.0, 20.0)

    # --- Superlative density ---
    # Use word-boundary regex to avoid substring hits ("total" → "totally",
    # "complete" → "completely", "slam" → "slammed", "ultimate" → "ultimately").
    sup_count = len(_SUPERLATIVE_PATTERN.findall(text_lower))
    sup_density = sup_count / max(word_count / 100, 1)
    score += min(sup_density * 5.0, 20.0)

    # --- Hyperbolic modifier density ---
    # Use word-boundary regex (like SUPERLATIVES) to prevent substring false
    # positives and double-counting between base/adverb forms.
    hyp_count = len(_HYPERBOLIC_PATTERN.findall(text_lower))
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
    # The raw score (0-15) is multiplied by 2.0 and capped at 30 pts — the
    # single largest potential contributor to body_score. This yields:
    #   - 1 isolated phrase in 500-word AP article: density=0.2 → raw=1.6 → +3.2 pts
    #   - 3 phrases in 200-word editorial: density=1.5 → raw=12 → +24 pts
    #   - Dense 60-word attack paragraph (10+ phrases): raw capped at 15 → +30 pts
    # The measured_density inverse signal partially offsets low-density cases
    # where AP articles quote partisan language in a well-attributed context.
    # Cap reduced from 50 to 30 so a single attack paragraph cannot consume
    # more than 30% of body_score capacity on its own.
    partisan_raw = _partisan_attack_score(text_lower, word_count)
    score += min(partisan_raw * 2.0, 30.0)

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

    # If no text at all, return low default.
    # Score 5 (below the content floor of 8) to reflect that no-text articles carry
    # less signal than real-text articles, not more. Previously this returned 10,
    # which was paradoxically higher than the 8-floor for articles with actual content.
    if not title.strip() and not full_text.strip():
        return {
            "score": 5,
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

    # Apply a floor-stretch to spread the compressed low range wider.
    # Steeper low-end curve (2.0x for combined <= 25) pushes articles with
    # moderate signals (combined 4-8) above the floor of 8, creating more
    # separation between truly neutral wire copy and articles with mild
    # sensationalism signals.  The breakpoint at 25 (was 30) ensures that
    # the high-end mapping (50+ scores for tabloid content) remains stable.
    # (nlp-engineer — sensationalism distribution spread)
    if combined <= 25:
        stretched = combined * 2.0
    else:
        stretched = 50.0 + (combined - 25.0) * (50.0 / 75.0)

    # Minimum floor for articles with actual text content.
    # Heavy attribution-language in wire copy pushes body_score to 0 via the
    # measured_density inverse signal, which correctly reduces the body score
    # but can produce a combined=0 → stretched=0 → score=0 outcome.  A score
    # of 0 is unreachable by any real journalism — even the most neutral wire
    # story carries some baseline subjectivity.  Floor of 8 preserves the
    # intent (AP ≈ 10-20, tabloid ≈ 50-80) without clamping genuine low-end
    # reporting to zero. (Priority H2 fix — sensationalism floor for real text)
    has_content = bool(title.strip() or full_text.strip())
    floor = 3 if has_content else 0
    score = max(floor, min(100, int(round(stretched))))

    # Compute sub-signal rationale
    text_lower = (full_text or "").lower()
    words = text_lower.split()
    word_count = len(words)
    per_100 = max(word_count / 100, 1)

    clickbait_signals = sum(1 for p, _ in CLICKBAIT_PATTERNS if p.search(title))
    sup_count = len(_SUPERLATIVE_PATTERN.findall(text_lower))
    urg_count = sum(text_lower.count(p) for p in URGENCY_WORDS)
    hyp_count = len(_HYPERBOLIC_PATTERN.findall(text_lower))
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
