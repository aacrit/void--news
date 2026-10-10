"""Assemble the On Air radio show from a rundown: voices, silence grammar,
original music cues, broadcast post-production, chapters.

    produce_radio_show(rundown, editorial_script, edition) -> RadioResult | None

Running order (see radio_script_generator):

    ident → OPEN → MENU (menu bed) → STORY 1-4 → BRIEFS → FINALLY
          → opinion entrance → OPINION (voice C, centred) → CLOSE (close bed) → outro

Every spoken line is one synthesis job; the timeline is built from the audio
lengths and a single table of gaps (RADIO_GAPS), so chapter offsets are exact
by construction and no silence detection is involved. Music sits only under
the menu and the sign-off (CEO: NPR-sparse, dry voice through the stories);
synthesised room tone runs under the whole programme so TTS silence never
reads as digital silence.

Post chain (ffmpeg): per-voice high-pass, presence lift, de-esser, gentle
compression, ±7 % pan → mix → limiter → two-pass loudnorm (-16 LUFS, -1 dBTP)
→ 128 kbps CBR stereo MP3 (ladder 96k stereo → 96k mono under the size cap)
→ ID3v2 chapters (mutagen) + a Podcasting 2.0 chapters JSON sidecar.

produce_audio() (weekly, legacy daily) and produce_history_audio() are
untouched; this module only shares their asset loader and static writer.
"""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except ImportError:  # pragma: no cover
    AudioSegment = None  # type: ignore
    PYDUB_AVAILABLE = False

try:
    from briefing.audio_producer import _load_asset, _write_audio_static
    from briefing.radio_script_generator import RadioRundown
    from briefing.spoken_text import normalize_for_speech
    from briefing.tts_engines import TurnSpec, synthesize_with_fallback, SAMPLE_RATE
except ImportError:  # pragma: no cover - package-relative
    from pipeline.briefing.audio_producer import _load_asset, _write_audio_static  # type: ignore
    from pipeline.briefing.radio_script_generator import RadioRundown  # type: ignore
    from pipeline.briefing.spoken_text import normalize_for_speech  # type: ignore
    from pipeline.briefing.tts_engines import TurnSpec, synthesize_with_fallback, SAMPLE_RATE  # type: ignore

SITE_URL = os.environ.get("PODCAST_SITE_URL", "https://news.voidvision.org").rstrip("/")

# ---------------------------------------------------------------------------
# The silence grammar (ms). One table; the timeline test asserts against it.
# ---------------------------------------------------------------------------

RADIO_GAPS: dict[str, int] = {
    "theme_overlap": 1200,      # sign-on starts this long before the THEME ends
    "ident_overlap": 500,       # ... or this long, on the legacy 2.4s ident
    "no_ident_lead": 300,
    "open_to_menu": 600,
    "menu_item": 400,
    "menu_to_story": 900,
    "same_speaker": 250,        # inside a story / the opinion
    "speaker_change": 320,
    "story_to_story": 850,      # when no transition cue exists
    "transition_lead": 300,     # seam = lead + transition + settle, in the clear
    "transition_settle": 500,
    "break_lead": 400,          # the one instrumental break, after deep story 2
    "break_settle": 700,
    "briefs_item": 450,
    "briefs_to_finally": 1200,
    "to_opinion": 900,          # last news word -> the opinion entrance
    "opinion_overlap": 1200,    # first opinion sentence starts over its tail
    "opinion_paragraph": 650,
    "opinion_verdict": 900,     # around a one-sentence paragraph
    "opinion_to_close": 900,
    "to_close_no_opinion": 1000,
    "outro_overlap": 400,       # outro starts this long before the sign-off ends
    "tail": 500,                # room tone only, after the outro's last sample
}

# Music placement relative to the cues (ms) and placement gains (dB applied
# on top of the asset as rendered by generate_assets). Measured 2026-09-18 on
# the first preview: speech masters at about -20 dBFS RMS, the beds were
# rendered at -40 dBFS RMS, and the CEO heard no music at all. A bed that is
# meant to be HEARD under a menu sits 8-12 dB under the voice, not 20.
BED_MENU_GAIN_DB = float(os.environ.get("VOID_RADIO_BED_GAIN_DB", "10") or 10)
# Beds that sit UNDER speech run quieter than the bookend beds, which play in
# the clear, and the duck below takes them further down while a voice is up.
BED_STORY_GAIN_DB = float(os.environ.get("VOID_RADIO_STORY_BED_GAIN_DB", "4") or 4)
BED_OPINION_GAIN_DB = float(os.environ.get("VOID_RADIO_OPINION_BED_GAIN_DB", "3") or 3)
CUE_GAIN_DB = 4.0          # theme, transition, break, opinion entrance, outro
# Ducking. Derived from the cue list, never from audio analysis: the timeline
# already knows every turn's start and end, so the curve is exact and the
# render stays deterministic.
DUCK_DB = float(os.environ.get("VOID_RADIO_DUCK_DB", "-9") or -9)
DUCK_ATTACK_MS = 140          # music is already down when the voice arrives
DUCK_RELEASE_MS = 900         # and comes back slowly, so it breathes
DUCK_STEP_MS = 10
# Arc shape (ms). Music enters before the first word, holds under the lede and
# fades out ACROSS the next turn, not in the gap after it.
STORY_MUSIC_LEAD = 900
# Absolute caps. Keying the hold to a turn boundary does not work on real
# copy: a story's opening turn runs 40s or more, so "hold under the lede"
# silently became "hold under the whole story" and the news block came out 96 %
# covered. Music holds for a fixed span and then goes, whatever the turn is
# doing, which is what keeps the entrances meaningful.
STORY_MUSIC_MAX_HOLD = 11000        # roughly the first two sentences
BRIEFS_MUSIC_MAX_HOLD = 22000
OPINION_OPEN_HOLD = 16000
OPINION_VERDICT_LEAD = 26000      # music returns this long before the last word
STORY_MUSIC_FADE_IN = 1600
STORY_MUSIC_FADE_OUT = 4200
OPINION_MUSIC_LEAD = 600
OPINION_MUSIC_FADE = 2600
BED_CLOSE_GAIN_DB = BED_MENU_GAIN_DB
BED_MENU_PRE = 1000
BED_MENU_FADE_IN = 1500
BED_MENU_FADE_OUT = 2000
BED_MENU_STOP_BEFORE_STORY = 200
BED_CLOSE_PRE = 800            # inside the editorial -> close gap (900), never under the editorial
BED_CLOSE_FADE_IN = 800
BED_CLOSE_HANDOVER = 2000   # the close bed fades out this far into the outro
ROOM_TONE_FADE = 1000

RADIO_ASSETS = {
    "ident": "radio_ident.wav",
    "theme": "radio_theme.wav",
    "menu_bed": "radio_menu_bed.wav",
    "story_bed": "radio_story_bed.wav",
    "transition": "radio_transition.wav",
    "break": "radio_break.wav",
    "opinion_theme": "radio_opinion_theme.wav",
    "opinion_bed": "radio_opinion_bed.wav",
    "close_bed": "radio_close_bed.wav",
    "outro": "radio_outro.wav",
    "room": "radio_room_tone.wav",
    "promo_bed": "radio_promo_bed.wav",   # under the house promo (house_promos.py)
}
# Beds rendered with an exact seam (_lock in generate_assets): these are looped
# with NO crossfade, because a crossfade shortens every cycle and drifts the
# pulse grid off the theme's tempo.
LOCKED_LOOPS = ("menu_bed", "story_bed", "opinion_bed", "room")

