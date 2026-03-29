"""
Political lean analyzer for the void --news bias engine.

Scores each article on a 0-100 political lean spectrum:
    0   = strong left
    50  = center
    100 = strong right

Uses rule-based NLP heuristics (no LLM API calls):
    - Partisan keyword lexicons (90+ terms per side)
    - Length-adaptive baseline blending (0.50/0.50 short → 0.90/0.10 long)
    - Entity sentiment via spaCy NER + TextBlob
    - Framing phrase detection
"""

import math
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
    # NOTE: "inclusivity": 1, "diversity": 1, "equity": 1 removed — these fire on
    # neutral financial/corporate reporting ("equity markets", "private equity",
    # "board diversity", "home equity"). Signal captured by higher-specificity terms:
    # "dei" (weight 2), "structural racism" (weight 3), "intersectionality" (weight 3).
    # (Cycle 3 fix)
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
    "predatory lending": 2,
    # NOTE: "housing crisis": 1 removed — neutral policy/reporting term used across
    # the full spectrum (Reuters, Bloomberg, AP housing beat). (bias-auditor fix)
    # Environment / climate
    "climate crisis": 3, "climate emergency": 3, "environmental justice": 2,
    "green new deal": 3, "climate justice": 3,
    "climate catastrophe": 3, "environmental racism": 3,
    "frontline communities": 2, "just transition": 3,
    "big oil": 3,
    # NOTE: Removed from LEFT_KEYWORDS (all weight=1) — energy industry terms used
    # neutrally across the full political spectrum including WSJ, Bloomberg, Fox Business:
    #   "fossil fuel", "carbon neutral", "net zero", "carbon footprint",
    #   "renewable energy", "clean energy"
    # These terms in AP/Reuters energy/climate reporting caused false left-scoring
    # of 20-30 pts below center. Genuine left-coded climate terms remain at weight 3
    # (climate crisis, climate emergency, green new deal, climate justice, etc.).
    # (bias-auditor fix)
    # Healthcare
    "healthcare access": 2, "universal healthcare": 3, "single payer": 3,
    "medicare for all": 3, "public option": 2, "healthcare is a right": 3,
    "insulin prices": 1, "big pharma": 2,
    # NOTE: "drug pricing": 1 removed — neutral policy/reporting term used across
    # the full spectrum (Bloomberg, Reuters, healthcare beat). (bias-auditor fix)
    # Gun control
    "gun control": 3, "ban assault weapons": 3,
    "gun violence epidemic": 3, "common sense gun laws": 2,
    # NOTE: "gun safety": 1 removed — neutral policy/reporting term used across
    # the spectrum. "gun violence epidemic" and "common sense gun laws" capture
    # the genuinely left-coded framing. (bias-auditor fix)
    "weapons of war": 3,
    # Immigration
    "undocumented": 2, "sanctuary city": 2, "abolish ice": 3,
    "pathway to citizenship": 3, "daca": 2,
    # NOTE: "asylum seekers": 1 removed — neutral immigration/legal reporting term
    # used across the full spectrum (AP, Reuters, BBC). (bias-auditor fix)
    "immigrant rights": 2, "dreamers": 2, "family separation": 2,
    "undocumented workers": 2, "migrant rights": 2,
    # Governance / democracy
    "voter suppression": 3, "gerrymandering": 2,
    "dark money": 2, "citizens united": 2, "right-wing extremism": 3,
    "authoritarianism": 2, "fascism": 2, "neo-nazi": 3,
    # NOTE: "disinformation": 1 removed — same rationale as "misinformation":
    # neutral tech/policy term used by AP, Reuters, government agencies, and
    # academics without partisan intent. (bias-auditor fix)
    "protect democracy": 2, "threat to democracy": 2,
    "authoritarian": 2, "autocratic": 2, "democratic backsliding": 3,
    "voting rights": 1, "project 2025": 3, "anti-woke": 2,
    # Police / criminal justice
    "police reform": 2, "defund the police": 3, "mass incarceration": 3,
    "prison reform": 2, "police brutality": 3, "police accountability": 2,
    "restorative justice": 2, "prison abolition": 3,
    "school to prison pipeline": 3, "carceral state": 3,
    # Gender / pay
    "gender equity": 2, "pay gap": 2, "gender pay gap": 2,
    "glass ceiling": 2,
    # NOTE: "equal pay": 1 removed — neutral policy/reporting term used across
    # the full spectrum (AP, Reuters, Bloomberg). (bias-auditor fix)
    # Tech / media
    # NOTE: "misinformation": 1, "content moderation": 1, "digital rights": 1
    # removed — these are neutral tech/policy reporting terms used routinely by
    # AP, Reuters, Bloomberg, and NYT. They caused AP/Reuters tech articles to
    # score far-left (35-point error). "algorithmic bias" and
    # "big tech accountability" retain their directional signal. (bias-auditor fix)
    "algorithmic bias": 2,
    "big tech accountability": 2,
    # Community
    "community organizing": 2,
    # NOTE: "grassroots": 1 removed — used by both left and right movements
    # neutrally. Not a reliable partisan signal. (nlp-engineer fix)
    # NOTE: "solidarity": 1 removed — appears in diplomatic/international
    # coverage neutrally (e.g. "solidarity with Ukraine"). (nlp-engineer fix)
    "mutual aid": 2, "collective action": 2, "people power": 2,
    # Additional high-value terms (Priority 3b fix — closing lexicon gap)
    "critical race theory": 3,     # appears in left rebuttal framing
    "student debt forgiveness": 2,
    "student loan relief": 2,
    "gentrification": 2,
    "housing justice": 2,
    "food insecurity": 2,
    # Economic inequality framing — left-coded phrases describing upward wealth
    # transfer or disparity that appear in progressive critique and satire alike.
    # Balances right-coded "trickle down" / "fiscal responsibility" hits in
    # articles framing policy as benefiting the wealthy. (bias-auditor final cycle fix)
    "tax cut for the rich": 3,
    "tax cuts for the wealthy": 3,
    "tax break for the rich": 3,
    "top 1%": 2,
    "for the wealthy": 2,
    "struggling families": 2,
    "trickle-down economics": 3,
}

