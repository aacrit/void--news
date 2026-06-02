"""Single-feed ordering layer for void --news.

Replaces edition_ranker.py (2026-06-02 collapse-editions).

The pipeline ships ONE daily feed. There are no editions to balance — no
us/europe/south-asia/world claim-and-demote dance, no cross-edition lead
gates, no regional keyword boosts, no backfill from "world" into thin
regional editions. All that machinery was removed.

What survives is the only thing the feed actually needs:
    rank_world = headline_rank
                 × STORY_TYPE_GATES (incremental_update / ceremonial)
                 × topic-diversity tie-breaking
                 × same-event cap (MAX_SAME_EVENT events get decayed)

Imported by pipeline/main.py and pipeline/rerank.py.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Configuration — single source of truth
# ---------------------------------------------------------------------------

# Story-type multipliers applied to every cluster's rank.
STORY_TYPE_GATES = {
    "incremental_update": 0.75,
    "ceremonial": 0.82,
}

# Same-event cap — prevents the feed from being dominated by one event.
MAX_SAME_EVENT = 2
EVENT_DECAY = 0.80

# Topic diversity
MAX_SAME_CAT_DEFAULT = 2
MAX_SAME_CAT_SOFT = 1
TOP_N = 10
FEED_CATEGORY_CAP = 12  # cap each category at this across positions TOP_N..FEED_CAP_END
FEED_CAP_END = 50

# Feed lead gate — top positions require this many sources.
FEED_LEAD_MIN = 3
FEED_LEAD_SLOTS = 10


# ---------------------------------------------------------------------------
# Same-event keyword groups (will go stale — TODO: dynamic extraction)
# ---------------------------------------------------------------------------
EVENT_KEYWORDS: dict[str, set[str]] = {
    # summit_diplomacy is checked FIRST (Python dict insertion order) so a
    # "Trump and Xi agree on Hormuz" cluster classifies as a summit event,
    # not an "iran" event. This lets the MAX_SAME_EVENT=2 cap fire across
    # all sub-angles of a single diplomatic summit.
    "summit_diplomacy": {
        "beijing summit", "white house summit", "kremlin summit",
        "trump-xi", "xi-trump", "trump and xi", "xi and trump",
        "trump-putin", "putin-trump", "trump and putin", "putin and trump",
        "trump-modi", "modi-trump", "biden-xi", "xi-biden",
        "g7 summit", "g20 summit", "g-7 summit", "g-20 summit",
        "brics summit", "shanghai cooperation summit", "sco summit",
        "trump arrives in", "xi arrives in", "putin arrives in",
        "trump meets", "xi meets", "putin meets", "modi meets",
        "trump invites", "xi invites",
        "joint statement", "bilateral talks", "trilateral talks",
        "trump-xi summit", "xi-trump summit",
    },
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

_SOFT_CATS: frozenset[str] = frozenset({
    "sports", "entertainment", "culture", "lifestyle",
    "celebrity", "music", "film", "television", "gaming",
})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_feed_ordering(clusters: list[dict], sources: list[dict] | None = None) -> None:
    """Compute rank_world on every cluster in-place.

    Pipeline:
      1. Initialize rank_world = headline_rank.
      2. Apply STORY_TYPE_GATES.
      3. Same-event cap: if more than MAX_SAME_EVENT clusters share an event
         keyword group, the excess get rank_world × EVENT_DECAY.
      4. Topic-diversity tie-breaking on the top TOP_N positions, then a
         FEED_CATEGORY_CAP for positions TOP_N..FEED_CAP_END.
      5. Feed-lead gate: clusters with source_count < FEED_LEAD_MIN cannot
         appear in the top FEED_LEAD_SLOTS slots.

    The `sources` parameter is accepted for back-compat with the old
    edition_ranker signature but is no longer used — single-feed mode
    derives all signals from cluster fields alone.
    """
    if not clusters:
        return

    # 1. Initialize rank_world from headline_rank.
    for c in clusters:
        c["rank_world"] = round(float(c.get("headline_rank", 0) or 0), 2)

    # 2. Story-type gates.
    for c in clusters:
        st = c.get("story_type")
        if st and st in STORY_TYPE_GATES:
            c["rank_world"] = round(c["rank_world"] * STORY_TYPE_GATES[st], 2)

    # Sort by current rank.
    pool = sorted(clusters, key=lambda c: c.get("rank_world", 0), reverse=True)

    # 3. Same-event cap.
    if len(pool) > TOP_N:
        event_counts: dict[str, int] = {}
        for c in pool:
            title = (c.get("title", "") or "").lower()
            event = _detect_event(title)
            if event:
                if event_counts.get(event, 0) >= MAX_SAME_EVENT:
                    c["rank_world"] = round(c["rank_world"] * EVENT_DECAY, 2)
                else:
                    event_counts[event] = event_counts.get(event, 0) + 1
        pool.sort(key=lambda c: c.get("rank_world", 0), reverse=True)

    # 4. Topic diversity on top N.
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
                MAX_SAME_CAT_SOFT if cat in _SOFT_CATS else MAX_SAME_CAT_DEFAULT
            )
            if cat_counts.get(cat, 0) < cat_limit:
                promoted.append(c)
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            else:
                deferred.append(c)

        while len(promoted) < TOP_N and deferred:
            promoted.append(deferred.pop(0))

        # Mid-feed category cap for positions TOP_N..FEED_CAP_END.
        mid_promoted: list[dict] = []
        mid_deferred: list[dict] = []
        mid_cat_counts: dict[str, int] = dict(cat_counts)
        slots_remaining = max(0, FEED_CAP_END - TOP_N)

        for c in deferred:
            cat = c.get("category", "general")
            if (
                len(mid_promoted) < slots_remaining
                and mid_cat_counts.get(cat, 0) < FEED_CATEGORY_CAP
            ):
                mid_promoted.append(c)
                mid_cat_counts[cat] = mid_cat_counts.get(cat, 0) + 1
            else:
                mid_deferred.append(c)

        # 0.1pt spacing on the top-N tier so reorder survives the float sort.
        for j in range(1, len(promoted)):
            if promoted[j].get("rank_world", 0) >= promoted[j - 1].get("rank_world", 0):
                promoted[j]["rank_world"] = round(
                    promoted[j - 1].get("rank_world", 0) - 0.1, 2
                )

        pool = promoted + mid_promoted + mid_deferred

    # 5. Feed-lead gate. Clusters below the source-count floor cannot sit in
    # the top FEED_LEAD_SLOTS positions when enough eligible clusters exist.
    eligible = [c for c in pool if c.get("source_count", 0) >= FEED_LEAD_MIN]
    ineligible = [c for c in pool if c.get("source_count", 0) < FEED_LEAD_MIN]
    if len(eligible) >= FEED_LEAD_SLOTS and ineligible:
        floor_rank = max(
            0.0, eligible[FEED_LEAD_SLOTS - 1].get("rank_world", 0) - 0.1
        )
        for c in ineligible:
            if c.get("rank_world", 0) > floor_rank:
                c["rank_world"] = round(floor_rank, 2)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _detect_event(title: str) -> str | None:
    """Return event key if title matches a known event, else None."""
    for event_key, keywords in EVENT_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return event_key
    return None
