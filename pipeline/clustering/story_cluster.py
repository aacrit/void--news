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
# v6.2 (2026-05-15): added Yonhap-style "(3rd LD)" / "(2nd LD)" lead-development
# prefixes that were bleeding through to world top 50 titles (audit found
# "(3rd LD) Seoul official..." at rank #25).
_WIRE_PREFIX_RE = re.compile(
    r'^\s*(?:\((?:LEAD|URGENT|CORRECTED|UPDATE(?:\s*\d*)?|RECASTS?|ADDS?|WRAPUP|NEWSALERT'
    r'|\d+(?:st|nd|rd|th)\s+LD)\)\s*)'
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

    NOTE (UAT 2026-05-13, P1-9 stub-words):
    Roughly 47% of fetched articles have word_count < 100 because RSS feeds
    publish stub bodies without a full-text scrape fallback. trafilatura was
    NOT added to requirements.txt in this fix (would have been the cleanest
    remediation), so these short articles still enter clustering. They do NOT
    distort the TF-IDF math (low-content rows simply contribute little signal
    via their title), but they DO inflate single-source cluster counts. If a
    future fix wires trafilatura into the fetchers, this comment can be
    removed. Until then: short articles are tolerated, not filtered. The
    word_count column is already populated by `_compute_word_count()` so any
    downstream filter only needs `article.get('word_count', 0) >= 100`.
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
# v6.1 (2026-05-14): Head-of-state pairings that act as legitimate event
# anchors when paired with summit/meeting tokens. The Trump-Xi summit's
# four sub-angles ("Taiwan warning", "Hormuz agreement", "WH invite",
# "China arrival") share only common-filtered entities (Trump, China,
# Iran, US) — the entity-overlap merge never fires, leaving 4 clusters
# of the same event in the top 50. This list, paired with summit tokens,
# unblocks legitimate same-event merges without admitting general
# transitive bridges. Substring-matched against title+summary; case-insens.
# TODO: review quarterly — Sunak/Starmer, Trudeau/Carney, etc. drift.
_HEAD_OF_STATE_NAMES = frozenset({
    "xi jinping", "vladimir putin", "putin",
    "narendra modi", "modi",
    "recep tayyip erdogan", "erdogan", "erdoğan",
    "luiz inácio lula", "lula",
    "keir starmer", "starmer",
    "emmanuel macron", "macron",
    "friedrich merz", "olaf scholz", "scholz",
    "mark carney", "justin trudeau", "carney", "trudeau",
    "benjamin netanyahu", "netanyahu",
    "mohammed bin salman", "mbs",
    "volodymyr zelenskyy", "volodymyr zelensky", "zelenskyy", "zelensky",
    "kim jong un", "kim jong-un",
    "anthony albanese", "albanese",
    "shigeru ishiba", "ishiba",
    "yoon suk yeol", "lee jae-myung",
    "claudia sheinbaum", "sheinbaum",
    "javier milei", "milei",
    "giorgia meloni", "meloni",
    "donald tusk", "tusk",
    "shehbaz sharif", "asim munir",
    "pope leo", "pope francis",
})

# Event-context tokens. A pairing of head-of-state + summit token in
# title/summary of two clusters strongly suggests the same diplomatic event.
_SUMMIT_TOKENS = frozenset({
    "summit", "meeting", "talks", "accord", "communique", "communiqué",
    "treaty", "bilateral", "trilateral", "agreement", "diplomatic",
    "white house", "kremlin", "g20", "g7", "brics", "shanghai cooperation",
    "phone call", "press conference", "joint statement",
})


def _extract_head_of_state_hits(articles: list[dict]) -> tuple[set[str], set[str]]:
    """Return (heads_of_state_seen, summit_tokens_seen) from up to 10 articles'
    titles + summaries. Substring match, lowercase. Used by
    merge_related_clusters to detect same-summit cross-cluster fragments.
    """
    heads: set[str] = set()
    tokens: set[str] = set()
    for article in articles[:10]:
        title = (article.get("title", "") or "").lower()
        summary = (article.get("summary", "") or "").lower()
        text = f"{title} {summary}"
        if not text.strip():
            continue
        for name in _HEAD_OF_STATE_NAMES:
            if name in text:
                heads.add(name)
        for tok in _SUMMIT_TOKENS:
            if tok in text:
                tokens.add(tok)
    return heads, tokens


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
    # v5.7: Geopolitical hotspots that act as transitive merge bridges
    # between unrelated stories (e.g., Iran links BJP politics to
    # Australian athletics to US diplomacy via ceasefire/israel chains).
    "iran", "iranian", "iran's",
    "israel", "israeli", "israel's",
    "india", "indian", "india's",
    "pakistan", "pakistani", "pakistan's",
    "ceasefire", "cease-fire",
    "gaza", "west bank", "palestine", "palestinian",
    "hezbollah", "hamas",
    "modi", "narendra modi",
    "nato", "pentagon",
    "australia", "australian",
    "germany", "german",
    "france", "french",
    "japan", "japanese",
    "south korea", "north korea",
    "middle east",
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
    max_cluster_articles: int = 30,
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
    # v6.1: head-of-state + summit-token hits for same-event merge exception.
    # Cheap substring scan; reuses article titles+summaries (no spaCy).
    cluster_hos: list[tuple[set[str], set[str]]] = [
        _extract_head_of_state_hits(c.get("articles", [])) for c in clusters
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
                # v6.1: Head-of-state pairing exception. Trump-Xi summit
                # sub-angles share only common-filtered entities — bypass
                # the normal threshold when both clusters mention the same
                # head-of-state AND a summit/meeting token. The HoS list is
                # narrow and the summit-token requirement blocks generic
                # transitive bridges (a "Modi domestic" cluster won't carry
                # summit tokens, so it won't merge with "Modi-Trump summit").
                hos_i, tok_i = cluster_hos[i]
                hos_j, tok_j = cluster_hos[j]
                shared_hos = hos_i & hos_j
                shared_tok = tok_i & tok_j
                if not (shared_hos and shared_tok):
                    continue
                # Heads-of-state pairing matched — fall through into the
                # time + size gates below, which still apply.

            # Time spread gate: don't merge stories far apart in time
            ti, tj = timestamps[i], timestamps[j]
            if ti is not None and tj is not None:
                spread_hours = abs((ti - tj).total_seconds()) / 3600.0
                if spread_hours > max_age_spread_hours:
                    continue

            # Size gate: prevent runaway mega-clusters from transitive merges.
            # Relaxed for high-source cluster pairs (both 10+ sources) — these
            # are major stories that SHOULD merge (e.g., Iran F-15 fragments).
            combined_size = group_size[find(i)] + group_size[find(j)]
            src_i = len(set(a.get("source_id", "") for a in clusters[i].get("articles", [])))
            src_j = len(set(a.get("source_id", "") for a in clusters[j].get("articles", [])))
            if src_i >= 10 and src_j >= 10:
                size_cap = 50
            elif src_i >= 5 and src_j >= 5:
                size_cap = 35
            else:
                size_cap = max_cluster_articles
            if combined_size > size_cap:
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
    "this", "not", "no", "says", "said", "new", "amid", "more", "than",
    "about", "how", "what", "why", "who", "when", "where", "which",
    "will", "would", "could", "should", "may", "might", "can",
    "reports", "report", "sources", "according", "also", "first",
    "two", "one", "three", "us", "announces", "amid", "while",
})


