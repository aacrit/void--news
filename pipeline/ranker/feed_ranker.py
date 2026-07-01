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
# entertainment (sports results, celebrity items) is soft news and must not
# occupy premium hard-news slots; Gemini tags it as story_type="entertainment",
# which is reliable even when the category vote mislabels it (2026-06-28, O7).
STORY_TYPE_GATES = {
    "incremental_update": 0.75,
    "ceremonial": 0.82,
    "entertainment": 0.78,
}

# Opinion / op-ed demotion. Opinion columns are not reporting and should sit
# below hard news. Applied in addition to the story-type gate. (2026-06-28, O7)
OPINION_GATE = 0.70

# Detects an "Opinion |" / "| Opinion" / "Opinion:" section label in a headline.
# Requires a separator after the word so "opinion poll shows..." is NOT matched.
import re as _re
_OPINION_TITLE_RE = _re.compile(r"\bopinion\s*[|:]|\|\s*opinion\b", _re.IGNORECASE)

# Tabloid / editorial framing that RSS-stripped content_type misses (2026-07-01
# top-50 review BIAS-01): a scare-quote label lead ("'What a loser': Biden
# blasts...", "'Morning Joe' Accuses...") or an unambiguous roast phrase marks a
# piece as opinion/tabloid rather than straight reporting, even when every
# /opinion/ URL marker was stripped upstream. Deliberately CONSERVATIVE — it
# requires a scare-quote label or a strong roast phrase, so ordinary news verbs
# ("court blasts ruling") do not trip it.
_TABLOID_TITLE_RE = _re.compile(
    r"^\s*['\"‘“].{1,45}['\"’”]\s*[:,]"        # leading scare-quote label lead
    r"|\b(?:scathing takedown|gets? savaged|claps? back|eviscerat\w+|"
    r"torches|rages? (?:at|over)|rips into|goes off on|unloads on|"
    r"melts? down|roasted (?:for|over)|owns? (?:the )?libs)\b",
    _re.IGNORECASE,
)


