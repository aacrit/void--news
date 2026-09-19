"""Publish a rendered History episode into the deployed static site.

The renderer (`history_producer.py`) writes an episode to a scratch directory.
This is the step that makes it REACHABLE: the MP3 and its Podcasting 2.0
sidecar are copied under `frontend/public/audio/history/`, and one manifest,
`frontend/public/data/history-audio.json`, records every published episode so
the History page knows which events have an audio edition without probing the
CDN for 78 files that mostly do not exist yet.

    python pipeline/history/publish_audio.py <slug> [slug ...] --from DIR

Where the files live is a decision with a shelf life. `docs/HISTORY-AUDIO.md`
picks Cloudflare R2 for the full 78-episode catalogue, because ~750 MB of MP3
cannot be un-committed from git cleanly. That bucket is not provisioned yet,
and the staged batches are small (10 episodes is ~110 MB), so the staged
catalogue ships on the Pages CDN out of `public/` exactly as the daily brief
does. The manifest is what makes the move cheap: every consumer reads the
`url` field, so switching to R2 changes the strings this script writes and
nothing else.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVENTS = ROOT / "data" / "history" / "events"
AUDIO_DIR = ROOT / "frontend" / "public" / "audio" / "history"
MANIFEST = ROOT / "frontend" / "public" / "data" / "history-audio.json"

# Cloudflare Pages refuses a single asset over 25 MiB. Every episode is 8-15
# minutes at 128k stereo (~10-15 MB), so this is headroom rather than a
# constraint, but a runaway render must fail here and not at deploy time.
MAX_BYTES = 25 * 1024 * 1024


def _duration_seconds(mp3: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(mp3)],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(out), 3)


def _load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text())
            if isinstance(data, dict) and isinstance(data.get("episodes"), dict):
                return data
        except json.JSONDecodeError:
            pass
    return {"generatedAt": None, "episodes": {}}


def publish(slug: str, src_dir: Path, manifest: dict) -> dict:
    mp3 = src_dir / f"{slug}.mp3"
    sidecar = src_dir / f"{slug}.chapters.json"
    event_file = EVENTS / f"{slug}.yaml"
    for f in (mp3, event_file):
        if not f.exists():
            raise FileNotFoundError(str(f))

    payload = mp3.read_bytes()
    if len(payload) > MAX_BYTES:
        raise ValueError(f"{slug}: {len(payload)/1048576:.1f} MB exceeds the "
                         f"{MAX_BYTES/1048576:.0f} MB Pages per-file limit")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    (AUDIO_DIR / f"{slug}.mp3").write_bytes(payload)

    chapters: list[dict] = []
    if sidecar.exists():
        shutil.copyfile(sidecar, AUDIO_DIR / f"{slug}.chapters.json")
        for c in json.loads(sidecar.read_text()).get("chapters", []):
            entry = {"startTime": c["startTime"], "title": c.get("title", ""),
                     # History segments are not radio segments. "segment" is the
                     # kind every consumer reads as "a documentary chapter": the
                     # rail draws the title alone, with no No. 3 / Opinion badge.
                     "kind": "segment"}
            if isinstance(c.get("endTime"), (int, float)):
                entry["endTime"] = c["endTime"]
            chapters.append(entry)

    # The filename is stable per slug so a re-render overwrites in place; the
    # fingerprint in the query string is what invalidates the CDN and the
    # browser cache. Same convention as the daily brief.
    fp = hashlib.md5(payload[:1024]).hexdigest()[:8]
    title = ""
    for line in event_file.read_text().splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip('"\'')
            break

    entry = {
        "url": f"/audio/history/{slug}.mp3?v={fp}",
        "chaptersUrl": f"/audio/history/{slug}.chapters.json?v={fp}",
        "title": title or slug,
        "durationSeconds": _duration_seconds(mp3),
        "bytes": len(payload),
        "chapters": chapters,
        "publishedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    manifest["episodes"][slug] = entry
    return entry


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--from", dest="src", required=True,
                    help="directory holding <slug>.mp3 and <slug>.chapters.json")
    a = ap.parse_args()

    manifest = _load_manifest()
    for slug in a.slugs:
        entry = publish(slug, Path(a.src), manifest)
        print(f"  [history] {slug}: {entry['durationSeconds']/60:.1f} min, "
              f"{entry['bytes']//1024} KB, {len(entry['chapters'])} chapters")

    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["episodes"] = dict(sorted(manifest["episodes"].items()))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")
    total = sum(e["bytes"] for e in manifest["episodes"].values())
    print(f"  [history] manifest: {len(manifest['episodes'])} episode(s), "
          f"{total/1048576:.1f} MB on the CDN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
