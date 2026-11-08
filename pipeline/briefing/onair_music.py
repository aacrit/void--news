"""On Air: the music, composed. Rev 3 (2026-11-07, CEO: "designed surgically,
from scratch; I don't like the tunes"). Rev 5 (2026-11-08): the Opinion is
read by the same voice as the news, so the firewall between them is the
MUSIC: the desk bed stops, a silence is held, and "Void Opinion" enters on a
cue with its own identity; the Opinion's bed is the same show in a warmer
room; and the whole score carries more bass where a speaker can feel it.

A score for a daily news conversation, in Void's voice: D minor, 84 beats a
minute, a four-chord cycle (i VI III VII, the cinematic cadence), a two-bar
hook on electric piano that falls to the tonic, an eighth-note ostinato, a
pulse bass on the sub, a kick with a click so a phone hears it, ticks on
the off-beats, a pad that breathes, a riser into every downbeat that
matters, and a final chord that lifts to the major. Stereo. Every sound is
synthesised here from a patch; nothing is sampled, nothing is looped.

Patches (the instruments):
    ep         two-operator FM electric piano (DX-style tine), lowpassed, with a tempo delay
    bell       two-operator FM glass (a 3.5:1 modulator), long release: the Opinion's register
    pad        six detuned saws, three a side, 24 dB/oct lowpass that opens over the attack
    bass       sub sine, its octave (so a small speaker hears the note), a plucked saw
    kick       a 150 to 42 Hz sine sweep with a 4 ms click
    tick/hat   shaped noise, 2.5 to 5 kHz, the clock
    riser      filtered noise rising into a downbeat
    impact     kick, sub and a low thump together, on the downbeat a riser lands on

Form (the cues), each composed to the length the producer asks for:
    theme      four bars: pulse and ostinato, pad enters, the hook, a riser into the
               downbeat the sign-on lands on
    bed        eight-bar phrases, layers entering and leaving by the day's seed, the
               hook once a phrase; half-time under the conversations, four on the
               floor on the desk; the Opinion's bed is the slow room (below)
    pageturn   a riser, the downbeat, the hook's first three notes
    entrance   "Void Opinion": out of a held silence a sub pedal on VI, then the hook
               in dotted augmentation on the bell, reharmonised VI iv V and left on
               the dominant with the tonic hanging over it; no pulse, no riser
    outro      the cycle in full, the bell doubling the hook, landing on D major

The Opinion's bed (`segment == "opinion"`): the harmonic rhythm halves (two
bars a chord) and the cycle starts on VI, not i; one soft kick a bar and no
ticks; the bass walks root and fifth in half notes instead of eighths; a
sparse bell line, one note in two beats, in place of the ostinato; the pad
warmer (its filter opens to 800 Hz, not 1100) and slower. Measurably: fewer
onsets a second than any news bed and a chroma profile further from theirs.

The stop (`ending == "stop"`): the desk bed does not rise into the entrance.
Its last downbeat is a hit (impact, a long bass root, the pad released) at
`STOP_RING_S` before its end; everything else is gone from that beat, the
ring decays, and the producer holds the studio floor before the entrance.

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


# Chords as (bass root, the fifth the Opinion's bass walks to, keys voicing in
# the fourth/fifth octave, ostinato eighths, the bell's two notes). The fifth
# is placed in the sub where the band shape keeps it (40 to 90 Hz).
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
    note (the bark of a tine), a 14:1 modulator for the 30 ms attack, 3 kHz
    lowpass, a 1.4 s release."""
    f = hz(note)
    n = int((length_s + 1.6) * SR)
    t = _t(n)
    idx = (1.2 + 2.6 * vel) * np.exp(-t / 0.35) + 0.25
    attack_idx = 0.9 * vel * np.exp(-t / 0.03)
    mod = idx * np.sin(2 * math.pi * f * t) + attack_idx * np.sin(2 * math.pi * f * 14 * t)
    x = np.sin(2 * math.pi * f * t + mod)
    x *= _env(n, 0.003, 0.9, 0.35, 1.4, length_s)
    x = _lp(x, 3000.0, 2)
    return stereo(x * vel, pan)


