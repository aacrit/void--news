"""
Edition-unique ranking layer v6.0 for the void --news pipeline.

Single source of truth for all edition-specific ranking logic.
Imported by both main.py (production 3x daily) and rerank.py (manual CLI).

Extracted from duplicated code in main.py (v5.7) and rerank.py (v5.7) which
had drifted to use different parameters. Canonical parameters come from
main.py (production-tested). Good features from rerank.py (same-event cap,
story-type gates, low-affinity demotion, regional keyword boost) are included.
Redundant features (freshness decay, source depth bonus) are dropped.

Three mechanisms per edition:
  1. REGIONAL AFFINITY BOOST: proportional to % of articles from the edition's
     region (up to 1.50x, quality-capped for thin stories).
  2. LOCAL-PRIORITY BOOST: edition-exclusive stories with 5+ sources get 1.40x.
  3. CROSS-EDITION DEMOTION: stories claimed by a previous edition's top-8
     get 0.70x (milder 0.88x for globally significant stories).

Plus: edition lead gate, same-event cap, topic diversity, thin-edition
backfill, story-type gates, regional keyword boost.

Processing order: regional first (us -> europe -> south-asia), then world.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Configuration — single source of truth
# ---------------------------------------------------------------------------
EDITIONS = ["us", "europe", "south-asia", "world"]  # regional first!

CROSS_EDITION_TOP = 8
CROSS_DEMOTION = 0.70
GLOBAL_SIG_DEMOTION = 0.88
GLOBAL_SIG_SOURCES = 20
GLOBAL_SIG_EDITIONS = 3
LOCAL_EXCLUSIVE_BOOST = 1.40
LOCAL_CROSSLIST_BOOST = 1.0
AFFINITY_MAX_BOOST = 1.5
WORLD_MULTI_ED_BOOST = 1.12

# Edition lead gate: top positions require this many sources
ED_LEAD_MIN = 3
ED_LEAD_SLOTS = 10

# Backfill: import from world when regional edition is thin
BACKFILL_QUALITY_FLOOR = 30.0  # lowered from 40 — thin editions (SA, EU) need more content
BACKFILL_TARGET = 15  # raised from 10 — fill more slots for thin editions
BACKFILL_SOURCE_MIN = 3  # lowered from 5 — 3-source stories are quality enough for backfill

# Same-event cap (from rerank.py — prevents feed dominated by one event)
MAX_SAME_EVENT = 2
EVENT_DECAY = 0.80

# Topic diversity
MAX_SAME_CAT_DEFAULT = 2
MAX_SAME_CAT_SOFT = 1
TOP_N = 10

# Low-affinity demotion threshold
LOW_AFFINITY_THRESHOLD = 0.10
LOW_AFFINITY_DEMOTION = 0.65

# Local-priority source count gate
LOCAL_PRIORITY_MIN_SOURCES = 5

# Affinity quality cap denominator (full boost at this many sources)
AFFINITY_QUALITY_CAP_SOURCES = 5

# Story-type multipliers
STORY_TYPE_GATES = {
    "incremental_update": 0.75,
    "ceremonial": 0.82,
}

# ---------------------------------------------------------------------------
# Country → edition mapping
# ---------------------------------------------------------------------------
COUNTRY_EDITION_MAP: dict[str, str] = {
    "US": "us",
    "IN": "south-asia", "PK": "south-asia", "BD": "south-asia",
    "LK": "south-asia", "NP": "south-asia", "AF": "south-asia",
    "MV": "south-asia", "BT": "south-asia",
    "GB": "europe", "UK": "europe",
    "FR": "europe", "DE": "europe", "ES": "europe", "IT": "europe",
    "NL": "europe", "BE": "europe", "PT": "europe", "AT": "europe",
    "CH": "europe", "IE": "europe", "SE": "europe", "DK": "europe",
    "NO": "europe", "FI": "europe", "IS": "europe",
    "PL": "europe", "CZ": "europe", "RO": "europe", "BG": "europe",
    "HR": "europe", "RS": "europe", "GR": "europe", "HU": "europe",
    "EE": "europe", "LV": "europe", "LT": "europe",
    "UA": "europe", "GE": "europe",
}

# ---------------------------------------------------------------------------
# Regional content keywords — boost stories ABOUT a region in that edition
# ---------------------------------------------------------------------------
REGIONAL_KEYWORDS: dict[str, set[str]] = {
    "us": {
        "congress", "senate", "white house", "capitol", "supreme court",
        "fbi", "cia", "pentagon", "doj", "irs", "fda", "epa", "cdc",
        "american", "americans", "democrat", "republican", "gop",
    },
    "europe": {
        "eu", "european union", "brussels", "nato", "ecb",
        "eurozone", "brexit", "uk", "britain", "germany", "france",
        "spain", "italy", "poland", "ukraine", "parliament",
    },
    "south-asia": {
        "india", "indian", "modi", "delhi", "mumbai", "bjp", "congress",
        "pakistan", "pakistani", "islamabad", "karachi", "lahore",
        "bangladesh", "dhaka", "nepal", "kathmandu",
        "sri lanka", "colombo", "kashmir", "rupee", "taliban",
        "lok sabha", "rajya sabha", "bsf", "ipl", "cricket",
        "hindu", "muslim", "sikh", "temple", "mosque",
        "chennai", "kolkata", "hyderabad", "bengaluru", "pune",
        "afghan", "afghanistan", "balochistan", "sindh", "punjab",
    },
}

# ---------------------------------------------------------------------------
# Same-event keyword groups (will go stale — TODO: dynamic extraction)
# ---------------------------------------------------------------------------
EVENT_KEYWORDS: dict[str, set[str]] = {
    "iran": {
        "iran", "iranian", "tehran", "hormuz", "persian gulf", "irgc",
        "hegseth", "isfahan", "f-15", "f-35", "warplane", "fighter jet",
    },
    "ukraine": {
        "ukraine", "ukrainian", "kyiv", "zelenskyy", "zelensky",
        "donbas", "crimea",
    },
    "israel_palestine": {
        "gaza", "hamas", "west bank", "netanyahu", "idf", "hezbollah",
        "israeli protest",
    },
    "china_taiwan": {"taiwan", "taipei", "strait", "xi jinping", "pla"},
    "us_scotus": {
        "supreme court", "scotus", "constitutional", "alito", "justice",
    },
}

# Soft-news categories for topic diversity
_SOFT_CATS: frozenset[str] = frozenset({
    "sports", "entertainment", "culture", "lifestyle",
    "celebrity", "music", "film", "television", "gaming",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_edition_ranking(
    clusters: list[dict],
    sources: list[dict],
    *,
    get_article_edition: str = "auto",
) -> None:
    """
    Apply edition-unique ranking to clusters in-place.

    Each cluster dict must have:
        - id: str (unique identifier)
        - headline_rank: float (base importance score from rank_importance())
        - source_count: int
        - sections: list[str] (edition memberships, e.g. ["us", "world"])
        - title: str
        - articles: list[dict] (article dicts)
        - category: str (optional)
        - story_type: str | None (optional, for incremental/ceremonial gates)

    Each article dict must have:
        - source_id: str

    For articles from main.py, each article also has:
        - section: str (edition derived from source country)

    For articles from rerank.py, section is derived from sources list.

    Args:
        clusters: List of cluster dicts (modified in-place).
        sources: Full sources list with id, db_id, country fields.
        get_article_edition: How to determine an article's edition.
            "section" — use article["section"] field (main.py path).
            "source_lookup" — derive from source country (rerank.py path).
            "auto" — try "section" first, fall back to "source_lookup".
    """
    if not clusters:
        return

    # Build source_id → edition lookup for rerank.py path
    src_edition: dict[str, str] = {}
    for s in sources:
        country = (s.get("country", "") or "").upper()
        ed_val = COUNTRY_EDITION_MAP.get(country, "world")
        for key_field in ("db_id", "id"):
            key = s.get(key_field, "")
            if key:
                src_edition[key] = ed_val

    def _get_article_ed(article: dict) -> str:
        """Resolve an article's edition."""
        if get_article_edition in ("section", "auto"):
            sec = article.get("section", "")
            if sec:
                return sec
        if get_article_edition in ("source_lookup", "auto"):
            return src_edition.get(article.get("source_id", ""), "world")
        return "world"

    # Initialize edition ranks from headline_rank
    for c in clusters:
        base = c.get("headline_rank", 0)
        for ed in EDITIONS:
            c[f"rank_{ed}"] = base

    # --- Story-type gates ---
    for c in clusters:
        st = c.get("story_type")
        if st and st in STORY_TYPE_GATES:
            mult = STORY_TYPE_GATES[st]
            for ed in EDITIONS:
                c[f"rank_{ed}"] = round(c[f"rank_{ed}"] * mult, 2)

    # --- Regional affinity + local-priority boost ---
    for c in clusters:
        c_sections = c.get("sections") or [c.get("section", "world")]
        c_articles = c.get("articles") or []

        for ed in ("us", "europe", "south-asia"):
            if ed not in c_sections:
                continue

            # 1. Regional affinity boost
            if c_articles:
                regional_count = sum(
                    1 for a in c_articles if _get_article_ed(a) == ed
                )
                total = len(c_articles)
                if total > 0:
                    affinity = regional_count / total

                    # Low-affinity demotion: stray articles (e.g., one Pakistani
                    # wire picking up a White Sox story)
                    if affinity < LOW_AFFINITY_THRESHOLD and regional_count <= 1:
                        c[f"rank_{ed}"] = round(
                            c[f"rank_{ed}"] * LOW_AFFINITY_DEMOTION, 2
                        )
                    else:
                        affinity_mult = (
                            1.0 + (AFFINITY_MAX_BOOST - 1.0) * affinity
                        )
                        # Quality cap: proportional to source count
                        _sc = c.get("source_count", 0)
                        if _sc < AFFINITY_QUALITY_CAP_SOURCES:
                            _cap = 1.0 + (
                                _sc / AFFINITY_QUALITY_CAP_SOURCES
                            ) * (AFFINITY_MAX_BOOST - 1.0)
                            affinity_mult = min(affinity_mult, _cap)
                        c[f"rank_{ed}"] = round(
                            c[f"rank_{ed}"] * affinity_mult, 2
                        )

            # 2. Local-priority boost — only for edition-exclusive stories
            # with enough sources to be credible
            if "world" not in c_sections:
                _sc = c.get("source_count", 0)
                if _sc >= LOCAL_PRIORITY_MIN_SOURCES:
                    c[f"rank_{ed}"] = round(
                        c[f"rank_{ed}"] * LOCAL_EXCLUSIVE_BOOST, 2
                    )
            else:
                c[f"rank_{ed}"] = round(
                    c[f"rank_{ed}"] * LOCAL_CROSSLIST_BOOST, 2
                )

    # --- Regional content keyword boost ---
    for c in clusters:
        title_lower = (c.get("title", "") or "").lower()
        for ed, keywords in REGIONAL_KEYWORDS.items():
            if any(kw in title_lower for kw in keywords):
                current = c.get(f"rank_{ed}", 0)
                c[f"rank_{ed}"] = round(current * 1.15, 2)

    # --- World multi-edition boost ---
    for c in clusters:
        c_sections = c.get("sections") or [c.get("section", "world")]
        if "world" in c_sections:
            edition_count = sum(1 for ed in EDITIONS if ed in c_sections)
            if edition_count >= 3:
                c["rank_world"] = round(
                    c["rank_world"] * WORLD_MULTI_ED_BOOST, 2
                )

    # --- Cross-edition demotion + lead gate + backfill ---
    claimed_ids: set[str] = set()
    for ed in EDITIONS:
        pool = [
            c for c in clusters
            if ed in (c.get("sections") or [c.get("section", "world")])
        ]
        if not pool:
            continue

        # Demote stories already claimed by a previous edition
        for c in pool:
            cid = c.get("id", "") or c.get("_db_id", "")
            if cid in claimed_ids:
                c_sections = c.get("sections") or [c.get("section", "world")]
                edition_count = sum(1 for e in EDITIONS if e in c_sections)
                src_count = c.get("source_count", 0)

                if (src_count >= GLOBAL_SIG_SOURCES
                        and edition_count >= GLOBAL_SIG_EDITIONS):
                    c[f"rank_{ed}"] = round(
                        c[f"rank_{ed}"] * GLOBAL_SIG_DEMOTION, 2
                    )
                else:
                    c[f"rank_{ed}"] = round(
                        c[f"rank_{ed}"] * CROSS_DEMOTION, 2
                    )

        pool.sort(key=lambda c: c.get(f"rank_{ed}", 0), reverse=True)

        # --- Same-event cap ---
        if len(pool) > TOP_N:
            event_counts: dict[str, int] = {}
            event_promoted: list[dict] = []
            event_deferred: list[dict] = []

            for c in pool:
                title = (c.get("title", "") or "").lower()
                event = _detect_event(title)
                if event and event_counts.get(event, 0) >= MAX_SAME_EVENT:
                    event_deferred.append(c)
                else:
                    event_promoted.append(c)
                    if event:
                        event_counts[event] = event_counts.get(event, 0) + 1

            for c in event_deferred:
                c[f"rank_{ed}"] = round(
                    c[f"rank_{ed}"] * EVENT_DECAY, 2
                )

            pool[:] = event_promoted + event_deferred
            if event_deferred:
                print(
                    f"  Event diversity ({ed}): demoted "
                    f"{len(event_deferred)} stories exceeding same-event "
                    f"cap (max {MAX_SAME_EVENT})"
                )

        # --- Topic diversity: soft-news max 1, others max 2 ---
        if len(pool) > TOP_N:
            promoted: list[dict] = []
            deferred: list[dict] = []
            cat_counts: dict[str, int] = {}

            for c in pool:
                if len(promoted) >= TOP_N:
                    deferred.append(c)
                    continue
                cat = c.get("category", "general")
                cat_limit = (
                    MAX_SAME_CAT_SOFT if cat in _SOFT_CATS
                    else MAX_SAME_CAT_DEFAULT
                )
                if cat_counts.get(cat, 0) < cat_limit:
                    promoted.append(c)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                else:
                    deferred.append(c)

            while len(promoted) < TOP_N and deferred:
                promoted.append(deferred.pop(0))

            final_order = promoted + deferred
            # 0.1pt spacing to prevent ties
            if final_order and len(promoted) >= 2:
                for j in range(1, len(promoted)):
                    if (promoted[j].get(f"rank_{ed}", 0)
                            >= promoted[j - 1].get(f"rank_{ed}", 0)):
                        promoted[j][f"rank_{ed}"] = round(
                            promoted[j - 1].get(f"rank_{ed}", 0) - 0.1, 2
                        )
            pool[:] = final_order

        # --- Edition lead gate ---
        eligible = [
            c for c in pool if c.get("source_count", 0) >= ED_LEAD_MIN
        ]
        ineligible = [
            c for c in pool if c.get("source_count", 0) < ED_LEAD_MIN
        ]
        if len(eligible) >= ED_LEAD_SLOTS and ineligible:
            floor_rank = (
                eligible[ED_LEAD_SLOTS - 1].get(f"rank_{ed}", 0) - 0.1
            )
            for c in ineligible:
                if c.get(f"rank_{ed}", 0) > floor_rank:
                    c[f"rank_{ed}"] = round(floor_rank, 2)
                    floor_rank -= 0.1
        pool[:] = eligible[:ED_LEAD_SLOTS]
        remaining = eligible[ED_LEAD_SLOTS:] + ineligible
        remaining.sort(
            key=lambda c: c.get(f"rank_{ed}", 0), reverse=True
        )
        pool.extend(remaining)

        # --- Thin-edition backfill ---
        if ed != "world":
            quality_count = sum(
                1 for c in pool[:BACKFILL_TARGET]
                if c.get("headline_rank", 0) >= BACKFILL_QUALITY_FLOOR
            )
            if quality_count < BACKFILL_TARGET:
                pool_ids = {
                    c.get("id", "") or c.get("_db_id", "")
                    for c in pool
                }
                world_pool = [
                    c for c in clusters
                    if "world" in (
                        c.get("sections") or [c.get("section", "world")]
                    )
                    and (c.get("id", "") or c.get("_db_id", ""))
                        not in pool_ids
                    and c.get("headline_rank", 0) >= BACKFILL_QUALITY_FLOOR
                    and c.get("source_count", 0) >= BACKFILL_SOURCE_MIN
                ]
                world_pool.sort(
                    key=lambda c: c.get("headline_rank", 0), reverse=True
                )
                backfill_needed = BACKFILL_TARGET - quality_count
                for wc in world_pool[:backfill_needed]:
                    wc[f"rank_{ed}"] = wc.get("headline_rank", 0)
                    pool.append(wc)
                pool.sort(
                    key=lambda c: c.get(f"rank_{ed}", 0), reverse=True
                )
                actual = min(backfill_needed, len(world_pool))
                if actual > 0:
                    print(
                        f"  Thin-edition backfill ({ed}): "
                        f"imported {actual} world stories"
                    )

        # Claim this edition's top stories
        for c in pool[:CROSS_EDITION_TOP]:
            cid = c.get("id", "") or c.get("_db_id", "")
            if cid:
                claimed_ids.add(cid)

    # --- Report overlap ---
    _section_top: dict[str, list[str]] = {}
    for ed in EDITIONS:
        pool = [
            c for c in clusters
            if ed in (c.get("sections") or [c.get("section", "world")])
        ]
        pool.sort(key=lambda c: c.get(f"rank_{ed}", 0), reverse=True)
        _section_top[ed] = [
            c.get("id", "") or c.get("_db_id", "")
            for c in pool[:10]
        ]

    def _overlap(a: str, b: str, n: int) -> int:
        return len(
            set(_section_top.get(a, [])[:n])
            & set(_section_top.get(b, [])[:n])
        )

    print(f"\n  Edition-unique ranks (v6.0).")
    print(
        f"  Top-5 overlap: "
        f"world/us={_overlap('world', 'us', 5)}, "
        f"world/eu={_overlap('world', 'europe', 5)}, "
        f"world/sa={_overlap('world', 'south-asia', 5)}, "
        f"us/eu={_overlap('us', 'europe', 5)}, "
        f"us/sa={_overlap('us', 'south-asia', 5)}, "
        f"eu/sa={_overlap('europe', 'south-asia', 5)}"
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_event(title: str) -> str | None:
    """Return event key if title matches a known event, else None."""
    for event_key, keywords in EVENT_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return event_key
    return None
