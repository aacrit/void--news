"""On Air: the chapters served beside an episode are that episode's. No LLM, no TTS.

    python tests/test_onair_sidecar.py

Why this exists (2026-09-26, run 36250153830). R-14 rejected both rundown
attempts, the show fell back to the legacy edge-tts path (a deliberate safety
path: a show always ships), and that path wrote latest.mp3 while leaving the
PREVIOUS radio show's latest.chapters.json beside it. The served tree then
offered Sept 25's chapter titles for Sept 26's audio, and brief.json labelled
the file "Three voices" / "Orus+Achernar+Sulafat" while two edge-tts voices
read it. And R-14 itself failed on a false positive: the prompt asks for
letter-spelled initialisms ("N-A-T-O", "U-S") and R-14 counted the spelled
form as a word the story never used.

Checks:
  S-01  committed tree: every latest.chapters.json is byte-identical to the
        dated sidecar of the episode latest.mp3 is (by content), and no
        latest.chapters.json sits beside an episode that has none
  S-02  committed tree: brief.json names the episode latest.mp3 is, and its
        audio_chapters agree with the served sidecar (both absent, or the same
        start times)
  S-03  committed tree: no dated sidecar survives its MP3
  S-04  _write_audio_static with no sidecar removes the older latest.chapters.json
        and keeps nothing stale; with a sidecar, writes both copies
  S-05  R-14: a spelled initialism is the written one ("N-A-T-O" == "NATO"),
        and a real substitution still fails
  S-06  brief.json's voice label is not a roster name the legacy path never
        used (a Gemini roster id over an edge-tts file)
"""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

AUDIO = ROOT / "frontend" / "public" / "audio"
BRIEF = ROOT / "frontend" / "public" / "data" / "brief.json"

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  [{'ok' if cond else 'FAIL'}] {msg}")
    if not cond:
        failures.append(msg)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def latest_stem(d: Path) -> str | None:
    """The dated stem whose MP3 is byte-identical to latest.mp3."""
    latest = d / "latest.mp3"
    if not latest.exists():
        return None
    want = _md5(latest)
    hits = [p.name[:-4] for p in sorted(d.glob("20??-??-??-??.mp3")) if _md5(p) == want]
    return hits[-1] if hits else None


def sidecar_problems(d: Path) -> list[str]:
    """S-01 and S-03 over one edition directory. Pure, so S-04 can reuse it."""
    out: list[str] = []
    stem = latest_stem(d)
    lc = d / "latest.chapters.json"
    if (d / "latest.mp3").exists() and stem is None:
        out.append(f"{d.name}: latest.mp3 matches no dated episode")
    if lc.exists():
        own = d / f"{stem}.chapters.json" if stem else None
        if own is None or not own.exists():
            out.append(f"{d.name}: latest.chapters.json sits beside {stem or 'an unknown episode'}, "
                       f"which has no chapters of its own (stale sidecar from an older show)")
        elif own.read_bytes() != lc.read_bytes():
            out.append(f"{d.name}: latest.chapters.json differs from {own.name}, the episode latest.mp3 is")
    for side in d.glob("20??-??-??-??.*"):
        if side.suffix != ".mp3" and not (d / (side.name.split(".", 1)[0] + ".mp3")).exists():
            out.append(f"{d.name}: {side.name} survives its MP3")
    return out


def committed_tree() -> None:
    dirs = [p for p in sorted(AUDIO.iterdir()) if p.is_dir() and p.name != "history"] if AUDIO.exists() else []
    check(bool(dirs), f"S-01 audio edition directories found ({[p.name for p in dirs]})")
    for d in dirs:
        probs = sidecar_problems(d)
        check(not probs, f"S-01/S-03 {d.name}: " + ("; ".join(probs) if probs else "latest sidecar is this episode's"))

    if not BRIEF.exists():
        return
    brief = json.loads(BRIEF.read_text())
    url = (brief.get("audio_url") or "").split("?")[0]
    if not url:
        return
    d = AUDIO / Path(url).parent.name
    named = Path(url).name[:-4] if url.endswith(".mp3") else None
    stem = latest_stem(d)
    check(named == stem, f"S-02 brief.json names {named}, latest.mp3 is {stem}")
    chapters = brief.get("audio_chapters")
    if isinstance(chapters, str):
        try:
            chapters = json.loads(chapters)
        except ValueError:
            chapters = None
    lc = d / "latest.chapters.json"
    if not chapters:
        check(not lc.exists(), "S-02 brief.json carries no chapters, so none may be served as latest")
    else:
        served = json.loads(lc.read_text()).get("chapters", []) if lc.exists() else []
        check([c.get("startTime") for c in served] == [c.get("startTime") for c in chapters],
              "S-02 brief.json chapters and latest.chapters.json have the same start times")

    # S-06: the legacy path used to label an edge-tts file with Gemini roster ids.
    voice = str(brief.get("audio_voice") or "")
    gen = str(brief.get("generator") or "")
    if chapters or "+radio:" in gen:
        check(True, "S-06 radio episode; voice label comes from the render")
    else:
        from briefing.voice_rotation import HOSTS, OPINION_VOICES
        roster = {h["id"] for h in HOSTS.values()} | set(OPINION_VOICES.values())
        used = [v for v in voice.replace("edge:", "").split("+") if v]
        bad = [v for v in used if v in roster]
        check(not bad, f"S-06 legacy episode's audio_voice names voices that read it, not roster ids ({voice!r})")
        label = brief.get("audio_voice_label")
        want = {1: "One voice", 2: "Two voices", 3: "Three voices"}.get(len(used))
        check(label in (None, want), f"S-06 audio_voice_label {label!r} agrees with {len(used)} voice(s) named")


