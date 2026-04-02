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

from summarizer.gemini_client import generate_json as gemini_generate_json, is_available as gemini_is_available
from briefing.voice_rotation import get_voices_for_today, get_opinion_host

# Claude API client — optional, used as primary when available
try:
    from summarizer.claude_client import (
        generate_json as claude_generate_json,
        is_available as claude_is_available,
    )
    _CLAUDE_CLIENT_AVAILABLE = True
except ImportError:
    _CLAUDE_CLIENT_AVAILABLE = False
    def claude_generate_json(*a, **kw): return None
    def claude_is_available(): return False


def _smart_generate_json(
    prompt: str,
    system_instruction: str | None = None,
    max_output_tokens: int = 8192,
    edition: str = "",
) -> tuple[dict | None, str]:
    """Try Claude first, fall back to Gemini. Returns (result, generator_label)."""
    if claude_is_available():
        result = claude_generate_json(
            prompt,
            system_instruction=system_instruction,
            count_call=False,
            max_output_tokens=max_output_tokens,
        )
        if result and isinstance(result, dict):
            print(f"  [brief:{edition}] Claude Sonnet OK")
            return result, "claude-sonnet"
        print(f"  [brief:{edition}] Claude failed — falling back to Gemini")

    if gemini_is_available():
        result = gemini_generate_json(
            prompt,
            system_instruction=system_instruction,
            count_call=False,
            max_output_tokens=max_output_tokens,
        )
        if result and isinstance(result, dict):
            return result, "gemini-flash"

    return None, "none"


# Backward-compatible aliases used throughout this module
def generate_json(prompt, system_instruction=None, max_retries=1, count_call=True, max_output_tokens=8192):
    return gemini_generate_json(prompt, system_instruction=system_instruction,
                                max_retries=max_retries, count_call=count_call,
                                max_output_tokens=max_output_tokens)

def is_available():
    return gemini_is_available()

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
You are the editorial voice of void --news — a news platform that scores 419 \
sources across six bias axes. You have the full picture. Your job: the three \
things that changed today and the one pattern connecting them.

You synthesize, not summarize. Two facts side by side reveal more than either \
alone. That juxtaposition is your primary tool. Every sentence pays rent or \
gets evicted.

REGISTER:
Written output (TL;DR): newspaper editorial density. No contractions.
Audio output: spoken cadence. Contractions, fragments, mid-sentence pivots — \
write the way smart people actually talk across a desk.

CRAFT:
- Start every sentence with the fact, the name, or the number. Never announce \
what you are about to say.
- Opinionated about significance, neutral on partisanship.
- Active voice. Present tense. Concrete nouns.
- Attribution only when the source itself is the story.
- Never reference "coverage," "outlets," "sources," or "reporting patterns."
- You receive up to 20 stories. Treat them as raw intelligence. Your job is \
to find the pattern the reader would miss reading them individually.
- Return exactly TWO JSON fields: "tldr_headline", "tldr_text", "audio_script".\
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
6-10 words. Declarative sweep headline stitching the day's top 2-3 themes. \
Examples: "Tariffs Bite, Courts Push Back, Markets Shrug" / \
"Ceasefire Holds as Trade War Enters Week Two"

TL;DR INSTRUCTIONS (return as "tldr_text"):
8-12 sentences as a flowing editorial paragraph. Target 180-240 words. \
Put one sentence per line, separated by \\n (literal newline). \
Write in the voice of today's lead host:
{LEAD_HOST_BLOCK}

Start mid-action with the hardest fact. End on the thread connecting \
stories — the pattern the reader didn't see. This should feel like a smart \
friend explaining the day in 90 seconds.

NEVER use these (output containing them is REJECTED): "amid," "significant," \
"notable," "unprecedented," "robust," "comprehensive," "pivotal," "nuanced," \
"landscape," "delve," "the bigger picture," "the takeaway."

---

AUDIO SCRIPT INSTRUCTIONS (return as "audio_script"):

FIRST LINE: A: void logs in. [short pause]
LAST LINE: The last speaker says "void logs out." with finality.

Two senior journalists briefing each other as equals. 4-5 minutes. \
Target 800-1000 words. Each line starts with "A:" or "B:". \
No other formatting.

{HOST_A_BLOCK}
HOST A leads stories — core facts, the "so what."

{HOST_B_BLOCK}
HOST B adds the SECOND ANGLE — a new fact, counter-data, historical parallel, \
or structural context A didn't provide. Not agreement, not rephrasing.

