"""Stitch the house promo under the outro of History episodes that are already
published, without sending a single line back through TTS.

The 73 rendered documentaries cost about eighteen hours of compute. Each one
ends the same way: the close lands on its particular, the 14 s outro plays
over 600 ms of room tone, and the file ends in silence. The promo goes under
the outro's held bars, so the episode keeps its length, its chapters keep
their positions, and the H-07 gate does not move.

Per episode: fetch the pristine master from the release store, decode it,
lay the promo in, re-encode once at the same bitrate, rewrite the chapters
with one more entry, refresh the manifest, and replace the release asset.
The pristine master is kept under a second release tag so a later copy
change re-stitches from the original rather than from a stitched file.

    python3 pipeline/history/stitch_promos.py --slugs a,b --dry-run
    python3 pipeline/history/stitch_promos.py --all

Needs ffmpeg and ffprobe on PATH, pydub, numpy, mutagen, pyyaml, and
GITHUB_TOKEN to upload. Nothing here calls Kokoro.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing import house_promos as hp          # noqa: E402
from briefing import radio_producer as rp        # noqa: E402
from history import publish_audio, release_store  # noqa: E402

AUDIO_DIR = publish_audio.AUDIO_DIR
EVENTS = publish_audio.EVENTS
CLEAN_TAG = "history-audio-clean"

# History's outro arithmetic (history_producer.GAPS): the close's last word
# ends at pos; outro_at = pos - 500; total = outro_at + 14000 + 600.
OUTRO_OVERLAP_MS = 500
TAIL_MS = 600
LENGTH_TOLERANCE_MS = 150

# Guards on the stitched file. A promo that jumps 6 LU is a defect; so is one
# that clips, or one that leaves the file not ending in silence.
MAX_INTEGRATED_DELTA_LU = 1.0
MAX_TRUE_PEAK_DBTP = -0.8
MAX_PROMO_VS_SPEECH_DB = 3.0
TAIL_SILENCE_MS = 300
TAIL_SILENCE_DBFS = -50.0
PROMO_MARKER = "VOID_PROMO"


class StitchError(RuntimeError):
    pass


def _ffprobe_duration(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True,
                         check=True).stdout.strip()
    return float(out)


def _decode(mp3: Path, wav: Path):
    from pydub import AudioSegment

    ff = rp._ffmpeg()
    if not ff:
        raise StitchError("ffmpeg is required")
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(mp3), str(wav)],
                   check=True)
    return AudioSegment.from_file(str(wav), format="wav")


def _promo_marker(mp3: Path) -> str | None:
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError
    except ImportError:
        return None
    try:
        tags = ID3(str(mp3))
    except ID3NoHeaderError:
        return None
    for frame in tags.getall("TXXX"):
        if frame.desc == PROMO_MARKER:
            return str(frame.text[0]) if frame.text else ""
    return None


def _write_marker(mp3: Path, value: str) -> None:
    from mutagen.id3 import ID3, TXXX

    tags = ID3(str(mp3))
    tags.delall(f"TXXX:{PROMO_MARKER}")
    tags.add(TXXX(encoding=3, desc=PROMO_MARKER, text=[value]))
    tags.save(str(mp3), v2_version=3)


def _loudness(path: Path) -> tuple[float, float]:
    st = rp.measure_loudness(path)
    if not st:
        raise StitchError("could not measure loudness (ffmpeg loudnorm)")
    return float(st["input_i"]), float(st["input_tp"])


def _base_chapters(sidecar: Path) -> list[dict]:
    """The episode's chapters without any promo chapter a previous stitch
    added, so a re-stitch does not stack them."""
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    out = [c for c in data.get("chapters", [])
           if c.get("title") != hp.HISTORY_PROMO_CHAPTER_TITLE]
    if out and len(out) < len(data.get("chapters", [])):
        # The chapter before the promo was closed at the promo start; reopen
        # it to the end of the file, which is where it ran originally.
        out[-1] = dict(out[-1])
        out[-1]["endTime"] = data["chapters"][-1].get("endTime", out[-1].get("endTime"))
    return out


def _event_meta(slug: str) -> tuple[str, str]:
    title, date_display = slug, ""
    for line in (EVENTS / f"{slug}.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("title:") and title == slug:
            title = line.split(":", 1)[1].strip().strip('"\'')
        elif line.startswith("date_display:"):
            date_display = line.split(":", 1)[1].strip().strip('"\'')
    return title, date_display


SITE_URL = rp.SITE_URL


def ensure_clean_master(slug: str, work: Path, *, upload: bool, from_site: bool = False) -> Path:
    """The un-stitched master for a slug, fetched from the clean tag when it
    is there, otherwise from the live tag (and parked under the clean tag so
    the next copy change starts from the same bytes).

    `from_site` pulls the bytes the CDN serves instead, for a dry run on a
    machine that cannot reach the GitHub API. They are the same bytes the
    deploy fetched from the release; the marker check below still refuses a
    copy that already carries a promo."""
    clean_dir = work / "clean"
    clean_dir.mkdir(parents=True, exist_ok=True)
    dest = clean_dir / f"{slug}.mp3"
    if dest.exists() and dest.stat().st_size > 100_000:
        return dest
    if from_site:
        subprocess.run(["curl", "-sSfL", f"{SITE_URL}/audio/history/{slug}.mp3", "-o", str(dest)],
                       check=True)
        if _promo_marker(dest):
            raise StitchError(f"{slug}: the served file already carries a promo; use the release")
        return dest
    if release_store.has_asset(f"{slug}.mp3", tag=CLEAN_TAG):
        release_store.fetch(clean_dir, tag=CLEAN_TAG, slugs=[slug])
        return dest
    release_store.fetch(clean_dir, tag=release_store.TAG, slugs=[slug])
    marker = _promo_marker(dest)
    if marker:
        raise StitchError(f"{slug}: the live asset already carries a promo ({marker}) and "
                          f"there is no clean master under {CLEAN_TAG}; refusing to double-stitch")
    if upload:
        release_store.upload([dest], tag=CLEAN_TAG, replace=False)
    return dest


def stitch_one(slug: str, manifest: dict, work: Path, *, upload: bool, force: bool,
               dry_run: bool, from_site: bool = False) -> dict | None:
    entry = manifest["episodes"].get(slug)
    if not entry:
        raise StitchError(f"{slug} is not in the manifest")
    promo = hp.select("history", f"history:{slug}")
    if promo is None:
        raise StitchError("no eligible promo for history")
    want = {"id": promo.id, "sha": promo.sha}
    have = entry.get("promo") or {}
    if not force and have.get("id") == want["id"] and have.get("sha") == want["sha"]:
        print(f"  [stitch] {slug}: already carries {promo.id}, skipping")
        return None
    raw = hp.load_render(promo)
    if raw is None:
        raise StitchError(f"{slug}: no render for {promo.id} (run the render job first)")

    src = ensure_clean_master(slug, work, upload=upload, from_site=from_site)
    ep_dir = work / slug
    ep_dir.mkdir(parents=True, exist_ok=True)
    audio = _decode(src, ep_dir / "orig.wav")

    sidecar = AUDIO_DIR / f"{slug}.chapters.json"
    if not sidecar.exists():
        raise StitchError(f"{slug}: no chapter sidecar committed")
    base = _base_chapters(sidecar)
    total_ms = int(round(float(base[-1]["endTime"]) * 1000)) if base and "endTime" in base[-1] \
        else len(audio)
    if abs(len(audio) - total_ms) > LENGTH_TOLERANCE_MS:
        raise StitchError(f"{slug}: decoded {len(audio)} ms vs sidecar {total_ms} ms; "
                          f"the outro position cannot be trusted")
    total_ms = len(audio)
    outro_at = total_ms - (hp.OUTRO_MS + TAIL_MS)
    last_word = outro_at + OUTRO_OVERLAP_MS

    promo_seg = hp.mastered(raw, ep_dir)
    bed = hp.load_bed()
    if bed is None:
        raise StitchError(f"{slug}: the promo bed asset is missing")
    stitched, at = hp.stitch_post_roll(audio, outro_at, promo_seg, last_word_ms=last_word, bed=bed)
    if len(stitched) != len(audio):
        raise StitchError(f"{slug}: length changed ({len(audio)} -> {len(stitched)} ms)")

    # Guards, measured, not assumed.
    orig_wav = ep_dir / "orig.wav"
    out_wav = ep_dir / "stitched.wav"
    stitched.export(str(out_wav), format="wav")
    oi, _ = _loudness(orig_wav)
    si, stp = _loudness(out_wav)
    if abs(si - oi) > MAX_INTEGRATED_DELTA_LU:
        raise StitchError(f"{slug}: integrated loudness moved {si - oi:+.2f} LU")
    if stp > MAX_TRUE_PEAK_DBTP:
        raise StitchError(f"{slug}: true peak {stp} dBTP after the stitch")
    promo_end = at + len(promo_seg)
    speech_db = audio[last_word - 8000:last_word].dBFS
    promo_db = stitched[at:promo_end].dBFS
    if abs(promo_db - speech_db) > MAX_PROMO_VS_SPEECH_DB:
        raise StitchError(f"{slug}: promo window {promo_db:.1f} dBFS vs the last speech "
                          f"{speech_db:.1f} dBFS")
    if stitched[-TAIL_SILENCE_MS:].max_dBFS >= TAIL_SILENCE_DBFS:
        raise StitchError(f"{slug}: file no longer ends in silence "
                          f"({stitched[-TAIL_SILENCE_MS:].max_dBFS:.1f} dBFS)")
    if stitched[-1000:].raw_data != audio[-1000:].raw_data:
        raise StitchError(f"{slug}: the end of the file was altered")

    mp3 = ep_dir / f"{slug}.mp3"
    if not rp.encode_mp3(out_wav, mp3, "128k", 2):
        raise StitchError(f"{slug}: encode failed")
    chapters = hp.append_promo_chapter(base, promo, at, total_ms, kind="segment",
                                       title=hp.HISTORY_PROMO_CHAPTER_TITLE)
    title, date_display = _event_meta(slug)
    rp.write_id3_chapters(mp3, chapters, title, date_display)
    _write_marker(mp3, f"{promo.id}@{promo.sha}")
    (ep_dir / f"{slug}.chapters.json").write_bytes(rp.chapters_sidecar(chapters, title))
    (ep_dir / f"{slug}.promo.json").write_text(json.dumps({
        "id": promo.id, "sha": promo.sha, "voice": hp.HOUSE_VOICE,
        "startTime": round(at / 1000.0, 3)}, indent=1) + "\n", encoding="utf-8")

    print(f"  [stitch] {slug}: {promo.id} at {at / 1000:.1f}s, I {oi:.1f} -> {si:.1f} LUFS, "
          f"TP {stp:.1f}, promo {promo_db:.1f} vs speech {speech_db:.1f} dBFS")
    if dry_run:
        return {"slug": slug, "promo": promo.id, "dry_run": True}

    new_entry = publish_audio.publish(slug, ep_dir, manifest, restitch=True)
    if upload:
        release_store.upload([mp3], tag=release_store.TAG, replace=True)
    return new_entry


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slugs", help="comma-separated slugs")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--work", default=None, help="scratch directory (default: temp)")
    ap.add_argument("--dry-run", action="store_true", help="stitch and measure, publish nothing")
    ap.add_argument("--force", action="store_true", help="re-stitch even if the promo matches")
    ap.add_argument("--no-upload", action="store_true", help="never touch the release store")
    ap.add_argument("--from-site", action="store_true",
                    help="dry runs only: fetch the master from the live site, not the release")
    a = ap.parse_args()

    if a.from_site and not (a.dry_run and a.no_upload):
        ap.error("--from-site is for dry runs: add --dry-run --no-upload")
    manifest = publish_audio._load_manifest()
    slugs = sorted(manifest["episodes"]) if a.all else [s.strip() for s in a.slugs.split(",") if s.strip()]
    work = Path(a.work) if a.work else Path(tempfile.mkdtemp(prefix="void-stitch-"))
    done, failed = 0, []
    for slug in slugs:
        try:
            if stitch_one(slug, manifest, work, upload=not a.no_upload, force=a.force,
                          dry_run=a.dry_run, from_site=a.from_site):
                done += 1
        except Exception as e:  # one bad episode must not stop the catalogue
            failed.append(f"{slug}: {e}")
            print(f"  [stitch] FAIL {slug}: {e}", file=sys.stderr)
        finally:
            shutil.rmtree(work / slug, ignore_errors=True)
    if not a.dry_run and done:
        publish_audio.write_manifest(manifest)
    print(f"  [stitch] {done} stitched, {len(slugs) - done - len(failed)} skipped, {len(failed)} failed")
    for f in failed:
        print(f"    - {f}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
