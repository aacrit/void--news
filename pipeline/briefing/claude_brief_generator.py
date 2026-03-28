"""
Claude CLI script generator for premium void --onair audio briefs.

Uses Claude Max (Sonnet/Opus) via CLI for higher-quality conversational
dialogue than Gemini Flash. Run manually 1x/day for premium scripts;
Gemini continues as automated 4x/day fallback.

Usage:
    python -m pipeline.briefing.claude_brief_generator
    python -m pipeline.briefing.claude_brief_generator --edition us
    python -m pipeline.briefing.claude_brief_generator --edition world --model opus

Requires: Claude CLI installed and authenticated (Claude Max subscription).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import supabase
from briefing.daily_brief_generator import (
    _SYSTEM_INSTRUCTION,
    _EDITION_FOCUS,
    _build_stories_block,
    _check_quality,
    _get_today_lean,
)
from briefing.audio_producer import produce_audio
from briefing.voice_rotation import get_voices_for_today

# Claude-specific craft — Vox-style explanatory energy
_CLAUDE_SYSTEM_ADDENDUM = """

ADDITIONAL CRAFT RULES (Claude-generated scripts):
- Think Vox "Today Explained" energy. You're curious about this material. Show it.
- Voice B is the audience proxy — asks "so what does that actually mean?",
  reframes headlines, explains WHY not just WHAT.
- Use concrete analogies to make abstract policy real.
- Pacing variation is critical. Short punchy sentences next to longer unpacking.
- Self-correction allowed: "roughly $1.4 trillion — depending on the estimate."
- Still banned (hollow filler): "Mm.", "Right.", "Indeed.", "Good point."
- Substantive reactions encouraged: "But that contradicts..." "So basically..."
- Direct address: "Here's what you need to know." "Think about it this way."
- The close: direct editorial take. What does today actually mean?
"""

# Claude-specific prompt — generates TL;DR, audio script, AND opinion in one call.
# The daily_brief_generator.py _USER_PROMPT_TEMPLATE explicitly excludes opinion
# (it generates opinion in a separate Gemini call). For Claude CLI, we combine
# everything into a single call to avoid spawning a second Claude process.
_CLAUDE_PROMPT_TEMPLATE = """\
Generate the daily brief for the {EDITION} edition of void --news.
Date: {DATE}

EDITION FOCUS: {EDITION_FOCUS}

OPINION LEAN: Today's editorial lens is {LEAN_UPPER} ({LEAN_LABEL}).

Below are today's top {N} stories for this edition, ranked by importance.

STORIES:
{stories_block}

Return JSON with exactly five fields:
1. "tldr_text" — 8-12 sentences as a flowing editorial paragraph, separated by \\n. \
   180-240 words. Hook → Stakes → Sweep → Pattern structure.
2. "audio_script" — two-voice explainer (A: and B: speaker tags, one per line). \
   4-5 minutes (800-1000 words). Structure: Headlines (3-sentence rundown) → \
   3 stories in depth → Close with "This was Void news." \
   No segment markers, no formatting. Just the dialogue.
3. "opinion_headline" — 6-12 word editorial headline. Not a news headline. \
   A declarative statement of the editorial thesis. Concrete nouns and active verbs. \
   Example: "Europe's energy bet just got called" or "The court ruling nobody wanted to write."
4. "opinion_text" — 80-120 words. 3-5 sentences. First-person plural editorial judgment \
   from "The Board." Genuinely opinionated. Where the TL;DR says what happened, this \
   says what we think about it. Use "we" voice. Pick the single most opinion-worthy \
   story from today's clusters. From the {LEAN_UPPER} lens.
5. "opinion_audio_script" — A single-voice editorial monologue for TTS. 500-700 words. \
   One speaker only — no A:/B: tags. Just flowing text. \
   Open EXACTLY with: \
   First line: "Now... void opinion." \
   Second line: State the opinion_headline as a spoken title. \
   Third line: "Today's {LEAN_LABEL} lens." \
   Then deliver the argument. Use ellipses (...) for thinking pauses. Use em dashes \
   for mid-thought pivots. End with: "void opinion." No summary.\
