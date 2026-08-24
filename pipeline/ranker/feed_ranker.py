"""Single-feed ordering layer for void --news.

Replaces edition_ranker.py (2026-06-02 collapse-editions).

The pipeline ships ONE daily feed. There are no editions to balance — no
us/europe/south-asia/world claim-and-demote dance, no cross-edition lead
gates, no regional keyword boosts, no backfill from "world" into thin
regional editions. All that machinery was removed.

What survives is the only thing the feed actually needs:
    rank_world = headline_rank
                 × OPINION_GATE
                 × same-event cap (MAX_SAME_EVENT events get decayed)
                 × near-duplicate story guard (unmerged same-story clusters)
                 × topic-diversity tie-breaking

2026-08-10 (deterministic-ranking): every LLM-derived ordering signal was
removed from rank_world. The Gemini editorial_importance nudge (Signal A) and
the Gemini story_type gates (incremental_update / ceremonial / entertainment,
Signal B) are gone. Diverse story types now land organically through the
deterministic topic-diversity partition + category caps, and soft news is
demoted by the deterministic soft-news category gate + tabloid gate that live
in importance_ranker (headline_rank), not by an LLM label. rank_world is now a
pure function of the deterministic signals: no clustering, DB schema, or bias
model change accompanies this.

Imported by pipeline/main.py and pipeline/rerank.py.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Configuration — single source of truth
# ---------------------------------------------------------------------------

# Story-type gates (Gemini story_type -> multiplier) were REMOVED on
# 2026-08-10 (deterministic-ranking). The incremental_update / ceremonial /
# entertainment multipliers depended on an LLM label and are gone:
#   - incremental_update mainly mis-ranked decisive one-time outcomes (an
#     election result tagged as an "update"); its net historical effect was a
#     bug, and every genuinely thin/old/slow story is already demoted by the
#     deterministic longevity + thin-cluster penalties in importance_ranker.
#   - ceremonial could not tell a minor gala from a major state funeral, so a
#     flat demotion was as likely to bury real news as soft news.
#   - entertainment is redundant with the deterministic soft-news category gate
#     (importance_ranker, 0.78x for sports/entertainment/culture) + tabloid gate.
# Story-type diversity now emerges from the topic-diversity partition + category
# caps below, not from an LLM tag.

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

# The Gemini editorial_importance multiplicative nudge (Signal A) was REMOVED
# on 2026-08-10 (deterministic-ranking). An uncalibrated per-cluster LLM score
# no longer touches rank_world; editorial prominence is carried entirely by the
# deterministic coverage / maturity / authority / consequentiality signals in
# importance_ranker's headline_rank.

# Near-duplicate story guard — clustering occasionally ships the SAME story
# as two clusters (2026-07-05: the transgender-ruling story sat at #3 AND #4;
# the Khamenei funeral split twice on 07-04/05). The same-event cap allows 2
# per event by design (two ANGLES are fine), so it cannot catch a true
# duplicate. Among the top NEAR_DUP_SCAN clusters, when two titles share
# >= 4 Porter-stemmed content words (HARD), or >= 3 covering >= 65% of the
# shorter title (SOFT), the lower-sourced cluster is decayed below the leader.
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
#
# SPECIFIC-STEM widening (2026-08-06): the HARD/SOFT floors are tuned for long
# titles and missed short same-story pairs that share only 2-3 words. 2026-08-06
# shipped "Michigan Democratic Primaries See 'Uncommitted' Founder Win" (#7,
# sc=34) AND "Progressive El-Sayed Wins Michigan Senate Primary" (#29, sc=75) —
# the SAME race — because they share only {michigan, primari, win} = 3 stems, one
# of which ("win") is a common outcome verb, so the SOFT rule's 65% containment
# was not met and HARD needs 4. Two Ukraine oil-refinery strikes (#1/#44) split
# the same way on {drone, refineri}. New rule: collapse when a pair shares >= 3
# raw stems AND >= NEAR_DUP_SPECIFIC_MIN of them are SPECIFIC (high-IDF: a
# distinctive locus/entity/topic — NOT a generic country/role/wire word and NOT
# a common reporting/action verb). "michigan"+"primari" are specific; "sign",
# "order", "win", "say", "new" are not, so two DIFFERENT Trump stories that both
# "sign an order" cannot collide. Over-collapse guard: the widened rule is
# blocked when the two titles name DIFFERENT elective offices (Senate vs
# Governor), so two distinct races in the same state (which share {state,
# primari, win} identically to a genuine dup) stay separate. The HARD/SOFT rules
# on RAW stems are untouched, so nothing that collapsed before stops collapsing.
# Scan the FULL working pool, not just the top 50. apply_feed_ordering fetches
# the top 80 (main.py step 8d.5) and mutates rank_world in-place across its earlier
# stages (story-type gates, same-event cap), which reorders the pool BEFORE the
# near-dup guard runs. A cluster that ends up DISPLAYED (final position <= 50) can
# therefore sit beyond position 50 in the working pool at scan time and escape a
# 50-wide scan. That is exactly why the 2026-08-24 feed shipped both "Humanoid
# Robots Beat Usain Bolt's 100m Record in Beijing" (18 src) and "Humanoid Robots
# Break Human Sprint Records at Beijing Games" (8 src): they share 4 raw stems
# (>= the HARD floor) and the guard WOULD have removed one, but the 8-source
# telling was outside the top 50 of the working pool when 3.6 ran. Widening the
# scan to 80 covers every candidate that can reach the displayed feed. The
# demotion CRITERIA are unchanged (same strict stem test), so no new pair
# collapses that would not have collapsed inside the top 50; this only stops a
# displayed re-telling from slipping through on pool churn.
NEAR_DUP_SCAN = 80
NEAR_DUP_DECAY = 0.72  # retained for reference; near-dups are now REMOVED, not decayed
# Sentinel rank for a near-duplicate re-telling that is REMOVED from the displayed
# feed (Option 1, 2026-08-20). Negative so it sorts strictly below every genuine
# (non-negative) rank_world and the frontend top-N cut drops it. A near-dup that
# was merely decayed x0.72 used to survive in the top 50.
NEAR_DUP_REMOVED_RANK = -1.0
NEAR_DUP_SHARED_HARD = 4
NEAR_DUP_SHARED_SOFT = 3
NEAR_DUP_CONTAINMENT = 0.65
# Widened rule: >= this many of the >= 3 shared raw stems must be SPECIFIC
# (entity/topic, per _specific_title_stems) for a short same-story pair to
# collapse. Two is the floor the task set ("michigan"+"primari" is enough).
NEAR_DUP_SPECIFIC_MIN = 2

# Common reporting / action verbs and vacuous outcome nouns. Stripped (on top of
# the generic geopolitical/role/wire set) before a stem counts as SPECIFIC for
# the widened near-dup rule, so a shared pair of these ("signs ... order",
# "announces ... plan", the task's "say"+"new") can never be the 2 specifics
# that trigger a collapse. Deliberately excludes physically-meaningful words
# (strike, hit, blast, fire, attack, crash) that distinguish real events.
_COMMON_ACTION_WORDS = frozenset({
    "sign", "signs", "signed", "order", "orders", "ordered", "announce",
    "announced", "unveil", "unveils", "unveiled", "reveal", "reveals",
    "revealed", "launch", "launches", "launched", "plan", "plans", "planned",
    "deal", "deals", "move", "moves", "back", "backs", "backed", "call",
    "calls", "called", "urge", "urges", "urged", "vow", "vows", "vowed",
    "warn", "warns", "warned", "set", "sets", "face", "faces", "faced",
    "push", "pushes", "pushed", "seek", "seeks", "sought", "eye", "eyes",
    "eyed", "weigh", "weighs", "weighed", "mull", "mulls", "hail", "hails",
    "hailed", "name", "names", "named", "pick", "picks", "picked", "tap",
    "taps", "meet", "meets", "hold", "holds", "held", "offer", "offers",
    "give", "gives", "get", "gets", "make", "makes", "keep", "keeps", "add",
    "adds", "see", "sees", "win", "wins", "won", "victory", "defeat",
    "elect", "elects", "elected",
})

# Elective-office / contest words. Two titles that each name an office and name
# DIFFERENT ones are distinct contests (Senate primary vs Governor primary), so
# the widened rule is suppressed for that pair even though they share {state,
# primari, win}. A SHARED office (both "Senate") never suppresses. Deliberately
# NOT in _GENERIC_EVENT_WORDS: these are still generic for anchoring, but here
# they carry the discriminating signal that separates two same-state races.
_CONTEST_ANCHOR_WORDS = frozenset({
    "senate", "governor", "gubernatorial", "mayor", "mayoral", "house",
    "presidential", "congressional", "council", "assembly", "parliamentary",
    "ward", "seat",
})

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

# Rank-aware cap correction tolerance (2026-08-10 Phase-2 ranking audit, 1a-Q4).
# The top-10 category cap defers a 3rd-in-category cluster below the fold for
# topic variety, but the deferral (plus the coverage guard reclaiming a slot)
# could stamp a HIGHER-base story below a LOWER-base one with no visible reason:
# 2026-08-10 sat Zelenskyy (base 54.53, 7th-highest base in the feed) at rank 11,
# below Tupac (base 42.62) at rank 10. Diversity is preserved, but a cap deferral
# must never invert the base ordering by more than this many points. A deferred
# story is pulled back up to just above the highest-positioned story it out-bases
# by more than CAP_RANK_TOLERANCE.
CAP_RANK_TOLERANCE = 8.0
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

# Mass-casualty ordering floor (2026-08-11, P0-4). importance_ranker already
# lifts a mass-casualty disaster (DISASTER_MAX_LIFT) on its own merit, but the
# diversity partition + category caps could still sort a well-sourced disaster
# below a lower-base NON-disaster (a 61-source earthquake stranded beneath a
# 37-source product recall). This deterministic guardrail runs AFTER every
# gate/cap and BEFORE the final strictly-decreasing re-encode: a cluster whose
# disaster_severity >= DISASTER_FLOOR_SEVERITY AND source_count >=
# DISASTER_FLOOR_MIN_SOURCES may never be ordered below a non-disaster cluster
# that carries a strictly lower headline_rank; it is repositioned just above the
# highest such cluster (mirrors the 4b CAP_RANK_TOLERANCE reorder). No LLM, no
# weight change — it only surfaces the already-computed disaster_severity signal
# (threaded onto the cluster dict in main.py, persisted via migration 077).
DISASTER_FLOOR_SEVERITY = 60.0
DISASTER_FLOOR_MIN_SOURCES = 8


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
      2. Apply the opinion / tabloid demotion gate (OPINION_GATE).
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

    # 2. Deterministic opinion / tabloid demotion. The Gemini story_type gates
    #    and the editorial_importance nudge were removed on 2026-08-10, so this
    #    is now the ONLY per-cluster multiplier applied here; every other
    #    signal already lives in headline_rank. Opinion columns and scare-quote
    #    tabloid framing sit below hard news (O7); detection is purely
    #    title/content_type based (see _is_opinion), no LLM label involved.
    for c in clusters:
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

    # 3.6. Near-duplicate story guard (see constants). Runs after the event
    # cap: the cap keeps two ANGLES of one event; this demotes a literal
    # second cluster of the SAME story that clustering failed to merge.
    # The kept cluster is the higher-sourced one (coverage breadth = the
    # canonical telling), mirroring the event cap's canonical anchor.
    _stems = _dup_title_stems_fn()
    if _stems is not None and len(pool) > 2:
        scan = pool[:NEAR_DUP_SCAN]
        stem_sets = [_stems(c.get("title", "") or "") for c in scan]
        spec_sets = [_specific_title_stems(c.get("title", "") or "") for c in scan]
        demoted: set[int] = set()
        for i in range(len(scan)):
            if i in demoted or len(stem_sets[i]) < 3:
                continue
            for j in range(i + 1, len(scan)):
                if j in demoted or len(stem_sets[j]) < 3:
                    continue
                shared = len(stem_sets[i] & stem_sets[j])
                smaller = min(len(stem_sets[i]), len(stem_sets[j]))
                # Widened SPECIFIC rule (B): a short same-story pair that shares
                # >= 3 raw stems of which >= NEAR_DUP_SPECIFIC_MIN are specific
                # (entity/topic, not common verbs), UNLESS the two titles name
                # different elective offices (distinct same-state races).
                shared_specific = len(spec_sets[i] & spec_sets[j])
                specific_match = (
                    shared >= NEAR_DUP_SHARED_SOFT
                    and shared_specific >= NEAR_DUP_SPECIFIC_MIN
                    and not _contest_anchor_conflict(stem_sets[i], stem_sets[j])
                )
                if shared >= NEAR_DUP_SHARED_HARD or specific_match or (
                    shared >= NEAR_DUP_SHARED_SOFT
                    and shared / smaller >= NEAR_DUP_CONTAINMENT
                ):
                    # Keep the higher-sourced telling; REMOVE the other from the
                    # displayed feed. Decay (x0.72, the prior behavior) only
                    # reordered the re-telling; a near-dup that started high stayed
                    # in the top 50 after the decay (2026-08-18: a 48-source and a
                    # 35-source telling of the same Korea drill story both shipped,
                    # ranks 2 and 10). A literal second cluster of the same story
                    # adds nothing, so we push it below the display cut with the
                    # NEAR_DUP_REMOVED_RANK sentinel (negative, so it sorts last and
                    # a legitimate non-negative rank never collides).
                    #
                    # KNOWN LIMITATION (see docs/PIPELINE-BRAIN.md): removing the
                    # 35-source telling discards its 35 sources from the coverage
                    # view of the 48-source card, so the surviving headline
                    # UNDERSTATES its own coverage breadth. The correct long-term
                    # answer is MERGING the two clusters upstream (their sources
                    # would combine), not hiding one. Removal is the interim guard;
                    # merging is tracked as the real fix.
                    keep, drop = (i, j) if (
                        scan[i].get("source_count", 0) >= scan[j].get("source_count", 0)
                    ) else (j, i)
                    scan[drop]["rank_world"] = NEAR_DUP_REMOVED_RANK
                    scan[drop]["_near_dup_of"] = scan[keep].get("title", "")[:60]
                    scan[drop]["_near_dup_removed"] = True
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
        # Snapshot the pre-partition rank (all gates/caps/nudges applied, but not
        # yet the diversity encoding) so 4b can measure base-score inversions the
        # cap introduces.
        for c in pool:
            c["_base_rank"] = c.get("rank_world", 0)
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

        # 4b. Rank-aware cap correction (see CAP_RANK_TOLERANCE). The category cap
        # can defer a high-base cluster below a lower-base filler (2026-08-10:
        # Zelenskyy base 54.53 landed at rank 11, below Tupac base 42.62). Topic
        # diversity is otherwise preserved, but such a deferral must not invert
        # the base ordering by more than the tolerance: pull each cap-deferred
        # cluster up to just above the earliest-positioned story it out-bases by
        # more than CAP_RANK_TOLERANCE. Highest-base deferral first so a chain of
        # deferrals resolves top-down. The strictly-decreasing encoding below then
        # re-stamps rank_world along the corrected order.
        still_capped = [c for c in overcap_deferred if c not in promoted]
        for c in sorted(
            still_capped, key=lambda x: x.get("_base_rank", 0), reverse=True
        ):
            try:
                ci = pool.index(c)
            except ValueError:
                continue
            base_c = c.get("_base_rank", c.get("rank_world", 0))
            target = None
            for k in range(ci):
                base_k = pool[k].get("_base_rank", pool[k].get("rank_world", 0))
                if base_c - base_k > CAP_RANK_TOLERANCE:
                    target = k
                    break
            if target is not None:
                pool.pop(ci)
                pool.insert(target, c)

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

        # 5b. Mass-casualty ordering floor (see DISASTER_FLOOR_* constants).
        # Runs AFTER every gate/cap/diversity pass and BEFORE the final
        # strictly-decreasing re-encode. A well-sourced mass-casualty disaster
        # may not sit below a NON-disaster cluster with a strictly lower
        # headline_rank; lift it to just above the highest such cluster.
        # Mirrors the 4b CAP_RANK_TOLERANCE reorder: highest-base disaster
        # first so a chain resolves top-down; pool.index recomputed each pass
        # because a lift shifts positions.
        disasters = [c for c in pool if _qualifies_mass_casualty(c)]
        for c in sorted(
            disasters, key=lambda x: (x.get("headline_rank", 0) or 0), reverse=True
        ):
            try:
                ci = pool.index(c)
            except ValueError:
                continue
            hd = c.get("headline_rank", 0) or 0
            target = None
            for k in range(ci):
                pk = pool[k]
                if not _qualifies_mass_casualty(pk) and (
                    (pk.get("headline_rank", 0) or 0) < hd
                ):
                    target = k
                    break
            if target is not None:
                pool.pop(ci)
                pool.insert(target, c)
                c["_mass_casualty_floor"] = True

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
_COMMON_ACTION_STEMS_CACHED = _UNSET
_CONTEST_ANCHOR_STEMS_CACHED = _UNSET


def _stemmed_word_set(words: frozenset) -> frozenset:
    """Porter-stem a word set with clustering's stemmer (lazy). Falls back to
    the raw words if the stemmer can't be imported. Keeps the union of stemmed
    and raw forms so a match works whichever form a title tokenises to."""
    try:
        from clustering.story_cluster import _stem_word
        return frozenset(_stem_word(w) for w in words) | words
    except Exception:
        return words


def _common_action_stems() -> frozenset:
    global _COMMON_ACTION_STEMS_CACHED
    if _COMMON_ACTION_STEMS_CACHED is _UNSET:
        _COMMON_ACTION_STEMS_CACHED = _stemmed_word_set(_COMMON_ACTION_WORDS)
    return _COMMON_ACTION_STEMS_CACHED


def _contest_anchor_stems() -> frozenset:
    global _CONTEST_ANCHOR_STEMS_CACHED
    if _CONTEST_ANCHOR_STEMS_CACHED is _UNSET:
        _CONTEST_ANCHOR_STEMS_CACHED = _stemmed_word_set(_CONTEST_ANCHOR_WORDS)
    return _CONTEST_ANCHOR_STEMS_CACHED


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


def _specific_title_stems(title: str) -> set[str]:
    """SPECIFIC (high-IDF) title stems for the widened near-dup rule: salient
    stems minus common reporting/action verbs and vacuous outcome nouns. What
    remains is distinctive enough that TWO shared specifics ("michigan" +
    "primari", "drone" + "refineri") mark two clusters as the same story, while
    a shared pair of generic verbs ("signs" + "order", "say" + "new") never
    can."""
    return _salient_title_stems(title) - _common_action_stems()


def _contest_anchor_conflict(stems_a: set[str], stems_b: set[str]) -> bool:
    """True when both titles name an elective office and the offices DIFFER
    (Senate primary vs Governor primary). Signals two distinct contests, so the
    widened near-dup rule is suppressed even when the pair shares {state,
    primari, win}. A shared office (both "Senate") is NOT a conflict."""
    anchors = _contest_anchor_stems()
    oa = stems_a & anchors
    ob = stems_b & anchors
    return bool(oa and ob and not (oa & ob))


def _qualifies_mass_casualty(cluster: dict) -> bool:
    """True when a cluster is a well-sourced mass-casualty disaster that the
    ordering floor protects. Guards against a NULL/absent disaster_severity
    (older DB rows read the column as None, which would raise on `>=`)."""
    return (
        (cluster.get("disaster_severity") or 0) >= DISASTER_FLOOR_SEVERITY
        and (cluster.get("source_count") or 0) >= DISASTER_FLOOR_MIN_SOURCES
    )


def _detect_event(title: str) -> str | None:
    """Return event key if title matches a known event, else None."""
    for event_key, keywords in EVENT_KEYWORDS.items():
        if any(kw in title for kw in keywords):
            return event_key
    return None
