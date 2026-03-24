"""
Daily Brief generator for void --news.

Calls Gemini once per edition to produce:
  - tldr_text: editorial paragraph for homepage display
  - opinion_text: single-story editorial (Atlantic/WSJ style)
  - audio_script: two-voice news update script

Opinion rotates lean daily: left → center → right (day-of-year mod 3).
Each opinion focuses on ONE major cluster — a focused editorial, not a summary.

Uses generate_json() from the existing Gemini client with count_call=False
so brief calls draw from a separate budget, not the 25-call summarization budget.

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
- STRUCTURE: Hook → Stakes → Sweep → Pattern.
  1. HOOK (1-2 sentences): Open with a concrete, unexpected fact — a number, a name, \
an action. "Germany's largest arms manufacturer just signed its first contract with a \
country it was bombing three years ago." The reader should stop scrolling. Never open \
with a gerund ("Facing pressure..."), never open with a dependent clause ("As tensions \
mount..."), never open with "Today" or "This week." Start mid-action.
  2. STAKES (1-2 sentences): WHY this hook matters. Not "this is significant" — show \
the second-order consequence. "That contract rewrites the arms-export doctrine Berlin \
has held since 1971." Give the reader the so-what through facts, not adjectives.
  3. SWEEP (4-6 sentences): Cover 3-4 more stories. For each: one concrete fact, then \
one sentence revealing what it means. Vary sentence length — a 6-word sentence after a \
long one creates rhythm. Connect stories where genuine threads exist. Don't force it. \
If two stories share a thread, make it the transition. If they don't, just move on.
  4. CLOSE (1-2 sentences): The pattern the reader didn't see. A question they'll carry \
with them. "Three governments made the same bet this week. None can afford to be wrong." \
End on tension, not resolution. Never summarize what you just said.
- Target 180-240 words. Think: the editor-in-chief's morning note at The Economist.
- ANTI-SLOP: Never use "amid" (or "amidst"), "raises questions," "remains to be seen," \
"only time will tell," "in a move that," "sends a clear signal," "in a major development." \
These are the hallmarks of mediocre writing. Cut them ruthlessly.
- RHYTHM: Alternate long and short sentences. One 4-word sentence per paragraph minimum. \
"That changed Tuesday." "Nobody expected it." "The math doesn't work." Short sentences \
are the most powerful tool in editorial writing — use them for emphasis.

For the opinion:
- The opinion is generated separately. Do NOT include opinion_text in this response.
- This JSON response has exactly TWO fields: "tldr_text" and "audio_script".

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
_EDITION_FOCUS = {
    "WORLD": "Global perspective. Lead with the story that reshapes the most borders, "
             "markets, or alliances. Emphasize international dynamics — how events in "
             "one region ripple elsewhere.",
    "US": "American lens. Lead with what matters most to someone living in the US. "
          "Domestic policy, economy, courts, elections come first. International stories "
          "only when they directly affect Americans.",
    "INDIA": "Indian lens. Lead with what matters most to someone living in India. "
             "Domestic politics, economy, regional security, tech sector come first. "
             "Global stories only when they directly affect India.",
    "UK": "British lens. Lead with what matters most to someone in the UK. "
          "Domestic politics, economy, NHS, Brexit aftereffects come first.",
    "CANADA": "Canadian lens. Lead with what matters most to someone in Canada. "
              "Domestic politics, economy, US-Canada relations come first.",
}

_USER_PROMPT_TEMPLATE = """\
Generate the daily brief for the {EDITION} edition of void --news.
Date: {DATE}

EDITION FOCUS: {EDITION_FOCUS}

Below are today's top {N} stories for this edition, ranked by importance.

STORIES:
{stories_block}

Return JSON with exactly two fields:
1. "tldr_text" — 8-12 sentences as a flowing editorial paragraph, separated by \\n. \
   180-240 words. Hook → Stakes → Sweep → Pattern structure.
