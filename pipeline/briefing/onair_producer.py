"""On Air: the newsroom, produced. Voices, score, mix, master, chapters.

    show (onair_show.Show) + opinion script
      -> turns, normalised for speech, Kokoro only (never another engine)
      -> per-line voice chain: trim, level to -20 LUFS, house warmth EQ, re-level, peak control
      -> timeline from the synthesised lengths and the gap table (chapters exact by construction)
      -> the score, composed for THIS timeline (onair_score): title, beds that enter and leave
         where the conversation asks for them, the page-turn, the opinion entrance, the outro
      -> levelled to the standard, ducked under the voices with the eased pre-roll, measured
      -> mix over room tone, house promo post-roll, loudnorm to -16 LUFS / -1.5 dBTP, MP3
      -> ID3 chapters, Podcasting 2.0 sidecar, the static tree (frontend/public/audio/<edition>)

Running order, what the listener hears:

    COLD        A, one line in the clear over room tone              [chapter: Today]
    theme       featured, the sign-on starts over its last third
    TITLE       A: sign-on, the day; B: the framing                   [bed: lead, enters under the framing]
    LEAD        A reads the story in passages, B takes the reaction
                and the coverage                                       [bed out after the second passage;
                                                                       back for the last, the coverage]
    page-turn   the motif's cell, in the clear                        [chapter: the lead's title, rank 1]
    SECOND      B leads, A takes the coverage                          [bed: second, same shape]
    page-turn                                                          [chapter: rank 2]
    DESK        "The rest of the desk." ranks 3-8, alternating         [bed: desk, the pulse, throughout]
    entrance    featured, minor shading, A introduces over its tail    [chapter: Void Opinion]
    OPINION     A: "This is Void Opinion." then A reads it as written  [bed: opinion under the first two and
                                                                       the last passage]
    CLOSE       A, the sign-off                                        [bed: close]
    outro       featured, resolving to the low D; the house promo rides it   [chapter: Also from Void]

Every decision about level is a number in onair_score; this file places things.
"""

from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

try:
    from briefing import onair_score as S
    from briefing.onair_show import Show, Segment, DESK_LEAD
    from briefing.spoken_text import normalize_for_speech
    from briefing.tts_engines import TurnSpec, KokoroEngine, synthesize_with_fallback, PYDUB_AVAILABLE
except ImportError:  # pragma: no cover - imported as pipeline.briefing.onair_producer
    from pipeline.briefing import onair_score as S  # type: ignore
    from pipeline.briefing.onair_show import Show, Segment, DESK_LEAD  # type: ignore
    from pipeline.briefing.spoken_text import normalize_for_speech  # type: ignore
    from pipeline.briefing.tts_engines import TurnSpec, KokoroEngine, synthesize_with_fallback, PYDUB_AVAILABLE  # type: ignore

try:
    from pydub import AudioSegment
except ImportError:  # pragma: no cover
    AudioSegment = None

SR = S.SR
SITE_URL = os.environ.get("PODCAST_SITE_URL", "https://news.voidvision.org").rstrip("/")

# Casting, rev 5 (CEO 2026-11-07, after hearing rev 4): TWO voices. The
# anchor, A, is af_aoede (rev 4's Opinion voice): the cold open, the sign-on,
# the lead, the close, and Void Opinion, which A reads whole. B, the second
# anchor, is male, the best of Kokoro's men on the audition of 2026-11-08
# (docs/ON-AIR-CONVERSATION.md "Voices" has the table). With one voice on
# both sides, the firewall between the news and the Opinion is the music and
# the words, never the voice. VOID_KOKORO_VOICE_A/B override; there is no C.
VOICES = {
    "A": os.environ.get("VOID_KOKORO_VOICE_A", "af_aoede"),
    "B": os.environ.get("VOID_KOKORO_VOICE_B", "am_puck"),
}
SPEED = float(os.environ.get("VOID_KOKORO_SPEED", "0.95") or 0.95)
PAN = {"A": -0.14, "B": 0.14}     # two positions: the anchor a touch left, the second anchor a touch right

# Silence grammar, seconds. A conversation breathes more slowly than a bulletin.
GAPS = {
    "cold_in": 0.6,            # room tone before the first word
    "cold_to_theme": 1.1,
    "signon_into_theme": 2.4,  # (rev 3: the sign-on lands on the theme's downbeat, S.THEME_DOWNBEAT_S)
    "title_lines": 0.7,
    "title_to_lead": 1.3,
    "handover": 0.72,          # one anchor's passage ends, the other's begins
    "handover_bedded": 1.25,   # while a bed plays, the music gets a breath at the handover
    "same_voice": 0.42,        # the same anchor's next passage
    "story_to_pageturn": 0.7,
    "pageturn_to_story": 0.35,  # the next voice starts this long before the page-turn ends
    "desk_lead_to_item": 0.6,
    "desk_items": 0.55,
    # Rev 5: the desk STOPS, a silence is held, then "Void Opinion" enters.
    "desk_to_stop": 0.5,       # the desk bed's closing hit lands this long after the desk's last word;
                               # the bed ends S.STOP_RING_S (2.6 s) later, once the ring is gone
    "stop_to_entrance": 1.6,   # the held silence (the -70 dBFS floor only) between the bed's end and the entrance
    "a_into_entrance": round(S.ENTRANCE_S - S.ENTRANCE_VOICE_S, 2),   # 1.6: A speaks once the hook's last note has landed
    "opinion_paragraphs": 0.65,
    "opinion_to_close": 1.0,
    "desk_to_close": 1.0,
    "outro_into_signoff": 0.4, # the outro starts this long before the sign-off ends
    "tail": 0.6,
}
ROOM_TONE_DBFS = -70.0     # a studio: present only so a silence is never digital zero (CEO 2026-11-07: -57 read as noise)
LOUDNESS_I, LOUDNESS_TP, LOUDNESS_LRA = -16.0, -1.5, 11.0
MAX_FILE_SIZE = 12 * 1024 * 1024
BITRATE_LADDER = (("128k", 2), ("96k", 2), ("96k", 1))
PHONE_VOICE_MARGIN_DB = 12.0

