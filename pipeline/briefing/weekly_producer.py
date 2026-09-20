"""Render a weekly rundown into "The Argument", the Sunday audio edition.

Reuses On Air wherever it is format-agnostic, exactly as History does:
synthesis, the voice buses, the ffmpeg chain, the duck, the two-pass loudnorm,
the encode, ID3 chapters and the Podcasting 2.0 sidecar. What it does NOT
reuse is `build_timeline`, which hard-codes the radio segment kinds. A
magazine has a different grammar and gets its own.

TWO DECISIONS DEFINE THE SOUND.

1. THE ARGUMENT IS DRY. Beds run under the OPEN, the CONTENTS, the NUMBERS,
   the EDITORIAL and the CLOSE, and nowhere else. Two people disagreeing over
   a bed is a talk show; naked voice with a held pause between the sides is a
   courtroom. The bed returning for the editorial is therefore also the
   opinion entrance: after eight minutes of dry argument, music coming back is
   unmistakably Void resuming its own voice.

2. THE BENCH IS RATE-MATCHED. am_michael and af_heart measure 160 and 162 wpm
   against the Editor's 172. Two voices at different natural rates give one
   side materially more airtime for the same number of words, which is an
   editorial fairness problem rather than an aesthetic one. Pace is a CASTING
   decision and never a stretch, the rule On Air established.

    python pipeline/briefing/weekly_producer.py --rundown FILE --issue FILE
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from briefing import radio_producer as rp                                    # noqa: E402
from briefing.spoken_text import normalize_for_speech                        # noqa: E402
from briefing.tts_engines import TurnSpec, KokoroEngine, EdgeTtsEngine, \
    synthesize_with_fallback                                                  # noqa: E402
from briefing.weekly_script import parse_script, validate_script, \
    estimated_minutes, TARGET_MINUTES, MUSIC_MINUTES                          # noqa: E402

# Engine roles. The script speaks in E/L/R; the mixer thinks in A/B/C.
EDITOR, LEFT, RIGHT = "A", "B", "C"
ROLE_FOR = {"E": EDITOR, "L": LEFT, "R": RIGHT}

#: The cast, and why. bm_lewis is the gravest voice on the roster at 93 Hz and
#: British, so it is instantly not On Air's anchor; am_michael is On Air's
#: PREVIOUS anchor, retired from that job and therefore free; af_heart is the
#: roster's only A-grade voice. House pace 0.92, against On Air's 0.95: a
#: decision about the programme, which the doctrine permits.
VOICES = {"editor": "bm_lewis", "left": "am_michael", "right": "af_heart"}
SPEED = 0.92

#: Measured Kokoro real-time factor on a four-core runner (CLAUDE.md rev 67).
KOKORO_RTF = 1.4
#: Headroom for a cold or contended machine. The cost of being wrong high is
#: waiting; the cost of being wrong low is losing a finished programme.
DEADLINE_MARGIN = 1.35

WEEKLY_ASSETS = {
    "theme": "weekly_theme.wav",
    "transition": "weekly_transition.wav",
    "break": "weekly_break.wav",
    "bed": "weekly_bed.wav",
    "outro": "weekly_outro.wav",
    # A studio floor is a studio floor: there is no Sunday version of one.
    "room": "radio_room_tone.wav",
}

# The silence grammar. Slower than On Air throughout and slower than History
# at the one place that matters: THE SPINE, the pause between the two columns.
GAPS: dict[str, int] = {
    "theme_overlap": 1400,     # the first line starts inside the theme's release
    "line": 460,               # between lines in one segment
    "segment": 1500,           # between segments
    "to_dateline": 1100,       # into the dateline beat
    "from_dateline": 1500,     # and out of it: the held beat is the device
    "to_topic": 2000,          # into the argument
    "spine": 2400,             # THE SPINE: between the left column and the right
    "to_turn": 2200,           # into the reckoning
    "to_numbers": 1400,
    "to_editorial": 1800,
    "to_close": 1900,
    "outro_overlap": 500,
    "tail": 700,
    "rest": 6500,              # a held pause with the bed alone in it
}

#: A musical seam plays in the clear before these.
TRANSITION_BEFORE = ("TOPIC", "SECOND")
#: The break plays before the turn from argument to measurement — the one seam
#: in the running order that changes the KIND of thing being said.
BREAK_BEFORE = ("NUMBERS",)
#: Decision 1, in one line.
BED_UNDER = ("OPEN", "CONTENTS", "NUMBERS", "EDITORIAL", "CLOSE")

CHAPTER_TITLES = {
    "OPEN": "The week", "CONTENTS": "Inside this week", "COVER": "The cover",
    "TOPIC": "The Argument", "SECOND": "Second feature",
    "DEPARTMENT": "Department", "NUMBERS": "The Week in Bias",
    "EDITORIAL": "Opinion", "CLOSE": "The open question",
}
#: Segments a listener would not jump to: they are beats inside a movement.
NOT_A_CHAPTER = ("DATELINE", "LEFT", "RIGHT", "TURN", "REST")


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
    opener_ms: int = 0
    transition_at_ms: list[int] = field(default_factory=list)
    break_at_ms: list[int] = field(default_factory=list)
    rest_at_ms: list[int] = field(default_factory=list)
    outro_at_ms: int = 0

    def bed_spans(self) -> list[tuple[int, int]]:
        """Contiguous runs of bedded segments, merged across adjacent cues.

        Computed from the CUES rather than from the script, so a segment whose
        synthesis failed cannot leave a bed playing under silence.
        """
        spans: list[list[int]] = []
        for c in self.cues:
            if c.kind not in BED_UNDER:
                continue
            if spans and c.start_ms - spans[-1][1] < 4000:
                spans[-1][1] = c.end_ms
            else:
                spans.append([c.start_ms, c.end_ms])
        return [(a, b) for a, b in spans]


def build_turns(script) -> list[tuple[TurnSpec, dict]]:
    out: list[tuple[TurnSpec, dict]] = []
    idx = 0
    for si, seg in enumerate(script.segments):
        for line in seg.lines:
            spoken = normalize_for_speech(line.text, script.say)
            if not spoken:
                continue
            out.append((TurnSpec(idx=idx, role=ROLE_FOR.get(line.speaker, EDITOR),
                                 text=spoken, speed=SPEED),
                        {"kind": seg.kind, "seg_idx": si, "title": seg.title,
                         "speaker": line.speaker}))
            idx += 1
    return out


def _gap(prev: dict | None, cur: dict) -> tuple[int, bool, bool]:
    """(silence before this turn, transition plays in it, break plays in it)."""
    if prev is None:
        return 0, False, False
    if prev["seg_idx"] == cur["seg_idx"]:
        return GAPS["line"], False, False
    kind, pkind = cur["kind"], prev["kind"]
    # The dateline beat, and the held pause coming out of it. This is signature
    # device two: "Tuesday. Thirteen sources." then a beat, inside the feature,
    # so the listener hears the week's shape rather than being told it.
    if kind == "DATELINE":
        return GAPS["to_dateline"], False, False
    if pkind == "DATELINE":
        return GAPS["from_dateline"], False, False
    # THE SPINE. Device one: the show's own REST, and the reason the argument
    # is dry. Nothing plays in it.
    if kind == "RIGHT" and pkind == "LEFT":
        return GAPS["spine"], False, False
    if kind == "TOPIC":
        return GAPS["to_topic"], True, False
    if kind == "TURN":
        return GAPS["to_turn"], False, False
    if kind == "NUMBERS":
        return GAPS["to_numbers"], False, True
    if kind == "EDITORIAL":
        return GAPS["to_editorial"], False, False
    if kind == "CLOSE":
        return GAPS["to_close"], False, False
    if kind in TRANSITION_BEFORE:
        return GAPS["segment"], True, False
    return GAPS["segment"], False, False


def build_timeline(turns, audio, *, opener_ms: int, transition_ms: int,
                   break_ms: int, outro_ms: int,
                   rests: dict[int, str] | None = None) -> Timeline:
    """Reserve room for every cue BEFORE placing a word.

    On Air's lesson: a transition that is not reserved for plays under the
    first sentence of the thing it introduces, which is the difference between
    music woven into a programme and music stitched onto one.
    """
    cues: list[Cue] = []
    pos = max(0, opener_ms - GAPS["theme_overlap"]) if opener_ms else 300
    transition_at: list[int] = []
    break_at: list[int] = []
    rest_at: list[int] = []
    prev: dict | None = None
    seen: set[int] = set()

    for spec, meta in turns:
        seg = audio.get(spec.idx)
        if seg is None:
            continue
        gap, wants_transition, wants_break = _gap(prev, meta)
        if meta["seg_idx"] not in seen and (rests or {}).get(meta["seg_idx"]):
            seen.add(meta["seg_idx"])
            if prev is not None:
                rest_at.append(pos)
                pos += GAPS["rest"]
                gap, wants_transition, wants_break = GAPS["line"], False, False
        seen.add(meta["seg_idx"])
        if wants_break and break_ms:
            gap = max(gap, 400) + break_ms + 600
            break_at.append(pos + 400)
        elif wants_transition and transition_ms:
            gap = max(gap, 300) + transition_ms + 500
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
                    transition_at_ms=transition_at, break_at_ms=break_at,
                    rest_at_ms=rest_at, outro_at_ms=outro_at)


def chapters(tl: Timeline) -> list[dict]:
    """One chapter per movement a listener would actually jump to.

    `kind` is lower-cased and passed straight through: `chapters.ts` renders
    any kind and already guards an empty label, which is what makes a new
    format's chapter rail work with no frontend change.
    """
    out: list[dict] = []
    seen: set[int] = set()
    for c in tl.cues:
        if c.seg_idx in seen or c.kind in NOT_A_CHAPTER:
            continue
        seen.add(c.seg_idx)
        title = c.title or CHAPTER_TITLES.get(c.kind, c.kind.title())
        out.append({"startTime": round(c.start_ms / 1000, 3), "title": title,
                    "kind": c.kind.lower()})
    if out:
        out[0]["startTime"] = 0.0
    for i, ch in enumerate(out):
        ch["endTime"] = out[i + 1]["startTime"] if i + 1 < len(out) \
            else round(tl.total_ms / 1000, 3)
    return out


def _as_radio_timeline(tl: Timeline):
    """`duck_envelope` reads only .cues/.total_ms and the kinds it treats as
    speech, so a shim keeps that proven code unchanged. Same seam History
    uses, and the same reason: this is the exact boundary between what is
    reusable and what is this format's own."""
    shim = [rp.Cue(idx=c.idx, kind="STORY", segment_idx=c.seg_idx,
                   speaker=c.speaker, start_ms=c.start_ms, end_ms=c.end_ms)
            for c in tl.cues]
    return type("T", (), {"cues": shim, "total_ms": tl.total_ms})()


