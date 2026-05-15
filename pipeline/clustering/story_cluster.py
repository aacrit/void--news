"""
Story clustering engine for the void --news pipeline.

Five rule-based phases (no tier-conditional caps, no special-case
blacklists outside the explicit editorial pair-list):

    Phase 1:   TF-IDF + agglomerative clustering on (title + first 500 words)
               at distance threshold 1 - STORY_TFIDF_THRESHOLD.
    Phase 2:   IDF-weighted entity-overlap merge — pairs of clusters
               accumulate sum-of-IDF over shared named entities, merging
               when the score crosses ENTITY_MERGE_IDF_THRESHOLD.
    Phase 2.5: Canonical-pair merge — editorial override for known
               co-occurrence pairs (Trump+Xi, Starmer+Streeting, etc).
               Pure surface-form match; bypasses IDF dilution that
               occurs when both names appear in many unrelated stories.
    Phase 3:   Stem-aware title Jaccard merge — Porter-stemmed title-word
               sets that cross TITLE_JACCARD_THRESHOLD merge.
    Phase 4:   Garbage-title force-split — when the title-generator
               produces a "X Spans Y, Z, and W" signature it has been
               forced to mash up unrelated sub-events; we re-cluster the
               articles at a stricter TF-IDF + IDF gate.

Wire-amplification is handled OUTSIDE the cluster topology: every article
arriving here may carry `is_wire_copy` / `wire_origin_publisher_id`
fields set by `deduplicator.deduplicate_articles()`. The final
`source_count` collapses wire copies to their origin publisher and a
companion `wire_amplification` metric (= total_articles / source_count)
records the syndication ratio for downstream ranking.

Uses scikit-learn (TF-IDF, AgglomerativeClustering, cosine_similarity),
spaCy NER (via utils.nlp_shared), and nltk PorterStemmer (with a spaCy
lemma fallback). No LLM API calls.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from utils.nlp_shared import get_nlp


# ---------------------------------------------------------------------------
# Calibrated thresholds — single source of truth for clustering signal
# sensitivity. Tuned 2026-05-15 against the 21-fixture clustering suite.
# ---------------------------------------------------------------------------
STORY_TFIDF_THRESHOLD       = 0.18   # Phase 1 agglomerative cosine cut
ENTITY_MERGE_IDF_THRESHOLD  = 2.0    # Phase 2: sum-of-IDF over shared entities
TITLE_JACCARD_THRESHOLD     = 0.27   # Phase 3: stemmed title Jaccard
MAX_AGE_SPREAD_HOURS        = 48.0   # Time gate (kept for both merge passes)
WIRE_HASH_FINGERPRINT_BYTES = 800    # Phase 0 (in deduplicator): chars hashed
WIRE_LEAD_COSINE            = 0.92   # Phase 0 (in deduplicator): confirm threshold


# ---------------------------------------------------------------------------
# Title cleanup
# ---------------------------------------------------------------------------
# Wire service prefixes: (LEAD), (URGENT), BREAKING:, (3rd LD), etc.
_WIRE_PREFIX_RE = re.compile(
    r"^\s*(?:\((?:LEAD|URGENT|CORRECTED|UPDATE(?:\s*\d*)?|RECASTS?|ADDS?|"
    r"WRAPUP|NEWSALERT|\d+(?:st|nd|rd|th)\s+LD)\)\s*)"
    r"|^\s*(?:WATCH\s*LIVE\s*:|WATCH\s*:|BREAKING\s*:|UPDATE\s*:|EXCLUSIVE\s*:)"
    r"\s*",
    re.IGNORECASE,
)
# Source attribution at end: " - Reuters", " | BBC News", " -- AP", etc.
_ATTRIBUTION_SUFFIX_RE = re.compile(
    r"\s*[-–—|]+\s*"
    r"(?:Reuters|AP\s*News?|Associated\s*Press|CNN|BBC(?:\s*News)?|NPR|PBS"
    r"|Fox\s*News|The\s+[A-Z]\w+(?:\s+[A-Z]\w+)?|[A-Z]\w+\s+News"
    r"|Al\s+Jazeera|Bloomberg|CNBC|ABC\s*News|CBS\s*News|NBC\s*News"
    r"|The\s+Guardian|Washington\s+Post|New\s+York\s+Times|Wall\s+Street\s+Journal"
    r"|Chicago\s+Tribune|UPI|NHK\s+WORLD(?:-JAPAN)?|NHK\s+World"
    r"|Nikkei|Haaretz|South\s+China\s+Morning\s+Post)"
    r"\s*$",
    re.IGNORECASE,
)
_DOMAIN_SUFFIX_RE = re.compile(
    r"\s*[-–—|]+\s*\w+\.(?:com|org|net|co\.uk|or\.jp|co\.jp)\s*$",
    re.IGNORECASE,
)


def _clean_title(title: str) -> str:
    """Strip wire prefixes, source attribution, and junk from a title."""
    title = _WIRE_PREFIX_RE.sub("", title).strip()
    for _ in range(2):
        title = _ATTRIBUTION_SUFFIX_RE.sub("", title).strip()
        title = _DOMAIN_SUFFIX_RE.sub("", title).strip()
    return title.strip(" \t\n\r-–—|")


def _build_document(article: dict) -> str:
    """Build a TF-IDF document from title + first 500 words of full_text."""
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""
    words = full_text.split()[:500]
    body_snippet = " ".join(words)
    return f"{title} {body_snippet}".strip()


# ---------------------------------------------------------------------------
# Cluster title / summary generation
# ---------------------------------------------------------------------------

def _generate_cluster_title(articles: list[dict]) -> str:
    """Pick the most representative headline across articles in a cluster."""
    raw_titles = [a.get("title", "") or "" for a in articles]
    cleaned_titles = [_clean_title(t) for t in raw_titles]
    valid_titles = [t for t in cleaned_titles if len(t) >= 15]

    if not valid_titles:
        nlp = get_nlp()
        ent_counter: Counter = Counter()
        for article in articles[:20]:
            t = article.get("title", "") or ""
            s = article.get("summary", "") or ""
            doc = nlp(f"{t} {s}"[:5000])
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT"):
                    ent_counter[ent.text] += 1
        top = [name for name, _ in ent_counter.most_common(3)]
        return ", ".join(top) if top else "Developing Story"

    if len(valid_titles) == 1:
        return valid_titles[0]

    # Score titles by entity coverage + length sweet spot
    nlp = get_nlp()
    ent_counter: Counter = Counter()
    for article in articles[:20]:
        doc = nlp(article.get("title", "") or "")
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "NORP"):
                ent_counter[ent.text.lower()] += 1
    top_entities = (
        {name for name, c in ent_counter.most_common(5) if c >= 2}
        if ent_counter else set()
    )

    def _score(title: str) -> float:
        score = 0.0
        length = len(title)
        if 40 <= length <= 120:
            score += 3.0
        elif 20 <= length < 40:
            score += 1.5
        elif 120 < length <= 160:
            score += 2.0
        elif length < 20:
            score += 0.5
        if top_entities:
            tl = title.lower()
            score += sum(1 for e in top_entities if e in tl) * 2.0
        if title.endswith("?"):
            score -= 1.0
        if title.isupper():
            score -= 2.0
        if any(w in title.lower() for w in (
                "you won't believe", "shocking", "this is why", "here's what")):
            score -= 1.5
        if ": " in title or " - " in title:
            score += 0.5
        return score

    scored = [(t, _score(t)) for t in valid_titles]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def _generate_cluster_summary(articles: list[dict]) -> str:
    """Pick the longest substantive article summary in a cluster."""
    summaries = []
    for a in articles:
        s = (a.get("summary", "") or "").strip()
        if s and len(s) >= 40:
            summaries.append(s)
    if not summaries:
        for a in articles:
            s = (a.get("summary", "") or "").strip()
            if s and len(s) >= 15:
                summaries.append(s)
    if summaries:
        summaries.sort(key=len, reverse=True)
        return summaries[0]
    for a in articles:
        t = (a.get("title", "") or "").strip()
        if t:
            return t
    return ""


# ---------------------------------------------------------------------------
# Section markers (US vs world fallback for downstream tagging)
# ---------------------------------------------------------------------------
US_MARKERS = {
    "congress", "house of representatives", "white house",
    "capitol hill", "pentagon", "state department",
    "fbi", "cia", "dhs", "fema", "epa", "fda", "sec",
    "federal reserve", "wall street", "medicare", "medicaid",
    "gop", "dnc", "rnc",
    "trump", "biden", "desantis", "pelosi", "mcconnell",
}
INTL_MARKERS = {
    "ukraine", "russia", "china", "eu ", "european union", "nato",
    "middle east", "gaza", "israel", "iran", "north korea", "un ",
    "united nations", "world bank", "imf", "brics",
    "africa", "asia", "latin america", "pacific",
    "india", "japan", "south korea", "taiwan", "syria",
    "saudi arabia", "turkey", "brazil", "mexico",
    "minister", "parliament", "european", "beijing", "moscow",
    "kiev", "kyiv", "jerusalem", "tehran", "kabul",
    "g7", "g20", "world cup", "olympics",
    "prime minister", "chancellor", "monarchy",
    "hong kong", "myanmar", "afghanistan", "iraq", "yemen",
    "sudan", "somalia", "ethiopia", "nigeria", "kenya",
    "australia", "new zealand", "philippines", "indonesia",
    "pakistan", "bangladesh", "sri lanka", "vietnam",
}


def _determine_section(articles: list[dict], cluster_title: str = "",
                       cluster_summary: str = "") -> str:
    """Resolve cluster section via content markers + source-country vote.

    Priority order:
      1. Content markers — strict one-sided wins (us_count >= 4 and
         intl_count == 0  OR  intl_count >= 3 and us_count == 0).
      2. Article-section vote (when fixtures supply pre-tagged sections).
      3. Source-country vote — when most articles come from US-located
         outlets AND content has at least one US marker, classify as US.
         Without the US-marker guard, an AP wire reposted to a UK outlet
         could mis-classify as world for a US-domestic story.
      4. Default to "world" — newsroom safe default for ambiguous content.
    """
    text = f"{cluster_title} {cluster_summary}".lower()
    us_count = sum(1 for m in US_MARKERS if m in text)
    intl_count = sum(1 for m in INTL_MARKERS if m in text)
    if us_count >= 4 and intl_count == 0:
        return "us"
    if intl_count >= 3 and us_count == 0:
        return "world"

    # Source-section vote (when articles carry a `section` field)
    sections: Counter = Counter()
    for article in articles:
        sec = article.get("section", "") or ""
        if sec:
            sections[sec.lower()] += 1
    if sections:
        top = sections.most_common(1)[0][0]
        if top in ("europe", "south-asia"):
            return top
        if any(kw in top for kw in (
                "us", "domestic", "nation", "national", "america")):
            return "us"
        return "world"

    # Source-country fallback: when content markers are inconclusive
    # (no clear one-sided win), defer to source country with two paths:
    #   (a) Any US marker in content + majority-US sources -> us
    #       Catches Trump-led foreign-policy stories that mention Beijing.
    #   (b) ALL sources US-located + zero international markers -> us
    #       Catches NYC city council / SCOTUS / state legislative stories
    #       whose title+summary doesn't hit any US_MARKERS keyword
    #       (Eric Adams / John Roberts / Greg Abbott aren't in the set).
    countries = Counter(
        (a.get("source_country") or a.get("country") or "").upper()
        for a in articles
        if (a.get("source_country") or a.get("country"))
    )
    if countries:
        total = sum(countries.values())
        us_share = countries.get("US", 0) / max(total, 1)
        if us_count >= 1 and us_share >= 0.5:
            return "us"
        if us_share == 1.0 and intl_count == 0:
            return "us"

    return "world"


# ---------------------------------------------------------------------------
# Phase 2: IDF-weighted entity merge
# ---------------------------------------------------------------------------

# Tokens spaCy emits as entities that carry no merge signal. Kept tight —
# the IDF math is the primary defence against generic-entity over-merging.
# Anything that survives both this stop-set AND a meaningful IDF score is
# considered a strong signal.
_ENTITY_STOP_TOKENS = frozenset({
    "us", "u.s.", "u.s",
    "the", "an", "a",
    "today", "yesterday", "tomorrow", "tonight",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
})

# Entities that appear in such a high baseline rate across world-news
# coverage that their per-fixture IDF over-states their distinguishing
# power. They get a weight multiplier of 0.4 in the merge score, so an
# overlap of {trump, white house, treasury, senate} no longer triggers
# a same-story merge between unrelated US-government clusters. The list
# is intentionally focused — only entities we've seen cause cross-story
# bridges in the validation suite.
_LOW_SPECIFICITY_ENTITIES = frozenset({
    # Heads of major governments — appear in dozens of unrelated stories
    "trump", "biden", "obama", "harris", "vance",
    "putin", "xi jinping", "xi", "modi", "starmer", "macron",
    "scholz", "merz", "netanyahu", "lula",
    # Geopolitical hot-spot countries — appear in many unrelated stories
    # via wire desk reactions ("Iran said...", "China called for...") and
    # cause transitive bridges between unrelated regional events.
    "iran", "iranian", "tehran",
    "china", "chinese", "beijing",
    "russia", "russian", "moscow", "kremlin",
    "ukraine", "ukrainian", "kyiv",
    "israel", "israeli", "jerusalem",
    "india", "indian", "new delhi",
    "brazil", "brazilian", "sao paulo",
    "japan", "japanese", "tokyo",
    "germany", "german", "berlin",
    "france", "french", "paris",
    "uk", "u.k.", "united kingdom", "britain", "british", "london",
    "europe", "european",
    "africa", "african",
    # Generic government / institution shells
    "white house", "kremlin", "downing street", "elysee",
    "congress", "senate", "house", "parliament", "supreme court",
    "treasury", "us treasury", "pentagon", "state department",
    "fbi", "cia", "doj", "justice department",
    "fed", "federal reserve", "wall street",
    "european commission", "european council", "european union",
    "nato", "un ", "united nations",
    # Wire-service self-references (always appear, never distinguishing)
    "reuters", "ap", "associated press", "bloomberg", "afp", "dpa",
    "bbc", "cnn", "fox news", "wall street journal", "nytimes",
    "the new york times", "washington post", "guardian",
})
_LOW_SPECIFICITY_WEIGHT = 0.4


# ---------------------------------------------------------------------------
# Canonical summit / known co-occurrence pairs
# ---------------------------------------------------------------------------
# Editorial override for known high-frequency political pair-events that
# the IDF formula systematically under-weights (each name appears in many
# unrelated clusters individually, deflating their idf). When two clusters
# both carry BOTH names from a pair AND fall within the merge time window,
# they are the same story by editorial fiat.
#
# Production failures motivating this list (audit 2026-05-15):
#   - Trump-Xi summit fragmented into 4 clusters (#5/#15/#17/#43)
#   - Starmer + Streeting fragmented into 2 clusters (#6 + #44)
#
# Keep the list short and intentional. Each entry must be a known
# bilateral / governance pair where every appearance in production news
# refers to the same underlying event-stream.
_SUMMIT_PAIRS = frozenset({
    # Heads-of-state diplomatic pairs (G2 / G7 / bilateral)
    frozenset({"trump", "xi"}),
    frozenset({"trump", "putin"}),
    frozenset({"trump", "modi"}),
    frozenset({"trump", "netanyahu"}),
    frozenset({"trump", "zelensky"}),
    frozenset({"biden", "xi"}),
    frozenset({"biden", "putin"}),
    frozenset({"biden", "netanyahu"}),
    frozenset({"biden", "zelensky"}),
    frozenset({"xi", "putin"}),
    # UK government internal — known fragmenters in 2026-05 audit
    frozenset({"starmer", "streeting"}),
    frozenset({"starmer", "reeves"}),
    # Israel / regional pairs
    frozenset({"netanyahu", "putin"}),
    # Ukraine / Russia
    frozenset({"zelensky", "putin"}),
})

# Garbage cluster-title signatures (Fix 2 — over-merge force-split).
# When the title-generator emits one of these, the cluster has aggregated
# unrelated sub-events sharing a single GPE or NORP, and we must split it.
# Each pattern targets a real production failure mode:
#   - "X Spans <list> and Y" — multi-event mash-up under one entity
#   - "Diplomatic ... Activity Spans" — UK celeb / Italy umbrella over-merge
#   - "Cluster Spans" — the title-generator literally writes "Cluster"
_GARBAGE_TITLE_PATTERNS = [
    # "Spans Deaths, Weddings, and Bond Casting" / "Spans Four Continents"
    re.compile(
        r"\bSpans\s+(?:[A-Z][A-Za-z]+(?:,\s*|\s+and\s+)){2,}[A-Z][A-Za-z]+",
    ),
    # "Italy Diplomatic Activity Spans..." / "Diplomatic and Cultural Activity Spans..."
    re.compile(
        r"\b(?:Diplomatic|Cultural|Political|Economic)\s+"
        r"(?:and\s+\w+\s+)?Activity\s+Spans\b",
        re.IGNORECASE,
    ),
    # Explicit "Cluster Spans" — title-generator gave up
    re.compile(r"\bCluster\s+Spans\b", re.IGNORECASE),
    # "News Cluster Spans" / "Coverage Spans Multiple"
    re.compile(r"\b(?:News\s+)?Cluster\s+Spans\b", re.IGNORECASE),
    re.compile(r"\bCoverage\s+Spans\s+(?:Multiple|Many|Several)\b", re.IGNORECASE),
]


_ENTITY_QUALIFIER_PREFIXES = (
    "the ", "a ", "an ",
    "president ", "vice president ", "prime minister ", "pm ",
    "chancellor ", "chairman ", "chairwoman ", "chair ",
    "secretary ", "minister ", "mr. ", "mrs. ", "ms. ", "dr. ",
    "sir ", "lord ", "lady ",
    "super ", "tropical ", "category 1 ", "category 2 ", "category 3 ",
    "category 4 ", "category 5 ",
    "former ", "ex-",
)


def _normalise_entity(text: str) -> str:
    """Lowercase + strip honorifics/qualifiers + possessive + punctuation.

    The qualifier strip aligns variants like:
        "President Trump"        -> "trump"
        "Super Typhoon Hagibis"  -> "typhoon hagibis"
        "Prime Minister Modi"    -> "modi"
    so that two articles using different honorifics land on the same key.
    """
    s = text.lower().strip()
    # Repeat once more to handle stacked qualifiers ("the former president ...")
    for _ in range(2):
        for pfx in _ENTITY_QUALIFIER_PREFIXES:
            if s.startswith(pfx):
                s = s[len(pfx):]
                break
    if s.endswith("'s") or s.endswith("’s"):
        s = s[:-2]
    return s.strip(" '\"‘’“”.,;:!?")


def _extract_cluster_entities(articles: list[dict]) -> dict[str, int]:
    """Return entity -> count from title + summary + first 1500 chars of body.

    Body inclusion (vs. title+summary alone) is what surfaces the
    distinguishing entities — Klitschko, Zelensky, Marcos, Cagayan,
    Hagibis, Fadnavis — that anchor a same-story merge. Without body,
    only generic GPEs/NORPs (Russia, Ukraine, Russian) appear and the
    IDF score collapses. The 1500-char cap balances NER cost against
    coverage: most named actors appear in the first 3-4 sentences.
    """
    nlp = get_nlp()
    counts: Counter = Counter()
    # Cap at first 10 articles to bound spaCy cost on giant clusters
    for article in articles[:10]:
        title = article.get("title", "") or ""
        summary = article.get("summary", "") or ""
        body = article.get("full_text", "") or ""
        # Body is sliced before concatenation so the title is always seen
        text = f"{title} {summary} {body[:1500]}"[:3000]
        if not text.strip():
            continue
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "NORP", "EVENT", "FAC", "LOC"):
                norm = _normalise_entity(ent.text)
                if len(norm) < 3:
                    continue
                if norm in _ENTITY_STOP_TOKENS:
                    continue
                counts[norm] += 1
    return dict(counts)


def _compute_global_idf(cluster_entities: list[dict[str, int]]) -> dict[str, float]:
    """Compute idf(e) = log(N_eff / df(e)) with corpus-prior smoothing.

    Pure within-fixture IDF collapses when an entity appears in every
    cluster of a small fixture (df = N -> log(1) = 0). To keep the
    signal stable across both fixture-scale (N ~ 6) and production-scale
    runs (N ~ 2000), we use:
        N_eff = max(N, 30)        — virtual corpus floor
        df_eff = df + ceil(N/4)   — additive smoothing
    The smoothing replaces the prior hard df_floor: every entity gets a
    prior count proportional to N/4, which damps the spread between
    truly-rare and merely-uncommon entities while preserving the
    ordering. Net effect for fixtures: an entity in 6/6 clusters gets
    idf ~ log(30/(6+2)) = 1.32 (was 0.05 with the old formula); an
    entity in 1/6 clusters gets idf ~ log(30/(1+2)) = 2.30. The signal
    is now stable enough to drive merge decisions on small N.
    """
    n = max(1, len(cluster_entities))
    n_eff = max(n, 30)
    smoothing = max(1, (n + 3) // 4)  # ~N/4 rounded up

    df: Counter = Counter()
    for ents in cluster_entities:
        for e in ents:
            df[e] += 1

    idf: dict[str, float] = {}
    for e, raw_df in df.items():
        df_eff = raw_df + smoothing
        idf[e] = max(0.05, math.log(n_eff / df_eff))
    return idf


def _parse_first_pub(cluster: dict) -> datetime | None:
    fp = cluster.get("first_published", "") or ""
    if not fp:
        return None
    try:
        dt = datetime.fromisoformat(fp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def merge_related_clusters(
    clusters: list[dict],
    idf_threshold: float = ENTITY_MERGE_IDF_THRESHOLD,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 2: IDF-weighted entity-overlap merge.

    Algorithm:
      1. For each cluster, extract its weighted entity set.
      2. Compute global IDF over the run (N = number of clusters).
      3. For each pair (i, j) of clusters with first_published within
         max_age_spread_hours, score = sum(idf(e) for e in shared entities).
      4. Union-find merge when score >= idf_threshold.

    No tier-conditional caps. No size cap. No head-of-state exception.
    The IDF math itself does the right thing for both highly-distinctive
    entity overlaps and broad cross-story common-entity bleed.
    """
    if len(clusters) <= 1:
        return clusters

    cluster_entities: list[dict[str, int]] = [
        _extract_cluster_entities(c.get("articles", [])) for c in clusters
    ]
    idf = _compute_global_idf(cluster_entities)
    timestamps = [_parse_first_pub(c) for c in clusters]

    n = len(clusters)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        ents_i = cluster_entities[i]
        if not ents_i:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            ents_j = cluster_entities[j]
            if not ents_j:
                continue

            # Time gate
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            shared = set(ents_i.keys()) & set(ents_j.keys())
            if not shared:
                continue
            # Per-entity IDF, downweighted for entities in the low-
            # specificity set (Trump, white house, treasury, etc.) that
            # appear across many unrelated clusters in any news cycle.
            score = 0.0
            distinguishing_shared = 0
            for e in shared:
                w = _LOW_SPECIFICITY_WEIGHT if e in _LOW_SPECIFICITY_ENTITIES else 1.0
                score += idf.get(e, 0.0) * w
                if e not in _LOW_SPECIFICITY_ENTITIES:
                    distinguishing_shared += 1

            # Primary merge: weighted sum-of-IDF crosses threshold AND
            # the pair shares at least 3 entities, of which at least 1 is
            # NOT in the low-specificity set. This blocks pure-government-
            # bridge merges (4 shared entities, all from {trump, white
            # house, treasury, senate}, score arithmetically ~3.0 but
            # carrying no actual story-similarity signal).
            should_merge = (
                score >= idf_threshold
                and len(shared) >= 3
                and distinguishing_shared >= 1
            )

            # Fallback merge: high-Jaccard, moderate-shared-count pairs
            # rescue same-story pairs whose entities are individually too
            # common to score on raw IDF (e.g. India election clusters all
            # mention BJP + Modi + Maharashtra + Fadnavis but each entity
            # has df ≈ N so IDF -> 0; Apple earnings clusters share Apple
            # + China + Vision Pro). Requires BOTH:
            #   (a) >= 3 shared distinct entities
            #   (b) Jaccard over entity sets >= 0.27
            # Jaccard 0.27 is the calibrated knee — Brazil deforestation/
            # football pair (jacc = 0.04, shared = 0) stays split, while
            # the Apple/India/Typhoon merge pairs (jacc 0.27-0.50) all
            # cross. Higher jaccard floors miss legitimate merges; lower
            # floors over-merge in cohort fixtures (overflow C2<->C12 at
            # jacc 0.25 sits exactly on the line).
            if not should_merge:
                union_size = len(set(ents_i.keys()) | set(ents_j.keys()))
                if (
                    len(shared) >= 3
                    and union_size > 0
                    and (len(shared) / union_size) >= 0.27
                ):
                    should_merge = True

            if should_merge:
                union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 2.5: Canonical-pair merge (editorial override)