def bell(note: str, length_s: float, *, vel: float = 0.8, pan: float = 0.0, rng=None) -> np.ndarray:
    """Glass: a carrier with a 3.5:1 modulator whose index falls over 0.8 s
    (the inharmonic partials of a struck bar), a second carrier 4 cents off
    for shimmer, a 3 kHz lowpass, a 2.6 s release. The Opinion's register:
    nothing in the news is struck like this."""
    f = hz(note)
    n = int((length_s + 2.8) * SR)
    t = _t(n)
    idx = (0.9 + 1.4 * vel) * np.exp(-t / 0.8) + 0.08
    mod = idx * np.sin(2 * math.pi * f * 3.5 * t)
    x = np.sin(2 * math.pi * f * t + mod) + 0.5 * np.sin(2 * math.pi * f * 2 ** (4 / 1200) * t + 0.7 * mod)
    x *= _env(n, 0.004, 1.6, 0.3, 2.6, length_s)
    x = _lp(x, 3000.0, 2)
    return stereo(x * vel * 0.55, pan)


def pad(chord: str, length_s: float, *, amp: float = 1.0, attack_s: float = 1.6, release_s: float = 2.4,
        open_hz: float = 1100.0, rng=None) -> np.ndarray:
    """Six detuned saws from the voicing, three a side, a 24 dB/oct lowpass
    that opens from 400 to `open_hz` (1100 under the news, 800 under the
    Opinion: warmer) over the attack, slow breathing."""
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
    breath = 1.0 - 0.18 * 0.5 * (1 + np.sin(2 * math.pi * 0.08 * t + rng.uniform(0, 6.28)))
    env = _env(n, attack_s, 0.1, 1.0, release_s, length_s) * breath
    return x * env[:, None] * amp * 0.22


def bass(note: str, length_s: float = 0.45, *, amp: float = 1.0) -> np.ndarray:
    """Sub sine, its octave at -9 dB (rev 5: the note's body in 100 to 175
    Hz, which is what a small speaker hears of it; the band shape's low-pass
    moved to 130 Hz to keep it), under a plucked saw whose cutoff falls 320
    to 110 Hz over 140 ms."""
    f = hz(note)
    n = int((length_s + 0.35) * SR)
    t = _t(n)
    sub = np.sin(2 * math.pi * f * t) * _env(n, 0.004, 0.3, 0.55, 0.24, length_s)
    octave = np.sin(2 * math.pi * 2 * f * t) * _env(n, 0.004, 0.22, 0.4, 0.18, length_s)
    saw = signal.sawtooth(2 * math.pi * f * t) * _env(n, 0.002, 0.14, 0.2, 0.15, length_s)
    saw = _sweep_lp(saw[:, None], 320.0, 110.0, 0.14)[:, 0]
    x = 0.8 * sub + 0.28 * octave + 0.5 * saw
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
    n = int(0.6 * SR)
    t = _t(n)
    f = 42.0 + 108.0 * np.exp(-t / 0.04)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.minimum(1.0, t / 0.003) * np.exp(-t / 0.26)
    click = np.random.default_rng(5).normal(0, 1, n) * np.exp(-t / 0.004)
    click = _hp(click, 2000.0, 2) * 0.25
    x = body + click
    return stereo(_norm(x, 1.0) * amp, 0.0)


def tick(*, amp: float = 1.0, open_: bool = False, pan: float = 0.25, rng=None) -> np.ndarray:
    """The clock: shaped noise in 2.5 to 5 kHz, 25 ms closed or 90 ms open."""
    rng = rng or np.random.default_rng(7)
    n = int(0.14 * SR)
    t = _t(n)
    x = rng.normal(0, 1, n) * np.minimum(1.0, t / 0.002) * np.exp(-t / (0.06 if open_ else 0.02))
    x = _bp(x[:, None], 2500.0, 5000.0)[:, 0]
    return stereo(_norm(x, 1.0) * amp, pan)


def rim(*, amp: float = 1.0, pan: float = -0.2) -> np.ndarray:
    n = int(0.08 * SR)
    t = _t(n)
    x = np.sin(2 * math.pi * 760.0 * t) * np.exp(-t / 0.012) + 0.4 * np.random.default_rng(9).normal(0, 1, n) * np.exp(-t / 0.006)
    x = _bp(x[:, None], 500.0, 4500.0)[:, 0]
    return stereo(_norm(x, 1.0) * amp, pan)


