"""
Framing analyzer for the void --news bias engine.

Scores each article on a 0-100 framing spectrum:
    0   = neutral, balanced framing
    100 = heavily framed (emphasis/omission patterns detected)

Uses rule-based NLP heuristics (no LLM API calls):
    - Connotation analysis (TextBlob sentiment around key entities)
    - Keyword emphasis (charged synonyms vs neutral alternatives)
    - Omission detection (one-sided sourcing)
    - Headline vs body divergence
    - Active vs passive voice for agency (spaCy dependency parsing)
"""

import re

from textblob import TextBlob

from utils.nlp_shared import get_nlp

# Pre-compiled word-boundary patterns for SYNONYM_PAIRS single-word terms.
# Using simple str.count() on the raw text caused substring false positives:
# "killed" matched in "unskilled", "mob" in "mobilize", "riot" in "patriot",
# "slam" in "Islam", "radical" in "radicalization". Word-boundary regex fixes this.
# Multi-word phrases (e.g. "illegal alien") continue to use str.count() since
# they cannot appear as sub-strings of other words by construction.
_SYNONYM_PATTERNS: list[tuple[re.Pattern | None, str, str, int]] = []


# ---------------------------------------------------------------------------
# Charged vs neutral synonym pairs
# Format: (charged_form, neutral_form, charge_intensity 1-3)
# ---------------------------------------------------------------------------
SYNONYM_PAIRS: list[tuple[str, str, int]] = [
    # Conflict & violence
    # NOTE: intensity reduced 2→1. AP style mandates "killed" for violent death
    # (vs "died" for natural causes). Two occurrences in a 30-word conflict brief
    # previously scored kw_emphasis=60, at the weight-shift boundary. At intensity=1
    # the same article scores kw_emphasis=30 — a mild framing signal, not a trigger.
    # (analytics-expert audit 2026-03-21)
    ("killed", "died", 1),
    ("slaughtered", "killed", 3),
    ("massacre", "mass killing", 3),
    ("regime", "government", 3),
    ("dictator", "leader", 3),
    ("puppet", "ally", 3),
    ("thug", "suspect", 3),
    ("mob", "crowd", 1),  # reduced 2→1: compound forms ("democrat mob") in PARTISAN_ATTACK_PHRASES
    ("riot", "protest", 2),
    ("looting", "property damage", 2),
    # NOTE: intensity reduced 3→1. "Invasion" is the factually correct AP/Reuters/UN
    # term for Russia's Ukraine entry and other military incursions. Two uses in a
    # 100-word AP article previously scored kw_emphasis=90, triggering the geopolitical
    # weight shift and inflating framing scores for neutral conflict reporting. The
    # genuine state-media Kremlin euphemism is captured by "special military operation"
    # (intensity=3), making "invasion" at weight=1 a mild secondary signal only.
    # (analytics-expert audit 2026-03-21)
    ("invasion", "military operation", 1),
    ("occupation", "presence", 2),
    ("terrorist", "militant", 3),
    ("freedom fighter", "rebel", 3),
    # Immigration
    ("flood", "influx", 2),
    ("swarm", "large number", 3),
    ("illegal alien", "undocumented immigrant", 3),
    ("anchor baby", "child of immigrants", 3),
    ("migrant caravan", "group of migrants", 2),        # added: partisan vs neutral
    # Political
    ("slammed", "criticized", 2),
    ("blasted", "responded to", 2),
    # NOTE: "destroyed" reduced 3->2 — "hurricane destroyed homes", "flood destroyed
    # infrastructure" are common in AP/Reuters disaster coverage; weight=3 inflated
    # framing scores for neutral disaster reporting. Still captures political "A destroyed
    # B's argument" usage. (bias-auditor fix)
    ("destroyed", "countered", 2),
    ("eviscerated", "challenged", 3),
    ("ripped", "criticized", 2),
    ("torched", "denounced", 2),
    ("grilled", "questioned", 2),
    ("hammered", "pressed", 2),
    ("schooled", "corrected", 2),
    ("doubled down", "reiterated", 1),
    # Economic
    ("tax burden", "tax rate", 2),
    ("job killing", "affecting employment", 3),
    ("government handout", "government assistance", 3),
    ("entitlement", "benefit program", 2),
    ("big tech", "technology companies", 2),
    ("bailout", "financial assistance", 2),
    ("wealth grab", "tax policy", 3),
    ("death tax", "estate tax", 3),                    # added: charged vs neutral
    ("job creators", "wealthy", 2),                    # added: right economic framing
    # Social
    ("radical", "progressive", 1),  # reduced 2→1: compound forms ("radical left") in PARTISAN_ATTACK_PHRASES
    ("extremist", "activist", 3),
    ("woke", "socially conscious", 3),
    ("cancel culture", "public accountability", 3),
    ("indoctrination", "education", 3),
    ("propaganda", "messaging", 3),
    ("anarchist", "protester", 2),                     # added: civil unrest framing
    # Abortion
    ("baby killing", "abortion", 3),                   # added: charged vs neutral
    ("pro-abortion", "pro-choice", 2),                 # added: framing of opposing view
    ("unborn child", "fetus", 2),                      # added: moral loading
    # Media / information
    ("fake news", "misinformation", 2),                # added: partisan media attack term
    ("enemy of the people", "press criticism", 3),     # added: anti-press framing
    # Healthcare
    ("death panels", "end-of-life care", 3),           # added: ACA-era charged term
    ("socialized medicine", "universal healthcare", 2), # added: charged vs descriptive
    # Climate
    ("climate alarmism", "climate concern", 2),        # added: dismissive framing
    ("climate hoax", "climate skepticism", 3),         # added: denial framing
    # Race / equity
    ("reverse discrimination", "affirmative action", 2), # added: charged framing
    ("race hustler", "civil rights advocate", 3),      # added: dismissive vs neutral
    # Geopolitical / state-media framing pairs
    # These catch the actual charged language that state broadcasters (RT,
    # CGTN, Sputnik, Global Times, TRT World) deploy instead of Western L/R
    # ideological vocabulary.  Both the pro-state euphemism and the adversarial
    # charged form are listed as "charged" relative to neutral wire-service
    # alternatives because both signal geopolitical framing intent.
    ("special military operation", "invasion", 3),     # Kremlin euphemism for Ukraine war
    ("western aggression", "western policy", 3),       # state-media adversarial frame
    ("anti-russia hysteria", "criticism of russia", 3),
    ("russophobia", "anti-russia sentiment", 2),
    ("western hegemony", "western influence", 2),
    ("proxy war", "conflict", 2),                      # used by RT/Sputnik for Ukraine
    ("puppet regime", "government", 2),                # reduced 3→2: compound form in PARTISAN_ATTACK_PHRASES
    ("neo-nazis", "ukrainian forces", 3),              # Kremlin framing of Ukraine
    ("denazification", "military campaign", 3),        # Kremlin justification phrase
    ("bioweapons labs", "research facilities", 3),     # RT/Sputnik disinformation frame
    ("nato expansion", "nato enlargement", 2),         # charged vs neutral formulation
    ("collective west", "western countries", 1),       # reduced 2→1: compound forms in PARTISAN_ATTACK_PHRASES
    ("reunification", "annexation", 3),                # CCP framing of Taiwan/territories
    ("separatists", "independence movement", 2),       # state framing of dissent
    ("anti-china forces", "critics of china", 3),      # CGTN/Global Times frame
    ("splittists", "independence advocates", 3),       # CCP term for Tibet/Taiwan activists
    ("interference in internal affairs", "human rights concern", 3),
    ("century of humiliation", "historical grievance", 2),  # nationalist framing
    ("hostile forces", "opposition groups", 2),        # CCP/state media catch-all
    ("western smear", "western criticism", 3),         # CGTN dismissive framing
    ("genocide allegations", "human rights abuses", 2),    # state denial framing
]

