"""
Auto-categorization engine for the void --news pipeline.

Automatically assigns topic categories to articles based on content analysis.
Categories: politics, economy, technology, health, environment, conflict,
science, culture, sports, general.

Uses rule-based NLP (no LLM API calls):
    - Keyword matching with weighted category dictionaries
    - spaCy NER entity type boosting
"""

import re
from functools import lru_cache

from utils.nlp_shared import get_nlp


@lru_cache(maxsize=4096)
def _keyword_pattern(keyword: str) -> "re.Pattern":
    """Word-boundary matcher for a keyword. Boundaries are alphanumeric edges,
    so short tokens ('ev', 'epa', 'eu', 'ko') match only as standalone words,
    never inside 'review'/'repatriates'/'campaign'. Phrases with spaces
    ('electric vehicle', 'heat wave') match verbatim. (2026-07-01 review CAT-3)"""
    return re.compile(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])")


# ---------------------------------------------------------------------------
# Category keyword dictionaries
# Each keyword has a weight (1-3). Higher weight = stronger signal.
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS: dict[str, dict[str, int]] = {
    "politics": {
        "election": 3, "elections": 3, "congress": 3, "congressional": 3,
        "president": 2, "presidential": 3, "senate": 3, "senator": 3,
        "legislation": 3, "legislative": 3, "vote": 2, "voting": 2,
        "democrat": 3, "democratic": 2, "republican": 3, "gop": 3,
        "policy": 2, "government": 2, "governor": 3, "mayor": 2,
        "parliament": 3, "parliamentary": 3, "cabinet": 2,
        "bipartisan": 3, "partisan": 3, "campaign": 2, "caucus": 3,
        "ballot": 3, "primary": 2, "midterm": 3, "impeach": 3,
        "inauguration": 3, "executive order": 3, "veto": 3,
        "political": 2, "politician": 2, "diplomacy": 2, "diplomat": 2,
        "ambassador": 2, "treaty": 2, "summit": 2, "state department": 3,
        "white house": 3, "capitol": 3, "supreme court": 3,
        "judicial": 2, "justice": 1, "constitution": 2, "constitutional": 2,
        "lobby": 2, "lobbyist": 3, "donor": 2, "fundraising": 2,
        # Law enforcement / political-judicial actions
        "arrested": 2, "arrest": 2, "detained": 2, "indicted": 3,
        "charged": 2, "convicted": 2, "sentenced": 2, "extradited": 3,
        "prime minister": 3, "minister": 2, "sworn in": 3,
        # Crime & justice — governance/judicial system
        "crime": 2, "criminal": 2, "murder": 2, "homicide": 3,
        "robbery": 2, "theft": 1, "fraud": 2, "corruption": 3,
        "trial": 2, "verdict": 3, "jury": 2, "plaintiff": 2,
        "prosecution": 3, "prosecutor": 3, "defendant": 2,
        "lawsuit": 2, "litigation": 2, "ruling": 2,
        "prison": 2, "inmate": 2, "parole": 2, "probation": 2,
        "death penalty": 3, "execution": 2, "death row": 3,
        "shooting": 1, "gun violence": 3, "mass shooting": 3,
        "fbi": 3, "doj": 3, "department of justice": 3,
        # Immigration — policy/governance
        "immigration": 3, "immigrant": 2, "deportation": 3,
        "border": 2, "asylum": 2, "visa": 2, "refugee": 2,
        "migrant": 2, "migration": 2, "citizenship": 2,
        "ice": 2, "customs": 1, "undocumented": 2,
    },
    "economy": {
        "gdp": 3, "inflation": 3, "market": 2, "stock": 2,
        "trade": 2, "employment": 2, "unemployment": 3, "fed": 2,
        "federal reserve": 3, "interest rate": 3, "economic": 2,
        "recession": 3, "economy": 3, "fiscal": 3, "monetary": 3,
        "wall street": 3, "dow jones": 3, "nasdaq": 3, "s&p": 3,
        "bond": 2, "treasury": 2, "deficit": 3, "debt": 2,
        "tariff": 3, "export": 2, "import": 2, "currency": 2,
        "crypto": 2, "bitcoin": 2, "cryptocurrency": 2,
        "earnings": 2, "revenue": 2, "profit": 1, "quarterly": 2,
        "consumer spending": 3, "retail sales": 3, "housing market": 3,
        "mortgage": 2, "bank": 1, "banking": 2, "financial": 2,
        "investor": 2, "investment": 2, "venture capital": 3,
        "ipo": 3, "merger": 3, "acquisition": 2, "bankruptcy": 3,
        "supply chain": 2, "manufacturing": 2, "industrial": 1,
        # v5.6: Strengthen export/trade signals — "S. Korea monthly exports"
        # was miscategorized as health due to weak economy keyword matching
        "exports": 3, "imports": 3, "trade surplus": 3,
        "trade deficit": 3, "trade balance": 3, "ceo": 2,
    },
    "technology": {
        # AI/ML — strong signals
        "artificial intelligence": 3, "machine learning": 3,
        "chatgpt": 3, "large language model": 3, "deep learning": 3,
        "openai": 3, "nvidia": 3, "generative ai": 3,
        # Cybersecurity — strong signals
        "cybersecurity": 3, "ransomware": 3, "data breach": 3,
        "zero-day": 3, "hacking": 3, "cyberattack": 3,
        # Software/industry — moderate signals
        "software update": 2, "open source": 2, "programming": 2,
        "silicon valley": 3, "tech company": 3, "tech industry": 3,
        "tech giant": 3, "software": 2, "app store": 2,
        # Hardware — moderate signals
        "semiconductor": 3, "microchip": 3, "quantum computing": 3,
        # Platforms — only strong tech-specific usages
        "cryptocurrency": 2, "bitcoin": 2, "blockchain": 2,
        # Transport tech — only unambiguous phrases
        "self-driving": 3, "autonomous vehicle": 3,
        # Connectivity — only strong signals
        "5g network": 2, "fiber optic": 2,
        # Immersive tech
        "virtual reality": 3, "augmented reality": 3, "metaverse": 3,
        # Robotics
        "robotics": 3, "robot": 2,
        # Big tech companies
        "google": 2, "apple": 2, "meta platforms": 3, "amazon web services": 3,
        "microsoft azure": 3, "cloud computing": 3, "tech startup": 3,
        # AI-specific terms (often categorized as "general" without these).
        # 2026-06-29: bare "ai" REMOVED — as a 2-char substring it matched
        # inside common words (rem-AI-n, cl-AI-ms, cert-AI-n, camp-AI-gn),
        # falsely tagging unrelated stories technology->science. Phrase forms
        # are safe substrings; real AI coverage still resolves via openai /
        # anthropic / "ai model" / chatbot / llm / "artificial intelligence".
        "ai model": 3, "ai models": 3, "ai chatbot": 3, "ai system": 2,
        "ai tool": 2, "ai race": 3, "a.i.": 3,
        "chatbot": 3, "llm": 3, "gpt": 3, "anthropic": 3,
        "copilot": 2, "deepfake": 3, "neural network": 3,
        "training data": 3, "foundation model": 3, "transformer": 2,
        "tech regulation": 3, "antitrust": 2, "data privacy": 3,
        "social media": 2, "algorithm": 2, "encryption": 2,
        "startup": 1, "unicorn": 2,
        # Consumer tech / messaging apps (2026-07-01 review CAT-4): a pure
        # app story like "WhatsApp to launch usernames" matched no tech
        # keyword and fell to conflict via a GPE boost.
        "whatsapp": 3, "telegram app": 3, "signal app": 3, "imessage": 3,
        "messaging app": 3, "username": 2, "usernames": 2, "sim card": 2,
        "sim-binding": 3, "smartphone": 2, "iphone": 2, "android": 2,
        "instagram": 2, "tiktok": 2, "youtube": 1, "gadget": 2,
        "operating system": 2, "data center": 2, "chip": 1, "chipmaker": 3,
    },
    "health": {
        "vaccine": 3, "vaccination": 3, "disease": 2, "hospital": 2,
        "medical": 2, "health": 2, "pandemic": 3, "epidemic": 3,
        "treatment": 2, "drug": 2, "fda": 3, "patient": 2,
        "doctor": 1, "physician": 2, "nurse": 1, "surgeon": 2,
        "clinical trial": 3, "pharmaceutical": 3, "pharma": 2,
        "mental health": 3, "depression": 2, "anxiety": 1,
        "cancer": 2, "diabetes": 2, "heart disease": 3,
        "covid": 3, "coronavirus": 3, "virus": 2, "infection": 2,
        "who": 2, "world health organization": 3, "cdc": 3,
        "nih": 3, "public health": 3, "healthcare": 3,
        "opioid": 3, "overdose": 2, "fentanyl": 3,
        "diagnosis": 2, "symptom": 2, "therapy": 2,
        "biotech": 2, "biotechnology": 3, "genome": 3,
        "surgical": 2, "transplant": 2, "organ": 1,
        "insurance": 1, "medicare": 2, "medicaid": 2,
    },
    "environment": {
        "climate": 3, "carbon": 2, "pollution": 3, "renewable": 3,
        "emissions": 3, "environmental": 3, "wildfire": 3,
        "drought": 3, "ecosystem": 3, "biodiversity": 3,
        "deforestation": 3, "conservation": 2, "endangered": 2,
        "solar": 2, "wind energy": 3, "green energy": 3,
        "fossil fuel": 3, "oil spill": 3, "coal": 2,
        "paris agreement": 3, "climate change": 3, "global warming": 3,
        "sea level": 3, "glacier": 3, "arctic": 2, "antarctic": 2,
        "epa": 3, "greenhouse": 3, "methane": 3,
        "sustainability": 2, "sustainable": 2, "recycling": 2,
        "electric vehicle": 3, "ev": 2, "clean energy": 3,
        "hurricane": 2, "tornado": 2, "flood": 1, "flooding": 2,
        "earthquake": 2, "tsunami": 2, "volcanic": 2,
        "water quality": 3, "air quality": 3, "smog": 3,
        "plastic": 1, "microplastic": 3, "ocean acidification": 3,
        # Extreme-heat vocabulary (2026-07-01 review CAT-4): a heatwave
        # cluster matched no environment keyword and fell to "general".
        "heat wave": 3, "heatwave": 3, "heat advisory": 3, "extreme heat": 3,
        "record heat": 3, "record temperatures": 3, "heat-related": 3,
        "scorching": 2, "sweltering": 2, "heat dome": 3, "temperatures": 1,
        "wildfires": 3, "blaze": 1,
    },
    "conflict": {
        "war": 3, "military": 3, "attack": 2, "troops": 3,
        "defense": 2, "weapons": 3, "conflict": 2, "ceasefire": 3,
        "nato": 3, "terrorism": 3, "terrorist": 3,
        "airstrike": 3, "bombing": 3, "missile": 3, "drone strike": 3,
        "invasion": 3, "occupation": 2, "siege": 3,
        "casualty": 3, "casualties": 3, "killed in action": 3,
        "refugee": 2, "displacement": 2, "humanitarian crisis": 3,
        "peacekeeping": 3, "sanctions": 2, "arms deal": 3,
        "nuclear weapon": 3, "chemical weapon": 3, "biological weapon": 3,
        "insurgent": 3, "rebel": 2, "militia": 3, "guerrilla": 3,
        "pentagon": 3, "armed forces": 3, "navy": 2, "army": 2,
        "combat": 3, "battlefield": 3, "frontline": 3,
        "coup": 3, "revolution": 2, "civil war": 3,
        "hostage": 3, "kidnapping": 2, "assassination": 3,
        "espionage": 3, "intelligence": 1, "cia": 2,
        # Military-specific terms to outweigh politics NER boosts
        "strike": 2, "strikes": 2, "shelling": 3, "artillery": 3,
        "airforce": 3, "warship": 3, "submarine": 3,
        "killed": 2, "wounded": 2, "fighters": 2,
        # v5.6: Nuclear disambiguation — "nuclear" in news context is almost
        # always geopolitical, not science. "nuclear threat eliminated" was
        # miscategorized as science; these phrases anchor it to conflict.
        "nuclear": 2, "nuclear threat": 3, "nuclear program": 3,
        "nuclear deal": 3, "nuclear arsenal": 3, "nuclear capability": 3,
        "nuclear talks": 3, "nuclear strike": 3,
        # v5.6: Kidnapping/abduction — conflict, not general crime
        "kidnapped": 3, "abducted": 3, "hostage crisis": 3,
    },
    "science": {
        # 2026-06-28 (O10): dropped the generic terms that fired on hard news —
        # "study"/"launch"/"theory" (launch an offensive, conspiracy theory) and
        # "journal" (matched the outlet "Wall Street Journal"). Science stories
        # still resolve via the specific terms below.
        "research": 2, "discovery": 2, "nasa": 3,
        "space": 2, "experiment": 2, "scientific": 2, "laboratory": 2,
        "physics": 3, "chemistry": 3, "biology": 2, "astronomy": 3,
        "telescope": 3, "satellite": 2, "mars": 3, "moon": 2,
        "spacex": 3, "rocket": 2, "orbit": 2,
        "particle": 2, "molecule": 2, "atom": 2, "quantum": 2,
        "fossil": 2, "paleontology": 3, "archaeology": 3,
        "peer-reviewed": 3, "thesis": 2,
        "hypothesis": 2, "breakthrough": 2,
        "neuroscience": 3, "genetics": 3, "dna": 3, "rna": 3,
        "evolution": 2, "species": 1, "climate science": 3,
        "observatory": 3, "cosmic": 3, "galaxy": 3, "universe": 2,
        "nobel prize": 3, "scientist": 2, "researcher": 1,
    },
    "culture": {
        "film": 2, "movie": 2, "music": 2, "art": 1,
        "book": 1, "celebrity": 2, "entertainment": 2,
        "festival": 2, "exhibition": 2, "museum": 2, "gallery": 2,
        "theater": 2, "theatre": 2, "broadway": 3, "concert": 2,
        "album": 2, "streaming": 1, "netflix": 2, "disney": 2,
        "oscar": 3, "emmy": 3, "grammy": 3, "tony": 2,
        "bestseller": 2, "novelist": 2, "author": 1,
        "fashion": 2, "designer": 1, "model": 1,
        "television": 2, "tv show": 2, "series": 1, "premiere": 2,
        "box office": 3, "director": 1, "actor": 2, "actress": 2,
        "viral": 1, "trending": 1, "influencer": 2,
        "podcast": 2, "documentary": 2, "animation": 2,
        "photography": 2, "sculpture": 2, "painting": 2,
        "cultural": 2, "heritage": 2, "tradition": 1,
        # v5.6: Celebrity trouble stories — often miscategorized as
        # health/politics when the subject is a public figure
        "dui": 2, "mugshot": 2, "rehab": 2, "tabloid": 2,
        "paparazzi": 2, "red carpet": 2, "memoir": 2,
        # Religion — maps to culture desk (no standalone religion category)
        "pope": 3, "vatican": 3, "catholic": 2, "church": 1,
        "easter": 2, "christmas": 2, "ramadan": 2, "eid": 2,
        "mosque": 2, "synagogue": 2, "temple": 1, "rabbi": 2,
        "imam": 2, "bishop": 2, "cardinal": 2, "archbishop": 3,
        "evangelical": 2, "protestant": 2, "orthodox": 1,
        "buddhist": 2, "hindu": 2, "muslim": 1, "christian": 1,
        "prayer": 1, "worship": 2, "congregation": 2,
        "religious": 2, "faith": 1, "clergy": 2, "sermon": 2,
        "pilgrimage": 2, "holy": 1, "sacred": 1, "scripture": 2,
        # Education — maps to culture desk
        "university": 1, "college": 1, "school": 1, "student": 1,
        "professor": 2, "campus": 2, "graduation": 2, "tuition": 2,
        "scholarship": 2, "academic": 1, "curriculum": 2,
        "school board": 3, "teacher": 1, "principal": 1,
    },
    "sports": {
        "game": 1, "championship": 3, "player": 2, "team": 1,
        "score": 1, "tournament": 3, "league": 2, "coach": 2,
        "nfl": 3, "nba": 3, "mlb": 3, "nhl": 3, "mls": 3,
        "fifa": 3, "olympics": 3, "olympic": 3, "world cup": 3,
        "super bowl": 3, "world series": 3, "playoffs": 3,
        "quarterback": 3, "touchdown": 3, "home run": 3,
        "goal": 1, "assist": 1, "rebound": 2,
        "transfer": 1, "draft": 2, "free agent": 3,
        "stadium": 2, "arena": 1, "athlete": 2,
        "tennis": 2, "golf": 2, "soccer": 2, "football": 2,
        "basketball": 2, "baseball": 2, "hockey": 2,
        "boxing": 2, "mma": 3, "ufc": 3, "wrestling": 2,
        # Combat sports — "fighter" often miscategorized as conflict
        "fighter": 2, "fight": 1, "bout": 2, "knockout": 3,
        "heavyweight": 3, "middleweight": 3, "lightweight": 3,
        "welterweight": 3, "featherweight": 3, "bantamweight": 3,
        "title fight": 3, "undercard": 3, "ringside": 3,
        "round": 1, "ko": 2, "tko": 3, "decision": 1,
        "medal": 2, "record-breaking": 2, "season": 1,
        "injury": 1, "suspension": 2, "contract": 1,
        "espn": 3, "sporting": 2, "match": 1, "race": 1,
        # Additional sports
        "cricket": 2, "rugby": 2, "f1": 3, "formula 1": 3,
        "grand prix": 3, "marathon": 2, "triathlon": 2,
    },
}

