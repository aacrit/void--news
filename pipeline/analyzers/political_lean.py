"""
Political lean analyzer for the void --news bias engine.

Scores each article on a 0-100 political lean spectrum:
    0   = strong left
    50  = center
    100 = strong right

Uses rule-based NLP heuristics (no LLM API calls):
    - Partisan keyword lexicons (90+ terms per side)
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
    # Social justice / identity
    "progressive": 2, "systemic racism": 3, "systemic oppression": 3,
    "social justice": 3, "marginalized": 2, "racial justice": 3,
    "intersectionality": 3, "white privilege": 3, "toxic masculinity": 3,
    "institutional racism": 3, "structural racism": 3,
    "inclusivity": 1, "diversity": 1, "equity": 1,
    "hate speech": 2, "microaggression": 3, "decolonize": 3,
    "non-binary": 2, "gender-affirming": 3, "trans rights": 3,
    "reparations": 3, "dei": 2, "anti-racist": 3,
    "privilege": 1, "allyship": 2, "centering voices": 3,
    "lived experience": 2, "cultural appropriation": 3,
    "reproductive rights": 3, "bodily autonomy": 2, "reproductive justice": 3,
    "book bans": 2, "drag ban": 3,
    # Economic
    "wealth inequality": 3, "income inequality": 3,
    "living wage": 2, "affordable housing": 2,
    "corporate greed": 3, "billionaire class": 3, "billionaire tax": 3,
    "worker exploitation": 3, "labor rights": 2, "union busting": 3,
    "occupy": 2, "democratic socialism": 3,
    "wealth gap": 2, "universal basic income": 3, "price gouging": 2,
    "wage theft": 3, "corporate accountability": 2, "profit motive": 2,
    "late capitalism": 3, "wealth redistribution": 3, "tax the rich": 3,
    "predatory lending": 2, "housing crisis": 1,
    # Environment / climate
    "climate crisis": 3, "climate emergency": 3, "environmental justice": 2,
    "green new deal": 3, "fossil fuel": 1, "climate justice": 3,
    "carbon neutral": 1, "renewable energy": 1, "clean energy": 1,
    "climate catastrophe": 3, "environmental racism": 3,
    "frontline communities": 2, "just transition": 3,
    "big oil": 3, "carbon footprint": 1, "net zero": 1,
    # Healthcare
    "healthcare access": 2, "universal healthcare": 3, "single payer": 3,
    "medicare for all": 3, "public option": 2, "healthcare is a right": 3,
    "insulin prices": 1, "big pharma": 2, "drug pricing": 1,
    # Gun control
    "gun control": 3, "ban assault weapons": 3,
    "gun violence epidemic": 3, "common sense gun laws": 2,
    "gun safety": 1, "weapons of war": 3,
    # Immigration
    "undocumented": 2, "sanctuary city": 2, "abolish ice": 3,
    "pathway to citizenship": 3, "daca": 2, "asylum seekers": 1,
    "immigrant rights": 2, "dreamers": 2, "family separation": 2,
    "undocumented workers": 2, "migrant rights": 2,
    # Governance / democracy
    "voter suppression": 3, "gerrymandering": 2,
    "dark money": 2, "citizens united": 2, "right-wing extremism": 3,
    "authoritarianism": 2, "fascism": 2, "neo-nazi": 3,
    "disinformation": 1, "protect democracy": 2, "threat to democracy": 2,
    "authoritarian": 2, "autocratic": 2, "democratic backsliding": 3,
    "voting rights": 1, "project 2025": 3, "anti-woke": 2,
    # Police / criminal justice
    "police reform": 2, "defund the police": 3, "mass incarceration": 3,
    "prison reform": 2, "police brutality": 3, "police accountability": 2,
    "restorative justice": 2, "prison abolition": 3,
    "school to prison pipeline": 3, "carceral state": 3,
    # Gender / pay
    "gender equity": 2, "pay gap": 2, "gender pay gap": 2,
    "glass ceiling": 2, "equal pay": 1,
    # Tech / media
    "misinformation": 1, "content moderation": 1, "algorithmic bias": 2,
    "big tech accountability": 2, "digital rights": 1,
    # Community
    "community organizing": 2, "grassroots": 1, "solidarity": 1,
    "mutual aid": 2, "collective action": 2, "people power": 2,
    # Additional high-value terms (Priority 3b fix — closing lexicon gap)
    "critical race theory": 3,     # appears in left rebuttal framing
    "student debt forgiveness": 2,
    "student loan relief": 2,
    "gentrification": 2,
    "housing justice": 2,
    "food insecurity": 2,
}

RIGHT_KEYWORDS: dict[str, int] = {
    # Immigration
    "illegal alien": 3, "illegal immigrant": 2, "illegal aliens": 3,
    "border security": 3, "secure the border": 3, "build the wall": 3,
    "illegal invasion": 3, "border crisis": 3, "mass deportation": 3,
    "open borders": 3, "migrant crime": 3, "criminal aliens": 3,
    "chain migration": 3, "anchor baby": 3, "catch and release": 2,
    # Economic
    "free market": 2, "tax cuts": 2, "trickle down": 2,
    "job creators": 3, "small business": 1, "deregulation": 2,
    "energy independence": 2, "war on coal": 3,
    "fiscal responsibility": 2, "welfare state": 3, "entitlements": 2,
    "government spending": 1, "balanced budget": 1,
    "government overreach": 3, "nanny state": 3, "tax burden": 2,
    "free enterprise": 2, "economic freedom": 1,
    "esg agenda": 3, "esg": 2, "woke capitalism": 3,
    # Social / culture
    "traditional values": 2, "traditional family": 3, "family values": 2,
    "religious liberty": 3, "religious freedom": 2,
    "parental rights": 2, "school choice": 2,
    "woke": 3, "cancel culture": 3, "virtue signaling": 3,
    "politically correct": 2, "political correctness": 2,
    "woke ideology": 3, "woke agenda": 3, "woke mob": 3,
    "grooming": 3, "indoctrination": 3, "gender ideology": 3,
    "radical gender": 3, "biological sex": 2, "born male": 2, "born female": 2,
    "protect children": 1, "parental consent": 1,
    "god-fearing": 2, "american exceptionalism": 2,
    "judeo-christian": 2, "faith and freedom": 2,
    "personal responsibility": 2,
    # Governance
    "big government": 3, "limited government": 3, "deep state": 3,
    "states rights": 2, "originalist": 2, "strict constructionist": 2,
    "constitutional originalism": 3, "judicial activism": 2,
    "tenth amendment": 2, "federal overreach": 3,
    "weaponization": 3, "two-tier justice": 3, "lawfare": 3,
    "politicized justice": 3, "weaponized government": 3,
    "administrative state": 2, "bureaucratic overreach": 3,
    # Elections
    "election integrity": 2, "voter fraud": 3,
    "rigged election": 3, "ballot harvesting": 3,
    "stolen election": 3, "election fraud": 3,
    # Gun rights
    "second amendment": 3, "right to bear arms": 3, "gun rights": 3,
    "stand your ground": 2, "constitutional carry": 3,
    "shall not be infringed": 3, "responsible gun owners": 1,
    # Law and order
    "law and order": 2, "tough on crime": 2,
    "blue lives matter": 3, "back the blue": 3, "thin blue line": 3,
    "soft on crime": 3, "pro-criminal": 3,
    "defund" : 1,  # opposing context — right uses "defund" as attack term
    # Pro-life
    "pro-life": 3, "unborn": 3, "sanctity of life": 3,
    "abortion on demand": 3, "heartbeat bill": 3, "protect the unborn": 3,
    "right to life": 2, "abortion industry": 3,
    # Military / defense
    "national security": 1, "strong military": 2,
    "peace through strength": 2, "military readiness": 1,
    "china threat": 2, "woke military": 3,
    # Anti-left labels
    "radical left": 3, "socialist agenda": 3, "socialism": 2,
    "radical agenda": 3, "liberal elite": 3, "coastal elite": 3,
    "real americans": 3, "marxist": 3, "communist": 2, "antifa": 3,
    "liberal bias": 3, "mainstream media": 2,
    "far-left agenda": 3, "radical democrat": 3, "leftist": 2,
    "progressive agenda": 2, "culture war": 1,
    # Patriotism
    "taxpayer": 1, "patriot": 2, "patriotic": 1,
    # Additional high-value terms (Priority 3b fix — closing lexicon gap)
    # NOTE: bare "globalists" intentionally excluded — phrase-scoped only to
    # avoid false positives in international finance/trade coverage.
    "globalist agenda": 3,
    "globalist elite": 3,
    "transgenderism": 2,
    "medical freedom": 2,
    "parental rights": 2,
    "america first": 2,
}

# ---------------------------------------------------------------------------
# Framing phrases  (shift_direction: negative = left shift, positive = right)
# ---------------------------------------------------------------------------
FRAMING_PHRASES: list[tuple[str, float]] = [
    # Left-leaning framing (negative shift = toward left)
    # Weights raised on strongest ideological markers to match right-side
    # phrase weights (e.g. "far-left" = 0.8, "liberal media" = 0.8).
    # Rebalanced per bias-auditor Priority 3a fix.
    ("advocates argue", -0.3), ("critics of the administration", -0.3),
    ("reproductive freedom", -0.8),   # raised from -0.5 (Priority 3a)
    ("voting access", -0.3),
    ("gun violence prevention", -0.4), ("common sense reform", -0.3),
    ("communities of color", -0.3), ("people of color", -0.2),
    ("working families", -0.3), ("corporate interests", -0.4),
    ("the most vulnerable", -0.3), ("safety net", -0.2),
    ("access to healthcare", -0.3), ("climate science", -0.2),
    ("experts warn", -0.2), ("studies show", -0.1),
    ("assault-style weapon", -0.8),   # raised from -0.5 (Priority 3a)
    ("weapons of war", -0.5),
    ("crisis at the border", -0.1),  # neutral-ish but used left
    ("undocumented immigrant", -0.3),
    ("threat to democracy", -0.8),   # raised from -0.5 (Priority 3a)
    ("democratic norms", -0.3),
    ("power grab", -0.7),             # raised from -0.3 (Priority 3a)
    ("erosion of rights", -0.7),      # raised from -0.3 (Priority 3a)
    # New left framing phrases — added to match right-side phrase count (Priority 3c)
    ("corporate capture", -0.5),
    ("voter intimidation", -0.5),
    ("book banning", -0.5),
    ("forced birth", -0.7),
    # Right-leaning framing (positive shift = toward right)
    ("critics say", 0.3), ("some argue", 0.1), ("many believe", 0.1),
    ("radical", 0.5), ("far-left", 0.8), ("extremist left", 0.8),
    ("so-called experts", 0.6), ("government overreach", 0.5),
    ("mainstream media", 0.5), ("liberal media", 0.8),
    ("taxpayer-funded", 0.4), ("government handout", 0.5),
    ("job-killing regulation", 0.6), ("burdensome regulation", 0.4),
    ("religious persecution", 0.5), ("war on faith", 0.7),
    ("illegal border crossing", 0.4), ("border invasion", 0.7),
    ("hard-working americans", 0.2), ("forgotten americans", 0.4),
    ("the radical left wants", 0.7), ("democrat-run", 0.5),
    ("failed policies", 0.3), ("activist judge", 0.6),
    ("weaponized doj", 0.8), ("two-tiered justice system", 0.7),
    ("witch hunt", 0.7), ("political persecution", 0.5),
    ("woke agenda", 0.7), ("gender ideology", 0.6),
    ("parental rights in education", 0.4),
    # Left-associated framing of the right (negative shift)
    ("far-right", -0.5), ("extremist", -0.3), ("white nationalist", -0.5),
    ("hard-line conservative", -0.3), ("ultra-conservative", -0.3),
    ("maga extremism", -0.7), ("maga republican", -0.5),
    ("christian nationalist", -0.5), ("right-wing conspiracy", -0.5),
    ("election denier", -0.5), ("insurrectionist", -0.7),
    ("climate denier", -0.5), ("science denier", -0.4),
    ("authoritarian playbook", -0.6), ("strongman politics", -0.4),
]

# ---------------------------------------------------------------------------
# Politically coded entities (used for entity-sentiment scoring)
# ---------------------------------------------------------------------------
LEFT_CODED_ENTITIES = {
    "democrat", "democrats", "democratic party", "dnc", "aclu",
    "planned parenthood", "naacp", "sierra club", "greenpeace",
    "progressive caucus", "labor union", "afl-cio",
    "moveon", "indivisible", "everytown", "moms demand action",
    "human rights campaign", "emily's list", "splc",
    "southern poverty law center", "center for american progress",
    "black lives matter", "blm", "sunrise movement",
    "working families party", "justice democrats",
    "league of conservation voters", "earthjustice",
}

RIGHT_CODED_ENTITIES = {
    "republican", "republicans", "gop", "rnc", "nra",
    "heritage foundation", "federalist society", "fox news",
    "conservative caucus", "freedom caucus", "tea party",
    "turning point usa", "breitbart",
    "heritage action", "cato institute", "americans for prosperity",
    "daily wire", "judicial watch", "project veritas",
    "moms for liberty", "prager university", "prageru",
    "american conservative union", "cpac", "liberty counsel",
    "family research council", "alliance defending freedom",
    "america first", "maga", "epoch times",
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
