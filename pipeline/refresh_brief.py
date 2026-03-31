"""
Standalone brief regenerator — regenerates TL;DR + opinion from current DB
without running the full pipeline. Uses Gemini for both calls.

Usage:
    python pipeline/refresh_brief.py                        # world edition
    python pipeline/refresh_brief.py --editions world,us
    python pipeline/refresh_brief.py --no-audio             # skip audio synthesis
    python pipeline/refresh_brief.py --opinion-only         # only regenerate opinion
    python pipeline/refresh_brief.py --tldr-only            # only regenerate TL;DR + audio
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from briefing.daily_brief_generator import (
    generate_daily_briefs,
    _get_today_lean,
    _select_opinion_cluster,
    _generate_opinion,
)
from briefing.voice_rotation import get_voices_for_today


def _fetch_clusters(editions: list[str]) -> list[dict]:
    """Fetch current clusters from DB."""
    all_clusters = []
    seen_ids = set()
    for edition in editions:
        res = supabase.table("story_clusters").select(
            "id,title,summary,category,section,sections,source_count,"
            "headline_rank,consensus_points,divergence_points,divergence_score"
        ).contains("sections", [edition]).order(
            "headline_rank", desc=True
        ).limit(25).execute()

        if res.data:
            for c in res.data:
                if c["id"] not in seen_ids:
                    c["_db_id"] = c["id"]
                    all_clusters.append(c)
                    seen_ids.add(c["id"])
            print(f"  {edition}: {len(res.data)} clusters")
        else:
            print(f"  {edition}: no clusters found")
    return all_clusters


def _get_current_brief(edition: str) -> dict | None:
    """Fetch the current brief for an edition."""
    res = supabase.table("daily_briefs").select("*").eq(
        "edition", edition
    ).order("created_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None


def main():
    parser = argparse.ArgumentParser(description="Regenerate Daily Brief from current DB")
    parser.add_argument("--editions", default="world", help="Comma-separated editions")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio synthesis")
    parser.add_argument("--opinion-only", action="store_true", help="Only regenerate opinion")
    parser.add_argument("--tldr-only", action="store_true", help="Only regenerate TL;DR + audio")
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",")]
    today_lean = _get_today_lean()
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    print(f"Regenerating briefs for: {editions}")
    print(f"Today's opinion lean: {today_lean.upper()}")
    print()

    # Fetch clusters
    print("[1/4] Fetching clusters from DB...")
    all_clusters = _fetch_clusters(editions)
    if not all_clusters:
        print("No clusters — nothing to generate")
        return

    for edition in editions:
        print(f"\n{'='*60}")
        print(f"EDITION: {edition.upper()}")
        print(f"{'='*60}")

        current = _get_current_brief(edition)

        # --- TL;DR + Audio ---
        if not args.opinion_only:
            print("\n[2/4] Generating TL;DR + audio script via Gemini...")
            briefs = generate_daily_briefs(all_clusters, {}, edition_sections=[edition])
            brief = briefs.get(edition, {})

            tldr = brief.get("tldr_text", "")
            script = brief.get("audio_script")
            words = len(tldr.split())
            lines = len([l for l in tldr.split("\n") if l.strip()])
            print(f"\n  TL;DR: {words} words, {lines} lines")
            print(f"  Audio script: {'yes' if script else 'no'}")
            print(f"\n  --- TL;DR TEXT ---")
            for line in tldr.split("\n"):
                if line.strip():
                    print(f"  {line.strip()}")
            print(f"  --- END ---")
        else:
            brief = {}
            if current:
                brief["tldr_text"] = current.get("tldr_text", "")
                brief["audio_script"] = current.get("audio_script")
                brief["top_cluster_ids"] = current.get("top_cluster_ids", [])

        # --- Opinion ---
        if not args.tldr_only:
            print(f"\n[3/4] Generating {today_lean.upper()} opinion editorial...")
            opinion_cluster = _select_opinion_cluster(all_clusters, edition)
            if opinion_cluster:
                title = (opinion_cluster.get("title") or "")[:80]
                sc = opinion_cluster.get("source_count", 0)
                print(f"  Selected: \"{title}\" ({sc} sources)")

                opinion_result = _generate_opinion(opinion_cluster, today_lean, date_str)
                if opinion_result:
                    brief["opinion_text"] = opinion_result["opinion_text"]
                    brief["opinion_audio_script"] = opinion_result.get("opinion_audio_script")
                    brief["opinion_lean"] = opinion_result["opinion_lean"]
                    brief["opinion_cluster_id"] = opinion_result["opinion_cluster_id"]
                    owords = len(opinion_result["opinion_text"].split())
                    print(f"\n  Opinion: {owords} words, lean={today_lean.upper()}")
                    print(f"\n  --- OPINION TEXT ---")
                    print(f"  {opinion_result['opinion_text']}")
                    print(f"  --- END ---")
                else:
                    print("  Opinion generation failed")
            else:
                print("  No suitable cluster for opinion")

        # --- Audio ---
        audio_result = None
        if not args.no_audio and not args.opinion_only and brief.get("audio_script"):
            print("\n[4/4] Synthesizing audio via Gemini Flash TTS...")
            try:
                from briefing.audio_producer import produce_audio
                voices = get_voices_for_today(edition)
                audio_result = produce_audio(
                    brief["audio_script"], voices, edition,
                    opinion_audio_script=brief.get("opinion_audio_script"),
                )
                if audio_result:
                    print(f"  Audio: {audio_result['duration_seconds']}s, "
                          f"{audio_result['file_size'] / 1024:.0f} KB")
            except ImportError:
                print("  Audio producer not available — skipping")
        else:
            print("\n[4/4] Audio: skipped")

        # --- Store to DB ---
        print("\n  Storing to DB...")
        row = {
            "edition": edition,
            "tldr_text": brief.get("tldr_text", current.get("tldr_text", "") if current else ""),
            "opinion_text": brief.get("opinion_text"),
            "opinion_headline": brief.get("opinion_headline"),
            "opinion_audio_script": brief.get("opinion_audio_script"),
            "opinion_lean": brief.get("opinion_lean"),
            "opinion_cluster_id": brief.get("opinion_cluster_id"),
            "audio_script": brief.get("audio_script", current.get("audio_script") if current else None),
            "top_cluster_ids": brief.get("top_cluster_ids", current.get("top_cluster_ids", []) if current else []),
        }

        # Carry forward audio from current brief if not regenerated
        if not audio_result and current:
            for field in ("audio_url", "audio_duration_seconds", "audio_file_size",
                          "audio_voice", "audio_voice_label", "opinion_start_seconds"):
                if current.get(field):
                    row[field] = current[field]
        elif audio_result:
            voices = get_voices_for_today(edition)
            row["audio_url"] = audio_result["audio_url"]
            row["audio_duration_seconds"] = audio_result["duration_seconds"]
            row["audio_file_size"] = audio_result["file_size"]
            has_opinion = bool(brief.get("opinion_audio_script"))
            row["audio_voice"] = f"{voices['host_a']['id']}+{voices['host_b']['id']}" + (
                f"+{voices['opinion']['id']}" if has_opinion else ""
            )
            row["audio_voice_label"] = "Three voices" if has_opinion else "Two voices"
            row["opinion_start_seconds"] = audio_result.get("opinion_start_seconds")

        try:
            # Delete old and insert new (no pipeline_run_id for standalone)
            supabase.table("daily_briefs").delete().eq("edition", edition).is_(
                "pipeline_run_id", "null"
            ).execute()
            supabase.table("daily_briefs").insert(row).execute()
            print(f"  Stored successfully")
        except Exception as e:
            # Fallback: try upsert without pipeline_run_id constraint
            try:
                supabase.table("daily_briefs").delete().eq("edition", edition).execute()
                supabase.table("daily_briefs").insert(row).execute()
                print(f"  Stored (replaced existing)")
            except Exception as e2:
                print(f"  DB error: {e2}")

    print("\nDone.")


if __name__ == "__main__":
    main()
