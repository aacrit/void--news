"""
A/B quality comparison: Claude Sonnet vs Gemini Flash for daily brief generation.

Generates briefs with both models using the same input stories, then compares
quality metrics side-by-side. CEO directive: only switch to Claude if quality
measurably improves.

Usage:
    python pipeline/briefing/compare_generators.py
    python pipeline/briefing/compare_generators.py --edition us
    python pipeline/briefing/compare_generators.py --fixtures  # use test fixtures

Output: side-by-side quality comparison with diff highlighting.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from briefing.daily_brief_generator import (
    _SYSTEM_INSTRUCTION,
    _OPINION_SYSTEM_INSTRUCTION,
    _USER_PROMPT_TEMPLATE,
    _OPINION_USER_PROMPT,
    _EDITION_FOCUS,
    _LEAN_INSTRUCTIONS,
    _build_host_blocks,
    _build_host_block,
    _build_stories_block,
    _check_quality,
    _get_today_lean,
    _get_previous_brief_opening,
    _select_opinion_cluster,
)
from briefing.voice_rotation import get_voices_for_today, get_opinion_host

# Import both clients directly
from summarizer.gemini_client import (
    generate_json as gemini_generate,
    is_available as gemini_ok,
)

try:
    from summarizer.claude_client import (
        generate_json as claude_generate,
        is_available as claude_ok,
    )
except ImportError:
    def claude_generate(*a, **kw): return None
    def claude_ok(): return False

_FIXTURES_PATH = Path(__file__).parent / "test_clusters.json"


def _fetch_clusters(edition: str) -> list[dict]:
    """Fetch clusters from live DB."""
    from utils.supabase_client import supabase
    res = supabase.table("story_clusters").select(
        "id,title,summary,category,section,sections,source_count,"
        "headline_rank,consensus_points,divergence_points,divergence_score"
    ).contains("sections", [edition]).order(
        "headline_rank", desc=True
    ).limit(20).execute()
    if res.data:
        for c in res.data:
            c["_db_id"] = c["id"]
        return res.data
    return []


def _build_prompt(edition: str, clusters: list[dict]) -> tuple[str, str]:
    """Build the TL;DR + audio prompt and return (prompt, system)."""
    top_clusters, stories_block = _build_stories_block(clusters, edition)
    edition_key = edition.upper()
    edition_focus = _EDITION_FOCUS.get(edition_key, _EDITION_FOCUS["WORLD"])
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    prev_opening = ""
    try:
        prev_opening = _get_previous_brief_opening(edition) or ""
    except Exception:
        pass
    previous_brief_line = (
        f"\nPREVIOUS BRIEF OPENING (do not repeat this angle or phrasing): {prev_opening}\n"
        if prev_opening else ""
    )

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
    return prompt, _SYSTEM_INSTRUCTION


def _build_opinion_prompt(cluster: dict, lean: str, edition: str) -> tuple[str, str]:
    """Build the opinion prompt and return (prompt, system)."""
    title = (cluster.get("title") or "").strip()
    summary = (cluster.get("summary") or "").strip()
    consensus = cluster.get("consensus_points") or []
    divergence = cluster.get("divergence_points") or []
    source_count = cluster.get("source_count", 1)
    category = cluster.get("category", "")
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

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
    return prompt, system


def _score_naturalness(script: str) -> dict:
    """Score dialogue naturalness heuristics beyond standard quality gates."""
    import re
    lines = [l.strip() for l in script.splitlines() if l.strip()]
    speaker_lines = [l for l in lines if l.startswith(("A:", "B:"))]

    # Count speaker switches (more = more conversational)
    switches = 0
    prev = None
    for line in speaker_lines:
        sp = line[:2]
        if prev and sp != prev:
            switches += 1
        prev = sp

    # Average words per turn (shorter = more natural)
    turn_lengths = [len(re.sub(r'^[AB]:\s*', '', l).split()) for l in speaker_lines]
    avg_turn = sum(turn_lengths) / max(len(turn_lengths), 1)

    # Count em dashes (indicates mid-thought pivots)
    dashes = script.count("—")

    # Count questions (hosts asking each other)
    questions = sum(1 for l in speaker_lines if l.rstrip().endswith("?"))

    # Count filler-as-prefix (natural acknowledgments)
    natural_acks = sum(1 for l in speaker_lines
                       if re.match(r'^[AB]:\s*(Mm|Right|Yeah)\s*[—,]', l))

    return {
        "speaker_switches": switches,
        "avg_words_per_turn": round(avg_turn, 1),
        "em_dashes": dashes,
        "questions_asked": questions,
        "natural_acknowledgments": natural_acks,
        "total_speaker_lines": len(speaker_lines),
    }


def _print_comparison(label: str, gemini_val, claude_val, better_fn=None):
    """Print a comparison row with winner indication."""
    if better_fn:
        g_win = better_fn(gemini_val, claude_val)
        c_win = better_fn(claude_val, gemini_val)
    else:
        g_win = c_win = False

    g_marker = " <" if g_win and not c_win else ""
    c_marker = " <" if c_win and not g_win else ""
    print(f"  {label:<35} {str(gemini_val):>15}{g_marker:>3}  {str(claude_val):>15}{c_marker:>3}")


def compare(edition: str = "world", use_fixtures: bool = False):
    """Run A/B comparison between Gemini Flash and Claude Sonnet."""

    print(f"\n{'='*75}")
    print(f"  A/B COMPARISON: Gemini Flash vs Claude Sonnet — {edition} edition")
    print(f"{'='*75}\n")

    # Check availability
    if not gemini_ok():
        print("  [SKIP] Gemini Flash not available (GEMINI_API_KEY not set)")
        return
    if not claude_ok():
        print("  [SKIP] Claude Sonnet not available (ANTHROPIC_API_KEY not set)")
        print("  Set ANTHROPIC_API_KEY to run comparison.")
        return

    # Load clusters
    if use_fixtures and _FIXTURES_PATH.exists():
        clusters = json.loads(_FIXTURES_PATH.read_text())
        print(f"  Using fixtures: {len(clusters)} clusters")
    else:
        clusters = _fetch_clusters(edition)
        print(f"  Using live DB: {len(clusters)} clusters")

    if not clusters:
        print("  No clusters available — aborting")
        return

    # Build prompt (same for both models)
    prompt, system = _build_prompt(edition, clusters)
    print(f"  Prompt: {len(prompt.split())} words")

    # --- Generate TL;DR + audio with Gemini ---
    print(f"\n  [1/4] Generating with Gemini Flash...")
    t0 = time.time()
    gemini_result = gemini_generate(
        prompt, system_instruction=system, count_call=False, max_output_tokens=65536,
    )
    gemini_time = time.time() - t0
    print(f"  Gemini: {'OK' if gemini_result else 'FAILED'} ({gemini_time:.1f}s)")

    # --- Generate TL;DR + audio with Claude ---
    print(f"  [2/4] Generating with Claude Sonnet...")
    t0 = time.time()
    claude_result = claude_generate(
        prompt, system_instruction=system, count_call=False, max_output_tokens=65536,
    )
    claude_time = time.time() - t0
    print(f"  Claude: {'OK' if claude_result else 'FAILED'} ({claude_time:.1f}s)")

    if not gemini_result or not claude_result:
        print("\n  One or both models failed — cannot compare")
        return

    # --- Quality gate comparison ---
    print(f"\n  [3/4] Running quality gates...")
    g_passed, g_report = _check_quality(gemini_result, edition)
    c_passed, c_report = _check_quality(claude_result, edition)

    gm = g_report["metrics"]
    cm = c_report["metrics"]

    print(f"\n  {'METRIC':<35} {'GEMINI':>15}    {'CLAUDE':>15}")
    print(f"  {'-'*35} {'-'*15}    {'-'*15}")

    _print_comparison("Response time (s)", f"{gemini_time:.1f}", f"{claude_time:.1f}",
                       lambda a, b: float(a) < float(b))
    _print_comparison("Quality gate passed", g_passed, c_passed)
    _print_comparison("TL;DR words", gm.get("tldr_words", 0), cm.get("tldr_words", 0))
    _print_comparison("TL;DR lines", gm.get("tldr_lines", 0), cm.get("tldr_lines", 0))
    _print_comparison("Headline words", gm.get("headline_words", 0), cm.get("headline_words", 0))
    _print_comparison("Script words", gm.get("script_words", 0), cm.get("script_words", 0))
    _print_comparison("Speaker lines", gm.get("speaker_lines", 0), cm.get("speaker_lines", 0))
    _print_comparison("Short sentence %", f"{gm.get('pacing_short_pct', 0)}%", f"{cm.get('pacing_short_pct', 0)}%")
    _print_comparison("Long sentence %", f"{gm.get('pacing_long_pct', 0)}%", f"{cm.get('pacing_long_pct', 0)}%")
    _print_comparison("Rhythm markers", gm.get("rhythm_markers", 0), cm.get("rhythm_markers", 0))
    _print_comparison("Monologue max", gm.get("monologue_max", 0), cm.get("monologue_max", 0),
                       lambda a, b: int(a) < int(b))
    _print_comparison("Prohibited terms", len(gm.get("prohibited_terms_found", [])),
                       len(cm.get("prohibited_terms_found", [])),
                       lambda a, b: int(a) < int(b))
    _print_comparison("Filler found", len(gm.get("filler_found", [])),
                       len(cm.get("filler_found", [])),
                       lambda a, b: int(a) < int(b))
    _print_comparison("Sign-on present", gm.get("sign_on_present", False), cm.get("sign_on_present", False))
    _print_comparison("Sign-off present", gm.get("sign_off_present", False), cm.get("sign_off_present", False))

    # Naturalness scoring
    g_script = gemini_result.get("audio_script", "")
    c_script = claude_result.get("audio_script", "")
    if g_script and c_script:
        g_nat = _score_naturalness(g_script)
        c_nat = _score_naturalness(c_script)

        print(f"\n  {'NATURALNESS':<35} {'GEMINI':>15}    {'CLAUDE':>15}")
        print(f"  {'-'*35} {'-'*15}    {'-'*15}")
        _print_comparison("Speaker switches", g_nat["speaker_switches"], c_nat["speaker_switches"],
                           lambda a, b: int(a) > int(b))
        _print_comparison("Avg words/turn", g_nat["avg_words_per_turn"], c_nat["avg_words_per_turn"],
                           lambda a, b: float(a) < float(b))
        _print_comparison("Em dashes", g_nat["em_dashes"], c_nat["em_dashes"],
                           lambda a, b: int(a) > int(b))
        _print_comparison("Questions asked", g_nat["questions_asked"], c_nat["questions_asked"],
                           lambda a, b: int(a) > int(b))
        _print_comparison("Natural acknowledgments", g_nat["natural_acknowledgments"],
                           c_nat["natural_acknowledgments"],
                           lambda a, b: int(a) > int(b))

    # --- Opinion comparison ---
    lean = _get_today_lean()
    opinion_cluster = _select_opinion_cluster(clusters, edition)
    if opinion_cluster:
        print(f"\n  [4/4] Comparing opinion generation ({lean} lens)...")
        op_prompt, op_system = _build_opinion_prompt(opinion_cluster, lean, edition)

        t0 = time.time()
        g_opinion = gemini_generate(op_prompt, system_instruction=op_system, count_call=False, max_output_tokens=65536)
        g_op_time = time.time() - t0

        time.sleep(2)  # Rate limit buffer

        t0 = time.time()
        c_opinion = claude_generate(op_prompt, system_instruction=op_system, count_call=False, max_output_tokens=65536)
        c_op_time = time.time() - t0

        if g_opinion and c_opinion:
            g_text = g_opinion.get("opinion_text", "")
            c_text = c_opinion.get("opinion_text", "")
            g_audio = g_opinion.get("opinion_audio_script", "")
            c_audio = c_opinion.get("opinion_audio_script", "")

            print(f"\n  {'OPINION':<35} {'GEMINI':>15}    {'CLAUDE':>15}")
            print(f"  {'-'*35} {'-'*15}    {'-'*15}")
            _print_comparison("Opinion time (s)", f"{g_op_time:.1f}", f"{c_op_time:.1f}")
            _print_comparison("Opinion words", len(g_text.split()), len(c_text.split()))
            _print_comparison("Audio script words",
                               len(g_audio.split()) if g_audio else 0,
                               len(c_audio.split()) if c_audio else 0)

    # --- Print actual output samples ---
    print(f"\n{'='*75}")
    print(f"  SAMPLE OUTPUT — TL;DR")
    print(f"{'='*75}")
    g_tldr = gemini_result.get("tldr_text", "")
    c_tldr = claude_result.get("tldr_text", "")
    print(f"\n  --- GEMINI ---")
    for line in g_tldr.split("\n")[:5]:
        print(f"  {line.strip()}")
    print(f"\n  --- CLAUDE ---")
    for line in c_tldr.split("\n")[:5]:
        print(f"  {line.strip()}")

    print(f"\n{'='*75}")
    print(f"  SAMPLE OUTPUT — AUDIO SCRIPT (first 10 lines)")
    print(f"{'='*75}")
    print(f"\n  --- GEMINI ---")
    for line in g_script.split("\n")[:10]:
        print(f"  {line.strip()}")
    print(f"\n  --- CLAUDE ---")
    for line in c_script.split("\n")[:10]:
        print(f"  {line.strip()}")

    # Warnings/failures summary
    print(f"\n{'='*75}")
    print(f"  WARNINGS/FAILURES")
    print(f"{'='*75}")
    print(f"\n  Gemini: {len(g_report['failures'])} failures, {len(g_report['warnings'])} warnings")
    for f in g_report['failures']:
        print(f"    FAIL: {f}")
    for w in g_report['warnings'][:5]:
        print(f"    WARN: {w}")
    print(f"\n  Claude: {len(c_report['failures'])} failures, {len(c_report['warnings'])} warnings")
    for f in c_report['failures']:
        print(f"    FAIL: {f}")
    for w in c_report['warnings'][:5]:
        print(f"    WARN: {w}")

    print(f"\n{'='*75}")
    print(f"  VERDICT: Run this comparison 3x across different days.")
    print(f"  If Claude consistently wins on naturalness + quality gates,")
    print(f"  the switch is justified. Cost: ~$0.05/month.")
    print(f"{'='*75}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="A/B compare Gemini vs Claude for daily brief")
    parser.add_argument("--edition", default="world")
    parser.add_argument("--fixtures", action="store_true")
    args = parser.parse_args()
    compare(edition=args.edition, use_fixtures=args.fixtures)


if __name__ == "__main__":
    main()
