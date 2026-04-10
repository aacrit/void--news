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

# Import shared prohibited terms — single canonical source.
try:
    from utils.prohibited_terms import PROHIBITED_TERMS as _SHARED_PROHIBITED, check_prohibited_terms as _shared_check
    _USE_SHARED_PROHIBITED = True
except ImportError:
    _USE_SHARED_PROHIBITED = False


# ---------------------------------------------------------------------------
# System instruction — persistent editorial voice, set once per API call.
# Defines void --news tone: neutral, attribution-heavy, no sensationalism.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are a senior correspondent and copy editor at void --news, a neutral news \
intelligence service. Your role is to synthesize news coverage from multiple \
sources into factual briefings. You have no political perspective. You describe \
what sources report; you do not editorialize.

GROUNDING RULE: Every fact, figure, name, quote, date, and claim in your output \
MUST appear in the provided articles. Do not supplement with prior knowledge, \
background context you recall, or facts not present in the text above. If the \
articles don't say it, you don't write it. You are a summarizer, not a reporter.

Cardinal rule: SHOW, DON'T TELL. Place facts next to each other and let the \
reader see the pattern. "The central bank cut rates Tuesday. The last time it \
moved this fast, three lenders collapsed within six months." — significance \
emerges from evidence, never from adjectives. Never assert significance — show \
the evidence that makes it self-evident.

Core standards that apply to all output:
- Active voice. Present tense for current and recent events.
- Every significant factual claim is attributed to a named or specific source. \
Prohibited pseudo-attribution: "it was widely reported," "it is understood that," \
"sources close to" (unless followed by a specific entity).
- No loaded, charged, or sensationalist language — including language borrowed \
from source headlines.
- No value judgments. Prohibited adjectives: controversial, divisive, landmark, \
historic, shocking, stunning, explosive, devastating, unprecedented (as rhetorical \
emphasis), radical, extreme, common-sense.
- No unattributed predictions or expert opinions. "Experts say" without a named \
or described expert is not attribution.
- In headlines, state what happened — not what might happen. Headlines use \
"passes," not "could pass." Hedge modal verbs (could, may, might, would) signal \
speculation in a headline and are prohibited unless directly quoting a source \
statement.
- Neutral framing of competing legitimate perspectives. No false balance on \
empirical questions with clear factual consensus.
- Precise language: name individuals when known, state exact figures, specify \
locations when central.
- KILL SCAFFOLDING: Never use templatic transitions that announce what you're \
about to say. "This isn't just...", "Here's the thing...", "The bigger \
picture...", "What makes this...", "The reality is..." — these are filler. Cut \
them. Start the sentence with the fact itself.
- When attribution is needed, use actual outlet names (e.g., "Reuters reported," \
"according to The Washington Post"). Do not use generic labels like "a US major \
source" or "an international outlet." Only attribute when it adds value — not \
every sentence needs a citation.
- NEVER use bracketed citations, footnotes, or reference markers like [1], [2,5], \
[Source], (1), etc. This is a news briefing, not an academic paper. Attribute \
inline using natural language ("according to...", "...X reported").\
"""

# ---------------------------------------------------------------------------
# User prompt template — per-call task injected with article context.
# {context_line} and {articles_block} are replaced at call time.
# ---------------------------------------------------------------------------
_USER_PROMPT_TEMPLATE = """\
Analyze the following news cluster and return a JSON object with exactly seven \
fields: headline, summary, consensus, divergence, editorial_importance, story_type, has_binding_consequences.

{context_line}
{source_names_line}
ARTICLES:
{articles_block}

---

TASK 1 — headline (string)
Write an 8-12 word factual headline. Count the words carefully.
- Title Case. Active voice. Present tense.
- State the action, the actor, and location if essential.
- No question marks, exclamation marks, or ellipses.
- No hedge constructions: "could," "may," "might," "would" are prohibited \
unless directly quoting a source statement.
- Prohibited words: crackdown, explosive, bombshell, shocking, stunning, chaos, \
chaotic, slams, blasts, doubles down, firestorm, war of words, crisis (unless an \
official designation).
- Do not reproduce sensationalist language from source headlines.
Good: "Senate Passes $1.2 Trillion Infrastructure Bill After Weekend Vote"
Bad: "Shocking Vote Shakes Washington as Senate Acts on Roads"
Bad: "US Senate Could Pass Immigration Bill as Talks Continue"