def _is_opinion(cluster: dict) -> bool:
    """True when a cluster is an opinion column rather than reporting.

    Reads content_type first; falls back to an "Opinion |" headline label
    because content_type is a member-average that an over-merged cluster can
    dilute to "reporting" even when its seed article is an op-ed. Also catches
    scare-quote / roast tabloid framing that has no /opinion/ marker."""
    if (cluster.get("content_type") or "").lower() == "opinion":
        return True
    title = cluster.get("title", "") or ""
    return bool(_OPINION_TITLE_RE.search(title) or _TABLOID_TITLE_RE.search(title))

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
      3.5. Feed-lead gate: clusters with source_count < FEED_LEAD_MIN cannot
         appear in the top FEED_LEAD_SLOTS slots. Runs BEFORE the diversity
         partition so a post-partition eviction can't backfill the top 10
         with over-cap categories.
      4. Topic-diversity partition on the top TOP_N positions, then a
         FEED_CATEGORY_CAP for positions TOP_N..FEED_CAP_END; the final pool
         order is encoded into strictly-decreasing rank_world.

    The `sources` parameter is accepted for back-compat with the old
    edition_ranker signature but is no longer used — single-feed mode
    derives all signals from cluster fields alone.
    """
    if not clusters:
        return

    # 1. Initialize rank_world from headline_rank.
    for c in clusters:
        c["rank_world"] = round(float(c.get("headline_rank", 0) or 0), 2)

    # 2. Story-type + editorial gates.
    for c in clusters:
        st = c.get("story_type")
        if st and st in STORY_TYPE_GATES:
            c["rank_world"] = round(c["rank_world"] * STORY_TYPE_GATES[st], 2)
        # Opinion columns are demoted below hard news (O7). Kept separate from
        # the story-type gate so a future opinion story_type still composes.
        if _is_opinion(c):
            c["rank_world"] = round(c["rank_world"] * OPINION_GATE, 2)

    # Sort by current rank.
    pool = sorted(clusters, key=lambda c: c.get("rank_world", 0), reverse=True)

    # 3. Same-event cap. Keep MAX_SAME_EVENT clusters per event undeacyed; decay
    #    the rest by EVENT_DECAY. The kept set is the CANONICAL (most-sourced)
    #    cluster plus the next highest-ranked siblings. (2026-06-28, O8)
    #    Previously the cap kept the first MAX_SAME_EVENT in rank order, which
    #    decayed the comprehensive 75-source Iran-war cluster to ~#35 while a
    #    narrow 24-source framing led at #2. Anchoring the kept set on the
    #    richest cluster ensures the "biggest story" version is the one that
    #    survives. Same number of clusters decayed as before (no extra
    #    suppression), only a better choice of which survive.
    if len(pool) > TOP_N:
        groups: dict[str, list[dict]] = {}
        for c in pool:
            event = _detect_event((c.get("title", "") or "").lower())
            if event:
                groups.setdefault(event, []).append(c)
        for members in groups.values():
            if len(members) <= MAX_SAME_EVENT:
                continue
            canonical = max(members, key=lambda c: c.get("source_count", 0))
            keep_ids = {id(canonical)}
            for c in sorted(members, key=lambda c: c.get("rank_world", 0), reverse=True):
                if len(keep_ids) >= MAX_SAME_EVENT:
                    break
                keep_ids.add(id(c))
            for c in members:
                if id(c) not in keep_ids:
                    c["rank_world"] = round(c["rank_world"] * EVENT_DECAY, 2)
        pool.sort(key=lambda c: c.get("rank_world", 0), reverse=True)

    # 3.5. Feed-lead gate — BEFORE the diversity partition. Clusters below
    # the source-count floor cannot sit in the top FEED_LEAD_SLOTS positions
    # when enough eligible clusters exist. Running this gate after the
    # partition (as it used to) let the diversity pass promote a thin
    # cluster into the top 10, evict it here, and backfill the vacated slot
    # with a deferred same-category cluster — silently busting the category
    # cap. Clamping first means the partition only ever sees an
    # already-gated ordering. (When fewer than FEED_LEAD_SLOTS eligible
    # clusters exist, thin clusters may still reach the top 10 by design.)
    eligible = [c for c in pool if c.get("source_count", 0) >= FEED_LEAD_MIN]
    ineligible = [c for c in pool if c.get("source_count", 0) < FEED_LEAD_MIN]
    if len(eligible) >= FEED_LEAD_SLOTS and ineligible:
        floor_rank = max(
            0.0, eligible[FEED_LEAD_SLOTS - 1].get("rank_world", 0) - 0.1
        )
        for c in ineligible:
            if c.get("rank_world", 0) > floor_rank:
                c["rank_world"] = round(floor_rank, 2)
        pool.sort(key=lambda c: c.get("rank_world", 0), reverse=True)

    # 4. Topic diversity on top N. The partition must enforce the lead gate
    # itself: it defers over-cap clusters and reaches deeper into the pool,
    # so the rank clamp from 3.5 alone can't keep thin clusters out of the
    # promoted tier (a clamped thin cluster can still outrank the deeper
    # eligible candidates the partition falls through to).
    if len(pool) > TOP_N:
        gate_active = (
            sum(1 for c in pool if c.get("source_count", 0) >= FEED_LEAD_MIN)
            >= FEED_LEAD_SLOTS
        )
        promoted: list[dict] = []
        deferred: list[dict] = []
        cat_counts: dict[str, int] = {}

        for c in pool:
            if len(promoted) >= TOP_N:
                deferred.append(c)
                continue
            if gate_active and c.get("source_count", 0) < FEED_LEAD_MIN:
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

        # Backfill to TOP_N from deferred, eligible clusters first so the
        # lead gate survives the over-cap fallback; thin clusters only if
        # eligible ones run out.
        while len(promoted) < TOP_N and deferred:
            pick = next(
                (i for i, c in enumerate(deferred)
                 if not gate_active or c.get("source_count", 0) >= FEED_LEAD_MIN),
                0,
            )
            promoted.append(deferred.pop(pick))

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

        pool = promoted + mid_promoted + mid_deferred

        # Encode the final pool order into rank_world. Every consumer (the
        # DB write, main's diagnostics, the frontend) sorts by rank_world
        # alone, so the partition above only takes effect if ranks are
        # strictly decreasing along the intended order. Without this, the
        # deferred clusters kept their original higher ranks and re-emerged
        # in the top 10 untouched, making both the diversity pass and the
        # mid-feed category cap silent no-ops. Violations only occur at
        # partition boundaries and cascade locally until the natural
        # descending order resumes, so tail granularity is preserved.
        for j in range(1, len(pool)):
            if pool[j].get("rank_world", 0) >= pool[j - 1].get("rank_world", 0):
                pool[j]["rank_world"] = round(
                    pool[j - 1].get("rank_world", 0) - 0.1, 2
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
