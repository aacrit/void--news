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
    _USER_PROMPT_TEMPLATE,
    _build_stories_block,
    _check_quality,
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
    prompt = _USER_PROMPT_TEMPLATE.format(
        EDITION=edition.upper(),
        DATE=date_str,
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
    script = result.get("audio_script")
    print(f"  TL;DR: {len(tldr.split(chr(10)))} lines")
    print(f"  Script: {'yes' if script else 'no'} ({len(script or '')} chars)")

    brief = {
        "tldr_text": tldr,
        "audio_script": script,
        "top_cluster_ids": [c.get("_db_id", "") for c in top_clusters if c.get("_db_id")],
        "generator": f"claude-{model}",
    }

    # 3. Synthesize audio
    if synthesize and script:
        print(f"\n[3/4] Synthesizing audio...")
        voices = get_voices_for_today(edition)
        audio_result = produce_audio(script, voices, edition)

        if audio_result:
            brief["audio_url"] = audio_result["audio_url"]
            brief["audio_duration_seconds"] = audio_result["duration_seconds"]
            brief["audio_file_size"] = audio_result["file_size"]
            brief["audio_voice"] = f"{voices['host_a']['id']}+{voices['host_b']['id']}"
        else:
            print("  Audio synthesis failed — brief will be text-only")
    else:
        print(f"\n[3/4] Skipping audio synthesis")

    # 4. Store in Supabase
    print(f"\n[4/4] Storing brief in Supabase...")
    brief_row = {
        "edition": edition,
        "tldr_text": brief["tldr_text"],
        "audio_script": brief.get("audio_script"),
        "top_cluster_ids": brief.get("top_cluster_ids", []),
    }
    if brief.get("audio_url"):
        brief_row["audio_url"] = brief["audio_url"]
        brief_row["audio_duration_seconds"] = brief.get("audio_duration_seconds")
        brief_row["audio_file_size"] = brief.get("audio_file_size")
        brief_row["audio_voice"] = brief.get("audio_voice")
        brief_row["audio_voice_label"] = "Two hosts"

    try:
        # Delete existing briefs for this edition, insert new
        supabase.table("daily_briefs").delete().eq("edition", edition).execute()
        supabase.table("daily_briefs").insert(brief_row).execute()
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