---

TASK 2 — summary (string, 250-350 words)
Write a comprehensive factual briefing in inverted pyramid structure. This should \
read like a complete news intelligence brief — rich with specifics, diverse \
perspectives, and contextual depth. SHOW, DON'T TELL: let concrete facts, figures, \
and juxtaposed perspectives convey significance. Never assert that something is \
"significant" or "notable" — show the evidence and let the reader conclude.

IMPORTANT: Articles are sorted newest-first and include publication timestamps. \
Lead with the MOST RECENT development — what is new as of the latest articles. \
Older articles in the cluster provide context and background, but the lede must \
reflect the freshest reported facts. If a cluster spans multiple days, clearly \
distinguish what happened today from prior developments.

Paragraph 1 (2-3 sentences): The most recent newsworthy development — what just \
happened, who, when, where. Lead with the latest event, then attribute. Include \
the most significant number, name, or outcome from the freshest reporting.

Paragraph 2 (3-4 sentences): Context and significance. Why this matters, what \
preceded it, how it connects to broader developments. Attribute all background \
claims to specific outlets by name when the attribution adds value.

Paragraph 3 (3-4 sentences): Diverse perspectives. What different sources \
emphasize — present the range of reported angles, reactions from named officials \
or organizations, and any competing stated positions. Represent perspectives with \
equal syntactic weight.

Paragraph 4 (2-3 sentences): Key specifics. Exact figures, direct quotes, \
technical details, geographic scope, affected populations. This is where data \
density matters most.

Paragraph 5 (1-2 sentences): Next steps, a deadline, an expected decision, or \
stated consequences. What to watch for next.

When attributing, use actual outlet names from the SOURCE NAMES list below \
(e.g., "Reuters reported," "according to The Washington Post"). Only attribute \
when it adds value — not every sentence needs a citation. Most factual statements \
confirmed across sources need no attribution.

Prohibited constructions:
- "In a stunning/shocking/unprecedented development..."
- "The world watched as..."
- "Experts say..." or "Analysts believe..." without named or described attribution
- "...raising questions about..." (vague concern framing)
- "...sparking outrage/controversy..." (importing reaction framing)
- Generic tier labels like "a US major source" or "an international outlet"
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
- Reference outlets by name where useful for specific divergence points.
- Permitted verbs: emphasize, include, omit, lead with, frame as, devote more \
coverage to, focus on, give less prominence to.
- Prohibited words: bias, ignore, spin, push, hide, downplay, downplayed, \
agenda, chose not to report, failed to mention.
- When sources cite conflicting verifiable facts, describe the conflict neutrally: \
"Reuters and Al Jazeera cite differing figures for [specific metric]."

---

TASK 5 — editorial_importance (integer, 1-10)
Rate this story's editorial importance. Primary question: "Would a senior NYT \
editor put this on the front page?"

10 = once-in-a-decade event (war declaration, pandemic, constitutional crisis, \
regime change)
8-9 = major irreversible development: supreme court ruling, military action, \
central bank rate change, treaty signed
6-7 = significant development with binding or structural consequences: \
legislation passed, sanctions imposed, major leader speech with policy commitment, \
election result
4-5 = significant but reversible or provisional: policy proposal, summit meeting, \
bilateral statement, major indictment without verdict, large protest
2-3 = incremental update on a known story: day-N of ongoing talks, progress \
report, reaction statement to a prior event
1 = ceremonial, human interest, or symbolic: award, anniversary, cultural event

Tiebreaker: if uncertain between two adjacent scores, score lower if (a) this is \
a continuation of a story already widely reported, or (b) the primary action is a \
statement rather than a decision.

---

TASK 6 — story_type (string, one of these exact values)
Classify into exactly one type:
- "breaking_crisis": active unfolding emergency with immediate consequences
- "policy_action": government/institutional decision with binding consequences
- "investigation": journalistic investigation revealing unknown information
- "ongoing_crisis": the story is about an active situation (war, famine, pandemic, \
political crisis) where no single news cycle contains the entire story. Choose \
this when articles primarily describe the state of an ongoing situation.
- "incremental_update": a specific narrow development on a story that has already \
been reported. Choose this when articles primarily describe a reaction, a minor \
announcement, or a scheduled event within a larger story. Example: spokesperson \
declining comment, scheduled hearing update.
- "human_interest": individual-focused story without policy implications
- "ceremonial": commemorative events, symbolic actions, awards, anniversaries
- "entertainment": arts, culture, sports, celebrity