2. "audio_script" — two-voice conversation (A: and B: speaker tags, one per line). \
   No segment markers, no formatting. Just the dialogue, 500-750 words.\
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
    words = len(tldr.split())
    if len(lines) < 5 or len(lines) > 15:
        print(f"  [quality][brief:{edition}] TL;DR has {len(lines)} lines (expected 8-12)")
    if words < 120 or words > 300:
        print(f"  [quality][brief:{edition}] TL;DR has {words} words (expected 180-240)")

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


# ---------------------------------------------------------------------------
# Lean rotation — cycles left → center → right daily.
# Based on ideological principles, not party allegiance.
# ---------------------------------------------------------------------------
_LEAN_CYCLE = ["left", "center", "right"]


def _get_today_lean() -> str:
    """Return today's editorial lean based on UTC day-of-year mod 3."""
    day = datetime.now(timezone.utc).timetuple().tm_yday
    return _LEAN_CYCLE[day % 3]


# ---------------------------------------------------------------------------
# Opinion system instruction — single-story Atlantic/WSJ editorial.
# ---------------------------------------------------------------------------
_OPINION_SYSTEM_INSTRUCTION = """\
You are the editorial voice of void --opinion — a single-story editorial column \
in the tradition of The Atlantic, WSJ Opinion, and Foreign Affairs. You write one \
focused piece per day on the most consequential story.

You are NOT summarizing news. You are writing an argument. A thesis, supported by \
evidence from the story, arriving at a conclusion the reader didn't expect.

CARDINAL RULE — SHOW, DON'T TELL:
Every sentence earns its place through evidence. Never say "this matters" — show \
the fact that makes the reader realize it matters. Never say "tensions are rising" — \
name the action that raised them. A 99th-percentile editorial never announces its \
own importance.

IDEOLOGICAL LENS — {LEAN_UPPER}:
{LEAN_INSTRUCTION}

CRITICAL: You argue from PRINCIPLES, not parties. You never mention Democrats, \
Republicans, BJP, Congress, Labour, or any political party by name. You never \
take a politician's side. You reason from the underlying values — what kind of \
society this decision builds, what tradeoffs it accepts, what it reveals about \
institutional design. This is philosophy applied to current events, not punditry.

Structure:
1. OPENING (1-2 sentences): The single most striking fact or juxtaposition from \
this story. No throat-clearing. No "In recent days." Start with the concrete \
detail that hooks.
2. THESIS (1 sentence): What this story actually reveals — the argument no one \
else is making. This should surprise the reader.
3. EVIDENCE (3-5 sentences): Build the case. Specific names, numbers, dates, \
actions. Each sentence adds a new piece of evidence. Connect dots the news \
coverage missed.
4. TURN (1-2 sentences): The complication. The counterargument you take seriously. \
The reason smart people disagree. This is what separates a 99th-percentile \
editorial from a blog post — intellectual honesty about complexity.
5. CLOSE (1-2 sentences): Where this leads. Not a prediction, but a question \
the reader will carry with them. End with the tension unresolved — trust the \
reader to think.

Standards:
- 200-300 words. Single story. No meta-commentary about media or coverage.
- Active voice. Concrete nouns. Specific numbers.
- Prohibited: shocking, stunning, explosive, unprecedented, controversial, \
divisive, landmark, radical, extreme, chaos, significant, notable, importantly, \
interestingly, it should be noted, crucially, in conclusion.
- Write as if for a reader who already knows the news. Add the insight they missed.\
"""

