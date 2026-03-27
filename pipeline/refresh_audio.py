"""
Standalone audio brief refresh — generates Daily Brief audio from current DB
without running the full pipeline. Fast: prompt + TTS only (~60-90 seconds).

Usage:
    python pipeline/refresh_audio.py                  # world edition
    python pipeline/refresh_audio.py --editions world,us,india
"""

import argparse
import sys
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from briefing.daily_brief_generator import generate_daily_briefs
from briefing.audio_producer import produce_audio
from briefing.voice_rotation import get_voices_for_today


def main():
    parser = argparse.ArgumentParser(description="Refresh Daily Brief audio from current DB")
    parser.add_argument("--editions", default="world", help="Comma-separated editions (default: world)")
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",")]
    print(f"Refreshing audio for editions: {editions}")

    # Fetch current clusters from DB (same query as frontend)
    print("\n[1/3] Fetching clusters from DB...")
    all_clusters = []
    for edition in editions:
        res = supabase.table("story_clusters").select(
            "id,title,summary,category,section,sections,source_count,"
            "headline_rank,consensus_points,divergence_points"
        ).contains("sections", [edition]).order(
            "headline_rank", desc=True
        ).limit(20).execute()

        if res.data:
            for c in res.data:
                c["_db_id"] = c["id"]
            all_clusters.extend(res.data)
            print(f"  {edition}: {len(res.data)} clusters")
        else:
            print(f"  {edition}: no clusters found")

    if not all_clusters:
        print("No clusters — nothing to generate")
        return

    # Generate briefs (Gemini call for prompt + audio script)
    print("\n[2/3] Generating briefs via Gemini...")
    briefs = generate_daily_briefs(all_clusters, {}, edition_sections=editions)

    # Synthesize audio and upload
    print("\n[3/3] Synthesizing audio via Gemini Flash TTS...")
    for edition, brief in briefs.items():
        script = brief.get("audio_script")
        if not script:
            print(f"  {edition}: no audio script — skipping")
            continue

        voices = get_voices_for_today(edition)
        result = produce_audio(
            script, voices, edition,
            opinion_audio_script=brief.get("opinion_audio_script"),
        )

        if result:
            # Update daily_briefs table with full brief data
            row = {
                "edition": edition,
                "tldr_text": brief["tldr_text"],
                "opinion_text": brief.get("opinion_text"),
                "opinion_lean": brief.get("opinion_lean"),
                "opinion_cluster_id": brief.get("opinion_cluster_id"),
                "audio_script": brief.get("audio_script"),
                "audio_url": result["audio_url"],
                "audio_duration_seconds": result["duration_seconds"],
                "audio_file_size": result["file_size"],
                "audio_voice": f"{voices['host_a']['id']}+{voices['host_b']['id']}" + (
                    f"+{voices['opinion']['id']}" if brief.get("opinion_audio_script") else ""
                ),
                "audio_voice_label": "Three voices" if brief.get("opinion_audio_script") else "Two voices",
                "top_cluster_ids": brief.get("top_cluster_ids", []),
            }
            try:
                supabase.table("daily_briefs").delete().eq("edition", edition).execute()
                supabase.table("daily_briefs").insert(row).execute()
                print(f"  {edition}: audio uploaded — {result['duration_seconds']}s, {result['file_size'] / 1024:.0f} KB")
            except Exception as e:
                print(f"  {edition}: DB update failed: {e}")
        else:
            print(f"  {edition}: audio synthesis failed")

    print("\nDone.")


if __name__ == "__main__":
    main()
