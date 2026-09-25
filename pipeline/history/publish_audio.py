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


def build_entry(slug: str, src_dir: Path, existing: dict | None = None, *,
                restitch: bool = False) -> dict:
    """The manifest entry for a rendered (or re-stitched) episode.

    The fingerprint hashes the WHOLE file. It used to hash the first 1 KB,
    which is the ID3 header: a re-encode that left the tags alone kept the
    same `?v=`, so the CDN could serve the old bytes under new chapters for
    the length of its cache. `renderedAt` is when TTS last ran; `publishedAt`
    is when the file last changed. The staleness test compares the script's
    commit date against `renderedAt`.
    """
    mp3 = src_dir / f"{slug}.mp3"
    sidecar = src_dir / f"{slug}.chapters.json"
    promo_file = src_dir / f"{slug}.promo.json"
    event_file = EVENTS / f"{slug}.yaml"
    for f in (mp3, event_file):
        if not f.exists():
            raise FileNotFoundError(str(f))

    payload = mp3.read_bytes()
    if len(payload) > MAX_BYTES:
        raise ValueError(f"{slug}: {len(payload)/1048576:.1f} MB exceeds the "
                         f"{MAX_BYTES/1048576:.0f} MB Pages per-file limit")

    chapters: list[dict] = []
    if sidecar.exists():
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
    fp = hashlib.md5(payload).hexdigest()[:8]
    title = ""
    for line in event_file.read_text().splitlines():
        if line.startswith("title:"):
            title = line.split(":", 1)[1].strip().strip('"\'')
            break

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    promo = None
    if promo_file.exists():
        try:
            promo = json.loads(promo_file.read_text())
        except json.JSONDecodeError:
            promo = None
    existing = existing or {}
    # A stitch re-publishes a render made earlier and keeps that date; a
    # fresh render, promo or not, is rendered now.
    rendered_at = (existing.get("renderedAt") or existing.get("publishedAt") or now) \
        if restitch else now

    entry = {
        "url": f"/audio/history/{slug}.mp3?v={fp}",
        "chaptersUrl": f"/audio/history/{slug}.chapters.json?v={fp}",
        "title": title or slug,
        "durationSeconds": _duration_seconds(mp3),
        "bytes": len(payload),
        "chapters": chapters,
        "renderedAt": rendered_at,
        "publishedAt": now,
    }
    if promo:
        entry["promo"] = {k: promo[k] for k in ("id", "sha", "voice", "startTime") if k in promo}
    # Archival clips the episode carries (HISTORY-AUDIO-ARCHIVAL.md §4c.7):
    # id, where it plays, and the sha256 of the excerpt that was verified, so
    # tests/test_history_audio.py can hold the row to its ledger record.
    clips_file = src_dir / f"{slug}.clips.json"
    if clips_file.exists():
        try:
            clips = json.loads(clips_file.read_text())
        except json.JSONDecodeError:
            clips = None
        if clips:
            entry["clips"] = [{k: c[k] for k in ("id", "startTime", "endTime", "sha256") if k in c}
                              for c in clips]
    elif restitch and existing.get("clips"):
        entry["clips"] = existing["clips"]
    return entry


def publish(slug: str, src_dir: Path, manifest: dict, *, restitch: bool = False) -> dict:
    entry = build_entry(slug, src_dir, manifest["episodes"].get(slug), restitch=restitch)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src_dir / f"{slug}.mp3", AUDIO_DIR / f"{slug}.mp3")
    sidecar = src_dir / f"{slug}.chapters.json"
    if sidecar.exists():
        shutil.copyfile(sidecar, AUDIO_DIR / f"{slug}.chapters.json")
    manifest["episodes"][slug] = entry
    return entry


def write_manifest(manifest: dict) -> None:
    manifest["generatedAt"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["episodes"] = dict(sorted(manifest["episodes"].items()))
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=False) + "\n")


def pending(limit: int) -> list[str]:
    """Events that have a script written and no published episode, in catalogue
    order. This is what the render workflow fans out over, so "what is left to
    make" is answered by the manifest rather than by a list somebody maintains
    by hand and forgets to update."""
    manifest = _load_manifest()
    scripts = ROOT / "data" / "history" / "scripts"
    out = [f.stem for f in sorted(scripts.glob("*.txt"))
           if f.stem not in manifest["episodes"] and (EVENTS / f"{f.stem}.yaml").exists()]
    return out[:limit] if limit > 0 else out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slugs", nargs="*")
    ap.add_argument("--from", dest="src",
                    help="directory holding <slug>.mp3 and <slug>.chapters.json")
    ap.add_argument("--pending", type=int, metavar="N",
                    help="print, as JSON, the next N events with a script and no "
                         "published episode, then exit (0 = all)")
    a = ap.parse_args()

    if a.pending is not None:
        print(json.dumps(pending(a.pending)))
        return 0
    if not a.slugs or not a.src:
        ap.error("give one or more slugs and --from DIR (or use --pending N)")

    manifest = _load_manifest()
    for slug in a.slugs:
        entry = publish(slug, Path(a.src), manifest)
        print(f"  [history] {slug}: {entry['durationSeconds']/60:.1f} min, "
              f"{entry['bytes']//1024} KB, {len(entry['chapters'])} chapters")

    write_manifest(manifest)
    total = sum(e["bytes"] for e in manifest["episodes"].values())
    print(f"  [history] manifest: {len(manifest['episodes'])} episode(s), "
          f"{total/1048576:.1f} MB on the CDN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
