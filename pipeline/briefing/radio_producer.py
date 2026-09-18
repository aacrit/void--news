"""Assemble the On Air radio show from a rundown: voices, silence grammar,
original music cues, broadcast post-production, chapters.

    produce_radio_show(rundown, editorial_script, edition) -> RadioResult | None

Running order (see radio_script_generator):

    ident → OPEN → MENU (menu bed) → STORY 1-4 → BRIEFS → FINALLY
          → throw line → stab → EDITORIAL (voice B) → CLOSE (close bed) → outro

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
    from briefing.radio_script_generator import RadioRundown, THROW_LINE
    from briefing.spoken_text import normalize_for_speech
    from briefing.tts_engines import TurnSpec, synthesize_with_fallback, SAMPLE_RATE
except ImportError:  # pragma: no cover - package-relative
    from pipeline.briefing.audio_producer import _load_asset, _write_audio_static  # type: ignore
    from pipeline.briefing.radio_script_generator import RadioRundown, THROW_LINE  # type: ignore
    from pipeline.briefing.spoken_text import normalize_for_speech  # type: ignore
    from pipeline.briefing.tts_engines import TurnSpec, synthesize_with_fallback, SAMPLE_RATE  # type: ignore

SITE_URL = os.environ.get("PODCAST_SITE_URL", "https://news.voidvision.org").rstrip("/")

# ---------------------------------------------------------------------------
# The silence grammar (ms). One table; the timeline test asserts against it.
# ---------------------------------------------------------------------------

RADIO_GAPS: dict[str, int] = {
    "ident_overlap": 500,       # sign-on starts this long before the ident ends
    "no_ident_lead": 300,
    "open_to_menu": 600,
    "menu_item": 400,
    "menu_to_story": 900,
    "same_speaker": 250,        # inside a story / the editorial
    "speaker_change": 320,
    "story_to_story": 850,      # also STORY -> BRIEFS
    "briefs_item": 450,
    "briefs_to_finally": 1200,
    "to_throw": 700,            # FINALLY (or BRIEFS) -> "Next, the editorial."
    "throw_to_stab": 300,
    "stab_to_editorial": 450,
    "editorial_paragraph": 650,
    "editorial_verdict": 900,   # around a one-sentence paragraph
    "editorial_to_close": 900,
    "to_close_no_editorial": 1000,
    "outro_overlap": 400,       # outro starts this long before the sign-off ends
    "tail": 250,
}

# Music placement relative to the cues (ms) and placement gains (dB applied
# on top of the asset as rendered by generate_assets). Measured 2026-09-18 on
# the first preview: speech masters at about -20 dBFS RMS, the beds were
# rendered at -40 dBFS RMS, and the CEO heard no music at all. A bed that is
# meant to be HEARD under a menu sits 8-12 dB under the voice, not 20.
BED_MENU_GAIN_DB = float(os.environ.get("VOID_RADIO_BED_GAIN_DB", "10") or 10)
BED_CLOSE_GAIN_DB = BED_MENU_GAIN_DB
IDENT_GAIN_DB = 4.0
OUTRO_GAIN_DB = 4.0
STAB_GAIN_DB = 3.0
BED_MENU_PRE = 1000
BED_MENU_FADE_IN = 1500
BED_MENU_FADE_OUT = 2000
BED_MENU_STOP_BEFORE_STORY = 200
BED_CLOSE_PRE = 800            # inside the editorial -> close gap (900), never under the editorial
BED_CLOSE_FADE_IN = 800
ROOM_TONE_FADE = 1000

RADIO_ASSETS = {
    "ident": "radio_ident.wav",
    "menu_bed": "radio_menu_bed.wav",
    "close_bed": "radio_close_bed.wav",
    "stab": "radio_editorial_stab.wav",
    "outro": "radio_outro.wav",
    "room": "radio_room_tone.wav",
}
# Fall back to the legacy assets so the show still has bookends if the new
# set has not been rendered (e.g. a branch before generate_assets ran).
LEGACY_FALLBACK = {"ident": "ident.wav", "stab": "news_to_opinion.wav", "outro": "outro.wav"}

LOUDNESS_I = -16.0
LOUDNESS_TP = -1.0
LOUDNESS_LRA = 11.0
PAN = 0.07                      # A slightly left, B slightly right
MAX_FILE_SIZE = 12 * 1024 * 1024
BITRATE_LADDER = (("128k", 2), ("96k", 2), ("96k", 1))

CHAPTER_TITLES = {"MENU": "Headlines", "BRIEFS": "Also today", "FINALLY": "One more",
                  "EDITORIAL": "The editorial"}


# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------

@dataclass
class Cue:
    idx: int
    kind: str            # OPEN MENU STORY BRIEFS FINALLY THROW EDITORIAL CLOSE
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
    ident_ms: int
    stab_at_ms: int | None
    outro_at_ms: int
    news_start_ms: int
    editorial_start_ms: int | None

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
            "audio_voice_label": "Two voices",
        }


# ---------------------------------------------------------------------------
# 1. Turns
# ---------------------------------------------------------------------------

_SENT_RE = re.compile(r"[.!?](?:\s|$)")


def _editorial_paragraphs(script: str) -> list[str]:
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
        add("A", THROW_LINE, {"kind": "THROW", "segment_idx": si})
        for p in _editorial_paragraphs(editorial_script):
            verdict = len(_SENT_RE.findall(p)) <= 1 and len(p.split()) <= 18
            add("B", p, {"kind": "EDITORIAL", "segment_idx": si + 1, "verdict": verdict})
    if close_seg:
        si = len(order) + 2
        for t in close_seg.turns:
            add(t.speaker, t.text, {"kind": "CLOSE", "segment_idx": si})
    return out


# ---------------------------------------------------------------------------
# 2. Timeline
# ---------------------------------------------------------------------------

def _gap_before(prev: dict | None, cur: dict, prev_role: str | None, role: str,
                prev_verdict: bool, stab_len: int) -> int:
    G = RADIO_GAPS
    if prev is None:
        return 0
    pk, ck = prev["kind"], cur["kind"]
    if pk == "OPEN" and ck == "MENU":
        return G["open_to_menu"]
    if pk == "MENU" and ck == "MENU":
        return G["menu_item"]
    if pk == "MENU":
        return G["menu_to_story"]
    if ck == "THROW":
        return G["to_throw"]
    if pk == "THROW":
        return G["throw_to_stab"] + stab_len + G["stab_to_editorial"]
    if pk == "EDITORIAL" and ck == "EDITORIAL":
        return G["editorial_verdict"] if (prev_verdict or cur.get("verdict")) else G["editorial_paragraph"]
    if ck == "CLOSE":
        return G["editorial_to_close"] if pk == "EDITORIAL" else G["to_close_no_editorial"]
    if pk == "BRIEFS" and ck == "BRIEFS":
        return G["briefs_item"]
    if ck == "FINALLY" and pk != "FINALLY":
        return G["briefs_to_finally"]
    if prev["segment_idx"] != cur["segment_idx"]:
        return G["story_to_story"]
    return G["same_speaker"] if prev_role == role else G["speaker_change"]


def build_timeline(turns: list[tuple[TurnSpec, dict]], audio: dict[int, "AudioSegment"],
                   ident_ms: int, stab_ms: int, outro_ms: int) -> Timeline:
    cues: list[Cue] = []
    pos = max(0, ident_ms - RADIO_GAPS["ident_overlap"]) if ident_ms else RADIO_GAPS["no_ident_lead"]
    prev_meta: dict | None = None
    prev_role: str | None = None
    prev_verdict = False
    stab_at: int | None = None
    for spec, meta in turns:
        seg = audio.get(spec.idx)
        if seg is None:
            continue
        gap = _gap_before(prev_meta, meta, prev_role, spec.role, prev_verdict, stab_ms)
        if prev_meta and prev_meta["kind"] == "THROW":
            stab_at = pos + RADIO_GAPS["throw_to_stab"]
        pos += gap
        cue = Cue(idx=spec.idx, kind=meta["kind"], segment_idx=meta["segment_idx"], speaker=spec.role,
                  start_ms=pos, end_ms=pos + len(seg), title=meta.get("title"),
                  cluster_id=meta.get("cluster_id"), rank=meta.get("rank"),
                  verdict=bool(meta.get("verdict")))
        cues.append(cue)
        pos = cue.end_ms
        prev_meta, prev_role, prev_verdict = meta, spec.role, cue.verdict
    outro_at = max(0, pos - RADIO_GAPS["outro_overlap"])
    total = max(pos, outro_at + outro_ms) + RADIO_GAPS["tail"]
    first_story = next((c for c in cues if c.kind == "STORY"), None)
    news_start = first_story.start_ms if first_story else (cues[0].start_ms if cues else 0)
    throw = next((c for c in cues if c.kind == "THROW"), None)
    return Timeline(cues=cues, total_ms=total, ident_ms=ident_ms, stab_at_ms=stab_at,
                    outro_at_ms=outro_at, news_start_ms=news_start,
                    editorial_start_ms=throw.start_ms if throw else None)


def chapters_from_timeline(tl: Timeline, opinion_headline: str | None = None,
                           permalinks: dict[str, str] | None = None) -> list[dict]:
    """Chapter list (seconds). Headlines covers ident+sign-on+menu; the
    editorial chapter starts at the throw line; the sign-off folds into the
    last chapter."""
    chapters: list[dict] = []
    current_key = None
    for c in tl.cues:
        if c.kind in ("OPEN", "MENU"):
            key = ("headlines", None)
        elif c.kind in ("THROW", "EDITORIAL"):
            key = ("editorial", None)
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
            ch: dict = {"startTime": round(c.start_ms / 1000, 3), "title": title, "kind": kind}
            if kind in ("story", "finally"):
                if c.cluster_id:
                    ch["cluster_id"] = c.cluster_id
                    url = (permalinks or {}).get(c.cluster_id)
                    if url:
                        ch["url"] = url
                if c.rank:
                    ch["rank"] = c.rank
            if kind == "editorial" and opinion_headline:
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


def _loop_to(seg: "AudioSegment", ms: int, crossfade: int = 400) -> "AudioSegment":
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
    buses = {"A": _silent(tl.total_ms), "B": _silent(tl.total_ms)}
    for c in tl.cues:
        buses[c.speaker] = buses[c.speaker].overlay(audio[c.idx], position=c.start_ms)
    return buses


def bed_envelope(tl: Timeline, menu_bed_ms: int, close_bed_ms: int) -> list[dict]:
    """Where music sits. Deterministic from the cues; nothing under stories."""
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
    close = tl.first("CLOSE")
    if close and close_bed_ms:
        start = max(0, close.start_ms - BED_CLOSE_PRE)
        cues.append({"asset": "close_bed", "start": start, "end": tl.total_ms,
                     "fade_in": BED_CLOSE_FADE_IN, "fade_out": 0})
    return cues


def render_music_bus(tl: Timeline) -> tuple["AudioSegment", dict]:
    bus = _silent(tl.total_ms, channels=2)
    used: dict = {}
    ident, stab, outro = _asset("ident"), _asset("stab"), _asset("outro")
    menu_bed, close_bed, room = _asset("menu_bed"), _asset("close_bed"), _asset("room")
    if ident:
        bus = bus.overlay(ident.apply_gain(IDENT_GAIN_DB).set_channels(2), position=0)
        used["ident"] = len(ident)
    if stab and tl.stab_at_ms is not None:
        bus = bus.overlay(stab.apply_gain(STAB_GAIN_DB).set_channels(2), position=tl.stab_at_ms)
        used["stab"] = tl.stab_at_ms
    if outro:
        bus = bus.overlay(outro.apply_gain(OUTRO_GAIN_DB).set_channels(2), position=tl.outro_at_ms)
        used["outro"] = tl.outro_at_ms
    for env in bed_envelope(tl, len(menu_bed) if menu_bed else 0, len(close_bed) if close_bed else 0):
        asset = menu_bed if env["asset"] == "menu_bed" else close_bed
        asset = asset.apply_gain(BED_MENU_GAIN_DB if env["asset"] == "menu_bed" else BED_CLOSE_GAIN_DB)
        length = env["end"] - env["start"]
        seg = _loop_to(asset, length) if len(asset) < length else asset[:length]
        seg = seg.fade_in(min(env["fade_in"], length // 2)) if env["fade_in"] else seg
        seg = seg.fade_out(min(env["fade_out"], length // 2)) if env["fade_out"] else seg
        bus = bus.overlay(seg.set_channels(2), position=env["start"])
        used[env["asset"]] = (env["start"], env["end"])
    if room:
        tone = _loop_to(room, tl.total_ms).fade_in(ROOM_TONE_FADE).fade_out(ROOM_TONE_FADE)
        bus = bus.overlay(tone.set_channels(2), position=0)
        used["room"] = True
    return bus, used


# ---------------------------------------------------------------------------
# 4. ffmpeg post-production
# ---------------------------------------------------------------------------

def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def voice_chain_filter(pan: float) -> str:
    left = 1.0 - max(0.0, pan)
    right = 1.0 + min(0.0, pan)
    return ",".join([
        "highpass=f=80:poles=2",
        "equalizer=f=250:t=q:w=1.0:g=-1.5",
        "equalizer=f=4000:t=q:w=1.2:g=2.5",
        "deesser=i=0.35:m=0.5:f=0.5",
        "acompressor=threshold=-18dB:ratio=3:attack=8:release=120:makeup=3",
        f"pan=stereo|c0={left:.3f}*c0|c1={right:.3f}*c0",
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
    """EBU R128 two-pass normalisation with a limiter ahead of it."""
    ff = _ffmpeg()
    stats: dict = {}
    if not ff:
        shutil.copy(src, dst)
        return stats
    base = f"alimiter=limit={10 ** (LOUDNESS_TP / 20):.3f}:attack=5:release=50,loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}"
    p1 = _run([ff, "-hide_banner", "-nostats", "-i", str(src), "-af", f"{base}:print_format=json",
               "-f", "null", "-"])
    m = _LOUDNORM_JSON_RE.search(p1.stderr or "")
    if not m:
        print(f"  [radio] loudnorm pass 1 failed: {(p1.stderr or '')[-200:]}")
        shutil.copy(src, dst)
        return stats
    try:
        measured = json.loads(m.group(0))
    except json.JSONDecodeError:
        shutil.copy(src, dst)
        return stats
    flt = (f"{base}:measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}"
           f":measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}"
           f":offset={measured.get('target_offset', 0)}:linear=true:print_format=json")
    p2 = _run([ff, "-y", "-hide_banner", "-nostats", "-i", str(src), "-af", flt, "-ar", "44100",
               "-ac", "2", str(dst)])
    m2 = _LOUDNORM_JSON_RE.search(p2.stderr or "")
    if p2.returncode != 0 or not dst.exists():
        print(f"  [radio] loudnorm pass 2 failed: {(p2.stderr or '')[-200:]}")
        shutil.copy(src, dst)
        return {"input": measured}
    stats = {"input": measured}
    if m2:
        try:
            stats["output"] = json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass
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

    ident, stab, outro = _asset("ident"), _asset("stab"), _asset("outro")
    tl = build_timeline(turns, res.audio, len(ident) if ident else 0, len(stab) if stab else 0,
                        len(outro) if outro else 0)
    spoken_ms = sum(c.end_ms - c.start_ms for c in tl.cues)
    wpm = words / (spoken_ms / 60000) if spoken_ms else 0
    print(f"  [radio] timeline {tl.total_ms / 1000:.1f}s, speech {spoken_ms / 1000:.1f}s, {wpm:.0f} wpm, "
          f"news at {tl.news_start_ms / 1000:.1f}s, editorial at "
          f"{(tl.editorial_start_ms or 0) / 1000:.1f}s")

    work = Path(tempfile.mkdtemp(prefix="void-radio-"))
    try:
        buses = render_voice_buses(tl, res.audio)
        a = process_voice_bus(buses["A"], -PAN, work, "A")
        b = process_voice_bus(buses["B"], +PAN, work, "B")
        music, used = render_music_bus(tl)
        print(f"  [radio] music cues: {used}")
        mix = _silent(tl.total_ms, channels=2).overlay(a).overlay(b).overlay(music)
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
            voices = f"{res.engine}:{eng.voice_id('A')}+{eng.voice_id('B')}"
        except StopIteration:
            from briefing.tts_engines import engine_chain
            eng = next((e for e in engine_chain() if e.name == res.engine), None)
            if eng:
                voices = f"{res.engine}:{eng.voice_id('A')}+{eng.voice_id('B')}"

        return RadioResult(
            audio_url=audio_url, duration_seconds=duration_s, file_size=len(audio_bytes),
            news_start_seconds=round(tl.news_start_ms / 1000, 3),
            opinion_start_seconds=round(tl.editorial_start_ms / 1000, 3) if tl.editorial_start_ms is not None else None,
            chapters=chapters, engine=res.engine, voices=voices,
            timing={"tts_s": round(tts_s, 1), "total_s": round(time.time() - t0, 1),
                    "wpm": round(wpm), "engine": res.timing, "loudness": stats.get("output"),
                    "bitrate": chosen[0], "channels": chosen[1]},
            audio_script=rundown.to_text(), local_path=local_path,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)
