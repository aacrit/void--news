"""
Story clustering engine for the void --news pipeline.

Groups articles covering the same story/event into clusters.
Each cluster represents one news story as seen through multiple sources.

Uses rule-based NLP (no LLM API calls):
    - TF-IDF vectorization of article titles + first 200 words
    - Cosine similarity via sklearn
    - Agglomerative clustering with distance threshold
    - Cluster title generation from most common named entities (spaCy NER)
"""

from collections import Counter

from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from utils.nlp_shared import get_nlp


def _build_document(article: dict) -> str:
    """Build a text document from title + first 200 words of full_text."""
    title = article.get("title", "") or ""
    full_text = article.get("full_text", "") or ""
    words = full_text.split()[:200]
    body_snippet = " ".join(words)
    return f"{title} {body_snippet}".strip()


def _generate_cluster_title(articles: list[dict]) -> str:
    """
    Generate a cluster title from the most common named entities
    across articles in the cluster.
    """
    nlp = get_nlp()
    entity_counter: Counter = Counter()

    for article in articles[:20]:  # limit for performance
        title = article.get("title", "") or ""
        doc = nlp(title)
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "EVENT", "NORP"):
                entity_counter[ent.text] += 1

    if not entity_counter:
        # Fallback: use the shortest title from the cluster
        titles = [a.get("title", "") for a in articles if a.get("title")]
        if titles:
            return min(titles, key=len)
        return "Untitled Story"

    # Build title from top entities
    top_entities = [name for name, _ in entity_counter.most_common(3)]
    return " / ".join(top_entities)


def _determine_section(articles: list[dict]) -> str:
    """Determine cluster section by majority vote of article sections."""
    sections: Counter = Counter()
    for article in articles:
        section = article.get("section", "") or ""
        if section:
            sections[section.lower()] += 1

    if not sections:
        return "world"

    top_section = sections.most_common(1)[0][0]
    # Map to standard sections
    if any(kw in top_section for kw in ("us", "domestic", "nation", "national", "america")):
        return "us"
    return "world"


def cluster_stories(
    articles: list[dict],
    similarity_threshold: float = 0.3,
) -> list[dict]:
    """
    Group articles into story clusters based on content similarity.

    Args:
        articles: List of article dicts with keys: id, title, summary,
            full_text, source_id, published_at, section.
        similarity_threshold: Minimum cosine similarity to consider
            two articles as covering the same story (default 0.3).

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
            "title": article.get("title", "Untitled"),
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
            "title": article.get("title", "Untitled"),
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

        clusters.append({
            "title": _generate_cluster_title(cluster_articles),
            "article_ids": article_ids,
            "source_ids": source_ids,
            "source_count": len(source_ids),
            "section": _determine_section(cluster_articles),
            "first_published": first_published,
            "articles": cluster_articles,
        })

    return clusters