# ---------------------------------------------------------------------------
# Build pre-compiled word-boundary patterns for SYNONYM_PAIRS.
# Single-word charged terms get a \b-bounded regex (prevents substring FPs).
# Multi-word phrases get pat=None (use str.count, which is safe for phrases).
# Populated at module load time — zero per-call overhead.
# ---------------------------------------------------------------------------
for _charged, _neutral, _intensity in SYNONYM_PAIRS:
    if " " not in _charged:
        _pat: re.Pattern | None = re.compile(
            r"\b" + re.escape(_charged) + r"\b", re.IGNORECASE
        )
    else:
        _pat = None
    _SYNONYM_PATTERNS.append((_pat, _charged, _neutral, _intensity))

# ---------------------------------------------------------------------------
# One-sided sourcing indicators
# ---------------------------------------------------------------------------
PRO_INDICATORS = re.compile(
    r"\b(supporters?|proponents?|advocates?|backers?|allies|defenders?)\s+(say|said|argue|argued|claim|believe)",
    re.IGNORECASE,
)

ANTI_INDICATORS = re.compile(
    r"\b(critics?|opponents?|detractors?|skeptics?|foes)\s+(say|said|argue|argued|claim|believe)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Evasive passive patterns
EVASIVE_PASSIVE: list[str] = [
    "mistakes were made", "errors were committed",
    "it was decided", "it was determined",
    "shots were fired", "damage was done",
    "lives were lost", "jobs were lost",
    "concerns were raised", "questions were raised",
    "steps were taken", "actions were taken",
    "measures were implemented",
    # Agency-erasing constructions common in political/diplomatic framing
    "it has been noted", "it was noted",
    "it was reported", "it has been reported",
    "it was announced", "it has been announced",
    "it is believed", "it was believed",
    "it is understood", "it was understood",
    "it is expected", "it was expected",
    "sanctions were imposed", "charges were filed",
    "arrests were made", "warnings were issued",
    "promises were broken", "commitments were made",
    "allegations were made", "claims were made",
    "reforms were introduced", "changes were made",
]


def _connotation_score(text: str, doc=None) -> float:
    """
    Measure sentiment polarity around key entities.
    High absolute polarity around entities = more framing.
    Returns 0-100.
    """
    if doc is None:
        nlp = get_nlp()
        doc = nlp(text[:15000])

    # Extract key entities (PERSON, ORG, GPE, NORP)
    key_labels = {"PERSON", "ORG", "GPE", "NORP", "EVENT"}
    entities = [ent for ent in doc.ents if ent.label_ in key_labels]

    if not entities:
        # No entities to frame — reduced from 5.0 to 2.0 to widen the gap
        # between entity-free articles and articles with neutral entity
        # sentiment (avg_abs_polarity ~0.05-0.10 → score 12-25).  At 2.0
        # the baseline gap is 10-23 pts, spreading the distribution further
        # and eliminating floor compression in the [5-19] band.
        # (bias-audit 2026-04-01 — framing distribution spread)
        return 2.0

    # Collect sentiment of sentences containing entities
    total_abs_polarity = 0.0
    entity_sentences = 0

    for sent in doc.sents:
        sent_ents = [e for e in entities if e.start >= sent.start and e.end <= sent.end]
        if sent_ents:
            blob = TextBlob(sent.text)
            total_abs_polarity += abs(blob.sentiment.polarity)
            entity_sentences += 1

    if entity_sentences == 0:
        return 2.0  # reduced from 5.0 (same rationale as no-entities case)

    avg_abs_polarity = total_abs_polarity / entity_sentences
    # avg_abs_polarity ranges 0-1; 0 = neutral, 0.5+ = heavily framed.
    # Multiplier increased from 200 to 250 to widen the dynamic range:
    # articles with moderate entity sentiment (0.10-0.20) now score 25-50
    # instead of 20-40, creating more separation from neutral articles.
    # (nlp-engineer — framing distribution spread)
    return min(100.0, avg_abs_polarity * 250.0)


def _keyword_emphasis_score(text: str) -> float:
    """
    Check for emotionally charged synonyms vs neutral alternatives.
    Returns 0-100.

    Uses word-boundary regex for single-word terms to prevent substring
    false positives: "killed" in "unskilled", "mob" in "mobilize",
    "riot" in "patriot", "slam" in "Islam", "radical" in "radicalization".
    Multi-word phrases use str.count() (cannot be substrings by construction).
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    charged_score = 0
    total_pairs_found = 0

    for pat, charged, neutral, intensity in _SYNONYM_PATTERNS:
        if pat is not None:
            # Single-word: use word-boundary regex to avoid substring matches
            charged_count = len(pat.findall(text_lower))
        else:
            # Multi-word phrase: substring search is safe
            charged_count = text_lower.count(charged)
        if charged_count > 0:
            charged_score += charged_count * intensity
            total_pairs_found += charged_count

    if total_pairs_found == 0:
        # Zero floor: articles with no charged synonyms should score 0 on
        # this sub-signal.  Previous floors (5.0, then 2.0) compressed
        # neutral articles into the same band as lightly-framed ones.
        # (bias-audit 2026-04-01 — framing distribution spread)
        return 0.0

    # Normalize by article length
    density = charged_score / max(word_count / 100, 1)
    return min(100.0, density * 15.0)


def _omission_score(
    text: str,
    cluster_articles: list[dict] | None = None,
    doc=None,
    cluster_entity_cache: set[str] | None = None,
) -> float:
    """
    Detect one-sided sourcing within the article.
    If cluster_articles provided, compare entity coverage.

    Performance optimization: accepts pre-computed spaCy doc and
    cluster_entity_cache to avoid redundant NLP processing during
    step 6b re-framing.

    Args:
        text: Article full text.
        cluster_articles: Other articles in the same cluster.
        doc: Pre-computed spaCy doc for this article (avoids re-parsing).
        cluster_entity_cache: Pre-computed set of entity strings from all
            cluster articles. When provided, skips parsing other articles.

    Returns 0-100.
    """
    text_lower = text.lower()

    pro_count = len(PRO_INDICATORS.findall(text_lower))
    anti_count = len(ANTI_INDICATORS.findall(text_lower))

    total_sided = pro_count + anti_count
    if total_sided == 0:
        # No explicit pro/anti sourcing detected
        base = 10.0
    elif pro_count == 0 or anti_count == 0:
        # Only one side represented
        base = min(100.0, total_sided * 15.0)
    else:
        # Both sides present; check balance
        ratio = min(pro_count, anti_count) / max(pro_count, anti_count)
        # ratio = 1.0 means balanced, 0 means completely one-sided
        base = (1.0 - ratio) * 60.0

    # Cross-article omission detection (if cluster provided)
    if cluster_articles and len(cluster_articles) >= 2:
        # Get entities from this article (reuse doc if provided)
        if doc is None:
            nlp = get_nlp()
            doc = nlp(text[:15000])
        this_entities = {ent.text.lower() for ent in doc.ents
                        if ent.label_ in ("PERSON", "ORG", "GPE")}

        # Use cached cluster entities if provided (avoids re-parsing all articles)
        cluster_entities = cluster_entity_cache
        if cluster_entities is None:
            nlp = get_nlp()
            cluster_entities = set()
            for other in cluster_articles[:10]:  # limit for performance
                other_text = other.get("full_text", "") or ""
                if other_text and other_text != text:
                    other_doc = nlp(other_text[:15000])
                    for ent in other_doc.ents:
                        if ent.label_ in ("PERSON", "ORG", "GPE"):
                            cluster_entities.add(ent.text.lower())

        if cluster_entities:
            # What fraction of cluster entities does this article mention?
            if this_entities:
                overlap = len(this_entities & cluster_entities) / len(cluster_entities)
                # Low overlap = potential omission
                omission_penalty = (1.0 - overlap) * 30.0
                base += omission_penalty

    return min(100.0, base)


def _headline_body_divergence(title: str, body: str) -> float:
    """
    Compare headline sentiment to body sentiment.
    Large divergence = framing.
    Returns 0-100.
    """
    if not title.strip() or not body.strip():
        return 0.0

    title_blob = TextBlob(title)
    body_blob = TextBlob(body[:10000])

    # Polarity divergence
    polarity_diff = abs(title_blob.sentiment.polarity - body_blob.sentiment.polarity)

    # Subjectivity divergence
    subj_diff = abs(title_blob.sentiment.subjectivity - body_blob.sentiment.subjectivity)

    # Combined divergence: both range 0-2, so combined max ~4.
    # Multiplier increased from 50 to 65 to make headline-body divergence
    # a stronger discriminator.  Headlines that editorialize beyond the
    # body content (e.g. "BREAKING: Crime Wave Hits Record" over a
    # measured AP story) now produce larger framing scores, widening the
    # gap between neutral and framed articles.
    # (nlp-engineer — framing distribution spread)
    divergence = polarity_diff + subj_diff
    return min(100.0, divergence * 65.0)


def _passive_voice_score(text: str, doc=None) -> float:
    """
    Check for evasive passive voice constructions.
    Returns 0-100.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    # Check for evasive passive patterns
    evasive_count = 0
    for phrase in EVASIVE_PASSIVE:
        evasive_count += text_lower.count(phrase)

    # General passive voice density using spaCy
    if doc is None:
        nlp = get_nlp()
        doc = nlp(text[:15000])

    passive_count = 0
    active_count = 0
    for token in doc:
        if token.dep_ == "nsubjpass":
            passive_count += 1
        elif token.dep_ == "nsubj":
            active_count += 1

    total_subj = passive_count + active_count
    if total_subj == 0:
        passive_ratio = 0.0
    else:
        passive_ratio = passive_count / total_subj

    # Evasive patterns are more heavily weighted
    evasive_score = min(evasive_count * 15.0, 40.0)

    # General passive ratio: > 0.3 is notable, > 0.5 is heavy.
    # Cap at 30 to prevent translated text (DW, NHK, Xinhua) and scientific
    # articles from over-scoring on idiomatic passive voice. Evasive-phrase
    # detection above carries full weight for genuinely evasive constructions.
    ratio_score = min(30.0, max(0.0, (passive_ratio - 0.2)) * 100.0)

    return min(100.0, evasive_score + ratio_score)


def analyze_framing(
    article: dict,
    cluster_articles: list[dict] | None = None,
    doc=None,
    cluster_entity_cache: set[str] | None = None,
) -> dict:
    """
    Score the framing bias of an article.

    Args:
        article: Dict with keys: full_text, title, summary.
        cluster_articles: Optional list of other articles in the same
            story cluster, used for omission detection.
        doc: Pre-computed spaCy doc for the article text (avoids re-parsing
            when called from step 6b re-framing).
        cluster_entity_cache: Pre-computed entity set from all cluster articles
            (avoids O(N*M) spaCy calls during step 6b).

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with sub-scores).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""

    if not full_text.strip() and not title.strip():
        return {
            "score": 15,
            "rationale": {
                "connotation_score": 0, "keyword_emphasis_score": 0,
                "omission_score": 0, "headline_body_divergence": 0,
                "passive_voice_score": 0, "has_cluster_context": False,
            },
        }

    # Parse once with spaCy and share the doc for NER/dep-based sub-scores
    if doc is None:
        nlp = get_nlp()
        doc = nlp(full_text[:15000])

    # Sub-scores
    connotation = _connotation_score(full_text, doc=doc)  # 0-100
    keyword_emp = _keyword_emphasis_score(full_text)       # 0-100
    omission = _omission_score(
        full_text, cluster_articles, doc=doc,
        cluster_entity_cache=cluster_entity_cache,
    )  # 0-100
    headline_div = _headline_body_divergence(title, full_text)  # 0-100
    passive = _passive_voice_score(full_text, doc=doc)     # 0-100

    # Weighted combination.
    # When geopolitical synonym pairs fire strongly (kw_emphasis > 60), the
    # standard 25% weight under-represents actual framing because TextBlob
    # returns near-zero polarity on declarative geopolitical assertions
    # ("historical inevitability", "firmly opposes") — reducing the connotation
    # sub-score that makes up the other 25%.  In these cases we shift 10 pts
    # of weight from connotation to kw_emphasis to reflect that keyword
    # detection is the more reliable signal for state-media geopolitical framing.
    #
    # Weight redistribution (nlp-engineer P1 fix): passive_voice contributes
    # <1% mean signal (92% of articles at zero). Shifted 5% from passive (0.15
    # -> 0.10) to keyword_emphasis (0.25->0.30 / 0.35->0.40) to widen the
    # dynamic range for articles with charged synonyms.
    #
    # Weight swap (nlp-engineer — framing distribution spread): headline_div
    # raised from 0.15 to 0.20, omission lowered from 0.20 to 0.15.
    # Headline-body divergence has the widest variation across articles (0-65)
    # while omission clusters at 10.0 (the default for no pro/anti sourcing).
    # Giving headline_div more weight spreads the distribution wider.
    # Weights still sum to 1.0.
    if keyword_emp > 60:
        w_connotation = 0.15
        w_keyword_emp = 0.40
    else:
        w_connotation = 0.25
        w_keyword_emp = 0.30

    weighted = (
        connotation * w_connotation
        + keyword_emp * w_keyword_emp
        + omission * 0.15
        + headline_div * 0.20
        + passive * 0.10
    )

    score = max(0, min(100, int(round(weighted))))

    return {
        "score": score,
        "rationale": {
            "connotation_score": round(connotation, 1),
            "keyword_emphasis_score": round(keyword_emp, 1),
            "omission_score": round(omission, 1),
            "headline_body_divergence": round(headline_div, 1),
            "passive_voice_score": round(passive, 1),
            "has_cluster_context": cluster_articles is not None and len(cluster_articles or []) >= 2,
        },
    }