def riser(length_s: float = 1.5, *, amp: float = 1.0, rng=None) -> np.ndarray:
    """Noise rising into a downbeat: level up, a bandpass sweeping 300 to 3.5 kHz."""
    rng = rng or np.random.default_rng(11)
    n = int(length_s * SR)
    t = _t(n)
    x = rng.normal(0, 1, n) * (t / length_s) ** 2.2
    blk = int(0.02 * SR)
    out = np.zeros(n)
    for i in range(0, n, blk):
        frac = i / n
        lo = 300.0 * (1 + 6 * frac)
        sos = signal.butter(2, [lo, min(lo * 2.2, 4800.0)], btype="band", fs=SR, output="sos")
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


def reverb(x: np.ndarray, *, wet: float = 0.3, decay_s: float = 1.8, lp_hz: float = 3200.0, seed: int = 21) -> np.ndarray:
    """A stereo room: two decorrelated tails, one a side."""
    if wet <= 0:
        return x
    irl, irr = _ir(decay_s, seed, lp_hz), _ir(decay_s, seed + 1, lp_hz)
    wl = signal.fftconvolve(x[:, 0], irl)[: len(x)]
    wr = signal.fftconvolve(x[:, 1], irr)[: len(x)]
    w = np.stack([wl, wr], axis=1)
    w = w / (np.max(np.abs(w)) + 1e-9) * (np.max(np.abs(x)) + 1e-9)
    return (1 - wet) * x + wet * w


def sidechain(x: np.ndarray, kick_times: list[float], *, depth_db: float = 5.0, recover_s: float = 0.22) -> np.ndarray:
    """The pump: a dip on every kick, recovering over `recover_s`."""
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


SWING = 0.56          # off-beat eighths land at 56 % of the beat, not 50: a human pulse
HUMAN_MS = 7.0        # timing jitter, one sigma


def _human(rng, at: float, ms: float = HUMAN_MS) -> float:
    return at + float(rng.normal(0, ms / 1000.0)) if rng is not None else at


def _ostinato(canvas, chord: str, bar_at: float, *, amp: float, rests: set[int] = frozenset(), rng=None,
              shape: float = 1.0):
    """`shape` scales the phrase's dynamics: under 1 the line sits back, over 1
    it leans in; the first note of a bar is always a little louder and the
    off-beats swing."""
    for k, note in enumerate(CHORDS[chord]["ost"]):
        if k in rests:
            continue
        beat_pos = k // 2 + (SWING if k % 2 else 0.0)
        at = _human(rng, bar_at + beat_pos * BEAT)
        vel = amp * shape * (1.0 if k % 2 == 0 else 0.68) * (1.14 if k == 0 else 1.0)
        if rng is not None:
            vel *= float(rng.uniform(0.86, 1.1))
        place(canvas, ep(note, 0.3, vel=vel, pan=(-0.18 if k % 2 == 0 else 0.18), rng=rng), at)


def _hook(canvas, bar_at: float, *, amp: float, inverted: bool = False, rng=None):
    for i, (note, start, length) in enumerate(HOOK_INVERTED if inverted else HOOK):
        vel = amp * (1.0 if i in (0, 4) else 0.86) * (float(rng.uniform(0.92, 1.06)) if rng is not None else 1.0)
        place(canvas, ep(note, length * BEAT * 0.95, vel=vel, pan=0.0, rng=rng), _human(rng, bar_at + start * BEAT, 5.0))


def _fill(canvas, bar_at: float, *, amp: float, rng=None):
    """A tick roll over the last beat into the next downbeat."""
    for k in range(4):
        at = _human(rng, bar_at + 3 * BEAT + k * 0.25 * BEAT, 4.0)
        place(canvas, tick(amp=amp * (0.5 + 0.15 * k), open_=(k == 3), rng=rng), at)
    place(canvas, rim(amp=amp * 0.7), _human(rng, bar_at + 3.5 * BEAT, 4.0))