---

TASK 7 — has_binding_consequences (boolean)
Does this story report a decision or event with binding policy, legal, military, or economic consequences? True if it changes the legal/military/economic status quo (law signed, sanctions imposed, rate decision, military deployment, court ruling). False for proposals, discussions, reactions, commentary, or ceremonial events.

---

Return JSON only. No markdown fences. No text outside the JSON object.

{{"headline": "...", "summary": "...", "consensus": ["...", ...], "divergence": ["...", ...], "editorial_importance": N, "story_type": "...", "has_binding_consequences": true/false}}\
"""

# ---------------------------------------------------------------------------
# Quality gate — prohibited terms scanned after generation.
# Warnings are logged but results are never discarded (zero extra API calls).
# Uses shared module when available; falls back to local list for resilience.
# ---------------------------------------------------------------------------
if _USE_SHARED_PROHIBITED:
    _PROHIBITED_TERMS = _SHARED_PROHIBITED
else:
    _PROHIBITED_TERMS = frozenset({
        "shocking", "stunned", "stunning", "explosive", "bombshell", "devastating",
        "chaos", "chaotic", "firestorm", "crackdown", "slams", "blasts",
        "doubles down", "war of words", "sparking outrage", "raising questions",
        "raises concerns", "casts doubt", "throws into question",
        "in an unprecedented", "unprecedented", "in a stunning", "the world watched",
        "experts say", "analysts believe", "experts believe", "analysts say",
        "it was widely reported", "it is widely understood",
        "controversial", "divisive", "landmark", "historic",
        "radical", "extreme", "common-sense",
        "could signal", "may mark", "might reshape",
        "most significant", "most important development", "key moment",
        "downplayed", "failed to mention", "chose not to report",
        "a us major source", "an international outlet", "a major source",
    })

# Minimum sources for a cluster to qualify for Gemini summarization.
# 2-source clusters don't benefit much from LLM synthesis — the rule-based
# "pick best title" approach works fine. 3+ sources is where synthesis shines.
_MIN_SOURCES = 3


def _check_quality(result: dict, cluster_id: str | int = "") -> None:
    """
    Log quality warnings for out-of-spec generated content.

    Checks headline word count (8-12), summary word count (250-350),
    consensus/divergence item counts, and scans all text fields for
    prohibited sensationalist or value-laden terms.

    Does not modify or discard the result — warnings are surfaced to the
    analytics-expert during post-run audit.
    """
    cid_str = f" {cluster_id}" if cluster_id != "" else ""

    headline = result.get("headline", "")
    word_count = len(headline.split())
    if not (8 <= word_count <= 12):
        print(
            f"  [quality]{cid_str} Headline word count {word_count} (expected 8-12): "
            f"{headline!r}"
        )

    # Summary word count (target: 250-350, warn outside 200-400 range)
    summary = result.get("summary", "")
    summary_wc = len(summary.split())
    if summary_wc > 0 and not (200 <= summary_wc <= 400):
        print(
            f"  [quality]{cid_str} Summary word count {summary_wc} (expected 250-350): "
            f"first 80 chars: {summary[:80]!r}"
        )

    # Consensus/divergence item counts
    consensus_count = len(result.get("consensus", []))
    if consensus_count > 0 and not (3 <= consensus_count <= 5):
        print(f"  [quality]{cid_str} Consensus count {consensus_count} (expected 3-5)")

    divergence_count = len(result.get("divergence", []))
    if divergence_count > 0 and not (2 <= divergence_count <= 4):
        print(f"  [quality]{cid_str} Divergence count {divergence_count} (expected 2-4)")

    ei = result.get("editorial_importance")
    if ei is not None and not (1 <= int(ei) <= 10):
        print(f"  [quality]{cid_str} editorial_importance out of range: {ei}")

    # Scan headline + summary + all consensus + all divergence items
    all_text = " ".join([
        headline,
        summary,
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

    Tells Gemini total article count, tier distribution, and time range
    so it can calibrate synthesis depth and prioritize recent developments.
    """
    total = len(articles)
    tier_counts: dict[str, int] = {}
    timestamps = []
    for art in articles:
        tier = (art.get("tier", "") or "unknown")
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        pub = art.get("published_at", "")
        if pub:
            timestamps.append(pub[:16])

    parts = []
    if tier_counts.get("us_major"):
        parts.append(f"{tier_counts['us_major']} US major")
    if tier_counts.get("international"):
        parts.append(f"{tier_counts['international']} international")
    if tier_counts.get("independent"):
        parts.append(f"{tier_counts['independent']} independent")

    distribution = ", ".join(parts) if parts else "mixed sources"

    # Add time range so Gemini knows how fresh the cluster is
    time_range = ""
    if timestamps:
        oldest = min(timestamps)
        newest = max(timestamps)
        if oldest != newest:
            time_range = f" Coverage spans {oldest} to {newest}. Lead with the most recent developments."
        else:
            time_range = f" Published around {newest}."

    return f"CLUSTER METADATA: {total} articles from {distribution} outlets.{time_range}\n"