# Where a bed leaves and returns: it plays under this many passages, goes
# out, and comes back under the last passage (the coverage, or the Opinion's
# last paragraph). A long segment gets one visit in its middle.
BED_OUT_AFTER_PASSAGES = {"LEAD": 2, "SECOND": 1, "OPINION": 2}
ANCHOR_OPINION_VOICE = "A"       # rev 5: the anchor reads Void Opinion
OPINION_CHAPTER_TITLE = "Void Opinion"   # CEO 2026-11-07; the chapter's kind stays "opinion"


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------

@dataclass
class Cue:
    kind: str            # COLD TITLE LEAD SECOND DESK OPINION CLOSE
    role: str            # A B C
    text: str
    start: float = 0.0
    end: float = 0.0
    idx: int = -1
    seg_title: str = ""
    rank: int | None = None
    cluster_id: str | None = None
    exchange: int = 0    # index of the passage within its segment (LEAD/SECOND/OPINION)
    is_question: bool = False   # kept for the row; a newsroom script carries none


@dataclass
class MusicCue:
    role: str            # featured | bed | transition
    name: str            # theme, lead, second, desk, opinion, close, pageturn, entrance, outro
    start: float
    end: float
    audio: np.ndarray | None = None
    findings: list = field(default_factory=list)


@dataclass
class Timeline:
    cues: list[Cue]
    music: list[MusicCue]
    total: float
    news_start: float
    opinion_start: float | None
    outro_at: float
    last_word: float


@dataclass
class ShowResult:
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
            # rev 5: two voices with or without the Opinion (the anchor reads it)
            "audio_voice_label": "Two voices",
        }


_SENT_RE = re.compile(r"[.!?](?:\s|$)")


def opinion_paragraphs(script: str | None) -> list[str]:
    if not script:
        return []
    paras = [p.strip() for p in re.split(r"\n\s*\n", script.strip()) if p.strip()]
    out = []
    for p in paras:
        p = re.sub(r"^\s*[A-C]\s*:\s*", "", p)   # a stray voice tag
        p = re.sub(r"\s+", " ", p)
        if p:
            out.append(p)
    return out


def build_cues(show: Show, opinion_script: str | None = None) -> list[Cue]:
    """The spoken lines in order, each a passage. The Opinion comes from the
    show's own OPINION segment (A introduces it and reads it, rev 5);
    `opinion_script`, a monologue, is read by the anchor only when the show
    carries no OPINION segment (a script from before 2026-11-07)."""
    cues: list[Cue] = []
    say = show.say or None
    for s in show.segments:
        k = 0
        for t in s.turns:
            text = normalize_for_speech(t.text, say)
            if not text.strip():
                continue
            cues.append(Cue(kind=s.kind, role=t.speaker, text=text, seg_title=s.title, rank=s.rank,
                            cluster_id=s.cluster_id, exchange=k, is_question=t.is_question))
            k += 1
    if opinion_script and not any(c.kind == "OPINION" for c in cues):
        paras = opinion_paragraphs(opinion_script)
        if paras:
            close_i = next((i for i, c in enumerate(cues) if c.kind == "CLOSE"), len(cues))
            op = [Cue(kind="OPINION", role=ANCHOR_OPINION_VOICE, text=normalize_for_speech(p, None), exchange=k)
                  for k, p in enumerate(paras)]
            cues = cues[:close_i] + op + cues[close_i:]
    for i, c in enumerate(cues):
        c.idx = i
    return cues


def _gap(prev: Cue | None, cur: Cue, bedded: set[tuple[str, int]] = frozenset()) -> float:
    if prev is None:
        return GAPS["cold_in"]
    if prev.kind != cur.kind:
        return {("COLD", "TITLE"): 0.0, ("TITLE", "LEAD"): GAPS["title_to_lead"],
                ("DESK", "OPINION"): 0.0, ("OPINION", "CLOSE"): GAPS["opinion_to_close"],
                ("DESK", "CLOSE"): GAPS["desk_to_close"]}.get((prev.kind, cur.kind), 0.8)
    if cur.kind == "TITLE":
        return GAPS["title_lines"]
    if cur.kind in ("LEAD", "SECOND", "OPINION"):
        if prev.role == cur.role:
            return GAPS["opinion_paragraphs"] if cur.kind == "OPINION" else GAPS["same_voice"]
        return GAPS["handover_bedded"] if (cur.kind, cur.exchange) in bedded else GAPS["handover"]
    if cur.kind == "DESK":
        return GAPS["desk_lead_to_item"] if prev.text.startswith(DESK_LEAD.split(".")[0]) else GAPS["desk_items"]
    return 0.8


