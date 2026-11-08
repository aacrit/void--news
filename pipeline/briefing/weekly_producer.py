"""Render a weekly rundown into "The Argument", the Sunday audio edition. Rev 2.

    script (weekly_script) + the published issue
      -> validated (W-01..W-17), grounded (every sentence outside the columns against the issue)
      -> turns, normalised for speech, Kokoro only, three voices at one house pace
      -> per-line voice chain (onair_producer: trim, gate, -20 LUFS, house warmth, peak control)
      -> timeline from the synthesised lengths and the gap table (chapters exact by construction)
      -> the score, composed for THIS timeline (weekly_music), levelled to the standard
         (onair_score), ducked under the voices with the eased pre-roll, measured
      -> phone check, mix over the studio floor, house promo post-roll, loudnorm -16 LUFS, MP3
      -> ID3 chapters, Podcasting 2.0 sidecar

Running order, what the listener hears:

    COLD        H, one or two lines in the clear over the floor         [chapter: The week]
    theme       18.0 s featured; the sign-on lands on its downbeat at 14.3 s
    OPEN        H: the sign-on, then the week in one image                [bed: open, from the downbeat's hold]
    CONTENTS    H: "Inside this week." four lines                          [chapter: Inside this week]
    COVER       A leads, B takes passages incl. the last                   [bed: feature, under the first two
      DATELINE  H: "Tuesday. Twenty-four sources." a toll answers it       and the last; a visit for the dateline]
      COVER     continues                                                  [chapter: The cover]
    interlude   12.2 s, the first; the host speaks over its release
    TOPIC       H names the story the columns argue                        [bed: tension, rising into the sting]
    sting       4.6 s: the verdict. Then 1.4 s of the floor.
    LEFT        A, the left column, DRY                                    [chapter: The Argument, from the interlude]
    spine       2.4 s of nothing
    RIGHT       B, the right column, DRY
    REST        6.5 s; the frame closes: the turn's bed swells in
    TURN        H: what each side leaves out                               [bed: turn, the slow room, rising]
    interlude   the second; never the first's tune, chords or voice
    SECOND      B leads, A takes passages incl. the last                   [bed: feature]                [chapter]
    DEPARTMENT  H (optional)                                               [bed: feature]
    WEEK        H: "The week in brief." A and B alternate the briefs;      [bed: week, the pushed pulse, breathing
                a breath after every second item, a bell in it              after every second item; it STOPS]
    NUMBERS     H: The Week in Bias, only when the issue carries one       [the spectrum drone under it]
    silence     1.6 s of the floor
    entrance    11.4 s, "Void Opinion" (On Air's cue); H speaks 9.8 s in   [chapter: Void Opinion]
    EDITORIAL   H: "This is Void Opinion." then the column as written      [bed: editorial, the slow room]
    CLOSE       H: the open question, the sign-off                          [bed: close, rising]          [chapter]
    outro       18.0 s featured, landing on D major; the promo rides it    [chapter: Also from Void]

Every level is a number in onair_score; every sound is in weekly_music; this file places things.

    python pipeline/briefing/weekly_producer.py --rundown FILE --issue FILE [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from briefing import onair_score as S                                        # noqa: E402
from briefing import weekly_music as W                                       # noqa: E402
from briefing import onair_producer as OP                                    # noqa: E402
from briefing.spoken_text import normalize_for_speech                        # noqa: E402
from briefing.tts_engines import TurnSpec, KokoroEngine, synthesize_with_fallback   # noqa: E402
from briefing.weekly_script import (                                         # noqa: E402
    CLOSE_PREFIX, HOST, OPINION_OPEN, SIGN_ON, SPEED, TARGET_MINUTES, MUSIC_MINUTES, WEEK_OPEN,
    Script, cast_for_week, estimated_minutes, ground_script, parse_script, validate_script,
)

SR = S.SR

#: Three positions in the room: the host centre, the correspondents left and
#: right, because the one thing a listener must never lose track of in the
#: argument is WHICH SIDE IS SPEAKING, and the room says it before the timbre.
PAN = {"H": 0.0, "A": -0.16, "B": 0.16}

#: Measured Kokoro real-time factor with two workers on four cores (2026-11-08:
#: 0.35); the old figure of 1.4 is kept as the planning number so the deadline
#: survives a slower runner.
KOKORO_RTF = 1.4
DEADLINE_MARGIN = 1.35

# The silence grammar, seconds. A magazine breathes more slowly than a
# bulletin; the spine and the rest are the format's own silences.
GAPS: dict[str, float] = {
    "cold_in": 0.6,             # the floor before the first word
    "cold_lines": 0.9,
    "cold_to_theme": 1.4,
    "theme_downbeat_offset": 0.12,   # the sign-on lands ON the downbeat (W.THEME_DOWNBEAT_S)
    "host_lines": 0.9,          # between the host's lines in one movement
    "open_to_contents": 1.6,
    "contents_lines": 0.8,
    "contents_to_cover": 1.9,
    "handover": 1.0,            # one correspondent's passage ends, the other's begins
    "handover_bedded": 1.7,     # under a bed the music gets a breath at the handover
    "same_voice": 0.65,
    "to_dateline": 1.3,         # into the dateline beat
    "from_dateline": 2.1,       # and out of it: the toll rings in this held beat
    "story_to_interlude": 1.0,
    "interlude_to_voice": round(W.INTERLUDE_S - W.INTERLUDE_VOICE_S, 2),   # 2.1: the voice over the release bar
    "topic_to_sting": 0.8,
    "sting_to_column": 1.4,     # the held floor between the sting and the first column
    "column_lines": 0.75,
    "spine": 2.4,               # THE SPINE: between the left column and the right. Nothing plays in it.
    "rest": 6.5,                # the held pause after the right column; the frame closes in it
    "turn_lines": 1.0,
    "feature_to_week": 2.0,
    "week_lead_to_item": 0.85,
    "week_items": 0.9,
    "week_breath": 2.4,         # after every second item, never the last: the duck lets the bed up, a bell answers
    "week_to_numbers": 1.6,
    "week_to_stop": 0.5,        # the stop's hit lands this long after the last word before Void Opinion
    "stop_to_entrance": 1.6,    # the held silence (the floor only) between the bed's end and the entrance
    "entrance_to_voice": round(W.M.ENTRANCE_S - W.M.ENTRANCE_VOICE_S, 2),  # 1.6
    "opinion_intro_to_body": 1.3,
    "opinion_paragraphs": 1.0,
    "editorial_to_close": 1.6,
    "close_lines": 0.9,
    "outro_into_signoff": 0.4,
    "tail": 0.6,
}
ROOM_TONE_DBFS = -70.0
LOUDNESS_I = -16.0
PHONE_VOICE_MARGIN_DB = OP.PHONE_VOICE_MARGIN_DB
WEEK_BREATH_EVERY = 2
WEEK_BREATH_TAG_S = 0.6
DATELINE_TOLL_S = 0.35
#: A bed plays under this many passages of a feature, goes out, and comes back
#: under the last (and once in the middle of a long one).
BED_OUT_AFTER_PASSAGES = {"COVER": 2, "SECOND": 1, "EDITORIAL": 2}

CHAPTER_TITLES = {
    "COLD": "The week", "OPEN": "The week", "CONTENTS": "Inside this week", "COVER": "The cover",
    "TOPIC": "The Argument", "SECOND": "Second feature", "DEPARTMENT": "Department",
    "WEEK": "The week in brief", "NUMBERS": "The Week in Bias",
    "EDITORIAL": "Void Opinion", "CLOSE": "The open question",
}
#: Beats inside a movement; a listener would not jump to them.
NOT_A_CHAPTER = ("DATELINE", "LEFT", "RIGHT", "TURN", "REST")
#: A movement whose chapter starts at the interlude before it.
CHAPTER_FROM_INTERLUDE = ("TOPIC", "SECOND")

# Pages allows 25 MiB per file; twenty-two minutes at 128k stereo is about 21
# MB. The editorial is NEVER dropped: the ladder steps the bitrate and then
# ships whole.
SIZE_CAP_BYTES = 22 * 1024 * 1024
BITRATE_LADDER = (("128k", 2), ("96k", 2), ("96k", 1), ("64k", 1))


@dataclass
class Cue:
    idx: int
    kind: str
    seg_idx: int
    role: str           # H A B
    text: str
    start: float = 0.0
    end: float = 0.0
    title: str | None = None
    exchange: int = 0   # index of the line within its segment


@dataclass
class MusicCue:
    role: str           # featured | bed | interlude | sting
    name: str           # theme, open, feature, tension, turn, week, editorial, close, interlude, sting, entrance, outro, drone
    start: float
    end: float
    audio: np.ndarray | None = None
    findings: list = field(default_factory=list)
    accents: tuple = ()     # tolls (seconds into the bed)
    tags: tuple = ()        # breath bells (seconds into the bed)


@dataclass
class Timeline:
    cues: list[Cue]
    music: list[MusicCue]
    total: float
    outro_at: float
    last_word: float
    editorial_at: float | None = None
    sting_at: float | None = None

    def of_kind(self, kind: str) -> list[Cue]:
        return [c for c in self.cues if c.kind == kind]

    def beds(self) -> list[MusicCue]:
        return [m for m in self.music if m.role == "bed"]


# ---------------------------------------------------------------------------
# Lines
# ---------------------------------------------------------------------------

def build_cues(script: Script) -> list[Cue]:
    out: list[Cue] = []
    idx = 0
    for si, seg in enumerate(script.segments):
        for k, line in enumerate(seg.lines):
            spoken = normalize_for_speech(line.text, script.say)
            if not spoken:
                continue
            out.append(Cue(idx=idx, kind=seg.kind, seg_idx=si, role=line.speaker, text=spoken,
                           title=seg.title, exchange=k))
            idx += 1
    return out


def week_breath_after(c: Cue) -> bool:
    """The week breathes after every second item (exchange 0 is the opener)."""
    return c.kind == "WEEK" and c.exchange >= WEEK_BREATH_EVERY and c.exchange % WEEK_BREATH_EVERY == 0


def _gap(prev: Cue, cur: Cue, bedded: set[int]) -> float:
    """Silence between two consecutive lines when no music cue sits between them."""
    if prev.seg_idx == cur.seg_idx:
        if cur.kind == "COLD":
            return GAPS["cold_lines"]
        if cur.kind in ("COVER", "SECOND"):
            if prev.role == cur.role:
                return GAPS["same_voice"]
            return GAPS["handover_bedded"] if cur.idx in bedded else GAPS["handover"]
        if cur.kind in ("LEFT", "RIGHT"):
            return GAPS["column_lines"]
        if cur.kind == "WEEK":
            if prev.exchange == 0:
                return GAPS["week_lead_to_item"]
            return GAPS["week_breath"] if week_breath_after(prev) else GAPS["week_items"]
        if cur.kind == "EDITORIAL":
            return GAPS["opinion_intro_to_body"] if prev.exchange == 0 else GAPS["opinion_paragraphs"]
        return {"CONTENTS": GAPS["contents_lines"], "TURN": GAPS["turn_lines"],
                "CLOSE": GAPS["close_lines"]}.get(cur.kind, GAPS["host_lines"])
    pair = (prev.kind, cur.kind)
    if pair == ("OPEN", "CONTENTS"):
        return GAPS["open_to_contents"]
    if cur.kind == "COVER" and prev.kind != "DATELINE":
        return GAPS["contents_to_cover"]
    if cur.kind == "DATELINE":
        return GAPS["to_dateline"]
    if prev.kind == "DATELINE":
        return GAPS["from_dateline"]
    if pair == ("LEFT", "RIGHT"):
        return GAPS["spine"]
    if cur.kind == "TURN":
        return GAPS["rest"]
    if cur.kind in ("WEEK", "DEPARTMENT"):
        return GAPS["feature_to_week"]
    if cur.kind == "NUMBERS":
        return GAPS["week_to_numbers"]
    if cur.kind == "CLOSE":
        return GAPS["editorial_to_close"]
    return 1.2


def build_timeline(cues: list[Cue], lengths: dict[int, float]) -> Timeline:
    """Place every voice line and every music cue. Music lengths are the
    renderers' fixed durations (theme 18.0, interlude 12.2, sting 4.6,
    entrance 11.4, outro 18.0); beds are composed to the span they are given."""
    # The passages a feature's bed plays under: the first few and the last.
    bedded: set[int] = set()
    for kind in ("COVER", "SECOND", "EDITORIAL"):
        seg = [c for c in cues if c.kind == kind and (kind != "EDITORIAL" or c.exchange > 0)]
        if seg:
            k = BED_OUT_AFTER_PASSAGES[kind]
            bedded.update(c.idx for c in seg[:k])
            bedded.add(seg[-1].idx)
            if len(seg) >= 6:
                bedded.add(seg[len(seg) // 2].idx)
    music: list[MusicCue] = []
    t = 0.0
    prev: Cue | None = None
    editorial_at = sting_at = None
    interludes = 0
    for c in cues:
        length = lengths[c.idx]
        if prev is None:
            t = GAPS["cold_in"]
        elif prev.kind == "COLD" and c.kind != "COLD":
            theme_at = prev.end + GAPS["cold_to_theme"]
            music.append(MusicCue("featured", "theme", theme_at, theme_at + W.THEME_S))
            t = theme_at + W.THEME_DOWNBEAT_S + GAPS["theme_downbeat_offset"]
        elif (prev.kind in ("COVER", "TURN")) and c.kind in ("TOPIC", "SECOND", "DEPARTMENT", "WEEK"):
            il_at = prev.end + GAPS["story_to_interlude"]
            music.append(MusicCue("interlude", "interlude", il_at, il_at + W.INTERLUDE_S))
            interludes += 1
            t = il_at + W.INTERLUDE_VOICE_S
        elif prev.kind == "TOPIC" and c.kind == "LEFT":
            sting_at = prev.end + GAPS["topic_to_sting"]
            music.append(MusicCue("sting", "sting", sting_at, sting_at + W.STING_S))
            t = sting_at + W.STING_S + GAPS["sting_to_column"]
        elif c.kind == "EDITORIAL" and prev.kind != "EDITORIAL":
            stop_end = prev.end + GAPS["week_to_stop"] + W.STOP_RING_S
            en_at = stop_end + GAPS["stop_to_entrance"]
            music.append(MusicCue("featured", "entrance", en_at, en_at + W.M.ENTRANCE_S))
            editorial_at = en_at
            t = en_at + W.M.ENTRANCE_VOICE_S
        else:
            t = prev.end + _gap(prev, c, bedded)
        c.start, c.end = t, t + length
        prev = c
    last_word = cues[-1].end if cues else 0.0
    outro_at = last_word - GAPS["outro_into_signoff"]
    music.append(MusicCue("featured", "outro", outro_at, outro_at + W.OUTRO_S))
    total = outro_at + W.OUTRO_S + GAPS["tail"]

    def seg_cues(kind: str) -> list[Cue]:
        return [c for c in cues if c.kind == kind]

    def next_cue_start(after: float) -> float | None:
        starts = [m.start for m in music if m.role != "bed" and m.start > after - 0.5]
        return min(starts) if starts else None

    # --- the open bed: from the theme's held downbeat, under OPEN and CONTENTS
    open_, contents = seg_cues("OPEN"), seg_cues("CONTENTS")
    if open_:
        theme = next((m for m in music if m.name == "theme"), None)
        start = (theme.end - 2.4) if theme else open_[0].start - 1.6
        end = (contents[-1].end if contents else open_[-1].end) + 1.2
        music.append(MusicCue("bed", "open", start, end))

    # --- the features: under the first passages and the last, with a visit for the dateline
    def feature_spans(kind: str) -> list[list[float]]:
        seg = seg_cues(kind)
        if not seg:
            return []
        k = BED_OUT_AFTER_PASSAGES[kind]
        spans: list[list[float]] = [[seg[0].start - 1.6, seg[min(k, len(seg)) - 1].end + 2.4]]
        if len(seg) >= 6:
            mid = seg[len(seg) // 2]
            spans.append([mid.start - 2.2, mid.end + 1.0])
        tail = seg[-1]
        spans.append([tail.start - 2.2, tail.end + GAPS["story_to_interlude"] + 0.2])
        return spans

    def merge(spans: list[list[float]]) -> list[tuple[float, float]]:
        spans = sorted(spans)
        out: list[list[float]] = []
        for a, b in spans:
            if out and a <= out[-1][1] + 1.5:
                out[-1][1] = max(out[-1][1], b)
            else:
                out.append([a, b])
        return [(a, b) for a, b in out]

    datelines = seg_cues("DATELINE")
    for kind in ("COVER", "SECOND"):
        seg = seg_cues(kind)
        if not seg:
            continue
        spans = feature_spans(kind)
        inside = [d for d in datelines if seg[0].start < d.start < seg[-1].end]
        for d in inside:
            spans.append([d.start - 2.0, d.end + GAPS["from_dateline"] + 0.4])
        for a, b in merge(spans):
            accents = tuple(round(d.end + DATELINE_TOLL_S - a, 3) for d in inside if a <= d.end + DATELINE_TOLL_S <= b)
            music.append(MusicCue("bed", "feature", a, b, accents=accents))
    dept = seg_cues("DEPARTMENT")
    if dept:
        music.append(MusicCue("bed", "feature", dept[0].start - 1.6, dept[-1].end + 1.2))

    # --- the tension bed: under the host's framing, rising into the sting
    topic = seg_cues("TOPIC")
    if topic:
        il = next((m for m in music if m.name == "interlude" and m.start < topic[0].start), None)
        start = (il.end - 1.6) if il else topic[0].start - 1.8
        end = sting_at if sting_at is not None else topic[-1].end + 1.0
        music.append(MusicCue("bed", "tension", start, end))

    # --- the frame closes: the turn's bed swells in during the rest
    right, turn = seg_cues("RIGHT"), seg_cues("TURN")
    if turn:
        start = (right[-1].end + 1.2) if right else turn[0].start - 2.0
        music.append(MusicCue("bed", "turn", start, turn[-1].end + GAPS["story_to_interlude"] + 0.2))

    # --- the week: throughout, breathing, and it stops before the entrance
    week, numbers = seg_cues("WEEK"), seg_cues("NUMBERS")
    if week:
        start = week[0].start - 1.6
        last = (numbers[-1] if numbers else week[-1])
        end = last.end + 1.2
        items = week[1:]
        tags = tuple(round(c.end + WEEK_BREATH_TAG_S - start, 3) for i, c in enumerate(items)
                     if week_breath_after(c) and i + 1 < len(items))
        music.append(MusicCue("bed", "week", start, end, tags=tags))
        if numbers:
            music.append(MusicCue("drone", "drone", numbers[0].start - 0.8, numbers[-1].end + 1.5))

    # --- the bed before the entrance STOPS (the hit, the ring, the held floor)
    en = next((m for m in music if m.name == "entrance"), None)
    if en is not None:
        before = [c for c in cues if c.end < en.start]
        if before:
            last_before = before[-1]
            stop_end = last_before.end + GAPS["week_to_stop"] + W.STOP_RING_S
            under = [m for m in music if m.role == "bed" and m.start < last_before.end and m.end > last_before.start]
            if under:
                under[-1].end = stop_end
            else:
                # a feature that runs straight into Void Opinion gets a short bed to stop on
                music.append(MusicCue("bed", "feature", max(0.0, last_before.start - 1.6), stop_end))

    # --- the editorial: the slow room under the introduction, the first two paragraphs and the last
    ed = seg_cues("EDITORIAL")
    if ed:
        start = (en.end - 1.0) if en else ed[0].start - 2.0
        body = ed[1:] if len(ed) > 1 else ed
        k = min(BED_OUT_AFTER_PASSAGES["EDITORIAL"], max(1, len(body) - 1))
        first_out = body[k - 1].end + 1.0
        music.append(MusicCue("bed", "editorial", start, min(first_out + 2.5, body[-1].end)))
        tail = body[-1]
        if tail.start - 2.0 > first_out + 8.0:
            music.append(MusicCue("bed", "editorial", tail.start - 2.2, tail.end + 0.8))

    close = seg_cues("CLOSE")
    if close:
        music.append(MusicCue("bed", "close", close[0].start - 1.6, outro_at + 1.8))

    for m in music:
        if m.role == "bed" and m.end - m.start < 5.0:
            m.end = m.start + 5.0     # a bed of under 4 s is not a bed (A29)
    music.sort(key=lambda m: m.start)
    return Timeline(cues=cues, music=music, total=total, outro_at=outro_at, last_word=last_word,
                    editorial_at=editorial_at, sting_at=sting_at)


# ---------------------------------------------------------------------------
# Score placement
# ---------------------------------------------------------------------------

def bed_ending(tl: Timeline, m: MusicCue) -> tuple[str, MusicCue | None]:
    """How a bed ends, read from the timeline: ("stop", the entrance) when the
    entrance follows it within 3 s; ("rise", that cue) when an interlude, the
    sting or the outro starts within 2.5 s of its end; ("out", None) otherwise."""
    entrance = next((c for c in tl.music if c.name == "entrance" and -0.5 <= c.start - m.end <= 3.0), None)
    if entrance is not None:
        return "stop", entrance
    leads_into = next((c for c in tl.music if c.role in ("featured", "interlude", "sting")
                       and c.name not in ("theme", "entrance") and abs(c.start - m.end) <= 2.5), None)
    return ("rise", leads_into) if leads_into is not None else ("out", None)


def _shape(x: np.ndarray, fi: float, fo: float) -> np.ndarray:
    return S._normalise(S.fade(S.shape_bed(x), fi, fo))


def render_score(tl: Timeline, v: W.WeeklyVoicing, stats: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """Compose and level every music cue for this timeline, duck it under the
    voices, measure it against the standard, and return the bus with notes."""
    n = int(math.ceil(tl.total * SR)) + SR
    bus = np.zeros((n, 2))
    notes: list[str] = []
    speech = [(c.start, c.end) for c in tl.cues]

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

    for m in tl.beds():
        dur = m.end - m.start
        ending, leads_into = bed_ending(tl, m)
        out_s = S.EXIT_FADE_MIN_S + 1.0 if ending != "stop" else min(1.0, W.STOP_RING_S - 1.5)
        x = _shape(W.render_bed(v, m.name, max(dur, 4.5), ending=ending, accents=m.accents, tags=m.tags),
                   S.ENTRY_FADE_MIN_S + 0.5, out_s)
        x, g = S.level_bed(x, gaps_in(m))
        findings = S.check_cue(x, "bed", gaps=gaps_in(m))
        if any(f.id in ("score-repetition", "bed-breathing", "bed-low-end") for f in findings):
            alt = W.voicing_for(v.seed + 101)
            x2 = _shape(W.render_bed(alt, m.name, max(dur, 4.5), ending=ending, accents=m.accents, tags=m.tags),
                        S.ENTRY_FADE_MIN_S + 0.5, out_s)
            x2, g2 = S.level_bed(x2, gaps_in(m))
            f2 = S.check_cue(x2, "bed", gaps=gaps_in(m))
            if len(f2) < len(findings):
                x, g, findings = x2, g2, f2
        rise = 0.0
        if ending == "rise" and leads_into is not None:
            st = S.lufs_shortterm(x)
            top = float(np.max(st)) if st.size else S.BED_LUFS
            ceiling = S.INTERLUDE_LUFS if leads_into.role == "interlude" else S.FEATURED_LUFS
            rise = max(0.0, min(S.RISE_DB, ceiling + 1.0 - top))
            x = S.rise_into(x, rise_db=rise, hold_s=max(0.0, m.end - leads_into.start))
        m.audio, m.findings = x, findings
        notes.append(f"bed {m.name} {m.start:.1f}-{m.end:.1f}s gain {g:+.1f}"
                     + (f" rise +{rise:.0f} into {leads_into.name}" if ending == "rise" and leads_into is not None else "")
                     + (f" stop, {leads_into.start - m.end:.1f} s of floor before the {leads_into.name}"
                        if ending == "stop" and leads_into is not None else "")
                     + (f" tolls {m.accents}" if m.accents else "") + (f" breaths {len(m.tags)}" if m.tags else "")
                     + (" " + "; ".join(f.id for f in findings) if findings else ""))
    interludes = 0
    for m in [m for m in tl.music if m.role != "bed"]:
        if m.name == "theme":
            x, g = S.level_featured(_shape(W.render_theme(v), 0.01, 1.0))
            role = "featured"
        elif m.name == "entrance":
            x, g = S.level_featured(_shape(W.render_entrance(v), 0.02, 1.4))
            role = "featured"
        elif m.name == "outro":
            x, g = S.level_featured(_shape(W.render_outro(v), 0.02, 3.0))
            role = "featured"
        elif m.name == "sting":
            x, g = S.level_sting(_shape(W.render_sting(v), 0.01, 0.2))
            role = "sting"
        elif m.name == "drone":
            st = stats or {}
            x = _shape(W.spectrum_drone(float(st.get("avg_lean") or 50.0), float(st.get("lean_std") or 0.0),
                                        m.end - m.start), 1.5, 2.5)
            x, g = S.level_to(x, S.BED_LUFS - 6.0)
            role = "drone"
        else:
            x, g = S.level_interlude(_shape(W.render_interlude(v, interludes), 0.01, 1.2))
            interludes += 1
            role = "interlude"
        m.findings = S.check_cue(x, role) if role != "drone" else []
        m.audio = x
        notes.append(f"{m.role} {m.name} {m.start:.1f}s gain {g:+.1f}"
                     + (" " + "; ".join(f.id for f in m.findings) if m.findings else ""))
    for m in tl.music:
        if m.audio is not None:
            S.place(bus, m.audio[: int((m.end - m.start) * SR) + SR], m.start)
    env = S.duck_envelope(tl.total + 1.0, speech)
    for f in S.check_duck(env):
        notes.append(f.id + ": " + f.detail)
    bus = S.apply_envelope(bus, env)
    return bus[:n], notes


# ---------------------------------------------------------------------------
# Chapters
# ---------------------------------------------------------------------------

def chapters(tl: Timeline) -> list[dict]:
    """One chapter per movement a listener would jump to. `kind` is the segment
    lower-cased; `chapters.ts` renders any kind (and resolves `editorial` as the
    opinion). The cold open and the sign-on share the first chapter; a story
    chapter starts at the interlude before it; Void Opinion at its entrance."""
    out: list[dict] = []
    seen: set[str] = set()
    for c in tl.cues:
        key = "OPEN" if c.kind == "COLD" else c.kind
        if key in NOT_A_CHAPTER or key in seen:
            continue
        seen.add(key)
        start = c.start
        if key in CHAPTER_FROM_INTERLUDE:
            il = next((m for m in tl.music if m.name == "interlude" and m.end > c.start - 0.5 and m.start < c.start), None)
            if il:
                start = il.start
        if key == "EDITORIAL" and tl.editorial_at is not None:
            start = tl.editorial_at
        title = c.title or CHAPTER_TITLES.get(key, key.title())
        if key == "EDITORIAL":
            title = CHAPTER_TITLES["EDITORIAL"]
        ch = {"startTime": round(start, 3), "title": title, "kind": key.lower()}
        if key == "EDITORIAL" and c.title:
            ch["subtitle"] = c.title
        out.append(ch)
    if out:
        out[0]["startTime"] = 0.0
    for i, ch in enumerate(out):
        ch["endTime"] = out[i + 1]["startTime"] if i + 1 < len(out) else round(tl.total, 3)
    return out


# ---------------------------------------------------------------------------
# Produce
# ---------------------------------------------------------------------------

def voicing_key(issue: dict) -> str:
    return f"argument:{issue.get('edition') or 'world'}:{issue.get('week_start') or ''}"


def weekly_voicing(issue: dict) -> W.WeeklyVoicing:
    seed = int(hashlib.sha256(voicing_key(issue).encode("utf-8")).hexdigest()[:8], 16)
    return W.voicing_for(seed)


def produce(script_text: str, issue: dict, out_dir: Path, stem: str = "weekly") -> dict | None:
    if os.environ.get("DISABLE_AUDIO", "").strip() in ("1", "true", "yes"):
        print("  [weekly-audio] DISABLE_AUDIO=1; skipping")
        return None
    edition = issue.get("edition") or "world"
    voices = cast_for_week(issue.get("week_start"), edition)
    script = parse_script(script_text, edition)
    findings = validate_script(script, issue, voices)
    fails = [f for f in findings if f.level == "fail"]
    for f in findings:
        print(f"  [weekly-audio] {f.id} {f.level:4} [{f.segment}] {f.detail[:110]}")
    if fails:
        print(f"  [weekly-audio] {len(fails)} failure(s); not rendering")
        return None

    # The grounding pass: every sentence outside the columns, against the issue.
    cuts = ground_script(script, issue)
    for c in cuts:
        print(f"  [weekly-audio][grounding] cut ({c.reason}): {c.sentence[:110]!r}")
    if cuts:
        print(f"  [weekly-audio] grounding cut {len(cuts)} sentence(s) the issue does not carry")
        after = [f for f in validate_script(script, issue, voices) if f.level == "fail"]
        if after:
            for f in after:
                print(f"  [weekly-audio] after the cut: {f.id} [{f.segment}] {f.detail[:110]}")
            print("  [weekly-audio] the cut programme no longer has the shape; not rendering")
            return None

    minutes, wpm = estimated_minutes(script, voices)
    print(f"  [weekly-audio] {script.words} words, ~{minutes:.1f} min at {wpm:.0f} wpm")
    print(f"  [weekly-audio] host {voices['H']}; A (left column, leads the cover) {voices['A']}; "
          f"B (right column, leads the second) {voices['B']}; one pace {SPEED}")

    cues = build_cues(script)
    if not cues:
        print("  [weekly-audio] nothing to say")
        return None
    t0 = time.time()
    speech_s = (max(TARGET_MINUTES) - MUSIC_MINUTES) * 60.0
    deadline = round(speech_s * KOKORO_RTF * DEADLINE_MARGIN)
    engine = KokoroEngine(voices=voices, speed={r: SPEED for r in voices})
    turns = [TurnSpec(idx=c.idx, role=c.role, text=c.text, speed=SPEED) for c in cues]
    required = {c.idx for c in cues if c.text.startswith(SIGN_ON) or c.text.startswith(CLOSE_PREFIX)
                or c.text.startswith(OPINION_OPEN)}
    res = synthesize_with_fallback(turns, engines=[engine], deadline_s=deadline, required=required, min_coverage=0.98)
    if res is None:
        print("  [weekly-audio] Kokoro did not synthesise the programme; no episode")
        return None
    voiced: dict[int, np.ndarray] = {}
    stats_v = []
    for c in cues:
        seg = res.audio.get(c.idx)
        if seg is None:
            continue
        x, st = OP.voice_chain(OP._seg_to_np(seg))
        voiced[c.idx] = x
        stats_v.append(st)
    cues = [c for c in cues if c.idx in voiced]
    g = [s["gain_db"] for s in stats_v]
    print(f"  [weekly-audio] voice chain: {len(stats_v)} lines levelled to {S.DIALOGUE_LUFS} LUFS "
          f"(gain {min(g):+.1f}..{max(g):+.1f} dB), {sum(1 for s in stats_v if s['peak_reduced_db'] > 0)} peak-controlled")
    tts_s = time.time() - t0

    v = weekly_voicing(issue)
    tl = build_timeline(cues, {c.idx: len(voiced[c.idx]) / SR for c in cues})
    spoken = sum(c.end - c.start for c in cues)
    print(f"  [weekly-audio] timeline {tl.total:.1f}s, speech {spoken:.1f}s, {len([m for m in tl.music if m.name == 'interlude'])} "
          f"interludes, sting at {tl.sting_at}, Void Opinion at {tl.editorial_at}, {len(tl.beds())} bed span(s); seed {v.seed}")

    n = int(math.ceil(tl.total * SR)) + SR
    voice_mono = np.zeros(n)
    voice_st = np.zeros((n, 2))
    for c in cues:
        x = voiced[c.idx]
        S.place(voice_mono, x, c.start)
        st = OP._to_stereo(x, PAN.get(c.role, 0.0))
        i = int(c.start * SR)
        m = min(len(st), n - i)
        voice_st[i:i + m] += st[:m]

    stats = ((issue.get("bias_report_data") or {}).get("stats") or {})
    music, notes = render_score(tl, v, stats)
    for line in notes:
        print(f"  [weekly-audio][score] {line}")
    margin, where = OP.phone_check(voice_mono, S.mono(music), cues)
    if margin < PHONE_VOICE_MARGIN_DB:
        music, n_fixed = OP.phone_fix(voice_mono, music, cues)
        print(f"  [weekly-audio][score] phone-check margin {margin:.1f} dB at {where:.1f}s; "
              f"the music dips in {n_fixed} spoken window(s)")
        margin, where = OP.phone_check(voice_mono, S.mono(music), cues)
        if margin < PHONE_VOICE_MARGIN_DB - 1.0:
            drop = PHONE_VOICE_MARGIN_DB - margin
            music = music * (10 ** (-drop / 20))
            margin, where = OP.phone_check(voice_mono, S.mono(music), cues)
    print(f"  [weekly-audio][score] phone-check: voice over music {margin:.1f} dB in the worst spoken second (at {where:.1f}s)")
    room = S.room_tone(n / SR, seed=v.seed % 1000, level_dbfs=ROOM_TONE_DBFS)[:n]
    music = music[:n] if len(music) >= n else np.pad(music, ((0, n - len(music)), (0, 0)))
    mix = (voice_st[:n] + music + np.stack([room, room], axis=1))[: int(tl.total * SR)]

    work = Path(tempfile.mkdtemp(prefix="void-weekly-"))
    try:
        from pydub import AudioSegment
        mix_wav = work / "mix.wav"
        OP.write_wav(mix_wav, mix)
        seg = AudioSegment.from_file(str(mix_wav), format="wav")
        from briefing import house_promos
        promo_key = f"weekly:{edition}:{issue.get('week_start') or stem}"
        seg, promo_info = house_promos.post_roll(seg, outro_at_ms=int(tl.outro_at * 1000),
                                                 last_word_ms=int(tl.last_word * 1000),
                                                 plays_in="weekly", key=promo_key, work=work)
        mixed = work / "mixed.wav"
        seg.export(str(mixed), format="wav")
        master = work / "master.wav"
        st_ln = OP.loudnorm_two_pass(mixed, master)
        o = st_ln.get("output") or {}
        print(f"  [weekly-audio] loudnorm I={o.get('output_i')} TP={o.get('output_tp')} LRA={o.get('output_lra')} "
              f"({o.get('normalization_type')})")

        out_dir.mkdir(parents=True, exist_ok=True)
        mp3 = out_dir / f"{stem}.mp3"
        for bitrate, channels in BITRATE_LADDER:
            if not OP.encode_mp3(master, mp3, bitrate, channels):
                print("  [weekly-audio] encode failed")
                return None
            if mp3.stat().st_size <= SIZE_CAP_BYTES:
                break
            print(f"  [weekly-audio] {mp3.stat().st_size / 1e6:.1f} MB over cap at {bitrate}/{channels}ch; stepping down")
        else:
            print("  [weekly-audio] still over cap at the lowest rung; shipping whole (the editorial is never dropped)")

        chs = chapters(tl)
        if promo_info:
            chs = house_promos.append_promo_chapter(chs, house_promos.select("weekly", promo_key),
                                                    promo_info["at_ms"], len(seg), kind="promo")
        title = issue.get("cover_headline") or "Void Weekly"
        OP.write_id3_chapters(mp3, chs, title, issue.get("week_start") or "")
        sidecar = out_dir / f"{stem}.chapters.json"
        sidecar.write_bytes(OP.chapters_sidecar(chs, title))
        size = mp3.stat().st_size
        seconds = round(len(seg) / 1000.0, 1)
        print(f"  [weekly-audio] {mp3.name}: {seconds:.0f}s, {size / 1e6:.1f} MB, {len(chs)} chapters, "
              f"{time.time() - t0:.0f}s total")
        return {"path": str(mp3), "seconds": seconds, "bytes": size, "chapters": chs,
                "voices": {"host": voices["H"], "left": voices["A"], "right": voices["B"]},
                "voice_string": "kokoro:" + "+".join((voices["H"], voices["A"], voices["B"])),
                "words": script.words, "sidecar": str(sidecar),
                "grounding": {"ran": True, "cuts": len(cuts)},
                "timing": {"tts_s": round(tts_s, 1), "total_s": round(time.time() - t0, 1),
                           "phone_margin_db": round(margin, 1), "loudness": o, "seed": v.seed, "notes": notes}}
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ---------------------------------------------------------------------------
# The music-only reel: every cue of the score in running order, with marks
# ---------------------------------------------------------------------------

def render_reel(out_mp3: Path, issue: dict) -> dict:
    """The score alone, in the programme's order, levelled to the standard and
    mastered to -16 LUFS, with a marks file beside it. Beds are levelled at
    the interlude's -27 so they can be heard on their own (in the programme
    they sit at -31 under the voice); the featured cues, the interludes and
    the sting are at their production levels."""
    v = weekly_voicing(issue)
    seq: list[tuple[str, np.ndarray]] = []

    def bed(name, dur, **kw):
        x = _shape(W.render_bed(v, name, dur, **kw), 2.0, 2.5 if kw.get("ending") != "stop" else 1.0)
        return S.level_interlude(x)[0]

    seq.append(("theme (18 s; the sign-on lands at 14.3)", S.level_featured(_shape(W.render_theme(v), 0.01, 1.0))[0]))
    seq.append(("open bed (half-time; under the sign-on and the contents)", bed("open", 20.0)))
    seq.append(("feature bed with the dateline's toll at 6 s", bed("feature", 16.0, accents=(6.0,), ending="rise")))
    seq.append(("interlude 1 (riser, three bars of the tune, the release)", S.level_interlude(_shape(W.render_interlude(v, 0), 0.01, 1.2))[0]))
    seq.append(("tension bed (dominant pedal in eighths, no drums, rising)", S.rise_into(bed("tension", 14.0, ending="rise"), rise_db=5.0)))
    seq.append(("sting (the verdict), then 1.4 s of floor", np.concatenate([S.level_sting(_shape(W.render_sting(v), 0.01, 0.2))[0], np.zeros((int(1.4 * SR), 2))])))
    seq.append(("[the columns are read dry here]  turn bed (the frame closes: the slow room)", bed("turn", 16.0, ending="rise")))
    seq.append(("interlude 2 (another tune, chords and voice)", S.level_interlude(_shape(W.render_interlude(v, 1), 0.01, 1.2))[0]))
    seq.append(("week bed (the pushed pulse, breaths at 7 and 13 s) ending on the stop, then 1.6 s of floor",
                np.concatenate([bed("week", 20.0, ending="stop", tags=(7.0, 13.0)), np.zeros((int(1.6 * SR), 2))])))
    seq.append(("Void Opinion entrance (On Air's cue)", S.level_featured(_shape(W.render_entrance(v), 0.02, 1.4))[0]))
    seq.append(("editorial bed (the slow room, never on the tonic)", bed("editorial", 16.0)))
    seq.append(("close bed, rising into the outro", S.rise_into(bed("close", 12.0, ending="rise"), rise_db=4.0)))
    seq.append(("outro (the cadence, the hook at half speed, D major)", S.level_featured(_shape(W.render_outro(v), 0.02, 3.0))[0]))
    marks, pos, parts = [], 0.0, []
    for name, x in seq:
        marks.append({"at_s": round(pos, 2), "cue": name, "seconds": round(len(x) / SR, 1)})
        parts.append(x)
        pos += len(x) / SR
    mix = np.concatenate(parts)
    room = S.room_tone(len(mix) / SR, seed=v.seed % 1000, level_dbfs=ROOM_TONE_DBFS)[: len(mix)]
    mix = mix + np.stack([room, room], axis=1)
    work = Path(tempfile.mkdtemp(prefix="void-weekly-reel-"))
    try:
        raw = work / "reel.wav"
        OP.write_wav(raw, mix)
        master = work / "master.wav"
        st = OP.loudnorm_two_pass(raw, master)
        out_mp3.parent.mkdir(parents=True, exist_ok=True)
        OP.encode_mp3(master, out_mp3, "128k", 2)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    info = {"seed": v.seed, "key": voicing_key(issue), "seconds": round(pos, 1), "marks": marks,
            "loudness": (st.get("output") or {}), "progressions": v.progression,
            "note": "beds levelled at the interlude's -27 LUFS for listening; in the programme they sit at -31 under the voice"}
    out_mp3.with_suffix(".marks.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    out_mp3.with_suffix(".marks.txt").write_text(
        "\n".join(f"{m['at_s']:7.1f}s  {m['cue']}  ({m['seconds']} s)" for m in marks) + "\n", encoding="utf-8")
    return info


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rundown", help="the script file")
    ap.add_argument("--issue", help="the published weekly JSON")
    ap.add_argument("--out", default="/tmp/weekly-audio")
    ap.add_argument("--reel", help="write a music-only reel of the score to this MP3 and stop")
    ap.add_argument("--week", default="2026-10-26", help="the week the reel is voiced for")
    a = ap.parse_args()
    if a.reel:
        info = render_reel(Path(a.reel), {"edition": "world", "week_start": a.week})
        print(f"reel: {a.reel} {info['seconds']}s, {len(info['marks'])} marks, I={info['loudness'].get('output_i')}")
        return 0
    if not (a.rundown and a.issue):
        ap.error("--rundown and --issue are required unless --reel is given")
    issue = json.loads(Path(a.issue).read_text(encoding="utf-8"))
    if isinstance(issue, list):
        issue = issue[0]
    ok = produce(Path(a.rundown).read_text(encoding="utf-8"), issue, Path(a.out))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