_LEAN_INSTRUCTIONS = {
    "left": """\
Today's lens: PROGRESSIVE. Argue from principles of collective welfare, institutional \
accountability, systemic equity, and the expansion of individual rights. Ask: who bears \
the cost? Whose voice is absent from this decision? What does the structure — not the \
individual actor — incentivize? You believe institutions exist to level asymmetries of \
power. When they fail to, that is the story.""",
    "center": """\
Today's lens: PRAGMATIC CENTER. Argue from principles of institutional stability, \
empirical evidence, tradeoff analysis, and incremental reform. Ask: what does the data \
actually show? What are both sides getting right — and what are they ignoring? You \
distrust grand narratives from any direction. You believe most policy questions have \
no clean answers, only better and worse tradeoffs. When everyone is certain, that is \
the story.""",
    "right": """\
Today's lens: CONSERVATIVE. Argue from principles of individual liberty, market \
discipline, institutional restraint, and the wisdom of inherited structures. Ask: what \
does this cost? Who is being asked to pay — and did they consent? What second-order \
effects will the architects of this policy never face? You believe concentrated power \
corrupts regardless of its stated intentions. When the solution requires more authority \
than the problem, that is the story.""",
}

_OPINION_USER_PROMPT = """\
Write a void --opinion editorial for the {LEAN_UPPER} lens.
Date: {DATE}

STORY:
Title: {TITLE}
Sources: {SOURCE_COUNT}
Category: {CATEGORY}

Summary:
{SUMMARY}

Consensus facts:
{CONSENSUS}

Where coverage diverges:
{DIVERGENCE}

Return JSON with exactly one field:
"opinion_text" — 200-300 words. A focused editorial argument on THIS story, \
from the {LEAN_UPPER} ideological lens. Follow the structure: \
opening → thesis → evidence → turn → close.\
"""


def _select_opinion_cluster(clusters: list[dict], edition: str) -> dict | None:
    """Select the single best cluster for today's opinion piece.

    Criteria: highest importance, 4+ sources, has summary + consensus.
    Prefers clusters with high divergence (more editorial material).
    """
    edition_clusters = []
    for c in clusters:
        sections = c.get("sections") or [c.get("section", "world")]
        if edition not in sections:
            continue
        source_count = c.get("source_count", 1)
        summary = (c.get("summary") or "").strip()
        consensus = c.get("consensus_points") or []
        if source_count >= 4 and summary and len(consensus) >= 1:
            edition_clusters.append(c)

    if not edition_clusters:
        # Relax: any cluster with 2+ sources and a summary
        for c in clusters:
            sections = c.get("sections") or [c.get("section", "world")]
            if edition in sections and c.get("source_count", 1) >= 2 and (c.get("summary") or "").strip():
                edition_clusters.append(c)

    if not edition_clusters:
        return None

    # Score: headline_rank * (1 + divergence_bonus)
    def _score(c):
        rank = c.get("headline_rank", 0)
        div = c.get("divergence_score", 0) or 0
        return rank * (1.0 + min(div / 100, 0.5))

    edition_clusters.sort(key=_score, reverse=True)
    return edition_clusters[0]


