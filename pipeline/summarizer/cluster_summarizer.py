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


# ---------------------------------------------------------------------------
# System instruction — persistent editorial voice, set once per API call.
# Defines void --news tone: neutral, attribution-heavy, no sensationalism.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are a senior correspondent and copy editor at void --news, a neutral news \
intelligence service. Your role is to synthesize news coverage from multiple \
sources into factual briefings. You have no political perspective. You describe \
what sources report; you do not editorialize.

Core standards that apply to all output:
- Active voice. Present tense for current and recent events.
- Every significant factual claim is attributed to a named or specific source.
- No loaded, charged, or sensationalist language — including language borrowed \
from source headlines.
- No value judgments. Prohibited adjectives: controversial, divisive, landmark, \
historic, shocking, stunning, explosive, devastating, unprecedented (as rhetorical \
emphasis), radical, extreme, common-sense.
- No unattributed predictions or expert opinions. "Experts say" without a named \
or described expert is not attribution.
- Neutral framing of competing legitimate perspectives. No false balance on \
empirical questions with clear factual consensus.
- Precise language: name individuals when known, state exact figures, specify \
locations when central.
- NEVER use bracketed citations, footnotes, or reference markers like [1], [2,5], \
[Source], (1), etc. This is a news briefing, not an academic paper. Attribute \
inline using natural language ("according to...", "...X reported").\
"""

# ---------------------------------------------------------------------------
# User prompt template — per-call task injected with article context.
# {context_line} and {articles_block} are replaced at call time.
# ---------------------------------------------------------------------------
_USER_PROMPT_TEMPLATE = """\
Analyze the following news cluster and return a JSON object with exactly four \
fields: headline, summary, consensus, divergence.

{context_line}
ARTICLES:
{articles_block}

---

TASK 1 — headline (string)
Write an 8-12 word factual headline. Count the words carefully.
- Title Case. Active voice. Present tense.
- State the action, the actor, and location if essential.
- No question marks, exclamation marks, or ellipses.
- Prohibited words: crackdown, explosive, bombshell, shocking, stunning, chaos, \
chaotic, slams, blasts, doubles down, firestorm, war of words, crisis (unless an \
official designation).
- Do not reproduce sensationalist language from source headlines.
Good: "Senate Passes $1.2 Trillion Infrastructure Bill After Weekend Vote"
Bad: "Shocking Vote Shakes Washington as Senate Acts on Roads"

---

TASK 2 — summary (string, 150-250 words)
Write a factual briefing in inverted pyramid structure.

Paragraph 1 (1-2 sentences): The single most newsworthy fact — what happened, \
who, when, where. Do not open with "According to." Lead with the event, then \
attribute in the same sentence or the next.
Paragraph 2 (2-3 sentences): Context and significance. Why this matters, what \
preceded it. Attribute all background claims.
Paragraph 3 (2-3 sentences): Key specifics. Named individuals, exact figures, \
direct quotes, competing stated positions. Represent perspectives with equal \
syntactic weight.
Final sentence: Next steps, a deadline, an expected decision, or stated \
consequences.

Prohibited constructions:
- "In a stunning/shocking/unprecedented development..."
- "The world watched as..."
- "Experts say..." or "Analysts believe..." without named or described attribution
- "...raising questions about..." (vague concern framing)
- "...sparking outrage/controversy..." (importing reaction framing)
- Any adjective that expresses editorial judgment rather than factual description
- Bracketed citations or reference numbers like [1], [2,5], [Source 3], (1). \
This is a news article, not a research paper. Use natural inline attribution.

---

TASK 3 — consensus (array of 3-5 strings)
List 3-5 specific factual points confirmed across all or most sources.
- One sentence per point.
- Specific: include names, numbers, dates, official positions, stated figures.
- Do not state the obvious ("sources agree the event occurred").
- Frame as factual confirmation: "All sources report that..." or name the \
specific verified fact directly.
- Prohibited: generic observations, unattributed interpretive claims.

---

TASK 4 — divergence (array of 2-4 strings)
List 2-4 observable ways sources differ in what they cover, emphasize, or frame.
- One sentence per point.
- Describe coverage patterns, not outlet credibility or character.
- Reference outlet type where useful (US major outlets, international sources, \
independent media) — not specific outlet names.
- Permitted verbs: emphasize, include, omit, lead with, frame as, devote more \
coverage to, focus on, give less prominence to.
- Prohibited words: bias, ignore, spin, push, hide, downplay, agenda, chose not \
to report.
- When sources cite conflicting verifiable facts, describe the conflict neutrally: \
"US and international outlets cite differing figures for [specific metric]."

---

Return JSON only. No markdown fences. No text outside the JSON object.