# ---------------------------------------------------------------------------
# NER entity label to category boost mapping
# ---------------------------------------------------------------------------
NER_CATEGORY_BOOST: dict[str, dict[str, float]] = {
    "GPE": {"politics": 0.3, "conflict": 0.3},  # balanced (was 0.5/0.3)
    "ORG": {"economy": 0.3},
    "PERSON": {"politics": 0.2, "culture": 0.2},
    "MONEY": {"economy": 0.5},
    "PERCENT": {"economy": 0.3},
    "DATE": {},  # generic, no boost
    "NORP": {"politics": 0.2, "conflict": 0.2},  # balanced (was 0.3/0.2)
    "FAC": {"culture": 0.2},
    "EVENT": {"sports": 0.3, "culture": 0.3, "conflict": 0.2},
    "PRODUCT": {"technology": 0.1},
    "LAW": {"politics": 0.5},
}


# ---------------------------------------------------------------------------
# Desk mapping — fine-grained categories → merged display desks
# The pipeline still uses fine-grained keywords for NLP accuracy, but the
# cluster-level category stored in the DB uses these merged desk slugs.
# ---------------------------------------------------------------------------
DESK_MAP: dict[str, str] = {
    "politics": "politics",       # Politics (domestic governance, elections, policy)
    "conflict": "conflict",       # Conflict (war, military, terrorism, security)
    "economy": "economy",         # Economy (unchanged)
    "technology": "science",      # Science + Tech → "Science"
    "science": "science",
    "health": "health",           # Health (unchanged)
    "environment": "environment", # Environment (climate, disasters, conservation)
    "culture": "culture",         # Culture + Sports → "Culture"
    "sports": "culture",
    "general": "general",
}