def _title_words(title: str) -> set[str]:
    """Extract lowercased content words from a title, stripping punctuation."""
    words = re.findall(r"[a-z0-9](?:[a-z0-9'-]*[a-z0-9])?", title.lower())
    return {w for w in words if w not in _TITLE_STOPWORDS and len(w) >= 2}


def merge_duplicate_title_clusters(
    clusters: list[dict],
    jaccard_threshold: float = 0.45,
    max_merged_articles: int = 100,
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

            # Relaxed threshold for high-source cluster pairs: both 10+ sources
            # are almost certainly sub-events of the same mega-story.
            # "Iran Air Defense System" + "US F-15 Shot Down Over Iran" share
            # only "iran" in title words (Jaccard ~0.15) but are the same story.
            src_i = clusters[i].get("source_count", 0)
            src_j = clusters[j].get("source_count", 0)
            # Relaxed for quality pairs: both 5+ sources are likely sub-events
            # of the same story. 10+ src pairs get even more relaxed threshold.
            if src_i >= 10 and src_j >= 10:
                effective_threshold = 0.40
            elif src_i >= 5 and src_j >= 5:
                effective_threshold = 0.42
            else:
                effective_threshold = jaccard_threshold

            if jaccard < effective_threshold:
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


def split_disjoint_country_clusters(clusters: list[dict]) -> list[dict]:
    """
    v6.1 (2026-05-14): post-Phase-3 split pass.

    Phase 1 TF-IDF agglomerative at threshold 0.2 sometimes fuses two
    genuinely unrelated stories that share generic regional vocabulary
    (e.g., Estonia conscript-language law + Germany scraps heating
    mandate — both "EU" + "law" + "policy"). The entity-merge (Phase 2)
    and title-Jaccard merge (Phase 3) only merge; nothing splits.

    Algorithm:
        1. For each cluster of ≥3 articles, extract per-article country
           GPEs from titles via title-only NER (cheap).
        2. Build union-find over "typed" articles (those with a non-empty
           country set). Two articles unite when their country sets
           intersect.
        3. If exactly two groups emerge, both ≥2 articles, and the union
           of their country sets is disjoint pairwise, split the cluster
           along that partition.
        4. "Empty country" articles (op-eds, abstract commentary) and
           singleton typed articles join the LARGER group (safer default).

    Conservative by design — only handles the 2-group case. 3-way splits
    are rare in practice and would risk over-splitting NATO/G20-style
    multi-country clusters.

    Returns: same list when no split criteria met; expanded list when
    splits occur.
    """
    nlp = get_nlp()
    out: list[dict] = []

    for c in clusters:
        articles = c.get("articles", [])
        if len(articles) < 3:
            out.append(c)
            continue

        country_sets: list[set[str]] = []
        for a in articles:
            title = (a.get("title", "") or "")[:200]
            cs: set[str] = set()
            if title.strip():
                doc = nlp(title)
                for ent in doc.ents:
                    if ent.label_ == "GPE":
                        cs.add(ent.text.lower().strip())
            country_sets.append(cs)

        typed = [i for i, cs in enumerate(country_sets) if cs]
        empty = [i for i, cs in enumerate(country_sets) if not cs]

        if len(typed) < 4:  # need at least 2+2 typed to split
            out.append(c)
            continue

        # Union-Find on typed articles by country-set overlap
        parent = {i: i for i in typed}

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        for i_idx, i in enumerate(typed):
            for j in typed[i_idx + 1:]:
                if country_sets[i] & country_sets[j]:
                    ri, rj = find(i), find(j)
                    if ri != rj:
                        parent[ri] = rj

        groups_map: dict[int, list[int]] = {}
        for i in typed:
            groups_map.setdefault(find(i), []).append(i)

        sized = sorted(
            [g for g in groups_map.values() if len(g) >= 2],
            key=len,
            reverse=True,
        )
        if len(sized) != 2:
            out.append(c)
            continue

        # Verify pairwise country-disjoint
        gA_countries: set[str] = set()
        gB_countries: set[str] = set()
        for i in sized[0]:
            gA_countries |= country_sets[i]
        for i in sized[1]:
            gB_countries |= country_sets[i]
        if gA_countries & gB_countries:
            out.append(c)
            continue

        # Singletons typed → larger group (sized[0]); empties → larger group
        leftover_typed = [
            i for i in typed
            if i not in set(sized[0]) and i not in set(sized[1])
        ]
        group_A = list(sized[0]) + leftover_typed + empty
        group_B = list(sized[1])

        # Build two new clusters
        def _build(article_indices: list[int]) -> dict:
            grp_articles = [articles[i] for i in article_indices]
            grp_article_ids = [
                c["article_ids"][i] for i in article_indices
                if i < len(c.get("article_ids", []))
            ] if c.get("article_ids") else [a.get("id", "") for a in grp_articles]
            grp_source_ids = list({
                a.get("source_id", "") for a in grp_articles if a.get("source_id")
            })
            pub_dates = [a.get("published_at", "") for a in grp_articles if a.get("published_at")]
            first_pub = min(pub_dates) if pub_dates else c.get("first_published", "")
            new_title = _generate_cluster_title(grp_articles)
            new_summary = _generate_cluster_summary(grp_articles)
            new_section = _determine_section(grp_articles, new_title, new_summary)
            return {
                "title": new_title,
                "summary": new_summary,
                "article_ids": grp_article_ids,
                "source_ids": grp_source_ids,
                "source_count": len(grp_source_ids),
                "section": new_section,
                "first_published": first_pub,
                "articles": grp_articles,
                **{
                    k: v for k, v in c.items()
                    if k not in ("title", "summary", "article_ids", "source_ids",
                                 "source_count", "section", "first_published", "articles")
                },
            }

        out.append(_build(group_A))
        out.append(_build(group_B))

    return out


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

    # Partition into vectorizable vs. empty-document articles.
    # Empty-document articles (both title and full_text blank/whitespace) cannot
    # be TF-IDF vectorized, but dropping them silently turns them into DB
    # orphans (no cluster_articles row, never reach the frontend feed).
    # Instead, emit each empty-document article as a singleton cluster so it
    # still flows downstream.
    valid_indices = [i for i, d in enumerate(documents) if d.strip()]
    empty_indices = [i for i, d in enumerate(documents) if not d.strip()]

    empty_singletons: list[dict] = []
    for i in empty_indices:
        a = articles[i]
        empty_singletons.append({
            "title": a.get("title") or "Developing Story",
            "summary": a.get("summary", "") or (a.get("full_text", "") or "")[:500],
            "article_ids": [a.get("id", "")],
            "source_ids": [a.get("source_id", "")] if a.get("source_id") else [],
            "source_count": 1 if a.get("source_id") else 0,
            "section": _determine_section([a]),
            "first_published": a.get("published_at", "") or "",
            "articles": [a],
        })

    if not valid_indices:
        return empty_singletons

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
        }] + empty_singletons

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
        if len(arts) <= 5:
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

    # Phase 4: country-disjoint split pass (v6.1, 2026-05-14)
    # Splits clusters that fused two unrelated regional stories on shared
    # generic vocabulary (e.g., Estonia conscript law + Germany heating
    # mandate). Conservative: only the 2-group disjoint case triggers.
    if run_merge_pass and len(clusters) > 1:
        clusters = split_disjoint_country_clusters(clusters)

    # Final pass: recount source_count from actual articles.
    # Merges can leave stale counts when source_ids lists are concatenated
    # but not deduped, or when articles are ejected by the purity check.
    for c in clusters:
        actual_sources = {a.get("source_id", "") for a in c.get("articles", []) if a.get("source_id")}
        c["source_ids"] = list(actual_sources)
        c["source_count"] = len(actual_sources)

    # Append empty-document singletons so they flow downstream and reach the
    # frontend feed rather than becoming silent DB orphans. They bypass the
    # merge passes (no document to compare against) and are appended here.
    if empty_singletons:
        clusters.extend(empty_singletons)

    return clusters
