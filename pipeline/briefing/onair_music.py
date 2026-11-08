"""On Air: the music, composed. Rev 3 (2026-11-07, CEO: "designed surgically,
from scratch; I don't like the tunes"). Rev 5 (2026-11-08): the Opinion is
read by the same voice as the news, so the firewall between them is the
MUSIC: the desk bed stops, a silence is held, and "Void Opinion" enters on a
cue with its own identity; the Opinion's bed is the same show in a warmer
room; and the whole score carries more bass where a speaker can feel it.
Rev 5c (2026-11-08, CEO: "add cool calming beats and tunes between stories;
ensure the score is also soothing"): the page-turn becomes an INTERLUDE, three
bars of a laid-back groove heard for itself between the stories; the desk
breathes between its items and a bell answers each breath; and every patch
and pattern is softened so the whole score is measurably calmer (fewer clock
onsets a second, less energy in the glare band over 3 kHz, a lower spectral
centroid) while it keeps the show's identity: D minor, 84 beats a minute,
the hook.

A score for a daily news conversation, in Void's voice: D minor, 84 beats a
minute, a four-chord cycle (i VI III VII, the cinematic cadence), a two-bar
hook on electric piano that falls to the tonic, a quarter-note ostinato with
a lilt, a round bass on the sub, a soft kick with a knock a phone hears, a
brush and a shaker for the clock, a pad that breathes, and a final chord that
lifts to the major. Stereo. Every sound is synthesised here from a patch;
nothing is sampled, nothing is looped.

Patches (the instruments):
    ep         two-operator FM electric piano (DX-style tine), lowpassed, with a tempo delay
    bell       two-operator FM glass (a 3.5:1 modulator), long release: the Opinion's register
    pad        six detuned saws, three a side, 24 dB/oct lowpass that opens over the attack
    bass       sub sine, its octave (so a small speaker hears the note), a round plucked saw
    kick       a 110 to 44 Hz sine sweep with a soft knock (700-2200 Hz, 3 ms), no click
    brush      the soft snare: shaped noise 400-1800 Hz, an 8 ms rise, 90 ms
    shaker     the clock: shaped noise 1.3-3.0 kHz, a 12 ms rise, 60 ms closed, 120 open
    riser      dark filtered noise rising into a downbeat, low
    impact     kick, sub and a low thump together, on the downbeat a riser lands on

Form (the cues), each composed to the length the producer asks for:
    theme      four bars: the pad and the bass, the pulse arrives, the hook, a soft riser
               into the downbeat the sign-on lands on
    bed        eight-bar phrases, layers entering and leaving by the day's seed, the
               hook once a phrase; a slow backbeat under the conversations, a relaxed
               pulse on the desk; the Opinion's bed is the slow room (below)
    interlude  three bars between two stories (rev 5c): a laid-back groove, a melody
               drawn from the hook over a chord pair, a release bar on the tonic the
               next anchor speaks over; two in an episode never share a melody, a
               chord pair or a voice
    entrance   "Void Opinion": out of a held silence a sub pedal on VI, then the hook
               in dotted augmentation on the bell, reharmonised VI iv V and left on
               the dominant with the tonic hanging over it; no pulse, no riser
    outro      the cycle in full, the bell doubling the hook, landing on D major

The Opinion's bed (`segment == "opinion"`): the harmonic rhythm halves (two
bars a chord), the cycle starts on VI and never lands on i; one soft kick a
bar and no clock; the bass walks root and fifth in half notes instead of eighths; a
sparse bell line, one note in two beats, in place of the ostinato; the pad
warmer (its filter opens to 800 Hz, not 900) and slower. Measurably: fewer
onsets a second than any news bed and a chroma profile further from theirs.

The stop (`ending == "stop"`): the desk bed does not rise into the entrance.
Its last downbeat is a hit (impact, a long bass root, the pad released) at
`STOP_RING_S` before its end; everything else is gone from that beat, the
ring decays, and the producer holds the studio floor before the entrance.

The desk's breaths (rev 5c, `accents`): the producer hands the desk bed the
moments its items pause for a breath; the ostinato rests through each and a
two-note bell tag lands in it, so the music surfaces between the items
instead of sitting under them.

`onair_score` keeps the standard (levels, band shape, duck, the checks) and
calls into this module for the sound. Everything here renders at SR = 48000,
stereo float64 of shape (n, 2).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import signal

SR = 48000
BPM = 84
BEAT = 60.0 / BPM
BAR = 4 * BEAT

# ---------------------------------------------------------------------------
# Notes and harmony
# ---------------------------------------------------------------------------

_NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
          "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def hz(name: str) -> float:
    i = len(name) - 1
    while i > 0 and not name[i].isdigit():
        i -= 1
    octave = int(name[i:])
    midi = 12 * (octave + 1) + _NOTES[name[:i]]
    return 440.0 * 2 ** ((midi - 69) / 12)


# Chords as (bass root, the fifth the bass walks to, keys voicing in the
# fourth/fifth octave, ostinato eighths, the bell's two notes). The fifth is
# placed in the sub where the band shape keeps it (40 to 90 Hz).
CHORDS = {
    "Dm": {"bass": "D2", "fifth": "A1", "pad": ("D3", "A3", "F4", "A4", "D5"), "ost": ("D4", "A4", "D5", "E5", "A4", "F5", "E5", "A4"), "bell": ("A5", "F5")},
    "Bb": {"bass": "Bb1", "fifth": "F2", "pad": ("Bb2", "F3", "D4", "F4", "A4"), "ost": ("F4", "Bb4", "D5", "F5", "Bb4", "D5", "C5", "A4"), "bell": ("D5", "F5")},
    "F":  {"bass": "F2", "fifth": "C2", "pad": ("F3", "C4", "A4", "C5", "E5"), "ost": ("F4", "C5", "E5", "F5", "C5", "A4", "G4", "C5"), "bell": ("C5", "A5")},
    "C":  {"bass": "C2", "fifth": "G1", "pad": ("C3", "G3", "E4", "G4", "D5"), "ost": ("E4", "G4", "C5", "D5", "G4", "E5", "D5", "G4"), "bell": ("E5", "G5")},
    "Gm": {"bass": "G1", "fifth": "D2", "pad": ("G2", "D3", "Bb3", "D4", "A4"), "ost": ("D4", "G4", "Bb4", "D5", "G4", "A4", "Bb4", "D5"), "bell": ("D5", "Bb4")},
    "A":  {"bass": "A1", "fifth": "E2", "pad": ("A2", "E3", "C#4", "E4", "G4"), "ost": ("E4", "A4", "C#5", "E5", "A4", "G4", "E5", "C#5"), "bell": ("E5", "C#5")},
    "Asus": {"bass": "A1", "fifth": "E2", "pad": ("A2", "E3", "D4", "E4", "A4"), "ost": ("E4", "A4", "D5", "E5", "A4", "D5", "E5", "A4"), "bell": ("E5", "D5")},
    "D":  {"bass": "D2", "fifth": "A1", "pad": ("D3", "A3", "F#4", "A4", "D5"), "ost": ("D4", "A4", "D5", "F#5", "A4", "D5", "F#5", "A5"), "bell": ("A5", "F#5")},
}
PROGRESSIONS = {
    "lead": [["Dm", "Bb", "F", "C"], ["Dm", "Bb", "Gm", "Asus"], ["Dm", "F", "C", "Gm"]],
    "second": [["Bb", "F", "Dm", "C"], ["Gm", "Dm", "Bb", "C"], ["Dm", "C", "Bb", "F"]],
    "desk": [["Dm", "C", "Dm", "Bb"], ["Dm", "Bb", "Dm", "C"]],
    # Rev 5: the Opinion never lands on i (the news is home; the Opinion is
    # the argument), starts on VI and spends two bars a chord
    # (OPINION_BARS_PER_CHORD): the same key heard from another room. The
    # tonic is only ever the hook's hanging note.
    "opinion": [["Bb", "Gm", "F", "A"], ["Bb", "F", "Gm", "Asus"], ["Gm", "Bb", "F", "Asus"]],
    "close": [["Dm", "Bb", "F", "C"]],
}
OPINION_BARS_PER_CHORD = 2
# The hook: (note, start beat, length beats), two bars, over Dm then Bb.
HOOK = [("D5", 0.0, 1.5), ("C5", 1.5, 0.5), ("A4", 2.0, 1.0), ("F4", 3.0, 1.0),
        ("G4", 4.0, 1.5), ("F4", 5.5, 0.5), ("D4", 6.0, 2.0)]
HOOK_INVERTED = [("A4", 0.0, 1.0), ("C5", 1.0, 1.0), ("D5", 2.0, 2.0), ("F5", 4.0, 1.5), ("E5", 5.5, 2.5)]
# The hook's answer (rev 5c): the same fall, from the top of the hook's range,
# landing on the fifth instead of the tonic: an open phrase for an interlude.
HOOK_ANSWER = [("F5", 0.0, 1.0), ("E5", 1.0, 0.5), ("D5", 1.5, 1.5), ("C5", 3.0, 1.0),
               ("A4", 4.0, 1.5), ("F4", 5.5, 0.5), ("A4", 6.0, 2.0)]
# The hook in dotted augmentation (every value 1.5x, three bars) for the
# Opinion's entrance: the same seven notes, slowed, so it is recognisably the
# show and unmistakably not the news.
HOOK_AUGMENTED = [(n, s * 1.5, l * 1.5) for n, s, l in HOOK]
# The entrance: one bar of the pedal alone, then the augmented hook over VI iv V.
ENTRANCE_BARS = 4
ENTRANCE_HARMONY = ["Bb", "Bb", "Gm", "Asus"]
ENTRANCE_S = round(ENTRANCE_BARS * BAR, 1)            # 11.4 s
ENTRANCE_VOICE_S = round(BAR + 9.0 * BEAT + 0.5, 1)   # 9.8 s: A speaks once the last note has landed
STOP_RING_S = 2.6                                     # a stopped bed: the hit lands this long before its end

# The interlude (rev 5c): three bars. Two bars of a melody drawn from the hook
# over a chord pair, then a release bar on the tonic that the next anchor
# speaks over (INTERLUDE_VOICE_S: the second beat of the release bar, once the
# landing has been heard). Each fragment carries the chord pairs it is written
# over; `interlude_plan` picks by the day's seed, and two interludes in one
# episode are consecutive picks, so they never share a fragment, a pair or a
# voice (electric piano against bell).
INTERLUDE_BARS = 3
INTERLUDE_S = round(INTERLUDE_BARS * BAR, 1)          # 8.6 s
INTERLUDE_VOICE_S = round(2 * BAR + 1.0 * BEAT, 1)    # 6.4 s: the next anchor starts over the release
INTERLUDE_FRAGMENTS = [
    (HOOK, [("Dm", "Bb"), ("Dm", "Gm")]),
    (HOOK_INVERTED, [("F", "C"), ("Bb", "C")]),
    (HOOK_ANSWER, [("Bb", "F"), ("Gm", "F")]),
]
INTERLUDE_RELEASE = "Dm"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _t(n: int) -> np.ndarray:
    return np.arange(n, dtype=np.float64) / SR


def _env(n: int, a: float, d: float, s: float, r: float, hold_s: float) -> np.ndarray:
    """ADSR in seconds; `hold_s` is the note's sounding length before release."""
    t = _t(n)
    env = np.zeros(n)
    na = max(1, int(a * SR))
    env[:na] = np.linspace(0, 1, na)[: min(na, n)]
    nd = max(1, int(d * SR))
    if na < n:
        dec = s + (1 - s) * np.exp(-np.arange(n - na) / (nd / 4.6))
        env[na:] = dec
    nh = min(n, int(hold_s * SR))
    rel = np.exp(-np.arange(n - nh) / max(r * SR / 4.6, 1))
    env[nh:] *= rel
    return env


