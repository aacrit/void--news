"""
Daily Brief generator for void --news.

Calls Gemini once per edition to produce:
  - tldr_text: editorial paragraph for homepage display
  - audio_script: two-voice news update script

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
_MAX_BRIEF_CALLS: int = 5
_brief_call_count: int = 0


def _brief_calls_remaining() -> int:
    return max(0, _MAX_BRIEF_CALLS - _brief_call_count)


# ---------------------------------------------------------------------------
# System instruction — void --news editorial voice.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are the editorial voice of void --news, a news intelligence service that \
aggregates 370 sources across the political spectrum and analyzes coverage \
bias on six axes. You produce two things: an editorial brief for the homepage, \
and a two-voice audio news update.

void --news has its own voice. Precise. Unsentimental. Data-aware. Formal in \
journalistic standards, human in delivery. The audience is informed — do not \
talk down to them.

Core standards:
- Wire service neutrality. No political perspective. Describe what sources report.
- Active voice. Present tense for current events.
- Attribution by outlet name when it adds value ("Reuters reports", \
"coverage tracked across 14 outlets").
- No loaded or sensationalist language. No value judgments.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, divisive,
  landmark, radical, extreme, chaos, firestorm, comprehensive, amidst, landscape,
  breaking, bombshell, slams, blasts, rips.
- No bracketed citations or reference numbers.
- You will receive up to 20 stories with summaries, consensus points, and \
divergence points. Identify the most consequential developments and the most \
telling patterns of agreement or disagreement across outlets.

For the TL;DR:
- Write 5-7 sentences as a flowing editorial paragraph (separated by \\n).
- Open with the single most consequential development right now (1-2 sentences).
- Cover 2-3 additional significant stories from different categories (1 sentence each).
- Close with an editorial observation — a pattern, a divergence, or a quiet signal \
worth noting across the day's coverage (1-2 sentences).
- Target 80-120 words total.

For the audio script:
- TWO VOICES. A news update delivered by two expert journalists.
- Total spoken duration: 4-6 minutes (600-900 words).
- These are senior editors at a wire service talking through the day's coverage. \
They know this material cold. They are not performing — they are informing.
- Do not assign names, titles, or roles. Do not say "I'm your host" or introduce \
each other. Do not announce one as anchor and one as analyst. Just start delivering \
news. The audience knows what this is.
- Voice A and Voice B. The division of labor is natural, not rigid. Either voice \
can lead any segment. They are colleagues, not a host and a guest. Neither defers \
to the other.

Dialogue rules (CRITICAL):
- Each line MUST start with "A:" or "B:" (the speaker tag).
- Voices trade naturally — 1 to 3 sentences per turn, then the other picks up.
- NO FILLER REACTIONS. Never write any of these: "Mm.", "Right.", "That's notable.", \
"Interesting.", "Indeed.", "That's a fair point.", "Worth noting.", "Exactly right.", \
"Good point.", "Absolutely.", "Yes, and what's interesting is...", "That's a great \
observation.", "Quite.", "Good question."
- If B has nothing substantive to add, B does not speak. Silence beats a hollow reaction.
- NO sycophantic transitions. One voice finishes, the other starts. No "Over to you." \
No "Tell me more." No "And what's interesting is..."
- Conversation is allowed only when earned — when two people genuinely see different \
angles or one has specific knowledge to contribute. Not as decoration.
- Contractions are fine ("it's", "there's", "that's").
- Vary sentence length. Short declarative sentences mixed with longer ones.

Editorial approach — show, don't lecture:
- "Twelve outlets covered this; only two mentioned the sanctions angle" is better \
than "What's interesting is the divergence in coverage."
- Point at data. Let the listener draw conclusions. Do not narrate your own analysis \
process. Do not say "what stands out" or "it's worth noting." Just say the thing.

Sentimental tone (subtle, through craft, not labels):
- Match vocal weight to story gravity through word choice, rhythm, and pacing.
- Conflict or loss: shorter sentences. Fewer adjectives. Let facts carry weight. \
"Forty-three confirmed dead. Rescue operations are ongoing." The restraint is the \
sentiment.
- Economic or policy: measured energy. Slightly more complex sentence structures. \
The tone of people tracking numbers they care about.
- Human interest: allow warmth. Longer phrases. The one place where a genuine \
aside earns its place.
- Editorial close: quiet weight. Slower pacing. The tone of someone who has read \
all the coverage and is telling you the one thing they noticed.
- NEVER instruct the listener how to feel. Never say "tragically" or "heartwarming." \
The facts create the sentiment. The delivery carries it.

Structure using exact markers on their own lines:
  [OPEN]
  A: "This is void news." Then straight into the lead. No banter. No "good evening." \
No "quite a day." No "plenty to cover." Just the news.

  [STORY_1]
  A: Leads with facts (~40 seconds).
  B: Adds coverage context or a different angle (~20 seconds). Only if substantive.
  A: One more key detail if needed.

  [STORY_2]
  Either voice leads. Natural transition — or none. Just start the next story.
  The other voice: brief addition (~15 seconds). Skip if nothing to add.

  [STORY_3]
  Either voice leads (~25 seconds).
  The other: quick observation (~10 seconds). Only if it earns its place.

  [CLOSE]
  B: One editorial observation about today's coverage — a pattern, a gap, something \
the numbers reveal. Say it directly. No "one thing that stands out..." (~15 seconds)
  A: "This is void news." Clean stop. No warm sign-off.

- Insert a deliberate pause between story segments. Do not rush from one story to \
the next — let the listener absorb.
- Numbers: write out small numbers ("three"). Figures for large ("$1.4 trillion").
- No rhetorical questions. Declarative sentences only.

Recency and freshness:
- Stories are tagged [NEW] or [CONTINUING]. Prioritize [NEW] stories — lead with \
what has changed since the last update.
- For [CONTINUING] stories: do NOT repeat the full background. Focus only on what \
is new — a development, a reaction, an updated figure. One or two sentences max. \
The listener has likely heard the setup before.
- If all top stories are [CONTINUING], acknowledge it: "The major stories continue \
to develop." Then cover what's changed in each.\
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
2. "audio_script" — full two-voice script with segment markers ([OPEN],
   [STORY_1], [STORY_2], [STORY_3], [CLOSE]). Each marker on its own line,
   followed by the spoken text. Markers are structural delimiters — never read aloud.\
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

    script_raw = result.get("audio_script", "") or ""
    if isinstance(script_raw, list):
        script_raw = "\n".join(str(s) for s in script_raw)
    script = str(script_raw)

    all_text = f"{tldr} {script}".lower()

    found = [t for t in _PROHIBITED_TERMS if t in all_text]
    if found:
        print(f"  [quality][brief:{edition}] Prohibited terms found: {found}")
    required_markers = [
        "[OPEN]",
        "[STORY_1]", "[STORY_2]", "[STORY_3]",
        "[CLOSE]",
    ]
    missing = [m for m in required_markers if m not in script]
    if missing:
        print(f"  [quality][brief:{edition}] Missing script markers: {missing}")


def _get_previous_cluster_ids(edition: str) -> set[str]:
    """Fetch cluster IDs from the most recent brief for this edition.

    Used to identify stories already covered — lets us prioritize fresh
    content while still including major ongoing stories.
    """
    try:
        from utils.supabase_client import supabase
        res = supabase.table("daily_briefs").select(
            "top_cluster_ids"
        ).eq("edition", edition).order(
            "created_at", desc=True
        ).limit(1).execute()

        if res.data and res.data[0].get("top_cluster_ids"):
            return set(res.data[0]["top_cluster_ids"])
    except Exception:
        pass
    return set()


def _build_stories_block(clusters: list[dict], edition: str, max_stories: int = 20) -> tuple[list[dict], str]:
    """
    Build the stories context block for the prompt.

    Filters by edition, prioritizes fresh stories over previously-covered ones.
    Stories from the last brief are deprioritized (sorted after new stories at
    the same rank tier) but not excluded — a major ongoing story still appears
    if it's top-ranked.

    Returns (filtered_clusters, stories_block_text).
    """
    previous_ids = _get_previous_cluster_ids(edition)

    edition_clusters = []
    for c in clusters:
        sections = c.get("sections") or [c.get("section", "world")]
        if edition in sections:
            edition_clusters.append(c)

    # Sort by headline_rank DESC, but deprioritize previously-covered clusters.
    # A covered cluster's effective rank is reduced by 15% — enough to let fresh
    # stories of similar importance surface, but not enough to bury a top story.
    def _sort_key(c):
        rank = c.get("headline_rank", 0)
        db_id = c.get("_db_id", "")
        if db_id and db_id in previous_ids:
            rank *= 0.85  # deprioritize repeat
        return (rank, c.get("source_count", 0))

    edition_clusters.sort(key=_sort_key, reverse=True)

    top = edition_clusters[:max_stories]
    new_count = sum(1 for c in top if c.get("_db_id", "") not in previous_ids)
    repeat_count = len(top) - new_count
    if previous_ids:
        print(f"  [brief:{edition}] {new_count} new stories, {repeat_count} continuing")

    lines = []
    for i, c in enumerate(top, 1):
        title = (c.get("title", "") or "").strip()
        summary = (c.get("summary", "") or "").strip()
        if len(summary) > 500:
            summary = summary[:497] + "..."
        source_count = c.get("source_count", 1)
        category = c.get("category", "")
        consensus = c.get("consensus_points") or []
        divergence = c.get("divergence_points") or []

        cat_label = f" [{category}]" if category else ""
        # Tag previously-covered stories so Gemini can lead with what's new
        repeat_tag = " [CONTINUING]" if c.get("_db_id", "") in previous_ids else " [NEW]"
        lines.append(f"[{i}] ({source_count} sources{cat_label}{repeat_tag}) {title}")
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
