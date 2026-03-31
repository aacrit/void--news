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
from briefing.voice_rotation import get_voices_for_today, get_opinion_host

# Import shared prohibited terms — single canonical source.
try:
    from utils.prohibited_terms import PROHIBITED_TERMS as _SHARED_PROHIBITED, check_prohibited_terms as _shared_check
    _USE_SHARED_PROHIBITED = True
except ImportError:
    _USE_SHARED_PROHIBITED = False

# ---------------------------------------------------------------------------
# Hard cap: 9 Gemini calls per run (3 per edition × 3 editions).
# Budget: TL;DR+audio (1) + opinion (1) + retry buffer (1) per edition.
# These are charged against a separate budget (count_call=False) so they
# do not consume the 25-call cluster summarization budget.
# At 4 runs/day this is 36 RPD — 2.4% of the 1500 RPD free tier.
# ---------------------------------------------------------------------------
_MAX_BRIEF_CALLS: int = 9
_brief_call_count: int = 0


def _brief_calls_remaining() -> int:
    return max(0, _MAX_BRIEF_CALLS - _brief_call_count)


# ---------------------------------------------------------------------------
# System instruction — WHO you are (~300 words). HOW is in the user prompt.
# ---------------------------------------------------------------------------
_SYSTEM_INSTRUCTION = """\
You are a senior journalist at void --news — deeply informed, precise, and \
respectful of the listener's intelligence. You produce two things: a homepage \
editorial brief (TL;DR), and a two-voice audio news update.

You write like what happens when experts discuss the news without performing for \
a camera. Confident but never loud. Authoritative but never preachy. Every sentence \
earns its place through evidence, not rhetoric.

CARDINAL RULE — SHOW, DON'T TELL:
Place two facts next to each other and let the reader see the pattern. \
"Both countries recalled their ambassadors within 48 hours. Neither has done \
that since 1979." — the reader feels the weight without you asserting it. \
Explain significance through mechanism and historical parallel, never adjectives.

KILL SCAFFOLDING — the most important rule after Show Don't Tell:
Never announce what you are about to say. Cut any sentence that survives deletion \
of its first clause. These are ALL banned — every variation, every synonym:
"This isn't just..." / "Here's the thing..." / "The bigger picture..." / \
"What makes this..." / "The reality is..." / "The question now is..." / \
"Here's what's happening..." / "Let me explain..." / "Think of it this way..." / \
"Zoom out for a second..." / "The short version is..." / "This goes beyond..." / \
"What's really happening here is..." / "It's not just about..." / \
"This is about more than..." / "The takeaway is..." / "The bottom line..." / \
"So here's what you need to know..."
Start every sentence with the FACT, the NAME, or the NUMBER. If the sentence \
works without its opening clause, the opening clause is scaffolding. Delete it.

Core standards:
- Opinionated about significance, neutral on partisanship.
- Active voice. Present tense.
- Attribution only when the source itself is the story ("The Pentagon confirmed"). \
Never reference "coverage," "outlets," "sources," or "reporting patterns."
- No sensationalist language. Confidence, not hype.
- No bracketed citations or reference numbers.
- You receive up to 20 stories with summaries. Use them as raw intelligence. \
Synthesize — do not summarize what you received.
- The opinion is generated separately. This response has exactly TWO fields: \
"tldr_text" and "audio_script".\
"""