def _build_source_names_line(articles: list[dict]) -> str:
    """
    Build a SOURCE NAMES reference line mapping article numbers to outlet names.

    Provides real outlet names so Gemini can use them for attribution in
    summaries and divergence points, instead of generic tier labels.
    """
    names = []
    for i, art in enumerate(articles[:10]):
        source_name = (art.get("source_name", "") or "").strip()
        if source_name:
            names.append(f"[{i + 1}] {source_name}")
    if not names:
        return ""
    return "SOURCE NAMES: " + ", ".join(names) + "\n"


def _build_articles_block(articles: list[dict], max_articles: int = 10) -> str:
    """
    Build the articles context block for the prompt.

    Uses tier-based labels in the article block itself (to prevent Gemini
    from weighting outlets by brand recognition), but real outlet names are
    provided separately via _build_source_names_line for attribution use.

    Articles are sorted newest-first so Gemini sees the most recent
    developments at the top of the context window. Each article includes
    its publication timestamp so Gemini can distinguish fresh developments
    from older background.

    Limits to max_articles and includes summaries up to 400 chars to give
    Gemini sufficient material for comprehensive synthesis.
    """
    _TIER_LABEL_MAP = {
        "us_major": "US Source",
        "international": "International Source",
        "independent": "Independent Source",
    }

    # Sort newest-first so Gemini prioritizes recent developments
    sorted_articles = sorted(
        articles[:max_articles],
        key=lambda a: a.get("published_at", "") or "",
        reverse=True,
    )

    lines = []
    for i, art in enumerate(sorted_articles):
        title = (art.get("title", "") or "").strip()
        summary = (art.get("summary", "") or "").strip()
        pub_date = (art.get("published_at", "") or "")[:16]  # YYYY-MM-DDTHH:MM

        # Use tier as source label in the article block.
        # Normalize tier value: lowercase + replace hyphens with underscores.
        tier_raw = (art.get("tier", "") or "").strip().lower().replace("-", "_")
        source_label = _TIER_LABEL_MAP.get(tier_raw, f"Source {i + 1}")

        header = f"[{i + 1}] {source_label}: {title}"
        if pub_date:
            header += f"  ({pub_date})"

        if len(summary) > 400:
            summary = summary[:397] + "..."

        lines.append(header)
        if summary:
            lines.append(f"    {summary}")
        lines.append("")

    return "\n".join(lines)