LEGACY_FALLBACK = {"ident": "ident.wav", "outro": "outro.wav"}

# "daily" scores the programme (a bed and a transition per segment, a break
# halfway through the news); "sparse" is the original NPR-shaped sound with
# music under the menu and the sign-off only. The opinion entrance plays in
# both, because it replaced the stab, which was a bookend.
MUSIC_STYLE = os.environ.get("VOID_RADIO_MUSIC_STYLE", "daily").strip().lower()

LOUDNESS_I = -16.0
LOUDNESS_TP = -1.0
LOUDNESS_LRA = 11.0
PAN = 0.07                      # A slightly left, B slightly right, C centred (it speaks alone)
MAX_FILE_SIZE = 12 * 1024 * 1024
BITRATE_LADDER = (("128k", 2), ("96k", 2), ("96k", 1))

# The served chapter sidecar carries only titles, no kinds, so for any reader
# of latest.chapters.json this string IS the segment's name.
CHAPTER_TITLES = {"MENU": "Headlines", "BRIEFS": "Also today", "FINALLY": "One more",
                  "OPINION": "Opinion"}


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

@dataclass
class Cue:
    idx: int
    kind: str            # OPEN MENU STORY BRIEFS FINALLY OPINION CLOSE
    segment_idx: int
    speaker: str
    start_ms: int
    end_ms: int
    title: str | None = None
    cluster_id: str | None = None
    rank: int | None = None
    verdict: bool = False


@dataclass
class Timeline:
    cues: list[Cue]
    total_ms: int
    opener_ms: int
    opener_kind: str | None            # "theme" | "ident" | None
    transition_at_ms: list[int]
    break_at_ms: int | None
    opinion_theme_at_ms: int | None
    opinion_start_ms: int | None
    outro_at_ms: int
    news_start_ms: int

    def first(self, kind: str) -> Cue | None:
        return next((c for c in self.cues if c.kind == kind), None)

    def last(self, kind: str) -> Cue | None:
        return next((c for c in reversed(self.cues) if c.kind == kind), None)


@dataclass
class RadioResult:
    audio_url: str
    duration_seconds: float
    file_size: int
    news_start_seconds: float
    opinion_start_seconds: float | None
    chapters: list[dict]
    engine: str
    voices: str
    timing: dict = field(default_factory=dict)
    audio_script: str = ""
    local_path: str | None = None

    def as_row_fields(self) -> dict:
        return {
            "audio_url": self.audio_url,
            "audio_duration_seconds": self.duration_seconds,
            "audio_file_size": self.file_size,
            "opinion_start_seconds": self.opinion_start_seconds,
            "news_start_seconds": self.news_start_seconds,
            "audio_chapters": self.chapters,
            "audio_voice": self.voices,
            "audio_voice_label": "Three voices",
        }


# ---------------------------------------------------------------------------
# 1. Turns
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(r"[.!?](?:\s|$)")


def _opinion_paragraphs(script: str) -> list[str]:
    paras: list[str] = []
    for block in re.split(r"\n\s*\n", script.strip()):
        lines = []
        for line in block.splitlines():
            s = re.sub(r"^(One|Two|A|B):\s*", "", line.strip())
            s = re.sub(r"\[[^\]]*\]", "", s).strip()
            if s:
                lines.append(s)
        if lines:
            paras.append(" ".join(lines))
    return paras


def build_turns(rundown: RadioRundown, editorial_script: str | None) -> list[tuple[TurnSpec, dict]]:
    """Flatten the rundown into synthesis jobs with per-turn metadata."""
    out: list[tuple[TurnSpec, dict]] = []
    idx = 0
    close_seg = None
    order = [s for s in rundown.segments if s.kind != "CLOSE"]
    close_seg = rundown.get("CLOSE")

    def add(role: str, text: str, meta: dict) -> None:
        nonlocal idx
        spoken = normalize_for_speech(text, rundown.say)
        if not spoken:
            return
        out.append((TurnSpec(idx=idx, role=role, text=spoken), meta))
        idx += 1

    for si, seg in enumerate(order):
        for t in seg.turns:
            add(t.speaker, t.text, {"kind": seg.kind, "segment_idx": si, "title": seg.title,
                                    "cluster_id": seg.cluster_id, "rank": seg.rank})
    if editorial_script and editorial_script.strip():
        si = len(order)
        # No spoken throw. The entrance music announces the segment and the
        # script's own first line says "Now, void opinion."; a voice saying
        # "Next, the editorial." immediately before that was two names for one
        # thing, back to back.
        for p in _opinion_paragraphs(editorial_script):
            verdict = len(_SENT_RE.findall(p)) <= 1 and len(p.split()) <= 18
            add("C", p, {"kind": "OPINION", "segment_idx": si, "verdict": verdict})
    if close_seg:
        si = len(order) + 1
        for t in close_seg.turns:
            add(t.speaker, t.text, {"kind": "CLOSE", "segment_idx": si})
    return out


# ---------------------------------------------------------------------------
# 2. Timeline
# ---------------------------------------------------------------------------

@dataclass
class CueLengths:
    """Lengths of the music cues the timeline must RESERVE ROOM for.

    The timeline has to know these because every one-motif cue plays in the
    clear: a transition that is merely overlaid lands under the first words of
    the story it introduces, which is what the previous build did. A zero
    length means the asset is absent, no room is reserved and no cue is placed,
    so a missing file degrades to silence at that seam rather than failing.
    """
    opener_ms: int = 0
    opener_is_theme: bool = False
    transition_ms: int = 0
    break_ms: int = 0
    opinion_theme_ms: int = 0
    outro_ms: int = 0


def load_music_set() -> dict:
    """Every music asset, loaded once, for both the timeline and the mix."""
    return {k: _asset(k) for k in RADIO_ASSETS}


def cue_lengths(assets: dict) -> CueLengths:
    theme, ident = assets.get("theme"), assets.get("ident")
    opener = theme or ident
    daily = MUSIC_STYLE == "daily"
    return CueLengths(
        opener_ms=len(opener) if opener else 0,
        opener_is_theme=theme is not None,
        # Transitions and the break are the scored sound; the sparse style keeps
        # only the bookends. The opinion entrance plays in BOTH, because it
        # replaced the stab, which was a bookend.
        transition_ms=len(assets["transition"]) if daily and assets.get("transition") else 0,
        break_ms=len(assets["break"]) if daily and assets.get("break") else 0,
        opinion_theme_ms=len(assets["opinion_theme"]) if assets.get("opinion_theme") else 0,
        outro_ms=len(assets["outro"]) if assets.get("outro") else 0,
    )


