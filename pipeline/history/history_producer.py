"""Render a History script into a finished mini audio documentary.

Reuses the On Air machinery wherever it is format-agnostic: synthesis, the
per-voice ffmpeg chain, the duck, the loop, the two-pass loudnorm, the encode,
ID3 chapters and the Podcasting 2.0 sidecar. What is NOT reused is the
timeline and the music placement, which hard-code the radio segment kinds; a
documentary has a different grammar and gets its own.

    python pipeline/history/history_producer.py <slug> [--out DIR]
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from briefing import radio_producer as rp                                    # noqa: E402
from briefing.spoken_text import normalize_for_speech                        # noqa: E402
from briefing.tts_engines import TurnSpec, KokoroEngine, EdgeTtsEngine, \
    synthesize_with_fallback, SAMPLE_RATE                                     # noqa: E402
from history.casting import cast                                             # noqa: E402
from history.script_format import parse_script, validate_script              # noqa: E402

EVENTS = Path(__file__).resolve().parents[2] / "data" / "history" / "events"
SCRIPTS = Path(__file__).resolve().parents[2] / "data" / "history" / "scripts"

# The silence grammar of a documentary. Slower than the radio show
# throughout: a bulletin is racing the clock, a documentary is not, and the
# pauses are where the listener does the work.
GAPS: dict[str, int] = {
    "theme_overlap": 1200,      # the first line starts inside the theme's release
    "line": 320,                # between narrator lines in one segment
    "to_document": 700,         # narrator -> the document voice: a beat to change who is speaking
    "from_document": 900,       # and a longer one coming back, to let the words land
    "scene": 1100,              # between scenes
    "to_perspective": 1500,     # into an account: the longest pause in the programme
    "to_turn": 1800,            # into the reckoning
    "to_close": 1400,
    "outro_overlap": 500,
    "tail": 600,
}
# Segments that get a musical transition in the clear before them.
TRANSITION_BEFORE = ("SCENE", "TURN")
BED_UNDER = ("SCENE", "PERSPECTIVE", "OPEN", "TURN")
NARRATOR, DOCUMENT = "A", "B"       # engine roles; the actual voices come from casting


@dataclass
class Cue:
    idx: int
    kind: str
    seg_idx: int
    speaker: str
    start_ms: int
    end_ms: int
    title: str | None = None


@dataclass
class Timeline:
    cues: list[Cue]
    total_ms: int
    opener_ms: int
    transition_at_ms: list[int] = field(default_factory=list)
    outro_at_ms: int = 0


def build_turns(script) -> list[tuple[TurnSpec, dict]]:
    out: list[tuple[TurnSpec, dict]] = []
    idx = 0
    for si, seg in enumerate(script.segments):
        for line in seg.lines:
            spoken = normalize_for_speech(line.text, script.say)
            if not spoken:
                continue
            role = DOCUMENT if line.speaker == "D" else NARRATOR
            out.append((TurnSpec(idx=idx, role=role, text=spoken),
                        {"kind": seg.kind, "seg_idx": si, "title": seg.title,
                         "speaker": line.speaker}))
            idx += 1
    return out


def _gap(prev: dict | None, cur: dict) -> tuple[int, bool]:
    """(silence before this turn, whether a transition plays in it)."""
    if prev is None:
        return 0, False
    if cur["speaker"] == "D" and prev["speaker"] == "N":
        return GAPS["to_document"], False
    if cur["speaker"] == "N" and prev["speaker"] == "D":
        return GAPS["from_document"], False
    if prev["seg_idx"] == cur["seg_idx"]:
        return GAPS["line"], False
    kind = cur["kind"]
    if kind == "TURN":
        return GAPS["to_turn"], True
    if kind == "PERSPECTIVE":
        return GAPS["to_perspective"], False
    if kind == "CLOSE":
        return GAPS["to_close"], False
    if kind in TRANSITION_BEFORE:
        return GAPS["scene"], True
    return GAPS["scene"], False


def build_timeline(turns, audio, *, opener_ms: int, transition_ms: int, outro_ms: int) -> Timeline:
    cues: list[Cue] = []
    pos = max(0, opener_ms - GAPS["theme_overlap"]) if opener_ms else 300
    transition_at: list[int] = []
    prev: dict | None = None
    for spec, meta in turns:
        seg = audio.get(spec.idx)
        if seg is None:
            continue
        gap, wants_transition = _gap(prev, meta)
        if wants_transition and transition_ms:
            # The transition plays in the clear, so the gap has to hold it.
            gap = max(gap, 300) + transition_ms + 400
            transition_at.append(pos + 300)
        pos += gap
        cues.append(Cue(idx=spec.idx, kind=meta["kind"], seg_idx=meta["seg_idx"],
                        speaker=spec.role, start_ms=pos, end_ms=pos + len(seg),
                        title=meta.get("title")))
        pos = cues[-1].end_ms
        prev = meta
    outro_at = max(0, pos - GAPS["outro_overlap"])
    total = max(pos, outro_at + outro_ms) + GAPS["tail"]
    return Timeline(cues=cues, total_ms=total, opener_ms=opener_ms,
                    transition_at_ms=transition_at, outro_at_ms=outro_at)


def chapters(tl: Timeline, script) -> list[dict]:
    """One chapter per segment that a listener would want to jump to."""
    out: list[dict] = []
    seen: set[int] = set()
    for c in tl.cues:
        if c.seg_idx in seen or c.kind in ("ASIDE", "DOCUMENT", "TITLE"):
            continue
        seen.add(c.seg_idx)
        title = c.title or {"OPEN": "Opening", "TURN": "The disagreement",
                            "CLOSE": "Legacy"}.get(c.kind, c.kind.title())
        out.append({"startTime": round(c.start_ms / 1000, 3), "title": title,
                    "kind": c.kind.lower()})
    if out:
        out[0]["startTime"] = 0.0
    for i, ch in enumerate(out):
        ch["endTime"] = out[i + 1]["startTime"] if i + 1 < len(out) else round(tl.total_ms / 1000, 3)
    return out


def music_bus(tl: Timeline, assets: dict):
    """Theme, transitions in the clear, a ducked bed under the spoken body, outro."""
    bus = rp._silent(tl.total_ms, channels=2)
    used: dict = {}
    duck = rp.duck_envelope(_as_radio_timeline(tl))
    for key, at in (("theme", 0), ("outro", tl.outro_at_ms)):
        seg = assets.get(key)
        if seg is not None:
            bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
            used[key] = at
    tr = assets.get("transition")
    if tr is not None and tl.transition_at_ms:
        for at in tl.transition_at_ms:
            bus = bus.overlay(tr.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
        used["transition"] = list(tl.transition_at_ms)
    bed = assets.get("story_bed")
    if bed is not None:
        # One bed across the spoken body, ducked and darkened under every
        # voice. A documentary sustains attention over fifteen minutes; the
        # per-scene arcs that suit a news bulletin would be restless here.
        first = tl.cues[0].start_ms if tl.cues else 0
        last = tl.cues[-1].end_ms if tl.cues else tl.total_ms
        length = max(2000, last - first)
        base = bed.apply_gain(rp.BED_STORY_GAIN_DB)
        shaped = rp._loop_to(base, length).fade_in(2500).fade_out(3500).set_channels(2)
        dark = rp._loop_to(base.low_pass_filter(2400).low_pass_filter(2400), length)
        dark = dark.fade_in(2500).fade_out(3500).set_channels(2)
        bus = bus.overlay(rp.apply_duck(shaped, duck, first, dark=dark), position=first)
        used["bed"] = (first, last)
    room = assets.get("room")
    if room is not None:
        bus = bus.overlay(rp._loop_to(room, tl.total_ms)
                          .fade_in(rp.ROOM_TONE_FADE).fade_out(rp.ROOM_TONE_FADE)
                          .set_channels(2), position=0)
        used["room"] = True
    return bus, used


def _as_radio_timeline(tl: Timeline):
    """duck_envelope only reads .cues/.total_ms and the cue kinds it treats as
    speech, so a shim keeps that proven code unchanged."""
    shim_cues = [rp.Cue(idx=c.idx, kind="STORY", segment_idx=c.seg_idx, speaker=c.speaker,
                        start_ms=c.start_ms, end_ms=c.end_ms) for c in tl.cues]
    return type("T", (), {"cues": shim_cues, "total_ms": tl.total_ms})()


def produce(slug: str, out_dir: Path) -> dict | None:
    event = yaml.safe_load((EVENTS / f"{slug}.yaml").read_text())
    script = parse_script((SCRIPTS / f"{slug}.txt").read_text(), slug)
    findings = validate_script(script, event)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"  [history] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
    if fails:
        print(f"  [history] {len(fails)} failure(s); not rendering")
        return None

    voices = cast(event)
    print(f"  [history] {event['title']}: {script.words} words, ~{script.minutes:.1f} min")
    print(f"  [history] narrator {voices['narrator']}, documents {voices['document']} ({voices['why']})")

    turns = build_turns(script)
    vmap = {NARRATOR: voices["narrator"], DOCUMENT: voices["document"], "C": voices["narrator"]}
    engines = [KokoroEngine(voices=vmap), EdgeTtsEngine()]
    t0 = time.time()
    res = synthesize_with_fallback([s for s, _ in turns], engines=engines)
    if res is None:
        print("  [history] every engine failed")
        return None
    turns = [(s, m) for s, m in turns if s.idx in res.audio]

    assets = {k: rp._asset(k) for k in ("theme", "transition", "story_bed", "outro", "room")}
    tl = build_timeline(turns, res.audio,
                        opener_ms=len(assets["theme"]) if assets["theme"] else 0,
                        transition_ms=len(assets["transition"]) if assets["transition"] else 0,
                        outro_ms=len(assets["outro"]) if assets["outro"] else 0)
    spoken = sum(c.end_ms - c.start_ms for c in tl.cues)
    print(f"  [history] timeline {tl.total_ms/1000:.1f}s, speech {spoken/1000:.1f}s, "
          f"{script.words/(spoken/60000):.0f} wpm, {len(tl.transition_at_ms)} transitions")

    work = Path(tempfile.mkdtemp(prefix="void-history-"))
    try:
        buses = {r: rp._silent(tl.total_ms) for r in (NARRATOR, DOCUMENT)}
        for c in tl.cues:
            buses[c.speaker] = buses[c.speaker].overlay(res.audio[c.idx], position=c.start_ms)
        # The narrator sits centre; the document voice is offset slightly, so
        # the change of speaker is felt in the room as well as in the timbre.
        n = rp.process_voice_bus(buses[NARRATOR], 0.0, work, "N")
        d = rp.process_voice_bus(buses[DOCUMENT], 0.10, work, "D")
        music, used = music_bus(tl, assets)
        print(f"  [history] music: {used}")
        mix = rp._silent(tl.total_ms, channels=2).overlay(n).overlay(d).overlay(music)
        raw = work / "mix.wav"
        mix.export(str(raw), format="wav")
        mastered = work / "master.wav"
        stats = rp.loudnorm_two_pass(raw, mastered)
        o = stats.get("output") or {}
        print(f"  [history] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} "
              f"LRA={o.get('output_lra')} ({stats.get('normalization_type')})")
        out_dir.mkdir(parents=True, exist_ok=True)
        mp3 = out_dir / f"{slug}.mp3"
        if not rp.encode_mp3(mastered, mp3, "128k", 2):
            print("  [history] encode failed")
            return None
        chs = chapters(tl, script)
        rp.write_id3_chapters(mp3, chs, event["title"], event.get("date_display", ""))
        (out_dir / f"{slug}.chapters.json").write_bytes(rp.chapters_sidecar(chs, event["title"]))
        size = mp3.stat().st_size
        print(f"  [history] {mp3.name}: {tl.total_ms/1000:.0f}s, {size/1e6:.1f} MB, "
              f"{len(chs)} chapters, {time.time()-t0:.0f}s total")
        return {"slug": slug, "path": str(mp3), "seconds": tl.total_ms / 1000,
                "bytes": size, "chapters": chs, "voices": voices}
    finally:
        pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--out", default="/tmp/history")
    a = ap.parse_args()
    return 0 if produce(a.slug, Path(a.out)) else 1


if __name__ == "__main__":
    sys.exit(main())