def _asset(key: str):
    seg = rp._load_asset(WEEKLY_ASSETS[key])
    if seg is not None:
        seg = seg.set_frame_rate(rp.SAMPLE_RATE).set_sample_width(2)
    return seg


def spectrum_cue(tl: Timeline, stats: dict, ms: int):
    """Signature device three: the week's own scorecard, sonified.

    Pitch carries the mean lean (the root D at centre, a fifth either way at
    the extremes); detuning width carries the spread, so a
    balanced-but-CONTESTED week beats audibly while a genuine consensus sits
    still. That is the distinction the Sigil's divergence fan draws on the
    page, in the one medium where a fan cannot be drawn.

    Returns None when numpy is absent or the issue carries no stats, because a
    missing decoration must never cost the programme.
    """
    try:
        import numpy as np
        from briefing.generate_assets import weekly_spectrum
        from pydub import AudioSegment
    except Exception:
        return None
    if not stats:
        return None
    buf = weekly_spectrum(float(stats.get("avg_lean") or 50.0),
                          float(stats.get("lean_std") or 0.0),
                          duration_s=max(4.0, ms / 1000.0))
    pcm = (np.clip(buf, -1.0, 1.0) * 32767.0).astype("<i2").tobytes()
    return AudioSegment(data=pcm, sample_width=2,
                        frame_rate=rp.SAMPLE_RATE, channels=1)


