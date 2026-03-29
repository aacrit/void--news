"""
Auto-categorization engine for the void --news pipeline.

Automatically assigns topic categories to articles based on content analysis.
Categories: politics, economy, technology, health, environment, conflict,
science, culture, sports, general.

Uses rule-based NLP (no LLM API calls):
    - Keyword matching with weighted category dictionaries
    - spaCy NER entity type boosting
"""

from utils.nlp_shared import get_nlp


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
    },
    "science": {
        "research": 2, "study": 1, "discovery": 2, "nasa": 3,
        "space": 2, "experiment": 2, "scientific": 2, "laboratory": 2,
        "physics": 3, "chemistry": 3, "biology": 2, "astronomy": 3,
        "telescope": 3, "satellite": 2, "mars": 3, "moon": 2,
        "spacex": 3, "rocket": 2, "launch": 1, "orbit": 2,
        "particle": 2, "molecule": 2, "atom": 2, "quantum": 2,
        "fossil": 2, "paleontology": 3, "archaeology": 3,
        "peer-reviewed": 3, "journal": 1, "thesis": 2,
        "hypothesis": 2, "theory": 1, "breakthrough": 2,
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
        "medal": 2, "record-breaking": 2, "season": 1,
        "injury": 1, "suspension": 2, "contract": 1,
        "espn": 3, "sporting": 2, "match": 1, "race": 1,
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
    title_lower = title.lower()
    category_scores: dict[str, float] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0.0
        for keyword, weight in keywords.items():
            count = combined_lower.count(keyword)
            if count > 0:
                # Normalize by word count to avoid length bias
                density = count / max(word_count / 100, 1)
                score += density * weight
            # Title bonus: keywords in the title are the strongest signal
            if keyword in title_lower:
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
    # Threshold of 1.5 requires at least one moderate keyword hit (weight 2
    # appearing once in a 100-word article, or multiple weight-1 hits).
    MIN_SCORE_THRESHOLD = 1.5
    if primary_score < MIN_SCORE_THRESHOLD:
        return ["general"]

    result = [sorted_cats[0][0]]

    # Include secondary categories if they score >= 60% of the primary
    for category, score in sorted_cats[1:]:
        if score >= primary_score * 0.6 and score > 0:
            result.append(category)
        else:
            break  # sorted, so remaining are lower

    return result
