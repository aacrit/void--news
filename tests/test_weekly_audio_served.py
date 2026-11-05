#!/usr/bin/env python3
"""The Weekly MP3 must be the file its own row says it is.

Every Weekly check in this repo runs before synthesis. W-01..W-12 judge the
script; `test_weekly_assembly` judges a timeline built from a fake segment.
Nothing has ever looked at the audio that ships, and on 2026-09-20 that gap
published a row reading

    audio_voice            kokoro:bm_lewis+am_michael+af_heart
    audio_voice_label      Three voices
    audio_duration_seconds 1349.7

over a file measuring

    24000 Hz, 1 channel, 96 kb/s, 1002.07 s, -20.5 LUFS integrated

which is the legacy `audio_producer` signature exactly: it encodes 96k mono at
24 kHz and calls `loudnorm` nowhere. The new producer encodes 128k stereo and
masters to -16 LUFS. A listener was told "Three voices" and heard two.

So this gate does not read the row and believe it. It probes the artifact and
asserts the row is true of it. Four properties, each of which the live file
failed:

  1. duration matches `audio_duration_seconds`
  2. stereo, not mono
  3. integrated loudness within 1 LU of -16
  4. a chapters sidecar exists beside the MP3

Run against a local deploy tree by default. Pass --url to probe the CDN, which
is where correctness is actually judged:

    python3 tests/test_weekly_audio_served.py
    python3 tests/test_weekly_audio_served.py --url https://news.voidvision.org
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request


def fetch(url: str, dest: pathlib.Path | None = None, timeout: int = 300):
    """Bytes from a URL. curl first: this container's egress proxy answers
    urllib with 403 while curl is configured for it, and a gate that cannot
    reach the CDN is a gate that never judges what readers actually get."""
    if have("curl"):
        cmd = ["curl", "-sS", "--fail", "--max-time", str(timeout), url]
        if dest:
            cmd += ["-o", str(dest)]
            subprocess.run(cmd, check=True, capture_output=True)
            return dest.read_bytes()
        out = subprocess.run(cmd, check=True, capture_output=True)
        return out.stdout
    with urllib.request.urlopen(url, timeout=timeout) as fh:
        data = fh.read()
    if dest:
        dest.write_bytes(data)
    return data

ROOT = pathlib.Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "frontend/public"

TARGET_LUFS = -16.0
LUFS_TOLERANCE = 1.0
DURATION_TOLERANCE_S = 1.5

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"  [ok] {name}" + (f" — {detail}" if detail else ""))
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"  [FAIL] {name}" + (f" — {detail}" if detail else ""))


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def probe(path: pathlib.Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0",
         "-show_entries", "stream=channels,sample_rate,bit_rate",
         "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True)
    blob = json.loads(out.stdout or "{}")
    stream = (blob.get("streams") or [{}])[0]
    return {
        "channels": int(stream.get("channels") or 0),
        "sample_rate": int(stream.get("sample_rate") or 0),
        "duration": float((blob.get("format") or {}).get("duration") or 0.0),
    }


def loudness(path: pathlib.Path) -> float | None:
    out = subprocess.run(
        ["ffmpeg", "-nostats", "-i", str(path),
         "-filter_complex", "ebur128=framelog=quiet", "-f", "null", "-"],
        capture_output=True, text=True)
    m = re.search(r"I:\s*(-?\d+\.?\d*)\s*LUFS", out.stderr or "")
    return float(m.group(1)) if m else None


WEEKLY_AUDIO_DIR = PUBLIC / "audio/weekly-world"
WEEKLY_ISSUES = ROOT / "frontend/build-data/weekly-issues.json"


def _issue_rows() -> list[dict]:
    """Every Weekly issue row the deploy tree carries: the back-issue archive
    and the current issue."""
    rows: list[dict] = []
    for path in (WEEKLY_ISSUES, PUBLIC / "data/weekly.json"):
        if not path.exists():
            continue
        blob = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(blob, dict):
            blob = blob["issues"] if isinstance(blob.get("issues"), list) else [blob]
        rows.extend(r for r in blob if isinstance(r, dict))
    return rows


def orphan_weekly_audio(audio_dir: pathlib.Path, rows: list[dict]) -> list[str]:
    """Files under the Weekly audio directory that no issue row names.

    The inverse of the gate below. On 2026-10-02 the withdrawn Issue #26 audio
    (rev 84 cut the passages it speaks) still answered 206 at
    `/audio/weekly-world/latest.mp3` and `/2026-09-21-am.mp3`, with
    `latest.chapters.json` titled for it, because withdrawing the episode
    cleared the row and left the files: no row pointed at them, so no check
    looked. A file is legitimate only if a row's `audio_url` names it, or it
    is that MP3's `.chapters.json` sidecar, or it is a `latest.*` alias that
    is byte-identical to a named file (the producer writes one beside every
    render). Anything else is audio no page offers and a URL still serves.
    """
    if not audio_dir.exists():
        return []
    named: set[str] = set()
    for r in rows:
        url = (r.get("audio_url") or "").split("?")[0]
        if not url.startswith("/audio/weekly-world/"):
            continue
        name = url.rsplit("/", 1)[1]
        named.add(name)
        named.add(name.rsplit(".", 1)[0] + ".chapters.json")
    named_bytes = {(audio_dir / n).read_bytes() for n in named if (audio_dir / n).is_file()}
    out = []
    for f in sorted(p for p in audio_dir.iterdir() if p.is_file()):
        if f.name in named:
            continue
        if f.name.startswith("latest.") and f.read_bytes() in named_bytes:
            continue
        out.append(f.name)
    return out


def check_no_orphans() -> None:
    """Runs everywhere, with or without ffmpeg: it reads names and bytes."""
    orphans = orphan_weekly_audio(WEEKLY_AUDIO_DIR, _issue_rows())
    check("no Weekly audio file that no issue row names", not orphans,
          (", ".join(orphans) + ": delete it (a withdrawn episode must not stay "
           "reachable by URL)") if orphans else "")

    # The rule must be able to fail: a planted orphan beside a named file.
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="void-weekly-orphan-"))
    try:
        (tmp / "2026-01-04-pm.mp3").write_bytes(b"named")
        (tmp / "2026-01-04-pm.chapters.json").write_bytes(b"{}")
        (tmp / "latest.mp3").write_bytes(b"named")
        (tmp / "2025-12-28-pm.mp3").write_bytes(b"withdrawn")
        (tmp / "latest.chapters.json").write_bytes(b"withdrawn chapters")
        planted = orphan_weekly_audio(tmp, [
            {"audio_url": "/audio/weekly-world/2026-01-04-pm.mp3?v=1"},
            {"audio_url": None}])
        check("the orphan rule catches a planted withdrawn file and a stale alias",
              planted == ["2025-12-28-pm.mp3", "latest.chapters.json"], str(planted))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--url", help="probe this origin instead of the local tree")
    args = ap.parse_args()

    if not args.url:
        print("Weekly audio directory: every file is named by an issue row")
        check_no_orphans()
        if failures:
            print(f"\nFAIL  {len(failures)} Weekly audio check(s)")
            return 1

    if not (have("ffprobe") and have("ffmpeg")):
        print("SKIP  ffmpeg/ffprobe not available; cannot judge the artifact")
        return 0

    print("Weekly served-audio gate")

    if args.url:
        base = args.url.rstrip("/")
        blob = json.loads(fetch(f"{base}/data/weekly.json", timeout=60).decode())
        print(f"  source: {base}/data/weekly.json")
    else:
        local = PUBLIC / "data/weekly.json"
        if not local.exists():
            print("SKIP  no local weekly.json")
            return 0
        blob = json.loads(local.read_text(encoding="utf-8"))
        print(f"  source: {local.relative_to(ROOT)}")

    issue = blob if isinstance(blob, dict) else blob[0]
    url = issue.get("audio_url")
    if not url:
        print("  [ok] this issue has no audio; nothing to judge")
        return 0

    stated_seconds = issue.get("audio_duration_seconds")
    stated_voice = issue.get("audio_voice") or ""
    bare = url.split("?")[0]
    sidecar = bare.rsplit(".", 1)[0] + ".chapters.json"

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="void-weekly-audio-"))
    try:
        if args.url:
            mp3 = tmp / "weekly.mp3"
            fetch(base + url, dest=mp3)
            try:
                sidecar_ok = bool(json.loads(fetch(base + sidecar, timeout=60).decode()))
            except Exception:
                sidecar_ok = False
        else:
            mp3 = PUBLIC / bare.lstrip("/")
            if not mp3.exists():
                check("the file the row points at exists", False, str(bare))
                return 1
            sidecar_ok = (PUBLIC / sidecar.lstrip("/")).exists()

        info = probe(mp3)
        lufs = loudness(mp3)

        # 1. The row's duration must describe this file.
        if stated_seconds:
            delta = abs(info["duration"] - float(stated_seconds))
            check("the row's duration describes this file",
                  delta <= DURATION_TOLERANCE_S,
                  f"row says {float(stated_seconds):.1f}s, file is "
                  f"{info['duration']:.1f}s ({delta:.1f}s apart)")

        # 2. Stereo. The legacy path wrote mono.
        check("stereo", info["channels"] == 2,
              f"{info['channels']} channel(s) at {info['sample_rate']} Hz")

        # 3. Mastered. The legacy path called loudnorm nowhere.
        if lufs is None:
            check("integrated loudness is measurable", False, "ebur128 gave nothing")
        else:
            check("mastered to the house target",
                  abs(lufs - TARGET_LUFS) <= LUFS_TOLERANCE,
                  f"{lufs:.1f} LUFS against {TARGET_LUFS:.0f} "
                  f"+/- {LUFS_TOLERANCE:.0f}")

        # 4. The chapter rail. The Argument always emits one.
        check("a chapters sidecar sits beside the MP3", sidecar_ok, sidecar)

        # 5. And the row must name a Kokoro cast, not a Gemini or edge label.
        check("the row names a Kokoro cast", stated_voice.startswith("kokoro:"),
              f"audio_voice is {stated_voice!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print(f"\nFAIL  {len(failures)} served-audio check(s)")
        print("  The row and the file disagree. Re-render with "
              "`weekly-digest.yml mode=audio-only`, which renders the "
              "committed script and spends no Gemini call.")
        return 1
    print("\nPASS  the served Weekly episode is what its row says it is")
    return 0


if __name__ == "__main__":
    sys.exit(main())
