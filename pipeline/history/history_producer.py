"""Render a History script into a finished mini audio documentary.

Reuses the On Air machinery wherever it is format-agnostic: synthesis, the
per-voice ffmpeg chain, the duck, the loop, the two-pass loudnorm, the encode,
ID3 chapters and the Podcasting 2.0 sidecar. What is NOT reused is the
timeline and the music placement, which hard-code the radio segment kinds; a
documentary has a different grammar and gets its own.

Two optional layers ride on the directives a script may carry
(docs/proposals/HISTORY-AUDIO-ARCHIVAL.md):

  `# MOOD:`  the mood-aware production: per-mood pace (Kokoro speed), silence
             grammar, duck depth and a History score that is a parameter set
             of the house motif (generate_assets.history_cues). A script with
             no moods renders exactly as before, with the On Air set.
  `# CLIP:`  a real recording in place of a document read, spliced ONLY when
             pipeline/history/clips.py admits it (policy B rights, the CEO's
             signature, provenance, a passing ASR verification, the spoken
             credit, the caps). Otherwise the document read renders, as today.
             A clip plays dry: 900 ms of silence before it, 1,200 after, no bed,
             no room tone, no sting, mono and centred, normalised on its own
             to 3 LU under the narrator.

    python pipeline/history/history_producer.py <slug> [--out DIR] [--only "OPEN,SCENE 2"]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(1, str(Path(__file__).resolve().parents[2]))    # pipeline.history.verify_clip

from briefing import radio_producer as rp                                    # noqa: E402
from briefing.spoken_text import normalize_for_speech                        # noqa: E402
from briefing.tts_engines import TurnSpec, KokoroEngine, EdgeTtsEngine, \
    synthesize_with_fallback, SAMPLE_RATE                                     # noqa: E402
from history.casting import cast                                             # noqa: E402
from history.script_format import parse_script, validate_script, Finding     # noqa: E402
from history import mood as moodmod                                          # noqa: E402
from history import clips as cliplib                                         # noqa: E402

EVENTS = Path(__file__).resolve().parents[2] / "data" / "history" / "events"
SCRIPTS = Path(__file__).resolve().parents[2] / "data" / "history" / "scripts"

# The silence grammar of a documentary. Slower than the radio show
# throughout: a bulletin is racing the clock, a documentary is not, and the
# pauses are where the listener does the work.
GAPS: dict[str, int] = {
    "theme_overlap": 1200,      # the first line starts inside the theme's release
    "line": 420,                # between narrator lines in one segment
    "to_document": 900,         # narrator -> a quoted voice: a beat to change who is speaking
    "from_document": 1400,      # and a longer one coming back, to let the words land
    "scene": 1600,              # between scenes
    "to_perspective": 2200,     # into an account
    "to_turn": 2400,            # into the reckoning
    "to_close": 2000,
    "outro_overlap": 500,
    "tail": 600,
    # A REST is a held pause with the bed alone in it. The duck recovers in
    # 900ms, so across a rest this long the music comes fully up and then
    # steps back under the next line: the "breath" of the programme.
    "rest": 7500,
    "rest_short": 4500,
    # A real recording (HISTORY-AUDIO-ARCHIVAL.md §1): nothing before it but
    # the credit and a silence, nothing after it but a longer one.
    "to_clip": 900,
    "from_clip": 1200,
}
# Segments that get a musical transition in the clear before them.
TRANSITION_BEFORE = ("SCENE", "TURN")
BED_UNDER = ("SCENE", "PERSPECTIVE", "OPEN", "TURN")
NARRATOR, DOC_M, DOC_F = "A", "B", "C"     # engine roles; voices come from casting
CLIP_ROLE = "CLIP"
ROLE_FOR = {"N": NARRATOR, "M": DOC_M, "F": DOC_F}
# Where the bed leaves before a clip and returns after it (§1): out inside the
# 900 ms before, back only once the 1,200 ms after is over.
CLIP_BLOCK_BEFORE_MS = 500
CLIP_BLOCK_AFTER_MS = GAPS["from_clip"]
AMBIENCE_RMS_DBFS = -32.0
DRY_WARN_MS = 4 * 60 * 1000


@dataclass
class Cue:
    idx: int
    kind: str
    seg_idx: int
    speaker: str
    start_ms: int
    end_ms: int
    title: str | None = None
    mood: str | None = None
    clip_id: str | None = None


@dataclass
class Timeline:
    cues: list[Cue]
    total_ms: int
    opener_ms: int
    transition_at_ms: list[int] = field(default_factory=list)
    rest_at_ms: list[tuple[int, int]] = field(default_factory=list)
    outro_at_ms: int = 0
    transition_keys: list[str] = field(default_factory=list)


def build_turns(script, moods: list[str | None] | None = None,
                admitted: dict[int, "cliplib.ClipSlot"] | None = None) -> list[tuple[TurnSpec, dict]]:
    """One turn per spoken line; an admitted clip becomes a turn of its own
    that the synthesiser skips. `moods` sets each turn's Kokoro speed; with
    none, every turn keeps the engine's house speed, as before."""
    out: list[tuple[TurnSpec, dict]] = []
    idx = 0
    admitted = admitted or {}
    for si, seg in enumerate(script.segments):
        m = (moods or [None] * len(script.segments))[si]
        mo = moodmod.MOODS.get(m) if m else None
        slot = admitted.get(si)

        def clip_turn():
            nonlocal idx
            rec = slot.rec or {}
            out.append((TurnSpec(idx=idx, role=NARRATOR, text=""),
                        {"kind": "CLIP", "seg_idx": si, "title": rec.get("title"), "speaker": CLIP_ROLE,
                         "mood": m, "clip": slot, "seg_kind": seg.kind}))
            idx += 1

        if slot is not None and slot.replaces == "none":
            clip_turn()
        clip_done = False
        for line in seg.lines:
            if slot is not None and slot.replaces == "document" and line.speaker in ("M", "F"):
                if not clip_done:
                    clip_turn()
                    clip_done = True
                continue
            spoken = normalize_for_speech(line.text, script.say)
            if not spoken:
                continue
            role = ROLE_FOR.get(line.speaker, NARRATOR)
            speed = None
            if mo is not None:
                speed = mo.narrator_speed if line.speaker == "N" else mo.document_speed
            out.append((TurnSpec(idx=idx, role=role, text=spoken, speed=speed),
                        {"kind": seg.kind, "seg_idx": si, "title": seg.title,
                         "speaker": line.speaker, "mood": m}))
            idx += 1
    return out