def _gap_before(prev: dict | None, cur: dict, prev_role: str | None, role: str,
                prev_verdict: bool, L: "CueLengths",
                second_story_idx: int | None) -> tuple[int, str | None]:
    """The silence before a turn, and the music cue that fills it (if any)."""
    G = RADIO_GAPS
    if prev is None:
        return 0, None
    pk, ck = prev["kind"], cur["kind"]
    if pk == "OPEN" and ck == "MENU":
        return G["open_to_menu"], None
    if pk == "MENU" and ck == "MENU":
        return G["menu_item"], None
    if pk == "MENU":
        return G["menu_to_story"], None
    if ck == "OPINION" and pk != "OPINION":
        # The entrance IS the throw: no one announces it, the music does, and
        # the script's own "Now, void opinion." follows over its tail.
        if L.opinion_theme_ms:
            return G["to_opinion"] + max(0, L.opinion_theme_ms - G["opinion_overlap"]), "opinion_theme"
        return G["to_opinion"], None
    new_segment = pk == "STORY" and prev["segment_idx"] != cur["segment_idx"]
    if new_segment and ck in ("STORY", "BRIEFS"):
        if prev["segment_idx"] == second_story_idx and L.break_ms:
            # The break replaces the transition here. Two cues that both
            # resolve on the root, back to back, is two endings.
            return G["break_lead"] + L.break_ms + G["break_settle"], "break"
        if L.transition_ms:
            return G["transition_lead"] + L.transition_ms + G["transition_settle"], "transition"
    if pk == "OPINION" and ck == "OPINION":
        return (G["opinion_verdict"] if (prev_verdict or cur.get("verdict"))
                else G["opinion_paragraph"]), None
    if ck == "CLOSE":
        return (G["opinion_to_close"] if pk == "OPINION" else G["to_close_no_opinion"]), None
    if pk == "BRIEFS" and ck == "BRIEFS":
        return G["briefs_item"], None
    if ck == "FINALLY" and pk != "FINALLY":
        return G["briefs_to_finally"], None
    if prev["segment_idx"] != cur["segment_idx"]:
        return G["story_to_story"], None
    return (G["same_speaker"] if prev_role == role else G["speaker_change"]), None


def build_timeline(turns: list[tuple[TurnSpec, dict]], audio: dict[int, "AudioSegment"],
                   L: "CueLengths") -> Timeline:
    """Lay the programme out in time, reserving room for every music cue.

    Cue positions are decided HERE and recorded on the Timeline, so the mix
    never recomputes them. One source of truth for placement is what makes the
    chapter offsets exact and lets the tests assert that a transition lands in
    a gap rather than over a voice.
    """
    cues: list[Cue] = []
    # The overlap is measured against the opener that will actually PLAY. It
    # used to be measured against the 2.4s ident while the 8s theme played,
    # so the sign-on began six seconds before the theme ended, over the top of
    # it, un-ducked.
    if L.opener_ms:
        pos = max(0, L.opener_ms - RADIO_GAPS["theme_overlap" if L.opener_is_theme else "ident_overlap"])
    else:
        pos = RADIO_GAPS["no_ident_lead"]
    story_segments = [m["segment_idx"] for _, m in turns if m["kind"] == "STORY"]
    seen: list[int] = []
    for idx in story_segments:
        if idx not in seen:
            seen.append(idx)
    second_story_idx = seen[1] if len(seen) > 1 else None
    prev_meta: dict | None = None
    prev_role: str | None = None
    prev_verdict = False
    transition_at: list[int] = []
    break_at: int | None = None
    opinion_theme_at: int | None = None
    for spec, meta in turns:
        seg = audio.get(spec.idx)
        if seg is None:
            continue
        gap, cue = _gap_before(prev_meta, meta, prev_role, spec.role, prev_verdict, L, second_story_idx)
        if cue == "transition":
            transition_at.append(pos + RADIO_GAPS["transition_lead"])
        elif cue == "break":
            break_at = pos + RADIO_GAPS["break_lead"]
        elif cue == "opinion_theme":
            opinion_theme_at = pos + RADIO_GAPS["to_opinion"]
        pos += gap
        cue_obj = Cue(idx=spec.idx, kind=meta["kind"], segment_idx=meta["segment_idx"], speaker=spec.role,
                      start_ms=pos, end_ms=pos + len(seg), title=meta.get("title"),
                      cluster_id=meta.get("cluster_id"), rank=meta.get("rank"),
                      verdict=bool(meta.get("verdict")))
        cues.append(cue_obj)
        pos = cue_obj.end_ms
        prev_meta, prev_role, prev_verdict = meta, spec.role, cue_obj.verdict
    outro_at = max(0, pos - RADIO_GAPS["outro_overlap"])
    total = max(pos, outro_at + L.outro_ms) + RADIO_GAPS["tail"]
    first_story = next((c for c in cues if c.kind == "STORY"), None)
    news_start = first_story.start_ms if first_story else (cues[0].start_ms if cues else 0)
    first_opinion = next((c for c in cues if c.kind == "OPINION"), None)
    # The Opinion chapter begins at its entrance music, not at the first word:
    # the entrance is part of the segment, and opinion_start_seconds is what the
    # player's Opinion jump and verify_audio A-06 both read.
    opinion_start = opinion_theme_at if opinion_theme_at is not None else (
        first_opinion.start_ms if first_opinion else None)
    return Timeline(cues=cues, total_ms=total, opener_ms=L.opener_ms,
                    opener_kind=("theme" if L.opener_is_theme else "ident") if L.opener_ms else None,
                    transition_at_ms=transition_at, break_at_ms=break_at,
                    opinion_theme_at_ms=opinion_theme_at, opinion_start_ms=opinion_start,
                    outro_at_ms=outro_at, news_start_ms=news_start)


def chapters_from_timeline(tl: Timeline, opinion_headline: str | None = None,
                           permalinks: dict[str, str] | None = None) -> list[dict]:
    """Chapter list (seconds). Headlines covers the opener, sign-on and menu;
    the Opinion chapter starts at its ENTRANCE MUSIC, not at its first word,
    because the entrance is part of the segment and is what the player's
    Opinion jump should land on; the sign-off folds into the last chapter."""
    chapters: list[dict] = []
    current_key = None
    for c in tl.cues:
        if c.kind in ("OPEN", "MENU"):
            key = ("headlines", None)
        elif c.kind == "OPINION":
            key = ("opinion", None)
        elif c.kind == "CLOSE":
            continue
        else:
            key = (c.kind.lower(), c.segment_idx)
        if key != current_key:
            current_key = key
            kind = key[0]
            title = CHAPTER_TITLES.get(c.kind, c.title or kind.title())
            if kind in ("story", "finally") and c.title:
                title = c.title
            start_ms = c.start_ms
            if kind == "opinion" and tl.opinion_theme_at_ms is not None:
                start_ms = tl.opinion_theme_at_ms
            ch: dict = {"startTime": round(start_ms / 1000, 3), "title": title, "kind": kind}
            if kind in ("story", "finally"):
                if c.cluster_id:
                    ch["cluster_id"] = c.cluster_id
                    url = (permalinks or {}).get(c.cluster_id)
                    if url:
                        ch["url"] = url
                if c.rank:
                    ch["rank"] = c.rank
            if kind == "opinion" and opinion_headline:
                ch["subtitle"] = opinion_headline
            chapters.append(ch)
    for i, ch in enumerate(chapters):
        nxt = chapters[i + 1]["startTime"] if i + 1 < len(chapters) else round(tl.total_ms / 1000, 3)
        ch["endTime"] = nxt
    if chapters:
        chapters[0]["startTime"] = 0.0
    return chapters