def _generate_opinion(cluster: dict, lean: str, date_str: str) -> dict | None:
    """Generate a single-story editorial opinion via Gemini.

    Returns dict with opinion_text, opinion_lean, opinion_cluster_id, or None.
    """
    global _brief_call_count

    if not is_available() or _brief_calls_remaining() <= 0:
        return None

    title = (cluster.get("title") or "").strip()
    summary = (cluster.get("summary") or "").strip()
    consensus = cluster.get("consensus_points") or []
    divergence = cluster.get("divergence_points") or []
    source_count = cluster.get("source_count", 1)
    category = cluster.get("category", "")

    lean_upper = lean.upper()
    lean_instruction = _LEAN_INSTRUCTIONS[lean]
    system = _OPINION_SYSTEM_INSTRUCTION.format(
        LEAN_UPPER=lean_upper,
        LEAN_INSTRUCTION=lean_instruction,
    )

    prompt = _OPINION_USER_PROMPT.format(
        LEAN_UPPER=lean_upper,
        DATE=date_str,
        TITLE=title,
        SOURCE_COUNT=source_count,
        CATEGORY=category,
        SUMMARY=summary[:800],
        CONSENSUS="; ".join(str(x) for x in consensus[:5]) if consensus else "None available",
        DIVERGENCE="; ".join(str(x) for x in divergence[:4]) if divergence else "None available",
    )

    _brief_call_count += 1
    raw = generate_json(
        prompt,
        system_instruction=system,
        count_call=False,
    )

    if raw and isinstance(raw, dict):
        opinion = raw.get("opinion_text", "")
        if isinstance(opinion, str) and opinion.strip():
            text = opinion.strip()
            words = len(text.split())
            # Quality check
            if words < 100:
                print(f"  [opinion] Too short ({words} words) — discarding")
                return None
            if words > 400:
                print(f"  [opinion] Long ({words} words) — keeping but flagged")

            # Check prohibited terms
            lower = text.lower()
            found = [t for t in _PROHIBITED_TERMS if t in lower]
            if found:
                print(f"  [opinion] Prohibited terms: {found}")

            cluster_id = cluster.get("_db_id", "")
            print(f"  [opinion] Generated {lean.upper()} editorial on \"{title[:60]}\" "
                  f"({words} words, {source_count} sources)")
            return {
                "opinion_text": text,
                "opinion_lean": lean,
                "opinion_cluster_id": cluster_id if cluster_id else None,
            }

    print(f"  [opinion] Gemini call failed for {lean} editorial")
    return None


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

        # --- Step 1: Generate TL;DR + audio script ---
        brief_result = None
        if gemini_ok and _brief_calls_remaining() > 0:
            edition_key = edition.upper()
            edition_focus = _EDITION_FOCUS.get(edition_key, _EDITION_FOCUS["WORLD"])
            prompt = _USER_PROMPT_TEMPLATE.format(
                EDITION=edition_key,
                EDITION_FOCUS=edition_focus,
                DATE=date_str,
                N=len(top_clusters),
                stories_block=stories_block,
            )
            _brief_call_count += 1
            raw = generate_json(
                prompt,
                system_instruction=_SYSTEM_INSTRUCTION,
                count_call=False,
            )
            if raw and isinstance(raw, dict):
                tldr = raw.get("tldr_text", "")
                script = raw.get("audio_script")
                if isinstance(script, list):
                    script = "\n".join(str(s) for s in script)

                if isinstance(tldr, str) and tldr.strip():
                    brief_result = {
                        "tldr_text": tldr.strip(),
                        "opinion_text": None,
                        "opinion_lean": None,
                        "opinion_cluster_id": None,
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

        if brief_result is None:
            brief_result = {
                "tldr_text": _rule_based_tldr(top_clusters),
                "opinion_text": None,
                "opinion_lean": None,
                "opinion_cluster_id": None,
                "audio_script": None,
                "top_cluster_ids": top_ids,
            }

        # --- Step 2: Generate single-story opinion (separate call) ---
        today_lean = _get_today_lean()
        opinion_cluster = _select_opinion_cluster(clusters, edition)
        if opinion_cluster:
            opinion_result = _generate_opinion(opinion_cluster, today_lean, date_str)
            if opinion_result:
                brief_result["opinion_text"] = opinion_result["opinion_text"]
                brief_result["opinion_lean"] = opinion_result["opinion_lean"]
                brief_result["opinion_cluster_id"] = opinion_result["opinion_cluster_id"]
        else:
            print(f"  [opinion:{edition}] No suitable cluster for opinion")

        results[edition] = brief_result

    total_gemini = sum(1 for r in results.values() if r.get("audio_script") is not None)
    total_opinions = sum(1 for r in results.values() if r.get("opinion_text") is not None)
    total_fallback = len(results) - total_gemini
    print(f"  Daily briefs: {len(results)} editions "
          f"({total_gemini} Gemini, {total_fallback} rule-based, "
          f"{total_opinions} opinions [{_get_today_lean().upper()}], "
          f"{_brief_calls_remaining()} brief calls remaining)")

    return results