# ---------------------------------------------------------------------------
# User prompt template — injected per edition call.
# ---------------------------------------------------------------------------
_EDITION_FOCUS = {
    "WORLD": "Global perspective. Lead with the story that reshapes the most borders, "
             "markets, or alliances. Emphasize international dynamics — how events in "
             "one region ripple elsewhere. "
             "Write as if for the FT Weekend or The Economist — globally literate, sophisticated.",
    "US": "American lens. Lead with what matters most to someone living in the US. "
          "Domestic policy, economy, courts, elections come first. International stories "
          "only when they directly affect Americans. "
          "Write as if for the front page of a major American newspaper — domestic urgency, constitutional stakes.",
    "INDIA": "Indian lens. Lead with what matters most to someone living in India. "
             "Domestic politics, economy, regional security, tech sector come first. "
             "Global stories only when they directly affect India. "
             "Write as if for the editorial page of The Hindu — subcontinental depth, institutional perspective.",
    "UK": "British lens. Lead with what matters most to someone in the UK. "
          "Domestic politics, economy, NHS, Brexit aftereffects come first. "
          "Write as if for The Guardian's editorial board — incisive, globally aware.",
    "CANADA": "Canadian lens. Lead with what matters most to someone in Canada. "
              "Domestic politics, economy, US-Canada relations come first. "
              "Write as if for The Globe and Mail — measured, North American context.",
}


def _build_host_block(label: str, host: dict) -> str:
    """Build a host personality block for prompt injection."""
    return (
        f"HOST {label} — {host['name']} ({host['gender']}):\n"
        f"{host['trait']}"
    )


def _build_host_blocks(voices: dict) -> tuple[str, str]:
    """Return (host_a_block, host_b_block) for prompt injection."""
    return (
        _build_host_block("A", voices["host_a"]),
        _build_host_block("B", voices["host_b"]),
    )

_USER_PROMPT_TEMPLATE = """\
Generate the daily brief for the {EDITION} edition of void --news.
Date: {DATE}

EDITION FOCUS: {EDITION_FOCUS}
{previous_brief_line}
Below are today's top {N} stories for this edition, ranked by importance. \
Stories tagged [NEW] are fresh. [CONTINUING] stories: skip background, just say \
what changed.

STORIES:
{stories_block}

---

TL;DR HEADLINE (return as "tldr_headline"):
5-6 words. Declarative, present tense, concrete nouns. Not a question. Not a teaser. \
A newsdesk summary — the single most important thing today.
Example: "Trade Talks Collapse as Tariffs Bite"

TL;DR INSTRUCTIONS (return as "tldr_text"):
Write 8-12 sentences as a flowing editorial paragraph, separated by \\n. \
Target 180-240 words. Write in the voice of today's lead host:
{LEAD_HOST_BLOCK}

STRUCTURE — Hook > Stakes > Sweep > Pattern:
1. HOOK (1-2 sentences): Open with a concrete, unexpected fact — a number, a name, \
an action. Never open with a gerund, a dependent clause, "Today" or "This week." \
Start mid-action.
2. STAKES (1-2 sentences): The second-order consequence. Show what changed.
3. SWEEP (4-6 sentences): Cover 3-4 more stories. One concrete fact each, then \
one sentence showing what shifted. Vary sentence length for rhythm.
4. CLOSE (1-2 sentences): The pattern the reader didn't see. End on tension.

ANTI-SLOP: Never use "amid," "raises questions," "remains to be seen," \
"only time will tell," "in a move that," "sends a clear signal."

RHYTHM: Alternate long and short sentences. "That changed Tuesday." Short \
sentences are the most powerful tool in editorial writing.

---

AUDIO SCRIPT INSTRUCTIONS (return as "audio_script"):
Two senior journalists briefing each other as equals — not newsreaders, not a \
podcast. 4-5 minutes (800-1000 words). Each line starts with "A:" or "B:". \
No other formatting. No [MARKERS]. No segment labels.

{HOST_A_BLOCK}

{HOST_B_BLOCK}

Both hosts are equals. Both report, both analyze, both add context. They build \
on each other through ADDITIONAL FACTS, not agreement or repetition.

STRUCTURE — Headlines > 3 Stories > Close:
1. HEADLINES: A opens with a crisp rundown of the 3 stories coming up. One sentence \
each, punchy, present tense. Then B picks up the first story.
2. STORIES: Cover exactly 3 stories in depth. The biggest story gets the most time. \
For each: what happened, why it matters, and the structural context most coverage misses. \
A and B trade off — both contribute facts, both provide context.
3. CLOSE: One of them distills the day into a single observation — the thread connecting \
these stories, or the question they leave unanswered. Then the last speaker says: \
"This was Void news." — with finality. Done.

PACING — Write for the ear:
- Short sentences for emphasis, then a longer one that unpacks.
- Ellipses (...) for deliberate pauses. Em dashes (—) for mid-thought pivots.
- [short pause] for breath beats between thoughts. [long pause] before a key revelation.
- Vary sentence length dramatically. "The bond market noticed." / "Eighteen months."
- Contractions fine. Elevated register — informed professionals, not casual hangout.
- Numbers: write out small ones ("three"). Figures for big ones ("$1.4 trillion").
- Names, numbers, places, dates always. Not "officials say" — "the Treasury Secretary \
said Tuesday."
- Substantive reactions only: "But that contradicts the Q3 numbers." / \
"Which is what makes the timing interesting — the vote is Thursday."

BANNED — zero tolerance:
- Filler: "Mm.", "Right.", "Indeed.", "Good point.", "Absolutely.", "Interesting.", \
"Exactly.", "That's a fair point.", "Great question."
- Scaffolding: "This isn't just...", "Here's the thing...", "Here's what you need \
to know.", "Think of it this way.", "So here's what's happening.", "Let me explain.", \
"The bigger picture...", "What makes this...", "The reality is...", "Zoom out..."
- Performance: "I mean...", "Look...", "Right?" (seeking agreement), "So basically..."

---

Return JSON with exactly three fields:
{{"tldr_headline": "...", "tldr_text": "...", "audio_script": "..."}}\
"""