def _mid_visit(music: list[MusicCue], name: str, seg: list[Cue], out_at: float, tail_start: float) -> None:
    """A long segment gets the bed back for one passage in its middle, so
    the music is never gone for minutes at a stretch."""
    ex = sorted({c.exchange for c in seg})
    if len(ex) < 6:
        return
    mid = [c for c in seg if c.exchange == ex[len(ex) // 2]]
    if not mid:
        return
    start, end = mid[0].start - 2.2, mid[-1].end + 1.0
    if start > out_at + 8.0 and end < tail_start - 8.0:
        music.append(MusicCue("bed", name, start, end))


def build_timeline(cues: list[Cue], lengths: dict[int, float], v: S.Voicing) -> Timeline:
    """Place every voice line and every music cue. Music lengths come from
    the renderers' fixed durations (theme 7.0, page-turn 3.4, entrance 6.0,
    outro 14.0); beds are composed to the span they are given."""
    theme_len, pageturn_len, entrance_len, outro_len = S.THEME_S, S.PAGETURN_S, S.ENTRANCE_S, S.OUTRO_S
    # The passages a bed plays under: the first few and the last (the coverage).
    bedded: set[tuple[str, int]] = set()
    for kind in ("LEAD", "SECOND", "OPINION"):
        ex = sorted({c.exchange for c in cues if c.kind == kind})
        if ex:
            k = BED_OUT_AFTER_PASSAGES.get(kind, 1)
            bedded.update((kind, e) for e in ex[:k + 1])
            bedded.add((kind, ex[-1]))
            if len(ex) >= 6:
                bedded.add((kind, ex[len(ex) // 2]))   # a visit in the middle of a long segment
    music: list[MusicCue] = []
    t = 0.0
    prev: Cue | None = None
    news_start = 0.0
    opinion_start: float | None = None
    for c in cues:
        length = lengths[c.idx]
        if prev is None:
            t = GAPS["cold_in"]
        elif prev.kind == "COLD" and c.kind == "TITLE":
            theme_at = prev.end + GAPS["cold_to_theme"]
            music.append(MusicCue("featured", "theme", theme_at, theme_at + theme_len))
            t = theme_at + S.THEME_DOWNBEAT_S + 0.12      # the sign-on lands on the downbeat
        elif prev.kind in ("LEAD", "SECOND") and c.kind != prev.kind:
            pt_at = prev.end + GAPS["story_to_pageturn"]
            music.append(MusicCue("transition", "pageturn", pt_at, pt_at + pageturn_len))
            t = pt_at + pageturn_len - GAPS["pageturn_to_story"]
        elif prev.kind == "DESK" and c.kind == "OPINION":
            # the desk bed stops on a hit, rings out, the floor is held, then the entrance
            stop_end = prev.end + GAPS["desk_to_stop"] + S.STOP_RING_S
            en_at = stop_end + GAPS["stop_to_entrance"]
            music.append(MusicCue("featured", "entrance", en_at, en_at + entrance_len))
            opinion_start = en_at
            t = en_at + S.ENTRANCE_VOICE_S
        else:
            t = prev.end + _gap(prev, c, bedded)
        c.start, c.end = t, t + length
        if c.kind == "LEAD" and news_start == 0.0:
            news_start = c.start
        prev = c
    last_word = cues[-1].end if cues else 0.0
    outro_at = last_word - GAPS["outro_into_signoff"]
    music.append(MusicCue("featured", "outro", outro_at, outro_at + outro_len))
    total = outro_at + outro_len + GAPS["tail"]

    # Beds: where the conversation asks for them.
    def seg_cues(kind: str) -> list[Cue]:
        return [c for c in cues if c.kind == kind]

    title = seg_cues("TITLE")

    def story_beds(name: str, seg: list[Cue], start: float, out_pad: float) -> None:
        k = min(BED_OUT_AFTER_PASSAGES[name.upper()], max(1, len(seg) - 1))
        out_at = seg[k - 1].end + out_pad
        music.append(MusicCue("bed", name, start, min(out_at + 3.0, seg[-1].end + 0.5)))
        tail = seg[-1]
        if tail.start - 2.0 > out_at + 6.0:
            music.append(MusicCue("bed", name, tail.start - 2.2, tail.end + GAPS["story_to_pageturn"] + 0.2))
        _mid_visit(music, name, seg, out_at, tail.start)

    lead = seg_cues("LEAD")
    if lead:
        theme_end = next((m.end for m in music if m.name == "theme"), lead[0].start - 2.0)
        start = min(theme_end - 2.6, (title[1].start - 1.6) if len(title) > 1 else lead[0].start - 2.0)
        story_beds("lead", lead, start, 1.2)
    second = seg_cues("SECOND")
    if second:
        pt = next((m for m in music if m.name == "pageturn" and m.start < second[0].start), None)
        start = (pt.start + 1.6) if pt else second[0].start - 1.8
        story_beds("second", second, start, 1.0)
    desk = seg_cues("DESK")
    if desk:
        pts = [m for m in music if m.name == "pageturn" and m.start < desk[0].start]
        start = (pts[-1].start + 1.6) if pts else desk[0].start - 1.8
        if any(c.kind == "OPINION" for c in cues):
            # ends on the stop: the hit at desk_to_stop after the last word, the ring after it
            desk_end = desk[-1].end + GAPS["desk_to_stop"] + S.STOP_RING_S
        else:
            desk_end = desk[-1].end + 1.2
        music.append(MusicCue("bed", "desk", start, desk_end))
    op = seg_cues("OPINION")
    if op:
        en = next((m for m in music if m.name == "entrance"), None)
        start = (en.end - 1.0) if en else op[0].start - 2.0
        k = min(BED_OUT_AFTER_PASSAGES["OPINION"], max(1, len(op) - 1))
        first_out = op[k - 1].end + 1.0
        music.append(MusicCue("bed", "opinion", start, min(first_out + 2.5, op[-1].end)))
        tail = op[-1]
        if tail.start - 2.0 > first_out + 8.0:
            music.append(MusicCue("bed", "opinion", tail.start - 2.2, tail.end + 0.8))
    close = seg_cues("CLOSE")
    if close:
        start = close[0].start - 1.6
        music.append(MusicCue("bed", "close", start, outro_at + 1.8))
    for m in music:
        if m.role == "bed" and m.end - m.start < 5.0:
            m.end = m.start + 5.0     # a bed of under 4 s is not a bed (A29)
    music.sort(key=lambda m: m.start)
    return Timeline(cues=cues, music=music, total=total, news_start=news_start,
                    opinion_start=opinion_start, outro_at=outro_at, last_word=last_word)


# ---------------------------------------------------------------------------
# Voices
# ---------------------------------------------------------------------------

def _seg_to_np(seg: "AudioSegment") -> np.ndarray:
    seg = seg.set_frame_rate(SR).set_channels(1).set_sample_width(2)
    x = np.frombuffer(seg.raw_data, dtype=np.int16).astype(np.float64) / 32768.0
    return x


def trim_silence(x: np.ndarray, thresh_db: float = -45.0, keep_s: float = 0.06) -> np.ndarray:
    if len(x) == 0:
        return x
    n = int(0.01 * SR)
    m = len(x) // n
    if m == 0:
        return x
    rms = np.sqrt(np.mean(x[: m * n].reshape(m, n) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms)
    loud = np.where(db > thresh_db)[0]
    if loud.size == 0:
        return x
    a = max(0, loud[0] * n - int(keep_s * SR))
    b = min(len(x), (loud[-1] + 1) * n + int(keep_s * SR))
    return x[a:b]


def spectral_gate(x: np.ndarray, *, reduction_db: float = 14.0, ratio: float = 2.5) -> np.ndarray:
    """A light spectral gate (the film studio's denoise, in one pass): the
    noise profile is each bin's 15th-percentile magnitude over the line; a
    bin under `ratio` times its profile is lowered by `reduction_db`, with
    the gain smoothed over time so nothing flutters. Speech is untouched;
    the residue between words goes down."""
    from scipy.signal import stft, istft
    if len(x) < 4096:
        return x
    nper = 1024
    f, t, Z = stft(x, fs=SR, nperseg=nper, noverlap=nper * 3 // 4, padded=True)
    mag = np.abs(Z)
    profile = np.percentile(mag, 15, axis=1, keepdims=True) + 1e-9
    mask = (mag < ratio * profile).astype(np.float64)
    # smooth the mask over time (a 5-frame moving mean) so the gain never steps
    k = np.ones(5) / 5.0
    mask = np.apply_along_axis(lambda row: np.convolve(row, k, mode="same"), 1, mask)
    gain = 1.0 - mask * (1.0 - 10 ** (-reduction_db / 20))
    _, y = istft(Z * gain, fs=SR, nperseg=nper, noverlap=nper * 3 // 4)
    y = y[: len(x)]
    if len(y) < len(x):
        y = np.pad(y, (0, len(x) - len(y)))
    return y


def voice_chain(x: np.ndarray) -> tuple[np.ndarray, dict]:
    """A13/A38 for one synthetic line: trim, a light spectral gate, level to
    the dialogue target, the house warmth, re-level, then peak control that
    only touches a line whose crest would reach the ceiling."""
    x = trim_silence(x)
    x = spectral_gate(x)
    x, g1 = S.level_to(x, S.DIALOGUE_LUFS)
    x = S.voice_house_eq(x)
    x, g2 = S.level_to(x, S.DIALOGUE_LUFS)
    peak = float(np.max(np.abs(x))) if len(x) else 0.0
    reduced = 0.0
    ceiling = 10 ** (-4.0 / 20)      # -4 dBFS sample peak
    if peak > ceiling:
        # a gentle knee: compress only the part over the ceiling
        over = np.abs(x) > ceiling
        y = x.copy()
        y[over] = np.sign(x[over]) * (ceiling + (np.abs(x[over]) - ceiling) * 0.35)
        reduced = 20 * math.log10(peak / float(np.max(np.abs(y))))
        x, _ = S.level_to(y, S.DIALOGUE_LUFS)
    return x, {"gain_db": round(g1 + g2, 2), "peak_reduced_db": round(reduced, 2)}


def synthesize(cues: list[Cue], *, engines: list | None = None) -> tuple[dict[int, np.ndarray], object] | None:
    """Kokoro only: a show never falls to another engine. Returns the voiced
    lines (after the chain) and the engine result."""
    engines = engines if engines is not None else [KokoroEngine(voices=VOICES, speed={"A": SPEED, "B": SPEED})]
    turns = [TurnSpec(idx=c.idx, role=c.role, text=c.text) for c in cues]
    required = {c.idx for c in cues if c.kind in ("TITLE", "CLOSE")}
    res = synthesize_with_fallback(turns, engines=engines, required=required, min_coverage=0.98)
    if res is None:
        return None
    voiced: dict[int, np.ndarray] = {}
    stats = []
    for c in cues:
        seg = res.audio.get(c.idx)
        if seg is None:
            continue
        x, st = voice_chain(_seg_to_np(seg))
        voiced[c.idx] = x
        stats.append(st)
    if stats:
        g = [s["gain_db"] for s in stats]
        print(f"  [onair] voice chain: {len(stats)} lines levelled to {S.DIALOGUE_LUFS} LUFS "
              f"(gain {min(g):+.1f}..{max(g):+.1f} dB), {sum(1 for s in stats if s['peak_reduced_db'] > 0)} peak-controlled")
    return voiced, res


# ---------------------------------------------------------------------------
# Score placement
# ---------------------------------------------------------------------------

STOP_SILENCE_MAX_S = 3.0   # a bed whose end is followed by the entrance within this long is the one that stops


def bed_ending(tl: Timeline, m: MusicCue) -> tuple[str, MusicCue | None]:
    """How a bed ends, read from the timeline: ("stop", the entrance) when the
    entrance follows it within STOP_SILENCE_MAX_S, the news stopping before
    the Opinion (rev 5); ("rise", that cue) when a page-turn or the outro
    starts within 2.5 s of its end; ("out", None) otherwise."""
    entrance = next((c for c in tl.music if c.name == "entrance" and -0.5 <= c.start - m.end <= STOP_SILENCE_MAX_S), None)
    if entrance is not None:
        return "stop", entrance
    leads_into = next((c for c in tl.music if c.role != "bed" and c.name not in ("theme", "entrance")
                       and abs(c.start - m.end) <= 2.5), None)
    return ("rise", leads_into) if leads_into is not None else ("out", None)


def render_score(tl: Timeline, v: S.Voicing) -> tuple[np.ndarray, list[str]]:
    """Compose and level every music cue for this timeline, duck it under the
    voices, measure it, and return the music bus with the findings logged."""
    n = int(math.ceil(tl.total * SR)) + SR
    bus = np.zeros((n, 2))          # the music is stereo (rev 3)
    notes: list[str] = []
    ir = None
    speech = [(c.start, c.end) for c in tl.cues]
    bed_peaks: dict[str, float] = {}

    def gaps_in(m: MusicCue) -> list[tuple[float, float]]:
        out = []
        t = m.start
        for s, e in sorted(speech):
            if e <= m.start or s >= m.end:
                continue
            if s > t:
                out.append((t - m.start, s - m.start))
            t = max(t, e)
        if m.end > t:
            out.append((t - m.start, m.end - m.start))
        return out

    # beds first, so a page-turn can be levelled to the bed it leads into
    for m in [m for m in tl.music if m.role == "bed"]:
        dur = m.end - m.start
        ending, leads_into = bed_ending(tl, m)
        x = S.render_bed(v, m.name, dur, ending=ending)
        x, g = S.level_bed(x, gaps_in(m))
        findings = S.check_cue(x, "bed", gaps=gaps_in(m))
        if any(f.id in ("score-repetition", "bed-breathing", "bed-low-end") for f in findings):
            # one more draw of the dice before it ships with the note
            alt = S.Voicing(seed=v.seed + 101, tempo_bpm=v.tempo_bpm, music=S.M.voicing_for(v.seed + 101))
            x2 = S.render_bed(alt, m.name, dur, ending=ending)
            x2, g2 = S.level_bed(x2, gaps_in(m))
            f2 = S.check_cue(x2, "bed", gaps=gaps_in(m))
            if len(f2) < len(findings):
                x, g, findings = x2, g2, f2
        # A bed that leads into a page-turn or the outro rises into it (CEO
        # 2026-11-07, second ear test); the rise happens AFTER the level is
        # set on the gaps, so the bed's resting level is the standard's and
        # only its last seconds climb. A bed the entrance follows STOPS
        # instead (rev 5): no rise, the hit, the ring, the held silence.
        rise = 0.0
        if ending == "rise" and leads_into is not None:
            # never above the featured cue it hands over to
            st = S.lufs_shortterm(x)
            top = float(np.max(st)) if st.size else S.BED_LUFS
            rise = max(0.0, min(S.RISE_DB, S.FEATURED_LUFS + 1.0 - top))
            x = S.rise_into(x, rise_db=rise, hold_s=max(0.0, m.end - leads_into.start))
        m.audio = x
        m.findings = findings
        bed_peaks[m.name] = max(bed_peaks.get(m.name, -99.0), S.bed_peak_lufs(x))
        notes.append(f"bed {m.name} {m.start:.1f}-{m.end:.1f}s gain {g:+.1f}" +
                     (f" rise +{rise:.0f} into {leads_into.name}" if ending == "rise" and leads_into is not None else "") +
                     (f" stop, {leads_into.start - m.end:.1f} s of floor before the {leads_into.name}"
                      if ending == "stop" and leads_into is not None else "") +
                     (" " + "; ".join(f.id for f in findings) if findings else ""))
    for m in [m for m in tl.music if m.role != "bed"]:
        nxt = None
        if m.name == "theme":
            x = S.render_theme(v, ir=ir)
            x, g = S.level_featured(x)
        elif m.name == "entrance":
            x = S.render_entrance(v, ir=ir)
            x, g = S.level_featured(x)
        elif m.name == "outro":
            x = S.render_outro(v, ir=ir)
            x, g = S.level_featured(x)
        else:
            x = S.render_transition(v, ir=ir)
            nxt = next((b for b in tl.music if b.role == "bed" and b.start >= m.start - 0.5), None)
            peak = bed_peaks.get(nxt.name, S.BED_LUFS + 4.0) if nxt else S.BED_LUFS + 4.0
            x, g = S.level_transition(x, peak)
        role = "transition" if m.role == "transition" else "featured"
        m.findings = S.check_cue(x, role, bed_peak_lufs=bed_peaks.get(nxt.name) if nxt is not None else None)
        m.audio = x
        notes.append(f"{m.role} {m.name} {m.start:.1f}s gain {g:+.1f}" +
                     (" " + "; ".join(f.id for f in m.findings) if m.findings else ""))
    for m in tl.music:
        if m.audio is not None:
            S.place(bus, m.audio[: int((m.end - m.start) * SR) + SR], m.start)
    env = S.duck_envelope(tl.total + 1.0, speech)
    for f in S.check_duck(env):
        notes.append(f.id + ": " + f.detail)
    bus = S.apply_envelope(bus, env)
    return bus[:n], notes


def _phone_bands(voice: np.ndarray, music: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    from scipy import signal
    sos_hp = signal.butter(4, 150.0, btype="high", fs=SR, output="sos")
    sos_bp = signal.butter(2, [150.0, 4000.0], btype="band", fs=SR, output="sos")
    v = signal.sosfilt(sos_bp, signal.sosfilt(sos_hp, voice))
    m = signal.sosfilt(sos_bp, signal.sosfilt(sos_hp, music))
    return v, m


def phone_windows(voice: np.ndarray, music: np.ndarray, cues: list[Cue]) -> list[tuple[float, float]]:
    """The mix as a small speaker plays it: mono, a 150 Hz high-pass, a roll-off
    over 8 kHz. Inside every spoken line, on 1 s windows every 0.5 s that hold
    speech (within 10 dB of the line's mean), the voice's level in 150 Hz to
    4 kHz over the music's. Returns (window start, margin dB) for every window."""
    v, m = _phone_bands(voice, music)
    out: list[tuple[float, float]] = []
    for c in cues:
        a0, b0 = int(c.start * SR), int(c.end * SR)
        if b0 - a0 < SR:
            continue
        line_mean = 10 * math.log10(float(np.mean(v[a0:b0] ** 2)) + 1e-12)
        t = c.start
        while t + 1.0 <= c.end:
            a, b = int(t * SR), int((t + 1.0) * SR)
            pv = float(np.mean(v[a:b] ** 2)) + 1e-12
            pm = float(np.mean(m[a:b] ** 2)) + 1e-12
            if 10 * math.log10(pv) >= line_mean - 10.0:
                out.append((t, 10 * math.log10(pv / pm)))
            t += 0.5
    return out


def phone_check(voice: np.ndarray, music: np.ndarray, cues: list[Cue]) -> tuple[float, float]:
    """Minimum phone margin in dB and where it was."""
    w = phone_windows(voice, music, cues)
    if not w:
        return 99.0, 0.0
    t, margin = min(w, key=lambda x: x[1])
    return margin, t


def phone_fix(voice: np.ndarray, music: np.ndarray, cues: list[Cue], *, target_db: float = PHONE_VOICE_MARGIN_DB,
              passes: int = 3) -> tuple[np.ndarray, int]:
    """Lower the music ONLY where a spoken window is under the margin: an
    extra dip of the shortfall, eased in and out over 0.6 s, so the bed keeps
    its level everywhere else (CEO 2026-11-07: more music, not less).
    Returns the music and the number of windows that needed it."""
    fixed = 0
    for _ in range(passes):
        failing = [(t, m) for t, m in phone_windows(voice, S.mono(music), cues) if m < target_db]
        if not failing:
            break
        step = 0.01
        env = np.zeros(int(len(music) / SR / step) + 2)
        for t, m in failing:
            need = target_db - m + 0.5
            i0, i1 = int(t / step), int((t + 1.0) / step)
            env[i0:i1] = np.minimum(env[i0:i1], -need)
        # ease every edge: a 0.6 s raised cosine on both sides of each dip
        k = int(0.6 / step)
        ramp = 0.5 - 0.5 * np.cos(np.linspace(0, math.pi, k))
        smooth = env.copy()
        for i in range(1, len(env)):
            if env[i] < env[i - 1]:
                a = max(0, i - k)
                smooth[a:i] = np.minimum(smooth[a:i], env[i] * ramp[-(i - a):])
            if env[i] > env[i - 1]:
                b = min(len(env), i + k)
                smooth[i:b] = np.minimum(smooth[i:b], env[i - 1] * (1 - ramp[: b - i]))
        music = S.apply_envelope(music, smooth, step)
        fixed += len(failing)
    return music, fixed


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

def chapters_from_timeline(tl: Timeline, *, opinion_headline: str | None, permalinks: dict[str, str] | None) -> list[dict]:
    chapters: list[dict] = []
    seen: set[str] = set()
    for c in tl.cues:
        if c.kind in ("COLD", "TITLE"):
            key = "open"
        elif c.kind == "CLOSE":
            continue
        else:
            key = c.kind
        if key in seen:
            continue
        seen.add(key)
        if key == "open":
            ch = {"startTime": 0.0, "title": "Today", "kind": "headlines"}
        elif c.kind in ("LEAD", "SECOND"):
            ch = {"startTime": round(c.start, 3), "title": c.seg_title or c.kind.title(), "kind": "story"}
            if c.rank:
                ch["rank"] = c.rank
            if c.cluster_id:
                ch["cluster_id"] = c.cluster_id
                url = (permalinks or {}).get(c.cluster_id)
                if url:
                    ch["url"] = url
            pt = next((m for m in tl.music if m.name == "pageturn" and m.end > c.start - 0.5 and m.start < c.start), None)
            if pt:
                ch["startTime"] = round(pt.start, 3)
        elif c.kind == "DESK":
            ch = {"startTime": round(c.start, 3), "title": "The desk", "kind": "briefs"}
            pt = next((m for m in tl.music if m.name == "pageturn" and m.end > c.start - 0.5 and m.start < c.start), None)
            if pt:
                ch["startTime"] = round(pt.start, 3)
        else:  # OPINION
            ch = {"startTime": round(tl.opinion_start if tl.opinion_start is not None else c.start, 3),
                  "title": OPINION_CHAPTER_TITLE, "kind": "opinion"}
            if opinion_headline:
                ch["subtitle"] = opinion_headline
        chapters.append(ch)
    for i, ch in enumerate(chapters):
        ch["endTime"] = chapters[i + 1]["startTime"] if i + 1 < len(chapters) else round(tl.total, 3)
    return chapters


def chapters_sidecar(chapters: list[dict], title: str) -> bytes:
    return json.dumps({"version": "1.2.0", "title": title, "author": "Void News", "chapters": chapters},
                      indent=1).encode("utf-8")


# ---------------------------------------------------------------------------
# Mastering
# ---------------------------------------------------------------------------

def _ffmpeg() -> str | None:
    return shutil.which("ffmpeg")


def _run(cmd: list[str], timeout: int = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


_LOUDNORM_JSON_RE = re.compile(r"\{[^{}]*\"input_i\"[^{}]*\}", re.DOTALL)


def write_wav(path: Path, stereo: np.ndarray) -> None:
    import wave
    pcm = (np.clip(stereo, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def loudnorm_two_pass(src: Path, dst: Path) -> dict:
    """EBU R128 in LINEAR mode with the limiter anchored (radio_producer's
    method), to -16 LUFS integrated and -1.5 dBTP."""
    ff = _ffmpeg()
    if not ff:
        shutil.copy(src, dst)
        return {}
    ln = f"loudnorm=I={LOUDNESS_I}:TP={LOUDNESS_TP}:LRA={LOUDNESS_LRA}"

    def measure(chain: str) -> dict | None:
        pr = _run([ff, "-hide_banner", "-nostats", "-i", str(src), "-af", f"{chain}:print_format=json", "-f", "null", "-"])
        mm = _LOUDNORM_JSON_RE.search(pr.stderr or "")
        try:
            return json.loads(mm.group(0)) if mm else None
        except json.JSONDecodeError:
            return None

    measured = measure(ln)
    if measured is None:
        shutil.copy(src, dst)
        return {}
    pre = ""
    try:
        gain = LOUDNESS_I - float(measured["input_i"])
        if float(measured["input_tp"]) + gain > LOUDNESS_TP - 0.5:
            limit_db = LOUDNESS_TP - gain - 0.5
            pre = f"alimiter=limit={10 ** (limit_db / 20):.4f}:attack=5:release=80:level=false,"
            re_m = measure(pre + ln)
            if re_m is not None:
                measured = re_m
    except (KeyError, ValueError):
        pass
    flt = (f"{pre}{ln}:measured_I={measured['input_i']}:measured_LRA={measured['input_lra']}"
           f":measured_TP={measured['input_tp']}:measured_thresh={measured['input_thresh']}"
           f":offset={measured.get('target_offset', 0)}:linear=true:print_format=json")
    p2 = _run([ff, "-y", "-hide_banner", "-nostats", "-i", str(src), "-af", flt, "-ar", "44100", "-ac", "2", str(dst)])
    stats: dict = {"input": measured, "limiter": bool(pre)}
    m2 = _LOUDNORM_JSON_RE.search(p2.stderr or "")
    if p2.returncode != 0 or not dst.exists():
        shutil.copy(src, dst)
        return stats
    if m2:
        try:
            stats["output"] = json.loads(m2.group(0))
        except json.JSONDecodeError:
            pass
    mode = (stats.get("output") or {}).get("normalization_type")
    if mode and mode != "linear":
        print(f"  [onair] WARNING loudnorm fell back to {mode} mode")
    return stats


def encode_mp3(src: Path, dst: Path, bitrate: str, channels: int) -> bool:
    ff = _ffmpeg()
    if not ff:
        return False
    p = _run([ff, "-y", "-hide_banner", "-nostats", "-i", str(src), "-codec:a", "libmp3lame", "-b:a", bitrate,
              "-ac", str(channels), "-ar", "44100", str(dst)])
    return p.returncode == 0 and dst.exists()


def write_id3_chapters(mp3_path: Path, chapters: list[dict], title: str, date_label: str) -> bool:
    try:
        from briefing.radio_producer import write_id3_chapters as _w
    except ImportError:  # pragma: no cover
        from pipeline.briefing.radio_producer import write_id3_chapters as _w  # type: ignore
    return _w(mp3_path, chapters, title, date_label)


def _to_stereo(mono: np.ndarray, pan: float) -> np.ndarray:
    """Constant-power pan, -1 left .. +1 right."""
    theta = (pan + 1.0) * math.pi / 4
    return np.stack([mono * math.cos(theta), mono * math.sin(theta)], axis=1)


# ---------------------------------------------------------------------------
# Produce
# ---------------------------------------------------------------------------

def produce_show(show: Show, opinion_script: str | None = None, edition: str = "world", *,
                 opinion_headline: str | None = None, permalinks: dict[str, str] | None = None,
                 engines: list | None = None, out_dir: Path | str | None = None,
                 date: datetime | None = None, label: str = "") -> Optional[ShowResult]:
    if os.environ.get("DISABLE_AUDIO", "").strip() in ("1", "true", "yes"):
        print("  [onair] DISABLE_AUDIO=1; skipping")
        return None
    if not PYDUB_AVAILABLE or AudioSegment is None:
        print("  [onair] pydub not installed; skipping")
        return None
    t0 = time.time()
    date = date or datetime.now(timezone.utc)
    cues = build_cues(show, opinion_script)
    if not cues:
        print("  [onair] nothing to say")
        return None
    words = sum(len(c.text.split()) for c in cues)
    print(f"  [onair] {len(cues)} lines, {words} spoken words, "
          f"{sum(1 for c in cues if c.kind == 'OPINION')} opinion paragraphs")

    synth = synthesize(cues, engines=engines)
    if synth is None:
        print("  [onair] Kokoro did not synthesise the show; no episode (the previous one is carried)")
        return None
    voiced, res = synth
    cues = [c for c in cues if c.idx in voiced]
    tts_s = time.time() - t0

    key = f"onair:{edition}:{date.strftime('%Y-%m-%d')}"
    v = S.voicing_for(key)
    lengths = {c.idx: len(voiced[c.idx]) / SR for c in cues}
    tl = build_timeline(cues, lengths, v)
    speech_s = sum(c.end - c.start for c in cues)
    wpm = words / (speech_s / 60) if speech_s else 0
    print(f"  [onair] timeline {tl.total:.1f}s, speech {speech_s:.1f}s, {wpm:.0f} wpm, news at {tl.news_start:.1f}s, "
          f"opinion at {tl.opinion_start if tl.opinion_start is not None else '-'}; "
          f"score {v.tempo_bpm} bpm seed {v.seed}")

    n = int(math.ceil(tl.total * SR)) + SR
    voice_mono = np.zeros(n)
    voice_st = np.zeros((n, 2))
    for c in cues:
        x = voiced[c.idx]
        S.place(voice_mono, x, c.start)
        st = _to_stereo(x, PAN.get(c.role, 0.0))
        i = int(c.start * SR)
        m = min(len(st), n - i)
        voice_st[i:i + m] += st[:m]

    music, notes = render_score(tl, v)
    for line in notes:
        print(f"  [onair][score] {line}")
    margin, where = phone_check(voice_mono, S.mono(music), cues)
    if margin < PHONE_VOICE_MARGIN_DB:
        music, n_fixed = phone_fix(voice_mono, music, cues)
        print(f"  [onair][score] phone-check margin {margin:.1f} dB at {where:.1f}s, under {PHONE_VOICE_MARGIN_DB}; "
              f"the music dips in {n_fixed} spoken window(s), nowhere else")
        margin, where = phone_check(voice_mono, S.mono(music), cues)
        if margin < PHONE_VOICE_MARGIN_DB - 1.0:
            drop = PHONE_VOICE_MARGIN_DB - margin
            music = music * (10 ** (-drop / 20))
            print(f"  [onair][score] phone-check still {margin:.1f} dB; music down {drop:.1f} dB throughout")
            margin, where = phone_check(voice_mono, S.mono(music), cues)
    print(f"  [onair][score] phone-check: voice over music {margin:.1f} dB in the worst spoken second (at {where:.1f}s)")
    room = S.room_tone(n / SR, seed=v.seed % 1000, level_dbfs=ROOM_TONE_DBFS)[:n]
    if len(music) < n:
        music = np.pad(music, ((0, n - len(music)), (0, 0)))
    music = music[:n]
    mix = voice_st[:n] + music + np.stack([room[:n], room[:n]], axis=1)
    mix = mix[: int(tl.total * SR)]

    work = Path(tempfile.mkdtemp(prefix="void-onair-"))
    try:
        mix_wav = work / "mix.wav"
        write_wav(mix_wav, mix)
        seg = AudioSegment.from_file(str(mix_wav), format="wav")
        try:
            from briefing import house_promos
        except ImportError:  # pragma: no cover
            from pipeline.briefing import house_promos  # type: ignore
        promo_key = f"onair:{edition}:{date.strftime('%Y-%m-%d')}:{'am' if date.hour < 12 else 'pm'}"
        seg, promo_info = house_promos.post_roll(seg, outro_at_ms=int(tl.outro_at * 1000),
                                                 last_word_ms=int(tl.last_word * 1000),
                                                 plays_in="onair", key=promo_key, work=work)
        mixed = work / "mixed.wav"
        seg.export(str(mixed), format="wav")
        master = work / "master.wav"
        stats = loudnorm_two_pass(mixed, master)
        o = stats.get("output") or {}
        if o:
            print(f"  [onair] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} LRA={o.get('output_lra')}")

        audio_bytes: bytes | None = None
        chosen = None
        for bitrate, channels in BITRATE_LADDER:
            mp3 = work / f"show_{bitrate}_{channels}.mp3"
            if encode_mp3(master, mp3, bitrate, channels):
                size = mp3.stat().st_size
                if size <= MAX_FILE_SIZE or (bitrate, channels) == BITRATE_LADDER[-1]:
                    audio_bytes = mp3.read_bytes()
                    chosen = (bitrate, channels, mp3)
                    break
        if not audio_bytes or not chosen:
            print("  [onair] MP3 encode failed")
            return None

        duration_s = round(len(seg) / 1000.0, 1)
        chapters = chapters_from_timeline(tl, opinion_headline=opinion_headline, permalinks=permalinks)
        if promo_info:
            chapters = house_promos.append_promo_chapter(chapters, house_promos.select("onair", promo_key),
                                                         promo_info["at_ms"], len(seg), kind="promo")
        title = f"On Air · {date.strftime('%A %d %B %Y')}"
        if write_id3_chapters(chosen[2], chapters, title, date.strftime("%Y-%m-%d")):
            audio_bytes = chosen[2].read_bytes()
        sidecar = chapters_sidecar(chapters, title)
        print(f"  [onair] {chosen[0]} {chosen[1]}ch, {len(audio_bytes) / 1024 / 1024:.2f} MB, {duration_s:.0f}s, "
              f"{len(chapters)} chapters")

        if out_dir:
            out = Path(out_dir)
            out.mkdir(parents=True, exist_ok=True)
            stem = f"{date.strftime('%Y-%m-%d')}-{'am' if date.hour < 12 else 'pm'}"
            (out / f"{stem}.mp3").write_bytes(audio_bytes)
            (out / f"{stem}.chapters.json").write_bytes(sidecar)
            (out / f"{stem}.script.txt").write_text(show.to_text(), encoding="utf-8")
            audio_url = str(out / f"{stem}.mp3")
            local_path = audio_url
        else:
            try:
                from briefing.audio_producer import _write_audio_static
            except ImportError:  # pragma: no cover
                from pipeline.briefing.audio_producer import _write_audio_static  # type: ignore
            # named by the EDITION's date, not the clock at render time (an
            # offline render after midnight UTC named Saturday's show 11-08-am)
            audio_url = _write_audio_static(audio_bytes, edition, sidecars={".chapters.json": sidecar}, when=date)
            local_path = None
            if not audio_url:
                return None

        eng = (engines or [None])[0]
        voices = f"{res.engine}:{VOICES['A']}+{VOICES['B']}"
        if eng is not None and hasattr(eng, "voice_id"):
            voices = f"{res.engine}:{eng.voice_id('A')}+{eng.voice_id('B')}"
        return ShowResult(
            audio_url=audio_url, duration_seconds=duration_s, file_size=len(audio_bytes),
            news_start_seconds=round(tl.news_start, 3),
            opinion_start_seconds=round(tl.opinion_start, 3) if tl.opinion_start is not None else None,
            chapters=chapters, engine=res.engine, voices=voices,
            timing={"tts_s": round(tts_s, 1), "total_s": round(time.time() - t0, 1), "wpm": round(wpm),
                    "engine": res.timing, "loudness": o, "bitrate": chosen[0], "channels": chosen[1],
                    "score": {"tempo_bpm": v.tempo_bpm, "seed": v.seed, "notes": notes,
                              "phone_margin_db": round(margin, 1)},
                    "label": label},
            audio_script=show.to_text(), local_path=local_path,
        )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def permalinks_from_archive(root: Path | None = None) -> dict[str, str]:
    try:
        from briefing.radio_producer import permalinks_from_archive as _p
    except ImportError:  # pragma: no cover
        from pipeline.briefing.radio_producer import permalinks_from_archive as _p  # type: ignore
    return _p(root) if root is not None else _p()
