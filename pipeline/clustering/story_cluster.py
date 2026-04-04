"""
Story clustering engine for the void --news pipeline.

Groups articles covering the same story/event into clusters.
Each cluster represents one news story as seen through multiple sources.

Uses rule-based NLP (no LLM API calls):
    - TF-IDF vectorization of article titles + first 500 words
    - Cosine similarity via sklearn
    - Agglomerative clustering with distance threshold (0.3)
    - Entity-overlap merge pass (Phase 2) to consolidate evolving-story fragments
    - Title-similarity merge pass (Phase 3) to catch near-duplicate split clusters
    - Cluster title generation from most common named entities (spaCy NER)
"""

import re
from collections import Counter
from datetime import datetime, timezone

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from utils.nlp_shared import get_nlp


# --- Title cleanup patterns ---
# Wire service prefixes: (LEAD), (URGENT), BREAKING:, etc.
_WIRE_PREFIX_RE = re.compile(
    r'^\s*(?:\((?:LEAD|URGENT|CORRECTED|UPDATE(?:\s*\d*)?|RECASTS?|ADDS?|WRAPUP|NEWSALERT)\)\s*)'
    r'|^\s*(?:WATCH\s*LIVE\s*:|WATCH\s*:|BREAKING\s*:|UPDATE\s*:|EXCLUSIVE\s*:)\s*',
    re.IGNORECASE,
)
# Source attribution at end: " - Reuters", " | BBC News", " -- AP", etc.
_ATTRIBUTION_SUFFIX_RE = re.compile(
    r'\s*[-\u2013\u2014|]+\s*'
    r'(?:Reuters|AP\s*News?|Associated\s*Press|CNN|BBC(?:\s*News)?|NPR|PBS'
    r'|Fox\s*News|The\s+[A-Z]\w+(?:\s+[A-Z]\w+)?|[A-Z]\w+\s+News'
    r'|Al\s+Jazeera|Bloomberg|CNBC|ABC\s*News|CBS\s*News|NBC\s*News'
    r'|The\s+Guardian|Washington\s+Post|New\s+York\s+Times|Wall\s+Street\s+Journal'
    r'|Chicago\s+Tribune|UPI|NHK\s+WORLD(?:-JAPAN)?|NHK\s+World'
    r'|Nikkei|Haaretz|South\s+China\s+Morning\s+Post)'
    r'\s*$',
    re.IGNORECASE,
)
# Domain suffix attribution: " - upi.com", " - nhk.or.jp", etc.
_DOMAIN_SUFFIX_RE = re.compile(
    r'\s*[-\u2013\u2014|]+\s*\w+\.(?:com|org|net|co\.uk|or\.jp|co\.jp)\s*$',
    re.IGNORECASE,
)


def _clean_title(title: str) -> str:
    """Strip wire prefixes, source attribution, and junk from a title.

    Applies attribution stripping twice to handle double attributions
    like '... | NHK WORLD-JAPAN - nhk.or.jp'.
    """
    # Strip wire prefixes
    title = _WIRE_PREFIX_RE.sub('', title).strip()
    # Strip source attribution and domain suffixes (apply twice for doubles)
    for _ in range(2):
        title = _ATTRIBUTION_SUFFIX_RE.sub('', title).strip()
        title = _DOMAIN_SUFFIX_RE.sub('', title).strip()
    # Strip trailing whitespace/punctuation artifacts
    title = title.strip(' \t\n\r-\u2013\u2014|')
    return title


def _build_document(article: dict) -> str:
    """Build a text document from title + first 500 words of full_text.

    500 words (up from 200) gives TF-IDF a richer vocabulary, capturing
    supporting context — actor names, locations, policy references — that
    bridges sub-event articles belonging to the same evolving story.
    """
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""
    words = full_text.split()[:500]
    body_snippet = " ".join(words)
    return f"{title} {body_snippet}".strip()