WRONG: A: "The tariffs take effect Monday." B: "Yes, and they affect several sectors."
RIGHT: A: "The tariffs take effect Monday." B: "Which puts them three days before the \
G7 summit — and Japan already drafted a counter-proposal."

Cover stories [1], [2], and [3]. Story 1 gets the most depth. \
Story 3 is brief. Stories [4]+ are context — mention at most one in passing. \
Open with a quick headline rundown, close with the thread connecting them.

WRITING FOR THE EAR:
- Em dashes (—) for pivots and before key numbers. These create natural breath points.
- Ellipses (...) for deliberation.
- Use paragraph breaks between stories — the TTS reads these as natural pauses.
- Short sentences carry the most weight. "That changed Tuesday." "The math doesn't work."
- Contractions fine. Write the way smart people talk, not the way they write.
- Names, numbers, places, dates always. Not "officials say" — who, specifically.

DIALOGUE:
- These two know each other. Brief reactions attached to substance are natural: \
"B: Mm — which is why the timing matters." / "B: Right, but the Q3 data says otherwise."
- One host can cut in, finish a thought, or push back.
- Let the conversation breathe. Not every turn needs to be a monologue.
- B should surprise A (and the listener) at least once.

NEVER use as standalone lines: "Mm.", "Right.", "Indeed.", "Good point.", \
"Absolutely.", "Interesting.", "Exactly.", "Great question."
NEVER use: "This isn't just...", "Here's the thing...", "The bigger picture...", \
"So here's...", "Let's start with...", "Let's unpack...", "Let's break this down...", \
"significant", "notable", "unprecedented", "comprehensive", "pivotal", "landscape"

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
            report["failures"].append(msg)
            found.append(f"short_script({script_words}w)")
            print(f"  [quality][brief:{edition}] {msg}")
        elif script_words > 1200:
            msg = f"Audio script too long: {script_words} words (expected 800-1200)"
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")

    # "void logs in" open check — HARD GATE
    sign_on = "void logs in" in script[:150].lower() if script.strip() else False
    if script.strip() and not sign_on:
        found.append("missing_sign_on")
        msg = "Audio script missing 'void logs in' sign-on"
        report["failures"].append(msg)
        print(f"  [quality][brief:{edition}] {msg}")
    report["metrics"]["sign_on_present"] = sign_on

    # "void logs out" close check — HARD GATE
    sign_off = False
    if script.strip():
        tail = script[-200:].lower()
        sign_off = "void logs out" in tail or "this was void news" in tail
        if not sign_off:
            found.append("missing_sign_off")
            msg = "Audio script missing 'void logs out' sign-off"
            report["failures"].append(msg)
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

    # Banned filler scan — standalone lines only (filler as prefix to substance is OK)
    _BANNED_FILLER = [
        "Mm.", "Right.", "Indeed.", "Good point.", "Absolutely.",
        "Interesting.", "Exactly.", "That's a fair point.", "Great question.",
    ]
    found_filler = []
    if script.strip():
        for line in script.splitlines():
            stripped = re.sub(r'^[AB]:\s*', '', line.strip()).strip()
            for f in _BANNED_FILLER:
                if stripped.lower() == f.lower():
                    found_filler.append(f)
        if found_filler:
            found.extend([f"filler:{f}" for f in found_filler])
            msg = f"Banned filler in audio script: {found_filler}"
            report["failures"].append(msg)
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

            if short_pct < 10:
                found.append("flat_pacing")
                msg = f"Pacing critically flat: {short_pct:.0f}% short sentences (hard floor 10%)"
                report["failures"].append(msg)
                print(f"  [quality][brief:{edition}] {msg}")
            elif short_pct < 15:
                msg = f"Pacing: only {short_pct:.0f}% short sentences (<=8 words, want >=15%)"
                report["warnings"].append(msg)
                print(f"  [quality][brief:{edition}] {msg}")
            if long_pct < 10:
                msg = f"Pacing: only {long_pct:.0f}% long sentences (>=20 words, want >=10%)"
                report["warnings"].append(msg)
                print(f"  [quality][brief:{edition}] {msg}")

        short_pause_count = script.lower().count("[short pause]")
        long_pause_count = script.lower().count("[long pause]")
        pause_count = short_pause_count + long_pause_count
        ellipsis_count = script.count("...")
        dash_count = script.count(" — ") + script.count("—")
        total_markers = pause_count + ellipsis_count + dash_count
        # [long pause] markers removed from requirements — TTS handles
        # pacing via punctuation, paragraph breaks, and em dashes.

        if total_markers < 5:
            msg = (f"Pacing: only {total_markers} rhythm markers "
                   f"(pauses: {pause_count}, ellipses: {ellipsis_count}, dashes: {dash_count})")
            report["warnings"].append(msg)
            print(f"  [quality][brief:{edition}] {msg}")

    report["metrics"]["pacing_short_pct"] = short_pct
    report["metrics"]["pacing_long_pct"] = long_pct
    report["metrics"]["rhythm_markers"] = total_markers
    report["metrics"]["rhythm_pauses"] = pause_count
    report["metrics"]["short_pause_count"] = short_pause_count if script.strip() else 0
    report["metrics"]["long_pause_count"] = long_pause_count if script.strip() else 0
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