def _drums(canvas, kicks: list[float], start: float, bars: int, pattern: str, *, kick_amp: float, tick_amp: float,
           rng=None, drop_bars: set[int] = frozenset(), fill_bars: set[int] = frozenset(),
           shape: "list[float] | None" = None):
    """`shape[b]` scales bar b's level (0 silences it): the arc of the bed."""
    for b in range(bars):
        bar_at = start + b * BAR
        dropped = b in drop_bars
        sc = shape[b] if shape is not None and b < len(shape) else 1.0
        if sc <= 0.0:
            continue
        k_amp, t_amp = kick_amp * sc, tick_amp * sc
        if b in fill_bars:
            _fill(canvas, bar_at, amp=t_amp, rng=rng)
        for beat in range(4):
            at = bar_at + beat * BEAT
            if pattern == "half":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=k_amp * (1.0 if beat == 0 else 0.85)), at)
                    kicks.append(at)
                if beat in (1, 3):
                    place(canvas, rim(amp=t_amp * 0.6), _human(rng, at, 4.0))
                place(canvas, tick(amp=t_amp * 0.55, rng=rng), _human(rng, at + SWING * BEAT, 4.0))
                continue
            if pattern == "four":
                if not dropped:
                    place(canvas, kick(amp=k_amp * (1.0 if beat == 0 else 0.8)), at)
                    kicks.append(at)
                place(canvas, tick(amp=t_amp * (1.0 if beat % 2 else 0.7), open_=(beat == 3), rng=rng),
                      _human(rng, at + SWING * BEAT, 4.0))
                if beat in (1, 3):
                    place(canvas, rim(amp=t_amp * 0.8), _human(rng, at, 4.0))
                continue
            if pattern == "dotted":
                if beat == 0 and not dropped:
                    place(canvas, kick(amp=k_amp), at)
                    kicks.append(at)
                if beat == 1:
                    place(canvas, kick(amp=k_amp * 0.75), at + 0.5 * BEAT)
                    kicks.append(at + 0.5 * BEAT)
                if beat == 3:
                    place(canvas, tick(amp=t_amp, rng=rng), _human(rng, at, 4.0))
                continue
            if pattern == "pulse":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=k_amp * 0.9), at)
                    kicks.append(at)
                continue
            if pattern == "slow":
                # the Opinion's room: one soft kick on the downbeat, a closed
                # tick on three at a whisper; no rims, no off-beats
                if beat == 0 and not dropped:
                    place(canvas, kick(amp=k_amp * 0.8), at)
                    kicks.append(at)
                if beat == 2:
                    place(canvas, tick(amp=t_amp * 0.35, rng=rng), _human(rng, at, 4.0))
    return


def _bassline(canvas, chord: str, bar_at: float, *, amp: float, eighths: bool = True, full: bool = False,
              walk: bool = False):
    """Eighths on the root (the news), half notes on the root (`eighths=False`),
    or the Opinion's walk: the root held a dotted half, the fifth on four."""
    root = CHORDS[chord]["bass"]
    if walk:
        place(canvas, bass(root, 2.0 * BEAT, amp=amp), bar_at)
        place(canvas, bass(CHORDS[chord]["fifth"], 0.9 * BEAT, amp=amp * 0.8), bar_at + 3.0 * BEAT)
        return
    steps = range(8) if eighths else (0, 4)
    for k in steps:
        if eighths and not full and k in (3, 7):
            continue
        place(canvas, bass(root, 0.42 if eighths else 1.2, amp=amp * (1.0 if k % 2 == 0 else 0.7)), bar_at + k * 0.5 * BEAT)


def _bell_line(canvas, chord: str, bar_at: float, *, amp: float, rng=None, beats: tuple[float, ...] = (0.0, 2.0)):
    """One bell note in two beats from the chord's two bell tones, alternating,
    panned apart: the Opinion's line in place of the ostinato."""
    notes = CHORDS[chord]["bell"]
    for i, b in enumerate(beats):
        vel = amp * (1.0 if i == 0 else 0.8) * (float(rng.uniform(0.9, 1.08)) if rng is not None else 1.0)
        place(canvas, bell(notes[i % len(notes)], 1.6 * BEAT, vel=vel, pan=(-0.3 if i % 2 == 0 else 0.3), rng=rng),
              _human(rng, bar_at + b * BEAT, 6.0))


