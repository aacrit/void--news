"""
Daily Brief generator for void --news.

Calls Gemini once per edition to produce:
  - tldr_text: 3-line summary for homepage display
  - audio_script: BBC World Service-style broadcast script

Uses generate_json() from the existing Gemini client with count_call=False
so brief calls draw from a separate 3-call-per-run budget, not the
25-call summarization budget.

Falls back to rule-based TL;DR when Gemini is unavailable.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from pipeline root or as part of main.py
sys.path.insert(0, str(Path(__file__).parent.parent))

from summarizer.gemini_client import generate_json, is_available

# ---------------------------------------------------------------------------
# Hard cap: 3 Gemini calls per run (one per edition).
# These are charged against a separate budget (count_call=False) so they
# do not consume the 25-call cluster summarization budget.
# ---------------------------------------------------------------------------
_MAX_BRIEF_CALLS: int = 3
_brief_call_count: int = 0


def _brief_calls_remaining() -> int:
    return max(0, _MAX_BRIEF_CALLS - _brief_call_count)


# ---------------------------------------------------------------------------
# System instruction — BBC World Service editorial voice.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are the editorial voice of void --news, a neutral news intelligence service.
You write two things: a 3-line editorial brief for the homepage, and a full audio
broadcast script in the style of the BBC World Service circa 1975 — formal,
balanced, intellectual, succinct.

Core standards:
- Wire service neutrality. No political perspective. Describe what sources report.
- Active voice. Present tense for current events.
- Attribution by outlet name when it adds value.
- No loaded or sensationalist language. No value judgments.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, divisive,
  landmark, radical, extreme, chaos, firestorm, comprehensive, amidst, landscape.
- No bracketed citations or reference numbers.

For the TL;DR:
- Exactly 3 lines. Each line is one sentence.
- Line 1: The single most consequential development right now.
- Line 2: A second significant story from a different category.
- Line 3: An editorial observation — a pattern, a divergence, or a quiet signal.

For the audio script:
- BBC World Service 1970s style: formal, measured, authoritative, intellectual.
- Total spoken duration target: 3-5 minutes (approximately 450-750 words of speech).
- Pure narration — no sound effects, no countdown, no jingles.
- Structure using exact markers on their own lines:
  [GREETING] This is void news. {edition} edition. {date}.
  [HEADLINES] (headline roundup, 3 stories, ~15 seconds)
  [STORY_1] (first story, ~60 seconds, with attribution)
  [STORY_2] (second story, ~50 seconds, with attribution)
  [STORY_3] (third story, ~40 seconds, with attribution)
  [EDITORIAL_NOTE] (one observation about coverage divergence, ~20 seconds)
  [SIGNOFF] This was void news.
- Keep sentences short and spoken-word friendly.
- Numbers: write out small numbers. Use figures for large numbers.
- No questions. No exclamation marks. Declarative sentences only.\
"""

# ---------------------------------------------------------------------------
# User prompt template — injected per edition call.
# ---------------------------------------------------------------------------
_USER_PROMPT_TEMPLATE = """\
Generate the daily brief for the {EDITION} edition of void --news.
Date: {DATE}

Below are today's top {N} stories for this edition, ranked by importance.

STORIES:
{stories_block}

Return JSON with exactly two fields:
1. "tldr_text" — 3 lines separated by \\n
2. "audio_script" — full broadcast script with segment markers\
"""

# ---------------------------------------------------------------------------
# Prohibited terms — same policy as cluster summarizer.
# ---------------------------------------------------------------------------
_PROHIBITED_TERMS = frozenset({
    "shocking", "stunning", "explosive", "unprecedented", "controversial",
    "divisive", "landmark", "radical", "extreme", "chaos", "firestorm",
    "comprehensive", "amidst", "landscape",
})


def _check_quality(result: dict, edition: str) -> None:
    """Log quality warnings for out-of-spec brief output."""
    tldr = result.get("tldr_text", "")
    lines = [l.strip() for l in tldr.split("\n") if l.strip()]
    if len(lines) != 3:
        print(f"  [quality][brief:{edition}] TL;DR has {len(lines)} lines (expected 3)")

    all_text = " ".join([
        tldr,
        result.get("audio_script", ""),
    ]).lower()

    found = [t for t in _PROHIBITED_TERMS if t in all_text]
    if found:
        print(f"  [quality][brief:{edition}] Prohibited terms found: {found}")

    script = result.get("audio_script", "")
    required_markers = [
        "[GREETING]", "[HEADLINES]",
        "[STORY_1]", "[STORY_2]", "[STORY_3]",
        "[EDITORIAL_NOTE]", "[SIGNOFF]",
    ]
    missing = [m for m in required_markers if m not in script]
    if missing:
        print(f"  [quality][brief:{edition}] Missing script markers: {missing}")