def _gap(prev: dict | None, cur: dict) -> tuple[int, bool]:
    """(silence before this turn, whether a transition plays in it)."""
    if prev is None:
        return 0, False
    # A clip is framed by silence and nothing else: never a transition.
    if cur.get("clip") is not None:
        return GAPS["to_clip"], False
    if prev.get("clip") is not None:
        return GAPS["from_clip"], False
    mo = moodmod.MOODS.get(cur.get("mood") or "")
    if cur["speaker"] in ("M", "F") and prev["speaker"] == "N":
        return (mo.to_document_ms if mo else GAPS["to_document"]), False
    if cur["speaker"] == "N" and prev["speaker"] in ("M", "F"):
        pm = moodmod.MOODS.get(prev.get("mood") or "") or mo
        return (pm.from_document_ms if pm else GAPS["from_document"]), False
    if prev["seg_idx"] == cur["seg_idx"]:
        return (mo.line_ms if mo else GAPS["line"]), False
    kind = cur["kind"]
    if prev["kind"] == "REST":
        # The rest has already supplied the silence; do not add another gap
        # on top of it or the programme stalls.
        return GAPS["line"], False
    if kind == "TURN":
        return GAPS["to_turn"], True
    if kind == "PERSPECTIVE":
        return GAPS["to_perspective"], False
    if kind == "CLOSE":
        return GAPS["to_close"], False
    if kind in TRANSITION_BEFORE:
        return GAPS["scene"], True
    return GAPS["scene"], False


def build_timeline(turns, audio, *, opener_ms: int, transition_ms, outro_ms: int,
                   rests: dict[int, str | int] | None = None, break_ms: int = 0) -> Timeline:
    """`rests` maps a segment index to a rest length (a GAPS key, or ms); the
    pause is opened before the first turn of that segment and the break cue
    plays inside it. `transition_ms` is a length, or a function of the
    incoming turn's meta returning (length, cue key); a zero length means the
    mood takes no transition and the gap is left as silence."""
    cues: list[Cue] = []
    pos = max(0, opener_ms - GAPS["theme_overlap"]) if opener_ms else 300
    transition_at: list[int] = []
    transition_keys: list[str] = []
    rest_at: list[tuple[int, int]] = []
    prev: dict | None = None
    seen_segs: set[int] = set()
    for spec, meta in turns:
        seg = audio.get(spec.idx)
        if seg is None:
            continue
        gap, wants_transition = _gap(prev, meta)
        pending_rest = (rests or {}).get(meta["seg_idx"]) if meta["seg_idx"] not in seen_segs else None
        seen_segs.add(meta["seg_idx"])
        if pending_rest and prev is not None:
            length = GAPS[pending_rest] if isinstance(pending_rest, str) else int(pending_rest)
            # The break cue plays inside the rest, starting a beat in, so the
            # silence is heard as music arriving rather than as a dropout.
            if break_ms:
                rest_at.append((pos + 600, min(break_ms, length - 900)))
            pos += length
            gap, wants_transition = GAPS["line"], False
        if callable(transition_ms):
            t_len, t_key = transition_ms(meta) if wants_transition else (0, "")
        else:
            t_len, t_key = transition_ms, "transition"
        if wants_transition and t_len:
            # The transition plays in the clear, so the gap has to hold it.
            gap = max(gap, 300) + t_len + 400
            transition_at.append(pos + 300)
            transition_keys.append(t_key)
        pos += gap
        cues.append(Cue(idx=spec.idx, kind=meta["kind"], seg_idx=meta["seg_idx"],
                        speaker=CLIP_ROLE if meta.get("clip") is not None else spec.role,
                        start_ms=pos, end_ms=pos + len(seg),
                        title=meta.get("title"), mood=meta.get("mood"),
                        clip_id=(meta["clip"].clip_id if meta.get("clip") is not None else None)))
        pos = cues[-1].end_ms
        prev = meta
    outro_at = max(0, pos - GAPS["outro_overlap"])
    total = max(pos, outro_at + outro_ms) + GAPS["tail"]
    tl = Timeline(cues=cues, total_ms=total, opener_ms=opener_ms,
                  transition_at_ms=transition_at, outro_at_ms=outro_at,
                  transition_keys=transition_keys)
    tl.rest_at_ms = rest_at
    return tl


def chapters(tl: Timeline, script) -> list[dict]:
    """One chapter per segment that a listener would want to jump to, and one
    for every real recording, titled with the exhibit's title (§4c.6)."""
    out: list[dict] = []
    seen: set[int] = set()
    for c in tl.cues:
        if c.clip_id is not None:
            out.append({"startTime": round(c.start_ms / 1000, 3), "title": c.title or "Recording",
                        "kind": "segment"})
            continue
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


def clip_blocks(tl: Timeline) -> list[tuple[int, int]]:
    """The windows no music may occupy: each clip, from inside the silence
    before it to the end of the silence after it."""
    return [(c.start_ms - CLIP_BLOCK_BEFORE_MS, c.end_ms + CLIP_BLOCK_AFTER_MS)
            for c in tl.cues if c.clip_id is not None]


