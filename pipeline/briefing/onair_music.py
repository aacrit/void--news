"""On Air: the music, composed. Rev 3 (2026-11-07, CEO: "designed surgically,
from scratch; I don't like the tunes").

A score for a daily news conversation, in Void's voice: D minor, 84 beats a
minute, a four-chord cycle (i VI III VII, the cinematic cadence), a two-bar
hook on electric piano that falls to the tonic, an eighth-note ostinato, a
pulse bass on the sub, a kick with a click so a phone hears it, ticks on
the off-beats, a pad that breathes, a riser into every downbeat that
matters, and a final chord that lifts to the major. Stereo. Every sound is
synthesised here from a patch; nothing is sampled, nothing is looped.

Patches (the instruments):
    ep         two-operator FM electric piano (DX-style tine), lowpassed, with a tempo delay
    pad        six detuned saws, three a side, 24 dB/oct lowpass that opens over the attack
    bass       sub sine under a plucked, filtered saw; eighth notes on the chord root
    kick       a 150 to 45 Hz sine sweep with a 4 ms click
    tick/hat   shaped noise, 2.5 to 5 kHz, the clock
    riser      filtered noise rising into a downbeat
    impact     kick, sub and a low thump together, on the downbeat a riser lands on

Form (the cues), each composed to the length the producer asks for:
    theme      four bars: pulse and ostinato, pad enters, the hook, a riser into the
               downbeat the sign-on lands on
    bed        eight-bar phrases, layers entering and leaving by the day's seed, the
               hook once a phrase; half-time under the conversations, four on the
               floor on the desk, a dotted pulse under the Opinion
    pageturn   a riser, the downbeat, the hook's first three notes
    entrance   i to iv, the hook inverted and left on the dominant: a question
    outro      the cycle in full, landing on D major

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


# Chords as (bass note, keys voicing in the fourth/fifth octave, ostinato eighths)
CHORDS = {
    "Dm": {"bass": "D2", "pad": ("D3", "A3", "F4", "A4", "D5"), "ost": ("D4", "A4", "D5", "E5", "A4", "F5", "E5", "A4")},
    "Bb": {"bass": "Bb1", "pad": ("Bb2", "F3", "D4", "F4", "A4"), "ost": ("F4", "Bb4", "D5", "F5", "Bb4", "D5", "C5", "A4")},
    "F":  {"bass": "F2", "pad": ("F3", "C4", "A4", "C5", "E5"), "ost": ("F4", "C5", "E5", "F5", "C5", "A4", "G4", "C5")},
    "C":  {"bass": "C2", "pad": ("C3", "G3", "E4", "G4", "D5"), "ost": ("E4", "G4", "C5", "D5", "G4", "E5", "D5", "G4")},
    "Gm": {"bass": "G1", "pad": ("G2", "D3", "Bb3", "D4", "A4"), "ost": ("D4", "G4", "Bb4", "D5", "G4", "A4", "Bb4", "D5")},
    "A":  {"bass": "A1", "pad": ("A2", "E3", "C#4", "E4", "G4"), "ost": ("E4", "A4", "C#5", "E5", "A4", "G4", "E5", "C#5")},
    "Asus": {"bass": "A1", "pad": ("A2", "E3", "D4", "E4", "A4"), "ost": ("E4", "A4", "D5", "E5", "A4", "D5", "E5", "A4")},
    "D":  {"bass": "D2", "pad": ("D3", "A3", "F#4", "A4", "D5"), "ost": ("D4", "A4", "D5", "F#5", "A4", "D5", "F#5", "A5")},
}
PROGRESSIONS = {
    "lead": [["Dm", "Bb", "F", "C"], ["Dm", "Bb", "Gm", "Asus"], ["Dm", "F", "C", "Gm"]],
    "second": [["Bb", "F", "Dm", "C"], ["Gm", "Dm", "Bb", "C"], ["Dm", "C", "Bb", "F"]],
    "desk": [["Dm", "C", "Dm", "Bb"], ["Dm", "Bb", "Dm", "C"]],
    "opinion": [["Dm", "Gm", "Bb", "Asus"], ["Dm", "Bb", "Gm", "A"]],
    "close": [["Dm", "Bb", "F", "C"]],
}
# The hook: (note, start beat, length beats), two bars, over Dm then Bb.
HOOK = [("D5", 0.0, 1.5), ("C5", 1.5, 0.5), ("A4", 2.0, 1.0), ("F4", 3.0, 1.0),
        ("G4", 4.0, 1.5), ("F4", 5.5, 0.5), ("D4", 6.0, 2.0)]
HOOK_INVERTED = [("A4", 0.0, 1.0), ("C5", 1.0, 1.0), ("D5", 2.0, 2.0), ("F5", 4.0, 1.5), ("E5", 5.5, 2.5)]


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


def pad(chord: str, length_s: float, *, amp: float = 1.0, attack_s: float = 1.6, release_s: float = 2.4,
        rng=None) -> np.ndarray:
    """Six detuned saws from the voicing, three a side, a 24 dB/oct lowpass
    that opens from 400 to 1100 Hz over the attack, slow breathing."""
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
    x = _sweep_lp(x, 400.0, 1100.0, attack_s)
    breath = 1.0 - 0.18 * 0.5 * (1 + np.sin(2 * math.pi * 0.08 * t + rng.uniform(0, 6.28)))
    env = _env(n, attack_s, 0.1, 1.0, release_s, length_s) * breath
    return x * env[:, None] * amp * 0.22


def bass(note: str, length_s: float = 0.45, *, amp: float = 1.0) -> np.ndarray:
    """Sub sine under a plucked saw: cutoff falls 320 to 110 Hz over 140 ms."""
    f = hz(note)
    n = int((length_s + 0.3) * SR)
    t = _t(n)
    sub = np.sin(2 * math.pi * f * t) * _env(n, 0.004, 0.3, 0.5, 0.2, length_s)
    saw = signal.sawtooth(2 * math.pi * f * t) * _env(n, 0.002, 0.14, 0.2, 0.15, length_s)
    saw = _sweep_lp(saw[:, None], 320.0, 110.0, 0.14)[:, 0]
    x = 0.8 * sub + 0.5 * saw
    return stereo(x * amp, 0.0)


def kick(*, amp: float = 1.0) -> np.ndarray:
    n = int(0.55 * SR)
    t = _t(n)
    f = 45.0 + 105.0 * np.exp(-t / 0.04)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.minimum(1.0, t / 0.003) * np.exp(-t / 0.22)
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


def _ostinato(canvas, chord: str, bar_at: float, *, amp: float, rests: set[int] = frozenset(), rng=None):
    for k, note in enumerate(CHORDS[chord]["ost"]):
        if k in rests:
            continue
        at = bar_at + k * 0.5 * BEAT
        vel = amp * (1.0 if k % 2 == 0 else 0.72) * (1.12 if k == 0 else 1.0)
        place(canvas, ep(note, 0.3, vel=vel, pan=(-0.18 if k % 2 == 0 else 0.18), rng=rng), at)


def _hook(canvas, bar_at: float, *, amp: float, inverted: bool = False, rng=None):
    for note, start, length in (HOOK_INVERTED if inverted else HOOK):
        place(canvas, ep(note, length * BEAT * 0.95, vel=amp, pan=0.0, rng=rng), bar_at + start * BEAT)


def _drums(canvas, kicks: list[float], start: float, bars: int, pattern: str, *, kick_amp: float, tick_amp: float,
           rng=None, drop_bars: set[int] = frozenset()):
    for b in range(bars):
        bar_at = start + b * BAR
        dropped = b in drop_bars
        for beat in range(4):
            at = bar_at + beat * BEAT
            if pattern == "half":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=kick_amp * (1.0 if beat == 0 else 0.85)), at)
                    kicks.append(at)
                if beat in (1, 3):
                    place(canvas, rim(amp=tick_amp * 0.6), at)
                place(canvas, tick(amp=tick_amp * 0.55, rng=rng), at + 0.5 * BEAT)
            elif pattern == "four":
                if not dropped:
                    place(canvas, kick(amp=kick_amp * (1.0 if beat == 0 else 0.8)), at)
                    kicks.append(at)
                place(canvas, tick(amp=tick_amp * (1.0 if beat % 2 else 0.7), open_=(beat == 3), rng=rng), at + 0.5 * BEAT)
                if beat in (1, 3):
                    place(canvas, rim(amp=tick_amp * 0.8), at)
            elif pattern == "dotted":
                if beat == 0 and not dropped:
                    place(canvas, kick(amp=kick_amp), at)
                    kicks.append(at)
                if beat == 1:
                    place(canvas, kick(amp=kick_amp * 0.75), at + 0.5 * BEAT)
                    kicks.append(at + 0.5 * BEAT)
                if beat == 3:
                    place(canvas, tick(amp=tick_amp, rng=rng), at)
            elif pattern == "pulse":
                if beat in (0, 2) and not dropped:
                    place(canvas, kick(amp=kick_amp * 0.9), at)
                    kicks.append(at)


def _bassline(canvas, chord: str, bar_at: float, *, amp: float, eighths: bool = True, full: bool = False):
    root = CHORDS[chord]["bass"]
    steps = range(8) if eighths else (0, 4)
    for k in steps:
        if eighths and not full and k in (3, 7):
            continue
        place(canvas, bass(root, 0.42 if eighths else 1.2, amp=amp * (1.0 if k % 2 == 0 else 0.7)), bar_at + k * 0.5 * BEAT)


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


def render_bed(v: Voicing, segment: str, dur_s: float) -> np.ndarray:
    """Eight-bar phrases; the layers each phrase carries are drawn by the day's
    seed, so the bed moves without ever repeating a bar; the hook once a
    phrase on the keys, the rest ostinato; a bar in eight dropped."""
    pattern = {"lead": "half", "second": "half", "desk": "four", "opinion": "dotted", "close": "half"}[segment]
    prog = v.progression[segment]
    bars = int(math.ceil(dur_s / BAR)) + 1
    n = int((bars * BAR + 3.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    kicks: list[float] = []
    for b in range(bars):
        chord = prog[b % len(prog)]
        at = b * BAR
        phrase = b // 8
        pos = b % 8
        layers = v.rng.random()
        place(pads, pad(chord, BAR + 0.4, amp=0.85 + 0.15 * (phrase % 2), attack_s=0.6, rng=v.rng), at)
        if segment == "desk" or pos not in (3, 7) or layers < 0.5:
            _bassline(low, chord, at, amp=0.72 if segment != "desk" else 0.85, eighths=segment == "desk" or pos % 2 == 0)
        if pos in (0, 1, 4, 5) or segment == "desk":
            rests = {3, 7} if segment != "desk" and v.rng.random() < 0.5 else set()
            _ostinato(keys, chord, at, amp=0.34 if segment != "desk" else 0.4, rests=rests, rng=v.rng)
        if pos == 6 and chord in ("Dm", "Bb"):
            _hook(keys, at, amp=0.62, inverted=(segment == "opinion"), rng=v.rng)
    drop = {b for b in range(bars) if b % 8 == 7 and b > 0}
    _drums(drums, kicks, 0.0, bars, pattern, kick_amp=0.9, tick_amp=0.42 if segment != "desk" else 0.5, rng=v.rng, drop_bars=drop)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=3.0)
    mix = reverb(keys, wet=0.3, seed=v.seed + 3) + reverb(pads, wet=0.42, decay_s=2.4, seed=v.seed + 4) + low + drums
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


def render_entrance(v: Voicing, dur_s: float = 6.8) -> np.ndarray:
    """i to iv, a dotted pulse, the hook inverted and left on the dominant: a
    question. The Opinion's anchor starts over the last bar."""
    n = int((dur_s + 2.0) * SR)
    keys = np.zeros((n, 2))
    pads = np.zeros((n, 2))
    low = np.zeros((n, 2))
    drums = np.zeros((n, 2))
    kicks: list[float] = []
    for b, chord in enumerate(["Dm", "Gm", "Asus"]):
        at = b * BAR * 0.75
        place(pads, pad(chord, BAR * 0.75 + 0.4, amp=0.9, attack_s=0.5 if b else 1.0, rng=v.rng), at)
        _bassline(low, chord, at, amp=0.7, eighths=False)
    _drums(drums, kicks, 0.0, 2, "dotted", kick_amp=0.85, tick_amp=0.38, rng=v.rng)
    _hook(keys, 0.0, amp=0.8, inverted=True, rng=v.rng)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks, depth_db=4.0)
    mix = reverb(keys, wet=0.34, seed=v.seed + 6) + reverb(pads, wet=0.45, decay_s=2.8, seed=v.seed + 7) + low + drums
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
    land = 4 * BAR
    place(fx, riser(1.5, amp=0.55, rng=v.rng), land - 1.5)
    place(drums, impact(amp=1.0), land)
    kicks.append(land)
    place(pads, pad("D", dur_s - land + 1.0, amp=1.0, attack_s=0.05, release_s=4.0, rng=v.rng), land)
    for note, pan_ in (("D4", -0.1), ("F#4", 0.1), ("A4", 0.0), ("D5", 0.0)):
        place(keys, ep(note, 4.0, vel=0.75, pan=pan_, rng=v.rng), land)
    place(low, bass("D2", 2.5, amp=0.9), land)
    keys = tempo_delay(keys)
    pads = sidechain(pads, kicks)
    low = sidechain(low, kicks, depth_db=3.0)
    mix = reverb(keys, wet=0.3, seed=v.seed + 8) + reverb(pads, wet=0.42, decay_s=3.0, seed=v.seed + 9) + low + drums + fx
    mix = mix[: int(dur_s * SR)]
    tail = int(3.0 * SR)
    mix[-tail:] *= (np.cos(np.linspace(0, math.pi / 2, tail)) ** 2)[:, None]
    return mix
