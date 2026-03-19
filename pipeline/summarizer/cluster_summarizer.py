"""
Cluster-level headline and summary generation using Gemini Flash.

Minimizes API usage by only summarizing high-value clusters:
    - 3+ sources (2-source clusters use rule-based — sufficient quality)
    - Sorted by source_count descending (most-covered stories first)
    - Stops when the per-run call cap is reached

Falls back to rule-based generation (existing pipeline behavior) when
Gemini is unavailable, fails, or the cluster doesn't qualify.
"""

from .gemini_client import generate_json, is_available, calls_remaining


_CLUSTER_PROMPT = """\
You are an editor at a neutral news wire service. Given articles about the \
same story from different sources, generate a comprehensive briefing so a \
reader never needs to leave this page to understand the full story.

1. **headline**: A neutral, factual headline (60-100 chars). No clickbait, \
no sensationalism, no question marks. State what happened.

2. **summary**: A comprehensive 150-250 word factual briefing that tells \
the complete story. Structure it as:
   - Opening: What happened, when, and where (the core event)
   - Context: Why it matters, what led to this, key background
   - Key details: Important names, numbers, quotes, and specifics from \
across all sources
   - What's next: Any stated next steps, reactions, or expected developments
Write in clear, neutral prose. A reader should fully understand the story \
from this summary alone without clicking any source link.

3. **consensus**: 3-5 specific factual points all sources agree on. \
Reference concrete details (names, numbers, dates, quotes), not generic \
observations like "sources agree on the facts."

4. **divergence**: 2-4 specific ways sources differ in coverage. Reference \
which types of sources (e.g. "US outlets", "international media", \
"independent sources") emphasize, downplay, or omit what. Be specific \
about the framing differences.

Articles:
{articles_block}

Return JSON: {{"headline": str, "summary": str, "consensus": [str], "divergence": [str]}}\
"""

# Minimum sources for a cluster to qualify for Gemini summarization.
# 2-source clusters don't benefit much from LLM synthesis — the rule-based
# "pick best title" approach works fine. 3+ sources is where synthesis shines.
_MIN_SOURCES = 3


def _build_articles_block(articles: list[dict], max_articles: int = 10) -> str:
    """
    Build the articles context block for the prompt.

    Limits to max_articles and includes longer summaries to give Gemini
    more material for a comprehensive briefing.
    """
    lines = []
    for i, art in enumerate(articles[:max_articles]):
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()
        source = (art.get("source_slug", "") or art.get("source_id", "") or "unknown")

        # Allow longer summaries for richer synthesis
        if len(summary) > 400:
            summary = summary[:397] + "..."

        lines.append(f"[{i + 1}] {source}: {title}")
        if summary:
            lines.append(f"    {summary}")
        lines.append("")

    return "\n".join(lines)


def summarize_cluster(articles: list[dict]) -> dict | None:
    """
    Generate headline, summary, consensus, and divergence for a cluster.

    Returns None if Gemini is unavailable, fails, or call cap reached.
    """
    if not is_available() or calls_remaining() <= 0:
        return None

    if not articles:
        return None

    articles_block = _build_articles_block(articles)
    prompt = _CLUSTER_PROMPT.format(articles_block=articles_block)
    result = generate_json(prompt)

    if not result:
        return None

    # Validate response shape
    headline = result.get("headline", "")
    summary = result.get("summary", "")
    consensus = result.get("consensus", [])
    divergence = result.get("divergence", [])

    if not isinstance(headline, str) or not headline.strip():
        return None
    if not isinstance(summary, str) or not summary.strip():
        return None
    if not isinstance(consensus, list):
        consensus = []
    if not isinstance(divergence, list):
        divergence = []

    consensus = [str(c) for c in consensus if c]
    divergence = [str(d) for d in divergence if d]

    return {
        "headline": headline.strip()[:500],
        "summary": summary.strip(),
        "consensus": consensus,
        "divergence": divergence,
    }


def summarize_clusters_batch(clusters: list[dict]) -> dict[int, dict]:
    """
    Summarize only high-value clusters, returning results keyed by index.

    Selection criteria (to minimize API calls):
        1. Must have 3+ sources (2-source clusters use rule-based)
        2. Processed in descending source_count order (biggest stories first)
        3. Stops when per-run call cap is reached

    Args:
        clusters: List of cluster dicts, each with "articles" and
            "source_count" keys.

    Returns:
        Dict mapping cluster index -> summarize_cluster result.
        Missing indices = use rule-based fallback.
    """
    if not is_available():
        return {}

    # Build list of (original_index, source_count) for qualifying clusters
    candidates = []
    for i, cluster in enumerate(clusters):
        source_count = cluster.get("source_count", 0) or len(cluster.get("articles", []))
        if source_count >= _MIN_SOURCES:
            candidates.append((i, source_count))

    # Process highest-source-count clusters first (most value per API call)
    candidates.sort(key=lambda x: x[1], reverse=True)

    results: dict[int, dict] = {}
    processed = 0

    for idx, _count in candidates:
        if calls_remaining() <= 0:
            remaining = len(candidates) - processed
            print(f"  Call cap reached after {processed} clusters "
                  f"({remaining} remaining will use rule-based)")
            break

        articles = clusters[idx].get("articles", [])
        result = summarize_cluster(articles)
        if result:
            results[idx] = result
            processed += 1

    skipped = len(clusters) - processed
    print(f"  Gemini: {processed} clusters summarized, "
          f"{skipped} using rule-based (cap: {calls_remaining()} calls left)")

    return results