def _mute(seg, blocks: list[tuple[int, int]], ramp_ms: int = 250):
    """Silence `seg` inside each block, with raised-cosine ramps OUTSIDE it,
    so the block itself is true zero. numpy, one pass."""
    if not blocks:
        return seg
    import numpy as np
    x = np.array(seg.get_array_of_samples()).astype(np.float32)
    ch, fr = seg.channels, seg.frame_rate
    n = len(x) // ch
    g = np.ones(n, dtype=np.float32)
    ramp = max(1, int(fr * ramp_ms / 1000))
    for a, b in blocks:
        i0, i1 = max(0, int(a * fr / 1000)), min(n, int(b * fr / 1000))
        if i1 <= 0 or i0 >= n:
            continue
        g[i0:i1] = 0.0
        r0 = max(0, i0 - ramp)
        if i0 > r0:
            g[r0:i0] = np.minimum(g[r0:i0], 0.5 + 0.5 * np.cos(np.pi * np.arange(i0 - r0) / (i0 - r0)))
        r1 = min(n, i1 + ramp)
        if r1 > i1:
            g[i1:r1] = np.minimum(g[i1:r1], 0.5 - 0.5 * np.cos(np.pi * np.arange(r1 - i1) / (r1 - i1)))
    if ch > 1:
        g = np.repeat(g, ch)
    return seg._spawn(np.clip(x * g[:len(x)], -32768, 32767).astype(np.int16).tobytes())


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
    brk = assets.get("break")
    if brk is not None and tl.rest_at_ms:
        for at, length in tl.rest_at_ms:
            cue = brk if len(brk) <= length else brk[:length].fade_out(600)
            bus = bus.overlay(cue.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
        used["rest"] = [at for at, _ in tl.rest_at_ms]
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
    # A real recording has no music under it and none running into or out of
    # it. Only a clip-bearing timeline has blocks, so this is a no-op for
    # every episode that carries none.
    blocks = clip_blocks(tl)
    if blocks:
        bus = _mute(bus, blocks)
        used["clip_blocks"] = blocks
    return bus, used


def _as_radio_timeline(tl: Timeline):
    """duck_envelope only reads .cues/.total_ms and the cue kinds it treats as
    speech, so a shim keeps that proven code unchanged."""
    shim_cues = [rp.Cue(idx=c.idx, kind="STORY", segment_idx=c.seg_idx, speaker=c.speaker,
                        start_ms=c.start_ms, end_ms=c.end_ms) for c in tl.cues]
    return type("T", (), {"cues": shim_cues, "total_ms": tl.total_ms})()


# --------------------------------------------------------------------- the mood-aware score

def duck_envelope_floor(tl: Timeline, floor_db: float, step_ms: int = rp.DUCK_STEP_MS) -> list[float]:
    """rp.duck_envelope with the floor as a parameter: the mood sets the depth
    (reckoning -18, procedure -14, dread and grief -10)."""
    steps = max(1, tl.total_ms // step_ms + 1)
    floor = 10 ** (floor_db / 20.0)
    env = [1.0] * steps
    for c in tl.cues:
        a0 = max(0, (c.start_ms - rp.DUCK_ATTACK_MS) // step_ms)
        a1 = max(0, c.start_ms // step_ms)
        r0 = min(steps, c.end_ms // step_ms)
        r1 = min(steps, (c.end_ms + rp.DUCK_RELEASE_MS) // step_ms)
        for i in range(a0, min(a1, steps)):
            t = (i - a0) / max(1, a1 - a0)
            env[i] = min(env[i], 1.0 - t * (1.0 - floor))
        for i in range(a1, r0):
            env[i] = min(env[i], floor)
        for i in range(r0, r1):
            t = (i - r0) / max(1, r1 - r0)
            env[i] = min(env[i], floor + t * (1.0 - floor))
    return env


def history_score(era: str) -> dict:
    """The History cue set as pydub segments at the producer's rate."""
    from pydub import AudioSegment
    from briefing import generate_assets as ga
    import numpy as np
    out = {}
    for k, x in ga.history_cues(era).items():
        pcm = (np.clip(x, -1.0, 1.0) * 32767.0).astype(np.int16)
        out[k] = AudioSegment(pcm.tobytes(), frame_rate=ga.SAMPLE_RATE, sample_width=2, channels=1) \
            .set_frame_rate(SAMPLE_RATE)
    return out


def _subtract(span: tuple[int, int], blocks: list[tuple[int, int]]) -> list[tuple[int, int]]:
    parts = [span]
    for a, b in blocks:
        nxt = []
        for s, e in parts:
            if b <= s or a >= e:
                nxt.append((s, e))
                continue
            if a > s:
                nxt.append((s, a))
            if b < e:
                nxt.append((b, e))
        parts = nxt
    return [(s, e) for s, e in parts if e - s > 200]


def mood_plan(tl: Timeline, dry_seg: list[bool]) -> list[cliplib.Span]:
    """Where every piece of the mood score goes, before anything renders.

    Returned as spans so H-17's timeline half can read the plan itself. Beds
    run per mood, across that mood's cues and into the silence after them
    (so a REST is the bed alone, the breath), ending before a dry segment's
    first word, and never inside a clip's block."""
    plan: list[cliplib.Span] = []
    blocks = clip_blocks(tl)
    cues = tl.cues
    # Beds: runs of consecutive spoken cues sharing one wet mood. A dry cue
    # (testimony, rupture, `# DRY`, a clip) is a run of its own and gets none.
    def wet_mood(c: Cue) -> str | None:
        if c.clip_id is not None or not c.mood or dry_seg[c.seg_idx] or moodmod.MOODS[c.mood].dry:
            return None
        return c.mood

    runs: list[list[Cue]] = []
    for c in cues:
        key = wet_mood(c)
        if runs and key is not None and wet_mood(runs[-1][-1]) == key:
            runs[-1].append(c)
        else:
            runs.append([c])
    for i, run in enumerate(runs):
        first = run[0]
        if wet_mood(first) is None:
            continue
        start = max(0, first.start_ms - 1200)
        nxt = runs[i + 1][0].start_ms if i + 1 < len(runs) else None
        end = (nxt - 300) if nxt is not None else min(tl.total_ms, run[-1].end_ms + 2500)
        for s, e in _subtract((start, end), blocks):
            plan.append(cliplib.Span("bed", s, e, first.mood))
    # Transitions, in the clear, as the timeline placed them.
    for at, key in zip(tl.transition_at_ms, tl.transition_keys):
        plan.append(cliplib.Span("transition", at, at + 4400, key))
    # The change-of-voice sting, in the gap before a document read.
    for a, b in zip(cues, cues[1:]):
        if a.speaker == NARRATOR and b.speaker in (DOC_M, DOC_F) and b.mood \
                and moodmod.MOODS[b.mood].stings and not dry_seg[b.seg_idx]:
            plan.append(cliplib.Span("sting", a.end_ms + 120, a.end_ms + 520, "sting:to_document"))
    # Rupture: withheld, then one entry on the last word of the moment (the
    # end of the quoted read), or after a clip's trailing silence, never on it.
    k = 0
    while k < len(cues):
        if cues[k].mood != "rupture":
            k += 1
            continue
        j = k
        while j + 1 < len(cues) and cues[j + 1].mood == "rupture":
            j += 1
        run = cues[k:j + 1]
        quoted = [c for c in run if c.speaker in (DOC_M, DOC_F, CLIP_ROLE)]
        land = quoted[-1] if quoted else run[-1]
        at = land.end_ms + GAPS["from_clip"] if land.clip_id else max(0, land.end_ms - 600)
        plan.append(cliplib.Span("sting", at, at + 6000, "rupture_entry"))
        k = j + 1
    # After a clip outside a rupture, the music returns on a swell that begins
    # only once the clip's trailing silence is over.
    for c in cues:
        if c.clip_id is not None and c.mood != "rupture":
            at = c.end_ms + GAPS["from_clip"]
            plan.append(cliplib.Span("sting", at, at + 2400, "sting:from_clip"))
    # Room tone everywhere but a clip's block.
    for s, e in _subtract((0, tl.total_ms), blocks):
        plan.append(cliplib.Span("room", s, e, "room"))
    return plan


def mood_music_bus(tl: Timeline, score: dict, plan: list[cliplib.Span], room=None):
    bus = rp._silent(tl.total_ms, channels=2)
    used: dict = {"beds": [], "stings": [], "transitions": []}
    for key, at in (("theme", 0), ("outro", tl.outro_at_ms)):
        seg = score.get(key)
        if seg is not None:
            bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
            used[key] = at
    darks: dict[str, object] = {}
    for sp in plan:
        if sp.kind == "transition":
            seg = score.get(sp.label)
            if seg is not None:
                bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=sp.start_ms)
                used["transitions"].append((sp.start_ms, sp.label))
        elif sp.kind == "sting":
            seg = score.get(sp.label)
            if seg is not None:
                bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=sp.start_ms)
                used["stings"].append((sp.start_ms, sp.label))
        elif sp.kind == "bed":
            base = score.get(f"bed:{sp.label}")
            mo = moodmod.MOODS[sp.label]
            if base is None or mo.duck_db is None:
                continue
            length = sp.end_ms - sp.start_ms
            base = base.apply_gain(rp.BED_STORY_GAIN_DB)
            fin, fout = min(1500, length // 3), min(2000, length // 3)
            shaped = rp._loop_to(base, length).fade_in(fin).fade_out(fout).set_channels(2)
            if sp.label not in darks:
                darks[sp.label] = base.low_pass_filter(2400).low_pass_filter(2400)
            dark = rp._loop_to(darks[sp.label], length).fade_in(fin).fade_out(fout).set_channels(2)
            env = duck_envelope_floor(tl, mo.duck_db)
            bus = bus.overlay(rp.apply_duck(shaped, env, sp.start_ms, dark=dark), position=sp.start_ms)
            used["beds"].append((sp.start_ms, sp.end_ms, sp.label))
        elif sp.kind == "room" and room is not None:
            length = sp.end_ms - sp.start_ms
            fade = min(rp.ROOM_TONE_FADE, length // 3)
            bus = bus.overlay(rp._loop_to(room, length).fade_in(fade).fade_out(fade).set_channels(2),
                              position=sp.start_ms)
            used["room"] = True
    blocks = clip_blocks(tl)
    if blocks:
        bus = _mute(bus, blocks)
        used["clip_blocks"] = blocks
    return bus, used


# --------------------------------------------------------------------- ambience (optional)

def ambience_rows(ledger) -> dict[str, dict]:
    raw = (getattr(ledger, "raw", None) or {}).get("sounds") or []
    return {str(r["id"]): r for r in raw if isinstance(r, dict) and r.get("id")}


def ambience_admissible(row: dict) -> list[str]:
    """A designed sound is admitted only from a CC0 or public-domain source
    with its provenance recorded (§5c). It claims nothing about the event."""
    why = []
    if row.get("kind") != "sound" or row.get("designed") is not True:
        why.append("not a designed sound row (kind: sound, designed: true)")
    if row.get("rights_basis") not in ("cc0-as-stated", "pdm-as-stated", "public-domain-as-stated"):
        why.append(f"rights basis {row.get('rights_basis')!r} is not CC0 or public domain as stated")
    for k in ("title", "uploader", "url", "file", "file_md5", "licence_as_stated", "fetched_at"):
        if not row.get(k):
            why.append(f"lacks {k}")
    return why


def ambience_plan(tl: Timeline, script, ledger) -> list[tuple[cliplib.Span, dict]]:
    """`# AMBIENCE: id=<sound>` under a segment's narration, never under a
    document read, and never within 3 s of a real recording."""
    rows = ambience_rows(ledger) if ledger is not None else {}
    out: list[tuple[cliplib.Span, dict]] = []
    clips_ = [(c.start_ms, c.end_ms) for c in tl.cues if c.clip_id is not None]
    far = [(a - cliplib.DESIGNED_CLEARANCE_MS, b + cliplib.DESIGNED_CLEARANCE_MS) for a, b in clips_]
    for si, seg in enumerate(script.segments):
        for d in seg.directives_of("AMBIENCE"):
            row = rows.get(d.args.get("id", ""))
            if row is None or ambience_admissible(row):
                print(f"  [history] ambience {d.args.get('id')!r} not admitted: "
                      f"{'no ledger row' if row is None else '; '.join(ambience_admissible(row))}")
                continue
            spoken = [c for c in tl.cues if c.seg_idx == si and c.speaker == NARRATOR]
            if not spoken:
                continue
            span = (spoken[0].start_ms - 800, spoken[-1].end_ms + 800)
            reads = [(c.start_ms - 300, c.end_ms + 300) for c in tl.cues
                     if c.seg_idx == si and c.speaker in (DOC_M, DOC_F)]
            for s, e in _subtract(span, far + reads):
                out.append((cliplib.Span("ambience", s, e, row["id"]), row))
    return out


def ambience_bus(tl: Timeline, placed, slug: str, era: str):
    from pydub import AudioSegment
    bus = rp._silent(tl.total_ms, channels=2)
    if not placed:
        return bus
    from pipeline.history import verify_clip as vc
    cache: dict[str, object] = {}
    for sp, row in placed:
        if row["id"] not in cache:
            src = vc.fetch(slug, row)
            cache[row["id"]] = AudioSegment.from_file(str(src)).set_frame_rate(SAMPLE_RATE).set_channels(2)
        seg = cache[row["id"]]
        length = sp.end_ms - sp.start_ms
        piece = rp._loop_to(seg, length, crossfade=400)
        gain = AMBIENCE_RMS_DBFS - piece.dBFS if piece.dBFS > -90 else 0.0
        piece = piece.apply_gain(gain).fade_in(min(1500, length // 3)).fade_out(min(1500, length // 3))
        bus = bus.overlay(piece, position=sp.start_ms)
    return bus


# --------------------------------------------------------------------- clips

def load_clip(slug: str, slot: "cliplib.ClipSlot"):
    """The admitted excerpt as a pydub segment, checked sample for sample
    against the sha256 its verification record holds. Returns None (and the
    document read plays) if the bytes are not the bytes that were verified."""
    from pydub import AudioSegment
    from pipeline.history import verify_clip as vc
    rec, ver = slot.rec or {}, slot.verification or {}
    w = cliplib.window(rec)
    try:
        src = vc.fetch(slug, rec)
        pcm, rate = vc.excerpt_pcm(src, w[0], w[1])
    except (SystemExit, Exception) as e:
        print(f"  [history] clip {slot.clip_id}: cannot load ({e})")
        return None
    sha = hashlib.sha256(pcm).hexdigest()
    if sha != ver.get("excerpt_sha256"):
        print(f"  [history] clip {slot.clip_id}: excerpt sha256 {sha[:12]} is not the verified "
              f"{str(ver.get('excerpt_sha256'))[:12]}; not splicing")
        return None
    seg = AudioSegment(pcm, frame_rate=rate, sample_width=2, channels=1)
    # One treatment, always the same (§1): mono, its own floor left alone, a
    # high-pass for rumble the source never had, 60 ms in, 180 ms out.
    seg = seg.high_pass_filter(60).fade_in(60).fade_out(180)
    return seg.set_frame_rate(SAMPLE_RATE)


def _integrated(seg, work: Path, label: str) -> tuple[float | None, float | None]:
    """(integrated LUFS, true peak dBTP) of a pydub segment, via loudnorm."""
    p = work / f"meas_{label}.wav"
    seg.export(str(p), format="wav")
    m = rp.measure_loudness(p) or {}
    try:
        return float(m.get("input_i")), float(m.get("input_tp"))
    except (TypeError, ValueError):
        return None, None


def clip_bus(tl: Timeline, clip_audio: dict, narrator_bus, work: Path):
    """Every admitted clip, dead centre, at 3 LU under the narrator (§4c.5):
    normalised on its own, over the excerpt only, so the master's loudnorm
    never pumps a 1947 floor up to the programme's level, and capped so it
    never peaks above the narrator."""
    bus = rp._silent(tl.total_ms, channels=2)
    placed = []
    clip_cues = [c for c in tl.cues if c.clip_id is not None]
    if not clip_cues:
        return bus, placed
    speech = rp._silent(0)
    for c in tl.cues:
        if c.speaker == NARRATOR:
            speech += narrator_bus[c.start_ms:c.end_ms].set_channels(1)
    n_i, n_tp = _integrated(speech, work, "narrator")
    for c in clip_cues:
        seg = clip_audio[c.idx]
        c_i, c_tp = _integrated(seg, work, f"clip{c.idx}")
        gain = 0.0
        if n_i is not None and c_i is not None:
            gain = (n_i - 3.0) - c_i
            if n_tp is not None and c_tp is not None:
                gain = min(gain, n_tp - c_tp)
        bus = bus.overlay(seg.apply_gain(gain).set_channels(2), position=c.start_ms)
        placed.append({"id": c.clip_id, "start_ms": c.start_ms, "end_ms": c.end_ms,
                       "gain_db": round(gain, 2), "narrator_lufs": n_i, "clip_lufs": c_i})
    return bus, placed


# --------------------------------------------------------------------- subset (smoke renders)

def subset(script, selectors: list[str]):
    """Keep the named segments and the DOCUMENT and ASIDE segments that belong
    to each (up to the next structural segment). For listening tests only:
    a subset is never published."""
    structural = ("OPEN", "TITLE", "SCENE", "TURN", "PERSPECTIVE", "CLOSE", "REST")
    keep: list[int] = []
    for sel in selectors:
        sel = sel.strip().upper()
        for i, seg in enumerate(script.segments):
            label = f"{seg.kind} {seg.title or ''}".upper()
            # "SCENE 2" is the second SCENE segment.
            if seg.kind == "SCENE" and sel.startswith("SCENE "):
                n = sum(1 for s in script.segments[:i + 1] if s.kind == "SCENE")
                hit = sel == f"SCENE {n}"
            else:
                hit = sel == seg.kind or sel == label.strip()
            if not hit:
                continue
            keep.append(i)
            j = i + 1
            while j < len(script.segments) and script.segments[j].kind not in structural:
                keep.append(j)
                j += 1
    out = copy.copy(script)
    out.segments = [script.segments[i] for i in sorted(set(keep))]
    return out


# --------------------------------------------------------------------- produce

def _load_ledger(slug: str):
    try:
        from pipeline.history.ledger import load_ledger
    except ImportError:  # pragma: no cover
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
        from pipeline.history.ledger import load_ledger
    try:
        return load_ledger(slug)
    except FileNotFoundError:
        return None


def produce(slug: str, out_dir: Path, *, only: list[str] | None = None,
            promo: bool = True) -> dict | None:
    event = yaml.safe_load((EVENTS / f"{slug}.yaml").read_text())
    script = parse_script((SCRIPTS / f"{slug}.txt").read_text(), slug)
    findings = validate_script(script, event)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"  [history] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
    if fails:
        print(f"  [history] {len(fails)} failure(s); not rendering")
        return None

    # Archival clips: admitted or not, before anything is synthesised.
    ledger = None
    admitted: dict[int, cliplib.ClipSlot] = {}
    if any(seg.directives_of("CLIP") for seg in script.segments):
        ledger = _load_ledger(slug)
        slots, cfind = cliplib.evaluate(script, ledger, slug)
        for f in cfind:
            print(f"  [history] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
        if any(f.level == "fail" for f in cfind):
            print("  [history] a clip gate failed; not rendering")
            return None
        for s in slots:
            print(f"  [history] clip {s.clip_id}: {'ADMITTED' if s.admitted else 'not admitted, the document read plays'}")
            if s.admitted:
                admitted[s.seg_idx] = s
    if only:
        full = script
        script = subset(script, only)
        idx_map = {id(seg): i for i, seg in enumerate(script.segments)}
        admitted = {idx_map[id(full.segments[k])]: v for k, v in admitted.items()
                    if id(full.segments[k]) in idx_map}
        for k, v in admitted.items():
            v.seg_idx = k
        print(f"  [history] SUBSET {only}: {len(script.segments)} segments (a listening test, never published)")

    mood_mode = moodmod.has_moods(script) and os.environ.get("VOID_HISTORY_MOODS", "1") != "0"
    moods = moodmod.segment_moods(script) if mood_mode else None
    dry_seg = moodmod.dry_segments(script) if mood_mode else [False] * len(script.segments)
    if mood_mode and moodmod.unknown_moods(script):
        print(f"  [history] unknown moods ignored: {moodmod.unknown_moods(script)}")

    voices = cast(event)
    print(f"  [history] {event['title']}: {script.words} words, ~{script.minutes:.1f} min"
          f"{', mood-aware' if mood_mode else ''}")
    print(f"  [history] narrator {voices['narrator']}, quotes {voices['document_m']}/"
          f"{voices['document_f']} ({voices['why']})")

    turns = build_turns(script, moods, admitted)
    clip_turns = [(s, m) for s, m in turns if m.get("clip") is not None]
    speak = [s for s, m in turns if m.get("clip") is None]
    vmap = {NARRATOR: voices["narrator"], DOC_M: voices["document_m"], DOC_F: voices["document_f"]}
    engines = [KokoroEngine(voices=vmap), EdgeTtsEngine()]
    t0 = time.time()
    res = synthesize_with_fallback(speak, engines=engines)
    if res is None:
        print("  [history] every engine failed")
        return None
    audio = dict(res.audio)
    clip_audio: dict[int, object] = {}
    for spec, meta in clip_turns:
        seg = load_clip(slug, meta["clip"])
        if seg is None:
            if cliplib.is_signed(meta["clip"].rec or {}):
                print("  [history] a SIGNED clip could not be spliced as verified; not rendering")
                return None
            continue
        clip_audio[spec.idx] = seg
        audio[spec.idx] = seg
    turns = [(s, m) for s, m in turns if s.idx in audio]

    era = str(event.get("era") or "modern")
    if mood_mode:
        score = history_score(era)
        room = rp._asset("room")
        assets = {"theme": score.get("theme"), "outro": score.get("outro")}

        def transition_for(meta: dict) -> tuple[int, str]:
            key = f"transition:{meta.get('mood')}"
            seg = score.get(key)
            if seg is None or dry_seg[meta["seg_idx"]]:
                return 0, ""
            return len(seg), key
        transition_ms = transition_for
        break_ms = 0
    else:
        assets = {k: rp._asset(k) for k in ("theme", "transition", "break", "story_bed", "outro", "room")}
        transition_ms = len(assets["transition"]) if assets["transition"] else 0
        break_ms = len(assets["break"]) if assets["break"] else 0
    # A REST segment has no words, so it never becomes a turn. Its length is
    # opened before whatever segment follows it; with moods, the length is the
    # mood of the segment it lets land.
    rests: dict[int, str | int] = {}
    for i, seg in enumerate(script.segments):
        if seg.kind == "REST":
            short = (seg.title or "").strip().lower() == "short"
            key = "rest_short" if short else "rest"
            prev_m = next((moods[j] for j in range(i - 1, -1, -1)
                           if script.segments[j].kind != "REST"), None) if moods else None
            nxt = next((j for j in range(i + 1, len(script.segments))
                        if script.segments[j].kind != "REST"), None)
            if nxt is not None:
                if prev_m:
                    mo = moodmod.MOODS[prev_m]
                    rests[nxt] = mo.rest_short_ms if short else mo.rest_ms
                else:
                    rests[nxt] = key
    tl = build_timeline(turns, audio,
                        opener_ms=len(assets["theme"]) if assets.get("theme") else 0,
                        transition_ms=transition_ms,
                        outro_ms=len(assets["outro"]) if assets.get("outro") else 0,
                        rests=rests, break_ms=break_ms)
    spoken = sum(c.end_ms - c.start_ms for c in tl.cues if c.clip_id is None)
    print(f"  [history] timeline {tl.total_ms/1000:.1f}s, speech {spoken/1000:.1f}s, "
          f"{script.words/(max(1, spoken)/60000):.0f} wpm, {len(tl.transition_at_ms)} transitions, "
          f"{len(tl.rest_at_ms)} rests, {len(clip_audio)} clip(s)")

    # H-17, first half: the plan, before anything is mixed.
    clip_spans = [cliplib.Span("clip", c.start_ms, c.end_ms, c.clip_id or "") for c in tl.cues
                  if c.clip_id is not None]
    plan = mood_plan(tl, dry_seg) if mood_mode else []
    amb = ambience_plan(tl, script, ledger) if (mood_mode and ledger is not None) else []
    h17 = cliplib.timeline_findings(clip_spans, plan + [sp for sp, _ in amb])
    for f in h17:
        print(f"  [history] {f.id} {f.level} [{f.segment}] {f.detail}")
    if h17:
        print("  [history] designed or musical sound scheduled under a real voice; not rendering")
        return None
    if mood_mode:
        # A script that never goes dry for four minutes wears the ear out.
        last_dry, worst = 0, 0
        for c in tl.cues:
            if dry_seg[c.seg_idx] or c.clip_id is not None:
                worst, last_dry = max(worst, c.start_ms - last_dry), c.end_ms
        worst = max(worst, tl.total_ms - last_dry)
        if worst > DRY_WARN_MS:
            print(f"  [history] warn: {worst/60000:.1f} min without a dry segment")

    work = Path(tempfile.mkdtemp(prefix="void-history-"))
    buses = {r: rp._silent(tl.total_ms) for r in (NARRATOR, DOC_M, DOC_F)}
    for c in tl.cues:
        if c.clip_id is None:
            buses[c.speaker] = buses[c.speaker].overlay(audio[c.idx], position=c.start_ms)
    # The narrator sits centre; the document voice is offset slightly, so
    # the change of speaker is felt in the room as well as in the timbre.
    n = rp.process_voice_bus(buses[NARRATOR], 0.0, work, "N")
    dm = rp.process_voice_bus(buses[DOC_M], 0.10, work, "M")
    df = rp.process_voice_bus(buses[DOC_F], -0.10, work, "F")
    if mood_mode:
        music, used = mood_music_bus(tl, score, plan, room=room)
    else:
        music, used = music_bus(tl, assets)
    print(f"  [history] music: {used}")
    ambience = ambience_bus(tl, amb, slug, era) if amb else None
    cbus, clips_placed = clip_bus(tl, clip_audio, n, work)
    # H-17, second half: the rendered buses, measured under every clip.
    h17b = cliplib.bus_findings(clip_spans, {"music": music, "ambience": ambience})
    for f in h17b:
        print(f"  [history] {f.id} {f.level} [{f.segment}] {f.detail}")
    if h17b:
        print("  [history] a bus is audible under a real voice; not rendering")
        return None
    mix = rp._silent(tl.total_ms, channels=2).overlay(n).overlay(dm).overlay(df).overlay(music).overlay(cbus)
    if ambience is not None:
        mix = mix.overlay(ambience)
    promo_info = None
    if promo:
        # House promo under the outro, after the close ends on its particular.
        # The length does not change, so H-07's gate is untouched.
        from briefing import house_promos
        promo_key = f"history:{slug}"
        mix, promo_info = house_promos.post_roll(
            mix, outro_at_ms=tl.outro_at_ms, last_word_ms=tl.cues[-1].end_ms if tl.cues else None,
            plays_in="history", key=promo_key, work=work)
    raw = work / "mix.wav"
    mix.export(str(raw), format="wav")
    mastered = work / "master.wav"
    stats = rp.loudnorm_two_pass(raw, mastered)
    if clips_placed:
        # The master's gain is one linear number the premix cannot know in
        # advance, so the clip is set 3 LU under the narrator, the programme is
        # mastered, and then the clip is measured where the listener hears it
        # and trimmed once toward -19 LUFS (§4c.5). A clip is a small share of
        # the programme, so the second master's gain barely moves.
        target = rp.LOUDNESS_I - 3.0
        deltas = [target - i for i, _ in (_clip_master_lufs(mastered, p, work) for p in clips_placed)
                  if i is not None]
        if deltas and max(abs(d) for d in deltas) > 0.5:
            trim = sum(deltas) / len(deltas)
            print(f"  [history] clip loudness trim {trim:+.2f} dB toward {target:.0f} LUFS; remastering")
            mix = rp._silent(tl.total_ms, channels=2).overlay(n).overlay(dm).overlay(df) \
                .overlay(music).overlay(cbus.apply_gain(trim))
            if ambience is not None:
                mix = mix.overlay(ambience)
            if promo_info:
                from briefing import house_promos
                mix, promo_info = house_promos.post_roll(
                    mix, outro_at_ms=tl.outro_at_ms, last_word_ms=tl.cues[-1].end_ms if tl.cues else None,
                    plays_in="history", key=f"history:{slug}", work=work)
            for p in clips_placed:
                p["gain_db"] = round(p["gain_db"] + trim, 2)
            mix.export(str(raw), format="wav")
            stats = rp.loudnorm_two_pass(raw, mastered)
    o = stats.get("output") or {}
    print(f"  [history] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} "
          f"LRA={o.get('output_lra')} ({stats.get('normalization_type')})")
    chs = chapters(tl, script)
    _report_loudness(mastered, tl, chs, clips_placed, work)
    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / f"{slug}.mp3"
    if not rp.encode_mp3(mastered, mp3, "128k", 2):
        print("  [history] encode failed")
        return None
    if promo_info:
        from briefing import house_promos
        promo_key = f"history:{slug}"
        # "segment" is the only kind the history rail draws without a
        # radio badge; the title says what it is.
        chs = house_promos.append_promo_chapter(
            chs, house_promos.select("history", promo_key), promo_info["at_ms"], tl.total_ms,
            kind="segment", title=house_promos.HISTORY_PROMO_CHAPTER_TITLE)
        (out_dir / f"{slug}.promo.json").write_text(json.dumps({
            "id": promo_info["id"], "sha": promo_info["sha"], "voice": promo_info["voice"],
            "startTime": round(promo_info["at_ms"] / 1000.0, 3)}, indent=1) + "\n")
    if clips_placed:
        # The manifest records what it carries (§4c.7), so the served file can
        # be checked against its row.
        (out_dir / f"{slug}.clips.json").write_text(json.dumps([{
            "id": p["id"], "startTime": round(p["start_ms"] / 1000, 3),
            "endTime": round(p["end_ms"] / 1000, 3),
            "sha256": next((s.verification or {}).get("excerpt_sha256") for s in admitted.values()
                           if s.clip_id == p["id"])} for p in clips_placed], indent=1) + "\n")
    rp.write_id3_chapters(mp3, chs, event["title"], event.get("date_display", ""))
    (out_dir / f"{slug}.chapters.json").write_bytes(rp.chapters_sidecar(chs, event["title"]))
    size = mp3.stat().st_size
    print(f"  [history] {mp3.name}: {tl.total_ms/1000:.0f}s, {size/1e6:.1f} MB, "
          f"{len(chs)} chapters, {time.time()-t0:.0f}s total")
    return {"slug": slug, "path": str(mp3), "seconds": tl.total_ms / 1000,
            "bytes": size, "chapters": chs, "voices": voices, "clips": clips_placed,
            "mood_mode": mood_mode, "music": used}


def _clip_master_lufs(mastered: Path, placed: dict, work: Path) -> tuple[float | None, float | None]:
    try:
        from pydub import AudioSegment
        m = AudioSegment.from_wav(str(mastered))
    except Exception:
        return None, None
    return _integrated(m[placed["start_ms"]:placed["end_ms"]], work, f"clipm{placed['start_ms']}")


def _report_loudness(mastered: Path, tl: Timeline, chs: list[dict], clips_placed: list[dict],
                     work: Path) -> None:
    """Moods live in the short-term loudness (§5e): report each chapter
    against its mood's target and each clip against -19 LUFS. Warnings only;
    the integrated master is loudnorm's."""
    try:
        from pydub import AudioSegment
        m = AudioSegment.from_wav(str(mastered))
    except Exception:
        return
    by_start = {}
    for c in tl.cues:
        by_start.setdefault(round(c.start_ms / 1000, 3), c.mood)
    for ch in chs:
        a, b = int(ch["startTime"] * 1000), int(ch["endTime"] * 1000)
        if b - a < 3000:
            continue
        i, _ = _integrated(m[a:b], work, f"ch{a}")
        mood = next((c.mood for c in tl.cues if c.start_ms >= a and c.mood), None)
        target = moodmod.MOODS[mood].lufs_short_term if mood else None
        flag = " WARN" if (i is not None and target is not None and abs(i - target) > 2.0) else ""
        print(f"  [history] chapter {ch['title'][:32]!r:34} {i if i is None else round(i, 1)} LUFS"
              f"{'' if target is None else f' (mood {mood} {target:.0f})'}{flag}")
    for p in clips_placed:
        i, tp = _integrated(m[p["start_ms"]:p["end_ms"]], work, f"clipm{p['start_ms']}")
        flag = " WARN" if (i is not None and abs(i - (rp.LOUDNESS_I - 3.0)) > 1.0) else ""
        print(f"  [history] clip {p['id']} in the master: {i} LUFS, {tp} dBTP "
              f"(target {rp.LOUDNESS_I - 3.0:.0f}){flag}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--out", default="/tmp/history")
    ap.add_argument("--only", default=None,
                    help='a listening test: render only these segments, e.g. "OPEN,SCENE 2"')
    ap.add_argument("--no-promo", action="store_true")
    a = ap.parse_args()
    only = [s for s in (a.only or "").split(",") if s.strip()] or None
    return 0 if produce(a.slug, Path(a.out), only=only, promo=not (a.no_promo or only)) else 1


if __name__ == "__main__":
    sys.exit(main())