def map_to_desk(fine_category: str) -> str:
    """Map a fine-grained category slug to its merged desk slug."""
    return DESK_MAP.get(fine_category, fine_category)


# 2026-05-21 nlp-engineer fix — early categorizer for Axis 6 EMA.
# The full categorize_article() uses spaCy NER + keyword density + entity
# boosting (≥10ms per article). It runs at pipeline step 7. But step 5's
# bias analysis needs the article's category NOW to look up the per-source
# per-topic EMA (source_topic_lean table) and blend it into the political
# lean score. Without a category at step 5, the 30% topic-blend in
# political_lean.py:858 is dead code on read — the per-topic EMA axis
# has been wired but dormant for the entire production lifetime.
#
# This is a microsecond-grade URL/section-only pre-categorizer. It
# correctly tags 60-70% of articles whose URL path or section metadata
# is unambiguous. The remaining articles get category="" and topic_lean
# stays None at step 5 (matching prior behavior). Step 7 still runs the
# full NLP categorizer to refine and store the final cluster category.

_URL_CATEGORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"/(?:politics|election|elections|political|campaign|campaigns)(?:/|$)", re.IGNORECASE), "politics"),
    (re.compile(r"/(?:world|international|global|foreign[-_ ]?affairs|world[-_ ]?news)(?:/|$)", re.IGNORECASE), "world"),
    (re.compile(r"/(?:business|economy|economic|markets|finance|financial|money|stocks|investing)(?:/|$)", re.IGNORECASE), "business"),
    (re.compile(r"/(?:tech|technology|tech[-_ ]?news|software|hardware|ai[-_ ]?news|gadgets)(?:/|$)", re.IGNORECASE), "tech"),
    (re.compile(r"/(?:science|sciences|scientific|research|space|astronomy|physics|biology|chemistry)(?:/|$)", re.IGNORECASE), "science"),
    (re.compile(r"/(?:health|healthcare|medical|medicine|wellness|fitness|nutrition)(?:/|$)", re.IGNORECASE), "health"),
    (re.compile(r"/(?:climate|environment|environmental|sustainability|green|weather)(?:/|$)", re.IGNORECASE), "climate"),
    (re.compile(r"/(?:sports|sport|games|nfl|nba|mlb|soccer|football|cricket|olympics)(?:/|$)", re.IGNORECASE), "sports"),
    (re.compile(r"/(?:culture|arts|entertainment|movies|music|tv|television|books|literature|theater)(?:/|$)", re.IGNORECASE), "culture"),
    (re.compile(r"/(?:opinion|opinions|editorial|editorials|op[-_]?ed|column|columns|commentary)(?:/|$)", re.IGNORECASE), "opinion"),
    (re.compile(r"/(?:lifestyle|food|travel|fashion|home|garden|family|parenting)(?:/|$)", re.IGNORECASE), "lifestyle"),
    (re.compile(r"/(?:law|legal|crime|courts|justice|police)(?:/|$)", re.IGNORECASE), "crime"),
    (re.compile(r"/(?:education|schools|university|college|academic)(?:/|$)", re.IGNORECASE), "education"),
]

