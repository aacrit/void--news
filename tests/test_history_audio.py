"""The History audio manifest describes what is actually deployed.

`frontend/public/data/history-audio.json` is the one record of which events
have an audio edition, and the History page reads it at build time. Nothing
else checks it: a manifest entry pointing at a file that was never committed
produces a Listen button that 404s, on a page where the audio IS the feature.

So this asserts the manifest against the repository it ships with:

1. Every entry names a real event (a slug with a YAML file), because an
   episode the catalogue cannot reach is invisible.
2. Every entry has its chapter sidecar committed. The MP3s are NOT in git any
   more (they live in a GitHub Release and the deploy pulls them into the
   publish directory), so the sidecar is the in-repo proof that an episode was
   really published, and a missing MP3 is caught at deploy time instead: the
   fetch step fails the deploy rather than shipping a Listen button that 404s.
3. The chapters are ordered, start at zero and stay inside the episode, which
   is what the player's rail arithmetic assumes.
4. Where an MP3 IS present (the render job, before it uploads), its size and
   duration match what the manifest claims and it is under the Cloudflare
   Pages per-file limit; and nothing sitting in public/audio/history is
   missing from the manifest.

Run: python tests/test_history_audio.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "frontend" / "public" / "data" / "history-audio.json"
AUDIO = ROOT / "frontend" / "public" / "audio" / "history"
EVENTS = ROOT / "data" / "history" / "events"
MAX_BYTES = 25 * 1024 * 1024

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}{': ' + detail if detail else ''}")


def duration_of(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, check=True).stdout.strip()
        return float(out)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None   # no ffprobe on this machine: the other checks still run


def main() -> int:
    if not MANIFEST.exists():
        print("PASS  no History audio manifest yet, nothing to verify")
        return 0

    data = json.loads(MANIFEST.read_text())
    episodes = data.get("episodes")
    check("manifest carries an episodes map", isinstance(episodes, dict))
    if not isinstance(episodes, dict):
        print("\n".join(failures))
        return 1

    for slug, ep in episodes.items():
        check(f"{slug}: event exists", (EVENTS / f"{slug}.yaml").exists())

        url = ep.get("url", "")
        # An episode lives EITHER in the deploy (site-relative) or in R2
        # (absolute). Both are valid, and a mixed manifest is expected while the
        # catalogue migrates; what is never valid is a third shape.
        on_r2 = url.startswith("https://")
        check(f"{slug}: url is site-relative or an absolute media url",
              on_r2 or url.startswith("/audio/history/"), url)
        check(f"{slug}: url carries a cache fingerprint", "?v=" in url, url)

        # An episode is published EITHER inside the deploy or to R2. When it is
        # on R2 the sidecar went with it, so neither file is in the repo, and an
        # episode that is in BOTH places is the migration left half-done.
        sidecar = AUDIO / f"{slug}.chapters.json"
        if on_r2:
            check(f"{slug}: not also committed to the repo",
                  not (AUDIO / f"{slug}.mp3").exists() and not sidecar.exists(),
                  "an episode on R2 that is ALSO in git is the migration half-done")
        else:
            check(f"{slug}: chapter sidecar is committed", sidecar.exists(), str(sidecar))

        claimed = ep.get("durationSeconds")
        check(f"{slug}: duration recorded", isinstance(claimed, (int, float)) and claimed > 0)
        check(f"{slug}: byte count recorded",
              isinstance(ep.get("bytes"), int) and ep["bytes"] > 0, str(ep.get("bytes")))
        check(f"{slug}: under the Pages per-file limit",
              isinstance(ep.get("bytes"), int) and ep["bytes"] <= MAX_BYTES,
              f"{(ep.get('bytes') or 0)/1048576:.1f} MB")

        # The MP3 itself is only on disk in the render job. Everywhere else
        # (a fresh clone, CI, a reviewer's machine) it lives in the release,
        # and the deploy's fetch step is what proves it is there. The manifest
        # checks above and the chapter checks below do not depend on it.
        mp3 = AUDIO / f"{slug}.mp3"
        if mp3.exists():
            size = mp3.stat().st_size
            check(f"{slug}: manifest byte count matches the file",
                  ep.get("bytes") == size, f"{ep.get('bytes')} vs {size}")
            real = duration_of(mp3)
            if real is not None and isinstance(claimed, (int, float)):
                check(f"{slug}: duration matches the file", abs(real - claimed) < 1.0,
                      f"{claimed} vs {real:.1f}")

        # The format is an 8-15 minute documentary (H-07 polices the script;
        # this polices what was actually rendered from it), measured from the
        # duration the render recorded so it holds without the file present.
        if isinstance(claimed, (int, float)):
            check(f"{slug}: runs 8-15 minutes", 7.5 * 60 <= claimed <= 15.5 * 60,
                  f"{claimed/60:.1f} min")

        chapters = ep.get("chapters") or []
        check(f"{slug}: has chapters", len(chapters) >= 3, str(len(chapters)))
        if chapters:
            check(f"{slug}: first chapter starts at zero",
                  chapters[0].get("startTime") == 0, str(chapters[0].get("startTime")))
        starts = [c.get("startTime") for c in chapters]
        check(f"{slug}: chapters are in play order",
              all(isinstance(s, (int, float)) for s in starts)
              and starts == sorted(starts), str(starts[:4]))
        if isinstance(claimed, (int, float)):
            check(f"{slug}: no chapter starts past the end",
                  all(isinstance(s, (int, float)) and s <= claimed for s in starts))
        check(f"{slug}: every chapter is titled",
              all(str(c.get("title", "")).strip() for c in chapters))
        # "segment" is what the player reads as a documentary chapter; any other
        # kind would draw a radio badge ("No. 3", "Opinion") on a history rail.
        check(f"{slug}: chapters are documentary segments",
              all(c.get("kind") == "segment" for c in chapters))

    if AUDIO.exists():
        for mp3 in sorted(AUDIO.glob("*.mp3")):
            check(f"{mp3.name}: published file is in the manifest",
                  mp3.stem in episodes)

    if failures:
        print("\n".join(f"FAIL  {f}" for f in failures))
        print(f"\n{len(failures)} History audio failure(s)")
        return 1
    on_disk = sum(1 for slug in episodes if (AUDIO / f"{slug}.mp3").exists())
    print(f"PASS  {len(episodes)} History episode(s): events, sidecars, chapters "
          f"({on_disk} with the MP3 on disk)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