def _generate_cluster_title(articles: list[dict]) -> str:
    """
    Generate a cluster title by selecting the most representative article
    headline from the cluster.

    For single-article clusters, uses that article's title directly.
    For multi-article clusters, scores each title by entity coverage,
    informativeness (length sweet spot), and absence of clickbait signals,
    then picks the best one.

    All titles are cleaned: wire prefixes stripped, source attribution
    removed, degenerate titles (<15 chars) rejected.
    """
    # Clean all titles and filter out degenerate ones
    raw_titles = [a.get("title", "") or "" for a in articles]
    cleaned_titles = [_clean_title(t) for t in raw_titles]
    valid_titles = [t for t in cleaned_titles if len(t) >= 15]

    if not valid_titles:
        # All titles degenerate — try entity-concatenated fallback
        nlp = get_nlp()
        entity_counter: Counter = Counter()
        for article in articles[:20]:
            title = article.get("title", "") or ""
            summary = article.get("summary", "") or ""
            doc = nlp(f"{title} {summary}"[:5000])
            for ent in doc.ents:
                if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT"):
                    entity_counter[ent.text] += 1
        top_ents = [name for name, _ in entity_counter.most_common(3)]
        if top_ents:
            return ", ".join(top_ents)
        return "Developing Story"

    if len(valid_titles) == 1:
        return valid_titles[0]

    # Extract common entities across the cluster to measure title relevance
    nlp = get_nlp()
    entity_counter: Counter = Counter()
    for article in articles[:20]:
        title = article.get("title", "") or ""
        doc = nlp(title)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "NORP"):
                entity_counter[ent.text.lower()] += 1

    top_entities = {name for name, count in entity_counter.most_common(5)
                    if count >= 2} if entity_counter else set()

    # Score each title
    def _score_title(title: str) -> float:
        score = 0.0
        length = len(title)

        # Length sweet spot: prefer 40-120 chars (informative but not wordy)
        if 40 <= length <= 120:
            score += 3.0
        elif 20 <= length < 40:
            score += 1.5
        elif 120 < length <= 160:
            score += 2.0
        elif length < 20:
            score += 0.5  # too vague

        # Entity coverage: reward titles that mention cluster-wide entities
        if top_entities:
            title_lower = title.lower()
            matches = sum(1 for e in top_entities if e in title_lower)
            score += matches * 2.0

        # Penalize clickbait signals
        if title.endswith("?"):
            score -= 1.0
        if title.isupper():
            score -= 2.0
        if any(w in title.lower() for w in ("you won't believe", "shocking",
                                              "this is why", "here's what")):
            score -= 1.5

        # Prefer titles with a colon or dash (often structured: "Topic: Detail")
        if ": " in title or " — " in title or " - " in title:
            score += 0.5

        return score

    scored = [(t, _score_title(t)) for t in valid_titles]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0]


def _generate_cluster_summary(articles: list[dict]) -> str:
    """
    Generate a cluster summary by selecting the most informative article
    summary from the cluster.

    For multi-article clusters, picks the longest substantive summary
    (avoiding very short or boilerplate text). Falls back to constructing
    a brief description from the cluster title and source count.
    """
    summaries = []
    for a in articles:
        summary = (a.get("summary", "") or "").strip()
        if summary and len(summary) >= 40:
            summaries.append(summary)

    if not summaries:
        # Fall back to shorter summaries
        for a in articles:
            summary = (a.get("summary", "") or "").strip()
            if summary and len(summary) >= 15:
                summaries.append(summary)

    if summaries:
        # Pick the longest non-duplicate summary (most informative)
        summaries.sort(key=len, reverse=True)
        return summaries[0]

    # Last resort: use the first article's title
    for a in articles:
        title = (a.get("title", "") or "").strip()
        if title:
            return title

    return ""


# --- Content-based section markers ---
# Only unambiguous US-specific terms. Removed overly broad terms that trigger
# on international reporting: "governor", "senator", "congressman" (other
# countries have these), "democrat"/"republican" (too common in any US political
# reporting), and US state names (e.g. "georgia" is also a country).
US_MARKERS = {
    'congress', 'house of representatives', 'white house',
    'capitol hill', 'pentagon', 'state department',
    'fbi', 'cia', 'dhs', 'fema', 'epa', 'fda', 'sec',
    'federal reserve', 'wall street', 'medicare', 'medicaid',
    'gop', 'dnc', 'rnc',
    # Key US political figures (unambiguous)
    'trump', 'biden', 'desantis', 'pelosi', 'mcconnell',
}

