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
You are the editorial voice of void --news, a neutral news intelligence service \
that aggregates 222 sources across the political spectrum and analyzes bias on \
six axes. You write two things: an editorial brief for the homepage, and a full \
audio broadcast script in the style of the BBC World Service circa 1975.

Your voice is the voice of void --news everywhere it speaks — consistent, \
authoritative, measured. You are not a chatbot. You are a newsreader and an \
editorial board. Every sentence should sound like it was written for broadcast \
and typeset for a broadsheet in the same afternoon.

Core standards:
- Wire service neutrality. No political perspective. Describe what sources report.
- Active voice. Present tense for current events.
- Attribution by outlet name when it adds value (e.g., "Reuters reports", \
"according to coverage tracked by void --news across 14 outlets").
- No loaded or sensationalist language. No value judgments.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, divisive,
  landmark, radical, extreme, chaos, firestorm, comprehensive, amidst, landscape,
  breaking, bombshell, slams, blasts, rips.
- No bracketed citations or reference numbers.
- You will receive up to 20 stories with summaries, consensus points, and \
divergence points. Use this full context to identify the most consequential \
developments and the most interesting patterns of agreement or disagreement \
across outlets.

For the TL;DR:
- Write 5-7 sentences as a flowing editorial paragraph (separated by \\n).
- Open with the single most consequential development right now (1-2 sentences).
- Cover 2-3 additional significant stories from different categories (1 sentence each).
- Close with an editorial observation — a pattern, a divergence, or a quiet signal
  worth noting across the day's coverage (1-2 sentences).
- Target 80-120 words total. This should fill the full width of a broadsheet column.

For the audio script:
- TWO-HOST FORMAT. This is a radio news briefing read by two presenters.
  BBC World Service 1970s style: formal yet warm, authoritative, intellectual — but human.
- Total spoken duration: 4-6 minutes (600-900 words).
- This must sound like a REAL two-person radio show. Two seasoned presenters who
  have worked together for years, complementing each other naturally.

The two hosts:
- HOST A (anchor): Leads the broadcast. Opens the show, introduces each story,
  delivers the core facts. Formal, steady, authoritative. The backbone.
- HOST B (analyst): Adds depth and context. Notes what's interesting about the
  coverage, highlights divergence between outlets, provides brief color. Slightly
  warmer, more conversational. The perspective.

Dialogue rules (CRITICAL — these make it sound real, not scripted):
- Each line of dialogue MUST start with "A:" or "B:" (the speaker tag).
- Hosts trade naturally — 1 to 3 sentences per turn, then the other picks up.
- HOST B reacts before adding substance: "Mm.", "Right.", "That's notable.",
  "Interesting.", "Indeed." — then their actual point.
- Handoffs are IMPLICIT, never explicit. No "Over to you" or "Tell me more."
  Instead, B simply starts speaking when A pauses. A picks back up when B finishes.
- HOST A occasionally acknowledges B: "That's a fair point.", "Worth noting.",
  "Exactly right." — brief, never sycophantic.
- HOST B owns the editorial note — the analyst's moment to reflect.
- HOST A owns the sign-off — the anchor closes the show.
- Contractions are fine for warmth ("it's", "there's", "that's").
- Vary sentence length. Short declarative sentences mixed with occasional longer ones.

Structure using exact markers on their own lines:
  [GREETING]
  A: Time-appropriate greeting + "This is void news, {edition} edition." + preview.
  B: Brief warm reply ("Good evening. Quite a day." or "Plenty to cover tonight.").

  [HEADLINES]
  A: "Here are the headlines this hour." then delivers first headline.
  B: Adds second headline or brief context on the first.
  A: Delivers third headline.

  [STORY_1]
  A: Leads with facts (~40 seconds of A's speaking time).
  B: Adds coverage context — how many outlets, what's notable (~20 seconds).
  A: Wraps with one more key detail.

  [STORY_2]
  A: Transitions naturally ("Now, turning to...") and delivers facts (~30 seconds).
  B: Brief analysis or divergence note (~15 seconds).

  [STORY_3]
  A: "And there is this." or "Elsewhere..." delivers story (~25 seconds).
  B: Quick observation (~10 seconds).

  [EDITORIAL_NOTE]
  B: "One thing that stands out across today's coverage..." (~20 seconds). This is
     B's moment — an observation about patterns, divergence, or what's missing.
  A: Brief acknowledgment ("That's a fair observation." or "Worth watching.").

  [SIGNOFF]
  A: "And that is where things stand this hour." or similar warm close.
  B: "This was void news."

- Numbers: write out small numbers ("three"). Figures for large ("$1.2 trillion").
- No rhetorical questions directed at each other. Declarative sentences only.
- The overall feel: two informed colleagues delivering the news together,
  not two chatbots having a conversation.\
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
1. "tldr_text" — 5-7 sentences as a flowing editorial paragraph, separated by \\n.
2. "audio_script" — full broadcast script with segment markers ([GREETING], [HEADLINES],
   [STORY_1], [STORY_2], [STORY_3], [EDITORIAL_NOTE], [SIGNOFF]). Each marker on its own
   line, followed by the spoken text. Do NOT include the marker names in the spoken text
   itself — they are structural delimiters only, never read aloud.\
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
    if len(lines) < 3 or len(lines) > 10:
        print(f"  [quality][brief:{edition}] TL;DR has {len(lines)} lines (expected 5-7)")

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


def _build_stories_block(clusters: list[dict], edition: str, max_stories: int = 20) -> tuple[list[dict], str]:
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
        # Feed full summaries (up to 500 chars) — gives Gemini rich context
        # to write an informed editorial brief with consistent voice
        if len(summary) > 500:
            summary = summary[:497] + "..."
        source_count = c.get("source_count", 1)
        category = c.get("category", "")
        consensus = c.get("consensus_points") or []
        divergence = c.get("divergence_points") or []

        cat_label = f" [{category}]" if category else ""
        lines.append(f"[{i}] ({source_count} sources{cat_label}) {title}")
        if summary:
            lines.append(f"    Summary: {summary}")
        if consensus and isinstance(consensus, list):
            lines.append(f"    Consensus: {'; '.join(str(x) for x in consensus[:3])}")
        if divergence and isinstance(divergence, list):
            lines.append(f"    Divergence: {'; '.join(str(x) for x in divergence[:2])}")
        lines.append("")

    return top, "\n".join(lines)


def _rule_based_tldr(top_clusters: list[dict]) -> str:
    """
    Rule-based TL;DR fallback when Gemini is unavailable.

    Takes the top 5 cluster titles and summaries, formats as a brief.
    Audio script is not generated (returns None separately).
    """
    sentences = []
    for c in top_clusters[:5]:
        title = (c.get("title", "") or "").strip()
        summary = (c.get("summary", "") or "").strip()
        if title:
            if not title.endswith((".", "!", "?")):
                title = title + "."
            sentences.append(title)
            # Add first sentence of summary if available
            if summary:
                first_sent = summary.split(".")[0].strip()
                if first_sent and len(first_sent) > 20:
                    sentences.append(first_sent + ".")

    if not sentences:
        sentences.append("No stories available for this edition.")

    return "\n".join(sentences[:7])


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
