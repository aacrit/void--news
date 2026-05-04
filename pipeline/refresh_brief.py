"""
Standalone brief regenerator — single entry point for all Daily Brief refresh
operations. Regenerates TL;DR, opinion, and/or audio from current DB (or
frozen test fixtures) without running the full pipeline.

Usage:
    python pipeline/refresh_brief.py                              # full: TL;DR + opinion + audio
    python pipeline/refresh_brief.py --editions world,us
    python pipeline/refresh_brief.py --no-audio                   # TL;DR + opinion, skip TTS
    python pipeline/refresh_brief.py --opinion-only               # only regenerate opinion
    python pipeline/refresh_brief.py --tldr-only --no-audio       # only regenerate TL;DR text

    # Prompt iteration (no DB writes, deterministic input):
    python pipeline/refresh_brief.py --dry-run --output /tmp/brief.json
    python pipeline/refresh_brief.py --fixtures --dry-run --output /tmp/brief.json
    python pipeline/refresh_brief.py --snapshot-fixtures           # save current DB → test_clusters.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from briefing.daily_brief_generator import (
    generate_daily_briefs,
    _get_today_lean,
    _select_opinion_cluster,
    _generate_opinion,
)
from briefing.voice_rotation import get_voices_for_today

_FIXTURES_PATH = Path(__file__).parent / "briefing" / "test_clusters.json"


def _fetch_clusters_db(editions: list[str]) -> list[dict]:
    """Fetch current clusters from live DB."""
    from utils.supabase_client import supabase

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


def _fetch_clusters_fixtures(editions: list[str]) -> list[dict]:
    """Load frozen test clusters from fixtures file."""
    if not _FIXTURES_PATH.exists():
        print(f"  Fixtures file not found: {_FIXTURES_PATH}")
        print(f"  Run with --snapshot-fixtures first to create it.")
        return []
    with open(_FIXTURES_PATH) as f:
        all_clusters = json.load(f)
    # Filter to requested editions
    filtered = []
    for c in all_clusters:
        sections = c.get("sections", [])
        if any(e in sections for e in editions):
            c["_db_id"] = c.get("id", c.get("_db_id", ""))
            filtered.append(c)
    print(f"  Loaded {len(filtered)} clusters from fixtures (editions: {editions})")
    return filtered


def _snapshot_fixtures(editions: list[str]) -> None:
    """Save current DB clusters to test_clusters.json for deterministic iteration."""
    clusters = _fetch_clusters_db(editions)
    if not clusters:
        print("No clusters to snapshot")
        return
    # Strip _db_id (will be re-added on load from "id" field)
    clean = []
    for c in clusters:
        row = {k: v for k, v in c.items() if k != "_db_id"}
        clean.append(row)
    with open(_FIXTURES_PATH, "w") as f:
        json.dump(clean, f, indent=2, default=str)
    print(f"Saved {len(clean)} clusters to {_FIXTURES_PATH}")


def _get_current_brief(edition: str) -> dict | None:
    """Fetch the current brief for an edition."""
    from utils.supabase_client import supabase

    res = supabase.table("daily_briefs").select("*").eq(
        "edition", edition
    ).order("created_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None


def main():
    parser = argparse.ArgumentParser(description="Regenerate Daily Brief")
    parser.add_argument("--editions", default="world", help="Comma-separated editions")
    parser.add_argument("--no-audio", action="store_true", help="Skip audio synthesis")
    parser.add_argument("--opinion-only", action="store_true", help="Only regenerate opinion")
    parser.add_argument("--tldr-only", action="store_true", help="Only regenerate TL;DR + audio")
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate but skip DB write. Use with --output for JSON dump.")
    parser.add_argument("--fixtures", action="store_true",
                        help="Load clusters from test_clusters.json instead of live DB")
    parser.add_argument("--output", type=str, default=None,
                        help="Write output + quality report to this JSON file (implies --dry-run)")
    parser.add_argument("--snapshot-fixtures", action="store_true",
                        help="Save current DB clusters to test_clusters.json and exit")
    args = parser.parse_args()

    editions = [e.strip() for e in args.editions.split(",")]

    # --output implies --dry-run
    if args.output:
        args.dry_run = True

    # Snapshot mode: save fixtures and exit
    if args.snapshot_fixtures:
        print(f"Snapshotting clusters for editions: {editions}")
        _snapshot_fixtures(editions)
        return

    today_lean = _get_today_lean()
    date_str = datetime.now(timezone.utc).strftime("%A, %d %B %Y")

    print(f"Regenerating briefs for: {editions}")
    print(f"Today's opinion lean: {today_lean.upper()}")
    if args.dry_run:
        print("DRY RUN — no DB writes")
    if args.fixtures:
        print("FIXTURES MODE — using frozen test clusters")
    print()

    # Fetch clusters
    print("[1/4] Fetching clusters...")
    if args.fixtures:
        all_clusters = _fetch_clusters_fixtures(editions)
    else:
        all_clusters = _fetch_clusters_db(editions)
    if not all_clusters:
        print("No clusters — nothing to generate")
        return

    # Collect all outputs for --output JSON dump
    all_outputs = {}

    for edition in editions:
        print(f"\n{'='*60}")
        print(f"EDITION: {edition.upper()}")
        print(f"{'='*60}")

        current = None if args.dry_run else _get_current_brief(edition)

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
                    brief["opinion_headline"] = opinion_result.get("opinion_headline")
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

        # --- Collect output for JSON dump ---
        edition_output = {
            "edition": edition,
            "tldr_headline": brief.get("tldr_headline"),
            "tldr_text": brief.get("tldr_text", ""),
            "opinion_text": brief.get("opinion_text"),
            "opinion_headline": brief.get("opinion_headline"),
            "opinion_lean": brief.get("opinion_lean"),
            "audio_script": brief.get("audio_script"),
            "opinion_audio_script": brief.get("opinion_audio_script"),
            "quality_report": brief.get("quality_report"),
        }
        all_outputs[edition] = edition_output

        # --- Audio ---
        audio_result = None
        if not args.no_audio and not args.opinion_only and not args.dry_run and brief.get("audio_script"):
            print("\n[4/4] Synthesizing audio via Gemini Flash TTS...")
            try:
                from briefing.audio_producer import produce_audio
                voices = get_voices_for_today(edition)
                audio_result = produce_audio(
                    brief["audio_script"], voices, edition,
                    opinion_audio_script=brief.get("opinion_audio_script"),
                    opinion_lean=brief.get("opinion_lean"),
                )
                if audio_result:
                    print(f"  Audio: {audio_result['duration_seconds']}s, "
                          f"{audio_result['file_size'] / 1024:.0f} KB")
            except ImportError:
                print("  Audio producer not available — skipping")
        else:
            reason = "dry-run" if args.dry_run else "skipped"
            print(f"\n[4/4] Audio: {reason}")

        # --- Store to DB (skip in dry-run) ---
        if args.dry_run:
            print("\n  DB write: skipped (dry-run)")
            continue

        print("\n  Storing to DB...")
        row = {
            "edition": edition,
            "tldr_headline": brief.get("tldr_headline"),
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
            from utils.supabase_client import supabase
            supabase.table("daily_briefs").delete().eq("edition", edition).is_(
                "pipeline_run_id", "null"
            ).execute()
            supabase.table("daily_briefs").insert(row).execute()
            print(f"  Stored successfully")
        except Exception as e:
            try:
                from utils.supabase_client import supabase
                supabase.table("daily_briefs").delete().eq("edition", edition).execute()
                supabase.table("daily_briefs").insert(row).execute()
                print(f"  Stored (replaced existing)")
            except Exception as e2:
                print(f"  DB error: {e2}")

    # --- Write JSON output ---
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(all_outputs, f, indent=2, default=str)
        print(f"\nOutput written to: {output_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