INTL_MARKERS = {
    'ukraine', 'russia', 'china', 'eu ', 'european union', 'nato',
    'middle east', 'gaza', 'israel', 'iran', 'north korea', 'un ',
    'united nations', 'world bank', 'imf', 'brics',
    'africa', 'asia', 'latin america', 'pacific',
    'india', 'japan', 'south korea', 'taiwan', 'syria',
    'saudi arabia', 'turkey', 'brazil', 'mexico',
    # Additional international markers for better balance
    'minister', 'parliament', 'european', 'beijing', 'moscow',
    'kiev', 'kyiv', 'jerusalem', 'tehran', 'kabul',
    'g7', 'g20', 'world cup', 'olympics',
    'prime minister', 'chancellor', 'monarchy',
    'hong kong', 'myanmar', 'afghanistan', 'iraq', 'yemen',
    'sudan', 'somalia', 'ethiopia', 'nigeria', 'kenya',
    'australia', 'new zealand', 'philippines', 'indonesia',
    'pakistan', 'bangladesh', 'sri lanka', 'vietnam',
}


def _determine_section(articles: list[dict], cluster_title: str = "",
                       cluster_summary: str = "") -> str:
    """
    Determine cluster section using content-based markers with
    source-based fallback.

    Priority:
    1. Check cluster title + summary for US vs. international markers
    2. If clear signal (3+ markers one side, 0 the other), override
    3. Otherwise fall back to majority vote of article sections
    """
    # Content-based detection from cluster title + summary
    text = f"{cluster_title} {cluster_summary}".lower()

    us_count = sum(1 for m in US_MARKERS if m in text)
    intl_count = sum(1 for m in INTL_MARKERS if m in text)

    # Override only when signal is clearly one-sided:
    # US requires 4+ markers (higher bar to avoid over-classification);
    # International keeps 3+ (under-represented, lower threshold is safer).
    # Both require 0 markers on the other side.
    # Asymmetry biases ambiguous stories toward "world" — safer default
    # for a global news product (target: US <= 55%).
    if us_count >= 4 and intl_count == 0:
        return "us"
    if intl_count >= 3 and us_count == 0:
        return "world"

    # Ambiguous, mixed, or insufficient content signal — fall back to source-based
    sections: Counter = Counter()
    for article in articles:
        section = article.get("section", "") or ""
        if section:
            sections[section.lower()] += 1

    if not sections:
        return "world"

    top_section = sections.most_common(1)[0][0]
    # Pass through standard edition names directly
    if top_section in ("europe", "south-asia"):
        return top_section
    if any(kw in top_section for kw in ("us", "domestic", "nation", "national", "america")):
        return "us"
    return "world"


# Entities too broad to be useful merge signals — they appear across many
# unrelated stories and cause transitive over-merging (Iran+Trump connects
# gas field strikes to NATO to Hegseth to oil prices to Hormuz).
_OVERLY_COMMON_ENTITIES = frozenset({
    "us", "u.s.", "united states", "america", "american",
    "trump", "donald trump", "president trump",
    "biden", "joe biden", "president biden",
    "china", "russia",
    "congress", "senate", "white house",
    "the united states", "the us", "washington",
    "republicans", "democrats", "gop",
    # v5.6: Added to prevent false merges at lower entity threshold (3→2).
    # These GPEs/ORGs appear across many unrelated stories.
    "new york", "california", "texas", "florida",
    "london", "paris", "beijing", "moscow",
    "european union", "eu", "united nations",
})


