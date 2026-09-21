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


sys.path.insert(0, str(ROOT / "pipeline"))
PROMO_CHAPTER_TITLE = "Also from Void News"   # house_promos.HISTORY_PROMO_CHAPTER_TITLE
try:
    from briefing import house_promos as hp
    PROMOS = hp.load_pool()
    assert hp.HISTORY_PROMO_CHAPTER_TITLE == PROMO_CHAPTER_TITLE
except Exception as _e:  # pyyaml missing: the promo checks degrade to "no promo entries"
    hp = None
    PROMOS = []


def promo_marker(path: Path) -> str | None:
    try:
        from mutagen.id3 import ID3
        for f in ID3(str(path)).getall("TXXX"):
            if f.desc == "VOID_PROMO":
                return str(f.text[0]) if f.text else ""
        return ""
    except Exception:
        return None   # no mutagen or no tags: skipped


def tail_max_dbfs(path: Path, ms: int = 300) -> float | None:
    try:
        from pydub import AudioSegment
        return AudioSegment.from_file(str(path))[-ms:].max_dBFS
    except Exception:
        return None


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
        check(f"{slug}: url is site-relative", url.startswith("/audio/history/"), url)
        check(f"{slug}: url carries a cache fingerprint", "?v=" in url, url)

        sidecar = AUDIO / f"{slug}.chapters.json"
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

        # A stitched episode carries the house promo under its outro. The
        # manifest says which one; the chapters, the file and the pool must
        # agree with it, and the promo must never be a History promo.
        promo = ep.get("promo")
        if promo and hp is None:
            check(f"{slug}: promo checks need pyyaml (pip install pyyaml)", False)
        elif promo:
            pool_ids = {p.id: p for p in PROMOS}
            check(f"{slug}: promo {promo.get('id')} is in the pool", promo.get("id") in pool_ids)
            pp = pool_ids.get(promo.get("id"))
            if pp:
                check(f"{slug}: promo text unchanged since the stitch", pp.sha == promo.get("sha"),
                      f"{promo.get('sha')} vs {pp.sha}: re-stitch")
                check(f"{slug}: promo does not advertise History", pp.promotes != "history")
                check(f"{slug}: promo is the deterministic pick for this slug",
                      hp.select("history", f"history:{slug}", PROMOS).id == pp.id)
            check(f"{slug}: last chapter is the promo",
                  bool(chapters) and chapters[-1].get("title") == PROMO_CHAPTER_TITLE,
                  str(chapters[-1].get("title") if chapters else None))
            if len(chapters) >= 2 and isinstance(claimed, (int, float)):
                start = chapters[-1].get("startTime")
                check(f"{slug}: chapter before the promo closes where it starts",
                      chapters[-2].get("endTime") == start)
                check(f"{slug}: promo starts under the outro",
                      isinstance(start, (int, float))
                      and claimed - 14.6 + 1.0 <= start <= claimed - 14.6 + 3.0,
                      f"start {start} vs duration {claimed}")
                check(f"{slug}: promo chapter runs to the end",
                      abs(float(chapters[-1].get("endTime", -1)) - claimed) <= 0.1)
            check(f"{slug}: renderedAt recorded", bool(ep.get("renderedAt")))
            if mp3.exists():
                marker = promo_marker(mp3)
                if marker is not None:
                    check(f"{slug}: file carries the promo marker",
                          marker == f"{promo.get('id')}@{promo.get('sha')}", marker)
                tail = tail_max_dbfs(mp3)
                if tail is not None:
                    check(f"{slug}: file still ends in silence", tail < -50.0, f"{tail:.1f} dBFS")
        else:
            check(f"{slug}: no promo chapter without a promo entry",
                  not any(c.get("title") == PROMO_CHAPTER_TITLE for c in chapters))

    if AUDIO.exists():
        for mp3 in sorted(AUDIO.glob("*.mp3")):
            check(f"{mp3.name}: published file is in the manifest",
                  mp3.stem in episodes)

    # An episode whose SCRIPT changed after it was rendered is serving audio
    # that no longer matches its own source of truth. This is not hypothetical:
    # two H-11 disclosure fixes (great-leap-forward's secondhand Mao quote,
    # gutenberg's attributed friar) were corrected in the scripts and left
    # uncorrected in the published MP3s, so the page kept presenting both lines
    # as verbatim speech. Nobody noticed until this check was written; the
    # manifest carries publishedAt and git carries the script's commit date, so
    # the comparison was always available.
    import subprocess
    from datetime import datetime

    # A SHALLOW clone has one commit, so `git log -1 -- <file>` returns that
    # commit's date for EVERY file, and every script looks newer than every
    # episode. actions/checkout defaults to fetch-depth 1, so the first CI run
    # after this check shipped reported all 49 episodes stale and failed the
    # publish job, discarding ten good renders. The guard for this was written
    # as "no output, skip", which is the one thing a shallow clone never does.
    shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                             capture_output=True, text=True, cwd=ROOT).stdout.strip()
    if shallow == "true":
        print("note: shallow clone, skipping the script-newer-than-audio check")
        episodes_to_date = {}
    else:
        episodes_to_date = episodes

    for slug, meta in sorted(episodes_to_date.items()):
        script = ROOT / f"data/history/scripts/{slug}.txt"
        # A stitch re-publishes without re-rendering, so the date that says
        # whether the AUDIO matches the script is renderedAt, not publishedAt.
        published = meta.get("renderedAt") or meta.get("publishedAt")
        if not script.exists() or not published:
            continue
        iso = subprocess.run(["git", "log", "-1", "--format=%cI", "--", str(script)],
                             capture_output=True, text=True, cwd=ROOT).stdout.strip()
        if not iso:
            continue          # untracked or shallow clone: nothing to compare
        changed = datetime.fromisoformat(iso)
        rendered = datetime.fromisoformat(published.replace("Z", "+00:00"))
        check(f"{slug}: published audio is not older than its script",
              changed <= rendered,
              f"script changed {changed:%Y-%m-%d %H:%M}, audio rendered "
              f"{rendered:%Y-%m-%d %H:%M}: re-render it")

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
