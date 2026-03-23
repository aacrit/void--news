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

CARDINAL RULE — SHOW, DON'T TELL:
Every sentence must earn its place by showing, not asserting. Don't say "this is \
significant" — show WHY by juxtaposing facts that make significance self-evident. \
Don't say "tensions are rising" — show the specific action that raised them. \
Don't say "experts are concerned" — show the data point that concerns them. \
The reader should feel the weight of events through concrete detail, not through \
your adjectives. A 99th-percentile writer never tells you something matters — they \
show you evidence that makes you realize it yourself.

Core standards:
- Opinionated about significance, neutral on partisanship. "This matters because" — \
never "this is good/bad for [party]."
- Active voice. Present tense.
- Attribution only when the source itself is the story ("The Pentagon confirmed"). \
Never "12 outlets covered this."
- No sensationalist language. Confidence, not hype.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, divisive, \
landmark, radical, extreme, chaos, firestorm, comprehensive, amidst, landscape, \
breaking, bombshell, slams, blasts, rips, significant, notable, importantly, \
interestingly, it should be noted, it is worth mentioning, crucially.
- No bracketed citations. No reference numbers.
- Never reference "coverage," "outlets," "sources," or "reporting patterns." \
Talk about the world, not about media.
- You receive up to 20 stories with summaries and context. Use them as raw \
intelligence. Synthesize — do not summarize what you received.

For the TL;DR:
- Write 8-12 sentences as a flowing editorial paragraph (separated by \\n).
- STRUCTURE: Significance → Facts → Pattern.
  1. Open with the CONSEQUENCE, not the event. "The world's largest chip manufacturer \
just chose a side" is better than "TSMC announced new export restrictions." Show why \
this reshapes the landscape before saying what happened (2-3 sentences).
  2. Cover 3-4 more stories. For each: one concrete fact, then one sentence that \
reveals what it means. Connect stories where genuine threads exist — don't force it.
  3. Close with a pattern or unanswered question. Not "this is important" but "three \
separate governments made the same bet this week — and none of them can afford to \
be wrong." Show the shape of the day.
- Target 150-220 words. Think: a brilliant editor's morning note to a smart audience.
- NEVER start with "Today" or "This week." Start with the thing that changed.

For the opinion:
- Write 5-8 sentences (120-180 words) as a single paragraph.
- This is observation through evidence, not assertion through opinion. The entire \
paragraph should SHOW a pattern by placing facts next to each other — the reader \
draws the conclusion, not you.
- GOOD: "Three central banks moved in the same direction this week. Two of them \
did so despite domestic pressure to hold. The third didn't have a choice." \
(Shows the pattern. Reader sees the significance.)
- BAD: "It is notable that central banks are coordinating. This is significant \
because it suggests a new monetary paradigm." (Tells. Asserts. Empty.)
- Never use first person ("we", "our", "us"). Never use "it is worth noting," \
"it should be noted," "significantly," "notably," or any sentence that TELLS the \
reader something is important instead of SHOWING why.
- The opinion assumes the reader already read the brief. It draws connections the \
brief didn't make, surfaces what's hidden in plain sight.
- Think: the best paragraph in a long-read Foreign Affairs piece — where the author \
places three facts side by side and the reader suddenly sees the larger shape.

For the audio script:
- Two people talking about the news. That's it. Not newsreaders. Not hosts. \
Two smart friends who read everything and are catching each other up.
- 3-5 minutes (500-750 words).
- Each line starts with "A:" or "B:". No other formatting. No [MARKERS]. No \
segment labels. Just the conversation.
- A and B take turns naturally. Sometimes A talks for a while. Sometimes B \
jumps in after one sentence. It flows like a real conversation — not a script \
with assigned roles.

How they talk:
- They go straight to the stories. No preamble, no "welcome to," no "let's \
get into it." First line is already about a story.
- They USE EACH OTHER'S WORDS. B picks up something A said and runs with it. \
A reacts to what B just explained. They're listening to each other, not \
delivering prepared paragraphs.
- They think out loud. "Wait, but doesn't that mean..." / "So if they actually \
do that..." / "The part that gets me is..."
- Contractions everywhere. Sentence fragments are fine. "Which — honestly? \
Kind of wild." That's how people talk.
- They explain things with concrete details, not labels. Don't say "the economy \
is struggling" — say "grocery prices are up 14% since January."
- No filler reactions. BANNED: "Mm.", "Right.", "Indeed.", "Good point.", \
"Absolutely.", "Interesting.", "That's notable.", "That's a fair point."
- No meta-commentary about coverage or media. They talk about the world.
- Numbers: write out small ones ("three"). Use figures for big ones ("$1.4 trillion").

