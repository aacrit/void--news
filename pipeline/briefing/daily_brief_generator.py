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
import time
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
6-10 words. Declarative, present tense, concrete nouns. Not a question. Not a teaser. \
Must encompass the top 2-3 stories — a sweep headline, not a single-story slug. \
Stitch the day's themes into one line using commas, semicolons, or conjunctions.
Examples: "Tariffs Bite, Courts Push Back, Markets Shrug" / \
"Ceasefire Holds as Trade War Enters Week Two"

TL;DR INSTRUCTIONS (return as "tldr_text"):
Write 8-12 sentences as a flowing editorial paragraph. Target 180-240 words. \
CRITICAL: Put exactly one sentence per line, separated by \\n (literal newline). \
Each line = one sentence. Do NOT concatenate all sentences into one block. \
Write in the voice of today's lead host:
{LEAD_HOST_BLOCK}

STRUCTURE — Hook > Stakes > Sweep > Pattern:
1. HOOK (1-2 sentences): Open with a concrete, unexpected fact — a number, a name, \
an action. Never open with a gerund, a dependent clause, "Today" or "This week." \
Start mid-action.
2. STAKES (1-2 sentences): The second-order consequence. Show what changed.
3. SWEEP (4-6 sentences): Cover 3-4 more stories. One concrete fact each, then \
one sentence showing what shifted. Vary sentence length for rhythm.
4. CLOSE (1-2 sentences): The pattern the reader didn't see. End on tension.

ANTI-SLOP — ZERO TOLERANCE (output containing these is REJECTED and regenerated):
Never use: "amid," "raises questions," "remains to be seen," \
"only time will tell," "in a move that," "sends a clear signal," \
"significant," "notable," "crucially," "importantly," "unprecedented," \
"this isn't just," "this is not just," "it's not just," "here's the thing," \
"the question now is," "the reality is," "the bigger picture," \
"what makes this," "the takeaway," "the bottom line," "this goes beyond," \
"this matters because," "what's really happening," "this is about more than," \
"robust," "comprehensive," "pivotal," "nuanced," "landscape," "navigate," \
"navigating," "underscores," "multifaceted," "delve," "delves into."

RHYTHM: At least 15% of sentences must be 8 words or fewer. "That changed Tuesday." \
"Three days." "Eighteen months." Short sentences are the most powerful tool \
in editorial writing. Alternate long and short deliberately — never let three \
long sentences appear in a row without a short one.

---

AUDIO SCRIPT INSTRUCTIONS (return as "audio_script"):
Two senior journalists briefing each other as equals — not newsreaders, not a \
podcast. 4-5 minutes. HARD MINIMUM: 800 words. Target 800-1000 words. \
Scripts under 700 words are REJECTED and regenerated — count your words. \
Each line starts with "A:" or "B:". \
No other formatting. No [MARKERS]. No segment labels.

{HOST_A_BLOCK}

{HOST_B_BLOCK}

Both hosts are equals. Both report, both analyze, both add context. They build \
on each other through ADDITIONAL FACTS, not agreement or repetition.

STRUCTURE — Open > Headlines > 3 Stories > Close:
0. OPEN: A begins with exactly: "void logs in." [short pause] — this is the brand \
sign-on. Then immediately into headlines.
1. HEADLINES: A continues with a crisp rundown of the 3 stories coming up. One sentence \
each, punchy, present tense. Then B picks up the first story.
2. STORIES: Cover exactly 3 stories in depth. The biggest story gets the most time. \
For each: what happened, why it matters, and the structural context most coverage misses. \
A and B trade off — both contribute facts, both provide context.
3. CLOSE: One of them distills the day into a single observation — the thread connecting \
these stories, or the question they leave unanswered. Then the last speaker says: \
"void logs out." — with finality. Done.