def _extract_cluster_entities(articles: list[dict]) -> set[str]:
    """
    Extract a set of prominent named entities (PERSON, ORG, GPE, NORP, EVENT)
    from the titles and summaries of up to 10 articles in a cluster.

    Used by merge_related_clusters() to find narrative overlap across
    initially-separate clusters. Returns lowercase entity strings.

    Filters out overly-common entities (Trump, US, Iran, etc.) that appear
    across many unrelated stories and cause transitive over-merging.
    """
    nlp = get_nlp()
    entities: set[str] = set()
    for article in articles[:10]:
        title = article.get("title", "") or ""
        summary = article.get("summary", "") or ""
        text = f"{title} {summary}"[:1000]
        if not text.strip():
            continue
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "NORP", "EVENT"):
                # Normalize: lowercase, strip possessives
                normalized = ent.text.lower().rstrip("'s").strip()
                if len(normalized) >= 3 and normalized not in _OVERLY_COMMON_ENTITIES:
                    entities.add(normalized)
    return entities


def merge_related_clusters(
    clusters: list[dict],
    min_shared_entities: int = 2,
    max_age_spread_hours: float = 48.0,
    max_cluster_articles: int = 75,
) -> list[dict]:
    """
    Post-clustering merge pass: consolidate micro-clusters that belong to the
    same evolving story narrative.

    This addresses the Iran-war fragmentation problem where sub-events
    ("Israel Strikes Gas Field", "Hegseth Defends $200B Request",
    "Hormuz Tensions") form separate clusters because they share no
    overlapping TF-IDF terms, yet share named entities (Iran, Pentagon,
    Netanyahu, Israel) that identify them as facets of one story.

    Algorithm:
        1. For each cluster, extract its top named entities.
        2. Compare entity sets pairwise across clusters.
        3. If two clusters share >= min_shared_entities AND their
           first_published timestamps are within max_age_spread_hours,
           merge the smaller into the larger.
        4. Repeat until stable (no more merges in a pass).

    Args:
        clusters: List of cluster dicts from cluster_stories().
        min_shared_entities: How many entities two clusters must share to
            trigger a merge (default 2 — requires two matching actors/places,
            preventing false merges on single common words like "Trump").
            v5.6: Lowered from 3 to 2 to catch cases like duplicate Supreme
            Court conversion therapy clusters ("supreme court" + "colorado").
            _OVERLY_COMMON_ENTITIES filter expanded to prevent false merges.
        max_age_spread_hours: Maximum time between the earliest articles of
            two clusters for them to be eligible for merging. Prevents
            cross-month merges (e.g., "Iran nuclear deal 2015" with
            "Iran-Israel war 2026"). Default 48h covers evolving stories
            that span 2-3 pipeline runs.
        max_cluster_articles: Maximum articles in a merged cluster. Prevents
            runaway transitive merges where Union-Find chains unrelated
            sub-events (e.g., 224-article Iran mega-cluster). Default 50.

    Returns:
        Reduced list of cluster dicts with merged source counts and article
        lists. Preserves all existing cluster dict keys.
    """
    if len(clusters) <= 1:
        return clusters

    def _parse_first_pub(cluster: dict):
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

    # Extract entities for each cluster once (O(N) spaCy parses)
    cluster_entities: list[set[str]] = [
        _extract_cluster_entities(c.get("articles", [])) for c in clusters
    ]

    # Union-Find for transitive merge closure with size tracking
    n = len(clusters)
    parent = list(range(n))
    group_size = [len(c.get("articles", [])) for c in clusters]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            group_size[rb] += group_size[ra]

    timestamps = [_parse_first_pub(c) for c in clusters]

    for i in range(n):
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue  # already in same group

            shared = cluster_entities[i] & cluster_entities[j]
            if len(shared) < min_shared_entities:
                continue

            # Time spread gate: don't merge stories far apart in time
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread_hours = abs((ti - tj).total_seconds()) / 3600.0
                if spread_hours > max_age_spread_hours:
                    continue

            # Size gate: prevent runaway mega-clusters from transitive merges
            if group_size[find(i)] + group_size[find(j)] > max_cluster_articles:
                continue

            union(i, j)

    # Group cluster indices by their root
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    # Build merged cluster dicts
    merged_clusters: list[dict] = []
    for root, members in groups.items():
        if len(members) == 1:
            merged_clusters.append(clusters[root])
            continue

        # Merge all member clusters into one
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

        # Pick the cluster with the most sources as the "anchor" for title/summary
        anchor = max(members, key=lambda idx: clusters[idx].get("source_count", 0))
        anchor_cluster = clusters[anchor]

        first_published = min(all_pub_dates) if all_pub_dates else ""

        # Regenerate title and summary from the full merged article set
        merged_title = _generate_cluster_title(all_articles)
        merged_summary = _generate_cluster_summary(all_articles)

        # Determine section from majority vote across all articles
        merged_section = _determine_section(
            all_articles, merged_title, merged_summary
        )

        merged_clusters.append({
            "title": merged_title,
            "summary": merged_summary,
            "article_ids": all_article_ids,
            "source_ids": list(all_source_ids),
            "source_count": len(all_source_ids),
            "section": merged_section,
            "first_published": first_published,
            "articles": all_articles,
            # Preserve any extra keys from the anchor (e.g., Gemini enrichment)
            **{
                k: v for k, v in anchor_cluster.items()
                if k not in ("title", "summary", "article_ids", "source_ids",
                             "source_count", "section", "first_published", "articles")
            },
        })

    return merged_clusters


