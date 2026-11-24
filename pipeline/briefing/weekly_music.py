"""The Argument: the Sunday score, composed. Rev 2 (2026-11-08, CEO: "it should
feel similar yet should be completely a weekly style show with a little more
drama and one more anchor. Embody this in the score, beats, and how the
episode is structured").

SAME FAMILY AS ON AIR, AND ITS OWN SHOW. Everything that makes On Air's score
Void's is kept and imported from `onair_music`: D minor, the 84-beat grid, the
seven-note hook, the patches (FM electric piano, felt bell, detuned pad, sub
bass, the soft kick with a knock, brush and shaker), the rooms, the Void
Opinion entrance. What is weekly about it, every cue:

    HALF-TIME.  The drums land once a bar where On Air's land twice: the kick on
                one, a brush on three, the shaker on two off-beats. The same
                grid, so the hook still fits; the pulse is felt at 42 a minute.
                The hook itself is heard at HALF SPEED (HOOK_HALF, four bars),
                the bell doubling it an octave up: On Air's tune, slowed.
    THE CADENCE. The cycle is i VI iv V (Dm Bb Gm A) and ends on the dominant,
                unresolved, where On Air's i VI III VII ends on the subtonic.
                The outro is the one place the weekly lands: on D major.
    THE TOLL.   A low bell on D3 opens the theme, answers each dateline inside
                the cover (an accent the producer places), and is the sting's
                bell. The dateline device, in one sound.
    THE STING.  Before the left column: a dark riser into a hit, the toll, a
                held sub, everything cut to the floor in under five seconds.
                Then silence, then a voice with no music under it. The
                argument is dry because the frame around it is not.
    THE TENSION BED. Under the host's framing of the argument: no drums, a
                dominant pedal in eighths on the sub, the pad opening and
                rising into the sting. Motion without a single bright onset.
    THE FRAME CLOSES. After the right column and the held rest, the turn's bed
                swells in from the floor: the slow room, VI iv i V.
    THE INTERLUDE. Four bars, a riser into its downbeat (a page turned), the
                hook or its answer in dotted augmentation over three chords,
                a release bar on the tonic the next voice speaks over.
    THE WEEK.   A pushed pulse (kick on one, the and of two, three) for the
                week in brief, breathing after every second item; it stops on
                a hit before Void Opinion, as On Air's desk does.
    THE EDITORIAL. On Air's Void Opinion entrance, unchanged (a signature is
                a signature), and the Opinion's slow room under the host.

Everything renders at SR = 48000, stereo float64 of shape (n, 2). `onair_score`
holds the standard; `weekly_producer` places the cues and levels them.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

try:
    from briefing import onair_music as M
except ImportError:  # pragma: no cover
    from pipeline.briefing import onair_music as M  # type: ignore

SR = M.SR
BPM = M.BPM
BEAT = M.BEAT
BAR = M.BAR
CHORDS = M.CHORDS
place = M.place

# ---------------------------------------------------------------------------
# The weekly's harmony and tunes
# ---------------------------------------------------------------------------

#: The hook at half speed: four bars, every value doubled.
HOOK_HALF = [(n, s * 2.0, l * 2.0) for n, s, l in M.HOOK]
#: The weekly cadence: ends on the dominant, unresolved.
CADENCE = ["Dm", "Bb", "Gm", "A"]
PROGRESSIONS = {
    "open": [["Dm", "Bb", "Gm", "A"], ["Dm", "C", "Bb", "A"]],
    "feature": [["Dm", "Bb", "F", "A"], ["Dm", "Gm", "Bb", "A"], ["Bb", "Gm", "Dm", "A"]],
    "tension": [["Dm", "Asus", "Dm", "Asus"], ["Bb", "Asus", "Gm", "Asus"]],
    "turn": [["Bb", "Gm", "Dm", "A"], ["Gm", "Bb", "F", "A"]],
    "week": [["Dm", "C", "Bb", "A"], ["Dm", "Bb", "C", "A"]],
    # the editorial is Void Opinion: On Air's harmony, never on i
    "editorial": M.PROGRESSIONS["opinion"],
    "close": [["Dm", "Bb", "Gm", "A"]],
}
#: Two bars a chord in the slow rooms (the turn, the editorial), as On Air's Opinion.
SLOW_BARS_PER_CHORD = 2
SLOW_SEGMENTS = ("turn", "editorial")

TOLL_NOTE = "D3"

# The theme: a toll and a swell for one bar, four bars of the hook at half
# speed over the cadence, a riser into the downbeat the sign-on lands on, then
# the pad holds under the voice.
THEME_BARS = 5
THEME_DOWNBEAT_S = round(THEME_BARS * BAR, 2)          # 14.29 s
THEME_S = 18.0

# The interlude: a riser (the page turned), three bars of a tune in dotted
# augmentation over three chords, a release bar on the tonic.
INTERLUDE_RISER_S = 0.8
INTERLUDE_BARS = 4
INTERLUDE_S = round(INTERLUDE_RISER_S + INTERLUDE_BARS * BAR, 1)       # 12.2 s
INTERLUDE_VOICE_S = round(INTERLUDE_RISER_S + 3 * BAR + 1.0 * BEAT, 1)  # 10.1 s: over the release bar
_AUG = lambda notes: [(n, s * 1.5, l * 1.5) for n, s, l in notes]  # noqa: E731
INTERLUDE_FRAGMENTS = [
    (M.HOOK_AUGMENTED, [("Dm", "Bb", "Gm"), ("Dm", "Gm", "A")]),
    (_AUG(M.HOOK_INVERTED), [("F", "C", "Bb"), ("Bb", "F", "C")]),
    (_AUG(M.HOOK_ANSWER), [("Bb", "Gm", "A"), ("Gm", "Bb", "A")]),
]
INTERLUDE_RELEASE = "Dm"

# The sting: the riser lands on the hit; the ring is cut to the floor by the end.
STING_RISER_S = 1.3
STING_S = 4.6

# The outro: the cadence with the hook at half speed, a riser, D major.
OUTRO_LAND_BARS = 4
OUTRO_LAND_S = round(OUTRO_LAND_BARS * BAR, 2)        # 11.43 s
OUTRO_S = 18.0

# A stopped bed: the hit lands this long before its end (On Air's number).
STOP_RING_S = M.STOP_RING_S
#: The pendulum rests from this long before an accent's toll to this long after it.
TOLL_REST = (0.15, 1.6)


@dataclass
class WeeklyVoicing:
    """The issue's seed, the chord cycle per movement drawn from it, and the
    generator every humanising jitter is drawn from."""
    seed: int
    rng: np.random.Generator
    progression: dict[str, list[str]]


def voicing_for(seed: int) -> WeeklyVoicing:
    rng = np.random.default_rng(seed)
    prog = {seg: opts[int(rng.integers(len(opts)))] for seg, opts in PROGRESSIONS.items()}
    return WeeklyVoicing(seed=seed, rng=rng, progression=prog)


# ---------------------------------------------------------------------------
# The weekly's own figures
# ---------------------------------------------------------------------------

def toll(canvas: np.ndarray, at_s: float, *, amp: float = 0.8, rng=None) -> None:
    """The toll: the felt bell on D3 with a soft electric piano under it, long.
    Nothing in it is a clock: a bell rings on, so the calm meter does not
    count it, and it sits under the glare band."""
    place(canvas, M.bell(TOLL_NOTE, 2.6, vel=amp, pan=0.0, rng=rng), at_s)
    place(canvas, M.ep(TOLL_NOTE, 1.6, vel=amp * 0.45, pan=0.0, rng=rng), at_s + 0.01)


def _pendulum(canvas, chord: str, bar_at: float, *, amp: float, rng=None, bell_on_one: bool = False,
              skip: tuple[tuple[float, float], ...] = ()) -> None:
    """The weekly's keys in place of On Air's lilting ostinato: a chord tone on
    one and another on three, two notes a bar, swinging left and right; now
    and then a pickup on the and of four. The bell doubles beat one on
    alternate bars so the line glints without getting busy."""
    ost = CHORDS[chord]["ost"]
    steps = [(0.0, ost[0], 1.0, -0.22), (2.0, ost[2], 0.8, 0.22)]
    if rng is not None and rng.random() < 0.35:
        steps.append((3.0 + M.SWING, ost[1], 0.5, 0.0))
    for beat, note, lvl, pan in steps:
        at = M._human(rng, bar_at + beat * BEAT)
        if any(lo <= at < hi for lo, hi in skip):
            continue
        vel = amp * lvl * (float(rng.uniform(0.9, 1.08)) if rng is not None else 1.0)
        place(canvas, M.ep(note, 0.9 * BEAT, vel=vel, pan=pan, rng=rng), at)
        if beat == 0.0 and bell_on_one:
            place(canvas, M.bell(note, 1.2 * BEAT, vel=vel * 0.5, pan=pan * 0.5, rng=rng), at + 0.004)


def _drums(canvas, kicks: list[float], start: float, bars: int, pattern: str, *, kick_amp: float,
           clock_amp: float, rng=None, drop_bars: set[int] = frozenset(), fill_bars: set[int] = frozenset(),
           shape: "list[float] | None" = None) -> None:
    """The weekly's patterns, on the same soft drums as On Air:
        halftime   kick on one, a brush on three, the shaker on the and of two and of four
                   (one kick a bar: the pulse is felt at half of On Air's)
        weekpulse  the week in brief: kick on one, the and of two and three (pushed), a brush
                   on four, the shaker on the and of one and of three
        slow       one soft kick a bar and no clock (the slow rooms), On Air's
    """
    if pattern == "slow":
        M._drums(canvas, kicks, start, bars, "slow", kick_amp=kick_amp, clock_amp=clock_amp, rng=rng,
                 drop_bars=drop_bars, fill_bars=fill_bars, shape=shape)
        return
    for b in range(bars):
        bar_at = start + b * BAR
        dropped = b in drop_bars
        sc = shape[b] if shape is not None and b < len(shape) else 1.0
        if sc <= 0.0:
            continue
        k_amp, c_amp = kick_amp * sc, clock_amp * sc
        if b in fill_bars:
            M._fill(canvas, bar_at, amp=c_amp, rng=rng)
        for beat in range(4):
            at = bar_at + beat * BEAT
            off = M._human(rng, at + M.SWING * BEAT, 5.0)
            if pattern == "halftime":
                if beat == 0 and not dropped:
                    place(canvas, M.kick(amp=k_amp), at)
                    kicks.append(at)
                if beat == 2:
                    place(canvas, M.brush(amp=c_amp * 0.75, rng=rng), M._human(rng, at, 5.0))
                if beat in (1, 3):
                    place(canvas, M.shaker(amp=c_amp * 0.55, open_=(beat == 3), rng=rng), off)
                continue
            if pattern == "weekpulse":
                if beat == 0 and not dropped:
                    place(canvas, M.kick(amp=k_amp), at)
                    kicks.append(at)
                if beat == 1 and not dropped:
                    place(canvas, M.kick(amp=k_amp * 0.6), off)
                    kicks.append(off)
                if beat == 2 and not dropped:
                    place(canvas, M.kick(amp=k_amp * 0.8), at)
                    kicks.append(at)
                if beat == 3:
                    place(canvas, M.brush(amp=c_amp * 0.7, rng=rng), M._human(rng, at, 5.0))
                if beat in (0, 2):
                    place(canvas, M.shaker(amp=c_amp * 0.55, open_=(beat == 2), rng=rng), off)
                continue


def _bassline(canvas, chord: str, bar_at: float, *, amp: float, style: str) -> None:
    """halftime: the root held from one, the fifth on three, a pickup on the and
    of four; pedal: the dominant in eighths under the tension bed; the rest
    are On Air's (pulse, walk, eighths)."""
    root = CHORDS[chord]["bass"]
    fifth = CHORDS[chord]["fifth"]
    if style == "halftime":
        place(canvas, M.bass(root, 1.9 * BEAT, amp=amp), bar_at)
        place(canvas, M.bass(fifth, 1.4 * BEAT, amp=amp * 0.8), bar_at + 2.0 * BEAT)
        place(canvas, M.bass(root, 0.35 * BEAT, amp=amp * 0.5), bar_at + (3.0 + M.SWING) * BEAT)
        return
    if style == "pedal":
        for k in range(8):
            place(canvas, M.bass("A1", 0.4, amp=amp * (1.0 if k % 2 == 0 else 0.72)), bar_at + k * 0.5 * BEAT)
        return
    M._bassline(canvas, chord, bar_at, amp=amp, style=style)


def _hook_half(canvas, bar_at: float, *, amp: float, rng=None, bell_octave: float = 0.0) -> None:
    """The hook at half speed on the electric piano, the bell doubling it an
    octave up when `bell_octave` is over zero."""
    M._melody(canvas, HOOK_HALF, bar_at, amp=amp, voice="ep", rng=rng, pan_spread=0.15)
    if bell_octave > 0:
        for i, (note, start, length) in enumerate(HOOK_HALF):
            up = note[:-1] + str(int(note[-1]) + 1)
            place(canvas, M.bell(up, length * BEAT * 0.9, vel=bell_octave * (1.0 if i in (0, 6) else 0.8),
                                 pan=(0.25 if i % 2 else -0.25), rng=rng),
                  M._human(rng, bar_at + start * BEAT, 5.0))


def _mix(keys, pads, low, drums, fx, *, seed: int, slow: bool = False, delay: bool = True) -> np.ndarray:
    if delay:
        keys = M.tempo_delay(keys, beats=1.5 if slow else 0.75, feedback=0.3, mix=0.2)
    return (M.reverb(keys, wet=0.42 if slow else 0.36, decay_s=3.2 if slow else 2.6, seed=seed + 3)
            + M.reverb(pads, wet=0.5, decay_s=3.6 if slow else 3.2, seed=seed + 4) + low + drums + fx)


def _canvases(n: int, k: int = 5) -> list[np.ndarray]:
    return [np.zeros((n, 2)) for _ in range(k)]


# ---------------------------------------------------------------------------
# The cues
# ---------------------------------------------------------------------------

def render_theme(v: WeeklyVoicing, dur_s: float = THEME_S) -> np.ndarray:
    """Bar by bar:
        0  the toll on D3, a sub pedal and a dark pad swelling in: nothing moves
        1  the half-time drums enter under the pad; the hook begins at half speed
           on the electric piano over Dm
        2  Bb; the drums fill in
        3  Gm; the bell doubles the hook an octave up
        4  A, the dominant: the hook's last note, the tonic, hangs over it; a dark
           riser draws in to the downbeat
        5  the downbeat: a hit, the pad on Dm held under the voice (the sign-on
           lands here, THEME_DOWNBEAT_S), the keys ring, the sub under it
    """
    n = int((dur_s + 2.0) * SR)
    keys, pads, low, drums, fx = _canvases(n)
    kicks: list[float] = []
    rng = v.rng
    toll(keys, 0.25, amp=0.8, rng=rng)
    place(low, M.sub_pedal("D2", BAR + 0.6, amp=0.6, attack_s=1.2, release_s=0.8), 0.0)
    place(pads, M.pad("Dm", BAR + 0.5, amp=0.6, attack_s=2.0, open_hz=700.0, rng=rng), 0.0)
    for b, chord in enumerate(CADENCE):
        at = (b + 1) * BAR
        place(pads, M.pad(chord, BAR + 0.4, amp=(0.85, 0.95, 1.0, 1.0)[b], attack_s=(1.0, 0.7, 0.6, 0.6)[b],
                          open_hz=800.0 + 50.0 * b, rng=rng), at)
        _bassline(low, chord, at, amp=0.85, style="halftime")
        if b >= 1:
            _pendulum(keys, chord, at, amp=0.22, rng=rng)
    # the drums build to the downbeat: the hit at THEME_DOWNBEAT_S is the theme's climax
    _drums(drums, kicks, BAR, 4, "halftime", kick_amp=0.9, clock_amp=0.3, rng=rng, shape=[0.5, 0.7, 0.85, 1.0])
    _hook_half(keys, BAR, amp=0.9, rng=rng, bell_octave=0.0)
    # the bell doubles the hook from its third bar (the fall G4 F4 D4)
    for i, (note, start, length) in enumerate(HOOK_HALF[4:]):
        up = note[:-1] + str(int(note[-1]) + 1)
        place(keys, M.bell(up, length * BEAT * 0.9, vel=0.34, pan=(0.25 if i % 2 else -0.25), rng=rng),
              M._human(rng, BAR + start * BEAT, 5.0))
    land = THEME_BARS * BAR
    place(fx, M.riser(1.8, amp=0.42, rng=rng), land - 1.8)
    place(drums, M.impact(amp=1.0), land)
    kicks.append(land)
    place(pads, M.pad("Dm", dur_s - land + 1.0, amp=1.0, attack_s=0.05, release_s=3.5, open_hz=900.0, rng=rng), land)
    place(keys, M.ep("D4", 2.8, vel=0.7, pan=0.0, rng=rng), land)
    place(keys, M.ep("A4", 2.8, vel=0.5, pan=0.12, rng=rng), land)
    place(low, M.bass("D2", 2.2, amp=0.95), land)
    place(low, M.sub_pedal("D2", dur_s - land - 0.5, amp=0.55, attack_s=0.5, release_s=2.0), land + 1.2)
    pads = M.sidechain(pads, kicks)
    low = M.sidechain(low, kicks, depth_db=2.0)
    return _mix(keys, pads, low, drums, fx, seed=v.seed)[: int(dur_s * SR)]


def render_bed(v: WeeklyVoicing, segment: str, dur_s: float, *, ending: str = "out",
               accents: tuple[float, ...] = (), tags: tuple[float, ...] = ()) -> np.ndarray:
    """A bed with On Air's arc (`onair_music._arc`: pad and bass alone, the
    pulse arrives, builds by eight-bar phrases, thins out / rises / STOPS) on
    the weekly's patterns:

        open, feature, close   half-time drums, the half-time bass, the pendulum, the
                               hook at half speed once a phrase
        tension                no drums; the dominant pedal in eighths on the sub, the
                               pad alternating Dm and Asus and opening across the bed, a
                               bell on the fifth every other bar
        week                   the pushed pulse; it STOPS on a hit before the entrance
        turn, editorial        the slow room: two bars a chord, one soft kick a bar, the
                               walking bass, a sparse bell line (On Air's Opinion room)

    `accents` are seconds into the bed where a toll lands (the datelines inside
    the cover); `tags` where a two-note bell answers a breath (the week in
    brief, after every second item, On Air's desk device); the pendulum rests
    through each.
    """
    slow = segment in SLOW_SEGMENTS
    tension = segment == "tension"
    pattern = {"open": "halftime", "feature": "halftime", "close": "halftime", "week": "weekpulse",
               "tension": "none", "turn": "slow", "editorial": "slow"}[segment]
    prog = v.progression[segment]
    rng = v.rng
    origin = 0.0
    stop_at = None
    if ending == "stop":
        stop_at = dur_s - STOP_RING_S
        origin = stop_at - math.floor(stop_at / BAR) * BAR
    bars = int(math.ceil((dur_s - origin) / BAR)) + 1
    n = int((origin + bars * BAR + 3.5) * SR)
    keys, pads, low, drums, fx = _canvases(n)
    kicks: list[float] = []
    d_shape, k_shape, fills, _ = M._arc(bars, ending, rng)
    if segment == "week":
        d_shape = [max(x, 0.85) if b else 0.9 for b, x in enumerate(d_shape)]   # the week never thins
    stop_bar = None
    if stop_at is not None:
        stop_bar = int(round((stop_at - origin) / BAR))
        for b in range(stop_bar, bars):
            d_shape[b] = 0.0
            k_shape[b] = 0.0
        fills.discard(stop_bar)
        fills.discard(stop_bar - 1)
    pad_open = 800.0 if (slow or tension) else 880.0
    if origin > 0.05:
        place(pads, M.pad(prog[0], origin + 0.4, amp=0.7, attack_s=min(1.6, origin), open_hz=pad_open, rng=rng), 0.0)

    def chord_at(b: int) -> str:
        return prog[(b // SLOW_BARS_PER_CHORD if slow else b) % len(prog)]

    tolls = tuple(t for t in accents if stop_at is None or t < stop_at - 0.5)
    breaths = tuple(t for t in tags if stop_at is None or t < stop_at - 0.5)
    rest_spans = tuple((t - TOLL_REST[0], t + TOLL_REST[1]) for t in tolls) \
        + tuple((t - M.BREATH_REST[0], t + M.BREATH_REST[1]) for t in breaths)
    for b in range(bars):
        if stop_bar is not None and b >= stop_bar:
            break
        chord = chord_at(b)
        at = origin + b * BAR
        pos = b % 8
        pad_amp = 0.8 + 0.2 * (0.5 + 0.5 * math.sin(math.pi * pos / 8))
        if tension:
            # the pad opens across the whole bed: the one thing that moves besides the pedal
            open_hz = 650.0 + 450.0 * min(1.0, b / max(1, bars - 2))
            place(pads, M.pad(chord, BAR + 0.5, amp=0.9 + 0.2 * min(1.0, b / max(1, bars - 1)), attack_s=1.1,
                              open_hz=open_hz, rng=rng), at)
            _bassline(low, chord, at, amp=0.55 + 0.4 * min(1.0, b / max(1, bars - 2)), style="pedal")
            if b % 2 == 1:
                place(keys, M.bell("A4" if chord != "Asus" else "E5", 2.0 * BEAT, vel=0.4, pan=(-0.3, 0.3)[(b // 2) % 2],
                                   rng=rng), M._human(rng, at + 1.0 * BEAT, 6.0))
            continue
        open_hz = pad_open + (0.0 if slow else 80.0 * min(2, b // 8))
        place(pads, M.pad(chord, BAR + 0.4, amp=pad_amp * (1.12 if slow else 1.0), attack_s=1.2 if slow else 1.0,
                          open_hz=open_hz, rng=rng), at)
        if b > 0 or bars <= 3:
            if slow:
                _bassline(low, chord, at, amp=0.82 * max(0.6, d_shape[b] or 0.6), style="walk")
            else:
                _bassline(low, chord, at, amp=(0.95 if segment == "week" else 0.85) * max(0.6, d_shape[b] or 0.6),
                          style="pulse" if segment == "week" else "halftime")
        if slow:
            if k_shape[b] > 0 and (pos in (0, 1, 2, 4, 5) or rng.random() < 0.4):
                beats = (0.0, 2.0) if rng.random() < 0.7 else (1.0, 3.0)
                M._bell_line(keys, chord, at, amp=0.5 * k_shape[b], rng=rng, beats=beats)
            if k_shape[b] > 0 and pos == 6 and chord in ("Bb", "Gm"):
                for note, start, length in M.HOOK_INVERTED[:3]:
                    place(keys, M.bell(note, length * BEAT, vel=0.55 * k_shape[b], pan=0.0, rng=rng),
                          M._human(rng, at + start * BEAT, 5.0))
            continue
        if k_shape[b] > 0 and (segment == "week" or pos in (0, 1, 2, 4, 5) or rng.random() < 0.4):
            _pendulum(keys, chord, at, amp=(0.3 if segment != "week" else 0.34) * k_shape[b], rng=rng,
                      bell_on_one=(b % 2 == 1 and segment != "week"), skip=rest_spans)
        if k_shape[b] > 0 and pos == 4 and chord == "Dm" and b + 4 <= bars and segment != "week":
            _hook_half(keys, at, amp=0.55 * k_shape[b], rng=rng, bell_octave=0.0)
    for t_acc in tolls:
        toll(keys, t_acc, amp=0.62, rng=np.random.default_rng(int(t_acc * 1000)))
    for t_acc in breaths:
        b = int((t_acc - origin) // BAR) if t_acc >= origin else 0
        M._bell_tag(keys, chord_at(max(0, b)), t_acc, amp=0.6)
    drop = {b for b in range(bars) if b % 8 == 3 and b > 2 and rng.random() < 0.5}
    if pattern != "none":
        _drums(drums, kicks, origin, bars, pattern, kick_amp=0.9 if not slow else 0.8,
               clock_amp=0.3 if segment != "week" else 0.33, rng=rng, drop_bars=drop, fill_bars=fills, shape=d_shape)
    if stop_at is not None:
        chord = chord_at(stop_bar or 0)
        place(drums, M.impact(amp=1.0), stop_at)
        kicks.append(stop_at)
        place(low, M.bass(CHORDS[chord]["bass"], 1.4, amp=1.0), stop_at)
        place(pads, M.pad(chord, 0.5, amp=0.9, attack_s=0.03, release_s=1.3, rng=rng), stop_at)
        cut = int(stop_at * SR)
        gate = np.ones(n)
        edge = int(0.012 * SR)
        gate[cut:] = 0.0
        gate[cut - edge:cut] = np.linspace(1, 0, edge)
        keys *= gate[:, None]
    pads = M.sidechain(pads, kicks)
    low = M.sidechain(low, kicks, depth_db=2.0)
    return _mix(keys, pads, low, drums, fx, seed=v.seed + (7 if slow else 0), slow=slow)[: int(dur_s * SR)]


def interlude_plan(v: WeeklyVoicing, index: int) -> tuple[list, tuple[str, str, str], str]:
    """What the `index`-th interlude plays: (melody, chord triple, voice). The
    issue's seed picks the first; each later one takes the next fragment, the
    next triple and the other voice, so two in one episode share none."""
    k = (v.seed % len(INTERLUDE_FRAGMENTS) + index) % len(INTERLUDE_FRAGMENTS)
    melody, triples = INTERLUDE_FRAGMENTS[k]
    triple = triples[((v.seed // 7) + index) % len(triples)]
    voice = "ep" if (v.seed // 13 + index) % 2 == 0 else "bell"
    return melody, triple, voice


def render_interlude(v: WeeklyVoicing, index: int = 0, dur_s: float = INTERLUDE_S) -> np.ndarray:
    """Bar by bar (after INTERLUDE_RISER_S of a dark riser, the page turned):
        1-3  the half-time groove from the downbeat (a soft impact on it), the
             bass on root and fifth, a warm pad, and the tune in dotted
             augmentation (the hook, its inversion or its answer) over three chords
        4    the release: a single kick and the bass land on the tonic, the pad opens
             on Dm and holds, the clock is gone, the tune's last note rings. The next
             voice speaks here (INTERLUDE_VOICE_S)."""
    melody, triple, voice = interlude_plan(v, index)
    rng = v.rng
    n = int((dur_s + 3.0) * SR)
    keys, pads, low, drums, fx = _canvases(n)
    kicks: list[float] = []
    t0 = INTERLUDE_RISER_S
    place(fx, M.riser(t0, amp=0.3, rng=rng), 0.0)
    place(drums, M.impact(amp=0.55), t0)
    chords = list(triple) + [INTERLUDE_RELEASE]
    for b, chord in enumerate(chords):
        at = t0 + b * BAR
        last = b == 3
        place(pads, M.pad(chord, (BAR + 1.6) if last else (BAR + 0.3), amp=0.9 if last else 0.8,
                          attack_s=0.35 if b == 0 else 0.6, release_s=3.0 if last else 2.0, open_hz=800.0, rng=rng), at)
        if last:
            place(low, M.bass(CHORDS[chord]["bass"], 2.4 * BEAT, amp=0.9), at)
        else:
            _bassline(low, chord, at, amp=0.85, style="halftime")
    _drums(drums, kicks, t0, 3, "halftime", kick_amp=0.85, clock_amp=0.3, rng=rng, shape=[0.0, 1.0, 1.0])
    place(drums, M.kick(amp=0.85), t0 + 3 * BAR)
    kicks.append(t0 + 3 * BAR)
    M._melody(keys, melody, t0, amp=0.72 if voice == "ep" else 0.8, voice=voice, rng=rng, pan_spread=0.2)
    place(keys, (M.bell if voice == "bell" else M.ep)("D4", 2.2, vel=0.42, pan=0.0, rng=rng), t0 + 3 * BAR)
    pads = M.sidechain(pads, kicks)
    low = M.sidechain(low, kicks, depth_db=2.0)
    return _mix(keys, pads, low, drums, fx, seed=v.seed + 11 + index)[: int(dur_s * SR)]


def render_sting(v: WeeklyVoicing, dur_s: float = STING_S) -> np.ndarray:
    """The verdict, before the left column: a dark riser draws in for
    STING_RISER_S and lands on a hit, the toll on D3, a sub on D under it and a
    pad stab released at once; every tail is cut to the floor by the end. Then
    the producer holds silence, and the first column is read dry."""
    rng = v.rng
    n = int((dur_s + 1.0) * SR)
    keys, pads, low, drums, fx = _canvases(n)
    hit = STING_RISER_S
    place(fx, M.riser(hit, amp=0.55, rng=rng), 0.0)
    place(drums, M.impact(amp=1.0), hit)
    toll(keys, hit, amp=1.0, rng=rng)
    place(keys, M.bell("D4", 1.4, vel=0.4, pan=0.15, rng=rng), hit + 0.006)
    place(low, M.bass("D2", 1.4, amp=1.0), hit)
    place(low, M.sub_pedal("D2", 1.6, amp=0.9, attack_s=0.02, release_s=0.9), hit)
    place(pads, M.pad("Dm", 0.6, amp=1.0, attack_s=0.02, release_s=1.2, open_hz=900.0, rng=rng), hit)
    mix = _mix(keys, pads, low, drums, fx, seed=v.seed + 23, delay=False)[: int(dur_s * SR)]
    # the ring is cut to the floor over the last 1.4 s: a sting ends, it does not fade away
    k = int(1.4 * SR)
    mix[-k:] *= (np.cos(np.linspace(0, math.pi / 2, k)) ** 2)[:, None]
    return mix


def render_entrance(v: WeeklyVoicing, dur_s: float = M.ENTRANCE_S) -> np.ndarray:
    """"Void Opinion": On Air's entrance, unchanged. A signature is a signature;
    the weekly borrows it whole so the listener who knows the daily show knows
    what is about to be said."""
    mv = M.Voicing(seed=v.seed, rng=v.rng, progression={k: o[0] for k, o in M.PROGRESSIONS.items()})
    return M.render_entrance(mv, dur_s)


def render_outro(v: WeeklyVoicing, dur_s: float = OUTRO_S) -> np.ndarray:
    """The cadence with the hook at half speed and the bell an octave up, the
    half-time drums under it, a riser into the fifth bar, and the landing on
    D MAJOR: the one resolution in the programme, held on a sub pedal with a
    bell arpeggio over it, then the pad falls to silence."""
    rng = v.rng
    n = int((dur_s + 3.0) * SR)
    keys, pads, low, drums, fx = _canvases(n)
    kicks: list[float] = []
    for b, chord in enumerate(CADENCE):
        at = b * BAR
        place(pads, M.pad(chord, BAR + 0.4, amp=1.0, attack_s=0.6, open_hz=900.0, rng=rng), at)
        _bassline(low, chord, at, amp=0.85, style="halftime" if b < 3 else "eighths")
        _pendulum(keys, chord, at, amp=0.24, rng=rng, bell_on_one=False)
    _drums(drums, kicks, 0.0, 4, "halftime", kick_amp=0.95, clock_amp=0.32, rng=rng, shape=[0.8, 0.9, 1.0, 1.0])
    _hook_half(keys, 0.0, amp=0.9, rng=rng, bell_octave=0.34)
    land = OUTRO_LAND_S
    place(fx, M.riser(1.8, amp=0.4, rng=rng), land - 1.8)
    place(drums, M.impact(amp=1.0), land)
    kicks.append(land)
    place(pads, M.pad("D", dur_s - land + 1.0, amp=1.0, attack_s=0.05, release_s=4.0, rng=rng), land)
    for note, pan_ in (("D4", -0.1), ("F#4", 0.1), ("A4", 0.0), ("D5", 0.0)):
        place(keys, M.ep(note, 4.0, vel=0.75, pan=pan_, rng=rng), land)
    for i, note in enumerate(("D5", "F#5", "A5", "D6")):
        place(keys, M.bell(note, 3.0 - 0.4 * i, vel=0.34 - 0.03 * i, pan=(-0.3, 0.3, -0.15, 0.0)[i], rng=rng),
              M._human(rng, land + 0.55 * (i + 1), 6.0))
    place(low, M.bass("D2", 2.5, amp=0.95), land)
    place(low, M.sub_pedal("D2", dur_s - land - 1.0, amp=0.55, attack_s=0.6, release_s=2.5), land + 1.5)
    pads = M.sidechain(pads, kicks)
    low = M.sidechain(low, kicks, depth_db=2.0)
    mix = _mix(keys, pads, low, drums, fx, seed=v.seed + 8)[: int(dur_s * SR)]
    tail = int(3.5 * SR)
    mix[-tail:] *= (np.cos(np.linspace(0, math.pi / 2, tail)) ** 2)[:, None]
    return mix


def spectrum_drone(avg_lean: float, lean_std: float, dur_s: float) -> np.ndarray:
    """The Week in Bias, sonified (rev 1's device, in the weekly's patches):
    a sub pedal whose pitch carries the week's mean lean (D at the centre, a
    fifth either way at the extremes) and whose detuning carries the spread,
    so a balanced-but-contested week beats audibly while a consensus sits
    still. Played under the NUMBERS read only; never written to disk."""
    n = int((dur_s + 2.0) * SR)
    t = np.arange(n) / SR
    base = M.hz("D2") * 2 ** (((float(avg_lean) - 50.0) / 50.0) * 7 / 12)
    spread = min(1.0, max(0.0, float(lean_std) / 25.0))
    cents = 2.0 + 28.0 * spread
    x = np.sin(2 * math.pi * base * t) + 0.7 * np.sin(2 * math.pi * base * 2 ** (cents / 1200) * t) \
        + 0.4 * np.sin(2 * math.pi * base * 2 * t)
    env = M._env(n, 2.0, 0.2, 1.0, 2.5, dur_s)
    return M.stereo(x * env * 0.3, 0.0)[: int(dur_s * SR)]