def render_theme(v: Voicing, dur_s: float = 11.6) -> np.ndarray:
    """Four bars in: pulse and ostinato; the pad; the hook; a riser into the
    downbeat the sign-on lands on, then the pad holds under the voice."""
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
        _bassline(low, chord, at, amp=0.8, eighths=True, full=True)
        _ostinato(keys, chord, at, amp=0.42 if b < 2 else 0.5, rng=v.rng)
        # the pad is the floor from the first bar (quiet), and opens from bar two
        place(pads, pad(chord, BAR + 0.3, amp=(0.45, 0.9, 0.95, 1.0)[b], attack_s=(1.6, 1.0, 0.4, 0.4)[b], rng=v.rng), at)
    _drums(drums, kicks, 0.0, 4, "half", kick_amp=0.95, tick_amp=0.5, rng=v.rng)
    _hook(keys, 2 * BAR, amp=0.95, rng=v.rng)
    place(fx, riser(1.5, amp=0.55, rng=v.rng), 4 * BAR - 1.5)
    place(drums, impact(amp=1.0), 4 * BAR)
    kicks.append(4 * BAR)
    place(pads, pad("Dm", dur_s - 4 * BAR + 1.0, amp=1.0, attack_s=0.05, release_s=3.5, rng=v.rng), 4 * BAR)
    place(keys, ep("D4", 2.5, vel=0.7, pan=0.0), 4 * BAR)
    place(keys, ep("A4", 2.5, vel=0.55, pan=0.1), 4 * BAR)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=3.0)
    mix = reverb(keys, wet=0.28, seed=v.seed) + reverb(pads, wet=0.4, decay_s=2.6, seed=v.seed + 2) + low + drums + fx
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
            if rng.random() < 0.6:
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