{{"headline": "...", "summary": "...", "consensus": ["...", ...], "divergence": ["...", ...]}}\
"""

# ---------------------------------------------------------------------------
# Quality gate — prohibited terms scanned after generation.
# Warnings are logged but results are never discarded (zero extra API calls).
# ---------------------------------------------------------------------------
_PROHIBITED_TERMS = frozenset({
    "shocking", "stunned", "stunning", "explosive", "bombshell", "devastating",
    "chaos", "chaotic", "firestorm", "crackdown", "slams", "blasts",
    "doubles down", "war of words", "sparking outrage", "raising questions",
    "in an unprecedented", "in a stunning", "the world watched",
    "experts say", "analysts believe", "experts believe", "analysts say",
    "controversial", "divisive", "landmark", "historic",
    "radical", "extreme", "common-sense",
})

# Minimum sources for a cluster to qualify for Gemini summarization.
# 2-source clusters don't benefit much from LLM synthesis — the rule-based
# "pick best title" approach works fine. 3+ sources is where synthesis shines.
_MIN_SOURCES = 3


def _check_quality(result: dict, cluster_id: str | int = "") -> None:
    """
    Log quality warnings for out-of-spec generated content.

    Checks headline word count (target: 8-12 words) and scans all text
    fields for prohibited sensationalist or value-laden terms.

    Does not modify or discard the result — warnings are surfaced to the
    analytics-expert during post-run audit.
    """
    headline = result.get("headline", "")
    word_count = len(headline.split())
    if not (8 <= word_count <= 12):
        print(
            f"  [quality] Headline word count {word_count} (expected 8-12): "
            f"{headline!r}"
        )

    # Scan headline + summary + all consensus + all divergence items
    all_text = " ".join([
        headline,
        result.get("summary", ""),
        *result.get("consensus", []),
        *result.get("divergence", []),
    ]).lower()

    found = [t for t in _PROHIBITED_TERMS if t in all_text]

    # Check for bracketed citations [1], [2,5], [Source 3], etc.
    import re
    bracket_refs = re.findall(r'\[\d[\d,\s]*\]|\[source\s*\d*\]', all_text)
    if bracket_refs:
        found.extend(f"citation:{ref}" for ref in bracket_refs[:3])

    if found:
        print(
            f"  [quality] Prohibited terms in cluster {cluster_id}: {found}"
        )


def _build_context_line(articles: list[dict]) -> str:
    """
    Build a one-line cluster metadata header for the prompt.

    Tells Gemini total article count and tier distribution so it can
    calibrate synthesis depth — without exposing individual outlet names.
    """
    total = len(articles)
    tier_counts: dict[str, int] = {}
    for art in articles:
        tier = (art.get("tier", "") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    parts = []
    if tier_counts.get("us_major"):
        parts.append(f"{tier_counts['us_major']} US major")
    if tier_counts.get("international"):
        parts.append(f"{tier_counts['international']} international")
    if tier_counts.get("independent"):
        parts.append(f"{tier_counts['independent']} independent")

    distribution = ", ".join(parts) if parts else "mixed sources"
    return f"Cluster: {total} articles from {distribution} outlets.\n"


def _build_articles_block(articles: list[dict], max_articles: int = 10) -> str:
    """
    Build the articles context block for the prompt.

    Replaces source slugs with tier-based labels (US Source, International
    Source, Independent Source) to prevent Gemini from applying outlet-level
    political heuristics learned from training data.

    Limits to max_articles and includes summaries up to 400 chars to give
    Gemini sufficient material for comprehensive synthesis.
    """
    _TIER_LABEL_MAP = {
        "us_major": "US Source",
        "international": "International Source",
        "independent": "Independent Source",
    }

    lines = []
    for i, art in enumerate(articles[:max_articles]):
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()

        # Use tier as source label to prevent outlet-name heuristics in Gemini.
        # Falls back to ordinal label if tier is unavailable.
        tier = (art.get("tier", "") or "").strip()
        source_label = _TIER_LABEL_MAP.get(tier, f"Source {i + 1}")

        if len(summary) > 400:
            summary = summary[:397] + "..."

        lines.append(f"[{i + 1}] {source_label}: {title}")
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

    context_line = _build_context_line(articles)
    articles_block = _build_articles_block(articles)
    prompt = _USER_PROMPT_TEMPLATE.format(
        context_line=context_line,
        articles_block=articles_block,
    )
    result = generate_json(prompt, system_instruction=_SYSTEM_INSTRUCTION)

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

    validated = {
        "headline": headline.strip()[:500],
        "summary": summary.strip(),
        "consensus": consensus,
        "divergence": divergence,
    }

    # Quality gate: log warnings for out-of-spec output (no discards).
    # Cluster index is not available here; caller passes cluster id when needed.
    _check_quality(validated)

    return validated


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
