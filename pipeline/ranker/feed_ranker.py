"""Single-feed ordering layer for void --news.

Replaces edition_ranker.py (2026-06-02 collapse-editions).

The pipeline ships ONE daily feed. There are no editions to balance — no
us/europe/south-asia/world claim-and-demote dance, no cross-edition lead
gates, no regional keyword boosts, no backfill from "world" into thin
regional editions. All that machinery was removed.

What survives is the only thing the feed actually needs:
    rank_world = headline_rank
                 × STORY_TYPE_GATES (incremental_update / ceremonial / entertainment)
                 × OPINION_GATE
                 × editorial-importance nudge (Gemini 1-10, ±3%/point clamped)
                 × same-event cap (MAX_SAME_EVENT events get decayed)
                 × near-duplicate story guard (unmerged same-story clusters)
                 × topic-diversity tie-breaking

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

# Gemini's per-cluster editorial_importance (1-10, from 7b/8d) nudges rank.
# 2026-07-05 regression: a 26-source bridge-fire spectacle (ei=5) led the
# feed over the 69-source Khamenei funeral (ei=6) and the SCOTUS ruling
# (ei=8) because velocity/recency outweighed breadth and the ranker ignored
# the model's own judgment. Deliberately a NUDGE, not a takeover: +/-3% per
# point around the pivot, clamped, so an uncalibrated per-cluster score can
# reorder near-ties but cannot bury a heavily-covered story.
EDITORIAL_IMPORTANCE_PIVOT = 6
EDITORIAL_IMPORTANCE_WEIGHT = 0.03
EDITORIAL_IMPORTANCE_CLAMP = (0.88, 1.12)

# Near-duplicate story guard — clustering occasionally ships the SAME story
# as two clusters (2026-07-05: the transgender-ruling story sat at #3 AND #4;
# the Khamenei funeral split twice on 07-04/05). The same-event cap allows 2
# per event by design (two ANGLES are fine), so it cannot catch a true
# duplicate. Among the top NEAR_DUP_SCAN clusters, when two titles share
# >= 4 Porter-stemmed content words (or >= 3 covering >= 65% of the shorter
# title), the lower-sourced cluster is decayed below the leader.
#
# Window = the full displayed feed (50). At 25 a duplicate whose second telling
# fell below the fold went uncaught: 2026-08-04 shipped "25 States Sue Trump
# Administration Over Global Tariffs" at #3 AND "25 States Sue Trump Over New
# Tariffs, Citing Illegality" at #38 (5 shared content stems, well past the
# HARD floor) because #38 sat outside the 25-row scan. The guard already keeps
# the higher-sourced telling and requires >= 4 shared content stems (stopwords
# excluded), so widening to 50 catches split duplicates without new false
# positives — a 4-content-word title collision between unrelated stories is rare
# and the demotion always favours the broader-sourced cluster regardless of rank.
NEAR_DUP_SCAN = 50
NEAR_DUP_DECAY = 0.72
NEAR_DUP_SHARED_HARD = 4
NEAR_DUP_SHARED_SOFT = 3
NEAR_DUP_CONTAINMENT = 0.65

# Dynamic same-event cap on a shared DISTINCTIVE (salient) title token.
# The static EVENT_KEYWORDS cap and the stem-overlap near-dup guard (3.6)
# both miss a live event whose clusters name the same place/actor but frame
# it with entirely different words, so no pair clears >=4 shared stems and
# most pairs share <2 stems. 2026-08 live front page: the Ceuta/Morocco
# migration story fragmented into FIVE top cards — "Spain Returns Migrants
# to Morocco", "Ceuta Migrant Death Toll Rises to 72", "Minister Blames
# Israel for Ceuta Migrant Surge", "EU Chief Urges Border Action After
# Ceuta" — glued only by the anchor "ceuta" (in 3 of them) and the topic
# "migrant" (in 3 of them). Wildfire and Ukraine-drone stories fragment the
# same way. When a SALIENT stem (a title stem that is NOT a generic country,
# leader, institution, or wire word) appears in >= DYN_EVENT_MIN_CLUSTERS of
# the top scan, those clusters are treated as one event: the MAX_SAME_EVENT
# most-sourced survive undecayed, the rest decay below them. Grouping is
# PER-TOKEN and never transitively unioned across tokens, so one anchor can
# only reach the clusters that literally name it — an unrelated story cannot
# be chained in. Pure ranking demotion: no cluster is merged, so
# MERGE_HARD_CEILING and every clustering fixture are untouched.
DYN_EVENT_MIN_CLUSTERS = 3
DYN_EVENT_DECAY = 0.72
DYN_EVENT_MIN_STEM_LEN = 3

# Generic geopolitical / institutional / role / wire words that name WHERE or
# WHO but never WHICH event. Removed before a stem is allowed to anchor a
# dynamic event group, so "spain" / "israel" / "minister" / "united" cannot
# bridge two unrelated stories; only a distinctive locus ("ceuta", "drone")
# survives to anchor. Stemmed lazily with clustering's Porter stemmer so the
# set aligns with _title_word_stems output. Over-inclusion here only makes
# anchoring MORE conservative (the safe direction).
_GENERIC_EVENT_WORDS = frozenset({
    # countries / demonyms / capitals / blocs
    "us", "usa", "america", "american", "uk", "britain", "british", "england",
    "english", "europe", "european", "eu", "un", "nato", "brics", "opec",
    "russia", "russian", "moscow", "kremlin", "ukraine", "ukrainian", "kyiv",
    "kiev", "china", "chinese", "beijing", "taiwan", "taipei",
    "israel", "israeli", "palestinian", "palestine",
    "iran", "iranian", "tehran", "spain", "spanish", "madrid", "france",
    "french", "paris", "germany", "german", "berlin", "italy", "italian",
    "rome", "india", "indian", "delhi", "japan", "japanese", "tokyo", "korea",
    "korean", "pakistan", "turkey", "turkish", "morocco", "moroccan", "egypt",
    "egyptian", "saudi", "brazil", "brazilian", "mexico", "mexican", "africa",
    "african", "asia", "asian", "canada", "canadian", "australia", "australian",
    # leaders / roles / titles
    "trump", "biden", "putin", "modi", "netanyahu", "zelensky", "zelenskyy",
    "starmer", "macron", "president", "minister", "premier", "chancellor",
    "secretary", "chief", "official", "officials", "leader", "leaders",
    "government", "governments", "spokesman", "lawmaker", "lawmakers",
    "senator", "governor", "mayor", "envoy", "ambassador",
    # institutions / generic bodies
    "united", "nations", "nation", "state", "states", "congress", "senate",
    "parliament", "court", "house", "white", "council", "commission",
    "committee", "ministry", "agency", "department", "administration",
    "authority", "authorities", "police", "military", "army", "forces",
    "troops",
    # wire / outlet / filler
    "reuters", "afp", "bloomberg", "bbc", "cnn", "press", "news", "report",
    "reports", "world", "global", "international", "national", "latest",
    "update", "updates", "live", "breaking", "today",
})

# Lead-breadth gate — the #1 slot is the front page. A story leads only when
# its outlet breadth is a meaningful share of the day's most-covered story;
# a high-velocity spectacle with a fraction of the coverage waits at #2+
# until verification breadth builds. (2026-07-05: a 26-source bridge fire
# led over a 69-source funeral and a 72-source national anniversary.)
LEAD_BREADTH_FRACTION = 0.45
LEAD_BREADTH_SCAN = 5

# Topic diversity
MAX_SAME_CAT_DEFAULT = 2
MAX_SAME_CAT_SOFT = 1
TOP_N = 10
FEED_CATEGORY_CAP = 12  # cap each category at this across positions TOP_N..FEED_CAP_END
FEED_CAP_END = 50

# Coverage guard on the TOP_N diversity swap (2026-08-06). The category cap can
# defer a 3rd-in-category cluster in favour of a lower-ranked, DIFFERENT-category
# filler purely for variety. That trades verification breadth for monotony
# relief. 2026-08-06 live feed: Diageo cost-cut (economy, sc=17) and an
# extradition (politics, sc=13) were promoted into the top-10 while
# Trump-munitions (general, sc=34) and EU golden-passport (general, sc=31) were
# demoted out. A 13-17-source item must not take a front-page slot from a
# 2x-better-sourced story. The guard: only complete the defer-and-backfill swap
# when the filler's coverage is at least this fraction of the deferred (over-cap)
# story's source_count; if the filler is materially thinner, the better-sourced
# story keeps its top-10 slot even as the 3rd of its category. Anti-monotony is
# preserved for genuinely comparable coverage (filler.sc >= ratio × displaced.sc
# still swaps). Applies to the TOP_N partition ONLY; the tail cap is untouched.
COVERAGE_GUARD_RATIO = 0.6

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
        # Editorial-importance nudge (see constants above).
        ei = c.get("editorial_importance")
        if isinstance(ei, (int, float)) and ei:
            lo, hi = EDITORIAL_IMPORTANCE_CLAMP
            factor = 1.0 + EDITORIAL_IMPORTANCE_WEIGHT * (float(ei) - EDITORIAL_IMPORTANCE_PIVOT)
            c["rank_world"] = round(c["rank_world"] * max(lo, min(hi, factor)), 2)

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

    # 3.6. Near-duplicate story guard (see constants). Runs after the event
    # cap: the cap keeps two ANGLES of one event; this demotes a literal
    # second cluster of the SAME story that clustering failed to merge.
    # The kept cluster is the higher-sourced one (coverage breadth = the
    # canonical telling), mirroring the event cap's canonical anchor.
    _stems = _dup_title_stems_fn()
    if _stems is not None and len(pool) > 2:
        scan = pool[:NEAR_DUP_SCAN]
        stem_sets = [_stems(c.get("title", "") or "") for c in scan]
        demoted: set[int] = set()
        for i in range(len(scan)):
            if i in demoted or len(stem_sets[i]) < 3:
                continue
            for j in range(i + 1, len(scan)):
                if j in demoted or len(stem_sets[j]) < 3:
                    continue
                shared = len(stem_sets[i] & stem_sets[j])
                smaller = min(len(stem_sets[i]), len(stem_sets[j]))
                if shared >= NEAR_DUP_SHARED_HARD or (
                    shared >= NEAR_DUP_SHARED_SOFT
                    and shared / smaller >= NEAR_DUP_CONTAINMENT
                ):
                    # Keep the higher-sourced telling; demote the other.
                    keep, drop = (i, j) if (
                        scan[i].get("source_count", 0) >= scan[j].get("source_count", 0)
                    ) else (j, i)
                    scan[drop]["rank_world"] = round(
                        min(
                            scan[drop].get("rank_world", 0),
                            scan[keep].get("rank_world", 0) * NEAR_DUP_DECAY,
                        ), 2,
                    )
                    scan[drop]["_near_dup_of"] = scan[keep].get("title", "")[:60]
                    demoted.add(drop)
                    if drop == i:
                        break  # the anchor itself was demoted; stop pairing it
        if demoted:
            pool.sort(key=lambda c: c.get("rank_world", 0), reverse=True)

    # 3.7. Dynamic same-event cap (see DYN_EVENT_* constants). Catches the
    # fragmentation the stem-overlap guard misses: clusters that share a
    # distinctive locus but not enough stems. Runs after 3.6 so the two
    # collaborate — 3.6 kills literal re-tellings, 3.7 caps the count of
    # differently-framed angles of one event. Per-token, non-transitive.
    if _stems is not None and len(pool) > TOP_N:
        scan = pool[:NEAR_DUP_SCAN]
        salient_sets = [_salient_title_stems(c.get("title", "") or "") for c in scan]
        token_members: dict[str, list[int]] = {}
        for idx, sset in enumerate(salient_sets):
            for tok in sset:
                token_members.setdefault(tok, []).append(idx)
        capped: set[int] = set()
        for tok, members in token_members.items():
            if len(members) < DYN_EVENT_MIN_CLUSTERS:
                continue
            # Keep the MAX_SAME_EVENT most-sourced (breadth = canonical
            # telling); demote the rest below the lower kept rank.
            ordered = sorted(
                members,
                key=lambda k: (
                    scan[k].get("source_count", 0),
                    scan[k].get("rank_world", 0),
                ),
                reverse=True,
            )
            keeper_floor = min(
                scan[k].get("rank_world", 0) for k in ordered[:MAX_SAME_EVENT]
            )
            for k in ordered[MAX_SAME_EVENT:]:
                target = round(
                    min(
                        scan[k].get("rank_world", 0),
                        keeper_floor * DYN_EVENT_DECAY,
                    ), 2,
                )
                if target < scan[k].get("rank_world", 0):
                    scan[k]["rank_world"] = target
                    scan[k].setdefault("_same_event_anchor", tok)
                    capped.add(k)
        if capped:
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
        overcap_deferred: list[dict] = []  # deferred purely by the category cap
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
                # Over-cap while top-10 slots still remained: this cluster is
                # being displaced by a lower-ranked, different-category filler.
                deferred.append(c)
                overcap_deferred.append(c)

        # 4a. Coverage guard (COVERAGE_GUARD_RATIO). Runs only when the forward
        # pass filled all TOP_N slots, so at least one over-cap cluster was
        # actually displaced by a lower-ranked filler. For each such displaced
        # story (best-ranked first), the marginal filler is the lowest-ranked
        # promoted cluster. If that filler is materially thinner than the
        # displaced story, reclaim the slot: keep the better-sourced over-cap
        # story even though it is the 3rd of its category. When the filler's
        # coverage is comparable (>= ratio × displaced), the swap stands and the
        # anti-monotony diversity treatment is preserved.
        if overcap_deferred and len(promoted) >= TOP_N:
            swapped = False
            for d in sorted(
                overcap_deferred,
                key=lambda c: c.get("rank_world", 0),
                reverse=True,
            ):
                if not promoted:
                    break
                filler = promoted[-1]  # lowest-ranked promoted cluster
                d_sc = d.get("source_count", 0)
                if (
                    filler.get("rank_world", 0) < d.get("rank_world", 0)
                    and filler.get("source_count", 0) < COVERAGE_GUARD_RATIO * d_sc
                ):
                    promoted.pop()
                    deferred.append(filler)
                    promoted.append(d)
                    deferred.remove(d)
                    promoted.sort(
                        key=lambda c: c.get("rank_world", 0), reverse=True
                    )
                    d_cat = d.get("category", "general")
                    f_cat = filler.get("category", "general")
                    cat_counts[d_cat] = cat_counts.get(d_cat, 0) + 1
                    cat_counts[f_cat] = max(0, cat_counts.get(f_cat, 0) - 1)
                    d["_coverage_guard_kept"] = True
                    swapped = True
            if swapped:
                # Restore rank order to the tail so the mid-feed cap and the
                # final strictly-decreasing encoding see a clean ordering.
                deferred.sort(key=lambda c: c.get("rank_world", 0), reverse=True)

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

        # 5. Lead-breadth gate (see constants): if the current #1 lacks
        # breadth, promote the highest-ranked top-5 story that has it.
        if len(pool) >= 10:
            _max_src = max(c.get("source_count", 0) for c in pool[:10])
            _required = LEAD_BREADTH_FRACTION * _max_src
            if pool[0].get("source_count", 0) < _required:
                for k in range(1, min(LEAD_BREADTH_SCAN, len(pool))):
                    if pool[k].get("source_count", 0) >= _required:
                        _lead = pool.pop(k)
                        pool.insert(0, _lead)
                        _lead["rank_world"] = round(
                            pool[1].get("rank_world", 0) + 0.1, 2
                        )
                        break

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

def _dup_title_stems_fn():
    """Lazy accessor for the Phase-3 stemmed-title tokenizer.

    Reuses clustering's Porter stemmer + stopwords so the near-dup guard
    judges titles with exactly the same lens Phase 3 used (and failed
    with) upstream. Returns None when unavailable (guard silently skips —
    ordering still works, just without dup demotion)."""
    global _DUP_STEMS_CACHED
    if _DUP_STEMS_CACHED is _UNSET:
        try:
            from clustering.story_cluster import _title_word_stems
            _DUP_STEMS_CACHED = _title_word_stems
        except Exception:
            _DUP_STEMS_CACHED = None
    return _DUP_STEMS_CACHED


_UNSET = object()
_DUP_STEMS_CACHED = _UNSET
_GENERIC_STEMS_CACHED = _UNSET


def _generic_event_stems() -> frozenset:
    """Porter-stemmed generic-word set (lazy). Stemming with clustering's own
    stemmer keeps the set comparable to _title_word_stems output; falls back
    to the raw words if the stemmer can't be imported."""
    global _GENERIC_STEMS_CACHED
    if _GENERIC_STEMS_CACHED is _UNSET:
        try:
            from clustering.story_cluster import _stem_word
            _GENERIC_STEMS_CACHED = frozenset(
                _stem_word(w) for w in _GENERIC_EVENT_WORDS
            ) | _GENERIC_EVENT_WORDS
        except Exception:
            _GENERIC_STEMS_CACHED = _GENERIC_EVENT_WORDS
    return _GENERIC_STEMS_CACHED


def _salient_title_stems(title: str) -> set[str]:
    """Distinctive title stems: Phase-3 stems minus generic geopolitical /
    institutional / role / wire words. What remains is a locus specific enough
    to anchor a same-event group (e.g. "ceuta", "drone", "wildfir")."""
    stems_fn = _dup_title_stems_fn()
    if stems_fn is None:
        return set()
    generic = _generic_event_stems()
    return {
        s for s in stems_fn(title)
        if len(s) >= DYN_EVENT_MIN_STEM_LEN and s not in generic
    }


def _detect_event(title: str) -> str | None:
    """Return event key if title matches a known event, else None."""
    for event_key, keywords in EVENT_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return event_key
    return None