def _build_stories_block(clusters: list[dict], edition: str, max_stories: int = 8) -> tuple[list[dict], str]:
    """
    Build the stories context block for the prompt.

    Filters clusters by edition (sections array containment), takes top N
    by headline_rank, and formats each with title, summary excerpt,
    source_count, consensus_points, and divergence_points.

    Returns (filtered_clusters, stories_block_text).
    """
    edition_clusters = []
    for c in clusters:
        sections = c.get("sections") or [c.get("section", "world")]
        if edition in sections:
            edition_clusters.append(c)

    # Sort by headline_rank descending (already sorted in pipeline, but be safe)
    edition_clusters.sort(
        key=lambda c: (c.get("headline_rank", 0), c.get("source_count", 0)),
        reverse=True,
    )

    top = edition_clusters[:max_stories]
    lines = []
    for i, c in enumerate(top, 1):
        title = (c.get("title", "") or "").strip()
        summary = (c.get("summary", "") or "").strip()
        if len(summary) > 300:
            summary = summary[:297] + "..."
        source_count = c.get("source_count", 1)
        consensus = c.get("consensus_points") or []
        divergence = c.get("divergence_points") or []

        lines.append(f"[{i}] ({source_count} sources) {title}")
        if summary:
            lines.append(f"    Summary: {summary}")
        if consensus and isinstance(consensus, list):
            lines.append(f"    Consensus: {consensus[0]}" if len(consensus) == 1
                         else f"    Consensus: {'; '.join(str(x) for x in consensus[:2])}")
        if divergence and isinstance(divergence, list):
            lines.append(f"    Divergence: {divergence[0]}")
        lines.append("")

    return top, "\n".join(lines)


def _rule_based_tldr(top_clusters: list[dict]) -> str:
    """
    Rule-based TL;DR fallback when Gemini is unavailable.

    Takes the top 3 cluster titles and formats them as three declarative
    sentences. Audio script is not generated (returns None separately).
    """
    sentences = []
    for c in top_clusters[:3]:
        title = (c.get("title", "") or "").strip()
        if title:
            # Ensure sentence ends with a period
            if not title.endswith((".","!","?")):
                title = title + "."
            sentences.append(title)

    # Pad to 3 lines if fewer clusters are available
    while len(sentences) < 3:
        sentences.append("No additional top stories available for this edition.")

    return "\n".join(sentences[:3])


def generate_daily_briefs(
    clusters: list[dict],
    source_map: dict,
    edition_sections: list[str] | None = None,
) -> dict[str, dict]:
    """
    Generate daily briefs for each requested edition.

    Args:
        clusters: Full list of ranked cluster dicts from the pipeline.
        source_map: Source slug -> source dict (used for context; reserved
            for future per-source attribution enrichment).
        edition_sections: List of editions to generate (default: world, us, india).

    Returns:
        Dict mapping edition -> brief dict with keys:
            tldr_text (str): 3-line summary.
            audio_script (str | None): Full broadcast script, or None if
                Gemini unavailable.
            top_cluster_ids (list[str]): IDs of top clusters used as context.
    """
    global _brief_call_count

    if edition_sections is None:
        edition_sections = ["world", "us", "india"]

    gemini_ok = is_available()
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    results: dict[str, dict] = {}

    for edition in edition_sections:
        top_clusters, stories_block = _build_stories_block(clusters, edition)

        # Collect top cluster IDs for storage
        top_ids: list[str] = []
        for c in top_clusters:
            cid = c.get("_db_id", "")
            if cid:
                top_ids.append(cid)

        if not top_clusters:
            print(f"  [brief:{edition}] No clusters for this edition — skipping")
            results[edition] = {
                "tldr_text": "No stories available for this edition.",
                "audio_script": None,
                "top_cluster_ids": [],
            }
            continue

        # Attempt Gemini generation within budget
        brief_result = None
        if gemini_ok and _brief_calls_remaining() > 0:
            prompt = _USER_PROMPT_TEMPLATE.format(
                EDITION=edition.upper(),
                DATE=date_str,
                N=len(top_clusters),
                stories_block=stories_block,
            )
            _brief_call_count += 1
            raw = generate_json(
                prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                count_call=False,  # Separate budget; does not consume summarization cap
            )
            if raw and isinstance(raw, dict):
                tldr = raw.get("tldr_text", "")
                script = raw.get("audio_script")

                # Validate tldr shape
                if isinstance(tldr, str) and tldr.strip():
                    brief_result = {
                        "tldr_text": tldr.strip(),
                        "audio_script": script if isinstance(script, str) and script.strip() else None,
                        "top_cluster_ids": top_ids,
                    }
                    _check_quality(raw, edition)
                    print(f"  [brief:{edition}] Gemini OK — TL;DR {len(tldr.split(chr(10)))} lines, "
                          f"script {'yes' if brief_result['audio_script'] else 'no'}")
                else:
                    print(f"  [brief:{edition}] Gemini returned invalid tldr_text — falling back")
            else:
                print(f"  [brief:{edition}] Gemini call failed — falling back to rule-based")
        elif not gemini_ok:
            print(f"  [brief:{edition}] Gemini not available — using rule-based TL;DR")
        else:
            print(f"  [brief:{edition}] Brief call cap reached — using rule-based TL;DR")

        # Fallback: rule-based TL;DR, no audio script
        if brief_result is None:
            brief_result = {
                "tldr_text": _rule_based_tldr(top_clusters),
                "audio_script": None,
                "top_cluster_ids": top_ids,
            }

        results[edition] = brief_result

    total_gemini = sum(1 for r in results.values() if r.get("audio_script") is not None)
    total_fallback = len(results) - total_gemini
    print(f"  Daily briefs: {len(results)} editions "
          f"({total_gemini} Gemini, {total_fallback} rule-based, "
          f"{_brief_calls_remaining()} brief calls remaining)")

    return results