# --- Stopwords for title Jaccard comparison ---
_TITLE_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "its", "it", "as", "after", "over", "up", "that",
    "this", "not", "no", "says", "said", "new", "amid",
})


def _title_words(title: str) -> set[str]:
    """Extract lowercased content words from a title, stripping punctuation."""
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", title.lower())
    return {w for w in words if w not in _TITLE_STOPWORDS and len(w) >= 2}


def merge_duplicate_title_clusters(
    clusters: list[dict],
    jaccard_threshold: float = 0.45,
    max_merged_articles: int = 250,
) -> list[dict]:
    """
    Final merge pass: consolidate clusters with near-identical headlines.

    Catches the oversized-split problem where a 76-article story about one
    event (e.g., "US Fighter Jet Shot Down Over Iran") gets split by the
    50-article cap into 2-3 sub-clusters with nearly identical titles that
    the entity merge can't re-merge (due to entity blacklist + size cap).

    Title Jaccard similarity is a much stronger same-story signal than entity
    overlap — if two clusters have ≥55% title-word overlap, they are almost
    certainly the same story.

    Args:
        clusters: List of cluster dicts.
        jaccard_threshold: Minimum Jaccard similarity of title word-sets
            to trigger a merge (default 0.55).
        max_merged_articles: Maximum articles in a merged cluster. Higher
            than the entity merge cap (50) because title-match is a
            stronger signal — these are definitively the same story.
    """
    if len(clusters) <= 1:
        return clusters

    n = len(clusters)
    title_words = [_title_words(c.get("title", "")) for c in clusters]

    # Union-Find
    parent = list(range(n))
    group_size = [len(c.get("articles", [])) for c in clusters]

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            group_size[rb] += group_size[ra]

    for i in range(n):
        if not title_words[i]:
            continue
        for j in range(i + 1, n):
            if find(i) == find(j):
                continue
            if not title_words[j]:
                continue

            intersection = len(title_words[i] & title_words[j])
            union_size = len(title_words[i] | title_words[j])
            if union_size == 0:
                continue
            jaccard = intersection / union_size
            if jaccard < jaccard_threshold:
                continue

            # Size gate
            if group_size[find(i)] + group_size[find(j)] > max_merged_articles:
                continue

            union(i, j)

    # Group and merge (same pattern as merge_related_clusters)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)

    merged = []
    for root, members in groups.items():
        if len(members) == 1:
            merged.append(clusters[root])
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

        anchor = max(members, key=lambda idx: clusters[idx].get("source_count", 0))
        anchor_cluster = clusters[anchor]
        first_published = min(all_pub_dates) if all_pub_dates else ""

        merged_title = _generate_cluster_title(all_articles)
        merged_summary = _generate_cluster_summary(all_articles)
        merged_section = _determine_section(
            all_articles, merged_title, merged_summary
        )

        merged.append({
            "title": merged_title,
            "summary": merged_summary,
            "article_ids": all_article_ids,
            "source_ids": list(all_source_ids),
            "source_count": len(all_source_ids),
            "section": merged_section,
            "first_published": first_published,
            "articles": all_articles,
            **{
                k: v for k, v in anchor_cluster.items()
                if k not in ("title", "summary", "article_ids", "source_ids",
                             "source_count", "section", "first_published", "articles")
            },
        })

    return merged