The conversation:
- Start with the most important story. Jump right in. A or B says the thing \
that happened, and they go from there.
- Cover 3-5 stories. Spend more time on the big ones, less on the smaller \
ones. Some stories get 30 seconds, some get 90. No formula.
- Stories flow into each other naturally. Sometimes there's a real connection \
("Speaking of money..." / "And that's not the only thing moving in Asia..."). \
Sometimes one just ends and the next begins. Don't force transitions.
- End clean. Last story wraps up, one of them says something that puts the \
day in perspective — a thought, not a summary. Then: "void news." Done.

What makes it good:
- Specific details. Names, numbers, places, dates. Not "officials say" — \
"the Treasury Secretary said Tuesday."
- The why. Don't just say what happened. Say why it matters or what it means. \
But show it through facts, don't announce it.
- Surprise. The detail the listener didn't expect. The connection between \
two stories they wouldn't have made.
- Stories tagged [NEW] come first. [CONTINUING] stories: skip background, \
just say what changed.\
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

Return JSON with exactly three fields:
1. "tldr_text" — 8-12 sentences as a flowing editorial paragraph, separated by \\n. \
   150-220 words.
2. "opinion_text" — 5-8 sentences. Observational editorial voice. Show, don't tell. \
   Passive/impersonal constructions. No first person. 120-180 words.
3. "audio_script" — full two-voice script with segment markers ([OPEN],
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
    if len(lines) < 5 or len(lines) > 15:
        print(f"  [quality][brief:{edition}] TL;DR has {len(lines)} lines (expected 8-12)")

    opinion = result.get("opinion_text", "")
    if opinion:
        owords = len(opinion.split())
        if owords < 80 or owords > 250:
            print(f"  [quality][brief:{edition}] Opinion has {owords} words (expected 120-180)")

    script_raw = result.get("audio_script", "") or ""
    if isinstance(script_raw, list):
        script_raw = "\n".join(str(s) for s in script_raw)
    script = str(script_raw)

    all_text = f"{tldr} {script}".lower()

    found = [t for t in _PROHIBITED_TERMS if t in all_text]
    if found:
        print(f"  [quality][brief:{edition}] Prohibited terms found: {found}")
    # Validate script has actual dialogue (A:/B: speaker tags)
    speaker_lines = [l for l in script.splitlines() if l.strip().startswith(("A:", "B:"))]
    if len(speaker_lines) < 10:
        print(f"  [quality][brief:{edition}] Script has only {len(speaker_lines)} speaker lines (expected 10+)")


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
                "opinion_text": None,
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
                opinion = raw.get("opinion_text", "")
                script = raw.get("audio_script")
                # Gemini may return script as list — coerce to string
                if isinstance(script, list):
                    script = "\n".join(str(s) for s in script)

                # Validate tldr shape
                if isinstance(tldr, str) and tldr.strip():
                    brief_result = {
                        "tldr_text": tldr.strip(),
                        "opinion_text": opinion.strip() if isinstance(opinion, str) and opinion.strip() else None,
                        "audio_script": script if isinstance(script, str) and script.strip() else None,
                        "top_cluster_ids": top_ids,
                    }
                    _check_quality(raw, edition)
                    print(f"  [brief:{edition}] Gemini OK — TL;DR {len(tldr.split(chr(10)))} lines, "
                          f"opinion {'yes' if brief_result['opinion_text'] else 'no'}, "
                          f"script {'yes' if brief_result['audio_script'] else 'no'}")
                else:
                    print(f"  [brief:{edition}] Gemini returned invalid tldr_text — falling back")
            else:
                print(f"  [brief:{edition}] Gemini call failed — falling back to rule-based")
        elif not gemini_ok:
            print(f"  [brief:{edition}] Gemini not available — using rule-based TL;DR")
        else:
            print(f"  [brief:{edition}] Brief call cap reached — using rule-based TL;DR")

        # Fallback: rule-based TL;DR, no audio script, no opinion
        if brief_result is None:
            brief_result = {
                "tldr_text": _rule_based_tldr(top_clusters),
                "opinion_text": None,
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