# ---------------------------------------------------------------------------
# 3. Mixing
# ---------------------------------------------------------------------------

def _silent(ms: int, channels: int = 1) -> "AudioSegment":
    return AudioSegment.silent(duration=ms, frame_rate=SAMPLE_RATE).set_channels(channels)


def _loop_to(seg: "AudioSegment", ms: int, crossfade: int = 0) -> "AudioSegment":
    """Repeat a bed to length.

    crossfade=0 (the default) is sample-exact repetition. The beds are rendered
    with every frequency and breath rate snapped by `_lock()` so the loop point
    is seamless BY CONSTRUCTION; a crossfade throws that away, shortening each
    cycle by its own length (a 24.0s bed became 23.6s) and drifting the pulse
    grid off the theme's tempo. Only pass a crossfade for material that was not
    rendered loop-locked.
    """
    if len(seg) <= 0:
        return seg
    if crossfade <= 0:
        return (seg * (ms // len(seg) + 1))[:ms]
    out = seg
    while len(out) < ms + crossfade:
        out = out.append(seg, crossfade=min(crossfade, len(seg) // 4))
    return out[:ms]


def _asset(key: str) -> Optional["AudioSegment"]:
    seg = _load_asset(RADIO_ASSETS[key])
    if seg is None and key in LEGACY_FALLBACK:
        seg = _load_asset(LEGACY_FALLBACK[key])
    if seg is not None:
        seg = seg.set_frame_rate(SAMPLE_RATE).set_sample_width(2)
    return seg


def render_voice_buses(tl: Timeline, audio: dict[int, "AudioSegment"]) -> dict[str, "AudioSegment"]:
    buses = {r: _silent(tl.total_ms) for r in ("A", "B", "C")}
    for c in tl.cues:
        buses[c.speaker] = buses[c.speaker].overlay(audio[c.idx], position=c.start_ms)
    return buses


SPOKEN_KINDS = ("OPEN", "MENU", "STORY", "BRIEFS", "FINALLY", "OPINION", "CLOSE")


def duck_envelope(tl: Timeline, step_ms: int = DUCK_STEP_MS) -> "list[float]":
    """Linear gain (0..1) per step for music that sits under speech.

    Derived from the cue list, not from the audio: the timeline is built from
    the synthesised turn lengths, so every speech window is already known to
    the millisecond. That keeps the mix deterministic (the same rundown always
    masters identically) and costs one pass over the cues instead of an RMS
    analysis of the voice bus.

    The curve falls to DUCK_DB over DUCK_ATTACK_MS BEFORE each turn starts, so
    the music is already out of the way when the voice arrives, and recovers
    over DUCK_RELEASE_MS after it ends, which is what makes a bed breathe in
    the gaps rather than pump.
    """
    steps = max(1, tl.total_ms // step_ms + 1)
    floor = 10 ** (DUCK_DB / 20.0)
    env = [1.0] * steps
    for c in tl.cues:
        if c.kind not in SPOKEN_KINDS:
            continue
        a0 = max(0, (c.start_ms - DUCK_ATTACK_MS) // step_ms)
        a1 = max(0, c.start_ms // step_ms)
        r0 = min(steps, c.end_ms // step_ms)
        r1 = min(steps, (c.end_ms + DUCK_RELEASE_MS) // step_ms)
        for i in range(a0, min(a1, steps)):            # attack ramp down
            t = (i - a0) / max(1, a1 - a0)
            env[i] = min(env[i], 1.0 - t * (1.0 - floor))
        for i in range(a1, r0):                        # held down under speech
            env[i] = min(env[i], floor)
        for i in range(r0, r1):                        # release ramp up
            t = (i - r0) / max(1, r1 - r0)
            env[i] = min(env[i], floor + t * (1.0 - floor))
    return env


def duck_weight(g: float) -> float:
    """0 when fully ducked, 1 when the bed is in the clear."""
    floor = 10 ** (DUCK_DB / 20.0)
    return 0.0 if g <= floor else (g - floor) / (1.0 - floor)


def apply_duck(seg: "AudioSegment", env: "list[float]", start_ms: int,
               step_ms: int = DUCK_STEP_MS, dark: "AudioSegment | None" = None) -> "AudioSegment":
    """Multiply a bed by the duck curve. numpy, so it is one vector op rather
    than tens of thousands of pydub slices."""
    try:
        import numpy as np
    except Exception:
        return seg
    samples = np.array(seg.get_array_of_samples()).astype(np.float32)
    ch = seg.channels
    frames = len(samples) // ch
    idx = (np.arange(frames) * (1000.0 / seg.frame_rate) + start_ms) / step_ms
    idx = np.clip(idx.astype(np.int64), 0, len(env) - 1)
    gain = np.asarray(env, dtype=np.float32)[idx]
    if dark is not None:
        # Frequency-aware duck. Under a voice the bed is not only quieter but
        # DARKER: a bed that only drops in level still competes with speech in
        # the 1-4 kHz band where consonants live. Crossfading to a low-passed
        # copy by the same envelope is how a bed gets out of the way without
        # disappearing.
        floor = 10 ** (DUCK_DB / 20.0)
        w = np.clip((gain - floor) / max(1e-9, 1.0 - floor), 0.0, 1.0)
        dk = np.array(dark.get_array_of_samples()).astype(np.float32)
        n = min(len(dk), len(samples))
        samples = samples[:n]
        blended = samples * np.repeat(w, ch)[:n] if ch > 1 else samples * w[:n]
        blended = blended + dk[:n] * (1.0 - (np.repeat(w, ch)[:n] if ch > 1 else w[:n]))
        samples, gain = blended, (np.repeat(gain, ch)[:n] if ch > 1 else gain[:n])
        out = np.clip(samples * gain, -32768, 32767).astype(np.int16)
        return seg._spawn(out.tobytes())
    if ch > 1:
        gain = np.repeat(gain, ch)
    out = np.clip(samples * gain, -32768, 32767).astype(np.int16)
    return seg._spawn(out.tobytes())


# Fraction into a turn at which a fade-out should COMPLETE. Early enough that
# the listener hears the music leave while the sentence is still going, late
# enough that the fade is not fighting the turn's first syllable.
WEAVE_AT = 0.45


def weave_end(tl: Timeline, ideal_ms: int, fade_ms: int) -> int:
    """Snap a fade-out so it finishes UNDER a sentence, never in a gap.

    This is the whole difference between music that feels woven into the read
    and music that feels stitched between segments. A fade that completes in
    silence is audible as an edit: the listener hears the music stop. A fade
    that completes while a voice is still speaking is heard as the voice
    emerging, which is the effect a scored programme wants.

    Given where the arc would ideally end, this returns the nearest point
    inside a spoken turn, preferring the turn already in progress and falling
    forward to the next one. It also guarantees the fade has somewhere to
    happen: the returned end is never so early that the fade would start before
    the cue does.
    """
    turns = [c for c in tl.cues if c.kind in SPOKEN_KINDS and c.end_ms > c.start_ms]
    if not turns:
        return ideal_ms
    inside = next((c for c in turns if c.start_ms <= ideal_ms < c.end_ms), None)
    if inside is not None:
        span = inside.end_ms - inside.start_ms
        lo = inside.start_ms + min(300, span // 4)
        hi = inside.end_ms - min(300, span // 4)
        return max(lo, min(ideal_ms, hi)) if hi > lo else ideal_ms
    nxt = next((c for c in turns if c.start_ms >= ideal_ms), None)
    if nxt is not None:
        span = nxt.end_ms - nxt.start_ms
        return nxt.start_ms + max(250, int(span * WEAVE_AT))
    prev = turns[-1]
    span = prev.end_ms - prev.start_ms
    return prev.start_ms + max(250, int(span * WEAVE_AT))


def _turns_of(tl: Timeline, kind: str) -> list[list[Cue]]:
    """Cues grouped into segments: each STORY is one group, in order."""
    groups: dict[int, list[Cue]] = {}
    for c in tl.cues:
        if c.kind == kind:
            groups.setdefault(c.segment_idx, []).append(c)
    return [groups[k] for k in sorted(groups)]


def _scored_cues(tl: Timeline) -> list[dict]:
    """Music with an ARC per segment, which is what a scored programme does.

    A continuous bed under the whole news block is a radio bed: always there,
    merely quieter under the voice. The Daily-shaped alternative is to let
    music ENTER on a beat, hold under the setup, and LEAVE, because the leaving
    is what gives the next entrance its weight. Music under everything flattens
    exactly the contrast it is there to create.

    So, per story: in under the transition, hold through the lede, then fade out
    ACROSS the following turn rather than in the gap after it. Fading under a
    sentence is what makes music feel woven into the read instead of stitched
    between segments; fading only in the gaps is audible as editing.

    The editorial gets the shape an argument wants: in at the throw, out under
    the opening paragraph, then back for the closing one, so the verdict lands
    over a rise rather than over nothing.

    All of it is derived from the cue list, so the render stays deterministic.
    """
    out: list[dict] = []
    stories = _turns_of(tl, "STORY")
    for i, turns in enumerate(stories):
        first, last = turns[0], turns[-1]
        start = max(0, first.start_ms - STORY_MUSIC_LEAD)
        # Hold through the lede, then fade across whatever is spoken next. A
        # one-turn story has no "next", so it fades across its own tail.
        hold_to = min(turns[0].end_ms, first.start_ms + STORY_MUSIC_MAX_HOLD)
        ideal = min(hold_to + STORY_MUSIC_FADE_OUT, last.end_ms)
        end = weave_end(tl, ideal, STORY_MUSIC_FADE_OUT)
        if end <= start + 2000:
            continue
        out.append({"asset": "story_bed", "start": start, "end": end,
                    "fade_in": STORY_MUSIC_FADE_IN,
                    "fade_out": STORY_MUSIC_FADE_OUT, "duck": True,
                    "tag": f"story{i + 1}"})
    # The briefs are a list, and a list reads better over motion than over
    # silence, so the bed runs the whole block and clears before the kicker.
    briefs = _turns_of(tl, "BRIEFS")
    if briefs:
        b = [c for g in briefs for c in g]
        b_end = min(b[0].start_ms + BRIEFS_MUSIC_MAX_HOLD, b[-1].end_ms)
        out.append({"asset": "story_bed", "start": max(0, b[0].start_ms - STORY_MUSIC_LEAD),
                    "end": weave_end(tl, b_end, STORY_MUSIC_FADE_OUT), "fade_in": STORY_MUSIC_FADE_IN,
                    "fade_out": STORY_MUSIC_FADE_OUT, "duck": True, "tag": "briefs"})
    ed = [c for c in tl.cues if c.kind == "OPINION"]
    if ed:
        ed_end = ed[-1].end_ms
        opening_end = min(ed[0].start_ms + OPINION_OPEN_HOLD, ed_end)
        out.append({"asset": "opinion_bed", "start": max(0, ed[0].start_ms - OPINION_MUSIC_LEAD),
                    "end": weave_end(tl, opening_end, OPINION_MUSIC_FADE),
                    "fade_in": OPINION_MUSIC_FADE, "fade_out": OPINION_MUSIC_FADE,
                    "duck": True, "tag": "opinion-open"})
        if len(ed) > 2 and ed_end - ed[0].start_ms > OPINION_VERDICT_LEAD + OPINION_OPEN_HOLD:
            # Back for the verdict, and it stays up into the sign-off so the
            # close bed takes over a programme that is already moving. Anchored
            # to the END of the editorial, not to its last paragraph, which on
            # real copy can be a single short sentence.
            out.append({"asset": "opinion_bed", "start": max(0, ed_end - OPINION_VERDICT_LEAD),
                        "end": ed_end + 700, "fade_in": OPINION_MUSIC_FADE,
                        "fade_out": 900, "duck": True, "tag": "opinion-verdict",
                        # The one cue that is NOT woven under a sentence: it is
                        # handed to the close bed, so it must outlast the last
                        # editorial word. Ending it mid-sentence here would cut
                        # the programme's only continuous run into the sign-off.
                        "handoff": True})
    return out

def bed_envelope(tl: Timeline, menu_bed_ms: int, close_bed_ms: int) -> list[dict]:
    """Where music sits.

    Deterministic from the cues. In "daily" style a bed runs under the stories
    and under the editorial, ducked against the voice; in "sparse" style the
    only music is the opening and closing bookends, which is the sound the
    show shipped with before 2026-09-19.
    """
    cues: list[dict] = []
    menu_first, menu_last = tl.first("MENU"), tl.last("MENU")
    story = tl.first("STORY")
    open_first = tl.first("OPEN")
    if menu_first and menu_last and menu_bed_ms:
        # The opening bed runs from the sign-on (it fades in under the ident
        # tail) through the menu and is gone before story 1 begins.
        anchor = open_first.start_ms if open_first else menu_first.start_ms
        start = max(0, anchor - BED_MENU_PRE)
        end = (story.start_ms - BED_MENU_STOP_BEFORE_STORY) if story else menu_last.end_ms + 800
        cues.append({"asset": "menu_bed", "start": start, "end": max(start + 1000, end),
                     "fade_in": BED_MENU_FADE_IN, "fade_out": BED_MENU_FADE_OUT})
    if MUSIC_STYLE == "daily":
        cues.extend(_scored_cues(tl))
    close = tl.first("CLOSE")
    if close and close_bed_ms:
        start = max(0, close.start_ms - BED_CLOSE_PRE)
        # Never looped: it is a one-shot that falls to silence, so a second
        # pass re-enters audibly. Clamped to its own length and handed over to
        # the outro, which carries the programme out from there.
        end = min(start + close_bed_ms, tl.outro_at_ms + BED_CLOSE_HANDOVER)
        cues.append({"asset": "close_bed", "start": start, "end": max(start + 1000, end),
                     "fade_in": BED_CLOSE_FADE_IN, "fade_out": BED_CLOSE_HANDOVER,
                     "loop": False})
    return cues


def transition_points(tl: Timeline) -> list[int]:
    """Where the story-to-story transitions land.

    The timeline decides this now, because it has to RESERVE the room: a cue
    that is merely overlaid plays under the first words of the story it
    introduces. This is a read-through so callers and tests have a name for it.
    """
    return list(tl.transition_at_ms)


def render_music_bus(tl: Timeline, assets: dict | None = None) -> tuple["AudioSegment", dict]:
    """The music. Every cue position comes from the timeline, which reserved
    room for it, so nothing here lands on top of a voice."""
    a = assets if assets is not None else load_music_set()
    bus = _silent(tl.total_ms, channels=2)
    used: dict = {}
    duck = duck_envelope(tl)
    beds = {"menu_bed": a.get("menu_bed"), "close_bed": a.get("close_bed"),
            "story_bed": a.get("story_bed"), "opinion_bed": a.get("opinion_bed")}
    gains = {"menu_bed": BED_MENU_GAIN_DB, "close_bed": BED_CLOSE_GAIN_DB,
             "story_bed": BED_STORY_GAIN_DB, "opinion_bed": BED_OPINION_GAIN_DB}

    def place(key: str, at: int | None) -> None:
        seg = a.get(key)
        if seg is None or at is None:
            return
        nonlocal bus
        bus = bus.overlay(seg.apply_gain(CUE_GAIN_DB).set_channels(2), position=at)

    opener_key = tl.opener_kind
    if opener_key:
        place(opener_key, 0)
        used[opener_key] = tl.opener_ms
    for at in tl.transition_at_ms:
        place("transition", at)
    if tl.transition_at_ms:
        used["transition"] = list(tl.transition_at_ms)
    if tl.break_at_ms is not None:
        place("break", tl.break_at_ms)
        used["break"] = tl.break_at_ms
    if tl.opinion_theme_at_ms is not None:
        place("opinion_theme", tl.opinion_theme_at_ms)
        used["opinion_theme"] = tl.opinion_theme_at_ms
    place("outro", tl.outro_at_ms)
    if a.get("outro"):
        used["outro"] = tl.outro_at_ms

    dark_cache: dict[str, "AudioSegment"] = {}
    for env in bed_envelope(tl, len(beds["menu_bed"] or b"") if beds["menu_bed"] else 0,
                            len(beds["close_bed"]) if beds["close_bed"] else 0):
        asset = beds.get(env["asset"])
        if asset is None:
            continue    # no such track supplied: that segment simply runs dry
        base = asset.apply_gain(gains[env["asset"]])
        start = max(0, env["start"])
        length = max(1000, env["end"] - start)
        loop_ok = env.get("loop", True) and env["asset"] in LOCKED_LOOPS

        def shape(src: "AudioSegment") -> "AudioSegment":
            seg = _loop_to(src, length) if (len(src) < length and loop_ok) else src[:length]
            if len(seg) < length:
                seg = seg + _silent(length - len(seg))
            seg = seg.fade_in(min(env["fade_in"], length // 2)) if env["fade_in"] else seg
            seg = seg.fade_out(min(env["fade_out"], length // 2)) if env["fade_out"] else seg
            return seg.set_channels(2)

        seg = shape(base)
        if env.get("duck"):
            if env["asset"] not in dark_cache:
                # 12 dB/oct at 2.4 kHz, computed once per asset, not per cue.
                dark_cache[env["asset"]] = base.low_pass_filter(2400).low_pass_filter(2400)
            seg = apply_duck(seg, duck, start, dark=shape(dark_cache[env["asset"]]))
        bus = bus.overlay(seg, position=start)
        used.setdefault(env["asset"], []).append(
            (env.get("tag") or env["asset"], start, env["end"]))
    room = a.get("room")
    if room:
        tone = _loop_to(room, tl.total_ms).fade_in(ROOM_TONE_FADE).fade_out(ROOM_TONE_FADE)
        bus = bus.overlay(tone.set_channels(2), position=0)
        used["room"] = True
    return bus, used


def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def voice_chain_filter(pan: float) -> str:
    """Per-voice chain. `pan` is -1..1; 0 is centred.

    The pan is constant-power and root-2 scaled, so moving a voice off centre
    does not change its loudness. The old form attenuated one channel
    (`c0=1.000, c1=0.930`), which left the two panned anchors about 0.6 dB under
    the centred opinion voice, and scaling without the root-2 would drop every
    voice 3 dB against the music and invalidate every bed gain.

    Compression is 2.5:1 with a slow release: it rides phrases rather than
    syllables. At 3:1 with a 120 ms release the programme came back at LRA 2.7,
    which is a flat read of copy that is meant to have light and shade.
    """
    theta = (pan + 1.0) * math.pi / 4.0
    left = math.sqrt(2.0) * math.cos(theta)
    right = math.sqrt(2.0) * math.sin(theta)
    return ",".join([
        "highpass=f=80:poles=2",
        "equalizer=f=250:t=q:w=1.0:g=-1.5",
        "equalizer=f=4000:t=q:w=1.2:g=2.5",
        "deesser=i=0.35:m=0.5:f=0.5",
        "acompressor=threshold=-18dB:ratio=2.5:attack=10:release=320:knee=4:makeup=2",
        f"pan=stereo|c0={left:.4f}*c0|c1={right:.4f}*c0",
    ])


def process_voice_bus(seg: "AudioSegment", pan: float, work: Path, label: str) -> "AudioSegment":
    """Per-voice chain via ffmpeg; degrades to pan-only, then raw, on failure."""
    ff = _ffmpeg()
    if not ff:
        return seg.set_channels(2)
    src = work / f"bus_{label}.wav"
    dst = work / f"bus_{label}_post.wav"
    seg.export(str(src), format="wav")
    for flt in (voice_chain_filter(pan), voice_chain_filter(pan).replace("deesser=i=0.35:m=0.5:f=0.5,", "")):
        proc = _run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-af", flt,
                     "-ar", str(SAMPLE_RATE), "-ac", "2", str(dst)])
        if proc.returncode == 0 and dst.exists():
            return AudioSegment.from_file(str(dst), format="wav")
        print(f"  [radio] voice chain failed for {label}: {proc.stderr.strip()[-160:]}")
    return seg.set_channels(2)


_LOUDNORM_JSON_RE = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.DOTALL)


def loudnorm_two_pass(src: Path, dst: Path) -> dict:
    """EBU R128 normalisation, in LINEAR mode, with the limiter anchored.

    Two things were wrong with the previous chain and both flattened the show.

    The limiter ran ahead of loudnorm on an un-normalised mix whose peaks were
    nowhere near it, so it never engaged; the -3.97 dBTP the programme came
    back at was simply the mix's crest factor after a linear gain, not a
    limiter doing its job.

    Worse, `loudnorm` only STAYS linear when the gain it is about to apply
    keeps true peak inside the target. Otherwise it silently switches to
    dynamic mode and compresses the programme itself, which is exactly the
    flattening we are removing from the voice chain. So: measure the raw mix,
    work out the gain, and only if that gain would breach the ceiling insert a
    limiter sized for it, re-measure through the limiter, and render linear.
    `normalization_type` is logged so a future regression is visible rather
    than merely audible.
    """
    ff = _ffmpeg()
    stats: dict = {}
    if not ff:
        shutil.copy(src, dst)
        return stats
    ln = f"loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}"

    def measure(chain: str) -> dict | None:
        pr = _run([ff, "-hide_banner", "-nostats", "-i", str(src), "-af",
                   f"{chain}:print_format=json", "-f", "null", "-"])
        mm = _LOUDNORM_JSON_RE.search(pr.stderr or "")
        if not mm:
            print(f"  [radio] loudnorm measure failed: {(pr.stderr or '')[-200:]}")
            return None
        try:
            return json.loads(mm.group(0))
        except json.JSONDecodeError:
            return None

    measured = measure(ln)
    if measured is None:
        shutil.copy(src, dst)
        return stats
    pre = ""
    try:
        gain = LOUDNESS_I - float(measured["input_i"])
        if float(measured["input_tp"]) + gain > LOUDNESS_TP - 0.5:
            # Sized in the PRE-gain domain so the post-gain peak lands under
            # the ceiling with half a dB to spare.
            limit_db = LOUDNESS_TP - gain - 0.5
            pre = f"alimiter=limit={10 ** (limit_db / 20):.4f}:attack=5:release=80:level=false,"
            remeasured = measure(pre + ln)
            if remeasured is not None:
                measured = remeasured
    except (KeyError, ValueError):
        pass
    flt = (f"{pre}{ln}:measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}"
           f":measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}"
           f":offset={measured.get('target_offset', 0)}:linear=true:print_format=json")
    p2 = _run([ff, "-y", "-hide_banner", "-nostats", "-i", str(src), "-af", flt, "-ar", "44100",
               "-ac", "2", str(dst)])
    m2 = _LOUDNORM_JSON_RE.search(p2.stderr or "")
    if p2.returncode != 0 or not dst.exists():
        print(f"  [radio] loudnorm render failed: {(p2.stderr or '')[-200:]}")
        shutil.copy(src, dst)
        return {"input": measured}
    stats = {"input": measured, "limiter": bool(pre)}
    if m2:
        try:
            stats["output"] = json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass
    mode = (stats.get("output") or {}).get("normalization_type")
    if mode:
        stats["normalization_type"] = mode
        if mode != "linear":
            print(f"  [radio] WARNING loudnorm fell back to {mode} mode: the programme "
                  f"was dynamics-processed a second time and LRA will read low")
    return stats


def measure_loudness(path: Path) -> dict | None:
    ff = _ffmpeg()
    if not ff:
        return None
    p = _run([ff, "-hide_banner", "-nostats", "-i", str(path), "-af",
              f"loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}:print_format=json", "-f", "null", "-"])
    m = _LOUDNORM_JSON_RE.search(p.stderr or "")
    try:
        return json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        return None


def encode_mp3(src: Path, dst: Path, bitrate: str, channels: int) -> bool:
    ff = _ffmpeg()
    if not ff:
        try:
            AudioSegment.from_file(str(src)).export(str(dst), format="mp3", bitrate=bitrate,
                                                    parameters=["-ac", str(channels)])
            return dst.exists()
        except Exception:
            return False
    p = _run([ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src), "-ar", "44100",
              "-ac", str(channels), "-codec:a", "libmp3lame", "-b:a", bitrate, "-write_xing", "1", str(dst)])
    return p.returncode == 0 and dst.exists()


# ---------------------------------------------------------------------------
# 5. Chapters
# ---------------------------------------------------------------------------

def write_id3_chapters(mp3_path: Path, chapters: list[dict], title: str, date_label: str) -> bool:
    try:
        from mutagen.id3 import ID3, ID3NoHeaderError, CHAP, CTOC, CTOCFlags, TIT2, TPE1, TALB, TDRC, WXXX
    except ImportError:
        print("  [radio] mutagen not installed; MP3 has no ID3 chapters")
        return False
    try:
        try:
            tags = ID3(str(mp3_path))
        except ID3NoHeaderError:
            tags = ID3()
        tags.delall("CHAP")
        tags.delall("CTOC")
        tags.add(TIT2(encoding=3, text=[title]))
        tags.add(TPE1(encoding=3, text=["Void News"]))
        tags.add(TALB(encoding=3, text=["On Air"]))
        tags.add(TDRC(encoding=3, text=[date_label]))
        ids = []
        for i, ch in enumerate(chapters, 1):
            cid = f"chp{i:02d}"
            ids.append(cid)
            sub = [TIT2(encoding=3, text=[f"{i}/{len(chapters)} · {ch['title']}"])]
            if ch.get("url"):
                sub.append(WXXX(encoding=3, desc="chapter url", url=ch["url"]))
            tags.add(CHAP(element_id=cid, start_time=int(round(ch["startTime"] * 1000)),
                          end_time=int(round(ch.get("endTime", ch["startTime"]) * 1000)), sub_frames=sub))
        tags.add(CTOC(element_id="toc", flags=CTOCFlags.TOP_LEVEL | CTOCFlags.ORDERED,
                      child_element_ids=ids, sub_frames=[TIT2(encoding=3, text=[title])]))
        tags.save(str(mp3_path), v2_version=3)
        return True
    except Exception as e:
        print(f"  [radio] ID3 chapter write failed: {e}")
        return False


def permalinks_from_archive(root: Path | None = None) -> dict[str, str]:
    """cluster id -> canonical /story/<printed id>/ URL, from the committed
    archive map the frontend already uses (frontend/build-data/archiveMap.json).
    Empty when the file is missing; chapters then simply carry no url."""
    root = root or Path(__file__).resolve().parents[2]
    path = root / "frontend" / "build-data" / "archiveMap.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, str] = {}
    items = data.items() if isinstance(data, dict) else []
    for cluster_id, value in items:
        printed = value.get("id") if isinstance(value, dict) else value
        if not isinstance(printed, str) or not printed:
            continue
        if printed.startswith("/"):           # "/story/<printed id>/" (current shape)
            out[str(cluster_id).lower()] = f"{SITE_URL}{printed}"
        elif printed.startswith("http"):
            out[str(cluster_id).lower()] = printed
        else:
            out[str(cluster_id).lower()] = f"{SITE_URL}/story/{printed}/"
    return out


def chapters_sidecar(chapters: list[dict], title: str) -> bytes:
    body = {"version": "1.2.0", "title": title, "author": "Void News",
            "chapters": [{k: v for k, v in ch.items() if k in ("startTime", "endTime", "title", "url")}
                         for ch in chapters]}
    return json.dumps(body, ensure_ascii=False, indent=1).encode("utf-8")


# ---------------------------------------------------------------------------
# 6. The show
# ---------------------------------------------------------------------------

def produce_radio_show(
    rundown: RadioRundown,
    editorial_script: str | None,
    edition: str = "world",
    *,
    opinion_headline: str | None = None,
    permalinks: dict[str, str] | None = None,
    engines: list | None = None,
    out_dir: Path | str | None = None,
    date: datetime | None = None,
) -> Optional[RadioResult]:
    """Synthesize, assemble, master and publish the show.

    ``out_dir`` (dry runs) writes the MP3 + chapters JSON there instead of the
    static site and returns a file path as ``audio_url``.
    """
    if os.environ.get("DISABLE_AUDIO", "").strip() in ("1", "true", "yes"):
        print("  [radio] DISABLE_AUDIO=1; skipping")
        return None
    if not PYDUB_AVAILABLE:
        print("  [radio] pydub not installed; skipping")
        return None

    t0 = time.time()
    date = date or datetime.now(timezone.utc)
    turns = build_turns(rundown, editorial_script)
    if not turns:
        print("  [radio] no turns to synthesise")
        return None
    required = {spec.idx for spec, meta in turns if meta["kind"] in ("OPEN", "CLOSE")}
    words = sum(len(spec.text.split()) for spec, _ in turns)
    print(f"  [radio] {len(turns)} turns, {words} spoken words "
          f"({sum(1 for _, m in turns if m['kind'] == 'EDITORIAL')} editorial paragraphs)")

    res = synthesize_with_fallback([spec for spec, _ in turns], engines=engines, required=required)
    if res is None:
        print("  [radio] every engine failed; no show")
        return None
    turns = [(s, m) for s, m in turns if s.idx in res.audio]
    tts_s = time.time() - t0

    assets = load_music_set()
    tl = build_timeline(turns, res.audio, cue_lengths(assets))
    spoken_ms = sum(c.end_ms - c.start_ms for c in tl.cues)
    wpm = words / (spoken_ms / 60000) if spoken_ms else 0
    print(f"  [radio] timeline {tl.total_ms / 1000:.1f}s, speech {spoken_ms / 1000:.1f}s, {wpm:.0f} wpm, "
          f"news at {tl.news_start_ms / 1000:.1f}s, opinion at "
          f"{(tl.opinion_start_ms or 0) / 1000:.1f}s")

    work = Path(tempfile.mkdtemp(prefix="void-radio-"))
    try:
        buses = render_voice_buses(tl, res.audio)
        a = process_voice_bus(buses["A"], -PAN, work, "A")
        b = process_voice_bus(buses["B"], +PAN, work, "B")
        c = process_voice_bus(buses["C"], 0.0, work, "C")
        music, used = render_music_bus(tl, assets)
        print(f"  [radio] music cues: {used}")
        mix = _silent(tl.total_ms, channels=2).overlay(a).overlay(b).overlay(c).overlay(music)
        # House promo under the outro's held bars, after the sign-off tag.
        # The length does not change, so A-04 and the size ladder are
        # untouched; a missing render ships the programme exactly as before.
        from briefing import house_promos
        promo_key = f"onair:{edition}:{date.strftime('%Y-%m-%d')}:{'am' if date.hour < 12 else 'pm'}"
        mix, promo_info = house_promos.post_roll(
            mix, outro_at_ms=tl.outro_at_ms, last_word_ms=tl.cues[-1].end_ms if tl.cues else None,
            plays_in="onair", key=promo_key, work=work)
        mix_wav = work / "mix.wav"
        mix.export(str(mix_wav), format="wav")
        master_wav = work / "master.wav"
        stats = loudnorm_two_pass(mix_wav, master_wav)
        if stats.get("output"):
            o = stats["output"]
            print(f"  [radio] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} LRA={o.get('output_lra')}")

        audio_bytes: bytes | None = None
        chosen = None
        for bitrate, channels in BITRATE_LADDER:
            mp3 = work / f"show_{bitrate}_{channels}.mp3"
            if encode_mp3(master_wav, mp3, bitrate, channels):
                size = mp3.stat().st_size
                if size <= MAX_FILE_SIZE or (bitrate, channels) == BITRATE_LADDER[-1]:
                    audio_bytes = mp3.read_bytes()
                    chosen = (bitrate, channels, mp3)
                    break
                print(f"  [radio] {size / 1024 / 1024:.1f} MB at {bitrate}/{channels}ch exceeds cap; next rung")
        if not audio_bytes or not chosen:
            print("  [radio] MP3 encode failed")
            return None

        duration_s = round(len(mix) / 1000.0, 1)
        chapters = chapters_from_timeline(tl, opinion_headline, permalinks)
        if promo_info:
            chapters = house_promos.append_promo_chapter(
                chapters, house_promos.select("onair", promo_key), promo_info["at_ms"], tl.total_ms,
                kind="promo")
        title = f"On Air · {date.strftime('%A %d %B %Y')}"
        mp3_path = chosen[2]
        if write_id3_chapters(mp3_path, chapters, title, date.strftime("%Y-%m-%d")):
            audio_bytes = mp3_path.read_bytes()
        sidecar = chapters_sidecar(chapters, title)
        print(f"  [radio] {chosen[0]} {chosen[1]}ch, {len(audio_bytes) / 1024 / 1024:.2f} MB, "
              f"{duration_s:.0f}s, {len(chapters)} chapters")

        if out_dir:
            out = Path(out_dir)
            out.mkdir(parents=True, exist_ok=True)
            stem = f"{date.strftime('%Y-%m-%d')}-{'am' if date.hour < 12 else 'pm'}"
            (out / f"{stem}.mp3").write_bytes(audio_bytes)
            (out / f"{stem}.chapters.json").write_bytes(sidecar)
            (out / f"{stem}.rundown.txt").write_text(rundown.to_text(), encoding="utf-8")
            audio_url = str(out / f"{stem}.mp3")
            local_path = audio_url
        else:
            audio_url = _write_audio_static(audio_bytes, edition, sidecars={".chapters.json": sidecar})
            local_path = None
            if not audio_url:
                return None

        voices = f"{res.engine}:{res.timing.get('voice_a', '')}"
        try:
            eng = next(e for e in (engines or []) if e.name == res.engine)
            voices = f"{res.engine}:{eng.voice_id('A')}+{eng.voice_id('B')}+{eng.voice_id('C')}"
        except StopIteration:
            from briefing.tts_engines import engine_chain
            eng = next((e for e in engine_chain() if e.name == res.engine), None)
            if eng:
                voices = f"{res.engine}:{eng.voice_id('A')}+{eng.voice_id('B')}+{eng.voice_id('C')}"

        return RadioResult(
            audio_url=audio_url, duration_seconds=duration_s, file_size=len(audio_bytes),
            news_start_seconds=round(tl.news_start_ms / 1000, 3),
            opinion_start_seconds=round(tl.opinion_start_ms / 1000, 3) if tl.opinion_start_ms is not None else None,
            chapters=chapters, engine=res.engine, voices=voices,
            timing={"tts_s": round(tts_s, 1), "total_s": round(time.time() - t0, 1),
                    "wpm": round(wpm), "engine": res.timing, "loudness": stats.get("output"),
                    "bitrate": chosen[0], "channels": chosen[1]},
            audio_script=rundown.to_text(), local_path=local_path,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