def cluster_stories(
    articles: list[dict],
    similarity_threshold: float = 0.2,
    run_merge_pass: bool = True,
) -> list[dict]:
    """
    Group articles into story clusters based on content similarity.

    Two-phase approach:
        Phase 1: TF-IDF cosine similarity + agglomerative clustering.
            Threshold 0.2 (down from 0.3) captures sub-events that share
            some overlapping terms but diverge in actor/action vocabulary.
        Phase 2 (optional): Entity-overlap merge pass via merge_related_clusters().
            Consolidates clusters that represent facets of the same evolving
            story narrative (e.g., 20 Iran-war micro-clusters → 3-5 mega-clusters).

    Args:
        articles: List of article dicts with keys: id, title, summary,
            full_text, source_id, published_at, section.
        similarity_threshold: Minimum cosine similarity to consider
            two articles as covering the same story (default 0.2).
        run_merge_pass: Whether to run the entity-overlap merge pass after
            initial clustering (default True). Set False to disable for
            debugging or performance profiling.

    Returns:
        List of cluster dicts, each with:
            - title: str (generated cluster headline)
            - article_ids: list[str] (IDs of articles in this cluster)
            - source_ids: list[str] (unique source IDs)
            - source_count: int (number of unique sources)
            - section: str ("world" or "us")
            - first_published: str (ISO timestamp of earliest article)
            - articles: list[dict] (the actual article dicts for downstream use)
    """
    if not articles:
        return []

    if len(articles) == 1:
        article = articles[0]
        return [{
            "title": article.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([article]),
            "article_ids": [article.get("id", "")],
            "source_ids": [article.get("source_id", "")],
            "source_count": 1,
            "section": _determine_section([article]),
            "first_published": article.get("published_at", ""),
            "articles": [article],
        }]

    # Build TF-IDF vectors
    documents = [_build_document(a) for a in articles]

    # Filter out empty documents
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    if not valid_indices:
        return []

    valid_docs = [documents[i] for i in valid_indices]
    valid_articles = [articles[i] for i in valid_indices]

    if len(valid_docs) == 1:
        article = valid_articles[0]
        return [{
            "title": article.get("title") or "Developing Story",
            "summary": _generate_cluster_summary([article]),
            "article_ids": [article.get("id", "")],
            "source_ids": [article.get("source_id", "")],
            "source_count": 1,
            "section": _determine_section([article]),
            "first_published": article.get("published_at", ""),
            "articles": [article],
        }]

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    tfidf_matrix = vectorizer.fit_transform(valid_docs)

    # Compute cosine similarity and convert to distance
    sim_matrix = cosine_similarity(tfidf_matrix)
    # Agglomerative clustering needs a distance matrix
    distance_matrix = 1.0 - sim_matrix
    # Clip to avoid negative values from floating-point errors
    distance_matrix = np.clip(distance_matrix, 0.0, 2.0)

    # Agglomerative clustering
    distance_threshold = 1.0 - similarity_threshold
    clustering = AgglomerativeClustering(
        n_clusters=None,
        distance_threshold=distance_threshold,
        metric="precomputed",
        linkage="average",
    )
    labels = clustering.fit_predict(distance_matrix)

    # Group articles by cluster label
    cluster_map: dict[int, list[int]] = {}
    for idx, label in enumerate(labels):
        cluster_map.setdefault(label, []).append(idx)

    # Build cluster dicts
    clusters = []
    for label, indices in sorted(cluster_map.items()):
        cluster_articles = [valid_articles[i] for i in indices]

        # Collect article IDs and source IDs
        article_ids = [a.get("id", "") for a in cluster_articles]
        source_ids = list({a.get("source_id", "") for a in cluster_articles})

        # Find earliest published_at
        pub_dates = [a.get("published_at", "") for a in cluster_articles if a.get("published_at")]
        first_published = min(pub_dates) if pub_dates else ""

        cluster_title = _generate_cluster_title(cluster_articles)
        cluster_summary = _generate_cluster_summary(cluster_articles)

        clusters.append({
            "title": cluster_title,
            "summary": cluster_summary,
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(
                cluster_articles, cluster_title, cluster_summary
            ),
            "first_published": first_published,
            "articles": cluster_articles,
        })

    # Cluster purity check: eject articles that don't belong.
    # If an article's max similarity to any other article in the cluster
    # is below 0.08, it was merged by shared stopwords or source proximity,
    # not content. Eject it into a singleton cluster.
    purified: list[dict] = []
    ejected_articles: list[dict] = []
    for c in clusters:
        arts = c.get("articles", [])
        if len(arts) <= 3:
            purified.append(c)
            continue
        # Re-vectorize this cluster's articles
        docs = [_build_document(a) for a in arts]
        try:
            vec = TfidfVectorizer(max_features=3000, stop_words="english", min_df=1, max_df=0.95)
            mat = vec.fit_transform(docs)
            sims = cosine_similarity(mat)
            keep_idx = []
            eject_idx = []
            for i in range(len(arts)):
                # Max similarity to any OTHER article in the cluster
                row = sims[i].copy()
                row[i] = 0.0  # exclude self
                max_sim = row.max()
                if max_sim < 0.08:
                    eject_idx.append(i)
                else:
                    keep_idx.append(i)
            if eject_idx and keep_idx:
                # Rebuild the cluster without outliers
                kept = [arts[i] for i in keep_idx]
                c["articles"] = kept
                c["article_ids"] = [a.get("id", "") for a in kept]
                c["source_ids"] = list({a.get("source_id", "") for a in kept})
                c["source_count"] = len(c["source_ids"])
                ejected_articles.extend(arts[i] for i in eject_idx)
            purified.append(c)
        except Exception:
            purified.append(c)  # on any error, keep the original
    clusters = purified
    # Ejected articles become singleton clusters (they'll be filtered out
    # by the 2+ source requirement downstream, or form their own micro-clusters).
    for a in ejected_articles:
        clusters.append({
            "title": a.get("title") or "Developing Story",
            "summary": a.get("summary", ""),
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")],
            "source_count": 1,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", ""),
            "articles": [a],
        })

    # Split oversized clusters: re-cluster with a tighter threshold.
    # Prevents 100+ article mega-clusters from TF-IDF over-merging on
    # shared political vocabulary (e.g., "Trump", "war", "Iran").
    MAX_CLUSTER_SIZE = 80
    split_clusters: list[dict] = []
    for c in clusters:
        if len(c.get("articles", [])) > MAX_CLUSTER_SIZE:
            sub = cluster_stories(
                c["articles"],
                similarity_threshold=similarity_threshold * 0.6,
                run_merge_pass=False,
            )
            split_clusters.extend(sub)
        else:
            split_clusters.append(c)
    clusters = split_clusters

    # Phase 2: entity-overlap merge pass
    # Consolidates micro-clusters that represent sub-events of the same
    # ongoing story (e.g., 20 Iran-war fragments → 3-5 mega-clusters).
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_related_clusters(clusters)

    # Phase 3: title-similarity merge pass
    # Catches near-duplicate clusters that survived the 50-article split and
    # entity merge (e.g., 3 clusters all titled "US Fighter Jet Shot Down
    # Over Iran" with 25/30/21 sources each). Title Jaccard is a stronger
    # same-story signal than entity overlap, so it uses a higher size cap.
    if run_merge_pass and len(clusters) > 1:
        clusters = merge_duplicate_title_clusters(clusters)

    return clusters