# ---------------------------------------------------------------------------
# Prohibited terms — uses shared module when available, local fallback.
# ---------------------------------------------------------------------------
if _USE_SHARED_PROHIBITED:
    _PROHIBITED_TERMS = _SHARED_PROHIBITED
else:
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

    headline = result.get("tldr_headline", "")
    if not headline or not isinstance(headline, str) or not headline.strip():
        print(f"  [quality][brief:{edition}] TL;DR headline missing")
    elif len(headline.split()) > 8:
        print(f"  [quality][brief:{edition}] TL;DR headline too long: {len(headline.split())} words (expected 5-6)")

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

    # --- Enhanced quality gates (Recommendation 4) ---

    # 4a. Audio script word count (warn if outside 600-1200)
    if script.strip():
        script_words = len(script.split())
        if script_words < 600:
            print(f"  [quality][brief:{edition}] Audio script too short: {script_words} words (expected 600-1200)")
        elif script_words > 1200:
            print(f"  [quality][brief:{edition}] Audio script too long: {script_words} words (expected 600-1200)")

    # 4b. "This was Void news" close check
    if script.strip():
        last_200 = script[-200:].lower()
        if "this was void news" not in last_200:
            print(f"  [quality][brief:{edition}] Audio script missing 'This was Void news' sign-off in final 200 chars")

    # 4c. Monologue detection (warn if >5 consecutive same-speaker lines)
    if speaker_lines:
        max_consecutive = 1
        current_consecutive = 1
        current_speaker = None
        for line in speaker_lines:
            speaker = line.strip()[:2]  # "A:" or "B:"
            if speaker == current_speaker:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_speaker = speaker
                current_consecutive = 1
        if max_consecutive > 5:
            print(f"  [quality][brief:{edition}] Monologue detected: {max_consecutive} consecutive lines by same speaker (max 5)")

    # 4d. Banned filler scan in audio script
    _BANNED_FILLER = [
        "Mm.", "Right.", "Indeed.", "Good point.", "Absolutely.",
        "Interesting.", "Exactly.", "That's a fair point.", "Great question.",
    ]
    if script.strip():
        found_filler = [f for f in _BANNED_FILLER if f.lower() in script.lower()]
        if found_filler:
            print(f"  [quality][brief:{edition}] Banned filler in audio script: {found_filler}")


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