def _lp(x: np.ndarray, hz_: float, order: int = 4) -> np.ndarray:
    sos = signal.butter(order, min(hz_, SR / 2 - 100), btype="low", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def _hp(x: np.ndarray, hz_: float, order: int = 2) -> np.ndarray:
    sos = signal.butter(order, max(hz_, 10.0), btype="high", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def _bp(x: np.ndarray, lo: float, hi: float, order: int = 4) -> np.ndarray:
    sos = signal.butter(order, [lo, min(hi, SR / 2 - 100)], btype="band", fs=SR, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def _sweep_lp(x: np.ndarray, hz_from: float, hz_to: float, sweep_s: float) -> np.ndarray:
    """A lowpass whose cutoff moves over the first `sweep_s`: rendered in 20 ms
    blocks with a one-pole-pair filter each, so the sweep is smooth enough."""
    n = len(x)
    blk = int(0.02 * SR)
    out = np.zeros_like(x)
    zi = None
    for i in range(0, n, blk):
        frac = min(1.0, (i / SR) / max(sweep_s, 1e-3))
        c = hz_from + (hz_to - hz_from) * (0.5 - 0.5 * math.cos(math.pi * frac))
        sos = signal.butter(2, min(c, SR / 2 - 100), btype="low", fs=SR, output="sos")
        seg = x[i:i + blk]
        if zi is None:
            zi = signal.sosfilt_zi(sos)
            zi = np.repeat(zi[:, :, None], seg.shape[1], axis=2) * 0.0 if seg.ndim == 2 else zi * 0.0
        y, zi = signal.sosfilt(sos, seg, axis=0, zi=zi)
        out[i:i + blk] = y
    return out


def stereo(mono: np.ndarray, pan: float = 0.0) -> np.ndarray:
    theta = (pan + 1.0) * math.pi / 4
    return np.stack([mono * math.cos(theta), mono * math.sin(theta)], axis=1)


def place(canvas: np.ndarray, x: np.ndarray, at_s: float) -> None:
    i = int(at_s * SR)
    if i >= len(canvas) or i + len(x) <= 0:
        return
    if i < 0:
        x = x[-i:]
        i = 0
    m = min(len(x), len(canvas) - i)
    canvas[i:i + m] += x[:m]


def _norm(x: np.ndarray, peak: float = 0.8) -> np.ndarray:
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return x * (peak / m) if m > 0 else x


# ---------------------------------------------------------------------------
# Patches
# ---------------------------------------------------------------------------

def ep(note: str, length_s: float, *, vel: float = 0.8, pan: float = 0.0, rng=None) -> np.ndarray:
    """Electric piano: carrier sine, a 1:1 modulator whose index falls with the
    note (the bark of a tine), a 14:1 modulator for the attack, lowpassed at
    2.6 kHz (rev 5c: 3 kHz before; mellower), a 1.6 s release. The attack's
    bark is softer and a little slower than rev 5's (12 ms, not 30 ms of a
    brighter index): a tine touched, not struck."""
    f = hz(note)
    n = int((length_s + 1.8) * SR)
    t = _t(n)
    idx = (1.0 + 2.0 * vel) * np.exp(-t / 0.35) + 0.22
    attack_idx = 0.5 * vel * np.exp(-t / 0.012)
    mod = idx * np.sin(2 * math.pi * f * t) + attack_idx * np.sin(2 * math.pi * f * 14 * t)
    x = np.sin(2 * math.pi * f * t + mod)
    x *= _env(n, 0.006, 0.9, 0.35, 1.6, length_s)
    x = _lp(x, 2600.0, 2)
    return stereo(x * vel, pan)


def bell(note: str, length_s: float, *, vel: float = 0.8, pan: float = 0.0, rng=None) -> np.ndarray:
    """Glass: a carrier with a 3.5:1 modulator whose index falls over 0.8 s
    (the inharmonic partials of a struck bar), a second carrier 4 cents off
    for shimmer, a 24 dB/oct lowpass at 2.4 kHz (rev 5c: 12 dB/oct at 3 kHz
    before, and the index a fifth smaller: the bar is struck with felt), a
    2.8 s release. The Opinion's register: nothing in the news is struck like
    this."""
    f = hz(note)
    n = int((length_s + 3.0) * SR)
    t = _t(n)
    idx = (0.7 + 1.0 * vel) * np.exp(-t / 0.8) + 0.08
    mod = idx * np.sin(2 * math.pi * f * 3.5 * t)
    x = np.sin(2 * math.pi * f * t + mod) + 0.5 * np.sin(2 * math.pi * f * 2 ** (4 / 1200) * t + 0.7 * mod)
    x *= _env(n, 0.008, 1.6, 0.3, 2.8, length_s)
    x = _lp(x, 2400.0, 4)
    return stereo(x * vel * 0.6, pan)


def pad(chord: str, length_s: float, *, amp: float = 1.0, attack_s: float = 1.6, release_s: float = 2.8,
        open_hz: float = 900.0, rng=None) -> np.ndarray:
    """Six detuned saws from the voicing, three a side, a 24 dB/oct lowpass
    that opens from 400 to `open_hz` (900 under the news since rev 5c, 1100
    before; 800 under the Opinion: warmer) over the attack, slow breathing."""
    rng = rng or np.random.default_rng(0)
    voicing = CHORDS[chord]["pad"]
    n = int((length_s + release_s) * SR)
    t = _t(n)
    left = np.zeros(n)
    right = np.zeros(n)
    for k, name in enumerate(voicing):
        f = hz(name)
        for side, det_cents in ((left, -7.0), (right, +7.0)):
            for d in (det_cents, det_cents * 0.5 + rng.normal(0, 1.0)):
                ff = f * 2 ** (d / 1200)
                side += signal.sawtooth(2 * math.pi * ff * t + rng.uniform(0, 2 * math.pi)) * (0.7 if k == 0 else 0.45)
    x = np.stack([left, right], axis=1)
    x = _sweep_lp(x, 400.0, open_hz, attack_s)
    breath = 1.0 - 0.18 * 0.5 * (1 + np.sin(2 * math.pi * 0.06 * t + rng.uniform(0, 6.28)))
    env = _env(n, attack_s, 0.1, 1.0, release_s, length_s) * breath
    return x * env[:, None] * amp * 0.22


def bass(note: str, length_s: float = 0.45, *, amp: float = 1.0) -> np.ndarray:
    """Sub sine, its octave at -9 dB (rev 5: the note's body in 100 to 175
    Hz, which is what a small speaker hears of it; the band shape's low-pass
    moved to 130 Hz to keep it), under a round plucked saw whose cutoff falls
    260 to 100 Hz over 160 ms (rev 5c: 320 to 110 before, and the pluck a
    third quieter: a thumb, not a pick)."""
    f = hz(note)
    n = int((length_s + 0.4) * SR)
    t = _t(n)
    sub = np.sin(2 * math.pi * f * t) * _env(n, 0.006, 0.3, 0.55, 0.28, length_s)
    octave = np.sin(2 * math.pi * 2 * f * t) * _env(n, 0.006, 0.22, 0.4, 0.2, length_s)
    saw = signal.sawtooth(2 * math.pi * f * t) * _env(n, 0.004, 0.16, 0.2, 0.16, length_s)
    saw = _sweep_lp(saw[:, None], 260.0, 100.0, 0.16)[:, 0]
    x = 0.8 * sub + 0.28 * octave + 0.34 * saw
    return stereo(x * amp, 0.0)


def sub_pedal(note: str, length_s: float, *, amp: float = 1.0, attack_s: float = 1.5, release_s: float = 1.2) -> np.ndarray:
    """A held sub tone with its octave, breathing slowly: the entrance's floor."""
    f = hz(note)
    n = int((length_s + release_s) * SR)
    t = _t(n)
    x = np.sin(2 * math.pi * f * t) + 0.22 * np.sin(2 * math.pi * 2 * f * t)
    x *= 1.0 - 0.12 * 0.5 * (1 + np.sin(2 * math.pi * 0.11 * t))
    return stereo(x * _env(n, attack_s, 0.2, 1.0, release_s, length_s) * 0.42 * amp, 0.0)


def kick(*, amp: float = 1.0) -> np.ndarray:
    """Rev 5c: a soft kick. A 110 to 44 Hz sweep (150 to 42 before) with a 6 ms
    rise and a 0.3 s body, and a KNOCK in place of the click: 3 ms of noise in
    700 to 2200 Hz at a tenth of the body, so a phone still hears the beat but
    nothing in it is sharp and nothing of it reaches the clock's band."""
    n = int(0.7 * SR)
    t = _t(n)
    f = 44.0 + 66.0 * np.exp(-t / 0.05)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.minimum(1.0, t / 0.006) * np.exp(-t / 0.3)
    knock = np.random.default_rng(5).normal(0, 1, n) * np.minimum(1.0, t / 0.001) * np.exp(-t / 0.003)
    knock = _bp(knock[:, None], 700.0, 2200.0)[:, 0]
    knock = knock / (np.max(np.abs(knock)) + 1e-9) * 0.10
    x = body + knock
    return stereo(_norm(x, 1.0) * amp, 0.0)


def brush(*, amp: float = 1.0, pan: float = -0.2, rng=None) -> np.ndarray:
    """The soft snare (rev 5c, in place of the rim): shaped noise in 400 to
    1800 Hz with an 8 ms rise and a 90 ms fall. A brush drawn across a head;
    nothing of it in the clock's band or the glare band."""
    rng = rng or np.random.default_rng(9)
    n = int(0.3 * SR)
    t = _t(n)
    x = rng.normal(0, 1, n) * np.minimum(1.0, t / 0.008) * np.exp(-t / 0.09)
    x = _bp(x[:, None], 400.0, 1800.0)[:, 0]
    return stereo(_norm(x, 1.0) * amp, pan)


def shaker(*, amp: float = 1.0, open_: bool = False, pan: float = 0.25, rng=None) -> np.ndarray:
    """The clock (rev 5c, in place of the tick): shaped noise in 1.3 to 3.0
    kHz with a 12 ms rise, 60 ms closed or 120 ms open. The tick was 2.5 to 5
    kHz with a 2 ms rise; this sits an octave lower, arrives slower, and
    leaves the glare band over 3 kHz nearly empty."""
    rng = rng or np.random.default_rng(7)
    n = int(0.3 * SR)
    t = _t(n)
    x = rng.normal(0, 1, n) * np.minimum(1.0, t / 0.012) * np.exp(-t / (0.12 if open_ else 0.06))
    x = _bp(x[:, None], 1300.0, 3000.0)[:, 0]
    return stereo(_norm(x, 1.0) * amp, pan)


def riser(length_s: float = 1.5, *, amp: float = 1.0, rng=None) -> np.ndarray:
    """Noise rising into a downbeat: level up, a bandpass sweeping 200 Hz to
    2.2 kHz (rev 5c: 300 to 3.5 kHz before, and darker: a breath drawn in)."""
    rng = rng or np.random.default_rng(11)
    n = int(length_s * SR)
    t = _t(n)
    x = rng.normal(0, 1, n) * (t / length_s) ** 2.5
    blk = int(0.02 * SR)
    out = np.zeros(n)
    for i in range(0, n, blk):
        frac = i / n
        lo = 200.0 * (1 + 4 * frac)
        sos = signal.butter(2, [lo, min(lo * 2.2, 2600.0)], btype="band", fs=SR, output="sos")
        out[i:i + blk] = signal.sosfilt(sos, x[i:i + blk])
    out[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
    return stereo(_norm(out, 1.0) * amp, 0.0) * np.array([[0.9, 1.1]])


def impact(*, amp: float = 1.0) -> np.ndarray:
    n = int(1.2 * SR)
    t = _t(n)
    thump = np.sin(2 * math.pi * (36.7 * (1 + 0.6 * np.exp(-t / 0.05))) * t) * np.exp(-t / 0.5)
    noise = _lp(np.random.default_rng(13).normal(0, 1, n), 400.0, 4) * np.exp(-t / 0.12) * 0.5
    x = stereo(_norm(thump + noise, 1.0), 0.0)
    k = kick(amp=1.0)
    place(x, k, 0.0)
    return _norm(x, 1.0) * amp


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

def tempo_delay(x: np.ndarray, *, beats: float = 0.75, feedback: float = 0.32, mix: float = 0.22) -> np.ndarray:
    """A dotted-eighth delay, filtered darker each repeat, ping-ponged."""
    d = int(beats * BEAT * SR)
    out = x.copy()
    wet = np.zeros_like(x)
    tap = x.copy()
    for k in range(5):
        tap = _lp(tap, 2200.0 / (1 + 0.5 * k), 2) * feedback
        shifted = np.zeros_like(x)
        shifted[d * (k + 1):] = tap[: len(x) - d * (k + 1)] if d * (k + 1) < len(x) else 0
        # ping-pong: swap channels every repeat
        if k % 2 == 0:
            shifted = shifted[:, ::-1]
        wet += shifted
    return out + wet * mix / feedback


def _ir(decay_s: float, seed: int, lp_hz: float) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n = int(decay_s * 3 * SR)
    t = _t(n)
    pre = int(0.022 * SR)
    ir = rng.normal(0, 1, n) * np.exp(-t / (decay_s / 3))
    ir[:pre] *= np.linspace(0, 1, pre) ** 3     # a little pre-delay
    ir = _lp(ir, lp_hz, 2)
    return ir / (np.max(np.abs(ir)) + 1e-9)


def reverb(x: np.ndarray, *, wet: float = 0.3, decay_s: float = 1.8, lp_hz: float = 2800.0, seed: int = 21) -> np.ndarray:
    """A stereo room: two decorrelated tails, one a side (rev 5c: the tails
    lowpassed at 2.8 kHz, 3.2 before; a softer room)."""
    if wet <= 0:
        return x
    irl, irr = _ir(decay_s, seed, lp_hz), _ir(decay_s, seed + 1, lp_hz)
    wl = signal.fftconvolve(x[:, 0], irl)[: len(x)]
    wr = signal.fftconvolve(x[:, 1], irr)[: len(x)]
    w = np.stack([wl, wr], axis=1)
    w = w / (np.max(np.abs(w)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)
    return (1 - wet) * x + wet * w


def sidechain(x: np.ndarray, kick_times: list[float], *, depth_db: float = 3.0, recover_s: float = 0.34) -> np.ndarray:
    """The pump: a dip on every kick, recovering over `recover_s` (rev 5c: 3 dB
    over 340 ms, from 5 dB over 220 ms; the pad leans, it does not duck)."""
    n = len(x)
    g = np.zeros(n)
    k = int(recover_s * SR)
    curve = -depth_db * (1 - np.linspace(0, 1, k)) ** 1.5
    for t in kick_times:
        i = int(t * SR)
        if 0 <= i < n:
            m = min(k, n - i)
            g[i:i + m] = np.minimum(g[i:i + m], curve[:m])
    return x * (10 ** (g / 20))[:, None]


# ---------------------------------------------------------------------------
# Arrangement
# ---------------------------------------------------------------------------

@dataclass
class Voicing:
    seed: int
    rng: np.random.Generator
    progression: dict[str, list[str]]


def voicing_for(seed: int) -> Voicing:
    rng = np.random.default_rng(seed)
    prog = {seg: opts[int(rng.integers(len(opts)))] for seg, opts in PROGRESSIONS.items()}
    return Voicing(seed=seed, rng=rng, progression=prog)


SWING = 0.58          # off-beats land at 58 % of the beat, not 50 (rev 5c: 56 before): a lazier pulse
HUMAN_MS = 8.0        # timing jitter, one sigma


def _human(rng, at: float, ms: float = HUMAN_MS) -> float:
    return at + float(rng.normal(0, ms / 1000.0)) if rng is not None else at


# The ostinato's lilt (rev 5c): the beats and the "and" of three, five notes a
# bar instead of eight; the eighth-note version is kept for a full bar.
OSTINATO_LILT = frozenset({1, 3, 7})


def _ostinato(canvas, chord: str, bar_at: float, *, amp: float, rests: set[int] = frozenset(), rng=None,
              shape: float = 1.0, skip: tuple[tuple[float, float], ...] = ()):
    """`shape` scales the phrase's dynamics: under 1 the line sits back, over 1
    it leans in; the first note of a bar is always a little louder and the
    off-beats swing. `skip` are spans (seconds) the line rests through: the
    desk's breaths (rev 5c), where the bell answers instead."""
    for k, note in enumerate(CHORDS[chord]["ost"]):
        if k in rests:
            continue
        beat_pos = k // 2 + (SWING if k % 2 else 0.0)
        at = _human(rng, bar_at + beat_pos * BEAT)
        vel = amp * shape * (1.0 if k % 2 == 0 else 0.62) * (1.12 if k == 0 else 1.0)
        if rng is not None:
            vel *= float(rng.uniform(0.86, 1.1))
        if any(lo <= at < hi for lo, hi in skip):
            continue        # after the draws, so a rested note changes nothing else in the bed
        place(canvas, ep(note, 0.34, vel=vel, pan=(-0.18 if k % 2 == 0 else 0.18), rng=rng), at)


def _melody(canvas, notes, bar_at: float, *, amp: float, voice: str = "ep", rng=None, pan_spread: float = 0.0):
    """A melody from its note list: (note, start beat, length beats)."""
    for i, (note, start, length) in enumerate(notes):
        vel = amp * (1.0 if i in (0, 4) else 0.86) * (float(rng.uniform(0.92, 1.06)) if rng is not None else 1.0)
        pan = (-1.0 if i % 2 == 0 else 1.0) * pan_spread
        x = (bell if voice == "bell" else ep)(note, length * BEAT * 0.95, vel=vel, pan=pan, rng=rng)
        place(canvas, x, _human(rng, bar_at + start * BEAT, 5.0))


def _hook(canvas, bar_at: float, *, amp: float, inverted: bool = False, rng=None):
    _melody(canvas, HOOK_INVERTED if inverted else HOOK, bar_at, amp=amp, rng=rng)


def _fill(canvas, bar_at: float, *, amp: float, rng=None):
    """A shaker drawn over the last beat into the next downbeat, and a brush
    on the last off-beat (rev 5c: the tick roll is gone)."""
    for k, (pos, lvl) in enumerate(((3.0, 0.45), (3.5, 0.6), (3.75, 0.7))):
        at = _human(rng, bar_at + pos * BEAT, 4.0)
        place(canvas, shaker(amp=amp * lvl, open_=(k == 2), rng=rng), at)
    place(canvas, brush(amp=amp * 0.55, rng=rng), _human(rng, bar_at + 3.5 * BEAT, 4.0))


def _drums(canvas, kicks: list[float], start: float, bars: int, pattern: str, *, kick_amp: float, clock_amp: float,
           rng=None, drop_bars: set[int] = frozenset(), fill_bars: set[int] = frozenset(),
           shape: "list[float] | None" = None):
    """`shape[b]` scales bar b's level (0 silences it): the arc of the bed.

    Patterns (rev 5c, every one softened):
        half     the conversations, the theme, the outro: kick on one and three, a brush
                 on two and four, the shaker on the "and" of two and of four (two a bar)
        pulse    the desk: kick on one and three and a soft pickup on the "and" of four,
                 a brush on two and four, the shaker on the "and" of two and of four;
                 the bass carries the motion the ticks used to
        groove   the interlude: kick on one and the "and" of two, a brush on two and
                 four, the shaker on the "and" of two and of four
        slow     the Opinion: one soft kick a bar and no clock at all
    """
    for b in range(bars):
        bar_at = start + b * BAR
        dropped = b in drop_bars
        sc = shape[b] if shape is not None and b < len(shape) else 1.0
        if sc <= 0.0:
            continue
        k_amp, c_amp = kick_amp * sc, clock_amp * sc
        if b in fill_bars:
            _fill(canvas, bar_at, amp=c_amp, rng=rng)
        for beat in range(4):
            at = bar_at + beat * BEAT
            off = _human(rng, at + SWING * BEAT, 5.0)
            if pattern == "half":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=k_amp * (1.0 if beat == 0 else 0.8)), at)
                    kicks.append(at)
                if beat in (1, 3):
                    place(canvas, brush(amp=c_amp * 0.7, rng=rng), _human(rng, at, 5.0))
                    place(canvas, shaker(amp=c_amp * 0.6, open_=(beat == 3), rng=rng), off)
                continue
            if pattern == "pulse":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=k_amp * (1.0 if beat == 0 else 0.85)), at)
                    kicks.append(at)
                if beat == 3 and not dropped:
                    place(canvas, kick(amp=k_amp * 0.45), off)
                    kicks.append(off)
                if beat in (1, 3):
                    place(canvas, brush(amp=c_amp * 0.65, rng=rng), _human(rng, at, 5.0))
                    place(canvas, shaker(amp=c_amp * 0.6, open_=(beat == 3), rng=rng), off)
                continue
            if pattern == "groove":
                if beat == 0 and not dropped:
                    place(canvas, kick(amp=k_amp), at)
                    kicks.append(at)
                if beat == 1 and not dropped:
                    place(canvas, kick(amp=k_amp * 0.7), off)
                    kicks.append(off)
                if beat in (1, 3):
                    place(canvas, brush(amp=c_amp * (0.55 if beat == 1 else 0.65), rng=rng), _human(rng, at, 5.0))
                    place(canvas, shaker(amp=c_amp * 0.6, open_=(beat == 3), rng=rng), off)
                continue
            if pattern == "slow":
                # the Opinion's room: one soft kick on the downbeat and no
                # clock at all (no shaker, no brush): an argument, not a bulletin.
                # Measured as `onair_score.clock_density`, the news beds carry
                # over twice the onsets in 2-6 kHz whatever the seed.
                if beat == 0 and not dropped:
                    place(canvas, kick(amp=k_amp * 0.8), at)
                    kicks.append(at)
    return


def _bassline(canvas, chord: str, bar_at: float, *, amp: float, style: str = "half"):
    """The bass by style (rev 5c; the eighth-note pulse is gone from the beds):
        half    the root held from one, again on three, a short pickup on the "and" of four
        pulse   the desk: root on one, the "and" of two and three, the fifth on four
        groove  the interlude: root on one and the "and" of two, the fifth on four
        walk    the Opinion: the root held a dotted half, the fifth on four
        eighths the theme's and the outro's last bars: the root in eighths
    """
    root = CHORDS[chord]["bass"]
    fifth = CHORDS[chord]["fifth"]
    if style == "walk":
        place(canvas, bass(root, 2.0 * BEAT, amp=amp), bar_at)
        place(canvas, bass(fifth, 0.9 * BEAT, amp=amp * 0.8), bar_at + 3.0 * BEAT)
        return
    if style == "half":
        place(canvas, bass(root, 1.6 * BEAT, amp=amp), bar_at)
        place(canvas, bass(root, 1.2 * BEAT, amp=amp * 0.82), bar_at + 2.0 * BEAT)
        place(canvas, bass(root, 0.35 * BEAT, amp=amp * 0.5), bar_at + (3.0 + SWING) * BEAT)
        return
    if style == "pulse":
        place(canvas, bass(root, 1.2 * BEAT, amp=amp), bar_at)
        place(canvas, bass(root, 0.4 * BEAT, amp=amp * 0.7), bar_at + (1.0 + SWING) * BEAT)
        place(canvas, bass(root, 0.9 * BEAT, amp=amp * 0.9), bar_at + 2.0 * BEAT)
        place(canvas, bass(fifth, 0.8 * BEAT, amp=amp * 0.75), bar_at + 3.0 * BEAT)
        return
    if style == "groove":
        place(canvas, bass(root, 1.4 * BEAT, amp=amp), bar_at)
        place(canvas, bass(root, 0.7 * BEAT, amp=amp * 0.75), bar_at + (1.0 + SWING) * BEAT)
        place(canvas, bass(fifth, 0.7 * BEAT, amp=amp * 0.7), bar_at + 3.0 * BEAT)
        return
    for k in range(8):
        place(canvas, bass(root, 0.42, amp=amp * (1.0 if k % 2 == 0 else 0.7)), bar_at + k * 0.5 * BEAT)


def _bell_line(canvas, chord: str, bar_at: float, *, amp: float, rng=None, beats: tuple[float, ...] = (0.0, 2.0)):
    """One bell note in two beats from the chord's two bell tones, alternating,
    panned apart: the Opinion's line in place of the ostinato."""
    notes = CHORDS[chord]["bell"]
    for i, b in enumerate(beats):
        vel = amp * (1.0 if i == 0 else 0.8) * (float(rng.uniform(0.9, 1.08)) if rng is not None else 1.0)
        place(canvas, bell(notes[i % len(notes)], 1.6 * BEAT, vel=vel, pan=(-0.3 if i % 2 == 0 else 0.3), rng=rng),
              _human(rng, bar_at + b * BEAT, 6.0))


BREATH_REST = (0.15, 1.2)      # the ostinato rests from this long before a breath's tag to this long after it


def _bell_tag(canvas, chord: str, at: float, *, amp: float):
    """The desk's breath (rev 5c): two bell notes from the chord, the second a
    half beat after the first, panned apart. It lands where the duck has let
    the bed up between two desk items, so the music surfaces there. Its
    jitter comes from a generator seeded by its own time, not the day's, so a
    bed with breaths and the same bed without them share every other draw."""
    rng = np.random.default_rng(int(at * 1000))
    notes = CHORDS[chord]["bell"]
    place(canvas, bell(notes[0], 1.2 * BEAT, vel=amp, pan=-0.3), _human(rng, at, 5.0))
    place(canvas, bell(notes[1], 1.6 * BEAT, vel=amp * 0.8, pan=0.3), _human(rng, at + 0.5 * BEAT, 5.0))


def render_theme(v: Voicing, dur_s: float = 11.6) -> np.ndarray:
    """Four bars in: the pad and the bass; the pulse arrives in the second bar
    with the ostinato's lilt; the hook; a soft riser into the downbeat the
    sign-on lands on, then the pad holds under the voice."""
    n = int((dur_s + 2.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    fx = np.zeros((n, 2))
    kicks: list[float] = []
    prog = ["Dm", "Bb", "F", "C"]
    for b, chord in enumerate(prog):
        at = b * BAR
        _bassline(low, chord, at, amp=0.8, style="half" if b < 3 else "eighths")
        _ostinato(keys, chord, at, amp=(0.3, 0.36, 0.4, 0.4)[b], rests=OSTINATO_LILT, rng=v.rng)
        # the pad is the floor from the first bar (quiet), and opens from bar two
        place(pads, pad(chord, BAR + 0.3, amp=(0.5, 0.9, 0.95, 1.0)[b], attack_s=(1.6, 1.0, 0.5, 0.5)[b], rng=v.rng), at)
    _drums(drums, kicks, 0.0, 4, "half", kick_amp=0.9, clock_amp=0.34, rng=v.rng, shape=[0.0, 0.75, 1.0, 1.0])
    _hook(keys, 2 * BAR, amp=0.9, rng=v.rng)
    place(fx, riser(1.5, amp=0.3, rng=v.rng), 4 * BAR - 1.5)
    place(drums, impact(amp=0.95), 4 * BAR)
    kicks.append(4 * BAR)
    place(pads, pad("Dm", dur_s - 4 * BAR + 1.0, amp=1.0, attack_s=0.05, release_s=3.5, rng=v.rng), 4 * BAR)
    place(keys, ep("D4", 2.5, vel=0.7, pan=0.0), 4 * BAR)
    place(keys, ep("A4", 2.5, vel=0.55, pan=0.1), 4 * BAR)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=2.0)
    mix = reverb(keys, wet=0.32, decay_s=2.2, seed=v.seed) + reverb(pads, wet=0.44, decay_s=3.0, seed=v.seed + 2) + low + drums + fx
    return mix[: int(dur_s * SR)]


def _arc(bars: int, ending: str, rng) -> tuple[list[float], list[float], set[int], set[int]]:
    """The shape of a bed in bars: (drum level per bar, keys level per bar,
    bars with a fill, bars dropped). It enters on pad and bass alone, the
    pulse arrives, it builds across eight-bar phrases with a dip before each
    new phrase, and it ends either thinning out ("out": the drums leave two
    bars early and the keys sit back) or gathering ("rise": a fill and
    everything leaning in, for the transition it hands over to)."""
    drums = [0.0] * bars
    keys = [0.0] * bars
    fills: set[int] = set()
    drops: set[int] = set()
    for b in range(bars):
        pos = b % 8
        # the pulse enters at bar 2 (or bar 1 on a short bed) and builds over the phrase
        if b == 0:
            drums[b] = 0.0 if bars > 4 else 0.7
        elif b == 1:
            drums[b] = 0.55 if bars > 4 else 0.9
        else:
            drums[b] = 0.8 + 0.2 * min(1.0, pos / 6.0)
        keys[b] = 0.0 if b == 0 and bars > 3 else (0.7 + 0.3 * min(1.0, pos / 5.0))
        if pos == 7 and b < bars - 2:
            drums[b] *= 0.55                       # the dip before a new phrase
            if rng.random() < 0.35:                # rev 5c: fewer fills (0.6 before)
                fills.add(b)
    if ending == "out" and bars >= 4:
        drums[-1] = 0.0
        drums[-2] = 0.0
        keys[-1] = 0.5
        keys[-2] = 0.7
    elif ending == "stop":
        # everything plays at full momentum up to the hit; `render_bed` cuts
        # the bars after it, so the arc itself does not thin
        for k in (1, 2):
            if bars - k >= 0:
                drums[bars - k] = 1.0
                keys[bars - k] = 1.0
    elif ending == "rise":
        for k in (1, 2):
            if bars - k >= 0:
                drums[bars - k] = 1.0
                keys[bars - k] = 1.0
        if bars >= 2:
            fills.add(bars - 1)
    return drums, keys, fills, drops


def render_bed(v: Voicing, segment: str, dur_s: float, *, ending: str = "out",
               accents: tuple[float, ...] = ()) -> np.ndarray:
    """A bed with an arc (`_arc`): pad and bass enter alone, the pulse arrives,
    the ostinato and the hook come and go by the day's seed, a dip and a fill
    before each eight-bar phrase, and an ending that thins out ("out"),
    gathers into the transition ("rise") or STOPS on a hit ("stop", the desk
    before the Opinion). Composed to length; never looped; a bar in eight
    dropped. The Opinion's bed is the slow room described in the module
    docstring: two bars a chord, one kick a bar, a walking bass, bells.
    `accents` (rev 5c) are seconds into the bed where a bell tag lands: the
    desk's breaths."""
    opinion = segment == "opinion"
    pattern = {"lead": "half", "second": "half", "desk": "pulse", "opinion": "slow", "close": "half"}[segment]
    prog = v.progression[segment]
    # A stopped bed ends on the grid: the hit is exactly STOP_RING_S before the
    # end, so the composition is shifted by the remainder and the first part
    # bar is the pad alone (the entry fades over it anyway).
    origin = 0.0
    stop_at = None
    if ending == "stop":
        stop_at = dur_s - STOP_RING_S
        origin = stop_at - math.floor(stop_at / BAR) * BAR
    bars = int(math.ceil((dur_s - origin) / BAR)) + 1
    n = int((origin + bars * BAR + 3.5) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    kicks: list[float] = []
    d_shape, k_shape, fills, _ = _arc(bars, ending, v.rng)
    if segment == "desk":
        d_shape = [max(x, 0.85) if b else 0.9 for b, x in enumerate(d_shape)]   # the desk never thins: momentum
    stop_bar = None
    if stop_at is not None:
        stop_bar = int(round((stop_at - origin) / BAR))
        for b in range(stop_bar, bars):
            d_shape[b] = 0.0
            k_shape[b] = 0.0
        fills.discard(stop_bar)
        fills.discard(stop_bar - 1)
    pad_open = 800.0 if opinion else 900.0
    if origin > 0.05:
        place(pads, pad(prog[0], origin + 0.4, amp=0.7, attack_s=min(1.6, origin), open_hz=pad_open, rng=v.rng), 0.0)

    def chord_at(b: int) -> str:
        return prog[(b // OPINION_BARS_PER_CHORD if opinion else b) % len(prog)]

    breaths = tuple(t for t in accents if stop_at is None or t < stop_at - 0.5)
    rest_spans = tuple((t - BREATH_REST[0], t + BREATH_REST[1]) for t in breaths)
    for b in range(bars):
        if stop_bar is not None and b >= stop_bar:
            break
        chord = chord_at(b)
        at = origin + b * BAR
        pos = b % 8
        pad_amp = 0.8 + 0.2 * (0.5 + 0.5 * math.sin(math.pi * pos / 8))       # the pad swells across the phrase
        # rev 5: the pad opens a little further in each later phrase (movement across the arc)
        open_hz = pad_open + (0.0 if opinion else 100.0 * min(2, b // 8))
        place(pads, pad(chord, BAR + 0.4, amp=pad_amp * (1.12 if opinion else 1.0), attack_s=1.2 if opinion else 1.0,
                        open_hz=open_hz, rng=v.rng), at)
        if b > 0 or bars <= 3:
            if opinion:
                _bassline(low, chord, at, amp=0.82 * max(0.6, d_shape[b] or 0.6), style="walk")
            else:
                _bassline(low, chord, at, amp=(0.82 if segment != "desk" else 0.95) * max(0.6, d_shape[b] or 0.6),
                          style="pulse" if segment == "desk" else "half")
        if opinion:
            if k_shape[b] > 0 and (pos in (0, 1, 2, 4, 5) or v.rng.random() < 0.4):
                beats = (0.0, 2.0) if v.rng.random() < 0.7 else (1.0, 3.0)
                _bell_line(keys, chord, at, amp=0.5 * k_shape[b], rng=v.rng, beats=beats)
            if k_shape[b] > 0 and pos == 6 and chord in ("Bb", "Gm"):
                for note, start, length in HOOK_INVERTED[:3]:
                    place(keys, bell(note, length * BEAT, vel=0.55 * k_shape[b], pan=0.0, rng=v.rng),
                          _human(v.rng, at + start * BEAT, 5.0))
            continue
        if k_shape[b] > 0 and (segment == "desk" or pos in (0, 1, 4, 5) or v.rng.random() < 0.3):
            # rev 5c: the lilt (five notes a bar); a bar in two under the
            # conversations rests the "and" of three as well (four notes)
            rests = set(OSTINATO_LILT) | ({5} if segment != "desk" and v.rng.random() < 0.5 else set())
            _ostinato(keys, chord, at, amp=0.3 if segment != "desk" else 0.36, rests=rests, rng=v.rng, shape=k_shape[b],
                      skip=rest_spans)
        if k_shape[b] > 0 and pos == 6 and chord in ("Dm", "Bb"):
            _hook(keys, at, amp=0.58 * k_shape[b], rng=v.rng)
        if k_shape[b] > 0 and segment in ("lead", "second", "close") and b >= 8 and pos in (2, 3):
            # a bell answers the ostinato from the second phrase on: fuller, and the arc moves
            _bell_line(keys, chord, at, amp=0.22 * k_shape[b], rng=v.rng, beats=(1.0,))
    for t_acc in breaths:
        # the breath: the ostinato has rested (rest_spans), the bell answers
        b = int((t_acc - origin) // BAR) if t_acc >= origin else 0
        _bell_tag(keys, chord_at(max(0, b)), t_acc, amp=0.6)
    drop = {b for b in range(bars) if b % 8 == 3 and b > 2 and v.rng.random() < 0.5}
    _drums(drums, kicks, origin, bars, pattern, kick_amp=0.9 if not opinion else 0.8,
           clock_amp=0.32 if segment != "desk" else 0.34, rng=v.rng, drop_bars=drop, fill_bars=fills, shape=d_shape)
    if stop_at is not None:
        # the hit: the downbeat the desk closes on, then the ring and nothing else
        chord = chord_at(stop_bar or 0)
        place(drums, impact(amp=1.0), stop_at)
        kicks.append(stop_at)
        place(low, bass(CHORDS[chord]["bass"], 1.4, amp=1.0), stop_at)
        place(pads, pad(chord, 0.5, amp=0.9, attack_s=0.03, release_s=1.3, rng=v.rng), stop_at)
        # cut every tail that would ring past the hit (delays, releases)
        cut = int(stop_at * SR)
        gate = np.ones(n)
        edge = int(0.012 * SR)
        gate[cut:] = 0.0
        gate[cut - edge:cut] = np.linspace(1, 0, edge)
        keys *= gate[:, None]
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=2.0)
    mix = reverb(keys, wet=0.34 if not opinion else 0.42, decay_s=2.4 if not opinion else 3.0, seed=v.seed + 3) \
        + reverb(pads, wet=0.45, decay_s=3.0 if not opinion else 3.6, seed=v.seed + 4) + low + drums
    return mix[: int(dur_s * SR)]


def interlude_plan(v: Voicing, index: int) -> tuple[list, tuple[str, str], str]:
    """What the `index`-th interlude of the day plays: (melody, chord pair,
    voice). The day's seed picks the first; each later interlude takes the
    next fragment, the next pair and the other voice, so two interludes in one
    episode never share any of the three."""
    k = (v.seed % len(INTERLUDE_FRAGMENTS) + index) % len(INTERLUDE_FRAGMENTS)
    melody, pairs = INTERLUDE_FRAGMENTS[k]
    pair = pairs[((v.seed // 7) + index) % len(pairs)]
    voice = "ep" if (v.seed // 13 + index) % 2 == 0 else "bell"
    return melody, pair, voice


def render_interlude(v: Voicing, index: int = 0, dur_s: float = INTERLUDE_S) -> np.ndarray:
    """The interlude (rev 5c), three bars, bar by bar:

        1  the groove is there from the downbeat: a soft kick on one and the "and"
           of two, a brush on two and four, a shaker on the "and" of two and of four;
           the bass on the
           root and the fifth; a warm pad (filter to 800 Hz) swelling in over the
           first beat; and the melody's first bar on the day's voice
        2  the chord pair's second chord; the melody's second bar
        3  the release: the bass and a single kick land on the tonic, the pad opens
           on Dm and holds, the shaker and the brush are gone, the melody's last
           note rings into the delay. The next anchor speaks over this bar
           (INTERLUDE_VOICE_S), once the landing has been heard.

    A breath, not a jingle: no riser, no impact, no ostinato, nothing bright.
    `interlude_plan` makes two interludes in one episode differ."""
    melody, pair, voice = interlude_plan(v, index)
    n = int((dur_s + 3.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    kicks: list[float] = []
    chords = [pair[0], pair[1], INTERLUDE_RELEASE]
    for b, chord in enumerate(chords):
        at = b * BAR
        last = b == 2
        place(pads, pad(chord, (BAR + 1.6) if last else (BAR + 0.3), amp=0.9 if last else 0.8,
                        attack_s=0.35 if b == 0 else 0.6, release_s=3.0 if last else 2.0, open_hz=800.0, rng=v.rng), at)
        if last:
            place(low, bass(CHORDS[chord]["bass"], 2.4 * BEAT, amp=0.9), at)
        else:
            _bassline(low, chord, at, amp=0.85, style="groove")
    _drums(drums, kicks, 0.0, 2, "groove", kick_amp=0.85, clock_amp=0.34, rng=v.rng)
    place(drums, kick(amp=0.85), 2 * BAR)
    kicks.append(2 * BAR)
    _melody(keys, melody, 0.0, amp=0.72 if voice == "ep" else 0.8, voice=voice, rng=v.rng, pan_spread=0.2)
    # the landing: the tonic's low octave under the melody's last note
    place(keys, (bell if voice == "bell" else ep)("D4", 2.2, vel=0.42, pan=0.0, rng=v.rng), 2 * BAR)
    keys = tempo_delay(keys, feedback=0.3, mix=0.2)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=2.0)
    mix = reverb(keys, wet=0.36, decay_s=2.6, seed=v.seed + 5 + index) \
        + reverb(pads, wet=0.45, decay_s=3.0, seed=v.seed + 11 + index) + low + drums
    return mix[: int(dur_s * SR)]


def render_entrance(v: Voicing, dur_s: float = ENTRANCE_S) -> np.ndarray:
    """"Void Opinion", four bars, no pulse (rev 5). Bar by bar:

        1  out of the held silence a sub pedal on Bb (VI) swells in over 1.5 s
           with a warm Bb pad under it; nothing else: the ground returns alone
        2  the hook begins on the bell, in dotted augmentation (D5 . . C5 A4 . F4 .),
           over VI: the tonic as the third of the chord, a new colour
        3  the pedal moves to G (iv), the hook continues (G4 . . F4 D4 ...)
        4  the pedal moves to A (V), a sus pad over it, and the hook's last note,
           the tonic D, is HELD over the dominant: unresolved. The anchor speaks
           over this bar (ENTRANCE_VOICE_S), and the Opinion's bed enters under
           the voice on VI, a deceptive resolution: not where the news goes.

    What it is not: no kick, no shaker, no riser, no impact, no ostinato, the
    hook not at tempo. Those are the news. The same seven notes say it is the
    same show."""
    n = int((dur_s + 3.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    prev = None
    for b, chord in enumerate(ENTRANCE_HARMONY):
        at = b * BAR
        if chord != prev:
            span = BAR * sum(1 for c in ENTRANCE_HARMONY[b:] if c == chord)
            place(low, sub_pedal(CHORDS[chord]["bass"], span + 0.1, amp=1.0 if b == 0 else 0.9,
                                 attack_s=1.5 if b == 0 else 0.35, release_s=1.6), at)
            place(pads, pad(chord, span + 0.3, amp=0.95 if b else 0.8, attack_s=2.0 if b == 0 else 0.9, release_s=2.6,
                            open_hz=800.0, rng=v.rng), at)
        prev = chord
    for i, (note, start, length) in enumerate(HOOK_AUGMENTED):
        vel = 0.9 if i in (0, 4, 6) else 0.78
        place(keys, bell(note, length * BEAT * 0.98, vel=vel, pan=(-0.2, 0.2)[i % 2] * 0.6, rng=v.rng),
              _human(v.rng, BAR + start * BEAT, 4.0))
    keys = tempo_delay(keys, beats=1.5, feedback=0.28, mix=0.16)
    mix = reverb(keys, wet=0.42, decay_s=3.2, seed=v.seed + 6) + reverb(pads, wet=0.5, decay_s=3.4, seed=v.seed + 7) + low
    return mix[: int(dur_s * SR)]


def render_outro(v: Voicing, dur_s: float = 15.0) -> np.ndarray:
    """The cycle in full, the hook on top, a soft riser into the last downbeat,
    and the landing on D major: the lift. Then the pad falls to silence."""
    n = int((dur_s + 3.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    fx = np.zeros((n, 2))
    kicks: list[float] = []
    prog = ["Dm", "Bb", "F", "C"]
    for b, chord in enumerate(prog):
        at = b * BAR
        place(pads, pad(chord, BAR + 0.4, amp=1.0, attack_s=0.6, rng=v.rng), at)
        _bassline(low, chord, at, amp=0.8, style="half" if b < 3 else "eighths")
        _ostinato(keys, chord, at, amp=0.36, rests=OSTINATO_LILT if b < 2 else frozenset(), rng=v.rng)
    _drums(drums, kicks, 0.0, 4, "half", kick_amp=0.9, clock_amp=0.34, rng=v.rng)
    _hook(keys, 0.0, amp=0.86, rng=v.rng)
    _hook(keys, 2 * BAR, amp=0.9, rng=v.rng)
    # rev 5: the bell doubles the second statement an octave up, so the outro
    # carries the Opinion's register home with the news's
    for i, (note, start, length) in enumerate(HOOK):
        up = note[:-1] + str(int(note[-1]) + 1)
        place(keys, bell(up, length * BEAT * 0.9, vel=0.3 if i not in (0, 6) else 0.36, pan=0.25 if i % 2 else -0.25,
                         rng=v.rng), _human(v.rng, 2 * BAR + start * BEAT, 5.0))
    land = 4 * BAR
    place(fx, riser(1.5, amp=0.3, rng=v.rng), land - 1.5)
    place(drums, impact(amp=1.0), land)
    kicks.append(land)
    place(pads, pad("D", dur_s - land + 1.0, amp=1.0, attack_s=0.05, release_s=4.0, rng=v.rng), land)
    for note, pan_ in (("D4", -0.1), ("F#4", 0.1), ("A4", 0.0), ("D5", 0.0)):
        place(keys, ep(note, 4.0, vel=0.75, pan=pan_, rng=v.rng), land)
    place(keys, bell("D6", 3.0, vel=0.32, pan=0.0, rng=v.rng), land)
    place(low, bass("D2", 2.5, amp=0.9), land)
    place(low, sub_pedal("D2", dur_s - land - 1.0, amp=0.5, attack_s=0.6, release_s=2.5), land + 1.5)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=2.0)
    mix = reverb(keys, wet=0.32, decay_s=2.2, seed=v.seed + 8) + reverb(pads, wet=0.44, decay_s=3.2, seed=v.seed + 9) + low + drums + fx
    mix = mix[: int(dur_s * SR)]
    tail = int(3.0 * SR)
    mix[-tail:] *= (np.cos(np.linspace(0, math.pi / 2, tail)) ** 2)[:, None]
    return mix