def writer() -> None:
    import briefing.audio_producer as ap
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        old_root = ap._STATIC_AUDIO_ROOT
        ap._STATIC_AUDIO_ROOT = root
        try:
            d = root / "world"
            d.mkdir()
            # Yesterday's radio show, with chapters, rotated in as the real writer does.
            (d / "2026-09-25-pm.mp3").write_bytes(b"radio-25" * 100)
            (d / "2026-09-25-pm.chapters.json").write_bytes(b'{"chapters": [0]}')
            (d / "2026-09-23-pm.chapters.json").write_bytes(b'{"chapters": [1]}')  # MP3 long gone
            (d / "latest.mp3").write_bytes(b"radio-25" * 100)
            (d / "latest.chapters.json").write_bytes(b'{"chapters": [0]}')
            url = ap._write_audio_static(b"legacy-26" * 100, "world")  # legacy: no sidecars
            check(bool(url), "S-04 writer returned a URL")
            check(not (d / "latest.chapters.json").exists(),
                  "S-04 a chapter-less episode removes the older latest.chapters.json")
            check(not (d / "2026-09-23-pm.chapters.json").exists(),
                  "S-04 a dated sidecar whose MP3 is gone is removed")
            check((d / "2026-09-25-pm.chapters.json").exists(),
                  "S-04 the previous episode keeps its own dated sidecar")
            probs = sidecar_problems(d)
            check(not probs, "S-04 tree after a legacy write is consistent " + "; ".join(probs))
            # A radio show after it: both copies written, and they agree.
            ap._write_audio_static(b"radio-27" * 120, "world", sidecars={".chapters.json": b'{"chapters": [2]}'})
            check((d / "latest.chapters.json").read_bytes() == b'{"chapters": [2]}',
                  "S-04 a chaptered episode writes latest.chapters.json")
            probs = sidecar_problems(d)
            check(not probs, "S-04 tree after a radio write is consistent " + "; ".join(probs))
        finally:
            ap._STATIC_AUDIO_ROOT = old_root


def r14() -> None:
    from briefing.radio_script_generator import attribution_grounding, _ATTRIBUTED_CLAIM_RE
    rows = [{"id": "x", "title": "German Minister Says Russian Aggression Against NATO on New Level",
             "summary": ("German Foreign Minister Johann Wadephul stated on Saturday that Russia's aggression "
                         "towards NATO member countries is on a new level, blaming Moscow for a failed explosive "
                         "drone attack last month on an airport in Leipzig."),
             "consensus_points": [], "divergence_points": []}]

    def verdict(sent: str):
        m = _ATTRIBUTED_CLAIM_RE.match(sent)
        return attribution_grounding(m.group("who"), m.group("clause"), rows)

    spelled = verdict("Wadephul says Russian aggression against N-A-T-O members is at a new level.")
    written = verdict("Wadephul says Russian aggression against NATO members is at a new level.")
    check(spelled is not None and spelled[0] >= 0.6,
          f"S-05 R-14 reads 'N-A-T-O' as 'NATO' (got {spelled})")
    check(spelled == written, "S-05 spelled and written forms score the same")
    subst = verdict("Wadephul says Russian aggression against N-A-T-O is a declaration of war.")
    check(subst is not None and subst[0] < 0.6,
          f"S-05 R-14 still fails a real substitution (got {subst})")


def main() -> int:
    print("On Air sidecar and label parity")
    committed_tree()
    writer()
    r14()
    if failures:
        print(f"\nFAILED {len(failures)}")
        return 1
    print("\nall passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