RIGHT_KEYWORDS: dict[str, int] = {
    # Immigration
    "illegal alien": 3, "illegal immigrant": 2, "illegal aliens": 3,
    # NOTE: "border security" removed entirely — even at weight=1 it causes
    # false positives in short NPR/AP articles that reference "border security
    # organizations" or "border security issues" neutrally. The phrase appears
    # across the full spectrum (DHS briefings, AP wire, congressional testimony).
    # "secure the border" (weight=3) and "build the wall" (weight=3) remain as
    # the genuinely partisan formulations. (bias-auditor Wave-3 fix)
    "secure the border": 3, "build the wall": 3,
    "illegal invasion": 3, "border crisis": 3, "mass deportation": 3,
    "open borders": 3, "migrant crime": 3, "criminal aliens": 3,
    "chain migration": 3, "anchor baby": 3, "catch and release": 2,
    # Economic
    # NOTE: "free market" and "deregulation" reduced from 2->1. Both appear
    # routinely in neutral WSJ/Bloomberg/Economist economic analysis pieces.
    # At weight=2 with 4 distinct types the sigmoid saturates, pushing WSJ
    # analysis to lean=85 (AllSides "lean right" expects [55,75]). At weight=1
    # the same article scores ~72-75, correctly reflecting mild right framing
    # without overshoot. Genuine partisan economic terms ("government overreach",
    # "nanny state", "job creators") retain weight 2-3.
    # (nlp-engineer P2 fix — WSJ lean=82 vs AllSides [55,75])
    "free market": 1, "tax cuts": 2, "trickle down": 2,
    "job creators": 3, "deregulation": 1,
    # NOTE: "small business": 1 removed — standard institutional vocabulary
    # that causes AP/Reuters to drift rightward. (nlp-engineer fix)
    # NOTE: "energy independence" reduced from 2->1. Used neutrally in energy
    # policy reporting across the spectrum. "war on coal" (3) remains as the
    # genuinely partisan formulation. (nlp-engineer P2 fix)
    "energy independence": 1, "war on coal": 3,
    "fiscal responsibility": 2, "welfare state": 3, "entitlements": 2,
    # NOTE: "government spending": 1 removed — standard policy/reporting term
    # used across the full spectrum. (nlp-engineer fix)
    # NOTE: "balanced budget": 1 removed — standard policy/reporting term
    # used across the full spectrum. (nlp-engineer fix)
    "government overreach": 3, "nanny state": 3, "tax burden": 2,
    "free enterprise": 2,
    # NOTE: "economic freedom" removed — generic term used in mainstream
    # economic discourse (World Bank "Economic Freedom Index", Heritage
    # Foundation rankings, academic papers). Not reliably partisan.
    # At weight=1 it still saturated WSJ analysis pieces to lean=85 because
    # it added a 4th distinct right keyword with zero left keywords to
    # balance. (nlp-engineer P2 fix)
    "esg agenda": 3, "esg": 2, "woke capitalism": 3,
    # Social / culture
    "traditional values": 2, "traditional family": 3, "family values": 2,
    "religious liberty": 3, "religious freedom": 2,
    "parental rights": 2, "school choice": 2,
    # NOTE: standalone "woke": 3 removed — double-counts inside every compound
    # phrase: "woke ideology", "woke agenda", "woke mob", "woke capitalism",
    # "woke military". The compound phrases already catch all legitimate uses.
    # (nlp-engineer fix)
    "cancel culture": 3, "virtue signaling": 3,
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
    # NOTE: bare "second amendment" removed — fires as a false positive on any
    # article mentioning "a second amendment to [non-US constitution/treaty]"
    # (e.g. "a second amendment to Nigeria's constitution was approved").
    # Replaced with phrase-scoped forms that are unambiguously US gun-rights framing.
    # "the second amendment" (with definite article) still fires via the phrase
    # forms below; generic "second amendment to the X" is excluded by negative
    # lookahead in the _keyword_score substitution logic.
    # (international-sources fix 2026-03-21)
    "second amendment rights": 3, "second amendment protection": 3,
    "second amendment supporters": 2, "second amendment advocates": 2,
    "right to bear arms": 3, "gun rights": 3,
    "stand your ground": 2, "constitutional carry": 3,
    "shall not be infringed": 3, "responsible gun owners": 1,
    # Law and order
    "law and order": 2, "tough on crime": 2,
    "blue lives matter": 3, "back the blue": 3, "thin blue line": 3,
    "soft on crime": 3, "pro-criminal": 3,
    # NOTE: bare "defund": 1 replaced with phrase-scoped forms. The bare word
    # also hits "defunding education", "defunding the arts", NPR budget coverage,
    # etc., causing false-right scoring of neutral budget reporting.
    # Phrase-scoped forms are unambiguously partisan attack language. (bias-auditor fix)
    "defund police": 3,           # right's attack phrase — "they want to defund police"
    "defund our military": 3,     # right's attack phrase
    "defund law enforcement": 2,  # right's attack phrase
    # Pro-life
    "pro-life": 3, "unborn": 3, "sanctity of life": 3,
    "abortion on demand": 3, "heartbeat bill": 3, "protect the unborn": 3,
    "right to life": 2, "abortion industry": 3,
    # Military / defense
    # NOTE: "national security": 1 removed — standard institutional vocabulary
    # used across the full political spectrum. (nlp-engineer fix)
    "strong military": 2,
    "peace through strength": 2, "china threat": 2, "woke military": 3,
    # NOTE: "military readiness"(1) removed — standard institutional/defense reporting
    # term used across spectrum. Not genuinely partisan. (bias-auditor fix)
    # Anti-left labels
    "radical left": 3, "socialist agenda": 3, "socialism": 2,
    "radical agenda": 3, "liberal elite": 3, "coastal elite": 3,
    "real americans": 3, "marxist": 3, "communist": 2, "antifa": 3,
    "liberal bias": 3, "mainstream media": 2,
    "far-left agenda": 3, "radical democrat": 3, "leftist": 2,
    "progressive agenda": 2, "culture war": 1,
    # Patriotism
    # NOTE: "taxpayer"(1) removed — used neutrally across spectrum in all tax/budget
    # reporting. "taxpayer-funded" remains covered by FRAMING_PHRASES at weight 0.4
    # where it appears in explicitly political contexts. (bias-auditor fix)
    # NOTE: "patriotic": 1 removed — standard institutional vocabulary that causes
    # AP/Reuters to drift rightward. (nlp-engineer fix)
    "patriot": 2,
    # Additional high-value terms (Priority 3b fix — closing lexicon gap)
    # NOTE: bare "globalists" intentionally excluded — phrase-scoped only to
    # avoid false positives in international finance/trade coverage.
    "globalist agenda": 3,
    "globalist elite": 3,
    "transgenderism": 2,
    "medical freedom": 2,
    # NOTE: "parental rights": 2 removed here — duplicate of line ~164 (Social/culture
    # section). Keeping only the first occurrence. (Cycle 3 fix)
    "america first": 2,
    # Geopolitical / state-media right-coded vocabulary
    # Chinese and Russian state media deploy these terms as pro-government
    # alignment signals that map to the authoritarian-right end of the
    # political spectrum (AllSides "right"). They are absent from Western
    # L/R vocabulary but carry the same directional meaning as "radical
    # left" or "deep state" in domestic partisan content.  Without these,
    # CGTN/RT articles with zero Western keywords score 50 (center) from
    # text alone, dragging the blended score below their calibrated baseline.
    # (nlp-engineer P1 fix — CGTN lean=63 vs AllSides "right" [70,100])
    "reunification": 2,           # CCP framing of Taiwan/territories
    "separatist forces": 3,       # CCP term for independence movements
    "splittist": 3,               # CCP term for Tibet/Taiwan activists
    "splittists": 3,              # plural form
    "territorial integrity": 1,   # neutral in isolation but state-media anchor term
    "interference in internal affairs": 3,  # CCP/Russia dismissal of human rights critique
    "hostile forces": 2,          # CCP catch-all for opposition
    "anti-china forces": 3,       # CGTN/Global Times adversarial frame
    "century of humiliation": 2,  # CCP nationalist historical framing
    "western hegemony": 3,        # RT/Sputnik/CGTN anti-Western frame
    "cold war mentality": 3,      # CCP/Russia delegitimization of Western policy
    "so-called human rights": 3,  # state-media dismissal of human rights
    "historical inevitability": 2, # CCP deterministic framing of reunification
    "denazification": 3,          # Kremlin justification for Ukraine war
    "special military operation": 3, # Kremlin euphemism for Ukraine invasion
    "collective west": 2,         # RT/Sputnik us-vs-them framing
    "western aggression": 3,      # state-media adversarial frame
    "proxy war": 2,               # RT/Sputnik framing of Ukraine conflict
    "puppet regime": 3,           # state-media delegitimization
    "russophobia": 3,             # RT anti-Western framing
    "nato aggression": 3,         # state-media adversarial frame
    "western smear": 3,           # CGTN dismissive framing
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
    # NOTE: "crisis at the border" moved to RIGHT framing — predominantly
    # right-coded alarmist framing of immigration. (nlp-engineer fix)
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
    # NOTE: "critics say", "some argue", "many believe" reduced from 0.3/0.1/0.1
    # to 0.05 each — these are standard AP/Reuters attribution phrases, not
    # partisan signals. (nlp-engineer fix)
    ("critics say", 0.05), ("some argue", 0.05), ("many believe", 0.05),
    # NOTE: "crisis at the border" moved here from LEFT framing — predominantly
    # right-coded alarmist immigration framing. (nlp-engineer fix)
    ("crisis at the border", 0.2),
    # NOTE: ("radical", 0.5) removed — bare "radical" fires on radicalization,
    # radical surgery, radical transparency, etc. Genuinely partisan uses are
    # already captured by "radical left" (weight=3), "radical agenda" (weight=3),
    # "radical democrat" (weight=3), etc. in both keywords and longer phrases.
    # (bias-auditor fix)
    ("far-left", 0.8), ("extremist left", 0.8),
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
    # Major political figures — Fix 16
    "joe biden", "biden", "bernie sanders", "sanders",
    "aoc", "alexandria ocasio-cortez", "kamala harris", "harris",
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
    # Major political figures — Fix 16
    "donald trump", "trump", "george soros", "soros", "elon musk",
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


def _keyword_score(text: str) -> tuple[float, list[str], list[str], int]:
    """Compute keyword-based lean score from 0-100. 50 = neutral.
    Returns (score, top_left_keywords, top_right_keywords, total_distinct).

    M3 fix: Use DISTINCT keyword count for sigmoid confidence (instead of
    density-weighted total).  The previous formula (floor=0.2, density-based
    total) caused short articles (<150 words) to saturate the sigmoid from
    just 1-2 keyword hits, because:
        right_total_raw = 4 (one gov-overreach hit, weight 3 + one small-biz, weight 1)
        divisor = max(107/500, 0.2) = 0.214
        right_norm = 4 / 0.214 = 18.7  →  sigmoid(18.7 - 4) ≈ 1.0  →  kw_score = 100

    A 107-word AP article mentioning 'government overreach' once in a quote
    should NOT score 100 (pure right). Scaling by density amplified sparse hits
    in short articles catastrophically.

    Fix: base the sigmoid on the count of DISTINCT keyword TYPES that fired
    (regardless of how many times each was repeated or how long the article is).
    Rationale: genuine partisan content reliably uses MULTIPLE different partisan
    terms; quoting one critic who says 'government overreach' should not behave
    identically to an op-ed that deploys 7 different right-coded terms throughout.

    Direction (right_ratio) is still computed from weighted totals so that
    high-weight terms (weight=3) count more than low-weight fillers (weight=1)
    — preserving the intensity weighting.  Only the CONFIDENCE (sigmoid) input
    switches from amplified density to distinct-type count.

    Sigmoid parameters (k=0.9, x0=3):
        1 distinct type  → sigmoid = 0.40  (cautious signal)
        2 distinct types → sigmoid = 0.60  (moderate signal)
        3 distinct types → sigmoid = 0.75  (solid signal)
        5 distinct types → sigmoid = 0.90  (strong signal)
        7+ distinct types → sigmoid ≥ 0.97 (saturated — clearly partisan)

    This gives NPR equity stories (2 left keywords) a score of ~35-40 (center-left)
    rather than 0 (extreme left), and prevents a Fox article quoting one right-wing
    critic from scoring 100 (pure right).
    """
    text_lower = text.lower()
    left_total = 0
    right_total = 0
    left_distinct = 0
    right_distinct = 0
    left_hits: dict[str, float] = {}
    right_hits: dict[str, float] = {}

    for phrase, weight in LEFT_KEYWORDS.items():
        if " " not in phrase:
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
        else:
            count = text_lower.count(phrase)
        if count > 0:
            left_total += count * weight
            left_distinct += 1
            left_hits[phrase] = count * weight

    for phrase, weight in RIGHT_KEYWORDS.items():
        if " " not in phrase:
            count = len(re.findall(r'\b' + re.escape(phrase) + r'\b', text_lower))
        else:
            count = text_lower.count(phrase)
        if count > 0:
            right_total += count * weight
            right_distinct += 1
            right_hits[phrase] = count * weight

    # NOTE: Supplemental "second amendment" regex removed — it double-counts every
    # phrase-scoped hit already captured by RIGHT_KEYWORDS ("second amendment rights",
    # "second amendment protection", "second amendment supporters", "second amendment
    # advocates"). Those phrase-scoped forms handle all legitimate US gun-rights uses.
    # (nlp-engineer Fix 1)

    # Top keywords by weighted impact (unchanged)
    top_left = sorted(left_hits, key=left_hits.get, reverse=True)[:5]
    top_right = sorted(right_hits, key=right_hits.get, reverse=True)[:5]

    total_weight = left_total + right_total
    total_distinct = left_distinct + right_distinct
    if total_weight == 0:
        return 50.0, top_left, top_right, total_distinct

    # Direction: weighted ratio (high-weight terms count more than low-weight fillers)
    right_ratio = right_total / total_weight

    # Confidence: sigmoid on DISTINCT keyword count (k=0.9, x0=3).
    # This is independent of article length and repetition, so short articles
    # with 1-2 keyword hits no longer saturate the sigmoid.
    sigmoid_weight = 1.0 / (1.0 + math.exp(-0.9 * (total_distinct - 3.0)))

    score = 50.0 + (right_ratio - 0.5) * sigmoid_weight * 100.0
    return score, top_left, top_right, total_distinct


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

    # Multiplier reduced from 3.0 to 1.5.  At 3.0, a single high-weight phrase
    # (e.g. "reproductive freedom" at -0.8) produced a shift of -2.4 which,
    # multiplied by 3, yielded -7.2 — roughly equivalent to 7 left-coded
    # keyword weight units.  That overweights isolated framing language relative
    # to keyword evidence.  At 1.5, the same phrase contributes -3.6, keeping
    # framing as a secondary signal that tilts but does not dominate lean.
    return max(-15.0, min(15.0, shift * 1.5)), phrases_found


def _entity_sentiment_score(text: str, doc=None) -> tuple[float, dict[str, float]]:
    """
    Use spaCy NER + TextBlob to gauge sentiment toward politically coded entities.
    Returns (lean_shift, entity_sentiments_dict).
    """
    if doc is None:
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
            # Use word-boundary matching: "democrat" must not hit "undemocratic",
            # "republican" must not hit "unrepublican", etc.
            # Single-word entity names get \b regex; multi-word phrases use
            # substring search (safe by construction — cannot be sub-words).
            if " " not in ent_name:
                if not re.search(r"\b" + re.escape(ent_name) + r"\b", sent_lower):
                    continue
            elif ent_name not in sent_lower:
                continue
            if blob is None:
                blob = TextBlob(sent.text)
            left_sentiment += blob.sentiment.polarity
            left_count += 1
            entity_sentiments.setdefault(ent_name, []).append(blob.sentiment.polarity)

        for ent_name in RIGHT_CODED_ENTITIES:
            if " " not in ent_name:
                if not re.search(r"\b" + re.escape(ent_name) + r"\b", sent_lower):
                    continue
            elif ent_name not in sent_lower:
                continue
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


def analyze_political_lean(article: dict, source: dict, topic_lean_data=None, doc=None) -> dict:
    """
    Score the political lean of an article.

    Args:
        article: Dict with keys: full_text, title, summary, source_id.
        source: Dict with keys: political_lean_baseline, tier, name,
                state_affiliated (optional bool).
        topic_lean_data: Optional dict from Axis 6 EMA with key "avg_lean"
                         (float 0-100). When provided, blended with source
                         baseline (70% baseline, 30% topic) for a topic-aware prior.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with evidence).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    combined = f"{title} {full_text}"
    source_baseline = _get_source_baseline(source)

    # Fix 20: Topic-specific source prior from Axis 6 EMA data.
    # Blend source baseline with topic-specific lean before text blending,
    # giving a more accurate prior for sources whose lean varies by topic.
    if topic_lean_data and "avg_lean" in topic_lean_data:
        topic_lean = float(topic_lean_data["avg_lean"])
        source_baseline = source_baseline * 0.7 + topic_lean * 0.3

    # State-affiliated outlets (RT, CGTN, Sputnik, Global Times, TRT World)
    # publish geopolitical content that uses neither Western left nor Western
    # right keyword vocabulary.  Their partisan bias is government alignment,
    # not ideological L/R.  The 0.85 text weight systematically underestimates
    # their actual editorial lean because the text signal is near-zero.  For
    # these sources, raise the baseline weight from 0.15 to 0.30 so the known
    # editorial alignment exerts stronger pull toward the calibrated baseline.
    is_state_affiliated = bool(source.get("state_affiliated"))

    # Length-adaptive baseline blending.
    #
    # Most RSS-sourced articles arrive as 30-80 word summaries.  With so little
    # text, the keyword scorer rarely accumulates enough total weight (>=4) to
    # move the sigmoid past 50%, so the text score stays near 50 regardless of
    # the source's actual lean.  The source baseline — which encodes calibrated
    # editorial lean from data/sources.json — should carry proportionally more
    # weight when text evidence is thin.
    #
    # Word-count buckets (based on combined title + full_text):
    #   <50 words   → 0.50 text / 0.50 baseline  (almost no evidence)
    #   50-150 words → 0.70 text / 0.30 baseline  (RSS summary range)
    #   150-500 words → 0.85 text / 0.15 baseline (current default, enough for signal)
    #   500+ words   → 0.90 text / 0.10 baseline  (full article, trust text)
    #
    # For state-affiliated sources, the baseline weight floors at 0.30 (the
    # existing state-media correction) so that correction is never weakened by
    # long articles that happen to use neutral geopolitical vocabulary.
    _wc = len(combined.split())
    if _wc < 50:
        text_weight, baseline_weight = 0.50, 0.50
    elif _wc < 150:
        text_weight, baseline_weight = 0.70, 0.30
    elif _wc < 500:
        text_weight, baseline_weight = 0.85, 0.15
    else:
        text_weight, baseline_weight = 0.90, 0.10

    if is_state_affiliated:
        # State-media correction: baseline weight never falls below 0.30.
        baseline_weight = max(baseline_weight, 0.30)
        text_weight = 1.0 - baseline_weight

    if not combined.strip():
        return {
            "score": source_baseline,
            "rationale": {"keyword_score": 50, "framing_shift": 0, "entity_shift": 0,
                          "source_baseline": source_baseline, "top_left_keywords": [],
                          "top_right_keywords": [], "framing_phrases_found": [],
                          "entity_sentiments": {}, "state_affiliated": is_state_affiliated},
        }

    # 1. Keyword-based score (0-100) + top keywords + distinct keyword count
    kw_score, top_left, top_right, total_distinct = _keyword_score(combined)

    # 2. Framing shift (-15 to +15) + phrases found
    framing_shift, framing_phrases = _framing_score(combined)

    # 3. Entity sentiment shift (-15 to +15) + sentiments
    entity_shift, entity_sentiments = _entity_sentiment_score(combined, doc=doc)

    # Combine text-based score
    text_score = kw_score + framing_shift + entity_shift
    text_score = max(0.0, min(100.0, text_score))

    # Fix 11: Sparsity-weighted baseline blending.
    # When NO keywords are found, lean more heavily on the source baseline.
    # A 600-word Fox News article with no keywords should score ~70-75, not 53.
    # sparsity_factor: 1.0 at zero keywords, 0.0 at 4+ distinct keywords.
    # The 0.8 multiplier prevents pure-baseline scores (keeps some text signal).
    sparsity_factor = 1.0 - min(1.0, total_distinct / 4.0)
    baseline_weight = baseline_weight + (1.0 - baseline_weight) * sparsity_factor * 0.8
    text_weight = 1.0 - baseline_weight

    # Divergence guard: when text_score diverges >30 points from source_baseline
    # AND word_count < 150, the keyword evidence is thin (short articles can
    # saturate on 1-2 incidental keyword hits).  Raise baseline_weight to at
    # least 0.60 so the calibrated source baseline anchors the final score more
    # strongly.  This corrects short AP/Reuters articles that pick up one
    # partisan keyword in a quote and score 30 points away from their baseline.
    # (bias-auditor fix)
    if _wc < 150 and abs(text_score - source_baseline) > 30:
        baseline_weight = max(baseline_weight, 0.60)
        text_weight = 1.0 - baseline_weight

    # 4. Blend with source baseline (length-adaptive weights computed above).
    final_score = text_weight * text_score + baseline_weight * source_baseline
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
            "state_affiliated": is_state_affiliated,
        },
    }