PACING — Write for the ear (MANDATORY rhythm markers — minimum 8 total):
- Use [short pause] for breath beats between thoughts (minimum 4 per script).
- Use [long pause] before key revelations or topic shifts (minimum 2 per script).
- Use em dashes (—) for mid-thought pivots (minimum 2 per script).
- Short sentences for emphasis, then a longer one that unpacks.
- Vary sentence length dramatically. "The bond market noticed." / "Eighteen months."
- At least 15% of sentences must be 8 words or fewer.
- Contractions fine. Elevated register — informed professionals, not casual hangout.
- Numbers: write out small ones ("three"). Figures for big ones ("$1.4 trillion").
- Names, numbers, places, dates always. Not "officials say" — "the Treasury Secretary \
said Tuesday."
- Substantive reactions only: "But that contradicts the Q3 numbers." / \
"Which is what makes the timing interesting — the vote is Thursday."

BANNED — zero tolerance (output containing these is REJECTED and regenerated):
- Filler: "Mm.", "Right.", "Indeed.", "Good point.", "Absolutely.", "Interesting.", \
"Exactly.", "That's a fair point.", "Great question."
- Scaffolding: "This isn't just...", "Here's the thing...", "Here's what you need \
to know.", "Think of it this way.", "So here's what's happening.", "Let me explain.", \
"The bigger picture...", "What makes this...", "The reality is...", "Zoom out...", \
"The question now is...", "The takeaway...", "The bottom line...", "This goes beyond...", \
"This matters because...", "What's really happening...", "This is about more than..."
- Performance: "I mean...", "Look...", "Right?" (seeking agreement), "So basically..."
- Slop words (never use these adjectives): "significant", "notable", "crucially", \
"importantly", "unprecedented", "comprehensive", "pivotal", "nuanced", "robust", \
"landscape", "navigate", "navigating", "underscores", "multifaceted", "delve"

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