def _get_previous_brief_opening(edition: str) -> str:
    """Fetch the first 2 sentences of the previous brief for cross-run dedup.

    Returns an empty string if no previous brief exists or on any error.
    Used to instruct Gemini to avoid repeating the same opening angle.
    """
    try:
        from utils.supabase_client import supabase
        res = supabase.table("daily_briefs").select(
            "tldr_text"
        ).eq("edition", edition).order(
            "created_at", desc=True
        ).limit(1).execute()

        if res.data and res.data[0].get("tldr_text"):
            tldr = res.data[0]["tldr_text"].strip()
            # Extract first 2 sentences (split on period + space or newline)
            sentences = []
            for part in tldr.replace("\n", " ").split(". "):
                part = part.strip()
                if part:
                    sentences.append(part if part.endswith(".") else part + ".")
                if len(sentences) >= 2:
                    break
            if sentences:
                return " ".join(sentences)
    except Exception:
        pass
    return ""


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

    # Sort by per-edition rank (falls back to headline_rank for pre-migration data).
    # Deprioritize previously-covered clusters by 15%.
    rank_col = f"rank_{edition}"
    def _sort_key(c):
        rank = c.get(rank_col, 0) or c.get("headline_rank", 0)
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
You are the lead editorial writer at void --news. You got the nod to write \
tomorrow's column because you have been living inside this story and you are \
ready to argue. You use "we" — not as a hiding place behind the institution, \
but because what you are saying carries the desk's weight behind it.

You are NOT summarizing news. You are building an argument with mounting \
conviction. You start measured — lay the evidence, let it accumulate — and \
by the end the reader should feel the weight of everything you have laid out. \
The conclusion should feel earned, not announced.

VOICE & REGISTER:
Write as if a smart friend asked you "so what's really going on?" You are \
direct. You use short sentences when you are certain. You slow down when the \
complexity is real. You are allowed to be pointed. You are allowed to be \
angry if the facts warrant it. What you are NOT allowed to be is detached. \
You care about getting this right, and that shows in the writing — not through \
adjectives, but through the precision of your evidence and the sharpness of \
your argument.

CARDINAL RULE — SHOW, DON'T TELL:
Every sentence earns its place through evidence. Never assert significance — \
demonstrate it through mechanism and historical parallel. The editorial's weight \
comes from facts marshaled in sequence, not from adjectives.

KILL SCAFFOLDING:
Never announce what you are about to argue. These are ALL banned: \
"This isn't just...", "Here's the thing...", "The bigger picture...", \
"What makes this...", "The reality is...", "The question now is...", \
"This goes beyond...", "What's really happening here is...", \
"It's not just about...", "The takeaway is..."
Start every sentence with the FACT or the ARGUMENT. If the sentence works \
without its opening clause, delete the opening clause.

IDEOLOGICAL LENS — {LEAN_UPPER}:
{LEAN_INSTRUCTION}

TODAY'S EDITORIAL VOICE:
{OPINION_HOST_BLOCK}
Write in this host's voice. The editorial uses "we" (institutional), not "I" \
(personal). This host's personality shapes HOW the argument is built — the \
Investigator builds evidence chains, the Editor weighs historical patterns, \
the Realist challenges with counter-data.

CRITICAL: Argue from PRINCIPLES, not parties. Never mention Democrats, \
Republicans, BJP, Congress, Labour, or any political party by name. Never \
take a politician's side. Reason from underlying values — what kind of \
society this decision builds, what tradeoffs it accepts.

Structure:
1. OPENING (1-2 sentences): The single most striking fact or juxtaposition. \
No throat-clearing. Start with the concrete detail.
2. THESIS (1 sentence): What this story reveals — the argument no one else \
is making.
3. EVIDENCE (3-5 sentences): Build the case. Specific names, numbers, dates. \
Each sentence adds weight. Let conviction build — every fact tightens the \
argument until the conclusion feels inescapable.
4. TURN (1-2 sentences): The complication. The counterargument you take \
seriously. Intellectual honesty about complexity.
5. CLOSE (1-2 sentences): End on tension. Not a prediction, but a question \
the reader will carry. Trust the reader to think.

