"""
void --revolt companion audio generator.

For each revolution YAML: build a deterministic two-voice narration script (no
LLM), synthesize it with edge-tts (Brian + Ava, $0), stitch to one MP3, upload
to Supabase Storage (audio-briefs/revolt/<slug>.mp3), and write audio_url +
audio_duration_seconds back to revolt_events.

Self-contained TTS (does not touch the shared audio_producer): edge-tts per
turn -> pydub concat -> mp3. Requires ffmpeg (pydub) + edge-tts.

Usage:
    python -m pipeline.revolt.generate_audio --slugs french-revolution
    python -m pipeline.revolt.generate_audio --all
    python -m pipeline.revolt.generate_audio --batch-size 8 --offset 0
    --force         regenerate ignoring the manifest
    --voices-only   reuse cached script, re-run TTS only
    --list          print manifest status
"""

import argparse
import asyncio
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.revolt.audio_script_generator import generate_revolt_audio_script

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_DIR = _PROJECT_ROOT / "data" / "revolt" / "events"
MANIFEST = _PROJECT_ROOT / "data" / "revolt" / "audio-manifest.json"
BUCKET = "audio-briefs"

_MALE_VOICE = "en-US-BrianMultilingualNeural"    # A = the narrator
_FEMALE_VOICE = "en-US-AvaMultilingualNeural"    # B = the analyst


def _parse_turns(script: str) -> list[tuple[str, str]]:
    turns: list[tuple[str, str]] = []
    for line in script.splitlines():
        line = line.strip()
        if len(line) < 3 or line[1] != ":":
            continue
        voice = _MALE_VOICE if line[0].upper() == "A" else _FEMALE_VOICE
        text = line[2:].strip()
        if text:
            turns.append((voice, text))
    return turns


async def _synth_turn(text: str, voice: str) -> bytes:
    import edge_tts
    comm = edge_tts.Communicate(text, voice)
    buf = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            buf.extend(chunk["data"])
    return bytes(buf)


async def _synth_all(turns: list[tuple[str, str]]) -> list[bytes]:
    return await asyncio.gather(*[_synth_turn(text, voice) for voice, text in turns])


def _upload(slug: str, audio_bytes: bytes) -> str:
    from pipeline.utils.supabase_client import supabase
    path = f"revolt/{slug}.mp3"
    supabase.storage.from_(BUCKET).upload(
        path, audio_bytes, {"content-type": "audio/mpeg", "upsert": "true"}
    )
    base = supabase.storage.from_(BUCKET).get_public_url(path)
    return f"{base}?v={hashlib.md5(audio_bytes[:1024]).hexdigest()[:8]}"


def produce_revolt_audio(script: str, slug: str) -> dict:
    from pydub import AudioSegment
    turns = _parse_turns(script)
    if not turns:
        raise RuntimeError("empty script")
    mp3s = asyncio.run(_synth_all(turns))

    combined = AudioSegment.silent(duration=200, frame_rate=24000)
    gap = AudioSegment.silent(duration=60, frame_rate=24000)
    for data in mp3s:
        seg = (
            AudioSegment.from_file(io.BytesIO(data), format="mp3")
            .set_frame_rate(24000).set_channels(1).set_sample_width(2)
        )
        combined += seg + gap

    buf = io.BytesIO()
    combined.export(buf, format="mp3", bitrate="96k", parameters=["-ac", "1"])
    audio_bytes = buf.getvalue()
    if len(audio_bytes) > 8 * 1024 * 1024:
        buf = io.BytesIO()
        combined.export(buf, format="mp3", bitrate="64k", parameters=["-ac", "1"])
        audio_bytes = buf.getvalue()

    audio_url = _upload(slug, audio_bytes)
    return {
        "audio_url": audio_url,
        "duration_seconds": round(len(combined) / 1000.0, 1),
        "file_size": len(audio_bytes),
    }


def _update_supabase(slug: str, audio_url: str, duration: float) -> None:
    from pipeline.utils.supabase_client import supabase
    supabase.table("revolt_events").update(
        {"audio_url": audio_url, "audio_duration_seconds": duration}
    ).eq("slug", slug).execute()


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def _save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def process_event(slug: str, manifest: dict, force: bool, voices_only: bool) -> None:
    if slug in manifest and not force and not voices_only:
        print(f"  [skip] {slug} (in manifest; --force to redo)")
        return
    path = EVENTS_DIR / f"{slug}.yaml"
    if not path.exists():
        print(f"  [error] not found: {path}")
        return
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    script = generate_revolt_audio_script(data, reuse_cached=voices_only)
    if not script:
        print(f"  [skip] {slug} (no script)")
        return
    print(f"  {slug}: {len(script.splitlines())} turns -> synthesizing")
    result = produce_revolt_audio(script, slug)
    _update_supabase(slug, result["audio_url"], result["duration_seconds"])
    manifest[slug] = {
        "url": result["audio_url"],
        "duration_seconds": result["duration_seconds"],
        "file_size_kb": round(result["file_size"] / 1024, 1),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_manifest(manifest)
    print(f"    done: {result['duration_seconds']}s, {round(result['file_size']/1024)}kb")


def _all_slugs() -> list[str]:
    return sorted(p.stem for p in EVENTS_DIR.glob("*.yaml"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate void --revolt companion audio")
    parser.add_argument("--slugs", nargs="*", help="Specific slugs")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--batch-size", type=int, default=0)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--voices-only", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    manifest = _load_manifest()

    if args.list:
        for slug in _all_slugs():
            row = manifest.get(slug)
            print(f"  {slug:34s} {'[' + str(row['duration_seconds']) + 's]' if row else '(none)'}")
        return

    if args.slugs:
        slugs = args.slugs
    else:
        slugs = _all_slugs()
        if args.batch_size:
            slugs = slugs[args.offset:args.offset + args.batch_size]

    if not slugs:
        print("  nothing to do")
        sys.exit(0)

    force = args.force or args.voices_only
    for slug in slugs:
        try:
            process_event(slug, manifest, force=force, voices_only=args.voices_only)
        except Exception as e:
            print(f"  [error] {slug}: {e}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