def music_bus(tl: Timeline, assets: dict, stats: dict | None = None):
    """Theme, seams in the clear, beds only where the format allows one."""
    bus = rp._silent(tl.total_ms, channels=2)
    used: dict = {}
    duck = rp.duck_envelope(_as_radio_timeline(tl))

    for key, at in (("theme", 0), ("outro", tl.outro_at_ms)):
        seg = assets.get(key)
        if seg is not None:
            bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
            used[key] = at

    for key, positions in (("transition", tl.transition_at_ms),
                           ("break", tl.break_at_ms)):
        seg = assets.get(key)
        if seg is not None and positions:
            for at in positions:
                bus = bus.overlay(seg.apply_gain(rp.CUE_GAIN_DB).set_channels(2), position=at)
            used[key] = list(positions)

    bed = assets.get("bed")
    if bed is not None:
        spans = tl.bed_spans()
        # A rest is a held pause with the bed ALONE in it, so it belongs to the
        # span it interrupts rather than ending one.
        base = bed.apply_gain(rp.BED_STORY_GAIN_DB)
        for start, end in spans:
            length = max(2000, end - start)
            shaped = rp._loop_to(base, length).fade_in(2500).fade_out(3500).set_channels(2)
            dark = rp._loop_to(base.low_pass_filter(2400).low_pass_filter(2400), length)
            dark = dark.fade_in(2500).fade_out(3500).set_channels(2)
            bus = bus.overlay(rp.apply_duck(shaped, duck, start, dark=dark), position=start)
        used["bed"] = spans

    # The spectrum sits under the NUMBERS read, at -40 dBFS, well beneath it.
    nums = [c for c in tl.cues if c.kind == "NUMBERS"]
    if nums and stats:
        start, end = nums[0].start_ms, nums[-1].end_ms
        cue = spectrum_cue(tl, stats, end - start + 1500)
        if cue is not None:
            bus = bus.overlay(cue.set_channels(2).fade_in(1500).fade_out(2500),
                              position=max(0, start - 800))
            used["spectrum"] = (start, end)

    room = assets.get("room")
    if room is not None:
        bus = bus.overlay(rp._loop_to(room, tl.total_ms)
                          .fade_in(rp.ROOM_TONE_FADE).fade_out(rp.ROOM_TONE_FADE)
                          .set_channels(2), position=0)
        used["room"] = True
    return bus, used