def _build_claims_block(claims_consensus) -> str:
    """
    Format NLP-extracted claims for the Gemini prompt.

    Produces a readable list with unicode status markers.
    """
    if claims_consensus is None:
        return ""

    lines = ["", "CLAIM EXTRACTION (NLP — void --verify):"]
    claims = getattr(claims_consensus, "claims", [])
    if not claims:
        return ""

    for vc in claims[:20]:  # Cap at 20 to stay within token limits
        status = getattr(vc, "status", "unverified")
        text = getattr(vc, "claim_text", "")
        count = getattr(vc, "source_count", 1)
        sources = getattr(vc, "source_names", [])
        total = getattr(claims_consensus, "total_claims", 0) or len(claims)

        if status == "corroborated":
            src_str = ", ".join(sources[:5]) if sources else ""
            lines.append(f"✓ CORROBORATED ({count}/{total} sources): \"{text}\"")
        elif status == "disputed":
            lines.append(f"⚠ DISPUTED: \"{text}\"")
        elif status == "single_source":
            src = sources[0] if sources else "unknown"
            lines.append(f"○ SINGLE SOURCE (only: {src}): \"{text}\"")

    # Add disputed details
    disputed_details = getattr(claims_consensus, "disputed_details", [])
    for dd in disputed_details[:5]:
        va = getattr(dd, "version_a", "")
        vb = getattr(dd, "version_b", "")
        va_src = ", ".join(getattr(dd, "version_a_sources", []))
        vb_src = ", ".join(getattr(dd, "version_b_sources", []))
        lines.append(f"  → \"{va}\" ({va_src}) vs \"{vb}\" ({vb_src})")

    return "\n".join(lines) + "\n"


# Claims deduplication task template (appended when claims data is available)
_CLAIMS_TASK_TEMPLATE = """
---

TASK 8 — claims (array of objects), consensus_ratio (float), consensus_summary (string)
You are given NLP-extracted factual claims from articles in this cluster with their verification status.

Your job:
1. Deduplicate semantically equivalent claims (NLP may extract "GDP grew 3.2%"
   and "the economy expanded by 3.2%" as separate claims — merge them)
2. Write a canonical version of each unique claim (clear, concise)
3. Preserve source counts and contradiction details
4. Select the 3-5 most newsworthy claims to highlight
5. For disputed claims, write both versions clearly
6. Write a one-sentence consensus_summary describing overall source agreement

Output these three additional fields in the JSON:
"claims": [{"text": "...", "status": "corroborated|single_source|disputed", "source_count": N, "sources": ["..."], "highlight": true, "disputed_versions": [{"text": "...", "sources": ["..."]}]}],
"consensus_ratio": 0.0-1.0,
"consensus_summary": "One sentence describing overall source agreement"
"""


