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
5. The audio speaks today's script: the manifest's `script_sha256` (the hash
   of the script the render read) equals the hash of the committed script.
   Content, not commit dates, so it holds on a shallow clone. A mismatch
   fails unless the entry is `audio_withdrawn` (served nowhere); a null hash
   is listed as unverified, never passed.

Run: python tests/test_history_audio.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "frontend" / "public" / "data" / "history-audio.json"
AUDIO = ROOT / "frontend" / "public" / "audio" / "history"
EVENTS = ROOT / "data" / "history" / "events"
MAX_BYTES = 25 * 1024 * 1024

failures: list[str] = []


# The editions an entry may name. Mirrors publish_audio.EDITIONS (asserted in
# main) and the frontend reader, which marks only these.
EDITIONS = frozenset({"first-listener"})


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


def _raises(fn, exc) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


def script_sha256(path: Path) -> str:
    """The same hash history_producer.py takes of the bytes it renders."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_findings(episodes: dict, scripts: Path) -> tuple[list[str], list[str], list[str]]:
    """(failures, notes, unverified) for the audio-speaks-its-script rule.

    - no `script_sha256` field at all: a failure (every entry must say what
      it knows, even if that is null);
    - null: unverified. Rendered before the hash was recorded and not provable
      from the run record. Listed on every run as needing a check, never
      counted as a pass;
    - a hash that differs from today's script: a failure, unless the entry is
      `audio_withdrawn`, in which case no page, feed or deploy serves it and
      it is noted as awaiting a re-render.
    """
    fails: list[str] = []
    notes: list[str] = []
    unverified: list[str] = []
    for slug, ep in sorted(episodes.items()):
        if "script_sha256" not in ep:
            fails.append(f"{slug}: manifest entry has no script_sha256 field "
                         f"(publish_audio.py writes it; null if unproven)")
            continue
        recorded = ep.get("script_sha256")
        script = scripts / f"{slug}.txt"
        if recorded is None:
            unverified.append(slug)
            continue
        if not script.exists():
            fails.append(f"{slug}: no script at {script.name} to hold the audio to")
            continue
        current = script_sha256(script)
        if current == recorded:
            if ep.get("audio_withdrawn"):
                notes.append(f"{slug}: withdrawn, yet its audio matches the script; "
                             f"lift the withdrawal")
            continue
        detail = (f"{slug}: audio was rendered from script {recorded[:12]}, the script is "
                  f"now {current[:12]}")
        # A revision that contradicts nothing the audio says (a time-bound
        # phrase made durable, 2026-10-02) may wait for its re-render while
        # the episode keeps serving, but only by a committed attestation tied
        # to the exact revised script: any further edit fails again.
        rev = ep.get("script_revised_after_render") or {}
        if ep.get("audio_withdrawn"):
            notes.append(detail + "; withdrawn, not served, awaiting a re-render")
        elif (isinstance(rev, dict) and rev.get("sha256") == current
              and str(rev.get("reason") or "").strip() and rev.get("at")):
            notes.append(detail + f"; revised {rev['at']} without contradicting the audio "
                         f"({rev['reason'][:90]}), awaiting a re-render")
        else:
            fails.append(detail + ": the served audio contradicts its corrected script. "
                         "Re-render it, or mark it audio_withdrawn (or, if the revision contradicts "
                         "nothing the audio says, record script_revised_after_render with this "
                         "script's sha256 and the reason)")
    return fails, notes, unverified


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
        # The edition mark ("New recording" on the pages) is a closed set: a
        # misspelt value would print nothing, and an unknown one would print a
        # claim no publisher made.
        if "edition" in ep:
            check(f"{slug}: edition is one publish_audio.py knows",
                  ep["edition"] in EDITIONS, repr(ep["edition"]))

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

        # An archival clip the row says the episode carries (§4c.7 of
        # HISTORY-AUDIO-ARCHIVAL.md) must be a signed ledger recording whose
        # verification record hashed exactly this excerpt, and must sit on
        # its own chapter inside the episode.
        for clip in ep.get("clips") or []:
            cid = clip.get("id")
            led_path = ROOT / "data/history/evidence" / slug / "ledger.yaml"
            rec = None
            try:
                import yaml as _y
                rows = (_y.safe_load(led_path.read_text(encoding="utf-8")) or {}).get("recordings") or []
                rec = next((r for r in rows if r.get("id") == cid), None)
            except Exception as e:  # noqa: BLE001
                check(f"{slug}: clip {cid}: ledger readable", False, str(e))
            check(f"{slug}: clip {cid} is a ledger recording", rec is not None)
            if rec is None:
                continue
            check(f"{slug}: clip {cid} is signed", bool(rec.get("signed_by")) and bool(rec.get("signed_at")))
            vpath = ROOT / "data/history/evidence" / slug / str(rec.get("verification") or "missing")
            ver = json.loads(vpath.read_text(encoding="utf-8")) if vpath.exists() else {}
            check(f"{slug}: clip {cid} verification passed", bool(ver.get("pass")))
            check(f"{slug}: clip {cid} sha256 is the verified excerpt",
                  clip.get("sha256") and clip.get("sha256") == ver.get("excerpt_sha256"),
                  f"{clip.get('sha256')} vs {ver.get('excerpt_sha256')}")
            s, e = clip.get("startTime"), clip.get("endTime")
            check(f"{slug}: clip {cid} plays inside the episode",
                  isinstance(s, (int, float)) and isinstance(e, (int, float)) and 0 < s < e
                  and (not isinstance(claimed, (int, float)) or e <= claimed), f"{s}-{e}")
            check(f"{slug}: clip {cid} has its own chapter",
                  any(abs((c.get("startTime") or -1) - (s or -2)) < 0.01 for c in chapters))

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

    # The audio must speak the script as it stands. Two H-11 fixes
    # (great-leap-forward, gutenberg) once sat corrected in the scripts and
    # uncorrected in the MP3s; on 2026-10-02 two published theses
    # (haitian-revolution, scramble-for-africa) did the same. The check that
    # should have caught the second pair compared commit dates and skipped
    # itself on a shallow clone, which is every CI checkout. It compares
    # CONTENT now: the manifest stores the sha256 of the script the render
    # read, and this hashes today's script. No history needed.
    fails, notes, unverified = script_findings(episodes, ROOT / "data/history/scripts")
    for f in fails:
        check(f, False)

    # The rule must be able to fail: the pair above, had nobody withdrawn
    # them, is exactly what it exists to refuse.
    line_sha = hashlib.sha256(b"N: a corrected line\n").hexdigest()
    planted = {"x": {"script_sha256": "0" * 64}, "y": {"script_sha256": None},
               "z": {"script_sha256": "0" * 64, "audio_withdrawn": True},
               "r": {"script_sha256": "0" * 64, "script_revised_after_render":
                     {"sha256": line_sha, "reason": "a time-bound phrase dated", "at": "2026-10-02"}},
               "s": {"script_sha256": "0" * 64, "script_revised_after_render":
                     {"sha256": "1" * 64, "reason": "attested an older revision", "at": "2026-10-02"}}}
    tmp = Path(tempfile.mkdtemp(prefix="void-hist-sha-"))
    try:
        for s in planted:
            (tmp / f"{s}.txt").write_text("N: a corrected line\n")
        pf, pn, pu = script_findings(planted, tmp)
        check("planted: a stale, served episode fails, and so does one whose attestation "
              "names another revision", sorted(f.split(":")[0] for f in pf) == ["s", "x"], str(pf))
        check("planted: an unverified episode is listed, not passed", pu == ["y"], str(pu))
        check("planted: a withdrawn episode and an attested revision are noted, not failed",
              sorted(n.split(":")[0] for n in pn) == ["r", "z"], str(pn))
        missing_field = script_findings({"w": {}}, tmp)[0]
        check("planted: an entry with no script_sha256 field fails",
              len(missing_field) == 1, str(missing_field))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # A withdrawn episode is served nowhere: the deploy does not fetch it, and
    # every reader of the manifest in the frontend filters it.
    withdrawn = {s for s, e in episodes.items() if e.get("audio_withdrawn")}
    try:
        from history import release_store
        fetched = set(release_store.served_slugs(data))
        check("deploy fetches no withdrawn episode", not (fetched & withdrawn),
              str(sorted(fetched & withdrawn)))
        check("deploy fetches every other episode", fetched == set(episodes) - withdrawn)
    except ImportError as e:
        check("release_store importable", False, str(e))
    for rel in ("frontend/app/history/audio.ts", "frontend/app/audio/page.tsx"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        check(f"{rel} filters audio_withdrawn episodes", "audio_withdrawn" in src)
        check(f"{rel} marks editions through history/edition.ts", "isNewRecording" in src)
    edition_src = (ROOT / "frontend/app/history/edition.ts").read_text(encoding="utf-8")
    for ed in EDITIONS:
        check(f"frontend/app/history/edition.ts marks the {ed!r} edition", f'"{ed}"' in edition_src)
    try:
        from history import publish_audio as _pa
        check("publish_audio.EDITIONS matches this test's", set(_pa.EDITIONS) == set(EDITIONS),
              f"{sorted(_pa.EDITIONS)} vs {sorted(EDITIONS)}")
        # A stitch keeps the edition; a fresh render keeps only what it is told.
        check("planted: an unknown --edition is refused",
              _raises(lambda: _pa.build_entry("x", Path("."), edition="remastered"), ValueError))
        real_slug = next(iter(sorted(episodes)), None)
        if real_slug:
            src = Path(tempfile.mkdtemp(prefix="void-hist-ed-"))
            real_dur = _pa._duration_seconds
            try:
                (src / f"{real_slug}.mp3").write_bytes(b"ID3planted")
                _pa._duration_seconds = lambda _p: 1.0
                prior = {"edition": "first-listener", "script_sha256": None}
                kept = _pa.build_entry(real_slug, src, prior, restitch=True)
                fresh = _pa.build_entry(real_slug, src, prior)
                named = _pa.build_entry(real_slug, src, {}, edition="first-listener")
                check("planted: a restitch keeps the edition", kept.get("edition") == "first-listener")
                check("planted: a re-render without --edition does not inherit it",
                      "edition" not in fresh)
                check("planted: --edition is written", named.get("edition") == "first-listener")
            finally:
                _pa._duration_seconds = real_dur
                shutil.rmtree(src, ignore_errors=True)
    except ImportError as e:
        check("publish_audio importable", False, str(e))
    for slug in withdrawn:
        check(f"{slug}: withdrawn with a reason on record",
              bool(str(episodes[slug].get("audio_withdrawn_reason") or "").strip()))

    for n in notes:
        print(f"note  {n}")
    if unverified:
        print(f"WARN  {len(unverified)} episode(s) need verifying against their script "
              f"(script_sha256 is null: rendered with no hash on record): "
              + ", ".join(unverified))

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
