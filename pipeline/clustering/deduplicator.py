"""
Content-based deduplication for the void --news pipeline.

Removes near-duplicate articles that share different URLs but contain
substantially the same text (syndicated/wire content).

Uses TF-IDF + cosine similarity on title + first ~1000 characters of text.
When duplicates are found, keeps the article from the higher-tier source.

No LLM API calls -- scikit-learn TF-IDF and cosine similarity only.
"""

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


# Source tier priority: higher value = higher priority (kept over lower)
TIER_PRIORITY = {
    "us_major": 3,
    "international": 2,
    "independent": 1,
}

# Process in chunks if more than this many articles (memory safety)
CHUNK_SIZE = 500


def _build_fingerprint(article: dict) -> str:
    """Build a text fingerprint from title + first ~1000 chars of text."""
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""
    return f"{title} {full_text[:1000]}".strip()


def _get_tier_priority(article: dict) -> int:
    """Get the source tier priority for an article."""
    tier = article.get("tier", "") or ""
    return TIER_PRIORITY.get(tier, 0)


def _get_text_length(article: dict) -> int:
    """Get word count or estimate from full_text."""
    wc = article.get("word_count", 0) or 0
    if wc > 0:
        return wc
    full_text = article.get("full_text", "") or ""
    return len(full_text.split())


def _deduplicate_chunk(
    articles: list[dict],
    similarity_threshold: float,
) -> list[dict]:
    """Deduplicate a single chunk of articles."""
    if len(articles) <= 1:
        return articles

    # Build fingerprints, tracking which articles have usable text
    fingerprints = []
    valid_indices = []
    for i, article in enumerate(articles):
        fp = _build_fingerprint(article)
        if fp.strip():
            fingerprints.append(fp)
            valid_indices.append(i)

    # Articles with no text at all: keep them (cannot compare)
    no_text_indices = set(range(len(articles))) - set(valid_indices)

    if len(fingerprints) <= 1:
        return articles

    # TF-IDF vectorization
    vectorizer = TfidfVectorizer(
        max_features=5000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=1,
        max_df=0.95,
    )
    try:
        tfidf_matrix = vectorizer.fit_transform(fingerprints)
    except ValueError:
        # All documents are empty after stop word removal
        return articles

    # Pairwise cosine similarity
    sim_matrix = cosine_similarity(tfidf_matrix)

    # Find duplicate pairs using Union-Find for transitive closure
    n = len(valid_indices)
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

    # Group articles that are near-duplicates
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= similarity_threshold:
                union(i, j)

    # For each group, pick the best article
    groups: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)

    keep_indices: set[int] = set(no_text_indices)

    for group_members in groups.values():
        if len(group_members) == 1:
            # No duplicates: keep it
            keep_indices.add(valid_indices[group_members[0]])
        else:
            # Pick the best: highest tier, then most text
            best = max(
                group_members,
                key=lambda idx: (
                    _get_tier_priority(articles[valid_indices[idx]]),
                    _get_text_length(articles[valid_indices[idx]]),
                ),
            )
            keep_indices.add(valid_indices[best])

    return [articles[i] for i in sorted(keep_indices)]


def deduplicate_articles(
    articles: list[dict],
    similarity_threshold: float = 0.85,
) -> list[dict]:
    """
    Remove near-duplicate articles based on text similarity.

    Uses TF-IDF + cosine similarity on title + first ~1000 characters.
    When duplicates are found, keeps the article from the higher-tier source.

    Args:
        articles: List of article dicts with title, full_text, tier, word_count.
        similarity_threshold: Cosine similarity above which two articles
            are considered duplicates (default 0.85).

    Returns:
        Deduplicated list of articles.
    """
    if len(articles) <= 1:
        return articles

    # For manageable batch sizes, process directly
    if len(articles) <= CHUNK_SIZE:
        return _deduplicate_chunk(articles, similarity_threshold)

    # For large batches, process in overlapping chunks to catch cross-chunk dupes.
    # First pass: deduplicate within chunks
    chunks = [
        articles[i:i + CHUNK_SIZE]
        for i in range(0, len(articles), CHUNK_SIZE)
    ]
    deduped_chunks = [
        _deduplicate_chunk(chunk, similarity_threshold)
        for chunk in chunks
    ]

    # Flatten and do a second pass on the combined result if still large
    combined = []
    for chunk in deduped_chunks:
        combined.extend(chunk)

    # Second pass: if the combined result fits in one chunk, deduplicate again
    if len(combined) <= CHUNK_SIZE:
        return _deduplicate_chunk(combined, similarity_threshold)

    # Otherwise return what we have (within-chunk dedup is still valuable)
    return combined