"""


def _fetch_clusters(edition: str, limit: int = 20) -> list[dict]:
    """Fetch current clusters from Supabase for the given edition."""
    res = supabase.table("story_clusters").select(
        "id,title,summary,category,section,sections,source_count,"
        "headline_rank,consensus_points,divergence_points"
    ).contains("sections", [edition]).order(
        "headline_rank", desc=True
    ).limit(limit).execute()

    if res.data:
        for c in res.data:
            c["_db_id"] = c["id"]
        return res.data
    return []


def _call_claude(prompt: str, system_prompt: str, model: str = "sonnet") -> dict | None:
    """Call Claude CLI non-interactively and parse JSON output."""
    cmd = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--system-prompt", system_prompt,
        "--no-session-persistence",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(f"  [claude] CLI returned exit code {result.returncode}")
            if result.stderr:
                print(f"  [claude] stderr: {result.stderr[:500]}")
            return None

        # Parse Claude CLI JSON output
        output = json.loads(result.stdout)
        text = output.get("result", "")

        # Claude returns the JSON as text inside "result" — parse it
        # Try to find JSON block in the response
        json_match = None
        # Look for ```json ... ``` blocks first
        import re
        code_block = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if code_block:
            json_match = code_block.group(1)
        else:
            # Try parsing the whole response as JSON
            brace_start = text.find("{")
            brace_end = text.rfind("}")
            if brace_start >= 0 and brace_end > brace_start:
                json_match = text[brace_start:brace_end + 1]

        if json_match:
            parsed = json.loads(json_match)
            if "tldr_text" in parsed:
                return parsed

        print(f"  [claude] Could not extract valid JSON from response ({len(text)} chars)")
        return None

    except subprocess.TimeoutExpired:
        print("  [claude] CLI timed out after 120s")
        return None
    except FileNotFoundError:
        print("  [claude] CLI not found — is `claude` installed and in PATH?")
        return None
    except json.JSONDecodeError as e:
        print(f"  [claude] JSON parse error: {e}")
        return None
    except Exception as e:
        print(f"  [claude] Unexpected error: {e}")
        return None


def generate_claude_brief(
    edition: str = "world",
    model: str = "sonnet",
    synthesize: bool = True,
) -> dict | None:
    """Generate a premium daily brief using Claude CLI.

    Args:
        edition: world/us/india
        model: Claude model (sonnet or opus)
        synthesize: If True, also generate and upload audio

    Returns brief dict with tldr_text, audio_script, and optionally audio_url.
    """
    print(f"\n{'='*60}")
    print(f"  void --onair | Claude {model} | {edition} edition")
    print(f"{'='*60}\n")

    # 1. Fetch clusters
    print("[1/4] Fetching clusters from Supabase...")
    clusters = _fetch_clusters(edition)
    if not clusters:
        print(f"  No clusters found for {edition}")
        return None

    top_clusters, stories_block = _build_stories_block(clusters, edition)
    print(f"  {len(top_clusters)} stories loaded")

    # 2. Generate script via Claude CLI
    print(f"\n[2/4] Generating script via Claude {model}...")
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")
    today_lean = _get_today_lean()
    lean_label = {"left": "progressive", "center": "pragmatic", "right": "conservative"}[today_lean]
    edition_key = edition.upper()
    edition_focus = _EDITION_FOCUS.get(edition_key, _EDITION_FOCUS["WORLD"])
    prompt = _CLAUDE_PROMPT_TEMPLATE.format(
        EDITION=edition_key,
        EDITION_FOCUS=edition_focus,
        DATE=date_str,
        LEAN_UPPER=today_lean.upper(),
        LEAN_LABEL=lean_label,
        N=len(top_clusters),
        stories_block=stories_block,
    )

    system_prompt = _SYSTEM_INSTRUCTION + _CLAUDE_SYSTEM_ADDENDUM
    result = _call_claude(prompt, system_prompt, model=model)

    if not result:
        print("  Claude generation failed")
        return None

    _check_quality(result, edition)
    tldr = result.get("tldr_text", "")
    opinion = result.get("opinion_text", "")
    script = result.get("audio_script")
    print(f"  TL;DR: {len(tldr.split(chr(10)))} lines")
    print(f"  Opinion: {'yes' if opinion else 'no'}")
    print(f"  Script: {'yes' if script else 'no'} ({len(script or '')} chars)")

    opinion_headline = result.get("opinion_headline", "")
    opinion_audio = result.get("opinion_audio_script", "")

    brief = {
        "tldr_text": tldr,
        "opinion_text": opinion if opinion else None,
        "opinion_headline": opinion_headline if opinion_headline else None,
        "opinion_audio_script": opinion_audio if opinion_audio else None,
        "opinion_lean": today_lean,
        "audio_script": script,
        "top_cluster_ids": [c.get("_db_id", "") for c in top_clusters if c.get("_db_id")],
        "generator": f"claude-{model}",
    }

    # 3. Synthesize audio
    if synthesize and script:
        print(f"\n[3/4] Synthesizing audio...")
        voices = get_voices_for_today(edition)
        audio_result = produce_audio(
            script, voices, edition,
            opinion_audio_script=brief.get("opinion_audio_script"),
        )

        if audio_result:
            brief["audio_url"] = audio_result["audio_url"]
            brief["audio_duration_seconds"] = audio_result["duration_seconds"]
            brief["audio_file_size"] = audio_result["file_size"]
            has_opinion = bool(brief.get("opinion_audio_script"))
            brief["audio_voice"] = f"{voices['host_a']['id']}+{voices['host_b']['id']}" + (
                f"+{voices['opinion']['id']}" if has_opinion else ""
            )
        else:
            print("  Audio synthesis failed — brief will be text-only")
    else:
        print(f"\n[3/4] Skipping audio synthesis")

    # 4. Store in Supabase
    print(f"\n[4/4] Storing brief in Supabase...")
    brief_row = {
        "edition": edition,
        "tldr_text": brief["tldr_text"],
        "opinion_text": brief.get("opinion_text"),
        "opinion_headline": brief.get("opinion_headline"),
        "opinion_lean": brief.get("opinion_lean"),
        "audio_script": brief.get("audio_script"),
        "top_cluster_ids": brief.get("top_cluster_ids", []),
    }
    if brief.get("audio_url"):
        brief_row["audio_url"] = brief["audio_url"]
        brief_row["audio_duration_seconds"] = brief.get("audio_duration_seconds")
        brief_row["audio_file_size"] = brief.get("audio_file_size")
        brief_row["audio_voice"] = brief.get("audio_voice")
        brief_row["audio_voice_label"] = "Three voices" if brief.get("opinion_audio_script") else "Two hosts"

    try:
        # Upsert: insert new brief, then delete older ones for this edition.
        # Order matters — insert first so the frontend always has a record.
        supabase.table("daily_briefs").insert(brief_row).execute()
        # Clean up older briefs for this edition (keep only the latest)
        latest = supabase.table("daily_briefs").select("id").eq(
            "edition", edition
        ).order("created_at", desc=True).limit(1).execute()
        if latest.data:
            keep_id = latest.data[0]["id"]
            supabase.table("daily_briefs").delete().eq(
                "edition", edition
            ).neq("id", keep_id).execute()
        print(f"  Stored successfully")
    except Exception as e:
        print(f"  DB update failed: {e}")

    print(f"\n{'='*60}")
    print(f"  Done. Generator: Claude {model}")
    if brief.get("audio_url"):
        print(f"  Audio: {brief['audio_duration_seconds']}s, "
              f"{brief.get('audio_file_size', 0) / 1024:.0f} KB")
    print(f"{'='*60}\n")

    return brief


def main():
    parser = argparse.ArgumentParser(
        description="Generate premium void --onair brief via Claude CLI"
    )
    parser.add_argument("--edition", default="world", help="Edition: world/us/india")
    parser.add_argument("--model", default="sonnet", help="Claude model: sonnet or opus")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio synthesis")
    args = parser.parse_args()

    generate_claude_brief(
        edition=args.edition,
        model=args.model,
        synthesize=not args.no_audio,
    )


if __name__ == "__main__":
    main()
