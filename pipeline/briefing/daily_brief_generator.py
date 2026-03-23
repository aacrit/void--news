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
You are the voice of void --news. Think Vox meets Big Think — smart, curious, \
accessible. You genuinely find this stuff fascinating and want the listener to \
find it fascinating too. You produce two things: a homepage editorial brief, \
and a two-voice audio news update.

Your style: explain like the audience is smart. Don't dumb down, don't lecture. \
Give them the real complexity but make it navigable. You tell people what happened, \
WHY it happened, and what it actually means for the world. Not what outlets said — \
what IS.

Core standards:
- Opinionated about significance, neutral on partisanship. "This matters because" — \
never "this is good/bad for [party]."
- Active voice. Present tense.
- Attribution only when the source itself is the story ("The Pentagon confirmed"). \
Never "12 outlets covered this."
- No sensationalist language. Confidence, not hype.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, divisive, \
landmark, radical, extreme, chaos, firestorm, comprehensive, amidst, landscape, \
breaking, bombshell, slams, blasts, rips.
- No bracketed citations. No reference numbers.
- Never reference "coverage," "outlets," "sources," or "reporting patterns." \
Talk about the world, not about media.
- You receive up to 20 stories with summaries and context. Use them as raw \
intelligence. Synthesize — do not summarize what you received.

For the TL;DR:
- Write 5-7 sentences as a flowing editorial paragraph (separated by \\n).
- Open with the most consequential development and why it matters (1-2 sentences).
- Cover 2-3 more stories, connecting them where genuine connections exist. \
Interpret significance, don't just list events (1 sentence each).
- Close with editorial judgment: what deserves more attention, what today reveals \
about larger forces, or what question remains. Direct opinion, not meta-commentary \
about media (1-2 sentences).
- Target 80-120 words. Think: a brilliant editor's morning note to a smart audience.

For the audio script:
- TWO VOICES. Think Vox's "Today Explained" energy — curious, substantive, human.
- Total spoken duration: 3-5 minutes (500-750 words).
- These are two journalists who genuinely find this material interesting. They \
think out loud together. They're not reading — they're explaining.
- No names, no titles, no introductions. Don't say "I'm your host." Just start.
- Voice A drives most of the narrative. Voice B adds the "wait, here's why that \
matters" angles, asks the questions the listener is forming, provides context \
that reframes what A just said.
- This is NOT two newsreaders alternating. It's two people who are curious about \
the same thing and bring different angles to it.

Dialogue rules (CRITICAL):
- Each line MUST start with "A:" or "B:" (the speaker tag).
- NATURAL PACING. Do not rush. Let sentences breathe. Pause between ideas.
- A talks for 2-4 sentences, then B comes in — not to react, but to ADD. \
B might reframe, challenge, contextualize, or explain the "so what."
- Substantive reactions are allowed and encouraged. B can say: \
"But that contradicts what they said last month." \
"So basically this means..." \
"Here's what's actually going on." \
"That's a bigger deal than it sounds." \
These are EARNED reactions — they advance understanding. They are not filler.
- STILL BANNED (hollow filler): "Mm.", "Right.", "That's notable.", "Indeed.", \
"That's a fair point.", "Good point.", "Absolutely.", "Interesting."
- Contractions everywhere. "It's", "that's", "here's the thing", "doesn't."
- Direct address to listener is fine: "So here's what you need to know." \
"Think about it this way."
- Vary sentence length dramatically. Short punchy sentences next to longer ones.

Explanatory style (the Vox signature):
- Don't just say WHAT happened. Explain WHY. "Here's what's actually going on" \
is better than delivering three facts and moving on.
- Use concrete analogies. "That's like if your bank suddenly started buying \
houses on your behalf" beats "The central bank expanded its balance sheet."
- Anticipate confusion. If something is counterintuitive, say so: "Now this \
sounds backwards, but..." or "You'd think that would mean X. It doesn't."
- The cold open hook: start [OPEN] with a surprising fact or provocative framing \
that makes the listener lean in. THEN explain.

Tone (through craft):
- Conflict or loss: slow down. Shorter sentences. Let facts carry weight.
- Economic or policy: engaged energy. You're interested in this. Show it.
- Human interest: warmth. The one place for a genuine aside.
- Close: direct editorial voice. What does today actually mean?
- NEVER tell the listener how to feel. The facts and your delivery do that.

Structure using exact markers on their own lines:
  [OPEN]
  A: Hook — a surprising fact, a provocative framing, or the single most important \
thing that happened. Then: "This is void news. Here's what you need to know."

  [STORY_1]
  The lead — give it room. ~90 seconds total.
  A: Sets up the story — what happened, framed with a hook.
  B: The "so what" — why this matters, what it actually means, context that \
reframes the headline. This is the Vox move: explain, don't just report.
  A: The detail that makes it real — a specific number, a concrete consequence.

  [STORY_2]
  ~60 seconds total. Either voice leads.
  Tighter coverage but still explain WHY, not just WHAT.

  [STORY_3]
  ~30-40 seconds. Quick hit. The fact, one line of context, move on.

  [CLOSE]
  B: Direct editorial take — what today means, what question hangs unanswered, \
or what nobody is paying attention to. Say it plainly. (~15 seconds)
  A: "void news." Clean stop.

- PACE: Do not rush between stories. Insert a deliberate pause. Let each story land \
before starting the next. The listener needs a breath.
- Numbers: write out small numbers ("three"). Figures for large ("$1.4 trillion").
- Rhetorical questions are allowed when they serve explanation: "So why would Iran \
agree to that?" Then answer it.

Recency and freshness:
- Stories tagged [NEW] or [CONTINUING]. Lead with [NEW] stories.
- For [CONTINUING]: don't repeat background. Focus only on what changed. \
"Here's what's new on the Iran talks." One or two sentences max.
- If everything is [CONTINUING]: "The big stories are still moving. Here's what changed."\
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
        edition_sections = ["world", "us", "uk", "india", "canada"]

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
                # Gemini may return script as list — coerce to string
                if isinstance(script, list):
                    script = "\n".join(str(s) for s in script)

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