def render_bed(v: Voicing, segment: str, dur_s: float, *, ending: str = "out") -> np.ndarray:
    """A bed with an arc (`_arc`): pad and bass enter alone, the pulse arrives,
    the ostinato and the hook come and go by the day's seed, a dip and a fill
    before each eight-bar phrase, and an ending that thins out ("out"),
    gathers into the transition ("rise") or STOPS on a hit ("stop", the desk
    before the Opinion). Composed to length; never looped; a bar in eight
    dropped. The Opinion's bed is the slow room described in the module
    docstring: two bars a chord, one kick a bar, a walking bass, bells."""
    opinion = segment == "opinion"
    pattern = {"lead": "half", "second": "half", "desk": "four", "opinion": "slow", "close": "half"}[segment]
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
    n = int((origin + bars * BAR + 3.0) * SR)
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
    if origin > 0.05:
        place(pads, pad(prog[0], origin + 0.4, amp=0.7, attack_s=min(1.6, origin), open_hz=800.0 if opinion else 1100.0,
                        rng=v.rng), 0.0)
    for b in range(bars):
        if stop_bar is not None and b >= stop_bar:
            break
        chord = prog[(b // OPINION_BARS_PER_CHORD if opinion else b) % len(prog)]
        at = origin + b * BAR
        pos = b % 8
        pad_amp = 0.8 + 0.2 * (0.5 + 0.5 * math.sin(math.pi * pos / 8))       # the pad swells across the phrase
        # rev 5: the pad opens a little further in each later phrase (movement across the arc)
        open_hz = (800.0 if opinion else 1100.0) + (0.0 if opinion else 120.0 * min(2, b // 8))
        place(pads, pad(chord, BAR + 0.4, amp=pad_amp * (1.12 if opinion else 1.0), attack_s=1.1 if opinion else 0.6,
                        open_hz=open_hz, rng=v.rng), at)
        if b > 0 or bars <= 3:
            if opinion:
                _bassline(low, chord, at, amp=0.82 * max(0.6, d_shape[b] or 0.6), walk=True)
            else:
                eighths = segment == "desk" or (pos % 2 == 0 and d_shape[b] > 0.6)
                _bassline(low, chord, at, amp=(0.82 if segment != "desk" else 0.95) * max(0.6, d_shape[b] or 0.6),
                          eighths=eighths)
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
            rests = {3, 7} if segment != "desk" and v.rng.random() < 0.5 else set()
            _ostinato(keys, chord, at, amp=0.34 if segment != "desk" else 0.4, rests=rests, rng=v.rng, shape=k_shape[b])
        if k_shape[b] > 0 and pos == 6 and chord in ("Dm", "Bb"):
            _hook(keys, at, amp=0.62 * k_shape[b], rng=v.rng)
        if k_shape[b] > 0 and segment in ("lead", "second", "close") and b >= 8 and pos in (2, 3):
            # a bell answers the ostinato from the second phrase on: fuller, and the arc moves
            _bell_line(keys, chord, at, amp=0.22 * k_shape[b], rng=v.rng, beats=(1.0,))
    drop = {b for b in range(bars) if b % 8 == 3 and b > 2 and v.rng.random() < 0.5}
    _drums(drums, kicks, origin, bars, pattern, kick_amp=0.9 if not opinion else 0.8,
           tick_amp=0.42 if segment != "desk" else 0.5, rng=v.rng, drop_bars=drop, fill_bars=fills, shape=d_shape)
    if stop_at is not None:
        # the hit: the downbeat the desk closes on, then the ring and nothing else
        chord = prog[((stop_bar or 0) // OPINION_BARS_PER_CHORD if opinion else (stop_bar or 0)) % len(prog)]
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
    low = sidechain(low, kicks, depth_db=3.0)
    mix = reverb(keys, wet=0.3 if not opinion else 0.4, decay_s=1.8 if not opinion else 2.6, seed=v.seed + 3) \
        + reverb(pads, wet=0.42, decay_s=2.4 if not opinion else 3.0, seed=v.seed + 4) + low + drums
    return mix[: int(dur_s * SR)]


def render_pageturn(v: Voicing, dur_s: float = 3.6) -> np.ndarray:
    """A riser into one downbeat, then the hook's first three notes."""
    n = int((dur_s + 1.5) * SR)
    keys = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    fx = np.zeros((n, 2))
    place(fx, riser(0.9, amp=0.5, rng=v.rng), 0.0)
    place(drums, impact(amp=0.95), 0.9)
    for note, start, length in HOOK[:3]:
        place(keys, ep(note, length * BEAT * 0.9, vel=0.8, pan=0.0, rng=v.rng), 0.9 + start * BEAT)
    place(keys, ep("D4", 1.6, vel=0.5, pan=0.0, rng=v.rng), 0.9)
    keys = tempo_delay(keys)
    mix = reverb(keys, wet=0.32, seed=v.seed + 5) + drums + fx
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

    What it is not: no kick, no tick, no riser, no impact, no ostinato, the
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
    """The cycle in full, the hook on top, a riser into the last downbeat, and
    the landing on D major: the lift. Then the pad falls to silence."""
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
        place(pads, pad(chord, BAR + 0.4, amp=1.0, attack_s=0.5, rng=v.rng), at)
        _bassline(low, chord, at, amp=0.8, eighths=True)
        _ostinato(keys, chord, at, amp=0.42, rng=v.rng)
    _drums(drums, kicks, 0.0, 4, "half", kick_amp=0.95, tick_amp=0.5, rng=v.rng)
    _hook(keys, 0.0, amp=0.9, rng=v.rng)
    _hook(keys, 2 * BAR, amp=0.95, rng=v.rng)
    # rev 5: the bell doubles the second statement an octave up, so the outro
    # carries the Opinion's register home with the news's
    for i, (note, start, length) in enumerate(HOOK):
        up = note[:-1] + str(int(note[-1]) + 1)
        place(keys, bell(up, length * BEAT * 0.9, vel=0.3 if i not in (0, 6) else 0.36, pan=0.25 if i % 2 else -0.25,
                         rng=v.rng), _human(v.rng, 2 * BAR + start * BEAT, 5.0))
    land = 4 * BAR
    place(fx, riser(1.5, amp=0.55, rng=v.rng), land - 1.5)
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
    low = sidechain(low, kicks, depth_db=3.0)
    mix = reverb(keys, wet=0.3, seed=v.seed + 8) + reverb(pads, wet=0.42, decay_s=3.0, seed=v.seed + 9) + low + drums + fx
    mix = mix[: int(dur_s * SR)]
    tail = int(3.0 * SR)
    mix[-tail:] *= (np.cos(np.linspace(0, math.pi / 2, tail)) ** 2)[:, None]
    return mix