_SECTION_CATEGORY_MAP: dict[str, str] = {
    "politics": "politics", "world": "world", "international": "world",
    "business": "business", "economy": "business", "markets": "business",
    "tech": "tech", "technology": "tech",
    "science": "science", "health": "health", "climate": "climate",
    "sports": "sports", "culture": "culture", "entertainment": "culture",
    "arts": "culture", "opinion": "opinion", "editorial": "opinion",
    "lifestyle": "lifestyle", "crime": "crime", "education": "education",
}


def categorize_early(article: dict) -> str:
    """Return a single best-guess category from URL + section only.

    Designed for step 4 (pre-bias-analysis) where we need a category
    string for the per-topic EMA lookup but can't afford full NLP
    categorization yet. Returns empty string when neither signal
    resolves — in that case the topic_lean blend at step 5 stays None.

    No spaCy, no keyword density, no entity recognition. Pure regex +
    dict lookup on already-fetched article metadata. ~5 microseconds.
    """
    # Section metadata is the strongest signal: outlets self-classify.
    section = (article.get("section") or "").strip().lower()
    if section in _SECTION_CATEGORY_MAP:
        return _SECTION_CATEGORY_MAP[section]
    # URL path: /politics/, /world/, /tech/, etc. Many outlets put the
    # category in the second URL segment.
    url = article.get("url") or ""
    for pat, cat in _URL_CATEGORY_PATTERNS:
        if pat.search(url):
            return cat
    return ""