def summarize_cluster(articles: list[dict],
                      claims_consensus=None) -> dict | None:
    """
    Generate headline, summary, consensus, and divergence for a cluster.

    Returns None if Gemini is unavailable, fails, or call cap reached.
    """
    if not is_available() or calls_remaining() <= 0:
        return None

    if not articles:
        return None

    context_line = _build_context_line(articles)
    source_names_line = _build_source_names_line(articles)
    articles_block = _build_articles_block(articles)

    # Build claims context if available
    claims_block = _build_claims_block(claims_consensus) if claims_consensus else ""

    prompt = _USER_PROMPT_TEMPLATE.format(
        context_line=context_line,
        source_names_line=source_names_line,
        articles_block=articles_block,
    )

    # Inject claims task before the final "Return JSON only" line
    if claims_block:
        # Replace field count and add claims task
        prompt = prompt.replace(
            "exactly seven \\\nfields: headline, summary, consensus, divergence, "
            "editorial_importance, story_type, has_binding_consequences.",
            "exactly ten \\\nfields: headline, summary, consensus, divergence, "
            "editorial_importance, story_type, has_binding_consequences, "
            "claims, consensus_ratio, consensus_summary.",
        )
        # Insert claims block and task before "Return JSON only"
        prompt = prompt.replace(
            "Return JSON only. No markdown fences.",
            claims_block + _CLAIMS_TASK_TEMPLATE
            + "\n---\n\nReturn JSON only. No markdown fences.",
        )
        # Update the JSON example at the end
        prompt = prompt.replace(
            '"has_binding_consequences": true/false}',
            '"has_binding_consequences": true/false, '
            '"claims": [...], "consensus_ratio": 0.0, '
            '"consensus_summary": "..."}',
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

    # Extract editorial intelligence fields (v5.0)
    editorial_importance = result.get("editorial_importance")
    if isinstance(editorial_importance, (int, float)):
        editorial_importance = max(1, min(10, int(editorial_importance)))
    else:
        editorial_importance = None

    _VALID_STORY_TYPES = {
        "breaking_crisis", "policy_action", "investigation",
        "ongoing_crisis", "incremental_update", "human_interest",
        "ceremonial", "entertainment",
    }
    story_type_raw = result.get("story_type", "")
    story_type = story_type_raw if story_type_raw in _VALID_STORY_TYPES else None

    has_binding = result.get("has_binding_consequences")
    has_binding_consequences = bool(has_binding) if isinstance(has_binding, bool) else None

    # void --verify: extract claim deduplication results
    claims = result.get("claims")
    if isinstance(claims, list):
        claims = [c for c in claims if isinstance(c, dict) and c.get("text")]
    else:
        claims = None

    consensus_ratio_val = result.get("consensus_ratio")
    if isinstance(consensus_ratio_val, (int, float)):
        consensus_ratio_val = max(0.0, min(1.0, float(consensus_ratio_val)))
    else:
        consensus_ratio_val = None

    consensus_summary_val = result.get("consensus_summary")
    if not isinstance(consensus_summary_val, str) or not consensus_summary_val.strip():
        consensus_summary_val = None

    validated = {
        "headline": headline.strip()[:500],
        "summary": summary.strip(),
        "consensus": consensus,
        "divergence": divergence,
        "editorial_importance": editorial_importance,
        "story_type": story_type,
        "has_binding_consequences": has_binding_consequences,
        "claims": claims,
        "consensus_ratio": consensus_ratio_val,
        "consensus_summary": consensus_summary_val,
    }

    # Quality gate: log warnings for out-of-spec output (no discards).
    # Cluster index is not available here; caller passes cluster id when needed.
    _check_quality(validated)

    return validated


def summarize_clusters_batch(clusters: list[dict],
                             cluster_consensus: dict | None = None,
                             top_n: int = 30,
                             regional_fill: int = 10,
                             topic_fill: int = 10,
                             ) -> tuple[dict[int, dict], set[int]]:
    """
    Summarize up to 50 clusters using three non-overlapping priority pools.

    Pool 1 — Top 30 global (headline_rank DESC): ensures the most important
      stories always get Gemini-quality summaries.
    Pool 2 — Regional fill (up to 10): round-robin across editions
      (world/us/europe/south-asia) to guarantee each region has representation
      even when Pool 1 is dominated by one region.
    Pool 3 — Topic fill (up to 10): 1 per category desk first, then fills
      remaining slots with the best remaining clusters.

    Each cluster is summarized at most once. Pool 1 failures have their
    rule-based summaries cleared by the caller (no fallback for premium slots).
    Pool 2/3 failures keep their rule-based summaries as acceptable fallback.

    Args:
        clusters: List of cluster dicts with "articles" and "source_count".
        cluster_consensus: Optional dict of cluster_index_str -> ClusterConsensus.
        top_n: Pool 1 size (top global clusters). Defaults to 30.
        regional_fill: Pool 2 max size. Defaults to 10.
        topic_fill: Pool 3 max size. Defaults to 10.

    Returns:
        Tuple of:
          - Dict mapping cluster index -> summarize_cluster result.
          - Set of Pool 1 cluster indices that Gemini failed on — callers
            should clear their rule-based summaries so no fallback text
            reaches the frontend for these premium positions.
    """
    if not is_available():
        return {}, set()

    # ── Helper: check if a cluster qualifies for Gemini summarization ──
    def _qualifies(cluster: dict) -> bool:
        if cluster.get("_is_opinion"):
            return False
        sc = cluster.get("source_count", 0) or len(cluster.get("articles", []))
        return sc >= _MIN_SOURCES

    def _rank_key(i: int) -> tuple:
        return (clusters[i].get("headline_rank") or 0,
                clusters[i].get("source_count", 0))

    # All qualifying indices sorted by headline_rank DESC
    all_qualifying = sorted(
        (i for i, c in enumerate(clusters) if _qualifies(c)),
        key=_rank_key,
        reverse=True,
    )

    # ── Pool 1: Top N global ──────────────────────────────────────────────────
    pool1: list[int] = all_qualifying[:top_n]
    selected: set[int] = set(pool1)

    # ── Pool 2: Regional round-robin ──────────────────────────────────────────
    _EDITIONS = ["world", "us", "europe", "south-asia"]

    # Per-edition sorted candidate queue (excluding pool1)
    edition_queues: dict[str, list[int]] = {ed: [] for ed in _EDITIONS}
    for i in all_qualifying:
        if i in selected:
            continue
        sections = clusters[i].get("sections") or [clusters[i].get("section", "world")]
        for ed in _EDITIONS:
            if ed in sections:
                edition_queues[ed].append(i)
    # Queues are already in headline_rank order since all_qualifying is sorted

    pool2: list[int] = []
    edition_ptrs = {ed: 0 for ed in _EDITIONS}
    while len(pool2) < regional_fill:
        advanced = False
        for ed in _EDITIONS:
            if len(pool2) >= regional_fill:
                break
            ptr = edition_ptrs[ed]
            queue = edition_queues[ed]
            while ptr < len(queue):
                candidate = queue[ptr]
                ptr += 1
                if candidate not in selected:
                    pool2.append(candidate)
                    selected.add(candidate)
                    advanced = True
                    break
            edition_ptrs[ed] = ptr
        if not advanced:
            break  # All edition queues exhausted

    # ── Pool 3: Topic (category desk) fill ───────────────────────────────────
    _CATEGORIES = ["politics", "conflict", "economy",
                   "science", "health", "environment", "culture"]

    pool3: list[int] = []

    # First pass: 1 per category (breadth)
    seen_cats: set[str] = set()
    for i in all_qualifying:
        if len(pool3) >= topic_fill:
            break
        if i in selected:
            continue
        cat = (clusters[i].get("category") or "").lower()
        if cat in _CATEGORIES and cat not in seen_cats:
            pool3.append(i)
            selected.add(i)
            seen_cats.add(cat)

    # Second pass: fill remaining slots with best unselected clusters
    if len(pool3) < topic_fill:
        for i in all_qualifying:
            if len(pool3) >= topic_fill:
                break
            if i not in selected:
                pool3.append(i)
                selected.add(i)

    # ── Summarize: pool1 → pool2 → pool3 ─────────────────────────────────────
    all_candidates = pool1 + pool2 + pool3
    pool1_set = set(pool1)
    pool2_set = set(pool2)

    results: dict[int, dict] = {}
    p1_ok = p2_ok = p3_ok = 0
    consecutive_failures = 0
    _CIRCUIT_BREAKER_THRESHOLD = 5  # bail if 5 clusters fail in a row (API down)
    attempted_pool1: set[int] = set()  # track which pool-1 indices were actually tried

    for idx in all_candidates:
        if consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
            print(f"  [warn] Circuit breaker triggered after {consecutive_failures} consecutive failures — Gemini overloaded, aborting batch")
            break
        if idx in pool1_set:
            attempted_pool1.add(idx)
        articles = clusters[idx].get("articles", [])
        cc = cluster_consensus.get(str(idx)) if cluster_consensus else None
        result = summarize_cluster(articles, claims_consensus=cc)
        if result:
            results[idx] = result
            consecutive_failures = 0  # reset on success
            if idx in pool1_set:
                p1_ok += 1
            elif idx in pool2_set:
                p2_ok += 1
            else:
                p3_ok += 1
        else:
            consecutive_failures += 1

    total_ok = p1_ok + p2_ok + p3_ok
    total_att = len(all_candidates)
    print(f"  Gemini: {total_ok}/{total_att} clusters summarized "
          f"({p1_ok} top-30 / {p2_ok} regional / {p3_ok} topic)")
    if total_ok < total_att:
        print(f"  {total_att - total_ok} failed (pool-1 failures will have summaries cleared)")

    # Per-run aggregate quality instrumentation
    if results:
        headline_lens = [len(r["headline"].split()) for r in results.values()]
        summary_lens = [len(r["summary"].split()) for r in results.values()]
        avg_h = sum(headline_lens) / len(headline_lens)
        avg_s = sum(summary_lens) / len(summary_lens)
        out_of_range_h = sum(1 for wc in headline_lens if not (8 <= wc <= 12))
        out_of_range_s = sum(1 for wc in summary_lens if not (200 <= wc <= 400))
        print(f"  Headline avg {avg_h:.1f} words, "
              f"{out_of_range_h}/{len(headline_lens)} out of 8-12 range")
        print(f"  Summary avg {avg_s:.1f} words, "
              f"{out_of_range_s}/{len(summary_lens)} out of 250-350 range")

    # Return only pool-1 indices that were attempted but failed — circuit-breaker
    # skipped indices are NOT cleared (their rule-based summaries stay as fallback).
    return results, attempted_pool1 - results.keys()