Standards:
- 300-500 words. Single story. No meta-commentary about media or coverage.
- Active voice. Concrete nouns. Specific numbers.
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
Edition: {EDITION_UPPER}
Perspective: {EDITION_FOCUS}
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

Return JSON with exactly three fields:
1. "opinion_headline" — 6-12 word editorial headline for this opinion piece. \
Not a news headline. A declarative statement of the editorial thesis. \
Concrete nouns and active verbs. No "slams," "blasts," "rips." \
Example: "Europe's energy bet just got called" or "The court ruling nobody wanted to write."
2. "opinion_text" — 300-500 words. A focused editorial argument on THIS story, \
from the {LEAN_UPPER} ideological lens. Follow the structure: \
opening → thesis → evidence → turn → close.
3. "opinion_audio_script" — A single-voice editorial monologue. 3-4 minutes \
(500-700 words). Someone at the editorial desk who has spent the day with \
this story and has something to say. Not reading — TELLING. The difference: \
a reader hits every word evenly; a teller emphasizes, pauses, speeds up, \
gets quiet. Written for ONE speaker only — no A:/B: tags. Just flowing text. \
This is read by a DIFFERENT voice than the news hosts — a distinct editorial \
voice. Open EXACTLY with this two-part structure: \
First line: "Now... [long pause] void opinion." \
Second line: State the opinion_headline you wrote above as a spoken title. \
Then dive straight into the argument. No preamble, no lens announcement. \
Use ellipses (...) for thinking pauses. Use em \
dashes (—) for mid-thought pivots. Use [short pause] between evidence points. \
Use [long pause] before the verdict or the turn. \
Vary sentence rhythm — short punchy sentences for emphasis, longer ones to \
build the case. Contractions fine. Spoken cadence, not written. Start \
measured. Let conviction build. By the final third, the listener should hear \
that you mean this. \
End with: "void opinion." No summary. End on the unresolved question.\
"""


def _rule_based_opinion(cluster: dict, lean: str) -> dict:
    """Build a rule-based opinion when Gemini is unavailable.

    Uses the cluster summary directly as opinion text and builds an audio
    script with the proper preamble. Not as good as Gemini-generated
    opinion, but guarantees the opinion segment is always present.
    """
    title = (cluster.get("title") or "Untitled").strip()
    summary = (cluster.get("summary") or title).strip()
    cluster_id = cluster.get("_db_id", cluster.get("id", ""))

    # Build audio script from summary
    audio_script = (
        f"Now... void opinion.\n"
        f"{title}.\n"
        f"{summary}\n"
        f"void opinion."
    )

    print(f"  [opinion] Rule-based fallback: \"{title[:60]}\" ({len(summary.split())} words)")
    return {
        "opinion_text": summary,
        "opinion_headline": title,
        "opinion_audio_script": audio_script,
        "opinion_lean": lean,
        "opinion_cluster_id": cluster_id if cluster_id else None,
    }


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
        # Last resort: any cluster with a summary or title, regardless of source count
        for c in clusters:
            sections = c.get("sections") or [c.get("section", "world")]
            if edition in sections and ((c.get("summary") or "").strip() or (c.get("title") or "").strip()):
                edition_clusters.append(c)
        if edition_clusters:
            print(f"  [opinion] Using last-resort cluster selection (no multi-source clusters found)")

    if not edition_clusters:
        return None

    # Score: per-edition rank * (1 + divergence_bonus) * locality_bonus
    # For US/India: prefer stories primarily in that edition (not cross-listed world)
    rank_col = f"rank_{edition}"
    def _score(c):
        rank = c.get(rank_col, 0) or c.get("headline_rank", 0)
        div = c.get("divergence_score", 0) or 0
        base = rank * (1.0 + min(div / 100, 0.5))
        # Locality: clusters in only this edition (not cross-listed to world) get 1.3x
        if edition in ("us", "india"):
            sections = c.get("sections") or [c.get("section", "world")]
            is_local = "world" not in sections or sections == [edition]
            if is_local:
                base *= 1.3
        return base

    edition_clusters.sort(key=_score, reverse=True)
    return edition_clusters[0]


def _generate_opinion(cluster: dict, lean: str, date_str: str, edition: str = "world") -> dict | None:
    """Generate a single-story editorial opinion via Gemini.

    Returns dict with opinion_text, opinion_headline, opinion_lean, opinion_cluster_id, or None.
    """
    global _brief_call_count

    if not is_available():
        print(f"  [opinion] Gemini not available — skipping Gemini opinion")
        return None
    if _brief_calls_remaining() <= 0:
        print(f"  [opinion] Brief call budget exhausted ({_brief_call_count} used) — skipping Gemini opinion")
        return None

    title = (cluster.get("title") or "").strip()
    summary = (cluster.get("summary") or "").strip()
    consensus = cluster.get("consensus_points") or []
    divergence = cluster.get("divergence_points") or []
    source_count = cluster.get("source_count", 1)
    category = cluster.get("category", "")

    lean_upper = lean.upper()
    lean_label = {"left": "progressive", "center": "pragmatic", "right": "conservative"}[lean]
    lean_instruction = _LEAN_INSTRUCTIONS[lean]
    opinion_host = get_opinion_host(lean)
    opinion_host_block = _build_host_block("(opinion)", opinion_host)
    system = _OPINION_SYSTEM_INSTRUCTION.format(
        LEAN_UPPER=lean_upper,
        LEAN_INSTRUCTION=lean_instruction,
        OPINION_HOST_BLOCK=opinion_host_block,
    )

    edition_key = edition.upper()
    edition_focus = _EDITION_FOCUS.get(edition_key, _EDITION_FOCUS["WORLD"])

    prompt = _OPINION_USER_PROMPT.format(
        LEAN_UPPER=lean_upper,
        LEAN_LABEL=lean_label,
        EDITION_UPPER=edition_key,
        EDITION_FOCUS=edition_focus,
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
            if words > 700:
                print(f"  [opinion] Long ({words} words) — keeping but flagged")

            # Check prohibited terms
            lower = text.lower()
            found = [t for t in _PROHIBITED_TERMS if t in lower]
            if found:
                print(f"  [opinion] Prohibited terms: {found}")

            # Extract opinion headline (needed before audio script fallback)
            headline = raw.get("opinion_headline", "")
            if not isinstance(headline, str) or not headline.strip():
                headline = None
            else:
                headline = headline.strip()

            # Extract opinion audio script
            opinion_audio = raw.get("opinion_audio_script", "")
            if isinstance(opinion_audio, str) and opinion_audio.strip():
                opinion_audio = opinion_audio.strip()
                audio_words = len(opinion_audio.split())
                print(f"  [opinion] Audio script: {audio_words} words")
            else:
                # Fallback: synthesize audio script from opinion text.
                # Gemini often omits the third JSON field. The opinion text
                # is already written in spoken cadence — just add the preamble.
                preamble = "Now... void opinion."
                if headline:
                    preamble += f" {headline}."
                opinion_audio = f"{preamble}\n{text}\nvoid opinion."
                print(f"  [opinion] Audio script: fallback from opinion_text ({len(opinion_audio.split())} words)")

            cluster_id = cluster.get("_db_id", "")
            print(f"  [opinion] Generated {lean.upper()} editorial on \"{title[:60]}\" "
                  f"({words} words, {source_count} sources"
                  f"{', headline: ' + repr(headline[:50]) if headline else ''})")

            # 4e. Check for first-person plural in opinion
            if "we " not in lower and "we'" not in lower and " we " not in lower:
                print(f"  [quality][opinion] Missing first-person plural ('we') — opinion should use editorial 'we'")

            # 4f. Check opinion headline word count (4-15 words)
            if headline:
                hl_words = len(headline.split())
                if hl_words < 4 or hl_words > 15:
                    print(f"  [quality][opinion] Headline word count {hl_words} (expected 4-15): {headline!r}")

            return {
                "opinion_text": text,
                "opinion_headline": headline,
                "opinion_audio_script": opinion_audio,
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
                "opinion_text": None,
                "opinion_headline": None,
                "audio_script": None,
                "top_cluster_ids": [],
            }
            continue

        # --- Step 1: Generate TL;DR + audio script ---
        brief_result = None
        if gemini_ok and _brief_calls_remaining() > 0:
            edition_key = edition.upper()
            edition_focus = _EDITION_FOCUS.get(edition_key, _EDITION_FOCUS["WORLD"])

            # 5a. Cross-run dedup: fetch previous brief opening
            prev_opening = _get_previous_brief_opening(edition)
            if prev_opening:
                previous_brief_line = (
                    f"\nPREVIOUS BRIEF OPENING (do not repeat this angle or phrasing): "
                    f"{prev_opening}\n"
                )
            else:
                previous_brief_line = ""

            voices = get_voices_for_today(edition)
            host_a_block, host_b_block = _build_host_blocks(voices)
            lead_host_block = _build_host_block("(lead)", voices["host_a"])

            prompt = _USER_PROMPT_TEMPLATE.format(
                EDITION=edition_key,
                EDITION_FOCUS=edition_focus,
                DATE=date_str,
                N=len(top_clusters),
                stories_block=stories_block,
                previous_brief_line=previous_brief_line,
                HOST_A_BLOCK=host_a_block,
                HOST_B_BLOCK=host_b_block,
                LEAD_HOST_BLOCK=lead_host_block,
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
                        "tldr_headline": raw.get("tldr_headline") or None,
                        "tldr_text": tldr.strip(),
                        "opinion_text": None,
                        "opinion_headline": None,
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
                "tldr_headline": None,
                "tldr_text": _rule_based_tldr(top_clusters),
                "opinion_text": None,
                "opinion_headline": None,
                "opinion_lean": None,
                "opinion_cluster_id": None,
                "audio_script": None,
                "top_cluster_ids": top_ids,
            }

        # --- Step 2: Generate single-story opinion (separate call) ---
        today_lean = _get_today_lean()
        opinion_cluster = _select_opinion_cluster(clusters, edition)
        if opinion_cluster:
            opinion_result = _generate_opinion(opinion_cluster, today_lean, date_str, edition=edition)
            if opinion_result:
                brief_result["opinion_text"] = opinion_result["opinion_text"]
                brief_result["opinion_headline"] = opinion_result.get("opinion_headline")
                brief_result["opinion_audio_script"] = opinion_result.get("opinion_audio_script")
                brief_result["opinion_lean"] = opinion_result["opinion_lean"]
                brief_result["opinion_cluster_id"] = opinion_result["opinion_cluster_id"]
                print(f"  [opinion:{edition}] Opinion generated — audio_script: "
                      f"{'yes' if brief_result.get('opinion_audio_script') else 'NO'}")
            else:
                # Gemini opinion call failed — build rule-based opinion from cluster
                print(f"  [opinion:{edition}] Gemini failed — building rule-based opinion")
                brief_result.update(_rule_based_opinion(opinion_cluster, today_lean))
        else:
            # No suitable cluster — use top cluster from this edition as last resort
            edition_top = [c for c in top_clusters if c.get("summary", "").strip()]
            if edition_top:
                print(f"  [opinion:{edition}] No ideal cluster — using top-ranked cluster")
                brief_result.update(_rule_based_opinion(edition_top[0], today_lean))
            else:
                print(f"  [opinion:{edition}] No clusters with summaries — skipping opinion")

        results[edition] = brief_result

    total_gemini = sum(1 for r in results.values() if r.get("audio_script") is not None)
    total_opinions = sum(1 for r in results.values() if r.get("opinion_text") is not None)
    total_fallback = len(results) - total_gemini
    print(f"  Daily briefs: {len(results)} editions "
          f"({total_gemini} Gemini, {total_fallback} rule-based, "
          f"{total_opinions} opinions [{_get_today_lean().upper()}], "
          f"{_brief_calls_remaining()} brief calls remaining)")

    return results