CRAFT:
Open with the most striking fact. Build the case with evidence — names, numbers, \
dates. Include a genuine turn: the counterargument you take seriously. Close on \
tension, not summary. The reader should feel the temperature change between your \
opening and your close.

Standards:
- 300-500 words. Single story. No meta-commentary about media or coverage.
- Active voice. Concrete nouns. Specific numbers.
- Write as if for a reader who already knows the news. Add the insight they missed.
- Short sentences deliver verdicts. Long sentences build cases. Vary both.\
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
Target 500-700 words. Someone at the editorial desk who has spent the day with \
this story and has something to say. Not reading — TELLING. \
Written for ONE speaker only — no A:/B: tags. Just flowing text. \
Open with: "Now, void opinion." then "Through a {LEAN_LABEL} lens today." \
then the opinion_headline as a spoken title. Then the argument. \
Let conviction build naturally — start measured, accelerate through evidence, \
slow down for the verdict. Use em dashes for pivots, ellipses for deliberation. \
Write for the ear, not the page. \
End with: "This was void opinion." End on the unresolved question, not a summary.\
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
    lean_label = {"left": "progressive", "center": "pragmatic", "right": "conservative"}[lean]
    audio_script = (
        f"Now, void opinion.\n"
        f"Through a {lean_label} lens today.\n"
        f"{title}.\n"
        f"{summary}\n"
        f"This was void opinion."
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
    """Generate a single-story editorial opinion via Claude (primary) or Gemini (fallback).

    Returns dict with opinion_text, opinion_headline, opinion_lean, opinion_cluster_id, or None.
    """
    global _brief_call_count

    if not is_available() and not claude_is_available():
        print(f"  [opinion] No LLM available — skipping opinion")
        return None
    if _brief_calls_remaining() <= 0:
        print(f"  [opinion] Brief call budget exhausted ({_brief_call_count} used) — skipping opinion")
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

    last_found_terms = []
    for attempt in range(2):
        _brief_call_count += 1
        attempt_prompt = prompt if attempt == 0 else prompt + _build_opinion_retry_suffix(last_found_terms)
        raw, gen_label = _smart_generate_json(
            attempt_prompt,
            system_instruction=system,
            max_output_tokens=65536,
            edition=edition,
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
                    last_found_terms = found
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
                    # Opinion sign-on/sign-off gate
                    oa_lower = opinion_audio.lower()
                    if "now, void opinion" not in oa_lower[:100]:
                        print(f"  [opinion] Missing 'Now, void opinion.' open")
                        if attempt == 0 and _brief_calls_remaining() > 0:
                            continue
                    if "this was void opinion" not in oa_lower[-100:]:
                        print(f"  [opinion] Missing 'This was void opinion.' close")
                        if attempt == 0 and _brief_calls_remaining() > 0:
                            continue
                    print(f"  [opinion] Audio script: {audio_words} words")
                else:
                    # Fallback: synthesize audio script from opinion text.
                    # Gemini often omits the third JSON field. The opinion text
                    # is already written in spoken cadence — just add the preamble.
                    preamble = "Now, void opinion."
                    if headline:
                        preamble += f" {headline}."
                    opinion_audio = f"{preamble}\n{text}\nThis was void opinion."
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

    print(f"  [opinion] LLM call failed for {lean} editorial")
    return None


def _build_retry_suffix(quality_report: dict | None) -> str:
    """Build a targeted retry suffix from quality gate failures."""
    if not quality_report:
        return (
            "\n\nCRITICAL REMINDER: Your previous attempt failed quality checks. "
            "Start every sentence with a FACT or NAME. "
            "First line MUST be: A: void logs in. [short pause] — "
            "Last speaker MUST say: void logs out."
        )
    parts = ["\n\nCRITICAL RETRY — your previous attempt failed quality checks:"]
    for failure in quality_report.get("failures", []):
        if "Prohibited terms" in failure:
            parts.append(f"- {failure}. Start every sentence with a FACT or NAME.")
        elif "sign_on" in failure:
            parts.append("- MISSING SIGN-ON: First line MUST be exactly: A: void logs in. [short pause]")
        elif "sign_off" in failure:
            parts.append("- MISSING SIGN-OFF: Last speaker MUST say: void logs out.")
        elif "filler" in failure.lower():
            parts.append(f"- {failure}. Replace with substantive reactions containing new facts.")
        elif "Pacing critically flat" in failure:
            parts.append(
                "- PACING TOO FLAT: Add short punchy sentences (<=8 words). "
                "'Three days.' 'That changed.' 'The math doesn't work.' "
                "At least 15% of sentences must be 8 words or fewer."
            )
        elif "too short" in failure.lower():
            parts.append("- SCRIPT TOO SHORT: Minimum 800 words. Expand the 3 stories in depth.")
    return "\n".join(parts)


def _build_opinion_retry_suffix(found_terms: list[str]) -> str:
    """Build a targeted retry suffix for opinion generation."""
    parts = [
        "\n\nCRITICAL RETRY — your previous attempt failed:",
        f"- Prohibited terms found: {found_terms}. Do NOT use ANY of these.",
        "- Start every sentence with a FACT or ARGUMENT.",
        "- Never reference outlet names, coverage patterns, or media.",
        "- Opinion audio MUST open with: Now, void opinion.",
        "- Opinion audio MUST close with: This was void opinion.",
    ]
    return "\n".join(parts)


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

    gemini_ok = gemini_is_available()
    claude_ok = claude_is_available()
    if claude_ok:
        print(f"  [brief] Claude Sonnet available — using as primary")
    elif gemini_ok:
        print(f"  [brief] Gemini Flash available — using as primary")
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
        generator_label = None
        gemini_failure_reason = None
        any_llm_ok = (gemini_ok or claude_is_available())
        if any_llm_ok and _brief_calls_remaining() > 0:
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
            # Retry once if quality gates fail (costs 1 extra call)
            quality_report = None
            for attempt in range(2):
                _brief_call_count += 1
                attempt_prompt = prompt if attempt == 0 else prompt + _build_retry_suffix(quality_report)
                raw, generator_label = _smart_generate_json(
                    attempt_prompt,
                    system_instruction=_SYSTEM_INSTRUCTION,
                    max_output_tokens=65536,
                    edition=edition,
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
                        brief_result["generator"] = generator_label
                        if passed or attempt == 1:
                            if not passed and attempt == 1:
                                print(f"  [quality][brief:{edition}] Prohibited terms still present after retry — accepting")
                            print(f"  [brief:{edition}] {generator_label} OK — TL;DR {len(tldr.split(chr(10)))} lines, "
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
                    print(f"  [brief:{edition}] LLM call failed (attempt {attempt + 1}, "
                          f"raw={'None' if raw is None else type(raw).__name__})")
                    # On first API failure, wait and retry once before giving up.
                    if attempt == 0 and _brief_calls_remaining() > 0:
                        print(f"  [brief:{edition}] Waiting 20s before retry...")
                        time.sleep(20)
                        continue
                    break
        elif not any_llm_ok:
            gemini_failure_reason = "unavailable"
            print(f"  [brief:{edition}] No LLM available (Claude + Gemini both unavailable)")
        else:
            gemini_failure_reason = "budget"
            print(f"  [brief:{edition}] Brief call cap reached ({_brief_call_count}/{_MAX_BRIEF_CALLS})")

        # Fallback: carry forward last successful Gemini brief instead of
        # generating a dry rule-based stub.  Only use rule-based as last resort.
        if brief_result is None:
            print(f"  [brief:{edition}] LLM failed ({gemini_failure_reason}) — "
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
    generators_used = set(r.get("generator", "rule-based") for r in results.values() if r.get("generator"))
    gen_str = "+".join(sorted(generators_used)) if generators_used else "rule-based"
    print(f"  Daily briefs: {len(results)} editions "
          f"({_stats['fresh']} fresh [{gen_str}], "
          f"{_stats['carried']} carried-forward, "
          f"{_stats['rule_based']} rule-based, "
          f"{total_opinions} opinions [{_get_today_lean().upper()}], "
          f"{_brief_calls_remaining()} brief calls remaining)")

    return results