# Pages allows 25 MiB per file; History's largest episode is 13.9 MB. Twenty
# minutes at 128k stereo is about 19 MB, so the weekly gets its own cap with
# headroom — and On Air's rule, which is that the editorial is NEVER dropped.
# The old weekly cap was 12 MB, against which the last issue shipped at 93.7%
# while running 40% UNDER its own word target: one good week from silently
# amputating the editorial.
SIZE_CAP_BYTES = 22 * 1024 * 1024
BITRATE_LADDER = (("128k", 2), ("96k", 2), ("96k", 1), ("64k", 1))


def produce(script_text: str, issue: dict, out_dir: Path,
            stem: str = "weekly") -> dict | None:
    script = parse_script(script_text, issue.get("edition") or "world")
    findings = validate_script(script, issue, VOICES)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"  [weekly-audio] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
    if fails:
        print(f"  [weekly-audio] {len(fails)} failure(s); not rendering")
        return None

    minutes, wpm = estimated_minutes(script, VOICES)
    print(f"  [weekly-audio] {script.words} words, ~{minutes:.1f} min at {wpm:.0f} wpm")
    print(f"  [weekly-audio] Editor {VOICES['editor']}, bench {VOICES['left']} vs "
          f"{VOICES['right']} (rate-matched), pace {SPEED}")

    turns = build_turns(script)
    vmap = {EDITOR: VOICES["editor"], LEFT: VOICES["left"], RIGHT: VOICES["right"]}
    t0 = time.time()

    # THE DEADLINE HAS TO BE SIZED TO THE BAND, and the default is not.
    # `synthesize_with_fallback` defaults to 1500 s, which was chosen for On
    # Air (10-12 min) and fits History (8-15 min) comfortably. This programme
    # runs 18-22 minutes: at the measured Kokoro rtf of 1.4 on a four-core
    # runner, 22 minutes of programme is about 20.6 minutes of speech and
    # therefore ~1,730 s of synthesis. Even the 19-minute launch issue lands at
    # ~1,478 s, a 1.5% margin against a deadline it would cross on any slower
    # runner. Derived from the band rather than guessed, with a third again for
    # a cold or contended machine.
    speech_s = (max(TARGET_MINUTES) - MUSIC_MINUTES) * 60.0
    deadline = round(speech_s * KOKORO_RTF * DEADLINE_MARGIN)
    print(f"  [weekly-audio] synthesis deadline {deadline}s "
          f"({max(TARGET_MINUTES):.0f} min band at rtf {KOKORO_RTF})")
    res = synthesize_with_fallback([s for s, _ in turns],
                                   engines=[KokoroEngine(voices=vmap), EdgeTtsEngine()],
                                   deadline_s=deadline)
    if res is None:
        print("  [weekly-audio] every engine failed")
        return None
    turns = [(s, m) for s, m in turns if s.idx in res.audio]

    assets = {k: _asset(k) for k in WEEKLY_ASSETS}
    rests = {}
    for i, seg in enumerate(script.segments):
        if seg.kind == "REST":
            nxt = next((j for j in range(i + 1, len(script.segments))
                        if script.segments[j].kind != "REST"), None)
            if nxt is not None:
                rests[nxt] = "rest"

    tl = build_timeline(
        turns, res.audio,
        opener_ms=len(assets["theme"]) if assets["theme"] else 0,
        transition_ms=len(assets["transition"]) if assets["transition"] else 0,
        break_ms=len(assets["break"]) if assets["break"] else 0,
        outro_ms=len(assets["outro"]) if assets["outro"] else 0,
        rests=rests,
    )
    spoken = sum(c.end_ms - c.start_ms for c in tl.cues)
    print(f"  [weekly-audio] timeline {tl.total_ms/1000:.1f}s, speech {spoken/1000:.1f}s, "
          f"{len(tl.transition_at_ms)} seams, {len(tl.break_at_ms)} breaks, "
          f"{len(tl.rest_at_ms)} rests, bed under {len(tl.bed_spans())} span(s)")

    work = Path(tempfile.mkdtemp(prefix="void-weekly-"))
    buses = {r: rp._silent(tl.total_ms) for r in (EDITOR, LEFT, RIGHT)}
    for c in tl.cues:
        buses[c.speaker] = buses[c.speaker].overlay(res.audio[c.idx], position=c.start_ms)
    # The Editor sits centre. The bench is placed left and right in the stereo
    # field, because the one thing a listener must never lose track of is WHICH
    # SIDE IS SPEAKING, and the room says it before the timbre does.
    e = rp.process_voice_bus(buses[EDITOR], 0.0, work, "E")
    l = rp.process_voice_bus(buses[LEFT], -0.16, work, "L")
    r = rp.process_voice_bus(buses[RIGHT], 0.16, work, "R")
    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})
    music, used = music_bus(tl, assets, stats)
    print(f"  [weekly-audio] music: { {k: v for k, v in used.items() if k != 'bed'} }")

    mix = rp._silent(tl.total_ms, channels=2).overlay(e).overlay(l).overlay(r).overlay(music)
    raw = work / "mix.wav"
    mix.export(str(raw), format="wav")
    mastered = work / "master.wav"
    st = rp.loudnorm_two_pass(raw, mastered)
    o = st.get("output") or {}
    print(f"  [weekly-audio] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} "
          f"LRA={o.get('output_lra')} ({st.get('normalization_type')})")

    out_dir.mkdir(parents=True, exist_ok=True)
    mp3 = out_dir / f"{stem}.mp3"
    for bitrate, channels in BITRATE_LADDER:
        if not rp.encode_mp3(mastered, mp3, bitrate, channels):
            print("  [weekly-audio] encode failed")
            return None
        if mp3.stat().st_size <= SIZE_CAP_BYTES:
            break
        print(f"  [weekly-audio] {mp3.stat().st_size/1e6:.1f} MB over cap at "
              f"{bitrate}/{channels}ch; stepping down")
    else:
        # Every rung exhausted. The programme ships long rather than short: the
        # editorial is never dropped, which is the rule the old 12 MB ladder
        # broke silently.
        print("  [weekly-audio] still over cap at the lowest rung; shipping whole")

    chs = chapters(tl)
    title = issue.get("cover_headline") or "Void Weekly"
    rp.write_id3_chapters(mp3, chs, title, issue.get("week_start") or "")
    (out_dir / f"{stem}.chapters.json").write_bytes(rp.chapters_sidecar(chs, title))
    size = mp3.stat().st_size
    print(f"  [weekly-audio] {mp3.name}: {tl.total_ms/1000:.0f}s, {size/1e6:.1f} MB, "
          f"{len(chs)} chapters, {time.time()-t0:.0f}s total")
    return {"path": str(mp3), "seconds": tl.total_ms / 1000, "bytes": size,
            "chapters": chs, "voices": dict(VOICES), "words": script.words,
            "sidecar": str(out_dir / f"{stem}.chapters.json")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rundown", required=True, help="the script file")
    ap.add_argument("--issue", required=True, help="the published weekly JSON")
    ap.add_argument("--out", default="/tmp/weekly-audio")
    a = ap.parse_args()
    issue = json.loads(Path(a.issue).read_text(encoding="utf-8"))
    if isinstance(issue, list):
        issue = issue[0]
    ok = produce(Path(a.rundown).read_text(encoding="utf-8"), issue, Path(a.out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