def categorize_article(article: dict) -> list[str]:
    """
    Assign topic categories to an article.

    Args:
        article: Dict with keys: title, summary, full_text, section.

    Returns:
        List of category slugs (e.g., ['politics', 'economy']).
        An article may belong to multiple categories.
        Returns at least one category.
        Slugs are fine-grained — call map_to_desk() to get display desks.
    """
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""
    full_text = article.get("full_text", "") or ""

    # Build analysis text: weight title more heavily by repeating it
    combined = f"{title} {title} {title} {summary} {full_text}"
    combined_lower = combined.lower()
    word_count = len(combined_lower.split())

    if word_count == 0:
        return ["general"]  # safe default for empty articles

    # 1. Keyword matching scores (title keywords get 2x weight)
    #
    # 2026-07-01 (review CAT-3): keyword hits are matched on WORD BOUNDARIES,
    # not raw substrings. The old combined_lower.count(keyword) matched short
    # abbreviations inside unrelated words — "ev" inside "review"/"revolution",
    # "epa" inside "repatriates", "ai" inside "campaign" — which made
    # `environment` a false-positive magnet (the #1 SCOTUS lead was tagged
    # environment via "ev"). _boundary_count() requires non-alphanumeric
    # neighbors so "ev" only matches the standalone token.
    title_lower = title.lower()
    category_scores: dict[str, float] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for keyword, weight in keywords.items():
            pat = _keyword_pattern(keyword)
            count = len(pat.findall(combined_lower))
            if count > 0:
                # Normalize by word count to avoid length bias
                density = count / max(word_count / 100, 1)
                score += density * weight
            # Title bonus: keywords in the title are the strongest signal
            if pat.search(title_lower):
                score += weight * 2.0
        category_scores[category] = score

    # 2. NER entity type boosting
    nlp = get_nlp()
    # Process title + summary (more focused than full text)
    analysis_text = f"{title} {summary}"[:10000]
    doc = nlp(analysis_text)

    entity_label_counts: dict[str, int] = {}
    for ent in doc.ents:
        entity_label_counts[ent.label_] = entity_label_counts.get(ent.label_, 0) + 1

    for label, count in entity_label_counts.items():
        boosts = NER_CATEGORY_BOOST.get(label, {})
        for category, boost_factor in boosts.items():
            category_scores[category] = category_scores.get(category, 0.0) + count * boost_factor

    # 3. Section metadata boost
    section = (article.get("section", "") or "").lower()
    if section:
        for category in CATEGORY_KEYWORDS:
            if category in section:
                category_scores[category] = category_scores.get(category, 0.0) + 5.0

    # 4. Select categories
    if not category_scores or max(category_scores.values()) == 0:
        return ["general"]  # default when no keywords matched

    # Sort by score descending
    sorted_cats = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)

    # Primary category is always included
    primary_score = sorted_cats[0][1]

    # Minimum score threshold: if the best score is very low, the article
    # couldn't be confidently classified — return "general" rather than
    # a misleading label based on a single weak keyword match.
    # Threshold of 1.0 requires at least one weak keyword hit. Lowered from
    # 1.5 to reduce "general" catch-all assignments (was 20% of clusters).
    MIN_SCORE_THRESHOLD = 1.0
    if primary_score < MIN_SCORE_THRESHOLD:
        return ["general"]

    result = [sorted_cats[0][0]]

    # Include secondary categories if they score >= 60% of the primary
    for category, score in sorted_cats[1:]:
        if score >= primary_score * 0.6 and score > 0:
            result.append(category)
        else:
            break  # sorted, so remaining are lower

    # Title-based hard override (v5.9) — strong title markers force category
    # regardless of keyword scoring. Catches: "fires AG" → politics (not economy),
    # "boxing odds" → sports (not environment), "F-15 shot down" → conflict.
    import re
    _tl = title_lower

    # v6.1 (2026-05-14) — Mass-casualty pre-override. A title carrying a hard
    # death-toll number ("storm kills 100", "bombing kills 9") belongs in
    # `conflict` under the current 10-category taxonomy, not `science` or
    # `environment` where storm/island keywords pull it. Skip when title
    # carries retrospective markers (study/report/model) so genuine analytical
    # pieces about historical death tolls stay in their subject category.
    _mass_casualty_skip = any(
        w in _tl
        for w in ("study", "report finds", "report shows", "research finds",
                  "estimates", "estimated", "model", "modeled", "modeling",
                  "estimate that", "found that")
    )
    if not _mass_casualty_skip:
        # v6.2 (2026-05-15): expanded verb set to catch all conjugations.
        # The original regex used a small explicit list (killed|kills|dead...)
        # which missed "Storm Kills Over 100" (UP storm — title-case "Kills"
        # tokenises fine, but the audit revealed other present-tense forms
        # like "Floods Killing 50" and "Bombing Killed dozens" weren't catching
        # because the connector word between verb and number varied.
        # New rule: any "kill*" word stem + optional connector ("over",
        # "at least", "about", "nearly") + number ≥ 5.
        _cas = re.search(
            r"\b(?:kill\w*|dead|deaths|fatalit\w*|dies|died)\s+"
            r"(?:(?:over|at\s+least|about|nearly|more\s+than|some)\s+)?"
            r"(\d{1,4})\b",
            _tl,
        )
        if _cas and int(_cas.group(1)) >= 5:
            if result[0] != "conflict":
                result = ["conflict"] + [c for c in result if c != "conflict"]
    _TITLE_OVERRIDES = [
        # Sports: league names, match-ups, odds, scores
        (r"\b(nba|nfl|mlb|nhl|mls|ufc|mma|premier league|la liga|bundesliga|serie a)\b", "sports"),
        (r"\b(boxing|bout|heavyweight|middleweight|lightweight|welterweight|knockout|ko|tko)\b", "sports"),
        (r"\b(fighter|fight night|title fight|ringside|undercard)\b", "sports"),
        (r"\bvs\.?\s", "sports"),  # "X vs Y" pattern
        (r"\b(odds|prediction|picks|fantasy|draft pick|free agent|trade deadline)\b", "sports"),
        (r"\b(quarterback|touchdown|home run|slam dunk|hat trick|penalty kick)\b", "sports"),
        (r"\b(lakers|celtics|yankees|dodgers|cowboys|patriots|warriors|chiefs)\b", "sports"),
        (r"\b(cricket|rugby|f1|formula 1|grand prix|marathon|triathlon)\b", "sports"),
        # Accidents/disasters (no dedicated desk) -> general, so a fatal crash
        # is not mislabeled "conflict" by the "killed/injured" keywords or the
        # mass-casualty pre-override. Placed BEFORE the conflict markers so a
        # military cause ("plane shot down", "missile") still wins for a mixed
        # title (later override in this list takes precedence). (2026-06-28)
        (r"\b(?:plane|jet|aircraft|airliner|helicopter|chopper)\b.{0,18}?"
         r"\bcrash(?:e[ds])?\b"                       # "plane crashes/crashed/has crashed"
         r"|\bcrash(?:e[ds])?\s+into\b"               # "crashed into a building"
         r"|\b(?:plane|jet|air|helicopter)\s+crash\b" # "plane crash" (noun)
         r"|\b(?:train derail\w*|derailment|building collapse|bridge collapse|"
         r"ferry (?:capsiz\w*|sink\w*)|bus crash\w*|car crash\w*|stampede)\b", "general"),
        # Conflict: military hardware, combat actions
        (r"\b(f-15|f-35|f-16|b-52|warplane|fighter jet|warship|submarine)\b", "conflict"),
        (r"\b(shot down|downed|airstrike|shelling|bombardment|missile strike)\b", "conflict"),
        # v6.1: military arrests / infiltration / bombing — strong conflict
        # markers that incidental environment/science keywords ("island",
        # "storm") can otherwise hijack.
        (r"\b(drone strike|car bomb|suicide bomb|bazaar bombing|market bombing)\b", "conflict"),
        (r"\b(irgc\s+(?:arrests?|members?|infiltration)|infiltrators?\s+(?:detained|arrested))\b", "conflict"),
        (r"\b(narco-terrorist|narco terror|terror plot|terror attack)\b", "conflict"),
        # v6.3 (2026-05-15): bilateral/diplomatic summit titles — strong
        # politics override. Production audit caught a Trump-Xi Iran
        # summit cluster mis-tagged as `category=science, section=us`
        # because wire-desk briefings were dense in "research / launch /
        # discovery" vocabulary that pulled the score toward science.
        # Title-level summit + pair-name signal forces politics.
        (r"\b(?:trump|biden|xi|putin|modi|netanyahu|starmer|zelensky|macron)[-\s]+"
         r"(?:trump|biden|xi|putin|modi|netanyahu|starmer|zelensky|macron)\b", "politics"),
        (r"\b(?:bilateral|trilateral|g[-\s]?7|g[-\s]?20|brics)\s+(?:summit|talks|meeting)\b", "politics"),
        (r"\b(?:summit|talks|meeting)\s+(?:on|over|about)\s+(?:iran|china|russia|nuclear|trade|sanctions|tariffs)\b", "politics"),
        (r"\b(?:state|presidential|prime\s+minister'?s?)\s+visit\s+to\b", "politics"),
        # Politics: appointments, firings, executive actions
        (r"\b(fires|fired|ousts|ousted|appoints|appointed|nominates|sworn in)\b", "politics"),
        (r"\b(attorney general|secretary of|chief of staff|executive order)\b", "politics"),
        # Culture/Religion: strong religious markers
        (r"\b(pope|vatican|easter|ramadan|eid al|dalai lama)\b", "culture"),
    ]
    for pattern, override_cat in _TITLE_OVERRIDES:
        if re.search(pattern, _tl):
            if result[0] != override_cat:
                result = [override_cat] + [c for c in result if c != override_cat]
            break

    return result


# NOTE (2026-07-01): a title+summary `categorize_cluster()` was prototyped
# here during the top-50 review, but main's O10 headline-primary path
# (main.py / rerank.py) proved strictly better — the cluster HEADLINE is immune
# to the off-topic summary an over-merged cluster accumulates, whereas voting
# over the summary re-imported that pollution. The engine fixes that made O10
# correct on the flagged cases live above: word-boundary keyword matching
# (kills ev/epa/eu/ai substring false positives) and the consumer-tech /
# extreme-heat vocabulary. No separate cluster-categorizer is needed.