def _check_quality(result: dict, edition: str) -> tuple[bool, dict]:
    """Check brief output against quality gates.

    Returns (passed, report) where:
    - passed: True if hard gates pass (no prohibited terms). False = caller should retry.
    - report: Structured dict with all metrics for programmatic consumption.

    Also prints warnings to stdout for pipeline log readability.
    """
    import re

    report: dict = {"edition": edition, "warnings": [], "failures": [], "metrics": {}}

    tldr = result.get("tldr_text", "")
    lines = [l.strip() for l in tldr.split("\n") if l.strip()]
    words = len(tldr.split())
    report["metrics"]["tldr_lines"] = len(lines)
    report["metrics"]["tldr_words"] = words
    if len(lines) < 5 or len(lines) > 15:
        msg = f"TL;DR has {len(lines)} lines (expected 8-12)"
        report["warnings"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")
    if words < 120 or words > 300:
        msg = f"TL;DR has {words} words (expected 180-240)"
        report["warnings"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")

    headline = result.get("tldr_headline", "")
    hl_words = len(headline.split()) if headline and isinstance(headline, str) else 0
    report["metrics"]["headline_words"] = hl_words
    if not headline or not isinstance(headline, str) or not headline.strip():
        msg = "TL;DR headline missing"
        report["warnings"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")
    elif hl_words > 12:
        msg = f"TL;DR headline too long: {hl_words} words (expected 6-10)"
        report["warnings"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")

    script_raw = result.get("audio_script", "") or ""
    if isinstance(script_raw, list):
        script_raw = "\n".join(str(s) for s in script_raw)
    script = str(script_raw)

    all_text = f"{tldr} {script}".lower()

    # --- HARD GATE: Prohibited terms ---
    found = [t for t in _PROHIBITED_TERMS if t in all_text]
    report["metrics"]["prohibited_terms_found"] = found
    if found:
        report["failures"].append(f"Prohibited terms: {found}")
        print(f"  [quality][brief:{edition}] Prohibited terms found: {found}")

    # Validate script has actual dialogue (A:/B: speaker tags)
    speaker_lines = [l for l in script.splitlines() if l.strip().startswith(("A:", "B:"))]
    report["metrics"]["speaker_lines"] = len(speaker_lines)
    if len(speaker_lines) < 10:
        msg = f"Script has only {len(speaker_lines)} speaker lines (expected 10+)"
        report["warnings"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")

    # Audio script word count — hard floor triggers retry
    script_words = len(script.split()) if script.strip() else 0
    report["metrics"]["script_words"] = script_words
    if script.strip():
        if script_words < 700:
            msg = f"Audio script too short: {script_words} words (minimum 700)"
            report["warnings"].append(msg)
            found.append(f"short_script({script_words}w)")
            print(f"  [quality][brief:{edition}] {msg}")
        elif script_words > 1200:
            msg = f"Audio script too long: {script_words} words (expected 800-1200)"
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")

    # "void logs out" close check
    sign_off = False
    if script.strip():
        tail = script[-200:].lower()
        sign_off = "void logs out" in tail or "this was void news" in tail
        if not sign_off:
            msg = "Audio script missing 'void logs out' sign-off"
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")
    report["metrics"]["sign_off_present"] = sign_off

    # Monologue detection
    max_consecutive = 0
    if speaker_lines:
        max_consecutive = 1
        current_consecutive = 1
        current_speaker = None
        for line in speaker_lines:
            speaker = line.strip()[:2]
            if speaker == current_speaker:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_speaker = speaker
                current_consecutive = 1
        if max_consecutive > 5:
            msg = f"Monologue detected: {max_consecutive} consecutive lines by same speaker (max 5)"
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")
    report["metrics"]["monologue_max"] = max_consecutive

    # Banned filler scan
    _BANNED_FILLER = [
        "Mm.", "Right.", "Indeed.", "Good point.", "Absolutely.",
        "Interesting.", "Exactly.", "That's a fair point.", "Great question.",
    ]
    found_filler = []
    if script.strip():
        found_filler = [f for f in _BANNED_FILLER if f.lower() in script.lower()]
        if found_filler:
            msg = f"Banned filler in audio script: {found_filler}"
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")
    report["metrics"]["filler_found"] = found_filler

    # Pacing enforcement — sentence rhythm and pause markers
    short_pct = 0.0
    long_pct = 0.0
    pause_count = 0
    ellipsis_count = 0
    dash_count = 0
    total_markers = 0
    if script.strip():
        sentences = re.split(r'(?<=[.!?])\s+', script.strip())
        word_counts = []
        for s in sentences:
            cleaned = re.sub(r'^[AB]:\s*', '', s.strip())
            wc = len(cleaned.split())
            if wc > 0:
                word_counts.append(wc)

        if word_counts:
            short_sentences = sum(1 for w in word_counts if w <= 8)
            long_sentences = sum(1 for w in word_counts if w >= 20)
            total = len(word_counts)
            short_pct = round(short_sentences / total * 100, 1)
            long_pct = round(long_sentences / total * 100, 1)

            if short_pct < 15:
                msg = f"Pacing: only {short_pct:.0f}% short sentences (<=8 words, want >=15%)"
                report["warnings"].append(msg)
                print(f"  [quality][brief:{edition}] {msg}")
            if long_pct < 10:
                msg = f"Pacing: only {long_pct:.0f}% long sentences (>=20 words, want >=10%)"
                report["warnings"].append(msg)
                print(f"  [quality][brief:{edition}] {msg}")

        pause_count = script.lower().count("[short pause]") + script.lower().count("[long pause]")
        ellipsis_count = script.count("...")
        dash_count = script.count(" — ") + script.count("—")
        total_markers = pause_count + ellipsis_count + dash_count

        if total_markers < 5:
            msg = (f"Pacing: only {total_markers} rhythm markers "
                   f"(pauses: {pause_count}, ellipses: {ellipsis_count}, dashes: {dash_count})")
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")

    report["metrics"]["pacing_short_pct"] = short_pct
    report["metrics"]["pacing_long_pct"] = long_pct
    report["metrics"]["rhythm_markers"] = total_markers
    report["metrics"]["rhythm_pauses"] = pause_count
    report["metrics"]["rhythm_ellipses"] = ellipsis_count
    report["metrics"]["rhythm_dashes"] = dash_count

    passed = not bool(found)
    report["passed"] = passed
    return passed, report


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


def _fetch_last_successful_brief(edition: str) -> dict | None:
    """Fetch the most recent Gemini-generated brief for this edition.

    A brief is considered "successful" if it has a non-NULL tldr_headline,
    which only Gemini produces. Returns the full brief dict ready for use
    as a carry-forward fallback, or None if no previous successful brief exists.
    """
    try:
        from utils.supabase_client import supabase
        res = supabase.table("daily_briefs").select(
            "tldr_headline,tldr_text,opinion_text,opinion_headline,"
            "opinion_lean,opinion_cluster_id,audio_script,"
            "opinion_audio_script,top_cluster_ids"
        ).eq("edition", edition).not_.is_(
            "tldr_headline", "null"
        ).order("created_at", desc=True).limit(1).execute()

        if res.data and res.data[0].get("tldr_text"):
            p = res.data[0]
            print(f"  [brief:{edition}] Carrying forward last successful Gemini brief")
            return {
                "tldr_headline": p.get("tldr_headline"),
                "tldr_text": p["tldr_text"],
                "opinion_text": p.get("opinion_text"),
                "opinion_headline": p.get("opinion_headline"),
                "opinion_lean": p.get("opinion_lean"),
                "opinion_cluster_id": p.get("opinion_cluster_id"),
                "audio_script": p.get("audio_script"),
                "opinion_audio_script": p.get("opinion_audio_script"),
                "top_cluster_ids": p.get("top_cluster_ids", []),
            }
    except Exception as e:
        print(f"  [warn] Could not fetch previous successful brief for {edition}: {e}")
    return None


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

KILL SCAFFOLDING — ZERO TOLERANCE (output containing these is REJECTED):
Never announce what you are about to argue. These are ALL banned: \
"This isn't just...", "Here's the thing...", "The bigger picture...", \
"What makes this...", "The reality is...", "The question now is...", \
"This goes beyond...", "What's really happening here is...", \
"It's not just about...", "The takeaway is...", "The bottom line...", \
"This matters because...", "This is about more than...", "Let's be clear..."
Also banned — slop adjectives that assert instead of showing: \
"significant", "notable", "crucially", "importantly", "unprecedented", \
"pivotal", "nuanced", "comprehensive", "robust", "landscape", "navigate", \
"navigating", "underscores", "multifaceted", "delve", "delves into", \
"breaking", "historic", "controversial", "divisive."
Never reference outlet names, "coverage," "sources," or "reporting patterns." \
Synthesize the facts — do not cite where they came from. \
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
opening → thesis → evidence → turn → close. \
Never reference outlet names, "coverage," "sources," or "reporting." \
Synthesize the facts — do not cite where they came from.
3. "opinion_audio_script" — A single-voice editorial monologue. 3-4 minutes. \
HARD MINIMUM: 500 words. Target 500-700 words. Scripts under 450 words are \
REJECTED — count your words. Someone at the editorial desk who has spent the day with \
this story and has something to say. Not reading — TELLING. The difference: \
a reader hits every word evenly; a teller emphasizes, pauses, speeds up, \
gets quiet. Written for ONE speaker only — no A:/B: tags. Just flowing text. \
This is read by a DIFFERENT voice than the news hosts — a distinct editorial \
voice. Open EXACTLY with this two-part structure: \
First line: "void --opinion logs in." [short pause] \
Second line: State the opinion_headline you wrote above as a spoken title. \
Then dive straight into the argument. No preamble, no lens announcement. \
Use ellipses (...) for thinking pauses. Use em \
dashes (—) for mid-thought pivots. Use [short pause] between evidence points. \
Use [long pause] before the verdict or the turn. \
Vary sentence rhythm — short punchy sentences for emphasis, longer ones to \
build the case. Contractions fine. Spoken cadence, not written. Start \
measured. Let conviction build. By the final third, the listener should hear \
that you mean this. \
End with: "void --opinion logs out." No summary. End on the unresolved question.\
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
        f"void --opinion logs in.\n"
        f"{title}.\n"
        f"{summary}\n"
        f"void --opinion logs out."
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

    _OPINION_RETRY_SUFFIX = (
        "\n\nCRITICAL: Your previous attempt contained banned phrases. "
        "ZERO TOLERANCE — do NOT use ANY of these: "
        "'this isn't just', 'this is not just', 'it's not just', "
        "'the question now is', 'the reality is', 'the bigger picture', "
        "'what makes this', 'the takeaway', 'the bottom line', "
        "'this goes beyond', 'this matters because', 'let's be clear', "
        "'significant', 'notable', 'unprecedented', 'robust', 'comprehensive', "
        "'pivotal', 'nuanced', 'landscape', 'breaking', 'historic', "
        "'navigate', 'navigating', 'underscores', 'multifaceted', 'delve'. "
        "Start every sentence with a FACT or ARGUMENT. "
        "Never reference outlet names, coverage patterns, or media."
    )

    for attempt in range(2):
        _brief_call_count += 1
        attempt_prompt = prompt if attempt == 0 else prompt + _OPINION_RETRY_SUFFIX
        raw = generate_json(
            attempt_prompt,
            system_instruction=system,
            count_call=False,
            max_output_tokens=65536,
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

                # Check prohibited terms — retry if found and budget allows
                lower = text.lower()
                # Also check audio script for prohibited terms
                opinion_audio_raw = raw.get("opinion_audio_script", "") or ""
                all_opinion_text = f"{lower} {opinion_audio_raw.lower()}"
                found = [t for t in _PROHIBITED_TERMS if t in all_opinion_text]
                if found:
                    print(f"  [opinion] Prohibited terms: {found}")
                    if attempt == 0 and _brief_calls_remaining() > 0:
                        print(f"  [opinion] Retrying opinion generation (attempt 2)...")
                        continue
                    else:
                        print(f"  [opinion] Accepting with prohibited terms (no retry budget)")

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
                    if audio_words < 450 and attempt == 0 and _brief_calls_remaining() > 0:
                        print(f"  [opinion] Audio script too short: {audio_words} words (minimum 450) — retrying")
                        continue
                    print(f"  [opinion] Audio script: {audio_words} words")
                else:
                    # Fallback: synthesize audio script from opinion text.
                    # Gemini often omits the third JSON field. The opinion text
                    # is already written in spoken cadence — just add the preamble.
                    preamble = "void --opinion logs in."
                    if headline:
                        preamble += f" {headline}."
                    opinion_audio = f"{preamble}\n{text}\nvoid --opinion logs out."
                    print(f"  [opinion] Audio script: fallback from opinion_text ({len(opinion_audio.split())} words)")

                cluster_id = cluster.get("_db_id", "")
                print(f"  [opinion] Generated {lean.upper()} editorial on \"{title[:60]}\" "
                      f"({words} words, {source_count} sources"
                      f"{', headline: ' + repr(headline[:50]) if headline else ''})"
                      f"{' (retry)' if attempt > 0 else ''}")

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
    _stats = {"fresh": 0, "carried": 0, "rule_based": 0}

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
        gemini_failure_reason = None
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
            # Retry once if prohibited terms detected (costs 1 extra call)
            _RETRY_SUFFIX = (
                "\n\nCRITICAL REMINDER: Your previous attempt contained banned phrases. "
                "Do NOT use: 'this isn't just', 'the question now is', 'significant', "
                "'notable', 'the reality is', 'the bigger picture', 'what makes this', "
                "'unprecedented', 'crucially'. Start every sentence with a FACT or NAME."
            )
            for attempt in range(2):
                _brief_call_count += 1
                attempt_prompt = prompt if attempt == 0 else prompt + _RETRY_SUFFIX
                raw = generate_json(
                    attempt_prompt,
                    system_instruction=_SYSTEM_INSTRUCTION,
                    count_call=False,
                    max_output_tokens=65536,
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
                        passed, quality_report = _check_quality(raw, edition)
                        brief_result["quality_report"] = quality_report
                        if passed or attempt == 1:
                            if not passed and attempt == 1:
                                print(f"  [quality][brief:{edition}] Prohibited terms still present after retry — accepting")
                            print(f"  [brief:{edition}] Gemini OK — TL;DR {len(tldr.split(chr(10)))} lines, "
                                  f"script {'yes' if brief_result['audio_script'] else 'no'}"
                                  f"{' (retry)' if attempt > 0 else ''}")
                            break
                        else:
                            print(f"  [quality][brief:{edition}] Prohibited terms found — retrying (attempt {attempt + 2})")
                            brief_result = None  # Reset so retry replaces it
                    else:
                        gemini_failure_reason = "invalid_tldr"
                        print(f"  [brief:{edition}] Gemini returned invalid tldr_text (type={type(tldr).__name__}, len={len(str(tldr))})")
                        break
                else:
                    gemini_failure_reason = "api_error" if attempt == 0 else "api_error_retry"
                    print(f"  [brief:{edition}] Gemini call failed (attempt {attempt + 1}, "
                          f"raw={'None' if raw is None else type(raw).__name__})")
                    # On first API failure, wait and retry once before giving up.
                    # Gemini 429s and transient 500s often clear within 20 seconds.
                    if attempt == 0 and _brief_calls_remaining() > 0:
                        print(f"  [brief:{edition}] Waiting 20s before retry...")
                        time.sleep(20)
                        continue
                    break
        elif not gemini_ok:
            gemini_failure_reason = "unavailable"
            print(f"  [brief:{edition}] Gemini not available")
        else:
            gemini_failure_reason = "budget"
            print(f"  [brief:{edition}] Brief call cap reached ({_brief_call_count}/{_MAX_BRIEF_CALLS})")

        # Fallback: carry forward last successful Gemini brief instead of
        # generating a dry rule-based stub.  Only use rule-based as last resort.
        if brief_result is None:
            print(f"  [brief:{edition}] Gemini failed ({gemini_failure_reason}) — "
                  f"trying carry-forward from last successful brief")
            carried = _fetch_last_successful_brief(edition)
            if carried:
                brief_result = carried
                _stats["carried"] += 1
            else:
                print(f"  [brief:{edition}] No previous successful brief — using rule-based fallback")
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
                _stats["rule_based"] += 1
        else:
            _stats["fresh"] += 1

        # --- Step 2: Generate single-story opinion (separate call) ---
        # Skip if brief was carried forward and already has a good opinion.
        has_carried_opinion = bool(brief_result.get("opinion_text") and brief_result.get("opinion_headline"))
        today_lean = _get_today_lean()
        opinion_cluster = _select_opinion_cluster(clusters, edition)
        if opinion_cluster and not has_carried_opinion:
            opinion_result = _generate_opinion(opinion_cluster, today_lean, date_str, edition=edition)
            if opinion_result:
                brief_result["opinion_text"] = opinion_result["opinion_text"]
                brief_result["opinion_headline"] = opinion_result.get("opinion_headline")
                brief_result["opinion_audio_script"] = opinion_result.get("opinion_audio_script")
                brief_result["opinion_lean"] = opinion_result["opinion_lean"]
                brief_result["opinion_cluster_id"] = opinion_result["opinion_cluster_id"]
                print(f"  [opinion:{edition}] Opinion generated — audio_script: "
                      f"{'yes' if brief_result.get('opinion_audio_script') else 'NO'}")
            elif not brief_result.get("opinion_text"):
                # Gemini failed and no carried-forward opinion — rule-based last resort
                print(f"  [opinion:{edition}] Gemini failed, no carry-forward — building rule-based opinion")
                brief_result.update(_rule_based_opinion(opinion_cluster, today_lean))
            else:
                print(f"  [opinion:{edition}] Gemini failed — keeping carried-forward opinion")
        elif has_carried_opinion:
            print(f"  [opinion:{edition}] Using carried-forward opinion")
        else:
            # No suitable cluster — use top cluster from this edition as last resort
            if not brief_result.get("opinion_text"):
                edition_top = [c for c in top_clusters if c.get("summary", "").strip()]
                if edition_top:
                    print(f"  [opinion:{edition}] No ideal cluster — using top-ranked cluster")
                    brief_result.update(_rule_based_opinion(edition_top[0], today_lean))
                else:
                    print(f"  [opinion:{edition}] No clusters with summaries — skipping opinion")

        results[edition] = brief_result

    total_opinions = sum(1 for r in results.values() if r.get("opinion_text") is not None)
    print(f"  Daily briefs: {len(results)} editions "
          f"({_stats['fresh']} fresh Gemini, "
          f"{_stats['carried']} carried-forward, "
          f"{_stats['rule_based']} rule-based, "
          f"{total_opinions} opinions [{_get_today_lean().upper()}], "
          f"{_brief_calls_remaining()} brief calls remaining)")

    return results