# ---------------------------------------------------------------------------

def _cluster_entity_surface_set(cluster: dict) -> set[str]:
    """Lowercased, qualifier-stripped entity-surface set for one cluster.

    Used by the canonical-pair pass — we look for surface-form matches like
    "trump" / "xi" / "starmer" / "streeting" regardless of how the entity
    appears (title-cased, with title prefixes, possessive, hyphenated, etc).

    Splits on whitespace, hyphens, slashes, parentheses, and most punctuation
    so that headlines like "Trump-Xi summit" yield {trump, xi}, not
    {trump-xi}. Two-letter surnames (Xi) are intentionally allowed.
    """
    surfaces: set[str] = set()
    for art in (cluster.get("articles") or [])[:10]:
        title = art.get("title", "") or ""
        summary = art.get("summary", "") or ""
        body = (art.get("full_text", "") or "")[:1500]
        text = f"{title} {summary} {body}".lower()
        # Split on any non-letter character (covers hyphens, slashes, dots,
        # quotes, punctuation, whitespace). Keep apostrophes inside words
        # but not as separators.
        for tok in re.findall(r"[a-z]+(?:'[a-z]+)?", text):
            if 2 <= len(tok) <= 20:
                surfaces.add(tok)
    return surfaces


def merge_canonical_pairs(
    clusters: list[dict],
    pair_set: frozenset = _SUMMIT_PAIRS,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 2.5: editorial pair-merge.

    For each known co-occurrence pair (e.g. {trump, xi}, {starmer, streeting}),
    if cluster A and cluster B BOTH contain BOTH names from the pair AND
    fall within the same time window, union them. This is intentionally
    NOT IDF-based — it's an editorial override for political pair-events
    whose individual entity counts are too high for IDF to surface.
    """
    if len(clusters) <= 1 or not pair_set:
        return clusters

    n = len(clusters)
    surface_sets = [_cluster_entity_surface_set(c) for c in clusters]
    timestamps = [_parse_first_pub(c) for c in clusters]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        if not surface_sets[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not surface_sets[j]:
                continue

            # Time gate (same as Phase 2)
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            # Both clusters must carry BOTH names from at least one pair
            for pair in pair_set:
                # pair is a frozenset of two names
                if pair.issubset(surface_sets[i]) and pair.issubset(surface_sets[j]):
                    union(i, j)
                    break

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Phase 4: "Spans X" garbage-title force-split
# ---------------------------------------------------------------------------

def _title_is_garbage(title: str) -> bool:
    """Return True if the cluster title matches a known over-merge signature."""
    if not title:
        return False
    return any(p.search(title) for p in _GARBAGE_TITLE_PATTERNS)


def _force_split_cluster(
    cluster: dict,
    tighter_threshold: float = STORY_TFIDF_THRESHOLD * 1.5,
    tighter_idf_threshold: float = ENTITY_MERGE_IDF_THRESHOLD * 1.5,
) -> list[dict]:
    """Re-cluster a single over-merged cluster's articles with stricter gates.

    Runs a mini Phase 1 + Phase 2 on JUST this cluster's articles. Used by
    the garbage-title force-split pass when the title-generator emits a
    "Spans X, Y, and Z" signature that proves the cluster has aggregated
    unrelated sub-events under a single shared entity (usually a GPE).
    """
    articles = cluster.get("articles") or []
    if len(articles) < 2:
        return [cluster]

    # Mini Phase 1: stricter TF-IDF cosine
    documents = [_build_document(a) for a in articles]
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    if len(valid_indices) < 2:
        return [cluster]

    valid_docs = [documents[i] for i in valid_indices]
    valid_articles = [articles[i] for i in valid_indices]

    try:
        vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95,
        )
        tfidf_matrix = vectorizer.fit_transform(valid_docs)
        sim_matrix = cosine_similarity(tfidf_matrix)
        distance_matrix = np.clip(1.0 - sim_matrix, 0.0, 2.0)
        distance_threshold = 1.0 - tighter_threshold
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=distance_threshold,
            metric="precomputed",
            linkage="average",
        )
        labels = clustering.fit_predict(distance_matrix)
    except Exception:
        # If anything goes wrong, return the original cluster unchanged
        return [cluster]

    # Group by label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(label, []).append(idx)

    # If still only one sub-cluster after stricter gating, give up the split
    if len(cluster_map) <= 1:
        return [cluster]

    sub_clusters: list[dict] = []
    for label, indices in sorted(cluster_map.items()):
        carts = [valid_articles[i] for i in indices]
        article_ids = [a.get("id", "") for a in carts]
        source_ids = list({a.get("source_id", "") for a in carts if a.get("source_id")})
        pub_dates = [a.get("published_at", "") for a in carts if a.get("published_at")]
        first_published = min(pub_dates) if pub_dates else ""
        sub_title = _generate_cluster_title(carts)
        sub_summary = _generate_cluster_summary(carts)
        sub_clusters.append({
            "title": sub_title,
            "summary": sub_summary,
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(carts, sub_title, sub_summary),
            "first_published": first_published,
            "articles": carts,
        })

    # Mini Phase 2: stricter IDF entity merge so we don't immediately re-merge
    if len(sub_clusters) > 1:
        sub_clusters = merge_related_clusters(
            sub_clusters,
            idf_threshold=tighter_idf_threshold,
        )

    # Final guard: if the stricter pass collapsed everything back to 1
    # (real same-story content), keep the original anchor cluster unchanged.
    if len(sub_clusters) == 1:
        return [cluster]

    return sub_clusters


def split_garbage_clusters(clusters: list[dict]) -> list[dict]:
    """Phase 4: scan cluster titles for over-merge signatures, force-split.

    The cluster title is the symptom. When the title-generator emits a
    "Spans X, Y, and Z" signature, it has been forced to manufacture a
    mash-up because no single headline covers the cluster's articles —
    proof of over-merge. Re-cluster those articles at a stricter
    threshold and replace the original with the resulting sub-clusters.
    """
    if not clusters:
        return clusters

    out: list[dict] = []
    for c in clusters:
        title = c.get("title", "") or ""
        if _title_is_garbage(title):
            sub = _force_split_cluster(c)
            out.extend(sub)
        else:
            out.append(c)
    return out


# ---------------------------------------------------------------------------
# Phase 3: Stem-aware title Jaccard merge
# ---------------------------------------------------------------------------

_TITLE_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "its", "it", "as", "after", "over", "up", "that",
    "this", "not", "no", "says", "said", "new", "amid", "more", "than",
    "about", "how", "what", "why", "who", "when", "where", "which",
    "will", "would", "could", "should", "may", "might", "can",
    "reports", "report", "sources", "according", "also", "first",
    "two", "one", "three", "us", "announces", "while",
})

# Lazy stemmer — try nltk PorterStemmer; on import failure fall back to
# spaCy lemmatisation (slower per-call but always available since spaCy
# is a hard pipeline dependency).
_STEMMER = None
_USE_LEMMA_FALLBACK = False


def _get_stemmer():
    global _STEMMER, _USE_LEMMA_FALLBACK
    if _STEMMER is not None or _USE_LEMMA_FALLBACK:
        return _STEMMER
    try:
        from nltk.stem import PorterStemmer
        _STEMMER = PorterStemmer()
    except Exception:
        _USE_LEMMA_FALLBACK = True
        _STEMMER = None
    return _STEMMER


def _stem_word(word: str) -> str:
    stemmer = _get_stemmer()
    if stemmer is not None:
        try:
            return stemmer.stem(word)
        except Exception:
            pass
    # spaCy lemma fallback
    try:
        nlp = get_nlp()
        doc = nlp(word)
        if len(doc) > 0:
            return doc[0].lemma_.lower() or word
    except Exception:
        pass
    return word


def _title_word_stems(title: str) -> set[str]:
    """Tokenise + stopword-filter + Porter-stem a title's content words."""
    cleaned = _clean_title(title)
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", cleaned.lower())
    out: set[str] = set()
    for w in words:
        if w in _TITLE_STOPWORDS or len(w) < 2:
            continue
        out.add(_stem_word(w))
    return out


def merge_duplicate_title_clusters(
    clusters: list[dict],
    jaccard_threshold: float = TITLE_JACCARD_THRESHOLD,
    max_age_spread_hours: float = MAX_AGE_SPREAD_HOURS,
) -> list[dict]:
    """Phase 3: stem-aware title Jaccard merge.

    Single threshold. Porter-stemmed token overlap (e.g. "resign" /
    "resignation" both reduce to "resign"). Same time-spread gate as
    Phase 2 — different stories about the same entity at different times
    will not collapse.

    No tier overrides. No max-merged-articles cap. The stem-aware
    Jaccard signal is strong enough on its own — title rewrites of the
    same headline reliably cross 0.35 once stemming aligns inflections.
    """
    if len(clusters) <= 1:
        return clusters

    n = len(clusters)
    title_stems = [_title_word_stems(c.get("title", "")) for c in clusters]
    timestamps = [_parse_first_pub(c) for c in clusters]

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        if not title_stems[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not title_stems[j]:
                continue

            inter = len(title_stems[i] & title_stems[j])
            uni = len(title_stems[i] | title_stems[j])
            if uni == 0:
                continue
            if (inter / uni) < jaccard_threshold:
                continue

            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread = abs((ti - tj).total_seconds()) / 3600.0
                if spread > max_age_spread_hours:
                    continue

            union(i, j)

    return _rebuild_merged(clusters, parent, find)


# ---------------------------------------------------------------------------
# Shared rebuild helper for both merge phases
# ---------------------------------------------------------------------------

def _rebuild_merged(
    clusters: list[dict],
    parent: list[int],
    find,
) -> list[dict]:
    n = len(clusters)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    out: list[dict] = []
    for root, members in groups.items():
        if len(members) == 1:
            out.append(clusters[root])
            continue

        all_articles: list[dict] = []
        all_article_ids: list[str] = []
        all_source_ids: set[str] = set()
        all_pub_dates: list[str] = []

        for idx in members:
            c = clusters[idx]
            all_articles.extend(c.get("articles", []))
            all_article_ids.extend(c.get("article_ids", []))
            all_source_ids.update(c.get("source_ids", []))
            fp = c.get("first_published", "")
            if fp:
                all_pub_dates.append(fp)

        anchor_idx = max(members, key=lambda i: clusters[i].get("source_count", 0))
        anchor = clusters[anchor_idx]

        first_published = min(all_pub_dates) if all_pub_dates else ""
        merged_title = _generate_cluster_title(all_articles)
        merged_summary = _generate_cluster_summary(all_articles)
        merged_section = _determine_section(all_articles, merged_title, merged_summary)

        out.append({
            "title": merged_title,
            "summary": merged_summary,
            "article_ids": all_article_ids,
            "source_ids": list(all_source_ids),
            "source_count": len(all_source_ids),
            "section": merged_section,
            "first_published": first_published,
            "articles": all_articles,
            **{
                k: v for k, v in anchor.items()
                if k not in (
                    "title", "summary", "article_ids", "source_ids",
                    "source_count", "section", "first_published", "articles",
                )
            },
        })
    return out


# ---------------------------------------------------------------------------
# Wire-amplification accounting (post-merge)
# ---------------------------------------------------------------------------

def _voice_id(article: dict) -> str:
    """Return the publisher slug that should count as one voice for
    source_count math. Wire copies collapse to their origin publisher.
    """
    if article.get("is_wire_copy"):
        return (
            article.get("wire_origin_publisher_id")
            or article.get("source_id", "")
            or ""
        )
    return article.get("source_id", "") or ""


def _apply_wire_aware_source_count(cluster: dict) -> None:
    """Mutate cluster in place: recompute source_count + source_ids using
    `_voice_id`, and add a `wire_amplification` ratio field."""
    arts = cluster.get("articles", []) or []
    voices = {_voice_id(a) for a in arts if _voice_id(a)}
    cluster["source_ids"] = list(voices)
    cluster["source_count"] = len(voices)
    total = len(arts)
    cluster["wire_amplification"] = (
        round(total / max(len(voices), 1), 3) if total else 0.0
    )


# ---------------------------------------------------------------------------
# Main entry: cluster_stories
# ---------------------------------------------------------------------------

def cluster_stories(
    articles: list[dict],
    similarity_threshold: float = STORY_TFIDF_THRESHOLD,
    run_merge_pass: bool = True,
) -> list[dict]:
    """Group articles into story clusters.

    Pipeline:
        Phase 1   — TF-IDF + agglomerative clustering at
                    `similarity_threshold` (default STORY_TFIDF_THRESHOLD).
        Phase 2   — IDF-weighted entity-overlap merge
                    (merge_related_clusters).
        Phase 2.5 — Canonical-pair merge (merge_canonical_pairs):
                    editorial override for known co-occurrence pairs
                    that IDF systematically under-weights.
        Phase 3   — Stem-aware title-Jaccard merge
                    (merge_duplicate_title_clusters).
        Phase 4   — Garbage-title force-split (split_garbage_clusters):
                    re-clusters at stricter gates when the title-generator
                    produces a "Spans X, Y, and Z" mash-up signature.

    Wire-amplification: if articles arrive carrying `is_wire_copy` /
    `wire_origin_publisher_id` (set by deduplicator.deduplicate_articles),
    the final source_count collapses wire copies to their origin
    publisher and a `wire_amplification` ratio is recorded.

    Args:
        articles: List of article dicts. Each may carry the wire-fingerprint
            fields populated by Phase 0.
        similarity_threshold: Cosine similarity floor for Phase 1
            (override only for sub-cluster recursion or debugging).
        run_merge_pass: When False, skip Phases 2 and 3 (used by callers
            that want raw TF-IDF output for diagnostic purposes).

    Returns:
        List of cluster dicts with keys:
            title, summary, article_ids, source_ids, source_count,
            section, first_published, articles, wire_amplification.
    """
    if not articles:
        return []

    # Single-article fast path
    if len(articles) == 1:
        a = articles[0]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([a]),
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", ""),
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        return [c]

    # Build documents and split into vectorizable / empty
    documents = [_build_document(a) for a in articles]
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    empty_indices = [i for i, d in enumerate(documents) if not d.strip()]

    empty_singletons: list[dict] = []
    for i in empty_indices:
        a = articles[i]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": a.get("summary", "") or (a.get("full_text", "") or "")[:500],
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", "") or "",
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        empty_singletons.append(c)

    if not valid_indices:
        return empty_singletons

    valid_docs = [documents[i] for i in valid_indices]
    valid_articles = [articles[i] for i in valid_indices]

    if len(valid_docs) == 1:
        a = valid_articles[0]
        c = {
            "title": a.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([a]),
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", ""),
            "articles": [a],
        }
        _apply_wire_aware_source_count(c)
        return [c] + empty_singletons

    # Phase 1: TF-IDF + agglomerative clustering
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    tfidf_matrix = vectorizer.fit_transform(valid_docs)
    sim_matrix = cosine_similarity(tfidf_matrix)
    distance_matrix = np.clip(1.0 - sim_matrix, 0.0, 2.0)

    distance_threshold = 1.0 - similarity_threshold
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance_matrix)

    # Group articles by label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(label, []).append(idx)

    clusters: list[dict] = []
    for label, indices in sorted(cluster_map.items()):
        carts = [valid_articles[i] for i in indices]
        article_ids = [a.get("id", "") for a in carts]
        source_ids = list({a.get("source_id", "") for a in carts if a.get("source_id")})
        pub_dates = [a.get("published_at", "") for a in carts if a.get("published_at")]
        first_published = min(pub_dates) if pub_dates else ""
        cluster_title = _generate_cluster_title(carts)
        cluster_summary = _generate_cluster_summary(carts)
        clusters.append({
            "title": cluster_title,
            "summary": cluster_summary,
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(carts, cluster_title, cluster_summary),
            "first_published": first_published,
            "articles": carts,
        })

    # Phases 2 + 2.5 + 3 + 4
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_related_clusters(clusters)
    # Phase 2.5 — editorial canonical-pair merge (Trump-Xi, Starmer-Streeting)
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_canonical_pairs(clusters)
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_duplicate_title_clusters(clusters)
    # Phase 4 — garbage-title force-split (over-merge detector)
    if run_merge_pass and clusters:
        clusters = split_garbage_clusters(clusters)

    # Append empty-document singletons (they bypass merge passes since
    # there's no document to compare against).
    if empty_singletons:
        clusters.extend(empty_singletons)

    # Final pass: recompute source_count using the wire-aware voice
    # collapse, and stamp wire_amplification on every cluster.
    for c in clusters:
        _apply_wire_aware_source_count(c)

    return clusters
